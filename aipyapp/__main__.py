#!/usr/bin/env python
# coding: utf-8

import os
import sys

if "pythonw" in sys.executable.lower():
    sys.stdout = open(os.devnull, "w", encoding='utf-8')
    sys.stderr = open(os.devnull, "w", encoding='utf-8')

from loguru import logger

logger.remove()
from .aipy.config import CONFIG_DIR
logger.add(CONFIG_DIR / "aipyapp.log", format="{time:HH:mm:ss} | {level} | {message} | {extra}", level='INFO')

def parse_args():
    import argparse
    config_help_message = (
        f"Specify the configuration directory.\nDefaults to {CONFIG_DIR} if not provided."
    )

    parser = argparse.ArgumentParser(description="Python use - AIPython", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", '--config-dir', type=str, help=config_help_message)
    parser.add_argument('-p', '--python', default=False, action='store_true', help="Python mode")
    parser.add_argument('-r', '--run', type=str, help="Run aipy python code, need set JSON history File")
    parser.add_argument('-i', '--ipython', default=False, action='store_true', help="IPython mode")
    parser.add_argument('-g', '--gui', default=False, action='store_true', help="GUI mode")
    parser.add_argument('--debug', default=False, action='store_true', help="Debug mode")
    parser.add_argument('-f', '--fetch-config', default=False, action='store_true', help="login to trustoken and fetch token config")
    parser.add_argument('cmd', nargs='?', default=None, help="Task to execute, e.g. 'Who are you?'")
    return parser.parse_args()

def ensure_pkg(pkg):
    try:
        import wx
    except:
        import subprocess

        cp = subprocess.run([sys.executable, "-m", "pip", "install", pkg])
        assert cp.returncode == 0

def aibot():
    args = parse_args()
    from .cli.cli_aibot import main as aipy_main
    aipy_main(args)

def mainw():
    args = parse_args()
    ensure_pkg('wxpython')
    from .gui.main import main as aipy_main
    aipy_main(args)

def main():
    args = parse_args()
    if args.python:
        from .cli.cli_python import main as aipy_main
    elif args.ipython:
        ensure_pkg('ipython')
        from .cli.cli_ipython import main as aipy_main
    elif args.gui:
        ensure_pkg('wxpython')
        from .gui.main import main as aipy_main
    elif args.run:
        from .cli.cli_runner import main as aipy_main
    else:
        from .cli.cli_task import main as aipy_main
    aipy_main(args)

if __name__ == '__main__':
    main()
