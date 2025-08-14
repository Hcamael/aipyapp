"""重构后的命令基类 - 职责分离（简化版）"""

from abc import ABC, abstractmethod
from typing import Optional, Any, List
import argparse

from loguru import logger

from .completer import CompleterBase, ArgparseCompleter
from .common import CommandMode

class Command(ABC):
    """
    命令基类
    """
    def __init__(self, name: str, description: str = "", modes: List[CommandMode] = [CommandMode.MAIN]):
        self.name = name
        self.description = description
        self.modes = modes or [CommandMode.MAIN]
        self.builtin = True
        self._completer: Optional[CompleterBase] = None

    def init(self):
        """Initialize the command, can be overridden by subclasses"""
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace, context: Any) -> Any:
        """Execute the command with parsed arguments"""
        pass

    @property
    def completer(self) -> CompleterBase:
        """Get the completer for the command"""
        if self._completer is None:
            self._completer = self._create_completer()
        return self._completer

    @abstractmethod
    def _create_completer(self) -> CompleterBase:
        """Create the completer for the command"""
        pass

class ParserCommand(Command):
    """
    重构后的命令基类（简化版）
    
    职责：
    1. 定义命令元信息
    2. 创建和管理 ArgumentParser
    3. 执行命令逻辑
    
    不负责：
    - 自动补齐（委托给 Completer）
    - 参数解析细节（委托给 ArgumentParser）
    """
    name: str = ''
    description: str = ''
    modes: List[CommandMode] = [CommandMode.MAIN]
    
    def __init__(self):
        """
        初始化命令
        
        Args:
            manager: 命令管理器
        """
        super().__init__(self.name, self.description, self.modes)
        self.manager = None
        self.log = logger.bind(src=f'cmd.{self.name}')
        self._parser: Optional[argparse.ArgumentParser] = None
    
    @property
    def parser(self) -> argparse.ArgumentParser:
        """Get the parser for the command"""
        if self._parser is None:
            self.init()
        return self._parser
    
    def init(self, manager: 'CommandManager'):
        """Initialize the command, can be overridden by subclasses"""
        self.manager = manager
        parser = argparse.ArgumentParser(prog=f'/{self.name}', description=self.description, exit_on_error=False)
        self.add_arguments(parser)
        if hasattr(self, 'add_subcommands'):
            subparsers = parser.add_subparsers(dest='subcommand')
            self.add_subcommands(subparsers)
        self._parser = parser
    
    def add_arguments(self, parser):
        """Add command-specific arguments to the parser"""
        pass
    
    def execute(self, args: argparse.Namespace, context: Any) -> Any:
        """
        执行命令
        
        Args:
            args: 解析后的参数
            context: 执行上下文
            
        Returns:
            命令执行结果
        """
        subcommand = getattr(args, 'subcommand', None)
        if subcommand:
            func = getattr(self, f'cmd_{subcommand}', None)
            if not func:
                self.log.error(f"Subcommand {subcommand} not found")
                return
        else:
            func = self.cmd

        return func(args, ctx=self.manager.context)
    
    def _create_completer(self) -> CompleterBase:
        """
        创建补齐器
        
        子类可以覆盖此方法以提供自定义补齐器
        """
        return ArgparseCompleter(self)
    
    def validate_args(self, args: argparse.Namespace) -> Optional[str]:
        """
        验证参数
        
        Args:
            args: 解析后的参数
            
        Returns:
            错误信息，如果验证通过则返回 None
        """
        return None