-- 旧版 PostgreSQL 资源索引库执行一次；新库使用更新后的 postgresql_schema.sql。
ALTER TABLE a12_resource_index
  DROP CONSTRAINT IF EXISTS ck_a12_resource_index_source;
ALTER TABLE a12_resource_index
  ADD CONSTRAINT ck_a12_resource_index_source
  CHECK (source_type IN ('public', 'personal', 'community'));
