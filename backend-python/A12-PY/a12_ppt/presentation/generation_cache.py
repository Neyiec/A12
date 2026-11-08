"""进程内有界生成缓存；按教师隔离，键只存摘要，RAG 仍在每次请求重新校验。"""
import copy
import hashlib
import json
import time
from collections import OrderedDict


class GenerationCache:
    def __init__(self, max_bytes=16 * 1024 * 1024, ttl=900, clock=time.monotonic):
        self.max_bytes, self.ttl, self.clock = max_bytes, ttl, clock
        self.entries = OrderedDict()
        self.size = 0

    def get(self, key):
        entry = self.entries.pop(key, None)
        if entry is None:
            return None
        expires, size, value = entry
        if expires <= self.clock():
            self.size -= size
            return None
        self.entries[key] = entry
        return copy.deepcopy(value)

    def put(self, key, value):
        size = len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
        if size > self.max_bytes:
            return
        previous = self.entries.pop(key, None)
        if previous:
            self.size -= previous[1]
        while self.entries and (self.size + size > self.max_bytes or len(self.entries) >= 256):
            _, (_, removed_size, _) = self.entries.popitem(last=False)
            self.size -= removed_size
        self.entries[key] = (self.clock() + self.ttl, size, copy.deepcopy(value))
        self.size += size


def generation_key(kind, settings, content):
    from ..direct_auth import direct_user_id
    from ..ai_runtime import current_runtime, routed_model
    runtime = current_runtime()
    # 密钥变化也使缓存失效；密钥与课程正文不作为可见缓存键保存或打印。
    raw = ["html-pipeline-v2", kind, direct_user_id.get() or runtime.user_id or "internal", routed_model(),
           getattr(settings, "openai_base_url", ""), getattr(settings, "openai_api_key", ""),
           runtime.model_profile, runtime.reasoning_effort, content]
    return hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


generation_cache = GenerationCache()
