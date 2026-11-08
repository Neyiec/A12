import asyncio
from unittest.mock import AsyncMock

from a12_ppt.models import OutlineChatStreamRequest
from a12_ppt.outline_chat import workflow as module
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow


def test_planning_parses_and_clarifies_with_uploaded_evidence_even_when_rag_disabled(monkeypatch):
    flow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
    flow._extract_intent_with_model = AsyncMock(return_value={'title':'环境搭建','subject':'计算机','grade':'大学'})
    flow._model_clarification = AsyncMock(return_value=None)
    monkeypatch.setattr(module.outline_session_store,'append_message',lambda *args,**kwargs: None)
    monkeypatch.setattr(module,'read_reference_material',AsyncMock(return_value='安装Java17和Maven3.9'))
    state = {'user_id':'1','session_id':'s1','request':OutlineChatStreamRequest(
        user_id='1',message='根据资料备课',resource_ids=['res_pdf'],enable_rag=False)}
    result = asyncio.run(flow._parse_input_node(state))
    assert result['intent']['enable_rag'] is False
    assert 'Maven3.9' in result['tool_context']['references']['context']
    intent_conversation = flow._extract_intent_with_model.await_args.args[0]
    clarify_conversation = flow._model_clarification.await_args.args[1]
    assert 'Java17' in intent_conversation[-1].content
    assert 'Java17' in clarify_conversation[-1].content
    # 参考资料作为本轮上下文，不假装成教师历史消息。
    assert len(result['messages']) == 1


def test_reference_context_survives_tool_node_without_retrieval_repetition():
    from a12_ppt.outline_chat.tool_node import OutlineToolNode
    flow = OutlineToolNode()
    flow._autonomous_plans = AsyncMock(return_value=[])
    flow.mcp_client = type('MCP',(),{'enabled':False})()
    flow._rule_plans = lambda *args: []
    evidence = {'references':{'context':'上传教材中的Java17'}}
    result = asyncio.run(flow({'intent':{'title':'环境'},'tool_context':evidence}))
    assert result['tool_context'] == evidence


def test_outline_request_retains_evidence_and_resources():
    flow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
    state = {'intent':{'title':'环境搭建','subject':'计算机','grade':'大学',
        'resource_ids':['res_pdf'],'enable_rag':True},
        'tool_context':{'references':{'context':'安装Java17和Maven3.9'}},
        'request':OutlineChatStreamRequest(user_id='1',message='生成大纲')}
    request = flow._outline_request_from_state(state)
    assert 'Maven3.9' in request.reference_text
    assert request.resource_ids == ['res_pdf']


def test_direct_outline_uses_selected_personal_material_without_rag_switch(monkeypatch):
    from a12_ppt.models import OutlineGenerateRequest
    from a12_ppt.presentation import PPTGenerator
    from a12_ppt.tools import rag
    monkeypatch.setattr(rag,'load_personal_material',AsyncMock(return_value=('环境.pdf','安装Maven3.9')))
    flow = PPTGenerator.__new__(PPTGenerator)
    req = OutlineGenerateRequest(title='环境搭建',subject='计算机',grade='大学',resource_ids=['12'],enable_rag=False)
    enriched = asyncio.run(flow._with_reference_and_rag_context(req))
    assert 'Maven3.9' in enriched.reference_text


def test_confirmed_outline_refreshes_newly_added_material(monkeypatch):
    flow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
    monkeypatch.setattr(module,'read_reference_material',AsyncMock(return_value='补充案例ABC'))
    state = {'intent':{'title':'环境','resource_ids':['res_old','res_new']},
        'request':OutlineChatStreamRequest(user_id='1',message='确认双图谱'),
        'tool_context':{'references':{'resource_ids':['res_old'],'context':'旧教材'}}}
    result = asyncio.run(flow._build_prompt_node(state))
    assert '补充案例ABC' in result['final_prompt']
    assert result['tool_context']['references']['resource_ids'] == ['res_old','res_new']


def test_confirmation_drops_public_evidence_when_switch_is_off(monkeypatch):
    flow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
    search = AsyncMock()
    monkeypatch.setattr(module, 'search_public_context', search)
    result = asyncio.run(flow._build_prompt_node({
        'intent': {'title': '环境', 'enable_rag': False},
        'request': OutlineChatStreamRequest(user_id='1', message='确认双图谱'),
        'tool_context': {'rag': {'context': '公共参考证据', 'search_scope': 'public'}},
    }))
    assert '公共参考证据' not in result['final_prompt']
    assert 'rag' not in result['tool_context']
    search.assert_not_awaited()


def test_presentation_uses_public_library_only_when_requested(monkeypatch):
    from types import SimpleNamespace
    from a12_ppt.models import PresentationGenerateRequest
    from a12_ppt.presentation import PPTGenerator
    from a12_ppt.tools import rag

    search = AsyncMock(return_value={'context': '公共课标证据'})
    monkeypatch.setattr(rag.resource_index_store, 'search_context', search)
    generator = PPTGenerator.__new__(PPTGenerator)
    generator.llm = SimpleNamespace(available=True)
    request = PresentationGenerateRequest(title='函数', outline={'generation_options': {'enable_rag': True}})
    assert asyncio.run(generator._collect_generation_rag_context(request)) == ''
    search.assert_not_awaited()
    enabled = request.model_copy(update={'enable_rag': True})
    assert '公共课标证据' in asyncio.run(generator._collect_generation_rag_context(enabled))
    search.assert_awaited_once_with([], '函数', limit=6000, source_type='public')
