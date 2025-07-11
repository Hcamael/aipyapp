#!/usr/bin/env python
# -*- coding: utf-8 -*-

from hmac import new
import os
import json
import re
from typing import TYPE_CHECKING
import uuid
import time
from pathlib import Path
from datetime import datetime
from collections import namedtuple
from importlib.resources import read_text

from loguru import logger
from rich.rule import Rule
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.syntax import Syntax
from rich.console import Console, Group
from rich.markdown import Markdown

from .. import T, __respkg__
from ..exec import Runner
from .runtime import Runtime
from .plugin import event_bus
from .utils import get_safe_filename
from .blocks import CodeBlocks
from .interface import Stoppable
from .llm import Client, ChatHistory
from . import prompt

if TYPE_CHECKING:
    from .taskmgr import TaskManager

CONSOLE_WHITE_HTML = read_text(__respkg__, "console_white.html")
CONSOLE_CODE_HTML = read_text(__respkg__, "console_code.html")

class Task(Stoppable):
    MAX_ROUNDS = 16

    def __init__(self, manager: 'TaskManager', client: 'Client'):
        super().__init__()
        self.manager = manager
        self.task_id = uuid.uuid4().hex
        self.log = logger.bind(src='task', id=self.task_id)
        self.settings = manager.settings
        self.envs = manager.envs
        self.console = Console(file=manager.console.file, record=True)
        self.max_rounds = self.settings.get('max_rounds', self.MAX_ROUNDS)
        self.cwd = manager.cwd / self.task_id
        self.client: 'Client' = client
        self.code_blocks = CodeBlocks(self.console)
        self.runtime: Runtime = Runtime(self)
        self.runner: Runner = Runner(self.runtime)
        self.system_prompt = prompt.get_system_prompt(manager.tips_manager.current_tips, manager.api_prompt, self.runtime.get_prompt(), manager.settings.get('system_prompt'))
        self.system_prompt += f"\n当前目录为：{self.cwd}\n**写文件时，请使用绝对路径**"
        self.cmd_exec_pattern = r'<!--\s*Cmd-Exec:\s*{\s*"name"\s*:\s*"([^"]+)"\s*}\s*-->'
        self.start_time = None
        self.done_time = None
        self.instruction = None

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
        if self.client:
            ret = self.client.use(name)
        return ret

    def save(self, path):
       if self.console.record:
           self.console.save_html(path, clear=False, code_format=CONSOLE_WHITE_HTML)

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
            self.console.print_exception()
        
    def _auto_save(self):
        event_bus.broadcast('auto_save', self)
        instruction = self.instruction
        task = {'instruction': instruction}
        if self.client:
            task['chats'] = self.client.history.json()
        task['runner'] = self.runner.history
        task['blocks'] = self.code_blocks.to_list()

        filename = self.cwd / "task.json"
        try:
            json.dump(task, open(filename, 'w', encoding='utf-8'), ensure_ascii=False, indent=4, default=str)
        except Exception as e:
            self.log.exception('Error saving task')

        filename = self.cwd / "console.html"
        self.save(filename)
        self.log.info('Task auto saved')

    def done(self):
        cwd = Path(self.manager.cwd)  # Change back to the original working directory
        curname = cwd / self.task_id # this is folder name
        newname = get_safe_filename(self.instruction)
        if not newname:
            newname = curname
        else:
            newname = cwd / newname
        if newname and os.path.exists(curname):
            try:
                os.rename(curname, newname)
            except Exception as e:
                self.log.exception('Error renaming task directory', curname=curname, newname=newname)

        self.done_time = time.time()
        self.log.info('Task done', parh=newname)
        self.console.print(f"[green]{T('Result file saved')}: \"{newname}\"")
        return newname
        
    def process_reply(self, markdown) -> tuple[bool, str]:
        status = False
        ret: dict = self.code_blocks.parse(markdown)
        if not ret:
            self.log.error('LLM 不太行，返回了错误的格式')
            return status, markdown
        
        json_str = json.dumps(ret, ensure_ascii=False, indent=2, default=str)
        self.box(f"✅ {T('Message parse result')}", json_str, lang="json")

        errors = ret.get('errors')
        if errors:
            event_bus('result', errors)
            self.console.print(f"{T('Start sending feedback')}...", style='dim white')
            feed_back = f"# 消息解析错误\n{json_str}"
            msg = self.chat(feed_back)
            if msg:
                status = True
            else:
                status = False
        elif 'exec_blocks' in ret:
            msg = self.process_code_reply(ret['exec_blocks'])
            status = True
        else:
            msg = "还未匹配该情况"
        return status, msg

    def print_code_result(self, block, result, title=None):
        line_numbers = True if 'traceback' in result else False
        syntax_code = Syntax(block.code, block.lang, line_numbers=line_numbers, word_wrap=True)
        json_result = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        syntax_result = Syntax(json_result, 'json', line_numbers=False, word_wrap=True)
        group = Group(syntax_code, Rule(), syntax_result)
        panel = Panel(group, title=title or block.name)
        self.console.print(panel)

    def process_code_reply(self, exec_blocks) -> str:
        results = []
        for block in exec_blocks:
            event_bus('exec', block)
            self.console.print(f"⚡ {T('Start executing code block')}: {block.name}", style='dim white')
            result = self.runner(block)
            if "stderr" in result or "errstr" in result:
                self.code_blocks.blocks.pop(block.name)
                self.code_blocks.history.remove(block)
            self.print_code_result(block, result)
            result['block_name'] = block.name
            results.append(result)
            event_bus('result', result)

        msg = prompt.get_results_prompt(results)
        self.console.print(f"{T('Start sending feedback')}...", style='dim white')
        feed_back = json.dumps(msg, ensure_ascii=False, default=str)
        return self.chat(feed_back)

    def box(self, title, content, align=None, lang=None):
        if lang:
            content = Syntax(content, lang, line_numbers=True, word_wrap=True)
        else:
            content = Markdown(content)

        if align:
            content = Align(content, align=align)
        
        self.console.print(Panel(content, title=title))

    def isInCodeBlock(self, cmd_id):
        self.console.print(f"⚡ blocks: {self.code_blocks.blocks.keys()}", style='dim white')
        for bid in self.code_blocks.blocks:
            if bid == cmd_id:
                return True
        return False

    # 删除错误的历史记录
    def clean(self):
        self.console.print(f"⚡ clean history", style='dim white')
        history: 'ChatHistory' = self.client.history
        if len(history.messages) > 3:
            index = -3
            while True:
                if history.messages[index].role == "assistant":
                    content = history.messages[index].content
                    # 使用正则表达式匹配 Cmd-Exec 注释
                    match = re.search(self.cmd_exec_pattern, content)
                    if match:
                        cmd_id = match.group(1)  # 获取匹配到的 id 值
                        # 如果id不在code_block中，则表明是发生错误的代码，可以从历史记录中删除
                        if not self.isInCodeBlock(cmd_id):
                            # 删除assistant错误部分
                            history.messages.pop(index)
                            # 删除user错误部分
                            history.messages.pop(index + 1)
                            index += 1
                            continue
                elif history.messages[index].role == "user":
                    # 如果用户消息不是最初任务，则到达了用户提问的地方
                    msg = history.messages[index].content
                    if msg.startswith('{"task"'):
                        break
                elif history.messages[index].role == "system":
                    break
                index -= 1

    def print_summary(self):
        history = self.client.history
        summary = history.get_summary()
        if self.start_time:
            summary['elapsed_time'] = time.time() - self.start_time
        summarys = "| {rounds} | {time:.3f}s/{elapsed_time:.3f}s | Tokens: {input_tokens}/{output_tokens}/{total_tokens}".format(**summary)
        event_bus.broadcast('summary', summarys)
        self.console.print(f"\n⏹ [cyan]{T('End processing instruction')} {summarys}")

    def chat(self, instruction, *, system_prompt=None) -> str:
        quiet = not self.settings.debug
        msg = self.client(instruction, system_prompt=system_prompt, quiet=quiet)
        if msg.role == 'error':
            self.console.print(f"[red]{msg.content}[/red]")
            return ""
        if msg.reason:
            content = f"{msg.reason}\n\n-----\n\n{msg.content}"
        else:
            content = msg.content
        self.box(f"[yellow]{T('Reply')} ({self.client.name})", content)
        return msg.content

    def run(self, instruction) -> str:
        """
        执行自动处理循环，直到 LLM 不再返回代码消息
        """
        self.box(f"[yellow]{T('Start processing instruction')}", instruction, align="center")
        if not self.start_time:
            self.start_time = time.time()
            self.instruction = instruction
            msg = prompt.get_task_prompt(instruction)
            event_bus('task_start', prompt)
            system_prompt = self.system_prompt
        else:
            system_prompt = None
            msg = prompt.get_chat_prompt(instruction, self.instruction)

        self.cwd.mkdir(exist_ok=True)

        rounds = 1
        max_rounds = self.max_rounds
        json_prompt = json.dumps(msg, ensure_ascii=False, default=str)
        response = self.chat(json_prompt, system_prompt=system_prompt)
        if not response:
            return "LLM 没有返回任何内容"
        status = True
        while status and rounds <= max_rounds:
            status, response = self.process_reply(response)
            rounds += 1
            if self.is_stopped():
                self.log.info('Task stopped')
                break

        self.print_summary()
        self.clean()
        self._auto_save()
        self.log.info('Loop done', rounds=rounds)
        return response