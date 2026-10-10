import copy
from unittest.mock import Mock, patch
from unittest.mock import AsyncMock
import json
import asyncio

import pytest

from a12_ppt.outline_chat.session_store import OutlineSessionStore
from a12_ppt.outline_chat.learning_graphs import propose_graph_edit


def graph_snapshot():
    return {
        "knowledge": {"nodes": [{"id": f"k{i}", "label": f"知识{i}"} for i in range(4)], "edges": []},
        "skill": {"nodes": [{"id": f"s{i}", "label": f"分析案例{i}", "task": "观察并解释现象", "assessment": "准确说明原因"} for i in range(4)],
                  "edges": [{"source": "s0", "target": "s1", "relation": "递进"}],
                  "knowledge_links": [{"knowledge_id": f"k{i}", "skill_id": f"s{i}"} for i in range(4)]},
    }


@pytest.fixture
def store():
    database = Mock(available=False)
    database.get_session.return_value = None
    with patch("a12_ppt.outline_chat.session_store.postgres_memory_store", database):
        value = OutlineSessionStore()
        value.save("teacher", "session", {"outline": {"pending_graph_review": {
            "learning_graphs": graph_snapshot(), "intent": {"title": "光的折射"}, "resource_ids": ["resource1"],
        }}}, status="awaiting_graph_confirmation")
        yield value


def test_edits_persist_with_audit_without_changing_knowledge_or_pending_context(store):
    skill = graph_snapshot()["skill"]
    skill["nodes"][0]["label"] = "绘制折射光路"
    result = store.update_skill_graph("teacher", "session", skill)
    saved = store.get("teacher", "session")
    pending = saved["outline"]["pending_graph_review"]
    assert pending["learning_graphs"] == result
    assert result["knowledge"] == graph_snapshot()["knowledge"]
    assert pending["resource_ids"] == ["resource1"]
    assert saved["status"] == "awaiting_graph_confirmation"
    audit = saved["messages"][-1]["metadata"]
    assert audit["before"]["nodes"][0]["label"] == "分析案例0"
    assert audit["after"]["nodes"][0]["label"] == "绘制折射光路"
    skill["nodes"][0]["label"] = "后续本地修改"
    assert store.get("teacher", "session")["outline"]["pending_graph_review"]["learning_graphs"] == result


@pytest.mark.parametrize("error", ["too_few", "empty_task", "broken_edge", "missing_support", "cloned_label"])
def test_invalid_edits_do_not_overwrite_saved_snapshot(store, error):
    before = store.get("teacher", "session")
    skill = copy.deepcopy(graph_snapshot()["skill"])
    if error == "too_few": skill["nodes"].pop()
    if error == "empty_task": skill["nodes"][0]["task"] = " "
    if error == "broken_edge": skill["edges"][0]["target"] = "missing"
    if error == "missing_support": skill["knowledge_links"].pop()
    if error == "cloned_label": skill["nodes"][0]["label"] = "知识0"
    with pytest.raises(ValueError):
        store.update_skill_graph("teacher", "session", skill)
    assert store.get("teacher", "session") == before


def test_other_users_and_completed_sessions_cannot_edit(store):
    with pytest.raises(LookupError):
        store.update_skill_graph("someone_else", "session", graph_snapshot()["skill"])
    state = store.get("teacher", "session")
    store.save("teacher", "session", state, status="completed")
    with pytest.raises(ValueError):
        store.update_skill_graph("teacher", "session", graph_snapshot()["skill"])


def complete_graphs():
    graphs = graph_snapshot()
    graphs["knowledge"]["edges"] = [{"source": "k0", "target": "k1", "relation": "先修"}]
    return graphs


def test_both_graphs_are_saved_atomically_with_audit(store):
    graphs = complete_graphs()
    graphs["knowledge"]["nodes"][0]["label"] = "折射规律"
    graphs["skill"]["nodes"][0]["assessment"] = "正确画出折射光路"
    result = store.update_learning_graphs("teacher", "session", graphs)
    state = store.graph_review("teacher", "session")
    assert state["outline"]["pending_graph_review"]["learning_graphs"] == result
    assert state["messages"][-1]["metadata"]["type"] == "learning_graph_edit"
    assert result["knowledge"]["nodes"][0]["label"] == "折射规律"
    assert result["skill"]["nodes"][0]["assessment"] == "正确画出折射光路"


def test_deleting_knowledge_requires_repairing_skill_support(store):
    graphs = complete_graphs()
    graphs["knowledge"]["nodes"][0]["id"] = "new-knowledge"
    before = store.get("teacher", "session")
    with pytest.raises(ValueError):
        store.update_learning_graphs("teacher", "session", graphs)
    assert store.get("teacher", "session") == before


@pytest.mark.parametrize("kind", ["knowledge", "skill"])
def test_ai_preview_changes_target_only_and_does_not_mutate_original(kind):
    original = complete_graphs()
    before = copy.deepcopy(original)
    proposed = copy.deepcopy(original)
    proposed[kind]["nodes"][0]["label"] = "新知识" if kind == "knowledge" else "绘制新光路"
    other = "skill" if kind == "knowledge" else "knowledge"
    proposed[other]["nodes"][0]["label"] = "不应采纳的无关修改"
    llm = Mock(available=True, complete=AsyncMock(return_value=json.dumps(proposed, ensure_ascii=False)))
    result = asyncio.run(propose_graph_edit(original, {"title": "折射"}, "细化节点", kind, llm))
    assert result[kind]["nodes"][0]["label"] == proposed[kind]["nodes"][0]["label"]
    assert result[other]["nodes"][0]["label"] == original[other]["nodes"][0]["label"]
    assert original == before


def test_ai_invalid_response_is_rejected_without_overwriting_graphs():
    original = complete_graphs()
    before = copy.deepcopy(original)
    llm = Mock(available=True, complete=AsyncMock(return_value='{"knowledge":{"nodes":[]}}'))
    with pytest.raises(ValueError, match="未通过校验"):
        asyncio.run(propose_graph_edit(original, {}, "细化概念", "knowledge", llm))
    assert original == before
