-- A12 项目 RBAC 权限模型重构迁移脚本
-- 内容:
--   1. 新建 sys_role / sys_permission / sys_user_role / sys_role_permission 四张表
--      (与库内其他表不同, 两张关联表带物理外键 ON DELETE CASCADE, 作为 RBAC 模块的新约定,
--       删除用户/角色/权限时自动清理关联行, 不会产生孤儿数据)
--   2. 写入角色、权限及超级管理员默认权限的种子数据
--   3. 将 sys_user 既有数据（user_type / roles JSON）迁移到 sys_user_role
--   4. 删除 sys_user 的 user_type / roles / permissions 三列及其索引
-- 执行顺序: 自上而下依次执行；种子与数据迁移均为幂等(INSERT IGNORE)，可重复执行
-- 注意: 数据迁移必须在删除三列之前执行

SET NAMES utf8mb4;

-- ===================================================================
-- 1. 新建表
-- ===================================================================

CREATE TABLE IF NOT EXISTS sys_role (
  id INT NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  role_code VARCHAR(50) NOT NULL COMMENT '角色标识: super_admin/admin/content_auditor/knowledge_curator/teacher',
  role_name VARCHAR(50) NOT NULL COMMENT '角色名称(展示用)',
  description VARCHAR(255) DEFAULT NULL COMMENT '角色说明',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '展示排序',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用: 1启用/0停用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_role_code (role_code),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色表';

CREATE TABLE IF NOT EXISTS sys_permission (
  id INT NOT NULL AUTO_INCREMENT COMMENT '权限ID',
  perm_code VARCHAR(100) NOT NULL COMMENT '权限标识: {module_key}:{action_key}, 如 users:view',
  perm_name VARCHAR(50) NOT NULL COMMENT '权限名称(展示用), 如 用户管理-查看',
  module_key VARCHAR(50) NOT NULL COMMENT '所属模块: dashboard/users/roles/audit/resources/settings',
  module_label VARCHAR(50) NOT NULL COMMENT '模块中文名, 如 用户管理',
  action_key VARCHAR(50) NOT NULL COMMENT '操作: view/create/edit/delete/audit/export/stats/modify/resetPassword/configPerm',
  action_label VARCHAR(50) NOT NULL COMMENT '操作中文名, 如 查看',
  description VARCHAR(255) DEFAULT NULL COMMENT '权限说明',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用: 1启用/0停用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_perm_code (perm_code),
  UNIQUE KEY uk_module_action (module_key, action_key),
  KEY idx_module (module_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统权限表';

CREATE TABLE IF NOT EXISTS sys_user_role (
  id INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  user_id INT NOT NULL COMMENT '用户ID, 关联 sys_user.id',
  role_id INT NOT NULL COMMENT '角色ID, 关联 sys_role.id',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_role (user_id, role_id),
  KEY idx_role_id (role_id),
  CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
  CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES sys_role(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户-角色关联表';

CREATE TABLE IF NOT EXISTS sys_role_permission (
  id INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  role_id INT NOT NULL COMMENT '角色ID, 关联 sys_role.id',
  permission_id INT NOT NULL COMMENT '权限ID, 关联 sys_permission.id',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_role_perm (role_id, permission_id),
  KEY idx_permission_id (permission_id),
  CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES sys_role(id) ON DELETE CASCADE,
  CONSTRAINT fk_rp_perm FOREIGN KEY (permission_id) REFERENCES sys_permission(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色-权限关联表';

-- ===================================================================
-- 2. 种子数据: 角色
--    来源: 前端 ROLE_OPTIONS + 原 user_type 取值 + 原角色映射(getRoleKey)
-- ===================================================================

INSERT IGNORE INTO sys_role (id, role_code, role_name, description, sort_order, status) VALUES
  (1, 'super_admin',      '超级管理员',   '拥有后台全部权限',                 1, 1),
  (2, 'admin',            '系统管理员',   '后台日常管理',                     2, 1),
  (3, 'content_auditor',  '内容审核员',   '社区内容审核与举报处理',           3, 1),
  (4, 'knowledge_curator','知识库维护员', '公共资源与知识库维护',             4, 1),
  (5, 'teacher',          '普通教师',     '前台教学功能用户',                 5, 1);

-- ===================================================================
-- 3. 种子数据: 权限（6 模块 × 21 个权限点，与前端 PERMISSION_MODULES 对应）
-- ===================================================================

INSERT IGNORE INTO sys_permission (perm_code, perm_name, module_key, module_label, action_key, action_label, status) VALUES
  ('dashboard:view',   '数据看板-查看',           'dashboard', '数据看板',           'view',          '查看', 1),
  ('dashboard:export', '数据看板-导出',           'dashboard', '数据看板',           'export',        '导出', 1),
  ('dashboard:stats',  '数据看板-统计',           'dashboard', '数据看板',           'stats',         '统计', 1),
  ('users:view',          '用户管理-查看',     'users', '用户管理', 'view',          '查看', 1),
  ('users:create',        '用户管理-新增',     'users', '用户管理', 'create',        '新增', 1),
  ('users:edit',          '用户管理-编辑',     'users', '用户管理', 'edit',          '编辑', 1),
  ('users:delete',        '用户管理-删除',     'users', '用户管理', 'delete',        '删除', 1),
  ('users:resetPassword', '用户管理-重置密码', 'users', '用户管理', 'resetPassword', '重置密码', 1),
  ('roles:view',       '角色管理-查看',     'roles', '角色管理', 'view',          '查看', 1),
  ('roles:create',     '角色管理-新增',     'roles', '角色管理', 'create',        '新增', 1),
  ('roles:edit',       '角色管理-编辑',     'roles', '角色管理', 'edit',          '编辑', 1),
  ('roles:delete',     '角色管理-删除',     'roles', '角色管理', 'delete',        '删除', 1),
  ('roles:configPerm', '角色管理-配置权限', 'roles', '角色管理', 'configPerm',    '配置权限', 1),
  ('audit:view',    '内容审核与社区治理-查看', 'audit', '内容审核与社区治理', 'view',   '查看', 1),
  ('audit:audit',   '内容审核与社区治理-审核', 'audit', '内容审核与社区治理', 'audit',  '审核', 1),
  ('audit:delete',  '内容审核与社区治理-删除', 'audit', '内容审核与社区治理', 'delete', '删除', 1),
  ('resources:view',   '公共资源与知识库-查看', 'resources', '公共资源与知识库', 'view',   '查看', 1),
  ('resources:edit',   '公共资源与知识库-编辑', 'resources', '公共资源与知识库', 'edit',   '编辑', 1),
  ('resources:delete', '公共资源与知识库-删除', 'resources', '公共资源与知识库', 'delete', '删除', 1),
  ('settings:view',   '系统配置-查看', 'settings', '系统配置', 'view',   '查看', 1),
  ('settings:modify', '系统配置-修改', 'settings', '系统配置', 'modify', '修改', 1);

-- 超级管理员默认拥有全部权限；其余角色的权限由管理端(API-82)自行配置
INSERT IGNORE INTO sys_role_permission (role_id, permission_id)
SELECT 1, p.id FROM sys_permission p WHERE p.status = 1;

-- ===================================================================
-- 4. 存量数据迁移: sys_user.user_type / roles JSON -> sys_user_role
--    两个来源取并集(唯一键自动去重)，确保原有 admin 判定(user_type)不丢权限:
--    ① roles JSON 数组逐元素映射 role_code
--    ② user_type 映射兜底: admin->admin, teacher->teacher, auditor->content_auditor
-- ===================================================================

-- ① 来自 roles JSON
INSERT IGNORE INTO sys_user_role (user_id, role_id, created_at)
SELECT DISTINCT u.id, r.id, NOW()
FROM sys_user u
JOIN (
  SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
) numbers
JOIN sys_role r
  ON r.role_code = JSON_UNQUOTE(JSON_EXTRACT(u.roles, CONCAT('$[', numbers.n, ']')))
WHERE u.deleted_at IS NULL
  AND u.roles IS NOT NULL
  AND JSON_VALID(u.roles)
  AND JSON_TYPE(u.roles) = 'ARRAY'
  AND numbers.n < JSON_LENGTH(u.roles);

-- ② 来自 user_type 兜底（角色与①去重后叠加，避免原 admin 用户丢失后台访问权）
INSERT IGNORE INTO sys_user_role (user_id, role_id, created_at)
SELECT u.id, r.id, NOW()
FROM sys_user u
JOIN sys_role r ON r.role_code = CASE u.user_type
    WHEN 'admin'   THEN 'admin'
    WHEN 'auditor' THEN 'content_auditor'
    WHEN 'teacher' THEN 'teacher'
    ELSE NULL END
WHERE u.deleted_at IS NULL
  AND r.id IS NOT NULL;

-- ===================================================================
-- 5. 删除 sys_user 的 user_type / roles / permissions 列及其索引
--    (必须在第 4 节之后执行)
-- ===================================================================

ALTER TABLE sys_user
  DROP KEY idx_user_type,
  DROP KEY idx_active_type,
  DROP COLUMN user_type,
  DROP COLUMN roles,
  DROP COLUMN permissions,
  ADD KEY idx_is_active (is_active);
