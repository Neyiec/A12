from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
import json
import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from a12_ppt.config import get_settings
from a12_ppt.direct_auth import (authenticate_browser, direct_bearer, direct_user_id, direct_user_role,
                                 internal_request_allowed, reject_identity_spoofing,
                                 signed_personal_resource_url, signed_public_resource_url,
                                 verify_active_token, require_active_browser_token)
from a12_ppt.workspace import WorkspaceChatRequest, stream_workspace_chat
from a12_ppt.chat_router import ChatRouteRequest, chat_route_workflow
from a12_ppt.asr import transcribe_audio
from a12_ppt.interactive import InteractiveModuleGenerator
from a12_ppt.lesson_plan import LessonPlanGenerator, export_lesson_plan_to_docx
from a12_ppt.presentation import (
    DEFAULT_THEME,
    PPTGenerator,
    create_template,
    delete_template,
    export_html_slides_to_pptx,
    get_template_file,
    list_templates,
    replace_template,
    set_template_status,
    validate_html,
)
from a12_ppt.models import (
    HtmlValidateRequest,
    IntentRecognizeRequest,
    InteractiveModuleGenerateRequest,
    LessonPlanExportRequest,
    LessonPlanGenerateRequest,
    OutlineChatSessionCreateRequest,
    OutlineChatSessionUpdateRequest,
    OutlineChatStreamRequest,
    OutlineGenerateRequest,
    OutlineUpdateRequest,
    PresentationExportRequest,
    PresentationGenerateRequest,
    PresentationModifyRequest,
    ResourceIndexBootstrapRequest,
    ResourceIndexMetadataRequest,
    ResourceIndexSearchRequest,
    ResourceIndexSyncRequest,
    Result,
    SlideModifyRequest,
    TemplateMutationRequest,
    TeacherFeedbackRequest,
    TextToSpeechRequest,
    ClassroomEventRequest,
    CourseGraphUpsertRequest,
)
from a12_ppt.course_graph import course_graph_store
from a12_ppt.resources import resource_index_store, save_upload
from a12_ppt.resources.index_worker import start_resource_index_worker
from a12_ppt.outline_chat import OutlineChatWorkflow
from a12_ppt.outline_chat.postgres_store import postgres_memory_store
from a12_ppt.outline_chat.session_store import outline_session_store
from a12_ppt.database import ensure_ai_schema
from a12_ppt.ai_runtime import probe_model, use_runtime_options


settings = get_settings()

# 统一日志约定：[%(levelname)s] %(filename)s: %(message)s
# 服务内模块（index_store 等）的 logger 依赖 root 处理器输出，uvicorn 不配置 root，必须在此 basicConfig
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(filename)s: %(message)s")

app = FastAPI(title=settings.app_name, version=settings.app_version)
generator = PPTGenerator()
interactive_generator = InteractiveModuleGenerator()
lesson_plan_generator = LessonPlanGenerator()
outline_chat_workflow = OutlineChatWorkflow(generator)


@app.middleware("http")
async def authorize_python_api(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/python/") or request.method == "OPTIONS":
        return await call_next(request)
    if internal_request_allowed(request.headers.get("X-A12-Internal-Key")):
        return await call_next(request)
    try:
        identity = await authenticate_browser(request.headers.get("Authorization"))
        user_id, token = identity[:2]
        await verify_active_token(user_id, token)
        role = identity[2] if len(identity) > 2 else ""
        admin_template = (request.url.path.startswith("/api/v1/python/templates/") or
                          (request.url.path == "/api/v1/python/templates" and request.method != "GET"))
        if admin_template and role != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可管理模板")
        if request.headers.get("Content-Type", "").split(";", 1)[0].lower() == "application/json":
            if role != "admin" or not request.url.path.startswith("/api/v1/python/resources/index/"):
                reject_identity_spoofing(await request.body(), dict(request.query_params), user_id)
        else:
            reject_identity_spoofing(b"", dict(request.query_params), user_id)
    except HTTPException as exc:
        return Response(content=json.dumps({"code": exc.status_code, "message": exc.detail, "data": None},
                                           ensure_ascii=False), status_code=exc.status_code,
                        media_type="application/json")
    user_scope = direct_user_id.set(user_id)
    token_scope = direct_bearer.set(token)
    role_scope = direct_user_role.set(role)
    try:
        return await call_next(request)
    finally:
        direct_user_id.reset(user_scope)
        direct_bearer.reset(token_scope)
        direct_user_role.reset(role_scope)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "A12_FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
async def initialize_ai_database() -> None:
    ensure_ai_schema()
    start_resource_index_worker()


@app.post("/api/v1/python/workspace/chat/stream")
async def workspace_chat(request: WorkspaceChatRequest):
    return StreamingResponse(stream_workspace_chat(request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/v1/python/workspace/chat/route")
async def route_workspace_chat(request: ChatRouteRequest) -> Result:
    with use_runtime_options(request.user_id, "chat_route", "fast", "low"):
        return Result(data=await chat_route_workflow.route(request))


@app.get("/api/v1/python/health")
async def health(probe: bool = Query(default=False)) -> Result:
    model_status = await probe_model() if probe else {
        "configured": bool(settings.openai_api_key),
        "available": None,
        "status": "not_probed",
        "model": settings.openai_model,
    }
    return Result(data={
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "model_ready": bool(model_status.get("available")) if probe else bool(settings.openai_api_key),
        "model_status": model_status,
        "embedding_ready": bool(settings.embedding_api_key),
        "embedding_model": settings.embedding_model,
        "asr_model": settings.asr_model,
        "quality_pipeline": settings.enable_quality_pipeline,
        "quality_preset": settings.quality_preset,
        "max_slide_concurrency": settings.max_slide_concurrency,
        "max_html_retries": settings.max_html_retries,
    })


@app.post("/api/v1/python/audio/asr")
async def transcribe_audio_input(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> Result:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp_path = Path(temp.name)
        temp.write(await file.read())
    try:
        result = await transcribe_audio(temp_path, language)
        result.update({
            "filename": file.filename,
            "content_type": file.content_type or "",
        })
        return Result(data=result)
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/api/v1/python/resources/upload")
async def upload_resource(file: UploadFile = File(...)) -> Result:
    record = await save_upload(file)
    return Result(data={
        "resource_id": record.resource_id,
        "filename": record.filename,
        "content_type": record.content_type,
        "text_length": len(record.text),
        "text_preview": record.text[:500],
    })


@app.post("/api/v1/python/resources/index/sync")
async def sync_resource_index(request: ResourceIndexSyncRequest) -> Result:
    if direct_user_id.get():
        if request.source_type == "public":
            if direct_user_role.get() != "admin":
                raise HTTPException(status_code=403, detail="仅管理员可维护公共资源索引")
            request.file_url = await signed_public_resource_url(request.resource_id)
        else:
            request.file_url = await signed_personal_resource_url(request.resource_id)
            request.owner_user_id = direct_user_id.get()
            request.uploaded_by = direct_user_id.get()
            request.metadata["owner_user_id"] = direct_user_id.get()
        request.metadata["file_url"] = request.file_url
    return Result(data=await resource_index_store.sync_resource(request))


@app.post("/api/v1/python/resources/index/bootstrap")
async def bootstrap_resource_index(request: ResourceIndexBootstrapRequest) -> Result:
    if direct_user_id.get():
        for resource in request.resources:
            if resource.source_type == "public":
                if direct_user_role.get() != "admin":
                    raise HTTPException(status_code=403, detail="仅管理员可维护公共资源索引")
                resource.file_url = await signed_public_resource_url(resource.resource_id)
            else:
                resource.file_url = await signed_personal_resource_url(resource.resource_id)
                resource.owner_user_id = direct_user_id.get()
                resource.uploaded_by = direct_user_id.get()
                resource.metadata["owner_user_id"] = direct_user_id.get()
            resource.metadata["file_url"] = resource.file_url
    return Result(data=await resource_index_store.bootstrap(request.resources, request.force_reparse))


@app.patch("/api/v1/python/resources/index/metadata")
async def update_resource_index_metadata(request: ResourceIndexMetadataRequest) -> Result:
    if direct_user_id.get():
        if request.source_type == "public":
            if direct_user_role.get() != "admin":
                raise HTTPException(status_code=403, detail="仅管理员可维护公共资源索引")
            await signed_public_resource_url(request.resource_id)
        else:
            if not resource_index_store.get_resource(request.source_type, request.resource_id, 0):
                raise HTTPException(status_code=403, detail="无权修改该资源索引")
            await signed_personal_resource_url(request.resource_id)
            request.metadata.pop("owner_user_id", None)
    return Result(data=resource_index_store.update_metadata(request))


@app.get("/api/v1/python/resources/index/overview")
async def resource_index_overview() -> Result:
    return Result(data=resource_index_store.overview())


@app.get("/api/v1/python/resources/index/resources")
async def list_resource_index_resources(
    source_type: str | None = Query(default=None),
    available: bool | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    parse_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> Result:
    return Result(data=resource_index_store.list_resources(source_type, available, limit, offset, parse_status, keyword))


@app.get("/api/v1/python/resources/index/resources/{source_type}/{resource_id}")
async def get_resource_index_resource(
    source_type: str,
    resource_id: str,
    chunk_limit: int = Query(20, ge=0, le=200),
) -> Result:
    resource = resource_index_store.get_resource(source_type, resource_id, chunk_limit)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource index not found")
    return Result(data=resource)


@app.get("/api/v1/python/resources/index/logs")
async def list_resource_index_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Result:
    return Result(data=resource_index_store.list_retrieval_logs(limit, offset))


@app.post("/api/v1/python/resources/index/search")
async def search_resource_index(request: ResourceIndexSearchRequest) -> Result:
    return Result(data=await resource_index_store.search_context(
        request.resource_ids,
        request.query,
        request.limit,
        request.top_k,
        request.source_type,
        request.min_score,
    ))


@app.delete("/api/v1/python/resources/index/{source_type}/{resource_id}")
async def delete_resource_index(source_type: str, resource_id: str) -> Result:
    if direct_user_id.get():
        if source_type == "public":
            if direct_user_role.get() != "admin":
                raise HTTPException(status_code=403, detail="仅管理员可维护公共资源索引")
        else:
            if not resource_index_store.get_resource(source_type, resource_id, 0):
                raise HTTPException(status_code=403, detail="无权删除该资源索引")
    return Result(data=resource_index_store.delete_resource(source_type, resource_id))


@app.get("/api/v1/python/templates")
async def templates() -> Result:
    templates_data = list_templates()
    return Result(data={
        "total": len(templates_data),
        "default_theme": DEFAULT_THEME,
        "templates": templates_data,
    })


@app.post("/api/v1/python/templates")
async def create_ppt_template(request: TemplateMutationRequest) -> Result:
    """管理后台创建 PPT 模板：template_data 必须是含 html_template 的模板 JSON 文本"""
    try:
        return Result(data=create_template(request.name, request.template_data, request.description))
    except ValueError as exc:
        return Result(code=400, message=str(exc))


@app.patch("/api/v1/python/templates/{theme}")
async def replace_ppt_template(theme: str, request: TemplateMutationRequest) -> Result:
    """管理后台替换 PPT 模板内容（覆盖原 JSON 文件）"""
    try:
        return Result(data=replace_template(theme, request.template_data, request.description))
    except ValueError as exc:
        return Result(code=400, message=str(exc))


@app.delete("/api/v1/python/templates/{theme}")
async def delete_ppt_template(theme: str) -> Result:
    """管理后台删除 PPT 模板（默认模板受保护）"""
    try:
        return Result(data=delete_template(theme))
    except ValueError as exc:
        return Result(code=400, message=str(exc))


@app.put("/api/v1/python/templates/{theme}/status")
async def update_ppt_template_status(theme: str, status: str = Query(...)) -> Result:
    try:
        return Result(data=set_template_status(theme, status))
    except ValueError as exc:
        return Result(code=400, message=str(exc))


@app.get("/api/v1/python/templates/{theme}/file")
async def download_ppt_template_file(theme: str):
    """管理后台下载模板 JSON 文件，业务错误以非 2xx 返回（调用方按字节流处理）"""
    try:
        path = get_template_file(theme)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    filename = quote(path.name)
    return Response(
        content=path.read_bytes(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.post("/api/v1/python/outlines/generate")
async def generate_outline(request: OutlineGenerateRequest) -> Result:
    with use_runtime_options(direct_user_id.get(), "outline_generate", request.model_profile, request.reasoning_effort):
        return Result(data=await generator.generate_outline(request))


@app.post("/api/v1/python/intent/recognize")
async def recognize_intent(request: IntentRecognizeRequest) -> Result:
    return Result(data=await outline_chat_workflow.recognize_intent(request))


@app.post("/api/v1/python/outlines/chat/stream")
async def stream_outline_chat(request: OutlineChatStreamRequest):
    async def event_source():
        with use_runtime_options(request.user_id, "outline_chat", request.model_profile, request.reasoning_effort):
            async for item in outline_chat_workflow.stream(request):
                event = item.get("event", "message")
                data = json.dumps(item.get("data", {}), ensure_ascii=False)
                yield f"event: {event}\ndata: {data}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/api/v1/python/outlines/chat/sessions")
async def list_outline_chat_sessions(user_id: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)) -> Result:
    return Result(data={
        "user_id": user_id,
        "sessions": outline_session_store.list_sessions(user_id, limit=limit),
    })


@app.post("/api/v1/python/outlines/chat/sessions")
async def create_outline_chat_session(request: OutlineChatSessionCreateRequest) -> Result:
    session = outline_session_store.create(request.user_id.strip(), request.title.strip() if request.title else None)
    return Result(data=session)


@app.get("/api/v1/python/outlines/chat/sessions/{session_id}")
async def get_outline_chat_session(session_id: str, user_id: str = Query(..., min_length=1)) -> Result:
    session = outline_session_store.get(user_id.strip(), session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outline chat session not found")
    return Result(data=session)


@app.patch("/api/v1/python/outlines/chat/sessions/{session_id}")
async def update_outline_chat_session(session_id: str, request: OutlineChatSessionUpdateRequest, user_id: str = Query(..., min_length=1)) -> Result:
    session = outline_session_store.update_title(user_id.strip(), session_id, request.title.strip())
    if not session:
        raise HTTPException(status_code=404, detail="Outline chat session not found")
    return Result(data=session)


@app.delete("/api/v1/python/outlines/chat/sessions/{session_id}")
async def delete_outline_chat_session(session_id: str, user_id: str = Query(..., min_length=1)) -> Result:
    deleted = outline_session_store.delete(user_id.strip(), session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Outline chat session not found")
    return Result(data={"user_id": user_id, "session_id": session_id, "deleted": True})


@app.get("/api/v1/python/teacher-style/profile")
async def get_teacher_style_profile(user_id: str = Query(..., min_length=1)) -> Result:
    return Result(data={
        "user_id": user_id,
        "profile": postgres_memory_store.get_teacher_profile(user_id),
        "postgres_available": postgres_memory_store.available,
    })


@app.put("/api/v1/python/courses/graph")
async def upsert_course_graph(request: CourseGraphUpsertRequest) -> Result:
    try:
        return Result(data=course_graph_store.put(request.user_id, request.course_id, request.title, request.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/python/courses/{course_id}/graph")
async def get_course_graph(course_id: str, user_id: str = Query(..., min_length=1)) -> Result:
    graph = course_graph_store.get(user_id, course_id)
    if not graph:
        raise HTTPException(status_code=404, detail="课程图谱不存在")
    return Result(data=graph)


@app.post("/api/v1/python/teacher-style/feedback")
async def record_teacher_feedback(request: TeacherFeedbackRequest) -> Result:
    return Result(data=postgres_memory_store.record_feedback(request.model_dump()))


@app.get("/api/v1/python/ai/metrics")
async def ai_metrics(limit: int = Query(50, ge=1, le=500)) -> Result:
    return Result(data=postgres_memory_store.ai_metrics(limit, direct_user_id.get()))


@app.post("/api/v1/python/classroom/events")
async def record_classroom_event(request: ClassroomEventRequest) -> Result:
    return Result(data={"stored": postgres_memory_store.record_classroom_event(request.model_dump())})


@app.get("/api/v1/python/classroom/insights/{project_id}")
async def classroom_insights(project_id: str, user_id: str = Query(..., min_length=1)) -> Result:
    return Result(data=postgres_memory_store.classroom_insights(user_id, project_id))


@app.post("/api/v1/python/outlines/update")
async def update_outline(request: OutlineUpdateRequest) -> Result:
    return Result(data=await generator.update_outline(request))


@app.post("/api/v1/python/presentations/generate")
async def generate_presentation(request: PresentationGenerateRequest) -> Result:
    with use_runtime_options(direct_user_id.get(), "presentation_generate", request.model_profile, request.reasoning_effort):
        return Result(data=await generator.generate_presentation(request))


@app.post("/api/v1/python/presentations/generate/stream")
async def stream_presentation(request: PresentationGenerateRequest):
    async def event_source():
        try:
            with use_runtime_options(direct_user_id.get(), "presentation_stream", request.model_profile, request.reasoning_effort):
                async for item in generator.stream_presentation(request):
                    event = "presentation_slide" if item.get("type") == "slide" else "final"
                    payload = item.get("response") if event == "final" else item
                    yield f"event: {event}\ndata: {json.dumps(payload or {}, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {\"status\":\"completed\"}\n\n"
        except Exception as exc:
            payload = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/api/v1/python/presentations/slides/modify")
async def modify_slide(request: SlideModifyRequest) -> Result:
    return Result(data=await generator.modify_slide(request))


@app.post("/api/v1/python/presentations/modify")
async def modify_presentation(request: PresentationModifyRequest) -> Result:
    return Result(data=await generator.modify_presentation(request))


@app.post("/api/v1/python/presentations/html/validate")
async def validate_ppt_html(request: HtmlValidateRequest) -> Result:
    return Result(data=validate_html(request.html, request.strict))


@app.post("/api/v1/python/presentations/export/pptx")
async def export_pptx(request: PresentationExportRequest):
    output = await export_html_slides_to_pptx(request.title, request.slides, request.filename, request.fidelity, request.package_static_assets)
    media_type = "application/zip" if output.suffix.lower() == ".zip" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    return FileResponse(
        path=str(output),
        filename=output.name,
        media_type=media_type,
    )


@app.post("/api/v1/python/interactive-modules/generate")
async def generate_interactive_module(request: InteractiveModuleGenerateRequest) -> Result:
    return Result(data=await interactive_generator.generate(request))


@app.post("/api/v1/python/lesson-plans/generate")
async def generate_lesson_plan(request: LessonPlanGenerateRequest) -> Result:
    return Result(data=await lesson_plan_generator.generate(request))


@app.post("/api/v1/python/audio/tts")
async def synthesize_speech(request: TextToSpeechRequest):
    from openai import AsyncOpenAI
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="TTS 服务未配置")
    await require_active_browser_token()
    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url.rstrip("/"),
                         timeout=settings.request_timeout_seconds)
    speech = await client.audio.speech.create(model=settings.tts_model,
                                              voice=request.voice or settings.tts_voice, input=request.text)
    return Response(content=speech.content, media_type="audio/mpeg")


@app.post("/api/v1/python/lesson-plans/export/docx")
async def export_lesson_plan_docx(request: LessonPlanExportRequest):
    output = export_lesson_plan_to_docx(request.title, request.lesson_plan, request.filename)
    return FileResponse(
        path=str(output),
        filename=output.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def main() -> None:
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)


if __name__ == "__main__":
    main()
