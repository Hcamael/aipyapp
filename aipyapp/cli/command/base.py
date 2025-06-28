import argparse
from collections import OrderedDict

from loguru import logger

def requires_value(action):
    ret = (
        action.nargs is not None or
        (action.type is not None and action.type != bool) or
        action.choices is not None
    )
    return ret

class Completable:
    def __init__(self, name: str, desc=None, **kwargs):
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

    def __init__(self):
        super().__init__(self.name, self.description)
        self.parser = None
        self.manager = None
        self.arguments = None
        self.subcommands = None
        self.log = logger.bind(src=f'cmd.{self.name}')

    def init(self):
        """Initialize the command, can be overridden by subclasses"""
        parser = argparse.ArgumentParser(prog=f'/{self.name}', description=self.description)
        self.add_arguments(parser)
        if hasattr(self, 'add_subcommands'):
            subparsers = parser.add_subparsers(dest='subcommand')
            self.add_subcommands(subparsers)

        arguments = OrderedDict()
        for action in parser._actions:
            for option in action.option_strings:
                if option in ('-h', '--help'):
                    continue

                choices = OrderedDict()
                if action.choices:
                    for choice in action.choices:
                        choices[choice] = Completable(choice)
                arguments[option] = Completable(option, action.help, choices=choices, requires_value=requires_value(action))

        subcommands = OrderedDict()
        for action in parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue

            for subaction in action._get_subactions():
                cmd_name = subaction.dest or subaction.name
                subcommands[cmd_name] = Completable(cmd_name, subaction.help)
            
            for subcmd, subparser in action.choices.items():
                sub_arguments = OrderedDict()
                for sub_action in subparser._actions:
                    for option in sub_action.option_strings:
                        if option in ('-h', '--help'):
                            continue

                        choices = OrderedDict()
                        if sub_action.choices:
                            for choice in sub_action.choices:
                                choices[choice] = Completable(choice)

                        sub_arguments[option] = Completable(option, sub_action.help, choices=choices, requires_value=requires_value(sub_action))
                subcommands[subcmd]['arguments'] = sub_arguments

        self.parser = parser
        self.arguments = arguments
        self.subcommands = subcommands

    def add_arguments(self, parser):
        """Add command-specific arguments to the parser"""
        pass
    
    def get_arg_values(self, arg, subcommand=None):
        """Get argument values for argument `arg`"""
        choices = arg.get('choices')
        if choices:
            return choices.values()
        return None
    
    def execute(self, args):
        """Execute the command with parsed arguments"""
        subcommand = getattr(args, 'subcommand', None)
        if subcommand:
            func = getattr(self, f'cmd_{subcommand}', None)
            if not func:
                self.log.error(f"Subcommand {subcommand} not found")
                return
        else:
            func = self.cmd

        return func(args)

    def cmd(self, args):
        """Execute the main command"""
        pass
