---
name: "sysinfo"
description: "Display comprehensive system information"
modes: ["main"]
arguments:
  - name: "--detail"
    type: "flag"
    help: "Show detailed information"
---

# System Information

## Current Configuration
- **Working Directory**: {{ctx.tm.get_status().workdir}}
- **Current LLM**: {{ctx.tm.get_status().client}}
- **Current Role**: {{ctx.tm.get_status().role}}
- **Display Style**: {{ctx.tm.get_status().display}}

{% if detail %}
## Detailed System Status

````python
import sys
import os
from pathlib import Path

# System information
print("## System Details")
print(f"- Python Version: {sys.version}")
print(f"- Python Executable: {sys.executable}")
print(f"- Platform: {sys.platform}")
print(f"- Current User: {os.getenv('USER', 'unknown')}")

# Directory information
cwd = Path.cwd()
print(f"- Current Directory: {cwd}")
print(f"- Home Directory: {Path.home()}")

# Available LLMs
print("\n## Available LLMs")
for llm in ctx.tm.list_llms():
    print(f"- {llm}")

# Task statistics
tasks = ctx.tm.get_tasks()
print(f"\n## Task Statistics")
print(f"- Total Tasks: {len(tasks)}")
````
{% endif %}

---
*Use `--detail` flag for comprehensive system information*