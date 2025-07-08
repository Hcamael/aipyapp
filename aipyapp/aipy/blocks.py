#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, Any

from loguru import logger

from .libmcp import extract_call_tool_str, extra_call_tool_blocks

@dataclass
class CodeBlock:
    """代码块对象"""
    name: str
    version: int
    lang: str
    code: str
    path: Optional[str] = None
    deps: Optional[Dict[str, set]] = None

    def add_dep(self, dep_name: str, dep_value: Any):
        """添加依赖"""
        if self.deps is None:
            self.deps = {}
        if dep_name not in self.deps:
            deps = set()
            self.deps[dep_name] = deps
        else:
            deps = self.deps[dep_name]

        # dep_value 可以是单个值，或者一个可迭代对象
        if isinstance(dep_value, (list, set, tuple)):
            deps.update(dep_value)
        else:
            deps.add(dep_value)

    def save(self):
        """保存代码块到文件"""
        if not self.path:
            return False
            
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.code, encoding='utf-8')
        return True

    @property
    def abs_path(self):
        if self.path:
            return Path(self.path).absolute()
        return None
    
    def get_lang(self):
        lang = self.lang.lower()
        return lang
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'version': self.version,
            'lang': self.lang,
            'code': self.code,
            'path': self.path,
            'deps': self.deps
        }

    def __repr__(self):
        return f"<CodeBlock name={self.name}, version={self.version}, lang={self.lang}, path={self.path}>"

class CodeBlocks:
    def __init__(self, console):
        self.console = console
        self.history = []
        self.blocks = OrderedDict()
        self.code_pattern = re.compile(
            r'<!--\s*Block-Start:\s*(\{.*?\})\s*-->\s*```(\w+)?\s*\n(.*?)\n```\s*<!--\s*Block-End:\s*(\{.*?\})\s*-->',
            re.DOTALL
        )
        self.line_pattern = re.compile(
            r'<!--\s*Cmd-(\w+):\s*(\{.*?\})\s*-->'
        )
        self.log = logger.bind(src='code_blocks')

    def parse(self, markdown_text, parse_mcp=False):
        blocks = OrderedDict()
        errors = []
        for match in self.code_pattern.finditer(markdown_text):
            start_json, lang, content, end_json = match.groups()
            try:
                start_meta = json.loads(start_json)
                end_meta = json.loads(end_json)
            except json.JSONDecodeError as e:
                self.console.print_exception(show_locals=True)
                error = {'JSONDecodeError': {'Block-Start': start_json, 'Block-End': end_json, 'reason': str(e)}}
                errors.append(error)
                continue

            code_name = start_meta.get("name")
            if code_name != end_meta.get("name"):
                self.log.error("Start and end name mismatch", start_name=code_name, end_name=end_meta.get("name"))
                error = {'Start and end name mismatch': {'start_name': code_name, 'end_name': end_meta.get("name")}}
                errors.append(error)
                continue

            version = start_meta.get("version", 1)
            if (code_name in blocks or code_name in self.blocks) and version == self.blocks.get(code_name).version:
                self.log.error("Duplicate code name with same version", code_name=code_name, version=version)
                error = {'Duplicate code name with same version': {'code_name': code_name, 'version': version}}
                errors.append(error)
                continue

            # 创建代码块对象
            block = CodeBlock(
                name=code_name,
                version=version,
                lang=lang,
                code=content,
                path=start_meta.get('path'),
            )

            blocks[code_name] = block
            self.history.append(block)
            self.log.info("Parsed code block", code_block=block)

            try:
                block.save()
                self.log.info("Saved code block", code_block=block)
            except Exception as e:
                self.log.error("Failed to save file", code_block=block, reason=e)

        self.blocks.update(blocks)

        exec_blocks = []
        line_matches = self.line_pattern.findall(markdown_text)
        for line_match in line_matches:
            cmd, json_str = line_match
            try:
                line_meta = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.log.error("Invalid JSON in Cmd-{cmd} block", json_str=json_str, reason=e)
                error = {f'Invalid JSON in Cmd-{cmd} block': {'json_str': json_str, 'reason': str(e)}}
                errors.append(error)
                continue

            error = None
            if cmd == 'Exec':
                exec_name = line_meta.get("name")
                if not exec_name:
                    error = {'Cmd-Exec block without name': {'json_str': json_str}}
                elif exec_name not in self.blocks:
                    error = {'Cmd-Exec block not found': {'exec_name': exec_name, 'json_str': json_str}}
                else:
                    exec_blocks.append(self.blocks[exec_name])
            else:
                error = {f'Unknown command in Cmd-{cmd} block': {'cmd': cmd}}

            if error:
                errors.append(error)

        ret = {}
        if errors: ret['errors'] = errors
        if exec_blocks: ret['exec_blocks'] = exec_blocks
        if blocks: ret['blocks'] = [v for v in blocks.values()]

        if parse_mcp:
            # 首先尝试从代码块中提取 MCP 调用, 然后尝试从markdown文本中提取
            json_content = extra_call_tool_blocks(list(blocks.values())) or extract_call_tool_str(markdown_text)

            if json_content:
                ret['call_tool'] = json_content
                self.log.info("Parsed MCP call_tool", json_content=json_content)

        return ret
    
    def get_code_by_name(self, code_name):
        try:
            return self.blocks[code_name].code
        except KeyError:
            self.log.error("Code name not found", code_name=code_name)
            self.console.print("❌ Code name not found", code_name=code_name)
            return None

    def get_block_by_name(self, code_name):
        try:
            return self.blocks[code_name]
        except KeyError:
            self.log.error("Code name not found", code_name=code_name)
            self.console.print("❌ Code name not found", code_name=code_name)
            return None

    def to_list(self):
        """将 CodeBlocks 对象转换为 JSON 字符串
        
        Returns:
            str: JSON 格式的字符串
        """
        blocks = [block.to_dict() for block in self.history]
        return blocks