import asyncio
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .common import ParsedResource, merge_text_blocks
from .vision_parser import describe_image
from ...asr.service import transcribe_audio


DEFAULT_AUDIO_CHUNK_SECONDS = 300
AUDIO_CHUNK_OVERLAP_SECONDS = 8
MAX_AUTO_KEYFRAMES = 24
VISION_CONCURRENCY = 4
ASR_CONCURRENCY = 2


async def parse_video(path: Path, max_frames: int | None = None) -> ParsedResource:
    """按时间轴解析教学视频，合并关键帧、字幕和分段语音转写。"""
    video_meta = await asyncio.to_thread(_probe_video, path)
    duration = float(video_meta.get("duration_seconds") or 0)
    frame_limit = max_frames or _adaptive_frame_limit(duration)
    frame_samples = await asyncio.to_thread(_extract_keyframes, path, frame_limit, video_meta)
    try:
        frame_analyses = await _describe_keyframes(frame_samples)
        subtitle_segments = await asyncio.to_thread(_extract_embedded_subtitles, path)
        if subtitle_segments:
            transcript = {
                "status": "completed", "source": "embedded_subtitles",
                "segments": subtitle_segments,
                "text": "\n".join(item["text"] for item in subtitle_segments),
                "error_message": None,
            }
        else:
            transcript = await _transcribe_video_audio(path, duration_seconds=duration)

        timeline = _build_timeline(frame_analyses, transcript.get("segments") or [], duration)
        text = _timeline_text(timeline)
        return ParsedResource(
            text=text,
            metadata={
                "modality": "video",
                "parser": "opencv/ffmpeg+scene-detection+vision+chunked-asr",
                **video_meta,
                "keyframe_limit": frame_limit,
                "keyframe_count": len(frame_samples),
                "keyframes": [
                    {
                        "timestamp_seconds": item["timestamp_seconds"],
                        "timestamp": _format_timestamp(item["timestamp_seconds"]),
                        "sampling_reason": item.get("sampling_reason"),
                        "vision_available": bool(item.get("summary")),
                    }
                    for item in frame_analyses
                ],
                "vision_summary_count": sum(bool(item.get("summary")) for item in frame_analyses),
                "transcript_source": transcript.get("source"),
                "transcript_available": bool(transcript.get("text")),
                "transcript_segment_count": len(transcript.get("segments") or []),
                "audio_status": transcript.get("status"),
                "audio_error": transcript.get("error_message"),
                "timeline_segment_count": len(timeline),
                "timeline": timeline,
            },
        )
    finally:
        _cleanup_frame_samples(frame_samples)


async def _describe_keyframes(frame_samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(VISION_CONCURRENCY)

    async def describe(index: int, sample: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            timestamp = float(sample.get("timestamp_seconds") or 0)
            summary = await describe_image(
                sample["path"],
                (
                    f"这是教学视频 {_format_timestamp(timestamp)} 处的代表画面（第 {index + 1} 帧）。"
                    "请提取画面、板书或PPT文字，识别知识点、公式、图表、例题、教师提问和教学环节，"
                    "并指出适合复用到课件中的内容。没有证据的内容不要猜测，使用简体中文。"
                ),
            )
            return {**sample, "summary": summary.strip()}

    if not frame_samples:
        return []
    return await asyncio.gather(*[
        describe(index, sample) for index, sample in enumerate(frame_samples)
    ])


def _probe_video(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {"duration_seconds": 0.0, "width": 0, "height": 0, "fps": 0.0}
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,avg_frame_rate,duration:format=duration",
                    "-of", "json", str(path),
                ],
                capture_output=True, text=True, timeout=30, check=False,
            )
            payload = json.loads(result.stdout or "{}")
            stream = (payload.get("streams") or [{}])[0]
            format_info = payload.get("format") or {}
            metadata.update({
                "duration_seconds": round(_safe_float(stream.get("duration") or format_info.get("duration")), 3),
                "width": int(_safe_float(stream.get("width"))),
                "height": int(_safe_float(stream.get("height"))),
                "fps": round(_parse_fraction(stream.get("avg_frame_rate")), 3),
            })
            if metadata["duration_seconds"] > 0:
                return metadata
        except Exception:
            pass

    # imageio-ffmpeg 自带 ffmpeg 但不一定带 ffprobe；读取首帧元数据作为免安装回退。
    try:
        import imageio_ffmpeg

        reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
        try:
            bundled_meta = next(reader)
        finally:
            reader.close()
        size = bundled_meta.get("source_size") or bundled_meta.get("size") or (0, 0)
        metadata.update({
            "duration_seconds": round(_safe_float(bundled_meta.get("duration")), 3),
            "width": int(size[0] or 0),
            "height": int(size[1] or 0),
            "fps": round(_safe_float(bundled_meta.get("fps")), 3),
        })
        if metadata["duration_seconds"] > 0:
            return metadata
    except Exception:
        pass

    try:
        import cv2

        capture = cv2.VideoCapture(str(path))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        metadata.update({
            "duration_seconds": round(total_frames / fps, 3) if fps > 0 else 0.0,
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            "fps": round(fps, 3),
        })
        capture.release()
    except Exception:
        pass
    return metadata


def _adaptive_frame_limit(duration_seconds: float) -> int:
    if duration_seconds <= 0:
        return 8
    return min(MAX_AUTO_KEYFRAMES, max(6, math.ceil(duration_seconds / 60) * 2))


def _extract_keyframes(path: Path, max_frames: int, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    frames = _extract_keyframes_with_opencv(path, max_frames, metadata or {})
    return frames or _extract_keyframes_with_ffmpeg(path, max_frames, metadata or {})


def _extract_keyframes_with_opencv(path: Path, max_frames: int, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        import cv2
        import numpy as np

        capture = cv2.VideoCapture(str(path))
        fps = float(metadata.get("fps") or capture.get(cv2.CAP_PROP_FPS) or 0)
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = float(metadata.get("duration_seconds") or (total / fps if fps > 0 else 0))
        if total <= 0 and duration <= 0:
            capture.release()
            return []

        candidate_count = min(96, max(max_frames * 5, 24))
        if duration > 0:
            timestamps = np.linspace(0, max(0, duration - 0.05), candidate_count).tolist()
        else:
            indexes = np.linspace(0, max(0, total - 1), candidate_count).astype(int).tolist()
            timestamps = [(index / fps) if fps > 0 else float(index) for index in indexes]

        candidates: list[dict[str, Any]] = []
        previous_gray = None
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            success, frame = capture.read()
            if not success:
                continue
            gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)
            scene_score = 1.0 if previous_gray is None else float(cv2.absdiff(gray, previous_gray).mean() / 255.0)
            previous_gray = gray
            encoded, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            if encoded:
                candidates.append({
                    "timestamp_seconds": round(float(timestamp), 3),
                    "scene_score": scene_score,
                    "jpeg": buffer.tobytes(),
                })
        capture.release()
        return _materialize_selected_frames(candidates, max_frames, duration)
    except Exception:
        return []


def _materialize_selected_frames(candidates: list[dict[str, Any]], max_frames: int, duration: float) -> list[dict[str, Any]]:
    if not candidates:
        return []
    limit = min(max_frames, len(candidates))
    selected: dict[int, str] = {}
    uniform_count = min(limit, max(2, math.ceil(limit / 2)))
    end_time = duration if duration > 0 else float(candidates[-1]["timestamp_seconds"])
    targets = [end_time * index / max(1, uniform_count - 1) for index in range(uniform_count)]
    for target in targets:
        index = min(range(len(candidates)), key=lambda item: abs(float(candidates[item]["timestamp_seconds"]) - target))
        selected[index] = "uniform"

    minimum_gap = max(1.0, end_time / max(1, limit * 3)) if end_time else 1.0
    for index in sorted(range(len(candidates)), key=lambda item: candidates[item]["scene_score"], reverse=True):
        if len(selected) >= limit:
            break
        timestamp = float(candidates[index]["timestamp_seconds"])
        if all(abs(timestamp - float(candidates[chosen]["timestamp_seconds"])) >= minimum_gap for chosen in selected):
            selected[index] = "scene_change"

    for index in range(len(candidates)):
        if len(selected) >= limit:
            break
        selected.setdefault(index, "coverage")

    output_dir = Path(tempfile.mkdtemp(prefix="a12_video_frames_"))
    frames: list[dict[str, Any]] = []
    for sequence, index in enumerate(sorted(selected, key=lambda item: candidates[item]["timestamp_seconds"])):
        frame_path = output_dir / f"frame_{sequence:03d}.jpg"
        frame_path.write_bytes(candidates[index]["jpeg"])
        frames.append({
            "path": frame_path,
            "timestamp_seconds": candidates[index]["timestamp_seconds"],
            "scene_score": round(float(candidates[index]["scene_score"]), 4),
            "sampling_reason": selected[index],
        })
    return frames


def _extract_keyframes_with_ffmpeg(path: Path, max_frames: int, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return []
    output_dir = Path(tempfile.mkdtemp(prefix="a12_video_frames_"))
    output_pattern = output_dir / "frame_%03d.jpg"
    duration = float(metadata.get("duration_seconds") or 0)
    interval = max(1.0, duration / max_frames) if duration else 10.0
    try:
        subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
                "-vf", f"fps=1/{interval}", "-frames:v", str(max_frames), str(output_pattern),
            ],
            check=False, timeout=180,
        )
        paths = sorted(output_dir.glob("frame_*.jpg"))[:max_frames]
        return [
            {
                "path": frame_path,
                "timestamp_seconds": round(index * interval, 3),
                "scene_score": None,
                "sampling_reason": "uniform_ffmpeg",
            }
            for index, frame_path in enumerate(paths)
        ]
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        return []


async def _transcribe_video_audio(path: Path, duration_seconds: float = 0) -> dict[str, Any]:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return {
            "status": "unavailable", "source": "asr", "segments": [], "text": "",
            "error_message": "视频音轨分析需要安装 FFmpeg",
        }

    with tempfile.TemporaryDirectory(prefix="a12_video_audio_") as directory:
        try:
            audio_chunks = await asyncio.to_thread(
                _extract_audio_chunks, path, Path(directory), ffmpeg, duration_seconds,
            )
            if not audio_chunks:
                return {
                    "status": "unavailable", "source": "asr", "segments": [], "text": "",
                    "error_message": "未能提取音轨，视频可能无音轨或格式不受支持",
                }

            semaphore = asyncio.Semaphore(ASR_CONCURRENCY)

            async def transcribe(chunk: dict[str, Any]) -> dict[str, Any]:
                audio_path = chunk["path"]
                if audio_path.stat().st_size > 24 * 1024 * 1024:
                    return {
                        **{key: value for key, value in chunk.items() if key != "path"}, "text": "",
                        "status": "failed", "error_message": "分段音轨仍超过 24MB",
                    }
                async with semaphore:
                    response = await transcribe_audio(audio_path)
                return {
                    **{key: value for key, value in chunk.items() if key != "path"},
                    "text": str(response.get("text") or "").strip(),
                    "status": response.get("status"),
                    "error_message": response.get("error_message"),
                    "asr_segments": [
                        {**part,
                         "start": round(float(chunk.get("start_seconds") or 0) + float(part.get("start") or 0), 3),
                         "end": round(float(chunk.get("start_seconds") or 0) + float(part.get("end") or 0), 3)}
                        for part in (response.get("segments") or []) if isinstance(part, dict)
                    ],
                }

            segments = await asyncio.gather(*[
                transcribe(chunk) for chunk in audio_chunks
            ])
            previous_text = ""
            for segment in segments:
                segment["text"] = _trim_transcript_overlap(previous_text, str(segment.get("text") or ""))
                if segment["text"]:
                    previous_text = f"{previous_text}{segment['text']}"[-500:]
            successful = [segment for segment in segments if segment.get("text")]
            status = "completed" if len(successful) == len(segments) else "partial" if successful else "failed"
            errors = [str(segment.get("error_message")) for segment in segments if segment.get("error_message")]
            return {
                "status": status,
                "source": "asr",
                "segments": segments,
                "word_timeline": [part for segment in segments for part in (segment.get("asr_segments") or [])],
                "text": "\n".join(segment["text"] for segment in successful),
                "error_message": "; ".join(dict.fromkeys(errors)) or None,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "status": "failed", "source": "asr", "segments": [], "text": "",
                "error_message": f"视频音轨提取失败或超时: {exc}",
            }


def _extract_audio_chunks(
    path: Path,
    directory: Path,
    ffmpeg: str,
    duration_seconds: float,
) -> list[dict[str, Any]]:
    if duration_seconds <= 0:
        output_pattern = directory / "audio_%03d.mp3"
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k",
                "-f", "segment", "-segment_time", str(DEFAULT_AUDIO_CHUNK_SECONDS),
                "-reset_timestamps", "1", str(output_pattern),
            ],
            capture_output=True, timeout=300, check=False,
        )
        if result.returncode:
            return []
        return [
            {
                "path": audio_path,
                "start_seconds": index * DEFAULT_AUDIO_CHUNK_SECONDS,
                "end_seconds": (index + 1) * DEFAULT_AUDIO_CHUNK_SECONDS,
                "extraction_start_seconds": index * DEFAULT_AUDIO_CHUNK_SECONDS,
                "extraction_end_seconds": (index + 1) * DEFAULT_AUDIO_CHUNK_SECONDS,
            }
            for index, audio_path in enumerate(sorted(directory.glob("audio_*.mp3")))
        ]

    chunks: list[dict[str, Any]] = []
    chunk_count = max(1, math.ceil(duration_seconds / DEFAULT_AUDIO_CHUNK_SECONDS))
    for index in range(chunk_count):
        content_start = index * DEFAULT_AUDIO_CHUNK_SECONDS
        content_end = min(duration_seconds, content_start + DEFAULT_AUDIO_CHUNK_SECONDS)
        extraction_start = max(0.0, content_start - (AUDIO_CHUNK_OVERLAP_SECONDS if index else 0))
        extraction_end = min(duration_seconds, content_end + (AUDIO_CHUNK_OVERLAP_SECONDS if index + 1 < chunk_count else 0))
        audio_path = directory / f"audio_{index:03d}.mp3"
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(extraction_start), "-i", str(path),
                "-t", str(max(0.1, extraction_end - extraction_start)),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(audio_path),
            ],
            capture_output=True, timeout=180, check=False,
        )
        if result.returncode == 0 and audio_path.exists():
            chunks.append({
                "path": audio_path,
                "start_seconds": round(content_start, 3),
                "end_seconds": round(content_end, 3),
                "extraction_start_seconds": round(extraction_start, 3),
                "extraction_end_seconds": round(extraction_end, 3),
            })
    return chunks


def _trim_transcript_overlap(previous: str, current: str, max_overlap: int = 120) -> str:
    previous = str(previous or "").strip()
    current = str(current or "").strip()
    if not previous or not current:
        return current
    limit = min(max_overlap, len(previous), len(current))
    for size in range(limit, 3, -1):
        if previous[-size:].casefold() == current[:size].casefold():
            return current[size:].lstrip(" ，。！？、,.;；:：")
    return current


def _extract_embedded_subtitles(path: Path) -> list[dict[str, Any]]:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return []
    with tempfile.TemporaryDirectory(prefix="a12_video_subtitles_") as directory:
        subtitle_path = Path(directory) / "subtitle.vtt"
        try:
            result = subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                    "-map", "0:s:0", "-f", "webvtt", str(subtitle_path),
                ],
                capture_output=True, timeout=90, check=False,
            )
            if result.returncode or not subtitle_path.exists():
                return []
            return _parse_subtitle_text(subtitle_path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, subprocess.TimeoutExpired):
            return []


def _parse_subtitle_text(content: str) -> list[dict[str, Any]]:
    normalized = str(content or "").replace("\r\n", "\n")
    pattern = re.compile(
        r"(?m)^(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
        r"(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})[^\n]*\n"
        r"(?P<text>.*?)(?=\n{2,}|\Z)",
        re.S,
    )
    segments = []
    for match in pattern.finditer(normalized):
        text = re.sub(r"<[^>]+>", "", match.group("text"))
        text = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if text:
            segments.append({
                "start_seconds": _subtitle_seconds(match.group("start")),
                "end_seconds": _subtitle_seconds(match.group("end")),
                "text": text,
                "status": "completed",
            })
    return segments


def _build_timeline(frames: list[dict[str, Any]], transcript_segments: list[dict[str, Any]], duration_seconds: float) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    if transcript_segments:
        for index, segment in enumerate(transcript_segments):
            start = float(segment.get("start_seconds") or 0)
            end = float(segment.get("end_seconds") or start)
            timeline.append({
                "index": index + 1,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "transcript": str(segment.get("text") or "").strip(),
                "frames": [],
            })

        for frame in frames:
            timestamp = float(frame.get("timestamp_seconds") or 0)
            if not timeline:
                continue
            containing = [
                item for item in timeline
                if item["start_seconds"] <= timestamp < max(item["end_seconds"], item["start_seconds"] + 0.001)
            ]
            candidates = containing or timeline
            nearest = min(
                candidates,
                key=lambda item: abs(timestamp - ((item["start_seconds"] + item["end_seconds"]) / 2)),
            )
            nearest["frames"].append({"timestamp_seconds": timestamp, "summary": frame.get("summary") or ""})
    else:
        for index, frame in enumerate(frames):
            start = float(frame.get("timestamp_seconds") or 0)
            next_start = float(frames[index + 1].get("timestamp_seconds") or start) if index + 1 < len(frames) else duration_seconds or start
            timeline.append({
                "index": index + 1,
                "start_seconds": round(start, 3),
                "end_seconds": round(max(start, next_start), 3),
                "transcript": "",
                "frames": [{"timestamp_seconds": start, "summary": frame.get("summary") or ""}],
            })
    return timeline


def _timeline_text(timeline: list[dict[str, Any]]) -> str:
    blocks = []
    for item in timeline:
        frame_lines = [
            f"画面 {_format_timestamp(frame['timestamp_seconds'])}: {frame['summary']}"
            for frame in item.get("frames") or [] if frame.get("summary")
        ]
        block = merge_text_blocks([
            f"[{_format_timestamp(item['start_seconds'])}-{_format_timestamp(item['end_seconds'])}] 视频片段 {item['index']}",
            f"语音或字幕:\n{item['transcript']}" if item.get("transcript") else "",
            "\n".join(frame_lines),
        ])
        if block:
            blocks.append(block)
    return merge_text_blocks(blocks)


def _cleanup_frame_samples(frame_samples: list[dict[str, Any]]) -> None:
    directories: set[Path] = set()
    for sample in frame_samples:
        frame_path = sample.get("path")
        if isinstance(frame_path, Path):
            directories.add(frame_path.parent)
            frame_path.unlink(missing_ok=True)
    for directory in directories:
        if directory.name.startswith("a12_video_frames_"):
            shutil.rmtree(directory, ignore_errors=True)


def _format_timestamp(seconds: float) -> str:
    value = max(0, int(round(float(seconds or 0))))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _subtitle_seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    try:
        if len(parts) == 3:
            return round(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]), 3)
        return round(float(parts[0]) * 60 + float(parts[1]), 3)
    except (ValueError, IndexError):
        return 0.0


def _parse_fraction(value: Any) -> float:
    text = str(value or "0")
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        denominator_value = _safe_float(denominator)
        return _safe_float(numerator) / denominator_value if denominator_value else 0.0
    return _safe_float(text)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _find_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
