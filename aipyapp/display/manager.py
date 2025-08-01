#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from typing import Dict, Type, Optional
from rich.console import Console

from loguru import logger

from .. import T
from .base import BaseDisplayPlugin
from .style_classic import DisplayClassic
from .style_modern import DisplayModern
from .style_minimal import DisplayMinimal
from .style_null import DisplayNull

class DisplayManager:
    """显示效果管理器"""
    
    # 可用的显示效果插件
    DISPLAY_PLUGINS = {
        'classic': DisplayClassic,
        'modern': DisplayModern,
        'minimal': DisplayMinimal,
    }
    
    def __init__(self, style: str, /, console: Console = None, record: bool = True, quiet: bool = False):
        """
        Args:
            style: 显示风格
            console: 控制台对象
            record: 是否记录输出，控制是否可以保存HTML文件
            quiet: 是否安静模式，控制是否输出到控制台，不影响记录功能
        """
        self.console = console
        self.record = record
        self.quiet = quiet
        self.current_style = None
        self._record_buffer = console._record_buffer[:] if console else []
        self.logger = logger.bind(src='display_manager')

        # 初始化默认插件
        self.set_style(style)
        
    def get_available_styles(self) -> list:
        """获取可用的显示风格列表"""
        return list(self.DISPLAY_PLUGINS.keys())
        
    def set_style(self, style_name: str) -> bool:
        """设置显示风格"""
        if style_name not in self.DISPLAY_PLUGINS:
            self.logger.error(f"Invalid display style: {style_name}")
            self.current_style = 'null'
            return False
            
        self.current_style = style_name
        self.logger.info(f"Set display style to {style_name}")
        return True
        
    def get_current_plugin(self) -> Optional[BaseDisplayPlugin]:
        """获取当前显示插件"""
        if self.current_style:
            plugin_class = self.DISPLAY_PLUGINS[self.current_style]
        else:
            self.logger.warning("No display style set, using null display")
            plugin_class = DisplayNull

        if self.quiet:
            if not self.record:
                quiet = True
            else:
                quiet = False
                file = open(os.devnull, 'w', encoding='utf-8')
        else:
            quiet = False
            file = None

        console = Console(file=file, record=self.record, quiet=quiet)
        console._record_buffer.extend(self._record_buffer)
        return plugin_class(console, quiet=self.quiet)
        
    def register_plugin(self, name: str, plugin_class: Type[BaseDisplayPlugin]):
        """注册新的显示效果插件"""
        self.DISPLAY_PLUGINS[name] = plugin_class
        
    def get_plugin_info(self) -> Dict[str, str]:
        """获取插件信息"""
        info = {}
        for name, plugin_class in self.DISPLAY_PLUGINS.items():
            info[name] = T(plugin_class.__doc__) or f"{name} display style"
        return info 