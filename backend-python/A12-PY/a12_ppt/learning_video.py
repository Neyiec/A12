"""HTML 逐页静态画面 + 讲稿旁白 → MP4，有限重试的持久化导出任务。"""
import asyncio
import contextlib
import json
import logging
import os
import sys
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from .config import get_settings
from .course_graph import course_graph_store
from .resources.parsers.video_parser import _find_ffmpeg

logger = logging.getLogger(__name__)
VIDEO_DIR = Path(__file__).resolve().parents[1] / "data" / "learning-videos"
_worker = None


class VideoJobStore:
    def create(self, user_id: str, payload: dict) -> dict:
        job_id = uuid.uuid4().hex
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"video:{user_id}",))
            cur.execute("SELECT COUNT(*) AS count FROM a12_learning_video_job WHERE user_id=%s AND status IN ('queued','running')", (user_id,))
            if cur.fetchone()["count"] >= 3:
                raise ValueError("最多同时提交3个视频任务，请等待已有任务完成")
            cur.execute("""INSERT INTO a12_learning_video_job(job_id,user_id,title,payload)
                VALUES (%s,%s,%s,%s::jsonb) RETURNING job_id,title,status,progress,created_at""",
                (job_id, user_id, payload["title"], json.dumps(payload, ensure_ascii=False)))
            return dict(cur.fetchone())

    def list(self, user_id: str) -> list[dict]:
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT job_id,title,status,progress,error,attempts,created_at,updated_at,
                expires_at,metadata FROM a12_learning_video_job WHERE user_id=%s ORDER BY created_at DESC LIMIT 50""", (user_id,))
            return [dict(row) for row in cur.fetchall()]

    def get(self, user_id: str, job_id: str) -> dict | None:
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM a12_learning_video_job WHERE user_id=%s AND job_id=%s", (user_id, job_id))
            row = cur.fetchone()
        return dict(row) if row else None

    def cancel(self, user_id: str, job_id: str) -> bool:
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE a12_learning_video_job SET status='cancelled',updated_at=NOW()
                WHERE user_id=%s AND job_id=%s AND status IN ('queued','running')""", (user_id, job_id))
            return cur.rowcount > 0

    def retry(self, user_id: str, job_id: str) -> bool:
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"video:{user_id}",))
            cur.execute("SELECT COUNT(*) AS count FROM a12_learning_video_job WHERE user_id=%s AND status IN ('queued','running')", (user_id,))
            if cur.fetchone()["count"] >= 3:
                return False
            cur.execute("""UPDATE a12_learning_video_job SET status='queued',progress=0,error='',updated_at=NOW()
                WHERE user_id=%s AND job_id=%s AND status='failed' AND attempts<2""", (user_id, job_id))
            return cur.rowcount > 0

    def claim(self) -> dict | None:
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            # 崩溃任务最多重新执行一次，持续运行任务由页级心跳保护。
            cur.execute("""UPDATE a12_learning_video_job SET status=CASE WHEN attempts<2 THEN 'queued' ELSE 'failed' END,
                error='任务中断，已触发有限恢复',updated_at=NOW() WHERE status='running' AND updated_at<NOW()-INTERVAL '10 minutes'""")
            cur.execute("""SELECT * FROM a12_learning_video_job WHERE status='queued' AND attempts<2
                ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""")
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("""UPDATE a12_learning_video_job SET status='running',attempts=attempts+1,
                lease_id=%s,updated_at=NOW() WHERE job_id=%s RETURNING *""", (uuid.uuid4().hex, row["job_id"]))
            claimed = cur.fetchone()
        return dict(claimed)

    def update(self, job_id: str, progress: int, *, error: str | None = None, metadata: dict | None = None, lease_id: str | None = None):
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE a12_learning_video_job SET progress=%s,
                status=CASE WHEN %s::text IS NOT NULL THEN 'failed' WHEN %s=100 THEN 'ready' ELSE status END,
                error=COALESCE(%s,error),metadata=COALESCE(%s::jsonb,metadata),updated_at=NOW(),
                expires_at=CASE WHEN %s=100 THEN NOW()+INTERVAL '24 hours' ELSE expires_at END
                WHERE job_id=%s AND status='running' AND lease_id=%s""", (progress, error, progress, error,
                json.dumps(metadata) if metadata is not None else None, progress, job_id, lease_id))
            if not cur.rowcount:
                raise asyncio.CancelledError("任务已取消或失去处理权")

    def cleanup_expired(self):
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT job_id FROM a12_learning_video_job WHERE expires_at<NOW() AND payload<>'{}'::jsonb LIMIT 100")
            for row in cur.fetchall():
                if re.fullmatch(r"[a-f0-9]{32}", row["job_id"]):
                    output = VIDEO_DIR / (row["job_id"] + ".mp4")
                    if output.resolve().parent == VIDEO_DIR.resolve():
                        output.unlink(missing_ok=True)
                cur.execute("UPDATE a12_learning_video_job SET payload='{}'::jsonb WHERE job_id=%s", (row["job_id"],))


video_job_store = VideoJobStore()


def _run_ffmpeg(args: list[str], timeout=180) -> None:
    result = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError("视频编码失败，请检查 ffmpeg 与输入音频")


async def render_learning_video(payload: dict, output: Path, progress) -> dict:
    if sys.platform == "win32" and not isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop):
        return await asyncio.to_thread(_render_isolated, payload, output, progress)
    ffmpeg = _find_ffmpeg()
    settings = get_settings()
    if not ffmpeg:
        raise RuntimeError("未检测到ffmpeg，请安装视频编码运行环境")
    tts_key = os.getenv("TTS_API_KEY") or settings.openai_api_key
    tts_url = os.getenv("TTS_BASE_URL") or settings.openai_base_url
    if not tts_key:
        raise RuntimeError("TTS服务未配置，请设置模型API密钥")
    from openai import AsyncOpenAI
    from playwright.async_api import async_playwright
    client = AsyncOpenAI(api_key=tts_key, base_url=tts_url.rstrip("/"),
                         timeout=settings.request_timeout_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    slides = payload["slides"]
    with tempfile.TemporaryDirectory(prefix="a12-learning-video-") as directory:
        work = Path(directory)
        clips = []
        async with client, async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 1280, "height": 720}, java_script_enabled=False)
                # 离线截图不允许模型HTML访问内网、用户主机或远程脚本。
                await page.route("**/*", lambda route: route.abort())
                for index, slide in enumerate(slides):
                    await progress(round(index / len(slides) * 90))
                    image, audio, clip = work / f"{index}.png", work / f"{index}.mp3", work / f"{index}.mp4"
                    await page.set_content(slide["html"], wait_until="domcontentloaded")
                    await page.evaluate("document.fonts.ready")
                    await page.screenshot(path=str(image))
                    speech = await client.audio.speech.create(model=settings.tts_model,
                        voice=payload.get("voice") or settings.tts_voice, input=slide["narration"], response_format="mp3")
                    audio.write_bytes(speech.content)
                    await asyncio.to_thread(_run_ffmpeg, [ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(image),
                        "-i", str(audio), "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                        "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", "-r", "12", str(clip)])
                    clips.append(clip)
            finally:
                await browser.close()
        manifest = work / "clips.txt"
        manifest.write_text("\n".join(f"file '{clip.name}'" for clip in clips), encoding="utf-8")
        await progress(95)
        await asyncio.to_thread(_run_ffmpeg, [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "1",
            "-i", str(manifest), "-c", "copy", "-movflags", "+faststart", str(output)])
    return {"page_count": len(slides), "resolution": "1280x720", "render_mode": "static_slides_with_tts",
            "course_id": payload.get("course_id"), "course_version": payload.get("course_version"),
            "file_size": output.stat().st_size}


def _render_isolated(payload, output, progress):
    loop = asyncio.ProactorEventLoop()
    try:
        return loop.run_until_complete(render_learning_video(payload, output, progress))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def _video_worker():
    cleanup_counter = 0
    while True:
        job = None
        try:
            job = await asyncio.to_thread(video_job_store.claim)
            if cleanup_counter % 100 == 0:
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(video_job_store.cleanup_expired)
            cleanup_counter += 1
            if job:
                async def progress(value):
                    await asyncio.to_thread(video_job_store.update, job["job_id"], value, lease_id=job["lease_id"])
                output = VIDEO_DIR / (job["job_id"] + ".mp4")
                metadata = await render_learning_video(job["payload"], output, progress)
                await asyncio.to_thread(video_job_store.update, job["job_id"], 100, metadata=metadata, lease_id=job["lease_id"])
        except asyncio.CancelledError:
            # 用户取消单个任务不退出全局消费者；进程关闭则停止。
            if asyncio.current_task().cancelling():
                raise
        except Exception as exc:
            logger.warning("学习视频任务失败: %s", type(exc).__name__)
            if job:
                with contextlib.suppress(Exception, asyncio.CancelledError):
                    await asyncio.to_thread(video_job_store.update, job["job_id"], 0,
                        error=str(exc)[:200] if isinstance(exc, RuntimeError) else "视频生成失败，请检查TTS或浏览器运行环境", lease_id=job["lease_id"])
        await asyncio.sleep(3)


def start_video_worker():
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_video_worker())


async def stop_video_worker():
    if _worker:
        _worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _worker
