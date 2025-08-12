#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
import time
import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from loguru import logger

from .taskmgr import TaskManager
from .task import Task

class AgentTask:
    """Agent任务封装"""
    
    def __init__(self, task_id: str, instruction: str, task: Task, display: Any):
        self.task_id = task_id
        self.instruction = instruction
        self.task = task
        self.display = display
        self.status = 'pending'
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error = None
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'task_id': self.task_id,
            'instruction': self.instruction,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'captured_data': self.display.get_captured_data() if self.display else None
        }

class AgentTaskManager(TaskManager):
    """Agent模式任务管理器"""
    
    def __init__(self, settings, /, display_manager=None):
        # 强制使用agent显示模式和headless设置
        super().__init__(settings, display_manager=display_manager)
        
        # Agent特有属性
        self.agent_tasks: Dict[str, AgentTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)  # 支持并发
        self.log = logger.bind(src='agent_taskmgr')
        
    async def submit_task(self, instruction: str, metadata: Dict[str, Any] = None) -> str:
        """提交新任务"""
        task_id = str(uuid.uuid4())
        
        try:
            # 创建任务
            task = super().new_task()
            
            # 获取Task内部的display对象（这个已经注册到事件系统）
            display = task.display
            
            # 确保display是DisplayAgent类型
            if display and hasattr(display, 'captured_data'):
                # 添加元数据
                if metadata:
                    display.captured_data['metadata'].update(metadata)
                # 清空之前可能的数据
                display.clear_captured_data()
                if metadata:
                    display.captured_data['metadata'].update(metadata)
            
            # 创建Agent任务封装
            agent_task = AgentTask(task_id, instruction, task, display)
            agent_task.status = 'pending'
            
            self.agent_tasks[task_id] = agent_task
            self.log.info(f"Task submitted: {task_id}")
            
            return task_id
            
        except Exception as e:
            self.log.error(f"Failed to submit task: {e}")
            raise
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """执行任务"""
        if task_id not in self.agent_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        agent_task = self.agent_tasks[task_id]
        if agent_task.status != 'pending':
            raise ValueError(f"Task {task_id} is not in pending status")
        
        agent_task.status = 'running'
        agent_task.started_at = datetime.now()
        
        try:
            # 在线程池中执行任务
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._run_task_sync,
                agent_task
            )
            
            agent_task.status = 'completed'
            agent_task.completed_at = datetime.now()
            
        except Exception as e:
            agent_task.status = 'error'
            agent_task.error = str(e)
            agent_task.completed_at = datetime.now()
            self.log.error(f"Task {task_id} failed: {e}")
            
        return agent_task.to_dict()
    
    def _run_task_sync(self, agent_task: AgentTask):
        """同步执行任务（在线程池中运行）"""
        try:
            # 执行任务
            agent_task.task.run(agent_task.instruction)
            
            # 确保任务完成
            agent_task.task.done()
            
        except Exception as e:
            # 捕获异常并记录到display中
            if hasattr(agent_task.display, 'on_exception'):
                from ..interface import Event
                event = Event('exception', msg=str(e), exception=e)
                agent_task.display.on_exception(event)
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id not in self.agent_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        return self.agent_tasks[task_id].to_dict()
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        if task_id not in self.agent_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        agent_task = self.agent_tasks[task_id]
        result = agent_task.to_dict()
        
        # 添加详细的执行结果
        if agent_task.status == 'completed':
            captured_data = agent_task.display.get_captured_data()
            result['output'] = {
                'messages': captured_data['messages'],
                'results': captured_data['results'],
                'errors': captured_data['errors'],
                'metadata': captured_data['metadata']
            }
        
        return result
    
    async def list_tasks(self) -> Dict[str, Any]:
        """列出所有任务"""
        tasks = {}
        for task_id, agent_task in self.agent_tasks.items():
            tasks[task_id] = {
                'task_id': task_id,
                'instruction': agent_task.instruction,
                'status': agent_task.status,
                'created_at': agent_task.created_at.isoformat(),
                'started_at': agent_task.started_at.isoformat() if agent_task.started_at else None,
                'completed_at': agent_task.completed_at.isoformat() if agent_task.completed_at else None,
            }
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.agent_tasks:
            return False
        
        agent_task = self.agent_tasks[task_id]
        if agent_task.status == 'running':
            # 尝试停止任务
            if hasattr(agent_task.task, 'stop'):
                agent_task.task.stop()
            agent_task.status = 'cancelled'
            agent_task.completed_at = datetime.now()
            return True
        
        return False
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理完成的任务"""
        current_time = datetime.now()
        to_remove = []
        
        for task_id, agent_task in self.agent_tasks.items():
            if agent_task.status in ['completed', 'error', 'cancelled']:
                if agent_task.completed_at:
                    age = (current_time - agent_task.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.agent_tasks[task_id]
            self.log.info(f"Cleaned up task: {task_id}")
        
        return len(to_remove)