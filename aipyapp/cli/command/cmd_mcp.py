from rich import print

from ... import T
from .base import BaseCommand

class MCPCommand(BaseCommand):
    name = 'mcp'
    description = T('MCP operations')

    def process_mcp_ret(self, arg, ret):
        if ret.get("status", "success") == "success":
            mcp_status = T('Enabled') if ret.get("globally_enabled") else T('Disabled')
            print(f"[green]{T('MCP server status: {}').format(mcp_status)}[/green]")
            mcp_servers = ret.get("servers", [])
            if ret.get("globally_enabled", False):
                for server_name, info in mcp_servers.items():
                    server_status = T('Enabled') if info.get("enabled", False) else T('Disabled')
                    print(
                        "[", server_status, "]",
                        server_name, info.get("tools_count"), T("Tools")
                    )
        else:
            print("操作失败", ret.get("message", ''))

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List MCP servers'))
        parser = subparsers.add_parser('enable', help=T('Enable MCP server'))
        parser.add_argument('server', nargs='?', default=None, help=T('MCP server name'))
        parser = subparsers.add_parser('disable', help=T('Disable MCP server'))
        parser.add_argument('server', nargs='?', default=None, help=T('MCP server name'))

    def execute(self, args):
        print(args.raw_args)
        raw_args = args.raw_args
        if not raw_args:
            return
        
        tm = self.manager.tm
        if not tm.mcp:
            self.log.error('MCP not found')
            return
            
        ret = tm.mcp.process_command(raw_args)
        self.process_mcp_ret(raw_args, ret)