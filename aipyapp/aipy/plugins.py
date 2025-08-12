#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import importlib.util
from typing import Dict, Any, List, Union, Optional, Type
from pathlib import Path

from loguru import logger

from .. import __pkgpath__, Plugin, PluginType

class PluginManager:
    """Plugin manager class."""
    FILE_PATTERN = "p_*.py"

    def __init__(self):
        self.sys_plugin_dir = os.path.join(__pkgpath__, 'plugins')
        self.plugin_directories: List[Path] = []
        self._plugins: Dict[str, Any] = {}
        self.logger = logger.bind(src=self.__class__.__name__)
        self.add_plugin_directory(self.sys_plugin_dir)
        
    def __iter__(self):
        return iter(self._plugins.values())
    
    def __getitem__(self, name: str) -> Plugin:
        return self._plugins[name]
    
    def __len__(self) -> int:
        return len(self._plugins)
    
    def add_plugin_directory(self, directory: Union[str, Path]):
        """Add a plugin directory to the plugin manager."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            self.logger.warning(f"Plugin directory {directory} does not exist")
            return False
        if dir_path in self.plugin_directories:
            self.logger.warning(f"Plugin directory {directory} already added")
            return False
        self.plugin_directories.append(dir_path)
        self.logger.info(f"Added plugin directory {directory}")
        return True

    def _discover_plugins(self) -> List[Path]:
        """Discover plugins in the plugin directories."""
        plugin_files = []
        for plugin_dir in self.plugin_directories:
            if not os.path.exists(plugin_dir):
                self.logger.warning(f"Plugin directory {plugin_dir} does not exist")
                continue
            for fname in plugin_dir.glob(self.FILE_PATTERN):
                plugin_files.append(fname)
        return plugin_files

    def _load_plugins(self, filepath: Path) -> List[Plugin]:
        """Load plugins from a file."""
        import sys
        
        name = filepath.stem
        plugin_dir = filepath.parent
        
        # 临时添加插件目录到 sys.path
        original_path = sys.path.copy()
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))
        
        try:
            spec = importlib.util.spec_from_file_location(name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugins = []
            for cls in module.__dict__.values():
                if isinstance(cls, type) and issubclass(cls, Plugin) and cls.name:
                    plugins.append(cls)
            return plugins
        finally:
            # 恢复原始 sys.path
            sys.path = original_path

    def _register_plugin(self, plugin: Plugin) -> bool:
        """Register a plugin."""
        plugin_name = plugin.name
        if not plugin_name:
            self.logger.warning(f"Plugin {plugin.__class__.__name__} has no name")
            return False
        if plugin_name in self._plugins:
            self.logger.warning(f"Plugin {plugin_name} already registered")
            return False
        self._plugins[plugin_name] = plugin
        return True

    def load_all_plugins(self):
        """Load all plugins."""
        success_count = 0
        plugin_files = self._discover_plugins()
        for plugin_file in plugin_files:
            plugins = self._load_plugins(plugin_file)
            for plugin in plugins:
                if self._register_plugin(plugin):
                    success_count += 1
                    self.logger.info(f"Loaded plugin {plugin.name} from {plugin_file}")
        self.logger.info(f"Loaded {success_count} plugins")

    def create_task_plugin(self, name: str, plugin_config: Dict[str, Any] = None) -> Optional[Plugin]:
        """Create a plugin by name."""
        plugin_cls = self._plugins.get(name)
        if not plugin_cls:
            self.logger.warning(f"Plugin {name} not found")
            return

        if plugin_cls.get_type() != PluginType.TASK:
            self.logger.warning(f"Plugin {name} is not a task plugin")
            return None

        plugin = plugin_cls(plugin_config)
        try:
            plugin.init()
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {name}: {e}")
            return None
        return plugin
    
    def get_task_plugins(self) -> List[Type[Plugin]]:
        """Get all task plugins."""
        return [plugin for plugin in self._plugins.values() if plugin.get_type() == PluginType.TASK]
    
    def get_display_plugins(self) -> List[Type[Plugin]]:
        """Get all display plugins."""
        return [plugin for plugin in self._plugins.values() if plugin.get_type() == PluginType.DISPLAY]
    