from pathlib import Path

from openai import AsyncOpenAI

from ..config import get_settings


async def transcribe_audio(path: Path, language: str | None = None) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "text": "",
            "language": language,
            "model": settings.asr_model,
            "status": "unavailable",
            "error_message": "OPENAI_API_KEY is not configured",
        }
    try:
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url.rstrip("/") if settings.openai_base_url else None,
            timeout=settings.request_timeout_seconds,
        )
        with path.open("rb") as audio_file:
            kwargs = {
                "model": settings.asr_model,
                "file": audio_file,
                "response_format": "json",
            }
            if language:
                kwargs["language"] = language
            transcript = await client.audio.transcriptions.create(**kwargs)
        text = getattr(transcript, "text", None) or str(transcript)
        return {
            "text": text.strip(),
            "language": language,
            "model": settings.asr_model,
            "status": "completed",
            "error_message": None,
        }
    except Exception as exc:
        return {
            "text": "",
            "language": language,
            "model": settings.asr_model,
            "status": "failed",
            "error_message": str(exc),
        }
