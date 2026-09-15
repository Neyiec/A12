import json
import re
from typing import Any, AsyncIterator, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph

from ..llm import LLMClient
from ..models import IntentRecognizeRequest, OutlineChatStreamRequest, OutlineGenerateRequest
from ..presentation import PPTGenerator
from ..presentation.json_utils import extract_json
from ..tools import diagram_tool, rag_search, should_call_diagram_tool, web_search
from .message_utils import message_text, messages_to_dicts, normalize_messages
from .postgres_store import postgres_memory_store
from .session_store import outline_session_store


class OutlineChatState(MessagesState, total=False):
    """生成课件大纲的所有状态记录(审计日志)"""
    user_id: str
    session_id: str
    request: OutlineChatStreamRequest
    intent: dict[str, Any]
    teacher_profile: dict[str, Any] | None
    tool_context: dict[str, Any]
    tool_trace: list[dict[str, Any]]
    interactive_policy: dict[str, Any]
    final_prompt: str
    clarification_question: str
    outline: dict[str, Any]
    response: dict[str, Any]
    reflection: dict[str, Any]
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
        graph.add_node("reflect", self._reflection_node)
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
            {"memory": "reflect", "failed": END},
        )
        graph.add_edge("reflect", "memory")
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
        # updates:节点返回值; custom:节点内 get_stream_writer 实时产出的事件(如逐页 outline_delta)
        async for mode, chunk in self.graph.astream(state, stream_mode=["updates", "custom"]):
            if mode == "custom":
                if isinstance(chunk, dict) and chunk.get("event"):
                    yield chunk
                continue

            node_name, node_update = next(iter(chunk.items()))
            self._merge_stream_update(final_state, node_update or {})

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
                assistant_text = self._assistant_outline_message(final_state["response"])
                final_state["messages"] = [
                    *normalize_messages(final_state.get("messages", [])),
                    AIMessage(content=assistant_text),
                ]
                yield {"event": "stage", "data": {"name": "generate_outline", "message": "Generated structured outline"}}

            elif node_name == "reflect":
                # 只归档反思修订后的最终稿，并替换会话中初稿摘要。
                final_response = final_state["response"]
                final_messages = normalize_messages(final_state.get("messages", []))
                if final_messages and isinstance(final_messages[-1], AIMessage):
                    final_messages[-1] = AIMessage(content=self._assistant_outline_message(final_response))
                    final_state["messages"] = final_messages
                final_assistant_text = self._assistant_outline_message(final_response)
                outline_session_store.append_message(
                    user_id,
                    session_id,
                    "assistant",
                    final_assistant_text,
                    {
                        "type": "outline_result",
                        "outline_id": final_response.get("outline_id"),
                        "slide_count": final_response.get("slide_count"),
                        "title": final_response.get("title"),
                        "reflection": final_response.get("reflection", {}),
                    },
                )
                postgres_memory_store.save_generation(user_id, session_id, final_response, final_state.get("final_prompt", ""))
                outline_session_store.save(user_id, session_id, self._session_snapshot(final_state), status="completed")
                yield {"event": "stage", "data": {"name": "reflect", "message": "Reflected on outline quality and tool usage"}}
                yield {"event": "reflection", "data": final_state.get("reflection", {})}
                yield {"event": "outline_replace", "data": {"slides": final_response.get("slides", []), "preview": False}}

            elif node_name == "memory":
                yield {"event": "stage", "data": {"name": "memory", "message": "Evaluated teacher-style long-term memory"}}
                yield {"event": "memory", "data": final_state.get("memory_result", {})}

        response = final_state.get("response")
        if not response:
            yield {"event": "error", "data": {"stage": "workflow", "message": "Outline workflow ended without a response", "user_id": user_id, "session_id": session_id}}
            yield {"event": "done", "data": {"status": "failed", "user_id": user_id, "session_id": session_id}}
            return

        yield {"event": "final", "data": {"user_id": user_id, "session_id": session_id, **response}}
        yield {"event": "done", "data": {"status": "completed", "user_id": user_id, "session_id": session_id}}

    async def run_once(self, request: OutlineChatStreamRequest) -> dict[str, Any]:
        final: dict[str, Any] = {}
        async for event in self.stream(request):
            if event["event"] in {"question", "final"}:
                final = event["data"]
        return final

    async def recognize_intent(self, request: IntentRecognizeRequest) -> dict[str, Any]:
        user_id = (request.user_id or "").strip()
        session_id = ""
        saved: dict[str, Any] = {"messages": [], "intent": {}, "final_prompt": "", "outline": {}}
        if user_id:
            session_id, saved = outline_session_store.load_or_create(user_id, request.session_id)
            if request.title:
                saved["title"] = request.title

        saved_messages = normalize_messages(saved.get("messages", [])) if user_id else []
        history_messages = [] if saved_messages else request.history
        messages: list[BaseMessage] = [
            HumanMessage(content=message.content) if message.role == "user" else AIMessage(content=message.content)
            for message in history_messages
        ]
        new_user_message = HumanMessage(content=request.message)
        conversation = [*saved_messages, *messages, new_user_message]

        if user_id and session_id:
            outline_session_store.append_message(user_id, session_id, "user", request.message, {
                "type": "intent_recognition_input",
                "input_type": request.input_type,
                "resource_ids": request.resource_ids,
                "enable_rag": request.enable_rag,
                "enable_web": request.enable_web,
            })

        known_context = {**(saved.get("intent") or {}), **request.known_context}
        extracted = await self._extract_intent_with_model(conversation, known_context)
        model_used = bool(extracted)
        if not extracted:
            extracted = self._extract_intent_heuristic(request.message)

        intent = self._merge_intent(known_context, extracted)
        intent.setdefault("slide_count", request.slide_count or 8)
        intent.setdefault("language", request.language)
        intent["enable_web"] = request.enable_web
        intent["enable_rag"] = request.enable_rag
        intent["resource_ids"] = request.resource_ids
        if user_id:
            intent["user_id"] = user_id

        interactive_policy = self._interactive_policy(intent, request.message)
        if interactive_policy.get("needs_interactive_assets"):
            intent["interactive_policy"] = interactive_policy

        missing_fields = self._missing_required_fields(intent)
        clarification_question = self._clarification_question(intent)
        result = {
            "intent": intent,
            "need_clarification": bool(missing_fields),
            "missing_fields": missing_fields,
            "clarification_question": clarification_question,
            "confidence": self._intent_confidence(intent, model_used, missing_fields),
            "input_type": request.input_type,
            "model_used": model_used,
        }
        if user_id and session_id:
            result["user_id"] = user_id
            result["session_id"] = session_id
            result["postgres_available"] = postgres_memory_store.available
            outline_session_store.append_message(
                user_id,
                session_id,
                "assistant",
                self._assistant_intent_message(result),
                {
                    "type": "intent_recognition_result",
                    "intent": intent,
                    "need_clarification": bool(missing_fields),
                    "missing_fields": missing_fields,
                    "confidence": result["confidence"],
                    "input_type": request.input_type,
                },
            )
            saved["intent"] = intent
            saved["messages"] = messages_to_dicts([*conversation, AIMessage(content=self._assistant_intent_message(result))])
            outline_session_store.save(user_id, session_id, saved, status="intent_recognized" if not missing_fields else "need_clarification")
        return result

    async def _load_profile_node(self, state: OutlineChatState) -> dict[str, Any]:
        profile = postgres_memory_store.get_teacher_profile(state["user_id"])
        return {"teacher_profile": profile}

    async def _parse_input_node(self, state: OutlineChatState) -> dict[str, Any]:
        request = state["request"]
        user_id = state["user_id"]
        session_id = state["session_id"]
        messages = normalize_messages(state.get("messages", []))
        history_messages = [] if messages else request.history
        new_messages: list[BaseMessage] = [
            HumanMessage(content=message.content) if message.role == "user" else AIMessage(content=message.content)
            for message in history_messages
        ]
        new_messages.append(HumanMessage(content=request.message))
        conversation = [*messages, *new_messages]

        outline_session_store.append_message(user_id, session_id, "user", request.message, {
            "resource_ids": request.resource_ids,
            "enable_rag": request.enable_rag,
            "enable_web": request.enable_web,
        })

        extracted = await self._extract_intent_with_model(conversation, state.get("intent", {}))
        if not extracted:
            extracted = self._extract_intent_heuristic(request.message)

        intent = self._merge_intent(state.get("intent", {}), extracted)
        intent.setdefault("slide_count", request.slide_count or 8)
        intent.setdefault("language", request.language)
        intent["enable_web"] = request.enable_web
        intent["enable_rag"] = request.enable_rag
        intent["resource_ids"] = request.resource_ids
        intent["user_id"] = user_id
        interactive_policy = self._interactive_policy(intent, request.message)
        if interactive_policy.get("needs_interactive_assets"):
            intent["interactive_policy"] = interactive_policy
        if state.get("teacher_profile"):
            intent["teacher_profile"] = state["teacher_profile"]

        question = self._clarification_question(intent)
        updates: dict[str, Any] = {"messages": new_messages, "intent": intent, "interactive_policy": interactive_policy}
        if question:
            updates["clarification_question"] = question
            updates["messages"] = [*new_messages, AIMessage(content=question)]
        return updates

    async def _tools_node(self, state: OutlineChatState) -> dict[str, Any]:
        intent = state["intent"]
        query = self._build_rag_query(state)
        tool_context: dict[str, Any] = {}
        tool_trace: list[dict[str, Any]] = []
        if intent.get("enable_rag"):
            result = await rag_search(list(intent.get("resource_ids") or []), query)
            tool_context["rag"] = result
            tool_trace.append({
                "tool": "rag_search",
                "status": "success" if result.get("context") or result.get("matches") else "empty",
                "query": result.get("query"),
                "enriched_query": result.get("enriched_query"),
                "match_count": len(result.get("matches") or []),
                "search_scope": result.get("search_scope"),
            })
        if intent.get("enable_web"):
            result = await web_search(query, max_results=5)
            tool_context["web"] = result
            tool_trace.append({
                "tool": "web_search",
                "status": "error" if result.get("error") else ("success" if result.get("results") else "empty"),
                "query": result.get("query"),
                "result_count": len(result.get("results") or []),
                "error": result.get("error"),
            })
        if should_call_diagram_tool(intent, query):
            result = await diagram_tool(intent, query)
            tool_context["diagram"] = result
            tool_trace.append({
                "tool": "diagram_tool",
                "status": "success",
                "diagram_type": result.get("diagram_type"),
                "format": result.get("format"),
                "node_count": len(result.get("nodes") or []),
            })
        return {"tool_context": tool_context, "tool_trace": tool_trace}

    async def _build_prompt_node(self, state: OutlineChatState) -> dict[str, Any]:
        intent = state["intent"]
        tool_context = state.get("tool_context", {})
        prompt = f"""
生成一份严格贴合教师真实意图、可用于课堂实施的结构化 PPT 大纲。

合并后的当前意图：
{json.dumps(intent, ensure_ascii=False, indent=2, default=str)}

教师长期风格画像（本轮明确要求优先级更高）：
{json.dumps(state.get("teacher_profile") or {}, ensure_ascii=False, default=str)}

工具上下文：
{json.dumps(tool_context, ensure_ascii=False, indent=2, default=str)[:14000]}

要求：
1. 输出可编辑结构化大纲，供后续 HTML PPT 生成使用。
2. 每页包含 slide_no、title、slide_type、content_points、teaching_intent、visual_suggestion、
   engagement_hook、student_task、teacher_prompt、understanding_check、estimated_minutes。
3. 上传资料用于版式、语气、案例和个性化适配；RAG 命中内容作为本地权威知识补充。
4. 教师长期画像决定稳定教学风格，本轮 requirements、class_level 等特定需求始终优先。
5. teaching_design_chain 需包含教学目标、学情、重难点、教学顺序、活动、评价、分层支持、
   参与度策略与作业。
6. 包含封面、学习路径、内容、活动或练习、总结；每 2 至 3 个内容页安排一次学生任务或即时检测。
7. 开场使用真实问题/预测/投票，结尾使用回忆、迁移题和出口条，避免整节课连续被动听讲。
8. 若图示工具返回 Mermaid，加入顶层 diagram_assets，并在相关页说明用途。
9. 若 interactive_policy.needs_interactive_assets=true，加入顶层 interactive_assets；每项包含
   asset_id、title、type、target_slide_no、preferred_format、integration 和 description。
""".strip()
        return {"final_prompt": prompt}

    async def _generate_outline_node(self, state: OutlineChatState) -> dict[str, Any]:
        writer = get_stream_writer()
        try:
            req = self._outline_request_from_state(state)
            response: dict[str, Any] = {}
            # 模型边产出边回传 outline_delta，用户可实时看到大纲页逐条生成
            async for item in self.generator.stream_outline(req):
                if item.get("type") == "slide":
                    writer({
                        "event": "outline_delta",
                        "data": {
                            "user_id": state["user_id"],
                            "session_id": state["session_id"],
                            "slide": item.get("slide"),
                            "index": item.get("index"),
                            "preview": True,
                        },
                    })
                elif item.get("type") == "final":
                    response = item.get("response") or {}
            if not response.get("slides"):
                return {"error": "Unable to generate outline"}
            self._attach_tool_outputs(response, state)
            return {"outline": response.get("outline", {}), "response": response}
        except Exception as exc:
            return {"error": str(exc)}

    async def _reflection_node(self, state: OutlineChatState) -> dict[str, Any]:
        response = dict(state.get("response") or {})
        if not response:
            return {"reflection": {"status": "skipped", "issues": ["没有可供反思的大纲结果。"], "retry_count": 0}}

        reflection = self._build_generation_reflection(response, state)
        if reflection["status"] == "needs_revision" and reflection["retry_count"] == 0:
            try:
                fix_instruction = self._reflection_fix_instruction(reflection)
                req = self._outline_request_from_state(state, regenerate_instruction=fix_instruction)
                retry_response = await self.generator.generate_outline(req)
                self._attach_tool_outputs(retry_response, state)
                retry_reflection = self._build_generation_reflection(retry_response, state)
                reflection["retry_count"] = 1
                reflection["fixes"].append(fix_instruction)
                reflection["after_retry"] = {
                    "status": retry_reflection.get("status"),
                    "issues": retry_reflection.get("issues", []),
                    "quality_passed": retry_reflection.get("quality_passed"),
                }
                response = retry_response
            except Exception as exc:
                reflection["fixes"].append(f"自动修订失败：{exc}")

        response["reflection"] = reflection
        response["tool_trace"] = state.get("tool_trace", [])
        if isinstance(response.get("outline"), dict):
            response["outline"]["reflection"] = reflection
            response["outline"]["tool_trace"] = state.get("tool_trace", [])
        return {"reflection": reflection, "response": response, "outline": response.get("outline", {})}

    async def _memory_node(self, state: OutlineChatState) -> dict[str, Any]:
        user_text = "\n".join(message_text(message) for message in state.get("messages", []) if isinstance(message, HumanMessage))[-6000:]
        evaluation = await self._evaluate_teacher_style(user_text, state.get("intent", {}))
        if not evaluation.get("should_store"):
            return {"memory_result": {"stored": False, "reason": evaluation.get("reason", "No stable teacher-style preference found")}}

        stored = postgres_memory_store.save_teacher_style_memory(
            state["user_id"],
            state["session_id"],
            user_text,
            evaluation.get("style") or {},
            float(evaluation.get("score") or 0.7),
            str(evaluation.get("reason") or "User input contains reusable teacher-style preference"),
        )
        return {
            "memory_result": {
                "stored": bool(stored),
                "score": evaluation.get("score", 0.7),
                "reason": evaluation.get("reason"),
                "style": evaluation.get("style"),
                "postgres_available": postgres_memory_store.available,
            }
        }

    def _outline_request_from_state(self, state: OutlineChatState, regenerate_instruction: str | None = None) -> OutlineGenerateRequest:
        intent = state["intent"]
        reference_parts = []
        tool_context = state.get("tool_context", {})
        if tool_context.get("rag", {}).get("context"):
            reference_parts.append(tool_context["rag"]["context"])
        if tool_context.get("web", {}).get("results"):
            reference_parts.append(json.dumps(tool_context["web"]["results"], ensure_ascii=False))
        if tool_context.get("diagram", {}).get("mermaid"):
            reference_parts.append("[Diagram tool]\n" + json.dumps(tool_context["diagram"], ensure_ascii=False))
        if state.get("final_prompt"):
            reference_parts.append(state["final_prompt"])
        if regenerate_instruction:
            reference_parts.append("[Reflection revision instruction]\n" + regenerate_instruction)

        return OutlineGenerateRequest(
            title=str(intent.get("title") or "Untitled topic"),
            subject=str(intent.get("subject") or "General"),
            grade=str(intent.get("grade") or "General"),
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
            regenerate_instruction=regenerate_instruction,
            interactive_policy=dict(intent.get("interactive_policy") or state.get("interactive_policy") or {}),
        )

    def _attach_tool_outputs(self, response: dict[str, Any], state: OutlineChatState) -> None:
        tool_context = state.get("tool_context", {})
        diagram = tool_context.get("diagram")
        if diagram:
            asset = {
                "asset_id": "diagram_1",
                "title": diagram.get("title"),
                "type": diagram.get("diagram_type"),
                "format": diagram.get("format"),
                "mermaid": diagram.get("mermaid"),
                "usage": diagram.get("usage"),
            }
            if not response.get("diagram_assets"):
                response["diagram_assets"] = [asset]
            if isinstance(response.get("outline"), dict):
                if not response["outline"].get("diagram_assets"):
                    response["outline"]["diagram_assets"] = [asset]
        response["tool_trace"] = state.get("tool_trace", [])
        if isinstance(response.get("outline"), dict):
            response["outline"]["tool_trace"] = state.get("tool_trace", [])

    def _build_generation_reflection(self, response: dict[str, Any], state: OutlineChatState) -> dict[str, Any]:
        report = response.get("quality_report") or (response.get("outline") or {}).get("quality_report") or {}
        checks = report.get("checks") if isinstance(report, dict) else {}
        issues = []
        if isinstance(checks, dict):
            issues.extend([f"quality_check_failed:{key}" for key, passed in checks.items() if not passed])
        missing_points = report.get("missing_knowledge_points") if isinstance(report, dict) else []
        for point in missing_points or []:
            issues.append(f"missing_knowledge_point:{point}")
        if not state.get("tool_trace"):
            issues.append("no_tool_called")

        quality_passed = bool(report.get("passed")) if isinstance(report, dict) else False
        status = "passed" if quality_passed and not issues else "needs_revision"
        if issues == ["no_tool_called"]:
            status = "passed"
        return {
            "status": status,
            "quality_passed": quality_passed,
            "issues": issues,
            "fixes": [],
            "retry_count": 0,
            "tool_trace": state.get("tool_trace", []),
            "summary": "生成质量符合要求。" if status == "passed" else "生成结果存在质量问题，应自动修订一次。",
        }

    def _reflection_fix_instruction(self, reflection: dict[str, Any]) -> str:
        issues = reflection.get("issues") or []
        return (
            "请修订大纲并解决以下质量问题："
            + "；".join(str(issue) for issue in issues)
            + "。保持用户意图和页数，保留完整教学设计链，并确保封面、学习路径、课堂活动、总结及每页的教学意图、视觉建议、学生任务和理解检测齐全。"
        )

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
requirements, slide_count, language, needs_animation, needs_game,
interactive_requirements, preferred_interactive_formats.

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
        lowered = text.lower()
        if any(keyword in lowered for keyword in ["animation", "animate", "html5", "gif", "mp4", "video"]) or any(keyword in text for keyword in ["动画", "动效", "演示动画", "视频"]):
            intent["needs_animation"] = True
        if any(keyword in lowered for keyword in ["game", "quiz", "mini game"]) or any(keyword in text for keyword in ["小游戏", "小 游戏", "互动游戏", "闯关", "配对", "答题游戏", "游戏化"]):
            intent["needs_game"] = True
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

    def _interactive_policy(self, intent: dict[str, Any], latest_message: str) -> dict[str, Any]:
        text = " ".join(
            str(part or "")
            for part in [
                latest_message,
                intent.get("requirements"),
                intent.get("interactive_requirements"),
                " ".join(str(item) for item in intent.get("preferred_interactive_formats") or []),
            ]
        ).lower()
        animation_keywords = ["animation", "animate", "animated", "html5", "gif", "mp4", "video", "动画", "动效", "演示动画", "视频"]
        game_keywords = ["game", "quiz", "小游戏", "小 游戏", "互动游戏", "闯关", "配对", "答题游戏", "游戏化"]
        needs_animation = bool(intent.get("needs_animation")) or any(keyword in text for keyword in animation_keywords)
        needs_game = bool(intent.get("needs_game")) or any(keyword in text for keyword in game_keywords)
        formats = [candidate for candidate in ["mp4", "html5", "gif"] if candidate in text]
        if not formats and (needs_animation or needs_game):
            formats = ["html5"]
        return {
            "needs_interactive_assets": needs_animation or needs_game,
            "needs_animation": needs_animation,
            "needs_game": needs_game,
            "preferred_formats": formats,
            "ppt_integration_rule": (
                "Use mp4 for direct PPT video embedding when available; package html5/gif/game files under static/ "
                "and place relative links plus textual descriptions in the PPT."
            ),
        }

    def _clarification_question(self, intent: dict[str, Any]) -> str:
        missing = self._missing_required_fields(intent)
        if not missing:
            return ""
        return "为了生成更贴近你意图的大纲，请补充：" + "、".join(self._missing_field_labels(missing)) + "。"

    def _missing_required_fields(self, intent: dict[str, Any]) -> list[str]:
        missing = []
        if not intent.get("title"):
            missing.append("title")
        if not intent.get("grade"):
            missing.append("grade")
        if not intent.get("subject"):
            missing.append("subject")
        return missing

    def _missing_field_labels(self, fields: list[str]) -> list[str]:
        labels = {
            "title": "课程/PPT主题",
            "grade": "年级或受众",
            "subject": "学科",
        }
        return [labels.get(field, field) for field in fields]

    def _intent_confidence(self, intent: dict[str, Any], model_used: bool, missing_fields: list[str]) -> float:
        required_count = 3
        filled_required = required_count - len(missing_fields)
        useful_optional = sum(
            1
            for key in ["duration_minutes", "teaching_goals", "knowledge_points", "requirements", "interactive_policy"]
            if intent.get(key)
        )
        score = 0.35 + filled_required * 0.15 + min(useful_optional, 4) * 0.06
        if model_used:
            score += 0.12
        return round(max(0.1, min(score, 0.95)), 2)

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
            "tool_trace": state.get("tool_trace", []),
            "reflection": state.get("reflection", {}),
        }

    def _assistant_outline_message(self, response: dict[str, Any]) -> str:
        title = str(response.get("title") or "未命名大纲")
        summary = str(response.get("summary") or "").strip()
        slide_count = int(response.get("slide_count") or len(response.get("slides") or []))
        lines = [f"已生成《{title}》的大纲，共 {slide_count} 页。"]
        if summary:
            lines.append(summary)
        if response.get("interactive_assets"):
            lines.append("已规划动画/小游戏等互动资源，生成 PPT 时会作为静态资源或视频资源处理。")
        return "\n".join(lines)

    def _assistant_intent_message(self, response: dict[str, Any]) -> str:
        intent = response.get("intent") or {}
        title = str(intent.get("title") or "未识别主题")
        subject = str(intent.get("subject") or "未识别学科")
        grade = str(intent.get("grade") or "未识别年级")
        confidence = response.get("confidence")
        if response.get("need_clarification"):
            return f"已识别当前意图：主题={title}，学科={subject}，年级={grade}，置信度={confidence}。{response.get('clarification_question') or ''}"
        return f"已识别当前意图：主题={title}，学科={subject}，年级={grade}，置信度={confidence}。"

    def _merge_stream_update(self, final_state: dict[str, Any], update: dict[str, Any]) -> None:
        if not update:
            return
        for key, value in update.items():
            if key == "messages":
                final_state["messages"] = [
                    *normalize_messages(final_state.get("messages", [])),
                    *normalize_messages(value or []),
                ]
            else:
                final_state[key] = value
