import time
from typing import AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from ..config import get_settings
from ..direct_auth import require_active_browser_token
from .model_factory import create_chat_model
from ..ai_runtime import current_runtime, record_run, routed_model
from ..timing import timed, timing_stage, log_timing


def _record_run(*args, **kwargs):
    with timing_stage("audit.write"):
        record_run(*args, **kwargs)


class LLMClient:
    """大模型服务类"""
    def __init__(self) -> None:
        self.settings = get_settings()

    """判断是否存在API_KEY"""
    @property
    def available(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.45) -> str:
        return await self.complete_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ], temperature=temperature)

    @timed("llm.total")
    async def complete_messages(self, messages: list[BaseMessage], temperature: float = 0.45) -> str:
        if not self.available:
            return ""

        with timing_stage("auth.redis"):
            await require_active_browser_token()

        runtime = current_runtime()
        model_name = routed_model()
        started = time.perf_counter()
        try:
            request_options = {"max_retries": runtime.max_retries} if runtime.max_retries is not None else {}
            model = create_chat_model(model_name, self.settings.openai_api_key, self.settings.openai_base_url,
                                      runtime.request_timeout_seconds or self.settings.request_timeout_seconds,
                                      temperature, runtime.reasoning_effort, **request_options)
            with timing_stage("llm.request", model=model_name, reasoning=runtime.reasoning_effort):
                response = await model.ainvoke(messages)
        except Exception as exc:
            _record_run("failed", round((time.perf_counter() - started) * 1000), model_name, fallback_reason=str(exc)[:300])
            raise
        usage = getattr(response, "usage_metadata", None) or {}
        _record_run("success", round((time.perf_counter() - started) * 1000), model_name,
                   input_tokens=int(usage.get("input_tokens") or 0), output_tokens=int(usage.get("output_tokens") or 0),
                   metadata={"reasoning_effort": runtime.reasoning_effort})
        content = response.content
        if isinstance(content, str):
            return content
        return "".join(str(part) for part in content)

    @timed("llm.stream_total")
    async def complete_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.45) -> AsyncIterator[str]:
        """流式补全：逐 token 产出文本片段。模型不可用时直接结束（不产出任何片段）。"""
        if not self.available:
            return
        with timing_stage("auth.redis"):
            await require_active_browser_token()
        runtime = current_runtime()
        model_name = routed_model()
        started = time.perf_counter()
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        try:
            model = create_chat_model(model_name, self.settings.openai_api_key, self.settings.openai_base_url,
                                      self.settings.request_timeout_seconds, temperature, runtime.reasoning_effort)
            produced = False
            async for chunk in model.astream(messages):
                content = chunk.content
                if isinstance(content, str):
                    text = content
                else:
                    text = "".join(str(part) for part in content) if content else ""
                if text:
                    if not produced:
                        log_timing("llm.first_token", (time.perf_counter() - started) * 1000, model=model_name)
                    produced = True
                    yield text
            if not produced:
                raise RuntimeError("模型没有返回可显示的正文")
            _record_run("success", round((time.perf_counter() - started) * 1000), model_name)
        except Exception as exc:
            _record_run("failed", round((time.perf_counter() - started) * 1000), model_name, fallback_reason=str(exc)[:300])
            raise
