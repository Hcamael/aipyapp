#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Any, Dict
from datetime import datetime

from aipyapp import Event
from aipyapp.display import RichDisplayPlugin

class DisplayAgent(RichDisplayPlugin):
    """Agent模式显示插件 - 捕获所有输出用于API返回"""
    name = "agent"
    version = "1.0.0"
    description = "Agent display style"
    author = "AiPy Team"

    def __init__(self, console, quiet: bool = True):
        super().__init__(console, quiet)
        # 捕获的输出数据
        self.captured_data = {
            'messages': [],
            'results': [],
            'errors': [],
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'metadata': {}
        }
        
    def _add_message(self, message_type: str, content: Any, timestamp: str = None):
        """添加消息到捕获数据"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        self.captured_data['messages'].append({
            'type': message_type,
            'content': content,
            'timestamp': timestamp
        })
    
    def get_captured_data(self) -> Dict:
        """获取捕获的数据"""
        return self.captured_data.copy()
    
    def clear_captured_data(self):
        """清空捕获的数据"""
        self.captured_data = {
            'messages': [],
            'results': [],
            'errors': [],
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'metadata': {}
        }

    # 重写父类方法，捕获输出而不显示
    def print(self, message: str, style: str = None):
        """捕获打印消息"""
        self._add_message('print', {'message': message, 'style': style})
    
    def input(self, prompt: str) -> str:
        """Agent模式不支持交互输入"""
        self._add_message('input_request', {'prompt': prompt})
        return ''
    
    def confirm(self, prompt, default="n", auto=None):
        """Agent模式自动确认"""
        self._add_message('confirm', {'prompt': prompt, 'default': default, 'auto_response': auto})
        return auto if auto is not None else (default == "y")

    # 事件处理方法
    def on_task_start(self, event: Event):
        """任务开始"""
        instruction = event.data.get('instruction', 'Unknown instruction')
        self._add_message('task_start', {
            'instruction': instruction,
            'task_id': event.data.get('task_id', None)
        })
        self.captured_data['status'] = 'running'
        self.captured_data['metadata']['instruction'] = instruction
        
    def on_response_complete(self, event: Event):
        """LLM响应完成"""
        llm = event.data.get('llm', 'unknown')
        msg = event.data.get('msg')
        message_content = msg.content if (msg and hasattr(msg, 'content')) else str(msg) if msg else 'No response'
        
        self._add_message('llm_response', {
            'llm': llm,
            'message': message_content
        })
        
    def on_exec_result(self, event: Event):
        """代码执行结果"""
        block = event.data.get('block')
        result = event.data.get('result', {})
        
        result_data = {
            'block_name': block.name if (block and hasattr(block, 'name')) else 'unknown',
            'language': block.lang if (block and hasattr(block, 'lang')) else 'unknown',
            'result': result
        }
        self._add_message('exec_result', result_data)
        self.captured_data['results'].append(result_data)

    def on_task_end(self, event: Event):
        """任务结束"""
        self.captured_data['status'] = 'completed'
        self.captured_data['end_time'] = datetime.now().isoformat()
        self._add_message('task_end', {
            'path': event.data.get('path', None)
        })

    def on_exception(self, event: Event):
        """异常处理"""
        error_data = {
            'message': event.data.get('msg', 'Unknown error'),
            'exception': str(event.data.get('exception')) if event.data.get('exception') else None
        }
        self._add_message('error', error_data)
        self.captured_data['errors'].append(error_data)
        self.captured_data['status'] = 'error'

    def on_stream(self, event: Event):
        """流式响应"""
        self._add_message('stream', {
            'llm': event.data.get('llm', 'unknown'),
            'lines': event.data.get('lines', []),
            'reason': event.data.get('reason', False)
        })

    def on_parse_reply(self, event: Event):
        """解析回复"""
        self._add_message('parse_reply', {
            'result': event.data.get('result', {})
        })

    def on_mcp_result(self, event: Event):
        """MCP工具调用结果"""
        block = event.data.get('block')
        self._add_message('mcp_result', {
            'block': str(block) if block else None,
            'result': event.data.get('result', None)
        })

    def on_upload_result(self, event: Event):
        """云端上传结果"""
        self._add_message('upload_result', {
            'status_code': event.data.get('status_code', None),
            'url': event.data.get('url', None)
        })

    def on_query_start(self, event: Event):
        """查询开始"""
        self._add_message('query_start', {
            'timestamp': datetime.now().isoformat()
        })

    def on_round_start(self, event: Event):
        """回合开始"""
        self._add_message('round_start', {
            'instruction': event.data.get('instruction', 'Unknown'),
            'user_prompt': str(event.data.get('user_prompt', ''))
        })

    def on_round_end(self, event: Event):
        """回合结束"""
        self._add_message('round_end', {
            'summary': event.data.get('summary', {}),
            'response': str(event.data.get('response', ''))
        })

    def on_exec(self, event: Event):
        """代码执行开始"""
        block = event.data.get('block')
        self._add_message('exec_start', {
            'block_name': block.name if (block and hasattr(block, 'name')) else 'unknown',
            'language': block.lang if (block and hasattr(block, 'lang')) else 'unknown',
            'code': block.code if (block and hasattr(block, 'code')) else 'No code'
        })
        
    def on_edit_start(self, event: Event):
        """代码编辑开始"""
        instruction = event.data.get('instruction', {})
        self._add_message('edit_start', {
            'block_name': instruction.get('name', 'unknown'),
            'old_str': instruction.get('old', ''),
            'new_str': instruction.get('new', ''),
            'replace_all': instruction.get('replace_all', False)
        })
        
    def on_edit_result(self, event: Event):
        """代码编辑结果"""
        result = event.data.get('result', {})
        self._add_message('edit_result', {
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'block_name': result.get('block_name', 'unknown'),
            'new_version': result.get('new_version'),
            'old_str': result.get('old_str', ''),
            'new_str': result.get('new_str', ''),
            'replace_all': result.get('replace_all', False)
        })

    def on_mcp_call(self, event: Event):
        """MCP工具调用"""
        block = event.data.get('block', {})
        self._add_message('mcp_call', {
            'content': block.get('content') if isinstance(block, dict) else str(block),
            'language': block.get('language') if isinstance(block, dict) else 'json'
        })