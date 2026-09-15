import logging
from pathlib import Path

from openai import AsyncOpenAI

from ...config import get_settings
from .common import ParsedResource

# 统一日志约定（main.py 启动时 basicConfig）
logger = logging.getLogger("a12_ppt.resources.parsers.audio")


async def parse_audio(path: Path) -> ParsedResource:
    """音频转写：走独立 ASR 配置（asr_api_key/asr_base_url/asr_model），未配置时回落 OPENAI_* 组"""
    settings = get_settings()
    if not settings.asr_api_key:
        return ParsedResource(text="", metadata={"modality": "audio", "parser": "openai-audio", "transcript_available": False})
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
            metadata={"modality": "audio", "parser": f"openai-whisper:{settings.asr_model}", "transcript_available": True},
        )
    except Exception as exc:
        # 转写失败必须留下原因：当前端点（LongCat 等）多半不支持 /audio/transcriptions
        logger.warning("音频转写失败 model=%s base_url=%s file=%s: %s",
                       settings.asr_model, settings.asr_base_url, path.name, exc)
        return ParsedResource(text="", metadata={"modality": "audio", "parser": "openai-whisper", "error": str(exc)})
