"""Kafka 事件消费者：资源索引流水线、课堂事件与教师反馈。

Kafka 仅承载可回放的长期业务事件；实时进度、缓存和限流仍由 Redis 负责。
依赖或 broker 不可用时启动失败但不会阻止 FastAPI 提供原 HTTP 接口。
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import get_settings
from .models import ClassroomEventRequest, ResourceIndexSyncRequest, TeacherFeedbackRequest
from .redis_support import redis_support

logger = logging.getLogger("a12_ppt.kafka")


class KafkaRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._producer = None
        self._consumers: list[Any] = []
        self._task: asyncio.Task | None = None
        self._resource_index_store = None
        self._memory_store = None

    async def start(self, resource_index_store, memory_store) -> None:
        self._resource_index_store = resource_index_store
        self._memory_store = memory_store
        if not self.settings.kafka_enabled:
            logger.info("Kafka 事件总线未启用，继续使用 HTTP 链路")
            return
        if self._task is None or self._task.done():
            # 监督循环负责首次连接和断线重连，不让 broker 启动顺序影响 FastAPI 启动。
            self._task = asyncio.create_task(self._supervise(), name="a12-kafka-supervisor")

    async def _supervise(self) -> None:
        while True:
            try:
                await self._connect()
                logger.info("Kafka 事件总线已连接: %s", self.settings.kafka_bootstrap_servers)
                await self._consume_loop()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Kafka 连接/消费中断，5 秒后重试；HTTP 降级链路保持可用: %s", exc)
            finally:
                await self._close_clients()
            await asyncio.sleep(5)

    async def _connect(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

            client_id = f"a12-python-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                client_id=client_id,
                acks="all",
                enable_idempotence=True,
                value_serializer=lambda value: json.dumps(
                    value, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
            )
            await self._producer.start()
            for topic, suffix in (
                (self.settings.kafka_resource_index_request_topic, "resource"),
                (self.settings.kafka_classroom_event_topic, "classroom"),
                (self.settings.kafka_teacher_feedback_topic, "feedback"),
            ):
                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=self.settings.kafka_bootstrap_servers,
                    group_id=f"{self.settings.kafka_consumer_group}-{suffix}",
                    client_id=f"{client_id}-{suffix}",
                    enable_auto_commit=False,
                    auto_offset_reset="earliest",
                    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
                )
                await consumer.start()
                self._consumers.append(consumer)
        except Exception:
            await self._close_clients()
            raise

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._close_clients()

    async def _close_clients(self) -> None:
        for consumer in self._consumers:
            try:
                await consumer.stop()
            except Exception:
                logger.debug("关闭 Kafka consumer 失败", exc_info=True)
        self._consumers = []
        if self._producer:
            try:
                await self._producer.stop()
            except Exception:
                logger.debug("关闭 Kafka producer 失败", exc_info=True)
            self._producer = None

    @property
    def ready(self) -> bool:
        return bool(self._producer and len(self._consumers) == 3 and self._task and not self._task.done())

    async def _consume_loop(self) -> None:
        await asyncio.gather(*(self._consume_consumer(consumer) for consumer in self._consumers))

    async def _consume_consumer(self, consumer) -> None:
        async for message in consumer:
            event = message.value if isinstance(message.value, dict) else {}
            try:
                await self._dispatch(message.topic, event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Kafka 事件处理失败 topic=%s offset=%s", message.topic, message.offset)
                await self._publish_dead_letter(message.topic, event, exc)
            # 失败事件已经进入 DLQ，提交 offset，避免毒消息无限阻塞分区。
            await consumer.commit()

    async def _dispatch(self, topic: str, event: dict[str, Any]) -> None:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if topic == self.settings.kafka_resource_index_request_topic:
            source_type = str(payload.get("source_type") or "unknown")
            resource_id = str(payload.get("resource_id") or "unknown")
            try:
                request = ResourceIndexSyncRequest.model_validate(payload)
                data = await self._resource_index_store.sync_resource(request)
                if data.get("status") in {"indexed", "updated", "deleted"}:
                    await redis_support.increment_version("resource-index")
                status = "failed" if data.get("status") == "failed" else "completed"
                await self._publish_resource_result(event, source_type, resource_id, status,
                                                    str(data.get("error_message") or ""), data)
            except Exception as exc:
                await self._publish_resource_result(event, source_type, resource_id, "failed", str(exc), {})
                raise
            return
        if topic == self.settings.kafka_classroom_event_topic:
            request = ClassroomEventRequest.model_validate(payload)
            record = request.model_dump()
            record["event_id"] = str(event.get("event_id") or uuid.uuid4().hex)
            stored = await asyncio.to_thread(self._memory_store.record_classroom_event, record)
            if not stored:
                raise RuntimeError("课堂事件写入 PostgreSQL 失败")
            return
        if topic == self.settings.kafka_teacher_feedback_topic:
            request = TeacherFeedbackRequest.model_validate(payload)
            record = request.model_dump()
            record["event_id"] = str(event.get("event_id") or uuid.uuid4().hex)
            result = await asyncio.to_thread(self._memory_store.record_feedback, record)
            if not result.get("stored"):
                raise RuntimeError(str(result.get("error") or "教师反馈写入 PostgreSQL 失败"))
            return
        raise RuntimeError(f"不支持的 Kafka topic: {topic}")

    async def _publish_dead_letter(self, source_topic: str, event: dict[str, Any], exc: Exception) -> None:
        await self._send(self.settings.kafka_dead_letter_topic, {
            "event_id": event.get("event_id") or uuid.uuid4().hex,
            "event_type": "dead-letter",
            "schema_version": 1,
            "source_topic": source_topic,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "error": str(exc)[:1000],
            "original_event": event,
        }, key=str(event.get("event_id") or "unknown"))

    async def _publish_resource_result(
        self,
        event: dict[str, Any],
        source_type: str,
        resource_id: str,
        status: str,
        error_message: str,
        data: dict[str, Any],
    ) -> None:
        await self._send(self.settings.kafka_resource_index_result_topic, {
            "event_id": event.get("event_id") or uuid.uuid4().hex,
            "event_type": "resource.index.failed" if status == "failed" else "resource.index.completed",
            "schema_version": 1,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "source_type": source_type,
            "resource_id": resource_id,
            "status": status,
            "error_message": error_message[:1000],
            "data": data,
        }, key=f"{source_type}:{resource_id}")

    async def _send(self, topic: str, value: dict[str, Any], key: str) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer 尚未启动")
        await self._producer.send_and_wait(topic, value, key=key.encode("utf-8"))


kafka_runtime = KafkaRuntime()
