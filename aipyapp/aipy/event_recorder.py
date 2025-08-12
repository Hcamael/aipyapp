#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .event_serializer import EventSerializer
from ..interface import Trackable

class EventRecorder(Trackable):
    """事件记录器 - 记录任务执行过程中的所有重要事件"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.events: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.log = logger.bind(src='event_recorder')
    
    def start_recording(self):
        """开始记录"""
        self.start_time = time.time()
        self.events.clear()
        self.record_event('recording_start', {'timestamp': self.start_time})
        self.log.info('Started event recording')
    
    def stop_recording(self):
        """停止记录"""
        if self.start_time:
            self.record_event('recording_end', {'timestamp': time.time()})
            self.log.info(f'Stopped event recording, total events: {len(self.events)}')
    
    def record_event(self, event_type: str, data: Dict[str, Any], timestamp: Optional[float] = None):
        """记录事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timestamp: 时间戳，为None时使用当前时间
        """
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = time.time()
        
        # 计算相对时间
        relative_time = timestamp - self.start_time if self.start_time else 0
        
        # 序列化对象参数
        
        serialized_data = EventSerializer.serialize_event_data(data.copy() if isinstance(data, dict) else data)
        
        event = {
            'type': event_type,
            'data': serialized_data,
            'timestamp': timestamp,
            'relative_time': relative_time,
            'datetime': datetime.fromtimestamp(timestamp).isoformat()
        }
        
        self.events.append(event)
        
        # 记录调试信息（简化版本，避免logger level检查）
        if len(self.events) % 100 == 0:  # 每100个事件记录一次调试信息
            self.log.debug(f'Recorded {len(self.events)} events, latest: {event_type} at {relative_time:.3f}s')
    
    
    def get_events(self) -> List[Dict[str, Any]]:
        """获取所有事件"""
        return self.events.copy()
    
    def get_events_for_replay(self) -> List[Dict[str, Any]]:
        """获取用于重放的事件（反序列化对象）"""
        return EventSerializer.deserialize_events(self.events)
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的事件"""
        return [event for event in self.events if event['type'] == event_type]
    
    def get_events_in_range(self, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """获取指定时间范围内的事件"""
        return [event for event in self.events 
                if start_time <= event['relative_time'] <= end_time]
    
    def clear_events(self):
        """清空所有事件"""
        self.events.clear()
        self.start_time = None
        self.log.info('Cleared all events')
    
    # Trackable接口实现
    def get_checkpoint(self) -> int:
        """获取当前检查点状态 - 返回事件数量"""
        return len(self.events)
    
    def restore_to_checkpoint(self, checkpoint: Optional[int]):
        """恢复到指定检查点"""
        if checkpoint is None:
            # 恢复到初始状态
            self.clear_events()
        else:
            # 恢复到指定事件数量
            if checkpoint < len(self.events):
                deleted_count = len(self.events) - checkpoint
                self.events = self.events[:checkpoint]
                self.log.info(f'Restored to checkpoint {checkpoint}, deleted {deleted_count} events')
    
    def get_state(self) -> Dict[str, Any]:
        """获取需要持久化的状态数据"""
        return {
            'enabled': self.enabled,
            'start_time': self.start_time,
            'events': self.events
        }
    
    def restore_state(self, state_data: Dict[str, Any]):
        """从状态数据恢复事件记录器"""
        self.enabled = state_data.get('enabled', True)
        self.start_time = state_data.get('start_time')
        self.events = state_data.get('events', [])
        self.log.info(f'Restored event recorder with {len(self.events)} events')
    
    def export_to_file(self, filepath: str):
        """导出事件到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'start_time': self.start_time,
                        'total_events': len(self.events),
                        'duration': self.events[-1]['relative_time'] if self.events else 0
                    },
                    'events': self.events
                }, f, indent=2, ensure_ascii=False)
            self.log.info(f'Exported {len(self.events)} events to {filepath}')
        except Exception as e:
            self.log.error(f'Failed to export events: {e}')
            raise
    
    def import_from_file(self, filepath: str):
        """从文件导入事件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.start_time = data.get('metadata', {}).get('start_time')
            self.events = data.get('events', [])
            self.log.info(f'Imported {len(self.events)} events from {filepath}')
        except Exception as e:
            self.log.error(f'Failed to import events: {e}')
            raise
    
    def get_summary(self) -> Dict[str, Any]:
        """获取事件摘要统计"""
        if not self.events:
            return {'total_events': 0, 'duration': 0, 'event_types': {}}
        
        # 统计事件类型
        event_types = {}
        for event in self.events:
            event_type = event['type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            'total_events': len(self.events),
            'duration': self.events[-1]['relative_time'] if self.events else 0,
            'start_time': self.start_time,
            'event_types': event_types
        }
    
    def __len__(self):
        """返回事件数量"""
        return len(self.events)
    
    def __bool__(self):
        """检查是否有事件"""
        return len(self.events) > 0