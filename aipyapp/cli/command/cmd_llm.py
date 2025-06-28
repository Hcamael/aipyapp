from ... import T
from .base import BaseCommand
from .utils import print_records

class LLMCommand(BaseCommand):
    name = 'llm'
    description = T('LLM operations')

    def add_subcommands(self, subparsers):
        # Commit subcommand
        subparsers.add_parser('list', help=T('List LLM providers'))
        
        tm = self.manager.tm
        names = tm.client_manager.names       
        use_parser = subparsers.add_parser('use', help=T('Use a LLM provider'))
        use_parser.add_argument('--name', choices=names['enabled'], help='Provider name')
        
    def cmd_list(self, args):
        rows = self.manager.tm.list_llms()
        print_records(rows)
        
    def cmd_use(self, args):
        self.manager.tm.use(llm=args.name)
        self.log.info(f'Use {args.name} LLM provider')

    def cmd(self, args):
        self.cmd_list(args)