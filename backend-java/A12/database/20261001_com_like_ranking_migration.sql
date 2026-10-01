-- 功能11 社区点赞与热门榜单迁移脚本（点赞表 / 冗余计数列 / 窗口聚合索引）
-- 背景:
--   功能11（社区优质内容发现: 点赞 / 排序 / 热门榜单）依赖三处表结构变更:
--   1) com_content.like_count / favorite_count 冗余计数列 —— 支撑「总量」排序与卡片计数展示;
--   2) 独立点赞表 com_like —— uk_user_target 唯一索引做幂等防重, created_at 支撑时间窗聚合
--      （点赞不并入 com_interaction 单表三用, 因其需要唯一防重与 created_at 窗口聚合）;
--   3) com_interaction(action_type, created_at) 复合索引 —— 日/周/月榜单的窗口聚合子查询按此扫描。
-- 变更:
--   1. com_content 新增 like_count / favorite_count INT NOT NULL DEFAULT 0;
--   2. 新建 com_like（uk_user_target 唯一索引防重 + idx_created 窗口索引）;
--   3. com_interaction 新增 KEY idx_action_created (action_type, created_at);
--   4. com_interaction.target_type 历史值归一（case → lesson_case, 与 normalizeContentType 白名单对齐）;
--   5. 存量回填 like_count / favorite_count（按互动行重算, 可重复执行）。
-- 说明:
--   与根目录 sql/upgrade_feature11_community_likes_ranking.sql 同源同内容;
--   a12_schema.sql 已同步全部变更(全新初始化无需执行本脚本); 本脚本用于已有库执行,
--   全部 DDL 基于 information_schema 防重入, 可重复执行。

SET NAMES utf8mb4;

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
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '点赞ID',
  user_id INT NOT NULL COMMENT '点赞用户ID',
  target_type VARCHAR(20) NOT NULL COMMENT '目标类型: skill/lesson_case',
  target_id INT NOT NULL COMMENT '目标内容ID',
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

-- ---------- 5. 历史数据归一: com_interaction.target_type case → lesson_case ----------
-- （先归一再回填, 保证 favorite 窗口聚合与冗余列口径一致）
UPDATE com_interaction SET target_type = 'lesson_case' WHERE target_type = 'case';

-- ---------- 6. 存量回填: like_count / favorite_count ----------
UPDATE com_content c SET
  like_count = (SELECT COUNT(*) FROM com_like l
                WHERE l.target_type = c.content_type AND l.target_id = c.id),
  favorite_count = (SELECT COUNT(*) FROM com_interaction i
                    WHERE i.action_type = 'favorite'
                      AND i.target_id = c.id
                      AND i.target_type = c.content_type);

-- =============================================
-- 回滚脚本（如需）:
-- ALTER TABLE com_content DROP COLUMN like_count;
-- ALTER TABLE com_content DROP COLUMN favorite_count;
-- DROP TABLE IF EXISTS com_like;
-- ALTER TABLE com_interaction DROP INDEX idx_action_created;
-- =============================================
