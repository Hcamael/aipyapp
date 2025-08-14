#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .utils import record2table
from ..base import CommandMode, ParserCommand
from aipyapp import T
from rich.tree import Tree

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
        if name == 'index':
            ctx = self.manager.context
            return [(str(step.Index), step.Instruction[:32]) for step in ctx.task.list_steps()]
        return None
    
    def cmd(self, args, ctx):
        return self.cmd_list(args, ctx)
    
    def cmd_list(self, args, ctx):
        task = ctx.task
        steps = task.list_steps()
        
        if not steps:
            ctx.console.print(T("No task steps found"))
            return
        
        # 创建根树节点
        tree = Tree(f"[bold blue]{T('Task Steps')}[/bold blue]")
        
        for i, step in enumerate(steps, 1):
            # 获取字段值
            fields = step._fields if hasattr(step, '_fields') else step.keys()
            
            # 为每个步骤创建子节点
            step_node = tree.add(f"[bold cyan]Step {i}[/bold cyan]")
            
            for field in fields:
                value = getattr(step, field) if hasattr(step, field) else step[field]
                
                if field == 'Instruction':
                    # 长文本字段作为单个节点，保持原有格式
                    step_node.add(f"[yellow]{T(field)}:[/yellow]\n[dim]{value}[/dim]")
                else:
                    # 短字段直接添加到步骤节点
                    step_node.add(f"[yellow]{T(field)}:[/yellow] [green]{value}[/green]")
        
        ctx.console.print(tree)
    
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