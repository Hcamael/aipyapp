# LLM对话上下文管理功能

## 概述

LLM对话上下文管理功能旨在智能地管理对话历史，通过多种压缩策略来减少发送给LLM的请求长度，从而降低token消耗并提高响应速度。

## 功能特性

### 1. 多种压缩策略

- **滑动窗口 (Sliding Window)**: 保留最近的N轮对话
- **重要性过滤 (Importance Filter)**: 基于消息重要性评分保留关键消息
- **摘要压缩 (Summary Compression)**: 将早期对话压缩为摘要
- **混合策略 (Hybrid)**: 结合多种策略的智能压缩

### 2. 智能Token管理

- 实时跟踪token使用量
- 自动触发压缩机制
- 支持多模态内容处理

### 3. 可配置参数

- 最大token数限制
- 最大对话轮数
- 压缩比例
- 重要性阈值
- 摘要长度限制

## 配置说明

在 `aipyapp/res/default.toml` 中添加以下配置：

```toml
[context_manager]
enable = true
strategy = "hybrid"
max_tokens = 8192
max_rounds = 10
compression_ratio = 0.3
importance_threshold = 0.5
summary_max_length = 200
preserve_system = true
preserve_recent = 3
```

### 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable` | bool | true | 是否启用上下文管理 |
| `strategy` | string | "hybrid" | 压缩策略 |
| `max_tokens` | int | 8192 | 最大token数 |
| `max_rounds` | int | 10 | 最大对话轮数 |
| `compression_ratio` | float | 0.3 | 压缩比例 |
| `importance_threshold` | float | 0.5 | 重要性阈值 |
| `summary_max_length` | int | 200 | 摘要最大长度 |
| `preserve_system` | bool | true | 是否保留系统消息 |
| `preserve_recent` | int | 3 | 保留最近几轮对话 |

## 使用方式

### 1. CLI命令

使用 `/context` 命令管理上下文：

```bash
# 显示当前上下文
/context show

# 显示上下文统计信息
/context stats

# 显示上下文配置
/context config

# 清空上下文
/context clear

# 更新配置
/context config --strategy sliding_window --max-tokens 4096
```

### 2. 编程接口

```python
from aipyapp.aipy.context_manager import ContextManager, ContextConfig, ContextStrategy

# 创建配置
config = ContextConfig(
    max_tokens=4096,
    strategy=ContextStrategy.HYBRID,
    preserve_recent=3
)

# 创建管理器
manager = ContextManager(config)

# 添加消息
message = ChatMessage(role="user", content="你好")
manager.add_message(message)

# 获取压缩后的消息
messages = manager.get_messages()

# 获取统计信息
stats = manager.get_stats()
```

## 压缩策略详解

### 1. 滑动窗口策略

保留最近的N轮对话，适合短期对话场景。

**优点**:
- 实现简单，性能好
- 保证对话的连续性

**缺点**:
- 可能丢失重要的早期信息
- 不适合长期对话

### 2. 重要性过滤策略

基于消息重要性评分保留关键消息。

**评分因素**:
- 消息角色（系统 > 用户 > 助手）
- 消息位置（越新越重要）
- 内容长度（长消息可能包含更多信息）

**优点**:
- 保留重要信息
- 智能选择保留内容

**缺点**:
- 计算复杂度较高
- 可能破坏对话顺序

### 3. 摘要压缩策略

将早期对话压缩为摘要，保留最近对话。

**优点**:
- 保留历史信息
- 大幅减少token消耗

**缺点**:
- 可能丢失细节信息
- 摘要质量依赖压缩算法

### 4. 混合策略

结合滑动窗口和摘要压缩，先尝试滑动窗口，如果仍然超出限制则使用摘要压缩。

**优点**:
- 平衡性能和效果
- 适应不同场景

**缺点**:
- 策略选择可能不够精确

## 性能优化

### 1. Token估算

使用简单的字符计数方法估算token数量：
- 1 token ≈ 4个字符（中英文混合）
- 支持多模态内容处理

### 2. 缓存机制

- 消息缓存避免重复计算
- 压缩结果缓存提高性能

### 3. 触发条件

自动压缩触发条件：
- Token数超出限制
- 消息数量超出限制
- 时间间隔超过5分钟

## 最佳实践

### 1. 策略选择

- **短期对话**: 使用滑动窗口策略
- **长期对话**: 使用摘要压缩策略
- **重要信息**: 使用重要性过滤策略
- **通用场景**: 使用混合策略

### 2. 参数调优

- 根据模型上下文窗口调整 `max_tokens`
- 根据对话特点调整 `preserve_recent`
- 根据重要性要求调整 `importance_threshold`

### 3. 监控和调试

- 定期查看上下文统计信息
- 监控压缩效果
- 根据实际使用情况调整配置

## 故障排除

### 1. 常见问题

**Q: 上下文管理没有生效？**
A: 检查配置中的 `enable` 是否为 `true`

**Q: 压缩效果不明显？**
A: 调整 `max_tokens` 和 `preserve_recent` 参数

**Q: 重要信息丢失？**
A: 尝试使用重要性过滤策略或调整 `importance_threshold`

### 2. 调试方法

```python
# 获取详细统计信息
stats = manager.get_stats()
print(f"消息数量: {stats['message_count']}")
print(f"当前Token: {stats['total_tokens']}")
print(f"压缩比例: {stats['compression_ratio']}")

# 强制压缩
messages = manager.get_messages(force_compress=True)
```

## 未来改进

### 1. 功能增强

- 支持更精确的token计算
- 添加语义相似度压缩
- 支持自定义压缩算法

### 2. 性能优化

- 实现增量压缩
- 添加并行处理支持
- 优化内存使用

### 3. 用户体验

- 提供可视化配置界面
- 添加压缩效果预览
- 支持策略自动选择 