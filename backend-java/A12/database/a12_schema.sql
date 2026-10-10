-- A12 项目 MySQL 建表脚本
-- 编码: UTF-8
-- 适配: Spring Boot + MyBatis 当前 mapper/entity 字段

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
  id INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  username VARCHAR(50) NOT NULL COMMENT '用户名',
  password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希',
  real_name VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
  phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  avatar VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
  user_type VARCHAR(20) NOT NULL COMMENT '用户类型: teacher/admin/auditor',
  roles JSON DEFAULT NULL COMMENT '角色列表',
  permissions JSON DEFAULT NULL COMMENT '权限列表',
  is_active TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用: 1启用/0停用',
  email_verified TINYINT NOT NULL DEFAULT 0 COMMENT '邮箱是否验证',
  phone_verified TINYINT NOT NULL DEFAULT 0 COMMENT '手机号是否验证',
  last_login_at DATETIME DEFAULT NULL COMMENT '最后登录时间',
  last_login_ip VARCHAR(50) DEFAULT NULL COMMENT '最后登录IP',
  password_changed_at DATETIME DEFAULT NULL COMMENT '密码最后修改时间',
  deleted_at DATETIME DEFAULT NULL COMMENT '软删除时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username),
  UNIQUE KEY uk_email (email),
  KEY idx_user_type (user_type),
  KEY idx_active_type (is_active, user_type),
  KEY idx_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

DROP TABLE IF EXISTS sys_config;
CREATE TABLE sys_config (
  id INT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  config_group VARCHAR(50) NOT NULL COMMENT '配置分组: ai_model/platform/security/template/sensitive_word',
  config_key VARCHAR(100) NOT NULL COMMENT '配置键',
  config_value TEXT DEFAULT NULL COMMENT '配置值',
  description VARCHAR(255) DEFAULT NULL COMMENT '配置说明',
  updated_by INT DEFAULT NULL COMMENT '最后修改人ID',
  version INT NOT NULL DEFAULT 1 COMMENT '版本号',
  status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态: draft/published',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_config_key (config_key),
  KEY idx_config_group (config_group),
  KEY idx_group_status (config_group, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

DROP TABLE IF EXISTS ai_config_version;
CREATE TABLE ai_config_version (
  id INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  config_id INT NOT NULL COMMENT '关联配置ID',
  version INT NOT NULL COMMENT '版本号',
  config_value TEXT DEFAULT NULL COMMENT '配置值快照',
  reason VARCHAR(500) DEFAULT NULL COMMENT '变更或回滚原因',
  created_by INT DEFAULT NULL COMMENT '操作人ID',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_config_id (config_id),
  UNIQUE KEY uk_config_version (config_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI配置版本历史表';

DROP TABLE IF EXISTS sys_log;
CREATE TABLE sys_log (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id INT DEFAULT NULL COMMENT '操作用户ID',
  log_type VARCHAR(30) NOT NULL COMMENT '日志类型: operation/download/browse/audit/system',
  module VARCHAR(50) NOT NULL COMMENT '所属模块',
  action VARCHAR(100) NOT NULL COMMENT '操作动作',
  target_type VARCHAR(50) DEFAULT NULL COMMENT '操作对象类型',
  target_id INT DEFAULT NULL COMMENT '操作对象ID',
  detail JSON DEFAULT NULL COMMENT '详细信息',
  ip VARCHAR(50) DEFAULT NULL COMMENT '操作IP',
  request_id VARCHAR(80) DEFAULT NULL COMMENT '请求ID',
  method VARCHAR(10) DEFAULT NULL COMMENT 'HTTP方法',
  path VARCHAR(255) DEFAULT NULL COMMENT '请求路径',
  user_agent VARCHAR(500) DEFAULT NULL COMMENT 'User-Agent',
  status VARCHAR(30) DEFAULT NULL COMMENT '处理状态',
  error_message TEXT DEFAULT NULL COMMENT '错误信息',
  duration_ms INT DEFAULT NULL COMMENT '耗时毫秒',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_log_type (log_type),
  KEY idx_created_at (created_at),
  KEY idx_module_action (module, action),
  KEY idx_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一业务日志表';

DROP TABLE IF EXISTS ai_conversation;
CREATE TABLE ai_conversation (
  id INT NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  user_id INT NOT NULL COMMENT '用户ID',
  title VARCHAR(200) DEFAULT NULL COMMENT '会话标题',
  status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/completed/archived',
  messages JSON DEFAULT NULL COMMENT 'Java侧轻量消息索引',
  context_summary TEXT DEFAULT NULL COMMENT '上下文摘要或Python解析意图摘要',
  python_session_id VARCHAR(80) DEFAULT NULL COMMENT 'Python会话ID',
  last_question TEXT DEFAULT NULL COMMENT 'Python最近一次澄清问题',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_python_session_id (python_session_id),
  KEY idx_user_updated (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话表';

DROP TABLE IF EXISTS ai_task;
CREATE TABLE ai_task (
  id INT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  user_id INT NOT NULL COMMENT '用户ID',
  conversation_id INT DEFAULT NULL COMMENT '关联会话ID',
  title VARCHAR(200) NOT NULL COMMENT '任务标题',
  subject VARCHAR(50) DEFAULT NULL COMMENT '学科',
  grade VARCHAR(50) DEFAULT NULL COMMENT '年级或学段',
  status VARCHAR(20) NOT NULL DEFAULT 'planning' COMMENT '状态: planning/confirmed/executing/completed/failed',
  uploaded_refs JSON DEFAULT NULL COMMENT '上传参考资料',
  plan_json JSON DEFAULT NULL COMMENT '教学设计大纲',
  plan_confirm_status VARCHAR(20) DEFAULT NULL COMMENT '大纲确认状态: pending/confirmed/rejected',
  exec_steps JSON DEFAULT NULL COMMENT '执行步骤',
  reflections JSON DEFAULT NULL COMMENT '反思迭代记录',
  python_session_id VARCHAR(80) DEFAULT NULL COMMENT 'Python会话ID',
  python_outline_id VARCHAR(80) DEFAULT NULL COMMENT 'Python生成的大纲ID',
  python_presentation_id VARCHAR(80) DEFAULT NULL COMMENT 'Python生成的PPT ID',
  generation_mode VARCHAR(30) NOT NULL DEFAULT 'python' COMMENT '生成模式: java/python',
  error_message TEXT DEFAULT NULL COMMENT '失败原因',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_conversation_id (conversation_id),
  KEY idx_status (status),
  KEY idx_python_session_id (python_session_id),
  KEY idx_python_outline_id (python_outline_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI教学任务表';

DROP TABLE IF EXISTS ws_project;
CREATE TABLE ws_project (
  id INT NOT NULL AUTO_INCREMENT COMMENT '项目ID',
  user_id INT NOT NULL COMMENT '用户ID',
  task_id INT DEFAULT NULL COMMENT '关联AI任务ID',
  project_name VARCHAR(200) NOT NULL COMMENT '项目名称',
  project_type VARCHAR(20) NOT NULL COMMENT '项目类型: ppt/word/h5/mixed',
  status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态: draft/editing/confirmed/exported/archived',
  current_version INT NOT NULL DEFAULT 1 COMMENT '当前版本号',
  snapshots JSON DEFAULT NULL COMMENT '版本快照列表',
  edit_history JSON DEFAULT NULL COMMENT '编辑历史',
  permissions JSON DEFAULT NULL COMMENT '授权用户ID列表',
  deleted_at DATETIME DEFAULT NULL COMMENT '软删除时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_task_id (task_id),
  KEY idx_status (status),
  KEY idx_user_status_updated (user_id, status, updated_at),
  KEY idx_user_deleted_updated (user_id, deleted_at, updated_at),
  KEY idx_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='创作项目表';

DROP TABLE IF EXISTS ws_page;
CREATE TABLE ws_page (
  id INT NOT NULL AUTO_INCREMENT COMMENT '页面ID',
  project_id INT NOT NULL COMMENT '所属项目ID',
  page_order INT NOT NULL COMMENT '页面排序',
  page_type VARCHAR(20) NOT NULL COMMENT '页面类型: cover/toc/content/summary',
  page_title VARCHAR(200) DEFAULT NULL COMMENT '页面标题',
  page_content JSON DEFAULT NULL COMMENT '页面内容',
  components JSON DEFAULT NULL COMMENT '组件列表',
  page_version INT NOT NULL DEFAULT 1 COMMENT 'page optimistic-lock version',
  client_version VARCHAR(80) DEFAULT NULL COMMENT 'frontend draft/client version',
  autosave TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'created by autosave',
  dirty TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'frontend dirty flag',
  last_saved_at DATETIME DEFAULT NULL COMMENT 'last saved time',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_id (project_id),
  UNIQUE KEY uk_project_page_order (project_id, page_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目页面表';

DROP TABLE IF EXISTS ws_version;
CREATE TABLE ws_version (
  id INT NOT NULL AUTO_INCREMENT COMMENT '版本ID',
  project_id INT NOT NULL COMMENT '项目ID',
  version_number INT NOT NULL COMMENT '版本号',
  description VARCHAR(500) DEFAULT NULL COMMENT '版本说明',
  snapshot_data JSON DEFAULT NULL COMMENT '版本快照数据',
  created_by INT DEFAULT NULL COMMENT '创建人ID',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_project_id (project_id),
  UNIQUE KEY uk_project_version (project_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目版本表';

DROP TABLE IF EXISTS res_material;
CREATE TABLE res_material (
  id INT NOT NULL AUTO_INCREMENT COMMENT '素材ID',
  user_id INT NOT NULL COMMENT '所属用户ID',
  file_name VARCHAR(200) NOT NULL COMMENT '文件名',
  file_type VARCHAR(20) NOT NULL COMMENT '文件类型: word/pdf/ppt/txt/image/audio/video',
  file_url VARCHAR(500) NOT NULL COMMENT '文件存储URL',
  file_size BIGINT DEFAULT NULL COMMENT '文件大小',
  thumbnail VARCHAR(500) DEFAULT NULL COMMENT '缩略图URL',
  description VARCHAR(500) DEFAULT NULL COMMENT '素材描述',
  categories JSON DEFAULT NULL COMMENT '分类列表',
  tags JSON DEFAULT NULL COMMENT '标签列表',
  access_type VARCHAR(20) NOT NULL DEFAULT 'private' COMMENT '访问权限: private/shared/authorized',
  authorized_users JSON DEFAULT NULL COMMENT '授权用户ID列表',
  allow_ai TINYINT NOT NULL DEFAULT 1 COMMENT '是否允许AI访问',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 1正常/0删除',
  ai_index_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'AI索引状态: pending/indexing/completed/failed/disabled',
  ai_indexed_at DATETIME DEFAULT NULL COMMENT 'AI索引完成时间',
  ai_index_error TEXT DEFAULT NULL COMMENT 'AI索引失败原因',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_file_type (file_type),
  KEY idx_allow_ai_status (allow_ai, status),
  KEY idx_created_at (created_at),
  KEY idx_user_type_created (user_id, file_type, created_at),
  KEY idx_ai_index_status (ai_index_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人素材资源表';

DROP TABLE IF EXISTS res_metadata_dictionary;
CREATE TABLE res_metadata_dictionary (
  id INT NOT NULL AUTO_INCREMENT COMMENT '字典ID',
  user_id INT NOT NULL COMMENT '所属用户ID',
  dict_type VARCHAR(20) NOT NULL COMMENT '字典类型: tag/category',
  name VARCHAR(80) NOT NULL COMMENT '标签或分类名称',
  color VARCHAR(30) DEFAULT NULL COMMENT '前端展示颜色',
  sort_order INT NOT NULL DEFAULT 1000 COMMENT '排序值',
  usage_count INT NOT NULL DEFAULT 0 COMMENT '冗余使用次数，实际列表会按资源实时统计覆盖',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 1正常/0删除',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_type_name (user_id, dict_type, name),
  KEY idx_user_type_status (user_id, dict_type, status),
  KEY idx_sort (sort_order, usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人资源标签/分类字典表';

DROP TABLE IF EXISTS kb_document;
CREATE TABLE kb_document (
  id INT NOT NULL AUTO_INCREMENT COMMENT '文档ID',
  source_type VARCHAR(20) NOT NULL COMMENT '来源类型: personal/platform',
  source_id INT DEFAULT NULL COMMENT '来源素材或平台资源ID',
  user_id INT DEFAULT NULL COMMENT '所属用户ID',
  title VARCHAR(200) NOT NULL COMMENT '文档标题',
  doc_type VARCHAR(20) NOT NULL COMMENT '文档类型: text/image/audio/video',
  parse_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '解析状态: pending/parsing/completed/failed',
  chunks JSON DEFAULT NULL COMMENT '分块列表',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_source_type (source_type),
  KEY idx_user_id (user_id),
  UNIQUE KEY uk_source (source_type, source_id),
  KEY idx_parse_status (parse_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识文档表';

DROP TABLE IF EXISTS kb_retrieval_log;
CREATE TABLE kb_retrieval_log (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  user_id INT NOT NULL COMMENT '用户ID',
  type VARCHAR(20) NOT NULL COMMENT '类型: retrieval/generation',
  task_id INT DEFAULT NULL COMMENT '关联任务ID',
  query_text TEXT DEFAULT NULL COMMENT '查询文本',
  result_chunks JSON DEFAULT NULL COMMENT '检索结果',
  prompt_context TEXT DEFAULT NULL COMMENT '生成上下文',
  generated_content TEXT DEFAULT NULL COMMENT '生成内容',
  model_name VARCHAR(100) DEFAULT NULL COMMENT '模型名称',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_type (type),
  KEY idx_task_id (task_id),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='检索与生成记录表';

DROP TABLE IF EXISTS exp_task;
CREATE TABLE exp_task (
  id INT NOT NULL AUTO_INCREMENT COMMENT '导出任务ID',
  user_id INT NOT NULL COMMENT '用户ID',
  project_id INT NOT NULL COMMENT '项目ID',
  snapshot_version INT DEFAULT NULL COMMENT '绑定的快照版本号',
  export_type VARCHAR(20) NOT NULL COMMENT '导出类型: pptx/word/package',
  status VARCHAR(20) NOT NULL DEFAULT 'queued' COMMENT '状态: queued/generating/checking/success/partial/failed/cancelled',
  config JSON DEFAULT NULL COMMENT '导出配置',
  file_name VARCHAR(200) DEFAULT NULL COMMENT '生成文件名',
  file_url VARCHAR(500) DEFAULT NULL COMMENT '文件下载地址',
  file_size BIGINT DEFAULT NULL COMMENT '文件大小',
  download_url VARCHAR(500) DEFAULT NULL COMMENT '临时下载链接',
  url_expire_at DATETIME DEFAULT NULL COMMENT '链接过期时间',
  file_status VARCHAR(20) DEFAULT NULL COMMENT '文件状态: available/expired/cleaned',
  quality_report JSON DEFAULT NULL COMMENT '质量报告',
  error_msg TEXT DEFAULT NULL COMMENT '失败原因',
  progress INT NOT NULL DEFAULT 0 COMMENT '任务进度: 0-100',
  retry_count INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  worker_id VARCHAR(80) DEFAULT NULL COMMENT '执行节点ID',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_project_id (project_id),
  KEY idx_status (status),
  KEY idx_user_created (user_id, created_at),
  KEY idx_project_created (project_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='导出任务表';

DROP TABLE IF EXISTS com_content;
CREATE TABLE com_content (
  id INT NOT NULL AUTO_INCREMENT COMMENT '内容ID',
  content_type VARCHAR(20) NOT NULL COMMENT '内容类型: skill/case',
  author_id INT NOT NULL COMMENT '作者ID',
  title VARCHAR(200) NOT NULL COMMENT '标题',
  description TEXT DEFAULT NULL COMMENT '描述或用途说明',
  subject VARCHAR(50) DEFAULT NULL COMMENT '学科',
  grade VARCHAR(50) DEFAULT NULL COMMENT '适用年级',
  lesson_type VARCHAR(50) DEFAULT NULL COMMENT '课型',
  keywords VARCHAR(500) DEFAULT NULL COMMENT '主题和知识点关键词',
  content_data JSON DEFAULT NULL COMMENT '内容主体',
  input_variables JSON DEFAULT NULL COMMENT '输入变量定义',
  example_effect TEXT DEFAULT NULL COMMENT '示例效果说明',
  version INT NOT NULL DEFAULT 1 COMMENT '当前版本号',
  version_history JSON DEFAULT NULL COMMENT '版本历史',
  license VARCHAR(50) DEFAULT NULL COMMENT '授权说明',
  status VARCHAR(20) NOT NULL DEFAULT 'reviewing' COMMENT '状态: public/reviewing/offline',
  is_top TINYINT NOT NULL DEFAULT 0 COMMENT '是否置顶',
  view_count INT NOT NULL DEFAULT 0 COMMENT '浏览次数',
  use_count INT NOT NULL DEFAULT 0 COMMENT '使用次数',
  like_count INT NOT NULL DEFAULT 0 COMMENT '点赞数',
  favorite_count INT NOT NULL DEFAULT 0 COMMENT '收藏数',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_content_type (content_type),
  KEY idx_author_id (author_id),
  KEY idx_subject (subject),
  KEY idx_grade (grade),
  KEY idx_status (status),
  KEY idx_public_sort (status, is_top, updated_at),
  KEY idx_author_status (author_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区内容表';

DROP TABLE IF EXISTS com_interaction;
CREATE TABLE com_interaction (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  user_id INT NOT NULL COMMENT '用户ID',
  action_type VARCHAR(20) NOT NULL COMMENT '操作类型: favorite/like/derivation/view',
  target_type VARCHAR(20) NOT NULL COMMENT '目标类型: skill/lesson_case/ppt',
  target_id INT NOT NULL COMMENT '目标内容ID',
  target_version INT DEFAULT NULL COMMENT '复用时来源版本号',
  target_project_id INT DEFAULT NULL COMMENT '派生项目ID',
  bind_materials JSON DEFAULT NULL COMMENT '绑定的私有素材ID列表',
  favorite_guard TINYINT GENERATED ALWAYS AS (CASE WHEN action_type = 'favorite' THEN 1 ELSE NULL END) VIRTUAL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_action_type (action_type),
  KEY idx_target_id (target_id),
  KEY idx_user_action_created (user_id, action_type, created_at),
  KEY idx_user_action_target (user_id, action_type, target_type, target_id),
  UNIQUE KEY uk_favorite_only (user_id, action_type, target_type, target_id, favorite_guard),
  KEY idx_com_interaction_ranking (action_type, target_id, created_at),
  KEY idx_action_created (action_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区互动表';

DROP TABLE IF EXISTS com_like;
CREATE TABLE com_like (
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

DROP TABLE IF EXISTS adm_audit;
CREATE TABLE adm_audit (
  id INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  audit_type VARCHAR(20) NOT NULL COMMENT '类型: audit/report',
  target_type VARCHAR(20) NOT NULL COMMENT '目标类型: skill/lesson_case/ppt',
  target_id INT NOT NULL COMMENT '目标内容ID',
  reporter_id INT DEFAULT NULL COMMENT '举报人ID',
  reason VARCHAR(500) DEFAULT NULL COMMENT '举报原因或审核备注',
  handler_id INT DEFAULT NULL COMMENT '处理人ID',
  action VARCHAR(20) DEFAULT NULL COMMENT '处理动作: approve/reject/offline/ignore',
  comment TEXT DEFAULT NULL COMMENT '处理意见',
  status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/processed/ignored',
  ai_domain VARCHAR(20) DEFAULT NULL COMMENT 'AI审核学科代理: arts/science/engineering',
  ai_verdict VARCHAR(20) DEFAULT NULL COMMENT 'AI结论: pass/review/fail/error',
  ai_score INT DEFAULT NULL COMMENT 'AI审核评分0-100',
  ai_report JSON DEFAULT NULL COMMENT '检查维度、证据和风险点',
  ai_model VARCHAR(100) DEFAULT NULL COMMENT 'AI审核模型',
  ai_reviewed_at DATETIME DEFAULT NULL COMMENT 'AI审核时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  processed_at DATETIME DEFAULT NULL COMMENT '处理时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_audit_type (audit_type),
  KEY idx_target_id (target_id),
  KEY idx_status (status),
  KEY idx_reporter_id (reporter_id),
  KEY idx_handler_id (handler_id),
  KEY idx_audit_status_created (audit_type, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核与举报表';

DROP TABLE IF EXISTS adm_resource;
CREATE TABLE adm_resource (
  id INT NOT NULL AUTO_INCREMENT COMMENT '资源ID',
  resource_type VARCHAR(30) NOT NULL COMMENT '类型: textbook/question_bank/media/component',
  title VARCHAR(200) NOT NULL COMMENT '资源名称',
  subject VARCHAR(50) DEFAULT NULL COMMENT '学科',
  grade VARCHAR(50) DEFAULT NULL COMMENT '适用年级',
  file_url VARCHAR(500) DEFAULT NULL COMMENT '文件URL',
  template_data JSON DEFAULT NULL COMMENT '组件模板数据',
  thumbnail VARCHAR(500) DEFAULT NULL COMMENT '缩略图',
  description VARCHAR(500) DEFAULT NULL COMMENT '描述',
  file_size BIGINT DEFAULT NULL COMMENT '文件大小',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 1启用/0禁用',
  uploaded_by INT DEFAULT NULL COMMENT '上传人ID',
  ai_index_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'AI索引状态: pending/indexing/completed/failed/disabled',
  ai_indexed_at DATETIME DEFAULT NULL COMMENT 'AI索引完成时间',
  ai_index_error TEXT DEFAULT NULL COMMENT 'AI索引失败原因',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_resource_type (resource_type),
  KEY idx_status_ai_index (status, ai_index_status),
  KEY idx_type_status_updated (resource_type, status, updated_at),
  KEY idx_uploaded_by (uploaded_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公共资源与组件表';

DROP TABLE IF EXISTS sys_file;
CREATE TABLE sys_file (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '文件ID',
  file_name VARCHAR(200) NOT NULL COMMENT '原始文件名',
  file_path VARCHAR(500) NOT NULL COMMENT '存储路径',
  file_type VARCHAR(20) NOT NULL COMMENT '文件扩展名',
  mime_type VARCHAR(100) DEFAULT NULL COMMENT 'MIME类型',
  file_size BIGINT NOT NULL COMMENT '文件大小',
  storage_type VARCHAR(20) NOT NULL DEFAULT 'local' COMMENT '存储方式: local/oss',
  uploader_id INT DEFAULT NULL COMMENT '上传者ID',
  biz_type VARCHAR(50) DEFAULT NULL COMMENT '业务类型: material/export/resource/avatar',
  biz_id INT DEFAULT NULL COMMENT '业务关联ID',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (id),
  KEY idx_uploader_id (uploader_id),
  KEY idx_biz (biz_type, biz_id),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一文件存储表';

SET FOREIGN_KEY_CHECKS = 1;
