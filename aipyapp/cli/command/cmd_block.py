#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.syntax import Syntax

from .utils import print_records
from .base import CommandMode, Completable
from .base_parser import ParserCommand
from ... import T

class BlockCommand(ParserCommand):
    """Block command"""
    name = "block"
    description = T("Manage code blocks")
    modes = [CommandMode.TASK]
    
    def get_arg_values(self, arg, subcommand=None, partial_value=''):
        if arg.name == 'index':
            ctx = self.manager.context
            return [Completable(str(block.Index), f"{block.Name} ({block.Language})") for block in ctx.task.list_code_blocks()]
        return None

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List code blocks'))
        parser = subparsers.add_parser('show', help=T('Show code block source'))
        parser.add_argument('index', type=int, help=T('Index of the code block'))
        parser = subparsers.add_parser('run', help=T('Run code block'))
        parser.add_argument('index', type=int, help=T('Index of the code block'))

    def cmd(self, args, ctx):
        return self.cmd_list(args, ctx)
    
    def cmd_show(self, args, ctx):
        """显示代码块源码"""
        task = ctx.task
        block = task.get_code_block(args.index)
        if not block:
            ctx.console.print(T("Code block not found"))
            return False
        
        syntax = Syntax(block.code, block.lang, theme="github-dark", line_numbers=False)
        
        ctx.console.print(f"\n[bold]{T('Code Block')}: {block.name} (v{block.version})[/bold]")
        if block.path:
            ctx.console.print(f"[dim]{T('Path')}: {block.path}[/dim]")
        ctx.console.print("")
        ctx.console.print(syntax)
        return True
    
    def cmd_run(self, args, ctx):
        """运行代码块"""
        task = ctx.task
        block = task.get_code_block(args.index)
        if not block:
            ctx.console.print(T("Code block not found"))
            return False
        task.run_code_block(block)
        return True
    
    def cmd_list(self, args, ctx):
        """列出所有代码块"""
        task = ctx.task
        blocks = task.list_code_blocks()
        print_records(blocks, title=T("Code Blocks"))