#!/usr/bin/env python
# coding: utf-8

from collections import OrderedDict
import platform
import locale
import os
from datetime import date

SYSTEM_PROMPT_TEMPLATE = """
{role_prompt}
{aipy_prompt}
{tips_prompt}
{api_prompt}
"""

AIPY_PROMPT = """
# 输出内容格式规范
输出内容必须采用结构化的 Markdown 格式，并符合以下规则：

## 多行代码块标记
1. 代码块必须用一对HTML注释标记包围，格式如下：
   - 代码开始：<!-- Block-Start: {{"name": "代码块名称", "version": 数字版本号如1/2/3, "path": "该代码块的可选文件路径"}} -->
   - 代码本体：用 Markdown 代码块包裹（如 ```python 或 ```html 等)。
   - 代码结束：<!-- Block-End: {{ "name": 和Block-Start中的name一致 }} -->

2. 多个代码块可以使用同一个name，但版本必须不同。版本最高的代码块会被认为是最新的有效版本。

3. `path` 为代码块需要保存为的本地文件路径可以包含目录, 如果是相对路径则默认为相对当前目录或者用户指定目录.

4. 同一个输出消息里可以定义多个代码块。

5. **正确示例：**
<!-- Block-Start: {{"name": "abc123", "version": 1, "path": "main.py"}} -->
```python
print("hello world")
```
<!-- Block-End: {{"name": "abc123"}} -->

## 单行命令标记
1. 每次输出中只能包含 **一个** `Cmd-Exec` 标记，用于执行可执行代码块来完成用户的任务：
   - 格式：<!-- Cmd-Exec: {{"name": "要执行的代码块 name"}} -->
   - 如果不需要执行任何代码，则不要添加 `Cmd-Exec`。
   - 要执行的代码块必需先使用前述多行代码块标记格式单独定义。
   - 如果代码块有多个版本，执行代码块的最新版本。
   - 可以使用 `Cmd-Exec` 执行会话历史中的所有代码块。特别地，如果需要重复执行某个任务，尽量使用 `Cmd-Exec` 执行而不是重复输出代码块。

2. Cmd-Exec 只能用来执行 Python 代码块，不能执行其它语言(如 JSON/CSS/JavaScript等)的代码块。

3. **正确示例：**
<!-- Cmd-Exec: {{"name": "abc123"}} -->

## 其它   
1. 所有 JSON 内容必须写成**单行紧凑格式**，例如：
   <!-- Block-Start: {{"name": "abc123", "path": "main.py", "version": 1}} -->

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
在标准 Python 运行环境的基础上额外增加了下述功能：
- 一些预装的第三方包
- 全局 `aipyrun` 对象

生成 Python 代码时可以直接使用这些额外功能。

## 预装的第三方包
下述第三方包可以无需安装直接使用：
- `requests`、`numpy`、`pandas`、`matplotlib`、`seaborn`、`bs4`。

其它第三方包，都必需通过下述 aipyrun 对象的 install_packages 方法申请安装才能使用。

在使用 matplotlib 时，需要根据系统类型选择和设置合适的中文字体，否则图片里中文会乱码导致无法完成客户任务。
示例代码如下：
```python
import platform

system = platform.system().lower()
font_options = {{
    'windows': ['Microsoft YaHei', 'SimHei'],
    'darwin': ['Kai', 'Hei'],
    'linux': ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Source Han Sans SC']
}}
```

## 全局 aipyrun 对象
aipyrun为全局对象，不需要额外导入，该对象提供一些协助代码完成任务的方法。

{aipyrun_prompt}

# 代码执行结果反馈
Python代码块的执行结果会通过JSON对象反馈给你，对象包括以下属性：
- `stdout`: 标准输出内容
- `stderr`: 标准错误输出
- `result`: 前述`set_result` 函数设置的当前代码块执行结果
- `errstr`: 异常信息
- `traceback`: 异常堆栈信息
- `block_name`: 执行的代码块名称

注意：
- 如果某个属性为空，它不会出现在反馈中。

收到反馈后，结合代码和反馈数据，做出下一步的决策。
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
1. 这些 API 信息里描述的环境变量必须用 aipyrun.get_env 方法获取，绝对不能使用 os.getenv 方法。
2. API获取数据失败时，请输出完整的API响应信息，方便调试和分析问题。

{apis}
"""

def get_system_prompt(tips, api_prompt, aipyrun_prompt, user_prompt=None) -> str:
    if user_prompt:
        user_prompt = user_prompt.strip()
    prompts = {
        'role_prompt': user_prompt or tips.role.detail,
        'aipy_prompt': AIPY_PROMPT.format(aipyrun_prompt=aipyrun_prompt),
        'tips_prompt': '',
        'api_prompt': API_PROMPT.format(apis=api_prompt)
    }
    if not user_prompt and len(tips) > 0:
        prompts['tips_prompt'] = TIPS_PROMPT.format(tips=str(tips))
    return SYSTEM_PROMPT_TEMPLATE.format(**prompts)

def get_results_prompt(results):
    prompt = OrderedDict()
    prompt['message'] = "These are the execution results of the code block/s automatically returned in the order of execution by the runtime environment."
    prompt['source'] = "Runtime Environment"
    prompt['results'] = results
    return prompt

def get_task_prompt(instruction):
    prompt = OrderedDict()
    prompt['task'] = instruction
    prompt['source'] = "User"
    context = OrderedDict()
    context['os_type'] = platform.system()
    context['os_locale'] = locale.getlocale()
    context['os_platform'] = platform.platform()
    context['python_version'] = platform.python_version()
    context['today'] = date.today().isoformat()
    
    context['TERM'] = os.environ.get('TERM', 'unknown')
    context['LC_TERMINAL'] = os.environ.get('LC_TERMINAL', 'unknown')

    prompt['context'] = context

    constraints = OrderedDict()
    constraints['reply_language'] = "Now, use the exact language of the `task` field for subsequent responses"
    constraints['file_creation_path'] = 'current_directory'
    prompt['constraints'] = constraints
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