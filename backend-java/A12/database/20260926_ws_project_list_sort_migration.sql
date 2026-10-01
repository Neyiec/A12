-- ws_project 列表查询排序索引迁移
-- 背景:
--   /api/v1/projects 列表查询仅按 user_id 过滤、按 updated_at DESC 排序时,
--   既有索引 idx_user_status_updated(user_id, status, updated_at) 因中间列 status 未参与过滤, 无法提供有序扫描,
--   MySQL 退化为 filesort 并将 snapshots / edit_history 大 JSON 列一并联入排序缓冲区,
--   在默认 sort_buffer_size=256KB 下触发 ERROR 1038 (Out of sort memory)。
-- 变更:
--   1. 新增 (user_id, deleted_at, updated_at) 复合索引, 使 deleted_at IS NULL 过滤后的 updated_at 排序
--      由索引有序扫描(Backward index scan)提供, 不再 filesort;
--   2. 配合 WsProjectMapper.xml 的 findByQuery 改为只查询列表所需列(不返回 snapshots / edit_history)。
-- 说明:
--   a12_schema.sql 已同步该索引(全新初始化无需执行本脚本); 本脚本用于已有库执行一次。

SET NAMES utf8mb4;

ALTER TABLE ws_project
  ADD KEY idx_user_deleted_updated (user_id, deleted_at, updated_at);