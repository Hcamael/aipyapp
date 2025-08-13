---
name: "workspace"
description: "Workspace and project management"
modes: ["main"]
arguments:
  - name: "action"
    type: "choice"
    choices: ["status", "clean", "backup", "stats"]
    required: true
    help: "Action to perform"
  - name: "--path"
    type: "str"
    help: "Specific path to work with"
---

# Workspace Management

{% if action == 'status' %}
## Workspace Status

````python
import os
from pathlib import Path

cwd = Path.cwd()
print(f"**Current Directory**: {cwd}")
print(f"**Directory Size**: {sum(f.stat().st_size for f in cwd.rglob('*') if f.is_file()) // 1024} KB")

# Count files by extension
extensions = {}
for f in cwd.rglob('*'):
    if f.is_file():
        ext = f.suffix.lower() or 'no extension'
        extensions[ext] = extensions.get(ext, 0) + 1

print("\n**File Types:**")
for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {ext}: {count} files")

# Check for common project files
project_files = ['.gitignore', 'README.md', 'requirements.txt', 'package.json', 'Cargo.toml', 'go.mod']
found_files = [f for f in project_files if (cwd / f).exists()]
if found_files:
    print(f"\n**Project Files Found**: {', '.join(found_files)}")
````
{% elif action == 'clean' %}
## Workspace Cleanup

````python
import os
import shutil
from pathlib import Path

cwd = Path.cwd()
cleaned = []

# Common cleanup patterns
cleanup_patterns = [
    '**/__pycache__',
    '**/*.pyc',
    '**/.DS_Store',
    '**/node_modules',
    '**/.pytest_cache'
]

total_size = 0
for pattern in cleanup_patterns:
    for path in cwd.glob(pattern):
        if path.is_file():
            size = path.stat().st_size
            path.unlink()
            cleaned.append(f"File: {path.relative_to(cwd)} ({size} bytes)")
            total_size += size
        elif path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            shutil.rmtree(path)
            cleaned.append(f"Directory: {path.relative_to(cwd)} ({size} bytes)")
            total_size += size

if cleaned:
    print(f"[green]Cleaned {len(cleaned)} items, freed {total_size // 1024} KB[/green]")
    for item in cleaned[:10]:  # Show first 10 items
        print(f"  - {item}")
    if len(cleaned) > 10:
        print(f"  ... and {len(cleaned) - 10} more items")
else:
    print("[green]Workspace is already clean[/green]")
````
{% elif action == 'backup' %}
## Workspace Backup

````python
import shutil
import datetime
from pathlib import Path

cwd = Path.cwd()
backup_name = f"workspace_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_path = cwd.parent / backup_name

try:
    # Create backup (excluding common ignore patterns)
    def ignore_patterns(dir, files):
        ignored = []
        for file in files:
            if file.startswith('.') and file in ['.git', '.venv', '__pycache__', 'node_modules']:
                ignored.append(file)
        return ignored
    
    shutil.copytree(cwd, backup_path, ignore=ignore_patterns)
    print(f"[green]Workspace backed up to: {backup_path}[/green]")
    
    # Show backup size
    backup_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()) // 1024
    print(f"[green]Backup size: {backup_size} KB[/green]")
    
except Exception as e:
    print(f"[red]Backup failed: {e}[/red]")

{% elif action == 'stats' %}
## Workspace Statistics

SCRIPT:
import os
from pathlib import Path
from collections import Counter

cwd = Path.cwd()

# File statistics
all_files = list(cwd.rglob('*'))
files = [f for f in all_files if f.is_file()]
dirs = [f for f in all_files if f.is_dir()]

print(f"**Total Files**: {len(files)}")
print(f"**Total Directories**: {len(dirs)}")

# Size statistics
total_size = sum(f.stat().st_size for f in files)
print(f"**Total Size**: {total_size // 1024} KB ({total_size // (1024*1024)} MB)")

# Largest files
largest_files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)[:5]
print("\n**Largest Files:**")
for f in largest_files:
    size = f.stat().st_size // 1024
    print(f"  {f.relative_to(cwd)}: {size} KB")

# Language statistics (by extension)
extensions = Counter(f.suffix.lower() for f in files if f.suffix)
print("\n**File Extensions:**")
for ext, count in extensions.most_common(10):
    print(f"  {ext}: {count} files")
````
{% endif %}