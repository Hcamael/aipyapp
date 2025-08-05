#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Any, Dict, Union

from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status

from .base import BaseDisplayPlugin
from .. import T

class DisplayMinimal(BaseDisplayPlugin):
    """Minimal display style"""
    
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.live_display = None
        self.received_lines = 0  # 记录接收的行数
        self.status = None  # Status 对象

    def on_task_start(self, event):
        """任务开始事件处理"""
        data = event.data
        instruction = data.get('instruction')
        self.console.print(f"→ {instruction}")

    def on_task_end(self, event):
        """任务结束事件处理"""
        path = event.data.get('path', '')
        self.console.print(f"[green]{T('Task completed')}: {path}")

    def on_exception(self, event):
        """异常事件处理"""
        data = event.data
        msg = data.get('msg', '')
        self.console.print(f"✗ {msg}", style='red')

    def on_query_start(self, event):
        """查询开始事件处理"""
        self.console.print("⟳ Sending...", style='dim')

    def on_round_start(self, event):
        """回合开始事件处理"""
        data = event.data
        instruction = data.get('instruction')
        self.console.print(f"→ {instruction}")

    def on_stream_start(self, event):
        """流式开始事件处理"""
        # 简约风格：重置行数计数器并启动 Status
        self.received_lines = 0
        self.status = Status("📥 Receiving response...", console=self.console)
        self.status.start()
    
    def on_stream_end(self, event):
        """流式结束事件处理"""
        # 简约风格：停止 Status 并显示最终结果
        if self.status:
            self.status.stop()
            if self.received_lines > 0:
                self.console.print(f"📥 Received {self.received_lines} lines total", style='dim')
        self.status = None

    def on_stream(self, event):
        """LLM 流式响应事件处理"""
        response = event.data
        lines = response.get('lines', [])
        reason = response.get('reason', False)
        
        if not reason:  # 只统计非思考内容
            self.received_lines += len(lines)
            # 使用 Status 在同一行更新进度
            if self.status:
                self.status.update(f"📥 Receiving response... ({self.received_lines} lines)")
                
    def on_response_complete(self, event):
        """LLM 响应完成事件处理"""
        data = event.data
        llm = data.get('llm', '')
        msg = data.get('msg')
        if not msg:
            self.console.print("✗ Empty response")
            return
        if msg.role == 'error':
            self.console.print(f"✗ {msg.content}")
            return

    def on_parse_reply(self, event):
        """消息解析结果事件处理"""
        ret = event.data.get('result')
        if ret:
            # 简约显示：显示解析到的代码块名称
            if 'exec_blocks' in ret:
                blocks = ret['exec_blocks']
                if blocks:
                    block_names = [getattr(block, 'name', f'block_{i}') for i, block in enumerate(blocks)]
                    names_str = ', '.join(block_names[:3])  # 只显示前3个
                    if len(blocks) > 3:
                        names_str += f'... (+{len(blocks)-3} more)'
                    self.console.print(f"📝 Found: {names_str}", style='dim')
            elif 'call_tool' in ret:
                self.console.print("🔧 Tool call detected", style='dim')

    def on_exec(self, event):
        """代码执行开始事件处理"""
        block = event.data.get('block')
        # 简约显示：显示将要执行的代码块信息
        name = getattr(block, 'name', 'Unknown')
        lang = getattr(block, 'lang', 'text')
        self.console.print(f"▶ Executing: {name} ({lang})", style='dim')

    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        
        # 简约显示：显示简要执行结果
        if isinstance(result, dict):
            if 'traceback' in result:
                self.console.print("✗ Error", style='red')
                # 显示错误的第一行
                if result.get('traceback'):
                    error_lines = result['traceback'].split('\n')
                    for line in error_lines:
                        if line.strip() and not line.startswith('Traceback'):
                            self.console.print(f"  {line.strip()}", style='red')
                            break
            else:
                self.console.print("✓ Success", style='green')
                # 如果有输出且不为空，显示简要输出
                if 'output' in result and result['output']:
                    output = str(result['output']).strip()
                    if output:
                        # 只显示前100个字符
                        if len(output) > 100:
                            output = output[:100] + "..."
                        self.console.print(f"  {output}", style='dim')
        else:
            self.console.print(f"✓ {result}", style='green')

    def on_mcp_call(self, event):
        """工具调用事件处理"""
        # 简约风格：不显示工具调用信息
        pass

    def on_mcp_result(self, event):
        """MCP 工具调用结果事件处理"""
        # 简约风格：不显示工具调用结果
        pass

    def on_round_end(self, event):
        """任务总结事件处理"""
        data = event.data
        summary = data.get('summary', {})
        response = data.get('response', '')
        # 简约显示：只显示总结信息
        self.console.print(Markdown(response)) 
        self.console.print(f"• {summary.get('summary')}")

    def on_runtime_message(self, event):
        """Runtime消息事件处理"""
        data = event.data
        message = data.get('message', '')
        self.console.print(message)

    def on_runtime_input(self, event):
        """Runtime输入事件处理"""
        # 输入事件通常不需要特殊处理，因为input_prompt已经处理了
        pass 
        