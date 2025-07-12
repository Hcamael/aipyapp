import asyncio
import contextlib
import json
import os
import re
import sys
from datetime import timedelta

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage
from .. import T

# 猴子补丁：修复第三方库中的 _handle_json_response 方法
# MR如果合并后，可以去掉这段代码 https://github.com/modelcontextprotocol/python-sdk/pull/1057
async def _patched_handle_json_response(
    self,
    response,
    read_stream_writer,
    is_initialization: bool = False,
) -> None:
    """修复后的 JSON 响应处理方法"""
    try:
        content = await response.aread()

        # Parse JSON first to determine structure
        data = json.loads(content)

        if isinstance(data, list):
            messages = [JSONRPCMessage.model_validate(item) for item in data]  # type: ignore
        else:
            message = JSONRPCMessage.model_validate(data)
            messages = [message]

        for message in messages:
            if is_initialization:
                self._maybe_extract_protocol_version_from_message(message)

            session_message = SessionMessage(message)
            await read_stream_writer.send(session_message)
    except Exception as exc:
        logger.error(f"Error parsing JSON response: {exc}")
        await read_stream_writer.send(exc)

# 应用猴子补丁
def _apply_streamable_http_patch():
    """应用 StreamableHTTP 客户端的补丁"""
    try:
        from mcp.client.streamable_http import StreamableHTTPTransport
        # 替换原有方法
        StreamableHTTPTransport._handle_json_response = _patched_handle_json_response
        logger.debug("Applied StreamableHTTP patch for _handle_json_response")
    except ImportError as e:
        logger.warning(f"Failed to apply StreamableHTTP patch: {e}")

# 在模块加载时应用补丁
_apply_streamable_http_patch()


# 预编译正则表达式
CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")
JSON_PATTERN = re.compile(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})")

def extra_call_tool_blocks(blocks) -> str:
    """
    从代码块列表中提取 MCP call_tool JSON。

    Args:
        blocks (list): CodeBlock 对象列表

    Returns:
        str: 找到的 JSON 字符串，如果没找到则返回空字符串
    """
    if not blocks:
        return ""

    for block in blocks:
        # 检查代码块是否是 JSON 格式
        if hasattr(block, 'lang') and block.lang and block.lang.lower() in ['json', '']:
            # 尝试解析代码块内容
            content = getattr(block, 'code', '') if hasattr(block, 'code') else str(block)
            if content:
                content = content.strip()
                try:
                    data = json.loads(content)
                    # 验证是否是 call_tool 动作
                    if not isinstance(data, dict):
                        continue
                    if "action" not in data or "name" not in data:
                        continue
                    if "arguments" in data and not isinstance(data["arguments"], dict):
                        continue

                    # 返回 JSON 字符串
                    return json.dumps(data, ensure_ascii=False)
                except json.JSONDecodeError:
                    continue

    return ""


def extract_call_tool_str(text) -> str:
    """
    Extract MCP call_tool JSON from text.

    Args:
        text (str): The input text that may contain MCP call_tool JSON.

    Returns:
        str: The JSON str if found and valid, otherwise empty str.
    """

    # 使用预编译的正则模式
    code_blocks = CODE_BLOCK_PATTERN.findall(text)

    # Potential JSON candidates to check
    candidates = code_blocks.copy()

    # 使用预编译的正则模式
    standalone_jsons = JSON_PATTERN.findall(text)
    candidates.extend(standalone_jsons)

    # Try to parse each candidate
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            data = json.loads(candidate)
            # Validate that it's a call_tool action
            if not isinstance(data, dict):
                continue
            if "action" not in data or "name" not in data:
                continue
            if "arguments" in data and not isinstance(data["arguments"], dict):
                continue

            # return json string. not dict
            return json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            continue

    return ""


class MCPConfigReader:
    def __init__(self, config_path, tt_api_key=None):
        self.config_path = config_path
        self.tt_api_key = tt_api_key

    def _rewrite_config(self, servers):
        """rewrite MCP server config"""
        if not self.tt_api_key:
            return servers

        for _, server_config in servers.items():
            # 检查是否是trustoken的URL且transport类型为streamable_http
            url = server_config.get("url", "")
            transport = server_config.get("transport", {})

            trustoken_urls = (
                url.startswith("https://sapi.trustoken.ai/") or
                url.startswith("https://api.trustoken.cn/")
            )

            if trustoken_urls and transport.get("type") == "streamable_http":
                if "headers" not in server_config:
                    server_config["headers"] = {}

                server_config["headers"].update({
                    "Authorization": f"Bearer {self.tt_api_key}"
                })

        return servers

    def get_mcp_servers(self):
        """读取 mcp.json 文件并返回 MCP 服务器清单，包括禁用的服务器"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                servers = config.get("mcpServers", {})
                return self._rewrite_config(servers)
        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            print(T("Error decoding MCP config file {}: {}").format(self.config_path, e))
            return {}


class MCPClientSync:
    def __init__(self, server_config, suppress_output=True):
        self.server_config = server_config
        self.suppress_output = suppress_output
        self.connection_type = self._determine_connection_type()

    def _determine_connection_type(self):
        """确定连接类型：stdio, sse, 或 streamable_http"""
        if "url" in self.server_config:
            # 检查是否明确指定为 streamable_http
            transport_type = self.server_config.get("transport", {}).get("type")
            if transport_type == "streamable_http":
                return "streamable_http"
            # 默认为 SSE
            return "sse"
        else:
            return "stdio"

    @contextlib.contextmanager
    def _suppress_stdout_stderr(self):
        """上下文管理器：临时重定向 stdout 和 stderr 到空设备"""
        if not self.suppress_output:
            yield  # 如果不需要抑制输出，直接返回
            return

        # 保存原始的 stdout 和 stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # 使用 os.devnull - 跨平台解决方案
            with open(os.devnull, "w") as devnull:
                sys.stdout = devnull
                sys.stderr = devnull
                yield
        finally:
            # 恢复原始的 stdout 和 stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def _run_async(self, coro):
        with self._suppress_stdout_stderr():
            try:
                return asyncio.run(coro)
            except Exception as e:
                print(f"Error running async function: {e}")

    def list_tools(self) -> list:
        return self._run_async(self._list_tools()) or []

    def call_tool(self, tool_name, arguments):
        return self._run_async(self._call_tool(tool_name, arguments))

    async def _create_client_session(self):
        """根据连接类型创建相应的客户端会话"""
        if self.connection_type == "stdio":
            # stdio 连接
            server_params = StdioServerParameters(
                command=self.server_config.get("command"),
                args=self.server_config.get("args", []),
                env=self.server_config.get("env"),
            )
            return stdio_client(server_params)
        elif self.connection_type == "sse":
            # SSE 连接
            kargs = {'url' : self.server_config["url"]}
            if "headers" in self.server_config and isinstance(self.server_config["headers"], dict):
                kargs['headers'] = self.server_config["headers"]
            if "timeout" in self.server_config:
                kargs['timeout'] = int(self.server_config["timeout"])
            if "sse_read_timeout" in self.server_config:
                kargs['sse_read_timeout'] = int(self.server_config["sse_read_timeout"])

            return sse_client(**kargs)
        elif self.connection_type == "streamable_http":
            # Streamable HTTP 连接
            kargs = {'url' : self.server_config["url"]}
            if "headers" in self.server_config and isinstance(self.server_config["headers"], dict):
                kargs['headers'] = self.server_config["headers"]
            if "timeout" in self.server_config:
                kargs['timeout'] = timedelta(seconds=int(self.server_config["timeout"]))
            if "sse_read_timeout" in self.server_config:
                kargs['sse_read_timeout'] = timedelta(seconds=int(self.server_config["sse_read_timeout"]))

            return streamablehttp_client(**kargs)
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")

    async def _execute_with_session(self, operation):
        """统一的会话执行方法，处理不同客户端类型的差异"""
        client_session = await self._create_client_session()

        if self.connection_type == "streamable_http":
            async with client_session as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await operation(session)
        else:
            async with client_session as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await operation(session)

    async def _list_tools(self):
        try:
            async def list_operation(session):
                server_tools = await session.list_tools()
                return server_tools.model_dump().get("tools", [])
            
            tools = await self._execute_with_session(list_operation)
            
            if sys.platform == "win32":
                # FIX windows下抛异常的问题
                await asyncio.sleep(3)
            return tools
        except Exception as e:
            logger.exception(f"Failed to list tools: {e}")
            return []

    async def _call_tool(self, tool_name, arguments):
        try:
            async def call_operation(session):
                result = await session.call_tool(tool_name, arguments=arguments)
                return result.model_dump()
            
            ret = await self._execute_with_session(call_operation)
            
            if sys.platform == "win32":
                # FIX windows下抛异常的问题
                await asyncio.sleep(3)
            return ret
        except Exception as e:
            logger.exception(f"Failed to call tool {tool_name}: {e}")
            print(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e), "tool_name": tool_name, "arguments": arguments}

