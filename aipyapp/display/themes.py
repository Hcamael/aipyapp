#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""显示主题定义"""

from rich.theme import Theme

# 默认主题（适合大多数终端）
DEFAULT_THEME = Theme({
    # 基础颜色
    "info": "cyan",
    "warning": "yellow", 
    "error": "red bold",
    "success": "green",
    
    # 面板和边框
    "panel.border": "blue",
    "panel.title": "bold cyan",
    
    # 代码相关
    "code": "white",
    "syntax.keyword": "magenta bold",
    "syntax.string": "green",
    "syntax.number": "cyan",
    "syntax.comment": "bright_black",
    
    # 任务状态
    "task.running": "yellow",
    "task.success": "green",
    "task.error": "red",
    
    # 表格
    "table.header": "bold cyan",
    "table.cell": "white",
})

# 深色主题（针对深色背景优化）
DARK_THEME = Theme({
    # 基础颜色
    "info": "bright_cyan",
    "warning": "bright_yellow",
    "error": "bright_red bold", 
    "success": "bright_green",
    
    # 面板和边框
    "panel.border": "bright_blue",
    "panel.title": "bold bright_cyan",
    
    # 代码相关
    "code": "bright_white",
    "syntax.keyword": "bright_magenta bold",
    "syntax.string": "bright_green",
    "syntax.number": "bright_cyan", 
    "syntax.comment": "bright_black",
    
    # 任务状态
    "task.running": "bright_yellow",
    "task.success": "bright_green", 
    "task.error": "bright_red",
    
    # 表格
    "table.header": "bold bright_cyan",
    "table.cell": "bright_white",
})

# 浅色主题（针对浅色背景优化）
LIGHT_THEME = Theme({
    # 基础颜色
    "info": "blue",
    "warning": "dark_orange",
    "error": "red bold",
    "success": "dark_green",
    
    # 面板和边框
    "panel.border": "blue", 
    "panel.title": "bold blue",
    
    # 代码相关
    "code": "black",
    "syntax.keyword": "blue bold",
    "syntax.string": "dark_green",
    "syntax.number": "dark_cyan",
    "syntax.comment": "bright_black",
    
    # 任务状态
    "task.running": "dark_orange",
    "task.success": "dark_green",
    "task.error": "red",
    
    # 表格
    "table.header": "bold blue",
    "table.cell": "black",
})

# 单色主题（只使用基本颜色，兼容性最好）
MONO_THEME = Theme({
    # 基础颜色
    "info": "white",
    "warning": "white", 
    "error": "white bold",
    "success": "white",
    
    # 面板和边框
    "panel.border": "white",
    "panel.title": "bold white",
    
    # 代码相关
    "code": "white",
    "syntax.keyword": "white bold",
    "syntax.string": "white",
    "syntax.number": "white",
    "syntax.comment": "bright_black",
    
    # 任务状态
    "task.running": "white",
    "task.success": "white",
    "task.error": "white bold",
    
    # 表格
    "table.header": "bold white",
    "table.cell": "white",
})

# 主题映射表
THEMES = {
    "default": DEFAULT_THEME,
    "dark": DARK_THEME, 
    "light": LIGHT_THEME,
    "mono": MONO_THEME,
}

def get_theme(theme_name: str) -> Theme:
    """获取指定名称的主题
    
    Args:
        theme_name: 主题名称 ("default", "dark", "light", "mono")
        
    Returns:
        Rich主题对象，如果主题名不存在则返回默认主题
    """
    return THEMES.get(theme_name, DEFAULT_THEME)