# 插件系统

AiPy 的插件系统允许开发者通过 Python 代码扩展和自定义 AiPy 的功能。插件可以监听和处理各种事件，实现代码保存、提示词修改、结果处理等功能。

## 插件位置

插件文件位于以下目录：
- **系统插件目录**：`aipyapp/plugins/`（内置插件）
- **用户插件目录**：`~/.aipyapp/plugins/`（用户自定义插件）

## 插件开发规范

### 文件命名规范
- 插件文件必须以 `.py` 结尾
- 文件名不能以 `_` 开头
- 每个插件文件定义一个插件

### 插件类规范
- 必须包含一个名为 `Plugin` 的类
- 插件类必须支持事件监听接口
- 可以实现 `__init__` 方法接收配置参数

## 插件接口

### 基本插件类结构

```python
class Plugin:
    def __init__(self, config=None):
        """插件初始化
        Args:
            config: 插件配置参数（来自角色配置）
        """
        self.config = config
        print("[+] 插件已加载")
    
    # 事件处理方法（可选实现）
    def on_exception(self, event):
        """异常事件处理"""
        pass
    
    def on_task_start(self, event):
        """任务开始事件处理"""
        pass
    
    def on_exec(self, event):
        """代码执行事件处理"""
        pass
    
    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        pass
    
    # ... 其他事件方法
```

### 事件参数格式

所有事件方法都接收 `event` 参数，通过 `event.data` 获取具体数据：

```python
def on_task_start(self, event):
    """任务开始事件处理"""
    data = event.data
    instruction = data.get('instruction')
    user_prompt = data.get('user_prompt')
    # 处理事件数据
```

## 支持的事件类型

插件可以实现以下事件处理方法：

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

## 插件管理器

### PluginManager 类

```python
from aipyapp.aipy.plugin import PluginManager

# 创建插件管理器
plugin_manager = PluginManager(plugin_dir="~/.aipyapp/plugins/")

# 加载所有插件
plugin_manager.load_plugins()

# 获取插件实例
plugin = plugin_manager.get_plugin("plugin_name", config_data)
```

### 主要方法
- `load_plugins()`: 加载所有插件文件
- `get_plugin(name, config)`: 获取插件实例
- `plugins`: 已加载的插件字典

## 插件与角色系统集成

插件可以通过角色配置进行管理：

### 角色配置中的插件设置

```toml
# 角色配置文件 (role.toml)
[plugins.code-saver]
enabled = true
save_path = "./saved_code"

[plugins.prompt-modifier]
enabled = true
template = "custom_template"
```

### 插件在任务中的加载

```python
# 在任务初始化时加载角色配置的插件
def init_plugins(self):
    plugin_manager = self.context.plugin_manager
    for plugin_name, plugin_data in self.role.plugins.items():
        plugin = plugin_manager.get_plugin(plugin_name, plugin_data)
        if plugin:
            self.register_listener(plugin)
```

## 插件示例

### 1. 代码保存插件

```python
import os
import datetime
from pathlib import Path

class Plugin:
    def __init__(self, config=None):
        self.config = config or {}
        self.save_path = self.config.get('save_path', './saved_code')
        print(f"[+] 代码保存插件已加载，保存路径: {self.save_path}")

    def on_exec(self, event):
        """代码执行事件处理"""
        block = event.data.get('block')
        if not block or not hasattr(block, 'code'):
            return
            
        # 创建保存目录
        save_dir = Path(self.save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"code_{timestamp}.py"
        file_path = save_dir / filename
        
        # 保存代码
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(block.code)
            print(f"[i] 代码已保存到: {file_path}")
        except Exception as e:
            print(f"[!] 保存代码失败: {e}")
```

### 2. 提示词修改插件

```python
class Plugin:
    def __init__(self, config=None):
        self.config = config or {}
        self.template = self.config.get('template', '')
        print("[+] 提示词修改插件已加载")

    def on_task_start(self, event):
        """任务开始事件处理"""
        data = event.data
        task = data.get('instruction', '')
        
        # 修改任务提示词
        if self.template:
            modified_task = f"{self.template}\n\n{task}"
            data['instruction'] = modified_task
            print(f"[i] 提示词已修改")
```

### 3. 结果处理插件

```python
import json

class Plugin:
    def __init__(self, config=None):
        self.config = config or {}
        print("[+] 结果处理插件已加载")

    def on_exec_result(self, event):
        """代码执行结果事件处理"""
        data = event.data
        result = data.get('result')
        block = data.get('block')
        
        if result and 'traceback' in result:
            print(f"[!] 代码执行出错: {result['traceback']}")
        elif result:
            print(f"[+] 代码执行成功，输出: {result.get('output', '')}")
```

## 插件开发最佳实践

### 1. 错误处理
```python
def on_exec(self, event):
    try:
        # 插件逻辑
        pass
    except Exception as e:
        print(f"[!] 插件执行出错: {e}")
```

### 2. 配置验证
```python
def __init__(self, config=None):
    self.config = config or {}
    required_config = ['api_key', 'endpoint']
    
    for key in required_config:
        if key not in self.config:
            raise ValueError(f"缺少必需配置: {key}")
```

### 3. 日志记录
```python
import logging

class Plugin:
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.logger.info("插件已初始化")
```

### 4. 资源清理
```python
def __del__(self):
    """插件销毁时的清理工作"""
    # 清理资源
    pass
```

## 插件调试

### 1. 启用调试模式
```python
class Plugin:
    def __init__(self, config=None):
        self.debug = config.get('debug', False)
        
    def on_task_start(self, event):
        if self.debug:
            print(f"[DEBUG] 任务开始事件: {event.data}")
```

### 2. 测试插件
```python
# 测试插件文件
if __name__ == '__main__':
    plugin = Plugin({'debug': True})
    # 测试事件处理
    test_event = Event('task_start', {'instruction': 'test task'})
    plugin.on_task_start(test_event)
```

## 插件分发

### 1. 插件打包
- 将插件文件放在用户插件目录
- 确保插件文件有正确的权限
- 提供插件配置示例

### 2. 插件文档
- 提供详细的使用说明
- 说明插件依赖和配置要求
- 提供使用示例

---

如需详细的事件说明，请参考 [Event.md](./Event.md) 文档。
如需角色系统集成说明，请参考 [Role.md](./Role.md) 文档。