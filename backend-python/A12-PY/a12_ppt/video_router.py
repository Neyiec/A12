from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .models import Result
from .course_router import current_teacher
from .learning_video import VIDEO_DIR, video_job_store


class VideoSlide(BaseModel):
    html: str = Field(min_length=1, max_length=200000)
    narration: str = Field(min_length=1, max_length=600)


class LearningVideoRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    course_id: str | None = Field(default=None, max_length=80)
    course_version: int | None = Field(default=None, ge=1)
    # 24个路径节点外，保留封面与总结两页。
    slides: list[VideoSlide] = Field(min_length=1, max_length=26)
    voice: str | None = Field(default=None, max_length=80)


router = APIRouter(prefix="/api/v1/python/learning-videos", tags=["学习视频导出"])


@router.post("")
async def create_video(request: LearningVideoRequest):
    if sum(len(slide.html) for slide in request.slides) > 2_000_000:
        raise HTTPException(413, "视频页面总量超过2MB，请减少页面或压缩内嵌图片")
    try:
        return Result(data=video_job_store.create(current_teacher(), request.model_dump()))
    except ValueError as exc:
        raise HTTPException(429, str(exc)) from exc


@router.get("")
async def list_videos():
    return Result(data=video_job_store.list(current_teacher()))


@router.post("/{job_id}/cancel")
async def cancel_video(job_id: str):
    if not video_job_store.cancel(current_teacher(), job_id):
        raise HTTPException(409, "任务不存在或不能取消")
    return Result(data={"cancelled": True})


@router.post("/{job_id}/retry")
async def retry_video(job_id: str):
    if not video_job_store.retry(current_teacher(), job_id):
        raise HTTPException(409, "任务不存在、尚未失败或已达到两次尝试上限")
    return Result(data={"queued": True})


@router.get("/{job_id}/download")
async def download_video(job_id: str):
    job = video_job_store.get(current_teacher(), job_id)
    if not job:
        raise HTTPException(404, "视频任务不存在")
    if job["status"] != "ready":
        raise HTTPException(409, "视频尚未生成完成")
    if not job.get("expires_at") or job["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(410, "视频下载已过期，请重新生成")
    output = VIDEO_DIR / (job["job_id"] + ".mp4")
    if not output.is_file():
        raise HTTPException(410, "视频文件已不可用，请重新生成")
    return FileResponse(output, media_type="video/mp4", filename="学习视频.mp4")
