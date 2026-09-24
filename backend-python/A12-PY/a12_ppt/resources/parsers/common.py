from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedResource:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_file_type(path: Path, file_type: str | None = None) -> str:
    raw = (file_type or "").lower().strip(". ")
    if "/" in raw:
        raw = raw.split("/", 1)[1]
    suffix = path.suffix.lower().strip(".")
    known = {
        "doc", "docx", "word", "ppt", "pptx", "powerpoint", "jpg", "jpeg", "png", "gif", "bmp", "webp",
        "image", "mp4", "mov", "avi", "mkv", "webm", "wmv", "flv", "video", "mp3", "wav", "m4a", "aac",
        "ogg", "audio", "pdf", "txt", "text", "md", "markdown", "csv", "srt", "vtt", "ass",
    }
    value = raw if raw in known else suffix
    if value in {"doc", "docx", "word"}:
        return "word"
    if value in {"ppt", "pptx", "powerpoint"}:
        return "ppt"
    if value in {"jpg", "jpeg", "png", "gif", "bmp", "webp", "image"}:
        return "image"
    if value in {"mp4", "mov", "avi", "mkv", "webm", "wmv", "flv", "video"}:
        return "video"
    if value in {"mp3", "wav", "m4a", "aac", "ogg", "audio"}:
        return "audio"
    if value in {"pdf", "txt", "text", "md", "markdown", "csv", "srt", "vtt", "ass"}:
        return "txt" if value in {"text", "md", "markdown", "csv", "srt", "vtt", "ass"} else value
    if suffix and raw != suffix:
        return normalize_file_type(path, suffix)
    return "other"


def plain_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def merge_text_blocks(blocks: list[str]) -> str:
    return "\n\n".join(block.strip() for block in blocks if block and block.strip())
