"""消费社区 PPT 审核事件；失败最多重试三次，之后进入死信并保留人工待审。"""

import asyncio
import logging
import os
import socket
import threading
import time

import httpx

from .community_review import review_content


logger = logging.getLogger(__name__)
STREAM = "a12:community-review:events"
GROUP = "a12-python-review"
DEAD_LETTER = "a12:community-review:dead-letter"
_worker_started = False


async def process_event(event: dict[str, str]) -> None:
    audit_id = str(event.get("audit_id") or "")
    version = str(event.get("content_version") or "")
    if not audit_id.isdecimal() or not version.isdecimal():
        raise ValueError("无效的社区审核事件")
    base = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    headers = {"X-A12-Internal-Key": os.environ["A12_PYTHON_INTERNAL_KEY"]}
    url = f"{base}/api/v1/internal/community-review/{audit_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        envelope = response.json()
        if envelope.get("code") == 409:
            return  # 人工已处理或课件不再待审，幂等确认即可。
        if envelope.get("code") not in (0, 200) or not isinstance(envelope.get("data"), dict):
            raise RuntimeError(f"读取待审课件失败：{envelope.get('message')}")
        payload = envelope["data"]
        if str(payload.get("content_version")) != version:
            return  # 旧版本事件不能影响新投稿。
        result = await review_content(payload)
        response = await client.post(f"{url}/result", headers=headers, json=result)
        response.raise_for_status()
        envelope = response.json()
        if envelope.get("code") == 409:
            return  # 已人工处理或相同 AI 结果先到达。
        if envelope.get("code") not in (0, 200):
            raise RuntimeError(f"回写 AI 审核失败：{envelope.get('message')}")


def _consume_forever(worker_index: int) -> None:
    import redis

    client = redis.Redis.from_url(os.getenv("A12_RESOURCE_REDIS_URL", "redis://127.0.0.1:6379/0"),
                                  decode_responses=True, socket_connect_timeout=3, socket_timeout=10)
    consumer = f"{socket.gethostname()}-{os.getpid()}-{worker_index}"
    while True:
        try:
            try:
                client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
            except redis.exceptions.ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            claimed = client.xautoclaim(STREAM, GROUP, consumer, min_idle_time=180_000,
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
                    logger.exception("社区 AI 初审失败 event=%s deliveries=%s", message_id, deliveries)
                    if deliveries >= 3:
                        client.xadd(DEAD_LETTER, {**event, "original_id": message_id,
                                                  "error": str(exc)[:500]})
                        client.xack(STREAM, GROUP, message_id)
        except Exception:
            logger.exception("社区审核事件消费者暂时不可用，稍后重连")
            time.sleep(5)


def start_community_review_worker() -> None:
    global _worker_started
    if _worker_started:
        return
    if not os.getenv("A12_PYTHON_INTERNAL_KEY"):
        logger.warning("未配置 A12_PYTHON_INTERNAL_KEY，社区 AI 审核消费者未启动，投稿保持人工待审")
        return
    _worker_started = True
    try:
        workers = max(1, min(6, int(os.getenv("A12_COMMUNITY_REVIEW_WORKERS", "3"))))
    except ValueError:
        logger.warning("A12_COMMUNITY_REVIEW_WORKERS 不是整数，使用默认 3 个消费者")
        workers = 3
    for index in range(workers):
        threading.Thread(target=_consume_forever, args=(index,), daemon=True,
                         name=f"a12-community-review-{index}").start()
