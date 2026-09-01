/**
 * [数据交互说明]
 * - 导出:
 *   - `getExportTemplates`: 分页查询后台导出模板（API-98）
 * - 依赖:
 *   - `../utils/api`: 导入 `get` HTTP 工具方法
 * - 输入: 接收来自 `SystemSettings.vue` 的筛选/分页参数
 * - 输出: 返回 Promise，resolve 时为 `Result<PageResult<TemplateVO>>`
 */
import { get } from '../utils/api'

/**
 * 分页查询导出模板（API-98）
 * 按模板类型(export_type)、状态(status)、关键词(keyword)分页查询
 * @param {{ export_type?: string, status?: string, keyword?: string,
 *           page?: number, size?: number }} params - 分页与筛选参数
 * @returns {Promise<Result<PageResult<TemplateVO>>>} 后端返回模板分页数据
 */
export function getExportTemplates(params) {
  return get('/api/v1/admin/export-templates', params)
}
