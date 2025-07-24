# 多模态消息支持

AIPY 现在支持多模态消息，允许在对话中包含图片。

## ChatMessage 内容格式

`ChatMessage` 的 `content` 字段现在支持两种格式：

### 1. 纯文本消息（向后兼容）

```python
from aipyapp.llm.base import ChatMessage

# 传统的文本消息
msg = ChatMessage(role="user", content="Hello, world!")
```

### 2. 多模态消息（文本 + 图片）

```python
import base64

# 读取图片文件并转换为 base64
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 多模态消息
multimodal_content = [
    {
        "type": "text",
        "text": "What is in this image?",
    },
    {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{image_data}"
        },
    },
]

msg = ChatMessage(role="user", content=multimodal_content)
```

## 多模态消息结构

多模态消息是一个包含多个对象的列表，每个对象有以下格式：

### 文本对象
```python
{
    "type": "text",
    "text": "文本内容"
}
```

### 图片对象
```python
{
    "type": "image_url",
    "image_url": {
        "url": "data:image/jpeg;base64,<base64编码的图片数据>"
    }
}
```

## 使用示例

### 单张图片
```python
multimodal_content = [
    {
        "type": "text",
        "text": "请分析这张图片中的内容",
    },
    {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
        },
    },
]
```

### 多张图片
```python
multimodal_content = [
    {
        "type": "text",
        "text": "请比较这两张图片的差异：",
    },
    {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image1}"
        },
    },
    {
        "type": "text",
        "text": "和",
    },
    {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{base64_image2}"
        },
    },
]
```

## 显示格式化

当多模态消息被显示时，系统会自动格式化内容：

- 纯文本消息：直接显示文本
- 多模态消息：提取文本内容，并用 `[图片 1]`、`[图片 2]` 等标记替换图片，最后显示包含的图片数量

例如：
```
What is in this image? [图片 1]

(包含 1 张图片)
```

## 注意事项

1. **向后兼容性**：现有的纯文本消息完全兼容，无需修改
2. **图片格式**：支持常见的图片格式（JPEG、PNG、GIF 等）
3. **Base64 编码**：图片数据需要转换为 base64 编码
4. **数据 URL 格式**：图片 URL 必须使用 `data:image/<格式>;base64,<数据>` 格式
5. **LLM 支持**：需要确保使用的 LLM 客户端支持多模态输入

## 在 LLM 客户端中使用

要使用多模态消息，需要确保：

1. LLM 客户端支持多模态输入（如 GPT-4 Vision、Claude 3 Vision 等）
2. 客户端正确实现了 `get_completion` 方法来处理多模态消息
3. 客户端能够解析包含图片的响应

```python
# 在客户端中使用多模态消息
history = ChatHistory()
history.add_message(ChatMessage(role="user", content=multimodal_content))

# 发送给支持多模态的 LLM
response = client.get_completion(history.get_messages())
``` 