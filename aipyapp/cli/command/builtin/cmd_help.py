from aipyapp import T
from ..base import ParserCommand
from .utils import row2table
from ..custom import MarkdownCommand

class HelpCommand(ParserCommand):
    name = 'help'
    description = T('Show available commands or detailed help for a specific command')

    def add_arguments(self, parser):
        parser.add_argument('target_command', nargs='?', help='Command to show detailed help for')

    def get_arg_values(self, name, subcommand=None):
        if name == 'target_command':
            return [(cmd.name, cmd.description) for cmd in self.manager.commands.values()]
        return None
    
    def execute(self, args, ctx):
        console = ctx.console
        commands = self.manager.commands
        if args.target_command:
            if args.target_command in commands:
                parser = commands[args.target_command].parser
                console.print(f"Help for command '{args.target_command}':")
                console.print(parser.format_help())
            else:
                console.print(f"Unknown command: {args.target_command}")
        else:
            rows = []
            for name, command in commands.items():
                kind = "user" if isinstance(command, MarkdownCommand) else "system"
                modes = ', '.join([mode.value for mode in command.modes])
                rows.append([f"/{name}", kind, modes,command.description])
            table = row2table(rows, headers=[T('Command'), T('Type'), T('Modes'), T('Description')], title=T('Available commands'))
            console.print(table)
            console.print()
            console.print(T("Or directly enter the question to be processed by AI, for example:\n>> Who are you?"))
            console.print()
