import asyncio
from contextlib import nullcontext
from unittest.mock import AsyncMock

import pytest
from a12_ppt import workspace
from a12_ppt.resources import upload_store
from a12_ppt.tools import rag
from a12_ppt.workspace import WorkspaceChatRequest, reference_context


def request(**kwargs):
    return WorkspaceChatRequest(user_id='1', messages=[{'role':'user','content':'这个环境怎么搭建'}], **kwargs)


def test_uploaded_text_does_not_trigger_public_search(monkeypatch):
    monkeypatch.setattr(upload_store, 'load_resource_text', lambda _: '安装Java17，配置JAVA_HOME')
    search = AsyncMock()
    monkeypatch.setattr(rag.resource_index_store, 'search_context', search)
    context = asyncio.run(reference_context(request(resource_ids=['uploaded-pdf'])))
    assert 'JAVA_HOME' in context
    search.assert_not_awaited()


def test_public_search_is_opt_in_and_public_only_even_without_attachments(monkeypatch):
    search = AsyncMock(return_value={'context': '公共资源证据'})
    monkeypatch.setattr(rag.resource_index_store, 'search_context', search)
    assert asyncio.run(reference_context(request())) == ''
    assert '公共资源证据' in asyncio.run(reference_context(request(enable_rag=True)))
    search.assert_awaited_once_with([], '这个环境怎么搭建', limit=12000, source_type='public')


def test_empty_document_does_not_silently_use_public_results(monkeypatch):
    monkeypatch.setattr(upload_store, 'load_resource_text', lambda _: '')
    search = AsyncMock(return_value={'context': '公共库内容'})
    monkeypatch.setattr(rag.resource_index_store, 'search_context', search)
    with pytest.raises(ValueError, match='重新上传'):
        asyncio.run(reference_context(request(resource_ids=['empty-pdf'], enable_rag=True)))
    search.assert_not_awaited()


def test_personal_material_is_read_directly_and_compressed_without_hiding_public_evidence(monkeypatch):
    personal = AsyncMock(return_value=('环境.pdf', 'Java17' + 'A' * 20000 + '结束命令'))
    search = AsyncMock(return_value={'context': '公共库内容'})
    monkeypatch.setattr(rag, 'load_personal_material', personal)
    monkeypatch.setattr(rag.resource_index_store, 'search_context', search)
    context = asyncio.run(reference_context(request(resource_ids=['12'], enable_rag=True)))
    personal.assert_awaited_once_with('12')
    search.assert_awaited_once_with([], '这个环境怎么搭建', limit=4000, source_type='public')
    assert len(context) <= 12000
    for evidence in ('环境.pdf', 'Java17', '已压缩', '结束命令', '公共库内容'):
        assert evidence in context


def test_chat_sends_reference_to_model_without_teacher_design_preferences(monkeypatch):
    from a12_ppt import ai_runtime
    monkeypatch.setattr(ai_runtime,'use_runtime_options',lambda *args: nullcontext())
    monkeypatch.setattr(upload_store, 'load_resource_text', lambda _: '环境需要Java17和Maven3.9')
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
