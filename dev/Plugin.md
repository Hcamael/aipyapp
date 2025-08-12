# 插件系统

AiPy 的插件系统允许开发者通过 Python 代码扩展和自定义 AiPy 的功能。插件可以监听和处理各种事件，实现代码保存、提示词修改、结果处理等功能。

## 插件位置

插件文件位于以下目录：
- **系统插件目录**：`aipyapp/plugins/`（内置插件）
- **用户插件目录**：`~/.aipyapp/plugins/`（用户自定义插件）

## 插件开发规范

### 文件命名规范
- 插件文件必须以 `p_*.py` 格式命名（例如：`p_image_tool.py`）
- 插件文件放在系统插件目录 `aipyapp/plugins/` 或用户插件目录
- 每个插件文件定义一个插件

### 插件类规范
- 必须包含一个继承自 `TaskPlugin` 或者 `DisplayPlugin` 的类
- 插件类必须设置 `name` 属性作为插件标识
- 可以实现 `__init__` 方法接收配置参数
- 可以实现 `init()` 方法进行插件初始化

## 插件接口

### 父类
```python
from aipyapp import TaskPlugin
from aipyapp.display import DisplayPlugin
```

### 插件类属性

- `name`: 插件名称（用于配置和标识，必需）
- `version`: 版本号（可选，默认 "1.0.0"）
- `description`: 描述信息（可选）
- `author`: 作者（可选）

### 插件方法

- `init(self)`: 插件初始化（必需实现）
- `on_xxx(self, **kwargs)`: 事件处理函数，自动注册（可选）
- `fn_xxx(self, **kwargs)`: 注册功能函数，LLM可调用（可选）

### 功能函数注册机制

插件通过 `fn_` 前缀的方法来注册可供 LLM 调用的函数：

- 方法名格式：`fn_<function_name>`
- 运行时会自动提取并注册为 `<function_name>`
- 函数会自动进行参数验证和类型检查
- 支持类型注解和默认值

### 基本插件类结构

```python
from aipyapp import TaskPlugin

class MyTaskPlugin(TaskPlugin):
    # 插件基本信息（必需）
    name = "my_plugin"
    version = "1.0.0"
    description = "一个示例插件"
    author = "Your Name"
    
    def __init__(self, config=None):
        """插件构造函数，接收配置参数"""
        super().__init__(config)
    
    def init(self):
        """插件初始化（必需实现）"""
        self.logger.info("插件已加载")
        # 从配置中获取参数
        self.some_config = self.config.get('some_setting', 'default_value')
    
    # 事件处理方法（可选实现）
    def on_exception(self, **kwargs):
        """异常事件处理"""
        pass
    
    def on_task_start(self, **kwargs):
        """任务开始事件处理"""
        instruction = kwargs.get('instruction')
        self.logger.info(f"任务开始: {instruction}")
    
    def on_exec(self, **kwargs):
        """代码执行事件处理"""
        block = kwargs.get('block')
        self.logger.info(f"代码执行: {block.name}")
    
    def on_exec_result(self, **kwargs):
        """代码执行结果事件处理"""
        result = kwargs.get('result')
        block = kwargs.get('block')
        self.logger.info(f"执行结果: {result}")
    
    # 注册功能函数（可选实现）
    def fn_my_function(self, param1: str, param2: int = 0) -> str:
        """
        一个可供 LLM 调用的功能函数
        
        Args:
            param1: 必需参数
            param2: 可选参数，默认为 0
            
        Returns:
            str: 处理结果
        """
        return f"处理结果: {param1} + {param2}"
```

### 事件参数格式

所有事件方法都直接接收关键字参数，无需通过 `event.data` 获取：

```python
def on_task_start(self, **kwargs):
    """任务开始事件处理"""
    instruction = kwargs.get('instruction')
    task_id = kwargs.get('task_id')
    # 处理事件数据
    self.logger.info(f"任务开始: {instruction}")
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
- `on_exception(**kwargs)`: 异常处理
- `on_upload_result(**kwargs)`: 上传结果
- `on_runtime_message(**kwargs)`: 运行时消息
- `on_runtime_input(**kwargs)`: 运行时输入
- `on_show_image(**kwargs)`: 显示图片事件
- `on_call_function(**kwargs)`: 函数调用事件

## 插件管理器

### PluginManager 类

```python
from aipyapp.aipy.plugins import PluginManager

# 创建插件管理器
plugin_manager = PluginManager()

plugin_manager.add_plugin_directory("~/.aipyapp/plugins/")

# 加载所有插件
plugin_manager.load_all_plugins()
```

### 主要方法
- `load_all_plugins()`: 加载所有插件文件
- `create_task_plugin(name, config)`: 创建任务插件实例
- `_plugins`: 已加载的插件类字典
- `add_plugin_directory(directory)`: 添加插件目录
- `get_task_plugins()`: 获取所有任务插件
- `get_display_plugins()`: 获取所有显示插件

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
        plugin = plugin_manager.create_task_plugin(plugin_name, plugin_data)
        if plugin:
            self.add_listener(plugin)
            self.runtime.register_plugin(plugin)
```

## 插件示例

### 1. 功能函数插件（推荐）

这类插件主要用于向 LLM 提供可调用的工具函数：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 文件名：p_my_tools.py

from typing import Dict, Any, Optional
from aipyapp import TaskPlugin, PluginInitError

class MyToolsPlugin(TaskPlugin):
    """我的工具插件 - 提供各种实用功能"""
    
    # 插件基本信息（必需）
    name = "my_tools"
    version = "1.0.0"
    description = "提供文本处理、数据转换等工具功能"
    author = "Your Name"
    
    def init(self):
        """初始化插件配置"""
        # 从配置中获取必要参数
        self.api_key = self.config.get('api_key')
        self.timeout = self.config.get('timeout', 30)
        
        # 验证必需配置
        if not self.api_key:
            raise PluginInitError("缺少必需的 api_key 配置")
        
        self.logger.info(f"我的工具插件已初始化，超时: {self.timeout}s")
    
    def fn_process_text(self, text: str, operation: str = "upper") -> str:
        """
        处理文本内容
        
        Args:
            text: 待处理的文本
            operation: 处理操作 (upper/lower/title/reverse)
            
        Returns:
            str: 处理后的文本
        """
        operations = {
            "upper": lambda x: x.upper(),
            "lower": lambda x: x.lower(), 
            "title": lambda x: x.title(),
            "reverse": lambda x: x[::-1]
        }
        
        func = operations.get(operation, operations["upper"])
        result = func(text)
        self.logger.info(f"文本处理完成: {operation}")
        return result
    
    def fn_convert_data(self, data: Dict[str, Any], format: str = "json") -> str:
        """
        数据格式转换
        
        Args:
            data: 原始数据字典
            format: 目标格式 (json/yaml/xml)
            
        Returns:
            str: 转换后的数据
        """
        import json
        
        if format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format == "yaml":
            try:
                import yaml
                return yaml.dump(data, allow_unicode=True, default_flow_style=False)
            except ImportError:
                return "需要安装 PyYAML 库"
        else:
            return f"不支持的格式: {format}"
    
    def fn_calculate(self, expression: str) -> float:
        """
        安全的数学表达式计算
        
        Args:
            expression: 数学表达式字符串
            
        Returns:
            float: 计算结果
        """
        import ast
        import operator
        
        # 支持的运算符
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
        }
        
        try:
            node = ast.parse(expression, mode='eval')
            result = self._eval_node(node.body, operators)
            self.logger.info(f"计算完成: {expression} = {result}")
            return float(result)
        except Exception as e:
            self.logger.error(f"计算失败: {e}")
            raise ValueError(f"无效的表达式: {expression}")
    
    def _eval_node(self, node, operators):
        """递归计算表达式节点"""
        import ast
        
        if isinstance(node, ast.Num):  # 数字
            return node.n
        elif isinstance(node, ast.BinOp):  # 二元运算
            return operators[type(node.op)](
                self._eval_node(node.left, operators),
                self._eval_node(node.right, operators)
            )
        else:
            raise ValueError(f"不支持的节点类型: {type(node)}")
    
    # 可选的事件处理方法
    def on_call_function(self, **kwargs):
        """函数调用事件处理"""
        funcname = kwargs.get('funcname')
        self.logger.info(f"插件函数被调用: {funcname}")
```

### 2. 代码保存插件

```python
import os
import datetime
from pathlib import Path

from aipyapp import TaskPlugin

class CodeSaverPlugin(TaskPlugin):
    name = "code_saver"
    version = "1.0.0"
    description = "自动保存执行的代码"
    
    def init(self):
        self.save_path = self.config.get('save_path', './saved_code')
        self.logger.info(f"代码保存插件已加载，保存路径: {self.save_path}")

    def on_exec(self, **kwargs):
        """代码执行事件处理"""
        block = kwargs.get('block')
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
            self.logger.info(f"代码已保存到: {file_path}")
        except Exception as e:
            self.logger.error(f"保存代码失败: {e}")
```

### 3. 结果处理插件

```python
import json

from aipyapp import TaskPlugin

class ResultProcessorPlugin(TaskPlugin):
    name = "result_processor"
    version = "1.0.0"
    description = "处理代码执行结果"
    
    def init(self):
        self.logger.info("结果处理插件已加载")

    def on_exec_result(self, **kwargs):
        """代码执行结果事件处理"""
        result = kwargs.get('result')
        block = kwargs.get('block')
        
        if result and 'traceback' in result:
            self.logger.error(f"代码执行出错: {result['traceback']}")
        elif result:
            self.logger.info(f"代码执行成功，输出: {result.get('output', '')}")
```

## 插件开发最佳实践

### 1. 错误处理
```python
def on_exec(self, **kwargs):
    try:
        # 插件逻辑
        block = kwargs.get('block')
        # 处理代码块
    except Exception as e:
        self.logger.error(f"插件执行出错: {e}")

def fn_my_function(self, param1: str) -> str:
    try:
        # 功能函数逻辑
        result = self._process_param(param1)
        return result
    except Exception as e:
        self.logger.error(f"功能函数执行失败: {e}")
        raise  # 重新抛出异常供调用方处理
```

### 2. 配置验证
```python
from aipyapp import PluginInitError

def __init__(self, config=None):
    super().__init__(config)
    
def init(self):
    """在 init 方法中验证配置"""
    required_config = ['api_key', 'endpoint']
    
    for key in required_config:
        if key not in self.config:
            raise PluginInitError(f"缺少必需配置: {key}")
    
    self.api_key = self.config['api_key']
    self.endpoint = self.config['endpoint']
```

### 3. 日志记录
```python
from aipyapp import TaskPlugin

class MyPlugin(TaskPlugin):
    name = "my_plugin"
    
    def init(self):
        # 使用 self.logger 进行日志记录
        self.logger.info("插件已初始化")
        self.logger.debug(f"配置信息: {self.config}")
    
    def fn_process(self, data: str) -> str:
        self.logger.info(f"开始处理数据: {len(data)} 字符")
        result = data.upper()
        self.logger.info("数据处理完成")
        return result
```

### 4. 类型注解和文档
```python
from typing import Dict, List, Optional, Union, Any

def fn_advanced_function(
    self, 
    text: str, 
    options: Optional[Dict[str, Any]] = None,
    multiple: bool = False
) -> Union[str, List[str]]:
    """
    高级功能函数示例
    
    Args:
        text: 输入文本
        options: 可选的配置字典
        multiple: 是否返回多个结果
        
    Returns:
        处理结果，单个字符串或字符串列表
        
    Raises:
        ValueError: 当输入参数无效时
    """
    if not text:
        raise ValueError("文本不能为空")
    
    # 函数逻辑...
    return result
```

## 功能函数注册机制详解

### 注册原理

1. **自动发现**：插件管理器会自动扫描插件类中以 `fn_` 开头的方法
2. **函数提取**：提取方法名去掉 `fn_` 前缀后作为函数名注册到 `FunctionManager`
3. **参数解析**：使用 `inspect` 模块分析函数签名，结合 `pydantic` 进行参数验证
4. **类型检查**：支持 Python 类型注解，自动进行参数类型验证

### 工作流程

```python
# 1. 插件加载时
plugin = MyPlugin()
runtime.register_plugin(plugin)  # 调用 plugin.get_functions()

# 2. 函数注册
functions = plugin.get_functions()  # 返回 {'my_function': <method>}
function_manager.register_functions(functions)

# 3. LLM 调用时
runtime.call_function('my_function', param1='test', param2=123)
```

### 参数验证机制

```python
# 插件中的函数定义
def fn_example(self, name: str, age: int = 18, active: bool = True) -> dict:
    """示例函数"""
    return {"name": name, "age": age, "active": active}

# 系统会自动创建 Pydantic 模型：
ExampleParams = create_model('example_Params', 
    name=(str, ...),           # 必需参数
    age=(int, 18),            # 可选参数，默认值18
    active=(bool, True)        # 可选参数，默认值True
)

# LLM 调用时自动验证：
call_function('example', name='张三', age='25')  # age 自动转换为 int
```

### 支持的参数类型

- **基础类型**：`str`, `int`, `float`, `bool`
- **复合类型**：`List[T]`, `Dict[str, T]`, `Optional[T]`
- **Union 类型**：`Union[str, int]`
- **Any 类型**：`Any`（不进行类型检查）

### 函数调用示例

```python
# 在 Python 运行时中调用插件函数
result = runtime.call_function('process_text', 
                              text='hello world', 
                              operation='upper')

# 函数会通过 FunctionManager 找到对应插件的 fn_process_text 方法
# 自动进行参数验证和调用
```

## 插件调试

### 1. 启用调试模式
```python
from aipyapp import TaskPlugin

class MyPlugin(TaskPlugin):
    name = "my_plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.debug = self.config.get('debug', False)
        
    def on_task_start(self, **kwargs):
        if self.debug:
            instruction = kwargs.get('instruction')
            self.logger.debug(f"任务开始事件: {instruction}")
```

### 2. 测试插件
```python
# 测试插件文件
if __name__ == '__main__':
    # 测试插件初始化
    config = {'debug': True, 'api_key': 'test_key'}
    plugin = MyPlugin(config)
    plugin.init()
    
    # 测试功能函数
    if hasattr(plugin, 'fn_process_text'):
        result = plugin.fn_process_text('hello world', 'upper')
        print(f"测试结果: {result}")
    
    # 测试事件处理
    plugin.on_task_start(instruction='test task', task_id='test123')
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