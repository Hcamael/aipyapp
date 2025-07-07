#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
from typing import Any
from abc import ABC, abstractmethod

from loguru import logger

class BaseRuntime(ABC):
    def __init__(self, envs=None):
        self.envs = envs or {}
        self.packages = set()
        self.current_state: dict[str, Any] = {}
        self.session: dict = {}
        self.log = logger.bind(src='runtime')

    def get_prompt(self) -> str:
        """
        返回该类中所有以aipyrun.开头详细docstring的成员函数的文档字符串拼接结果。
        """
        docs = []
        for attr_name in dir(self):
            if attr_name.startswith("__"):
                continue
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "__doc__") and attr.__doc__:
                doc = attr.__doc__.strip()
                if doc.startswith("###"):
                    docs.append(doc)
        return "\n\n".join(docs)

    def set_env(self, name, value, desc):
        '''设置换变量
        '''
        self.envs[name] = (value, desc)

    def set_result(self, **kwargs) -> None:
        '''### `aipyrun.set_result` 函数
- 定义: `set_result(**kwargs)`
- 参数: 
  - **kwargs: 状态键值对，类型可以为任意Python基本数据类型，如字符串/数字/列表/字典等。
- 用途: 设置当前代码块的运行结果值，作为当前代码块的执行结果反馈。
- 使用示例：
```python
aipyrun.set_result(success=False, reason="Error: 发生了错误") # 设置当前代码块的执行结果状态
aipyrun.set_result(success=True, data={"name": "John", "age": 30}) # 设置当前代码块的执行结果状态
```
        '''
        self.current_state.update(kwargs)
    
    def set_persistent_state(self, **kwargs) -> None:
        '''### `aipyrun.set_persistent_state` 函数
- 定义: `set_persistent_state(**kwargs)`
- 参数: 
  - **kwargs: 状态键值对，类型可以为任意Python基本数据类型，如字符串/数字/列表/字典等。
- 用途: 设置会话中持久化的状态值。
- 使用示例：
```python
aipyrun.set_persistent_state(data={"name": "John", "age": 30}) # 保存数据到会话中
```
        '''
        self.session.update(kwargs)

    def get_persistent_state(self, key: str) -> Any:
        '''### `aipyrun.get_persistent_state` 函数
- 类型: 函数。
- 参数: 
  - key: 状态键名
- 用途: 获取会话中持久化的状态值。不存在时返回 None。
- 使用示例：
```python
data = aipyrun.get_persistent_state("data")
```
        '''
        return self.session.get(key)

    def ensure_packages(self, *packages, upgrade=False, quiet=False):
        if not packages:
            return True

        packages = list(set(packages) - self.packages)
        if not packages:
            return True
        
        cmd = ["uv", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        if quiet:
            cmd.append("-q")
        cmd.extend(packages)

        try:
            subprocess.check_call(cmd)
            self.packages.update(packages)
            return True
        except subprocess.CalledProcessError:
            self.log.error("依赖安装失败: {}", " ".join(packages))
        
        return False

    def ensure_requirements(self, path="requirements.txt", **kwargs):
        with open(path) as f:
            reqs = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return self.ensure_packages(*reqs, **kwargs)
    
    @abstractmethod
    def install_packages(self, packages):
        pass

    @abstractmethod
    def get_env(self, name, default=None, *, desc=None):
        pass
    
    # @abstractmethod
    # def display(self, path=None, url=None):
    #     pass

    # @abstractmethod
    # def input(self, prompt=''):
    #     pass