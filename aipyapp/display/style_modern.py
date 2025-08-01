#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
from typing import Any, Dict, Optional
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.table import Table
from rich.rule import Rule

from .base import BaseDisplayPlugin
from .. import T

class DisplayModern(BaseDisplayPlugin):
    """Modern display style"""
    
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.current_block = None
        self.execution_status = {}
        self.stream_buffer = ""
        self.thinking_buffer = ""
        
    def on_task_start(self, content: Any):
        """任务开始事件处理"""
        if isinstance(content, str):
            self.console.print(f"📝 {T('Task')}: {content}")
        else:
            self.console.print(f"📝 {T('Task started')}")
        self.console.print()
        
    def on_exception(self, msg: str, exception: Exception):
        """异常事件处理"""
        self.console.print(f"❌ {msg}")
        self.console.print_exception(exception)
        
    def on_response_stream(self, response: Dict[str, Any]):
        """LLM 流式响应事件处理"""
        content = response.get('content', '')
        reason = response.get('reason', False)
        
        if reason:
            # Thinking 内容
            self.thinking_buffer += content
            self._show_thinking()
        else:
            # 普通内容，累积到缓冲区并实时显示
            self.stream_buffer += content
            self._show_streaming_content()
            
    def on_response_complete(self, llm: str, msg: Any):
        """LLM 响应完成事件处理"""
        if not msg:
            self.console.print(f"[red]{T('LLM response is empty')}[/red]")
            return
        if msg.role == 'error':
            self.console.print(f"[red]{msg.content}[/red]")
            return
        if msg.reason:
            content = f"{msg.reason}\n\n-----\n\n{msg.content}"
        else:
            content = msg.content
        self._parse_and_display_content(content)
            
    def on_exec(self, block: Any):
        """代码执行开始事件处理"""
        block_name = getattr(block, 'name', 'Unknown')
        self.current_block = block_name
        self.execution_status[block_name] = 'running'
        
        # 显示代码块
        self._show_code_block(block)
        
        # 显示执行状态
        self.console.print(f"⏳ {T('Executing')}...")
        
    def on_result(self, result: Any):
        """代码执行结果事件处理"""
        if self.current_block:
            self.execution_status[self.current_block] = 'success'
            
        # 显示执行结果
        self._show_execution_result(result)
        
    def on_exec_result(self, data: Dict[str, Any]):
        """代码执行结果事件处理"""
        result = data.get('result')
        block = data.get('block')
        
        if block and hasattr(block, 'name'):
            self.current_block = block.name
            self.execution_status[block.name] = 'success'
            
        # 显示执行结果
        self._show_execution_result(result)
        
    def on_summary(self, summary: str):
        """任务总结事件处理"""
        self.console.print()
        self.console.print(f"✅ {T('Task completed')}")
        self.console.print(f"📊 {summary}")
        
    def on_tool_call(self, block: Any):
        """工具调用事件处理"""
        self.console.print(f"🔧 {T('Calling tool')}...")
        
    def _show_thinking(self):
        """显示思考过程"""
        if self.thinking_buffer:
            with self:
                self.update_live(f"🤔 {T('Thinking')}...\n{self.thinking_buffer}")
                
    def _show_streaming_content(self):
        """显示流式内容"""
        if self.stream_buffer:
            with self:
                self.update_live(self.stream_buffer)
                
    def _parse_and_display_content(self, content: str):
        """解析并显示内容"""
        # 简单的代码块检测
        if '```' in content:
            # 有代码块，使用特殊格式
            self._show_content_with_code_blocks(content)
        else:
            # 纯文本内容
            self._show_text_content(content)
            
    def _show_content_with_code_blocks(self, content: str):
        """显示包含代码块的内容"""
        lines = content.split('\n')
        in_code_block = False
        code_lang = ""
        code_content = []
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # 结束代码块
                    self._show_code_block_content(code_lang, '\n'.join(code_content))
                    in_code_block = False
                    code_content = []
                else:
                    # 开始代码块
                    in_code_block = True
                    code_lang = line[3:].strip()
            elif in_code_block:
                code_content.append(line)
            else:
                # 普通文本行
                if line.strip():
                    self.console.print(line)
                    
    def _show_text_content(self, content: str):
        """显示纯文本内容"""
        self.console.print(content)
                

        
    def _show_code_block(self, block: Any):
        """显示代码块"""
        if hasattr(block, 'code') and hasattr(block, 'lang'):
            self._show_code_block_content(block.lang, block.code, block.name)
        else:
            # 兼容其他格式
            self.console.print(f"📝 {T('Code block')}")
            
    def _show_code_block_content(self, lang: str, code: str, name: str = None):
        """显示代码块内容"""
        title = f"📝 {name or T('Code')} ({lang})"
        
        # 使用简洁的代码显示格式
        syntax = Syntax(code, lang, line_numbers=True, word_wrap=True)
        panel = Panel(syntax, title=title, border_style="blue")
        self.console.print(panel)
        
    def _show_execution_result(self, result: Any):
        """显示执行结果"""
        if isinstance(result, dict):
            # 结构化结果
            self._show_structured_result(result)
        else:
            # 简单结果
            self._show_simple_result(result)
            
    def _show_structured_result(self, result: Dict[str, Any]):
        """显示结构化结果"""
        # 检查是否有错误
        if 'traceback' in result or 'error' in result:
            self.console.print("❌ {T('Execution failed')}")
            if 'traceback' in result:
                syntax = Syntax(result['traceback'], 'python', line_numbers=True)
                panel = Panel(syntax, title="❌ Error", border_style="red")
                self.console.print(panel)
        else:
            self.console.print("✅ {T('Execution successful')}")
            # 显示结果摘要
            if 'output' in result:
                self.console.print(f"📤 {T('Output')}: {result['output']}")
                
    def _show_simple_result(self, result: Any):
        """显示简单结果"""
        self.console.print("✅ {T('Execution completed')}")
        if result:
            self.console.print(f"📤 {T('Result')}: {result}")

    def on_runtime_message(self, data: Dict[str, Any]):
        """Runtime消息事件处理"""
        message = data.get('message', '')
        self.console.print(message)

    def on_runtime_input(self, data: Dict[str, Any]):
        """Runtime输入事件处理"""
        # 输入事件通常不需要特殊处理，因为input_prompt已经处理了
        pass 