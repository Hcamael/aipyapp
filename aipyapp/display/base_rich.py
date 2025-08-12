#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025, Aipy.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.   

from .base import DisplayPlugin
from .. import T

class RichDisplayPlugin(DisplayPlugin):
    def save(self, path: str, clear: bool = False, code_format: str = None):
        """保存输出"""
        if self.console.record:
            self.console.save_html(path, clear=clear, code_format=code_format)

    # 新增：输入输出相关方法
    def print(self, message: str, style: str = None):
        """显示消息"""
        if style:
            self.console.print(message, style=style)
        else:
            self.console.print(message)
    
    def input(self, prompt: str) -> str:
        """获取用户输入"""
        return self.console.input(prompt)
    
    def confirm(self, prompt, default="n", auto=None):
        """确认操作"""
        if auto in (True, False):
            self.print(f"✅ {T('Auto confirm')}")
            return auto
        while True:
            response = self.input(prompt).strip().lower()
            if not response:
                response = default
            if response in ["y", "n"]:
                break
        return response == "y"
