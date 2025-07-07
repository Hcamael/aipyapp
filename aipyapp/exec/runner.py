#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import traceback
from pathlib import Path
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..aipy.blocks import CodeBlock
    from ..aipy.runtime import Runtime

from loguru import logger

INIT_IMPORTS = """
import os
import re
import sys
import json
import time
import random
import traceback
import warnings
warnings.filterwarnings("ignore")
"""

def is_json_serializable(obj):
    try:
        json.dumps(obj, ensure_ascii=False, default=str)
        return True
    except (TypeError, OverflowError):
        return False

def diff_dicts(dict1, dict2):
    diff = {}
    for key, value in dict1.items():
        if key not in dict2:
            diff[key] = value
            continue

        try:
            if value != dict2[key]:
                diff[key] = value
        except Exception:
            pass
    return diff

class Runner():
    def __init__(self, runtime):
        self.runtime: 'Runtime' = runtime
        self.history = []
        self.log = logger.bind(src='runner')
        self._globals = {'aipyrun': runtime, '__name__': '__main__'}
        exec(INIT_IMPORTS, self._globals)

    def __repr__(self):
        return f"<Runner history={len(self.history)}>"
    
    @property
    def globals(self):
        return self._globals
    
    def _exec_python_block(self, block: 'CodeBlock') -> dict:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        sys.stdout, sys.stderr = captured_stdout, captured_stderr
        result = {}
        self.runtime.current_state.clear()
        gs = self._globals.copy()
        try:
            exec(block.code, gs)
        except (SystemExit, Exception) as e:
            result['errstr'] = str(e)
            result['traceback'] = traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        s = captured_stdout.getvalue().strip()
        if s: result['stdout'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'
        s = captured_stderr.getvalue().strip()
        if s: result['stderr'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'        

        if self.runtime.current_state:
            result['result'] = self.filter_result(self.runtime.current_state)

        return result

    def __call__(self, block):
        self.log.info(f'Exec: {block}')
        lang = block.get_lang()
        history = {}
        if lang == 'python':
            result = self._exec_python_block(block)
        elif lang == 'html':
            result = self._exec_html_block(block)
        else:
            result = {'stderr': f'Exec: Ignore unsupported block type: {lang}'}
        history['block_name'] = block.name
        history['result'] = result
        self.history.append(history)
        return result.copy()
        
    def _exec_html_block(self, block) -> dict:
        cwd = self.runtime.task.cwd
        path = cwd / Path(block.path)
        path.write_text(block.code, encoding='utf-8')
        self.runtime.upload_file(str(path))
        result = {'stdout': 'OK'}
        return result

    def filter_result(self, vars):
        if isinstance(vars, dict):
            for key in vars.keys():
                if key in self.runtime.envs:
                    vars[key] = '<masked>'
                else:
                    vars[key] = self.filter_result(vars[key])
        elif isinstance(vars, list):
            vars = [self.filter_result(v) for v in vars]
        else:
            vars = vars if is_json_serializable(vars) else '<filtered>'
        return vars
    