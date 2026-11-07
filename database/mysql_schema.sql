
-- 智核 A12 MySQL 当前数据库结构快照，导出日期：2026-10-10。
-- 来源：本机 a12 数据库，共27张表；不包含业务数据、账号、角色种子数据。
-- 在空数据库中执行。本脚本不删除已有表；不要直接导入正在使用的数据库。
-- 使用方式：先创建空的 a12 数据库，再使用 mysql -u 用户名 -p a12 < mysql_schema.sql
-- 包含当前真实字段、生成列、主外键、唯一索引、默认值、注释和表选项。
-- 自增起始值保留当前表定义，但未导出任何历史数据。

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `adm_audit` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `audit_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型: audit/report',
  `target_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标类型: skill/case',
  `target_id` int NOT NULL COMMENT '目标内容ID',
  `reporter_id` int DEFAULT NULL COMMENT '举报人ID',
  `reason` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '举报原因或审核备注',
  `handler_id` int DEFAULT NULL COMMENT '处理人ID',
  `action` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处理动作: approve/reject/offline/ignore',
  `comment` text COLLATE utf8mb4_unicode_ci COMMENT '处理意见',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '状态: pending/processed/ignored',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `processed_at` datetime DEFAULT NULL COMMENT '处理时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `ai_domain` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ai_verdict` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ai_score` int DEFAULT NULL,
  `ai_report` json DEFAULT NULL,
  `ai_model` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ai_reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_audit_type` (`audit_type`),
  KEY `idx_target_id` (`target_id`),
  KEY `idx_status` (`status`),
  KEY `idx_reporter_id` (`reporter_id`),
  KEY `idx_handler_id` (`handler_id`),
  KEY `idx_audit_status_created` (`audit_type`,`status`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核与举报表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `adm_resource` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '资源ID',
  `resource_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型: textbook/question_bank/media/component',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '资源名称',
  `subject` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学科',
  `grade` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '适用年级',
  `file_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文件URL',
  `template_data` json DEFAULT NULL COMMENT '组件模板数据',
  `thumbnail` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '缩略图',
  `description` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `source_metadata` longtext COLLATE utf8mb4_unicode_ci COMMENT '来源、版本及有效期登记',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态: 1启用/0禁用',
  `uploaded_by` int DEFAULT NULL COMMENT '上传人ID',
  `ai_index_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT 'AI索引状态: pending/indexing/completed/failed/disabled',
  `ai_indexed_at` datetime DEFAULT NULL COMMENT 'AI索引完成时间',
  `ai_index_error` text COLLATE utf8mb4_unicode_ci COMMENT 'AI索引失败原因',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_resource_type` (`resource_type`),
  KEY `idx_status_ai_index` (`status`,`ai_index_status`),
  KEY `idx_type_status_updated` (`resource_type`,`status`,`updated_at`),
  KEY `idx_uploaded_by` (`uploaded_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公共资源与组件表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_config_version` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `config_id` int NOT NULL COMMENT '关联配置ID',
  `version` int NOT NULL COMMENT '版本号',
  `config_value` text COLLATE utf8mb4_unicode_ci COMMENT '配置值快照',
  `reason` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '变更或回滚原因',
  `created_by` int DEFAULT NULL COMMENT '操作人ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_version` (`config_id`,`version`),
  KEY `idx_config_id` (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI配置版本历史表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_conversation` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '会话标题',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态: active/completed/archived',
  `messages` json DEFAULT NULL COMMENT 'Java侧轻量消息索引',
  `context_summary` text COLLATE utf8mb4_unicode_ci COMMENT '上下文摘要或Python解析意图摘要',
  `python_session_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Python会话ID',
  `last_question` text COLLATE utf8mb4_unicode_ci COMMENT 'Python最近一次澄清问题',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_python_session_id` (`python_session_id`),
  KEY `idx_user_updated` (`user_id`,`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_task` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `conversation_id` int DEFAULT NULL COMMENT '关联会话ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务标题',
  `subject` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学科',
  `grade` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '年级或学段',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'planning' COMMENT '状态: planning/confirmed/executing/completed/failed',
  `uploaded_refs` json DEFAULT NULL COMMENT '上传参考资料',
  `plan_json` json DEFAULT NULL COMMENT '教学设计大纲',
  `plan_confirm_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '大纲确认状态: pending/confirmed/rejected',
  `exec_steps` json DEFAULT NULL COMMENT '执行步骤',
  `reflections` json DEFAULT NULL COMMENT '反思迭代记录',
  `python_session_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Python会话ID',
  `python_outline_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Python生成的大纲ID',
  `python_presentation_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Python生成的PPT ID',
  `generation_mode` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'python' COMMENT '生成模式: java/python',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '失败原因',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_conversation_id` (`conversation_id`),
  KEY `idx_status` (`status`),
  KEY `idx_python_session_id` (`python_session_id`),
  KEY `idx_python_outline_id` (`python_outline_id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI教学任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `com_content` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '内容ID',
  `content_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '内容类型: skill/case',
  `author_id` int NOT NULL COMMENT '作者ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '描述或用途说明',
  `subject` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学科',
  `grade` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '适用年级',
  `lesson_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '课型',
  `content_data` json DEFAULT NULL COMMENT '内容主体',
  `input_variables` json DEFAULT NULL COMMENT '输入变量定义',
  `example_effect` text COLLATE utf8mb4_unicode_ci COMMENT '示例效果说明',
  `version` int NOT NULL DEFAULT '1' COMMENT '当前版本号',
  `version_history` json DEFAULT NULL COMMENT '版本历史',
  `license` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '授权说明',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'reviewing' COMMENT '状态: public/reviewing/offline',
  `is_top` tinyint NOT NULL DEFAULT '0' COMMENT '是否置顶',
  `view_count` int NOT NULL DEFAULT '0' COMMENT '浏览次数',
  `use_count` int NOT NULL DEFAULT '0' COMMENT '使用次数',
  `like_count` int NOT NULL DEFAULT '0' COMMENT '点赞数',
  `favorite_count` int NOT NULL DEFAULT '0' COMMENT '收藏数',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `keywords` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '主题和知识点关键词',
  PRIMARY KEY (`id`),
  KEY `idx_content_type` (`content_type`),
  KEY `idx_author_id` (`author_id`),
  KEY `idx_subject` (`subject`),
  KEY `idx_grade` (`grade`),
  KEY `idx_status` (`status`),
  KEY `idx_public_sort` (`status`,`is_top`,`updated_at`),
  KEY `idx_author_status` (`author_id`,`status`),
  KEY `idx_author_updated` (`author_id`,`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区内容表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `com_interaction` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `action_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作类型: favorite/derivation/view',
  `target_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标类型: skill/case',
  `target_id` int NOT NULL COMMENT '目标内容ID',
  `target_version` int DEFAULT NULL COMMENT '复用时来源版本号',
  `target_project_id` int DEFAULT NULL COMMENT '派生项目ID',
  `bind_materials` json DEFAULT NULL COMMENT '绑定的私有素材ID列表',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `favorite_guard` tinyint GENERATED ALWAYS AS ((case when (`action_type` = _utf8mb4'favorite') then 1 else NULL end)) VIRTUAL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_favorite_only` (`user_id`,`action_type`,`target_type`,`target_id`,`favorite_guard`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_action_type` (`action_type`),
  KEY `idx_target_id` (`target_id`),
  KEY `idx_user_action_created` (`user_id`,`action_type`,`created_at`),
  KEY `idx_action_created` (`action_type`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区互动表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `com_like` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '点赞ID',
  `user_id` int NOT NULL COMMENT '点赞用户ID',
  `target_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标类型: skill/lesson_case',
  `target_id` int NOT NULL COMMENT '目标内容ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_target` (`user_id`,`target_type`,`target_id`),
  KEY `idx_target` (`target_type`,`target_id`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区点赞表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exp_task` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '导出任务ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `project_id` int NOT NULL COMMENT '项目ID',
  `snapshot_version` int DEFAULT NULL COMMENT '绑定的快照版本号',
  `export_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '导出类型: pptx/word/package',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'queued' COMMENT '状态: queued/generating/checking/success/partial/failed/cancelled',
  `config` json DEFAULT NULL COMMENT '导出配置',
  `file_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '生成文件名',
  `file_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文件下载地址',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小',
  `download_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '临时下载链接',
  `url_expire_at` datetime DEFAULT NULL COMMENT '链接过期时间',
  `file_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文件状态: available/expired/cleaned',
  `quality_report` json DEFAULT NULL COMMENT '质量报告',
  `error_msg` text COLLATE utf8mb4_unicode_ci COMMENT '失败原因',
  `progress` int NOT NULL DEFAULT '0' COMMENT '任务进度: 0-100',
  `retry_count` int NOT NULL DEFAULT '0' COMMENT '重试次数',
  `worker_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '执行节点ID',
  `started_at` datetime DEFAULT NULL COMMENT '开始时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `completed_at` datetime DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_created` (`user_id`,`created_at`),
  KEY `idx_project_created` (`project_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='导出任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `kb_document` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '文档ID',
  `source_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源类型: personal/platform',
  `source_id` int DEFAULT NULL COMMENT '来源素材或平台资源ID',
  `user_id` int DEFAULT NULL COMMENT '所属用户ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文档标题',
  `doc_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文档类型: text/image/audio/video',
  `parse_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '解析状态: pending/parsing/completed/failed',
  `chunks` json DEFAULT NULL COMMENT '分块列表',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_source` (`source_type`,`source_id`),
  KEY `idx_source_type` (`source_type`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_parse_status` (`parse_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识文档表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `kb_retrieval_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型: retrieval/generation',
  `task_id` int DEFAULT NULL COMMENT '关联任务ID',
  `query_text` text COLLATE utf8mb4_unicode_ci COMMENT '查询文本',
  `result_chunks` json DEFAULT NULL COMMENT '检索结果',
  `prompt_context` text COLLATE utf8mb4_unicode_ci COMMENT '生成上下文',
  `generated_content` text COLLATE utf8mb4_unicode_ci COMMENT '生成内容',
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '模型名称',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_type` (`type`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='检索与生成记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qb_paper` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `owner_id` int NOT NULL,
  `title` varchar(120) NOT NULL,
  `subject` varchar(40) NOT NULL,
  `duration_minutes` int NOT NULL,
  `total_score` decimal(8,2) NOT NULL,
  `content_json` mediumtext NOT NULL,
  `revision` int NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qb_paper_owner` (`owner_id`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qb_question` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `owner_id` int NOT NULL,
  `subject` varchar(40) NOT NULL,
  `grade` varchar(40) NOT NULL,
  `question_type` varchar(20) NOT NULL,
  `difficulty` varchar(20) NOT NULL,
  `stem` text NOT NULL,
  `knowledge_points` varchar(500) NOT NULL DEFAULT '',
  `content_json` mediumtext NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `review_note` varchar(1000) NOT NULL DEFAULT '',
  `reviewer_id` int DEFAULT NULL,
  `revision` int NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qb_public` (`status`,`subject`,`grade`,`question_type`,`difficulty`,`id`),
  KEY `idx_qb_owner` (`owner_id`,`status`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qb_review` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `question_id` bigint NOT NULL,
  `reviewer_id` int NOT NULL,
  `decision` varchar(20) NOT NULL,
  `note` varchar(1000) NOT NULL DEFAULT '',
  `question_revision` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qb_review_question` (`question_id`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `res_material` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '素材ID',
  `user_id` int NOT NULL COMMENT '所属用户ID',
  `file_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件名',
  `file_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型: word/pdf/ppt/txt/image/audio/video',
  `file_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件存储URL',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小',
  `thumbnail` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '缩略图URL',
  `description` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '素材描述',
  `categories` json DEFAULT NULL COMMENT '分类列表',
  `tags` json DEFAULT NULL COMMENT '标签列表',
  `access_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'private' COMMENT '访问权限: private/shared/authorized',
  `authorized_users` json DEFAULT NULL COMMENT '授权用户ID列表',
  `allow_ai` tinyint NOT NULL DEFAULT '1' COMMENT '是否允许AI访问',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态: 1正常/0删除',
  `ai_index_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT 'AI索引状态: pending/indexing/completed/failed/disabled',
  `ai_indexed_at` datetime DEFAULT NULL COMMENT 'AI索引完成时间',
  `ai_index_error` text COLLATE utf8mb4_unicode_ci COMMENT 'AI索引失败原因',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_file_type` (`file_type`),
  KEY `idx_allow_ai_status` (`allow_ai`,`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_type_created` (`user_id`,`file_type`,`created_at`),
  KEY `idx_ai_index_status` (`ai_index_status`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人素材资源表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `res_metadata_dictionary` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'dictionary id',
  `user_id` int NOT NULL COMMENT 'owner user id',
  `dict_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'tag/category',
  `name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'tag or category name',
  `color` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'frontend display color',
  `sort_order` int NOT NULL DEFAULT '1000' COMMENT 'sort order',
  `usage_count` int NOT NULL DEFAULT '0' COMMENT 'cached usage count; API also computes live counts',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '1 active / 0 deleted',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'created time',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'updated time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_type_name` (`user_id`,`dict_type`,`name`),
  KEY `idx_user_type_status` (`user_id`,`dict_type`,`status`),
  KEY `idx_sort` (`sort_order`,`usage_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='resource tag/category dictionary';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_config` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `config_group` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置分组: ai_model/platform/security/template/sensitive_word',
  `config_key` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置键',
  `config_value` text COLLATE utf8mb4_unicode_ci COMMENT '配置值',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配置说明',
  `updated_by` int DEFAULT NULL COMMENT '最后修改人ID',
  `version` int NOT NULL DEFAULT '1' COMMENT '版本号',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft' COMMENT '状态: draft/published',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`),
  KEY `idx_config_group` (`config_group`),
  KEY `idx_group_status` (`config_group`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_file` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '文件ID',
  `file_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '存储路径',
  `file_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件扩展名',
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'MIME类型',
  `file_size` bigint NOT NULL COMMENT '文件大小',
  `storage_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'local' COMMENT '存储方式: local/oss',
  `uploader_id` int DEFAULT NULL COMMENT '上传者ID',
  `biz_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '业务类型: material/export/resource/avatar',
  `biz_id` int DEFAULT NULL COMMENT '业务关联ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (`id`),
  KEY `idx_uploader_id` (`uploader_id`),
  KEY `idx_biz` (`biz_type`,`biz_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一文件存储表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id` int DEFAULT NULL COMMENT '操作用户ID',
  `log_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '日志类型: operation/download/browse/audit/system',
  `module` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属模块',
  `action` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作动作',
  `target_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '操作对象类型',
  `target_id` int DEFAULT NULL COMMENT '操作对象ID',
  `detail` json DEFAULT NULL COMMENT '详细信息',
  `ip` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '操作IP',
  `request_id` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '请求ID',
  `method` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HTTP方法',
  `path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '请求路径',
  `user_agent` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User-Agent',
  `status` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处理状态',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '错误信息',
  `duration_ms` int DEFAULT NULL COMMENT '耗时毫秒',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_log_type` (`log_type`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_module_action` (`module`,`action`),
  KEY `idx_request_id` (`request_id`)
) ENGINE=InnoDB AUTO_INCREMENT=280 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一业务日志表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_permission` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '权限ID',
  `perm_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '权限标识: {module_key}:{action_key}, 如 users:view',
  `perm_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '权限名称(展示用), 如 用户管理-查看',
  `module_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属模块: dashboard/users/roles/audit/resources/settings',
  `module_label` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模块中文名, 如 用户管理',
  `action_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作: view/create/edit/delete/audit/export/stats/modify/resetPassword/configPerm',
  `action_label` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作中文名, 如 查看',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '权限说明',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用: 1启用/0停用',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_perm_code` (`perm_code`),
  UNIQUE KEY `uk_module_action` (`module_key`,`action_key`),
  KEY `idx_module` (`module_key`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统权限表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '角色标识: super_admin/admin/content_auditor/knowledge_curator/teacher',
  `role_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '角色名称(展示用)',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '角色说明',
  `sort_order` int NOT NULL DEFAULT '0' COMMENT '展示排序',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用: 1启用/0停用',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role_permission` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `role_id` int NOT NULL COMMENT '角色ID, 关联 sys_role.id',
  `permission_id` int NOT NULL COMMENT '权限ID, 关联 sys_permission.id',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm` (`role_id`,`permission_id`),
  KEY `idx_permission_id` (`permission_id`),
  CONSTRAINT `fk_rp_perm` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_rp_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色-权限关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `real_name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '真实姓名',
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '手机号',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '邮箱',
  `avatar` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像URL',
  `is_active` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用: 1启用/0停用',
  `email_verified` tinyint NOT NULL DEFAULT '0' COMMENT '邮箱是否验证',
  `phone_verified` tinyint NOT NULL DEFAULT '0' COMMENT '手机号是否验证',
  `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最后登录IP',
  `password_changed_at` datetime DEFAULT NULL COMMENT '密码最后修改时间',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_deleted_at` (`deleted_at`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user_role` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int NOT NULL COMMENT '用户ID, 关联 sys_user.id',
  `role_id` int NOT NULL COMMENT '角色ID, 关联 sys_role.id',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`,`role_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_ur_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户-角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ws_page` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '页面ID',
  `project_id` int NOT NULL COMMENT '所属项目ID',
  `page_order` int NOT NULL COMMENT '页面排序',
  `page_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '页面类型: cover/toc/content/summary',
  `page_title` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '页面标题',
  `page_content` json DEFAULT NULL COMMENT '页面内容',
  `components` json DEFAULT NULL COMMENT '组件列表',
  `page_version` int NOT NULL DEFAULT '1' COMMENT 'page optimistic-lock version',
  `client_version` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'frontend draft/client version',
  `autosave` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'created by autosave',
  `dirty` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'frontend dirty flag',
  `last_saved_at` datetime DEFAULT NULL COMMENT 'last saved time',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_page_order` (`project_id`,`page_order`),
  KEY `idx_project_id` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目页面表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ws_project` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '项目ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `task_id` int DEFAULT NULL COMMENT '关联AI任务ID',
  `project_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '项目名称',
  `project_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '项目类型: ppt/word/h5/mixed',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft' COMMENT '状态: draft/editing/confirmed/exported/archived',
  `current_version` int NOT NULL DEFAULT '1' COMMENT '当前版本号',
  `snapshots` json DEFAULT NULL COMMENT '版本快照列表',
  `edit_history` json DEFAULT NULL COMMENT '编辑历史',
  `permissions` json DEFAULT NULL COMMENT '授权用户ID列表',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status_updated` (`user_id`,`status`,`updated_at`),
  KEY `idx_deleted_at` (`deleted_at`),
  KEY `idx_user_deleted_updated` (`user_id`,`deleted_at`,`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='创作项目表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ws_version` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '版本ID',
  `project_id` int NOT NULL COMMENT '项目ID',
  `version_number` int NOT NULL COMMENT '版本号',
  `description` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '版本说明',
  `snapshot_data` json DEFAULT NULL COMMENT '版本快照数据',
  `created_by` int DEFAULT NULL COMMENT '创建人ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_version` (`project_id`,`version_number`),
  KEY `idx_project_id` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目版本表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Idempotent batch materialization (20261105)
CREATE TABLE IF NOT EXISTS ws_batch_import (
 user_id INT NOT NULL,batch_id VARCHAR(32) NOT NULL,item_id VARCHAR(32) NOT NULL,
 project_id INT NULL,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,batch_id,item_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
