from pathlib import Path

from .audio_parser import parse_audio
from .common import ParsedResource, normalize_file_type
from .document_parser import parse_pdf, parse_presentation, parse_text, parse_word
from .video_parser import parse_video
from .vision_parser import parse_image


async def parse_resource_file(path: Path, file_type: str | None = None, title: str | None = None) -> ParsedResource:
    normalized = normalize_file_type(path, file_type)
    if normalized == "pdf":
        result = await parse_pdf(path)
    elif normalized == "word":
        result = await parse_word(path)
    elif normalized == "ppt":
        result = await parse_presentation(path)
    elif normalized == "image":
        result = ParsedResource(*await parse_image(path))
    elif normalized == "video":
        result = await parse_video(path)
    elif normalized == "audio":
        result = await parse_audio(path)
    elif normalized == "txt":
        result = await parse_text(path)
    else:
        result = ParsedResource(text="", metadata={"modality": "unknown", "parser": "unsupported", "file_type": normalized})

    metadata = dict(result.metadata or {})
    metadata.update({
        "normalized_file_type": normalized,
        "title": title,
        "source_filename": path.name,
        "text_length": len(result.text or ""),
    })
    return ParsedResource(text=result.text or "", metadata=metadata)
