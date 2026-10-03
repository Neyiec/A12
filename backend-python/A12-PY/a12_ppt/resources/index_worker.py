"""消费 Java 业务资源事件；AI 索引仅在 Python 进程执行。"""

import asyncio
import json
import logging
import os
import socket
import threading
import time
from bs4 import BeautifulSoup

import httpx

from ..models import ResourceIndexMetadataRequest, ResourceIndexSyncRequest
from . import resource_index_store


logger = logging.getLogger(__name__)
STREAM = "a12:resource-index:events"
GROUP = "a12-python-index"
DEAD_LETTER = "a12:resource-index:dead-letter"
_worker_started = False


async def process_event(event: dict[str, str]) -> None:
    source = event["source_type"]
    resource_id = event["resource_id"]
    action = event["action"]
    if source not in ("public", "personal", "community") or not resource_id.isdecimal():
        raise ValueError("无效的资源索引事件")
    if action == "delete":
        resource_index_store.delete_resource(source, resource_id)
        return
    base = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    headers = {"X-A12-Internal-Key": os.environ["A12_PYTHON_INTERNAL_KEY"]}
    url = f"{base}/api/v1/internal/resource-index/{source}/{resource_id}"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        envelope = response.json()
        if envelope.get("code") == 404:
            resource_index_store.delete_resource(source, resource_id)
            return
        if envelope.get("code") not in (0, 200) or not isinstance(envelope.get("data"), dict):
            raise ValueError(f"Java 资源查询失败: {envelope.get('message')}")
        payload = envelope["data"]
        if source == "community":
            if not payload.get("allow_ai"):
                resource_index_store.delete_resource(source, resource_id)
                return
            if action != "sync":
                raise ValueError(f"未知社区索引事件: {action}")
            content = payload.get("content_data") or {}
            if isinstance(content, str):
                content = json.loads(content)
            slides = content.get("slides") if isinstance(content, dict) else None
            if not isinstance(slides, list) or not slides:
                raise ValueError("社区课件缺少可索引页面")
            parts = [str(payload.get("title") or ""), str(payload.get("description") or "")]
            for number, slide in enumerate(slides[:200], 1):
                if not isinstance(slide, dict):
                    continue
                soup = BeautifulSoup(str(slide.get("html") or ""), "html.parser")
                for tag in soup(["script", "style"]):
                    tag.decompose()
                elements = " ".join(str(item.get("content") or item.get("text") or "")
                                    for item in slide.get("elements", []) if isinstance(item, dict))
                parts.append(f"第 {number} 页：{slide.get('title') or ''} "
                             f"{soup.get_text(' ', strip=True)} {elements} {slide.get('notes') or ''}"[:2500])
            text = "\n".join(parts)[:200_000]
            await resource_index_store.sync_community_text(payload, text)
            return
        if action == "sync":
            if not payload.get("file_url"):
                raise ValueError("资源缺少下载地址")
            payload["force_reparse"] = event.get("force_reparse") == "true"
            result = await resource_index_store.sync_resource(ResourceIndexSyncRequest.model_validate(payload))
            status = "failed" if result.get("status") == "failed" else "completed"
            error = str(result.get("error") or result.get("error_message") or "") if status == "failed" else ""
        elif action == "metadata":
            resource_index_store.update_metadata(ResourceIndexMetadataRequest(
                source_type=source, resource_id=resource_id,
                available=payload["available"], allow_ai=payload["allow_ai"],
                metadata=payload["metadata"],
            ))
            return
        else:
            raise ValueError(f"未知索引事件: {action}")
        status_response = await client.post(f"{url}/status", headers=headers,
                                            json={"status": status, "error": error})
        status_response.raise_for_status()
        if status == "failed":
            raise RuntimeError(error or "资源索引失败")


def _consume_forever() -> None:
    import redis

    client = redis.Redis.from_url(os.getenv("A12_RESOURCE_REDIS_URL", "redis://127.0.0.1:6379/0"),
                                  decode_responses=True, socket_connect_timeout=3, socket_timeout=10)
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    while True:
        try:
            try:
                client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
            except redis.exceptions.ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            claimed = client.xautoclaim(STREAM, GROUP, consumer, min_idle_time=30_000,
                                        start_id="0-0", count=1)
            entries = claimed[1] if claimed else []
            if not entries:
                streams = client.xreadgroup(GROUP, consumer, {STREAM: ">"}, count=1, block=5000)
                entries = streams[0][1] if streams else []
            for message_id, event in entries:
                try:
                    asyncio.run(process_event(event))
                    client.xack(STREAM, GROUP, message_id)
                except Exception as exc:
                    pending = client.xpending_range(STREAM, GROUP, message_id, message_id, 1)
                    deliveries = pending[0]["times_delivered"] if pending else 1
                    logger.exception("资源索引失败 event=%s deliveries=%s", message_id, deliveries)
                    if deliveries >= 3:
                        client.xadd(DEAD_LETTER, {**event, "original_id": message_id,
                                                  "error": str(exc)[:500]})
                        client.xack(STREAM, GROUP, message_id)
        except Exception:
            logger.exception("资源事件消费者暂时不可用，稍后重连")
            time.sleep(5)


def start_resource_index_worker() -> None:
    global _worker_started
    if _worker_started:
        return
    if not os.getenv("A12_PYTHON_INTERNAL_KEY"):
        logger.warning("未配置 A12_PYTHON_INTERNAL_KEY，后台资源索引消费者未启动")
        return
    _worker_started = True
    threading.Thread(target=_consume_forever, daemon=True, name="a12-resource-index").start()
