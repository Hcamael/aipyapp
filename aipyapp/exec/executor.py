#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback

from loguru import logger

from .python import PythonRuntime, PythonExecutor
from .html import HtmlExecutor
from .prun import BashExecutor, PowerShellExecutor, AppleScriptExecutor, NodeExecutor

EXECUTORS = {executor.name: executor for executor in [
    PythonExecutor,
    HtmlExecutor,
    BashExecutor,
    PowerShellExecutor,
    AppleScriptExecutor,
    NodeExecutor
]}

class BlockExecutor():
    def __init__(self):
        self.history = []
        self.executors = {}
        self.runtimes = {}
        self.log = logger.bind(src='block_executor')

    def _set_runtime(self, lang, runtime):
        if lang not in self.runtimes:
            if lang not in EXECUTORS:
                self.log.warning(f'No executor found for {lang}')
            self.runtimes[lang] = runtime
            self.log.info(f'Registered runtime for {lang}: {runtime}')               
        else:
            self.log.warning(f'Runtime for {lang} already registered: {self.runtimes[lang]}')

    def set_python_runtime(self, runtime):
        assert isinstance(runtime, PythonRuntime), "Expected a PythonRuntime instance"
        self._set_runtime('python', runtime)

    def get_executor(self, block):
        lang = block.get_lang()
        if lang in self.executors:
            return self.executors[lang]
        
        if lang not in EXECUTORS:
            self.log.warning(f'No executor found for {lang}')
            return None 
        
        runtime = self.runtimes.get(lang)
        executor = EXECUTORS[lang](runtime)
        self.executors[lang] = executor
        self.log.info(f'Registered executor for {lang}: {executor}')
        return executor

    def __call__(self, block):
        self.log.info(f'Exec: {block}')
        history = {}
        executor = self.get_executor(block)
        if executor:
            try:
                result = executor(block)
            except Exception as e:
                result = {'errstr': str(e), 'traceback': traceback.format_exc()}
        else:
            result = {'stderr': f'Exec: Ignore unsupported block: {block}'}

        history['block'] = block
        history['result'] = result
        self.history.append(history)
        return result

    def get_state(self):
        """获取需要持久化的状态数据"""
        return self.history.copy()

    def restore_state(self, runner_data):
        """从运行历史数据恢复状态"""
        self.history.clear()
        if runner_data:
            self.history = runner_data.copy()
    
    def delete_range(self, start_index, end_index):
        """删除指定范围的执行历史"""
        if start_index < 0 or end_index > len(self.history) or start_index >= end_index:
            return
        
        # 删除指定范围的执行历史
        self.history = self.history[:start_index] + self.history[end_index:]
    
    def clear(self):
        self.history.clear()