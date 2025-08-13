from rich import print
import argparse

from aipyapp import T
from ..base import ParserCommand
from .utils import record2table, row2table

class MCPCommand(ParserCommand):
    name = 'mcp'
    description = T('MCP operations')

    def add_subcommands(self, subparsers):
        subparsers.add_parser('status', help=T('Show MCP status'))

        common_parser = argparse.ArgumentParser(add_help=False)
        common_parser.add_argument('--user', action='store_true', help=T('User MCP'))
        common_parser.add_argument('--sys', action='store_true', help=T('System MCP'))
        subparsers.add_parser('enable', help=T('Enable MCP'), parents=[common_parser])
        subparsers.add_parser('disable', help=T('Disable MCP'), parents=[common_parser])

        # 服务器管理子命令
        server_parser = subparsers.add_parser('server', help=T('MCP server operations'))
        server_group = server_parser.add_mutually_exclusive_group()
        server_group.add_argument('--list', action='store_true', help=T('List MCP servers'))
        server_group.add_argument('--enable', nargs='?', const='*',help=T('Enable MCP server'))
        server_group.add_argument('--disable', nargs='?', const='*', help=T('Disable MCP server'))
        
    def _enable_mcp(self, args, ctx, enable):
        mcp = ctx.tm.mcp
        if args.user:
            ret = mcp.enable_user_mcp(enable)
        elif args.sys:
            ret = mcp.enable_sys_mcp(enable)
        else:
            ctx.console.print(T('Please specify --user or --sys'), style="bold red")
            ret = None
        ctx.console.print(T('Success') if ret else T('Failed'), style="bold green" if ret else "bold red")
        return ret
    
    def cmd_status(self, args, ctx):
        mcp = ctx.tm.mcp
        ret = mcp.get_status()
        rows = [
            (T('System MCP'), T('Enabled') if ret['sys_mcp_enabled'] else T('Disabled')),
            (T('User MCP'), T('Enabled') if ret['user_mcp_enabled'] else T('Disabled')),
            (T('Total Servers'), ret['total_servers']),
            (T('Enabled Servers'), ret['enabled_servers']),
            (T('Total Tools'), ret['total_tools']),
            (T('Enabled Tools'), ret['enabled_tools'])
        ]
        table = row2table(rows, title=T('MCP status'), headers=["Name", "Value"])
        ctx.console.print(table)
        return ret
    
    def cmd_enable(self, args, ctx):
        ret = self._enable_mcp(args, ctx, True)
        return ret

    def cmd_disable(self, args, ctx):
        ret = self._enable_mcp(args, ctx, False)
        return ret

    def cmd_server(self, args, ctx):
        mcp = ctx.tm.mcp
        if args.enable:
            ret = mcp.enable_user_server(args.enable)
        elif args.disable:
            ret = mcp.enable_user_server(args.disable, False)
        else:
            servers = mcp.list_user_servers()
            table = record2table(servers, title=T('MCP servers'))
            ctx.console.print(table)
            ret = True
        ctx.console.print(T('Success') if ret else T('Failed'), style="bold green" if ret else "bold red")
        return ret
    
    def cmd(self, args, ctx):
        return self.cmd_status(args, ctx)