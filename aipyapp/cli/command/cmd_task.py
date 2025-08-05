from ... import T
from .base import Completable
from .base_parser import ParserCommand
from .utils import print_records
from pathlib import Path
import json

class TaskCommand(ParserCommand):
    name = 'task'
    description = T('Task operations')

    def add_subcommands(self, subparsers):
        subparsers.add_parser('list', help='List tasks')
        parser = subparsers.add_parser('use', help='Load an old task')
        parser.add_argument('tid', type=str, help='Task ID')
        parser = subparsers.add_parser('load', help='Load task from task.json file')
        parser.add_argument('path', type=str, help='Path to task.json file')

    def cmd_list(self, args, ctx):
        rows = ctx.tm.list_tasks()
        print_records(rows)

    def get_arg_values(self, arg, subcommand=None):
        if subcommand == 'use' and arg.name == 'tid':
            tasks = self.manager.tm.get_tasks()
            return [Completable(task.task_id, task.instruction[:32]) for task in tasks]
        return super().get_arg_values(arg, subcommand)
    
    def cmd_use(self, args, ctx):
        task = ctx.tm.get_task_by_id(args.tid)
        return task

    def cmd_load(self, args, ctx):
        """从 task.json 文件加载任务"""
        task_file = Path(args.path)
        if not task_file.exists():
            raise FileNotFoundError(f"Task file not found: {args.path}")
        if not task_file.name.endswith('.json'):
            raise ValueError("Task file must be a .json file")
        
        # 读取任务数据
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")
        
        # 将任务添加到任务管理器中
        task = ctx.tm.load_task(task_data)
        return task

    def cmd(self, args, ctx):
        self.cmd_list(args, ctx)