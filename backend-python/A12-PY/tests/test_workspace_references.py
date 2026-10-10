import asyncio
import json
from contextlib import nullcontext
from unittest.mock import AsyncMock

import pytest
from a12_ppt import workspace
from a12_ppt.workspace import WorkspaceChatRequest, reference_context


def request(**kwargs):
    return WorkspaceChatRequest(user_id='1', messages=[{'role':'user','content':'这个环境怎么搭建'}], **kwargs)


def test_uploaded_text_survives_vector_index_failure(monkeypatch):
    search = AsyncMock(return_value={'reference_context':'安装Java17，配置JAVA_HOME','knowledge_context':'无关公共资料'})
    monkeypatch.setattr(workspace,'rag_search',search)
    context = asyncio.run(reference_context(request(resource_ids=['uploaded-pdf'])))
    assert 'JAVA_HOME' in context and '公共资料' not in context
    search.assert_awaited_once_with(['uploaded-pdf'],'这个环境怎么搭建')


def test_empty_document_does_not_silently_use_global_results(monkeypatch):
    monkeypatch.setattr(workspace,'rag_search',AsyncMock(return_value={'context':'公共库内容','knowledge_context':'公共库内容'}))
    with pytest.raises(ValueError,match='重新上传'):
        asyncio.run(reference_context(request(resource_ids=['empty-pdf'])))


def test_personal_resource_id_uses_personal_partition(monkeypatch):
    search = AsyncMock(return_value={'selected_context':'环境文档'})
    monkeypatch.setattr(workspace,'rag_search',search)
    asyncio.run(reference_context(request(resource_ids=['12'])))
    search.assert_awaited_once_with(['personal:12'],'这个环境怎么搭建')


def test_chat_sends_reference_to_model_without_teacher_design_preferences(monkeypatch):
    from a12_ppt import ai_runtime
    monkeypatch.setattr(ai_runtime,'use_runtime_options',lambda *args: nullcontext())
    monkeypatch.setattr(workspace,'rag_search',AsyncMock(return_value={'reference_context':'环境需要Java17和Maven3.9'}))
    monkeypatch.setattr(workspace.postgres_memory_store,'refresh_teacher_profile',lambda *args: pytest.fail('普通聊天不应加载教学画像'))
    captured = {}
    class Client:
        available = True
        async def complete_stream(self, system, transcript, temperature):
            captured.update(system=system,transcript=transcript)
            yield '请先安装Java17'
    monkeypatch.setattr(workspace,'LLMClient',Client)
    async def collect():
        return [event async for event in workspace.stream_workspace_chat(request(resource_ids=['pdf']))]
    events = asyncio.run(collect())
    assert 'Maven3.9' in captured['transcript']
    assert '不自动转成' in captured['system']
    assert '[DONE]' in events[-1]
