-- 社区公开列表排序索引
-- 背景：com_content 上已有 idx_public_sort(status, is_top, updated_at)，但社区列表常带 subject /
-- content_type 过滤；过滤列不在索引里时优化器会退化为 filesort，数据量增长后会触发
-- "Out of sort memory, consider increasing server sort buffer size"（MySQL error 1038）。
-- 本迁移补两个组合索引，让「等值过滤 + is_top/updated_at 排序」直接按索引顺序读取，避免 filesort。
-- 可重复执行：MySQL 8.0 不支持 ADD INDEX IF NOT EXISTS，重复执行会报 1061，属预期。

ALTER TABLE com_content
  ADD KEY idx_public_subject_sort (status, subject, is_top, updated_at);

ALTER TABLE com_content
  ADD KEY idx_public_type_sort (status, content_type, is_top, updated_at);

-- 校验（应看到两条新索引）：
-- SHOW INDEX FROM com_content WHERE Key_name LIKE 'idx_public%';
