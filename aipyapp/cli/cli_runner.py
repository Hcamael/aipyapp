#!/usr/bin/env python3
# -*- coding=utf-8 -*-

import json
from rich.console import Console
from ..config import LLMConfig
from ..aipy.blocks import CodeBlock
from .. import T, set_lang, __version__
from ..aipy import TaskManager, ConfigManager, CONFIG_DIR

SYSTEM_PROMPT = """下面我会提供给你 AIPYAPP生成的多个连续的Python代码块，请帮我归纳总结成一份代码文件，并输出。
"""

class CliRunner:
    def __init__(self, task: 'Task', console: 'Console'):
        self.task = task
        self.console = console

    def run(self, jsonFile):
        try:
            with open(jsonFile) as f:
                jsonData = json.load(f)
        except Exception as e:
            self.console.print("[bold red]Error Json File")
            return
        if "blocks" not in jsonData:
            self.console.print("[bold red]Error Format File, not 'blocks' key.")
            return
        blocks = jsonData["blocks"]
        if not isinstance(blocks, list):
            self.console.print("[bold red]Error Format File, not list in 'blocks'.")
            return
        for block in blocks:
            block = CodeBlock(**block)
            result = self.task.runner(block)
            for key in result:
                if key == "stdout":
                    self.console.print(f"[green]{result[key]}")
                elif key == "stderr":
                    self.console.print(f"[red]{result[key]}")
    
    def run2(self, jsonFile):
        try:
            with open(jsonFile) as f:
                jsonData = json.load(f)
        except Exception as e:
            self.console.print("[bold red]Error Json File")
            return
        if "blocks" not in jsonData:
            self.console.print("[bold red]Error Format File, not 'blocks' key.")
            return
        blocks = jsonData["blocks"]
        if not isinstance(blocks, list):
            self.console.print("[bold red]Error Format File, not list in 'blocks'.")
            return
        code = ""
        n = 1
        for block in blocks:
            block = CodeBlock(**block)
            if block.lang == "python":
                code += f"# 代码块{n}\n```python\n{block.code}\n```\n"
                n += 1
        response = self.task.chat(code, system_prompt=SYSTEM_PROMPT)
        print(response)

def main(args):
    console = Console(record=True)
    console.print(f"[bold cyan]🚀 Python use - AIPython ({__version__}) [[green]https://aipy.app[/green]]")
    conf = ConfigManager(args.config_dir)
    settings = conf.get_config()
    lang = settings.get('lang')
    if lang: set_lang(lang)
    # llm_config = LLMConfig(CONFIG_DIR / "config")
    # if conf.check_config(gui=True) == 'TrustToken':
    #     if llm_config.need_config():
    #         console.print(f"[yellow]{T('Starting LLM Provider Configuration Wizard')}[/yellow]")
    #         try:
    #             config = config_llm(llm_config)
    #         except KeyboardInterrupt:
    #             console.print(f"[yellow]{T('User cancelled configuration')}[/yellow]")
    #             return
    #         if not config:
    #             return
    #     settings["llm"] = llm_config.config

    # if args.fetch_config:
    #     conf.fetch_config()
    #     return

    settings.gui = False
    settings.debug = args.debug
    
    try:
        tm = TaskManager(settings, console=console)
    except Exception as e:
        console.print_exception()
        return
   
    if not tm.client_manager:
        console.print(f"[bold red]{T('No available LLM, please check the configuration file')}")
        return
    task = tm.new_task()
    CliRunner(task, console).run(args.run)