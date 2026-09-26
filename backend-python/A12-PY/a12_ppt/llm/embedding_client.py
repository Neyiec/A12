import asyncio
import hashlib
import time
from collections import OrderedDict

from ..config import get_settings
from ..redis_support import redis_support
from .model_factory import create_embedding_model_from_settings


class EmbeddingClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._query_cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()

    @property
    def available(self) -> bool:
        return bool(self.settings.embedding_api_key)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self.available or not texts:
            return []
        keys = [self._cache_key(text) for text in texts]
        cached_values = await asyncio.gather(*(
            redis_support.get_json(redis_support.key("cache", "embedding", self.settings.embedding_model, key))
            for key in keys
        ))
        results: list[list[float] | None] = [
            [float(value) for value in cached] if isinstance(cached, list) and cached else None
            for cached in cached_values
        ]
        missing_indexes = [index for index, value in enumerate(results) if value is None]
        if missing_indexes:
            model = create_embedding_model_from_settings(self.settings)
            generated = await model.aembed_documents([texts[index] for index in missing_indexes])
            writes = []
            for index, embedding in zip(missing_indexes, generated):
                results[index] = list(embedding)
                writes.append(redis_support.set_json(
                    redis_support.key("cache", "embedding", self.settings.embedding_model, keys[index]),
                    embedding,
                    self.settings.embedding_cache_ttl_seconds,
                ))
            if writes:
                await asyncio.gather(*writes)
        return [value or [] for value in results]

    async def embed_query(self, text: str) -> list[float]:
        if not self.available or not text:
            return []
        key = self._cache_key(text)
        redis_key = redis_support.key("cache", "embedding", self.settings.embedding_model, key)
        redis_cached = await redis_support.get_json(redis_key)
        if isinstance(redis_cached, list) and redis_cached:
            return [float(value) for value in redis_cached]
        cached = self._query_cache.get(key)
        if cached and time.time() - cached[0] < 3600:
            self._query_cache.move_to_end(key)
            return list(cached[1])
        model = create_embedding_model_from_settings(self.settings)
        embedding = await model.aembed_query(text)
        await redis_support.set_json(redis_key, embedding, self.settings.embedding_cache_ttl_seconds)
        self._query_cache[key] = (time.time(), list(embedding))
        self._query_cache.move_to_end(key)
        while len(self._query_cache) > 256:
            self._query_cache.popitem(last=False)
        return embedding

    def _cache_key(self, text: str) -> str:
        material = f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}:{text.strip()}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()
