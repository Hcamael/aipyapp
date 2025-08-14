"""专门化的补齐器实现"""

import os
import glob
import shlex
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from prompt_toolkit.completion import Completion

from .base import CompleterBase, CompleterContext, create_completion


class PathCompleter(CompleterBase):
    """文件路径补齐器"""
    
    def __init__(self, 
                 only_dirs: bool = False,
                 only_files: bool = False,
                 glob_pattern: str = "*",
                 show_hidden: bool = False,
                 expanduser: bool = True):
        """
        Args:
            only_dirs: 只显示目录
            only_files: 只显示文件
            glob_pattern: glob 匹配模式
            show_hidden: 是否显示隐藏文件
            expanduser: 是否展开 ~ 路径
        """
        self.only_dirs = only_dirs
        self.only_files = only_files
        self.glob_pattern = glob_pattern
        self.show_hidden = show_hidden
        self.expanduser = expanduser
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """获取路径补齐"""
        path_str = context.current_word
        
        # 处理引号包裹的路径
        if path_str and path_str[0] in ('"', "'"):
            try:
                path_str = shlex.split(path_str)[0] if shlex.split(path_str) else path_str
            except ValueError:
                pass
        
        # 展开用户目录
        if self.expanduser and path_str.startswith('~'):
            path_str = os.path.expanduser(path_str)
        
        # 确定搜索目录和前缀
        if os.path.isdir(path_str) and path_str.endswith(os.sep):
            search_dir = path_str
            prefix = ""
        else:
            search_dir = os.path.dirname(path_str) or "."
            prefix = os.path.basename(path_str)
        
        # 获取匹配的路径
        completions = []
        try:
            pattern = os.path.join(search_dir, prefix + self.glob_pattern)
            matches = glob.glob(pattern)
            
            # 按修改时间排序，最新的在前面
            matches_with_mtime = []
            for match in matches:
                try:
                    mtime = os.path.getmtime(match)
                    matches_with_mtime.append((mtime, match))
                except (OSError, PermissionError):
                    # 如果无法获取修改时间，使用0作为默认值
                    matches_with_mtime.append((0, match))
            
            # 按修改时间降序排序（最新的在前）
            matches_with_mtime.sort(key=lambda x: x[0], reverse=True)
            
            for _, match in matches_with_mtime:
                basename = os.path.basename(match)
                
                # 检查是否显示隐藏文件
                if not self.show_hidden and basename.startswith('.'):
                    continue
                
                # 检查文件类型过滤
                is_dir = os.path.isdir(match)
                if self.only_dirs and not is_dir:
                    continue
                if self.only_files and is_dir:
                    continue
                
                # 构造补齐文本
                if ' ' in match:
                    completion_text = shlex.quote(match)
                else:
                    completion_text = match
                
                # 构造显示文本
                display_text = basename
                if is_dir:
                    display_text += '/'
                
                # 计算替换位置
                start_position = -len(context.current_word) if context.current_word else 0
                
                completions.append(create_completion(
                    completion_text,
                    start_position=start_position,
                    display=display_text,
                    display_meta="目录" if is_dir else "文件"
                ))
        
        except (OSError, PermissionError):
            pass
        
        return completions


class ChoiceCompleter(CompleterBase):
    """选择项补齐器"""
    
    def __init__(self, 
                 choices: List[str], 
                 descriptions: Optional[Dict[str, str]] = None,
                 case_sensitive: bool = False):
        """
        Args:
            choices: 选项列表
            descriptions: 选项描述字典
            case_sensitive: 是否区分大小写
        """
        self.choices = choices
        self.descriptions = descriptions or {}
        self.case_sensitive = case_sensitive
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """获取选择项补齐"""
        partial = context.current_word
        completions = []
        
        for choice in self.choices:
            # 匹配检查
            if self.case_sensitive:
                matches = choice.startswith(partial)
            else:
                matches = choice.lower().startswith(partial.lower())
            
            if matches:
                completions.append(create_completion(
                    choice,
                    start_position=-len(partial) if partial else 0,
                    display_meta=self.descriptions.get(choice, "")
                ))
        
        return completions


class CompositeCompleter(CompleterBase):
    """组合补齐器 - 支持多种补齐策略"""
    
    def __init__(self):
        self.strategies: List[tuple[CompleterBase, Optional[Callable]]] = []
    
    def add_strategy(self, 
                     completer: CompleterBase, 
                     condition: Optional[Callable[[CompleterContext], bool]] = None) -> 'CompositeCompleter':
        """
        添加补齐策略
        
        Args:
            completer: 补齐器
            condition: 可选的条件函数，返回 True 时才使用该补齐器
        """
        self.strategies.append((completer, condition))
        return self
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """按策略顺序尝试获取补齐"""
        for completer, condition in self.strategies:
            # 检查条件
            if condition is None or condition(context):
                completions = completer.get_completions(context)
                if completions:
                    return completions
        return []


class DynamicCompleter(CompleterBase):
    """动态补齐器 - 根据函数动态生成补齐项"""
    
    def __init__(self, 
                 provider: Callable[[CompleterContext], List[tuple[str, str]]]):
        """
        Args:
            provider: 提供补齐项的函数，返回 (text, description) 列表
        """
        self.provider = provider
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """动态获取补齐"""
        try:
            items = self.provider(context)
            partial = context.current_word
            completions = []
            
            for text, description in items:
                if text.startswith(partial):
                    completions.append(create_completion(
                        text,
                        start_position=-len(partial) if partial else 0,
                        display_meta=description
                    ))
            
            return completions
        except Exception:
            return []


class FuzzyCompleter(CompleterBase):
    """模糊匹配补齐器"""
    
    def __init__(self, completer: CompleterBase, min_score: float = 0.6):
        """
        Args:
            completer: 基础补齐器
            min_score: 最小匹配分数 (0-1)
        """
        self.completer = completer
        self.min_score = min_score
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """获取模糊匹配的补齐"""
        # 先获取所有可能的补齐
        all_completions = self.completer.get_completions(context)
        
        if not context.current_word:
            return all_completions
        
        # 计算模糊匹配分数
        partial = context.current_word.lower()
        scored_completions = []
        
        for completion in all_completions:
            text = completion.text.lower()
            score = self._calculate_fuzzy_score(partial, text)
            if score >= self.min_score:
                scored_completions.append((score, completion))
        
        # 按分数排序
        scored_completions.sort(reverse=True, key=lambda x: x[0])
        
        # 返回排序后的补齐
        return [completion for _, completion in scored_completions]
    
    def _calculate_fuzzy_score(self, partial: str, text: str) -> float:
        """计算模糊匹配分数"""
        if partial in text:
            # 包含完整字符串，分数较高
            return 0.9 + (0.1 * (1 - len(partial) / len(text)))
        
        # 计算字符匹配度
        matched_chars = 0
        partial_index = 0
        
        for char in text:
            if partial_index < len(partial) and char == partial[partial_index]:
                matched_chars += 1
                partial_index += 1
        
        if matched_chars == len(partial):
            # 所有字符按顺序匹配
            return 0.7 + (0.2 * (1 - len(partial) / len(text)))
        
        # 部分匹配
        return matched_chars / len(partial) * 0.6


class ChainedCompleter(CompleterBase):
    """链式补齐器 - 合并多个补齐器的结果"""
    
    def __init__(self, completers: List[CompleterBase]):
        self.completers = completers
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """合并所有补齐器的结果"""
        all_completions = []
        seen_texts = set()
        
        for completer in self.completers:
            completions = completer.get_completions(context)
            for completion in completions:
                # 去重
                if completion.text not in seen_texts:
                    seen_texts.add(completion.text)
                    all_completions.append(completion)
        
        return all_completions