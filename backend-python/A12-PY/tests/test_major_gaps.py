import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from a12_ppt.models import OutlineGenerateRequest, PresentationExportRequest, PresentationGenerateRequest, ResourceIndexSyncRequest
from a12_ppt.presentation.generator import PPTGenerator
from a12_ppt.presentation.image_generator import GeneratedImage
from a12_ppt.presentation.html_utils import validate_html
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow
from a12_ppt.resources.index_store import ResourceIndexStore
from a12_ppt.resources.downloader import download_and_parse_resource
from a12_ppt.resources.parsers.common import ParsedResource
from a12_ppt.resources.parsers.audio_parser import parse_audio
from a12_ppt.resources.parsers.document_parser import _render_pdf_pages
from a12_ppt.resources.parsers.video_parser import _transcribe_video_audio
from a12_ppt.workspace import WorkspaceChatRequest, stream_workspace_chat


class _FakeResponse:
    content = b"same-resource-content"

    def raise_for_status(self):
        return None


class _FakeHttpClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _url):
        return _FakeResponse()


class _FakeLlm:
    available = True

    async def complete_stream(self, _system, _prompt, _temperature):
        yield "课堂"
        yield "建议"


class MajorGapTests(unittest.IsolatedAsyncioTestCase):
    def test_presentation_asset_policy_defaults_to_auto(self):
        request = PresentationGenerateRequest(title="光合作用", outline={})
        self.assertEqual(request.asset_policy, "auto")

    def test_auto_asset_policy_understands_user_intent_and_subject(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        no_image = PresentationGenerateRequest(
            title="函数证明", outline={"requirements": "请使用纯文字，不要配图"}
        )
        biology = PresentationGenerateRequest(
            title="观察植物细胞",
            outline={"subject": "生物", "slides": [{"visual_suggestion": "展示实验场景和显微镜照片"}]},
        )
        self.assertEqual(generator._resolve_asset_policy(no_image, [])[0], "none")
        self.assertEqual(generator._resolve_asset_policy(biology, biology.outline["slides"])[0], "generate")

    def test_generated_image_is_embedded_as_independent_ppt_element(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        image = GeneratedImage(
            source_url="https://example.com/temporary.png",
            data_url="data:image/png;base64,aGVsbG8=",
            prompt="教学图片",
            model="wan2.2-t2i-flash",
            cache_key="asset123",
        )
        markup = "<!DOCTYPE html><html><head><style>body{overflow:hidden}.slide{width:1280px;height:720px}</style></head><body><section class='slide'></section></body></html>"
        result = generator._embed_generated_image(markup, image)
        self.assertIn('data-ppt-element="image"', result)
        self.assertIn("data:image/png;base64,aGVsbG8=", result)

    async def test_generate_policy_materializes_image_and_reports_metadata(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        generator.settings = SimpleNamespace(
            max_slide_concurrency=2, max_generated_images=1,
            enable_quality_pipeline=False, quality_preset="fast", max_html_retries=1,
        )
        generator.llm = SimpleNamespace(available=False)
        generated = GeneratedImage(
            source_url="https://example.com/temporary.png",
            data_url="data:image/png;base64,aGVsbG8=",
            prompt="植物细胞教学配图",
            model="wan2.2-t2i-flash",
            cache_key="asset123",
        )
        generator.image_generator = SimpleNamespace(available=True, generate=AsyncMock(return_value=generated))
        generator._build_quality_assets = AsyncMock(return_value={})
        request = PresentationGenerateRequest(
            title="观察植物细胞",
            asset_policy="generate",
            outline={"subject": "生物", "slides": [{
                "title": "观察植物细胞", "slide_type": "cover",
                "content_points": ["显微镜观察"], "visual_suggestion": "实验场景照片",
            }]},
        )
        with patch("a12_ppt.presentation.generator.get_template", return_value={
            "_selected_theme": "素白风", "template_name": "素白风", "html_template": "",
        }):
            events = [item async for item in generator.stream_presentation(request)]

        final = events[-1]["response"]
        self.assertEqual(final["metadata"]["generated_image_count"], 1)
        self.assertEqual(final["slides"][0]["metadata"]["asset_status"], "generated")
        self.assertIn('data-ppt-element="image"', final["slides"][0]["html"])

    def test_pptx_export_defaults_to_editable_elements(self):
        request = PresentationExportRequest(title="可编辑课件", slides=[])
        self.assertEqual(request.fidelity, "dom_editable")

    async def test_presentation_stream_emits_completed_html_pages_before_final(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        generator.settings = SimpleNamespace(
            max_slide_concurrency=2, enable_quality_pipeline=False,
            quality_preset="fast", max_html_retries=1,
        )
        generator.llm = SimpleNamespace(available=False)
        generator._normalize_slides_for_deck = lambda value: value
        generator._extract_slides = lambda _outline: [
            {"title": "第一页", "content_points": ["A"]},
            {"title": "第二页", "content_points": ["B"]},
        ]
        generator._normalize_interactive_assets = lambda _value: []
        generator._request_context = lambda _req: {}
        generator._build_quality_assets = AsyncMock(return_value={})
        generator._generate_slide_html = AsyncMock(side_effect=[
            "<!DOCTYPE html><html><head></head><body>1</body></html>",
            "<!DOCTYPE html><html><head></head><body>2</body></html>",
        ])
        generator._speaker_notes = lambda _slide: ""
        generator._combine_deck = lambda _title, slides: f"deck:{len(slides)}"
        request = SimpleNamespace(
            outline={}, title="流式课件", theme="商务", aspect_ratio="16:9",
        )
        with patch("a12_ppt.presentation.generator.get_template", return_value={
            "_selected_theme": "商务", "template_name": "商务", "html_template": "",
        }):
            events = [item async for item in generator.stream_presentation(request)]

        self.assertEqual([item["type"] for item in events], ["slide", "slide", "final"])
        self.assertEqual(events[0]["completed"], 1)
        self.assertEqual(events[-1]["response"]["slide_count"], 2)

    def test_model_intent_fields_are_enforced_by_code(self):
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        merged = workflow._merge_intent(
            {"title": "已有主题"},
            {"grade": "三年级", "unexpected_admin_field": True},
        )
        self.assertEqual(merged["grade"], "三年级")
        self.assertNotIn("unexpected_admin_field", merged)

    async def test_resource_sync_skips_parse_and_embedding_when_content_sha_is_unchanged(self):
        store = ResourceIndexStore.__new__(ResourceIndexStore)
        store.available = False
        store.settings = SimpleNamespace(index_parse_timeout_seconds=2)
        store.embedding_client = SimpleNamespace(embed_documents=AsyncMock())
        store._load_resource_meta = lambda _key: {
            "parse_status": "completed",
            "chunk_count": 3,
            "file_fingerprint": "abc123",
            "metadata": {"parse": {"content_sha256": "abc123"}},
        }
        store.update_metadata = lambda _request: {"status": "updated"}
        request = ResourceIndexSyncRequest(
            source_type="personal", resource_id="12", title="资料.txt",
            file_url="https://example.com/material.txt", file_type="txt",
        )
        unchanged = ParsedResource(text="", metadata={"content_sha256": "abc123", "unchanged": True})
        with patch("a12_ppt.resources.index_store.download_and_parse_resource", new=AsyncMock(return_value=unchanged)) as downloader:
            result = await store.sync_resource(request)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "content_sha256_unchanged")
        downloader.assert_awaited_once_with(request, previous_digest="abc123")
        store.embedding_client.embed_documents.assert_not_awaited()

    async def test_audio_resource_parser_uses_shared_asr_service(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp, patch(
            "a12_ppt.resources.parsers.audio_parser.transcribe_audio",
            new=AsyncMock(return_value={
                "text": "课堂录音内容", "model": "whisper-1", "status": "completed",
                "language": "zh", "error_message": None,
            }),
        ):
            parsed = await parse_audio(Path(temp.name))
        self.assertIn("课堂录音内容", parsed.text)
        self.assertTrue(parsed.metadata["transcript_available"])

    async def test_html_generation_performs_one_repair_after_initial_failure(self):
        class _RepairLlm:
            def __init__(self):
                self.calls = 0

            async def complete(self, *_args):
                self.calls += 1
                if self.calls == 1:
                    return "<html><head></head><body><div>broken</div></body></html>"
                return "<!DOCTYPE html><html><head><style>body{overflow:hidden}.slide{width:1280px;height:720px}</style></head><body><section class='slide'>ok</section></body></html>"

        generator = PPTGenerator.__new__(PPTGenerator)
        generator.llm = _RepairLlm()
        generator.settings = SimpleNamespace(max_html_retries=1)
        result = await generator._complete_html_with_retry("prompt", "system", {}, 1, 1)
        self.assertIn("1280px", result)
        self.assertEqual(generator.llm.calls, 2)

    def test_strict_html_validation_rejects_external_cdn(self):
        markup = "<!DOCTYPE html><html><head><link href='https://cdn.example.com/a.css' rel='stylesheet'><style>body{overflow:hidden}.slide{width:1280px;height:720px}</style></head><body><section class='slide'>ok</section></body></html>"
        report = validate_html(markup, strict=True)
        self.assertFalse(report["valid"])
        self.assertTrue(any("CDN" in item for item in report["errors"]))

    def test_scanned_pdf_page_can_render_for_ocr(self):
        from PyPDF2 import PdfWriter

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            pdf_path = Path(temp.name)
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            writer.write(temp)
        rendered = _render_pdf_pages(pdf_path, [0])
        try:
            self.assertEqual(len(rendered), 1)
            self.assertTrue(rendered[0][1].exists())
            self.assertGreater(rendered[0][1].stat().st_size, 0)
        finally:
            pdf_path.unlink(missing_ok=True)
            for _, image_path in rendered:
                image_path.unlink(missing_ok=True)

    def test_outline_always_has_classroom_engagement_fields(self):
        generator = PPTGenerator.__new__(PPTGenerator)
        request = OutlineGenerateRequest(
            title="分数的初步认识",
            subject="数学",
            grade="三年级",
            requirements="基础薄弱，风格活泼，多提问",
            slide_count=8,
        )
        outline = generator._fallback_outline(request, 8)
        decorated = generator._decorate_outline(outline, request)

        self.assertTrue(decorated["quality_report"]["passed"])
        self.assertTrue(any(slide["slide_type"] == "activity" for slide in decorated["slides"]))
        phases = {slide["learning_phase"] for slide in decorated["slides"]}
        self.assertIn("pre_assessment", phases)
        self.assertIn("worked_example", phases)
        self.assertIn("summary", phases)
        self.assertTrue(any(slide["student_action_mode"] == "interactive" for slide in decorated["slides"]))
        for slide in decorated["slides"]:
            self.assertTrue(slide["student_task"])
            self.assertTrue(slide["teacher_prompt"])
            self.assertTrue(slide["understanding_check"])
            self.assertTrue(slide["learner_question"])
            self.assertTrue(slide["learning_theories"])
            self.assertTrue(slide["scaffolding"])
            self.assertTrue(slide["feedback_strategy"])
            self.assertGreater(slide["estimated_minutes"], 0)

    async def test_workspace_stream_uses_openai_compatible_chunks(self):
        request = WorkspaceChatRequest(
            user_id="teacher-1",
            mode="discussion",
            messages=[{"role": "user", "content": "怎样设计课堂导入？"}],
        )
        with patch("a12_ppt.workspace.LLMClient", return_value=_FakeLlm()), \
                patch("a12_ppt.workspace.postgres_memory_store.get_teacher_profile", return_value=None):
            chunks = [chunk async for chunk in stream_workspace_chat(request)]

        self.assertEqual(chunks[-1], "data: [DONE]\n\n")
        payload = json.loads(chunks[0].removeprefix("data: "))
        self.assertEqual(payload["choices"][0]["delta"]["content"], "课堂")

    async def test_unchanged_resource_skips_parser_by_content_sha256(self):
        import hashlib

        request = ResourceIndexSyncRequest(
            source_type="personal",
            resource_id="12",
            title="测试资料.txt",
            file_url="http://127.0.0.1/material.txt",
            file_type="txt",
        )
        digest = hashlib.sha256(_FakeResponse.content).hexdigest()
        with patch("a12_ppt.resources.downloader.httpx.AsyncClient", return_value=_FakeHttpClient()), \
                patch("a12_ppt.resources.downloader.parse_resource_file", new=AsyncMock(return_value=ParsedResource(text="不应执行", metadata={})) ) as parser:
            parsed = await download_and_parse_resource(request, previous_digest=digest)

        self.assertTrue(parsed.metadata["unchanged"])
        parser.assert_not_awaited()

    async def test_video_without_ffmpeg_returns_clear_degradation(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as temp, \
                patch("a12_ppt.resources.parsers.video_parser._find_ffmpeg", return_value=None):
            result = await _transcribe_video_audio(Path(temp.name))
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("FFmpeg", result["error_message"])


if __name__ == "__main__":
    unittest.main()
