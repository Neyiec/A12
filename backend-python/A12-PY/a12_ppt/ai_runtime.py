"""Per-request model routing, readiness probes and lightweight observability."""
import json
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from .config import get_settings


@dataclass(frozen=True)
class RuntimeOptions:
    user_id: str | None = None
    operation: str = "unknown"
    model_profile: str = "standard"
    reasoning_effort: str = "medium"
    run_id: str = ""


_runtime: ContextVar[RuntimeOptions] = ContextVar("a12_ai_runtime", default=RuntimeOptions())


@contextmanager
def use_runtime_options(user_id: str | None = None, operation: str = "unknown",
                        model_profile: str = "standard", reasoning_effort: str = "medium"):
    options = RuntimeOptions(user_id, operation, model_profile, reasoning_effort, f"run_{uuid.uuid4().hex[:16]}")
    token = _runtime.set(options)
    try:
        yield options
    finally:
        _runtime.reset(token)


def current_runtime() -> RuntimeOptions:
    return _runtime.get()


def routed_model(profile: str | None = None) -> str:
    settings = get_settings()
    profile = (profile or current_runtime().model_profile or "standard").lower()
    mapping = {
        "fast": getattr(settings, "openai_model_fast", "") or settings.openai_model,
        "standard": getattr(settings, "openai_model_standard", "") or settings.openai_model,
        "deep": getattr(settings, "openai_model_deep", "") or settings.openai_model,
        "vision": getattr(settings, "openai_model_vision", "") or settings.openai_model,
    }
    return mapping.get(profile, mapping["standard"])


def record_run(status: str, latency_ms: int, model: str, *, fallback_reason: str | None = None,
               input_tokens: int = 0, output_tokens: int = 0, metadata: dict[str, Any] | None = None) -> None:
    options = current_runtime()
    try:
        import psycopg
        with psycopg.connect(get_settings().postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO a12_ai_run_log
                  (run_id,user_id,operation,model,model_profile,reasoning_effort,status,latency_ms,
                   input_tokens,output_tokens,fallback_reason,metadata)
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""", (
                    options.run_id or f"run_{uuid.uuid4().hex[:16]}", options.user_id, options.operation,
                    model, options.model_profile, options.reasoning_effort, status, latency_ms,
                    input_tokens, output_tokens, fallback_reason, json.dumps(metadata or {}, ensure_ascii=False),
                ))
    except Exception:
        pass


async def probe_model() -> dict[str, Any]:
    from .direct_auth import require_active_browser_token
    await require_active_browser_token()
    settings = get_settings()
    if not settings.openai_api_key:
        return {"configured": False, "available": False, "status": "not_configured"}
    started = time.perf_counter()
    try:
        from .llm.model_factory import create_chat_model
        model_name = routed_model("fast")
        model = create_chat_model(model_name, settings.openai_api_key, settings.openai_base_url,
                                  min(settings.request_timeout_seconds, 15), 0.0, "low")
        response = await model.ainvoke("仅回复OK")
        return {"configured": True, "available": bool(response.content), "status": "available",
                "model": model_name, "latency_ms": round((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        message = str(exc)
        status = "quota_exhausted" if "quota" in message.lower() or "freetier" in message.lower() else "unavailable"
        return {"configured": True, "available": False, "status": status,
                "model": routed_model("fast"), "error": message[:300],
                "latency_ms": round((time.perf_counter() - started) * 1000)}
