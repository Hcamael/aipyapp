#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
对象序列化器 - 统一处理事件中的对象序列化和反序列化
"""

from typing import Any, Dict, List, Union


class EventSerializer:
    """对象序列化器 - 处理事件数据中的对象序列化和反序列化"""
    
    @staticmethod
    def serialize(data: Any) -> Any:
        """序列化数据中的对象
        
        Args:
            data: 待序列化的数据
            
        Returns:
            序列化后的数据
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = EventSerializer.serialize(value)
            return result
        elif isinstance(data, (list, tuple)):
            return [EventSerializer.serialize(item) for item in data]
        elif hasattr(data, 'to_dict'):
            # 对象有 to_dict 方法，使用它进行序列化
            return data.to_dict()
        else:
            # 基本类型直接返回
            return data
    
    @staticmethod
    def deserialize(data: Any) -> Any:
        """反序列化数据中的对象
        
        Args:
            data: 待反序列化的数据
            
        Returns:
            反序列化后的数据
        """
        if isinstance(data, dict):
            # 检查是否是序列化的对象
            if '__type__' in data:
                return EventSerializer._reconstruct_object(data)
            else:
                # 递归处理字典
                result = {}
                for key, value in data.items():
                    result[key] = EventSerializer.deserialize(value)
                return result
        elif isinstance(data, list):
            return [EventSerializer.deserialize(item) for item in data]
        else:
            # 基本类型直接返回
            return data
    
    @staticmethod
    def _reconstruct_object(data: Dict[str, Any]) -> Any:
        """根据类型信息重构对象
        
        Args:
            data: 包含类型信息的字典
            
        Returns:
            重构的对象，如果类型未知则返回原始数据
        """
        obj_type = data.get('__type__')
        
        if obj_type == 'ChatMessage':
            from ..llm.base import ChatMessage
            return ChatMessage.from_dict(data)
        elif obj_type == 'CodeBlock':
            from .blocks import CodeBlock
            return CodeBlock.from_dict(data)
        else:
            # 未知类型，返回原始数据
            return data
    
    @staticmethod
    def serialize_event_data(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """序列化事件数据
        
        Args:
            event_data: 事件数据字典
            
        Returns:
            序列化后的事件数据
        """
        if not isinstance(event_data, dict):
            return event_data
        
        return EventSerializer.serialize(event_data.copy())
    
    @staticmethod
    def deserialize_event_data(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化事件数据
        
        Args:
            event_data: 序列化的事件数据字典
            
        Returns:
            反序列化后的事件数据
        """
        if not isinstance(event_data, dict):
            return event_data
        
        return EventSerializer.deserialize(event_data.copy())
    
    @staticmethod
    def serialize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """序列化事件列表
        
        Args:
            events: 事件列表
            
        Returns:
            序列化后的事件列表
        """
        serialized_events = []
        for event in events:
            serialized_event = event.copy()
            if 'data' in serialized_event:
                serialized_event['data'] = EventSerializer.serialize_event_data(serialized_event['data'])
            serialized_events.append(serialized_event)
        return serialized_events
    
    @staticmethod
    def deserialize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """反序列化事件列表（用于重放）
        
        Args:
            events: 序列化的事件列表
            
        Returns:
            反序列化后的事件列表
        """
        deserialized_events = []
        for event in events:
            deserialized_event = event.copy()
            if 'data' in deserialized_event:
                deserialized_event['data'] = EventSerializer.deserialize_event_data(deserialized_event['data'])
            deserialized_events.append(deserialized_event)
        return deserialized_events
    
    @staticmethod
    def register_serializable_type(type_name: str, from_dict_func: callable):
        """注册新的可序列化类型
        
        Args:
            type_name: 类型名称（与 __type__ 字段对应）
            from_dict_func: 从字典重构对象的函数
        """
        # 这里可以扩展为动态注册机制
        # 目前硬编码在 _reconstruct_object 中
        pass