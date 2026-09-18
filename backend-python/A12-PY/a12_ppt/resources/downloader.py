import tempfile
import hashlib
from pathlib import Path

import httpx

from ..models import ResourceIndexSyncRequest
from .parsers import ParsedResource, normalize_file_type, parse_resource_file


async def download_and_parse_resource(request: ResourceIndexSyncRequest, previous_digest: str | None = None) -> ParsedResource:
    suffix = guess_suffix(request)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp_path = Path(temp.name)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(request.file_url)
            response.raise_for_status()
            digest = hashlib.sha256(response.content).hexdigest()
            if previous_digest == digest and not request.force_reparse:
                return ParsedResource(text="", metadata={"content_sha256": digest, "unchanged": True})
            temp_path.write_bytes(response.content)
        parsed = await parse_resource_file(temp_path, request.file_type, request.title)
        parsed.metadata["content_sha256"] = digest
        return parsed
    finally:
        temp_path.unlink(missing_ok=True)


def guess_suffix(request: ResourceIndexSyncRequest) -> str:
    metadata = request.metadata or {}
    candidates = [
        request.file_type,
        metadata.get("file_type"),
        metadata.get("detected_file_type"),
        metadata.get("original_filename"),
        metadata.get("file_name"),
        request.title,
        request.file_url,
    ]
    for candidate in candidates:
        suffix = _suffix_from_value(candidate)
        if suffix:
            return suffix
    suffix = Path(request.file_url.split("?", 1)[0]).suffix
    return suffix or ".bin"


def _suffix_from_value(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    filename = text.split("?", 1)[0].split("#", 1)[0]
    normalized = normalize_file_type(Path(filename), text)
    mapped = {
        "word": ".docx",
        "pdf": ".pdf",
        "ppt": ".pptx",
        "txt": ".txt",
        "image": ".png",
        "audio": ".mp3",
        "video": ".mp4",
    }
    if normalized in mapped:
        return mapped[normalized]
    suffix = Path(filename).suffix
    return suffix if suffix else ""
