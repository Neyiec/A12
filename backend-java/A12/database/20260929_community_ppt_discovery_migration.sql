-- 在已有数据库执行一次；新库使用更新后的 a12_schema.sql。
ALTER TABLE com_content
  ADD COLUMN keywords VARCHAR(500) DEFAULT NULL COMMENT '主题和知识点关键词' AFTER lesson_type;

CREATE INDEX idx_com_interaction_ranking
  ON com_interaction (action_type, target_id, created_at);

-- 历史工作台投稿若含完整课件页面，可归入独立的 PPT 分类。
UPDATE com_content
SET content_type = 'ppt'
WHERE content_type = 'lesson_case'
  AND JSON_VALID(content_data)
  AND JSON_UNQUOTE(JSON_EXTRACT(content_data, '$.source')) = 'a12-html-ppt-workspace';

-- 保持历史收藏、浏览和复用记录与新分类一致，避免取消收藏时找不到旧记录。
UPDATE com_interaction i
JOIN com_content c ON c.id = i.target_id
SET i.target_type = 'ppt'
WHERE c.content_type = 'ppt' AND i.target_type = 'lesson_case';

-- 审核任务同样依赖目标类型匹配；历史待审课件必须一起迁移。
UPDATE adm_audit a
JOIN com_content c ON c.id = a.target_id
SET a.target_type = 'ppt'
WHERE c.content_type = 'ppt' AND a.target_type = 'lesson_case';
