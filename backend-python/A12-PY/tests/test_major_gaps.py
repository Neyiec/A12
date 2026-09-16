import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from a12_ppt.models import OutlineGenerateRequest, ResourceIndexSyncRequest
from a12_ppt.presentation.generator import PPTGenerator
from a12_ppt.resources.downloader import download_and_parse_resource
from a12_ppt.resources.parsers.common import ParsedResource
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
                patch("a12_ppt.resources.parsers.video_parser.shutil.which", return_value=None):
            result = await _transcribe_video_audio(Path(temp.name))
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("FFmpeg", result["error_message"])


if __name__ == "__main__":
    unittest.main()
