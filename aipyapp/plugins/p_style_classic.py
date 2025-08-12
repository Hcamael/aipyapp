#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
from functools import wraps
import json

from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.tree import Tree
from rich.text import Text
from rich.console import Console

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

class DisplayClassic(RichDisplayPlugin):
    """Classic display style"""
    name = "classic"
    version = "1.0.0"
    description = "Classic display style"
    author = "AiPy Team"

    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.live_display = None

    def _get_title(self, title: str, *args, style: str = "info", prefix: str = "\n"):
        text = Text(f"{prefix}● {title}".format(*args), style=style)
        text.highlight_words(args, style="bold white")
        return text

    def on_exception(self, event):
        """异常事件处理"""
        msg = event.data.get('msg', '')
        exception = event.data.get('exception')
        title = self._get_title(T("Exception occurred"), msg, style="error")
        tree = Tree(title)
        tree.add(exception)
        self.console.print(tree)

    def on_task_start(self, event):
        """任务开始事件处理"""
        data = event.data
        instruction = data.get('instruction')
        title = data.get('title')
        if not title:
            title = instruction
        tree = Tree(f"🚀 {T('Task processing started')}")
        tree.add(title)
        self.console.print(tree)

    def on_query_start(self, event):
        """查询开始事件处理"""
        data = event.data
        llm = data.get('llm', '')
        title = self._get_title(T("Sending message to {}"), llm)
        self.console.print(title)

    def on_round_start(self, event):
        """回合开始事件处理"""
        data = event.data
        instruction = data.get('instruction')
        title = data.get('title')
        if not title:
            title = instruction
        prompt = self._get_title(T("Instruction processing started"))
        tree = Tree(prompt)
        tree.add(title)
        self.console.print(tree)

    def on_stream_start(self, event):
        """流式开始事件处理"""
        if not self.quiet:
            self.live_display = LiveDisplay()
            self.live_display.__enter__()
            title = self._get_title(T("Streaming started"), prefix="")
            self.console.print(title)
    
    def on_stream_end(self, event):
        """流式结束事件处理"""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None

    def on_stream(self, event):
        """LLM 流式响应事件处理"""
        response = event.data
        lines = response.get('lines')
        reason = response.get('reason', False)
        if self.live_display:
            self.live_display.update_display(lines, reason=reason)

    @staticmethod
    def convert_front_matter(md_text: str) -> str:
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        #return re.sub(pattern, r"```yaml\n\1\n```\n", md_text, flags=re.DOTALL)
        return re.sub(pattern, "", md_text, flags=re.DOTALL)
          
    def on_response_complete(self, event):
        """LLM 响应完成事件处理"""
        data = event.data
        llm = data.get('llm', '')
        msg = data.get('msg')
        if not msg:
            title = self._get_title(T("LLM response is empty"), style="error")
            self.console.print(title)
            return
        
        if msg.role == 'error':
            title = self._get_title(T("Failed to receive message"), style="error")
            tree = Tree(title)
            tree.add(msg.content)
            self.console.print(tree)
            return
        
        content = self.convert_front_matter(msg.content)
        if msg.reason:
            content = f"{msg.reason}\n\n-----\n\n{content}"
        title = self._get_title(f"{T('Completed receiving message')} ({llm})", style="success")
        tree = Tree(title)
        tree.add(Markdown(content))
        self.console.print(tree)

    def on_task_status(self, event):
        """任务状态事件处理"""
        status = event.data.get('status')
        completed = status.get('completed', False)
        style = "success" if completed else "error" 
        title = self._get_title(T("Task status"), style=style)
        tree = Tree(title, guide_style=style)
        if completed:
            tree.add(T("Completed"))
            tree.add(T("Confidence level: {}", status.get('confidence', 0)))
        else:
            tree.add(T("Failed"))
            tree.add(T("Reason: {}", status.get('reason', '')))
            tree.add(T("Suggestion: {}", status.get('suggestion', '')))
        self.console.print(tree)

    def on_parse_reply(self, event):
        """消息解析结果事件处理"""
        ret = event.data.get('result')
        if not ret:
            return
            
        title = self._get_title(T("Message parse result"))
        tree = Tree(title)
        
        if 'blocks' in ret and ret['blocks']:
            block_count = len(ret['blocks'])
            tree.add(f"{block_count} {T('code blocks')}")
        
        if 'commands' in ret and ret['commands']:
            commands = ret['commands']
            # 分别统计和显示不同类型的指令
            exec_commands = [cmd for cmd in commands if cmd['type'] == 'exec']
            edit_commands = [cmd for cmd in commands if cmd['type'] == 'edit']
            
            if exec_commands:
                exec_names = [cmd.get('block_name', 'Unknown') for cmd in exec_commands]
                exec_str = ", ".join(exec_names[:3])
                if len(exec_names) > 3:
                    exec_str += f" (+{len(exec_names)-3} more)"
                tree.add(f"{T('Execution')}: {exec_str}")
                
            if edit_commands:
                edit_names = [cmd['instruction']['name'] for cmd in edit_commands if 'instruction' in cmd]
                edit_str = ", ".join(edit_names[:3])
                if len(edit_names) > 3:
                    edit_str += f" (+{len(edit_names)-3} more)"
                tree.add(f"{T('Edit')}: {edit_str}")
        
        if 'call_tool' in ret:
            tree.add(T("MCP tool call"))
        
        if 'errors' in ret and ret['errors']:
            error_count = len(ret['errors'])
            tree.add(f"{error_count} {T('errors')}")
        
        self.console.print(tree)

    def on_exec(self, event):
        """代码执行开始事件处理"""
        block = event.data.get('block')
        title = self._get_title(T("Start executing code block {}"), block.name)
        self.console.print(title)
        
    def on_edit_start(self, event):
        """代码编辑开始事件处理"""
        instruction = event.data.get('instruction', {})
        block_name = instruction.get('name', 'Unknown')
        old_str = instruction.get('old', '')
        new_str = instruction.get('new', '')
        
        title = self._get_title(T("Start editing code block {}"), block_name, style="warning")
        tree = Tree(title)
        
        if old_str:
            old_preview = old_str[:50] + '...' if len(old_str) > 50 else old_str
            tree.add(f"{T('Replace')}: {repr(old_preview)}")
        if new_str:
            new_preview = new_str[:50] + '...' if len(new_str) > 50 else new_str
            tree.add(f"{T('With')}: {repr(new_preview)}")
            
        self.console.print(tree)
        
    def on_edit_result(self, event):
        """代码编辑结果事件处理"""
        data = event.data
        result = data.get('result', {})
        
        success = result.get('success', False)
        message = result.get('message', '')
        block_name = result.get('block_name', 'Unknown')
        new_version = result.get('new_version')
        
        if success:
            style = "success"
            title = self._get_title(T("Edit completed {}"), block_name, style=style)
            tree = Tree(title)
            
            if message:
                tree.add(message)
            if new_version:
                tree.add(f"{T('New version')}: v{new_version}")
        else:
            style = "error"
            title = self._get_title(T("Edit failed {}"), block_name, style=style)
            tree = Tree(title)
            tree.add(message or T("Edit operation failed"))
            
        self.console.print(tree)
            
    @restore_output
    def on_call_function(self, event):
        """函数调用事件处理"""
        data = event.data
        funcname = data.get('funcname')
        title = self._get_title(T("Start calling function {}"), funcname)
        self.console.print(title)

    @restore_output
    def on_call_function_result(self, event):
        """函数调用结果事件处理"""
        data = event.data
        funcname = data.get('funcname')
        success = data.get('success', False)
        result = data.get('result')
        error = data.get('error')
        
        if success:
            style = "success"
            title = self._get_title(T("Function call result {}"), funcname, style=style)
            tree = Tree(title)
            if result is not None:
                # 格式化并显示结果
                if isinstance(result, (dict, list)):
                    json_result = json.dumps(result, ensure_ascii=False, indent=2, default=str)
                    tree.add(Syntax(json_result, "json", word_wrap=True, line_range=(0, 10)))
                else:
                    tree.add(str(result))
            else:
                tree.add(T("No return value"))
            self.console.print(tree)
        else:
            style = "error"
            title = self._get_title(T("Function call failed {}"), funcname, style=style)
            tree = Tree(title)
            tree.add(error if error else T("Unknown error"))
            self.console.print(tree)

    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        
        try:
            success = result['__state__']['success']
            style = "success" if success else "error"
        except:
            style = "warning"
        
        # 显示说明信息
        block_name = getattr(block, 'name', 'Unknown') if block else 'Unknown'
        title = self._get_title(T("Execution result {}"), block_name, style=style)
        tree = Tree(title)
        
        # JSON格式化和高亮显示结果
        json_result = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        tree.add(Syntax(json_result, "json", word_wrap=True))
        self.console.print(tree)

    def on_mcp_call(self, event):
        """工具调用事件处理"""
        title = self._get_title(T("Start calling MCP tool"))
        self.console.print(title)
                
    def on_mcp_result(self, event):
        """MCP 工具调用结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        title = self._get_title(T("MCP tool call result {}"), block.name)
        self.console.print(title)
        json_result = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        self.console.print_json(json_result, style="dim")

    def on_round_end(self, event):
        """任务总结事件处理"""
        summary = event.data['summary']
        usages = summary.get('usages', [])
        if usages:
            table = Table(title=T("Task Summary"), show_lines=True)

            table.add_column(T("Round"), justify="center", style="bold cyan", no_wrap=True)
            table.add_column(T("Time(s)"), justify="right")
            table.add_column(T("In Tokens"), justify="right")
            table.add_column(T("Out Tokens"), justify="right")
            table.add_column(T("Total Tokens"), justify="right", style="bold magenta")

            round = 1
            for row in usages:
                table.add_row(
                    str(round),
                    str(row["time"]),
                    str(row["input_tokens"]),
                    str(row["output_tokens"]),
                    str(row["total_tokens"]),
                )
                round += 1
            self.console.print("\n")
            self.console.print(table)

        summary = summary.get('summary')
        title = self._get_title(T("End processing instruction"))
        tree = Tree(title)
        tree.add(f"{T('Summary')}: {summary}")
        self.console.print(tree)

    def on_upload_result(self, event):
        """云端上传结果事件处理"""
        data = event.data
        status_code = data.get('status_code', 0)
        url = data.get('url', '')
        if url:
            self.console.print(f"🟢 {T('Article uploaded successfully, {}', url)}", style="success")
        else:
            self.console.print(f"🔴 {T('Upload failed (status code: {})', status_code)}", style="error")

    def on_task_end(self, event):
        """任务结束事件处理"""
        path = event.data.get('path', '')
        title = self._get_title(T("Task completed"))
        tree = Tree(title)
        tree.add(path)
        self.console.print(tree)

    def on_runtime_message(self, event):
        """Runtime消息事件处理"""
        data = event.data
        message = data.get('message', '')
        status = data.get('status', 'info')
        title = self._get_title(message, style=status)
        self.console.print(title)

    def on_runtime_input(self, event):
        """Runtime输入事件处理"""
        # 输入事件通常不需要特殊处理，因为input_prompt已经处理了
        pass