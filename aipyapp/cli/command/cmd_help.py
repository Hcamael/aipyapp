from rich import print

from  ... import T
from .base import BaseCommand
from .utils import print_table

class HelpCommand(BaseCommand):
    name = 'help'
    description = T('Show available commands or detailed help for a specific command')

    def add_arguments(self, parser):
        parser.add_argument('target_command', nargs='?', default=None, help='Command to show detailed help for')

    def execute(self, args):
        manager = self.manager
        if args.target_command:
            if args.target_command in manager.commands:
                parser = manager.commands[args.target_command].parser
                print(f"Help for command '{args.target_command}':")
                print(parser.format_help())
            else:
                print(f"Unknown command: {args.target_command}")
        else:
            rows = []
            for cmd, cmd_instance in sorted(manager.commands.items()):
                rows.append([f"/{cmd}", cmd_instance.description])
            print_table(rows, headers=[T('Command'), T('Description')], title=T('Available commands'))
            print()
            print(T("Or directly enter the question to be processed by AI, for example:\n>> Who are you?"))
            print()
