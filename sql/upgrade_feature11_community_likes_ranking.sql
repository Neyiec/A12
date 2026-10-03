-- =============================================
-- 功能11：社区优质内容发现（点赞/收藏排序/热门榜单）
-- 升级脚本（可重复执行：基于 information_schema 防重入）
-- 1) com_content 新增 like_count / favorite_count 冗余列
-- 2) 新增点赞表 com_like（user_id+target 唯一索引防重）
-- 3) com_interaction 新增窗口聚合索引
-- 4) 存量数据回填 + target_type 历史值归一（case → lesson_case）
-- =============================================
USE a12;

-- ---------- 1. com_content 新增 like_count ----------
SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE com_content ADD COLUMN like_count INT NOT NULL DEFAULT 0 COMMENT ''点赞数'' AFTER use_count',
    'SELECT ''com_content.like_count already exists'' AS note')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'a12' AND TABLE_NAME = 'com_content' AND COLUMN_NAME = 'like_count');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------- 2. com_content 新增 favorite_count ----------
SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE com_content ADD COLUMN favorite_count INT NOT NULL DEFAULT 0 COMMENT ''收藏数'' AFTER like_count',
    'SELECT ''com_content.favorite_count already exists'' AS note')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'a12' AND TABLE_NAME = 'com_content' AND COLUMN_NAME = 'favorite_count');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------- 3. 点赞表 com_like ----------
CREATE TABLE IF NOT EXISTS com_like (
  id BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '点赞ID',
  user_id INT(11) NOT NULL COMMENT '点赞用户ID',
  target_type VARCHAR(20) NOT NULL COMMENT '目标类型(skill/lesson_case)',
  target_id INT(11) NOT NULL COMMENT '目标内容ID',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_target (user_id, target_type, target_id),
  KEY idx_target (target_type, target_id),
  KEY idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区点赞表';

-- ---------- 4. com_interaction 窗口聚合索引 ----------
SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE com_interaction ADD KEY idx_action_created (action_type, created_at)',
    'SELECT ''com_interaction.idx_action_created already exists'' AS note')
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = 'a12' AND TABLE_NAME = 'com_interaction' AND INDEX_NAME = 'idx_action_created');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------- 5. 历史数据归一：com_interaction.target_type case → lesson_case ----------
-- （先归一再回填，保证 favorite 窗口聚合与冗余列口径一致）
UPDATE com_interaction SET target_type = 'lesson_case' WHERE target_type = 'case';

-- 将旧版社区点赞记录迁入独立点赞表，保留用户状态与时间；唯一索引使重复执行安全。
INSERT IGNORE INTO com_like (user_id, target_type, target_id, created_at)
SELECT user_id, target_type, target_id, MIN(created_at)
FROM com_interaction WHERE action_type = 'like'
GROUP BY user_id, target_type, target_id;

-- ---------- 6. 存量回填：like_count / favorite_count ----------
UPDATE com_content c SET
  like_count = (SELECT COUNT(*) FROM com_like l
                WHERE l.target_type = c.content_type AND l.target_id = c.id),
  favorite_count = (SELECT COUNT(*) FROM com_interaction i
                    WHERE i.action_type = 'favorite'
                      AND i.target_id = c.id
                      AND i.target_type = c.content_type);

-- =============================================
-- 回滚脚本（如需）：
-- ALTER TABLE com_content DROP COLUMN like_count;
-- ALTER TABLE com_content DROP COLUMN favorite_count;
-- DROP TABLE IF EXISTS com_like;
-- ALTER TABLE com_interaction DROP INDEX idx_action_created;
-- =============================================
