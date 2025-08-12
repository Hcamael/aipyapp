# 系统快速检查

这是一个纯 Markdown 主模式命令，没有 YAML frontmatter。

## 当前系统状态

````python
import os
import sys
from datetime import datetime

print("## 系统信息")
print(f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"- Python 版本: {sys.version.split()[0]}")
print(f"- 当前目录: {os.getcwd()}")
print(f"- 系统用户: {os.getenv('USER', 'unknown')}")
````

## 磁盘使用情况

````bash
echo "磁盘使用情况:"
df -h | head -5
````

---
*这是一个无需配置的快速系统检查工具*