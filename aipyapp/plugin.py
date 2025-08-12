from typing import Any, Callable, Dict
import inspect
from enum import Enum

from loguru import logger

from .interface import EventListener

class PluginType(Enum):
    """插件类型"""
    BASE = "base"
    TASK = "task"
    DISPLAY = "display"

class PluginError(Exception):
    """插件异常"""
    pass

class PluginConfigError(PluginError):
    """插件配置异常"""
    pass

class PluginInitError(PluginError):
    """插件初始化异常"""
    pass

class Plugin(EventListener):
    """插件基类"""
    name: str = None
    version: str = None
    description: str = None
    author: str = None

    def __init__(self):
        self.logger = logger.bind(src=f"plugin.{self.name}")

    @property
    def description(self) -> str:
        """插件描述"""
        return self.description or self.__doc__
    
    @property
    def version(self) -> str:
        """插件版本"""
        return self.version or "1.0.0"
    
    @property
    def author(self) -> str:
        """插件作者"""
        return self.author or "Unknown"
    
    def init(self):
        """插件初始化逻辑
        
        Raises:
            PluginInitError: 插件初始化异常
        """
        pass
    
    @classmethod
    def get_type(cls) -> PluginType:
        """Get plugin type
        
        Returns:
            Plugin type
        """
        return PluginType.BASE
    
    def _get_methods(self, prefix: str = "fn_") -> Dict[str, Callable]:
        """Get all functions
        
        Returns:
            All functions
        """
        return {
            name[len(prefix):]: method
            for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if name.startswith(prefix) and len(name) > len(prefix)
        }
    
    def get_handlers(self) -> Dict[str, Callable]:
        """Get all handlers
        
        Returns:
            All handlers
        """
        return self._get_methods(prefix='on_')

class TaskPlugin(Plugin):
    """任务插件"""
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}

    @classmethod
    def get_type(cls) -> PluginType:
        """Get plugin type
        
        Returns:
            Plugin type
        """
        return PluginType.TASK

    def get_functions(self) -> Dict[str, Callable]:
        """Get all functions
        
        Returns:
            All functions
        """
        return self._get_methods(prefix='fn_')
    