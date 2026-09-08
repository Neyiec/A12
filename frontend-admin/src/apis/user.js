/**
 * [数据交互说明]
 * - 导出:
 *   - `getAdminUsers`: 分页查询后台用户
 *   - `updateUserStatus`: 启用/停用/锁定用户
 *   - `createAdminUser`: 创建单个后台账号
 *   - `updateAdminUser`: 更新后台用户信息
 *   - `deleteAdminUser`: 删除后台用户（软删除）
 *   - `getAdminRoles`: 查询角色列表
 *   - `updateAdminRole`: 更新角色信息
 *   - `deleteAdminRole`: 删除角色
 *   - `updateRolePermissions`: 配置角色权限
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post`、`put`、`del`、`apiRequest` HTTP 工具方法
 * - 输入: 接收来自 `UserPermission.vue` 的分页/筛选参数、状态更新、创建账号、更新及删除数据；
 *          来自 `RoleManagement.vue` 的角色列表查询、创建、更新、删除角色及权限矩阵数据
 * - 输出: 返回 Promise，resolve 时为 `Result<PageResult<UserVO>>` / `Result<UserVO>` / `Result<void>` / `Result<Map>`
 */
import { get, post, put, del, apiRequest } from '../utils/api'

/**
 * 分页查询后台用户（API-75）
 * 按角色(user_type)、账号状态(is_active)和关键词(keyword)分页查询
 * @param {{ keyword?: string, user_type?: string, is_active?: number,
 *           page?: number, size?: number }} params - 分页与筛选参数
 * @returns {Promise<Result<PageResult<UserVO>>>} 后端返回用户分页数据
 */
export function getAdminUsers(params) {
  return get('/api/v1/admin/users', params)
}

/**
 * 启用/停用/锁定用户（API-77）
 * @param {number|string} id - 用户ID
 * @param {0|1|-1} isActive - 0=停用, 1=启用, -1=锁定
 * @returns {Promise<Result<UserVO>>} 后端返回更新后的用户信息
 */
export function updateUserStatus(id, isActive) {
  return apiRequest({ url: `/api/v1/admin/users/${id}/status`, method: 'patch', data: { is_active: isActive } })
}

/**
 * 创建单个后台账号（API-78）
 * @param {{ username: string, password: string, real_name: string, phone?: string,
 *           email?: string, user_type: string, roles: string }} data - 创建账号数据（roles 为 JSON 字符串）
 * @returns {Promise<Result<UserVO>>} 后端返回创建的用户信息
 */
export function createAdminUser(data) {
  return post('/api/v1/admin/users', data)
}

/**
 * 更新后台用户信息（API-82A）
 * 后端只更新请求体中非空的字段；不传 password 则保持原密码，is_active 的启停走 updateUserStatus
 * @param {number|string} id - 用户ID
 * @param {{ username?: string, password?: string, real_name?: string, phone?: string,
 *           email?: string, avatar?: string, roles?: string }} data - 更新数据（roles 为 JSON 字符串）
 * @returns {Promise<Result<UserVO>>} 后端返回更新后的用户信息
 */
export function updateAdminUser(id, data) {
  return put(`/api/v1/admin/users/${id}`, data)
}

/**
 * 删除后台用户（API-82B，软删除）
 * @param {number|string} id - 用户ID
 * @returns {Promise<Result<void>>} 后端返回删除结果
 */
export function deleteAdminUser(id) {
  return del(`/api/v1/admin/users/${id}`)
}

/**
 * 查询角色列表（API-80）
 * 返回全部角色及其权限矩阵（permissions 为"模块×操作" JSON 字符串，含 granted 标记）、
 * 描述、有效成员数（member_count）与启用状态（status: 1/0），按 sort_order 排序
 * @returns {Promise<Result<Array<{role_id: number, role_code: string, role_name: string,
 *           description: string, permissions: string, audit_scope: string,
 *           status: number, member_count: number, created_at: string}>>>}
 */
export function getAdminRoles() {
  return get('/api/v1/admin/roles')
}

/**
 * 创建角色（API-80A）
 * role_code 全局唯一（小写字母开头）；sort_order 缺省由后端追加到末尾
 * @param {{ role_code: string, role_name: string, description?: string,
 *           sort_order?: number, status?: number }} data - 角色数据
 * @returns {Promise<Result<Map>>} 后端返回与 API-80 列表项结构一致的角色对象（permissions 全未授权，member_count 为 0）
 */
export function createAdminRole(data) {
  return post('/api/v1/admin/roles', data)
}

/**
 * 更新角色信息（API-80B）
 * 仅更新传入的字段；role_code 不可修改；status 启停会即时影响持有者有效权限
 * @param {number|string} id - 角色ID
 * @param {{ role_name?: string, description?: string, sort_order?: number, status?: number }} data - 更新数据
 * @returns {Promise<Result<Map>>} 后端返回与 API-80 列表项结构一致的角色对象
 */
export function updateAdminRole(id, data) {
  return put(`/api/v1/admin/roles/${id}`, data)
}

/**
 * 删除角色（API-80C）
 * 硬删除：sys_user_role / sys_role_permission 关联行由外键级联清理，
 * 持有该角色的用户将立即失去对应权限
 * @param {number|string} id - 角色ID
 * @returns {Promise<Result<void>>} 后端返回删除结果
 */
export function deleteAdminRole(id) {
  return del(`/api/v1/admin/roles/${id}`)
}

/**
 * 配置角色权限（API-82）
 * 后端解析权限矩阵中 granted=true 的权限码写入 sys_role_permission，
 * 并清除该角色持有者的鉴权缓存与角色列表缓存
 * @param {number|string} id - 角色ID
 * @param {string} permissions - 权限矩阵 JSON 字符串
 *        [{moduleKey, moduleLabel, actions:[{key, label, granted}]}]
 * @returns {Promise<Result<void>>} 后端返回保存结果
 */
export function updateRolePermissions(id, permissions) {
  return put(`/api/v1/admin/roles/${id}/permissions`, { permissions })
}