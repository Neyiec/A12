import tempfile
from pathlib import Path

import httpx

from ..models import ResourceIndexSyncRequest
from .upload_store import extract_text


async def download_and_extract_text(request: ResourceIndexSyncRequest) -> str:
    suffix = guess_suffix(request)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp_path = Path(temp.name)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(request.file_url)
            response.raise_for_status()
            temp_path.write_bytes(response.content)
        return extract_text(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def guess_suffix(request: ResourceIndexSyncRequest) -> str:
    file_type = (request.file_type or "").lower()
    if file_type in {"word", "doc", "docx"}:
        return ".docx"
    if file_type == "pdf":
        return ".pdf"
    if file_type in {"txt", "text", "md", "markdown"}:
        return ".txt"
    suffix = Path(request.file_url.split("?", 1)[0]).suffix
    return suffix or ".bin"
