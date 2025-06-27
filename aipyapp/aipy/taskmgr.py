#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from collections import deque

from loguru import logger

from .. import T
from .task import Task
from .plugin import PluginManager
from .prompt import get_system_prompt
from .diagnose import Diagnose
from .llm import ClientManager
from .config import PLUGINS_DIR, TIPS_DIR, get_mcp, get_tt_api_key, get_tt_aio_api
from .tips import TipsManager

class TaskManager:
    MAX_TASKS = 16

    def __init__(self, settings, console, gui=False):
        self.settings = settings
        self.console = console
        self.tasks = deque(maxlen=self.MAX_TASKS)
        self.envs = {}
        self.gui = gui
        self.log = logger.bind(src='taskmgr')
        self.api_prompt = None
        # 加载插件
        self.plugins_dir = Path(settings.config_dir) / 'plugins'
        self.plugin_manager = PluginManager(self.plugins_dir)
        self.plugin_manager.load_plugins()
        # 设置工作目录
        if settings.workdir:
            workdir = Path.cwd() / settings.workdir
            workdir.mkdir(parents=True, exist_ok=True)
            self._cwd = workdir
        else:
            self._cwd = Path.cwd() / "work"
        # 初始化 mcp
        self.mcp = get_mcp(settings.get('_config_dir'))
        # 初始化环境变量
        self._init_environ()
        # 初始化tt_api_key
        self.tt_api_key = get_tt_api_key(settings)
        # 初始化 api
        self._init_api()
        # 初始化客户端管理
        self.client_manager = ClientManager(settings)
        # 初始化 tips
        self.tips_dir = Path(settings.config_dir) / 'tips'
        self.tips_manager = TipsManager(self.tips_dir)
        self.tips_manager.load_tips()

    @property
    def workdir(self):
        return str(self._cwd)

    def use(self, llm=None, role=None):
        if llm:
            ret = self.client_manager.use(llm)
            self.console.print(f"LLM: {'[green]Ok[/green]' if ret else '[red]Error[/red]'}")
        if role:
            ret = self.tips_manager.use(role)
            self.console.print(f"Role: {'[green]Ok[/green]' if ret else '[red]Error[/red]'}")

    def _init_environ(self):
        envs = self.settings.get('environ', {})
        for name, value in envs.items():
            os.environ[name] = value

    def _init_api(self):
        api = self.settings.get('api', {})

        # update tt aio api, for map and search
        if self.tt_api_key:
            tt_aio_api = get_tt_aio_api(self.tt_api_key)
            api.update(tt_aio_api)

        lines = []
        for api_name, api_conf in api.items():
            lines.append(f"## {api_name} API")
            desc = api_conf.get('desc')
            if desc:
                lines.append(f"### API {T('Description')}\n{desc}")

            envs = api_conf.get('env')
            if not envs:
                continue

            lines.append(f"### {T('Environment variable name and meaning')}")
            for name, (value, desc) in envs.items():
                value = value.strip()
                if not value:
                    continue
                lines.append(f"- {name}: {desc}")
                self.envs[name] = (value, desc)

        self.api_prompt = "\n".join(lines)


    def _update_mcp_prompt(self, prompt):
        """更新 MCP 工具提示信息"""
        mcp_tools = self.mcp.list_tools()
        if not mcp_tools:
            return prompt
        tools_json = json.dumps(mcp_tools, ensure_ascii=False)
        lines = [prompt]
        lines.append("""\n## MCP工具调用规则：
1. 如果需要调用MCP工具，请以 JSON 格式输出你的决策和调用参数，并且仅返回json，不输出其他内容。
2. 返回 JSON 格式如下：
{"action": "call_tool", "name": "tool_name", "arguments": {"arg_name": "arg_value", ...}}
3. 一次只能返回一个工具，即只能返回一个 JSON 代码块，不能有其它多余内容。
以下是你可用的工具，以 JSON 数组形式提供：
""")
        lines.append(f"```json\n{tools_json}\n```")
        # 更新系统提示
        return "\n".join(lines)

    def new_task(self):
        with_mcp = self.settings.get('mcp', {}).get('enable', True)
        system_prompt = get_system_prompt(self.tips_manager.current_tips, self.api_prompt)
        if self.mcp and with_mcp:
            self.log.info('Update MCP prompt')
            system_prompt = self._update_mcp_prompt(system_prompt)

        task = Task(self)
        task.client = self.client_manager.Client()
        task.system_prompt = system_prompt
        task.mcp = self.mcp if with_mcp else None
        self.tasks.append(task)
        self.log.info('New task created', task_id=task.task_id)
        return task