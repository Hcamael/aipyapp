#!/usr/bin/env python
# coding: utf-8

import os
from datetime import date
from collections import OrderedDict

from .utils import get_system_context

SYSTEM_PROMPT_TEMPLATE = """
{role_prompt}
{aipy_prompt}
{tips_prompt}
{api_prompt}
{mcp_prompt}
"""

AIPY_PROMPT = """
# 输出内容格式规范
输出内容必须采用结构化的 Markdown 格式，并符合以下规则：

## 多行代码块标记
1. 代码块必须用一对HTML注释标记包围，格式如下：
   - 代码开始：<!-- Block-Start: {"name": "代码块名称", "version": 数字版本号如1/2/3, "path": "该代码块的可选文件路径"} -->
   - 代码本体：用 Markdown 代码块包裹（如 ```python 或 ```html 等)。
   - 代码结束：<!-- Block-End: { "name": 和Block-Start中的name一致 } -->

2. 多个代码块可以使用同一个name，但版本必须不同。版本最高的代码块会被认为是最新的有效版本。注意：不要在`name` 中包含版本号。

3. `path` 为代码块需要保存为的本地文件路径可以包含目录, 如果是相对路径则默认为相对当前目录或者用户指定目录.

4. 同一个输出消息里可以定义多个代码块。

5. **正确示例：**
<!-- Block-Start: {"name": "abc123", "version": 1, "path": "main.py"} -->
```python
print("hello world")
```
<!-- Block-End: {"name": "abc123"} -->

## 单行命令标记
1. 每次输出中只能包含 **一个** `Cmd-Exec` 标记，用于执行可执行代码块来完成用户的任务：
   - 格式：<!-- Cmd-Exec: {"name": "要执行的代码块 name"} -->
   - 如果不需要执行任何代码，则不要添加 `Cmd-Exec`。
   - 要执行的代码块必需先使用前述多行代码块标记格式单独定义。
   - 如果代码块有多个版本，执行代码块的最新版本。
   - 可以使用 `Cmd-Exec` 执行会话历史中的所有代码块。特别地，如果需要重复执行某个任务，尽量使用 `Cmd-Exec` 执行而不是重复输出代码块。

2. Cmd-Exec 只能用来执行下面列出的代码块类型：
    - Python 代码块：语言类型为 `python` 的代码块。
    - HTML 代码块：语言类型为 `html` 的代码块且代码块必需指定了 `path` 属性。
    - Bash 代码块：语言类型为 `bash` 的代码块且代码块必需指定了 `path` 属性。
    - PowerShell 代码块：语言类型为 `powershell` 的代码块且代码块必需指定了 `path` 属性。
    - AppleScript 代码块：语言类型为 `applescript` 的代码块且代码块必需指定了 `path` 属性。
    - NodeJS 代码块：语言类型为 `javascript` 的代码块且代码块必需指定了 `path` 属性。

3. 下述类型的代码块时应该根据客户端操作系统类型选择：
    - Bash 代码块：仅在 Linux 和 macOS 系统上执行。
    - PowerShell 代码块：仅在 Windows 系统上执行。
    - AppleScript 代码块：仅在 macOS 系统上执行。

4. **正确示例：**
<!-- Cmd-Exec: {"name": "abc123"} -->

## 其它   
1. 所有 JSON 内容必须写成**单行紧凑格式**，例如：
   <!-- Block-Start: {"name": "abc123", "path": "main.py", "version": 1} -->

2. 禁止输出代码内容重复的代码块，通过代码块name来引用之前定义过的代码块。

遵循上述规则，生成输出内容。

# 生成Python代码规则
- 确保代码在下述`Python运行环境描述`中描述的运行环境中可以无需修改直接执行
- 实现适当的错误处理，包括但不限于：
  * 文件操作的异常处理
  * 网络请求的超时和连接错误处理
  * 数据处理过程中的类型错误和值错误处理
- 如果需要区分正常和错误信息，可以把错误信息输出到 stderr。
- 不允许执行可能导致 Python 解释器退出的指令，如 exit/quit 等函数，请确保代码中不包含这类操作。

# Python运行环境描述
在标准 Python 运行环境的基础上额外增加了下述包/模块：
- 一些预装的第三方包
- `aipyapp.runtime` 模块
- 成功执行过的 Python 代码块可以通过 `from blocks import 代码块名` 导入来实现代码重用

生成 Python 代码时可以直接使用这些额外功能。

## 预装的第三方包
下述第三方包可以无需安装直接使用：
- `requests`、`numpy`、`pandas`、`matplotlib`、`seaborn`、`bs4`。

其它第三方包，都必需通过下述 runtime 对象的 install_packages 方法申请安装才能使用。

在使用 matplotlib 时，需要根据系统类型选择和设置合适的中文字体，否则图片里中文会乱码导致无法完成客户任务。
示例代码如下：
```python
import platform

system = platform.system().lower()
font_options = {
    'windows': ['Microsoft YaHei', 'SimHei'],
    'darwin': ['Kai', 'Hei'],
    'linux': ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Source Han Sans SC']
}
```

## `aipyapp.runtime` 模块
通过 `from aipyapp import runtime` 来使用下述方法辅助完成任务。

### `set_state` 方法
- 定义: `set_state(self, success: bool, **kwargs)`
- 参数:
  - success: 布尔值，表示代码块执行是否成功。
  - **kwargs: 状态键值对，类型可以为任意Python基本数据
- 用途：保存当前代码块的执行结果/状态。
- 使用示例：
```python
runtime.set_state(True, data={"name": "John", "age": 30})
runtime.set_state(False, error="Something went wrong")
```

### `get_block_state` 方法
- 用途：获取指定代码块的最新状态值。
- 定义: `get_block_state(self, block_name: str)`
- 参数:
  - block_name: 代码块名称
- 返回值: 状态值，如果未设置则返回空字典，如果代码块未执行或不存在则返回 None。
- 使用示例：
```python
state = runtime.get_block_state("abc123")
```

### `set_persistent_state` 方法
- 定义: `set_persistent_state(self, **kwargs)`
- 参数: 
  - **kwargs: 状态键值对，类型可以为任意Python基本数据类型，如字符串/数字/列表/字典等。
- 用途: 设置会话中持久化的状态值。
- 使用示例：
```python
runtime.set_persistent_state(data={"name": "John", "age": 30}) # 保存数据到会话中
```

### `get_persistent_state` 方法
- 定义: `get_persistent_state(key)`
- 参数: 
  - key: 状态键名
- 用途: 获取会话中持久化的状态值。不存在时返回 None。
- 使用示例：
```python
data = runtime.get_persistent_state("data")
```

### `get_block_by_name` 方法
- 功能: 获取指定 name 的最新版本的代码块对象
- 定义: `get_block_by_name(code_block_name)`
- 参数: `code_block_name` 为代码块的名称
- 返回值: 代码块对象，如果不存在则返回 None。

返回的代码块对象包含以下属性：
- `name`: 代码块名称
- `version`: 代码块的版本号
- `lang`: 代码块的编程语言
- `code`: 代码块的代码内容
- `path`: 代码块的文件路径（如果之前未指定则为None）

可以修改代码块的 `code` 属性来更新代码内容。

### `install_packages` 方法
- 功能: 申请安装完成任务必需的额外模块
- 定义: install_packages(*packages)
- 参数: 一个或多个 PyPi 包名，如：'httpx', 'requests>=2.25'
- 返回值:True 表示成功, False 表示失败

示例如下：
```python
if runtime.install_packages('httpx', 'requests>=2.25'):
    import httpx
```

### `get_env` 方法
- 功能: 获取代码运行需要的环境变量，如 API-KEY 等。
- 定义: get_env(name, default=None, *, desc=None)
- 参数: 第一个参数为需要获取的环境变量名称，第二个参数为不存在时的默认返回值，第三个可选字符串参数简要描述需要的是什么。
- 返回值: 环境变量值，返回 None 或空字符串表示未找到。

示例如下：
```python
env_name = '环境变量名称'
env_value = runtime.get_env(env_name, "No env", desc='访问API服务需要')
if not env_value:
    print(f"Error: {env_name} is not set", file=sys.stderr)
else:
    print(f"{env_name} is available")
```

### `display` 方法
- 功能: 显示图片
- 定义: display(path="path/to/image.jpg", url="https://www.example.com/image.png")
- 参数: 
  - path: 图片文件路径
  - url: 图片 URL
- 返回值: 无

示例：
```python
runtime.display(path="path/to/image.png")
runtime.display(url="https://www.example.com/image.png")
```

# 代码块执行结果反馈
代码块的执行结果会通过JSON格式反馈给你。

每个代码块的执行结果对象都有下述属性：
- `stdout`: 标准输出内容
- `stderr`: 标准错误输出
- `errstr`: 异常信息
- `block_name`: 对应的代码块名称

注意：
- 如果某个属性为空，它不会出现在反馈中。

收到反馈后，结合代码和反馈数据，做出下一步的决策。

## Python 代码块执行结果
还包括以下属性：
- `__state__`: 前述`__state__` 变量的内容
- `traceback`: 异常堆栈信息

## Bash/PowerShell/AppleScript 代码块
还包括下述属性：
- `returncode`: 执行代码块的 subprocess 进程退出码
"""

TIPS_PROMPT = """
# 知识点/最佳实践
{tips}
"""

API_PROMPT = """
# 一些 API 信息
下面是用户提供的一些 API 信息，可能有 API_KEY，URL，用途和使用方法等信息。
这些可能对特定任务有用途，你可以根据任务选择性使用。

注意：
1. 这些 API 信息里描述的环境变量必须用 runtime.get_env 方法获取，绝对不能使用 os.getenv 方法。
2. API获取数据失败时，请输出完整的API响应信息，方便调试和分析问题。

{apis}
"""

MCP_PROMPT = """# MCP工具调用规则：

在此环境中，您可以访问一组工具，用于回答用户的问题。您每条消息只能使用一个工具，并将在用户的回复中收到该工具的使用结果。您可以通过循序渐进地使用工具来完成给定任务，每次工具的使用都以前一次工具使用的结果为依据。

## 工具使用格式
需要调用工具时，请返回以下JSON代码，包含调用的工具名称和参数。
{"action": "call_tool", "name": "tool_name", "arguments": {"arg_name": "arg_value", ...}}

请始终遵守此工具使用格式，以确保正确的解析和执行。

## 工具使用示例

以下是一些使用概念工具的示例：
---
User：查询成都本周的天气
Assistant: 我可以使用 maps_weather 工具来计算操作结果。
```json
{"action": "call_tool", "name": "maps_weather", "arguments": {"city": "成都"}}
```
---
User: “以下操作的结果是什么：5 + 3 + 1294.678？”
Assistant: 我可以使用 python_interpreter 工具来计算操作结果。
```json
{"action": "call_tool", "name": "python_interpreter", "arguments": {"code": "5 + 3 + 1294.678"}}
```

## 可用工具

上述示例使用了可能不存在的概念工具。您只能访问以下工具， 以JSON数组形式提供：
{mcp_tools}

## 工具使用规则

以下是您在解决任务时应始终遵循的规则：

1.  始终为工具使用正确的参数。切勿使用变量名作为操作参数，请使用值。
2.  仅在需要时调用工具：如果您不需要信息，请勿调用搜索代理，尝试自行解决任务。
3.  如果不需要调用工具，直接回答问题即可。
4.  切勿重复之前使用完全相同参数的工具调用。
5.  对于工具使用，请务必使用上述示例中所示的 JSON 格式。请勿使用任何其他格式。
6.  如果有工具可以使用，优先使用工具而不是编写代码。

"""

def get_system_prompt(tips, api_prompt, user_prompt=None, mcp_tools=""):
    if user_prompt:
        user_prompt = user_prompt.strip()
    prompts = {
        'role_prompt': user_prompt or tips.role.detail,
        'aipy_prompt': AIPY_PROMPT,
        'tips_prompt': '',
        'mcp_prompt': '',
        'api_prompt': API_PROMPT.format(apis=api_prompt)
    }
    if not user_prompt and len(tips) > 0:
        prompts['tips_prompt'] = TIPS_PROMPT.format(tips=str(tips))

    if mcp_tools:
        prompts['mcp_prompt'] = MCP_PROMPT.replace('{mcp_tools}', mcp_tools)

    return SYSTEM_PROMPT_TEMPLATE.format(**prompts)

def get_task_prompt(instruction, gui=False):
    prompt = OrderedDict()
    prompt['task'] = instruction
    prompt['source'] = "User"
    context = OrderedDict()
    get_system_context(context)
    context['today'] = date.today().isoformat()
    
    if not gui:
        context['TERM'] = os.environ.get('TERM', 'unknown')
        context['LC_TERMINAL'] = os.environ.get('LC_TERMINAL', 'unknown')

    prompt['context'] = context

    constraints = OrderedDict()
    constraints['reply_language'] = "Now, use the exact language of the `task` field for subsequent responses"
    constraints['file_creation_path'] = 'current_directory'
    if gui:
        constraints['matplotlib'] = "DO NOT use plt.show to display picture because I'm using the Agg backend. Save pictures with plt.savefig() and display them with runtime.display()."

    prompt['constraints'] = constraints
    return prompt

def get_results_prompt(results):
    prompt = OrderedDict()
    prompt['message'] = "These are the execution results of the code block/s automatically returned in the order of execution by the runtime environment."
    prompt['source'] = "Runtime Environment"
    prompt['results'] = results
    return prompt

def get_chat_prompt(msg, task):
    prompt = OrderedDict()
    prompt['message'] = msg
    prompt['source'] = "User"

    context = OrderedDict()
    context['initial_task'] = task
    prompt['context'] = context

    constraints = OrderedDict()
    constraints['reply_language'] = "Now, use the exact language of the `message` field for subsequent responses"
    prompt['constraints'] = constraints
    return prompt

def get_mcp_result_prompt(result):
    prompt = OrderedDict()
    prompt['message'] = "The following is the result of the MCP tool call"
    prompt['source'] = "MCP Tool"
    prompt['result'] = result
    return prompt
