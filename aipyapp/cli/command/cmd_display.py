from rich import print
from rich.table import Table

from ... import T
from .base_parser import ParserCommand
from .utils import print_table

class DisplayCommand(ParserCommand):
    name = 'display'
    description = T('Display style operations')

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List available display styles'))
        
        # 为 set 子命令添加参数
        ctx = self.manager.context
        set_parser = subparsers.add_parser('use', help=T('Set display style'))
        set_parser.add_argument('style', choices=ctx.tm.display_manager.get_available_styles(), help='Display style to set')

    def cmd_list(self, args, ctx):
        """列出可用的显示风格"""
        styles = ctx.tm.display_manager.get_available_styles()
        info = ctx.tm.display_manager.get_plugin_info()
        
        rows = []
        for style in styles:
            description = info.get(style, '')
            rows.append([style, description])
            
        print_table(rows, headers=[T('Style'), T('Description')], title=T('Available Display Styles'))

    def cmd_use(self, args, ctx):
        """设置显示风格"""
        success = ctx.tm.display_manager.set_style(args.style)
        if success:
            print(f"[green]{T('Display style changed to')}: {args.style}[/green]")
        else:
            print(f"[red]{T('Invalid display style')}: {args.style}[/red]")
            print(f"[yellow]{T('Use /display list to see available styles')}[/yellow]") 

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)