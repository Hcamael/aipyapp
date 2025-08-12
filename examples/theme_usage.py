#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主题使用示例

展示如何在AIPy中使用不同主题和样式
"""

# 配置示例 (aipy.toml)
"""
[display]
style = "modern"    # 显示风格: classic, modern, minimal, agent
theme = "dark"      # 颜色主题: default, dark, light, mono
"""

# 在代码中使用主题样式
def example_usage():
    from aipyapp.display.manager import DisplayManager
    from rich.panel import Panel
    from rich.table import Table
    
    # 使用配置创建DisplayManager
    display_config = {
        'style': 'modern',
        'theme': 'default'
    }
    
    dm = DisplayManager(display_config=display_config)
    plugin = dm.get_display_plugin()
    console = plugin.console
    
    # 使用预定义的样式
    console.print("这是信息消息", style="info")
    console.print("这是成功消息", style="success") 
    console.print("这是警告消息", style="warning")
    console.print("这是错误消息", style="error")
    
    # 使用任务状态样式
    console.print("任务运行中", style="task.running")
    console.print("任务成功完成", style="task.success")
    console.print("任务执行失败", style="task.error")
    
    # 使用面板样式
    panel = Panel(
        "面板内容",
        title="面板标题", 
        border_style="panel.border"
    )
    console.print(panel)
    
    # 使用表格样式
    table = Table(show_header=True, header_style="table.header")
    table.add_column("列1", style="table.cell")
    table.add_column("列2", style="table.cell")
    table.add_row("数据1", "数据2")
    console.print(table)
    
    # 内联样式使用
    console.print("[info]信息[/info] [success]成功[/success] [error]错误[/error]")

if __name__ == "__main__":
    example_usage()