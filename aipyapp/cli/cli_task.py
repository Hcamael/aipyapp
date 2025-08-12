#!/usr/bin/env python
# -*- coding: utf-8 -*-
from importlib.resources import read_text

from rich.console import Console
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from ..aipy import TaskManager
from .. import T, __version__, __respkg__
from .command import CommandManager, TaskModeResult, CommandError, CommandResult
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
        self.history = FileHistory(str(settings['config_dir'] / ".history"))
        self.console = console
        self.settings = settings
        self.task = None
        self.style_main = Style.from_dict(STYLE_MAIN)
        self.style_task = Style.from_dict(STYLE_AI)
        self.command_manager = CommandManager(settings,tm, console)
        self.completer = self.command_manager
        self.session = PromptSession(
            history=self.history, 
            completer=self.completer, 
            auto_suggest=AutoSuggestFromHistory(), 
            bottom_toolbar=self.get_bottom_toolbar,
            key_bindings=self.command_manager.create_key_bindings()
        )
    
    def get_main_status(self):
        status = self.tm.get_status()
        try:
            mcp_text = f" | MCP: {T('Enabled') if status['mcp_enabled'] else T('Disabled')}"
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

    def run_task(self, task, instruction, title=None):
        try:
            task.run(instruction, title=title)
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            self.console.print_exception()

    def start_task_mode(self, task, instruction=None, title=None):
        if instruction:
            self.console.print(f"[AI] {T('Enter Ctrl+d or /done to end current task')}", style="dim color(240)")
            self.run_task(task, instruction, title=title)
        else:
            self.console.print(f"[AI] {T('Resuming task')}: {task.instruction[:32]}", style="dim color(240)")
            
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

            if not user_input.startswith('/'):
                self.run_task(task, user_input)
                continue

            try:
                self.command_manager.execute(user_input)
            except CommandError as e:
                self.console.print(f"[red]{e}[/red]")

        try:
            task.done()
        except Exception as e:
            self.console.print_exception()
        self.task = None
        self.console.print(f"[{T('Exit AI mode')}]", style="dim")

    def run(self):
        self.console.print(f"[Main] {T('Please enter an instruction or `/help` for more information')}", style="dim color(240)")
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
                    if isinstance(ret, CommandResult) and isinstance(ret.result, TaskModeResult):
                        result = ret.result
                        if result.instruction:
                            task = tm.new_task()
                            title = result.title
                        else:
                            task = result.task
                            title = None
                        self.start_task_mode(task, result.instruction, title=title)
                        continue
                except CommandError as e:
                    self.console.print(f"[red]{e}[/red]")
            except (EOFError, KeyboardInterrupt):
                break

def get_logo_text(config_dir):
    path = config_dir / "logo.txt"
    if path.exists():
        logo_text = path.read_text()
    else:
        logo_text = read_text(__respkg__, "logo.txt")
    return logo_text

def main(settings):
    console = Console(record=True)
    console.print(f"🚀 Python use - AIPython ({__version__}) [[pink]https://aipy.app[/pink]]", style="bold green")
    logo_text = get_logo_text(settings['config_dir'])
    console.print(Text.from_ansi(logo_text))

    # 初始化显示效果管理器
    display_config = settings.get('display', {})
    display_manager = DisplayManager(display_config, console=console)
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
    
    cmd = settings.get('exec_cmd')
    if cmd:
        tm.new_task().run(cmd)
        return
    InteractiveConsole(tm, console, settings).run()
