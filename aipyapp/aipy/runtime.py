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
        ok = utils.confirm(self.console, f"💬 {T('If you agree, please enter')} 'y'> ", auto=self._auto_install)
        if ok:
            ret = self.ensure_packages(*packages)
            self.console.print("\n✅" if ret else "\n❌")
            return ret
        return False
    
    @restore_output
    def get_env(self, name, default=None, *, desc=None):
        self.console.print(f"\n⚠️ LLM {T('Request to obtain environment variable {}, purpose', name)}: {desc}")
        env = self.envs.get(name, None)
        if env:
            value = env[0]
            self.console.print(f"✅ {T('Environment variable {} exists, returned for code use', name)}")
        else:
            value = None
        return value or default
    
    def upload_file(self, file_path: str):
        '''让 aipy 把文件上传到服务器中。
        '''
        try:
            subprocess.run(
                ["scp", "-P2233", file_path, f"admin@x.x:/xxx/{file_path}"],
                capture_output=False,
                text=True,
                check=True
            )
            return "上传成功"
        except subprocess.CalledProcessError as e:
            return f"上传失败: {e.stderr}"
        except Exception as e:
            return f"上传异常: {str(e)}"
    
    # 非 CLI 交互无法使用 display 和 input 方法
    # @restore_output
    # def display(self, path=None, url=None):
    #     image = {'path': path, 'url': url}
    #     event_bus.broadcast('display', image)
    #     if not self.gui:
    #         image = from_file(path) if path else from_url(url)
    #         image.draw()

    # @restore_output
    # def input(self, prompt=''):
    #     return self.console.input(prompt)    
    
    def get_block_by_name(self, block_name):
        return self.task.code_blocks.get_block_by_name(block_name)