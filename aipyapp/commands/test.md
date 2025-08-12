---
name: test_example
description: 测试功能示例命令
modes: [main]
task: true
arguments:
  - name: --count
    type: int
    default: 3
    help: 生成的项目数量
---

# 系统测试报告示例

这是一个演示测试功能的示例命令。

## 随机数据生成

````python
import random
import platform
from datetime import datetime

count = {{ count }}

print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"操作系统: {platform.system()}")
print(f"Python版本: {platform.python_version()}")

print(f"\n随机数据 (共{count}项):")
for i in range(count):
    value = random.randint(1, 100)
    status = "正常" if value > 50 else "异常"
    print(f"  项目 {i+1}: 值={value}, 状态={status}")

# 统计信息
normal_count = sum(1 for _ in range(count) if random.randint(1, 100) > 50)
print(f"\n统计: {normal_count}/{count} 项正常")
````

## 分析请求

请基于上述数据进行分析：
1. 评估数据的分布情况
2. 识别任何异常模式
3. 提供优化建议

---

**使用示例:**
```bash
# 测试模式：预览输出
/test_example --test

# 测试模式：自定义参数
/test_example --count 5 --test

# 正常模式：发送给AI分析
/test_example

# 正常模式：自定义参数
/test_example --count 10
```