from ... import T
from .base import BaseCommand
from .utils import print_records

class EnvCommand(BaseCommand):
    name = 'env'
    description = T('Environment operations')

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help=T('List environment variables'))

    def cmd_list(self, args):
        rows = self.manager.tm.list_envs()
        print_records(rows)
        
    def cmd(self, args):
        self.cmd_list(args)