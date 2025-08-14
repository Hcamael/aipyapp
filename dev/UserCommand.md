# 用户自定义命令指南

本指南介绍如何在 aipy 中创建和使用自定义命令。自定义命令基于 Markdown 文件，支持两种模式：任务模式（与 AI 交互）和主模式（系统操作）。

## 概述

自定义命令系统支持：
- **Markdown 文件作为命令**: 文件名对应命令名，目录结构支持多级命令
- **两种运行模式**: TASK 模式（发送给 AI）和 MAIN 模式（执行系统操作）
- **YAML 配置**: 通过 frontmatter 配置参数、描述等
- **模板渲染**: 使用 Jinja2 模板引擎处理动态内容
- **代码块执行**: 支持 Python、Bash/Shell 代码块执行（MAIN 模式）
- **命令包含** 通过 Jinja2 include 语句包含其它文件

## 快速开始

### 1. 创建命令目录

默认命令目录为 `~/.aipyapp/commands/`。

### 2. 创建简单命令

创建文件 `hello.md`：

```markdown
Hello, World!

这是一个简单的自定义命令示例。
```

使用命令：
```bash
/hello  # 在 TASK 模式下发送给 AI
```

### 3. 创建带配置的命令

创建文件 `greet.md`：

```yaml
---
name: greet
description: 个性化问候命令
modes: [task, main]
arguments:
  - name: --name
    type: str
    required: true
    help: 要问候的人名
  - name: --formal
    type: flag
    help: 使用正式问候语
---

{% if formal %}
尊敬的 {{ name }}，您好！
{% else %}
嗨，{{ name }}！
{% endif %}

希望你今天过得愉快。
```

使用命令：
```bash
/greet --name="张三" --formal  # 正式问候
/greet --name="李四"          # 非正式问候
```

## 配置选项

### YAML Frontmatter

支持以下配置项：

```yaml
---
name: command_name           # 命令名（默认使用文件名）
description: 命令描述        # 命令说明
modes: [task, main]          # 支持的模式，可选 task/main
arguments:                   # 参数配置
  - name: --option           # 参数名
    type: str                # 参数类型：str/int/float/flag/choice
    required: false          # 是否必需
    default: value           # 默认值
    help: 参数说明           # 帮助信息
    choices: [a, b, c]       # 选择项（type=choice时）
subcommands:                 # 子命令配置
  sub1:
    description: 子命令说明
    arguments: [...]         # 子命令参数
template_vars:               # 模板变量
  var1: value1
  var2: value2
local: true                   # 本地执行还是发给LLM处理
---
```

### 参数类型

- **str**: 字符串参数
- **int**: 整数参数
- **float**: 浮点数参数
- **flag**: 布尔标志（存在为 true）
- **choice**: 从预定义选项中选择

### 模式说明

- **TASK 模式**: 命令只在Task模式下显示，默认发给LLM,除非 `local` 为 true。
- **MAIN 模式**: 命令只在Main模式下显示，默认不发给LLM,除非 `local` 为 false。

## 代码块执行

两种模式都支持执行代码块，但行为不同：

### TASK 模式代码执行
- 执行代码块并捕获输出
- 默认只发送执行结果给 AI（不包含源代码），节省 token
- 适用于数据收集、状态检查等需要 AI 分析的场景

### 测试功能
**所有自定义命令都支持 `--local` 参数用于本地执行(不发送给LLM)：**

```bash
# 测试模式：预览命令输出，不发送给LLM
/syscheck_ai --local

# 测试模式：带参数预览
/code_analysis myfile.py --local

# 正常模式：实际执行
/syscheck_ai
```

**执行结果格式示例：**
```markdown
请分析系统状态：

```
CPU使用率: 25.3%
内存使用率: 68.2%
磁盘使用率: 45.1%
```

请给出优化建议。
```

### MAIN 模式代码执行  
- 直接执行代码块并在终端显示结果
- 适用于系统操作、工具执行等

支持的代码块类型：

### Python 代码块

````python
# 获取系统信息
import platform
print(f"系统: {platform.system()}")
print(f"版本: {platform.release()}")
````

### Shell/Bash 代码块

````bash
# 显示当前目录内容
ls -la
````

````shell
# 显示系统信息
uname -a
````

### Exec 代码块

````exec
whoami
````

## 模板功能

使用 Jinja2 模板语法处理动态内容：

### 变量替换

```yaml
---
arguments:
  - name: --user
    type: str
template_vars:
  greeting: "欢迎"
---

{{ greeting }}，{{ user }}！
```

### 条件判断

```jinja2
{% if debug %}
调试模式已启用
{% else %}
正常运行模式
{% endif %}
```

### 循环处理

```jinja2
{% for item in items %}
- {{ item }}
{% endfor %}
```

### 文件引用
```jinja2
{% include "common.md" %}
```
搜索顺序为：
- 命令当前目录
- 用户命令主目录

## 实际示例

### 系统信息命令（MAIN模式）

`sysinfo.md`：

```yaml
---
name: sysinfo
description: 显示系统信息
modes: [main]
arguments:
  - name: --detail
    type: flag
    help: 显示详细信息
---

# 系统信息

````python
import platform
import psutil
from datetime import datetime

print("=== 基本信息 ===")
print(f"系统: {platform.system()}")
print(f"版本: {platform.release()}")
print(f"架构: {platform.machine()}")

{% if detail %}
print("\n=== 详细信息 ===")
print(f"处理器: {platform.processor()}")
print(f"内存使用: {psutil.virtual_memory().percent}%")
print(f"磁盘使用: {psutil.disk_usage('/').percent}%")
print(f"启动时间: {datetime.fromtimestamp(psutil.boot_time())}")
{% endif %}
````

### 系统分析命令（TASK模式）

`syscheck.md`：

```yaml
---
name: syscheck
description: 检查系统状态并请AI分析
modes: [task]
arguments:
  - name: --detail
    type: flag
    help: 包含详细的系统信息
---

# 系统状态检查

请分析以下系统信息并提供建议：

## 当前系统状态

````python
import psutil
import platform

print("=== 系统资源使用情况 ===")
print(f"CPU使用率: {psutil.cpu_percent(interval=1)}%")
print(f"内存使用率: {psutil.virtual_memory().percent}%")
print(f"磁盘使用率: {psutil.disk_usage('/').percent}%")
````

{% if detail %}
````bash
# 检查网络连接
netstat -tuln | head -5
````
{% endif %}

## 分析请求
基于上述信息，请评估系统健康状况并提供优化建议。
```

### 代码审查模板

`review.md`：

```yaml
---
name: review
description: 代码审查请求模板
modes: [task]
arguments:
  - name: --type
    type: choice
    choices: [bug, feature, refactor, docs]
    default: feature
    help: 审查类型
  - name: --language
    type: str
    default: python
    help: 编程语言
---

# 代码审查请求

## 类型
{{ type }}

## 语言
{{ language }}

## 请求
请帮我审查以下代码：

```{{ language }}
// 在此粘贴你的代码
```

## 关注点
{% if type == 'bug' %}
- 检查逻辑错误
- 验证边界条件
- 确认异常处理
{% elif type == 'feature' %}
- 评估代码质量
- 检查性能问题
- 验证设计模式
{% elif type == 'refactor' %}
- 优化建议
- 简化复杂逻辑
- 提升可读性
{% else %}
- 文档完整性
- 注释清晰度
- 示例准确性
{% endif %}

请提供具体的改进建议。
```

## 命令管理

使用内置的 `/custom` 命令管理自定义命令：

```bash
/custom list              # 列出所有自定义命令
/custom show <name>       # 显示命令详情
/custom reload            # 重新加载命令
/custom create <name>     # 创建新命令模板
```

## 最佳实践

### 1. 文件组织

```
custom_commands/
├── basic/
│   ├── hello.md
│   └── greet.md
├── dev/
│   ├── review.md
│   └── debug.md
├── system/
│   ├── sysinfo.md
│   └── monitor.md
└── help/
    └── template.md
```

### 2. 开发和测试

**使用测试模式进行开发：**

```bash
# 1. 开发阶段：使用测试模式验证输出
/mycommand --test

# 2. 调试阶段：结合参数测试
/mycommand --param value --test

# 3. 确认无误后正式使用
/mycommand --param value
```

### 3. 命名规范

- 使用小写字母和下划线
- 避免与内置命令冲突
- 使用描述性名称

### 4. 文档编写

- 提供清晰的描述
- 为参数添加帮助信息
- 在模板中添加使用说明

### 5. 错误处理

在 Python 代码块中添加适当的错误处理：

````python
try:
    # 你的代码
    result = some_operation()
    print(result)
except Exception as e:
    print(f"错误: {e}")
````

## 常见问题

### Q: 命令不显示在自动补全中？
A: 检查文件是否保存在正确的目录，使用 `/custom reload` 重新加载。

### Q: YAML frontmatter 解析失败？
A: 确保 YAML 格式正确，特别注意缩进和语法。

### Q: 代码块不执行？
A: 确保命令在 MAIN 模式下运行，检查代码块语言标签是否正确。

### Q: 模板变量未替换？
A: 检查 Jinja2 语法，确保变量名称匹配参数或 template_vars 中的定义。

## 进阶用法

### 动态子命令

```yaml
---
subcommands:
  add:
    description: 添加项目
    arguments:
      - name: item
        type: str
        required: true
  remove:
    description: 删除项目
    arguments:
      - name: item
        type: str
        required: true
---

{% if subcommand == 'add' %}
添加项目: {{ item }}
{% elif subcommand == 'remove' %}
删除项目: {{ item }}
{% endif %}
```

### 复杂模板逻辑

```jinja2
{% set current_time = moment().format() %}
{% set user_name = ctx.user.name if ctx.user else 'Anonymous' %}

处理时间: {{ current_time }}
操作用户: {{ user_name }}

{% for arg_name, arg_value in arguments.items() %}
- {{ arg_name }}: {{ arg_value }}
{% endfor %}
```

## MAIN→TASK 模式转换

**新功能**: MAIN 模式命令支持 `task: true` 配置，可以将命令输出作为新任务的指令。

### 配置方式

```yaml
---
name: syscheck_ai
description: 系统状态检查并AI分析
modes: [main]
task: true    # 关键配置：自动创建任务
arguments:
  - name: --detail
    type: flag
---
```

### 使用对比

```bash
# task: false - 仅终端显示
/sysinfo_display

# task: true - 自动创建AI任务
/syscheck_ai
```

### 工作流程

1. **执行命令**: MAIN 模式执行代码块和markdown内容
2. **捕获输出**: 收集所有输出内容（代码执行结果+markdown文本）  
3. **创建任务**: 自动创建新任务，使用输出作为AI指令
4. **切换模式**: 无缝切换到TASK模式开始AI对话

### 应用场景

- **系统分析**: `/syscheck_ai` → AI分析系统健康状况
- **代码审查**: `/code_analysis file.py` → AI进行代码审查  
- **日志分析**: `/log_parser error.log` → AI找出问题模式
- **数据处理**: `/data_summary data.csv` → AI提供数据洞察

### 实现原理

```markdown
命令执行 → 输出捕获 → 任务创建 → 模式切换
   ↓           ↓          ↓         ↓
 执行代码    收集结果   new_task()  进入AI对话
```

这个自定义命令系统提供了强大而灵活的方式来扩展 aipy 的功能，让用户可以根据自己的需求创建专用的命令和工作流，并无缝集成AI分析能力。