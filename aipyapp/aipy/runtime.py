#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
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
    
    def upload_file(self, file_path: str):
        '''让 aipy 把结果都输出到 html 中，然后上传到服务中。
        '''
        try:
            subprocess.run(
                ["scp", "-P2233", f"{file_path}", "xxx@xx.xx:/xxx/{file_path}"],
                capture_output=False,
                text=True,
                check=True
            )
            self.log.info(f"文件上传成功: {file_path}")
            return "上传成功"
        except subprocess.CalledProcessError as e:
            self.log.error(f"文件上传失败: {e.stderr}")
            return f"上传失败: {e.stderr}"
        except Exception as e:
            self.log.exception(f"文件上传异常: {e}")
            return f"上传异常: {str(e)}"
