#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter, merge_completers

from ..aipy import TaskManager, ConfigManager, CONFIG_DIR
from .. import T, set_lang, __version__
from ..config import LLMConfig
from ..aipy.wizard import config_llm
from .command import CommandManager, TaskCommandManager

from loguru import logger

if TYPE_CHECKING:
    from ..aipy.task import Task

STYLE_MAIN = {
    'completion-menu.completion': 'bg:#000000 #ffffff',
    'completion-menu.completion.current': 'bg:#444444 #ffffff',
    'completion-menu.meta': 'bg:#000000 #999999',
    'completion-menu.meta.current': 'bg:#444444 #aaaaaa',
    'prompt': 'green',
}

STYLE_AI = {
    'completion-menu.completion': 'bg:#002244 #ffffff',         # 深蓝背景，白色文本
    'completion-menu.completion.current': 'bg:#005577 #ffffff', # 当前选中，亮蓝
    'completion-menu.meta': 'bg:#002244 #cccccc',               # 补全项的 meta 信息
    'completion-menu.meta.current': 'bg:#005577 #eeeeee',       # 当前选中的 meta
    'prompt': 'cyan',
}

log = logger.bind(src='aibot')

class InteractiveConsole():
    def __init__(self, tm, console, settings):
        self.tm = tm
        self.names = tm.client_manager.names
        self.history = FileHistory(str(CONFIG_DIR / ".history"))
        self.console = console
        self.settings = settings
        self.style_main = Style.from_dict(STYLE_MAIN)
        self.style_task = Style.from_dict(STYLE_AI)
        self.command_manager_main = CommandManager(tm)
        self.command_manager_task = TaskCommandManager(tm)
        self.completer_main = self.command_manager_main
        self.completer_task = self.command_manager_task
        self.session = PromptSession(history=self.history, completer=self.completer_main, style=self.style_main)
        self.session_task = PromptSession(history=self.history, completer=self.completer_task, style=self.style_task)
    
    def input_with_possible_multiline(self, prompt_text, task_mode=False):
        session = self.session_task if task_mode else self.session
        first_line = session.prompt([("class:prompt", prompt_text)])
        if not first_line.endswith("\\"):
            return first_line
        # Multi-line input
        lines = [first_line.rstrip("\\")]
        while True:
            next_line = session.prompt([("class:prompt", "... ")])
            if next_line.endswith("\\"):
                lines.append(next_line.rstrip("\\"))
            else:
                lines.append(next_line)
                break
        return "\n".join(lines)

    def run_task(self, task: 'Task', instruction):
        try:
            r = task.run(instruction)
            self.console.print(f"⚡ response: {r}", style='dim white')
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            log.error(f"⚡ error: {e}")
            self.console.print_exception()

    def start_task_mode(self, task, instruction):
        self.console.print(f"{T('Enter AI mode, start processing tasks, enter Ctrl+d or /done to end the task')}", style="cyan")
        self.run_task(task, instruction)
        while True:
            try:
                user_input = self.input_with_possible_multiline(">>> ", task_mode=True).strip()
                if len(user_input) < 2: continue
            except (EOFError, KeyboardInterrupt):
                break

            if user_input in ('/done', 'done'):
                break

            if self.command_manager_task.execute(task, user_input):
                continue

            self.run_task(task, user_input)

        try:
            task.done()
        except Exception as e:
            self.console.print_exception()
        self.console.print(f"[{T('Exit AI mode')}]", style="cyan")

    def run(self):
        self.console.print(f"{T('Please enter an instruction or `/help` for more information')}", style="green")
        tm = self.tm
        while True:
            try:
                user_input = self.input_with_possible_multiline(">> ").strip()
                if len(user_input) < 2:
                    continue

                if user_input.startswith('/'):
                    self.command_manager_main.execute(user_input)
                    continue
                else:
                    task = tm.new_task('admin')
                    self.start_task_mode(task, user_input)
            except (EOFError, KeyboardInterrupt):
                break

def main(args):
    console = Console(record=True)
    console.print(f"[bold cyan]🚀 Python use - AIPython ({__version__}) [[green]https://aipy.app[/green]]")
    conf = ConfigManager(args.config_dir)
    settings = conf.get_config()
    lang = settings.get('lang')
    if lang: set_lang(lang)

    settings.gui = False
    settings.debug = True
    settings.config_dir = CONFIG_DIR
    
    try:
        tm = TaskManager(settings, console=console)
    except Exception as e:
        console.print_exception()
        return
   
    if not tm.client_manager:
        console.print(f"[bold red]{T('No available LLM, please check the configuration file')}")
        return
    
    InteractiveConsole(tm, console, settings).run()
