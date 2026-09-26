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
        results: list[list[float] | None] = [None] * len(texts)
        missing_indexes: list[int] = []
        for index, text in enumerate(texts):
            cached = await redis_support.get_json(self._cache_key(text))
            if isinstance(cached, list):
                results[index] = [float(value) for value in cached]
            else:
                missing_indexes.append(index)
        if not missing_indexes:
            return [item or [] for item in results]
        model = create_embedding_model_from_settings(self.settings)
        generated = await model.aembed_documents([texts[index] for index in missing_indexes])
        for index, embedding in zip(missing_indexes, generated):
            vector = list(embedding)
            results[index] = vector
            await redis_support.set_json(
                self._cache_key(texts[index]), vector, self.settings.embedding_cache_ttl_seconds)
        return [item or [] for item in results]

    async def embed_query(self, text: str) -> list[float]:
        if not self.available or not text:
            return []
        key = self._cache_key(text)
        distributed = await redis_support.get_json(key)
        if isinstance(distributed, list):
            return [float(value) for value in distributed]
        cached = self._query_cache.get(key)
        if cached and time.time() - cached[0] < 3600:
            self._query_cache.move_to_end(key)
            return list(cached[1])
        model = create_embedding_model_from_settings(self.settings)
        embedding = await model.aembed_query(text)
        await redis_support.set_json(key, list(embedding), self.settings.embedding_cache_ttl_seconds)
        self._query_cache[key] = (time.time(), list(embedding))
        self._query_cache.move_to_end(key)
        while len(self._query_cache) > 256:
            self._query_cache.popitem(last=False)
        return embedding

    def _cache_key(self, text: str) -> str:
        material = f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}:{text.strip()}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return redis_support.key("cache", "embedding", digest)
