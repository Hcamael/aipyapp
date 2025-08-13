"""补齐器基础架构"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, InitVar
from typing import List, Optional, Any, Callable, Dict
from prompt_toolkit.completion import Completion

@dataclass
class CompleteItem:
    name: str
    desc: str
    _options: dict[str, Any] = field(default_factory=dict, init=False)
    _kwargs: InitVar[Optional[Dict[str, Any]]] = None

    def __post_init__(self, _kwargs: Optional[Dict[str, Any]]):
        if _kwargs:
            self._options.update(_kwargs)

    def __getitem__(self, key):
        return self._options[key]

    def __setitem__(self, key, value):
        self._options[key] = value

    def __contains__(self, key):
        return key in self._options

    def get(self, key, default=None):
        return self._options.get(key, default)
    
@dataclass
class CompleterContext:
    """补齐上下文信息"""
    text: str  # 完整文本
    cursor_pos: int  # 光标位置
    words: List[str]  # 已解析的单词列表
    current_word: str  # 当前正在输入的单词
    word_before_cursor: str  # 光标前的文本
    
    @property
    def is_empty_position(self) -> bool:
        """是否在空位置（刚输入空格后）"""
        return self.word_before_cursor.endswith(' ')
    
    @property
    def current_word_start(self) -> int:
        """当前单词的起始位置"""
        if self.is_empty_position:
            return self.cursor_pos
        return self.cursor_pos - len(self.current_word)


class CompleterBase(ABC):
    """补齐器基类"""
    
    @abstractmethod
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """
        获取补齐建议
        
        Args:
            context: 补齐上下文
            
        Returns:
            补齐建议列表
        """
        pass
    
    def can_handle(self, context: CompleterContext) -> bool:
        """
        判断是否可以处理当前上下文
        
        默认返回 True，子类可以覆盖以实现条件判断
        """
        return True


class CompleterChain:
    """
    补齐器链，支持级联处理
    
    按顺序尝试每个补齐器，直到获得结果
    """
    
    def __init__(self):
        self.completers: List[CompleterBase] = []
    
    def add(self, completer: CompleterBase) -> 'CompleterChain':
        """添加补齐器到链中"""
        self.completers.append(completer)
        return self
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        """获取补齐建议"""
        for completer in self.completers:
            if completer.can_handle(context):
                completions = completer.get_completions(context)
                if completions:
                    return completions
        return []


class ConditionalCompleter(CompleterBase):
    """
    条件补齐器，根据条件决定是否处理
    """
    
    def __init__(self, completer: CompleterBase, condition: Callable[[CompleterContext], bool]):
        self.completer = completer
        self.condition = condition
    
    def can_handle(self, context: CompleterContext) -> bool:
        return self.condition(context)
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        if self.can_handle(context):
            return self.completer.get_completions(context)
        return []


class PrefixCompleter(CompleterBase):
    """
    前缀补齐器，只处理特定前缀的输入
    """
    
    def __init__(self, prefix: str, completer: CompleterBase):
        self.prefix = prefix
        self.completer = completer
    
    def can_handle(self, context: CompleterContext) -> bool:
        return context.word_before_cursor.startswith(self.prefix)
    
    def get_completions(self, context: CompleterContext) -> List[Completion]:
        if not self.can_handle(context):
            return []
        
        # 移除前缀后创建新的上下文
        text_without_prefix = context.word_before_cursor[len(self.prefix):]
        modified_context = CompleterContext(
            text=text_without_prefix,
            cursor_pos=len(text_without_prefix),
            words=context.words,
            current_word=context.current_word.lstrip(self.prefix) if context.current_word.startswith(self.prefix) else context.current_word,
            word_before_cursor=text_without_prefix
        )
        
        return self.completer.get_completions(modified_context)


def create_completion(text: str, start_position: int = 0, display: Optional[str] = None, 
                      display_meta: Optional[str] = None) -> Completion:
    """
    创建补齐项的辅助函数
    
    Args:
        text: 补齐文本
        start_position: 起始位置（负数表示从光标前多少个字符开始替换）
        display: 显示文本
        display_meta: 显示元信息
    """
    return Completion(
        text=text,
        start_position=start_position,
        display=display or text,
        display_meta=display_meta or ""
    )