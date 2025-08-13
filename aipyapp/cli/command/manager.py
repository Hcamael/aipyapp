"""重构后的命令管理器 - 职责分离"""

import shlex
import argparse
from collections import OrderedDict
from typing import Dict, Optional, Any, List
from prompt_toolkit.completion import Completer, Completion
from loguru import logger

from .common import CommandContext, CommandMode, CommandManagerConfig, CommandError, CommandResult
from .base import Command
from .completer import CompleterBase, CompleterContext
from .custom.manager import CustomCommandManager
from .builtin import BUILTIN_COMMANDS
from .keybindings import create_key_bindings

class CommandRegistry:
    """
    命令注册表
    
    负责命令的注册和查找
    """
    
    def __init__(self):
        self._commands: OrderedDict[str, Command] = OrderedDict()
        self.aliases: Dict[str, str] = {}  # 别名 -> 命令名
        self.commands_by_mode: Dict[CommandMode, List[Command]] = {
            CommandMode.MAIN: [],
            CommandMode.TASK: []
        }
    
    @property
    def commands(self) -> OrderedDict[str, Command]:
        """获取所有命令"""
        return self._commands
    
    def register(self, command: Command):
        """注册命令"""
        # 注册主名称
        self._commands[command.name] = command
        
        # 注册别名
        if hasattr(command, 'aliases'):
            for alias in command.aliases:
                self.aliases[alias] = command.name
        
        # 按模式分类
        for mode in command.modes:
            self.commands_by_mode[mode].append(command)
    
    def unregister(self, name: str):
        """注销命令"""
        if name in self._commands:
            command = self._commands[name]
            del self._commands[name]
            
            # 移除别名
            for alias, cmd_name in list(self.aliases.items()):
                if cmd_name == name:
                    del self.aliases[alias]
            
            # 从模式列表中移除
            for mode in command.modes:
                if command in self.commands_by_mode[mode]:
                    self.commands_by_mode[mode].remove(command)
    
    def get(self, name: str) -> Optional[Command]:
        """获取命令"""
        # 先检查直接名称
        if name in self._commands:
            return self._commands[name]
        
        # 再检查别名
        if name in self.aliases:
            return self._commands.get(self.aliases[name])
        
        return None
    
    def get_commands_by_mode(self, mode: CommandMode) -> List[Command]:
        """获取特定模式的命令"""
        return self.commands_by_mode.get(mode, [])
    
class CommandExecutor:
    """
    命令执行器
    
    负责解析和执行命令
    """
    
    def __init__(self, registry: CommandRegistry):
        self.registry = registry
        self.log = logger.bind(src="CommandExecutor")
    
    def execute(self, text: str, context: CommandContext) -> Any:
        """
        执行命令
        
        Args:
            text: 命令文本（带 / 前缀）
            context: 执行上下文
            
        Returns:
            命令执行结果
        """
        # 验证命令格式
        if not text.startswith('/'):
            raise ValueError(f"Invalid command format: {text}")
        
        # 解析命令
        text = text[1:].strip()
        if not text:
            raise ValueError("Empty command")
        
        # 分割命令和参数
        try:
            words = shlex.split(text)
        except ValueError as e:
            raise ValueError(f"Failed to parse command: {e}")
        
        if not words:
            raise ValueError("No command specified")
        
        cmd_name = words[0]
        cmd_args = words[1:]
        
        # 查找命令
        command = self.registry.get(cmd_name)
        if not command:
            raise CommandError(f"Unknown command: {cmd_name}")
        
        # 检查命令是否支持当前模式
        if context.mode not in command.modes:
            raise CommandError(f"Command '{cmd_name}' not available in {context.mode.value} mode")
        
        # 解析参数
        try:
            parsed_args = command.parser.parse_args(cmd_args)
        except SystemExit:
            # argparse 尝试退出，转换为异常
            raise CommandError(f"Invalid arguments for command '{cmd_name}'")
        except argparse.ArgumentError as e:
            raise CommandError(f"Invalid arguments: {e}")
        except Exception as e:
            raise CommandError(f"Failed to parse arguments: {e}")
        
        # 验证参数
        if hasattr(command, 'validate_args'):
            error = command.validate_args(parsed_args)
            if error:
                raise CommandError(f"Invalid arguments: {error}")
        
        # 执行命令
        try:
            result = command.execute(parsed_args, context)
            return CommandResult(command=command.name, subcommand=getattr(parsed_args, 'subcommand', None), args=vars(parsed_args), result=result)
        except Exception as e:
            self.log.error(f"Command execution failed: {e}")
            raise CommandError(f"Command execution failed: {e}")


class CommandCompleter(CompleterBase):
    """
    命令级别的补齐器
    
    负责路由补齐请求到具体命令的补齐器
    """
    
    def __init__(self, registry: CommandRegistry, context_provider: CommandContext):
        self.registry = registry
        self.context_provider = context_provider  # 用于获取当前执行上下文
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """获取补齐建议"""
        text = context.word_before_cursor
        
        # 解析命令名
        try:
            words = shlex.split(text)
        except ValueError:
            # 引号不匹配等情况，尝试简单分割
            words = text.split()
        
        if not words:
            # 补齐所有命令名
            return self._complete_command_names("", context)
        
        cmd_name = words[0]
        
        # 如果还在输入命令名
        if len(words) == 1 and not context.is_empty_position:
            return self._complete_command_names(cmd_name, context)
        
        # 查找命令
        command = self.registry.get(cmd_name)
        if not command:
            return []
        
        # 获取命令的补齐器
        completer = command.completer
        
        # 创建命令参数的上下文（去掉命令名）
        remaining_text = text[len(cmd_name):].lstrip()
        arg_context = CompleterContext(
            text=remaining_text,
            cursor_pos=len(remaining_text),
            words=words[1:],
            current_word=words[-1] if len(words) > 1 and not context.is_empty_position else "",
            word_before_cursor=remaining_text
        )
        
        return completer.get_completions(arg_context)
    
    def _complete_command_names(self, partial: str, context: CompleterContext) -> List[Completion]:
        """补齐命令名"""
        completions = []
        
        # 获取当前模式
        current_mode = self.context_provider.mode
        
        # 获取当前模式的命令
        commands = self.registry.get_commands_by_mode(current_mode)
        for command in commands:
            if command.name.startswith(partial):
                completions.append(Completion(
                    command.name,
                    start_position=-len(partial) if partial else 0,
                    display=command.name,
                    display_meta=command.description
                ))
        
        return completions


class CommandManager(Completer):
    """
    重构后的命令管理器
    
    职责：
    1. 作为顶层接口，协调各组件
    2. 管理命令注册表
    3. 提供执行入口
    4. 作为 prompt_toolkit 的 Completer
    
    不负责：
    - 具体的补齐逻辑（委托给 CommandCompleter）
    - 具体的执行逻辑（委托给 CommandExecutor）
    - 命令的实现（由 Command 子类负责）
    """

    def __init__(self, config: CommandManagerConfig, context: CommandContext):
        """
        初始化命令管理器
        
        Args:
            config: 静态配置
            runtime_context: 运行时上下文
        """
        self.config = config
        self.context = context   
        self.registry = CommandRegistry()
        self.executor = CommandExecutor(self.registry)
        self.completer = CommandCompleter(self.registry, self.context)  # 传递 context 以获取当前模式
        self.log = logger.bind(src="CommandManager")

        # 自定义命令管理器
        self.custom_command_manager = self._create_custom_command_manager()
        
        # 初始化命令
        self._init_commands()

        # 创建键绑定
        self.key_bindings = create_key_bindings(self)
    
    @property
    def commands(self) -> OrderedDict[str, Command]:
        """获取所有命令"""
        return self.registry.commands
    
    def _create_custom_command_manager(self) -> CustomCommandManager:
        """创建自定义命令管理器"""
        manager = CustomCommandManager()
        
        # 内置命令目录
        if self.config.builtin_command_dir:
            self.log.info(f"Adding builtin command directory: {self.config.builtin_command_dir}")
            manager.add_command_dir(self.config.builtin_command_dir)
        
        # 添加自定义命令目录
        for cmd_dir in self.config.custom_command_dirs:
            if cmd_dir.exists():
                self.log.info(f"Adding custom command directory: {cmd_dir}")
                manager.add_command_dir(cmd_dir)
        
        return manager
        
    def register_command(self, command: Command):
        """注册命令"""
        self.registry.register(command)
        self.log.info(f"Registered command: {command.name}")
    
    def unregister_command(self, name: str):
        """注销命令"""
        self.registry.unregister(name)
        self.log.info(f"Unregistered command: {name}")

    def _init_commands(self):
        """初始化所有命令"""
        commands = []
        # 初始化内置命令
        for command_class in BUILTIN_COMMANDS:
            command = command_class()
            self.register_command(command)
            commands.append(command)
        
        # 初始化自定义命令
        custom_commands = self.custom_command_manager.scan_commands()
        for custom_command in custom_commands:
            # 验证命令名不冲突
            all_names = list(self.registry.commands.keys())
            if self.custom_command_manager.validate_command_name(
                custom_command.name, 
                all_names
            ):
                custom_command.manager = self  # 设置管理器引用
                self.register_command(custom_command)
                commands.append(custom_command)
        
        # 初始化所有命令
        for command in commands:
            if hasattr(command, 'init'):
                command.init(self)
        
        self.log.info(
            f"Initialized {len(BUILTIN_COMMANDS)} built-in commands "
            f"and {len(custom_commands)} custom commands"
        )

    def execute(self, text: str) -> Any:
        """
        执行命令
        
        Args:
            text: 命令文本（带 / 前缀）
            
        Returns:
            命令执行结果
        """
        return self.executor.execute(text, self.context)
    
    def get_completions(self, document, complete_event):
        """
        prompt_toolkit Completer 接口
        
        将补齐请求路由到命令补齐器
        """
        text = document.text_before_cursor
        
        # 只处理以 / 开头的命令
        if not text.startswith('/'):
            return
        
        # 去掉 / 前缀
        text = text[1:]
        
        # 创建补齐上下文
        try:
            words = shlex.split(text)
        except ValueError:
            words = text.split()
        
        current_word = ""
        if words and not text.endswith(' '):
            current_word = words[-1]
        
        context = CompleterContext(
            text=text,
            cursor_pos=len(text),
            words=words,
            current_word=current_word,
            word_before_cursor=text
        )
        
        # 获取补齐建议
        completions = self.completer.get_completions(context)
        
        # 转换为 prompt_toolkit 的 Completion
        for completion in completions:
            yield completion
    