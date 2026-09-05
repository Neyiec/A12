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
    request_timeout_seconds: float
    max_slide_concurrency: int
    max_html_retries: int
    enable_quality_pipeline: bool
    quality_preset: str
    postgres_dsn: str
    enable_autonomous_tools: bool
    enable_mcp_tools: bool
    mcp_servers: str


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
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS")) if os.getenv("EMBEDDING_DIMENSIONS") else None,
        asr_model=os.getenv("ASR_MODEL", "whisper-1"),
        request_timeout_seconds=request_timeout_seconds,
        max_slide_concurrency=int(os.getenv("MAX_SLIDE_CONCURRENCY", "8")),
        max_html_retries=int(os.getenv("MAX_HTML_RETRIES", "1")),
        enable_quality_pipeline=enable_quality_pipeline,
        quality_preset=quality_preset,
        postgres_dsn=os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"),
        enable_autonomous_tools=os.getenv("ENABLE_AUTONOMOUS_TOOLS", "true").lower() == "true",
        enable_mcp_tools=os.getenv("ENABLE_MCP_TOOLS", "false").lower() == "true",
        mcp_servers=os.getenv("MCP_SERVERS", ""),
    )
