from pathlib import Path

from ...asr.service import transcribe_audio
from .common import ParsedResource


async def parse_audio(path: Path) -> ParsedResource:
    result = await transcribe_audio(path)
    text = result.get("text", "")
    return ParsedResource(text=f"音频转写:\n{text}" if text else "", metadata={
        "modality": "audio", "parser": "configured-asr", "transcript_available": bool(text),
        "status": result.get("status"), "model": result.get("model"), "error": result.get("error_message"),
    })
