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
    )
