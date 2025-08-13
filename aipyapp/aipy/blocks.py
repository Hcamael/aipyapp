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
from ..interface import Trackable

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
            '__type__': 'CodeBlock',
            'name': self.name,
            'version': self.version,
            'lang': self.lang,
            'code': self.code,
            'path': self.path,
            'deps': self.deps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeBlock':
        """从字典恢复对象"""
        return cls(
            name=data.get('name', ''),
            version=data.get('version', 1),
            lang=data.get('lang', ''),
            code=data.get('code', ''),
            path=data.get('path'),
            deps=data.get('deps')
        )

    def __repr__(self):
        return f"<CodeBlock name={self.name}, version={self.version}, lang={self.lang}, path={self.path}>"

class CodeBlocks(Trackable):
    def __init__(self):
        self.history = []
        self.blocks = OrderedDict()
        self.code_pattern = re.compile(
            r'<!--\s*Block-Start:\s*(\{.*?\})\s*-->\s*(?P<ticks>`{3,})(\w+)?\s*\n(.*?)\n(?P=ticks)\s*<!--\s*Block-End:\s*(\{.*?\})\s*-->',
            re.DOTALL
        )
        self.line_pattern = re.compile(
            r'<!--\s*Cmd-(\w+):\s*(\{.*?\})\s*-->'
        )
        self.log = logger.bind(src='code_blocks')

    def __len__(self):
        return len(self.blocks)
    
    def parse(self, markdown_text, parse_mcp=False):
        blocks = OrderedDict()
        errors = []
        for match in self.code_pattern.finditer(markdown_text):
            start_json, _, lang, content, end_json = match.groups()
            try:
                start_meta = json.loads(start_json)
                end_meta = json.loads(end_json)
            except json.JSONDecodeError as e:
                self.log.exception('Error parsing code block', start_json=start_json, end_json=end_json)
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
            if code_name in blocks or code_name in self.blocks:
                old_block = blocks.get(code_name) or self.blocks.get(code_name)
                old_version = old_block.version
                if old_version >= version:
                    self.log.error("Duplicate code name with same or newer version", code_name=code_name, old_version=old_version, version=version)
                    error = {'Duplicate code name with same or newer version': {'code_name': code_name, 'old_version': old_version, 'version': version}}
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

        commands = []  # 按顺序收集所有命令
        line_matches = self.line_pattern.findall(markdown_text)
        for line_match in line_matches:
            cmd, json_str = line_match
            try:
                line_meta = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.log.error(f"Invalid JSON in Cmd-{cmd} block", json_str=json_str, reason=e)
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
                    commands.append({
                        'type': 'exec',
                        'block_name': exec_name
                    })
            elif cmd == 'Edit':
                edit_name = line_meta.get("name")
                if not edit_name:
                    error = {'Cmd-Edit block without name': {'json_str': json_str}}
                elif edit_name not in self.blocks:
                    error = {'Cmd-Edit block not found': {'edit_name': edit_name, 'json_str': json_str}}
                elif not line_meta.get("old"):
                    error = {'Cmd-Edit block without old string': {'json_str': json_str}}
                elif "new" not in line_meta:
                    error = {'Cmd-Edit block without new string': {'json_str': json_str}}
                else:
                    commands.append({
                        'type': 'edit',
                        'instruction': {
                            'name': edit_name,
                            'old': line_meta.get("old"),
                            'new': line_meta.get("new"),
                            'replace_all': line_meta.get("replace_all", False),
                            'json_str': json_str
                        }
                    })
            else:
                error = {f'Unknown command in Cmd-{cmd} block': {'cmd': cmd}}

            if error:
                errors.append(error)

        ret = {}
        if errors: ret['errors'] = errors
        if commands: ret['commands'] = commands
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
            return None

    def get_block_by_name(self, code_name):
        try:
            return self.blocks[code_name]
        except KeyError:
            self.log.error("Code name not found", code_name=code_name)
            return None

    def apply_edit_modification(self, edit_instruction):
        """
        应用编辑指令到指定代码块，创建新版本而不修改原代码块
        
        Args:
            edit_instruction: 包含name, old, new, replace_all等字段的编辑指令
            
        Returns:
            tuple: (success: bool, message: str, new_block: CodeBlock or None)
        """
        name = edit_instruction['name']
        old_str = edit_instruction['old']
        new_str = edit_instruction['new']
        replace_all = edit_instruction.get('replace_all', False)
        
        if name not in self.blocks:
            return False, f"代码块 '{name}' 不存在", None
            
        original_block = self.blocks[name]
        
        # 检查是否找到匹配的字符串
        if old_str not in original_block.code:
            return False, f"未找到匹配的代码片段: {old_str[:50]}...", None
        
        # 检查匹配次数
        match_count = original_block.code.count(old_str)
        if match_count > 1 and not replace_all:
            return False, f"代码片段匹配 {match_count} 个位置，请设置 replace_all: true 或提供更具体的上下文", None
        
        # 执行替换生成新代码
        if replace_all:
            new_code = original_block.code.replace(old_str, new_str)
            replaced_count = match_count
        else:
            # 只替换第一个匹配项
            new_code = original_block.code.replace(old_str, new_str, 1)
            replaced_count = 1
        
        # 创建新的代码块（版本号+1）
        new_block = CodeBlock(
            name=original_block.name,
            version=original_block.version + 1,
            lang=original_block.lang,
            code=new_code,
            path=original_block.path,
            deps=original_block.deps.copy() if original_block.deps else None
        )
        
        # 保存新代码块到文件
        try:
            new_block.save()
            self.log.info("Created and saved new block version", code_block=new_block, replaced_count=replaced_count)
        except Exception as e:
            self.log.error("Failed to save new block", code_block=new_block, reason=e)
        
        # 更新blocks字典为新版本（同名代码块始终指向最新版本）
        self.blocks[name] = new_block
        
        # 添加新版本到历史记录
        self.history.append(new_block)
        
        message = f"成功替换 {replaced_count} 处匹配项，创建版本 v{new_block.version}"
        return True, message, new_block

    def to_list(self):
        """将 CodeBlocks 对象转换为 JSON 字符串
        
        Returns:
            str: JSON 格式的字符串
        """
        blocks = [block.to_dict() for block in self.history]
        return blocks
    
    def get_state(self):
        """获取需要持久化的状态数据"""
        return self.to_list()
    
    def restore_state(self, blocks_data):
        """从代码块数据恢复状态"""
        self.history.clear()
        self.blocks.clear()
        
        if blocks_data:
            for block_data in blocks_data:
                code_block = CodeBlock(
                    name=block_data['name'],
                    version=block_data['version'],
                    lang=block_data['lang'],
                    code=block_data['code'],
                    path=block_data.get('path'),
                    deps=block_data.get('deps')
                )
                self.history.append(code_block)
                self.blocks[code_block.name] = code_block
    

    def clear(self):
        self.history.clear()
        self.blocks.clear()
    
    # Trackable接口实现
    def get_checkpoint(self) -> int:
        """获取当前检查点状态 - 返回history长度"""
        return len(self.history)
    
    def restore_to_checkpoint(self, checkpoint: Optional[int]):
        """恢复到指定检查点"""
        if checkpoint is None:
            # 恢复到初始状态
            self.clear()
        else:
            # 恢复到指定长度
            if checkpoint < len(self.history):
                # 获取要删除的代码块
                deleted_blocks = self.history[checkpoint:]
                
                # 从 blocks 字典中删除对应的代码块
                for block in deleted_blocks:
                    if block.name in self.blocks:
                        del self.blocks[block.name]
                
                # 截断 history 到指定长度
                self.history = self.history[:checkpoint]