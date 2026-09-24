import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from a12_ppt.resources.parsers.common import normalize_file_type
from a12_ppt.resources.chunks import chunk_records
from a12_ppt.resources.index_store import ResourceIndexStore
from a12_ppt.resources.parsers.common import ParsedResource
from a12_ppt.models import ResourceIndexSyncRequest
from a12_ppt.resources.parsers.video_parser import (
    _adaptive_frame_limit,
    _build_timeline,
    _format_timestamp,
    _parse_subtitle_text,
    _timeline_text,
    _trim_transcript_overlap,
    _transcribe_video_audio,
    parse_video,
)


class VideoParserTests(unittest.IsolatedAsyncioTestCase):
    def test_subtitle_files_are_text_and_unknown_extensions_do_not_recurse(self):
        self.assertEqual(normalize_file_type(Path("lesson.vtt")), "txt")
        self.assertEqual(normalize_file_type(Path("lesson.srt")), "txt")
        self.assertEqual(normalize_file_type(Path("archive.zip")), "other")

    def test_frame_limit_grows_with_duration_and_is_capped(self):
        self.assertEqual(_adaptive_frame_limit(30), 6)
        self.assertEqual(_adaptive_frame_limit(300), 10)
        self.assertEqual(_adaptive_frame_limit(7200), 24)

    def test_subtitles_preserve_timestamps_and_clean_markup(self):
        content = """WEBVTT

00:00:01.000 --> 00:00:03.500
<b>勾股定理</b>

2
00:01:02,250 --> 00:01:05,000
a²+b²=c²
"""
        segments = _parse_subtitle_text(content)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "勾股定理")
        self.assertEqual(segments[1]["start_seconds"], 62.25)

    def test_timeline_aligns_frames_with_transcript_segments(self):
        frames = [
            {"timestamp_seconds": 12, "summary": "展示三角形"},
            {"timestamp_seconds": 330, "summary": "展示公式"},
        ]
        transcripts = [
            {"start_seconds": 0, "end_seconds": 300, "text": "情境导入"},
            {"start_seconds": 300, "end_seconds": 600, "text": "公式推导"},
        ]
        timeline = _build_timeline(frames, transcripts, 600)
        self.assertEqual(timeline[0]["frames"][0]["summary"], "展示三角形")
        self.assertEqual(timeline[1]["frames"][0]["summary"], "展示公式")
        text = _timeline_text(timeline)
        self.assertIn("[00:00-05:00]", text)
        self.assertIn("公式推导", text)
        self.assertEqual(_format_timestamp(3661), "01:01:01")

    def test_video_chunks_carry_own_time_range_without_full_timeline(self):
        timeline = [{
            "start_seconds": 300,
            "end_seconds": 600,
            "transcript": "公式推导",
            "frames": [{"timestamp_seconds": 330, "summary": "展示公式"}],
        }]
        metadata = {
            "source": "personal", "resource_id": "12", "allow_ai": True, "available": True,
            "parse": {"modality": "video", "duration_seconds": 600, "timeline": timeline, "keyframes": [1, 2]},
        }
        records = chunk_records("旧文本", metadata=metadata)
        self.assertEqual(records[0]["metadata"]["start_seconds"], 300)
        self.assertEqual(records[0]["metadata"]["frame_timestamps"], [330.0])

        store = ResourceIndexStore.__new__(ResourceIndexStore)
        compact = store._compact_chunk_metadata(metadata, records[0]["metadata"])
        self.assertNotIn("timeline", compact["parse"])
        self.assertNotIn("keyframes", compact["parse"])
        self.assertTrue(compact["allow_ai"])
        self.assertEqual(compact["start_timestamp"], "05:00")

    def test_transcript_overlap_is_removed(self):
        self.assertEqual(_trim_transcript_overlap("下面开始学习勾股定理", "勾股定理的证明方法"), "的证明方法")

    async def test_audio_is_split_into_five_minute_asr_segments(self):
        def fake_run(args, **_kwargs):
            pattern = str(args[-1])
            for index in range(3):
                Path(pattern.replace("%03d", f"{index:03d}")).write_bytes(b"audio")
            return SimpleNamespace(returncode=0)

        responses = [
            {"text": "第一段", "status": "completed", "error_message": None},
            {"text": "第二段", "status": "completed", "error_message": None},
            {"text": "第三段", "status": "completed", "error_message": None},
        ]
        with tempfile.NamedTemporaryFile(suffix=".mp4") as temp, \
                patch("a12_ppt.resources.parsers.video_parser._find_ffmpeg", return_value="ffmpeg"), \
                patch("a12_ppt.resources.parsers.video_parser.subprocess.run", side_effect=fake_run), \
                patch("a12_ppt.resources.parsers.video_parser.transcribe_audio", new=AsyncMock(side_effect=responses)):
            result = await _transcribe_video_audio(Path(temp.name), duration_seconds=620)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["segments"]), 3)
        self.assertEqual(result["segments"][1]["start_seconds"], 300)
        self.assertEqual(result["segments"][0]["extraction_end_seconds"], 308)
        self.assertEqual(result["segments"][1]["extraction_start_seconds"], 292)
        self.assertEqual(result["segments"][2]["end_seconds"], 620)
        self.assertIn("第三段", result["text"])

    async def test_video_result_contains_searchable_timeline_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            frame_path = Path(directory) / "frame.jpg"
            frame_path.write_bytes(b"frame")
            samples = [{
                "path": frame_path,
                "timestamp_seconds": 15,
                "sampling_reason": "scene_change",
            }]
            with tempfile.NamedTemporaryFile(suffix=".mp4") as video, \
                    patch("a12_ppt.resources.parsers.video_parser._probe_video", return_value={
                        "duration_seconds": 120, "width": 1280, "height": 720, "fps": 25,
                    }), \
                    patch("a12_ppt.resources.parsers.video_parser._extract_keyframes", return_value=samples), \
                    patch("a12_ppt.resources.parsers.video_parser._describe_keyframes", new=AsyncMock(return_value=[{
                        **samples[0], "summary": "教师展示直角三角形",
                    }])), \
                    patch("a12_ppt.resources.parsers.video_parser._extract_embedded_subtitles", return_value=[{
                        "start_seconds": 10, "end_seconds": 20, "text": "下面学习勾股定理", "status": "completed",
                    }]):
                parsed = await parse_video(Path(video.name))

        self.assertIn("[00:10-00:20]", parsed.text)
        self.assertIn("教师展示直角三角形", parsed.text)
        self.assertEqual(parsed.metadata["transcript_source"], "embedded_subtitles")
        self.assertEqual(parsed.metadata["timeline_segment_count"], 1)

    async def test_video_index_writes_compact_per_chunk_timestamps(self):
        store = ResourceIndexStore.__new__(ResourceIndexStore)
        store.available = False
        store.settings = SimpleNamespace(index_parse_timeout_seconds=5)
        store.embedding_dimensions = 2
        store.embedding_client = SimpleNamespace(embed_documents=AsyncMock(return_value=[[0.1, 0.2]]))
        store._load_resource_meta = lambda _key: None
        store._read_fallback = lambda: {"resources": {}, "chunks": {}}
        saved = {}
        store._write_fallback = lambda data: saved.update(data)
        parsed = ParsedResource(text="视频内容", metadata={
            "modality": "video",
            "duration_seconds": 600,
            "timeline": [{
                "start_seconds": 0, "end_seconds": 300, "transcript": "课堂导入", "frames": [],
            }],
            "keyframes": [{"timestamp_seconds": 10}],
        })
        request = ResourceIndexSyncRequest(
            source_type="personal", resource_id="99", title="课堂.mp4",
            file_url="https://example.com/class.mp4", file_type="video", allow_ai=True,
        )
        with patch(
            "a12_ppt.resources.index_store.download_and_parse_resource",
            new=AsyncMock(return_value=parsed),
        ):
            result = await store.sync_resource(request)

        chunk = saved["chunks"]["personal:99"][0]
        self.assertEqual(result["status"], "indexed")
        self.assertEqual(chunk["metadata"]["start_seconds"], 0)
        self.assertEqual(chunk["metadata"]["end_seconds"], 300)
        self.assertNotIn("timeline", chunk["metadata"]["parse"])
        self.assertNotIn("keyframes", chunk["metadata"]["parse"])


if __name__ == "__main__":
    unittest.main()
