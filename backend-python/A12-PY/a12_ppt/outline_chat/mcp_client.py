import asyncio
import hashlib
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from jsonschema import ValidationError, validate

from ..config import get_settings


logger = logging.getLogger(__name__)


def _model_tool_name(server: str, tool: str) -> str:
    raw = f"mcp__{server}__{tool}"
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    if normalized == raw and len(normalized) <= 64:
        return normalized
    suffix = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{normalized[:55]}_{suffix}"


@dataclass(frozen=True)
class MCPToolSpec:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return _model_tool_name(self.server, self.name)


class MCPClient:
    """Discover and invoke tools from stdio, SSE and Streamable HTTP MCP servers."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cached_tools: list[MCPToolSpec] = []
        self._cache_initialized = False
        self._cache_expires_at = 0.0
        self._cache_lock = asyncio.Lock()
        self._discovery_logs: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_mcp_tools and self._server_configs())

    async def list_tools(self, force_refresh: bool = False) -> list[MCPToolSpec]:
        if not self.enabled:
            return []
        if not force_refresh and self._cache_initialized and time.monotonic() < self._cache_expires_at:
            return list(self._cached_tools)

        async with self._cache_lock:
            if not force_refresh and self._cache_initialized and time.monotonic() < self._cache_expires_at:
                return list(self._cached_tools)

            self._discovery_logs = []
            configs = self._server_configs()
            results = await asyncio.gather(
                *(self._discover_server(server_name, config) for server_name, config in configs.items()),
                return_exceptions=True,
            )
            specs: list[MCPToolSpec] = []
            for server_name, result in zip(configs, results):
                if isinstance(result, Exception):
                    self._record_discovery(server_name, "failed", 0.0, error=str(result))
                    continue
                specs.extend(result)

            self._cached_tools = specs
            self._cache_initialized = True
            self._cache_expires_at = time.monotonic() + max(0.0, self.settings.mcp_tool_cache_ttl_seconds)
            return list(specs)

    def drain_discovery_logs(self) -> list[dict[str, Any]]:
        logs = list(self._discovery_logs)
        self._discovery_logs.clear()
        return logs

    def invalidate_cache(self) -> None:
        self._cached_tools = []
        self._cache_initialized = False
        self._cache_expires_at = 0.0

    async def call_tool(
        self,
        qualified_name: str,
        arguments: dict[str, Any],
        tool_spec: MCPToolSpec | None = None,
    ) -> dict[str, Any]:
        spec = tool_spec or next(
            (item for item in self._cached_tools if item.qualified_name == qualified_name),
            None,
        )
        if spec is None:
            return {"error": f"MCP tool is not discovered: {qualified_name}", "error_type": "tool_not_found"}

        validation_error = self._validate_arguments(arguments, spec.input_schema)
        if validation_error:
            return {
                "error": validation_error,
                "error_type": "schema_validation",
                "tool": qualified_name,
                "server": spec.server,
            }

        config = self._server_configs().get(spec.server)
        if not config:
            return {"error": f"MCP server not configured: {spec.server}", "error_type": "server_not_found"}

        timeout = max(0.1, self.settings.tool_call_timeout_seconds)
        try:
            return await asyncio.wait_for(self._call_tool_once(spec, config, arguments), timeout=timeout)
        except asyncio.TimeoutError:
            message = f"MCP tool timed out after {timeout:g}s"
            logger.warning("%s server=%s tool=%s", message, spec.server, spec.name)
            return {"error": message, "error_type": "timeout", "tool": qualified_name, "server": spec.server}
        except Exception as exc:
            logger.exception("MCP tool call failed server=%s tool=%s", spec.server, spec.name)
            return {
                "error": str(exc),
                "error_type": "execution",
                "tool": qualified_name,
                "server": spec.server,
            }

    async def _discover_server(self, server_name: str, config: dict[str, Any]) -> list[MCPToolSpec]:
        started = time.perf_counter()
        timeout = max(0.1, self.settings.mcp_discovery_timeout_seconds)
        try:
            specs = await asyncio.wait_for(self._list_server_tools(server_name, config), timeout=timeout)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self._record_discovery(server_name, "success", elapsed_ms, tool_count=len(specs))
            return specs
        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self._record_discovery(
                server_name,
                "failed",
                elapsed_ms,
                error=f"MCP discovery timed out after {timeout:g}s",
            )
            return []
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self._record_discovery(server_name, "failed", elapsed_ms, error=str(exc))
            return []

    async def _list_server_tools(self, server_name: str, config: dict[str, Any]) -> list[MCPToolSpec]:
        async with self._session(server_name, config) as session:
            result = await session.list_tools()
        specs: list[MCPToolSpec] = []
        for tool in getattr(result, "tools", []) or []:
            name = str(getattr(tool, "name", "") or "").strip()
            if not name:
                continue
            specs.append(MCPToolSpec(
                server=server_name,
                name=name,
                description=str(getattr(tool, "description", "") or ""),
                input_schema=self._to_dict(
                    getattr(tool, "inputSchema", None)
                    or getattr(tool, "input_schema", None)
                    or {"type": "object", "properties": {}}
                ),
            ))
        return specs

    async def _call_tool_once(
        self,
        spec: MCPToolSpec,
        config: dict[str, Any],
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._session(spec.server, config) as session:
            result = await session.call_tool(spec.name, arguments or {})
        return self._normalize_tool_result(result)

    def _validate_arguments(self, arguments: dict[str, Any], schema: dict[str, Any]) -> str | None:
        if not schema:
            return None
        try:
            validate(instance=arguments or {}, schema=schema)
            return None
        except ValidationError as exc:
            location = ".".join(str(item) for item in exc.absolute_path)
            prefix = f" at {location}" if location else ""
            return f"MCP tool arguments do not match inputSchema{prefix}: {exc.message}"
        except Exception as exc:
            return f"Invalid MCP inputSchema: {exc}"

    def _record_discovery(
        self,
        server: str,
        status: str,
        latency_ms: float,
        tool_count: int = 0,
        error: str | None = None,
    ) -> None:
        event = {
            "tool": "mcp_discovery",
            "server": server,
            "status": status,
            "latency_ms": latency_ms,
            "tool_count": tool_count,
        }
        if error:
            event["error"] = error
            logger.warning("MCP discovery failed server=%s latency_ms=%s error=%s", server, latency_ms, error)
        else:
            logger.info("MCP discovery succeeded server=%s tools=%s latency_ms=%s", server, tool_count, latency_ms)
        self._discovery_logs.append(event)

    @asynccontextmanager
    async def _session(self, server_name: str, config: dict[str, Any]) -> AsyncIterator[Any]:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

        transport = str(config.get("transport") or config.get("type") or "stdio").lower().replace("-", "_")
        timeout = float(config.get("timeout") or self.settings.tool_call_timeout_seconds)
        read_timeout = float(config.get("sse_read_timeout") or config.get("read_timeout") or 300)
        headers = {str(k): str(v) for k, v in dict(config.get("headers") or {}).items()}

        if transport in {"sse", "server_sent_events"}:
            url = self._required_url(server_name, config)
            async with sse_client(
                url,
                headers=headers or None,
                timeout=timeout,
                sse_read_timeout=read_timeout,
            ) as streams:
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
        params = StdioServerParameters(command=command, args=args, env=env, cwd=config.get("cwd"))
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
        except Exception as exc:
            logger.warning("Unable to parse MCP_SERVERS: %s", exc)
            return {}

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
