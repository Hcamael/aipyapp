
from rich.panel import Panel
from rich.syntax import Syntax

from aipyapp import T
from ..base import CommandMode, ParserCommand
from .utils import row2table

class CustomCommand(ParserCommand):
    name = 'custom'
    description = T('Manage custom commands')
    modes = [CommandMode.MAIN, CommandMode.TASK]

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List all custom commands'))
        subparsers.add_parser('reload', help=T('Reload custom commands from disk'))
        
        show_parser = subparsers.add_parser('show', help=T('Show custom command details'))
        show_parser.add_argument('name', type=str, help=T('Custom command name'))
        
    def get_arg_values(self, name, subcommand=None):
        if name == 'name':
            custom_commands = self.manager.user_commands
            return [(cmd.name, cmd.description) for cmd in custom_commands.values()]
        return None

    def cmd_list(self, args, ctx):
        """List all custom commands"""
        custom_commands = self.manager.user_commands
        if not custom_commands:
            print(f"[yellow]{T('No custom commands found')}[/yellow]")
            dirs_str = ', '.join(str(d) for d in self.manager.config.custom_command_dirs)
            print(f"{T('Custom commands directories')}: {dirs_str}")
            return
        
        rows = []
        for cmd in custom_commands.values():
            modes_str = ', '.join([mode.value for mode in cmd.modes])
            rows.append([cmd.name, cmd.description, modes_str, cmd.relative_path])
        
        table = row2table(
            rows, 
            headers=[T('Name'), T('Description'), T('Modes'), T('File')], 
            title=T('Custom Commands')
        )
        ctx.console.print(table)

    def cmd_reload(self, args, ctx):
        """Reload custom commands from disk"""
        commands = self.manager.init_custom_commands(reload=True)
        ctx.console.print(f"[green]{T('Reloaded')} {len(commands)} {T('custom commands')}[/green]")

    def cmd_show(self, args, ctx):
        """Show custom command details"""
        command = self.manager.user_commands.get(args.name)
        if not command:
            ctx.console.print(f"[red]{T('Custom command not found')}: {args.name}[/red]")
            return
        
        # Show command info
        ctx.console.print(Panel(
            f"**{T('Name')}:** {command.name}\n"
            f"**{T('Description')}:** {command.description}\n"
            f"**{T('Modes')}:** {', '.join([mode.value for mode in command.modes])}\n"
            f"**{T('File')}:** {command.file_path}",
            title=T('Command Details'),
            border_style="blue"
        ))
        
        # Show command content
        try:
            content = command.file_path.read_text(encoding='utf-8')
            syntax = Syntax(content, "markdown", theme="monokai", line_numbers=True)
            ctx.console.print(Panel(syntax, title=T('Command Content'), border_style="green"))
        except Exception as e:
            ctx.console.print(f"[red]{T('Error reading file')}: {e}[/red]")

    def cmd(self, args, ctx):
        """Default action: list commands"""
        self.cmd_list(args, ctx)