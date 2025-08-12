import shlex
import argparse
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from ... import __pkgpath__
from .base import BaseCommand, CommandMode
from .cmd_info import InfoCommand
from .cmd_help import HelpCommand
from .cmd_llm import LLMCommand
from .cmd_role import RoleCommand
from .cmd_task import TaskCommand
from .cmd_mcp import MCPCommand
from .cmd_display import DisplayCommand
from .cmd_context import ContextCommand
from .cmd_steps import StepsCommand
from .cmd_block import BlockCommand
from .cmd_plugin import Command as PluginCommand
from .cmd_custom import CustomCommand
from .custom_command_manager import CustomCommandManager
from .result import CommandResult

from loguru import logger
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path

COMMANDS = [
    InfoCommand, LLMCommand, RoleCommand, DisplayCommand, PluginCommand, StepsCommand, 
    BlockCommand, ContextCommand, TaskCommand, MCPCommand, HelpCommand, CustomCommand,
]

@dataclass
class CommandContext:
    """命令执行上下文"""
    task: Any = None
    tm: Any = None
    console: Any = None

class CommandError(Exception):
    """Command error"""
    pass

class CommandInputError(CommandError):
    """Command input error"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class CommandArgumentError(CommandError):
    """Command argument error"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class InvalidCommandError(CommandError):
    """Invalid command error"""
    def __init__(self, command):
        self.command = command
        super().__init__(f"Invalid command: {command}")

class InvalidSubcommandError(CommandError):
    """Invalid subcommand error"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class CommandManager(Completer):
    def __init__(self, settings, tm, console):
        self.settings = settings
        self.tm = tm
        self.task = None
        self.console = console
        self.mode = CommandMode.MAIN
        self.commands_main = OrderedDict()
        self.commands_task = OrderedDict()
        self.commands = self.commands_main
        self.log = logger.bind(src="CommandManager")
        self.custom_command_manager = CustomCommandManager()
        self.custom_command_manager.add_command_dir(Path(__pkgpath__ / "commands" ))
        self.custom_command_manager.add_command_dir(Path(self.settings['config_dir']) / "commands" )
        self.init()
        
    @property
    def context(self):
        return CommandContext(task=self.task, tm=self.tm, console=self.console)
    
    def init(self):
        """Initialize all registered commands"""
        commands = []
        
        # Initialize built-in commands
        for command_class in COMMANDS:
            command = command_class(self)
            self.register_command(command)
            commands.append(command)
        
        # Initialize custom commands
        custom_commands = self.custom_command_manager.scan_commands()
        for custom_command in custom_commands:
            # Validate command name doesn't conflict
            if self.custom_command_manager.validate_command_name(
                custom_command.name, 
                list(self.commands_main.keys()) + list(self.commands_task.keys())
            ):
                custom_command.manager = self  # Set manager reference
                self.register_command(custom_command)
                commands.append(custom_command)
        
        # Initialize all commands
        for command in commands:
            command.init()
        
        built_in_count = len(COMMANDS)
        custom_count = len(custom_commands)
        self.log.info(f"Initialized {built_in_count} built-in commands and {custom_count} custom commands")

    def is_task_mode(self):
        return self.mode == CommandMode.TASK
    
    def is_main_mode(self):
        return self.mode == CommandMode.MAIN
    
    def set_task_mode(self, task):
        self.task = task
        self.mode = CommandMode.TASK
        self.commands = self.commands_task

    def set_main_mode(self):
        self.mode = CommandMode.MAIN
        self.task = None
        self.commands = self.commands_main
    
    def create_key_bindings(self):
        """创建键绑定"""
        kb = KeyBindings()
        
        @kb.add('@')  # @: 插入 @ 并补齐文件路径
        def _(event):
            """按 @ 插入符号并进入文件补齐模式"""
            buffer = event.app.current_buffer
            
            # 插入 @ 符号
            buffer.insert_text('@')
            
            # 创建文件补齐器，使用 @ 作为前缀
            file_completer = self._create_path_completer(prefix='@')
            
            # 临时切换到文件补齐器
            buffer.completer = file_completer
            
            # 触发补齐
            buffer.start_completion()
        
        @kb.add('c-f')  # Ctrl+F: 直接补齐文件路径（不插入 @）
        def _(event):
            """按 Ctrl+F 直接进入文件补齐模式（不插入 @）"""
            buffer = event.app.current_buffer
            
            # 创建文件补齐器，不使用前缀
            path_completer = self._create_path_completer(prefix=None)
            
            # 临时切换到路径补齐器
            buffer.completer = path_completer
            
            # 触发补齐
            buffer.start_completion()
            
        @kb.add('escape', eager=True)  # ESC: 恢复默认补齐模式
        def _(event):
            """按ESC恢复默认补齐模式"""
            buffer = event.app.current_buffer
            
            # 直接恢复到CommandManager作为补齐器
            buffer.completer = self
            
            # 关闭当前的补齐窗口
            if buffer.complete_state:
                buffer.cancel_completion()
            
        @kb.add('c-t')  # Ctrl+T: 插入当前时间戳
        def _(event):
            """按Ctrl+T插入当前时间戳"""
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            event.app.current_buffer.insert_text(timestamp)
        
        return kb
    
    def _create_path_completer(self, prefix=None):
        """创建通用路径补齐器
        
        Args:
            prefix: 如果设置（如 '@'），则查找该前缀后的路径；否则从光标位置开始补齐
        """
        import glob
        import os
        import shlex
        
        class PathCompleter(Completer):
            def __init__(self, prefix_char):
                self.prefix = prefix_char
            
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                
                # 根据是否有前缀确定路径起始位置
                if self.prefix:
                    # 查找前缀位置
                    prefix_pos = text.rfind(self.prefix)
                    if prefix_pos == -1:
                        return
                    path = text[prefix_pos + 1:]
                else:
                    # Ctrl+F 模式：从当前位置开始补齐
                    # 不分割文本，直接使用全部文本作为路径
                    # 这样可以处理包含空格的路径
                    path = text.strip()
                
                # 处理可能的引号（如果用户输入了引号包裹的路径）
                try:
                    if path and (path[0] in ('"', "'") or '"' in path or "'" in path):
                        # 尝试解析引号
                        parsed = shlex.split(path)
                        path = parsed[0] if parsed else path
                except ValueError:
                    # 引号不匹配，使用原始路径
                    pass
                
                # 使用 glob 匹配文件
                pattern = path + '*' if path else '*'
                matches = glob.glob(pattern)
                
                for match in matches:
                    # 跳过隐藏文件
                    if os.path.basename(match).startswith('.'):
                        continue
                    
                    # 如果文件名包含空格，使用引号包裹
                    completion_text = shlex.quote(match) if ' ' in match else match
                    
                    # 生成补齐项
                    display = match
                    if os.path.isdir(match):
                        display += '/'
                    
                    yield Completion(
                        completion_text,
                        start_position=-len(path),
                        display=display
                    )
        
        return PathCompleter(prefix)

    def register_command(self, command):
        """Register a command instance"""
        if not isinstance(command, BaseCommand):
            raise ValueError("Command must be an instance of BaseCommand")
        
        if CommandMode.MAIN in command.modes:
            self.commands_main[command.name] = command
        if CommandMode.TASK in command.modes:
            self.commands_task[command.name] = command
            
    def get_completions(self, document, complete_event):
        """获取自动补齐选项"""
        text = document.text_before_cursor
        if not text.startswith('/'):
            return

        text = text[1:]
        try:
            words = shlex.split(text)
        except ValueError as e:
            self.log.error(f"输入解析错误: {e}")
            return

        # 处理主命令补齐
        if self._should_complete_main_command(words, text):
            yield from self._complete_main_commands(words)
            return

        # 获取命令实例和参数
        command_instance, arguments, subcmd = self._get_command_and_arguments(words)
        if not command_instance:
            return

        # 处理子命令补齐
        if self._should_complete_subcommand(words, text, command_instance):
            yield from self._complete_subcommands(words, command_instance)
            return

        # 处理参数补齐
        if arguments is None:
            # 当没有参数时（如只有主命令），不进行参数补齐
            return
        
        # 简化的补齐逻辑：统一处理，不区分特殊情况
        if text.endswith(' '):
            yield from self._complete_after_space(words, arguments, command_instance, subcmd)
        else:
            yield from self._complete_partial_input(words, arguments, command_instance, subcmd)

    def _should_complete_main_command(self, words, text):
        """判断是否应该补齐主命令"""
        return len(words) == 0 or (len(words) == 1 and not text.endswith(' '))

    def _complete_main_commands(self, words):
        """补齐主命令"""
        partial_cmd = words[0] if len(words) > 0 else ''
        yield from self._complete_items(self.commands.values(), partial_cmd)

    def _should_complete_subcommand(self, words, text, command_instance):
        """判断是否应该补齐子命令"""
        return (command_instance.subcommands and 
                (len(words) == 1 or (len(words) == 2 and not text.endswith(' '))))

    def _complete_subcommands(self, words, command_instance):
        """补齐子命令"""
        partial_subcmd = words[1] if len(words) > 1 else ''
        yield from self._complete_items(command_instance.get_subcommands().values(), partial_subcmd)

    def _get_command_and_arguments(self, words):
        """获取命令实例和参数"""
        cmd = words[0]
        if cmd not in self.commands:
            return None, None, None

        command_instance = self.commands[cmd]
        subcommands = command_instance.subcommands

        if subcommands:
            if len(words) < 2:
                # 当只有主命令时，返回命令实例但不设置子命令和参数
                return command_instance, None, None
            subcmd = words[1]
            if subcmd not in subcommands:
                return None, None, None
            arguments = subcommands[subcmd]['arguments']
        else:
            subcmd = None
            arguments = command_instance.arguments

        return command_instance, arguments, subcmd

    def _complete_after_space(self, words, arguments, command_instance, subcmd):
        """处理以空格结尾的补齐"""
        # 检查选项参数
        for word in [words[-2] if len(words) > 1 else None, words[-1] if len(words) > 0 else None]:
            if word and word.startswith('-'):
                yield from self._complete_option_argument(word, arguments, command_instance, subcmd, start_position=0)
                return

        # 检查位置参数
        for arg_name, arg in arguments.items():
            if not arg_name.startswith('-') and arg['requires_value']:
                choices = command_instance.get_arg_values(arg, subcmd, '')
                if choices:
                    yield from self._complete_items(choices, '')
                    return

        # 显示所有可用参数
        yield from self._complete_items(arguments.values(), '')

    def _complete_partial_input(self, words, arguments, command_instance, subcmd):
        """处理部分输入的补齐"""
        partial_arg = words[-1]
        last_word = words[-2] if len(words) > 1 else None

        # 检查当前输入是否是选项参数
        if partial_arg.startswith('-'):
            yield from self._complete_option_argument(partial_arg, arguments, command_instance, subcmd, 
                                                     start_position=-len(partial_arg))
            return

        # 检查上一个词是否是选项参数
        if last_word and last_word.startswith('-'):
            arg = arguments.get(last_word, None)
            if arg and arg['requires_value']:
                choices = command_instance.get_arg_values(arg, subcmd, partial_arg)
                if choices:
                    yield from self._complete_items(choices, partial_arg)
                return

        # 检查是否是位置参数的输入
        for arg_name, arg in arguments.items():
            if not arg_name.startswith('-') and arg['requires_value']:
                choices = command_instance.get_arg_values(arg, subcmd, partial_arg)
                if choices:
                    yield from self._complete_items(choices, partial_arg)
                    return
        
        # 显示所有可用参数
        yield from self._complete_items(arguments.values(), partial_arg)

    def _complete_option_argument(self, option_name, arguments, command_instance, subcmd, start_position):
        """补齐选项参数"""
        arg = arguments.get(option_name, None)
        if not arg or not arg.get('requires_value'):
            return

        # 尝试通过 get_arg_values 获取选项
        choices = command_instance.get_arg_values(arg, subcmd, '')
        if choices:
            yield from self._complete_items(choices, '')
            return

        # 尝试使用 arg 的 choices
        if 'choices' in arg and arg['choices']:
            choice_names = list(arg['choices'].keys())
            for choice_name in choice_names:
                yield Completion(choice_name, start_position=start_position, 
                               display_meta=f"Option: {choice_name}")

    def _complete_items(self, items, partial, start_pos=None):
        """通用的补齐函数"""
        start_pos = -len(partial) if start_pos is None else start_pos
        for item in items:
            if item.name.startswith(partial):
                yield Completion(
                    item.name,
                    start_position=start_pos,
                    display_meta=item.desc
                )

    def execute(self, user_input: str) -> dict[str, Any]:
        """Execute a command"""
        if not user_input.startswith('/'):
            raise CommandInputError(user_input)
        
        user_input = user_input[1:].strip()
        if not user_input:
            raise CommandInputError(user_input)
        
        args = shlex.split(user_input)
        command = args[0]
        if command not in self.commands:
            raise InvalidCommandError(command)
        
        command_instance = self.commands[command]
        parser = command_instance.parser
        ret = None
        try:
            # Parse remaining arguments (excluding the command name)
            parsed_args = parser.parse_args(args[1:])
            parsed_args.raw_args = args[1:]
            ret = command_instance.execute(parsed_args)
        except SystemExit as e:
            raise CommandError(f"SystemExit: {e}")
        except argparse.ArgumentError as e:
            raise CommandArgumentError(f"ArgumentError: {e}") from e
        except Exception as e:
            raise CommandError(f"Error: {e}") from e
        
        return CommandResult(command=command, subcommand=getattr(parsed_args, 'subcommand', None), args=vars(parsed_args), result=ret)
    
    def reload_custom_commands(self):
        """Reload all custom commands"""
        # Remove existing custom commands
        custom_command_names = []
        for name, command in list(self.commands_main.items()):
            if hasattr(command, 'file_path'):  # It's a custom command
                custom_command_names.append(name)
                del self.commands_main[name]
        
        for name, command in list(self.commands_task.items()):
            if hasattr(command, 'file_path'):  # It's a custom command
                custom_command_names.append(name)
                del self.commands_task[name]
        
        # Reload custom commands
        custom_commands = self.custom_command_manager.reload_commands()
        for custom_command in custom_commands:
            if self.custom_command_manager.validate_command_name(
                custom_command.name,
                list(self.commands_main.keys()) + list(self.commands_task.keys())
            ):
                custom_command.manager = self
                self.register_command(custom_command)
                custom_command.init()
        
        self.log.info(f"Reloaded {len(custom_commands)} custom commands")
        return len(custom_commands)