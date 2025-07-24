#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" 实现兼容 aipy/runtime.py 的接口，支持模块级方法调用 """
import os

def install_packages(*packages):
    print(f"[install_packages] 需要安装的包: {packages}")
    return True

def get_env(name, default=None, *, desc=None):
    return os.environ.get(name, default)

def display(path=None, url=None):
    if path:
        print(f"[display] 显示本地文件: {path}")
    elif url:
        print(f"[display] 显示网络资源: {url}")
    else:
        print("[display] 未提供 path 或 url")

def input(prompt=''):
    return __builtins__.input(prompt)

def get_block_by_name(block_name):
    pass

