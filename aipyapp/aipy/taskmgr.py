#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from collections import deque, namedtuple
from dataclasses import dataclass
from typing import Optional, Any

from loguru import logger

from .task import Task
from .plugin import PluginManager
from .prompts import Prompts
from .diagnose import Diagnose
from .llm import ClientManager
from .config import PLUGINS_DIR, ROLES_DIR, get_mcp_config_file, get_tt_api_key
from .role import RoleManager
from .mcp_tool import MCPToolManager

@dataclass
class TaskContext:
    """任务上下文，包含创建任务所需的所有信息"""
    settings: Any
    cwd: Path
    plugin_manager: PluginManager
    display_manager: Any
    client_manager: ClientManager
    role_manager: RoleManager
    diagnose: Diagnose
    mcp: Optional[MCPToolManager]
    prompts: Prompts

class TaskManager:
    MAX_TASKS = 16

    def __init__(self, settings):
        # 核心配置
        self.settings = settings
        self.log = logger.bind(src='taskmgr')
        
        # 任务管理
        self.tasks = deque(maxlen=self.MAX_TASKS)
        self.current_task: Optional[Task] = None
        
        # 工作环境
        self._init_workenv()
        
        # 初始化各种管理器
        self._init_managers()
        
        # 创建任务上下文
        self.task_context = self._create_task_context()

    def _init_workenv(self):
        """初始化工作环境"""
        # 环境变量
        envs = self.settings.get('environ', {})
        for name, value in envs.items():
            os.environ[name] = value

        if self.settings.workdir:
            workdir = Path.cwd() / self.settings.workdir
            workdir.mkdir(parents=True, exist_ok=True)
            os.chdir(workdir)
            self.cwd = workdir
        else:
            self.cwd = Path.cwd()

    def set_display_manager(self, display_manager):
        self.display_manager = display_manager
        self.task_context.display_manager = display_manager

    def _init_managers(self):
        """初始化各种管理器"""
        # 插件管理器
        self.plugin_manager = PluginManager(PLUGINS_DIR)
        self.plugin_manager.load_plugins()

        self.display_manager = None

        # 诊断器
        self.diagnose = Diagnose.create(self.settings)
        
        # 客户端管理器
        self.client_manager = ClientManager(self.settings)
        
        # 角色管理器
        api_conf = self.settings.get('api', {})
        self.role_manager = RoleManager(ROLES_DIR, api_conf)
        self.role_manager.load_roles()
        self.role_manager.use(self.settings.get('role', 'aipy'))
        
        # MCP 工具管理器
        mcp_config_file = get_mcp_config_file(self.settings.get('_config_dir'))
        self.mcp = MCPToolManager(mcp_config_file, get_tt_api_key(self.settings))
        
        # 提示管理器
        self.prompts = Prompts()

    def _create_task_context(self) -> TaskContext:
        """创建任务上下文"""
        # 构建系统提示
        with_mcp = self.settings.get('mcp', {}).get('enable', True)
        
        return TaskContext(
            settings=self.settings,
            cwd=self.cwd,
            plugin_manager=self.plugin_manager,
            display_manager=self.display_manager,
            client_manager=self.client_manager,
            role_manager=self.role_manager,
            diagnose=self.diagnose,
            mcp=self.mcp if with_mcp else None,
            prompts=self.prompts
        )

    @property
    def workdir(self):
        return str(self.cwd)

    def get_tasks(self):
        return list(self.tasks)

    def list_llms(self):
        return self.client_manager.to_records()
    
    def list_envs(self):
        EnvRecord = namedtuple('EnvRecord', ['Name', 'Description', 'Value'])
        rows = []
        for name, (value, desc) in self.role_manager.current_role.env.items():    
            rows.append(EnvRecord(name, desc, value[:32]))
        return rows
    
    def list_tasks(self):
        rows = []
        for task in self.tasks:
            rows.append(task.to_record())
        return rows
    
    def get_task_by_id(self, task_id):
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_update(self, force=False):
        return self.diagnose.check_update(force)

    def use(self, llm=None, role=None, task=None):
        rets = {}
        if llm:
            ret = self.client_manager.use(llm)
            rets['llm'] = ret
        if role:
            ret = self.role_manager.use(role)
            rets['role'] = ret
        if task:
            task = self.get_task_by_id(task)
            rets['task'] = task
            self.current_task = task
        return rets

    def new_task(self):
        """创建新任务"""
        # 如果有当前任务，返回它
        if self.current_task:
            task = self.current_task
            self.current_task = None
            self.log.info('Reload task', task_id=task.task_id)
            return task

        # 创建新任务
        task = Task(self.task_context)
        self.tasks.append(task)
        self.log.info('New task created', task_id=task.task_id)
        return task