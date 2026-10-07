import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from a12_ppt.lesson_plan.generator import LessonPlanGenerator
from a12_ppt.models import LessonPlanGenerateRequest, OutlineGenerateRequest, PresentationGenerateRequest
from a12_ppt.models import SlideImageGenerateRequest, TeacherStyleTagsRequest
from a12_ppt.presentation.generator import PPTGenerator
from a12_ppt.resources import upload_store
from a12_ppt.teaching_policy import teaching_policy
from a12_ppt.teaching_policy import set_published_policies
from a12_ppt import runtime_config
from a12_ppt.presentation.image_generator import ImageGenerationClient
from a12_ppt.presentation.subject_components import embed_subject_component, normalize_subject_components
from a12_ppt.direct_auth import direct_user_id
from a12_ppt.ai_runtime import use_runtime_options
from a12_ppt.tools import rag as rag_module


class TeachingPhaseTests(unittest.IsolatedAsyncioTestCase):
    def test_boppps_lesson_has_six_phases_and_exact_duration(self):
        generator = LessonPlanGenerator.__new__(LessonPlanGenerator)
        request = LessonPlanGenerateRequest(title="函数", duration_minutes=45, outline={
            "slides": [{"learning_phase": "pre_assessment"}, {"learning_phase": "summary"}]})
        response = generator._normalize_response(request, {"lesson_process": [
            {"stage": "新授", "teacher_activity": "分析函数案例", "student_activity": "绘制函数图像", "ppt_reference": "第99页"}]})
        plan = response["lesson_plan"]
        self.assertEqual(len(plan["lesson_process"]), 6)
        self.assertEqual(sum(row["duration_minutes"] for row in plan["lesson_process"]), 45)
        self.assertEqual(plan["lesson_process"][2]["ppt_reference"], "第 1 页")
        self.assertIn("绘制函数图像", plan["lesson_process"][3]["student_activity"])
        self.assertTrue(all("99" not in row["ppt_reference"] for row in plan["lesson_process"]))

    def test_general_lesson_does_not_force_boppps(self):
        generator = LessonPlanGenerator.__new__(LessonPlanGenerator)
        request = LessonPlanGenerateRequest(title="函数", teaching_model="general")
        result = generator._normalize_response(request, {"lesson_process": [{"stage": "项目实践"}]})
        self.assertEqual(len(result["lesson_plan"]["lesson_process"]), 1)

    def tearDown(self):
        set_published_policies({})

    def test_function_graph_is_sampled_without_executing_expressions(self):
        components = normalize_subject_components([{"type": "function_graph", "data": {
            "coefficients": [0, 0, 1], "x_min": -5, "x_max": 5}}])
        self.assertEqual(components[0]["type"], "chart")
        option = components[0]["data"]["option"]
        self.assertEqual(option["series"][0]["data"][20], 0)
        self.assertEqual(option["series"][0]["data"][0], 25)
        self.assertEqual(normalize_subject_components([{"type": "function_graph", "data": {
            "coefficients": ["__import__('os')"]}}]), [])
        self.assertEqual(normalize_subject_components([{"type": "math_formula", "data": {"latex": {"bad": True}}}]), [])

    def test_edit_metrics_extract_preferences_without_single_instruction(self):
        from a12_ppt.outline_chat.postgres_store import infer_style_signals_from_edit
        self.assertEqual(set(infer_style_signals_from_edit({
            "style_before": {"avg_text_chars": 200, "activity_pages": 1, "case_pages": 0},
            "style_after": {"avg_text_chars": 120, "activity_pages": 2, "case_pages": 1},
        })), {"less_slide_text", "more_practice", "more_cases"})
        self.assertEqual(infer_style_signals_from_edit({"style_before": "bad"}), [])

    def test_profile_refresh_is_daily_and_respects_disabled_profile(self):
        from a12_ppt.outline_chat.postgres_store import PostgresOutlineMemoryStore
        store = PostgresOutlineMemoryStore()
        with patch.object(store, "get_teacher_profile", return_value={"enabled": True, "profile": {}}), \
             patch.object(store, "relearn_teacher_profile", return_value={"updated": True}) as relearn:
            store.refresh_teacher_profile("9")
            store.refresh_teacher_profile("9")
            relearn.assert_called_once_with("9")
        with patch.object(store, "get_teacher_profile", return_value={"enabled": False}), \
             patch.object(store, "relearn_teacher_profile") as relearn:
            store.refresh_teacher_profile("10")
            relearn.assert_not_called()

    async def test_history_material_learning_uses_current_teacher_and_cleans_temp_file(self):
        from io import BytesIO
        from fastapi import UploadFile
        from main import learn_teacher_material
        seen = []
        async def parse(path):
            seen.append(path)
            return SimpleNamespace(text="教学目标和案例练习", metadata={})
        token = direct_user_id.set("9")
        try:
            with patch("a12_ppt.resources.parsers.parse_resource_file", side_effect=parse), \
                 patch("a12_ppt.teacher_style.analyze_material_style", AsyncMock(return_value={"structure": "案例驱动"})), \
                 patch("main.require_active_browser_token", AsyncMock()), \
                 patch("main.postgres_memory_store.save_teacher_material_style", return_value=True) as save:
                result = await learn_teacher_material(UploadFile(filename="history.txt", file=BytesIO("案例教学".encode())))
            self.assertEqual(save.call_args.args[0], "9")
            self.assertEqual(result.data["style"]["structure"], "案例驱动")
            self.assertFalse(seen[0].exists())
        finally:
            direct_user_id.reset(token)

    def test_two_subject_components_are_preserved_and_not_overlaid(self):
        markup = embed_subject_component('<html><body><section></section></body></html>', {
            "subject_components": [{"type": "math_formula", "data": {"latex": "y=x^2"}},
                                   {"type": "chemical_formula", "data": {"formula": "H2O"}}]}, 1)
        self.assertEqual(markup.count('data-a12-generated-subject="1"'), 2)
        self.assertIn("top:230px", markup)
        self.assertIn("top:445px", markup)

    def test_published_subject_policy_overrides_fallback_and_rejects_invalid_data(self):
        set_published_policies({"subject_policy:理科": json.dumps({
            "subjects": ["数学"], "method": "先实验", "activity": "学生测量", "visual": "绘制图表",
        }, ensure_ascii=False), "subject_policy:坏配置": "{}"})
        self.assertEqual(teaching_policy("高中数学")["method"], "先实验")
        self.assertEqual(teaching_policy("高中历史")["category"], "文科")
        set_published_policies({})
        self.assertNotEqual(teaching_policy("高中数学")["method"], "先实验")

    async def test_runtime_config_only_applies_valid_published_values(self):
        response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"code": 0, "data": {
            "teaching_subject": {"subject_policy:工科": json.dumps({
                "subjects": ["编程"], "method": "项目", "activity": "调试", "visual": "流程图",
            }, ensure_ascii=False)}, "image_generation": {"monthly_quota": "7", "model": "wan2.2-t2i-flash"},
        }})
        client = SimpleNamespace(get=AsyncMock(return_value=response))
        class ClientContext:
            async def __aenter__(self): return client
            async def __aexit__(self, *_): return False
        with patch.dict("os.environ", {"A12_PYTHON_INTERNAL_KEY": "test"}), \
             patch.object(runtime_config.httpx, "AsyncClient", return_value=ClientContext()), \
             patch.object(runtime_config, "_next_refresh", 0):
            await runtime_config.refresh_runtime_config()
            self.assertEqual(runtime_config.image_monthly_quota(), 7)
            self.assertEqual(runtime_config.image_generation_model("fallback"), "wan2.2-t2i-flash")
            self.assertEqual(teaching_policy("编程")["method"], "项目")
        runtime_config._image_monthly_quota = None
        runtime_config._image_model = None
        runtime_config._next_refresh = 0

    async def test_image_quota_refunds_on_remote_failure(self):
        image = ImageGenerationClient()
        image.settings = SimpleNamespace(image_generation_api_key="test", image_generation_model="test")
        token = direct_user_id.set("9")
        try:
            with patch.object(image, "_read_cache", return_value=None), \
                 patch.object(image, "_reserve_quota", AsyncMock(return_value="quota-key")), \
                 patch.object(image, "_refund_quota", AsyncMock()) as refund, \
                 patch.object(image, "_request_image", AsyncMock(side_effect=RuntimeError("remote failed"))), \
                 patch("a12_ppt.presentation.image_generator.require_active_browser_token", new_callable=AsyncMock):
                with self.assertRaisesRegex(RuntimeError, "remote failed"):
                    await image.generate("课堂实验")
                refund.assert_awaited_once_with("quota-key")
        finally:
            direct_user_id.reset(token)

    async def test_image_quota_uses_atomic_redis_reservation(self):
        image = ImageGenerationClient()
        redis_client = SimpleNamespace(eval=AsyncMock(return_value=1))
        class RedisContext:
            async def __aenter__(self): return redis_client
            async def __aexit__(self, *_): return False
        token = direct_user_id.set("9")
        try:
            with patch("a12_ppt.presentation.image_generator.image_monthly_quota", return_value=3), \
                 patch("a12_ppt.presentation.image_generator.async_redis.from_url", return_value=RedisContext()):
                key = await image._reserve_quota()
            self.assertTrue(key.endswith(":9"))
            self.assertEqual(redis_client.eval.await_args.args[1], 1)
            self.assertEqual(redis_client.eval.await_args.args[-1], 3)
        finally:
            direct_user_id.reset(token)

    async def test_single_slide_image_api_returns_renderable_asset(self):
        from main import generate_slide_image, generator as app_generator
        generated = SimpleNamespace(data_url="data:image/png;base64,AAAA", model="test-image", prompt="教学配图")
        with patch.object(app_generator.image_generator, "generate", AsyncMock(return_value=generated)) as call:
            result = await generate_slide_image(SlideImageGenerateRequest(
                lesson_title="函数", slide_title="函数图像", subject="数学"))
        self.assertEqual(result.data["model"], "test-image")
        self.assertTrue(result.data["data_url"].startswith("data:image/"))
        self.assertIn("函数图像", call.await_args.args[0])

    async def test_manual_style_tags_are_scoped_to_current_teacher(self):
        from main import update_teacher_style_tags
        token = direct_user_id.set("9")
        try:
            with patch("main.postgres_memory_store.set_teacher_profile_tags", return_value=True) as save:
                result = await update_teacher_style_tags(TeacherStyleTagsRequest(tags=["多案例", "多案例", "重实践"]))
            save.assert_called_once_with("9", ["多案例", "重实践"])
            self.assertEqual(result.data["tags"], ["多案例", "重实践"])
        finally:
            direct_user_id.reset(token)

    def test_subject_policy_distinguishes_disciplines(self):
        self.assertEqual(teaching_policy("高中历史")["category"], "文科")
        self.assertEqual(teaching_policy("初中数学")["category"], "理科")
        self.assertEqual(teaching_policy("信息技术")["category"], "工科")
        self.assertEqual(teaching_policy("初中英语")["category"], "语言")

    def test_subject_component_dsl_survives_outline_and_html_generation(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        raw = {"slides": [{"title": "函数关系", "subject_components": [
            {"type": "math_formula", "data": {"latex": "y=x^2", "display_mode": True}},
        ]}]}
        outline = generator._normalize_outline(raw, "函数")
        component = outline["slides"][0]["subject_components"][0]
        self.assertEqual(component["data"]["latex"], "y=x^2")
        markup = embed_subject_component("<html><body><section></section></body></html>", outline["slides"][0], 1)
        self.assertIn('data-subject-type="math_formula"', markup)
        self.assertIn('data-a12-generated-subject="1"', markup)
        self.assertEqual(embed_subject_component(markup, outline["slides"][0], 1), markup)
        self.assertEqual(normalize_subject_components([{"type": "unsafe", "data": {"latex": "x"}}]), [])

    async def test_fast_profile_skips_expensive_html_repair_roundtrip(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        generator.settings = SimpleNamespace(max_html_retries=2, quality_preset="fast")
        generator.llm = SimpleNamespace(complete=AsyncMock(return_value="<bad>"))
        with use_runtime_options(model_profile="fast"), \
             patch("a12_ppt.presentation.generator.validate_html", return_value={"valid": False, "errors": ["bad"], "warnings": []}):
            result = await generator._complete_html_with_retry("prompt", "system", {}, 1, 3)
        self.assertEqual(result, "")
        self.assertEqual(generator.llm.complete.await_count, 1)

    def test_boppps_quality_guardrails_restore_missing_pretest_and_transfer(self):
        generator = PPTGenerator()
        request = OutlineGenerateRequest(title="函数", subject="数学", grade="初三", slide_count=6)
        outline = {"title": "函数", "slides": [
            {"title": f"第{i}页", "slide_type": "cover" if i == 1 else "summary" if i == 6 else "content",
             "learning_phase": "participatory_learning", "student_task": "完成课堂题目"}
            for i in range(1, 7)
        ]}
        normalized = generator._ensure_outline_quality(outline, request, 6)
        self.assertTrue(normalized["quality_report"]["checks"]["has_pre_assessment"])
        self.assertTrue(normalized["quality_report"]["checks"]["has_retrieval_and_transfer"])

    def test_outline_prompt_uses_teacher_profile_and_chosen_model(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        request = OutlineGenerateRequest(
            title="函数", subject="数学", grade="高一", teaching_model="general",
            teaching_style="heuristic", teacher_profile={"style_summary": "偏好多案例与练习"},
        )
        prompt = generator._outline_prompt(request, 8)
        self.assertIn("多案例与练习", prompt)
        self.assertIn("理科", prompt)
        self.assertIn("不强制套用固定六阶段", prompt)

    def test_presentation_keeps_outline_teaching_choices(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        request = PresentationGenerateRequest(
            title="函数", outline={"subject": "数学", "teaching_model": "general",
                                   "teaching_style": "heuristic", "teacher_style_summary": "多案例"},
        )
        context = generator._request_context(request)
        self.assertEqual(context["teaching_model"], "general")
        self.assertEqual(context["subject_policy"]["category"], "理科")
        self.assertEqual(context["teacher_style_summary"], "多案例")

    async def test_lesson_plan_prompt_uses_outline_model_and_style(self):
        generator = LessonPlanGenerator.__new__(LessonPlanGenerator)
        generator.llm = SimpleNamespace(complete=AsyncMock(return_value='{"title":"函数"}'))
        request = LessonPlanGenerateRequest(
            title="函数", subject="数学", outline={"teaching_model": "boppps",
                                           "teaching_style": "heuristic", "teacher_style_summary": "多练习"},
        )
        await generator._generate_with_model(request)
        prompt = generator.llm.complete.call_args.args[1]
        self.assertIn("BOPPPS", prompt)
        self.assertIn("启发式探究", prompt)
        self.assertIn("多练习", prompt)

    def test_only_expired_temp_directories_are_returned(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(upload_store, "DATA_DIR", Path(directory)):
            old = Path(directory) / "res_aaaaaaaaaaaaaaaa"
            recent = Path(directory) / "res_bbbbbbbbbbbbbbbb"
            old.mkdir()
            recent.mkdir()
            (old / "metadata.json").write_text(json.dumps({"created_at_epoch": time.time() - 72 * 3600}), encoding="utf-8")
            (recent / "metadata.json").write_text(json.dumps({"created_at_epoch": time.time()}), encoding="utf-8")
            self.assertEqual(upload_store.expired_temp_upload_ids(), [old.name])

    async def test_selected_retrieval_source_is_searched_and_ranked_first(self):
        async def fake_search(keys, _query, **_kwargs):
            if keys:
                return {"context": "选定资料", "matches": [{"resource_id": "public:7", "chunk_id": "a", "content": "选定内容"}]}
            return {"context": "公共资料", "matches": [{"resource_id": "public:8", "chunk_id": "b", "content": "其他内容"}]}

        with patch.object(rag_module.resource_index_store, "search_context", side_effect=fake_search), \
             patch.object(rag_module, "build_rag_context", return_value=""):
            result = await rag_module.rag_search(["public:7"], "函数")
        self.assertEqual(result["matches"][0]["resource_id"], "public:7")
        self.assertIn("selected_materials", result["search_scope"])


if __name__ == "__main__":
    unittest.main()
