import json
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from a12_ppt.course_graph import validate_graph, GraphVersionConflict
from a12_ppt.learning_path import plan_learning_path, prune_graph, estimated_tokens
from a12_ppt.course_router import PathRequest, validated_path
from a12_ppt.course_draft import outline_from_path, extract_course_draft
from a12_ppt.video_router import LearningVideoRequest


def course():
    return {"course_id": "math", "title": "函数", "version": 3,
        **validate_graph({"nodes": [
            {"id": "basic", "label": "基础运算", "kind": "concept"},
            {"id": "linear", "label": "一次函数", "kind": "concept"},
            {"id": "quadratic", "label": "二次函数", "kind": "concept"},
            {"id": "skill", "label": "解释函数图像", "kind": "skill", "mastery_standard": "用图像说明变化趋势"},
            {"id": "other", "label": "三角函数", "kind": "concept"}], "edges": [
            {"source": "basic", "target": "linear", "relation": "prerequisite"},
            {"source": "linear", "target": "quadratic", "relation": "prerequisite"},
            {"source": "quadratic", "target": "skill", "relation": "supports"}]})}


class LearningPathTests(unittest.TestCase):
    def test_path_includes_all_transitive_prerequisites_and_skills(self):
        result = plan_learning_path(course(), ["quadratic"])
        self.assertEqual([node["id"] for node in result["nodes"]], ["basic", "linear", "quadratic"])
        self.assertEqual(result["skills"][0]["id"], "skill")

    def test_mastered_nodes_are_skipped_but_targets_remain(self):
        result = plan_learning_path(course(), ["quadratic"], mastered=["basic", "quadratic"])
        self.assertEqual([node["id"] for node in result["nodes"]], ["linear", "quadratic"])

    def test_invalid_start_and_broken_order_are_rejected(self):
        with self.assertRaises(ValueError):
            plan_learning_path(course(), ["quadratic"], "other")
        with self.assertRaises(ValueError):
            validated_path(course(), PathRequest(target_ids=["quadratic"], ordered_ids=["quadratic", "linear", "basic"]))
        with self.assertRaises(ValueError):
            validated_path(course(), PathRequest(target_ids=["quadratic"], ordered_ids=["quadratic"]))

    def test_cycles_duplicates_and_nan_are_rejected(self):
        for edge in [{"source": "quadratic", "target": "basic", "relation": "prerequisite"},
                     {"source": "basic", "target": "linear", "relation": "prerequisite"}]:
            graph = course(); graph["edges"].append(edge)
            with self.assertRaises(ValueError): validate_graph(graph)
        graph = course(); graph["nodes"][0]["difficulty"] = float("nan")
        with self.assertRaises(ValueError): validate_graph(graph)

    def test_hops_are_fixed_and_not_dependent_on_edge_order(self):
        graph = course()
        first = prune_graph(graph, ["quadratic"], hops=1)
        graph["edges"].reverse()
        second = prune_graph(graph, ["quadratic"], hops=1)
        self.assertEqual({n["id"] for n in first["nodes"]}, {"quadratic", "linear", "skill"})
        self.assertEqual({n["id"] for n in first["nodes"]}, {n["id"] for n in second["nodes"]})

    def test_budget_preserves_seeds_and_reports_estimates(self):
        graph = course()
        budget = estimated_tokens({"nodes": [graph["nodes"][2]], "edges": []})
        result = prune_graph(graph, ["quadratic"], hops=2, token_budget=budget)
        self.assertEqual([n["id"] for n in result["nodes"]], ["quadratic"])
        self.assertLessEqual(result["pruning_metrics"]["estimated_tokens_after"], budget)
        self.assertEqual(result["pruning_metrics"]["seed_coverage"], 1)
        with self.assertRaises(ValueError): prune_graph(graph, ["quadratic"], token_budget=1)

    def test_path_outline_covers_every_node_in_order(self):
        path = plan_learning_path(course(), ["quadratic"])
        outline = outline_from_path(course(), path, "数学", "初三")
        self.assertEqual([slide["graph_node_ids"][0] for slide in outline["slides"][1:-1]], ["basic", "linear", "quadratic"])
        self.assertEqual(outline["slides"][-2]["graph_skill_ids"], ["skill"])
        self.assertEqual(outline["course_version"], 3)


class LearningApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from main import app
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.auth = patch("main.authenticate_browser", AsyncMock(return_value=("7", "token", "teacher")))
        self.redis = patch("main.verify_active_token", AsyncMock())
        self.auth.start(); self.redis.start()

    async def asyncTearDown(self):
        self.auth.stop(); self.redis.stop(); await self.client.aclose()

    async def test_graph_list_is_scoped_to_authenticated_teacher(self):
        with patch("a12_ppt.course_router.course_graph_store.list_courses", return_value=[]) as fetch:
            response = await self.client.get("/api/v1/python/courses", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200); fetch.assert_called_once_with("7")

    async def test_path_api_and_conflict_response(self):
        with patch("a12_ppt.course_router.course_graph_store.get", return_value=course()):
            response = await self.client.post("/api/v1/python/courses/math/learning-path", json={"target_ids": ["quadratic"]}, headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["nodes"]), 3)
        with patch("main.course_graph_store.put", side_effect=GraphVersionConflict("已更新")):
            graph = course()
            response = await self.client.put("/api/v1/python/courses/graph", json={"user_id": "7", "course_id": "math", "title": "函数", "nodes": graph["nodes"], "edges": graph["edges"], "expected_version": 3}, headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 409)

    async def test_other_teacher_video_is_not_downloadable(self):
        with patch("a12_ppt.video_router.video_job_store.get", return_value=None) as fetch:
            response = await self.client.get("/api/v1/python/learning-videos/any/download", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 404); fetch.assert_called_once_with("7", "any")

    async def test_video_retry_has_bounded_attempts(self):
        with patch("a12_ppt.video_router.video_job_store.retry", return_value=False):
            response = await self.client.post("/api/v1/python/learning-videos/any/retry", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 409)

    async def test_candidate_graph_is_not_silently_saved(self):
        candidate = course()
        candidate['nodes'].extend([
            {'id': 'skill_basic', 'label': '计算函数值', 'kind': 'skill', 'task': '代入自变量计算函数值', 'assessment': '计算正确'},
            {'id': 'skill_transfer', 'label': '建立函数模型', 'kind': 'skill', 'task': '根据情境建立函数模型', 'assessment': '表达式符合情境'},
        ])
        candidate['edges'].extend([
            {'source': 'skill_basic', 'target': 'skill', 'relation': 'prerequisite'},
            {'source': 'skill', 'target': 'skill_transfer', 'relation': 'prerequisite'},
        ])
        model = type("Model", (), {"available": True, "complete": AsyncMock(return_value=json.dumps(candidate))})()
        with patch("a12_ppt.course_draft.rag_search", AsyncMock(return_value={"context": "资料"})), \
             patch("a12_ppt.course_router.course_graph_store.put") as save:
            result = await extract_course_draft({"title": "函数", "resource_ids": ["temp:x"]}, model)
        self.assertTrue(result["requires_teacher_confirmation"]); save.assert_not_called()

    async def test_video_submission_quota_and_no_token_in_payload(self):
        with patch("a12_ppt.video_router.video_job_store.create", return_value={"job_id": "123"}) as create:
            response = await self.client.post("/api/v1/python/learning-videos", json={"title": "函数", "slides": [{"html": "<html>函数</html>", "narration": "讲解函数"}]}, headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create.call_args.args[0], "7")
        self.assertNotIn("token", create.call_args.args[1])

    async def test_full_path_video_accepts_cover_and_summary_and_rejects_over_limit(self):
        nodes = [{"id": f"k{i}", "label": str(i), "kind": "concept"} for i in range(24)]
        graph = {"course_id": "full", "version": 1, "title": "完整课程", "nodes": nodes,
                 "edges": [{"source": f"k{i}", "target": f"k{i+1}", "relation": "prerequisite"} for i in range(23)]}
        outline = outline_from_path(graph, plan_learning_path(graph, ["k23"]), "", "")
        self.assertEqual(len(outline["slides"]), 26)
        payload = {"title": "完整课程", "slides": [{"html": "<div>内容</div>", "narration": slide["title"]} for slide in outline["slides"]]}
        with patch("a12_ppt.video_router.video_job_store.create", return_value={"job_id": "123"}) as create:
            response = await self.client.post("/api/v1/python/learning-videos", json=payload, headers={"Authorization": "Bearer token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(create.call_args.args[1]["slides"]), 26)
            payload["slides"].append(payload["slides"][0])
            response = await self.client.post("/api/v1/python/learning-videos", json=payload, headers={"Authorization": "Bearer token"})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(create.call_count, 1)
