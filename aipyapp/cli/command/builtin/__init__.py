from .cmd_info import InfoCommand
from .cmd_help import HelpCommand
from .cmd_llm import LLMCommand
from .cmd_role import RoleCommand
from .cmd_task import TaskCommand
from .cmd_mcp import MCPCommand
from .cmd_display import DisplayCommand
from .cmd_context import ContextCommand
from .cmd_steps import StepsCommand
from .cmd_block import BlockCommand
from .cmd_plugin import PluginCommand
from .cmd_custom import CustomCommand

# 内置命令列表
BUILTIN_COMMANDS = [
    InfoCommand, LLMCommand, RoleCommand, DisplayCommand, PluginCommand, StepsCommand,
    BlockCommand, ContextCommand, TaskCommand, MCPCommand, HelpCommand, CustomCommand,
]