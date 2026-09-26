"""配置文件"""

import os
from dataclasses import dataclass
from functools import lru_cache


def _load_dotenv() -> None:
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_model_fast: str
    openai_model_standard: str
    openai_model_deep: str
    openai_model_vision: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_dimensions: int | None
    asr_model: str
    asr_api_key: str
    asr_base_url: str
    index_parse_timeout_seconds: float
    enable_vision_parse: bool
    request_timeout_seconds: float
    max_slide_concurrency: int
    max_html_retries: int
    enable_quality_pipeline: bool
    quality_preset: str
    postgres_dsn: str
    enable_autonomous_tools: bool
    enable_mcp_tools: bool
    mcp_servers: str
    tool_call_timeout_seconds: float
    mcp_discovery_timeout_seconds: float
    mcp_tool_cache_ttl_seconds: float
    image_generation_api_key: str
    image_generation_base_url: str
    image_generation_model: str
    image_generation_timeout_seconds: float
    image_generation_poll_interval_seconds: float
    max_generated_images: int
    retrieval_min_score: float
    tts_model: str
    tts_voice: str
    redis_url: str
    redis_key_prefix: str
    embedding_cache_ttl_seconds: int
    rag_cache_ttl_seconds: int
    ai_rate_limit_per_minute: int
    ai_global_concurrency: int
    ai_user_concurrency: int
    kafka_enabled: bool
    kafka_bootstrap_servers: str
    kafka_consumer_group: str
    kafka_resource_index_request_topic: str
    kafka_resource_index_result_topic: str
    kafka_classroom_event_topic: str
    kafka_teacher_feedback_topic: str
    kafka_dead_letter_topic: str


@lru_cache
def get_settings() -> Settings:
    """获取配置文件


        Return:
        Settings 一个配置信息领域类
    """
    _load_dotenv()
    enable_quality_pipeline = os.getenv("ENABLE_QUALITY_PIPELINE", "true").lower() == "true"
    quality_preset = os.getenv("QUALITY_PRESET", "fast").lower()
    request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
    if enable_quality_pipeline:
        request_timeout_seconds = max(request_timeout_seconds, 60.0)
    return Settings(
        app_name=os.getenv("APP_NAME", "a12-python-ppt-service"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_model_fast=os.getenv("OPENAI_MODEL_FAST", ""),
        openai_model_standard=os.getenv("OPENAI_MODEL_STANDARD", ""),
        openai_model_deep=os.getenv("OPENAI_MODEL_DEEP", ""),
        openai_model_vision=os.getenv("OPENAI_MODEL_VISION", ""),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS")) if os.getenv("EMBEDDING_DIMENSIONS") else None,
        asr_model=os.getenv("ASR_MODEL", "whisper-1"),
        # ASR 独立接入配置：可指向与 OPENAI_BASE_URL 不同的平台（如硅基流动 SenseVoice）；
        # 未设置 ASR_API_KEY/ASR_BASE_URL 时回落 LLM 组（OPENAI_*），保持旧行为兼容
        asr_api_key=os.getenv("ASR_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
        asr_base_url=os.getenv("ASR_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        # 资源索引下载+解析整体限时：卡死按超时转 failed，必须小于 Java→Python 的 600s 超时
        index_parse_timeout_seconds=float(os.getenv("INDEX_PARSE_TIMEOUT_SECONDS", "540")),
        # 资源解析的视觉理解开关（逐图调用主 LLM，图片多时耗时线性增长）：
        # 仅当 OPENAI_MODEL 支持图片输入时开启；LongCat 等纯文本模型保持 false，避免逐图烧满超时
        enable_vision_parse=os.getenv("ENABLE_VISION_PARSE", "false").lower() == "true",
        request_timeout_seconds=request_timeout_seconds,
        max_slide_concurrency=int(os.getenv("MAX_SLIDE_CONCURRENCY", "8")),
        max_html_retries=int(os.getenv("MAX_HTML_RETRIES", "1")),
        enable_quality_pipeline=enable_quality_pipeline,
        quality_preset=quality_preset,
        postgres_dsn=os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"),
        enable_autonomous_tools=os.getenv("ENABLE_AUTONOMOUS_TOOLS", "true").lower() == "true",
        enable_mcp_tools=os.getenv("ENABLE_MCP_TOOLS", "false").lower() == "true",
        mcp_servers=os.getenv("MCP_SERVERS", ""),
        tool_call_timeout_seconds=float(os.getenv("TOOL_CALL_TIMEOUT_SECONDS", "30")),
        mcp_discovery_timeout_seconds=float(os.getenv("MCP_DISCOVERY_TIMEOUT_SECONDS", "15")),
        mcp_tool_cache_ttl_seconds=float(os.getenv("MCP_TOOL_CACHE_TTL_SECONDS", "300")),
        image_generation_api_key=(
            os.getenv("IMAGE_GENERATION_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("EMBEDDING_API_KEY", "")
        ),
        image_generation_base_url=(os.getenv("IMAGE_GENERATION_BASE_URL") or "https://dashscope.aliyuncs.com/api/v1").rstrip("/"),
        image_generation_model=os.getenv("IMAGE_GENERATION_MODEL", "wan2.2-t2i-flash"),
        image_generation_timeout_seconds=float(os.getenv("IMAGE_GENERATION_TIMEOUT_SECONDS", "150")),
        image_generation_poll_interval_seconds=float(os.getenv("IMAGE_GENERATION_POLL_INTERVAL_SECONDS", "5")),
        max_generated_images=max(0, int(os.getenv("MAX_GENERATED_IMAGES", "4"))),
        retrieval_min_score=max(0.0, min(1.0, float(os.getenv("RETRIEVAL_MIN_SCORE", "0.18")))),
        tts_model=os.getenv("TTS_MODEL", "tts-1"),
        tts_voice=os.getenv("TTS_VOICE", "alloy"),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "a12"),
        embedding_cache_ttl_seconds=max(60, int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "604800"))),
        rag_cache_ttl_seconds=max(10, int(os.getenv("RAG_CACHE_TTL_SECONDS", "900"))),
        ai_rate_limit_per_minute=max(1, int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "30"))),
        ai_global_concurrency=max(1, int(os.getenv("AI_GLOBAL_CONCURRENCY", "8"))),
        ai_user_concurrency=max(1, int(os.getenv("AI_USER_CONCURRENCY", "2"))),
        kafka_enabled=os.getenv("KAFKA_ENABLED", "false").lower() == "true",
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
        kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "a12-python-ai"),
        kafka_resource_index_request_topic=os.getenv("KAFKA_RESOURCE_INDEX_REQUEST_TOPIC", "a12.resource.index.requested"),
        kafka_resource_index_result_topic=os.getenv("KAFKA_RESOURCE_INDEX_RESULT_TOPIC", "a12.resource.index.result"),
        kafka_classroom_event_topic=os.getenv("KAFKA_CLASSROOM_EVENT_TOPIC", "a12.classroom.events"),
        kafka_teacher_feedback_topic=os.getenv("KAFKA_TEACHER_FEEDBACK_TOPIC", "a12.teacher.feedback"),
        kafka_dead_letter_topic=os.getenv("KAFKA_DEAD_LETTER_TOPIC", "a12.dead-letter"),
    )
