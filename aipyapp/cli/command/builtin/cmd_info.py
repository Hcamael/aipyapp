import sys

from aipyapp import T
from ..base import ParserCommand
from .utils import row2table

class InfoCommand(ParserCommand):
    name = 'info'
    description = T('System information')

    def execute(self, args, ctx):
        settings = ctx.settings
        status = ctx.tm.get_status()

        info = [
            (T('Current configuration directory'), str(settings.config_dir)),
            (T('Current working directory'), status['workdir']),
            (T('Current LLM'), status['client']),
            (T('Current role'), status['role']),
            (T('Current display style'), T(status['display'])),
            ('Python', sys.executable),
            (T('Python version'), sys.version),
            (T('Python base prefix'), sys.base_prefix),
        ]

        table = row2table(info, title=T("System information"), headers=[T("Parameter"), T("Value")])
        ctx.console.print(table)
