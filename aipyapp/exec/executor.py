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
        