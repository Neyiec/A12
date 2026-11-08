import asyncio
import logging
import re

from ..resources import build_rag_context, resource_index_store
from ..resources.similarity import keyword_score

logger = logging.getLogger("a12_ppt.tools.rag")


async def search_public_context(query: str, limit: int = 12000) -> dict:
    if query.strip():
        try:
            result = await resource_index_store.search_context([], query, limit=limit, source_type="public")
            if result.get("context"):
                result = {**result, "context": "[公共资源库参考证据]\n" + result["context"]}
            return {**result, "search_scope": "public", "query": query}
        except Exception:
            logger.warning("公共资源库检索失败，继续处理当前请求", exc_info=True)
    return {"context": "", "matches": [], "search_scope": "public", "query": query}


async def load_personal_material(resource_id: str) -> tuple[str, str]:
    from fastapi import HTTPException
    from ..direct_auth import personal_resource_download

    try:
        url, metadata = await personal_resource_download(resource_id)
        return await parse_personal_material(resource_id, url, metadata)
    except HTTPException as exc:
        raise ValueError(str(exc.detail)) from exc
    except Exception as exc:
        logger.warning("个人资料读取或解析失败 resource_id=%s error_type=%s", resource_id, type(exc).__name__)
        raise ValueError("所选个人资料解析失败，请检查文件或重新上传") from exc


async def parse_personal_material(resource_id: str, url: str, metadata: dict) -> tuple[str, str]:
    from ..models import ResourceIndexSyncRequest
    from ..resources.downloader import download_and_parse_resource

    title = str(metadata.get("file_name") or f"个人资料 {resource_id}")
    parsed = await download_and_parse_resource(ResourceIndexSyncRequest(
        source_type="personal", resource_id=resource_id, title=title, file_url=url,
        file_type=metadata.get("file_type"), metadata={"original_filename": title},
    ))
    return title, parsed.text


async def read_reference_material(resource_ids: list[str], limit: int = 12000) -> str:
    """读取教师明确选择的资料，按长度截取解析文本，无需向量索引。"""
    from ..resources.upload_store import load_resource_text

    ids = list(dict.fromkeys(
        f"personal:{item}" if item.isdecimal() else item for item in resource_ids
    ))
    if not ids:
        return ""
    parts = []
    per_file = max(1, limit // len(ids))
    for key in ids:
        if key.startswith("personal:"):
            title, content = await load_personal_material(key.removeprefix("personal:"))
        else:
            title = key.removeprefix("temp:")
            content = await asyncio.to_thread(load_resource_text, title)
        content = content.strip()
        if not content:
            raise ValueError("所选资料未读取到可用文本，请重新上传；扫描版 PDF 请确认 OCR 解析成功")
        header = f"[教师引用资料 · {title}]\n"
        budget = max(1, per_file - len(header) - 2)
        if len(content) > budget:
            marker = "\n…（已压缩）…\n"
            available = max(0, budget - len(marker))
            head = available * 2 // 3
            tail = available - head
            content = content[:head] + marker + (content[-tail:] if tail else "")
        parts.append(header + content)
    return "\n\n".join(parts)[:limit]


async def conversation_material_context(resource_ids: list[str], query: str, *,
                                        enable_rag: bool, limit: int = 12000) -> dict:
    public_limit = limit // 3 if resource_ids else limit
    reference_limit = limit - public_limit - 2 if resource_ids and enable_rag else limit
    references = await read_reference_material(resource_ids, reference_limit)
    public = await search_public_context(query, public_limit) if enable_rag else {}
    return {
        "context": "\n\n".join(part for part in (references, public.get("context")) if part)[:limit],
        "matches": public.get("matches", []),
    }


async def rag_search(resource_ids: list[str], query: str, limit: int = 12000) -> dict:
    resource_ids = [f'personal:{item}' if item.isdecimal() else item for item in resource_ids]
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
        context_parts.append("[Uploaded reference material]\n" + local_context[:limit])
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
        "reference_context": local_context[:limit],
        "temp_context": temp_context,
        "selected_context": selected_context,
        "knowledge_context": indexed_context,
        "context": context,
        "matches": structured_matches,
        "reference_matches": reference_matches,
    }


def selected_material_context(result: dict) -> str:
    """只把教师选择的资料算作上传证据，公共库命中不能替代上传失败。"""
    parts = [result.get(key) or '' for key in ('reference_context', 'selected_context', 'temp_context')]
    context = '\n\n'.join(part for part in parts if part.strip())[:12000]
    if not context.strip():
        raise ValueError('所选资料未读取到可用文本，请重新上传；扫描版 PDF 请确认 OCR 解析成功')
    return context


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
