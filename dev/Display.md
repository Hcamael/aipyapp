# 显示插件系统

AiPy 的显示插件系统负责处理任务执行过程中的各种输出和交互，提供不同的显示风格来满足不同用户的需求。显示插件通过事件机制监听任务执行过程，并以不同的方式呈现信息。

## 系统架构

### 核心组件

1. **DisplayProtocol**: 显示插件协议，定义统一的接口规范
2. **DisplayPlugin**: 显示插件基类，实现基础功能
3. **RichDisplayPlugin**: 基于 Rich 的显示插件基类  
4. **DisplayManager**: 显示管理器，负责插件的注册、切换和管理
5. **LiveDisplay**: 实时显示组件，处理流式内容的动态更新
6. **样式插件**: 具体的显示风格实现

### 目录结构

```
aipyapp/
├── display/                 # 显示系统核心
│   ├── __init__.py         # 模块导出
│   ├── base.py             # 基类和协议定义
│   ├── base_rich.py        # Rich 基类实现
│   ├── manager.py          # 显示管理器
│   ├── live_display.py     # 实时显示组件
│   └── themes.py           # 主题定义
└── plugins/                 # 显示插件实现
    ├── p_style_classic.py  # 经典风格
    ├── p_style_modern.py   # 现代风格
    ├── p_style_minimal.py  # 简约风格
    ├── p_style_agent.py    # Agent 模式
    └── p_style_null.py     # 空显示风格
```

## 显示管理器

### DisplayManager 类

显示管理器负责管理所有显示插件，提供统一的接口：

```python
from aipyapp.display import DisplayManager
from rich.console import Console

# 创建显示管理器
display_config = {
    'style': 'classic',    # 显示风格
    'theme': 'default',    # 主题（default, dark, light, mono）
    'record': True,        # 是否记录输出
    'quiet': False         # 是否安静模式
}

console = Console()
display_manager = DisplayManager(
    display_config, 
    console=console, 
    record=True, 
    quiet=False
)

# 创建显示插件实例
plugin = display_manager.create_display_plugin()

# 切换显示风格
display_manager.set_style('modern')

# 获取可用风格列表
styles = display_manager.get_available_styles()

# 获取可用主题列表
themes = display_manager.get_available_themes()
```

### 主要方法

- `create_display_plugin()`: 创建当前显示插件实例
- `set_style(style_name)`: 设置显示风格
- `get_available_styles()`: 获取可用的显示风格列表
- `get_available_themes()`: 获取可用的主题列表
- `register_plugin(plugin_class, name=None)`: 注册新的显示插件
- `get_plugin_info()`: 获取所有插件的信息

## 显示插件架构

### DisplayProtocol 协议

所有显示插件必须遵循 `DisplayProtocol` 协议，定义了必须实现的方法：

```python
from typing import Protocol
from aipyapp import Event

class DisplayProtocol(Protocol):
    """显示效果插件协议"""
    def save(self, path: str, clear: bool = False, code_format: str = None): ...
    def print(self, message: str, style: str = None): ...
    def input(self, prompt: str) -> str: ...
    def confirm(self, prompt, default="n", auto=None): ...
    
    # 事件处理方法
    def on_task_start(self, event: Event): ...
    def on_task_end(self, event: Event): ...
    def on_exception(self, event: Event): ...
    # ... 其他事件方法
```

### DisplayPlugin 基类

```python
from aipyapp.display import DisplayPlugin
from aipyapp import Plugin, PluginType
from rich.console import Console

class MyDisplayPlugin(DisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        # 初始化代码
    
    @classmethod
    def get_type(cls) -> PluginType:
        return PluginType.DISPLAY
    
    def init(self):
        """初始化显示效果插件"""
        pass
    
    # 事件处理方法
    def on_task_start(self, event):
        """任务开始事件处理"""
        pass
```

### RichDisplayPlugin 基类

对于使用 Rich 库的显示插件，建议继承自 `RichDisplayPlugin`：

```python
from aipyapp.display import RichDisplayPlugin

class MyRichDisplayPlugin(RichDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
    
    def save(self, path: str, clear: bool = False, code_format: str = None):
        """保存为 HTML 文件"""
        if self.console.record:
            self.console.save_html(path, clear=clear, code_format=code_format)
```

### 核心方法

- `save(path, clear=False, code_format=None)`: 保存输出为 HTML
- `print(message, style=None)`: 显示消息  
- `input(prompt)`: 获取用户输入
- `confirm(prompt, default="n", auto=None)`: 确认操作
- `init()`: 初始化插件

## 现有显示风格

### 1. Classic (经典风格)

**文件**: `aipyapp/plugins/p_style_classic.py`  
**类名**: `DisplayClassic`

**特点**：
- 传统的命令行界面风格
- 使用丰富的 Rich 组件（Panel、Table、Syntax、Rule 等）
- 详细的执行信息和统计表格
- 支持实时流式显示（LiveDisplay）
- 显示完整的解析结果和执行统计

**适用场景**：
- 需要详细执行信息的用户
- 喜欢传统命令行界面的用户
- 调试和开发环境

**示例输出**：
```
🚀 Task processing started: 用户指令
➡️ Sending message to LLM
🔄 Streaming started
🔸 Completed receiving message (gpt-4):
┌─ LLM 回复 ──────────────────────────────────────┐
│ 这里是 LLM 的回复内容...                        │
└─────────────────────────────────────────────────┘
➔ Message parse result: 1个代码块 | 执行: main
⚡ Start executing code block: main
☑️ Execution result: main
{
  "output": "执行结果",
  "stdout": "标准输出"
}
```

### 2. Modern (现代风格)

**文件**: `aipyapp/plugins/p_style_modern.py`  
**类名**: `DisplayModern`

**特点**：
- 现代化的界面设计，使用面板布局
- 智能的内容解析和显示
- 支持代码块自动识别和语法高亮
- 结构化的结果展示
- 详细的异常处理和错误显示

**适用场景**：
- 喜欢现代界面的用户
- 需要清晰代码显示的用户
- 日常使用场景

**示例输出**：
```
┌─ 🚀 任务开始 ──────────────────────────────────┐
│ 用户任务描述                                   │
└────────────────────────────────────────────────┘
📤 Sending message to LLM...
📥 Streaming started...
┌─ 📝 Code (python) ─────────────────────────────┐
│   1 │ def hello():                             │
│   2 │     print("Hello, World!")               │
└────────────────────────────────────────────────┘
⏳ Executing...
┌─ ✅ 执行成功 ──────────────────────────────────┐
│ 📤 Output: Hello, World!                      │
└────────────────────────────────────────────────┘
```

### 3. Minimal (简约风格)

**文件**: `aipyapp/plugins/p_style_minimal.py`  
**类名**: `DisplayMinimal`

**特点**：
- 极简的输出风格
- 使用 Status 组件显示进度
- 只显示核心信息和简要结果
- 错误时显示简要错误信息

**适用场景**：
- 喜欢简洁输出的用户
- 自动化脚本环境
- 快速执行场景

**示例输出**：
```
→ 用户任务
⟳ Sending...
📥 Receiving response... (15 lines)
📝 Found: main
▶ Executing: main (python)
✓ Success
  Hello, World!
• 任务执行完成
```

### 4. Agent (Agent模式)

**文件**: `aipyapp/plugins/p_style_agent.py`  
**类名**: `DisplayAgent`

**特点**：
- 专为 API 模式设计
- 捕获所有输出数据而不显示
- 自动确认操作，不支持交互输入
- 提供结构化的数据输出

**适用场景**：
- API 集成
- 自动化服务
- 数据收集和分析

**数据结构**：
```json
{
  "messages": [
    {"type": "task_start", "content": {...}, "timestamp": "..."},
    {"type": "exec_result", "content": {...}, "timestamp": "..."}
  ],
  "results": [...],
  "errors": [...],
  "status": "completed",
  "start_time": "...",
  "end_time": "..."
}
```

### 5. Null (空显示风格)

**文件**: `aipyapp/plugins/p_style_null.py`  
**类名**: `DisplayNull`

**特点**：
- 不实现任何显示逻辑
- 完全静默模式
- 最小资源占用

**适用场景**：
- 纯静默执行
- 性能敏感环境
- 测试环境

## 事件系统

显示插件通过事件系统监听任务执行过程，支持以下事件：

### 任务相关事件
- `on_task_start(event)`: 任务开始，包含指令信息
- `on_task_end(event)`: 任务结束，包含结果路径
- `on_round_start(event)`: 回合开始，包含当前指令
- `on_round_end(event)`: 回合结束，包含统计和总结信息

### 执行相关事件  
- `on_exec(event)`: 代码执行开始，包含代码块信息
- `on_exec_result(event)`: 代码执行结果，包含输出和错误信息
- `on_call_function(event)`: 函数调用事件，包含函数名
- `on_mcp_call(event)`: MCP 工具调用开始
- `on_mcp_result(event)`: MCP 工具调用结果

### LLM 响应相关事件
- `on_query_start(event)`: 查询开始，发送消息到 LLM
- `on_response_complete(event)`: LLM 响应完成，包含完整回复
- `on_stream_start(event)`: 流式响应开始
- `on_stream_end(event)`: 流式响应结束  
- `on_stream(event)`: 流式响应数据，包含行内容和思考状态
- `on_parse_reply(event)`: 消息解析结果，包含代码块和工具调用信息

### 运行时事件
- `on_runtime_message(event)`: Runtime 消息处理
- `on_runtime_input(event)`: Runtime 输入处理
- `on_show_image(event)`: 图片显示处理

### 其他事件
- `on_exception(event)`: 异常处理，包含错误信息和堆栈
- `on_upload_result(event)`: 云端上传结果处理

### 事件数据结构

每个事件都包含一个 `Event` 对象，通过 `event.data` 访问事件数据：

```python
def on_task_start(self, event):
    data = event.data
    instruction = data.get('instruction', '')
    task_id = data.get('task_id', None)
    # 处理任务开始事件

def on_exec_result(self, event):
    data = event.data  
    result = data.get('result', {})
    block = data.get('block')
    # 处理执行结果
    
def on_stream(self, event):
    response = event.data
    lines = response.get('lines', [])
    reason = response.get('reason', False)  # 是否为思考内容
    # 处理流式响应
```

## 主题系统

AiPy 显示系统支持多种颜色主题，定义在 `aipyapp/display/themes.py` 中：

### 可用主题

1. **default**: 默认主题，适合大多数终端
2. **dark**: 深色主题，针对深色背景优化
3. **light**: 浅色主题，针对浅色背景优化  
4. **mono**: 单色主题，只使用基本颜色，兼容性最好

### 主题配置

```python
from aipyapp.display.themes import get_theme, THEMES

# 获取主题
theme = get_theme('dark')
console = Console(theme=theme)

# 查看所有可用主题
print(THEMES.keys())  # ['default', 'dark', 'light', 'mono']
```

### 主题样式定义

每个主题包含以下样式：
- **基础颜色**: info, warning, error, success
- **面板和边框**: panel.border, panel.title
- **代码相关**: code, syntax.keyword, syntax.string, syntax.number, syntax.comment
- **任务状态**: task.running, task.success, task.error
- **表格**: table.header, table.cell

## 创建自定义显示风格

### 1. 创建插件文件

在 `aipyapp/plugins/` 目录下创建新的插件文件，例如 `p_style_custom.py`：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

from aipyapp.display import RichDisplayPlugin
from aipyapp import T

class DisplayCustom(RichDisplayPlugin):
    """Custom display style - 自定义显示风格"""
    name = "custom"
    version = "1.0.0" 
    description = "Custom display style"
    author = "Your Name"
    
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        # 初始化自定义属性
        self.custom_buffer = []
    
    def init(self):
        """初始化插件"""
        # 执行初始化逻辑
        pass
    
    def on_task_start(self, event):
        """任务开始事件处理"""
        data = event.data
        instruction = data.get('instruction', '')
        
        # 自定义显示逻辑
        title = Text("🚀 任务开始", style="bold blue")
        content = Text(instruction, style="white")
        panel = Panel(content, title=title, border_style="blue")
        self.console.print(panel)
    
    def on_exec(self, event):
        """代码执行事件处理"""
        block = event.data.get('block')
        if block and hasattr(block, 'code'):
            # 使用语法高亮显示代码
            syntax = Syntax(block.code, block.lang, line_numbers=True, word_wrap=True)
            panel = Panel(syntax, title=f"💻 执行代码: {block.name}", border_style="green")
            self.console.print(panel)
    
    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result', {})
        
        if 'traceback' in result:
            # 错误显示
            error_syntax = Syntax(result['traceback'], 'python', line_numbers=True)
            panel = Panel(error_syntax, title="❌ 执行错误", border_style="red")
            self.console.print(panel)
        else:
            # 成功显示
            output = result.get('output', '')
            if output:
                panel = Panel(Text(output, style="green"), title="✅ 执行成功", border_style="green")
                self.console.print(panel)
    
    def on_response_complete(self, event):
        """LLM 响应完成事件处理"""
        data = event.data
        msg = data.get('msg')
        llm = data.get('llm', 'LLM')
        
        if msg and hasattr(msg, 'content'):
            # 使用 Markdown 渲染响应内容
            from rich.markdown import Markdown
            content = Markdown(msg.content)
            panel = Panel(content, title=f"🤖 {llm} 回复", border_style="cyan")
            self.console.print(panel)
    
    def on_exception(self, event):
        """异常事件处理"""
        data = event.data
        msg = data.get('msg', '')
        exception = data.get('exception')
        
        error_text = Text(f"{msg}: {exception}", style="red")
        panel = Panel(error_text, title="💥 异常", border_style="red") 
        self.console.print(panel)
```

### 2. 注册新插件

显示插件会自动通过插件系统注册，只需确保：

1. 插件文件以 `p_style_` 开头
2. 插件类继承自 `DisplayPlugin` 或 `RichDisplayPlugin`  
3. 插件类定义了 `name` 属性
4. 插件类实现了 `get_type()` 方法返回 `PluginType.DISPLAY`

插件系统会自动发现并注册插件。

## 实时显示组件

### LiveDisplay 类

`LiveDisplay` 提供实时流式内容的显示功能，专门负责显示 LLM 的流式响应：

```python
from aipyapp.display import LiveDisplay

class MyDisplayPlugin(RichDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.live_display = None
    
    def on_stream_start(self, event):
        """流式开始事件处理"""
        if not self.quiet:
            self.live_display = LiveDisplay(quiet=self.quiet)
            self.live_display.__enter__()
    
    def on_stream(self, event):
        """流式响应事件处理"""
        response = event.data
        lines = response.get('lines', [])
        reason = response.get('reason', False)  # 是否为思考内容
        
        if self.live_display:
            self.live_display.update_display(lines, reason=reason)
    
    def on_stream_end(self, event):
        """流式结束事件处理"""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None
```

### LiveDisplay 特性

- **实时更新**: 显示流式响应的实时内容
- **思考状态**: 自动处理 `<think>` 和 `</think>` 标记
- **行数限制**: 最多显示 10 行内容，保持界面整洁  
- **上下文管理器**: 支持 `with` 语句自动管理生命周期

## 使用示例

### 1. 基本使用

```python
from aipyapp.display import DisplayManager
from rich.console import Console

# 创建显示配置
display_config = {
    'style': 'classic',
    'theme': 'default', 
    'record': True,
    'quiet': False
}

# 创建显示管理器
console = Console()
display_manager = DisplayManager(display_config, console=console, record=True, quiet=False)

# 创建显示插件实例
plugin = display_manager.create_display_plugin()

# 使用插件
plugin.print("Hello, World!", style="green")
user_input = plugin.input("请输入内容: ")
confirmed = plugin.confirm("是否继续?", default="y")
```

### 2. 切换显示风格和主题

```python
# 切换到现代风格
display_manager.set_style('modern')
plugin = display_manager.create_display_plugin()

# 获取可用风格
styles = display_manager.get_available_styles()
print(f"可用风格: {styles}")  # ['classic', 'modern', 'minimal', 'agent', 'null']

# 获取可用主题
themes = display_manager.get_available_themes() 
print(f"可用主题: {themes}")  # ['default', 'dark', 'light', 'mono']

# 使用不同主题创建管理器
dark_config = {'style': 'classic', 'theme': 'dark', 'record': True, 'quiet': False}
dark_manager = DisplayManager(dark_config, console=console)
```

### 3. 保存输出

```python
# 保存为 HTML 文件
plugin.save("output.html", clear=True, code_format="github")

# 注意：只有启用 record=True 的插件才能保存 HTML
```

### 4. Agent 模式使用

```python
# Agent 模式用于 API 集成
agent_config = {'style': 'agent', 'theme': 'default', 'record': False, 'quiet': True}
agent_manager = DisplayManager(agent_config, console=console)
agent_plugin = agent_manager.create_display_plugin()

# 获取捕获的数据
data = agent_plugin.get_captured_data()
print(data['messages'])  # 所有捕获的消息
print(data['results'])   # 执行结果
print(data['errors'])    # 错误信息

# 清空捕获数据
agent_plugin.clear_captured_data()
```

## 最佳实践

### 1. 事件处理
- 只实现需要的事件方法，不需要实现所有协议方法
- 使用 `event.data` 获取事件数据
- 正确处理异常情况，避免插件崩溃影响整体系统
- 对于可能不存在的数据使用 `.get()` 方法

```python
def on_exec_result(self, event):
    data = event.data
    result = data.get('result', {})  # 安全获取
    block = data.get('block')
    
    if not result:
        return  # 优雅处理空结果
```

### 2. 样式设计
- 保持一致的视觉风格和颜色方案
- 使用合适的 Unicode 符号和 emoji
- 考虑不同终端的兼容性，提供降级方案
- 遵循主题系统，使用定义好的样式名称

### 3. 性能优化
- 避免在事件处理中进行耗时操作
- 对于频繁的 `on_stream` 事件，避免复杂计算
- 合理使用缓存和缓冲区
- 及时清理资源，特别是 `LiveDisplay` 对象

### 4. 用户体验
- 提供清晰的状态指示和进度反馈
- 正确支持 `quiet` 模式
- 提供有用的错误信息和异常处理
- 对于交互式操作，提供合理的默认值

### 5. 插件规范
- 继承自 `RichDisplayPlugin` 而不是直接继承 `DisplayPlugin`
- 正确设置插件元数据（name、version、description、author）
- 实现 `init()` 方法进行初始化
- 遵循插件命名规范：文件以 `p_style_` 开头

## 调试和测试

### 1. 调试模式

```python
import os
from aipyapp.display import RichDisplayPlugin

class MyDisplayPlugin(RichDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.debug = os.getenv('AIPY_DEBUG_DISPLAY', False)
    
    def on_task_start(self, event):
        if self.debug:
            self.console.print(f"[DEBUG] Task start: {event.data}", style="dim yellow")
        # 正常处理逻辑
```

### 2. 测试插件

```python
# 测试插件文件
if __name__ == '__main__':
    from rich.console import Console
    from aipyapp import Event
    
    console = Console()
    plugin = MyDisplayPlugin(console)
    plugin.init()
    
    # 测试各种事件
    events = [
        Event('task_start', {'instruction': 'test task'}),
        Event('exec', {'block': type('Block', (), {'name': 'test', 'code': 'print("hello")', 'lang': 'python'})}),
        Event('exec_result', {'result': {'output': 'hello'}, 'block': None})
    ]
    
    for event in events:
        handler = getattr(plugin, f'on_{event.type}', None)
        if handler:
            handler(event)
```

### 3. 集成测试

```python
# 完整的显示管理器测试
def test_display_system():
    from aipyapp.display import DisplayManager
    
    config = {'style': 'custom', 'theme': 'default', 'record': True, 'quiet': False}
    manager = DisplayManager(config, console=Console())
    
    # 测试插件注册
    manager.register_plugin(MyDisplayPlugin, 'custom')
    
    # 测试插件创建
    plugin = manager.create_display_plugin()
    assert plugin is not None
    
    # 测试基本功能
    plugin.print("Test message")
    plugin.save("test_output.html")
    
    print("✅ Display system test passed")

if __name__ == '__main__':
    test_display_system()
```

---

## 总结

AiPy 的显示插件系统提供了灵活而强大的显示定制能力：

1. **多样化风格**: 从详细的 Classic 到简约的 Minimal，满足不同需求
2. **主题支持**: 4 种内置主题适配不同终端环境  
3. **事件驱动**: 完整的事件系统覆盖任务执行的各个阶段
4. **易于扩展**: 简单的插件开发接口，自动注册机制
5. **实时显示**: LiveDisplay 组件支持流式内容的实时更新

通过合理使用显示插件系统，可以为用户提供优秀的交互体验。

如需了解更多：
- 事件系统详情请参考 [Event.md](./Event.md)
- 插件系统说明请参考 [Plugin.md](./Plugin.md)
- Rich 库文档：https://rich.readthedocs.io/ 