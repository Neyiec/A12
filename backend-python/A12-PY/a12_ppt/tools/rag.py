import re

from ..resources import build_rag_context, resource_index_store


def rag_search(resource_ids: list[str], query: str, limit: int = 12000) -> dict:
    indexed_result = resource_index_store.search_context(resource_ids, query, limit=limit)
    indexed_context = indexed_result.get("context", "")
    local_ids = [resource_id for resource_id in resource_ids if ":" not in resource_id]
    local_context = build_rag_context(local_ids, limit=limit)
    context = "\n\n".join(part for part in [indexed_context, local_context] if part)[:limit]
    if not context:
        return {"query": query, "resource_ids": resource_ids, "context": "", "matches": []}

    keywords = [word.lower() for word in re.findall(r"[\w\u4e00-\u9fff]+", query or "") if len(word) > 1]
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", context) if part.strip()]
    scored: list[tuple[int, str]] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        score = sum(1 for keyword in keywords if keyword in lower)
        if score:
            scored.append((score, paragraph))
    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [text[:1500] for _, text in scored[:5]] or [context[:3000]]
    structured_matches = indexed_result.get("matches", [])
    return {
        "query": query,
        "resource_ids": resource_ids,
        "context": "\n\n".join(matches)[:limit],
        "matches": structured_matches or matches,
    }
