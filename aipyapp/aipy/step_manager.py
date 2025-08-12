#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dataclasses import dataclass
from collections import namedtuple
from typing import List, Dict, Any, Optional

from ..interface import Trackable

@dataclass
class Step:
    """步骤数据结构"""
    instruction: str
    round: int
    response: str
    timestamp: float
    checkpoints: Dict[str, Any]
    
    def get_summary(self) -> str:
        """获取步骤摘要"""
        return f"Step {self.round}: {self.instruction[:32]}..."

class StepManager:
    """步骤管理器 - 统一管理所有步骤和相关对象"""
    
    def __init__(self):
        self.steps: List[Step] = []
        self.trackables: Dict[str, Trackable] = {}
    
    def register_trackable(self, name: str, obj: Trackable):
        """注册可追踪对象"""
        self.trackables[name] = obj
    
    def create_checkpoint(self, instruction: str, round: int, response: str) -> Step:
        """创建新的检查点"""
        checkpoints = {}
        for name, trackable in self.trackables.items():
            checkpoints[name] = trackable.get_checkpoint()
        
        step = Step(
            instruction=instruction,
            round=round,
            response=response,
            timestamp=time.time(),
            checkpoints=checkpoints
        )
        self.steps.append(step)
        return step
    
    def delete_step(self, index: int):
        """删除指定步骤及之后的所有步骤"""
        if index < 0 or index >= len(self.steps):
            raise ValueError("Invalid step index")
        
        # 获取恢复目标检查点
        if index == 0:
            # 删除第一个步骤，恢复到初始状态
            for trackable in self.trackables.values():
                trackable.restore_to_checkpoint(None)
        else:
            # 恢复到前一个步骤的状态
            prev_step = self.steps[index - 1]
            for name, trackable in self.trackables.items():
                checkpoint = prev_step.checkpoints.get(name)
                trackable.restore_to_checkpoint(checkpoint)
        
        # 删除步骤及之后的所有步骤
        self.steps = self.steps[:index]
        return True
    
    def clear_all(self):
        """清空所有步骤"""
        for trackable in self.trackables.values():
            trackable.restore_to_checkpoint(None)
        self.steps.clear()
    
    def list_steps(self):
        """列出所有步骤"""
        StepRecord = namedtuple('StepRecord', ['Index', 'Instruction', 'Round', 'Ended'])
        return [StepRecord(index, step.instruction, step.round, datetime.fromtimestamp(step.timestamp).strftime('%Y-%m-%d %H:%M:%S')) 
                for index, step in enumerate(self.steps)]
    
    def get_step(self, index: int) -> Optional[Step]:
        """获取指定索引的步骤"""
        if index < 0 or index >= len(self.steps):
            return None
        return self.steps[index]
    
    def __len__(self):
        """返回步骤数量"""
        return len(self.steps)
    
    def get_state(self):
        """获取需要持久化的状态数据"""
        return [
            {
                'instruction': step.instruction,
                'round': step.round,
                'response': step.response,
                'timestamp': step.timestamp,
                'checkpoints': step.checkpoints
            }
            for step in self.steps
        ]
    
    def restore_state(self, state_data):
        """从状态数据恢复步骤管理器"""
        self.steps.clear()
        if not state_data:
            return
        
        for step_data in state_data:
            step = Step(
                instruction=step_data['instruction'],
                round=step_data['round'],
                response=step_data.get('response', ''),
                timestamp=step_data.get('timestamp', time.time()),
                checkpoints=step_data.get('checkpoints', {})
            )
            self.steps.append(step)