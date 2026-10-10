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
    async def test_refraction_drafts_have_distinct_relations_and_assessable_skills(self):
        graphs = await build_learning_graphs({"title": "光的折射", "grade": "八年级"}, {}, {},
                                             type("Offline", (), {"available": False})())
        knowledge, skill = graphs["knowledge"], graphs["skill"]
        self.assertFalse({node["label"] for node in knowledge["nodes"]} & {node["label"] for node in skill["nodes"]})
        topology = lambda graph: {(edge["source"][1:], edge["target"][1:]) for edge in graph["edges"]}
        self.assertNotEqual(topology(knowledge), topology(skill))
        self.assertTrue(all(node.get("task") and node.get("assessment") for node in skill["nodes"]))
        self.assertEqual({node["id"] for node in skill["nodes"]}, {link["skill_id"] for link in skill["knowledge_links"]})

    async def test_model_cannot_copy_the_same_nodes_into_both_graphs(self):
        nodes = [{"id": f"n{i}", "label": f"识别概念{i}", "task": "观察实例", "assessment": "判断正确"} for i in range(4)]
        edges = [{"source": f"n{i}", "target": f"n{i+1}", "relation": "先修"} for i in range(3)]
        payload = {"knowledge": {"nodes": nodes, "edges": edges}, "skill": {"nodes": nodes, "edges": edges,
            "knowledge_links": [{"knowledge_id": f"n{i}", "skill_id": f"n{i}"} for i in range(4)]}}
        class Model:
            available = True
            async def complete(self, *_args):
                return json.dumps(payload, ensure_ascii=False)
        graphs = await build_learning_graphs({"title": "光的折射"}, {}, {}, Model())
        self.assertEqual(graphs["status"], "unverified_draft")
        self.assertFalse({n["label"] for n in graphs["knowledge"]["nodes"]} & {n["label"] for n in graphs["skill"]["nodes"]})

    async def test_model_keeps_task_assessment_and_valid_many_to_many_support(self):
        payload = {"knowledge": {"nodes": [{"id": f"k{i}", "label": f"折射概念{i}"} for i in range(4)],
                                  "edges": [{"source": "k0", "target": f"k{i}", "relation": "包含"} for i in range(1, 4)]},
                   "skill": {"nodes": [{"id": f"s{i}", "label": f"解释现象{i}", "task": f"完成情境任务{i}",
                                          "assessment": f"说明依据{i}"} for i in range(4)],
                             "edges": [{"source": f"s{i}", "target": f"s{i+1}", "relation": "能力递进"} for i in range(3)],
                             "knowledge_links": [{"knowledge_id": "k0", "skill_id": f"s{i}"} for i in range(4)]
                                + [{"knowledge_id": "k1", "skill_id": "s3"}, {"knowledge_id": "missing", "skill_id": "s0"}]}}
        class Model:
            available = True
            async def complete(self, *_args):
                return json.dumps(payload, ensure_ascii=False)
        graphs = await build_learning_graphs({"title": "光的折射"}, {}, {}, Model())
        self.assertEqual(graphs["status"], "ai_proposal")
        self.assertEqual(graphs["skill"]["nodes"][3]["assessment"], "说明依据3")
        self.assertEqual(len(graphs["skill"]["knowledge_links"]), 5)

    async def test_approved_course_yields_both_graphs_before_outline(self):
        approved = {"course_id": "java-programming", "version": 3, **EXAMPLE}
        graphs = await build_learning_graphs({"title": "HashMap"}, approved, {}, type("Offline", (), {"available": False})())
        self.assertEqual(graphs["status"], "approved_course")
        self.assertIn("hashmap", {node["id"] for node in graphs["knowledge"]["nodes"]})
        self.assertIn("use_hashmap", {node["id"] for node in graphs["skill"]["nodes"]})

    async def test_no_course_still_yields_two_drafts(self):
        graphs = await build_learning_graphs({"title": "分数", "knowledge_points": ["分数意义", "同分母加法"]},
                                             {}, {}, type("Offline", (), {"available": False})())
        self.assertEqual(graphs["status"], "unverified_draft")
        self.assertGreaterEqual(len(graphs["knowledge"]["nodes"]), 4)
        self.assertGreaterEqual(len(graphs["skill"]["nodes"]), 4)
        self.assertTrue(graphs["knowledge"]["edges"])
        self.assertTrue(graphs["skill"]["edges"])

    async def test_model_graph_is_bounded_and_dangling_edges_removed(self):
        class Model:
            available = True

            async def complete(self, *_args):
                return json.dumps({"knowledge": {"nodes": [{"id": "k1", "label": "分数"}],
                                                  "edges": [{"source": "k1", "target": "missing", "relation": "先修"}]},
                                   "skill": {"nodes": [{"id": "s1", "label": "比较分数大小"}], "edges": []}}, ensure_ascii=False)

        graphs = await build_learning_graphs({"title": "分数"}, {}, {}, Model())
        self.assertEqual(graphs["status"], "unverified_draft")
        self.assertGreaterEqual(len(graphs["knowledge"]["nodes"]), 4)
        self.assertGreaterEqual(len(graphs["skill"]["nodes"]), 4)

    async def test_sparse_approved_graph_is_enriched_as_draft(self):
        sparse = {"course_id": "optics", "version": 2,
                  "nodes": [{"id": "refraction", "kind": "concept", "label": "光的折射"},
                            {"id": "observe", "kind": "skill", "label": "观察折射现象"}],
                  "edges": []}
        graphs = await build_learning_graphs({"title": "光的折射", "grade": "八年级"}, sparse, {},
                                             type("Offline", (), {"available": False})())
        self.assertEqual(graphs["status"], "unverified_draft")
        self.assertIn("光的折射", {node["label"] for node in graphs["knowledge"]["nodes"]})
        self.assertGreaterEqual(len(graphs["knowledge"]["nodes"]), 4)
        self.assertGreaterEqual(len(graphs["skill"]["nodes"]), 4)

    async def test_long_duplicate_course_labels_do_not_hide_fallback_knowledge_nodes(self):
        course = {"nodes": [{"id": f"concept-{index}", "kind": "concept",
                             "label": "很长的共同前缀" * 10 + str(index)} for index in range(12)]}
        graphs = await build_learning_graphs({"title": "光的折射"}, course, {},
                                             type("Offline", (), {"available": False})())
        self.assertGreaterEqual(len(graphs["knowledge"]["nodes"]), 4)
        self.assertGreaterEqual(len(graphs["skill"]["nodes"]), 4)
        self.assertIn("折射现象与介质界面", {node["label"] for node in graphs["knowledge"]["nodes"]})

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
