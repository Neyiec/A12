/**
 * [数据交互说明]
 * - 导出:
 *   - `getExportTemplates`: 分页查询后台导出模板
 *   - `createExportTemplate`: 创建导出模板
 *   - `replaceExportTemplate`: 替换导出模板（覆盖 Python 侧模板文件）
 *   - `deleteExportTemplate`: 删除导出模板
 *   - `downloadExportTemplate`: 下载模板 JSON 文件（Blob）
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post`、`del`、`apiRequest` HTTP 工具方法
 * - 输入: 接收来自 `SystemSettings.vue` 的筛选/分页参数与模板创建/替换数据
 * - 输出: 返回 Promise，resolve 时为 `Result<PageResult<TemplateVO>>` / `Result<Map>` / axios response
 */
import { get, post, del, apiRequest } from '../utils/api'

/**
 * 分页查询后台导出模板（API-98）
 * 按模板类型(export_type)、状态(status)、关键词(keyword)分页查询
 * @param {{ export_type?: string, status?: string, keyword?: string,
 *           page?: number, size?: number }} params - 分页与筛选参数
 * @returns {Promise<Result<PageResult<TemplateVO>>>} 后端返回模板分页数据
 */
export function getExportTemplates(params) {
  return get('/api/v1/admin/export-templates', params)
}

/**
 * 创建导出模板（API-95）
 * 注意：目前仅支持 PPTX 模板（export_type 固定 pptx）；template_data 必须是模板 JSON 文件的文本内容（含 html_template 字段）
 * @param {{ name: string, export_type: string, template_data: string, description?: string }} data - 模板数据
 * @returns {Promise<Result<{id: string, version: number}>>} 后端返回创建结果（id 即 Python 侧 theme）
 */
export function createExportTemplate(data) {
  return post('/api/v1/admin/export-templates', data)
}

/**
 * 替换导出模板（API-100，PATCH /{id}）
 * id 即 Python 侧 theme；template_data 为新模板 JSON 文件文本内容，后端整体覆盖原模板文件
 * @param {number|string} id - 模板ID（theme）
 * @param {{ name: string, export_type: string, template_data: string, description?: string }} data - 模板数据
 * @returns {Promise<Result<{id: string, version: number}>>} 后端返回替换结果
 */
export function replaceExportTemplate(id, data) {
  return apiRequest({ url: `/api/v1/admin/export-templates/${id}`, method: 'patch', data })
}

/**
 * 删除导出模板（DELETE /{id}）
 * id 即 Python 侧 theme；默认模板（素白风）后端拒绝删除
 * @param {number|string} id - 模板ID（theme）
 * @returns {Promise<Result<void>>} 后端返回删除结果
 */
export function deleteExportTemplate(id) {
  return del(`/api/v1/admin/export-templates/${id}`)
}

/**
 * 下载导出模板 JSON 文件（GET /{id}/download）
 * 返回完整 axios response（blob 由拦截器原样透传），由调用方转 Blob 触发浏览器下载
 * @param {number|string} id - 模板ID（theme）
 * @returns {Promise<Object>} axios response（response.data 为 Blob）
 */
export function downloadExportTemplate(id) {
  return apiRequest({ url: `/api/v1/admin/export-templates/${id}/download`, method: 'get', responseType: 'blob' })
}
