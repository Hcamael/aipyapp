#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .utils import record2table
from ..base import CommandMode, ParserCommand
from aipyapp import T

class StepsCommand(ParserCommand):
    """Steps command"""
    name = "step"
    description = T("Manage task steps")
    modes = [CommandMode.TASK]

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List task steps'))
        subparsers.add_parser('clear', help=T('Clear task steps'))
        parser = subparsers.add_parser('delete', help=T('Delete task steps'))
        parser.add_argument('index', type=int, help=T('Index of the task step to delete'))
        
    def get_arg_values(self, name, subcommand=None):
        if subcommand == 'delete' and name == 'index':
            ctx = self.manager.context
            return [(str(step.Index), step.Instruction[:32]) for step in ctx.task.list_steps()]
        return None
    
    def cmd(self, args, ctx):
        return self.cmd_list(args, ctx)
    
    def cmd_list(self, args, ctx):
        task = ctx.task
        steps = task.list_steps()
        table = record2table(steps, title=T("Task Steps"))
        ctx.console.print(table)
    
    def cmd_clear(self, args, ctx):
        task = ctx.task
        ret = task.clear_steps()
        if ret:
            ctx.console.print(T("Task steps cleared"))
        else:
            ctx.console.print(T("Failed to clear task steps"))
        return ret
    
    def cmd_delete(self, args, ctx):
        task = ctx.task
        ret = task.delete_step(args.index)
        if ret:
            ctx.console.print(T("Task step deleted"))
        else:
            ctx.console.print(T("Failed to delete task step"))
        return ret