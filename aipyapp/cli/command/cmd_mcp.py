from rich import print

from ... import T
from .base_parser import ParserCommand
from .utils import print_table

class MCPCommand(ParserCommand):
    name = 'mcp'
    description = T('MCP operations')

    def add_subcommands(self, subparsers):
        # 服务器管理子命令
        server_parser = subparsers.add_parser('server', help=T('MCP server operations'))
        server_group = server_parser.add_mutually_exclusive_group()
        server_group.add_argument('--list', action='store_true', help=T('List MCP servers'))
        server_group.add_argument('--enable', nargs='?', const='__MISSING__',help=T('Enable MCP server'))
        server_group.add_argument('--disable', nargs='?', const='__MISSING__', help=T('Disable MCP server'))
        
        # 工具管理子命令
        tools_parser = subparsers.add_parser('tools', help=T('Internal tools operations'))
        tools_group = tools_parser.add_mutually_exclusive_group()
        tools_group.add_argument('--list', action='store_true', help=T('List available tools'))
        tools_group.add_argument('--enable', action='store_true', help=T('Enable tools'))
        tools_group.add_argument('--disable', action='store_true', help=T('Disable tools'))

    def cmd_server(self, args, ctx):
        server_args = []
        if args.enable:
            server_args.append('enable')
            if args.enable != '__MISSING__':
                server_args.append(args.enable)
        elif args.disable:
            server_args.append('disable')
            if args.disable != '__MISSING__':
                server_args.append(args.disable)
        else:
            server_args.append('list')
        ret = ctx.tm.mcp.process_command(server_args)
        self.process_mcp_ret(server_args, ret)

    def cmd_tools(self, args, ctx):
        cmd = 'list'
        if args.enable:
            cmd = 'enable'
        elif args.disable:
            cmd = 'disable'
        ret = ctx.tm.mcp.process_tool_cmd([cmd])
        self.process_tools_ret([cmd], ret)

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

    def process_tools_ret(self, args, ret):
        """处理 tools 命令的返回结果并格式化显示"""
        if not isinstance(ret, dict):
            print(f"[red]{T('Invalid response format')}[/red]")
            return
            
        action = args[0] if args else "list"
        
        # 显示操作结果
        if action == "enable":
            print(
                f"[green]{T('Internal tools have been enabled')}[/green]"
            )
        elif action == "disable" or not ret:
            msg = T('Internal tools have been disabled, use "/mcp tools --enable" to enable')
            print(f"[yellow]{msg}[/yellow]")
        
        # 如果返回的是错误信息
        if ret.get("status") == "error":
            print(f"[red]{T('Error')}: {ret.get('message', 'Unknown error')}[/red]")
            return
        
        # 显示服务器状态表格
        table_data = []

        for server_name, info in ret.items():
            status = T('Enabled') if info.get("enabled", False) else T('Disabled')
            tools_count = info.get("tools_count", 0)
            table_data.append([server_name, status, tools_count])

        if table_data:
            headers = [T('Tool Group Name'), T('Status'), T('Tools Count')]
            print_table(
                table_data,
                title=T("Internal Tools"),
                headers=headers
            )
