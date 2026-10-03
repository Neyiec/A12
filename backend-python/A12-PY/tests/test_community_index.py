import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx

from a12_ppt.resources.index_store import ResourceIndexStore
from a12_ppt.resources.index_worker import process_event


def test_community_text_is_embedded_with_traceable_source():
    store = object.__new__(ResourceIndexStore)
    store._load_resource_meta = Mock(return_value=None)
    store._replace_index = Mock()
    store.embedding_client = SimpleNamespace(embed_documents=AsyncMock(return_value=[[0.1, 0.2]]))
    payload = {"resource_id": "42", "title": "函数课件", "file_url": "community://42/2",
               "metadata": {"subject": "数学", "version": 2}}
    with patch("a12_ppt.resources.index_store.chunk_records",
               return_value=[{"content": "第 1 页：函数", "metadata": {}}]):
        result = asyncio.run(store.sync_community_text(payload, "第 1 页：函数"))
    assert result["status"] == "indexed"
    request, metadata, *_ = store._replace_index.call_args.args
    assert request.source_type == "community"
    assert metadata["content_version"] == 2
    assert metadata["resource_key"] == "community:42"


def test_unlicensed_community_content_is_removed_not_indexed():
    async def respond(request):
        return httpx.Response(200, json={"code": 200, "data": {"allow_ai": False}})

    real_client = httpx.AsyncClient
    with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-key"}), \
         patch("a12_ppt.resources.index_worker.httpx.AsyncClient",
               side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(respond))), \
         patch("a12_ppt.resources.index_worker.resource_index_store") as store:
        asyncio.run(process_event({"source_type": "community", "resource_id": "42", "action": "sync"}))
    store.delete_resource.assert_called_once_with("community", "42")
    store.sync_community_text.assert_not_called()


def test_public_community_slide_text_is_indexed():
    async def respond(request):
        return httpx.Response(200, json={"code": 200, "data": {
            "resource_id": "42", "title": "函数课件", "allow_ai": True,
            "metadata": {"version": 2},
            "content_data": json.dumps({"slides": [{"html": "<h1>函数</h1><script>bad()</script>",
                                                    "notes": "观察图像"}]})}})

    real_client = httpx.AsyncClient
    with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-key"}), \
         patch("a12_ppt.resources.index_worker.httpx.AsyncClient",
               side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(respond))), \
         patch("a12_ppt.resources.index_worker.resource_index_store") as store:
        store.sync_community_text = AsyncMock()
        asyncio.run(process_event({"source_type": "community", "resource_id": "42", "action": "sync"}))
    text = store.sync_community_text.await_args.args[1]
    assert "函数" in text and "观察图像" in text
    assert "bad()" not in text
