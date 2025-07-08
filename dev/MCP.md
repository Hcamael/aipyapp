# MCP 使用说明

MCP (Model Context Protocol) 是一组工具协议，允许 AI 模型与外部工具交互。在 aipyapp 中，您可以配置和使用多种 MCP 工具来增强 AI 助手的能力。本文档将指导您完成 MCP 的配置和使用。

## 1. MCP 环境安装

### 基础环境要求

- Node.js 环境 (用于大部分 MCP 工具)
- uvx (可选，用于部分使用python编写的MCP工具)

### 安装特定 MCP 工具

根据您使用的工具类型，可能需要安装额外的依赖：

1. **基于 Node.js 的工具**：

   ```bash
   # 文件系统工具
   npm install -g @modelcontextprotocol/server-filesystem
   
   # Playwright 工具
   npm install -g @playwright/mcp
   ```

2. **基于 `uvx` 的工具**：

   `uvx` 是`uv`项目的一个工具，可以用来执行 Python 包。 安装参考：https://docs.astral.sh/uv/getting-started/installation/#standalone-installer

   ```bash
   # 需要安装uv工具
   pip install uv
   ```
   使用 `uvx` 运行 MCP Server 时，通常不需要为 MCP Server 单独安装依赖，`uvx` 会处理。


## 2. MCP 配置文件

aipyapp 使用 JSON 格式的配置文件来管理 MCP 工具。默认配置文件位置为应用程序配置目录下的 `mcp.json`。

**支持的连接方式：**
- **stdio**：标准输入/输出(stdio)，默认方式
- **HTTP/SSE**：服务器发送事件（sse）
- **Streamable HTTP**：可流式传输的 HTTP (streamable http)

### 配置文件格式

#### 1. stdio 方式（默认）

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/directory1",
        "/path/to/directory2"
      ]
    },
    "everything": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-everything"
      ]
    },
    "playwright_uvx": {
      "command": "uvx",
      "args": [
        "@playwright/mcp"
      ]
    },
    "weather": {
      "command": "/path/to/python",
      "args": [
        "/path/to/weather.py"
      ]
    },
    "disabled_server": {
      "command": "some-tool",
      "args": [],
      "disabled": true
    }
  }
}
```

#### 2. HTTP/SSE 方式

```json
{
  "mcpServers": {
    "sse_server": {
      "url": "http://localhost:3000/sse"
    },
    "remote_sse_server": {
      "url": "https://api.example.com/sse",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

#### 3. Streamable HTTP 方式

```json
{
  "mcpServers": {
    "streamable_server": {
      "url": "http://localhost:3000/mcp",
      "transport": {
        "type": "streamable_http"
      }
    },
    "remote_streamable_server": {
      "url": "https://api.example.com/mcp",
      "transport": {
        "type": "streamable_http"
      },
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```


### 配置文件位置

配置文件位置默认为应用程序配置目录下的 `mcp.json`。您可以通过以下方式查找和创建配置：

- aipy的命令行界面中查看配置目录：`/info`
- 手动创建配置：在应用程序配置目录创建 `mcp.json` 文件

## 3. 配置 MCP 服务器

### 服务器配置字段

#### stdio 方式配置字段：
- `command`：(必填) 执行命令，可以是可执行文件路径或命令名称
- `args`：(可选) 命令行参数数组
- `env`：(可选) 环境变量对象
- `disabled`：(可选) 设置为 `true` 时禁用该服务器
- `enabled`：(可选) 设置为 `false` 时禁用该服务器

#### HTTP/SSE 和 Streamable HTTP 方式配置字段：
- `url`：(必填) MCP 服务器的 URL 地址
- `transport`：(可选) 传输配置，用于指定 streamable_http 类型
  - `type`：传输类型，可选 `"streamable_http"`
- `headers`：(可选) 自定义 HTTP 请求头，键值对格式
- `timeout`：(可选) HTTP 请求超时时间，单位秒
- `sse_read_timeout`：(可选) SSE 读取超时时间，单位秒
- `disabled`：(可选) 设置为 `true` 时禁用该服务器
- `enabled`：(可选) 设置为 `false` 时禁用该服务器


## 4. 禁用 MCP 服务器

您可以通过以下两种方式禁用 MCP 服务器：

### 方法一：使用 `disabled` 属性

添加 `"disabled": true` 字段来禁用一个服务器：

```json
"server_name": {
  "command": "...",
  "args": [...],
  "disabled": true  // 禁用该服务器
}
```

### 方法二：使用 `enabled` 属性

添加 `"enabled": false` 字段来禁用一个服务器：

```json
"server_name": {
  "command": "...",
  "args": [...],
  "enabled": false  // 禁用该服务器
}
```

## 5. 缓存机制

为提高性能，aipyapp 会将 MCP 工具列表缓存，避免每次启动都重新加载所有工具。缓存文件位于与 `mcp.json` 同一目录下，名称为 `cache.db`。

缓存在以下情况会被自动更新：
- MCP配置变更
- 缓存时间超过 48 小时

如果您添加或修改了工具但缓存未更新，可以删除 `cache.db` 文件，aipyapp 将在下次启动时重新加载所有工具。

## 6. MCP 命令行管理

默认情况下，MCP 功能是禁用的，需要手动启用。

### 6.1 全局控制命令

#### 启用 MCP 功能

```bash
/mcp enable
```

- 全局启用 MCP 功能
- 返回当前状态和可用工具数量

#### 禁用 MCP 功能

```bash
/mcp disable
```

- 全局禁用 MCP 功能
- 所有工具将不可用

### 6.2 服务器级别控制

#### 启用特定服务器

```bash
/mcp enable <server_name>
```

- 启用指定名称的 MCP 服务器
- 例如：`/mcp enable filesystem`

#### 禁用特定服务器

```bash
/mcp disable <server_name>
```

- 禁用指定名称的 MCP 服务器
- 例如：`/mcp disable filesystem`

#### 批量操作所有服务器

```bash
/mcp enable *
/mcp disable *
```

- 使用通配符 `*` 对所有服务器执行相同操作
- 不影响全局启用/禁用状态

### 6.3 查看状态

#### 列出所有服务器状态

```bash
/mcp
```

- 显示全局启用状态
- 全局启用时：
  - 显示所有服务器的启用状态
  - 显示每个服务器的工具数量


## 7. 使用 MCP 工具

在 aipyapp 中，AI 助手会自动识别可能需要使用工具的请求，并调用合适的工具。您只需要向 AI 提出问题，例如：

```
搜索我的文档里含有"人工智能"的文件
```

如果需要了解所有可用的工具，可以在 aipyapp 中查看：

```
请列出所有可用的工具及其用途
```

## 8. 常见问题排查

1. **工具未显示**：检查 `mcp.json` 配置，确保 `command` 路径正确
2. **工具调用失败**：检查工具依赖是否已安装，命令是否可执行
3. **权限问题**：确保命令有足够的权限执行

如果仍然有问题，可以删除缓存文件 `cache.db` 并重启 aipyapp。
