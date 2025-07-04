#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import traceback
from io import StringIO
import webbrowser

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

__result__ = {}
__storage__ = {}

def set_result(**kwargs):
    global __result__
    __result__.update(kwargs)

def set_persistent_state(**kwargs):
    global __storage__
    __storage__.update(kwargs)

def get_persistent_state(key):
    global __storage__
    return __storage__.get(key)
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
        self.runtime = runtime
        self.history = []
        self.log = logger.bind(src='runner')
        self._globals = {'runtime': runtime, '__name__': '__main__', 'input': self.runtime.input}
        exec(INIT_IMPORTS, self._globals)

    def __repr__(self):
        return f"<Runner history={len(self.history)}, env={len(self.env)}>"
    
    @property
    def globals(self):
        return self._globals
    
    def _exec_python_block(self, block, params=None):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        sys.stdout, sys.stderr = captured_stdout, captured_stderr
        result = {}
        env = self.runtime.envs.copy()
        session = self._globals['__storage__'].copy()
        gs = self._globals.copy()
        gs['__result__'].clear()
        gs['__params__'] = params
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

        vars = gs.get('__result__')
        if vars:
            #self._globals['__retval__'] = vars
            result['result'] = self.filter_result(vars)

        history = {}
        diff = diff_dicts(env, self.runtime.envs)
        if diff:
            history['env'] = diff
        diff = diff_dicts(gs['__storage__'], session)
        if diff:
            history['session'] = diff

        return result, history

    def __call__(self, block):
        self.log.info(f'Exec: {block}')
        lang = block.get_lang()
        if lang == 'python':
            result, history = self._exec_python_block(block)
        elif lang == 'html':
            result, history = self._exec_html_block(block)
        else:
            result = {'stderr': f'Exec: Ignore unsupported block type: {lang}'}
            history = {}

        history['block_name'] = block.name
        history['result'] = result
        self.history.append(history)
        return result.copy()
        
    def _exec_html_block(self, block):
        abs_path = block.abs_path
        if abs_path:
            webbrowser.open(f'file://{abs_path}')
        result = {'stdout': 'OK'}
        return result, {}

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
    