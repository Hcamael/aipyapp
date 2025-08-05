import argparse
from collections import OrderedDict
from typing import List

from .base import BaseCommand, Completable

def requires_value(action):
    ret = (
        action.nargs is not None or
        (action.type is not None and action.type != bool) or
        action.choices is not None
    )
    return ret

class ParserCommand(BaseCommand):
    """Base class for all commands"""
    def __init__(self, manager):
        super().__init__(manager)
        self.parser = None
        self.arguments = None
        self.subcommands = None

    def init(self):
        """Initialize the command, can be overridden by subclasses"""
        parser = argparse.ArgumentParser(prog=f'/{self.name}', description=self.description)
        self.add_arguments(parser)
        if hasattr(self, 'add_subcommands'):
            subparsers = parser.add_subparsers(dest='subcommand')
            self.add_subcommands(subparsers)

        arguments = OrderedDict()
        for action in parser._actions:
            # 处理选项参数（如 --option）
            for option in action.option_strings:
                if option in ('-h', '--help'):
                    continue

                choices = OrderedDict()
                if action.choices:
                    for choice in action.choices:
                        choices[choice] = Completable(choice)
                arguments[option] = Completable(option, action.help, choices=choices, requires_value=requires_value(action))
            
            # 处理位置参数（如 'name'）
            if not action.option_strings and action.dest != 'help' and action.dest != 'subcommand':
                choices = OrderedDict()
                if action.choices:
                    for choice in action.choices:
                        choices[choice] = Completable(choice)
                # 对于位置参数，不将参数名作为自动补齐的一部分，直接使用选项值
                if action.choices:
                    for choice in action.choices:
                        arguments[choice] = Completable(choice, action.help, requires_value=False)
                else:
                    arguments[action.dest] = Completable(action.dest, action.help, choices=choices, requires_value=requires_value(action))

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
                    # 处理子命令的选项参数
                    for option in sub_action.option_strings:
                        if option in ('-h', '--help'):
                            continue

                        choices = OrderedDict()
                        if sub_action.choices:
                            for choice in sub_action.choices:
                                choices[choice] = Completable(choice)

                        sub_arguments[option] = Completable(option, sub_action.help, choices=choices, requires_value=requires_value(sub_action))
                    
                    # 处理子命令的位置参数
                    if not sub_action.option_strings and sub_action.dest != 'help':
                        choices = OrderedDict()
                        if sub_action.choices:
                            for choice in sub_action.choices:
                                choices[choice] = Completable(choice)
                        # 对于位置参数，不将参数名作为自动补齐的一部分，直接使用选项值
                        if sub_action.choices:
                            for choice in sub_action.choices:
                                sub_arguments[choice] = Completable(choice, sub_action.help, requires_value=False)
                        else:
                            sub_arguments[sub_action.dest] = Completable(sub_action.dest, sub_action.help, choices=choices, requires_value=requires_value(sub_action))
                
                # 将 arguments 作为属性添加到 Completable 对象中
                if subcmd in subcommands:
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

        return func(args, ctx=self.manager.context)

    def cmd(self, args, ctx):
        """Execute the main command"""
        pass
