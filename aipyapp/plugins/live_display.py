#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.live import Live
from rich.text import Text

class LiveDisplay:
    """传统的 Live 显示组件，专门负责实时显示流式内容"""
    
    def __init__(self, quiet=False):
        self.reason_started = False
        self.display_lines = []
        self.max_lines = 10
        self.quiet = quiet
        self.live = None

    def __enter__(self):
        self.live = Live(auto_refresh=False, vertical_overflow='crop', transient=True)
        self.live.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.live.__exit__(exc_type, exc_val, exc_tb)
        self.live = None

    def update_display(self, lines, reason=False):
        """更新显示内容"""
        if self.quiet: 
            return
        
        # 处理思考状态的开始和结束
        if reason and not self.reason_started:
            self.display_lines.append("<think>")
            self.reason_started = True
        elif not reason and self.reason_started:
            self.display_lines.append("</think>")
            self.reason_started = False

        self.display_lines.extend(lines)

        # 限制显示行数，保持最新的行
        while len(self.display_lines) > self.max_lines:
            self.display_lines.pop(0)
            
        # 更新显示
        display_content = '\n'.join(self.display_lines)
        self.live.update(Text(display_content, style="dim color(240)"), refresh=True) 