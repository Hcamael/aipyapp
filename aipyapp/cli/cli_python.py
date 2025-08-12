#!/usr/bin/env python
# -*- coding: utf-8 -*-
import code
import builtins

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.history import FileHistory
from pygments.lexers.python import PythonLexer

from ..aipy import TaskManager
from .. import T, __version__

class PythonCompleter(WordCompleter):
    def __init__(self, ai):
        names = ['exit()']
        names += [name for name in dir(builtins)]
        names += [f"ai.{attr}" for attr in dir(ai) if not attr.startswith('_')]
        super().__init__(names, ignore_case=True)
    
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

    interp = code.InteractiveConsole({'ai': ai})

    completer = PythonCompleter(ai)
    lexer = PygmentsLexer(PythonLexer)
    auto_suggest = AutoSuggestFromHistory()
    history = FileHistory(str(settings['config_dir'] / '.history.py'))
    session = PromptSession(history=history, completer=completer, lexer=lexer, auto_suggest=auto_suggest)
    while True:
        try:
            user_input = session.prompt(HTML('<ansiblue>>> </ansiblue>'))
            if user_input.strip() in {"exit()", "quit()"}:
                break
            interp.push(user_input)
        except EOFError:
            console.print("[bold yellow]Exiting...")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}")
