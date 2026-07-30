import re

from ..resources import build_rag_context, resource_index_store
from ..resources.similarity import keyword_score


async def rag_search(resource_ids: list[str], query: str, limit: int = 12000) -> dict:
    indexed_result = await resource_index_store.search_context(resource_ids, query, limit=limit)
    indexed_context = indexed_result.get("context", "")
    local_ids = [resource_id for resource_id in resource_ids if ":" not in resource_id]
    local_context = build_rag_context(local_ids, limit=limit)

    local_matches = _rank_local_context(local_context, query)
    structured_matches = list(indexed_result.get("matches", []))
    structured_matches.extend(local_matches)

    context_parts = [indexed_context]
    context_parts.extend(match["content"] for match in local_matches)
    context = "\n\n".join(part for part in context_parts if part)[:limit]
    return {
        "query": query,
        "resource_ids": resource_ids,
        "context": context,
        "matches": structured_matches,
    }


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
