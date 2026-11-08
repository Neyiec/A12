-- Non-destructive, repeatable migration for an existing MySQL database.
SET @a12_add_source = IF(
  (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='adm_resource' AND column_name='source_metadata')=0,
  'ALTER TABLE adm_resource ADD COLUMN source_metadata LONGTEXT NULL COMMENT ''来源、版本及有效期登记''',
  'SELECT 1');
PREPARE a12_source_stmt FROM @a12_add_source;
EXECUTE a12_source_stmt;
DEALLOCATE PREPARE a12_source_stmt;
