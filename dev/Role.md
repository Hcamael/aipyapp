# 角色系统

AiPy 的角色系统用于定义 LLM 的行为模式、提供知识点和配置环境。角色通过 TOML 配置文件定义，支持提示信息、环境变量、包依赖和插件配置。

## 配置文件

角色配置文件位于以下目录：
- 系统角色：`aipyapp/res/roles/`
- 用户角色：`~/.aipyapp/roles/` (通过 `ROLES_DIR` 配置)

配置文件格式为 TOML，每个 `.toml` 文件定义一个角色。

## TOML 配置文件格式

```toml
# 角色基本信息
name = "角色名称"
short = "简短描述"
detail = """
详细描述，支持多行文本
"""

# 环境变量配置
[envs]
API_KEY = ["your-api-key", "API密钥描述"]
DEBUG = ["true", "调试模式开关"]

# 包依赖配置
[packages]
python = ["requests", "pandas", "numpy"]
node = ["axios", "lodash"]

# 提示信息配置
[tips.tip-name]
short = "提示信息简短描述"
detail = """
提示信息的详细内容
支持多行文本和 Markdown 格式
"""

# 插件配置
[plugins.plugin-name]
enabled = true
config = "插件配置参数"
```

## 角色组件

### 1. 基本信息
- `name`: 角色名称，用于标识和切换角色
- `short`: 简短描述，用于角色列表显示
- `detail`: 详细描述，作为角色的核心提示信息

### 2. 环境变量 (envs)
定义角色需要的环境变量：
```toml
[envs]
变量名 = ["变量值", "变量描述"]
```

### 3. 包依赖 (packages)
定义不同编程语言的包依赖：
```toml
[packages]
python = ["requests", "pandas"]
javascript = ["axios", "lodash"]
```

### 4. 提示信息 (tips)
定义角色可用的知识点和提示：
```toml
[tips.plan-task]
short = "任务规划"
detail = """
任务规划相关的详细说明
"""
```

### 5. 插件配置 (plugins)
配置角色启用的插件：
```toml
[plugins.code-analyzer]
enabled = true
config = "插件配置"
```

## 角色管理器

### RoleManager 类
负责加载和管理所有角色：

```python
from aipyapp.aipy.role import RoleManager

# 创建角色管理器
role_manager = RoleManager(roles_dir="~/.aipyapp/roles/", api_conf=api_config)

# 加载所有角色
role_manager.load_roles()

# 切换角色
role_manager.use("aipy")
```

### 主要方法
- `load_roles()`: 加载所有角色配置文件
- `use(name)`: 切换到指定角色
- `current_role`: 获取当前角色

## 角色对象

### Role 类
表示单个角色，包含所有角色信息：

```python
from aipyapp.aipy.role import Role

# 从 TOML 文件加载角色
role = Role.load("path/to/role.toml")

# 获取提示信息
tip = role.get_tip("plan-task")

# 添加环境变量
role.add_env("API_KEY", "value", "description")

# 添加提示信息
role.add_tip("custom-tip", "short", "detail")
```

### 主要属性
- `name`: 角色名称
- `short`: 简短描述
- `detail`: 详细描述
- `envs`: 环境变量字典
- `packages`: 包依赖字典
- `tips`: 提示信息字典
- `plugins`: 插件配置字典

## 提示信息对象

### Tip 类
表示单个提示信息：

```python
from aipyapp.aipy.role import Tip

tip = Tip(
    name="tip-name",
    short="简短描述",
    detail="详细内容"
)

# 转换为字符串格式
tip_str = str(tip)  # 输出: <tip name="tip-name">详细内容</tip>
```

## 使用方式

### 1. 命令行使用
```bash
# 切换角色
/use @role.aipy

# 查看当前角色
/role info
```

### 2. 编程使用
```python
# 在任务中使用角色
task = Task(context)
current_role = task.role

# 获取角色提示信息
tip = current_role.get_tip("plan-task")

# 获取环境变量
api_key = current_role.envs.get("API_KEY")
```

### 3. 插件集成
角色系统与插件系统集成，角色可以配置启用哪些插件：

```python
# 在任务初始化时加载角色配置的插件
def init_plugins(self):
    for plugin_name, plugin_data in self.role.plugins.items():
        plugin = self.plugin_manager.get_plugin(plugin_name, plugin_data)
        if plugin:
            self.register_listener(plugin)
```

## 默认角色

AiPy 提供默认角色 `aipy`，包含：
- 任务规划提示信息
- 核心规则提示信息
- 默认行为模式定义

## 扩展角色

用户可以通过以下方式扩展角色系统：

1. **创建自定义角色**：在用户角色目录创建 `.toml` 文件
2. **添加提示信息**：在角色配置中添加 `[tips]` 部分
3. **配置环境变量**：在角色配置中添加 `[envs]` 部分
4. **集成插件**：在角色配置中添加 `[plugins]` 部分

## 示例配置文件

参考 `aipyapp/res/roles/aipy.toml` 查看完整的角色配置示例。

---

如需详细实现说明，请参考 `aipyapp/aipy/role.py` 和 `aipyapp/aipy/taskmgr.py` 代码实现。


