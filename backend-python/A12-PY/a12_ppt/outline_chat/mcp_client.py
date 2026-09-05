import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from ..config import get_settings


@dataclass(frozen=True)
class MCPToolSpec:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return f"mcp__{self.server}__{self.name}"


class MCPClient:
    """MCP client for stdio, SSE and Streamable HTTP servers.

    Example:
    MCP_SERVERS={
      "python_mcp": {"transport":"sse","url":"http://127.0.0.1:8080/sse"},
      "my12306": {"type":"streamable_http","url":"https://.../mcp"},
      "chart": {"type":"streamable_http","url":"https://.../mcp"}
    }
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_mcp_tools and self._server_configs())

    async def list_tools(self) -> list[MCPToolSpec]:
        if not self.enabled:
            return []
        specs: list[MCPToolSpec] = []
        for server_name, config in self._server_configs().items():
            try:
                async with self._session(server_name, config) as session:
                    result = await session.list_tools()
                    for tool in getattr(result, "tools", []) or []:
                        specs.append(MCPToolSpec(
                            server=server_name,
                            name=str(getattr(tool, "name", "") or ""),
                            description=str(getattr(tool, "description", "") or ""),
                            input_schema=self._to_dict(getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}),
                        ))
            except Exception:
                continue
        return [spec for spec in specs if spec.name]

    async def call_tool(self, qualified_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        parsed = self._parse_qualified_name(qualified_name)
        if not parsed:
            return {"error": f"Invalid MCP tool name: {qualified_name}"}
        server_name, tool_name = parsed
        config = self._server_configs().get(server_name)
        if not config:
            return {"error": f"MCP server not configured: {server_name}"}
        try:
            async with self._session(server_name, config) as session:
                result = await session.call_tool(tool_name, arguments or {})
                return self._normalize_tool_result(result)
        except Exception as exc:
            return {"error": str(exc), "tool": qualified_name}

    @asynccontextmanager
    async def _session(self, server_name: str, config: dict[str, Any]) -> AsyncIterator[Any]:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

        transport = str(config.get("transport") or config.get("type") or "stdio").lower().replace("-", "_")
        timeout = float(config.get("timeout") or 30)
        read_timeout = float(config.get("sse_read_timeout") or config.get("read_timeout") or 300)
        headers = {str(k): str(v) for k, v in dict(config.get("headers") or {}).items()}

        if transport in {"sse", "server_sent_events"}:
            url = self._required_url(server_name, config)
            async with sse_client(url, headers=headers or None, timeout=timeout, sse_read_timeout=read_timeout) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    yield session
            return

        if transport in {"streamable_http", "streamablehttp", "http"}:
            url = self._required_url(server_name, config)
            async with create_mcp_http_client(headers=headers or None) as http_client:
                async with streamable_http_client(url, http_client=http_client) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        yield session
            return

        command = str(config.get("command") or "")
        if not command:
            raise ValueError(f"MCP server {server_name} missing command")
        args = [str(item) for item in list(config.get("args") or [])]
        extra_env = config.get("env") if isinstance(config.get("env"), dict) else {}
        env = {**os.environ, **{str(key): str(value) for key, value in extra_env.items()}}
        cwd = config.get("cwd")
        params = StdioServerParameters(command=command, args=args, env=env, cwd=cwd)
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                yield session

    def _server_configs(self) -> dict[str, dict[str, Any]]:
        raw = self.settings.mcp_servers.strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            return {str(name): config for name, config in data.items() if isinstance(config, dict)}
        except Exception:
            return {}

    def _parse_qualified_name(self, value: str) -> tuple[str, str] | None:
        if not value.startswith("mcp__"):
            return None
        parts = value.split("__", 2)
        if len(parts) != 3 or not parts[1] or not parts[2]:
            return None
        return parts[1], parts[2]

    def _required_url(self, server_name: str, config: dict[str, Any]) -> str:
        url = str(config.get("url") or "").strip()
        if not url:
            raise ValueError(f"MCP server {server_name} missing url")
        return url

    def _normalize_tool_result(self, result: Any) -> dict[str, Any]:
        data = self._to_dict(result)
        content = data.get("content")
        if isinstance(content, list):
            data["text"] = "\n".join(
                str(item.get("text") or item.get("data") or item)
                for item in content
                if isinstance(item, dict)
            )
        return data if isinstance(data, dict) else {"result": data}

    def _to_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        return {}
