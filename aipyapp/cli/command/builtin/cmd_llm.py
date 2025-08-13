from aipyapp import T
from ..base import CommandMode, ParserCommand
from .utils import record2table

class LLMCommand(ParserCommand):
    name = 'llm'
    description = T('LLM operations')
    modes = [CommandMode.MAIN, CommandMode.TASK]

    def add_subcommands(self, subparsers):
        use_parser = subparsers.add_parser('use', help=T('Use a LLM provider'))
        use_parser.add_argument('provider', type=str, help=T('Provider name'))
        subparsers.add_parser('list', help=T('List LLM providers'))

    def get_arg_values(self, name, subcommand=None):
        if name == 'provider':
            ctx = self.manager.context
            return [(client.name, str(client)) for client in ctx.tm.client_manager.clients.values()]
        return None
            
    def cmd_list(self, args, ctx):
        rows = ctx.tm.list_llms()
        table = record2table(rows)
        ctx.console.print(table)
        
    def cmd_use(self, args, ctx):
        if ctx.task:
            ret = ctx.task.use(args.provider)
        else:
            ret = ctx.tm.use(llm=args.provider)
        ctx.console.print(T('Success') if ret else T('Failed'), style='cyan' if ret else 'red')
        if ret:
            self.log.info(f'Use {args.provider} LLM provider')
        return ret

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)