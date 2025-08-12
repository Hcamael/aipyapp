#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.console import Console
from traitlets.config import Config
from IPython.terminal.prompts import ClassicPrompts, Token
from IPython.terminal.embed import embed, InteractiveShellEmbed
from IPython.core.magic import Magics, magics_class, line_cell_magic,line_magic, cell_magic, register_line_magic

from ..aipy import TaskManager
from .. import T, __version__

class MainPrompt(ClassicPrompts):
    def in_prompt_tokens(self):
        return [(Token.Prompt, '>> ')]

class TaskPrompt(ClassicPrompts):
    def in_prompt_tokens(self):
        return [(Token.Prompt, '>>> ')]
    
def get_task_config():
    c = Config()
    c.TerminalInteractiveShell.display_banner = False
    c.InteractiveShell.prompt_in1 = '>> '
    c.InteractiveShell.prompt_in2 = '... '
    c.InteractiveShell.prompt_out = ''
    c.InteractiveShell.banner1 = 'Use /ai "Task" to start a task'
    c.InteractiveShell.banner2 = 'For example: ai 获取Google网站标题\n'
    c.InteractiveShell.separate_in = ''
    c.InteractiveShell.separate_out = ''
    c.InteractiveShell.separate_out2 = ''
    c.InteractiveShell.prompts_class = TaskPrompt
    c.InteractiveShell.confirm_exit = False
    return c

def get_main_config():
    c = Config()
    c.TerminalInteractiveShell.display_banner = False
    c.InteractiveShell.prompt_in1 = '>> '
    c.InteractiveShell.prompt_in2 = '... '
    c.InteractiveShell.prompt_out = ''
    c.InteractiveShell.banner1 = 'Use /ai "Task" to start a task'
    c.InteractiveShell.banner2 = 'For example: ai 获取Google网站标题\n'
    c.InteractiveShell.separate_in = ''
    c.InteractiveShell.separate_out = ''
    c.InteractiveShell.separate_out2 = ''
    c.InteractiveShell.prompts_class = MainPrompt
    c.InteractiveShell.confirm_exit = False
    return c

@magics_class
class AIMagics(Magics):
    def __init__(self, shell, ai):
        super().__init__(shell)
        self.ai = ai

    @line_magic
    def task(self, line):
        task = self.ai.new_task()
        user_ns = {'task': task, 'settings': self.ai.settings}
        shell = InteractiveShellEmbed(user_ns=user_ns, config=get_task_config())
        shell()

    @line_magic
    def clear(self, _):
        self.ai.clear()

    @line_magic
    def save(self, line):
        self.ai.save(line)

    @line_cell_magic
    def ai(self, line, cell=None):
        print(line)
        print(cell)
    
def main(settings):
    console = Console(record=True)
    console.print(f"[bold cyan]🚀 Python use - AIPython ({__version__}) [[green]https://aipy.app[/green]]")

    try:
        ai = TaskManager(settings, console=console)
    except Exception as e:
        console.print_exception(e)
        return

    update = ai.get_update(True)
    if update and update.get('has_update'):
        console.print(f"[bold red]🔔 号外❗ {T('Update available')}: {update.get('latest_version')}")

    if not ai.client_manager:
        console.print(f"[bold red]{T('No available LLM, please check the configuration file')}")
        return
    
    names = ai.client_manager.names
    console.print(f"{T('Please use ai(task) to enter the task to be processed by AI (enter ai.use(llm) to switch to the following LLM:')}", style="green")
    console.print(f"[cyan]{T('Default')}: [green]{names['default']}，[cyan]{T('Enabled')}: [yellow]{' '.join(names['enabled'])}")

    user_ns = {'AI': ai, 'settings': settings}
    shell = InteractiveShellEmbed(user_ns=user_ns, config=get_main_config())
    shell.register_magics(AIMagics(shell, ai))
    shell()

