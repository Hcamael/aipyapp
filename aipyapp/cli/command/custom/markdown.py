import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, NamedTuple
import re
import io
from contextlib import redirect_stdout, redirect_stderr

from rich.markdown import Markdown
from jinja2 import Environment, BaseLoader, FileSystemLoader, ChoiceLoader, TemplateNotFound

from ..base import ParserCommand
from ..common import TaskModeResult, CommandMode, CommandContext

@dataclass
class CustomCommandConfig:
    """Configuration for a custom command"""
    name: str
    description: str = ""
    modes: List[CommandMode] = field(default_factory=lambda: [CommandMode.TASK])
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    subcommands: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    template_vars: Dict[str, Any] = field(default_factory=dict)
    local: bool|None = None  # 是否在本地下执行，即不发送给LLM

class CodeBlock(NamedTuple):
    """Represents a code block with its metadata"""
    language: str
    code: str
    start_pos: int
    end_pos: int

class RenderContext(NamedTuple):
    """Represents the context for rendering"""
    ctx: CommandContext
    args: argparse.Namespace
    subcommand: Optional[str] = None

class ParsedContent(NamedTuple):
    """Represents parsed content with separated markdown and code blocks"""
    parts: List[tuple]  # List of ('markdown', content) or ('code', CodeBlock) tuples
    num_code_blocks: int


class StringTemplateLoader(BaseLoader):
    """Simple template loader for string templates"""
    
    def __init__(self, template_string: str, main_template_name: str = '_main_'):
        self.template_string = template_string
        self.main_template_name = main_template_name
    
    def get_source(self, environment, template):
        if template == self.main_template_name:
            return self.template_string, None, lambda: True
        raise TemplateNotFound(template)


class CodeExecutor:
    """Unified code execution engine for both TASK and MAIN modes"""
    
    def __init__(self, render_ctx: RenderContext):
        self.render_ctx = render_ctx
    
    def execute_code_block(self, code_block: CodeBlock) -> Optional[str]:
        """Execute a code block and return output"""
        if code_block.language == 'python':
            return self._execute_python(code_block.code)
        elif code_block.language in ['bash', 'shell', 'exec']:
            return self._execute_shell(code_block.code)
        return None
    
    def _execute_python(self, code: str) -> Optional[str]:
        """Execute Python code and capture output"""
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            exec_globals = {
                'ctx': self.render_ctx.ctx,
                'args': self.render_ctx.args,
                'subcommand': self.render_ctx.subcommand,
                'tm': getattr(self.render_ctx.ctx, 'tm', None),
                'console': self.render_ctx.ctx.console,
                'print': self.render_ctx.ctx.console.print,
                '__name__': '__main__'
            }
            
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(code, exec_globals)
            
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()
            
            output = []
            if stdout_content.strip():
                output.append(stdout_content.strip())
            if stderr_content.strip():
                output.append(f"错误: {stderr_content.strip()}")
            
            return "\n".join(output) if output else None
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Python 执行错误: {e}"
    
    def _execute_shell(self, code: str) -> Optional[str]:
        """Execute shell code and capture output"""
        try:
            import subprocess
            result = subprocess.run(code, shell=True, capture_output=True, text=True)
            
            output = []
            if result.stdout.strip():
                output.append(result.stdout.strip())
            if result.stderr.strip():
                output.append(f"错误: {result.stderr.strip()}")
            
            return "\n".join(output) if output else None
            
        except Exception as e:
            return f"Shell 执行错误: {e}"


class ContentParser:
    """Unified content parser for extracting code blocks"""
    
    EXECUTABLE_PATTERN = re.compile(r'````(python|bash|shell|exec)\n(.*?)````', re.DOTALL | re.IGNORECASE)
    
    def parse_content(self, content: str) -> ParsedContent:
        """Parse content into markdown parts and code blocks"""
        parts = []
        last_end = 0
        
        num_code_blocks = 0
        for match in self.EXECUTABLE_PATTERN.finditer(content):
            # Add markdown before code block
            if match.start() > last_end:
                markdown_content = content[last_end:match.start()].strip()
                if markdown_content:
                    parts.append(('markdown', markdown_content))
            
            # Add code block
            code_block = CodeBlock(
                language=match.group(1).lower(),
                code=match.group(2).strip(),
                start_pos=match.start(),
                end_pos=match.end()
            )
            parts.append(('code', code_block))
            num_code_blocks += 1
            last_end = match.end()
        
        # Add remaining markdown after last code block
        if last_end < len(content):
            remaining_content = content[last_end:] if last_end else content
            remaining_content = remaining_content.strip()
            if remaining_content:
                parts.append(('markdown', remaining_content))
        
        return ParsedContent(parts=parts, num_code_blocks=num_code_blocks)
    
class MarkdownCommand(ParserCommand):
    """Custom command loaded from markdown file"""
    
    def __init__(self, config: CustomCommandConfig, content: str, file_path: Path, command_dir: Path):
        self.config = config
        self.content = content
        self.builtin = False
        self.file_path = file_path
        self.command_dir = command_dir
        self.relative_path = file_path.relative_to(command_dir)
        
        # Set command properties from config
        self.name = config.name
        self.description = config.description
        self.modes = config.modes
        super().__init__()
        
        # Template environment with include support
        self.template_env = self._create_template_environment(content, command_dir)
        self.template = self.template_env.get_template('_main_')
        
        # Unified content parser
        self.content_parser = ContentParser()
    
    def _create_template_environment(self, content: str, command_dir: Path) -> Environment:
        """创建支持文件包含的模板环境"""
        # 混合加载器：按优先级查找模板
        loaders = [
            StringTemplateLoader(content, '_main_'),  # 主模板
            FileSystemLoader(str(self.file_path.parent)),  # 当前模板目录
            FileSystemLoader(str(command_dir))  # 命令主目录（共享模板）
        ]
        return Environment(loader=ChoiceLoader(loaders))
    
    def add_arguments(self, parser):
        """Add arguments defined in the command configuration"""
        for arg_config in self.config.arguments:
            self._add_argument_from_config(parser, arg_config)
        
        # Add universal --test argument for all custom commands
        # Check if --test already exists to avoid conflicts
        existing_options = [action.option_strings for action in parser._actions 
                           if hasattr(action, 'option_strings')]
        existing_options_flat = [opt for opts in existing_options for opt in opts]
        
        if '--local' not in existing_options_flat:
            parser.add_argument(
                '--local', 
                action='store_true',
                help='本地模式：预览命令输出，不发送给LLM'
            )
    
    def add_subcommands(self, subparsers):
        """Add subcommands defined in the configuration"""
        for subcmd_name, subcmd_config in self.config.subcommands.items():
            subcmd_parser = subparsers.add_parser(
                subcmd_name,
                help=subcmd_config.get('description', '')
            )
            
            # Add arguments for subcommand
            for arg_config in subcmd_config.get('arguments', []):
                self._add_argument_from_config(subcmd_parser, arg_config)
    
    def _add_argument_from_config(self, parser, arg_config: Dict[str, Any]):
        """Add a single argument from configuration"""
        name = arg_config['name']
        arg_type = arg_config.get('type', 'str')
        required = arg_config.get('required', False)
        default = arg_config.get('default')
        help_text = arg_config.get('help', '')
        choices = arg_config.get('choices')
        
        kwargs = {'help': help_text}
        
        # Handle different argument types
        if arg_type == 'flag':
            kwargs['action'] = 'store_true'
        elif arg_type in ('str', 'int', 'float'):
            kwargs['type'] = eval(arg_type)
            if default is not None:
                kwargs['default'] = default
        elif arg_type == 'choice' and choices:
            kwargs['choices'] = choices
            if default is not None:
                kwargs['default'] = default
        
        # Add required flag for positional arguments
        if not name.startswith('-') and required and default is None:
            # For positional arguments, required is implicit
            pass
        elif name.startswith('-') and required:
            kwargs['required'] = True
        elif not name.startswith('-') and not required:
            kwargs['nargs'] = '?'
        
        parser.add_argument(name, **kwargs)
    
    
    def cmd(self, args, ctx):
        """Execute the main command"""
        return self._execute_with_content(args, ctx)
    
    def _execute_with_content(self, args, ctx, subcommand: Optional[str] = None):
        """Execute command by rendering template and processing content"""
        # Get subcommand from args if available
        if not subcommand:
            subcommand = getattr(args, 'subcommand', None)
        
        render_ctx = RenderContext(ctx=ctx, args=args, subcommand=subcommand)
        
        # Render template with arguments
        rendered_content = self._render_template(render_ctx)
        
        # Parse content once
        parsed_content = self.content_parser.parse_content(rendered_content)
        self.log.info(f"Num code blocks: {parsed_content.num_code_blocks}")

        # 渲染代码块
        final_content = self._render_code_block(parsed_content, render_ctx)
        
        # 检查是否是测试模式
        is_local_mode = getattr(args, 'local', False)
        if is_local_mode:
            # 本地模式：始终显示输出，不发送给LLM
            ctx.console.print("[yellow]🧪 本地模式 - 以下是命令输出：[/yellow]")
            ctx.console.print(Markdown(final_content))
            return True
        
        # 判断是否发送给LLM
        is_local_mode = self.config.local
        if is_local_mode is None:
            is_local_mode = False if ctx.task else True
        
        if not is_local_mode:
            if ctx.task:
                return ctx.task.run(final_content, title=self.description)
            else:
                return TaskModeResult(instruction=final_content, title=self.description)
            
        ctx.console.print(Markdown(final_content))
        return True
    
    def _render_code_block(self, parsed_content: ParsedContent, render_ctx: RenderContext) -> str:
        """Render code block"""
        if parsed_content.num_code_blocks == 0:
            return parsed_content.parts[0][1]
        
        result_parts = []
        executor = CodeExecutor(render_ctx)
        
        for part_type, content in parsed_content.parts:
            if part_type == 'markdown':
                result_parts.append(content)
            elif part_type == 'code':
                output = executor.execute_code_block(content)
                if output:
                    result_parts.append("```")
                    result_parts.append(output)
                    result_parts.append("```")

        return "\n".join(result_parts)
    
    def _render_template(self, render_ctx: RenderContext) -> str:
        """Render the command template with arguments"""
        # Build template variables
        template_vars = {}
        
        # Add argument values
        for key, value in vars(render_ctx.args).items():
            if key not in ('subcommand', 'raw_args'):
                template_vars[key] = value
        
        # Add config template variables
        template_vars.update(self.config.template_vars)
        
        # Add subcommand info
        if render_ctx.subcommand:
            template_vars['subcommand'] = render_ctx.subcommand
            
        # Add context object for main mode commands
        if render_ctx.ctx:
            template_vars['ctx'] = render_ctx.ctx
        
        try:
            return self.template.render(**template_vars)
        except Exception as e:
            if self.log:
                self.log.error(f"Template rendering error: {e}")
            return self.content
    