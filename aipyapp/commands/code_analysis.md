---
name: code_analysis
description: 分析Python文件结构并让AI审查
modes: [main, task]
task: true
arguments:
  - name: file_path
    type: str
    required: true
    help: 要分析的Python文件路径
---

# Python 文件结构分析

正在分析文件: `{{ file_path }}`

````python
import ast
import os

file_path = "{{ file_path }}"

if not os.path.exists(file_path):
    print(f"❌ 文件不存在: {file_path}")
    exit(1)

if not file_path.endswith('.py'):
    print(f"❌ 不是Python文件: {file_path}")
    exit(1)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    print(f"📄 文件: {file_path}")
    print(f"📊 总行数: {len(content.splitlines())}")
    print(f"🔤 字符数: {len(content)}")
    
    # 分析AST结构
    classes = []
    functions = []
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    
    print(f"\n🏗️  类定义 ({len(classes)}个):")
    for cls in classes:
        print(f"  - {cls}")
    
    print(f"\n🔧 函数定义 ({len(functions)}个):")
    for func in functions[:10]:  # 只显示前10个
        print(f"  - {func}")
    if len(functions) > 10:
        print(f"  ... 还有 {len(functions) - 10} 个函数")
    
    print(f"\n📦 导入模块 ({len(set(imports))}个):")
    for imp in sorted(set(imports))[:10]:  # 只显示前10个
        print(f"  - {imp}")
    if len(set(imports)) > 10:
        print(f"  ... 还有 {len(set(imports)) - 10} 个模块")

except Exception as e:
    print(f"❌ 分析失败: {e}")
````

---

**使用方式:**
- `/code_analysis path/to/file.py`

该命令会分析Python文件的结构，并自动将分析结果发送给AI进行代码审查。你可以继续与AI讨论代码优化建议、架构改进或最佳实践。