#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from functools import wraps
from typing import Any, Dict, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown

from aipyapp.display import RichDisplayPlugin
from live_display import LiveDisplay
from aipyapp import T

def restore_output(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

        try:
            return func(self, *args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
    return wrapper

class DisplayModern(RichDisplayPlugin):
    """Modern display style"""
    name = "modern"
    version = "1.0.0"
    description = "Modern display style"
    author = "AiPy Team"

    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.current_block = None
        self.execution_status = {}
        self.live_display = None
        self.stream_buffer = ""
        self.thinking_buffer = ""
        self.is_thinking = False
        
    def on_task_start(self, event):
        """任务开始事件处理"""
        data = event.data
        instruction = data.get('instruction', '')
        user_prompt = data.get('user_prompt', '')
        
        # 显示任务开始信息
        title = Text("🚀 任务开始", style="bold blue")
        content = Text(instruction, style="white")
        panel = Panel(content, title=title, border_style="blue")
        self.console.print(panel)
        self.console.print()
        
    def on_round_start(self, event):
        """回合开始事件处理"""
        data = event.data
        instruction = data.get('instruction', '')
        
        # 显示回合开始信息
        title = Text("🔄 回合开始", style="bold yellow")
        content = Text(instruction, style="white")
        panel = Panel(content, title=title, border_style="yellow")
        self.console.print(panel)
        self.console.print()
        
    def on_query_start(self, event):
        """查询开始事件处理"""
        self.console.print(f"📤 {T('Sending message to LLM')}...", style="dim cyan")
        
    def on_stream_start(self, event):
        """流式开始事件处理"""
        if not self.quiet:
            self.live_display = LiveDisplay()
            self.live_display.__enter__()
            self.console.print(f"📥 {T('Streaming started')}...", style="dim cyan")
    
    def on_stream_end(self, event):
        """流式结束事件处理"""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None
        self.console.print()
        
    def on_stream(self, event):
        """LLM 流式响应事件处理"""
        response = event.data
        lines = response.get('lines', [])
        reason = response.get('reason', False)
        
        if self.live_display:
            self.live_display.update_display(lines, reason=reason)
        
    def on_response_complete(self, event):
        """LLM 响应完成事件处理"""
        data = event.data
        llm = data.get('llm', '')
        msg = data.get('msg')
        
        if not msg:
            self.console.print(f"❌ {T('LLM response is empty')}", style="red")
            return
            
        if msg.role == 'error':
            self.console.print(f"❌ {msg.content}", style="red")
            return
            
        # 处理响应内容
        if msg.reason:
            content = f"{msg.reason}\n\n-----\n\n{msg.content}"
        else:
            content = msg.content
            
        # 智能解析和显示内容
        self._parse_and_display_content(content, llm)
        
    def on_parse_reply(self, event):
        """消息解析结果事件处理"""
        ret = event.data.get('result')
        if ret:
            # 显示解析结果摘要
            if 'commands' in ret:
                commands = ret['commands']
                if commands:
                    # 统计不同类型的指令
                    exec_count = sum(1 for cmd in commands if cmd['type'] == 'exec')
                    edit_count = sum(1 for cmd in commands if cmd['type'] == 'edit')
                    
                    summary_parts = []
                    if exec_count > 0:
                        summary_parts.append(f"{exec_count} exec")
                    if edit_count > 0:
                        summary_parts.append(f"{edit_count} edit")
                        
                    if summary_parts:
                        summary = ', '.join(summary_parts)
                        self.console.print(f"🎯 {T('Found commands')}: {summary}", style="dim green")
            elif 'call_tool' in ret:
                self.console.print(f"🔧 {T('Tool call detected')}", style="dim blue")
            elif 'blocks' in ret and ret['blocks']:
                block_count = len(ret['blocks'])
                self.console.print(f"📝 {T('Found {} code blocks')}.format({block_count})", style="dim green")
                
    def on_exec(self, event):
        """代码执行开始事件处理"""
        block = event.data.get('block')
        if not block:
            return
            
        block_name = getattr(block, 'name', 'Unknown')
        self.current_block = block_name
        self.execution_status[block_name] = 'running'
        
        # 显示代码块
        self._show_code_block(block)
        
        # 显示执行状态
        self.console.print(f"⏳ {T('Executing')}...", style="yellow")
        
    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        
        if block and hasattr(block, 'name'):
            self.current_block = block.name
            self.execution_status[block.name] = 'success'
            
        # 显示执行结果
        self._show_execution_result(result)
        
    def on_edit_start(self, event):
        """代码编辑开始事件处理"""
        instruction = event.data.get('instruction', {})
        block_name = instruction.get('name', 'Unknown')
        old_str = instruction.get('old', '')
        new_str = instruction.get('new', '')
        
        # 显示编辑操作信息
        title = Text(f"✏️ 编辑代码块: {block_name}", style="bold yellow")
        
        # 创建编辑预览内容
        content_lines = []
        if old_str:
            old_preview = old_str[:50] + '...' if len(old_str) > 50 else old_str
            content_lines.append(Text(f"替换: {repr(old_preview)}", style="red"))
        if new_str:
            new_preview = new_str[:50] + '...' if len(new_str) > 50 else new_str
            content_lines.append(Text(f"为: {repr(new_preview)}", style="green"))
        
        from rich.console import Group
        content = Group(*content_lines) if content_lines else Text("编辑操作", style="white")
        panel = Panel(content, title=title, border_style="yellow")
        self.console.print(panel)
        
    def on_edit_result(self, event):
        """代码编辑结果事件处理"""
        data = event.data
        result = data.get('result', {})
        
        success = result.get('success', False)
        message = result.get('message', '')
        block_name = result.get('block_name', 'Unknown')
        new_version = result.get('new_version')
        
        if success:
            title = Text(f"✅ 编辑成功: {block_name}", style="bold green")
            content_lines = []
            
            if message:
                content_lines.append(Text(message, style="white"))
            if new_version:
                content_lines.append(Text(f"新版本: v{new_version}", style="cyan"))
                
            from rich.console import Group
            content = Group(*content_lines) if content_lines else Text("编辑完成", style="white")
            panel = Panel(content, title=title, border_style="green")
        else:
            title = Text(f"❌ 编辑失败: {block_name}", style="bold red")
            content = Text(message or "编辑操作失败", style="red")
            panel = Panel(content, title=title, border_style="red")
            
        self.console.print(panel)
        
    def on_mcp_call(self, event):
        """MCP 工具调用事件处理"""
        block = event.data.get('block')
        if block and hasattr(block, 'content'):
            # 显示工具调用内容
            title = Text("🔧 MCP 工具调用", style="bold blue")
            content = Syntax(block.content, 'json', line_numbers=False, word_wrap=True)
            panel = Panel(content, title=title, border_style="blue")
            self.console.print(panel)
        else:
            self.console.print(f"🔧 {T('Calling MCP tool')}...", style="dim blue")
                
    def on_mcp_result(self, event):
        """MCP 工具调用结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        
        # 显示工具调用结果
        title = Text("🔧 MCP 工具结果", style="bold green")
        if isinstance(result, dict):
            content = Syntax(json.dumps(result, ensure_ascii=False, indent=2), 'json', line_numbers=False, word_wrap=True)
        else:
            content = Text(str(result), style="white")
        panel = Panel(content, title=title, border_style="green")
        self.console.print(panel)
        
    def on_round_end(self, event):
        """回合结束事件处理"""
        data = event.data
        summary = data.get('summary', {})
        response = data.get('response', '')
        
        # 显示统计信息
        if 'usages' in summary and summary['usages']:
            self._show_usage_table(summary['usages'])
            
        # 显示总结信息
        summary_text = summary.get('summary', '')
        if summary_text:
            title = Text("📊 执行统计", style="bold cyan")
            content = Text(summary_text, style="white")
            panel = Panel(content, title=title, border_style="cyan")
            self.console.print(panel)
            
        # 显示最终响应
        if response:
            self.console.print()
            self._parse_and_display_content(response, "Final Response")
            
    def on_task_end(self, event):
        """任务结束事件处理"""
        path = event.data.get('path', '')
        title = Text("✅ 任务完成", style="bold green")
        content = Text(f"结果已保存到: {path}", style="white")
        panel = Panel(content, title=title, border_style="green")
        self.console.print(panel)
        
    def on_upload_result(self, event):
        """云端上传结果事件处理"""
        data = event.data
        status_code = data.get('status_code', 0)
        url = data.get('url', '')
        
        if url:
            title = Text("☁️ 上传成功", style="bold green")
            content = Text(f"链接: {url}", style="white")
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
        else:
            title = Text("❌ 上传失败", style="bold red")
            content = Text(f"状态码: {status_code}", style="white")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
            
    def on_exception(self, event):
        """异常事件处理"""
        import traceback
        data = event.data
        msg = data.get('msg', '')
        exception = data.get('exception')
        traceback_str = data.get('traceback')
        
        title = Text("💥 异常", style="bold red")
        if traceback_str:
            content = Syntax(traceback_str, 'python', line_numbers=True, word_wrap=True)
        elif exception:
            try:
                tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
                tb_str = ''.join(tb_lines)
                content = Syntax(tb_str, 'python', line_numbers=True, word_wrap=True)
            except:
                content = Text(f"{msg}: {exception}", style="red")
        else:
            content = Text(msg, style="red")
            
        panel = Panel(content, title=title, border_style="red")
        self.console.print(panel)
        
    def on_runtime_message(self, event):
        """Runtime消息事件处理"""
        data = event.data
        message = data.get('message', '')
        if message:
            self.console.print(message, style="dim white")
            
    def on_runtime_input(self, event):
        """Runtime输入事件处理"""
        # 输入事件通常不需要特殊处理，因为input_prompt已经处理了
        pass
    
    @restore_output
    def on_call_function(self, event):
        """函数调用事件处理"""
        data = event.data
        funcname = data.get('funcname')
        title = Text(f"🔧 {T('Start calling function {}')}".format(funcname), style="bold blue")
        panel = Panel(Text(funcname, style="white"), title=title, border_style="blue")
        self.console.print(panel)
    
    @restore_output
    def on_call_function_result(self, event):
        """函数调用结果事件处理"""
        data = event.data
        funcname = data.get('funcname')
        success = data.get('success', False)
        result = data.get('result')
        error = data.get('error')
        
        if success:
            title = Text(f"✅ {T('Function call result {}')}".format(funcname), style="bold green")
            
            if result is not None:
                # 格式化并显示结果
                if isinstance(result, (dict, list)):
                    content = Syntax(json.dumps(result, ensure_ascii=False, indent=2, default=str), 'json', line_numbers=False, word_wrap=True)
                else:
                    content = Text(str(result), style="white")
            else:
                content = Text(T("No return value"), style="dim white")
            
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
        else:
            title = Text(f"❌ {T('Function call failed {}')}".format(funcname), style="bold red")
            content = Text(error if error else T("Unknown error"), style="red")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
        
    def _parse_and_display_content(self, content: str, llm: str = ""):
        """智能解析并显示内容"""
        if not content:
            return
            
        # 检测是否包含代码块
        if '```' in content:
            self._show_content_with_code_blocks(content, llm)
        else:
            self._show_text_content(content, llm)
            
    def _show_content_with_code_blocks(self, content: str, llm: str = ""):
        """显示包含代码块的内容"""
        lines = content.split('\n')
        in_code_block = False
        code_lang = ""
        code_content = []
        text_content = []
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # 结束代码块
                    if code_content:
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
                text_content.append(line)
                
        # 显示文本内容
        if text_content:
            text = '\n'.join(text_content).strip()
            if text:
                self._show_text_content(text, llm)
                    
    def _show_text_content(self, content: str, llm: str = ""):
        """显示纯文本内容"""
        if not content.strip():
            return
            
        # 使用 Markdown 渲染文本内容
        try:
            markdown = Markdown(content)
            if llm:
                title = Text(f"🤖 {llm}", style="bold cyan")
                panel = Panel(markdown, title=title, border_style="cyan")
            else:
                panel = Panel(markdown, border_style="white")
            self.console.print(panel)
        except:
            # 如果 Markdown 渲染失败，直接显示文本
            if llm:
                self.console.print(f"🤖 {llm}:", style="bold cyan")
            self.console.print(content)
            
    def _show_code_block(self, block: Any):
        """显示代码块"""
        if hasattr(block, 'code') and hasattr(block, 'lang'):
            self._show_code_block_content(block.lang, block.code, block.name)
        else:
            # 兼容其他格式
            self.console.print(f"📝 {T('Code block')}", style="dim white")
            
    def _show_code_block_content(self, lang: str, code: str, name: str = None):
        """显示代码块内容"""
        if not code.strip():
            return
            
        title = f"📝 {name or T('Code')} ({lang})"
        
        # 使用语法高亮显示代码
        syntax = Syntax(code, lang, line_numbers=True, word_wrap=True)
        panel = Panel(syntax, title=title, border_style="blue")
        self.console.print(panel)
        
    def _show_execution_result(self, result: Any):
        """显示执行结果"""
        if isinstance(result, dict):
            self._show_structured_result(result)
        else:
            self._show_simple_result(result)
            
    def _show_structured_result(self, result: Dict[str, Any]):
        """显示结构化结果"""
        # 检查是否有错误
        if 'traceback' in result or 'error' in result:
            title = Text("❌ 执行失败", style="bold red")
            if 'traceback' in result:
                content = Syntax(result['traceback'], 'python', line_numbers=True, word_wrap=True)
            else:
                content = Text(str(result.get('error', 'Unknown error')), style="red")
            panel = Panel(content, title=title, border_style="red")
            self.console.print(panel)
        else:
            # 显示成功结果
            title = Text("✅ 执行成功", style="bold green")
            output_parts = []
            
            # 收集输出信息
            if 'output' in result and result['output']:
                output_parts.append(f"📤 {T('Output')}: {result['output']}")
            if 'stdout' in result and result['stdout']:
                output_parts.append(f"📤 {T('Stdout')}: {result['stdout']}")
            if 'stderr' in result and result['stderr']:
                output_parts.append(f"⚠️ {T('Stderr')}: {result['stderr']}")
                
            if output_parts:
                content = Text('\n'.join(output_parts), style="white")
                panel = Panel(content, title=title, border_style="green")
                self.console.print(panel)
            else:
                self.console.print("✅ 执行成功", style="green")
                
    def _show_simple_result(self, result: Any):
        """显示简单结果"""
        if result is None:
            self.console.print("✅ 执行完成", style="green")
        else:
            title = Text("✅ 执行结果", style="bold green")
            content = Text(str(result), style="white")
            panel = Panel(content, title=title, border_style="green")
            self.console.print(panel)
            
    def _show_usage_table(self, usages: List[Dict[str, Any]]):
        """显示使用统计表格"""
        if not usages:
            return
            
        table = Table(title=T("执行统计"), show_lines=True)
        
        table.add_column(T("回合"), justify="center", style="bold cyan", no_wrap=True)
        table.add_column(T("时间(s)"), justify="right")
        table.add_column(T("输入Token"), justify="right")
        table.add_column(T("输出Token"), justify="right")
        table.add_column(T("总计Token"), justify="right", style="bold magenta")
        
        for i, usage in enumerate(usages, 1):
            table.add_row(
                str(i),
                str(usage.get("time", 0)),
                str(usage.get("input_tokens", 0)),
                str(usage.get("output_tokens", 0)),
                str(usage.get("total_tokens", 0)),
            )
            
        self.console.print(table)
        self.console.print() 