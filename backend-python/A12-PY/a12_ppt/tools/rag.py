import re

from ..resources import build_rag_context, resource_index_store
from ..resources.similarity import keyword_score


async def rag_search(resource_ids: list[str], query: str, limit: int = 12000) -> dict:
    # Uploaded references enrich the retrieval query; they are not the retrieval scope.
    local_ids = [resource_id for resource_id in resource_ids if ":" not in resource_id]
    indexed_ids = [resource_id for resource_id in resource_ids
                   if resource_id.startswith(("public:", "personal:", "community:"))]
    local_context = build_rag_context(local_ids, limit=limit)
    enriched_query = _build_enriched_query(query, local_context)
    indexed_result = await resource_index_store.search_context(indexed_ids, enriched_query, limit=limit)
    indexed_context = indexed_result.get("context", "")

    reference_matches = _rank_local_context(local_context, query)
    structured_matches = list(indexed_result.get("matches", []))

    context_parts = []
    if local_context:
        context_parts.append("[Uploaded reference material]\n" + local_context[:4000])
    if indexed_context:
        context_parts.append("[RAG knowledge base matches]\n" + indexed_context)
    context = "\n\n".join(part for part in context_parts if part)[:limit]
    return {
        "query": query,
        "enriched_query": enriched_query,
        "resource_ids": resource_ids,
        "search_scope": "selected_knowledge_sources" if indexed_ids else "global_knowledge_base",
        "reference_context": local_context[:4000],
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
