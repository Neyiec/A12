from typing import Any, Literal
from pydantic import BaseModel, Field


class Result(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


class TemplateMutationRequest(BaseModel):
    """管理后台 PPT 模板创建/替换请求：template_data 为模板 JSON 文件的文本内容"""
    name: str | None = None
    template_data: str | None = None
    description: str | None = None


class OutlineGenerateRequest(BaseModel):
    session_id: int | None = None
    title: str
    subject: str
    grade: str
    duration_minutes: int | None = None
    teaching_goals: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    requirements: str | None = None
    reference_text: str | None = None
    resource_ids: list[str] = Field(default_factory=list)
    enable_web: bool = False
    enable_rag: bool = False
    slide_count: int | None = Field(default=8, ge=1, le=30)
    language: str = "zh-CN"
    regenerate_instruction: str | None = None
    interactive_policy: dict[str, Any] = Field(default_factory=dict)


class PresentationGenerateRequest(BaseModel):
    session_id: int | None = None
    outline_id: str | None = None
    title: str
    outline: dict[str, Any]
    theme: str | None = None
    aspect_ratio: Literal["16:9", "4:3"] = "16:9"
    language: str = "zh-CN"
    asset_policy: Literal["none", "placeholder", "generate"] = "placeholder"


class SlideModifyRequest(BaseModel):
    presentation_id: str | None = None
    slide_no: int = Field(ge=1)
    current_html: str
    instruction: str
    outline_context: dict[str, Any] | None = None
    theme: str | None = None
    keep_style: bool = True


class PresentationModifyRequest(BaseModel):
    presentation_id: str | None = None
    title: str = "A12 PPT"
    slides: list[dict[str, Any]]
    instruction: str
    outline: dict[str, Any] | None = None
    theme: str | None = None
    keep_style: bool = True
    max_modified_slides: int | None = Field(default=None, ge=1, le=30)


class HtmlValidateRequest(BaseModel):
    html: str
    strict: bool = False


class OutlineUpdateRequest(BaseModel):
    outline: dict[str, Any]
    instruction: str
    resource_ids: list[str] = Field(default_factory=list)
    enable_web: bool = False
    enable_rag: bool = False


class OutlineChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class OutlineChatStreamRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str | None = None
    message: str
    history: list[OutlineChatMessage] = Field(default_factory=list)
    known_context: dict[str, Any] = Field(default_factory=dict)
    resource_ids: list[str] = Field(default_factory=list)
    enable_web: bool = False
    enable_rag: bool = False
    slide_count: int | None = Field(default=8, ge=1, le=30)
    language: str = "zh-CN"


class IntentRecognizeRequest(BaseModel):
    user_id: str | None = None
    session_id: str | None = None
    title: str | None = None
    message: str = Field(..., min_length=1)
    history: list[OutlineChatMessage] = Field(default_factory=list)
    known_context: dict[str, Any] = Field(default_factory=dict)
    resource_ids: list[str] = Field(default_factory=list)
    enable_web: bool = False
    enable_rag: bool = False
    slide_count: int | None = Field(default=8, ge=1, le=30)
    language: str = "zh-CN"
    input_type: Literal["text", "audio"] = "text"


class OutlineChatSessionCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    title: str | None = None


class OutlineChatSessionUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class PresentationExportRequest(BaseModel):
    title: str = "A12 PPT"
    slides: list[dict[str, Any]]
    filename: str | None = None
    fidelity: Literal["high_fidelity", "editable_text"] = "high_fidelity"
    package_static_assets: bool = True


class LessonPlanGenerateRequest(BaseModel):
    title: str
    subject: str | None = None
    grade: str | None = None
    duration_minutes: int | None = None
    teaching_goals: str | None = None
    outline: dict[str, Any] = Field(default_factory=dict)
    slides: list[dict[str, Any]] = Field(default_factory=list)
    requirements: str | None = None
    reference_text: str | None = None
    language: str = "zh-CN"


class LessonPlanExportRequest(BaseModel):
    title: str = "A12 教案"
    lesson_plan: dict[str, Any]
    filename: str | None = None


class InteractiveModuleGenerateRequest(BaseModel):
    title: str
    topic: str
    module_type: Literal["animation", "quiz_game", "matching_game", "timeline_game", "simulation"] = "animation"
    subject: str | None = None
    grade: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    requirements: str | None = None
    theme: str | None = None
    embed_mode: Literal["standalone", "slide_fragment"] = "standalone"
    language: str = "zh-CN"


class ResourceIndexSyncRequest(BaseModel):
    source_type: Literal["public", "personal"]
    resource_id: str = Field(..., min_length=1)
    title: str
    file_url: str
    file_type: str | None = None
    file_size: int | None = None
    uploaded_by: str | None = None
    owner_user_id: str | None = None
    available: bool = True
    allow_ai: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    force_reparse: bool = False


class ResourceIndexBootstrapRequest(BaseModel):
    resources: list[ResourceIndexSyncRequest] = Field(default_factory=list)
    force_reparse: bool = False


class ResourceIndexMetadataRequest(BaseModel):
    source_type: Literal["public", "personal"]
    resource_id: str = Field(..., min_length=1)
    available: bool | None = None
    allow_ai: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceIndexSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    resource_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=12000, ge=1000, le=30000)
    top_k: int = Field(default=8, ge=1, le=30)
    source_type: Literal["public", "personal"] | None = None
