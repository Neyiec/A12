/**
 * [数据交互说明]
 * - 导出:
 *   - `getAdminUsers`: 分页查询后台用户
 *   - `updateUserStatus`: 启用/停用/锁定用户
 *   - `createAdminUser`: 创建单个后台账号
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post`、`apiRequest` HTTP 工具方法
 * - 输入: 接收来自 `UserPermission.vue` 的分页/筛选参数、状态更新及创建账号数据
 * - 输出: 返回 Promise，resolve 时为 `Result<PageResult<UserVO>>` / `Result<UserVO>`
 */
import { get, post, apiRequest } from '../utils/api'

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