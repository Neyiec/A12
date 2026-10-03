-- 功能11 测试用 H2 schema（MySQL 兼容模式；与生产表结构对齐的精简版）
CREATE TABLE com_content (
  id INT AUTO_INCREMENT PRIMARY KEY,
  content_type VARCHAR(20) NOT NULL,
  author_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description VARCHAR(2000),
  subject VARCHAR(50),
  grade VARCHAR(50),
  lesson_type VARCHAR(50),
  keywords VARCHAR(500),
  content_data TEXT,
  input_variables TEXT,
  example_effect TEXT,
  version INT NOT NULL DEFAULT 1,
  version_history TEXT,
  license VARCHAR(50),
  status VARCHAR(20) NOT NULL DEFAULT 'reviewing',
  is_top TINYINT NOT NULL DEFAULT 0,
  view_count INT NOT NULL DEFAULT 0,
  use_count INT NOT NULL DEFAULT 0,
  like_count INT NOT NULL DEFAULT 0,
  favorite_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE com_interaction (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  action_type VARCHAR(20) NOT NULL,
  target_type VARCHAR(20) NOT NULL,
  target_id INT NOT NULL,
  target_version INT,
  target_project_id INT,
  bind_materials TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE com_like (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  target_type VARCHAR(20) NOT NULL,
  target_id INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_user_target UNIQUE (user_id, target_type, target_id)
);
