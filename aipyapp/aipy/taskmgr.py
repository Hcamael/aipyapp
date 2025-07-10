#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from collections import namedtuple

from loguru import logger

from .. import T
from .task import Task
from .plugin import PluginManager
from .llm import ClientManager
from .config import PLUGINS_DIR, CONFIG_DIR, get_tt_api_key
from .tips import TipsManager

class TaskManager:
    def __init__(self, settings, console):
        self.settings = settings
        self.console = console
        self.tasks: dict[str, Task] = {}
        self.envs = {}
        self.log = logger.bind(src='taskmgr')
        self.api_prompt = None
        self.config_files = settings._loaded_files
        self.plugin_manager = PluginManager(PLUGINS_DIR)
        self.plugin_manager.load_plugins()
        if settings.workdir:
            workdir = Path.cwd() / os.getenv('AIPY_WORKDIR', settings.workdir)
            workdir.mkdir(parents=True, exist_ok=True)
            os.chdir(workdir)
            self.cwd = workdir
        else:
            self.cwd = Path.cwd()
        self._init_environ()
        self.tt_api_key = get_tt_api_key(settings)
        self._init_api()
        self.client_manager = ClientManager(settings)
        self.tips_dir = Path(settings.get('config_dir', CONFIG_DIR)) / 'tips'
        self.tips_manager = TipsManager(self.tips_dir)
        self.tips_manager.load_tips()
        self.tips_manager.use(settings.get('role', 'aipy'))
        self.task: 'Task|None' = None

    @property
    def workdir(self) -> str:
        return str(self.cwd)

    def get_tasks(self) -> dict[str, Task]:
        return self.tasks

    def list_llms(self):
        return self.client_manager.to_records()
    
    def list_envs(self):
        EnvRecord = namedtuple('EnvRecord', ['Name', 'Description', 'Value'])
        rows = []
        for name, (value, desc) in self.envs.items():    
            rows.append(EnvRecord(name, desc, value[:32]))
        return rows
    
    def list_tasks(self):
        rows = []
        for task in self.tasks:
            rows.append(task)
        return rows
    
    def get_task_by_name(self, username: str) -> Task | None:
        if username in self.tasks:
            return self.tasks[username]
        return None

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
        # if self.tt_api_key:
        #     tt_aio_api = get_tt_aio_api(self.tt_api_key)
        #     api.update(tt_aio_api)

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

    def end_user_task(self, username: str):
        if username in self.tasks:
            task = self.tasks[username]
            task.done()
            del self.tasks[username]
            self.log.debug(f'{username} task ended and removed')
        else:
            self.log.warning(f'Task for {username} not found')

    def get_task_by_username(self, username: str) -> Task:
        if username in self.tasks:
            task = self.tasks[username]
            self.task = task
            self.log.debug(f'{username} get task')
            return task
        task = self.new_task(username)
        self.task = task
        return task

    def new_task(self, username: str) -> Task:
        task = Task(self, client=self.client_manager.Client())
        self.tasks[username] = task
        self.log.debug(f'{username} New task created')
        return task