import json
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

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


def ai_proposal():
    concepts = ["介质与光速", "入射角与折射角", "折射方向", "光路可逆性"]
    skills = ["标注法线与角度", "绘制折射光路", "判断偏折方向", "解释水中物体的视深"]
    return {"knowledge": {"nodes": [{"id": f"k{i}", "label": label, "description": f"说明{label}的含义和适用条件"} for i, label in enumerate(concepts)],
                          "edges": [{"source": "k0", "target": "k1", "relation": "先修"},
                                    {"source": "k1", "target": "k2", "relation": "分析"},
                                    {"source": "k2", "target": "k3", "relation": "关联"}]},
            "skill": {"nodes": [{"id": f"s{i}", "label": label, "task": f"根据实验光路图{label}",
                                 "assessment": "标注与方向正确，并说明所用依据"} for i, label in enumerate(skills)],
                      "edges": [{"source": "s0", "target": "s1", "relation": "能力递进"},
                                {"source": "s0", "target": "s2", "relation": "能力递进"},
                                {"source": "s2", "target": "s3", "relation": "迁移"}],
                      "knowledge_links": [{"knowledge_id": f"k{i}", "skill_id": f"s{i}"} for i in range(4)]}}


class GraphWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_model_never_invents_local_topic_graph(self):
        from a12_ppt.outline_chat.learning_graphs import LearningGraphGenerationError
        for title in ("光的折射", "分数", "盐类水解"):
            with self.assertRaisesRegex(LearningGraphGenerationError, "AI模型"):
                await build_learning_graphs({"title": title}, {}, {}, type("Offline", (), {"available": False})())

    async def test_model_result_preserves_independent_topology_and_assessment(self):
        model = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(ai_proposal()))})()
        graphs = await build_learning_graphs({"title": "光的折射", "grade": "八年级"}, {}, {}, model)
        self.assertEqual(graphs["status"], "ai_proposal")
        self.assertEqual(graphs["knowledge"]["source"], "ai_proposal")
        self.assertEqual(graphs["skill"]["nodes"][3]["label"], "解释水中物体的视深")
        self.assertTrue(graphs["skill"]["nodes"][3]["assessment"])
        self.assertEqual(graphs["generation"]["attempts"], 1)
        topology = lambda graph: {(edge["source"][1:], edge["target"][1:]) for edge in graph["edges"]}
        self.assertNotEqual(topology(graphs["knowledge"]), topology(graphs["skill"]))

    async def test_identical_graphs_trigger_model_repair_instead_of_fixed_replacement(self):
        broken = ai_proposal()
        for i in range(4):
            broken["skill"]["nodes"][i]["label"] = broken["knowledge"]["nodes"][i]["label"]
        model = type("Model", (), {"available": True, "complete": AsyncMock(side_effect=[
            json.dumps(broken), json.dumps(ai_proposal())])})()
        graphs = await build_learning_graphs({"title": "光的折射"}, {}, {}, model)
        self.assertEqual(model.complete.await_count, 2)
        self.assertEqual(graphs["generation"]["attempts"], 2)
        self.assertIn("correction", json.loads(model.complete.call_args.args[1]))

    async def test_approved_course_is_reference_and_does_not_bypass_model(self):
        approved = {"course_id": "java-programming", "version": 3, **EXAMPLE}
        model = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(ai_proposal()))})()
        result = await build_learning_graphs({"title": "光的折射"}, approved, {}, model)
        model.complete.assert_awaited_once()
        context = json.loads(model.complete.call_args.args[1])
        self.assertEqual(context["course_evidence"]["version"], 3)
        self.assertTrue(context["course_evidence"]["edges"])
        self.assertEqual(result["status"], "ai_proposal")

    async def test_original_input_grade_and_uploaded_reference_reach_model(self):
        model = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(ai_proposal()))})()
        await build_learning_graphs({"title": "光的折射", "grade": "八年级", "requirements": "重实验"},
            {}, {"teacher_request": "备课光的折射，学生刚学完反射", "teacher_conversation": ["只做空气到水的实验"],
                 "rag": {"context": "教师教材摘录：比较入射角与折射角"}}, model)
        prompt = json.loads(model.complete.call_args.args[1])
        self.assertEqual(prompt["course_requirements"]["grade"], "八年级")
        self.assertIn("反射", prompt["teacher_request"])
        self.assertIn("教材摘录", prompt["reference_excerpt"])
        self.assertIn("空气到水", prompt["recent_conversation"][0])

    async def test_invalid_or_generic_graph_never_becomes_a_template_draft(self):
        from a12_ppt.outline_chat.learning_graphs import LearningGraphGenerationError
        for bad in ({}, ai_proposal()):
            if bad:
                bad["knowledge"]["nodes"][0]["label"] = "光的折射的基本概念"
            model = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(bad))})()
            with self.assertRaises(LearningGraphGenerationError):
                await build_learning_graphs({"title": "光的折射"}, {}, {}, model)
            self.assertEqual(model.complete.await_count, 2)

    async def test_timeout_retry_is_bounded_and_explicit(self):
        from a12_ppt.outline_chat.learning_graphs import LearningGraphGenerationError
        model = type("Model", (), {"available": True, "complete": AsyncMock(side_effect=TimeoutError())})()
        with self.assertRaisesRegex(LearningGraphGenerationError, "模型请求超时"):
            await build_learning_graphs({"title": "光的折射"}, {}, {}, model)
        self.assertEqual(model.complete.await_count, 2)

    async def test_graph_node_reports_failure_without_awaiting_teacher_confirmation(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.llm = type("Offline", (), {"available": False})()
        update = await workflow._generate_learning_graphs_node({"intent": {"title": "分数"}})
        self.assertEqual(update["learning_graphs"], {})
        self.assertIn("AI模型", update["error"])

    async def test_outline_node_keeps_real_ai_graphs(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.llm = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(ai_proposal()))})()
        state = {"intent": {"title": "光的折射"}, "course_graph": {}, "tool_context": {}, "tool_trace": []}
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
