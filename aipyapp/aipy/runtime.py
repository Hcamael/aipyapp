#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from functools import wraps

from term_image.image import from_file, from_url

from . import utils
from .plugin import event_bus
from .. import T
from ..exec import BaseRuntime

def restore_output(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

        try:
            return func(self, *args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
    return wrapper

class Runtime(BaseRuntime):
    def __init__(self, task):
        super().__init__(task.envs)
        self.gui = task.gui
        self.task = task
        self.console = task.console
        self._auto_install = True
        self._auto_getenv = True

    @restore_output
    def install_packages(self, *packages):
        self.console.print(f"\n⚠️ LLM {T('Request to install third-party packages')}: {packages}")
        ret = self.ensure_packages(*packages)
        self.console.print("\n✅" if ret else "\n❌")
        return ret
    
    @restore_output
    def get_env(self, name, default=None, *, desc=None):
        self.console.print(f"\n⚠️ LLM {T('Request to obtain environment variable {}, purpose', name)}: {desc}")
        try:
            value = self.envs[name][0]
            self.console.print(f"✅ {T('Environment variable {} exists, returned for code use', name)}")
        except KeyError:
            value = None
        return value or default
    
    def get_code_by_id(self, code_id):
        return self.task.code_blocks.get_code_by_id(code_id)