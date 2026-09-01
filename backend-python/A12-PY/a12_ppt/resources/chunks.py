import re
from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 120,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text or "").strip()
    if not normalized:
        return []

    strategy = _chunk_strategy(metadata or {})
    effective_size, effective_overlap = _strategy_window(strategy, chunk_size, overlap)
    segments = _semantic_segments(normalized, strategy)
    return _pack_segments(segments, effective_size, effective_overlap)


def _chunk_strategy(metadata: dict[str, Any]) -> str:
    parse_meta = metadata.get("parse") if isinstance(metadata.get("parse"), dict) else {}
    haystack = " ".join([
        str(metadata.get("title") or ""),
        str(metadata.get("subject") or ""),
        str(metadata.get("file_type") or ""),
        " ".join(_as_text_list(metadata.get("tags"))),
        " ".join(_as_text_list(metadata.get("categories"))),
        str(parse_meta.get("modality") or ""),
    ]).lower()

    if any(token in haystack for token in ("ppt", "presentation", "slide", "幻灯片", "课件")):
        return "slide"
    if any(token in haystack for token in ("video", "audio", "keyframe", "transcript", "视频", "音频", "字幕")):
        return "timeline"
    if any(token in haystack for token in ("数学", "公式", "几何", "物理", "化学", "molecule", "chem", "formula")):
        return "subject_dense"
    if any(token in haystack for token in ("习题", "试题", "问答", "qa", "exercise", "quiz")):
        return "qa"
    return "paragraph"


def _strategy_window(strategy: str, chunk_size: int, overlap: int) -> tuple[int, int]:
    if strategy in {"subject_dense", "qa"}:
        return min(chunk_size, 900), min(overlap, 90)
    if strategy == "slide":
        return min(chunk_size, 1100), min(overlap, 80)
    if strategy == "timeline":
        return min(chunk_size, 1000), min(overlap, 100)
    return chunk_size, overlap


def _semantic_segments(text: str, strategy: str) -> list[str]:
    if strategy == "slide":
        segments = re.split(r"(?im)(?=^\s*(slide|page|第\s*\d+\s*[页章节]|#{1,3})\b)", text)
    elif strategy == "timeline":
        segments = re.split(r"(?im)(?=^\s*(\[\d{1,2}:\d{2}|#{1,3}|关键帧|片段|章节))", text)
    elif strategy == "qa":
        segments = re.split(r"(?im)(?=^\s*(q[:：]|问题[:：]|题目[:：]|\d+[\.、]))", text)
    elif strategy == "subject_dense":
        segments = re.split(r"(?<=[。！？；;])\s+|\n{2,}|(?=例\s*\d+|公式|推导|实验|结论)", text)
    else:
        segments = re.split(r"\n{2,}|(?<=[。！？.!?])\s+", text)
    return [segment.strip() for segment in segments if segment and segment.strip()]


def _pack_segments(segments: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for segment in segments:
        if len(segment) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.extend(_hard_split(segment, chunk_size, overlap))
            continue

        candidate = f"{current}\n\n{segment}".strip() if current else segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current.strip():
            chunks.append(current.strip())
        current = _tail(current, overlap)
        current = f"{current}\n\n{segment}".strip() if current else segment

    if current.strip():
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _tail(text: str, overlap: int) -> str:
    if overlap <= 0 or not text:
        return ""
    return text[-overlap:].strip()


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []
