import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_BAILIAN_CHAT_MODEL = "qwen-plus"
DEFAULT_BAILIAN_PPT_HTML_MODEL = "qwen-turbo"
DEFAULT_BAILIAN_EMBEDDING_MODEL = "text-embedding-v4"
DEFAULT_BAILIAN_ASR_MODEL = "qwen3-asr-flash"


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
    ppt_html_model: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_dimensions: int | None
    asr_api_key: str
    asr_base_url: str
    asr_model: str
    request_timeout_seconds: float
    max_slide_concurrency: int
    max_html_retries: int
    enable_quality_pipeline: bool
    enable_autonomous_tools: bool
    quality_preset: str
    postgres_dsn: str


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    enable_quality_pipeline = os.getenv("ENABLE_QUALITY_PIPELINE", "true").lower() == "true"
    quality_preset = os.getenv("QUALITY_PRESET", "fast").lower()
    request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
    if enable_quality_pipeline:
        request_timeout_seconds = max(request_timeout_seconds, 60.0)
    return Settings(
        app_name=os.getenv("APP_NAME", "a12-python-ppt-service"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL", DEFAULT_BAILIAN_BASE_URL),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_BAILIAN_CHAT_MODEL),
        ppt_html_model=os.getenv("PPT_HTML_MODEL", DEFAULT_BAILIAN_PPT_HTML_MODEL),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", ""),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL", DEFAULT_BAILIAN_BASE_URL),
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_BAILIAN_EMBEDDING_MODEL),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS")) if os.getenv("EMBEDDING_DIMENSIONS") else None,
        asr_api_key=os.getenv("ASR_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", ""),
        asr_base_url=os.getenv("ASR_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL", DEFAULT_BAILIAN_BASE_URL),
        asr_model=os.getenv("ASR_MODEL", DEFAULT_BAILIAN_ASR_MODEL),
        request_timeout_seconds=request_timeout_seconds,
        max_slide_concurrency=int(os.getenv("MAX_SLIDE_CONCURRENCY", "12")),
        max_html_retries=int(os.getenv("MAX_HTML_RETRIES", "1")),
        enable_quality_pipeline=enable_quality_pipeline,
        enable_autonomous_tools=os.getenv("ENABLE_AUTONOMOUS_TOOLS", "true").lower() == "true",
        quality_preset=quality_preset,
        postgres_dsn=os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"),
    )
