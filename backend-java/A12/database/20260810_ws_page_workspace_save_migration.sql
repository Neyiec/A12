ALTER TABLE ws_page
  ADD COLUMN page_version INT NOT NULL DEFAULT 1 COMMENT 'page optimistic-lock version' AFTER components,
  ADD COLUMN client_version VARCHAR(80) DEFAULT NULL COMMENT 'frontend draft/client version' AFTER page_version,
  ADD COLUMN autosave TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'created by autosave' AFTER client_version,
  ADD COLUMN dirty TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'frontend dirty flag' AFTER autosave,
  ADD COLUMN last_saved_at DATETIME DEFAULT NULL COMMENT 'last saved time' AFTER dirty;

UPDATE ws_page
SET last_saved_at = COALESCE(updated_at, created_at, NOW())
WHERE last_saved_at IS NULL;
