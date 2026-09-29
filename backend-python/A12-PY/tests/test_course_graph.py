import json
import unittest
from pathlib import Path
from unittest.mock import patch

from a12_ppt.course_graph import CourseGraphStore, validate_graph
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow
from a12_ppt.outline_chat.learning_graphs import build_learning_graphs
from a12_ppt.outline_chat.postgres_store import extract_style_signals


EXAMPLE = json.loads((Path(__file__).parents[1] / "examples" / "java_programming_course_graph.json").read_text(encoding="utf-8"))


class CourseGraphTests(unittest.TestCase):
    def test_style_signal_extraction_is_bounded(self):
        self.assertEqual(extract_style_signals("多案例，减少理论，PPT 每页字少"),
                         ["more_cases", "less_theory", "less_slide_text"])
        self.assertEqual(extract_style_signals("这次讲 HashMap"), [])

    def test_example_has_concept_skill_and_prerequisite_links(self):
        graph = validate_graph(EXAMPLE)
        self.assertTrue(any(n["kind"] == "concept" for n in graph["nodes"]))
        self.assertTrue(any(n["kind"] == "skill" for n in graph["nodes"]))
        self.assertTrue(any(e["relation"] == "prerequisite" for e in graph["edges"]))

    def test_rejects_unapproved_relation_or_dangling_node(self):
        broken = {"nodes": EXAMPLE["nodes"], "edges": [{"source": "hashmap", "target": "missing", "relation": "causes"}]}
        with self.assertRaises(ValueError):
            validate_graph(broken)

    def test_retrieval_includes_prerequisite(self):
        store = CourseGraphStore()
        with patch.object(store, "get", return_value={"course_id": "java-programming", "version": 3, **EXAMPLE}), \
             patch.object(store, "_connect") as connect:
            connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = []
            result = store.retrieve("teacher-1", "java-programming", "讲 HashMap")
        self.assertIn("hashmap", {node["id"] for node in result["nodes"]})
        self.assertIn("collections", {node["id"] for node in result["nodes"]})
        self.assertIn("use_hashmap", {node["id"] for node in result["nodes"]})
        self.assertEqual(result["version"], 3)


class GraphWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_approved_course_yields_both_graphs_before_outline(self):
        store = CourseGraphStore()
        with patch.object(store, "get", return_value={"course_id": "java-programming", "version": 3, **EXAMPLE}), \
             patch.object(store, "_connect") as connect:
            connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = []
            retrieved = store.retrieve("teacher-1", "java-programming", "HashMap")
        graphs = await build_learning_graphs({"title": "HashMap"}, retrieved, {}, type("Offline", (), {"available": False})())
        self.assertEqual(graphs["status"], "approved_course")
        self.assertIn("hashmap", {node["id"] for node in graphs["knowledge"]["nodes"]})
        self.assertIn("use_hashmap", {node["id"] for node in graphs["skill"]["nodes"]})

    async def test_no_course_still_yields_two_drafts(self):
        graphs = await build_learning_graphs({"title": "分数", "knowledge_points": ["分数意义", "同分母加法"]},
                                             {}, {}, type("Offline", (), {"available": False})())
        self.assertEqual(graphs["status"], "unverified_draft")
        self.assertEqual(len(graphs["knowledge"]["nodes"]), 2)
        self.assertEqual(len(graphs["skill"]["nodes"]), 2)

    async def test_model_graph_is_bounded_and_dangling_edges_removed(self):
        class Model:
            available = True

            async def complete(self, *_args):
                return json.dumps({"knowledge": {"nodes": [{"id": "k1", "label": "分数"}],
                                                  "edges": [{"source": "k1", "target": "missing", "relation": "先修"}]},
                                   "skill": {"nodes": [{"id": "s1", "label": "比较分数大小"}], "edges": []}}, ensure_ascii=False)

        graphs = await build_learning_graphs({"title": "分数"}, {}, {}, Model())
        self.assertEqual(graphs["status"], "ai_proposal")
        self.assertEqual(graphs["knowledge"]["edges"], [])

    async def test_outline_graph_node_attaches_both_graphs_to_saved_outline(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.llm = type("Offline", (), {"available": False})()
        state = {"intent": {"title": "分数", "knowledge_points": ["分数意义"]},
                 "course_graph": {}, "tool_context": {}, "tool_trace": []}
        update = await workflow._generate_learning_graphs_node(state)
        response = {"outline": {"slides": []}}
        workflow._attach_tool_outputs(response, {**state, **update})
        self.assertEqual(response["outline"]["learning_graphs"], update["learning_graphs"])

    async def test_strategy_node_uses_graph_and_preserves_rag(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        with patch("a12_ppt.outline_chat.workflow.course_graph_store") as store:
            store.retrieve.return_value = {"version": 2, "nodes": [{"id": "hashmap"}], "edges": []}
            store.choose_strategy.return_value = {"name": "graph", "reason": "test"}
            update = await workflow._select_strategy_node({"user_id": "t1", "session_id": "s1",
                "intent": {"course_id": "java-programming", "title": "HashMap", "enable_rag": True}})
        self.assertEqual(update["strategy"]["name"], "graph_rag")
        self.assertEqual(update["course_graph"]["version"], 2)

    async def test_graph_failure_degrades_to_existing_path(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        with patch("a12_ppt.outline_chat.workflow.course_graph_store") as store:
            store.match_course.side_effect = OSError("db down")
            update = await workflow._select_strategy_node({"user_id": "t1", "session_id": "s1",
                "intent": {"title": "HashMap", "enable_rag": True}})
        self.assertEqual(update["strategy"]["name"], "rag")
