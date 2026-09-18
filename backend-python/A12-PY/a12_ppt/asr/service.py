from pathlib import Path

from openai import AsyncOpenAI

from ..config import get_settings

"""语音转文字服务"""
async def transcribe_audio(path: Path, language: str | None = None) -> dict:
    settings = get_settings()
    if not settings.asr_api_key:
        return {
            "text": "",
            "language": language,
            "model": settings.asr_model,
            "status": "unavailable",
            "error_message": "ASR_API_KEY (fallback OPENAI_API_KEY) is not configured",
        }
    try:
        # ASR 可独立接入第三方平台（ASR_BASE_URL/ASR_API_KEY），未配置时回落 OPENAI_BASE_URL
        client = AsyncOpenAI(
            api_key=settings.asr_api_key,
            base_url=settings.asr_base_url.rstrip("/") if settings.asr_base_url else None,
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
