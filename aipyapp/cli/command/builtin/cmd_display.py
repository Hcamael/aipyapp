
from aipyapp import T
from ..base import ParserCommand
from .utils import row2table

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
            
        table = row2table(rows, headers=[T('Style'), T('Description')], title=T('Available Display Styles'))
        ctx.console.print(table)

    def cmd_use(self, args, ctx):
        """设置显示风格"""
        console = ctx.console
        success = ctx.tm.display_manager.set_style(args.style)
        if success:
            console.print(f"[green]{T('Display style changed to')}: {T(args.style)}[/green]")
        else:
            console.print(f"[red]{T('Invalid display style')}: {T(args.style)}[/red]")
            console.print(f"[yellow]{T('Use /display list to see available styles')}[/yellow]") 

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)