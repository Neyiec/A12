import asyncio
import json
import re
from typing import Any, AsyncIterator, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from ..llm import LLMClient
from ..models import OutlineChatStreamRequest, OutlineGenerateRequest
from ..presentation import PPTGenerator
from ..presentation.json_utils import extract_json
from ..tools import rag_search, web_search
from .message_utils import message_text, messages_to_dicts, normalize_messages
from .postgres_store import postgres_memory_store
from .session_store import outline_session_store


class OutlineChatState(TypedDict, total=False):
    user_id: str
    session_id: str
    request: OutlineChatStreamRequest
    messages: list[BaseMessage]
    intent: dict[str, Any]
    teacher_profile: dict[str, Any] | None
    tool_context: dict[str, Any]
    final_prompt: str
    clarification_question: str
    outline: dict[str, Any]
    response: dict[str, Any]
    memory_result: dict[str, Any]
    error: str


class OutlineChatWorkflow:
    def __init__(self, generator: PPTGenerator | None = None) -> None:
        self.generator = generator or PPTGenerator()
        self.llm = LLMClient()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(OutlineChatState)
        graph.add_node("load_profile", self._load_profile_node)
        graph.add_node("parse_input", self._parse_input_node)
        graph.add_node("tools", self._tools_node)
        graph.add_node("build_prompt", self._build_prompt_node)
        graph.add_node("generate_outline", self._generate_outline_node)
        graph.add_node("memory", self._memory_node)

        graph.add_edge(START, "load_profile")
        graph.add_edge("load_profile", "parse_input")
        graph.add_conditional_edges(
            "parse_input",
            self._after_parse,
            {"clarify": END, "continue": "tools"},
        )
        graph.add_edge("tools", "build_prompt")
        graph.add_edge("build_prompt", "generate_outline")
        graph.add_conditional_edges(
            "generate_outline",
            self._after_generate,
            {"memory": "memory", "failed": END},
        )
        graph.add_edge("memory", END)
        return graph.compile()

    async def stream(self, request: OutlineChatStreamRequest) -> AsyncIterator[dict[str, Any]]:
        user_id = request.user_id.strip()
        session_id, saved = outline_session_store.load_or_create(user_id, request.session_id)
        state: OutlineChatState = {
            "user_id": user_id,
            "session_id": session_id,
            "request": request,
            "messages": normalize_messages(saved.get("messages", [])),
            "intent": {**saved.get("intent", {}), **request.known_context},
            "outline": saved.get("outline", {}),
            "final_prompt": saved.get("final_prompt", ""),
        }

        yield {"event": "session", "data": {"user_id": user_id, "session_id": session_id}}

        final_state = dict(state)
        async for chunk in self.graph.astream(state, stream_mode="updates"):
            node_name, node_update = next(iter(chunk.items()))
            final_state.update(node_update or {})

            if node_name == "load_profile":
                yield {"event": "stage", "data": {"name": "load_profile", "message": "Loaded long-term teacher profile"}}

            elif node_name == "parse_input":
                outline_session_store.save(user_id, session_id, self._session_snapshot(final_state))
                if final_state.get("clarification_question"):
                    question = final_state["clarification_question"]
                    outline_session_store.append_message(user_id, session_id, "assistant", question, {"type": "clarification"})
                    yield {
                        "event": "question",
                        "data": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "question": question,
                            "intent": final_state.get("intent", {}),
                        },
                    }
                    yield {"event": "done", "data": {"status": "need_clarification", "user_id": user_id, "session_id": session_id}}
                    return
                yield {"event": "stage", "data": {"name": "parse_input", "message": "Parsed user input and merged known context"}}

            elif node_name == "tools":
                yield {"event": "stage", "data": {"name": "tools", "message": "Executed enabled RAG and web tools"}}
                yield {"event": "tool_result", "data": final_state.get("tool_context", {})}

            elif node_name == "build_prompt":
                yield {"event": "stage", "data": {"name": "build_prompt", "message": "Built final outline prompt"}}

            elif node_name == "generate_outline":
                if final_state.get("error"):
                    yield {"event": "error", "data": {"stage": "generate_outline", "message": final_state["error"], "user_id": user_id, "session_id": session_id}}
                    yield {"event": "done", "data": {"status": "failed", "user_id": user_id, "session_id": session_id}}
                    return
                outline_session_store.save(user_id, session_id, self._session_snapshot(final_state), status="completed")
                postgres_memory_store.save_generation(user_id, session_id, final_state["response"], final_state.get("final_prompt", ""))
                yield {"event": "stage", "data": {"name": "generate_outline", "message": "Generated structured outline"}}

            elif node_name == "memory":
                yield {"event": "stage", "data": {"name": "memory", "message": "Evaluated teacher-style long-term memory"}}
                yield {"event": "memory", "data": final_state.get("memory_result", {})}

        response = final_state.get("response")
        if not response:
            yield {"event": "error", "data": {"stage": "workflow", "message": "Outline workflow ended without a response", "user_id": user_id, "session_id": session_id}}
            yield {"event": "done", "data": {"status": "failed", "user_id": user_id, "session_id": session_id}}
            return

        for slide in response.get("slides", []):
            yield {"event": "outline_delta", "data": {"user_id": user_id, "session_id": session_id, "slide": slide}}
            await asyncio.sleep(0)

        yield {"event": "final", "data": {"user_id": user_id, "session_id": session_id, **response}}
        yield {"event": "done", "data": {"status": "completed", "user_id": user_id, "session_id": session_id}}

    async def run_once(self, request: OutlineChatStreamRequest) -> dict[str, Any]:
        final: dict[str, Any] = {}
        async for event in self.stream(request):
            if event["event"] in {"question", "final"}:
                final = event["data"]
        return final

    async def _load_profile_node(self, state: OutlineChatState) -> dict[str, Any]:
        profile = postgres_memory_store.get_teacher_profile(state["user_id"])
        return {"teacher_profile": profile}

    async def _parse_input_node(self, state: OutlineChatState) -> dict[str, Any]:
        request = state["request"]
        user_id = state["user_id"]
        session_id = state["session_id"]
        messages = normalize_messages(state.get("messages", []))
        messages.extend(HumanMessage(content=message.content) if message.role == "user" else AIMessage(content=message.content) for message in request.history)
        messages.append(HumanMessage(content=request.message))

        outline_session_store.append_message(user_id, session_id, "user", request.message, {
            "resource_ids": request.resource_ids,
            "enable_rag": request.enable_rag,
            "enable_web": request.enable_web,
        })

        extracted = await self._extract_intent_with_model(messages, state.get("intent", {}))
        if not extracted:
            extracted = self._extract_intent_heuristic(request.message)

        intent = self._merge_intent(state.get("intent", {}), extracted)
        intent.setdefault("slide_count", request.slide_count or 8)
        intent.setdefault("language", request.language)
        intent["enable_web"] = request.enable_web
        intent["enable_rag"] = request.enable_rag
        intent["resource_ids"] = request.resource_ids
        intent["user_id"] = user_id
        if state.get("teacher_profile"):
            intent["teacher_profile"] = state["teacher_profile"]

        question = self._clarification_question(intent)
        updates: dict[str, Any] = {"messages": messages, "intent": intent}
        if question:
            updates["clarification_question"] = question
            messages.append(AIMessage(content=question))
        return updates

    async def _tools_node(self, state: OutlineChatState) -> dict[str, Any]:
        intent = state["intent"]
        query = self._build_rag_query(state)
        tool_context: dict[str, Any] = {}
        if intent.get("enable_rag") and intent.get("resource_ids"):
            tool_context["rag"] = await rag_search(list(intent.get("resource_ids") or []), query)
        if intent.get("enable_web"):
            tool_context["web"] = await web_search(query, max_results=5)
        return {"tool_context": tool_context}

    async def _build_prompt_node(self, state: OutlineChatState) -> dict[str, Any]:
        intent = state["intent"]
        tool_context = state.get("tool_context", {})
        prompt = f"""
Generate a structured teaching PPT outline that closely follows the user's real intent.

Merged intent:
{json.dumps(intent, ensure_ascii=False, indent=2, default=str)}

Tool context:
{json.dumps(tool_context, ensure_ascii=False, indent=2, default=str)[:14000]}

Requirements:
1. Output an editable structured outline for later HTML PPT generation.
2. Each slide must include slide_no, title, slide_type, content_points, teaching_intent, visual_suggestion.
3. Prefer effective information from RAG resources when RAG is enabled.
4. Reflect stable teacher preferences from teacher_profile when available.
5. Keep slide count close to slide_count.
""".strip()
        return {"final_prompt": prompt}

    async def _generate_outline_node(self, state: OutlineChatState) -> dict[str, Any]:
        try:
            intent = state["intent"]
            reference_parts = []
            tool_context = state.get("tool_context", {})
            if tool_context.get("rag", {}).get("context"):
                reference_parts.append(tool_context["rag"]["context"])
            if tool_context.get("web", {}).get("results"):
                reference_parts.append(json.dumps(tool_context["web"]["results"], ensure_ascii=False))
            if state.get("final_prompt"):
                reference_parts.append(state["final_prompt"])

            req = OutlineGenerateRequest(
                title=str(intent.get("title") or "未命名主题"),
                subject=str(intent.get("subject") or "通用"),
                grade=str(intent.get("grade") or "通用"),
                duration_minutes=int(intent["duration_minutes"]) if str(intent.get("duration_minutes") or "").isdigit() else None,
                teaching_goals=str(intent.get("teaching_goals") or "") or None,
                knowledge_points=list(intent.get("knowledge_points") or []),
                requirements=str(intent.get("requirements") or "") or None,
                reference_text="\n\n".join(reference_parts),
                resource_ids=list(intent.get("resource_ids") or []),
                enable_web=bool(intent.get("enable_web")),
                enable_rag=bool(intent.get("enable_rag")),
                slide_count=int(intent.get("slide_count") or 8),
                language=str(intent.get("language") or "zh-CN"),
            )
            response = await self.generator.generate_outline(req)
            return {"outline": response.get("outline", {}), "response": response}
        except Exception as exc:
            return {"error": str(exc)}

    async def _memory_node(self, state: OutlineChatState) -> dict[str, Any]:
        user_text = "\n".join(message_text(message) for message in state.get("messages", []) if isinstance(message, HumanMessage))[-6000:]
        evaluation = await self._evaluate_teacher_style(user_text, state.get("intent", {}))
        if not evaluation.get("should_store"):
            return {"memory_result": {"stored": False, "reason": evaluation.get("reason", "No stable teacher-style preference found")}}

        postgres_memory_store.save_teacher_style_memory(
            state["user_id"],
            state["session_id"],
            user_text,
            evaluation.get("style") or {},
            float(evaluation.get("score") or 0.7),
            str(evaluation.get("reason") or "User input contains reusable teacher-style preference"),
        )
        return {
            "memory_result": {
                "stored": True,
                "score": evaluation.get("score", 0.7),
                "reason": evaluation.get("reason"),
                "style": evaluation.get("style"),
                "postgres_available": postgres_memory_store.available,
            }
        }

    def _after_parse(self, state: OutlineChatState) -> Literal["clarify", "continue"]:
        return "clarify" if state.get("clarification_question") else "continue"

    def _after_generate(self, state: OutlineChatState) -> Literal["memory", "failed"]:
        return "failed" if state.get("error") else "memory"

    async def _extract_intent_with_model(self, messages: list[BaseMessage], known: dict[str, Any]) -> dict[str, Any]:
        if not self.llm.available:
            return {}
        prompt = f"""
Extract the user's outline-generation parameters from the multi-turn conversation.
Merge them with known fields. Return strict JSON only.

Known fields:
{json.dumps(known, ensure_ascii=False, default=str)}

Conversation:
{json.dumps(messages_to_dicts(messages[-12:]), ensure_ascii=False)}

Allowed fields:
title, subject, grade, duration_minutes, teaching_goals, knowledge_points,
requirements, slide_count, language.

Do not invent uncertain fields.
""".strip()
        try:
            raw = await self.llm.complete("Return parseable JSON only.", prompt, 0.15)
            data = json.loads(extract_json(raw))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _extract_intent_heuristic(self, message: str) -> dict[str, Any]:
        text = message.strip()
        intent: dict[str, Any] = {}
        slide_match = re.search(r"(\d{1,2})\s*(页|张|p|P)", text)
        if slide_match:
            intent["slide_count"] = int(slide_match.group(1))

        grade_match = re.search(r"(一年级|二年级|三年级|四年级|五年级|六年级|七年级|八年级|九年级|[1-9]年级|高一|高二|高三|初一|初二|初三|小学|初中|高中|大学)", text)
        if grade_match:
            intent["grade"] = grade_match.group(1)

        for subject in ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "科学", "信息技术"]:
            if subject in text:
                intent["subject"] = subject
                break

        title = self._infer_title(text, intent)
        if title:
            intent["title"] = title
        if text:
            intent["requirements"] = text
        if "光合作用" in text and "subject" not in intent:
            intent["subject"] = "生物"
        return intent

    def _infer_title(self, text: str, intent: dict[str, Any]) -> str:
        patterns = [
            r"(?:主题|标题|课题)\s*(?:是|为|:|：)?\s*([^，。；;\n]{2,40})",
            r"(?:关于|讲)\s*([^，。；;\n]{2,30})\s*(?:的)?\s*(?:PPT|课件|大纲)",
            r"(?:做|生成|制作)\s*(?:一个|一份)?\s*([^，。；;\n]{2,30})\s*(?:的)?\s*(?:PPT|课件|大纲)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = self._clean_title(match.group(1), intent)
                if value:
                    return value
        value = re.sub(r"(帮我|请|麻烦|做一个|生成|制作|大纲|课件|PPT|ppt)", "", text)
        value = self._clean_title(value, intent)
        return value if 2 <= len(value) <= 40 else ""

    def _clean_title(self, title: str, intent: dict[str, Any]) -> str:
        value = re.sub(r"\d{1,2}\s*(页|张|p|P)", "", title)
        if intent.get("grade"):
            value = value.replace(str(intent["grade"]), "")
        if intent.get("subject"):
            value = value.replace(str(intent["subject"]), "")
        return value.strip(" ，。；;:：")

    def _merge_intent(self, current: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current or {})
        for key, value in (extracted or {}).items():
            if value not in (None, "", [], {}):
                merged[key] = value
        if isinstance(merged.get("knowledge_points"), str):
            merged["knowledge_points"] = [item.strip() for item in re.split(r"[，,、\n]", merged["knowledge_points"]) if item.strip()]
        return merged

    def _build_rag_query(self, state: OutlineChatState) -> str:
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

    def _clarification_question(self, intent: dict[str, Any]) -> str:
        missing = []
        if not intent.get("title"):
            missing.append("课程/PPT主题")
        if not intent.get("grade"):
            missing.append("年级或受众")
        if not intent.get("subject"):
            missing.append("学科")
        if not missing:
            return ""
        return "为了生成更贴近你意图的大纲，请补充：" + "、".join(missing) + "。"

    async def _evaluate_teacher_style(self, user_text: str, intent: dict[str, Any]) -> dict[str, Any]:
        if self.llm.available:
            prompt = f"""
Decide whether this user input should be stored as long-term teacher-style memory.
Only store stable reusable preferences, such as interaction style, teaching method,
language style, assessment preference, or classroom rhythm.
Do not store one-off topic, subject, grade, or slide-count requirements.

User input:
{user_text}

Parsed intent:
{json.dumps(intent, ensure_ascii=False, default=str)}

Return strict JSON:
{{
  "should_store": true,
  "score": 0.0,
  "reason": "...",
  "style": {{
    "summary": "...",
    "teaching_methods": [],
    "interaction_preference": "",
    "language_style": "",
    "assessment_preference": "",
    "evidence": []
  }}
}}
""".strip()
            try:
                raw = await self.llm.complete("Return JSON only.", prompt, 0.15)
                data = json.loads(extract_json(raw))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        keywords = {
            "互动": "偏好课堂互动",
            "提问": "偏好问题驱动",
            "启发": "偏好启发式教学",
            "探究": "偏好探究式学习",
            "小组": "偏好小组合作",
            "案例": "偏好案例教学",
            "项目式": "偏好项目式学习",
            "分层": "偏好分层教学",
            "幽默": "偏好轻松幽默表达",
            "严谨": "偏好严谨清晰表达",
        }
        hits = [label for key, label in keywords.items() if key in user_text]
        if not hits:
            return {"should_store": False, "score": 0.0, "reason": "Input is mainly a one-off generation request."}
        return {
            "should_store": True,
            "score": min(0.95, 0.55 + len(hits) * 0.1),
            "reason": "User input contains reusable teaching-style preferences.",
            "style": {
                "summary": "；".join(hits),
                "teaching_methods": hits,
                "interaction_preference": "；".join(item for item in hits if "互动" in item or "提问" in item or "小组" in item),
                "language_style": "幽默" if "偏好轻松幽默表达" in hits else ("严谨" if "偏好严谨清晰表达" in hits else ""),
                "assessment_preference": "",
                "evidence": hits,
            },
        }

    def _session_snapshot(self, state: OutlineChatState) -> dict[str, Any]:
        return {
            "user_id": state["user_id"],
            "session_id": state["session_id"],
            "messages": messages_to_dicts(state.get("messages", [])),
            "intent": state.get("intent", {}),
            "final_prompt": state.get("final_prompt", ""),
            "outline": state.get("outline", {}),
        }
