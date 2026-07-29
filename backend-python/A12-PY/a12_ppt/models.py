from typing import Any, Literal
from pydantic import BaseModel, Field


class Result(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


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


class PresentationExportRequest(BaseModel):
    title: str = "A12 PPT"
    slides: list[dict[str, Any]]
    filename: str | None = None


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
