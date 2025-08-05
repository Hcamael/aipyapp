#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC
from typing import Any, Dict, Union
from rich.console import Console

from .. import T
from ..aipy import Event

class BaseDisplayPlugin(ABC):
    """显示效果插件基类"""
    
    def __init__(self, console: Console, quiet: bool = False):
        self.console = console
        self.quiet = quiet

    def save(self, path: str, clear: bool = False, code_format: str = None):
        """保存输出"""
        if self.console.record:
            self.console.save_html(path, clear=clear, code_format=code_format)

    # 新增：输入输出相关方法
    def print(self, message: str, style: str = None):
        """显示消息"""
        if style:
            self.console.print(message, style=style)
        else:
            self.console.print(message)
    
    def input(self, prompt: str) -> str:
        """获取用户输入"""
        return self.console.input(prompt)
    
    def confirm(self, prompt, default="n", auto=None):
        """确认操作"""
        if auto in (True, False):
            self.print(f"✅ {T('Auto confirm')}")
            return auto
        while True:
            response = self.input(prompt).strip().lower()
            if not response:
                response = default
            if response in ["y", "n"]:
                break
        return response == "y"

    def on_exception(self, event: Event):
        """异常事件处理"""
        pass

    def on_task_start(self, event: Event):
        """任务开始事件处理"""
        pass
        
    def on_response_complete(self, event: Event):
        """LLM 响应完成事件处理"""
        pass
        
    def on_exec_result(self, event: Event):
        """代码执行结果事件处理"""
        pass

    def on_task_end(self, event: Event):
        """任务结束事件处理"""
        pass

    def on_query_start(self, event: Event):
        """查询开始事件处理"""
        pass
        
    def on_round_start(self, event: Event):
        """回合开始事件处理"""
        pass
        
    def on_round_end(self, event: Event):
        """回合结束事件处理"""
        pass
        
    def on_stream_start(self, event: Event):
        """流式开始事件处理"""
        pass
        
    def on_stream_end(self, event: Event):
        """流式结束事件处理"""
        pass
        
    def on_stream(self, event: Event):
        """LLM 流式响应事件处理"""
        pass
        
    def on_parse_reply(self, event: Event):
        """消息解析结果事件处理"""
        pass
        
    def on_exec(self, event: Event):
        """代码执行开始事件处理"""
        pass
        
    def on_mcp_result(self, event: Event):
        """MCP 工具调用结果事件处理"""
        pass
        
    def on_mcp_call(self, event: Event):
        """工具调用事件处理"""
        pass 

    def on_upload_result(self, event: Event):
        """云端上传结果事件处理"""
        pass

    def on_runtime_message(self, event: Event):
        """Runtime消息事件处理"""
        pass

    def on_runtime_input(self, event: Event):
        """Runtime输入事件处理"""
        pass

    def on_show_image(self, event: Event):
        """显示图片事件处理"""
        pass