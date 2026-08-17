CREATE TABLE IF NOT EXISTS res_metadata_dictionary (
  id INT NOT NULL AUTO_INCREMENT COMMENT 'dictionary id',
  user_id INT NOT NULL COMMENT 'owner user id',
  dict_type VARCHAR(20) NOT NULL COMMENT 'tag/category',
  name VARCHAR(80) NOT NULL COMMENT 'tag or category name',
  color VARCHAR(30) DEFAULT NULL COMMENT 'frontend display color',
  sort_order INT NOT NULL DEFAULT 1000 COMMENT 'sort order',
  usage_count INT NOT NULL DEFAULT 0 COMMENT 'cached usage count; API also computes live counts',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1 active / 0 deleted',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'created time',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'updated time',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_type_name (user_id, dict_type, name),
  KEY idx_user_type_status (user_id, dict_type, status),
  KEY idx_sort (sort_order, usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='resource tag/category dictionary';

INSERT INTO res_metadata_dictionary(user_id, dict_type, name, sort_order, usage_count, status, created_at, updated_at)
SELECT user_id, 'tag', tag_name, 1000, COUNT(*), 1, NOW(), NOW()
FROM (
  SELECT user_id, TRIM(JSON_UNQUOTE(JSON_EXTRACT(tags, CONCAT('$[', numbers.n, ']')))) AS tag_name
  FROM res_material
  JOIN (
    SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
  ) numbers
  WHERE status = 1
    AND JSON_VALID(tags)
    AND JSON_TYPE(tags) = 'ARRAY'
    AND numbers.n < JSON_LENGTH(tags)
) t
WHERE tag_name IS NOT NULL AND tag_name <> ''
GROUP BY user_id, tag_name
ON DUPLICATE KEY UPDATE status = 1, usage_count = VALUES(usage_count), updated_at = NOW();

INSERT INTO res_metadata_dictionary(user_id, dict_type, name, sort_order, usage_count, status, created_at, updated_at)
SELECT user_id, 'category', category_name, 1000, COUNT(*), 1, NOW(), NOW()
FROM (
  SELECT user_id, TRIM(JSON_UNQUOTE(JSON_EXTRACT(categories, CONCAT('$[', numbers.n, ']')))) AS category_name
  FROM res_material
  JOIN (
    SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
  ) numbers
  WHERE status = 1
    AND JSON_VALID(categories)
    AND JSON_TYPE(categories) = 'ARRAY'
    AND numbers.n < JSON_LENGTH(categories)
) c
WHERE category_name IS NOT NULL AND category_name <> ''
GROUP BY user_id, category_name
ON DUPLICATE KEY UPDATE status = 1, usage_count = VALUES(usage_count), updated_at = NOW();
