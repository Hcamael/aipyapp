#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, TYPE_CHECKING
from collections import OrderedDict

from loguru import logger

if TYPE_CHECKING:
    from .task import Task

# 任务版本常量
TASK_VERSION = 20250806

class TaskStateError(Exception):
    """任务状态异常"""
    pass

class TaskState:
    """任务状态管理器 - 封装任务状态的序列化、反序列化和文件操作"""
    
    def __init__(self, task: Optional['Task'] = None):
        self.log = logger.bind(src='task_state')
        
        # 任务基本信息
        self.version: int = TASK_VERSION
        self.task_id: Optional[str] = None
        self.instruction: Optional[str] = None
        self.start_time: Optional[float] = None
        self.done_time: Optional[float] = None
        
        # 组件状态
        self._component_states: Dict[str, Any] = {}
        
        if task:
            self.from_task(task)
    
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> 'TaskState':
        """从文件创建 TaskState 对象"""
        instance = cls()
        instance.load_from_file(path)
        return instance
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskState':
        """从字典创建 TaskState 对象"""
        instance = cls()
        instance._load_from_dict(data)
        return instance
    
    def from_task(self, task: 'Task') -> None:
        """从 Task 对象提取状态"""
        self.task_id = task.task_id
        self.instruction = task.instruction
        self.start_time = task.start_time
        self.done_time = task.done_time
        
        # 提取各组件状态
        self._component_states['steps'] = task.step_manager.get_state()
        self._component_states['context_manager'] = task.context_manager.get_state()
        self._component_states['runner'] = task.runner.get_state()
        self._component_states['blocks'] = task.code_blocks.get_state()
        
        # 提取事件记录（如果存在）
        if task.event_recorder:
            self._component_states['events'] = task.event_recorder.get_events()
        
        self.log.debug('Extracted state from task', task_id=self.task_id)
    
    def restore_to_task(self, task: 'Task') -> None:
        """恢复状态到 Task 对象"""
        # 验证版本兼容性
        if self.version != TASK_VERSION:
            raise TaskStateError(f'Task version mismatch: expected {TASK_VERSION}, got {self.version}')
        
        # 恢复任务基本信息
        task.task_id = self.task_id
        task.instruction = self.instruction
        task.start_time = self.start_time
        task.done_time = self.done_time
        
        # 恢复各组件状态
        if 'steps' in self._component_states:
            task.step_manager.restore_state(self._component_states['steps'])
        
        if 'context_manager' in self._component_states:
            task.context_manager.restore_state(self._component_states['context_manager'])
        
        if 'runner' in self._component_states:
            task.runner.restore_state(self._component_states['runner'])
        
        if 'blocks' in self._component_states:
            task.code_blocks.restore_state(self._component_states['blocks'])
        
        # 恢复事件记录器状态（如果存在）
        if 'events' in self._component_states and task.event_recorder:
            events_data = self._component_states['events']
            task.event_recorder.restore_state({'events': events_data, 'enabled': True})
        
        self.log.info('Restored state to task', task_id=self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        # 使用 OrderedDict 保持字段顺序
        data = OrderedDict()
        data['version'] = self.version
        data['task_id'] = self.task_id
        data['instruction'] = self.instruction
        data['start_time'] = int(self.start_time) if self.start_time else None
        data['done_time'] = int(self.done_time) if self.done_time else None
        
        # 添加组件状态
        for key, state in self._component_states.items():
            data[key] = state
        
        return data
    
    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典加载状态"""
        # 加载基本字段
        basic_fields = {'version', 'task_id', 'instruction', 'start_time', 'done_time'}
        self.version = data.get('version', TASK_VERSION)
        self.task_id = data.get('task_id')
        self.instruction = data.get('instruction')
        self.start_time = data.get('start_time')
        self.done_time = data.get('done_time')
        
        # 加载所有非基本字段作为组件状态
        for key, value in data.items():
            if key not in basic_fields:
                self._component_states[key] = value
    
    def save_to_file(self, path: Union[str, Path]) -> None:
        """保存到文件"""
        path = Path(path)
        
        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 更新完成时间
        if not self.done_time:
            self.done_time = time.time()
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4, default=str)
            self.log.info('Saved task state to file', path=str(path))
        except Exception as e:
            self.log.exception('Failed to save task state', path=str(path))
            raise TaskStateError(f'Failed to save task state: {e}') from e
    
    def load_from_file(self, path: Union[str, Path]) -> None:
        """从文件加载状态"""
        path = Path(path)
        self.validate_file(path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._load_from_dict(data)
            self.log.info('Loaded task state from file', path=str(path), task_id=self.task_id)
        except json.JSONDecodeError as e:
            raise TaskStateError(f'Invalid JSON file: {e}') from e
        except Exception as e:
            self.log.exception('Failed to load task state', path=str(path))
            raise TaskStateError(f'Failed to load task state: {e}') from e
    
    def validate_file(self, path: Union[str, Path]) -> None:
        """验证文件格式和存在性"""
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
        
        if not path.name.endswith('.json'):
            raise ValueError("Task file must be a .json file")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
    
    def get_component_state(self, name: str) -> Any:
        """获取组件状态"""
        return self._component_states.get(name)
    
    def set_component_state(self, name: str, state: Any) -> None:
        """设置组件状态"""
        self._component_states[name] = state
    
    def has_component_state(self, name: str) -> bool:
        """检查是否有指定组件的状态"""
        return name in self._component_states
    
    def get_summary(self) -> Dict[str, Any]:
        """获取状态摘要信息"""
        return {
            'version': self.version,
            'task_id': self.task_id,
            'instruction': self.instruction[:50] + '...' if self.instruction and len(self.instruction) > 50 else self.instruction,
            'start_time': self.start_time,
            'done_time': self.done_time,
            'components': list(self._component_states.keys())
        }
    
    def __repr__(self):
        return f"<TaskState task_id={self.task_id}, version={self.version}, components={list(self._component_states.keys())}>"