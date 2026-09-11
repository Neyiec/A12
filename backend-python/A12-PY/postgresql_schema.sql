-- =============================================
-- A12-PY PostgreSQL schema
-- Recommended database/account: postgres
-- Default DSN example: postgresql://postgres:postgres@127.0.0.1:5432/postgres
-- pgvector is required for real RAG vector similarity retrieval.
-- Default embedding model is Alibaba Cloud Model Studio text-embedding-v4,
-- using its default 1024-dimensional output.
-- =============================================

CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS a12_resource_index_chunk CASCADE;
DROP TABLE IF EXISTS a12_resource_index CASCADE;
DROP TABLE IF EXISTS a12_retrieval_log CASCADE;
DROP TABLE IF EXISTS a12_outline_generation_record CASCADE;
DROP TABLE IF EXISTS a12_teacher_style_memory CASCADE;
DROP TABLE IF EXISTS a12_outline_chat_message CASCADE;
DROP TABLE IF EXISTS a12_outline_chat_session CASCADE;
DROP TABLE IF EXISTS a12_teacher_style_profile CASCADE;

-- =============================================
-- Outline chat session
-- =============================================
CREATE TABLE a12_outline_chat_session (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  session_id VARCHAR(80) NOT NULL,
  title VARCHAR(255) DEFAULT NULL,
  intent JSONB NOT NULL DEFAULT '{}'::jsonb,
  final_prompt TEXT DEFAULT NULL,
  outline_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  last_message_at TIMESTAMPTZ DEFAULT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uk_a12_outline_chat_session_user_session UNIQUE (user_id, session_id)
);

COMMENT ON TABLE a12_outline_chat_session IS 'A12-PY outline generation chat session';
COMMENT ON COLUMN a12_outline_chat_session.user_id IS 'User ID from Java request';
COMMENT ON COLUMN a12_outline_chat_session.session_id IS 'Python chat session ID';
COMMENT ON COLUMN a12_outline_chat_session.intent IS 'Merged multi-turn user intent';
COMMENT ON COLUMN a12_outline_chat_session.final_prompt IS 'Final prompt after merging input/files/RAG/web results';
COMMENT ON COLUMN a12_outline_chat_session.outline_data IS 'Latest generated outline JSON';

CREATE INDEX idx_a12_outline_chat_session_user ON a12_outline_chat_session (user_id);
CREATE INDEX idx_a12_outline_chat_session_updated ON a12_outline_chat_session (updated_at DESC);
CREATE INDEX idx_a12_outline_chat_session_intent_gin ON a12_outline_chat_session USING GIN (intent);

-- =============================================
-- Outline chat message
-- =============================================
CREATE TABLE a12_outline_chat_message (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  session_id VARCHAR(80) NOT NULL,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_a12_outline_chat_message_role CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  CONSTRAINT fk_a12_outline_chat_message_session
    FOREIGN KEY (user_id, session_id)
    REFERENCES a12_outline_chat_session (user_id, session_id)
    ON DELETE CASCADE
);

COMMENT ON TABLE a12_outline_chat_message IS 'A12-PY outline chat messages';
COMMENT ON COLUMN a12_outline_chat_message.metadata IS 'Message metadata such as resource_ids, tool switches, clarification type';

CREATE INDEX idx_a12_outline_chat_message_session ON a12_outline_chat_message (user_id, session_id, created_at);

-- =============================================
-- Outline generation record
-- =============================================
CREATE TABLE a12_outline_generation_record (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  session_id VARCHAR(80) NOT NULL,
  outline_id VARCHAR(80) DEFAULT NULL,
  title VARCHAR(255) DEFAULT NULL,
  final_prompt TEXT DEFAULT NULL,
  outline_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  slide_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_a12_outline_generation_session
    FOREIGN KEY (user_id, session_id)
    REFERENCES a12_outline_chat_session (user_id, session_id)
    ON DELETE CASCADE
);

COMMENT ON TABLE a12_outline_generation_record IS 'A12-PY outline generation results';

CREATE INDEX idx_a12_outline_generation_user ON a12_outline_generation_record (user_id, created_at DESC);
CREATE INDEX idx_a12_outline_generation_outline_id ON a12_outline_generation_record (outline_id);
CREATE INDEX idx_a12_outline_generation_data_gin ON a12_outline_generation_record USING GIN (outline_data);

-- =============================================
-- Teacher style profile
-- =============================================
CREATE TABLE a12_teacher_style_profile (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  style_summary TEXT DEFAULT NULL,
  profile JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_count INT NOT NULL DEFAULT 0,
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uk_a12_teacher_style_profile_user UNIQUE (user_id)
);

COMMENT ON TABLE a12_teacher_style_profile IS 'Long-term teacher teaching style profile';

CREATE INDEX idx_a12_teacher_style_profile_profile_gin ON a12_teacher_style_profile USING GIN (profile);

-- =============================================
-- Teacher style memory evidence
-- =============================================
CREATE TABLE a12_teacher_style_memory (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  session_id VARCHAR(80) NOT NULL,
  source_message TEXT NOT NULL,
  extracted_style JSONB NOT NULL DEFAULT '{}'::jsonb,
  necessity_score NUMERIC(5,4) NOT NULL DEFAULT 0,
  reason VARCHAR(500) DEFAULT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_a12_teacher_style_memory_session
    FOREIGN KEY (user_id, session_id)
    REFERENCES a12_outline_chat_session (user_id, session_id)
    ON DELETE CASCADE
);

COMMENT ON TABLE a12_teacher_style_memory IS 'Teacher style evidence extracted from user inputs';

CREATE INDEX idx_a12_teacher_style_memory_user ON a12_teacher_style_memory (user_id, created_at DESC);
CREATE INDEX idx_a12_teacher_style_memory_session ON a12_teacher_style_memory (user_id, session_id);
CREATE INDEX idx_a12_teacher_style_memory_style_gin ON a12_teacher_style_memory USING GIN (extracted_style);

-- =============================================
-- Resource vector/index master table
-- source_type:
--   public   -> Java MySQL adm_resource
--   personal -> Java MySQL res_material
-- resource_key format:
--   public:{adm_resource.id}
--   personal:{res_material.id}
-- =============================================
CREATE TABLE a12_resource_index (
  resource_key TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  file_url TEXT NOT NULL,
  file_fingerprint TEXT NOT NULL,
  title TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  available BOOLEAN NOT NULL DEFAULT TRUE,
  allow_ai BOOLEAN NOT NULL DEFAULT TRUE,
  parse_status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT DEFAULT NULL,
  text_length INTEGER NOT NULL DEFAULT 0,
  chunk_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  indexed_at TIMESTAMPTZ DEFAULT NULL,
  CONSTRAINT ck_a12_resource_index_source CHECK (source_type IN ('public', 'personal')),
  CONSTRAINT ck_a12_resource_index_status CHECK (parse_status IN ('pending', 'completed', 'failed'))
);

COMMENT ON TABLE a12_resource_index IS 'A12-PY resource index master table; metadata stores uploaded_by/resource_id/available/allow_ai/source table information';
COMMENT ON COLUMN a12_resource_index.metadata IS 'Resource metadata, including source, mysql_table, uploaded_by, owner_user_id, resource_id, available, allow_ai, file_url';

CREATE INDEX idx_a12_resource_index_available ON a12_resource_index (source_type, available, allow_ai);
CREATE INDEX idx_a12_resource_index_metadata_gin ON a12_resource_index USING GIN (metadata);

-- =============================================
-- Resource chunks for RAG retrieval
-- embedding_vector uses pgvector cosine similarity retrieval.
-- =============================================
CREATE TABLE a12_resource_index_chunk (
  chunk_id TEXT PRIMARY KEY,
  resource_key TEXT NOT NULL REFERENCES a12_resource_index(resource_key) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding_vector vector(1024) DEFAULT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE a12_resource_index_chunk IS 'Parsed resource chunks used by RAG retrieval';

CREATE INDEX idx_a12_resource_chunk_resource ON a12_resource_index_chunk (resource_key, chunk_index);
CREATE INDEX idx_a12_resource_chunk_metadata_gin ON a12_resource_index_chunk USING GIN (metadata);
CREATE INDEX idx_a12_resource_chunk_embedding_hnsw
  ON a12_resource_index_chunk
  USING hnsw (embedding_vector vector_cosine_ops);

-- =============================================
-- RAG retrieval audit log
-- Stores direct index searches and outline-generation RAG calls.
-- =============================================
CREATE TABLE a12_retrieval_log (
  id BIGSERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  resource_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  match_count INTEGER NOT NULL DEFAULT 0,
  top_score DOUBLE PRECISION DEFAULT NULL,
  search_mode TEXT NOT NULL DEFAULT 'unknown',
  latency_ms INTEGER NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE a12_retrieval_log IS 'A12-PY RAG retrieval log for observability and evaluation';
COMMENT ON COLUMN a12_retrieval_log.metadata IS 'Top match summaries, fallback mode, embedding/postgres status';

CREATE INDEX idx_a12_retrieval_log_created ON a12_retrieval_log (created_at DESC);
CREATE INDEX idx_a12_retrieval_log_metadata_gin ON a12_retrieval_log USING GIN (metadata);
