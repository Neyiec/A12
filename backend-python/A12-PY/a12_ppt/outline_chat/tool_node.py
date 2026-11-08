import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..llm import LLMClient
from ..ai_runtime import use_auxiliary_reasoning
from ..tools import diagram_tool, should_call_diagram_tool, web_search
from ..tools.rag import search_public_context
from .mcp_client import MCPClient, MCPToolSpec


@dataclass(frozen=True)
class ToolPlan:
    name: str
    args: dict[str, Any]
    source: str
    reason: str = ""
    tool_call_id: str | None = None


class OutlineToolNode:
    """LangGraph tool node combining deterministic rules and native LLM tool calls."""

    def __init__(self, llm: LLMClient | None = None, mcp_client: MCPClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.mcp_client = mcp_client or MCPClient()
        self.settings = get_settings()

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        intent = dict(state.get("intent") or {})
        query = self._build_query(state)
        mcp_specs = await self.mcp_client.list_tools() if self.mcp_client.enabled else []
        discovery_trace = self.mcp_client.drain_discovery_logs() if self.mcp_client.enabled else []

        rule_plans = self._rule_plans(intent, query)
        cached_context = dict(state.get('tool_context') or {})
        if not intent.get("enable_web"):
            cached_context.pop("web", None)
        if not intent.get("enable_rag") or (cached_context.get("rag") or {}).get("search_scope") != "public":
            cached_context.pop("rag", None)
        if cached_context.get('rag'):
            rule_plans = [plan for plan in rule_plans if plan.name != 'rag_search']
        mcp_by_name = {spec.qualified_name: spec for spec in mcp_specs}
        # 已确定的检索立即执行，无需等模型选完可选工具。gather 负责传播取消，
        # 不启动脱离本次请求的后台任务；可选工具仍按原来的去重和权限规则执行。
        rule_plans = self._dedupe_and_filter(rule_plans, intent, mcp_specs)
        autonomous_plans, rule_results = await asyncio.gather(
            self._autonomous_plans(
                intent, query, state, mcp_specs,
                excluded_names={plan.name for plan in rule_plans}
                    | ({'rag_search'} if cached_context.get('rag') else set()),
            ),
            asyncio.gather(*(self._execute_timed(plan, mcp_by_name) for plan in rule_plans)),
        )
        plans = self._dedupe_and_filter([*rule_plans, *autonomous_plans], intent, mcp_specs)
        optional_plans = plans[len(rule_plans):]
        optional_results = await asyncio.gather(
            *(self._execute_timed(plan, mcp_by_name) for plan in optional_plans))
        results = [*rule_results, *optional_results]

        tool_context: dict[str, Any] = cached_context
        tool_trace: list[dict[str, Any]] = list(discovery_trace)
        for plan, (payload, latency_ms) in zip(plans, results):
            self._store_context(tool_context, plan, payload)
            tool_trace.append(self._trace(plan, payload, latency_ms))

        return {"tool_context": tool_context, "tool_trace": tool_trace}

    def _rule_plans(self, intent: dict[str, Any], query: str) -> list[ToolPlan]:
        plans: list[ToolPlan] = []
        if intent.get("enable_rag"):
            plans.append(ToolPlan(
                "rag_search",
                {"query": query},
                "rule",
                "RAG is enabled for this request.",
            ))
        if intent.get("enable_web"):
            # 公网查询仅使用课程标识，不把聊天记录、上传资料或个性化要求发给搜索服务。
            web_query = " ".join(str(intent.get(key) or "").strip() for key in ("title", "subject", "grade")).strip()[:240]
            plans.append(ToolPlan(
                "web_search",
                {"query": web_query, "max_results": 5},
                "rule",
                "Web search is enabled for this request.",
            ))
        if should_call_diagram_tool(intent, query):
            plans.append(ToolPlan(
                "diagram_tool",
                {"intent": intent, "query": query},
                "rule",
                "The request contains diagram/process/concept-map intent.",
            ))
        return plans

    async def _autonomous_plans(
        self,
        intent: dict[str, Any],
        query: str,
        state: dict[str, Any],
        mcp_specs: list[MCPToolSpec],
        excluded_names: set[str],
    ) -> list[ToolPlan]:
        if not self.settings.enable_autonomous_tools or not self.llm.available:
            return []

        tools = self._available_tool_specs(intent, mcp_specs, excluded_names)
        if not tools:
            return []

        planner_context = {
            "intent": intent,
            "query": query,
            "recent_messages": [str(message.content) for message in state.get("messages", [])[-6:]],
            "already_planned_by_rules": sorted(excluded_names),
        }
        messages = [
            SystemMessage(content=(
                "Select optional tools for a teaching-outline workflow. Use only the bound tools. "
                "Do not repeat tools already planned by deterministic rules. Select at most three "
                "tools, and select MCP tools only when their result clearly improves the lesson."
            )),
            HumanMessage(content=json.dumps(planner_context, ensure_ascii=False, default=str)),
        ]
        try:
            with use_auxiliary_reasoning():
                response = await self.llm.invoke_tools(messages, tools, temperature=0.1)
        except Exception:
            return []

        plans: list[ToolPlan] = []
        for tool_call in response.tool_calls or []:
            name = str(tool_call.get("name") or "").strip()
            args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
            if name == "rag_search":
                args = {
                    "query": str(args.get("query") or query),
                    "limit": int(args.get("limit") or 12000),
                }
            elif name == "web_search":
                args = {
                    "query": str(args.get("query") or query),
                    "max_results": int(args.get("max_results") or 5),
                }
            elif name == "diagram_tool":
                args = {
                    "intent": intent,
                    "query": str(args.get("query") or query),
                    "max_nodes": int(args.get("max_nodes") or 6),
                }
            plans.append(ToolPlan(
                name=name,
                args=args,
                source="llm_native",
                reason="Selected by the model through native tool calling.",
                tool_call_id=str(tool_call.get("id") or "") or None,
            ))
        return plans

    async def _execute_timed(
        self,
        plan: ToolPlan,
        mcp_by_name: dict[str, MCPToolSpec],
    ) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        validation_error = self._validate_plan(plan, mcp_by_name)
        if validation_error:
            payload = {"error": validation_error, "error_type": "schema_validation"}
            return payload, round((time.perf_counter() - started) * 1000, 2)

        timeout = max(0.1, self.settings.tool_call_timeout_seconds)
        try:
            payload = await asyncio.wait_for(self._execute_plan(plan, mcp_by_name), timeout=timeout)
        except asyncio.TimeoutError:
            payload = {"error": f"Tool timed out after {timeout:g}s", "error_type": "timeout"}
        except Exception as exc:
            payload = {"error": str(exc), "error_type": "execution"}
        return payload, round((time.perf_counter() - started) * 1000, 2)

    async def _execute_plan(
        self,
        plan: ToolPlan,
        mcp_by_name: dict[str, MCPToolSpec],
    ) -> dict[str, Any]:
        if plan.name == "rag_search":
            return await search_public_context(
                str(plan.args.get("query") or ""),
                min(int(plan.args.get("limit") or 3900), 3900),
            )
        if plan.name == "web_search":
            return await web_search(
                str(plan.args.get("query") or ""),
                int(plan.args.get("max_results") or 5),
            )
        if plan.name == "diagram_tool":
            return await diagram_tool(
                dict(plan.args.get("intent") or {}),
                str(plan.args.get("query") or ""),
                int(plan.args.get("max_nodes") or 6),
            )
        if plan.name.startswith("mcp__"):
            return await self.mcp_client.call_tool(
                plan.name,
                dict(plan.args or {}),
                mcp_by_name.get(plan.name),
            )
        return {"error": f"Unknown tool: {plan.name}", "error_type": "tool_not_found"}

    def _available_tool_specs(
        self,
        intent: dict[str, Any],
        mcp_specs: list[MCPToolSpec],
        excluded_names: set[str],
    ) -> list[dict[str, Any]]:
        schemas = self._built_in_schemas()
        descriptions = {
            "rag_search": "Search the public teaching resource library.",
            "web_search": "Search web pages for supplementary teaching materials.",
            "diagram_tool": "Generate a Mermaid flowchart, timeline, concept map, or comparison diagram.",
        }
        allowed_builtins = {"diagram_tool"}
        if intent.get("enable_rag"):
            allowed_builtins.add("rag_search")
        if intent.get("enable_web"):
            allowed_builtins.add("web_search")

        tools = [
            self._openai_tool(name, descriptions[name], schemas[name])
            for name in allowed_builtins
            if name not in excluded_names
        ]
        for spec in mcp_specs:
            if spec.qualified_name in excluded_names:
                continue
            schema = spec.input_schema or {"type": "object", "properties": {}}
            tools.append(self._openai_tool(
                spec.qualified_name,
                spec.description or f"Tool {spec.name} from MCP server {spec.server}.",
                schema,
            ))
        return tools

    def _openai_tool(self, name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description[:1024],
                "parameters": parameters,
            },
        }

    def _dedupe_and_filter(
        self,
        plans: list[ToolPlan],
        intent: dict[str, Any],
        mcp_specs: list[MCPToolSpec],
    ) -> list[ToolPlan]:
        mcp_names = {spec.qualified_name for spec in mcp_specs}
        allowed = {"diagram_tool"}
        if intent.get("enable_rag"):
            allowed.add("rag_search")
        if intent.get("enable_web"):
            allowed.add("web_search")
        allowed.update(mcp_names)

        deduped: list[ToolPlan] = []
        seen_names: set[str] = set()
        for plan in plans:
            if plan.name not in allowed or plan.name in seen_names:
                continue
            seen_names.add(plan.name)
            deduped.append(plan)
        return deduped[:6]

    def _validate_plan(self, plan: ToolPlan, mcp_by_name: dict[str, MCPToolSpec]) -> str | None:
        if plan.name.startswith("mcp__"):
            spec = mcp_by_name.get(plan.name)
            if spec is None:
                return f"MCP tool is not discovered: {plan.name}"
            schema = spec.input_schema
        else:
            schema = self._built_in_schemas().get(plan.name)
        if not schema:
            return None
        try:
            validate(instance=plan.args, schema=schema)
            return None
        except ValidationError as exc:
            location = ".".join(str(item) for item in exc.absolute_path)
            prefix = f" at {location}" if location else ""
            return f"Tool arguments do not match schema{prefix}: {exc.message}"
        except Exception as exc:
            return f"Invalid tool schema: {exc}"

    def _built_in_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            "rag_search": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 100, "maximum": 50000},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "web_search": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "diagram_tool": {
                "type": "object",
                "properties": {
                    "intent": {"type": "object"},
                    "query": {"type": "string", "minLength": 1},
                    "max_nodes": {"type": "integer", "minimum": 2, "maximum": 12},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        }

    def _store_context(self, tool_context: dict[str, Any], plan: ToolPlan, payload: dict[str, Any]) -> None:
        if plan.name.startswith("mcp__"):
            tool_context.setdefault("mcp", {})[plan.name] = payload
            return
        tool_context[self._context_key(plan.name)] = payload

    def _trace(self, plan: ToolPlan, result: dict[str, Any], latency_ms: float) -> dict[str, Any]:
        trace = {
            "tool": plan.name,
            "tool_call_id": plan.tool_call_id,
            "source": plan.source,
            "reason": plan.reason,
            "status": "error" if result.get("error") else "success",
            "latency_ms": latency_ms,
            "error_type": result.get("error_type"),
        }
        if plan.name == "rag_search":
            trace.update({
                "query": result.get("query"),
                "enriched_query": result.get("enriched_query"),
                "match_count": len(result.get("matches") or []),
                "search_scope": result.get("search_scope"),
                "status": "error" if result.get("error") else (
                    "success" if result.get("context") or result.get("matches") else "empty"
                ),
            })
        elif plan.name == "web_search":
            trace.update({
                "query": result.get("query"),
                "result_count": len(result.get("results") or []),
                "error": result.get("error"),
                "status": "error" if result.get("error") else (
                    "success" if result.get("results") else "empty"
                ),
            })
        elif plan.name == "diagram_tool":
            trace.update({
                "diagram_type": result.get("diagram_type"),
                "format": result.get("format"),
                "node_count": len(result.get("nodes") or []),
                "error": result.get("error"),
            })
        elif plan.name.startswith("mcp__"):
            trace.update({"mcp": True, "error": result.get("error")})
        return trace

    def _context_key(self, tool_name: str) -> str:
        return {
            "rag_search": "rag",
            "web_search": "web",
            "diagram_tool": "diagram",
        }.get(tool_name, tool_name)

    def _build_query(self, state: dict[str, Any]) -> str:
        intent = state.get("intent") or {}
        parts = [
            str(intent.get("title") or ""),
            str(intent.get("subject") or ""),
            str(intent.get("grade") or ""),
            str(intent.get("teaching_goals") or ""),
            " ".join(str(item) for item in intent.get("knowledge_points") or []),
            str(intent.get("requirements") or ""),
        ]
        for message in state.get("messages", [])[-4:]:
            content = getattr(message, "content", "")
            if content:
                parts.append(str(content))
        return "\n".join(part for part in parts if part).strip()
