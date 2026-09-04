import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage

from ..config import get_settings
from ..llm import LLMClient
from ..presentation.json_utils import extract_json
from ..tools import diagram_tool, rag_search, should_call_diagram_tool, web_search
from .message_utils import message_text


class OutlineToolNode:
    """Hybrid tool node: deterministic business tools plus LLM-planned tools."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMClient()

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        intent = state.get("intent", {})
        query = self._build_query(state)
        rule_calls = self._rule_tool_calls(intent, query)
        autonomous_calls = await self._autonomous_tool_calls(state, intent, query, rule_calls)
        tool_calls = self._dedupe_tool_calls([*rule_calls, *autonomous_calls])

        results = await asyncio.gather(
            *(self._execute_tool_call(call, intent, query) for call in tool_calls),
            return_exceptions=False,
        )

        tool_context: dict[str, Any] = {}
        tool_trace: list[dict[str, Any]] = []
        for item in results:
            name = item["tool"]
            result = item["result"]
            context_key = self._context_key(name)
            if context_key:
                if context_key not in tool_context:
                    tool_context[context_key] = result
                else:
                    tool_context.setdefault("additional_results", []).append({"tool": name, "result": result})
            tool_trace.append(item["trace"])

        if autonomous_calls:
            tool_context["autonomous_tool_plan"] = {
                "enabled": True,
                "planned_tools": [
                    {
                        "tool": call["name"],
                        "reason": call.get("reason", ""),
                        "source": call.get("source", "model"),
                    }
                    for call in autonomous_calls
                ],
            }
        elif self.settings.enable_autonomous_tools:
            tool_context["autonomous_tool_plan"] = {"enabled": True, "planned_tools": []}

        return {"tool_context": tool_context, "tool_trace": tool_trace}

    def _rule_tool_calls(self, intent: dict[str, Any], query: str) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []
        if intent.get("enable_rag"):
            calls.append({
                "name": "rag_search",
                "args": {"resource_ids": list(intent.get("resource_ids") or []), "query": query},
                "source": "rule",
                "reason": "enable_rag=true",
            })
        if intent.get("enable_web"):
            calls.append({
                "name": "web_search",
                "args": {"query": query, "max_results": 5},
                "source": "rule",
                "reason": "enable_web=true",
            })
        if should_call_diagram_tool(intent, query):
            calls.append({
                "name": "diagram_tool",
                "args": {"query": query},
                "source": "rule",
                "reason": "diagram/process/concept-map intent detected",
            })
        return calls

    async def _autonomous_tool_calls(
        self,
        state: dict[str, Any],
        intent: dict[str, Any],
        query: str,
        rule_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not (self.settings.enable_autonomous_tools and self.llm.available):
            return []

        allowed_tools = ["diagram_tool"]
        if intent.get("enable_rag"):
            allowed_tools.append("rag_search")
        if intent.get("enable_web"):
            allowed_tools.append("web_search")

        prompt = f"""
You are the tool planner for a teaching outline agent.
Decide whether extra tools are needed after deterministic rule calls.
Return strict JSON only.

Allowed tools:
- rag_search: search local knowledge base. Only useful when enable_rag=true.
- web_search: search web. Only useful when enable_web=true.
- diagram_tool: create Mermaid diagram for process, comparison, relation, timeline, or concept-map content.

Already planned by rules:
{json.dumps([{"tool": call["name"], "reason": call.get("reason", "")} for call in rule_calls], ensure_ascii=False)}

Intent:
{json.dumps(intent, ensure_ascii=False, default=str)[:8000]}

Latest retrieval/query text:
{query[:4000]}

Output format:
{{
  "tool_calls": [
    {{
      "name": "rag_search|web_search|diagram_tool",
      "args": {{"query": "optional rewritten query"}},
      "reason": "why this tool is needed"
    }}
  ]
}}

Rules:
1. Only choose from allowed tools: {allowed_tools}.
2. Do not repeat a tool that is already planned unless the rewritten query is clearly different.
3. Prefer no extra tool if the rule calls are enough.
4. Never call web_search unless enable_web=true.
5. Never call rag_search unless enable_rag=true.
""".strip()
        try:
            raw = await self.llm.complete("You output only valid JSON for tool planning.", prompt, 0.1)
            data = json.loads(extract_json(raw))
        except Exception:
            return []

        planned: list[dict[str, Any]] = []
        for raw_call in data.get("tool_calls") or []:
            if not isinstance(raw_call, dict):
                continue
            name = str(raw_call.get("name") or "").strip()
            if name not in allowed_tools:
                continue
            args = raw_call.get("args") if isinstance(raw_call.get("args"), dict) else {}
            planned.append({
                "name": name,
                "args": {
                    "query": str(args.get("query") or query),
                    "resource_ids": list(intent.get("resource_ids") or []),
                    "max_results": int(args.get("max_results") or 5) if str(args.get("max_results") or "").isdigit() else 5,
                },
                "source": "model",
                "reason": str(raw_call.get("reason") or "model-planned tool call"),
            })
        return planned

    async def _execute_tool_call(self, call: dict[str, Any], intent: dict[str, Any], default_query: str) -> dict[str, Any]:
        name = call["name"]
        args = call.get("args") or {}
        query = str(args.get("query") or default_query)
        try:
            if name == "rag_search":
                result = await rag_search(list(args.get("resource_ids") or intent.get("resource_ids") or []), query)
                trace = {
                    "tool": name,
                    "source": call.get("source", "rule"),
                    "status": "success" if result.get("context") or result.get("matches") else "empty",
                    "reason": call.get("reason", ""),
                    "query": result.get("query"),
                    "enriched_query": result.get("enriched_query"),
                    "match_count": len(result.get("matches") or []),
                    "search_scope": result.get("search_scope"),
                }
            elif name == "web_search":
                result = await web_search(query, max_results=int(args.get("max_results") or 5))
                trace = {
                    "tool": name,
                    "source": call.get("source", "rule"),
                    "status": "error" if result.get("error") else ("success" if result.get("results") else "empty"),
                    "reason": call.get("reason", ""),
                    "query": result.get("query"),
                    "result_count": len(result.get("results") or []),
                    "error": result.get("error"),
                }
            elif name == "diagram_tool":
                result = await diagram_tool(intent, query)
                trace = {
                    "tool": name,
                    "source": call.get("source", "rule"),
                    "status": "success",
                    "reason": call.get("reason", ""),
                    "diagram_type": result.get("diagram_type"),
                    "format": result.get("format"),
                    "node_count": len(result.get("nodes") or []),
                }
            else:
                result = {"error": f"Unknown tool: {name}"}
                trace = {"tool": name, "source": call.get("source", "unknown"), "status": "error", "error": result["error"]}
        except Exception as exc:
            result = {"error": str(exc)}
            trace = {
                "tool": name,
                "source": call.get("source", "unknown"),
                "status": "error",
                "reason": call.get("reason", ""),
                "error": str(exc),
            }
        return {"tool": name, "result": result, "trace": trace}

    def _dedupe_tool_calls(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for call in calls:
            name = str(call.get("name") or "")
            query = str((call.get("args") or {}).get("query") or "").strip()
            key = (name, query[:500])
            if not name or key in seen:
                continue
            seen.add(key)
            deduped.append(call)
        return deduped

    def _context_key(self, tool_name: str) -> str:
        return {
            "rag_search": "rag",
            "web_search": "web",
            "diagram_tool": "diagram",
        }.get(tool_name, "")

    def _build_query(self, state: dict[str, Any]) -> str:
        intent = state.get("intent", {})
        latest_user_text = ""
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage):
                latest_user_text = message_text(message)
                break

        parts = [
            latest_user_text,
            str(intent.get("title") or ""),
            str(intent.get("subject") or ""),
            str(intent.get("grade") or ""),
            str(intent.get("teaching_goals") or ""),
            " ".join(str(item) for item in intent.get("knowledge_points") or []),
            str(intent.get("requirements") or ""),
        ]
        return "\n".join(part for part in parts if part).strip()
