-- =============================================
-- A12 Java AI / resource gateway incremental migration
-- Use this for an existing MySQL database. Do not re-run table_created.txt on production data.
-- This is a one-time migration. Do not run it again after the columns/indexes have been added.
-- =============================================

ALTER TABLE ai_conversation
  ADD COLUMN python_session_id VARCHAR(80) DEFAULT NULL COMMENT 'Python outline chat session ID' AFTER context_summary,
  ADD COLUMN last_question TEXT DEFAULT NULL COMMENT 'Latest clarification question returned by Python' AFTER python_session_id,
  ADD KEY idx_python_session_id (python_session_id);

ALTER TABLE ai_task
  ADD COLUMN python_session_id VARCHAR(80) DEFAULT NULL COMMENT 'Python outline chat session ID' AFTER reflections,
  ADD COLUMN python_outline_id VARCHAR(80) DEFAULT NULL COMMENT 'Python generated outline ID' AFTER python_session_id,
  ADD COLUMN python_presentation_id VARCHAR(80) DEFAULT NULL COMMENT 'Python generated presentation ID' AFTER python_outline_id,
  ADD COLUMN generation_mode VARCHAR(30) NOT NULL DEFAULT 'python' COMMENT 'Generation mode(java/python)' AFTER python_presentation_id,
  ADD COLUMN error_message TEXT DEFAULT NULL COMMENT 'Python generation or gateway forwarding error' AFTER generation_mode,
  ADD KEY idx_python_session_id (python_session_id),
  ADD KEY idx_python_outline_id (python_outline_id);

UPDATE ai_task
SET generation_mode = 'python'
WHERE generation_mode IS NULL OR generation_mode = '';

ALTER TABLE res_material
  ADD COLUMN ai_index_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'AI index status(pending/indexing/completed/failed/disabled)' AFTER status,
  ADD COLUMN ai_indexed_at DATETIME DEFAULT NULL COMMENT 'AI index completed time' AFTER ai_index_status,
  ADD COLUMN ai_index_error TEXT DEFAULT NULL COMMENT 'AI index error message' AFTER ai_indexed_at,
  ADD KEY idx_allow_ai_status (allow_ai, status);

UPDATE res_material
SET ai_index_status = CASE
    WHEN status = 0 THEN 'disabled'
    WHEN allow_ai = 0 THEN 'disabled'
    ELSE 'pending'
END
WHERE ai_index_status IS NULL OR ai_index_status = '';

ALTER TABLE adm_resource
  ADD COLUMN ai_index_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'AI index status(pending/indexing/completed/failed/disabled)' AFTER uploaded_by,
  ADD COLUMN ai_indexed_at DATETIME DEFAULT NULL COMMENT 'AI index completed time' AFTER ai_index_status,
  ADD COLUMN ai_index_error TEXT DEFAULT NULL COMMENT 'AI index error message' AFTER ai_indexed_at,
  ADD KEY idx_status_ai_index (status, ai_index_status);

UPDATE adm_resource
SET ai_index_status = CASE
    WHEN status = 0 THEN 'disabled'
    ELSE 'pending'
END
WHERE ai_index_status IS NULL OR ai_index_status = '';
