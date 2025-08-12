import os
from pathlib import Path

from rich import print
from rich.panel import Panel
from rich.syntax import Syntax

from ... import T
from .base import CommandMode, Completable
from .base_parser import ParserCommand
from .utils import print_table


class CustomCommand(ParserCommand):
    name = 'custom'
    description = T('Manage custom commands')
    modes = [CommandMode.MAIN, CommandMode.TASK]

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List all custom commands'))
        subparsers.add_parser('reload', help=T('Reload custom commands from disk'))
        
        show_parser = subparsers.add_parser('show', help=T('Show custom command details'))
        show_parser.add_argument('name', type=str, help=T('Custom command name'))
        
        create_parser = subparsers.add_parser('create', help=T('Create new custom command'))
        create_parser.add_argument('name', type=str, help=T('Command name'))
        create_parser.add_argument('--description', type=str, default='', help=T('Command description'))
        create_parser.add_argument('--mode', choices=['main', 'task', 'both'], default='task', help=T('Command mode'))

    def get_arg_values(self, arg, subcommand=None, partial_value=''):
        if arg.name == 'name' and subcommand == 'show':
            custom_commands = self.manager.custom_command_manager.get_all_commands()
            return [Completable(cmd.name, cmd.description) for cmd in custom_commands]
        return super().get_arg_values(arg, subcommand, partial_value)

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
        
        print_table(
            rows, 
            headers=[T('Name'), T('Description'), T('Modes'), T('File')], 
            title=T('Custom Commands')
        )

    def cmd_reload(self, args, ctx):
        """Reload custom commands from disk"""
        count = self.manager.reload_custom_commands()
        print(f"[green]{T('Reloaded')} {count} {T('custom commands')}[/green]")

    def cmd_show(self, args, ctx):
        """Show custom command details"""
        command = self.manager.custom_command_manager.get_command(args.name)
        if not command:
            print(f"[red]{T('Custom command not found')}: {args.name}[/red]")
            return
        
        # Show command info
        print(Panel(
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
            print(Panel(syntax, title=T('Command Content'), border_style="green"))
        except Exception as e:
            print(f"[red]{T('Error reading file')}: {e}[/red]")

    def cmd_create(self, args, ctx):
        """Create a new custom command"""
        # Use the first available directory or create a default one
        command_dirs = self.manager.custom_command_manager.command_dirs
        
        if not command_dirs:
            print(f"[red]{T('No custom command directories configured')}[/red]")
            return
            
        # Use the first directory for creation
        command_dir = next(iter(command_dirs))
        
        # Ensure the directory exists
        command_dir.mkdir(parents=True, exist_ok=True)
        
        command_file = command_dir / f"{args.name}.md"
        
        if command_file.exists():
            print(f"[red]{T('Command already exists')}: {args.name}[/red]")
            return
        
        # Determine modes
        if args.mode == 'both':
            modes = ['main', 'task']
        else:
            modes = [args.mode]
        
        # Create command template
        template_content = f'''---
name: "{args.name}"
description: "{args.description or f'Custom {args.name} command'}"
modes: {modes}
arguments:
  - name: "input"
    type: "str"
    required: false
    help: "Input parameter"
---

# {args.name.title()} Command

This is a custom command: {{{{input}}}}

You can modify this template to create your custom command logic.

## Available template variables:
- {{{{input}}}}: The input parameter
- {{{{subcommand}}}}: The subcommand if any

## Template syntax:
- Use Jinja2 syntax for advanced templating
- Simple {{{{variable}}}} replacement for basic usage
'''
        
        try:
            command_file.write_text(template_content, encoding='utf-8')
            print(f"[green]{T('Created custom command')}: {command_file}[/green]")
            print(f"[yellow]{T('Run')}: /custom reload {T('to load the new command')}[/yellow]")
        except Exception as e:
            print(f"[red]{T('Error creating command')}: {e}[/red]")

    def cmd(self, args, ctx):
        """Default action: list commands"""
        self.cmd_list(args, ctx)