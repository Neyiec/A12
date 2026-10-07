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
    scoped_keys = [resource_id for resource_id in resource_ids if resource_id.startswith(("public:", "personal:", "community:", "temp:"))]
    local_context = build_rag_context(local_ids, limit=limit)
    enriched_query = _build_enriched_query(query, local_context)

    # 全局知识库与 temp 分区两次检索相互独立，并行以抵消双倍 embedding/检索延迟
    tasks = {"global": resource_index_store.search_context([], enriched_query, limit=limit)}
    if temp_keys:
        tasks["temp"] = resource_index_store.search_context(temp_keys, enriched_query, limit=limit)
    if scoped_keys:
        tasks["selected"] = resource_index_store.search_context(scoped_keys, enriched_query, limit=limit)
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    found = {}
    for name, result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.warning("资料检索失败 scope=%s query=%s: %s", name, query[:100], result)
            result = {"context": "", "matches": []}
        found[name] = result
    indexed_result = found["global"]
    temp_result = found.get("temp", {"context": "", "matches": []})
    selected_result = found.get("selected", {"context": "", "matches": []})
    indexed_context = indexed_result.get("context", "")
    temp_context = temp_result.get("context", "")
    selected_context = selected_result.get("context", "")

    reference_matches = _rank_local_context(local_context, query)
    structured_matches = []
    seen = set()
    for item in [*(selected_result.get("matches", [])), *(temp_result.get("matches", [])), *(indexed_result.get("matches", []))]:
        key = (item.get("resource_id"), item.get("chunk_id"))
        if key not in seen:
            seen.add(key)
            structured_matches.append(item)

    context_parts = []
    if local_context:
        context_parts.append("[Uploaded reference material]\n" + local_context[:4000])
    if selected_context:
        context_parts.append("[Teacher-selected material hits]\n" + selected_context)
    if temp_context:
        context_parts.append("[Temporary upload material hits]\n" + temp_context)
    if indexed_context:
        context_parts.append("[RAG knowledge base matches]\n" + indexed_context)
    context = "\n\n".join(part for part in context_parts if part)[:limit]
    search_scopes = ["global_knowledge_base"]
    if temp_keys:
        search_scopes.append("temp_uploads")
    if scoped_keys:
        search_scopes.append("selected_materials")
    return {
        "query": query,
        "enriched_query": enriched_query,
        "resource_ids": resource_ids,
        "search_scope": "+".join(search_scopes),
        "reference_context": local_context[:4000],
        "temp_context": temp_context,
        "selected_context": selected_context,
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
