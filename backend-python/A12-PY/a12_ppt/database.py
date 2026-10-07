"""Non-destructive PostgreSQL migrations for AI runtime state."""
import logging

from .config import get_settings

logger = logging.getLogger("a12_ppt.database")


def ensure_ai_schema() -> bool:
    """Create/upgrade AI tables without dropping user data."""
    statements = [
        """CREATE TABLE IF NOT EXISTS a12_outline_chat_session (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80) NOT NULL,
          title VARCHAR(255), intent JSONB NOT NULL DEFAULT '{}'::jsonb, final_prompt TEXT,
          outline_data JSONB NOT NULL DEFAULT '{}'::jsonb, status VARCHAR(30) NOT NULL DEFAULT 'active',
          last_message_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(user_id, session_id))""",
        """CREATE TABLE IF NOT EXISTS a12_outline_chat_message (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80) NOT NULL,
          role VARCHAR(20) NOT NULL, content TEXT NOT NULL, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          FOREIGN KEY(user_id, session_id) REFERENCES a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE)""",
        """CREATE TABLE IF NOT EXISTS a12_outline_generation_record (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80) NOT NULL,
          outline_id VARCHAR(80), title VARCHAR(255), final_prompt TEXT,
          outline_data JSONB NOT NULL DEFAULT '{}'::jsonb, slide_count INT NOT NULL DEFAULT 0,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          FOREIGN KEY(user_id, session_id) REFERENCES a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE)""",
        """CREATE TABLE IF NOT EXISTS a12_teacher_style_profile (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL UNIQUE, style_summary TEXT,
          profile JSONB NOT NULL DEFAULT '{}'::jsonb, evidence_count INT NOT NULL DEFAULT 0,
          confidence NUMERIC(5,4) NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS a12_teacher_style_memory (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80) NOT NULL,
          source_message TEXT NOT NULL, extracted_style JSONB NOT NULL DEFAULT '{}'::jsonb,
          necessity_score NUMERIC(5,4) NOT NULL DEFAULT 0, reason VARCHAR(500),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          FOREIGN KEY(user_id, session_id) REFERENCES a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE)""",
        """CREATE TABLE IF NOT EXISTS a12_ai_feedback (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80), project_id VARCHAR(80),
          action VARCHAR(32) NOT NULL, target_type VARCHAR(32) NOT NULL DEFAULT 'presentation',
          instruction TEXT, change_summary TEXT, before_data JSONB NOT NULL DEFAULT '{}'::jsonb,
          after_data JSONB NOT NULL DEFAULT '{}'::jsonb, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS a12_ai_run_log (
          id BIGSERIAL PRIMARY KEY, run_id VARCHAR(64) NOT NULL, user_id VARCHAR(64), operation VARCHAR(80) NOT NULL,
          model VARCHAR(120), model_profile VARCHAR(32), reasoning_effort VARCHAR(32), status VARCHAR(32) NOT NULL,
          latency_ms INT NOT NULL DEFAULT 0, input_tokens INT NOT NULL DEFAULT 0, output_tokens INT NOT NULL DEFAULT 0,
          fallback_reason TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS a12_classroom_event (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, project_id VARCHAR(80) NOT NULL,
          session_id VARCHAR(80), student_key VARCHAR(128), event_type VARCHAR(32) NOT NULL,
          question_id VARCHAR(128), answer TEXT, correct BOOLEAN, response_ms INT,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS a12_course_graph (
          user_id VARCHAR(64) NOT NULL, course_id VARCHAR(80) NOT NULL, title VARCHAR(255) NOT NULL,
          version INT NOT NULL DEFAULT 1, graph_data JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY(user_id, course_id))""",
        """CREATE TABLE IF NOT EXISTS a12_graph_evidence (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, course_id VARCHAR(80) NOT NULL,
          resource_key VARCHAR(180) NOT NULL, content_sha256 VARCHAR(64) NOT NULL,
          node_id VARCHAR(80) NOT NULL, excerpt TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          UNIQUE(user_id, course_id, resource_key, node_id))""",
        """CREATE TABLE IF NOT EXISTS a12_course_graph_version (
          user_id VARCHAR(64) NOT NULL, course_id VARCHAR(80) NOT NULL, version INT NOT NULL,
          title VARCHAR(255) NOT NULL, graph_data JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(user_id,course_id,version))""",
        """CREATE TABLE IF NOT EXISTS a12_learning_video_job (
          job_id VARCHAR(32) PRIMARY KEY, user_id VARCHAR(64) NOT NULL, title VARCHAR(255) NOT NULL,
          payload JSONB NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'queued',progress INT NOT NULL DEFAULT 0,
          attempts INT NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '', metadata JSONB NOT NULL DEFAULT '{}',
          expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        "ALTER TABLE a12_learning_video_job ADD COLUMN IF NOT EXISTS lease_id VARCHAR(32)",
        "CREATE INDEX IF NOT EXISTS idx_a12_video_queue ON a12_learning_video_job(status,created_at)",
        """CREATE TABLE IF NOT EXISTS a12_outline_strategy_run (
          id BIGSERIAL PRIMARY KEY, user_id VARCHAR(64) NOT NULL, session_id VARCHAR(80) NOT NULL,
          course_id VARCHAR(80), strategy VARCHAR(32) NOT NULL, graph_version INT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(user_id, session_id))""",
        "CREATE INDEX IF NOT EXISTS idx_a12_chat_session_user ON a12_outline_chat_session(user_id, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_a12_chat_message_session ON a12_outline_chat_message(user_id, session_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_a12_teacher_memory_user ON a12_teacher_style_memory(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_a12_ai_feedback_user ON a12_ai_feedback(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_a12_ai_run_created ON a12_ai_run_log(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_a12_classroom_project ON a12_classroom_event(user_id, project_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_a12_graph_evidence_course ON a12_graph_evidence(user_id, course_id, node_id)",
    ]
    try:
        import psycopg
        with psycopg.connect(get_settings().postgres_dsn) as conn:
            with conn.cursor() as cur:
                for statement in statements:
                    cur.execute(statement)
        return True
    except Exception:
        logger.exception("AI 数据库增量迁移失败")
        return False
