import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..direct_auth import direct_user_id
from ..llm import EmbeddingClient
from ..models import ResourceIndexMetadataRequest, ResourceIndexSyncRequest
from .chunks import chunk_records
from .downloader import download_and_parse_resource
from .identity import resource_fingerprint, resource_key
from .records import IndexedChunk
from .similarity import cosine_similarity, embedding_to_pgvector, keyword_score

# 统一日志约定：[%(levelname)s] %(filename)s: %(message)s（main.py 启动时 basicConfig）
logger = logging.getLogger("a12_ppt.resources.index_store")


INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "resource_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_INDEX_PATH = INDEX_DIR / "index.json"
FALLBACK_RETRIEVAL_LOG_PATH = INDEX_DIR / "retrieval_logs.jsonl"


class ResourceIndexStore:
    @staticmethod
    def _visible(source_type: str, metadata: dict[str, Any]) -> bool:
        user_id = direct_user_id.get()
        return user_id is None or source_type == "public" or str(metadata.get("owner_user_id") or "") == user_id

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
                    # temp 分区（临时上传）为后加分区：老库按旧 CHECK 建表时需放行 'temp'。
                    cur.execute("ALTER TABLE a12_resource_index DROP CONSTRAINT IF EXISTS ck_a12_resource_index_source")
                    cur.execute(
                        "ALTER TABLE a12_resource_index ADD CONSTRAINT ck_a12_resource_index_source "
                        "CHECK (source_type IN ('public', 'personal', 'temp'))"
                    )
            self.available = True
            self._ensure_vector_index()
        except Exception:
            self.available = False
            # PG 不可用会静默降级为本地 JSON 文件存储，RAG 检索将无法命中——必须把原因打进日志
            logger.error("PostgreSQL 初始化失败，资源索引降级为本地文件存储（RAG 将无法命中）", exc_info=True)

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
            logger.warning("创建 HNSW 向量索引失败（不影响写入，仅影响检索性能）", exc_info=True)

    async def sync_resource(self, request: ResourceIndexSyncRequest) -> dict[str, Any]:
        started_at = time.perf_counter()
        metadata = self._build_metadata(request)
        key = resource_key(request.source_type, request.resource_id)
        # 请求指纹只用于下载/解析失败时留下可诊断标识；成功后会用文件内容
        # SHA-256 覆盖它，避免签名 URL 变化或同尺寸文件替换造成误判。
        fingerprint = resource_fingerprint(request)
        existing = self._load_resource_meta(key)
        if not self.available:
            logger.warning("sync_resource 于降级模式执行（PG 不可用，仅写本地文件） resource_key=%s", key)
        try:
            existing_metadata = (existing or {}).get("metadata") or {}
            existing_parse = existing_metadata.get("parse") if isinstance(existing_metadata.get("parse"), dict) else {}
            previous_digest = None
            if not request.force_reparse and existing and existing.get("parse_status") == "completed":
                previous_digest = existing_parse.get("content_sha256") or existing.get("file_fingerprint")
            # 下载+解析整体限时：大文件解析卡死时按超时转为 failed，而不是无限挂起拖垮调用方
            parsed = await asyncio.wait_for(
                download_and_parse_resource(request, previous_digest=previous_digest),
                timeout=self.settings.index_parse_timeout_seconds,
            )
            if parsed.metadata.get("unchanged") and existing and existing.get("parse_status") == "completed":
                # 保留上次解析元数据和内容摘要，只刷新授权及业务元数据。
                metadata["parse"] = {**existing_parse, **parsed.metadata}
                self.update_metadata(ResourceIndexMetadataRequest(
                    source_type=request.source_type,
                    resource_id=request.resource_id,
                    available=request.available,
                    allow_ai=request.allow_ai,
                    metadata=metadata,
                ))
                elapsed = round((time.perf_counter() - started_at) * 1000)
                return {
                    "resource_key": key,
                    "status": "skipped",
                    "reason": "content_sha256_unchanged",
                    "content_sha256": previous_digest,
                    "chunk_count": existing.get("chunk_count", 0),
                    "latency_ms": elapsed,
                }
            metadata["parse"] = parsed.metadata
            fingerprint = str(parsed.metadata.get("content_sha256") or fingerprint)
            text = parsed.text
            if not text.strip():
                raise ValueError("资料未解析出有效文本，请检查格式、OCR、视觉模型或语音转写服务")
            chunk_items = chunk_records(text, metadata=metadata)
            chunks = [item["content"] for item in chunk_items]
            chunk_metadata = [self._compact_chunk_metadata(metadata, item.get("metadata") or {}) for item in chunk_items]
            # 向量化失败必须显式 failed：静默返回空向量会产生「假 indexed」（有分块无向量，RAG 永远查不到）
            try:
                embeddings = await self.embedding_client.embed_documents(chunks)
            except Exception as exc:
                logger.error("向量化失败 resource_key=%s chunks=%d: %s", key, len(chunks), exc)
                message = f"向量化失败: {exc}"
                self._record_failure(request, metadata, fingerprint, message)
                return {
                    "resource_key": key,
                    "status": "failed",
                    "error_message": message,
                }
            self._replace_index(request, metadata, fingerprint, text, chunks, embeddings, chunk_metadata)
            # Graph evidence follows successful indexing, but cannot make RAG ingestion fail.
            course_id = str((request.metadata or {}).get("course_id") or "").strip()
            if course_id and request.owner_user_id:
                try:
                    from ..course_graph import course_graph_store
                    course_graph_store.add_resource_evidence(
                        str(request.owner_user_id), course_id, key, fingerprint, text)
                except Exception:
                    logger.warning("课程图谱证据更新失败 resource_key=%s", key, exc_info=True)
            elapsed = round((time.perf_counter() - started_at) * 1000)
            logger.info(
                "sync_resource 完成 resource_key=%s status=indexed text_length=%d chunks=%d embeddings=%d 耗时=%dms",
                key, len(text), len(chunks), len(embeddings), elapsed,
            )
            return {
                "resource_key": key,
                "status": "indexed",
                "text_length": len(text),
                "chunk_count": len(chunks),
            }
        except asyncio.TimeoutError:
            elapsed = round((time.perf_counter() - started_at) * 1000)
            message = f"下载/解析超时（>{self.settings.index_parse_timeout_seconds:.0f}s，实际 {elapsed}ms）"
            logger.error("sync_resource 超时 resource_key=%s: %s", key, message)
            self._record_failure(request, metadata, fingerprint, message)
            return {"resource_key": key, "status": "failed", "error_message": message}
        except Exception as exc:
            logger.error("sync_resource 失败 resource_key=%s: %s", key, exc, exc_info=True)
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

    async def index_local_text(
        self,
        *,
        source_type: str,
        resource_id: str,
        title: str,
        text: str,
        owner_user_id: str | None = None,
        file_url: str = "",
        file_type: str | None = None,
        file_size: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """已在本机落盘的资料（临时上传）直接分块向量化，跳过下载/解析阶段。

        与 sync_resource 一致：向量化失败显式返回 failed，绝不写「有分块无向量」的假索引。
        """
        if not text.strip():
            return {"resource_key": resource_key(source_type, resource_id), "status": "failed", "error_message": "资料未解析出有效文本"}
        request = ResourceIndexSyncRequest(
            source_type=source_type,
            resource_id=resource_id,
            title=title,
            file_url=file_url or f"local:{resource_id}",
            file_type=file_type,
            file_size=file_size,
            owner_user_id=owner_user_id,
            uploaded_by=owner_user_id,
            metadata=dict(metadata or {}),
        )
        built_metadata = self._build_metadata(request)
        try:
            chunk_items = chunk_records(text, metadata=built_metadata)
            chunks = [item["content"] for item in chunk_items]
            chunk_metadata = [self._compact_chunk_metadata(built_metadata, item.get("metadata") or {}) for item in chunk_items]
            embeddings = await self.embedding_client.embed_documents(chunks)
        except Exception as exc:
            logger.error("临时资料向量化失败 resource_key=%s: %s", resource_key(source_type, resource_id), exc)
            return {
                "resource_key": resource_key(source_type, resource_id),
                "status": "failed",
                "error_message": f"向量化失败: {exc}",
            }
        fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._replace_index(request, built_metadata, fingerprint, text, chunks, embeddings, chunk_metadata)
        logger.info(
            "index_local_text 完成 resource_key=%s text_length=%d chunks=%d",
            resource_key(source_type, resource_id), len(text), len(chunks),
        )
        return {
            "resource_key": resource_key(source_type, resource_id),
            "status": "indexed",
            "text_length": len(text),
            "chunk_count": len(chunks),
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
        chunk_updates = self._compact_chunk_metadata(metadata, {})
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
                        "UPDATE a12_resource_index_chunk SET metadata = metadata || %s::jsonb WHERE resource_key = %s",
                        (json.dumps(chunk_updates, ensure_ascii=False), key),
                    )
        else:
            data = self._read_fallback()
            if key in data.get("resources", {}):
                data["resources"][key]["metadata"] = metadata
                data["resources"][key]["available"] = available
                data["resources"][key]["allow_ai"] = allow_ai
                for chunk in data.get("chunks", {}).get(key, []):
                    chunk["metadata"] = {**(chunk.get("metadata") or {}), **chunk_updates}
                self._write_fallback(data)
        return {"resource_key": key, "status": "updated", "available": available, "allow_ai": allow_ai}

    def delete_resource(self, source_type: str, resource_id: str) -> dict[str, Any]:
        key = resource_key(source_type, resource_id)
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM a12_resource_index WHERE resource_key = %s", (key,))
            try:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM a12_graph_evidence WHERE resource_key = %s", (key,))
            except Exception:
                logger.warning("清除课程图谱证据失败 resource_key=%s", key, exc_info=True)
        else:
            data = self._read_fallback()
            data.get("resources", {}).pop(key, None)
            data.get("chunks", {}).pop(key, None)
            self._write_fallback(data)
        return {"resource_key": key, "status": "deleted"}

    async def search_context(
        self,
        resource_ids: list[str],
        query: str,
        limit: int = 12000,
        top_k: int = 8,
        source_type: str | None = None,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        search_mode = "empty"
        matches: list[dict[str, Any]] = []
        try:
            query_embedding = await self.embedding_client.embed_query(query)
        except Exception:
            query_embedding = []
        if self.available and len(query_embedding) == self.embedding_dimensions:
            try:
                vector_result = self._search_pgvector(resource_ids, query, query_embedding, limit, max(top_k * 4, top_k), source_type)
                keyword_matches = self._search_keyword_postgres(resource_ids, query, max(top_k * 4, top_k), source_type)
                merged = {item["chunk_id"]: item for item in vector_result.get("matches", [])}
                for item in keyword_matches:
                    if item["chunk_id"] in merged:
                        merged[item["chunk_id"]]["match_type"] = "pgvector_cosine+keyword_candidate"
                    else:
                        merged[item["chunk_id"]] = item
                vector_result["matches"] = list(merged.values())
            except Exception:
                vector_result = {"context": "", "matches": []}
            if vector_result.get("matches"):
                matches = self._rerank_matches(vector_result["matches"], query, top_k)
                threshold = self.settings.retrieval_min_score if min_score is None else min_score
                matches = [item for item in matches if float(item.get("score") or 0) >= threshold]
                for item in matches:
                    item["grounding_confidence"] = round(min(1.0, max(0.0, float(item.get("score") or 0))), 4)
                    item["citation_id"] = f"{item.get('resource_id')}#{item.get('chunk_id')}"
                search_mode = "pgvector_hybrid_rerank"
                result = self._build_search_result(query, matches, limit, search_mode)
                result["latency_ms"] = self._elapsed_ms(started_at)
                self._record_retrieval_log(query, resource_ids, matches, search_mode, result["latency_ms"], {
                    "embedding": True,
                    "postgres": True,
                })
                return result

        chunks = self._load_chunks(resource_ids)
        if source_type:
            chunks = [chunk for chunk in chunks if chunk.source_type == source_type]
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
                "start_seconds": chunk.metadata.get("start_seconds"),
                "end_seconds": chunk.metadata.get("end_seconds"),
                "start_timestamp": chunk.metadata.get("start_timestamp"),
                "end_timestamp": chunk.metadata.get("end_timestamp"),
                "score": round(score, 6),
                "match_type": match_type,
            }
            for score, match_type, chunk in selected
        ]
        matches = self._rerank_matches(matches, query, top_k)
        threshold = self.settings.retrieval_min_score if min_score is None else min_score
        matches = [item for item in matches if float(item.get("score") or 0) >= threshold]
        for item in matches:
            item["grounding_confidence"] = round(min(1.0, max(0.0, float(item.get("score") or 0))), 4)
            item["citation_id"] = f"{item.get('resource_id')}#{item.get('chunk_id')}"
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
        source_type: str | None = None,
    ) -> dict[str, Any]:
        keys = [resource_id for resource_id in resource_ids if ":" in resource_id]
        query_vector = embedding_to_pgvector(query_embedding)
        if not query_vector:
            return {"context": "", "matches": []}
        key_filter = "AND resource_key = ANY(%s)" if keys else ""
        source_filter = "AND source_type = %s" if source_type else ""
        user_id = direct_user_id.get()
        owner_filter = "AND (source_type = 'public' OR metadata->>'owner_user_id' = %s)" if user_id else ""
        params: list[Any] = [query_vector]
        if keys:
            params.append(keys)
        if source_type:
            params.append(source_type)
        if user_id:
            params.append(user_id)
        params.extend([query_vector, top_k])
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT chunk_id, source_type, resource_id, chunk_index, content, metadata,
                           1 - (embedding_vector <=> %s::vector) AS similarity
                    FROM a12_resource_index_chunk
                    WHERE embedding_vector IS NOT NULL
                      {key_filter}
                      {source_filter}
                      {owner_filter}
                      AND COALESCE((metadata->>'available')::boolean, TRUE) IS TRUE
                      AND COALESCE((metadata->>'allow_ai')::boolean, TRUE) IS TRUE
                    ORDER BY embedding_vector <=> %s::vector
                    LIMIT %s
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()
        matches = [
            {
                "resource_id": f"{row[1]}:{row[2]}",
                "chunk_id": row[0],
                "chunk_index": row[3],
                "content": row[4][:1500],
                "metadata": row[5] or {},
                "start_seconds": (row[5] or {}).get("start_seconds"),
                "end_seconds": (row[5] or {}).get("end_seconds"),
                "start_timestamp": (row[5] or {}).get("start_timestamp"),
                "end_timestamp": (row[5] or {}).get("end_timestamp"),
                "score": round(float(row[6] or 0.0), 6),
                "match_type": "pgvector_cosine",
            }
            for row in rows
        ]
        return {"query": query, "matches": matches}

    def _search_keyword_postgres(self, resource_ids: list[str], query: str, top_k: int,
                                 source_type: str | None = None) -> list[dict[str, Any]]:
        keys = [resource_id for resource_id in resource_ids if ":" in resource_id]
        chinese = re.sub(r"\s+", "", query or "")
        terms = re.findall(r"[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,6}", chinese)
        if len(chinese) >= 4:
            terms.extend(chinese[index:index + 2] for index in range(0, min(len(chinese) - 1, 20), 2))
        terms = list(dict.fromkeys(term.lower() for term in terms if term.strip()))[:12]
        if not terms:
            return []
        filters = ["embedding_vector IS NOT NULL", "COALESCE((metadata->>'available')::boolean, TRUE) IS TRUE",
                   "COALESCE((metadata->>'allow_ai')::boolean, TRUE) IS TRUE"]
        params: list[Any] = []
        if keys:
            filters.append("resource_key = ANY(%s)")
            params.append(keys)
        if source_type:
            filters.append("source_type = %s")
            params.append(source_type)
        user_id = direct_user_id.get()
        if user_id:
            filters.append("(source_type = 'public' OR metadata->>'owner_user_id' = %s)")
            params.append(user_id)
        filters.append("(" + " OR ".join("LOWER(content) LIKE %s" for _ in terms) + ")")
        params.extend([f"%{term}%" for term in terms])
        params.append(top_k)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""SELECT chunk_id,source_type,resource_id,chunk_index,content,metadata
                                 FROM a12_resource_index_chunk WHERE {' AND '.join(filters)} LIMIT %s""", tuple(params))
                rows = cur.fetchall()
        return [{"resource_id": f"{row[1]}:{row[2]}", "chunk_id": row[0], "chunk_index": row[3],
                 "content": row[4][:1500], "metadata": row[5] or {}, "score": keyword_score(row[4], query),
                 "match_type": "keyword_candidate", "start_seconds": (row[5] or {}).get("start_seconds"),
                 "end_seconds": (row[5] or {}).get("end_seconds"),
                 "start_timestamp": (row[5] or {}).get("start_timestamp"),
                 "end_timestamp": (row[5] or {}).get("end_timestamp")} for row in rows]

    def overview(self) -> dict[str, Any]:
        user_id = direct_user_id.get()
        scope = "WHERE (source_type = 'public' OR metadata->>'owner_user_id' = %s)" if user_id else ""
        params = (user_id,) if user_id else ()
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*), COALESCE(SUM(chunk_count), 0) FROM a12_resource_index {scope}", params)
                    total_resources, total_chunks = cur.fetchone()
                    cur.execute(
                        """
                        SELECT source_type, parse_status, available, allow_ai, COUNT(*), COALESCE(SUM(chunk_count), 0)
                        FROM a12_resource_index
                        {scope}
                        GROUP BY source_type, parse_status, available, allow_ai
                        ORDER BY source_type, parse_status
                        """.replace("{scope}", scope), params
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
                    log_scope = " WHERE metadata->>'user_id' = %s" if user_id else ""
                    cur.execute(f"SELECT COUNT(*) FROM a12_retrieval_log{log_scope}", params)
                    retrieval_log_count = cur.fetchone()[0]
            ready_for_rag = total_resources > 0 and total_chunks > 0
            return {
                "postgres_available": True,
                "embedding_dimensions": self.embedding_dimensions,
                "resource_count": total_resources,
                "chunk_count": total_chunks,
                "ready_for_rag": ready_for_rag,
                "readiness_message": (
                    "知识库已可用于检索增强生成。"
                    if ready_for_rag
                    else "知识库当前为空，请先上传资料或执行资源索引同步。"
                ),
                "retrieval_log_count": retrieval_log_count,
                "groups": groups,
                "fallback_path": str(FALLBACK_INDEX_PATH),
            }

        data = self._read_fallback()
        resources = [item for item in data.get("resources", {}).values()
                     if self._visible(item.get("source_type", ""), item.get("metadata") or {})]
        chunk_count = sum(len(data.get("chunks", {}).get(item.get("resource_key"), [])) for item in resources)
        ready_for_rag = len(resources) > 0 and chunk_count > 0
        return {
            "postgres_available": False,
            "embedding_dimensions": self.embedding_dimensions,
            "resource_count": len(resources),
            "chunk_count": chunk_count,
            "ready_for_rag": ready_for_rag,
            "readiness_message": (
                "本地降级知识库已可用于检索。"
                if ready_for_rag
                else "PostgreSQL 不可用且本地知识库为空，请检查数据库后同步资源。"
            ),
            "retrieval_log_count": self.list_retrieval_logs(1).get("total", 0),
            "groups": self._fallback_groups(resources),
            "fallback_path": str(FALLBACK_INDEX_PATH),
        }

    def list_resources(
        self,
        source_type: str | None = None,
        available: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        parse_status: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        if self.available:
            filters = []
            params: list[Any] = []
            user_id = direct_user_id.get()
            if user_id:
                filters.append("(source_type = 'public' OR metadata->>'owner_user_id' = %s)")
                params.append(user_id)
            if source_type:
                filters.append("source_type = %s")
                params.append(source_type)
            if available is not None:
                filters.append("available = %s")
                params.append(available)
            if parse_status:
                filters.append("parse_status = %s")
                params.append(parse_status)
            if keyword:
                escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                filters.append("(title ILIKE %s ESCAPE '\\' OR resource_id ILIKE %s ESCAPE '\\')")
                params.extend([f"%{escaped}%", f"%{escaped}%"])
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

        resources = [item for item in self._read_fallback().get("resources", {}).values()
                     if self._visible(item.get("source_type", ""), item.get("metadata") or {})]
        if source_type:
            resources = [item for item in resources if item.get("source_type") == source_type]
        if available is not None:
            resources = [item for item in resources if bool(item.get("available", True)) is available]
        if parse_status:
            resources = [item for item in resources if item.get("parse_status") == parse_status]
        if keyword:
            kw = keyword.lower()
            resources = [
                item for item in resources
                if kw in str(item.get("title", "")).lower() or kw in str(item.get("resource_id", "")).lower()
            ]
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
                    if not self._visible(resource["source_type"], resource["metadata"]):
                        return None
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
        if not self._visible(resource.get("source_type", ""), resource.get("metadata") or {}):
            return None
        result = dict(resource)
        result["chunks"] = data.get("chunks", {}).get(key, [])[:chunk_limit]
        return result

    def list_retrieval_logs(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        if self.available:
            user_id = direct_user_id.get()
            scope = " WHERE metadata->>'user_id' = %s" if user_id else ""
            params = (user_id,) if user_id else ()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM a12_retrieval_log{scope}", params)
                    total = cur.fetchone()[0]
                    cur.execute(
                        """
                        SELECT id, query, resource_ids, match_count, top_score, search_mode, latency_ms, metadata, created_at
                        FROM a12_retrieval_log
                        {scope}
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                        """.replace("{scope}", scope),
                        (*params, limit, offset),
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
        user_id = direct_user_id.get()
        if user_id:
            items = [item for item in items if str((item.get("metadata") or {}).get("user_id")) == user_id]
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
            (
                f"[UNTRUSTED_EVIDENCE citation={item.get('citation_id') or (str(item['resource_id']) + '#' + str(item['chunk_id']))} score={item.get('score', 0)}"
                + (f" time={item.get('start_timestamp')}-{item.get('end_timestamp')}" if item.get("start_timestamp") else "")
                + f"]\n{item['content']}\n[/UNTRUSTED_EVIDENCE]"
            )
            for item in matches
        )[:limit]
        return {
            "query": query,
            "context": context,
            "matches": matches,
            "search_mode": search_mode,
            "citations": [
                {"citation_id": item.get("citation_id"), "resource_id": item.get("resource_id"),
                 "chunk_id": item.get("chunk_id"), "score": item.get("score"),
                 "start_timestamp": item.get("start_timestamp"), "end_timestamp": item.get("end_timestamp")}
                for item in matches
            ],
            "grounding_status": "grounded" if matches else "insufficient_evidence",
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
        if direct_user_id.get():
            log_metadata["user_id"] = direct_user_id.get()
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
            "mysql_table": "adm_resource" if request.source_type == "public" else ("res_material" if request.source_type == "personal" else "local_upload"),
            "uploaded_by": request.uploaded_by,
            "owner_user_id": request.owner_user_id,
            "available": request.available,
            "allow_ai": request.allow_ai,
            # 只存剥离签名参数的稳定地址；带签名的 URL 60 分钟后就失效，存进去会导致后续同步拿到过期地址
            "file_url": (request.file_url or "").split("?", 1)[0],
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
        chunk_metadata: list[dict[str, Any]] | None = None,
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
                                json.dumps(self._metadata_at(chunk_metadata, index, metadata), ensure_ascii=False),
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
                    metadata=self._metadata_at(chunk_metadata, index, metadata),
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
        else:
            data = self._read_fallback()
            previous = data.get("resources", {}).get(key, {})
            data.setdefault("resources", {})[key] = {
                **previous,
                "resource_key": key,
                "source_type": request.source_type,
                "resource_id": request.resource_id,
                "file_url": (request.file_url or "").split("?", 1)[0],
                "file_fingerprint": fingerprint,
                "title": request.title,
                "metadata": metadata,
                "available": request.available,
                "allow_ai": request.allow_ai,
                "parse_status": "failed",
                "error_message": error_message[:2000],
                "text_length": previous.get("text_length", 0),
                "chunk_count": previous.get("chunk_count", 0),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write_fallback(data)

    def _compact_chunk_metadata(self, metadata: dict[str, Any], specific: dict[str, Any]) -> dict[str, Any]:
        """避免把完整视频时间轴复制到每个向量块，同时保留权限和定位字段。"""
        keys = (
            "source", "source_type", "resource_id", "resource_key", "uploaded_by", "owner_user_id",
            "available", "allow_ai", "file_type", "file_size", "title", "description", "subject", "grade",
            "categories", "tags", "access_type",
        )
        compact = {key: metadata.get(key) for key in keys if key in metadata}
        parse_metadata = metadata.get("parse") if isinstance(metadata.get("parse"), dict) else {}
        compact["parse"] = {
            key: value for key, value in parse_metadata.items()
            if key not in {"timeline", "keyframes"}
        }
        compact.update(specific)
        return compact

    @staticmethod
    def _metadata_at(
        chunk_metadata: list[dict[str, Any]] | None,
        index: int,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        if chunk_metadata and index < len(chunk_metadata):
            return chunk_metadata[index]
        return fallback

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
        user_id = direct_user_id.get()
        if self.available:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    key_filter = "AND resource_key = ANY(%s)" if keys else ""
                    owner_filter = "AND (source_type = 'public' OR metadata->>'owner_user_id' = %s)" if user_id else ""
                    params: tuple[Any, ...] = ((keys,) if keys else ()) + ((user_id,) if user_id else ())
                    cur.execute(
                        f"""
                        SELECT chunk_id, source_type, resource_id, chunk_index, content, embedding_vector::text, metadata
                        FROM a12_resource_index_chunk
                        WHERE COALESCE((metadata->>'available')::boolean, TRUE) IS TRUE
                          {key_filter}
                          {owner_filter}
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
            if not self._visible(meta.get("source_type", ""), meta.get("metadata") or {}):
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
        if "text-embedding-v4" in model:
            return 1024
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
