from enum import Enum
from typing import List

from loguru import logger

class CommandMode(Enum):
    MAIN = "main"
    TASK = "task"

class Completable:
    def __init__(self, name: str, desc=None, **kwargs):
        super().__init__()
        self.name = name
        self.desc = desc
        self._options = kwargs

    def __getitem__(self, key):
        return self._options[key]

    def __setitem__(self, key, value):
        self._options[key] = value

    def __contains__(self, key):
        return key in self._options

    def get(self, key, default=None):
        return self._options.get(key, default)
    
class BaseCommand(Completable):
    """Base class for all commands"""
    name: str = ''
    description: str = ''
    modes: List[CommandMode] = [CommandMode.MAIN]

    def __init__(self, manager):
        super().__init__(self.name, self.description)
        self.manager = manager
        self.log = logger.bind(src=f'cmd.{self.name}')

    def execute(self, args, context=None):
        pass
