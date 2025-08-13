#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.table import Table

from ..base import CommandMode, ParserCommand
from aipyapp import T

class ContextCommand(ParserCommand):
    """上下文管理命令"""
    name = "context"
    description = T("Manage LLM conversation context")
    modes = [CommandMode.TASK]
    
    def add_subcommands(self, subparsers):
        subparsers.add_parser('show', help=T('Show context'))
        subparsers.add_parser('clear', help=T('Clear context'))
        subparsers.add_parser('stats', help=T('Show context stats'))
        parser = subparsers.add_parser('config', help=T('Show context config'))
        parser.add_argument('--strategy', choices=['sliding_window', 'importance_filter', 'summary_compression', 'hybrid'], help=T('Set compression strategy'))
        parser.add_argument('--max-tokens', type=int, help=T('Set max tokens'))
        parser.add_argument('--max-rounds', type=int, help=T('Set max rounds'))
        parser.add_argument('--auto-compress', action='store_true', help=T('Set auto compress'))
        
    def cmd(self, args, ctx):
        self.cmd_show(args, ctx)
        
    def cmd_show(self, args, ctx):
        """显示当前上下文"""
        messages = ctx.task.client.context_manager.get_messages()
        console = ctx.console
        
        if not messages:
            console.print(T("No conversation history"), style="yellow")
            return
        
        table = Table(title=T("Conversation context"))
        table.add_column(T("Role"), style="cyan")
        table.add_column(T("Content"), style="white")
        
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str) and len(content) > 100:
                content = content[:100] + "..."
            table.add_row(msg.get('role', ''), content)
        
        console.print(table)
    
    def cmd_clear(self, args, ctx):
        """清空上下文"""
        task = ctx.task
        console = ctx.console
        
        task.client.context_manager.clear()
        console.print(T("Context cleared"), style="green")
    
    def cmd_stats(self, args, ctx):
        """显示上下文统计信息"""
        task = ctx.task
        console = ctx.console
        
        stats = task.client.context_manager.get_stats()
        
        if not stats:
            console.print(T("Context manager not enabled"), style="yellow")
            return
        
        table = Table(title=T("Context stats"))
        table.add_column(T("Metric"), style="cyan")
        table.add_column(T("Value"), style="white")
        
        table.add_row(T("Message count"), str(stats['message_count']))
        table.add_row(T("Current token"), str(stats['total_tokens']))
        table.add_row(T("Max tokens"), str(stats['max_tokens']))
        table.add_row(T("Compression ratio"), f"{stats['compression_ratio']:.2f}")
        
        console.print(table)
    
    def cmd_config(self, args, ctx):
        """显示上下文配置"""
        if args.strategy or args.max_tokens or args.max_rounds:
            return self._update_config(args, ctx)

        task = ctx.task
        console = ctx.console
        config = task.client.context_manager.config
        
        table = Table(title=T("Context config"))
        table.add_column(T("Config item"), style="cyan")
        table.add_column(T("Value"), style="white")
        
        table.add_row(T("Strategy"), config.strategy.value)
        table.add_row(T("Max tokens"), str(config.max_tokens))
        table.add_row(T("Max rounds"), str(config.max_rounds))
        table.add_row(T("Auto compress"), str(config.auto_compress))
        table.add_row(T("Compression ratio"), str(config.compression_ratio))
        table.add_row(T("Importance threshold"), str(config.importance_threshold))
        table.add_row(T("Summary max length"), str(config.summary_max_length))
        table.add_row(T("Preserve system message"), str(config.preserve_system))
        table.add_row(T("Preserve recent rounds"), str(config.preserve_recent))
        
        console.print(table)
    
    def _update_config(self, args, ctx):
        """更新上下文配置"""
        task = ctx.task
        console = ctx.console
        
        current_config = task.client.context_manager.config
        
        # 更新配置
        if args.strategy:
            if not current_config.set_strategy(args.strategy):
                console.print(T("Invalid strategy: {}, using default strategy", args.strategy), style="red")
        
        if args.max_tokens:
            current_config.max_tokens = args.max_tokens
        
        if args.max_rounds:
            current_config.max_rounds = args.max_rounds
        
        # 应用新配置
        task.client.context_manager.update_config(current_config)
        console.print(T("Config updated"), style="green") 