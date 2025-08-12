# Event 描述

在 AiPy 中，Task对象负责事件注册和通知。事件通过 `Event` 对象传递，所有事件处理函数统一接收 `event: Event` 参数，通过 `event.data` 获取具体数据。

## Event 对象

- `event.name`：事件名称（如 "exception"、"task_start" 等）
- `event.data`：事件数据（dict，包含所有参数）

## Event 调用方式

## emit
- 发出事件

---

## 主要事件类型与参数

### exception
- 参数：
  - `msg`：异常说明
  - `exception`：异常对象（可选）
  - `traceback`：异常堆栈字符串（可选，优先显示）

### task_start
- 参数：
  - `instruction`：用户输入的任务
  - `user_prompt`：处理后的提示词

### round_start
- 参数：
  - `instruction`：本轮指令
  - `user_prompt`：处理后的提示词

### query_start
- 参数：无

### response_complete
- 参数：
  - `llm`：LLM 名称
  - `msg`：LLM 返回的消息对象

### stream_start / stream_end
- 参数：
  - `llm`：LLM 名称

### stream
- 参数：
  - `llm`：LLM 名称
  - `lines`：流式内容（list）
  - `reason`：是否为思考内容（bool，可选）

### exec
- 参数：
  - `block`：代码块对象

### exec_result
- 参数：
  - `result`：执行结果（dict，可能包含 traceback）
  - `block`：代码块对象

### mcp_call / mcp_result
- 参数：
  - `block`：工具调用的代码块
  - `result`：工具调用结果

### parse_reply
- 参数：
  - `result`：解析结果（dict）

### round_end
- 参数：
  - `summary`：统计信息（dict，含 tokens、耗时等）
  - `response`：最终回复内容

### task_end
- 参数：
  - `path`：任务保存路径

### upload_result
- 参数：
  - `status_code`：上传状态码
  - `url`：上传后的链接

### runtime_message / runtime_input
- 参数：
  - `message`：运行时消息内容

---

## 事件处理插件实现

所有插件事件处理函数签名统一为：

```python
def on_xxx(self, event: Event):
    # 通过 event.data 获取参数
    ...
```

如：

```python
def on_exception(self, event):
    msg = event.data.get('msg')
    traceback_str = event.data.get('traceback')
    ...
```

---

如需详细参数说明，请参考 `aipyapp/aipy/task.py` 和 `aipyapp/display/base.py` 代码实现。
