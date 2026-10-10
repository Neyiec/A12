-- Scope uniqueness to favorites only. Reuse/view events may occur repeatedly.
-- No interaction or project data is deleted. Safe to run repeatedly on MySQL 8.
SET @guard_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'com_interaction' AND COLUMN_NAME = 'favorite_guard');
SET @sql = IF(@guard_exists = 0,
  'ALTER TABLE com_interaction ADD COLUMN favorite_guard TINYINT GENERATED ALWAYS AS (CASE WHEN action_type = ''favorite'' THEN 1 ELSE NULL END) VIRTUAL',
  'SELECT ''favorite_guard already exists'' AS note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'com_interaction' AND INDEX_NAME = 'uk_favorite_only');
SET @sql = IF(@index_exists = 0,
  'ALTER TABLE com_interaction ADD UNIQUE INDEX uk_favorite_only (user_id, action_type, target_type, target_id, favorite_guard)',
  'SELECT ''uk_favorite_only already exists'' AS note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @old_index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'com_interaction' AND INDEX_NAME = 'uk_favorite_target');
SET @sql = IF(@old_index_exists > 0,
  'ALTER TABLE com_interaction DROP INDEX uk_favorite_target',
  'SELECT ''legacy broad unique index already removed'' AS note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
