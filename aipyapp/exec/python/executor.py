#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import traceback
from io import StringIO

from loguru import logger

from .mod_obj import ObjectImporter
from .mod_dict import DictModuleImporter

INIT_IMPORTS = """
import os
import re
import sys
import json
import time
import random
import traceback
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

class PythonExecutor():
    name = 'python'

    def __init__(self, runtime):
        self.runtime = runtime
        self.log = logger.bind(src='PythonExecutor')
        self._globals = {'__name__': '__main__', 'input': self.runtime.input}
        self.block_importer = DictModuleImporter()
        self.runtime_importer = ObjectImporter({'runtime': runtime})
        exec(INIT_IMPORTS, self._globals)

    def __repr__(self):
        return "<PythonExecutor>"
    
    @property
    def globals(self):
        return self._globals
    
    def __call__(self, block):
        result = {}
        try:
            co = compile(block.code, block.abs_path or block.name, 'exec')
        except SyntaxError as e:
            result['errstr'] = f"Syntax error: {str(e)}"
            result['traceback'] = traceback.format_exc()
            return result

        runtime = self.runtime
        old_stdout, old_stderr = sys.stdout, sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        sys.stdout, sys.stderr = captured_stdout, captured_stderr
        gs = self._globals.copy()
        runtime.start_block(block)
        try:
            with self.block_importer, self.runtime_importer:
                exec(co, gs)
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

        vars = runtime.current_state
        if vars:
            if vars.get('success'):
                self.block_importer.add_module(block.name, co)
            result['__state__'] = self.filter_result(vars)

        return result

    def filter_result(self, vars):
        if isinstance(vars, dict):
            ret = {}
            for key in vars.keys():
                if key in self.runtime.envs:
                    ret[key] = '<masked>'
                else:
                    ret[key] = self.filter_result(vars[key])
        elif isinstance(vars, list):
            ret = [self.filter_result(v) for v in vars]
        else:
            ret = vars if is_json_serializable(vars) else '<filtered>'
        return ret
