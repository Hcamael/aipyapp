![logo](https://github.com/user-attachments/assets/3af4e228-79b2-4fa0-a45c-c38276c6db91)
# Python use
AIPy 是 Python-use 概念的一个具体实现，旨在展示该理念的实际价值与应用潜力。

- **使命**: 释放大语言模型的全部潜能
- **愿景**: 能够自主改进和使用 AIPy 的更聪明的LLM

## What
Python use 是把整个 Python 执行环境提供给 LLM 使用，可以想象为 LLM 坐在电脑前用键盘在 Python 命令行解释器里输入各种命令，按回车运行，然后观察执行结果，再输入代码和执行。

和 Agent 的区别是 Python use 不定义任何 tools 接口，LLM 可以自由使用 Python 运行环境提供的所有功能。

## Why
假如你是一个数据工程师，你对下面的场景一定不陌生：
- 处理各种不同格式的数据文件：csv/excel，json，html, sqlite, parquet ...
- 对数据进行清洗，转换，计算，聚合，排序，分组，过滤，分析，可视化等操作

这个过程经常需要：
- 启动 Python，import pandas as pd，输入一堆命令处理数据
- 生成一堆中间临时文件
- 找 ChatGPT / Claude 描述你的需要，手工拷贝生成的数据处理代码运行。

所以，为什么不启动 Python 命令行解释器后，直接描述你的数据处理需求，然后自动完成？好处是：
- 无需手工临时输入一堆 Python 命令
- 无需去找 GPT 描述需求，拷贝程序，然后手工运行

这就是 Python use 要解决的问题！

## How
Python use (aipython) 是一个集成 LLM 的 Python 命令行解释器。你可以：
- 像往常一样输入和执行 Python 命令
- 用自然语言描述你的需求，aipython 会自动生成 Python 命令，然后执行

而且，两种模式可以互相访问数据。例如，aipython 处理完你的自然语言命令后，你可以用标准 Python 命令查看各种数据。

## 使用
AIPython 有两种运行模式：
- 任务模式：非常简单易用，直接输入你的任务即可，适合不熟悉 Python 的用户。
- Python模式：适合熟悉 Python 的用户，既可以输入任务也可以输入 Python 命令，适合高级用户。

默认运行模式是任务模式，可以通过 `--python` 参数切换到 Python 模式。

### 最小配置
~/.aipyapp/aipyapp.toml:
```toml
[llm.deepseek]
type = "deepseek"
api_key = "Your DeepSeek API Key"
```

### 任务模式
`uv run aipy`

```
>>> 获取Reddit r/LocalLLaMA 最新帖子
......
......
>>> /done
```

`pip install aipyapp` ，运行aipy命令进入任务模式

```
-> % aipy
🚀 Python use - AIPython (0.1.22) [https://aipy.app]
请输入需要 AI 处理的任务 (输入 /use <下述 LLM> 切换)
>> 获取Reddit r/LocalLLaMA 最新帖子
......
>>
```

### Python 模式

#### 基本用法
自动任务处理：

```
>>> ai("获取Google官网首页标题")
```

#### 自动申请安装第三方库
```
Python use - AIPython (Quit with 'exit()')
>>> ai("使用psutil列出当前MacOS所有进程列表")

📦 LLM 申请安装第三方包: ['psutil']
如果同意且已安装，请输入 'y [y/n] (n): y

```

## Thanks
- 黑哥: 产品经理/资深用户/首席测试官
- Sonnet 3.7: 生成了第一版的代码，几乎无需修改就能使用。
- ChatGPT: 提供了很多建议和代码片段，特别是命令行接口。
- Codeium: 代码智能补齐
- Copilot: 代码改进建议和翻译 README



