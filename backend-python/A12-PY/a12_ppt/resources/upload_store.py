import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


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
    text = extract_text(file_path)
    text_path = resource_dir / "content.txt"
    text_path.write_text(text, encoding="utf-8")
    return ResourceRecord(
        resource_id=resource_id,
        filename=filename,
        content_type=file.content_type or "",
        file_path=file_path,
        text_path=text_path,
        text=text,
    )


def load_resource_text(resource_id: str) -> str:
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


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _extract_docx(path)
    if suffix in {".txt", ".md", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore")
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
