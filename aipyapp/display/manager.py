#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from typing import Dict, Type, Optional
from rich.console import Console

from loguru import logger

from .. import T
from .base import DisplayPlugin
from .themes import get_theme, THEMES

class DisplayManager:
    """显示效果管理器"""
    
    def __init__(self, display_config, console: Console = None, record: bool = True, quiet: bool = False):
        """
        Args:
            console: 控制台对象
            record: 是否记录输出，控制是否可以保存HTML文件
            quiet: 是否安静模式，控制是否输出到控制台，不影响记录功能
            display_config: display配置字典，包含style、theme等设置
        """
        # 处理display配置
        config = display_config or {}
        self.console = console
        self.plugins = {}
        self.style = config.get('style', 'classic')
        self.theme = config.get('theme', 'default')
        self.record = config.get('record', True)
        self.quiet = config.get('quiet', False)
        self._record_buffer = console._record_buffer[:] if console else []
        self.logger = logger.bind(src='display_manager')
        self.logger.info(f"DisplayManager initialized with style: {self.style}, theme: {self.theme}")
        
    def set_style(self, style: str):
        """设置显示风格"""
        self.style = style
        self.logger.info(f"Display style changed to: {self.style}")
        return True
        
    def get_available_styles(self) -> list:
        """获取可用的显示风格列表"""
        return [name for name in self.plugins.keys() if name not in ['null', 'agent']]
        
    def get_available_themes(self) -> list:
        """获取可用的主题列表"""
        return list(THEMES.keys())
        
    def create_display_plugin(self) -> Optional[DisplayPlugin]:
        """获取当前显示插件"""
        plugin_class = self.plugins[self.style]

        if self.quiet:
            if not self.record:
                quiet = True
            else:
                quiet = False
                file = open(os.devnull, 'w', encoding='utf-8')
        else:
            quiet = False
            file = None

        # 获取用户配置的主题
        rich_theme = get_theme(self.theme)
        console = Console(file=file, record=self.record, quiet=quiet, theme=rich_theme)
        console._record_buffer.extend(self._record_buffer)
        plugin = plugin_class(console, quiet=self.quiet)
        try:
            plugin.init()
        except Exception as e:
            self.logger.error(f"Failed to initialize display plugin {plugin_class.__name__}: {e}")
            return None
        return plugin
        
    def register_plugin(self, plugin_class: Type[DisplayPlugin], name: str = None):
        """注册新的显示效果插件"""
        if name is None:
            name = plugin_class.name or plugin_class.__class__.__name__

        if name in self.plugins:
            self.logger.warning(f"Display plugin {name} already registered")
            return False

        if not issubclass(plugin_class, DisplayPlugin):
            self.logger.warning(f"Display plugin {name} is not a subclass of DisplayPlugin")
            return False

        self.plugins[name] = plugin_class
        return True
        
    def get_plugin_info(self) -> Dict[str, str]:
        """获取插件信息"""
        info = {}
        for name, plugin_class in self.plugins.items():
            info[name] = T(plugin_class.__doc__) or f"{name} display style"
        return info
    
 