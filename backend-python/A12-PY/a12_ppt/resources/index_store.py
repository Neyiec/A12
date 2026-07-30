import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..models import ResourceIndexMetadataRequest, ResourceIndexSyncRequest
from .chunks import chunk_text
from .downloader import download_and_extract_text
from .identity import resource_fingerprint, resource_key
from .records import IndexedChunk


INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "resource_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_INDEX_PATH = INDEX_DIR / "index.json"


class ResourceIndexStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.available = False
        self._ensure_postgres()

    def _connect(self):
        import psycopg

        return psycopg.connect(self.settings.postgres_dsn)

    def _ensure_postgres(self) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS a12_resource_index (
                            resource_key TEXT PRIMARY KEY,
                            source_type TEXT NOT NULL,
                            resource_id TEXT NOT NULL,
                            file_url TEXT NOT NULL,
                            file_fingerprint TEXT NOT NULL,
                            title TEXT NOT NULL,
                            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                            available BOOLEAN NOT NULL DEFAULT TRUE,
                            allow_ai BOOLEAN NOT NULL DEFAULT TRUE,
                            parse_status TEXT NOT NULL DEFAULT 'pending',
                            error_message TEXT,
                            text_length INTEGER NOT NULL DEFAULT 0,
                            chunk_count INTEGER NOT NULL DEFAULT 0,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            indexed_at TIMESTAMPTZ
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS a12_resource_index_chunk (
                            chunk_id TEXT PRIMARY KEY,
                            resource_key TEXT NOT NULL REFERENCES a12_resource_index(resource_key) ON DELETE CASCADE,
                            source_type TEXT NOT NULL,
                            resource_id TEXT NOT NULL,
                            chunk_index INTEGER NOT NULL,
                            content TEXT NOT NULL,
                            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_a12_resource_index_available ON a12_resource_index(source_type, available, allow_ai)"
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_a12_resource_chunk_resource ON a12_resource_index_chunk(resource_key)"
                    )
            self.available = True
        except Exception:
            self.available = False

    async def sync_resource(self, request: ResourceIndexSyncRequest) -> dict[str, Any]:
        metadata = self._build_metadata(request)
        key = resource_key(request.source_type, request.resource_id)
        fingerprint = resource_fingerprint(request)
        existing = self._load_resource_meta(key)
        should_parse = (
            request.force_reparse
            or not existing
            or existing.get("file_fingerprint") != fingerprint
            or existing.get("parse_status") != "completed"
        )
        if not should_parse:
            self.update_metadata(ResourceIndexMetadataRequest(
                source_type=request.source_type,
                resource_id=request.resource_id,
                available=request.available,
                allow_ai=request.allow_ai,
                metadata=metadata,
            ))
            return {
                "resource_key": key,
                "status": "skipped",
                "reason": "already_indexed",
                "chunk_count": existing.get("chunk_count", 0),
            }

        try:
            text = await download_and_extract_text(request)
            chunks = chunk_text(text)
            self._replace_index(request, metadata, fingerprint, text, chunks)
            return {
                "resource_key": key,
                "status": "indexed",
                "text_length": len(text),
                "chunk_count": len(chunks),
            }
        except Exception as exc:
            self._record_failure(request, metadata, fingerprint, str(exc))
            return {
                "resource_key": key,
                "status": "failed",
                "error_message": str(exc),
            }

    async def bootstrap(self, resources: list[ResourceIndexSyncRequest], force_reparse: bool = False) -> dict[str, Any]:
        results = []
        for resource in resources:
            if force_reparse:
                resource.force_reparse = True
            results.append(await self.sync_resource(resource))
        return {
            "total": len(resources),
            "indexed": sum(1 for item in results if item.get("status") == "indexed"),
            "skipped": sum(1 for item in results if item.get("status") == "skipped"),
            "failed": sum(1 for item in results if item.get("status") == "failed"),
            "results": results,
        }

    def update_metadata(self, request: ResourceIndexMetadataRequest) -> dict[str, Any]:
        key = resource_key(request.source_type, request.resource_id)
        existing = self._load_resource_meta(key)
        if not existing:
            return {"resource_key": key, "status": "missing"}
        metadata = dict(existing.get("metadata") or {})
        metadata.update(request.metadata or {})
        if request.available is not None:
            metadata["available"] = request.available
        if request.allow_ai is not None:
            metadata["allow_ai"] = request.allow_ai

        available = bool(metadata.get("available", existing.get("available", True)))
        allow_ai = bool(metadata.get("allow_ai", existing.get("allow_ai", True)))
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE a12_resource_index
                        SET metadata = %s::jsonb, available = %s, allow_ai = %s, updated_at = NOW()
                        WHERE resource_key = %s
                        """,
                        (json.dumps(metadata, ensure_ascii=False), available, allow_ai, key),
                    )
                    cur.execute(
                        "UPDATE a12_resource_index_chunk SET metadata = %s::jsonb WHERE resource_key = %s",
                        (json.dumps(metadata, ensure_ascii=False), key),
                    )
        else:
            data = self._read_fallback()
            if key in data.get("resources", {}):
                data["resources"][key]["metadata"] = metadata
                data["resources"][key]["available"] = available
                data["resources"][key]["allow_ai"] = allow_ai
                for chunk in data.get("chunks", {}).get(key, []):
                    chunk["metadata"] = metadata
                self._write_fallback(data)
        return {"resource_key": key, "status": "updated", "available": available, "allow_ai": allow_ai}

    def delete_resource(self, source_type: str, resource_id: str) -> dict[str, Any]:
        key = resource_key(source_type, resource_id)
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM a12_resource_index WHERE resource_key = %s", (key,))
        else:
            data = self._read_fallback()
            data.get("resources", {}).pop(key, None)
            data.get("chunks", {}).pop(key, None)
            self._write_fallback(data)
        return {"resource_key": key, "status": "deleted"}

    def search_context(self, resource_ids: list[str], query: str, limit: int = 12000) -> dict[str, Any]:
        chunks = self._load_chunks(resource_ids)
        if not chunks:
            return {"context": "", "matches": []}
        keywords = [word.lower() for word in re.findall(r"[\w\u4e00-\u9fff]+", query or "") if len(word) > 1]
        scored: list[tuple[int, IndexedChunk]] = []
        for chunk in chunks:
            lower = chunk.content.lower()
            score = sum(1 for keyword in keywords if keyword in lower)
            if score or not keywords:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [chunk for _, chunk in scored[:8]]
        matches = [
            {
                "resource_id": f"{chunk.source_type}:{chunk.resource_id}",
                "chunk_id": chunk.chunk_id,
                "content": chunk.content[:1500],
                "metadata": chunk.metadata,
            }
            for chunk in selected
        ]
        context = "\n\n".join(
            f"[{item['resource_id']}#{item['chunk_id']}]\n{item['content']}" for item in matches
        )[:limit]
        return {"context": context, "matches": matches}

    def _build_metadata(self, request: ResourceIndexSyncRequest) -> dict[str, Any]:
        metadata = dict(request.metadata or {})
        metadata.update({
            "source": request.source_type,
            "source_type": request.source_type,
            "resource_id": request.resource_id,
            "resource_key": resource_key(request.source_type, request.resource_id),
            "mysql_table": "adm_resource" if request.source_type == "public" else "res_material",
            "uploaded_by": request.uploaded_by,
            "owner_user_id": request.owner_user_id,
            "available": request.available,
            "allow_ai": request.allow_ai,
            "file_url": request.file_url,
            "file_type": request.file_type,
            "file_size": request.file_size,
            "title": request.title,
        })
        return metadata

    def _replace_index(self, request: ResourceIndexSyncRequest, metadata: dict[str, Any], fingerprint: str, text: str, chunks: list[str]) -> None:
        key = resource_key(request.source_type, request.resource_id)
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM a12_resource_index_chunk WHERE resource_key = %s", (key,))
                    cur.execute(
                        """
                        INSERT INTO a12_resource_index(resource_key, source_type, resource_id, file_url, file_fingerprint,
                            title, metadata, available, allow_ai, parse_status, error_message, text_length, chunk_count, indexed_at, updated_at)
                        VALUES(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, 'completed', NULL, %s, %s, NOW(), NOW())
                        ON CONFLICT(resource_key) DO UPDATE SET
                            file_url = EXCLUDED.file_url,
                            file_fingerprint = EXCLUDED.file_fingerprint,
                            title = EXCLUDED.title,
                            metadata = EXCLUDED.metadata,
                            available = EXCLUDED.available,
                            allow_ai = EXCLUDED.allow_ai,
                            parse_status = 'completed',
                            error_message = NULL,
                            text_length = EXCLUDED.text_length,
                            chunk_count = EXCLUDED.chunk_count,
                            indexed_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            key, request.source_type, request.resource_id, request.file_url, fingerprint,
                            request.title, json.dumps(metadata, ensure_ascii=False), request.available, request.allow_ai,
                            len(text), len(chunks),
                        ),
                    )
                    for index, chunk in enumerate(chunks):
                        chunk_id = f"{key}:{index}"
                        cur.execute(
                            """
                            INSERT INTO a12_resource_index_chunk(chunk_id, resource_key, source_type, resource_id, chunk_index, content, metadata)
                            VALUES(%s, %s, %s, %s, %s, %s, %s::jsonb)
                            """,
                            (chunk_id, key, request.source_type, request.resource_id, index, chunk, json.dumps(metadata, ensure_ascii=False)),
                        )
        else:
            data = self._read_fallback()
            data.setdefault("resources", {})[key] = {
                "resource_key": key,
                "source_type": request.source_type,
                "resource_id": request.resource_id,
                "file_url": request.file_url,
                "file_fingerprint": fingerprint,
                "title": request.title,
                "metadata": metadata,
                "available": request.available,
                "allow_ai": request.allow_ai,
                "parse_status": "completed",
                "text_length": len(text),
                "chunk_count": len(chunks),
            }
            data.setdefault("chunks", {})[key] = [
                asdict(IndexedChunk(
                    chunk_id=f"{key}:{index}",
                    source_type=request.source_type,
                    resource_id=request.resource_id,
                    chunk_index=index,
                    content=chunk,
                    metadata=metadata,
                ))
                for index, chunk in enumerate(chunks)
            ]
            self._write_fallback(data)

    def _record_failure(self, request: ResourceIndexSyncRequest, metadata: dict[str, Any], fingerprint: str, error_message: str) -> None:
        key = resource_key(request.source_type, request.resource_id)
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO a12_resource_index(resource_key, source_type, resource_id, file_url, file_fingerprint,
                            title, metadata, available, allow_ai, parse_status, error_message, updated_at)
                        VALUES(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, 'failed', %s, NOW())
                        ON CONFLICT(resource_key) DO UPDATE SET
                            metadata = EXCLUDED.metadata,
                            available = EXCLUDED.available,
                            allow_ai = EXCLUDED.allow_ai,
                            parse_status = 'failed',
                            error_message = EXCLUDED.error_message,
                            updated_at = NOW()
                        """,
                        (
                            key, request.source_type, request.resource_id, request.file_url, fingerprint,
                            request.title, json.dumps(metadata, ensure_ascii=False), request.available, request.allow_ai,
                            error_message[:2000],
                        ),
                    )

    def _load_resource_meta(self, resource_key: str) -> dict[str, Any] | None:
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT file_fingerprint, parse_status, chunk_count, metadata, available, allow_ai FROM a12_resource_index WHERE resource_key = %s",
                        (resource_key,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "file_fingerprint": row[0],
                        "parse_status": row[1],
                        "chunk_count": row[2],
                        "metadata": row[3],
                        "available": row[4],
                        "allow_ai": row[5],
                    }
        return self._read_fallback().get("resources", {}).get(resource_key)

    def _load_chunks(self, resource_ids: list[str]) -> list[IndexedChunk]:
        keys = [resource_id for resource_id in resource_ids if ":" in resource_id]
        if not keys:
            return []
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT chunk_id, source_type, resource_id, chunk_index, content, metadata
                        FROM a12_resource_index_chunk
                        WHERE resource_key = ANY(%s)
                          AND (metadata->>'available')::boolean IS TRUE
                          AND (metadata->>'allow_ai')::boolean IS TRUE
                        ORDER BY resource_key, chunk_index
                        """,
                        (keys,),
                    )
                    return [
                        IndexedChunk(
                            chunk_id=row[0],
                            source_type=row[1],
                            resource_id=row[2],
                            chunk_index=row[3],
                            content=row[4],
                            metadata=row[5] or {},
                        )
                        for row in cur.fetchall()
                    ]
        data = self._read_fallback()
        chunks: list[IndexedChunk] = []
        for key in keys:
            meta = data.get("resources", {}).get(key, {})
            if not meta.get("available", True) or not meta.get("allow_ai", True):
                continue
            chunks.extend(IndexedChunk(**chunk) for chunk in data.get("chunks", {}).get(key, []))
        return chunks

    def _read_fallback(self) -> dict[str, Any]:
        if not FALLBACK_INDEX_PATH.exists():
            return {"resources": {}, "chunks": {}}
        return json.loads(FALLBACK_INDEX_PATH.read_text(encoding="utf-8"))

    def _write_fallback(self, data: dict[str, Any]) -> None:
        FALLBACK_INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


resource_index_store = ResourceIndexStore()
