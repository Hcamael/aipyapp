from ... import T
from .base import BaseCommand

class UseCommand(BaseCommand):
    name = 'use'
    description = T('Use a LLM or a role')

    def add_arguments(self, parser):
        tm = self.manager.tm
        names = tm.client_manager.names
        roles = {tips.name: tips.role.short for tips in tm.tips_manager.tips.values()}
        parser.add_argument('--llm', choices=names['enabled'], help=T('LLM name'))
        parser.add_argument('--role', choices=roles.keys(), help=T('Role name'))
        parser.add_argument('name', choices=names['enabled'], nargs='?', help=T('LLM name'))

    def execute(self, args):
        tm = self.manager.tm

        params = {}
        if args.llm:
            params['llm'] = args.llm
        if args.role:
            params['role'] = args.role
        if args.name:
            params['llm'] = args.name
        if params:
            tm.use(**params)
        else:
            self.parser.print_help()