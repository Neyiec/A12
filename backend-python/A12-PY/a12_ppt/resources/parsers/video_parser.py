import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from .common import ParsedResource, merge_text_blocks
from .vision_parser import describe_image


async def parse_video(path: Path, max_frames: int = 6) -> ParsedResource:
    frame_paths = _extract_keyframes(path, max_frames)
    try:
        summaries = await asyncio.gather(*[
            describe_image(frame, f"这是教学参考视频的第 {index + 1} 个关键帧。请提取画面文字、场景、知识点和可用于课件生成的信息。")
            for index, frame in enumerate(frame_paths)
        ])
        blocks = [
            f"视频关键帧 {index + 1} 视觉理解:\n{summary}"
            for index, summary in enumerate(summaries)
            if summary
        ]
        return ParsedResource(
            text=merge_text_blocks(blocks),
            metadata={
                "modality": "video",
                "parser": "opencv/ffmpeg+vision",
                "keyframe_count": len(frame_paths),
                "vision_summary_count": len(blocks),
            },
        )
    finally:
        for frame in frame_paths:
            frame.unlink(missing_ok=True)


def _extract_keyframes(path: Path, max_frames: int) -> list[Path]:
    frames = _extract_keyframes_with_opencv(path, max_frames)
    if frames:
        return frames
    return _extract_keyframes_with_ffmpeg(path, max_frames)


def _extract_keyframes_with_opencv(path: Path, max_frames: int) -> list[Path]:
    try:
        import cv2

        capture = cv2.VideoCapture(str(path))
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            return []
        frame_indexes = _sample_indexes(total, max_frames)
        output_paths: list[Path] = []
        for index in frame_indexes:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            success, frame = capture.read()
            if not success:
                continue
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                frame_path = Path(temp.name)
            cv2.imwrite(str(frame_path), frame)
            output_paths.append(frame_path)
        capture.release()
        return output_paths
    except Exception:
        return []


def _extract_keyframes_with_ffmpeg(path: Path, max_frames: int) -> list[Path]:
    if not shutil.which("ffmpeg"):
        return []
    output_dir = Path(tempfile.mkdtemp(prefix="a12_video_frames_"))
    output_pattern = output_dir / "frame_%03d.jpg"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-vf",
                f"fps=1/{max(1, 60 // max_frames)}",
                "-frames:v",
                str(max_frames),
                str(output_pattern),
            ],
            check=False,
            timeout=90,
        )
        return sorted(output_dir.glob("frame_*.jpg"))[:max_frames]
    except Exception:
        return []


def _sample_indexes(total_frames: int, max_frames: int) -> list[int]:
    if total_frames <= max_frames:
        return list(range(total_frames))
    step = total_frames / (max_frames + 1)
    return [max(0, min(total_frames - 1, round(step * (index + 1)))) for index in range(max_frames)]
