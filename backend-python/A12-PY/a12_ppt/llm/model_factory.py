from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..config import Settings


@lru_cache(maxsize=32)
def create_chat_model(
    model: str,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    temperature: float,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url.rstrip("/") if base_url else None,
        timeout=timeout_seconds,
        temperature=temperature,
    )


def create_chat_model_from_settings(settings: Settings, temperature: float = 0.45, model: str | None = None) -> ChatOpenAI:
    return create_chat_model(
        model=model or settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout_seconds=settings.request_timeout_seconds,
        temperature=temperature,
    )


@lru_cache(maxsize=16)
def create_embedding_model(
    model: str,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    dimensions: int | None = None,
) -> OpenAIEmbeddings:
    kwargs = {
        "model": model,
        "api_key": api_key,
        "base_url": base_url.rstrip("/") if base_url else None,
        "timeout": timeout_seconds,
    }
    if dimensions:
        kwargs["dimensions"] = dimensions
    return OpenAIEmbeddings(**kwargs)


def create_embedding_model_from_settings(settings: Settings) -> OpenAIEmbeddings:
    return create_embedding_model(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        timeout_seconds=settings.request_timeout_seconds,
        dimensions=settings.embedding_dimensions,
    )
