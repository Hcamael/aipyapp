from ... import T
from .base_parser import ParserCommand

class UseCommand(ParserCommand):
    name = 'use'
    description = T('Use a LLM or a role')

    def add_arguments(self, parser):
        tm = self.manager.tm
        names = tm.client_manager.names
        roles = {role.name: role.short for role in tm.role_manager.roles.values()}
        parser.add_argument('--llm', choices=names['enabled'], help=T('LLM name'))
        parser.add_argument('--role', choices=roles.keys(), help=T('Role name'))
        parser.add_argument('name', choices=names['enabled'], nargs='?', help=T('LLM name'))

    def execute(self, args, context=None):
        tm = self.manager.tm

        params = {}
        if args.llm:
            params['llm'] = args.llm
        if args.role:
            params['role'] = args.role
        if args.name:
            params['llm'] = args.name
        if not params:
            self.parser.print_help()
            return
        rets = tm.use(**params)
        for name, ret in rets.items():
            self.console.print(f"{name}: {'[green]Ok[/green]' if ret else '[red]Error[/red]'}")