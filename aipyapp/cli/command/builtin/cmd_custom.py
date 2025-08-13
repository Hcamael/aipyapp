
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
        if name == 'name' and subcommand == 'show':
            custom_commands = self.manager.custom_command_manager.get_all_commands()
            return [(cmd.name, cmd.description) for cmd in custom_commands]
        return None

    def cmd_list(self, args, ctx):
        """List all custom commands"""
        custom_commands = self.manager.custom_command_manager.get_all_commands()
        
        if not custom_commands:
            print(f"[yellow]{T('No custom commands found')}[/yellow]")
            dirs_str = ', '.join(str(d) for d in self.manager.custom_command_manager.command_dirs)
            print(f"{T('Custom commands directories')}: {dirs_str}")
            return
        
        rows = []
        for cmd in custom_commands:
            modes_str = ', '.join([mode.value for mode in cmd.modes])
            
            # Find which directory this command belongs to
            file_path_str = str(cmd.file_path)
            for command_dir in self.manager.custom_command_manager.command_dirs:
                try:
                    relative_path = cmd.file_path.relative_to(command_dir)
                    file_path_str = str(relative_path)
                    break
                except ValueError:
                    # This file is not in this directory, try next
                    continue
            
            rows.append([cmd.name, cmd.description, modes_str, file_path_str])
        
        table = row2table(
            rows, 
            headers=[T('Name'), T('Description'), T('Modes'), T('File')], 
            title=T('Custom Commands')
        )
        ctx.console.print(table)

    def cmd_reload(self, args, ctx):
        """Reload custom commands from disk"""
        count = self.manager.reload_custom_commands()
        ctx.console.print(f"[green]{T('Reloaded')} {count} {T('custom commands')}[/green]")

    def cmd_show(self, args, ctx):
        """Show custom command details"""
        command = self.manager.custom_command_manager.get_command(args.name)
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