import json
import re
import hashlib
from . import cache
from .libmcp import MCPClientSync, MCPConfigReader
from .. import T


def build_function_call_tool_name(server_name: str, tool_name: str) -> str:
    """
    构建函数调用工具名称

    Args:
        server_name: 服务器名称
        tool_name: 工具名称

    Returns:
        处理后的工具名称
    """

    sanitized_server = server_name.strip()
    if not sanitized_server.isascii():
        # 生成MD5并取前4位
        sanitized_server = hashlib.md5(sanitized_server.encode('utf-8')).hexdigest()[:4]
    else:
        # 用下划线替换无效字符，保留 a-z, A-Z, 0-9, 下划线和短横线
        sanitized_server = re.sub(r'[^a-zA-Z0-9_-]', '_', sanitized_server)

    sanitized_tool = tool_name.strip().replace('-', '_')

    # 合并服务器名称和工具名称
    name = sanitized_tool
    if sanitized_server[:16] not in sanitized_tool:
        name = f"{sanitized_server[:16] or ''}.{sanitized_tool or ''}"

    # 确保名称以字母或下划线开头
    if not re.match(r'^[a-zA-Z]', name):
        name = f"tool-{name}"

    # 移除连续的下划线/短横线
    name = re.sub(r'[_-]{2,}', '_', name)

    # 最大截断为 63 个字符
    if len(name) > 63:
        name = name[:63]

    # 处理边缘情况：确保截断后仍有有效名称
    if name.endswith('_') or name.endswith('-'):
        name = name[:-1]

    return name


class MCPToolManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config_reader = MCPConfigReader(config_path)
        self.mcp_servers = self.config_reader.get_mcp_servers()
        self._tools_dict = {}  # 缓存已获取的工具列表
        self._inited = False

        # 全局启用/禁用标志，默认禁用
        self._globally_enabled = False
        # 服务器状态缓存，记录每个服务器的启用/禁用状态
        self._server_status = self._init_server_status()

    def _init_server_status(self):
        """初始化服务器状态，从配置文件中读取初始状态，包括禁用的服务器"""

        server_status = {}
        for server_name, server_config in self.mcp_servers.items():
            # 服务器默认启用，除非配置中明确设置为disabled: true或enabled: false
            is_enabled = not (
                server_config.get("disabled", False)
                or server_config.get("enabled", True) is False
            )
            server_status[server_name] = is_enabled
        return server_status

    def list_tools(self):
        """返回所有MCP服务器的工具列表
        [{'description': 'Get weather alerts for a US state.\n'
                           '\n'
                           '    Args:\n'
                           '        state: Two-letter US state code (e.g. CA, '
                           'NY)\n'
                           '    ',
            'inputSchema': {'properties': {'state': {'title': 'State',
                                                     'type': 'string'}},
                            'required': ['state'],
                            'title': 'get_alertsArguments',
                            'type': 'object'},
            'name': 'get_alerts',
            'server': 'server1'
            },
        ]
        """
        # 如果全局禁用，直接返回空列表
        if not self._globally_enabled:
            return []

        all_tools = []
        print(
            T(
                "Initializing MCP server, this may take a while if it's the first load, please wait patiently..."
            )
        )
        for server_name, server_config in self.mcp_servers.items():
            if server_name not in self._tools_dict:
                try:
                    print("+ Loading MCP", server_name)
                    key = f"mcp_tool:{server_name}:{cache.cache_key(server_config)}"
                    tools = cache.get_cache(key)
                    if tools is not None:
                        # 如果缓存中有工具列表，直接使用
                        self._tools_dict[server_name] = tools
                        continue

                    client = MCPClientSync(server_config)
                    tools = client.list_tools()

                    # 为每个工具添加服务器标识
                    for tool in tools:
                        tool["server"] = server_name
                        tool["id"] = build_function_call_tool_name(
                            server_name, tool.get("name", "")
                        )

                    if tools:
                        cache.set_cache(key, tools, ttl=60 * 60 * 24 * 2)

                    self._tools_dict[server_name] = tools
                except Exception as e:
                    print(f"Error listing tools for server {server_name}: {e}")
                    self._tools_dict[server_name] = []

            # 添加到总工具列表
            all_tools.extend(self._tools_dict[server_name])
            self._inited = True

        return all_tools

    def get_tools_prompt(self):
        """获取工具列表并转换为 Markdown 格式"""
        tools = self.get_available_tools()  # 获取启用的工具
        if not tools:
            return ""

        ret = []
        for tool in tools:
            # 构建工具信息的 JSON 对象
            # 去掉 inputSchema里的additionalProperties、$schema
            input_schema = tool.get("inputSchema", {}).copy()
            if "additionalProperties" in input_schema:
                del input_schema["additionalProperties"]
            if "$schema" in input_schema:
                del input_schema["$schema"]

            ret.append(
                {
                    "name": tool.get("id", ""),
                    "description": tool.get("description", ""),
                    "arguments": input_schema,
                }
            )

        # 转换为 JSON 字符串并添加到 Markdown 中
        json_str = json.dumps(ret, ensure_ascii=False)
        return f"```json\n{json_str}\n```\n"

    def get_available_tools(self):
        """返回已经启用的工具列表"""
        # 如果全局禁用，直接返回空列表
        if not self._globally_enabled:
            return []

        if not self._inited:
            self.list_tools()

        all_tools = []
        for server_name, tools in self._tools_dict.items():
            # 只包含启用的服务器
            if self._server_status.get(server_name, True):
                for tool in tools:
                    tool["server"] = server_name
                    all_tools.append(tool)
        return all_tools

    def get_all_servers(self) -> dict:
        """返回所有服务器的列表及其启用状态"""
        if not self._inited:
            self.list_tools()

        # 返回服务器列表及其启用状态
        servers_info = {}
        for server_name, status in self._server_status.items():
            ret = {'enabled': status, 'tools_count': 0}
            # if server_name not in self._tools_dict:
            tools = self._tools_dict.get(server_name, [])
            if tools:
                # 如果服务器有工具，则更新工具数量
                ret['tools_count'] = len(tools)
            servers_info[server_name] = ret

        return servers_info

    def call_tool(self, tool_name, arguments):
        """调用指定名称的工具，自动选择最匹配的服务器"""
        # 获取所有工具
        all_tools = self.get_available_tools()
        if not all_tools:
            raise ValueError("No tools available to call.")

        # 查找匹配的工具，根据id查找
        matching_tools = [t for t in all_tools if t["id"] == tool_name]
        if not matching_tools:
            raise ValueError(f"No tool found with name: {tool_name}")

        # 选择参数匹配度最高的工具
        best_match = None
        best_score = -1

        for tool in matching_tools:
            score = 0
            required_params = []

            # 检查工具的输入模式
            if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                properties = tool["inputSchema"]["properties"]
                required_params = tool["inputSchema"].get("required", [])

                # 检查所有必需参数是否提供
                required_provided = all(param in arguments for param in required_params)
                if not required_provided:
                    continue

                # 计算匹配的参数数量
                matching_params = sum(1 for param in arguments if param in properties)
                extra_params = len(arguments) - matching_params

                # 评分：匹配参数越多越好，额外参数越少越好
                score = matching_params - 0.1 * extra_params

            if score > best_score:
                best_score = score
                best_match = tool

        if not best_match:
            raise ValueError(
                f"No suitable tool found for {tool_name} with given arguments"
            )

        # 获取服务器配置
        server_name = best_match["server"]
        real_tool_name = best_match["name"]
        server_config = self.mcp_servers[server_name]

        # 创建客户端并调用工具
        client = MCPClientSync(server_config)
        return client.call_tool(real_tool_name, arguments)

    def process_command(self, args):
        """处理命令行参数，执行相应操作

        Args:
            args (list): 命令行参数列表，例如 [], ["enable"], ["disable"],
                         ["enable", "playwright"], ["disable", "playwright"]

        Returns:
            dict: 执行结果
        """
        assert len(args) > 0, "No arguments provided"
        # 第一个参数是action
        action = args[0].lower() or "list"

        # 处理全局启用/禁用命令
        if action == "enable" or action == "disable":
            # 检查是全局操作还是针对特定服务器
            if len(args) == 1:
                # 全局启用/禁用
                if action == "enable":
                    self._globally_enabled = True
                    return {
                        "status": "success",
                        "action": "global_enable",
                        "globally_enabled": self._globally_enabled,
                        "servers": self.get_all_servers(),
                    }
                else:  # disable
                    self._globally_enabled = False
                    return {
                        "status": "success",
                        "action": "global_disable",
                        "globally_enabled": self._globally_enabled,
                        "servers": self.get_all_servers(),
                    }
            elif len(args) == 2:
                # 针对特定服务器的启用/禁用
                server_name = args[1]

                # 处理特殊情况：星号操作符，对所有服务器执行相同操作
                if server_name == "*":
                    # 遍历所有服务器并设置状态（不改变全局启用/禁用状态）
                    for srv_name in self.mcp_servers.keys():
                        self._server_status[srv_name] = action == "enable"

                    # 刷新工具列表
                    self.list_tools()
                    return {
                        "status": "success",
                        "action": f"all_servers_{action}",
                        "globally_enabled": self._globally_enabled,
                        "servers": self.get_all_servers(),
                    }

                # 检查服务器是否存在
                if server_name not in self.mcp_servers:
                    return {
                        "status": "error",
                        "message": f"Unknown server: {server_name}",
                    }

                if action == "enable":
                    self._server_status[server_name] = True
                    # 刷新工具列表
                    self.list_tools()
                    return {
                        "status": "success",
                        "action": "server_enable",
                        "server": server_name,
                        "globally_enabled": self._globally_enabled,
                        "servers": self.get_all_servers(),
                    }
                else:  # disable
                    self._server_status[server_name] = False
                    # 刷新工具列表
                    self.list_tools()
                    return {
                        "status": "success",
                        "action": "server_disable",
                        "server": server_name,
                        "globally_enabled": self._globally_enabled,
                        "servers": self.get_all_servers(),
                    }
        elif action == "list":
            return {
                "status": "success",
                "action": "list",
                "globally_enabled": self._globally_enabled,
                "servers": self.get_all_servers(),
            }

        # 如果没有匹配任何已知命令
        return {"status": "error", "message": f"Invalid command: {' '.join(args)}"}
