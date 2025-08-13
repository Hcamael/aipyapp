"""
命令系统配置类

定义 CommandManager 所需的配置和运行时上下文
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, model_validator

class CommandMode(Enum):
    """命令执行模式"""
    MAIN = "main"
    TASK = "task"

class CommandError(Exception):
    """Command error"""
    pass

@dataclass
class CommandManagerConfig:
    """
    CommandManager 静态配置
    
    包含不会在运行时改变的配置项
    """
    settings: Dict[str, Any]  # 应用设置
    builtin_command_dir: Optional[Path] = None  # 包内命令目录
    custom_command_dirs: List[Path] = field(default_factory=list)  # 自定义命令目录
    
@dataclass
class CommandContext:
    """
    运行时上下文
    
    包含会在运行时改变的状态和依赖
    """
    tm: Any                                 # TaskManager 实例
    task: Optional[Any]                     # 当前执行的任务
    console: Any                            # Rich Console 实例
    settings: Dict[str, Any]                # 应用设置
    mode: CommandMode = CommandMode.MAIN    # 当前模式
    
    def is_task_mode(self) -> bool:
        """是否在任务模式"""
        return self.mode == CommandMode.TASK
    
    def is_main_mode(self) -> bool:
        """是否在主模式"""
        return self.mode == CommandMode.MAIN
    
    def set_task_mode(self, task: Any):
        """切换到任务模式"""
        self.task = task
        self.mode = CommandMode.TASK
    
    def set_main_mode(self):
        """切换到主模式"""
        self.task = None
        self.mode = CommandMode.MAIN

class CommandResult(BaseModel):
    command: str
    subcommand: str | None
    args: dict[str, Any]
    result: Any 

class TaskModeResult(BaseModel):
    task: Any | None = None
    instruction: str | None = None
    title: str | None = None

    @model_validator(mode='after')
    def validate_task_or_instruction(self):
        if self.task is None and self.instruction is None:
            raise ValueError("task or instruction must be provided")
        return self