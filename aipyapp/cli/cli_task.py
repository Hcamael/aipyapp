#!/usr/bin/env python
# -*- coding: utf-8 -*-
from importlib.resources import read_text

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from ..aipy import TaskManager, ConfigManager, CONFIG_DIR
from .. import T, set_lang, __version__, __respkg__
from ..config import LLMConfig
from ..aipy.wizard import config_llm
from .command import CommandManager, CommandError
from ..display import DisplayManager

STYLE_MAIN = {
    'completion-menu.completion': 'bg:green #ffffff',
    'completion-menu.completion.current': 'bg:#444444 #ffffff',
    'completion-menu.meta': 'bg:#000000 #999999',
    'completion-menu.meta.current': 'bg:#444444 #aaaaaa',
    'prompt': 'green',
    'bottom-toolbar': 'bg:#FFFFFF green'
}

STYLE_AI = {
    'completion-menu.completion': 'bg:#008080 #ffffff',         # 深蓝背景，白色文本
    'completion-menu.completion.current': 'bg:#005577 #ffffff', # 当前选中，亮蓝
    'completion-menu.meta': 'bg:#002244 #cccccc',               # 补全项的 meta 信息
    'completion-menu.meta.current': 'bg:#005577 #eeeeee',       # 当前选中的 meta
    'prompt': '#008080',
    'bottom-toolbar': "bg:#880000 #008080"
}

class InteractiveConsole():
    def __init__(self, tm, console, settings):
        self.tm = tm
        self.names = tm.client_manager.names
        self.history = FileHistory(str(CONFIG_DIR / ".history"))
        self.console = console
        self.settings = settings
        self.task = None
        self.style_main = Style.from_dict(STYLE_MAIN)
        self.style_task = Style.from_dict(STYLE_AI)
        self.command_manager = CommandManager(tm, console)
        self.completer = self.command_manager
        self.session = PromptSession(history=self.history, completer=self.completer, auto_suggest=AutoSuggestFromHistory(), bottom_toolbar=self.get_bottom_toolbar)
    
    def get_main_status(self):
        status = self.tm.get_status()
        try:
            mcp = status['mcp']
            mcp_text = f" | MCP: {mcp['enabled_servers']}/{mcp['total_servers']}S, {mcp['enabled_tools']}/{mcp['total_tools']}T"
        except KeyError:
            mcp_text = ""
        return f"LLM: {status['llm']} | Role: {status['role']} | Display: {status['display']} | Tasks: {status['tasks']}{mcp_text}"
    
    def get_task_status(self):
        if self.task:
            status = self.task.get_status()
            return f"LLM: {status['llm']} | Blocks: {status['blocks']} | Steps: {status['steps']}"
        return ""
    
    def get_bottom_toolbar(self):
        if self.command_manager.is_task_mode():
            status = self.get_task_status()
            text = f"[AI] {status}"
        else:
            status = self.get_main_status()
            text = f"[Main] {status}"
        return [('class:bottom-toolbar', text)]
    
    def input_with_possible_multiline(self, prompt_text, task_mode=False):
        session = self.session
        style = self.style_task if task_mode else self.style_main
        cursor_shape = CursorShape.BEAM if not task_mode else CursorShape.BLOCK
        first_line = session.prompt([("class:prompt", prompt_text)], style=style, cursor=cursor_shape)
        if not first_line.endswith("\\"):
            return first_line
        # Multi-line input
        lines = [first_line.rstrip("\\")]
        while True:
            next_line = session.prompt([("class:prompt", "... ")], style=style)
            if next_line.endswith("\\"):
                lines.append(next_line.rstrip("\\"))
            else:
                lines.append(next_line)
                break
        return "\n".join(lines)

    def run_task(self, task, instruction):
        try:
            task.run(instruction)
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            self.console.print_exception()

    def start_task_mode(self, task, instruction=None):
        if instruction:
            self.console.print(f"[AI] {T('Enter Ctrl+d or /done to end current task')}", style="cyan")
            self.run_task(task, instruction)
        else:
            self.console.print(f"[AI] {T('Resuming task')}: {task.instruction[:32]}", style="cyan")
            
        while True:
            self.task = task
            self.command_manager.set_task_mode(task)
            try:
                user_input = self.input_with_possible_multiline(">>> ", task_mode=True).strip()
                if len(user_input) < 2: continue
            except (EOFError, KeyboardInterrupt):
                break

            if user_input in ('/done', 'done'):
                break

            if user_input.startswith('/'):
                self.command_manager.execute(user_input)
                continue
            self.run_task(task, user_input)

        try:
            task.done()
        except Exception as e:
            self.console.print_exception()
        self.task = None
        self.console.print(f"[{T('Exit AI mode')}]", style="cyan")

    def run(self):
        self.console.print(f"[Main] {T('Please enter an instruction or `/help` for more information')}", style="green")
        tm = self.tm
        while True:
            self.command_manager.set_main_mode()
            try:
                user_input = self.input_with_possible_multiline(">> ").strip()
                if len(user_input) < 2:
                    continue

                if not user_input.startswith('/'):
                    task = tm.new_task()
                    self.start_task_mode(task, user_input)
                    continue

                try:
                    ret = self.command_manager.execute(user_input)
                    if ret and ret['command'] == 'task' and ret['subcommand'] in ('use', 'load'):
                        task = ret['ret']
                        self.start_task_mode(task)
                except CommandError as e:
                    self.console.print(f"[red]{e}[/red]")
                    continue
            except (EOFError, KeyboardInterrupt):
                break

def main(args):
    console = Console(record=True)
    console.print(f"🚀 Python use - AIPython ({__version__}) [[pink]https://aipy.app[/pink]]", style="bold green")
    console.print(read_text(__respkg__, "logo.txt"))
    conf = ConfigManager(args.config_dir)
    settings = conf.get_config()
    lang = settings.get('lang')
    if lang: set_lang(lang)
    llm_config = LLMConfig(CONFIG_DIR / "config")
    if conf.check_config(gui=True) == 'TrustToken':
        if llm_config.need_config():
            console.print(f"[yellow]{T('Starting LLM Provider Configuration Wizard')}[/yellow]")
            try:
                config = config_llm(llm_config)
            except KeyboardInterrupt:
                console.print(f"[yellow]{T('User cancelled configuration')}[/yellow]")
                return
            if not config:
                return
        settings["llm"] = llm_config.config

    if args.fetch_config:
        conf.fetch_config()
        return

    settings.gui = False
    settings.debug = args.debug
    settings.config_dir = CONFIG_DIR
    if args.role:
        settings['role'] = args.role.lower()

    # 初始化显示效果管理器
    display_style = args.style or settings.get('display', 'classic')
    display_manager = DisplayManager(display_style, console=console)
    try:
        tm = TaskManager(settings, display_manager=display_manager)
    except Exception as e:
        console.print_exception()
        return
    
    update = tm.get_update()
    if update and update.get('has_update'):
        console.print(f"[bold red]🔔 号外❗ {T('Update available')}: {update.get('latest_version')}")
   
    if not tm.client_manager:
        console.print(f"[bold red]{T('No available LLM, please check the configuration file')}")
        return
    
    if args.cmd:
        tm.new_task().run(args.cmd)
        return
    InteractiveConsole(tm, console, settings).run()
