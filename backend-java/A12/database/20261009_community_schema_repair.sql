-- 已有库补齐社区搜索与 AI 审核字段，可重复执行；不删除或重写用户内容。
SET NAMES utf8mb4;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE com_content ADD COLUMN keywords VARCHAR(500) DEFAULT NULL COMMENT ''主题和知识点关键词''',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'com_content' AND COLUMN_NAME = 'keywords');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_domain VARCHAR(20) DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_domain');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_verdict VARCHAR(20) DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_verdict');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_score INT DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_score');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_report JSON DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_report');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_model VARCHAR(100) DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_model');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE adm_audit ADD COLUMN ai_reviewed_at DATETIME DEFAULT NULL',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'adm_audit' AND COLUMN_NAME = 'ai_reviewed_at');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
