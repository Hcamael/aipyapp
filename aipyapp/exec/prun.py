#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" subprocess-based bash/powershell code execution """

import traceback
import subprocess
from typing import Any, Dict, Optional

from loguru import logger

class SubprocessExecutor:
    """使用 subprocess 执行代码块"""
    name = None
    command = None
    timeout = 30  # 默认超时时间为10秒

    def __init__(self, runtime=None):
        self.runtime = runtime
        self.log = logger.bind(src=f'{self.name}_executor')

    def get_cmd(self, block) -> Optional[str]:
        """获取执行命令"""
        path = block.abs_path
        if path:
            cmd = self.command.copy()
            cmd.append(str(path))
        else:
            cmd = None
        return cmd
    
    def __call__(self, block) -> Dict[str, Any]:
        """执行代码块"""
        cmd = self.get_cmd(block)
        if not cmd:
            return {'errstr': 'No file to execute'}

        self.log.info(f"Exec: {cmd}")

        try:
            cp = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            stdout = cp.stdout.strip() if cp.stdout else None
            stderr = cp.stderr.strip() if cp.stderr else None

            result = {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': cp.returncode
            }
        except subprocess.TimeoutExpired:
            result = {'errstr': f'Execution timed out after {self.timeout} seconds'}
        except Exception as e:
            result = {'errstr': str(e), 'traceback': str(traceback.format_exc())}

        return result
    
class BashExecutor(SubprocessExecutor):
    name = 'bash'
    command = ['bash']

class PowerShellExecutor(SubprocessExecutor):
    name = 'powershell'
    command = ['powershell', '-Command']

class AppleScriptExecutor(SubprocessExecutor):
    name = 'applescript'
    command = ['osascript']
    
class NodeExecutor(SubprocessExecutor):
    name = 'javascript'
    command = ['node']