from ..config import get_settings
from .model_factory import create_embedding_model_from_settings


class EmbeddingClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def available(self) -> bool:
        return bool(self.settings.embedding_api_key)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self.available or not texts:
            return []
        model = create_embedding_model_from_settings(self.settings)
        return await model.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        if not self.available or not text:
            return []
        model = create_embedding_model_from_settings(self.settings)
        return await model.aembed_query(text)
