import json
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from ..direct_auth import direct_user_id
from .parsers import parse_resource_file

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "resources"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ResourceRecord:
    resource_id: str
    filename: str
    content_type: str
    file_path: Path
    text_path: Path
    text: str


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    return re.sub(r"[^a-zA-Z0-9._\-\u4e00-\u9fff]", "_", name)


async def save_upload(file: UploadFile) -> ResourceRecord:
    resource_id = f"res_{uuid.uuid4().hex[:16]}"
    filename = _safe_filename(file.filename or f"{resource_id}.bin")
    resource_dir = DATA_DIR / resource_id
    resource_dir.mkdir(parents=True, exist_ok=True)
    file_path = resource_dir / filename
    content = await file.read()
    file_path.write_bytes(content)
    parsed = await parse_resource_file(file_path, file.content_type, filename)
    text = parsed.text
    text_path = resource_dir / "content.txt"
    text_path.write_text(text, encoding="utf-8")
    metadata_path = resource_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps({**parsed.metadata, "owner_user_id": direct_user_id.get()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ResourceRecord(
        resource_id=resource_id,
        filename=filename,
        content_type=file.content_type or "",
        file_path=file_path,
        text_path=text_path,
        text=text,
    )


def load_resource_text(resource_id: str) -> str:
    if not re.fullmatch(r"res_[0-9a-f]{16}", resource_id):
        return ""
    user_id = direct_user_id.get()
    if user_id:
        metadata_path = DATA_DIR / resource_id / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        if str(metadata.get("owner_user_id") or "") != user_id:
            return ""
    text_path = DATA_DIR / resource_id / "content.txt"
    if not text_path.exists():
        return ""
    return text_path.read_text(encoding="utf-8", errors="ignore")


def build_rag_context(resource_ids: list[str], limit: int = 12000) -> str:
    chunks: list[str] = []
    remaining = limit
    for resource_id in resource_ids:
        text = load_resource_text(resource_id).strip()
        if not text:
            continue
        excerpt = text[:remaining]
        chunks.append(f"[{resource_id}]\n{excerpt}")
        remaining -= len(excerpt)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)


def delete_temp_upload_resources(resource_ids: list[str], owner_user_id: str | None = None) -> dict:
    """按 res_xxx 清理临时上传：删除 data/resources/{rid} 目录（owner 校验通过时）。

    只删磁盘目录；temp 向量索引由调用方走 index_store.delete_resource('temp', rid) 清理。
    """
    deleted: list[str] = []
    missing: list[str] = []
    denied: list[str] = []
    for raw_id in resource_ids or []:
        resource_id = str(raw_id or "").strip()
        if not re.fullmatch(r"res_[0-9a-f]{16}", resource_id):
            missing.append(resource_id)
            continue
        resource_dir = DATA_DIR / resource_id
        if not resource_dir.exists():
            missing.append(resource_id)
            continue
        if owner_user_id:
            try:
                metadata = json.loads((resource_dir / "metadata.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                metadata = {}
            if str(metadata.get("owner_user_id") or "") != owner_user_id:
                denied.append(resource_id)
                continue
        shutil.rmtree(resource_dir, ignore_errors=True)
        deleted.append(resource_id)
    return {"deleted": deleted, "missing": missing, "denied": denied}


def extract_text(path: Path) -> str:
    import asyncio

    try:
        return asyncio.run(parse_resource_file(path)).text
    except RuntimeError:
        return ""


def _extract_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception:
        return ""
