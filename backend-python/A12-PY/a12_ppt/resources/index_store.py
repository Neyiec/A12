import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..llm import EmbeddingClient
from ..models import ResourceIndexMetadataRequest, ResourceIndexSyncRequest
from .chunks import chunk_text
from .downloader import download_and_parse_resource
from .identity import resource_fingerprint, resource_key
from .records import IndexedChunk
from .similarity import cosine_similarity, embedding_to_pgvector, keyword_score


INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "resource_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_INDEX_PATH = INDEX_DIR / "index.json"
FALLBACK_RETRIEVAL_LOG_PATH = INDEX_DIR / "retrieval_logs.jsonl"


class ResourceIndexStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_client = EmbeddingClient()
        self.embedding_dimensions = self.settings.embedding_dimensions or self._default_embedding_dimensions()
        self.available = False
        self._ensure_postgres()

    def _connect(self):
        import psycopg

        return psycopg.connect(self.settings.postgres_dsn, connect_timeout = 60)
    def _ensure_postgres(self) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "CREATE EXTENSION IF NOT EXISTS vector"
                    )
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
                            embedding_vector vector(%s),
                            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """ % self.embedding_dimensions
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_a12_resource_index_available ON a12_resource_index(source_type, available, allow_ai)"
                    )
                    cur.execute(
                        "ALTER TABLE a12_resource_index_chunk ADD COLUMN IF NOT EXISTS embedding_vector vector(%s)" % self.embedding_dimensions
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_a12_resource_chunk_resource ON a12_resource_index_chunk(resource_key)"
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS a12_retrieval_log (
                            id BIGSERIAL PRIMARY KEY,
                            query TEXT NOT NULL,
                            resource_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                            match_count INTEGER NOT NULL DEFAULT 0,
                            top_score DOUBLE PRECISION DEFAULT NULL,
                            search_mode TEXT NOT NULL DEFAULT 'unknown',
                            latency_ms INTEGER NOT NULL DEFAULT 0,
                            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_a12_retrieval_log_created ON a12_retrieval_log(created_at DESC)"
                    )
            self.available = True
            self._ensure_vector_index()
        except Exception:
            self.available = False

    def _ensure_vector_index(self) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_a12_resource_chunk_embedding_hnsw
                        ON a12_resource_index_chunk
                        USING hnsw (embedding_vector vector_cosine_ops)
                        """
                    )
        except Exception:
            pass

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
            parsed = await download_and_parse_resource(request)
            metadata["parse"] = parsed.metadata
            text = parsed.text
            chunks = chunk_text(text, metadata=metadata)
            try:
                embeddings = await self.embedding_client.embed_documents(chunks)
            except Exception:
                embeddings = []
            self._replace_index(request, metadata, fingerprint, text, chunks, embeddings)
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

    async def search_context(self, resource_ids: list[str], query: str, limit: int = 12000, top_k: int = 8) -> dict[str, Any]:
        started_at = time.perf_counter()
        search_mode = "empty"
        matches: list[dict[str, Any]] = []
        try:
            query_embedding = await self.embedding_client.embed_query(query)
        except Exception:
            query_embedding = []
        if self.available and len(query_embedding) == self.embedding_dimensions:
            try:
                vector_result = self._search_pgvector(resource_ids, query, query_embedding, limit, max(top_k * 4, top_k))
            except Exception:
                vector_result = {"context": "", "matches": []}
            if vector_result.get("matches"):
                matches = self._rerank_matches(vector_result["matches"], query, top_k)
                search_mode = "pgvector_hybrid_rerank"
                result = self._build_search_result(query, matches, limit, search_mode)
                result["latency_ms"] = self._elapsed_ms(started_at)
                self._record_retrieval_log(query, resource_ids, matches, search_mode, result["latency_ms"], {
                    "embedding": True,
                    "postgres": True,
                })
                return result

        chunks = self._load_chunks(resource_ids)
        if not chunks:
            latency_ms = self._elapsed_ms(started_at)
            self._record_retrieval_log(query, resource_ids, [], "no_match", latency_ms, {
                "embedding": bool(query_embedding),
                "postgres": self.available,
            })
            return {"query": query, "context": "", "matches": [], "search_mode": "no_match", "latency_ms": latency_ms}

        scored: list[tuple[float, str, IndexedChunk]] = []
        for chunk in chunks:
            if query_embedding and chunk.embedding:
                score = cosine_similarity(query_embedding, chunk.embedding)
                match_type = "embedding_fallback"
            else:
                score = keyword_score(chunk.content, query)
                match_type = "keyword"
            if score > 0 or not query:
                scored.append((score, match_type, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = scored[:top_k] or [(0.0, "fallback", chunk) for chunk in chunks[:top_k]]
        matches = [
            {
                "resource_id": f"{chunk.source_type}:{chunk.resource_id}",
                "chunk_id": chunk.chunk_id,
                "content": chunk.content[:1500],
                "metadata": chunk.metadata,
                "score": round(score, 6),
                "match_type": match_type,
            }
            for score, match_type, chunk in selected
        ]
        matches = self._rerank_matches(matches, query, top_k)
        search_mode = "fallback_hybrid_rerank"
        result = self._build_search_result(query, matches, limit, search_mode)
        result["latency_ms"] = self._elapsed_ms(started_at)
        self._record_retrieval_log(query, resource_ids, matches, search_mode, result["latency_ms"], {
            "embedding": bool(query_embedding),
            "postgres": self.available,
        })
        return result

    def _search_pgvector(
        self,
        resource_ids: list[str],
        query: str,
        query_embedding: list[float],
        limit: int,
        top_k: int,
    ) -> dict[str, Any]:
        keys = [resource_id for resource_id in resource_ids if ":" in resource_id]
        query_vector = embedding_to_pgvector(query_embedding)
        if not query_vector:
            return {"context": "", "matches": []}
        key_filter = "AND resource_key = ANY(%s)" if keys else ""
        params: tuple[Any, ...]
        if keys:
            params = (query_vector, keys, query_vector, top_k)
        else:
            params = (query_vector, query_vector, top_k)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT chunk_id, source_type, resource_id, chunk_index, content, metadata,
                           1 - (embedding_vector <=> %s::vector) AS similarity
                    FROM a12_resource_index_chunk
                    WHERE embedding_vector IS NOT NULL
                      {key_filter}
                      AND COALESCE((metadata->>'available')::boolean, TRUE) IS TRUE
                      AND COALESCE((metadata->>'allow_ai')::boolean, TRUE) IS TRUE
                    ORDER BY embedding_vector <=> %s::vector
                    LIMIT %s
                    """,
                    params,
                )
                rows = cur.fetchall()
        matches = [
            {
                "resource_id": f"{row[1]}:{row[2]}",
                "chunk_id": row[0],
                "chunk_index": row[3],
                "content": row[4][:1500],
                "metadata": row[5] or {},
                "score": round(float(row[6] or 0.0), 6),
                "match_type": "pgvector_cosine",
            }
            for row in rows
        ]
        return {"query": query, "matches": matches}

    def overview(self) -> dict[str, Any]:
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*), COALESCE(SUM(chunk_count), 0) FROM a12_resource_index")
                    total_resources, total_chunks = cur.fetchone()
                    cur.execute(
                        """
                        SELECT source_type, parse_status, available, allow_ai, COUNT(*), COALESCE(SUM(chunk_count), 0)
                        FROM a12_resource_index
                        GROUP BY source_type, parse_status, available, allow_ai
                        ORDER BY source_type, parse_status
                        """
                    )
                    groups = [
                        {
                            "source_type": row[0],
                            "parse_status": row[1],
                            "available": row[2],
                            "allow_ai": row[3],
                            "resource_count": row[4],
                            "chunk_count": row[5],
                        }
                        for row in cur.fetchall()
                    ]
                    cur.execute("SELECT COUNT(*) FROM a12_retrieval_log")
                    retrieval_log_count = cur.fetchone()[0]
            return {
                "postgres_available": True,
                "embedding_dimensions": self.embedding_dimensions,
                "resource_count": total_resources,
                "chunk_count": total_chunks,
                "retrieval_log_count": retrieval_log_count,
                "groups": groups,
                "fallback_path": str(FALLBACK_INDEX_PATH),
            }

        data = self._read_fallback()
        resources = list(data.get("resources", {}).values())
        return {
            "postgres_available": False,
            "embedding_dimensions": self.embedding_dimensions,
            "resource_count": len(resources),
            "chunk_count": sum(len(items) for items in data.get("chunks", {}).values()),
            "retrieval_log_count": self._fallback_log_count(),
            "groups": self._fallback_groups(resources),
            "fallback_path": str(FALLBACK_INDEX_PATH),
        }

    def list_resources(
        self,
        source_type: str | None = None,
        available: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        if self.available:
            filters = []
            params: list[Any] = []
            if source_type:
                filters.append("source_type = %s")
                params.append(source_type)
            if available is not None:
                filters.append("available = %s")
                params.append(available)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM a12_resource_index {where}", tuple(params))
                    total = cur.fetchone()[0]
                    cur.execute(
                        f"""
                        SELECT resource_key, source_type, resource_id, title, available, allow_ai,
                               parse_status, error_message, text_length, chunk_count, metadata, indexed_at, updated_at
                        FROM a12_resource_index
                        {where}
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        tuple(params + [limit, offset]),
                    )
                    items = [self._resource_row(row) for row in cur.fetchall()]
            return {"total": total, "limit": limit, "offset": offset, "items": items}

        resources = list(self._read_fallback().get("resources", {}).values())
        if source_type:
            resources = [item for item in resources if item.get("source_type") == source_type]
        if available is not None:
            resources = [item for item in resources if bool(item.get("available", True)) is available]
        total = len(resources)
        items = resources[offset:offset + limit]
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    def get_resource(self, source_type: str, resource_id: str, chunk_limit: int = 20) -> dict[str, Any] | None:
        key = resource_key(source_type, resource_id)
        chunk_limit = max(0, min(chunk_limit, 200))
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT resource_key, source_type, resource_id, title, available, allow_ai,
                               parse_status, error_message, text_length, chunk_count, metadata, indexed_at, updated_at
                        FROM a12_resource_index
                        WHERE resource_key = %s
                        """,
                        (key,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    resource = self._resource_row(row)
                    cur.execute(
                        """
                        SELECT chunk_id, chunk_index, content, metadata
                        FROM a12_resource_index_chunk
                        WHERE resource_key = %s
                        ORDER BY chunk_index
                        LIMIT %s
                        """,
                        (key, chunk_limit),
                    )
                    resource["chunks"] = [
                        {
                            "chunk_id": chunk[0],
                            "chunk_index": chunk[1],
                            "content": chunk[2][:1500],
                            "metadata": chunk[3] or {},
                        }
                        for chunk in cur.fetchall()
                    ]
                    return resource

        data = self._read_fallback()
        resource = data.get("resources", {}).get(key)
        if not resource:
            return None
        result = dict(resource)
        result["chunks"] = data.get("chunks", {}).get(key, [])[:chunk_limit]
        return result

    def list_retrieval_logs(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM a12_retrieval_log")
                    total = cur.fetchone()[0]
                    cur.execute(
                        """
                        SELECT id, query, resource_ids, match_count, top_score, search_mode, latency_ms, metadata, created_at
                        FROM a12_retrieval_log
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    items = [
                        {
                            "id": row[0],
                            "query": row[1],
                            "resource_ids": row[2] or [],
                            "match_count": row[3],
                            "top_score": row[4],
                            "search_mode": row[5],
                            "latency_ms": row[6],
                            "metadata": row[7] or {},
                            "created_at": row[8].isoformat() if row[8] else None,
                        }
                        for row in cur.fetchall()
                    ]
            return {"total": total, "limit": limit, "offset": offset, "items": items}
        items = self._read_fallback_logs()
        total = len(items)
        return {"total": total, "limit": limit, "offset": offset, "items": items[offset:offset + limit]}

    def _rerank_matches(self, matches: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
        reranked: list[dict[str, Any]] = []
        for item in matches:
            base_score = float(item.get("score") or 0.0)
            lexical_score = keyword_score(str(item.get("content") or ""), query)
            metadata_score = self._metadata_score(item.get("metadata") or {}, query)
            exact_boost = 0.08 if query and query.strip() in str(item.get("content") or "") else 0.0
            rerank_score = (0.68 * base_score) + (0.24 * lexical_score) + metadata_score + exact_boost
            current = dict(item)
            current["base_score"] = round(base_score, 6)
            current["rerank_score"] = round(rerank_score, 6)
            current["match_type"] = f"{current.get('match_type', 'unknown')}+hybrid_rerank"
            reranked.append(current)
        reranked.sort(key=lambda item: item.get("rerank_score", item.get("score", 0.0)), reverse=True)
        for rank, item in enumerate(reranked[:top_k], start=1):
            item["rank"] = rank
            item["score"] = item.get("rerank_score", item.get("score", 0.0))
        return reranked[:top_k]

    def _metadata_score(self, metadata: dict[str, Any], query: str) -> float:
        if not query:
            return 0.0
        haystack = " ".join([
            str(metadata.get("title") or ""),
            str(metadata.get("subject") or ""),
            " ".join(str(item) for item in metadata.get("tags", []) if item is not None) if isinstance(metadata.get("tags"), list) else str(metadata.get("tags") or ""),
            " ".join(str(item) for item in metadata.get("categories", []) if item is not None) if isinstance(metadata.get("categories"), list) else str(metadata.get("categories") or ""),
        ])
        return min(keyword_score(haystack, query) * 0.12, 0.12)

    def _build_search_result(self, query: str, matches: list[dict[str, Any]], limit: int, search_mode: str) -> dict[str, Any]:
        context = "\n\n".join(
            f"[{item['resource_id']}#{item['chunk_id']} score={item.get('score', 0)}]\n{item['content']}"
            for item in matches
        )[:limit]
        return {
            "query": query,
            "context": context,
            "matches": matches,
            "search_mode": search_mode,
        }

    def _record_retrieval_log(
        self,
        query: str,
        resource_ids: list[str],
        matches: list[dict[str, Any]],
        search_mode: str,
        latency_ms: int,
        metadata: dict[str, Any],
    ) -> None:
        top_score = max((float(item.get("score") or 0.0) for item in matches), default=None)
        log_metadata = {
            **metadata,
            "top_matches": [
                {
                    "resource_id": item.get("resource_id"),
                    "chunk_id": item.get("chunk_id"),
                    "score": item.get("score"),
                    "rank": item.get("rank"),
                }
                for item in matches[:5]
            ],
        }
        if self.available:
            try:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO a12_retrieval_log(query, resource_ids, match_count, top_score, search_mode, latency_ms, metadata)
                            VALUES(%s, %s::jsonb, %s, %s, %s, %s, %s::jsonb)
                            """,
                            (
                                query[:4000],
                                json.dumps(resource_ids, ensure_ascii=False),
                                len(matches),
                                top_score,
                                search_mode,
                                latency_ms,
                                json.dumps(log_metadata, ensure_ascii=False),
                            ),
                        )
                return
            except Exception:
                pass
        self._append_fallback_log({
            "id": None,
            "query": query[:4000],
            "resource_ids": resource_ids,
            "match_count": len(matches),
            "top_score": top_score,
            "search_mode": search_mode,
            "latency_ms": latency_ms,
            "metadata": log_metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def _elapsed_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

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

    def _replace_index(
        self,
        request: ResourceIndexSyncRequest,
        metadata: dict[str, Any],
        fingerprint: str,
        text: str,
        chunks: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
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
                            INSERT INTO a12_resource_index_chunk(chunk_id, resource_key, source_type, resource_id, chunk_index, content, embedding_vector, metadata)
                            VALUES(%s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                            """,
                            (
                                chunk_id,
                                key,
                                request.source_type,
                                request.resource_id,
                                index,
                                chunk,
                                embedding_to_pgvector(self._embedding_at(embeddings, index)),
                                json.dumps(metadata, ensure_ascii=False),
                            ),
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
                    embedding=self._embedding_at(embeddings, index),
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
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    key_filter = "AND resource_key = ANY(%s)" if keys else ""
                    params: tuple[Any, ...] = (keys,) if keys else ()
                    cur.execute(
                        f"""
                        SELECT chunk_id, source_type, resource_id, chunk_index, content, embedding_vector::text, metadata
                        FROM a12_resource_index_chunk
                        WHERE COALESCE((metadata->>'available')::boolean, TRUE) IS TRUE
                          {key_filter}
                          AND COALESCE((metadata->>'allow_ai')::boolean, TRUE) IS TRUE
                        ORDER BY resource_key, chunk_index
                        """,
                        params,
                    )
                    return [
                        IndexedChunk(
                            chunk_id=row[0],
                            source_type=row[1],
                            resource_id=row[2],
                            chunk_index=row[3],
                            content=row[4],
                            embedding=self._parse_pgvector(row[5]),
                            metadata=row[6] or {},
                        )
                        for row in cur.fetchall()
                    ]
        data = self._read_fallback()
        chunks: list[IndexedChunk] = []
        target_keys = keys or list(data.get("chunks", {}).keys())
        for key in target_keys:
            meta = data.get("resources", {}).get(key, {})
            if not meta.get("available", True) or not meta.get("allow_ai", True):
                continue
            chunks.extend(IndexedChunk(**chunk) for chunk in data.get("chunks", {}).get(key, []))
        return chunks

    def _resource_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "resource_key": row[0],
            "source_type": row[1],
            "resource_id": row[2],
            "title": row[3],
            "available": row[4],
            "allow_ai": row[5],
            "parse_status": row[6],
            "error_message": row[7],
            "text_length": row[8],
            "chunk_count": row[9],
            "metadata": row[10] or {},
            "indexed_at": row[11].isoformat() if row[11] else None,
            "updated_at": row[12].isoformat() if row[12] else None,
        }

    def _fallback_groups(self, resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str, bool, bool], dict[str, Any]] = {}
        for item in resources:
            key = (
                str(item.get("source_type") or "unknown"),
                str(item.get("parse_status") or "unknown"),
                bool(item.get("available", True)),
                bool(item.get("allow_ai", True)),
            )
            group = groups.setdefault(key, {
                "source_type": key[0],
                "parse_status": key[1],
                "available": key[2],
                "allow_ai": key[3],
                "resource_count": 0,
                "chunk_count": 0,
            })
            group["resource_count"] += 1
            group["chunk_count"] += int(item.get("chunk_count") or 0)
        return list(groups.values())

    def _fallback_log_count(self) -> int:
        if not FALLBACK_RETRIEVAL_LOG_PATH.exists():
            return 0
        return sum(1 for line in FALLBACK_RETRIEVAL_LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip())

    def _read_fallback_logs(self) -> list[dict[str, Any]]:
        if not FALLBACK_RETRIEVAL_LOG_PATH.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in FALLBACK_RETRIEVAL_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
        items.reverse()
        return items

    def _append_fallback_log(self, item: dict[str, Any]) -> None:
        with FALLBACK_RETRIEVAL_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _default_embedding_dimensions(self) -> int:
        model = (self.settings.embedding_model or "").lower()
        if "3-large" in model:
            return 3072
        return 1536

    def _parse_pgvector(self, value: str | None) -> list[float] | None:
        if not value:
            return None
        return [float(item) for item in value.strip("[]").split(",") if item]

    def _embedding_at(self, embeddings: list[list[float]] | None, index: int) -> list[float] | None:
        if not embeddings or index >= len(embeddings):
            return None
        embedding = embeddings[index]
        return embedding if len(embedding) == self.embedding_dimensions else None

    def _read_fallback(self) -> dict[str, Any]:
        if not FALLBACK_INDEX_PATH.exists():
            return {"resources": {}, "chunks": {}}
        return json.loads(FALLBACK_INDEX_PATH.read_text(encoding="utf-8"))

    def _write_fallback(self, data: dict[str, Any]) -> None:
        FALLBACK_INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


resource_index_store = ResourceIndexStore()
