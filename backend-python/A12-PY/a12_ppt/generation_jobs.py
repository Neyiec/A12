"""基于 Redis Stream 的 PPT/教案生成队列和可恢复进度事件。"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
import uuid
from typing import Any, AsyncIterator

from .models import LessonPlanGenerateRequest, PresentationGenerateRequest
from .redis_support import ai_request_guard, redis_support

logger = logging.getLogger("a12_ppt.generation_jobs")


class GenerationJobManager:
    def __init__(self) -> None:
        self.queue_key = redis_support.key("queue", "generation")
        self.group = "a12-generation-workers"
        self.consumer = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self._worker: asyncio.Task | None = None
        self._generator = None
        self._lesson_plan_generator = None

    async def start(self, generator, lesson_plan_generator) -> None:
        self._generator = generator
        self._lesson_plan_generator = lesson_plan_generator
        client = await redis_support.client()
        if client is None:
            logger.warning("Redis 不可用，生成队列未启动；原同步接口仍可使用")
            return
        try:
            await client.xgroup_create(self.queue_key, self.group, id="0-0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                logger.warning("创建生成队列消费组失败: %s", exc)
                return
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop(), name="a12-generation-worker")

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass

    async def enqueue(self, kind: str, payload: dict[str, Any], user_id: str | None) -> dict[str, Any]:
        client = await redis_support.client()
        if client is None or not await redis_support.ping():
            raise RuntimeError("Redis 生成队列暂不可用，请使用原生成接口或稍后重试")
        subject = (user_id or "anonymous").strip() or "anonymous"
        await redis_support.assert_rate_limit(
            subject,
            kind,
            redis_support.settings.ai_rate_limit_per_minute,
        )
        # Redis 可能在应用启动后才恢复；首次成功入队时顺带恢复消费者。
        if (self._worker is None or self._worker.done()) and self._generator is not None:
            await self.start(self._generator, self._lesson_plan_generator)
        job_id = f"gen_{uuid.uuid4().hex}"
        state = {
            "job_id": job_id,
            "kind": kind,
            "user_id": subject,
            "status": "queued",
            "progress": 0,
            "message": "任务已进入生成队列",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        await redis_support.set_json(self._state_key(job_id), state, 86400)
        await client.xadd(self.queue_key, {
            "job_id": job_id,
            "kind": kind,
            "user_id": subject,
            "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        })
        await self._event(job_id, "queued", 0, state["message"])
        return state

    async def get(self, job_id: str, include_result: bool = True) -> dict[str, Any] | None:
        state = await redis_support.get_json(self._state_key(job_id))
        if not isinstance(state, dict):
            return None
        if include_result and state.get("status") == "success":
            state["result"] = await redis_support.get_json(self._result_key(job_id))
        return state

    async def events(self, job_id: str, last_event_id: str = "0-0") -> AsyncIterator[dict[str, Any]]:
        client = await redis_support.client()
        if client is None:
            yield {"id": last_event_id, "event": "error", "data": {"message": "Redis 不可用"}}
            return
        offset = last_event_id or "0-0"
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            rows = await client.xread({self._events_key(job_id): offset}, count=50, block=15000)
            if not rows:
                yield {"id": offset, "event": "heartbeat", "data": {}}
                continue
            for _, records in rows:
                for event_id, data in records:
                    offset = event_id
                    event = str(data.get("event") or "progress")
                    payload = {k: self._coerce(v) for k, v in data.items() if k != "event"}
                    extra = payload.pop("data", None)
                    if isinstance(extra, str):
                        try:
                            parsed = json.loads(extra)
                            if isinstance(parsed, dict):
                                payload.update(parsed)
                        except json.JSONDecodeError:
                            pass
                    yield {"id": event_id, "event": event, "data": payload}
                    if payload.get("status") in {"success", "failed", "cancelled"}:
                        return

    async def _worker_loop(self) -> None:
        while True:
            try:
                client = await redis_support.client()
                if client is None:
                    await asyncio.sleep(2)
                    continue
                rows = await client.xreadgroup(
                    self.group, self.consumer, {self.queue_key: ">"}, count=1, block=5000,
                )
                if not rows:
                    continue
                for _, records in rows:
                    for record_id, fields in records:
                        await self._process(fields)
                        await client.xack(self.queue_key, self.group, record_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("生成队列消费失败: %s", exc)
                await asyncio.sleep(2)

    async def _process(self, fields: dict[str, str]) -> None:
        job_id = fields.get("job_id", "")
        kind = fields.get("kind", "")
        user_id = fields.get("user_id") or "anonymous"
        try:
            payload = json.loads(fields.get("payload") or "{}")
            await self._update(job_id, "running", 5, "生成任务已开始")
            async with ai_request_guard(user_id, f"queued-{kind}"):
                if kind == "presentation":
                    request = PresentationGenerateRequest.model_validate(payload)
                    final_result = None
                    total = max(1, len(request.outline.get("slides") or []))
                    completed = 0
                    async for item in self._generator.stream_presentation(request):
                        if item.get("type") == "slide":
                            completed += 1
                            progress = min(90, 10 + int(completed / total * 75))
                            await self._update(job_id, "running", progress,
                                               f"已完成第 {completed}/{total} 页",
                                               event_data={
                                                   "slide": item.get("slide"),
                                                   "completed": completed,
                                                   "total": total,
                                               })
                        elif item.get("type") == "final":
                            final_result = item.get("response")
                    result = final_result or {}
                elif kind == "lesson-plan":
                    request = LessonPlanGenerateRequest.model_validate(payload)
                    await self._update(job_id, "running", 35, "正在生成结构化教案")
                    result = await self._lesson_plan_generator.generate(request)
                else:
                    raise RuntimeError(f"不支持的生成任务类型: {kind}")
            await redis_support.set_json(self._result_key(job_id), result, 86400)
            await self._update(job_id, "success", 100, "生成完成")
        except Exception as exc:
            logger.exception("生成任务失败 job_id=%s", job_id)
            await self._update(job_id, "failed", 100, str(exc))

    async def _update(
        self,
        job_id: str,
        status: str,
        progress: int,
        message: str,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        state = await self.get(job_id, include_result=False) or {"job_id": job_id}
        state.update({"status": status, "progress": progress, "message": message, "updated_at": time.time()})
        await redis_support.set_json(self._state_key(job_id), state, 86400)
        await self._event(job_id, status, progress, message, event_data)

    async def _event(
        self,
        job_id: str,
        status: str,
        progress: int,
        message: str,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        client = await redis_support.client()
        if client is None:
            return
        key = self._events_key(job_id)
        payload = {
            "event": "progress",
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": time.time(),
        }
        if event_data:
            payload["data"] = json.dumps(event_data, ensure_ascii=False, separators=(",", ":"))
        await client.xadd(key, payload, maxlen=500, approximate=True)
        await client.expire(key, 86400)

    def _state_key(self, job_id: str) -> str:
        return redis_support.key("generation", "job", job_id)

    def _result_key(self, job_id: str) -> str:
        return redis_support.key("generation", "result", job_id)

    def _events_key(self, job_id: str) -> str:
        return redis_support.key("events", "generation", job_id)

    @staticmethod
    def _coerce(value: str) -> Any:
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return value


generation_job_manager = GenerationJobManager()
