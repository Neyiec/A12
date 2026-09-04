from pathlib import Path

from openai import AsyncOpenAI

from ...config import get_settings
from .common import ParsedResource


async def parse_audio(path: Path) -> ParsedResource:
    settings = get_settings()
    if not settings.asr_api_key:
        return ParsedResource(text="", metadata={"modality": "audio", "parser": "bailian-audio", "transcript_available": False})
    try:
        client = AsyncOpenAI(
            api_key=settings.asr_api_key,
            base_url=settings.asr_base_url.rstrip("/") if settings.asr_base_url else None,
            timeout=settings.request_timeout_seconds,
        )
        with path.open("rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model=settings.asr_model,
                file=audio_file,
                response_format="text",
            )
        return ParsedResource(
            text=f"音频转写:\n{str(transcript).strip()}",
            metadata={"modality": "audio", "parser": "bailian-compatible-asr", "model": settings.asr_model, "transcript_available": True},
        )
    except Exception as exc:
        return ParsedResource(text="", metadata={"modality": "audio", "parser": "bailian-compatible-asr", "model": settings.asr_model, "error": str(exc)})
