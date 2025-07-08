#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import locale
import platform
import subprocess
from functools import wraps
from importlib.resources import read_text

from rich.panel import Panel

from .. import T, __respkg__

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

def confirm(console, prompt, default="n", auto=None):
    if auto in (True, False):
        console.print(f"✅ {T('Auto confirm')}")
        return auto
    while True:
        response = console.input(prompt).strip().lower()
        if not response:
            response = default
        if response in ["y", "n"]:
            break
    return response == "y"

def confirm_disclaimer(console):
    DISCLAIMER_TEXT = read_text(__respkg__, "DISCLAIMER.md")
    console.print()
    panel = Panel.fit(DISCLAIMER_TEXT, title="[red]免责声明", border_style="red", padding=(1, 2))
    console.print(panel)

    while True:
        console.print("\n[red]是否确认已阅读并接受以上免责声明？[/red](yes/no):", end=" ")
        response = input().strip().lower()
        if response in ("yes", "y"):
            console.print("[green]感谢确认，程序继续运行。[/green]")
            return True
        elif response in ("no", "n"):
            console.print("[red]您未接受免责声明，程序将退出。[/red]")
            return False
        else:
            console.print("[yellow]请输入 yes 或 no。[/yellow]")

def get_safe_filename(input_str, extension=".html", max_length=16):
    input_str = input_str.strip()
    safe_str = re.sub(r'[\\/:*?"<>|]', '', input_str).strip()
    if not safe_str:
        return None

    name = safe_str[:max_length]
    base_name = name
    filename = f"{base_name}{extension}" if extension else base_name
    counter = 1

    while os.path.exists(filename):
        filename = f"{base_name}_{counter}{extension}" if extension else f"{base_name}_{counter}"
        counter += 1

    return filename

def check_commands(commands):
    """
    检查多个命令是否存在，并获取其版本号。
    :param commands: dict，键为命令名，值为获取版本的参数（如 ["--version"]）
    :return: dict，例如 {"node": "v18.17.1", "bash": "5.1.16", ...}
    """
    result = {}

    for cmd, version_args in commands.items():
        path = shutil.which(cmd)
        if not path:
            result[cmd] = None
            continue

        try:
            proc = subprocess.run(
                [cmd] + version_args,
                capture_output=True,
                text=True,
                timeout=5
            )
            # 合并 stdout 和 stderr，然后提取类似 1.2.3 或 v1.2.3 的版本
            output = (proc.stdout or '') + (proc.stderr or '')
            version_match = re.search(r"\bv?\d+(\.\d+){1,2}\b", output)
            version = version_match.group(0) if version_match else output.strip()
            result[cmd] = version
        except Exception as e:
            result[cmd] = f"error: {e}"

    return result

COMMANDS = {}

def get_system_context(context):
    """ 获取操作系统和脚本语言执行程序信息 """
    global COMMANDS

    context['operating_system'] = {'type': platform.system(), 'platform': platform.platform(), 'locale': locale.getlocale()}

    if not COMMANDS:
        commands_to_check = {
            "node": ["--version"],
            "bash": ["--version"],
            "powershell": ["-Command", "$PSVersionTable.PSVersion.ToString()"],
            "osascript": ["-e", 'return "AppleScript OK"']
        }
        COMMANDS = check_commands(commands_to_check)
        COMMANDS['python'] = platform.python_version()
    context['command_versions'] = COMMANDS
