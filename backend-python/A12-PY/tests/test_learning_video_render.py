import io
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from a12_ppt.learning_video import render_learning_video
from a12_ppt.resources.parsers.video_parser import _find_ffmpeg


class LearningVideoRenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_browser_and_ffmpeg_create_mp4_with_stubbed_speech(self):
        if not _find_ffmpeg(): self.skipTest("需要ffmpeg")
        stream = io.BytesIO()
        with wave.open(stream, "wb") as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(struct.pack("<h", 0) * 8000)
        client = SimpleNamespace(audio=SimpleNamespace(speech=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(content=stream.getvalue())))))
        class Client:
            async def __aenter__(self): return client
            async def __aexit__(self, *_): return False
        # render函数通过client对象直接调用audio；模拟只替换外部TTS，不替换编码和浏览器。
        stub = Client(); stub.audio = client.audio
        settings = SimpleNamespace(openai_api_key="test", openai_base_url="https://example.invalid/v1",
            request_timeout_seconds=10, tts_model="test", tts_voice="test")
        with tempfile.TemporaryDirectory() as directory, patch("a12_ppt.learning_video.get_settings", return_value=settings), \
             patch("openai.AsyncOpenAI", return_value=stub):
            output = Path(directory) / "test.mp4"
            try:
                metadata = await render_learning_video({"slides": [{"html": '<html><body style="margin:0;background:#eff6ff"><h1>学习视频</h1></body></html>', "narration": "测试旁白"}]}, output, AsyncMock())
            except Exception as exc:
                if "Executable doesn't exist" in str(exc): self.skipTest("需要Chromium")
                raise
            self.assertGreater(output.stat().st_size, 1000)
            self.assertIn(b"ftyp", output.read_bytes()[:32])
            self.assertEqual(metadata["page_count"], 1)
