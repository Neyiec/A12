/**
 * [数据交互说明]
 * - 导出:
 *   - `getPublicResources`: 分页查询公共资源列表（API-83）
 * - 依赖:
 *   - `../utils/api`: 导入 `get` HTTP 工具方法
 * - 输入: 接收来自 `ResourceKnowledge.vue` 的资源筛选与分页参数
 * - 输出: 返回 Promise，resolve 时为 `Result<PageResult<ResourceVO>>`
 */
import { get } from '../utils/api'

/**
 * 分页查询公共资源列表（API-83）
 * 支持按资源类型与启用状态筛选（status：1=启用 0=停用）
 * @param {{ resource_type?: string, status?: number, page?: number, size?: number }} [params] - 筛选与分页参数
 * @returns {Promise<Result<PageResult<ResourceVO>>>} 公共资源分页数据
 */
export function getPublicResources(params) {
  return get('/api/v1/admin/public-resources', params)
}
