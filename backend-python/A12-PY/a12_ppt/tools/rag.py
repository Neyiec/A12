import asyncio
import logging
import re

from ..resources import build_rag_context, resource_index_store
from ..resources.similarity import keyword_score

logger = logging.getLogger("a12_ppt.tools.rag")


async def rag_search(resource_ids: list[str], query: str, limit: int = 12000) -> dict:
    # Uploaded references enrich the retrieval query; they are additionally vector-searched
    # inside the temp partition (temp:{res_id}, written at /resources/upload). The global
    # knowledge base search scope stays unchanged.
    local_ids = [resource_id for resource_id in resource_ids if ":" not in resource_id]
    temp_keys = [f"temp:{resource_id}" for resource_id in local_ids]
    local_context = build_rag_context(local_ids, limit=limit)
    enriched_query = _build_enriched_query(query, local_context)

    # 全局知识库与 temp 分区两次检索相互独立，并行以抵消双倍 embedding/检索延迟
    global_task = resource_index_store.search_context([], enriched_query, limit=limit)
    temp_task = (
        resource_index_store.search_context(temp_keys, enriched_query, limit=limit)
        if temp_keys else None
    )
    if temp_task is not None:
        indexed_result, temp_result = await asyncio.gather(global_task, temp_task, return_exceptions=True)
    else:
        indexed_result = await global_task
        temp_result = None
    if isinstance(indexed_result, Exception):
        logger.warning("全局知识库检索失败 query=%s: %s", query[:100], indexed_result)
        indexed_result = {"context": "", "matches": []}
    if isinstance(temp_result, Exception):
        logger.warning("temp 分区检索失败 temp_keys=%s: %s", temp_keys, temp_result)
        temp_result = {"context": "", "matches": []}
    temp_result = temp_result or {"context": "", "matches": []}
    indexed_context = indexed_result.get("context", "")
    temp_context = temp_result.get("context", "")

    reference_matches = _rank_local_context(local_context, query)
    structured_matches = list(temp_result.get("matches", [])) + list(indexed_result.get("matches", []))

    context_parts = []
    if local_context:
        context_parts.append("[Uploaded reference material]\n" + local_context[:4000])
    if temp_context:
        context_parts.append("[Temporary upload material hits]\n" + temp_context)
    if indexed_context:
        context_parts.append("[RAG knowledge base matches]\n" + indexed_context)
    context = "\n\n".join(part for part in context_parts if part)[:limit]
    return {
        "query": query,
        "enriched_query": enriched_query,
        "resource_ids": resource_ids,
        "search_scope": "global_knowledge_base+temp_uploads" if temp_keys else "global_knowledge_base",
        "reference_context": local_context[:4000],
        "temp_context": temp_context,
        "knowledge_context": indexed_context,
        "context": context,
        "matches": structured_matches,
        "reference_matches": reference_matches,
    }


def _build_enriched_query(query: str, reference_context: str, max_reference_chars: int = 4000) -> str:
    parts = [query.strip()]
    if reference_context.strip():
        parts.append("Uploaded reference material for query enrichment:\n" + reference_context.strip()[:max_reference_chars])
    return "\n\n".join(part for part in parts if part)


def _rank_local_context(context: str, query: str, top_k: int = 5) -> list[dict]:
    if not context:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", context) if part.strip()]
    scored: list[tuple[float, str]] = []
    for paragraph in paragraphs:
        score = keyword_score(paragraph, query)
        if score > 0 or not query:
            scored.append((score, paragraph))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "resource_id": "local_upload",
            "chunk_id": f"local:{index}",
            "content": text[:1500],
            "metadata": {"source": "local_upload"},
            "score": round(score, 6),
            "match_type": "local_keyword",
        }
        for index, (score, text) in enumerate(scored[:top_k] or [(0.0, context[:3000])])
    ]
