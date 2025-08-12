#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum

from loguru import logger

from ..llm import ChatMessage
from ..interface import Trackable


class ContextStrategy(Enum):
    """上下文管理策略"""
    SLIDING_WINDOW = "sliding_window"      # 滑动窗口
    IMPORTANCE_FILTER = "importance_filter"  # 重要性过滤
    SUMMARY_COMPRESSION = "summary_compression"  # 摘要压缩
    HYBRID = "hybrid"                      # 混合策略


@dataclass
class ContextConfig:
    """上下文管理配置"""
    max_tokens: int = 100000               # 最大token数
    max_rounds: int = 10                   # 最大对话轮数
    auto_compress: bool = True             # 是否自动压缩
    strategy: ContextStrategy = ContextStrategy.HYBRID
    compression_ratio: float = 0.3         # 压缩比例
    importance_threshold: float = 0.5      # 重要性阈值
    summary_max_length: int = 200          # 摘要最大长度
    preserve_system: bool = True           # 是否保留系统消息
    preserve_recent: int = 3               # 保留最近几轮对话

    def set_strategy(self, strategy: str) -> Union[ContextStrategy, None]:
        try:
            strategy = ContextStrategy(strategy)
            self.strategy = strategy
        except ValueError:
            strategy = None
        return strategy

    @classmethod
    def from_dict(cls, data: dict) -> 'ContextConfig':
        obj = cls(**data)
        obj.set_strategy(data.get('strategy', 'hybrid'))
        return obj
    
    def to_dict(self) -> dict:
        return self.__dict__

class TokenCounter:
    """Token计数器"""
    
    def __init__(self):
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
    
    def add_message(self, message: ChatMessage):
        """添加消息的token统计"""
        if hasattr(message, 'usage') and message.usage:
            self.total_tokens += message.usage.get('total_tokens', 0)
            self.input_tokens += message.usage.get('input_tokens', 0)
            self.output_tokens += message.usage.get('output_tokens', 0)
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（简单估算：1token ≈ 4字符）"""
        return len(text) // 4
    
    def reset(self):
        """重置计数器"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0

class ChatHistory:
    def __init__(self):
        self.messages = []
        self._total_tokens = Counter()

    def __len__(self):
        return len(self.messages)
    
    def get_state(self):
        """获取需要持久化的状态数据"""
        return [msg.__dict__ for msg in self.messages]
    
    def restore_state(self, state_data):
        """从状态数据恢复历史状态"""
        self.messages.clear()
        self._total_tokens = Counter()
        
        if not state_data:
            return
        
        chat_data = state_data
        
        # 恢复消息
        if chat_data:
            for chat_item in chat_data:
                usage = Counter(chat_item.get('usage', {}))
                message = ChatMessage(
                    role=chat_item['role'],
                    content=chat_item['content'],
                    reason=chat_item.get('reason'),
                    usage=usage
                )
                self.add_message(message)
    
    def clear(self):
        self.messages.clear()
        self._total_tokens.clear()

    def delete_range(self, start_index, end_index):
        """删除指定范围的消息"""
        if start_index < 0 or end_index > len(self.messages) or start_index >= end_index:
            return
        
        # 删除指定范围的消息
        self.messages = self.messages[:start_index] + self.messages[end_index:]
        
        # 重新计算 token 统计
        self._total_tokens = Counter()
        for msg in self.messages:
            self._total_tokens += msg.usage
        
    def add(self, role, content):
        self.add_message(ChatMessage(role=role, content=content))

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self._total_tokens += message.usage
        
    def get_usage(self):
        return iter(row.usage for row in self.messages if row.role == "assistant")
    
    def get_summary(self):
        summary = {'time': 0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        summary.update(dict(self._total_tokens))
        summary['rounds'] = sum(1 for row in self.messages if row.role == "assistant")
        return summary

    def get_messages(self):
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
    
class MessageCompressor:
    """消息压缩器"""
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self.log = logger.bind(src='message_compressor')
    
    def compress_messages(self, messages: List[Dict[str, Any]], 
                         current_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """压缩消息列表"""
        if current_tokens <= self.config.max_tokens:
            return messages, current_tokens
        
        strategy = self.config.strategy
        if strategy == ContextStrategy.SLIDING_WINDOW:
            return self._sliding_window_compress(messages, current_tokens)
        elif strategy == ContextStrategy.IMPORTANCE_FILTER:
            return self._importance_filter_compress(messages, current_tokens)
        elif strategy == ContextStrategy.SUMMARY_COMPRESSION:
            return self._summary_compression_compress(messages, current_tokens)
        elif strategy == ContextStrategy.HYBRID:
            return self._hybrid_compress(messages, current_tokens)
        else:
            return messages, current_tokens
    
    def _sliding_window_compress(self, messages: List[Dict[str, Any]], 
                                current_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """滑动窗口压缩"""
        preserved_messages = []
        preserved_tokens = 0
        
        # 保留系统消息
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        for msg in system_messages:
            preserved_messages.append(msg)
            preserved_tokens += self._estimate_message_tokens(msg)
        
        # 保留最近的对话
        recent_messages = [msg for msg in messages if msg['role'] != 'system']
        max_recent = self.config.preserve_recent * 2  # 用户+助手消息
        
        for msg in recent_messages[-max_recent:]:
            msg_tokens = self._estimate_message_tokens(msg)
            if preserved_tokens + msg_tokens <= self.config.max_tokens:
                preserved_messages.append(msg)
                preserved_tokens += msg_tokens
            else:
                break
        
        self.log.info(f"Sliding window compression: {len(messages)} -> {len(preserved_messages)} messages")
        return preserved_messages, preserved_tokens
    
    def _importance_filter_compress(self, messages: List[Dict[str, Any]], 
                                   current_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """重要性过滤压缩"""
        # 计算消息重要性分数
        scored_messages = []
        for i, msg in enumerate(messages):
            score = self._calculate_importance_score(msg, i, len(messages))
            scored_messages.append((score, msg))
        
        # 按重要性排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        preserved_messages = []
        preserved_tokens = 0
        
        for score, msg in scored_messages:
            msg_tokens = self._estimate_message_tokens(msg)
            if preserved_tokens + msg_tokens <= self.config.max_tokens:
                preserved_messages.append(msg)
                preserved_tokens += msg_tokens
            else:
                break
        
        # 按原始顺序重新排序
        preserved_messages.sort(key=lambda x: messages.index(x))
        
        self.log.info(f"Importance filter compression: {len(messages)} -> {len(preserved_messages)} messages")
        return preserved_messages, preserved_tokens
    
    def _summary_compression_compress(self, messages: List[Dict[str, Any]], 
                                     current_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """摘要压缩"""
        preserved_messages = []
        preserved_tokens = 0
        
        # 保留系统消息
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        for msg in system_messages:
            preserved_messages.append(msg)
            preserved_tokens += self._estimate_message_tokens(msg)
        
        # 保留最近的对话
        recent_messages = [msg for msg in messages if msg['role'] != 'system']
        max_recent = self.config.preserve_recent * 2
        
        # 分割消息
        if len(recent_messages) > max_recent:
            old_messages = recent_messages[:-max_recent]
            new_messages = recent_messages[-max_recent:]
            
            # 创建摘要消息
            summary_content = self._create_summary(old_messages)
            summary_msg = {
                'role': 'system',
                'content': f"对话历史摘要：{summary_content}"
            }
            
            preserved_messages.append(summary_msg)
            preserved_tokens += self._estimate_message_tokens(summary_msg)
        
        # 添加新消息
        for msg in recent_messages[-max_recent:]:
            msg_tokens = self._estimate_message_tokens(msg)
            if preserved_tokens + msg_tokens <= self.config.max_tokens:
                preserved_messages.append(msg)
                preserved_tokens += msg_tokens
            else:
                break
        
        self.log.info(f"Summary compression: {len(messages)} -> {len(preserved_messages)} messages")
        return preserved_messages, preserved_tokens
    
    def _hybrid_compress(self, messages: List[Dict[str, Any]], 
                        current_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """混合压缩策略"""
        # 首先尝试滑动窗口
        compressed_messages, compressed_tokens = self._sliding_window_compress(messages, current_tokens)
        
        # 如果仍然超出限制，使用摘要压缩
        if compressed_tokens > self.config.max_tokens:
            compressed_messages, compressed_tokens = self._summary_compression_compress(messages, current_tokens)
        
        return compressed_messages, compressed_tokens
    
    def _calculate_importance_score(self, message: Dict[str, Any], index: int, total: int) -> float:
        """计算消息重要性分数"""
        score = 0.0
        
        # 基于角色评分
        role = message.get('role', '')
        if role == 'system':
            score += 1.0  # 系统消息最重要
        elif role == 'user':
            score += 0.8  # 用户消息次重要
        elif role == 'assistant':
            score += 0.6  # 助手消息一般重要
        
        # 基于位置评分（越新越重要）
        recency = (index + 1) / total
        score += recency * 0.4
        
        # 基于内容长度评分
        content = message.get('content', '')
        if isinstance(content, str):
            length_score = min(len(content) / 1000, 1.0)  # 标准化到0-1
            score += length_score * 0.2
        
        return score
    
    def _create_summary(self, messages: List[Dict[str, Any]]) -> str:
        """创建消息摘要"""
        summary_parts = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if isinstance(content, str):
                # 截取前100个字符作为摘要
                content_preview = content[:100] + ('...' if len(content) > 100 else '')
                summary_parts.append(f"{role}: {content_preview}")
        
        summary = " | ".join(summary_parts)
        return summary[:self.config.summary_max_length]
    
    def _estimate_message_tokens(self, message: Dict[str, Any]) -> int:
        """估算消息的token数量"""
        content = message.get('content', '')
        if isinstance(content, str):
            return len(content) // 4  # 简单估算
        elif isinstance(content, list):
            # 多模态内容
            total_length = 0
            for item in content:
                if item.get('type') == 'text':
                    total_length += len(item.get('text', ''))
            return total_length // 4
        return 0


class ContextManager(Trackable):
    """上下文管理器"""
    
    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self.token_counter = TokenCounter()
        self.compressor = MessageCompressor(self.config)
        self.log = logger.bind(src='context_manager')
        
        # 原始消息历史
        self.chat_history = ChatHistory()
        
        # 消息缓存
        self._messages_cache: List[Dict[str, Any]] = []
        self._cached_tokens = 0
        self._last_compression_time = 0
    
    def __len__(self):
        """返回消息数量，用于兼容旧接口"""
        return len(self.chat_history)
    
    def add(self, role, content):
        """添加简单消息，用于兼容旧接口"""
        message = ChatMessage(role=role, content=content)
        self.add_message(message)

    def add_message(self, message: ChatMessage):
        """添加消息到上下文"""
        # 添加到原始历史
        self.chat_history.add_message(message)
        
        # 转换为字典格式添加到缓存
        msg_dict = {
            'role': message.role,
            'content': message.content
        }
        
        # 更新token计数
        self.token_counter.add_message(message)
        
        # 添加到缓存
        self._messages_cache.append(msg_dict)
        self._cached_tokens += self.compressor._estimate_message_tokens(msg_dict)
        
        self.log.debug(f"Added message: {message.role}, tokens: {self._cached_tokens}")
    
    def get_messages(self, force_compress: bool = False) -> List[Dict[str, Any]]:
        """获取压缩后的消息列表"""
        current_time = time.time()
        
        # 检查是否需要压缩
        if force_compress or self.config.auto_compress:
            should_compress = (
                force_compress or
                self._cached_tokens > self.config.max_tokens or
                len(self._messages_cache) > self.config.max_rounds * 2 or
                (current_time - self._last_compression_time) > 300  # 5分钟强制压缩
            )
            
            if should_compress:
                self._compress_messages()
        
        return self._messages_cache.copy()
    
    def get_usage(self):
        """获取使用统计"""
        return self.chat_history.get_usage()
    
    def get_summary(self):
        """获取摘要统计"""
        return self.chat_history.get_summary()
    
    def json(self):
        """获取原始消息的JSON格式，用于序列化"""
        return self.chat_history.get_state()
    
    def _compress_messages(self):
        """压缩消息"""
        if not self._messages_cache:
            return
        
        original_count = len(self._messages_cache)
        original_tokens = self._cached_tokens
        
        # 执行压缩
        compressed_messages, compressed_tokens = self.compressor.compress_messages(
            self._messages_cache, self._cached_tokens
        )
        
        # 更新缓存
        self._messages_cache = compressed_messages
        self._cached_tokens = compressed_tokens
        self._last_compression_time = time.time()
        
        self.log.info(
            f"Context compressed: {original_count}->{len(compressed_messages)} messages, "
            f"{original_tokens}->{compressed_tokens} tokens"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        return {
            'message_count': len(self._messages_cache),
            'total_tokens': self._cached_tokens,
            'max_tokens': self.config.max_tokens,
            'compression_ratio': len(self._messages_cache) / max(len(self._messages_cache), 1),
            'last_compression': self._last_compression_time
        }
    
    def _clear_messages_cache(self):
        """清理消息缓存，只保留最初的两条消息和最后一条消息"""
        if not self._messages_cache:
            return
            
        # 如果消息数量小于等于3，不需要清理
        if len(self._messages_cache) <= 3:
            return
            
        # 保留最初的两条消息和最后一条消息
        first_two = self._messages_cache[:2]
        last_one = self._messages_cache[-1:]
        
        # 合并消息
        self._messages_cache = first_two + last_one
        
        # 重新计算 token 数量
        self._cached_tokens = sum(self.compressor._estimate_message_tokens(msg) for msg in self._messages_cache)
        self.log.info(f"Context cleaned: {len(self._messages_cache)} messages, {self._cached_tokens} tokens")

    def clear(self):
        """清空上下文"""
        #self.chat_history.clear()
        self._clear_messages_cache()
        #self._cached_tokens = 0
        self.token_counter.reset()
        self._last_compression_time = 0
        self.log.info("Context cleared")
    
    
    def _rebuild_cache(self):
        """重建消息缓存"""
        self._messages_cache.clear()
        self._cached_tokens = 0
        self.token_counter.reset()
        
        for message in self.chat_history.messages:
            msg_dict = {
                'role': message.role,
                'content': message.content
            }
            self._messages_cache.append(msg_dict)
            self._cached_tokens += self.compressor._estimate_message_tokens(msg_dict)
            self.token_counter.add_message(message)
    
    def update_config(self, config: ContextConfig):
        """更新配置"""
        self.config = config
        self.compressor = MessageCompressor(config)
        self.log.info(f"Context config updated: {config.strategy.value}")
    
    def get_state(self):
        """获取需要持久化的状态数据"""
        return {
            'config': {
                'max_tokens': self.config.max_tokens,
                'max_rounds': self.config.max_rounds,
                'auto_compress': self.config.auto_compress,
                'strategy': self.config.strategy.value,
                'compression_ratio': self.config.compression_ratio,
                'importance_threshold': self.config.importance_threshold,
                'summary_max_length': self.config.summary_max_length,
                'preserve_system': self.config.preserve_system,
                'preserve_recent': self.config.preserve_recent,
            },
            'chat_history': self.chat_history.get_state(),
            'messages_cache': self._messages_cache.copy(),
            'cached_tokens': self._cached_tokens,
            'token_counter': {
                'total_tokens': self.token_counter.total_tokens,
                'input_tokens': self.token_counter.input_tokens,
                'output_tokens': self.token_counter.output_tokens,
            },
            'last_compression_time': self._last_compression_time,
        }
    
    def restore_state(self, state_data):
        """从状态数据恢复上下文管理器"""
        if not state_data:
            return
        
        # 恢复配置
        if 'config' in state_data:
            config_data = state_data['config']
            self.config = ContextConfig(
                max_tokens=config_data.get('max_tokens', 100000),
                max_rounds=config_data.get('max_rounds', 10),
                auto_compress=config_data.get('auto_compress', False),
                strategy=ContextStrategy(config_data.get('strategy', 'hybrid')),
                compression_ratio=config_data.get('compression_ratio', 0.3),
                importance_threshold=config_data.get('importance_threshold', 0.5),
                summary_max_length=config_data.get('summary_max_length', 200),
                preserve_system=config_data.get('preserve_system', True),
                preserve_recent=config_data.get('preserve_recent', 3),
            )
            self.compressor = MessageCompressor(self.config)
        
        # 恢复原始聊天历史
        if 'chat_history' in state_data:
            self.chat_history.restore_state(state_data['chat_history'])
        
        # 恢复消息缓存
        self._messages_cache = state_data.get('messages_cache', []).copy()
        self._cached_tokens = state_data.get('cached_tokens', 0)
        
        # 恢复token计数器
        if 'token_counter' in state_data:
            token_data = state_data['token_counter']
            self.token_counter.total_tokens = token_data.get('total_tokens', 0)
            self.token_counter.input_tokens = token_data.get('input_tokens', 0)
            self.token_counter.output_tokens = token_data.get('output_tokens', 0)
        
        # 恢复其他状态
        self._last_compression_time = state_data.get('last_compression_time', 0)
        
        self.log.info(f"Context manager state restored: {len(self._messages_cache)} messages, {self._cached_tokens} tokens")
    
    # Trackable接口实现
    def get_checkpoint(self) -> int:
        """获取当前检查点状态 - 返回消息数量"""
        return len(self.chat_history)
    
    def restore_to_checkpoint(self, checkpoint: Optional[int]):
        """恢复到指定检查点"""
        if checkpoint is None:
            # 恢复到初始状态
            self.clear()
        else:
            # 恢复到指定消息数量
            if checkpoint < len(self.chat_history):
                # 删除checkpoint之后的消息
                self.chat_history.delete_range(checkpoint, len(self.chat_history))
                # 重建缓存
                self._rebuild_cache()