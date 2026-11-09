/**
 * [数据交互说明]
 * - 导出模板（数据源为 Python PPT 服务 a12_ppt/templates/*.json，模板 id 即 Python 侧 theme）:
 *   - `getExportTemplates`: 查询全部导出模板（Python 全量返回，分页/筛选由前端完成）
 *   - `createExportTemplate`: 创建导出模板
 *   - `replaceExportTemplate`: 替换导出模板（覆盖 Python 侧模板文件）
 *   - `deleteExportTemplate`: 删除导出模板
 *   - `downloadExportTemplate`: 下载模板 JSON 文件（Blob）
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post`、`del`、`apiRequest` HTTP 工具方法
 *   - `../utils/request`: `/api/v1/python/**` 请求自动切换 `VITE_PYTHON_API_BASE_URL`（开发环境走 Vite 代理）
 * - 输入: 接收来自 `SystemSettings.vue` 的筛选/分页参数与模板创建/替换数据
 * - 输出: 返回 Promise，resolve 时为 `Result<{total, default_theme, templates}>` / `Result<Map>` / axios response
 */
import { get, post, del, apiRequest } from '../utils/api'

/**
 * 查询全部导出模板（API-134 GET /api/v1/python/templates）
 * Python 全量返回且不支持查询参数；export_type 固定 pptx、status 固定 published、version 固定 1
 * @returns {Promise<Result<{total: number, default_theme: string, templates: Array<{theme, template_name, description, aliases, is_default, filename, size}>>}>>}
 */
export function getExportTemplates() {
  return get('/api/v1/python/templates')
}

/**
 * 创建导出模板（POST /api/v1/python/templates）
 * template_data 必须是模板 JSON 文件的文本内容（含 html_template 字段）；name 即 Python 侧 theme
 * @param {{ name: string, export_type?: string, template_data: string, description?: string }} data - 模板数据
 * @returns {Promise<Result<{theme: string, filename: string}>>} 后端返回创建结果（theme 即模板 id）
 */
export function createExportTemplate(data) {
  return post('/api/v1/python/templates', data)
}

/**
 * 替换导出模板（PATCH /api/v1/python/templates/{theme}）
 * id 即 Python 侧 theme；template_data 为新模板 JSON 文件文本内容，Python 整体覆盖原模板文件；默认模板（素白风）拒绝替换
 * @param {number|string} id - 模板ID（theme）
 * @param {{ name?: string, export_type?: string, template_data: string, description?: string }} data - 模板数据
 * @returns {Promise<Result<{theme: string, filename: string}>>} 后端返回替换结果
 */
export function replaceExportTemplate(id, data) {
  return apiRequest({ url: `/api/v1/python/templates/${id}`, method: 'patch', data })
}

/**
 * 删除导出模板（DELETE /api/v1/python/templates/{theme}）
 * id 即 Python 侧 theme；默认模板（素白风）后端拒绝删除
 * @param {number|string} id - 模板ID（theme）
 * @returns {Promise<Result<void>>}
 */
export function deleteExportTemplate(id) {
  return del(`/api/v1/python/templates/${id}`)
}

/**
 * 下载导出模板 JSON 文件（GET /api/v1/python/templates/{theme}/file）
 * 返回完整 axios response（blob 由拦截器原样透传），由调用方转 Blob 触发浏览器下载
 * @param {number|string} id - 模板ID（theme）
 * @returns {Promise<Object>} axios response（response.data 为 Blob）
 */
export function downloadExportTemplate(id) {
  return apiRequest({ url: `/api/v1/python/templates/${id}/file`, method: 'get', responseType: 'blob' })
}
