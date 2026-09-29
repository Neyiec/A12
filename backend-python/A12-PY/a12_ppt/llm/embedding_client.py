import hashlib
import time
from collections import OrderedDict

from ..config import get_settings
from ..direct_auth import require_active_browser_token
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
        await require_active_browser_token()
        model = create_embedding_model_from_settings(self.settings)
        return await model.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        if not self.available or not text:
            return []
        await require_active_browser_token()
        key = hashlib.sha256(f"{self.settings.embedding_model}:{text.strip()}".encode("utf-8")).hexdigest()
        cached = self._query_cache.get(key)
        if cached and time.time() - cached[0] < 3600:
            self._query_cache.move_to_end(key)
            return list(cached[1])
        model = create_embedding_model_from_settings(self.settings)
        embedding = await model.aembed_query(text)
        self._query_cache[key] = (time.time(), list(embedding))
        self._query_cache.move_to_end(key)
        while len(self._query_cache) > 256:
            self._query_cache.popitem(last=False)
        return embedding
