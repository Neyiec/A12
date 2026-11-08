from typing import Any, Literal
from pydantic import BaseModel, Field, PrivateAttr, model_validator


class SlideCountRange(BaseModel):
    min_pages: int = Field(ge=1, le=30)
    max_pages: int = Field(ge=1, le=30)

    @model_validator(mode="after")
    def ordered(self):
        if self.min_pages > self.max_pages:
            raise ValueError("最少页数不能大于最多页数")
        return self


class Result(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


class TeacherStyleConfigRequest(BaseModel):
    enabled: bool


class TeacherStyleTagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=8)


class TemplateMutationRequest(BaseModel):
    """管理后台 PPT 模板创建/替换请求：template_data 为模板 JSON 文件的文本内容"""
    name: str | None = None
    template_data: str | None = None
    description: str | None = None


class OutlineGenerateRequest(BaseModel):
    _references_prepared: bool = PrivateAttr(default=False)
    _retrieval_citations: dict[str, Any] = PrivateAttr(default_factory=dict)
    slide_count_range: SlideCountRange | None = None
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
    model_profile: Literal["fast", "standard", "deep"] = "standard"
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
    classroom_insights: dict[str, Any] = Field(default_factory=dict)
    teaching_model: Literal["boppps", "general"] = "boppps"
    teaching_style: str | None = None
    teacher_profile: dict[str, Any] = Field(default_factory=dict)


class PresentationGenerateRequest(BaseModel):
    stream_compact: bool = False  # 流式客户端可选：最终事件不重复已发送的页面HTML。
    session_id: int | None = None
    outline_id: str | None = None
    title: str
    outline: dict[str, Any]
    resource_ids: list[str] = Field(default_factory=list)
    enable_rag: bool = False
    theme: str | None = None
    aspect_ratio: Literal["16:9", "4:3"] = "16:9"
    language: str = "zh-CN"
    # auto 会根据用户要求、学科和逐页内容在 none / placeholder / generate 间选择。
    asset_policy: Literal["auto", "none", "placeholder", "generate"] = "auto"
    model_profile: Literal["fast", "standard", "deep"] = "standard"
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
    teaching_model: Literal["boppps", "general"] | None = None
    teaching_style: str | None = None


class SlideImageGenerateRequest(BaseModel):
    lesson_title: str = Field(min_length=1, max_length=160)
    slide_title: str = Field(min_length=1, max_length=160)
    subject: str = Field(default="通用", max_length=80)
    grade: str = Field(default="", max_length=80)
    visual_suggestion: str = Field(default="", max_length=600)
    aspect_ratio: Literal["16:9", "4:3"] = "16:9"


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
    slide_count_range: SlideCountRange | None = None
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
    model_profile: Literal["fast", "standard", "deep"] = "standard"
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
    teaching_model: Literal["boppps", "general"] = "boppps"
    teaching_style: str | None = None
    confirm_learning_graphs: bool = False


class IntentRecognizeRequest(BaseModel):
    slide_count_range: SlideCountRange | None = None
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


class SkillGraphUpdateRequest(BaseModel):
    skill: dict[str, Any]


class TeacherPreferencesRequest(BaseModel):
    teaching_style: Literal["", "heuristic", "lecture", "cooperative", "project_based", "blended"] = ""
    template_style: Literal["", "business", "academic", "lively", "tech"] = ""
    interaction_forms: list[Literal["random_call", "group_discussion", "quiz", "poll", "bullet_chat", "raise_hand"]] = Field(default_factory=list, max_length=6)


class LearningGraphUpdateRequest(BaseModel):
    graphs: dict[str, Any]


class LearningGraphAIEditRequest(LearningGraphUpdateRequest):
    instruction: str = Field(..., min_length=1, max_length=2000)
    kind: Literal["knowledge", "skill"]


class PresentationExportRequest(BaseModel):
    title: str = "A12 PPT"
    slides: list[dict[str, Any]]
    filename: str | None = None
    fidelity: Literal["dom_editable", "high_fidelity", "editable_text"] = "dom_editable"
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
    teaching_model: Literal["boppps", "general"] | None = None
    teaching_style: str | None = None


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
    source_type: Literal["public", "personal", "community", "temp"]
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
    source_type: Literal["public", "personal", "community", "temp"]
    resource_id: str = Field(..., min_length=1)
    available: bool | None = None
    allow_ai: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceIndexSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    resource_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=12000, ge=1000, le=30000)
    top_k: int = Field(default=8, ge=1, le=30)
    source_type: Literal["public", "personal", "community", "temp"] | None = None
    min_score: float | None = Field(default=None, ge=0, le=1)


class CourseGraphUpsertRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1)
    course_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    title: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(default='', max_length=80)
    grade: str = Field(default='', max_length=80)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    expected_version: int | None = Field(default=None, ge=0)


class TeacherFeedbackRequest(BaseModel):
    prompt_run_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    event_id: str | None = Field(default=None, min_length=1, max_length=80)
    user_id: str | None = Field(default=None, min_length=1)
    session_id: str | None = None
    project_id: str | None = None
    action: Literal["accept", "reject", "undo", "manual_edit", "regenerate"]
    target_type: Literal["presentation", "slide", "outline", "lesson_plan", "interactive"] = "presentation"
    instruction: str | None = None
    change_summary: str | None = None
    before_data: dict[str, Any] = Field(default_factory=dict)
    after_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextToSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = None


class ClassroomEventRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    session_id: str | None = None
    student_key: str | None = None
    event_type: Literal["answer", "confusion", "engagement", "exit_ticket", "resource_open"]
    question_id: str | None = None
    answer: str | None = None
    correct: bool | None = None
    response_ms: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
