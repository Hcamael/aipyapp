#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
from functools import wraps

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
        self.task = task
        self.console = task.console
        self._auto_install = True
        self._auto_getenv = True

    @restore_output
    def install_packages(self, *packages):
        '''### aipyrun.install_packages 方法
- 功能: 申请安装完成任务必需的额外模块
- 参数: 一个或多个 PyPi 包名，如：'httpx', 'requests>=2.25'
- 返回值:True 表示成功, False 表示失败

示例如下：
```python
if aipyrun.install_packages('httpx', 'requests>=2.25'):
    import httpx
```
        '''
        self.console.print(f"\n⚠️ LLM {T('Request to install third-party packages')}: {packages}")
        ok = utils.confirm(self.console, f"💬 {T('If you agree, please enter')} 'y'> ", auto=self._auto_install)
        if ok:
            ret = self.ensure_packages(*packages)
            self.console.print("\n✅" if ret else "\n❌")
            return ret
        return False
    
    @restore_output
    def get_env(self, name, default=None, *, desc=None):
        '''### aipyrun.get_env 方法
- 功能: 获取代码运行需要的环境变量，如 API-KEY 等。
- 定义: get_env(name, default=None, *, desc=None)
- 参数: 第一个参数为需要获取的环境变量名称，第二个参数为不存在时的默认返回值，第三个可选字符串参数简要描述需要的是什么。
- 返回值: 环境变量值，返回 None 或空字符串表示未找到。

示例如下：
```python
env_name = '环境变量名称'
env_value = aipyrun.get_env(env_name, "No env", desc='访问API服务需要')
if not env_value:
    print(f"Error: {env_name} is not set", file=sys.stderr)
else:
    print(f"{env_name} is available")
```
        '''
        self.console.print(f"\n⚠️ LLM {T('Request to obtain environment variable {}, purpose', name)}: {desc}")
        env = self.envs.get(name, None)
        if env:
            value = env[0]
            self.console.print(f"✅ {T('Environment variable {} exists, returned for code use', name)}")
        else:
            value = None
        return value or default
    
    def upload_file(self, file_path: str):
        '''### runtime.upload_file 方法
- 功能：由于用户无法接触服务器，所以生成的 HTML 文件需要上传到服务器上，该方法用来上传指定文件到服务器。
- 定义：upload_file(file_path: str)
- 参数：file_path为需要上传的文件路径。
- 返回值：上传成功后，返回HTML 文件的URL地址。

示例如下：
```python
filePath = "/app/file.html"
url = aipyrun.upload_file(filePath)
print(f"File uploaded to {url}")
```
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
    
    def get_block_by_name(self, block_name):
        '''### `aipyrun.get_block_by_name` 方法
- 功能: 获取指定 name 的最新版本的代码块对象
- 定义: `get_block_by_name(code_block_name)`
- 参数: `code_block_name` 为代码块的名称
- 返回值: 代码块对象，如果不存在则返回 None。

返回的代码块对象包含以下属性：
- `name`: 代码块名称
- `version`: 代码块的版本号
- `lang`: 代码块的编程语言
- `code`: 代码块的代码内容
- `path`: 代码块的文件路径（如果之前未指定则为None）

可以修改代码块的 `code` 属性来更新代码内容。
        '''
        return self.task.code_blocks.get_block_by_name(block_name)