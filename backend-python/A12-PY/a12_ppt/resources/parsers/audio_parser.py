from pathlib import Path

from ...asr.service import transcribe_audio
from .common import ParsedResource

async def parse_audio(path: Path) -> ParsedResource:
    """音频转写：走独立 ASR 配置（asr_api_key/asr_base_url/asr_model），未配置时回落 OPENAI_* 组"""
    result = await transcribe_audio(path)
    text = str(result.get("text") or "").strip()
    return ParsedResource(
        text=f"音频转写:\n{text}" if text else "",
        metadata={
            "modality": "audio",
            "parser": f"openai-compatible-asr:{result.get('model') or 'unknown'}",
            "transcript_available": bool(text),
            "status": result.get("status"),
            "language": result.get("language"),
            "error": result.get("error_message"),
        },
    )
