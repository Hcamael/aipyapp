from ... import T
from .base import CommandMode, Completable
from .base_parser import ParserCommand
from .utils import print_records

class RoleCommand(ParserCommand):
    name = 'role'
    description = T('Role operations')

    def add_subcommands(self, subparsers):
        # List subcommand
        subparsers.add_parser('list', help=T('List available roles'))
        
        # Show subcommand
        show_parser = subparsers.add_parser('show', help=T('Show role details'))
        show_parser.add_argument('role', type=str, help=T('Role name'))
        
        # Use subcommand
        use_parser = subparsers.add_parser('use', help=T('Use a role'))
        use_parser.add_argument('role', type=str, help=T('Role name'))

    def get_arg_values(self, arg, subcommand=None):
        if subcommand in ['show', 'use'] and arg.name == 'role':
            ctx = self.manager.context
            return [Completable(name, role.short) for name, role in ctx.tm.role_manager.roles.items()]
        return super().get_arg_values(arg, subcommand)
            
    def cmd_list(self, args, ctx):
        rows = ctx.tm.list_roles()
        print_records(rows)
        
    def cmd_show(self, args, ctx):
        role_name = args.role.lower()
        role = ctx.tm.role_manager.roles.get(role_name)
        if not role:
            self.log.error(T('Role not found').format(args.role))
            return
        
        from rich.table import Table
        from rich import print
        
        # 基本信息表格
        basic_table = Table(title=f"{T('Role Information')}: {role.name}", show_lines=True)
        basic_table.add_column(T('Property'), style="bold cyan", justify="right")
        basic_table.add_column(T('Value'), style="bold white", justify="left")
        
        basic_table.add_row(T('Role name'), role.name)
        basic_table.add_row(T('Role description'), role.short)
        basic_table.add_row(T('Tips count'), str(len(role.tips)))
        basic_table.add_row(T('Environment variables count'), str(len(role.envs)))
        basic_table.add_row(T('Package dependencies count'), str(len(role.packages)))
        basic_table.add_row(T('Plugins count'), str(len(role.plugins)))
        
        print(basic_table)
        
        # 详细描述
        if role.detail:
            from rich.panel import Panel
            detail_panel = Panel(role.detail, title=T('Role detail'), border_style="blue")
            print(detail_panel)
        
        # 提示信息表格
        if role.tips:
            tips_table = Table(title=T('Tips'), show_lines=True)
            tips_table.add_column(T('Name'), style="bold green", justify="left")
            tips_table.add_column(T('Description'), style="bold white", justify="left")
            
            for tip_name, tip in role.tips.items():
                tips_table.add_row(tip_name, tip.short)
            
            print(tips_table)
        
        # 环境变量表格
        if role.envs:
            env_table = Table(title=T('Environment variables'), show_lines=True)
            env_table.add_column(T('Name'), style="bold yellow", justify="left")
            env_table.add_column(T('Description'), style="bold white", justify="left")
            env_table.add_column(T('Value'), style="dim", justify="left")
            
            for env_name, (value, desc) in role.envs.items():
                # 截断过长的值
                display_value = value[:50] + "..." if len(value) > 50 else value
                env_table.add_row(env_name, desc, display_value)
            
            print(env_table)
        
        # 包依赖表格
        if role.packages:
            pkg_table = Table(title=T('Package dependencies'), show_lines=True)
            pkg_table.add_column(T('Language'), style="bold magenta", justify="left")
            pkg_table.add_column(T('Packages'), style="bold white", justify="left")
            
            for lang, packages in role.packages.items():
                pkg_table.add_row(lang, ', '.join(packages))
            
            print(pkg_table)
        
    def cmd_use(self, args, ctx):
        success = ctx.tm.use(role=args.role)
        if success:
            self.log.info(f'Use {args.role} role')
        else:
            self.log.error(T('Failed to use role').format(args.role))

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx) 