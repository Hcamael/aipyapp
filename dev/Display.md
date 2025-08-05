# 显示插件系统

AiPy 的显示插件系统负责处理任务执行过程中的各种输出和交互，提供不同的显示风格来满足不同用户的需求。显示插件通过事件机制监听任务执行过程，并以不同的方式呈现信息。

## 系统架构

### 核心组件

1. **BaseDisplayPlugin**: 显示插件基类，定义统一的接口
2. **DisplayManager**: 显示管理器，负责插件的注册、切换和管理
3. **LiveDisplay**: 实时显示组件，处理流式内容的动态更新
4. **样式插件**: 具体的显示风格实现

### 目录结构

```
aipyapp/display/
├── __init__.py          # 模块导出
├── base.py              # 基类定义
├── manager.py           # 显示管理器
├── live_display.py      # 实时显示组件
├── style_classic.py     # 经典风格
├── style_modern.py      # 现代风格
├── style_minimal.py     # 简约风格
└── style_null.py        # 空显示风格
```

## 显示管理器

### DisplayManager 类

显示管理器负责管理所有显示插件，提供统一的接口：

```python
from aipyapp.display import DisplayManager
from rich.console import Console

# 创建显示管理器
console = Console()
display_manager = DisplayManager(
    style='classic',      # 显示风格
    console=console,      # 控制台对象
    record=True,          # 是否记录输出
    quiet=False           # 是否安静模式
)

# 获取当前插件
plugin = display_manager.get_current_plugin()

# 切换显示风格
display_manager.set_style('modern')

# 获取可用风格列表
styles = display_manager.get_available_styles()
```

### 主要方法

- `get_available_styles()`: 获取可用的显示风格列表
- `set_style(style_name)`: 设置显示风格
- `get_current_plugin()`: 获取当前显示插件实例
- `register_plugin(name, plugin_class)`: 注册新的显示插件

## 显示插件基类

### BaseDisplayPlugin 类

所有显示插件都继承自 `BaseDisplayPlugin`，提供统一的接口：

```python
from aipyapp.display import BaseDisplayPlugin
from rich.console import Console

class MyDisplayPlugin(BaseDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        # 初始化代码
    
    # 事件处理方法
    def on_task_start(self, event):
        """任务开始事件处理"""
        pass
    
    def on_exception(self, event):
        """异常事件处理"""
        pass
    
    # ... 其他事件方法
```

### 核心方法

- `print(message, style=None)`: 显示消息
- `input(prompt)`: 获取用户输入
- `confirm(prompt, default="n", auto=None)`: 确认操作
- `save(path, clear=False, code_format=None)`: 保存输出

## 现有显示风格

### 1. Classic (经典风格)

**特点**：
- 传统的命令行界面风格
- 使用丰富的 Rich 组件（Panel、Table、Syntax 等）
- 详细的执行信息和统计表格
- 支持实时流式显示

**适用场景**：
- 需要详细执行信息的用户
- 喜欢传统命令行界面的用户
- 调试和开发环境

**示例输出**：
```
🔄 Streaming started...
➡️ Sending message to LLM...
📝 Reply (gpt-4): 
┌─ 回复内容 ──────────────────────────────────────┐
│ 这里是 LLM 的回复内容...                        │
└─────────────────────────────────────────────────┘
```

### 2. Modern (现代风格)

**特点**：
- 现代化的界面设计
- 简洁的图标和符号
- 智能的内容解析和显示
- 支持代码块自动识别

**适用场景**：
- 喜欢现代界面的用户
- 需要清晰代码显示的用户
- 日常使用场景

**示例输出**：
```
📝 Task: 用户任务
⏳ Executing...
📝 Code (python): 
┌─ 代码内容 ──────────────────────────────────────┐
│ def hello():                                    │
│     print("Hello, World!")                      │
└─────────────────────────────────────────────────┘
✅ Execution successful
```

### 3. Minimal (简约风格)

**特点**：
- 极简的输出风格
- 最少的信息显示
- 使用 Status 组件显示进度
- 专注于核心信息

**适用场景**：
- 喜欢简洁输出的用户
- 自动化脚本环境
- 快速执行场景

**示例输出**：
```
→ 用户任务
⟳ Sending...
📥 Receiving response... (15 lines)
→ 代码执行结果
✓ Success
```

### 4. Null (空显示风格)

**特点**：
- 不输出任何内容
- 适用于静默模式
- 仅用于记录功能

**适用场景**：
- 自动化环境
- 仅需要记录功能的场景
- 调试和测试

## 事件系统

显示插件通过事件系统监听任务执行过程，支持以下事件：

### 任务相关事件
- `on_task_start(event)`: 任务开始
- `on_task_end(event)`: 任务结束
- `on_round_start(event)`: 回合开始
- `on_round_end(event)`: 回合结束

### 执行相关事件
- `on_exec(event)`: 代码执行开始
- `on_exec_result(event)`: 代码执行结果
- `on_mcp_call(event)`: MCP 工具调用
- `on_mcp_result(event)`: MCP 工具调用结果

### 响应相关事件
- `on_query_start(event)`: 查询开始
- `on_response_complete(event)`: LLM 响应完成
- `on_stream_start(event)`: 流式开始
- `on_stream_end(event)`: 流式结束
- `on_stream(event)`: 流式响应
- `on_parse_reply(event)`: 消息解析结果

### 其他事件
- `on_exception(event)`: 异常处理
- `on_upload_result(event)`: 上传结果
- `on_runtime_message(event)`: 运行时消息
- `on_runtime_input(event)`: 运行时输入

## 创建自定义显示风格

### 1. 创建插件文件

在 `aipyapp/display/` 目录下创建新的样式文件，例如 `style_custom.py`：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .base import BaseDisplayPlugin
from .. import T

class DisplayCustom(BaseDisplayPlugin):
    """Custom display style - 自定义显示风格"""
    
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        # 初始化自定义属性
        self.custom_buffer = []
    
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
            # 自定义代码显示
            code_text = Text(block.code, style="green")
            self.console.print(f"💻 执行代码:\n{code_text}")
    
    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result', {})
        
        if 'traceback' in result:
            # 错误显示
            error_text = Text(result['traceback'], style="red")
            self.console.print(f"❌ 执行错误:\n{error_text}")
        else:
            # 成功显示
            output = result.get('output', '')
            if output:
                output_text = Text(output, style="green")
                self.console.print(f"✅ 执行成功:\n{output_text}")
    
    def on_response_complete(self, event):
        """LLM 响应完成事件处理"""
        data = event.data
        msg = data.get('msg')
        
        if msg and hasattr(msg, 'content'):
            # 自定义响应显示
            response_text = Text(msg.content, style="cyan")
            panel = Panel(response_text, title="🤖 AI 回复", border_style="cyan")
            self.console.print(panel)
    
    # 实现其他需要的事件方法...
    def on_exception(self, event):
        """异常事件处理"""
        data = event.data
        msg = data.get('msg', '')
        exception = data.get('exception')
        
        error_text = Text(f"{msg}: {exception}", style="red")
        self.console.print(f"💥 异常: {error_text}")
```

### 2. 注册新插件

在 `aipyapp/display/manager.py` 中注册新插件：

```python
from .style_custom import DisplayCustom

class DisplayManager:
    # 可用的显示效果插件
    DISPLAY_PLUGINS = {
        'classic': DisplayClassic,
        'modern': DisplayModern,
        'minimal': DisplayMinimal,
        'custom': DisplayCustom,  # 添加新插件
    }
```

### 3. 更新模块导出

在 `aipyapp/display/__init__.py` 中添加导出：

```python
from .style_custom import DisplayCustom

__all__ = [
    'BaseDisplayPlugin',
    'DisplayClassic',
    'DisplayModern',
    'DisplayMinimal',
    'DisplayCustom',  # 添加新插件
    'DisplayManager',
    'LiveDisplay'
]
```

## 实时显示组件

### LiveDisplay 类

`LiveDisplay` 提供实时流式内容的显示功能：

```python
from aipyapp.display import LiveDisplay

class MyDisplayPlugin(BaseDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.live_display = None
    
    def on_stream_start(self, event):
        """流式开始事件处理"""
        if not self.quiet:
            self.live_display = LiveDisplay()
            self.live_display.__enter__()
    
    def on_stream(self, event):
        """流式响应事件处理"""
        response = event.data
        lines = response.get('lines', [])
        reason = response.get('reason', False)
        
        if self.live_display:
            self.live_display.update_display(lines, reason=reason)
    
    def on_stream_end(self, event):
        """流式结束事件处理"""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None
```

## 使用示例

### 1. 基本使用

```python
from aipyapp.display import DisplayManager
from rich.console import Console

# 创建显示管理器
console = Console()
display_manager = DisplayManager('classic', console=console)

# 获取显示插件
plugin = display_manager.get_current_plugin()

# 使用插件
plugin.print("Hello, World!", style="green")
```

### 2. 切换显示风格

```python
# 切换到现代风格
display_manager.set_style('modern')

# 切换到简约风格
display_manager.set_style('minimal')

# 获取可用风格
styles = display_manager.get_available_styles()
print(f"可用风格: {styles}")
```

### 3. 保存输出

```python
# 保存为 HTML 文件
plugin.save("output.html", clear=True, code_format="github")
```

## 最佳实践

### 1. 事件处理
- 只实现需要的事件方法
- 使用 `event.data` 获取事件数据
- 处理异常情况

### 2. 样式设计
- 保持一致的视觉风格
- 使用合适的颜色和符号
- 考虑不同终端的兼容性

### 3. 性能优化
- 避免在事件处理中进行耗时操作
- 合理使用缓存和缓冲区
- 及时清理资源

### 4. 用户体验
- 提供清晰的状态指示
- 支持安静模式
- 提供有用的错误信息

## 调试和测试

### 1. 调试模式

```python
class MyDisplayPlugin(BaseDisplayPlugin):
    def __init__(self, console: Console, quiet: bool = False):
        super().__init__(console, quiet)
        self.debug = True  # 启用调试模式
    
    def on_task_start(self, event):
        if self.debug:
            self.console.print(f"[DEBUG] Task start event: {event.data}")
        # 正常处理逻辑
```

### 2. 测试插件

```python
# 测试插件文件
if __name__ == '__main__':
    from rich.console import Console
    
    console = Console()
    plugin = MyDisplayPlugin(console)
    
    # 测试事件处理
    from aipyapp.aipy import Event
    test_event = Event('task_start', {'instruction': 'test task'})
    plugin.on_task_start(test_event)
```

---

如需详细的事件说明，请参考 [Event.md](./Event.md) 文档。
如需插件系统说明，请参考 [Plugin.md](./Plugin.md) 文档。 