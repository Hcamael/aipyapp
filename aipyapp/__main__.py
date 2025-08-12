#!/usr/bin/env python
# coding: utf-8

import os
import sys

if "pythonw" in sys.executable.lower():
    sys.stdout = open(os.devnull, "w", encoding='utf-8')
    sys.stderr = open(os.devnull, "w", encoding='utf-8')

from loguru import logger

logger.remove()
from .i18n import set_lang, T
from .aipy import CONFIG_DIR, ConfigManager
logger.add(CONFIG_DIR / "aipyapp.log", format="{time:HH:mm:ss} | {level} | {message} | {extra}", level='INFO')

def parse_args():
    import argparse
    config_help_message = (
        f"Specify the configuration directory.\nDefaults to {CONFIG_DIR} if not provided."
    )

    parser = argparse.ArgumentParser(description="Python use - AIPython", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-r', '--run', type=str, help="Run aipy python code, need set JSON history File")
    parser.add_argument("-c", '--config-dir', default=CONFIG_DIR, type=str, help=config_help_message)
    parser.add_argument('--debug', default=False, action='store_true', help="Debug mode")

    modes = parser.add_mutually_exclusive_group(required=False)
    modes.add_argument('-u', '--update', default=False, action='store_true', help="Update aipyapp to latest version")
    modes.add_argument('-s', '--sync', default=False, action='store_true', help="Sync content from trustoken")
    modes.add_argument('-p', '--python', default=False, action='store_true', help="Python mode")
    modes.add_argument('-i', '--ipython', default=False, action='store_true', help="IPython mode")
    modes.add_argument('-g', '--gui', default=False, action='store_true', help="GUI mode")
    modes.add_argument('-e', '--exec', default=None, help="CMD mode - execute an instruction")
    modes.add_argument('-a', '--agent', default=False, action='store_true', help='Agent mode - HTTP API server for n8n integration')
    parser.add_argument('--port', type=int, default=8848, help="Port for agent mode HTTP server (default: 8848)")
    parser.add_argument('--host', default='127.0.0.1', help="Host for agent mode HTTP server (default: 127.0.0.1)")
    parser.add_argument('--style', default=None, help="Style of the display, e.g. 'classic' or 'modern'")
    parser.add_argument('--role', default=None, help="Role to use")
    parser.add_argument('--beta', action='store_true', help='Include beta versions in update')
    
    return parser.parse_args()

def ensure_pkg(pkg):
    try:
        if pkg == 'wxpython':
            import wx
        elif pkg == 'ipython':
            import IPython
        elif pkg == 'fastapi':
            import fastapi
        elif pkg == 'uvicorn':
            import uvicorn
    except ImportError:
        import subprocess
        print(f"Installing required package: {pkg}")
        cp = subprocess.run([sys.executable, "-m", "pip", "install", pkg])
        assert cp.returncode == 0

def handle_update(args):
    """处理 update 命令"""
    import subprocess
    from . import __version__
    
    package_name = 'aipyapp'
    print(f"当前版本: {__version__}")
    
    if args.beta:
        print(f"更新到最新版本 (包括测试版): {package_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--pre", package_name]
    else:
        print(f"更新到最新稳定版本: {package_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package_name]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("更新完成!")
        if result.stdout.strip():
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"更新失败: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"更新失败: {str(e)}")
        sys.exit(1)

def handle_sync(conf, args):
    """处理 sync 命令"""
    conf.fetch_config()

def init_settings(conf, args):
    settings = conf.get_config()
    lang = settings.get('lang')
    if lang: set_lang(lang)
    settings.gui = args.gui
    settings.debug = args.debug
    settings.config_dir = args.config_dir
    if args.role:
        settings['role'] = args.role.lower()
    if args.style:
        display_config = settings.setdefault('display', {})
        display_config['style'] = args.style
    if args.agent:
        settings['agent'] = {'port': args.port, 'host': args.host}

    #TODO: remove these lines
    if conf.check_config(gui=True) == 'TrustToken':
        from .config import LLMConfig
        llm_config = LLMConfig(CONFIG_DIR / "config")
        if llm_config.need_config():
            settings['llm_need_config'] = True
            if not args.gui:
                from .aipy.wizard import show_provider_config
                show_provider_config(llm_config)
                if llm_config.need_config():
                    print(f"❌ {T('LLM configuration required')}")
                    sys.exit(1)
        settings["llm"] = llm_config.config
        
    settings['config_manager'] = conf
    return settings

def get_aipy_main(args, settings):
    """根据参数获取对应的 aipy_main 函数"""
    if args.agent:
        ensure_pkg('fastapi')
        ensure_pkg('uvicorn')
        from .cli.cli_agent import main as aipy_main
    elif args.python:
        from .cli.cli_python import main as aipy_main
    elif args.ipython:
        ensure_pkg('ipython')
        from .cli.cli_ipython import main as aipy_main
    elif args.gui:
        settings['gui'] = True
        ensure_pkg('wxpython')
        from .gui.main import main as aipy_main
    else:
        if args.exec:
            settings['exec_cmd'] = args.exec
        from .cli.cli_task import main as aipy_main
    return aipy_main

def main():
    args = parse_args()
    
    # 处理 update 子命令
    if args.update:
        handle_update(args)
        return
    
    conf = ConfigManager(args.config_dir)
    if args.sync:
        handle_sync(conf, args)
        return
    
    settings = init_settings(conf, args)
    aipy_main = get_aipy_main(args, settings)
    aipy_main(settings)

def mainw():
    args = parse_args()
    ensure_pkg('wxpython')
    from .gui.main import main as aipy_main
    aipy_main(args)

if __name__ == '__main__':
    main()
