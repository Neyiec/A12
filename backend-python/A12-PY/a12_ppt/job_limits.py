"""Redis admission control for costly requests. Results stay in their existing stores."""

import asyncio
import hashlib
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from fastapi import HTTPException
from redis.asyncio import from_url
from redis.exceptions import RedisError

from .direct_auth import direct_user_id

logger = logging.getLogger(__name__)
LEASE_SECONDS = 180
LIMITS = {"presentation": 4, "outline": 6, "word_parse": 4, "export": 3, "batch_plan": 2}

# All keys for one lane share a Redis cluster hash tag.
ACQUIRE = """
local current = redis.call('GET', KEYS[1])
if current then return {1, current} end
local now = tonumber(ARGV[5])
for i=2,3 do
  redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now)
end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3])
   or redis.call('ZCARD', KEYS[3]) >= 1 then return {2} end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[4])
for i=2,3 do
  redis.call('ZADD', KEYS[i], now + tonumber(ARGV[4]), ARGV[1])
  redis.call('EXPIRE', KEYS[i], ARGV[4])
end
return {0}
"""
UPDATE = """
local state = redis.call('GET', KEYS[1])
if not state or string.sub(state, 1, 32) ~= ARGV[1] then return 0 end
if ARGV[2] == '' then
  redis.call('DEL', KEYS[1])
  for i=2,3 do redis.call('ZREM', KEYS[i], ARGV[1]) end
else
  local now = tonumber(ARGV[4])
  redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
  for i=2,3 do
    redis.call('ZADD', KEYS[i], now + tonumber(ARGV[3]), ARGV[1])
    redis.call('EXPIRE', KEYS[i], ARGV[3])
  end
end
return 1
"""


class JobLease:
    def __init__(self, client, keys: tuple[str, ...]):
        self.client = client
        self.keys = keys
        self.id = uuid4().hex
        self.stage = "processing"
        self.completed_pages = 0
        self._write_lock = asyncio.Lock()

    def state(self):
        return self.id + json.dumps({"job_id": self.id, "stage": self.stage,
                                    "completed_pages": self.completed_pages})

    async def update(self):
        async with self._write_lock:
            try:
                await self.client.eval(UPDATE, 3, *self.keys, self.id, self.state(), LEASE_SECONDS, int(time.time()))
            except RedisError:
                logger.warning("Job lease progress update unavailable")

    async def keep_alive(self):
        while True:
            await asyncio.sleep(30)
            await self.update()


@asynccontextmanager
async def limit_job(lane: str, payload, *, user_id: str | None = None):
    owner = user_id or direct_user_id.get() or "internal"
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":")).encode()).hexdigest()
    prefix = f"a12:jobs:{{{lane}}}"
    keys = (f"{prefix}:job:{owner}:{digest}", f"{prefix}:global", f"{prefix}:user:{owner}")
    url = os.getenv("A12_RESOURCE_REDIS_URL", "redis://127.0.0.1:6379/0")
    async with from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2) as client:
        lease = JobLease(client, keys)
        try:
            result = await client.eval(ACQUIRE, 3, *keys, lease.id, lease.state(), LIMITS[lane], LEASE_SECONDS, int(time.time()))
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="任务调度暂时不可用，请稍后重试") from exc
        if result[0] == 1:
            state = json.loads(result[1][32:])
            pages = state["completed_pages"]
            message = f"相同任务正在处理，已完成 {pages} 页，请查看原任务" if pages else "相同任务正在处理，请查看原任务"
            raise HTTPException(status_code=409, detail={**state, "message": message})
        if result[0] == 2:
            raise HTTPException(status_code=429, detail="当前任务较多，请等待已有任务完成后重试",
                                headers={"Retry-After": "5"})
        heartbeat = asyncio.create_task(lease.keep_alive())
        try:
            yield lease
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            try:
                await client.eval(UPDATE, 3, *keys, lease.id, "", LEASE_SECONDS)
            except RedisError:
                logger.warning("Job lease release unavailable; lease will expire")
