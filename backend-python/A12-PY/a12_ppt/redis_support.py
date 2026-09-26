"""Redis 基础能力：缓存、版本号、原子限流和分布式并发租约。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from .config import get_settings

logger = logging.getLogger("a12_ppt.redis")


class RedisSupport:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._disabled_until = 0.0

    def key(self, *parts: object) -> str:
        suffix = ":".join(str(part).replace(" ", "_") for part in parts)
        return f"{self.settings.redis_key_prefix}:{suffix}"

    async def client(self):
        if time.monotonic() < self._disabled_until:
            return None
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    self.settings.redis_url, encoding="utf-8", decode_responses=True,
                    socket_connect_timeout=1.0, socket_timeout=2.0, health_check_interval=30,
                )
            except Exception as exc:
                self._mark_unavailable(exc)
                return None
        return self._client

    async def ping(self) -> bool:
        client = await self.client()
        if client is None:
            return False
        try:
            return bool(await client.ping())
        except Exception as exc:
            self._mark_unavailable(exc)
            return False

    async def get_json(self, key: str) -> Any | None:
        client = await self.client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            self._mark_unavailable(exc)
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        client = await self.client()
        if client is None:
            return False
        try:
            await client.set(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), ex=ttl_seconds)
            return True
        except Exception as exc:
            self._mark_unavailable(exc)
            return False

    async def increment_version(self, name: str) -> int:
        client = await self.client()
        if client is None:
            return 0
        try:
            return int(await client.incr(self.key("version", name)))
        except Exception as exc:
            self._mark_unavailable(exc)
            return 0

    async def get_version(self, name: str) -> int:
        client = await self.client()
        if client is None:
            return 0
        try:
            return int(await client.get(self.key("version", name)) or 0)
        except Exception as exc:
            self._mark_unavailable(exc)
            return 0

    async def assert_rate_limit(self, subject: str, operation: str, limit: int, window_seconds: int = 60) -> None:
        client = await self.client()
        if client is None:
            return
        bucket = int(time.time()) // window_seconds
        key = self.key("quota", operation, subject, bucket)
        script = """
        local value = redis.call('INCR', KEYS[1])
        if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
        return value
        """
        try:
            count = int(await client.eval(script, 1, key, window_seconds + 5))
            if count > limit:
                raise RuntimeError(f"AI 请求过于频繁，请稍后再试（每分钟最多 {limit} 次）")
        except RuntimeError:
            raise
        except Exception as exc:
            self._mark_unavailable(exc)

    async def acquire_semaphore(self, name: str, limit: int, lease_seconds: int = 900) -> str | None:
        client = await self.client()
        if client is None:
            return "redis-unavailable"
        key = self.key("semaphore", name)
        token = uuid.uuid4().hex
        now_ms = int(time.time() * 1000)
        expires_ms = now_ms + lease_seconds * 1000
        script = """
        redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
        if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
        redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
        redis.call('EXPIRE', KEYS[1], ARGV[5])
        return 1
        """
        try:
            acquired = int(await client.eval(script, 1, key, now_ms, expires_ms, limit, token, lease_seconds + 30))
            return token if acquired == 1 else None
        except Exception as exc:
            self._mark_unavailable(exc)
            return "redis-unavailable"

    async def release_semaphore(self, name: str, token: str | None) -> None:
        if not token or token == "redis-unavailable":
            return
        client = await self.client()
        if client is None:
            return
        try:
            await client.zrem(self.key("semaphore", name), token)
        except Exception as exc:
            self._mark_unavailable(exc)

    def _mark_unavailable(self, exc: Exception) -> None:
        self._disabled_until = time.monotonic() + 10.0
        logger.warning("Redis 暂时不可用，降级为本地执行: %s", exc)


redis_support = RedisSupport()


@asynccontextmanager
async def ai_request_guard(user_id: str | None, operation: str, *, apply_rate_limit: bool = True) -> AsyncIterator[None]:
    settings = get_settings()
    subject = (user_id or "anonymous").strip() or "anonymous"
    if apply_rate_limit:
        await redis_support.assert_rate_limit(subject, operation, settings.ai_rate_limit_per_minute)
    global_token = await redis_support.acquire_semaphore("ai:global", settings.ai_global_concurrency)
    if global_token is None:
        raise RuntimeError("当前 AI 生成任务较多，请稍后重试")
    user_token = await redis_support.acquire_semaphore(f"ai:user:{subject}", settings.ai_user_concurrency)
    if user_token is None:
        await redis_support.release_semaphore("ai:global", global_token)
        raise RuntimeError("当前账号已有生成任务正在执行，请稍后重试")
    try:
        yield
    finally:
        await redis_support.release_semaphore(f"ai:user:{subject}", user_token)
        await redis_support.release_semaphore("ai:global", global_token)
