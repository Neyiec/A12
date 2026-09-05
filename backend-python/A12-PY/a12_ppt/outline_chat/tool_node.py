import asyncio
import json
from dataclasses import dataclass
from typing import Any

from ..config import get_settings
from ..llm import LLMClient
from ..tools import diagram_tool, rag_search, should_call_diagram_tool, web_search
from .mcp_client import MCPClient, MCPToolSpec


@dataclass(frozen=True)
class ToolPlan:
    name: str
    args: dict[str, Any]
    source: str
    reason: str = ""


class OutlineToolNode:
    """Unified outline tool node.

    It combines three sources:
    1. Deterministic rules for stable business behavior.
    2. LLM autonomous planning for optional extra tools.
    3. Optional MCP server tools configured by environment variables.
    """

    def __init__(self, llm: LLMClient | None = None, mcp_client: MCPClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.mcp_client = mcp_client or MCPClient()
        self.settings = get_settings()

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        intent = dict(state.get("intent") or {})
        query = self._build_query(state)
        mcp_specs = await self.mcp_client.list_tools() if self.mcp_client.enabled else []

        plans = self._rule_plans(intent, query)
        plans.extend(await self._autonomous_plans(intent, query, state, mcp_specs))
        plans = self._dedupe_and_filter(plans, intent, mcp_specs)

        if not plans:
            return {"tool_context": {}, "tool_trace": []}

        results = await asyncio.gather(
            *(self._execute_plan(plan) for plan in plans),
            return_exceptions=True,
        )

        tool_context: dict[str, Any] = {}
        tool_trace: list[dict[str, Any]] = []
        for plan, result in zip(plans, results):
            if isinstance(result, Exception):
                payload: dict[str, Any] = {"error": str(result)}
            else:
                payload = result if isinstance(result, dict) else {"result": result}
            context_key = self._context_key(plan.name)
            if context_key in tool_context:
                existing = tool_context[context_key]
                if isinstance(existing, list):
                    existing.append(payload)
                else:
                    tool_context[context_key] = [existing, payload]
            else:
                tool_context[context_key] = payload
            tool_trace.append(self._trace(plan, payload))

        return {"tool_context": tool_context, "tool_trace": tool_trace}

    def _rule_plans(self, intent: dict[str, Any], query: str) -> list[ToolPlan]:
        plans: list[ToolPlan] = []
        if intent.get("enable_rag"):
            plans.append(ToolPlan(
                "rag_search",
                {"resource_ids": list(intent.get("resource_ids") or []), "query": query},
                "rule",
                "RAG is enabled for this request.",
            ))
        if intent.get("enable_web"):
            plans.append(ToolPlan(
                "web_search",
                {"query": query, "max_results": 5},
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
    ) -> list[ToolPlan]:
        if not self.settings.enable_autonomous_tools or not self.llm.available:
            return []

        tool_specs = self._available_tool_specs(intent, mcp_specs)
        if not tool_specs:
            return []

        prompt = f"""
You are planning tools for a teaching-outline generation workflow.
Return strict JSON array only. Each item:
{{"tool": "...", "args": {{}}, "reason": "..."}}

Rules:
- Only choose tools from available_tools.
- Do not call rag_search if enable_rag is false.
- Do not call web_search if enable_web is false.
- Prefer 0-3 tools. Use MCP tools only when they clearly add value.
- Do not invent arguments outside the tool schema.

Intent:
{json.dumps(intent, ensure_ascii=False, default=str)}

Query:
{query}

Available tools:
{json.dumps(tool_specs, ensure_ascii=False, default=str)}

Existing messages:
{json.dumps([str(m.content) for m in state.get("messages", [])[-6:]], ensure_ascii=False)}
""".strip()
        try:
            raw = await self.llm.complete("Return strict JSON only.", prompt, temperature=0.1)
            parsed = json.loads(self._extract_json_value(raw))
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []

        plans: list[ToolPlan] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = str(item.get("tool") or item.get("name") or "").strip()
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            if name == "rag_search":
                args = {"resource_ids": list(intent.get("resource_ids") or []), "query": str(args.get("query") or query)}
            elif name == "web_search":
                args = {"query": str(args.get("query") or query), "max_results": int(args.get("max_results") or 5)}
            elif name == "diagram_tool":
                args = {"intent": intent, "query": str(args.get("query") or query)}
            plans.append(ToolPlan(name, args, "llm", str(item.get("reason") or "")))
        return plans

    async def _execute_plan(self, plan: ToolPlan) -> dict[str, Any]:
        if plan.name == "rag_search":
            return await rag_search(
                list(plan.args.get("resource_ids") or []),
                str(plan.args.get("query") or ""),
                int(plan.args.get("limit") or 12000),
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
            return await self.mcp_client.call_tool(plan.name, dict(plan.args or {}))
        return {"error": f"Unknown tool: {plan.name}"}

    def _available_tool_specs(self, intent: dict[str, Any], mcp_specs: list[MCPToolSpec]) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        if intent.get("enable_rag"):
            specs.append({
                "name": "rag_search",
                "description": "Search local/global teaching knowledge base. Uploaded references enrich query but are not the retrieval scope.",
                "args": {"query": "string", "resource_ids": "list[string]"},
            })
        if intent.get("enable_web"):
            specs.append({
                "name": "web_search",
                "description": "Search web pages for fresh supplementary teaching materials.",
                "args": {"query": "string", "max_results": "integer"},
            })
        specs.append({
            "name": "diagram_tool",
            "description": "Generate Mermaid diagram assets for flowcharts, timelines, concept maps, or comparison diagrams.",
            "args": {"query": "string"},
        })
        for spec in mcp_specs:
            specs.append({
                "name": spec.qualified_name,
                "description": spec.description,
                "input_schema": spec.input_schema,
            })
        return specs

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
        seen: set[str] = set()
        for plan in plans:
            if plan.name not in allowed:
                continue
            key = json.dumps({"name": plan.name, "args": plan.args}, ensure_ascii=False, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(plan)
        return deduped[:6]

    def _trace(self, plan: ToolPlan, result: dict[str, Any]) -> dict[str, Any]:
        trace = {
            "tool": plan.name,
            "source": plan.source,
            "reason": plan.reason,
            "status": "error" if result.get("error") else "success",
        }
        if plan.name == "rag_search":
            trace.update({
                "query": result.get("query"),
                "enriched_query": result.get("enriched_query"),
                "match_count": len(result.get("matches") or []),
                "search_scope": result.get("search_scope"),
                "status": "success" if result.get("context") or result.get("matches") else "empty",
            })
        elif plan.name == "web_search":
            trace.update({
                "query": result.get("query"),
                "result_count": len(result.get("results") or []),
                "error": result.get("error"),
                "status": "error" if result.get("error") else ("success" if result.get("results") else "empty"),
            })
        elif plan.name == "diagram_tool":
            trace.update({
                "diagram_type": result.get("diagram_type"),
                "format": result.get("format"),
                "node_count": len(result.get("nodes") or []),
            })
        elif plan.name.startswith("mcp__"):
            trace.update({"mcp": True, "error": result.get("error")})
        return trace

    def _context_key(self, tool_name: str) -> str:
        if tool_name == "rag_search":
            return "rag"
        if tool_name == "web_search":
            return "web"
        if tool_name == "diagram_tool":
            return "diagram"
        if tool_name.startswith("mcp__"):
            return "mcp"
        return tool_name

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

    def _extract_json_value(self, raw: str) -> str:
        text = (raw or "").strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                candidate = part.strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("[") or candidate.startswith("{"):
                    return candidate
        array_start = text.find("[")
        array_end = text.rfind("]")
        if array_start >= 0 and array_end > array_start:
            return text[array_start:array_end + 1]
        object_start = text.find("{")
        object_end = text.rfind("}")
        if object_start >= 0 and object_end > object_start:
            return text[object_start:object_end + 1]
        return text
