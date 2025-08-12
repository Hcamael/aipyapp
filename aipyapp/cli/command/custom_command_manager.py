import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger

try:
    import jinja2
except ImportError:
    raise ImportError("Jinja2 is required for custom commands. Install with: pip install jinja2")

from .base import CommandMode


@dataclass
class CustomCommandConfig:
    """Configuration for a custom command"""
    name: str
    description: str = ""
    modes: List[CommandMode] = field(default_factory=lambda: [CommandMode.TASK])
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    subcommands: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    template_vars: Dict[str, Any] = field(default_factory=dict)
    task: bool|None = None  # 是否在MAIN模式下创建新任务


class CustomCommandManager:
    """Manager for custom markdown-based commands"""
    
    def __init__(self):
        self.command_dirs: set[Path] = set()
        self.commands: Dict[str, 'MarkdownCommand'] = {}
        self.log = logger.bind(src="CustomCommandManager")
        
    def add_command_dir(self, command_dir: str | Path):
        """Add a custom command directory"""
        self.command_dirs.add(Path(command_dir))
        self.log.info(f"Added custom command directory: {command_dir}")
    
    def scan_commands(self) -> List['MarkdownCommand']:
        """Scan the command directories for markdown commands"""
        commands = []
        
        for command_dir in self.command_dirs:
            if not command_dir.exists():
                # Create default directory if it doesn't exist
                if command_dir.name == "custom_commands":
                    self._ensure_default_command_dir(command_dir)
                else:
                    self.log.warning(f"Command directory does not exist: {command_dir}")
                    continue
        
            # Scan for .md files
            for md_file in command_dir.rglob("*.md"):
                try:
                    command = self._load_command_from_file(md_file)
                    if command:
                        commands.append(command)
                        self.commands[command.name] = command
                        self.log.info(f"Loaded custom command: {command.name} from {md_file.relative_to(command_dir)}")
                except Exception as e:
                    self.log.error(f"Failed to load command from {md_file}: {e}")
        
        if commands:
            self.log.info(f"Loaded {len(commands)} custom commands")
        return commands
    
    def _load_command_from_file(self, md_file: Path) -> Optional['MarkdownCommand']:
        """Load a command from a markdown file"""
        try:
            content = md_file.read_text(encoding='utf-8')
            frontmatter, body = self._parse_frontmatter(content)
            
            if frontmatter:
                # File has frontmatter, parse configuration from it
                config = self._parse_command_config(frontmatter, md_file.stem)
            else:
                # No frontmatter, use default configuration
                self.log.info(f"No frontmatter found in {md_file}, using default configuration")
                config = self._create_default_config(md_file.stem, content)
                body = content  # Use entire content as body
            
            # Import here to avoid circular imports
            from .markdown_command import MarkdownCommand
            return MarkdownCommand(config, body, md_file)
            
        except Exception as e:
            self.log.error(f"Error loading command from {md_file}: {e}")
            return None
    
    def _parse_frontmatter(self, content: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Parse YAML frontmatter from markdown content"""
        # Use regex to match YAML frontmatter pattern
        pattern = r'^\s*---\n(.*?)\n---\n?(.*)'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return None, content
        
        yaml_content = match.group(1)
        body_content = match.group(2)
        
        try:
            frontmatter = yaml.safe_load(yaml_content) if yaml_content.strip() else {}
            return frontmatter, body_content
        except yaml.YAMLError as e:
            self.log.error(f"Invalid YAML frontmatter: {e}")
            return None, content
    
    def _create_default_config(self, default_name: str, content: str = "") -> CustomCommandConfig:
        """Create default configuration for pure markdown files"""
        mode = CommandMode.TASK
        
        return CustomCommandConfig(
            name=default_name,
            description=f"Custom command: {default_name}",
            modes=[mode],
            arguments=[],
            subcommands={},
            template_vars={},
            task=True
        )
    
    def _parse_command_config(self, frontmatter: Dict[str, Any], default_name: str) -> CustomCommandConfig:
        """Parse command configuration from frontmatter"""
        config = CustomCommandConfig(
            name=frontmatter.get('name', default_name),
            description=frontmatter.get('description', ''),
            arguments=frontmatter.get('arguments', []),
            subcommands=frontmatter.get('subcommands', {}),
            template_vars=frontmatter.get('template_vars', {}),
            task=frontmatter.get('task')
        )
        
        # Parse modes
        mode_strings = frontmatter.get('modes', ['task'])
        config.modes = []
        for mode_str in mode_strings:
            try:
                mode = CommandMode[mode_str.upper()]
                config.modes.append(mode)
            except KeyError:
                self.log.warning(f"Invalid command mode: {mode_str}, using TASK as default")
                config.modes.append(CommandMode.TASK)
        
        return config
    
    def get_command(self, name: str) -> Optional['MarkdownCommand']:
        """Get a custom command by name"""
        return self.commands.get(name)
    
    def get_all_commands(self) -> List['MarkdownCommand']:
        """Get all loaded custom commands"""
        return list(self.commands.values())
    
    def reload_commands(self) -> List['MarkdownCommand']:
        """Reload all custom commands"""
        self.commands.clear()
        return self.scan_commands()
    
    def validate_command_name(self, name: str, existing_commands: List[str]) -> bool:
        """Validate that a command name doesn't conflict with existing commands"""
        if name in existing_commands:
            self.log.warning(f"Custom command '{name}' conflicts with existing command")
            return False
        return True