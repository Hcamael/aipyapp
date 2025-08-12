---
name: syscheck
description: 检查系统状态并请AI分析
modes: [main]
task: true
arguments:
  - name: --detail
    type: flag
    help: 包含详细的系统信息
---

# 系统状态检查

请分析以下系统信息并提供建议：

## 基本系统信息

````python
import platform
import psutil
from datetime import datetime

print("=== 系统概况 ===")
print(f"操作系统: {platform.system()} {platform.release()}")
print(f"处理器架构: {platform.machine()}")
print(f"Python版本: {platform.python_version()}")
print(f"系统启动时间: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}")
````

## 资源使用情况

````python
import psutil

print("=== 资源使用 ===")
# CPU信息
cpu_percent = psutil.cpu_percent(interval=1)
cpu_count = psutil.cpu_count()
print(f"CPU使用率: {cpu_percent}% (核心数: {cpu_count})")

# 内存信息
memory = psutil.virtual_memory()
print(f"内存使用率: {memory.percent}%")
print(f"总内存: {memory.total / (1024**3):.1f} GB")
print(f"可用内存: {memory.available / (1024**3):.1f} GB")

# 磁盘信息
disk = psutil.disk_usage('/')
print(f"磁盘使用率: {disk.percent}%")
print(f"总磁盘空间: {disk.total / (1024**3):.1f} GB")
print(f"可用磁盘空间: {disk.free / (1024**3):.1f} GB")
````

{% if detail %}
## 详细进程信息

````python
import psutil

print("=== 进程信息 ===")
# 获取前5个CPU使用率最高的进程
processes = []
for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent', 'memory_percent']):
    try:
        info = proc.info
        info['cpu_percent'] = info['cpu_percent'] or 0.0
        info['memory_percent'] = info['memory_percent'] or 0.0
        processes.append(info)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

# 按CPU使用率排序
processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)

print("CPU使用率最高的前5个进程:")
for proc in processes[:5]:
    print(f"  {proc['name']} (PID: {proc['pid']}) - CPU: {proc['cpu_percent']:.1f}% Memory: {proc['memory_percent']:.1f}%")
````

## 网络状态

````bash
# 检查网络连接
netstat -tuln | head -10
````
{% endif %}

## 分析请求

基于上述系统信息：
1. 评估当前系统的整体健康状况
2. 指出任何潜在的性能瓶颈或问题
3. 提供优化建议
4. 如果发现异常，请建议进一步的诊断步骤

请给出专业的分析和建议。