import copy
import unittest
from unittest.mock import patch

from a12_ppt.models import OutlineChatStreamRequest
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow


class _FakeGraph:
    def __init__(self, updates):
        self.updates = updates
        self.calls = 0

    async def astream(self, _state, stream_mode):
        self.calls += 1
        for name, update in self.updates:
            yield "updates", {name: update}


class _FakeSessionStore:
    def __init__(self):
        self.saved = {"messages": [], "intent": {}, "outline": {}, "status": "active"}
        self.history = []

    def load_or_create(self, _user_id, _session_id):
        return "session-1", copy.deepcopy(self.saved)

    def save(self, _user_id, _session_id, state, status="active"):
        self.saved = {**copy.deepcopy(state), "status": status}
        self.history.append(status)

    def append_message(self, _user_id, _session_id, role, content, metadata=None):
        self.saved.setdefault("messages", []).append({"role": role, "content": content, "metadata": metadata or {}})


class GraphConfirmationFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_graph_is_not_exposed_for_confirmation(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.graph = _FakeGraph([("generate_learning_graphs", {
            "learning_graphs": {"knowledge": {"nodes": []},
                                "skill": {"nodes": [{"id": str(i)} for i in range(6)]}},
        })])
        store = _FakeSessionStore()
        with patch("a12_ppt.outline_chat.workflow.outline_session_store", store):
            request = OutlineChatStreamRequest(user_id="teacher-1", session_id="session-1", message="光的折射")
            events = [event async for event in workflow.stream(request)]
        self.assertEqual(events[-1]["data"]["status"], "failed")
        self.assertNotIn("learning_graphs", [event["event"] for event in events])
        self.assertNotIn("awaiting_graph_confirmation", store.history)

    async def test_graph_generation_pauses_until_teacher_confirms(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        graphs = {kind: {"nodes": [{"id": f"{kind}-{i}"} for i in range(4)], "edges": []}
                  for kind in ("knowledge", "skill")}
        workflow.graph = _FakeGraph([("generate_learning_graphs", {
            "learning_graphs": graphs, "intent": {"title": "光的折射", "grade": "八年级"},
            "strategy": {"name": "direct"}, "tool_context": {}, "tool_trace": [],
        })])
        workflow.confirmed_graph = _FakeGraph([("build_prompt", {"final_prompt": "教师确认后的提示词"}),
                                                ("generate_outline", {"error": "mocked outline attempt"})])
        store = _FakeSessionStore()
        with patch("a12_ppt.outline_chat.workflow.outline_session_store", store):
            request = OutlineChatStreamRequest(user_id="teacher-1", session_id="session-1", message="备一节光的折射")
            before = [event async for event in workflow.stream(request)]
            self.assertEqual(before[-1]["data"]["status"], "awaiting_graph_confirmation")
            self.assertEqual(workflow.confirmed_graph.calls, 0)
            self.assertNotIn("final", [event["event"] for event in before])
            self.assertEqual(store.saved["outline"]["pending_graph_review"]["learning_graphs"], graphs)

            confirm = request.model_copy(update={"message": "确认双图谱", "confirm_learning_graphs": True})
            after = [event async for event in workflow.stream(confirm)]
            self.assertEqual(workflow.confirmed_graph.calls, 1)
            self.assertIn("build_prompt", [event["data"].get("name") for event in after if event["event"] == "stage"])
            self.assertEqual(after[-1]["data"]["status"], "failed")
            # A generation failure leaves the confirmed graphs available for retry.
            self.assertEqual(store.saved["status"], "awaiting_graph_confirmation")

    async def test_confirmation_without_pending_graph_is_rejected(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.confirmed_graph = _FakeGraph([])
        store = _FakeSessionStore()
        with patch("a12_ppt.outline_chat.workflow.outline_session_store", store):
            request = OutlineChatStreamRequest(user_id="teacher-1", session_id="session-1",
                                               message="确认", confirm_learning_graphs=True)
            events = [event async for event in workflow.stream(request)]
        self.assertEqual([event["event"] for event in events], ["error", "done"])
        self.assertEqual(workflow.confirmed_graph.calls, 0)

    async def test_confirmed_graph_produces_outline_and_completes_session(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        graphs = {kind: {"nodes": [{"id": f"{kind}-{i}"} for i in range(4)], "edges": []}
                  for kind in ("knowledge", "skill")}
        response = {"title": "光的折射", "slide_count": 1, "slides": [{"slide_no": 1, "title": "导入"}],
                    "outline": {"title": "光的折射"}, "learning_graphs": graphs}
        workflow.confirmed_graph = _FakeGraph([
            ("build_prompt", {"final_prompt": "已确认图谱"}),
            ("generate_outline", {"response": response, "outline": response["outline"]}),
            ("reflect", {"response": response, "outline": response["outline"], "reflection": {"status": "passed"}}),
            ("memory", {"memory_result": {"stored": False}}),
        ])
        store = _FakeSessionStore()
        store.saved = {"messages": [], "intent": {"title": "光的折射"},
                       "outline": {"pending_graph_review": {"learning_graphs": graphs,
                           "intent": {"title": "光的折射"}, "tool_context": {}, "tool_trace": [],
                           "resource_ids": [], "enable_rag": False, "enable_web": False}},
                       "status": "awaiting_graph_confirmation"}
        with patch("a12_ppt.outline_chat.workflow.outline_session_store", store), \
             patch("a12_ppt.outline_chat.workflow.postgres_memory_store.save_generation"):
            request = OutlineChatStreamRequest(user_id="teacher-1", session_id="session-1",
                                               message="确认", confirm_learning_graphs=True)
            events = [event async for event in workflow.stream(request)]
        self.assertEqual(events[-2]["event"], "final")
        self.assertEqual(events[-1]["data"]["status"], "completed")
        self.assertEqual(store.saved["status"], "completed")
