import sys

from ... import T
from .base_parser import ParserCommand
from .utils import print_table

class InfoCommand(ParserCommand):
    name = 'info'
    description = T('System information')

    def execute(self, args):
        ctx = self.manager.context
        tm = ctx.tm
        settings = tm.settings
        status = tm.get_status()

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

        print_table(info, title=T("System information"), headers=[T("Parameter"), T("Value")])
