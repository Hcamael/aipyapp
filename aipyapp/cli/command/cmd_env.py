from ... import T
from .base_parser import ParserCommand
from .utils import print_records

class EnvCommand(ParserCommand):
    name = 'env'
    description = T('Environment operations')

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List environment variables'))

    def cmd_list(self, args, ctx):
        rows = ctx.tm.list_envs()
        print_records(rows)
        
    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)