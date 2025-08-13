from aipyapp import T
from ..base import CommandMode, ParserCommand
from .utils import row2table

class PluginCommand(ParserCommand):
    name = 'plugin'
    description = T('Plugin operations')
    modes = [CommandMode.MAIN, CommandMode.TASK]

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List available plugins'))
        
        parser = subparsers.add_parser('show', help=T('Show plugin details'))
        parser.add_argument('name', type=str, help=T('Plugin name'))

    def has_subcommand(self, name: str):
        if name == 'show' and self.manager.context.is_main_mode():
            return False
        return True

    def get_arg_values(self, name, subcommand=None):
        if name == 'name':
            ctx = self.manager.context
            return [(plugin.name, plugin.description) for plugin in ctx.tm.plugin_manager]
        return None

    def cmd_list(self, args, ctx):
        """列出可用的插件"""
        rows = []
        for plugin in ctx.tm.plugin_manager:
            rows.append([plugin.name, plugin.description, plugin.get_type().name, plugin.version, plugin.author])
        table = row2table(rows, headers=[T('Name'), T('Description'), T('Type'), T('Version'), T('Author')], title=T('Available Plugins'))
        ctx.console.print(table)

    def _get_first_line(self, doc: str) -> str:
        """Get the first non-empty line of the docstring"""
        return next((line for line in doc.split('\n') if line.strip()), '')
    
    def cmd_show(self, args, ctx):
        """显示插件详情"""
        task = ctx.task
        if not task:
            ctx.console.print(T('Task mode only'), style='yellow')
            return
        plugin = task.plugins.get(args.name)
        if not plugin:
            ctx.console.print(f"[red]{T('Plugin not found')}: {args.name}[/red]")
            return
        
        rows = []
        for name, func in plugin.get_handlers().items():    
            rows.append([T('Event'), name, self._get_first_line(func.__doc__)])
        for name, func in plugin.get_functions().items():
            rows.append([T('Function'), name, self._get_first_line(func.__doc__)])
        table = row2table(rows, headers=[T('Type'), T('Name'), T('Description')], title=T('Plugin Details'))
        ctx.console.print(table)

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)