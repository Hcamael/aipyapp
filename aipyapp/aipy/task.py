#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import time
from datetime import datetime
from collections import namedtuple, OrderedDict
from importlib.resources import read_text

import requests
from loguru import logger

from .. import T, __respkg__
from ..exec import BlockExecutor
from .runtime import CliPythonRuntime
from .utils import get_safe_filename
from .blocks import CodeBlocks, CodeBlock
from .interface import Stoppable, EventBus
from .multimodal import MMContent, LLMContext

CONSOLE_WHITE_HTML = read_text(__respkg__, "console_white.html")
CONSOLE_CODE_HTML = read_text(__respkg__, "console_code.html")

class TaskError(Exception):
    """Task 异常"""
    pass

class TaskInputError(TaskError):
    """Task 输入异常"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class Task(Stoppable, EventBus):
    MAX_ROUNDS = 16

    def __init__(self, context):
        super().__init__()
        self.task_id = uuid.uuid4().hex
        self.log = logger.bind(src='task', id=self.task_id)
        
        self.context = context
        self.settings = context.settings
        self.prompts = context.prompts

        self.start_time = None
        self.done_time = None
        self.instruction = None
        self.saved = None
        self.gui = self.settings.gui

        self.cwd = context.cwd / self.task_id
        self.max_rounds = self.settings.get('max_rounds', self.MAX_ROUNDS)
        
        self.mcp = context.mcp
        self.client = context.client_manager.Client(self)
        self.role = context.role_manager.current_role
        self.code_blocks = CodeBlocks()
        self.runtime = CliPythonRuntime(self)
        self.runner = BlockExecutor()
        self.runner.set_python_runtime(self.runtime)
        self.init_plugins()

    def init_plugins(self):
        """初始化插件"""
        plugin_manager = self.context.plugin_manager
        for plugin_name, plugin_data in self.role.plugins.items():
            plugin = plugin_manager.get_plugin(plugin_name, plugin_data)
            if not plugin:
                self.log.warning(f"Plugin {plugin_name} not found")
                continue
            self.register_listener(plugin)
            
        # 注册显示效果插件
        self.display = self.context.display_manager.get_current_plugin()
        self.register_listener(self.display)

    def to_record(self):
        TaskRecord = namedtuple('TaskRecord', ['task_id', 'start_time', 'done_time', 'instruction'])
        start_time = datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S') if self.start_time else '-'
        done_time = datetime.fromtimestamp(self.done_time).strftime('%H:%M:%S') if self.done_time else '-'
        return TaskRecord(
            task_id=self.task_id,
            start_time=start_time,
            done_time=done_time,
            instruction=self.instruction[:32] if self.instruction else '-'
        )
    
    def use(self, name):
        ret = self.client.use(name)
        return ret
        
    def save(self, path):
        self.display.save(path, clear=False, code_format=CONSOLE_WHITE_HTML)

    def save_html(self, path, task):
        if 'chats' in task and isinstance(task['chats'], list) and len(task['chats']) > 0:
            if task['chats'][0]['role'] == 'system':
                task['chats'].pop(0)

        task_json = json.dumps(task, ensure_ascii=False, default=str)
        html_content = CONSOLE_CODE_HTML.replace('{{code}}', task_json)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            self.log.exception('Error saving html')
            self.broadcast('exception', 'save_html', e)
        
    def _auto_save(self):
        # event_bus.broadcast('auto_save', self)
        instruction = self.instruction
        task = OrderedDict()
        task['instruction'] = instruction
        task['start_time'] = self.start_time
        task['done_time'] = self.done_time
        task['chats'] = self.client.history.json()
        task['runner'] = self.runner.history
        task['blocks'] = self.code_blocks.to_list()

        filename = self.cwd / "task.json"
        try:
            json.dump(task, open(filename, 'w', encoding='utf-8'), ensure_ascii=False, indent=4, default=str)
        except Exception as e:
            self.log.exception('Error saving task')
            self.broadcast('exception', 'save_task', e)

        filename = self.cwd / "console.html"
        #self.save_html(filename, task)
        self.save(filename)
        self.saved = True
        self.log.info('Task auto saved')

    def done(self):
        if not self.instruction or not self.start_time:
            self.log.warning('Task not started, skipping save')
            return
        
        self.done_time = time.time()
        if not self.saved:
            self.log.warning('Task not saved, trying to save')
            self._auto_save()

        os.chdir(self.context.cwd)  # Change back to the original working directory
        curname = self.task_id
        newname = get_safe_filename(self.instruction, extension=None)
        if newname and os.path.exists(curname):
            try:
                os.rename(curname, newname)
            except Exception as e:
                self.log.exception('Error renaming task directory', curname=curname, newname=newname)

        self.log.info('Task done', path=newname)
        self.broadcast('task_end', path=newname)
        self.context.diagnose.report_code_error(self.runner.history)
        if self.settings.get('share_result'):
            self.sync_to_cloud()
        
    def process_reply(self, markdown):
        parse_mcp = self.mcp is not None
        ret = self.code_blocks.parse(markdown, parse_mcp=parse_mcp)
        self.broadcast('parse_reply', ret)
        if not ret:
            return None

        if 'call_tool' in ret:
            return self.process_mcp_reply(ret['call_tool'])

        errors = ret.get('errors')
        if errors:
            json_str = json.dumps(errors, ensure_ascii=False, default=str)
            feed_back = f"# 消息解析错误\n{json_str}"
            ret = self.chat(feed_back)
        elif 'exec_blocks' in ret:
            ret = self.process_code_reply(ret['exec_blocks'])
        else:
            ret = None
        return ret

    def process_code_reply(self, exec_blocks):
        results = OrderedDict()
        for block in exec_blocks:
            self.pipeline('exec', block)
            result = self.runner(block)
            results[block.name] = result
            self.broadcast('exec_result', {'result': result, 'block': block})

        msg = self.prompts.get_results_prompt(results)
        return self.chat(msg)

    def process_mcp_reply(self, json_content):
        """处理 MCP 工具调用的回复"""
        block = {'content': json_content, 'language': 'json'}
        self.pipeline('mcp_call', block)

        call_tool = json.loads(json_content)
        result = self.mcp.call_tool(call_tool['name'], call_tool.get('arguments', {}))
        code_block = CodeBlock(
            code=json_content,
            lang='json',
            name=call_tool.get('name', 'MCP Tool Call'),
            version=1,
        )
        self.broadcast('mcp_result', {'block': code_block, 'result': result})
        msg = self.prompts.get_mcp_result_prompt(result)
        return self.chat(msg)

    def _get_summary(self, detail=False):
        data = {}
        history = self.client.history
        if detail:
            data['usages'] = history.get_usage()

        summary = history.get_summary()
        summary['elapsed_time'] = time.time() - self.start_time
        summarys = "| {rounds} | {time:.3f}s/{elapsed_time:.3f}s | Tokens: {input_tokens}/{output_tokens}/{total_tokens}".format(**summary)
        data['summary'] = summarys
        return data

    def chat(self, context: LLMContext, *, system_prompt=None):
        self.broadcast('query_start')
        quiet = self.gui and not self.settings.debug
        msg = self.client(context, system_prompt=system_prompt)
        self.broadcast('response_complete', llm=self.client.name, msg=msg)
        return msg.content if msg else None

    def _get_system_prompt(self):
        params = {}
        if self.mcp:
            params['mcp_tools'] = self.mcp.get_tools_prompt()
        params['util_functions'] = self.runtime.get_function_list()
        params['tool_functions'] = {}
        params['role'] = self.role
        return self.prompts.get_default_prompt(**params)
    
    def run(self, instruction: str):
        """
        执行自动处理循环，直到 LLM 不再返回代码消息
        instruction: 用户输入的字符串（可包含@file等多模态标记）
        """
        mmc = MMContent(instruction, base_path=self.context.cwd)
        try:
            content = mmc.content
        except Exception as e:
            raise TaskInputError(T("Invalid input"), e) from e

        if not self.client.has_capability(content):
            raise TaskInputError(T("Current model does not support this content"))

        user_prompt = content
        if not self.start_time:
            self.start_time = time.time()
            self.instruction = instruction
            if isinstance(content, str):
                user_prompt = self.prompts.get_task_prompt(content, gui=self.gui)
            system_prompt = self._get_system_prompt()
            self.pipeline('task_start', {'instruction': instruction, 'user_prompt': user_prompt})
        else:
            system_prompt = None
            if isinstance(content, str):
                user_prompt = self.prompts.get_chat_prompt(content, self.instruction)
            self.pipeline('round_start', {'instruction': instruction, 'user_prompt': user_prompt})

        self.cwd.mkdir(exist_ok=True)
        os.chdir(self.cwd)

        rounds = 1
        max_rounds = self.max_rounds
        self.saved = False
        response = self.chat(user_prompt, system_prompt=system_prompt)
        if not response:
            self.log.error('No response from LLM')
            return
        
        while rounds <= max_rounds:
            prev_response = response
            response = self.process_reply(response)
            rounds += 1
            if self.is_stopped():
                self.log.info('Task stopped')
                break
            if not response:
                response = prev_response
                break

        summary = self._get_summary()
        self.broadcast('round_end', summary, response=response)
        self._auto_save()
        self.log.info('Round done', rounds=rounds)

    def sync_to_cloud(self):
        """ Sync result
        """
        url = T("https://store.aipy.app/api/work")

        trustoken_apikey = self.settings.get('llm', {}).get('Trustoken', {}).get('api_key')
        if not trustoken_apikey:
            trustoken_apikey = self.settings.get('llm', {}).get('trustoken', {}).get('api_key')
        if not trustoken_apikey:
            return False
        self.log.info('Uploading result to cloud')
        try:
            # Serialize twice to remove the non-compliant JSON type.
            # First, use the json.dumps() `default` to convert the non-compliant JSON type to str.
            # However, NaN/Infinity will remain.
            # Second, use the json.loads() 'parse_constant' to convert NaN/Infinity to str.
            data = json.loads(
                json.dumps({
                    'apikey': trustoken_apikey,
                    'author': os.getlogin(),
                    'instruction': self.instruction,
                    'llm': self.client.history.json(),
                    'runner': self.runner.history,
                }, ensure_ascii=False, default=str),
                parse_constant=str)
            response = requests.post(url, json=data, verify=True,  timeout=30)
        except Exception as e:
            self.broadcast('exception', 'sync_to_cloud', e)
            return False

        url = None
        status_code = response.status_code
        if status_code in (200, 201):
            data = response.json()
            url = data.get('url', '')

        self.broadcast('upload_result', status_code, url)
        return True
