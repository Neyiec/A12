"""从 Java 业务后台读取已发布的 AI 配置，使用短缓存避免逐页访问。"""

from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

from .teaching_policy import set_published_policies

logger = logging.getLogger(__name__)
_lock = asyncio.Lock()
_next_refresh = 0.0
_image_monthly_quota: int | None = None
_image_model: str | None = None


def image_monthly_quota() -> int:
    fallback = max(0, int(os.getenv("IMAGE_GENERATION_MONTHLY_QUOTA", "100")))
    return fallback if _image_monthly_quota is None else _image_monthly_quota


def image_generation_model(default: str) -> str:
    return _image_model or default


async def refresh_runtime_config() -> None:
    global _next_refresh, _image_monthly_quota, _image_model
    key = os.getenv("A12_PYTHON_INTERNAL_KEY", "")
    if not key or time.monotonic() < _next_refresh:
        return
    async with _lock:
        if time.monotonic() < _next_refresh:
            return
        # 失败时也短暂缓存，避免 Java 暂停期间每个请求重试。
        _next_refresh = time.monotonic() + 30
        url = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{url}/api/v1/internal/ai-runtime-config",
                                            headers={"X-A12-Internal-Key": key})
            response.raise_for_status()
            body = response.json()
            if body.get("code") not in (0, 200) or not isinstance(body.get("data"), dict):
                raise ValueError("运行配置响应无效")
            data = body["data"]
            policies = data.get("teaching_subject", {})
            if not isinstance(policies, dict):
                raise ValueError("学科策略配置无效")
            set_published_policies(policies)
            image = data.get("image_generation", {})
            raw_quota = image.get("monthly_quota") if isinstance(image, dict) else None
            _image_monthly_quota = int(raw_quota) if raw_quota is not None and str(raw_quota).isdecimal() and int(raw_quota) <= 100000 else None
            raw_model = image.get("model") if isinstance(image, dict) else None
            _image_model = raw_model.strip() if isinstance(raw_model, str) and 1 <= len(raw_model.strip()) <= 100 else None
            _next_refresh = time.monotonic() + 60
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning("AI 运行配置刷新失败，保留上次有效配置: %s", exc)
