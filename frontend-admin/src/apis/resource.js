/**
 * [数据交互说明]
 * - 导出:
 *   - `getPublicResources`: 分页查询公共资源列表（API-83）
 *   - `createUploadSession`: 创建上传会话（返回 OSS 预签名 PUT URL，120 分钟有效）
 *   - `completeUpload`: 完成上传（验桶 + 启用 + 同步触发 AI 索引解析，阻塞至解析结束）
 *   - `updateResource`: 编辑资源元数据（API-87，status=1 时会触发重新索引）
 *   - `deleteResource`: 删除资源（API-89，同步清理 PG 侧向量索引）
 *   - `reparseResource`: 单资源强制重解析（force_reparse=true，阻塞至解析结束）
 *   - `getDownloadUrl`: 获取 60 分钟预签名下载 URL
 *   - `bootstrapAiIndex`: 全量重建 AI 索引（public + personal 双域，长耗时，210s 超时）
 * - 依赖:
 *   - `../utils/api`: 导入 `get` / `post` / `del` / `apiRequest` HTTP 工具方法
 * - 输入: 接收来自 `ResourceKnowledge.vue` 的筛选/分页/表单参数
 * - 输出: 返回 Promise，resolve 时为 `Result<T>` 统一响应结构
 */
import { get, post, del, apiRequest } from '../utils/api'

const pythonUrl = (path) => `${(import.meta.env.VITE_PYTHON_API_BASE_URL || '').replace(/\/$/, '')}${path}`

/** 长耗时索引操作超时（与项目 210s 约定一致，见 ai-index/bootstrap） */
const AI_INDEX_TIMEOUT = 210000

/** 上传确认/单资源重解析：Java 侧同步等待 Python 解析完成，需放宽超时 */
const SYNC_INDEX_TIMEOUT = 600000

/**
 * 分页查询公共资源列表（API-83）
 * 支持按资源类型与启用状态筛选（status：1=启用 0=停用）
 * @param {{ resource_type?: string, status?: number, page?: number, size?: number }} [params] - 筛选与分页参数
 * @returns {Promise<Result<PageResult<ResourceVO>>>} 公共资源分页数据
 */
export function getPublicResources(params) {
  return get('/api/v1/admin/public-resources', params)
}

/**
 * 创建上传会话（三段式第一段）
 * 后端写入 adm_resource（status=0, ai_index_status=pending）并签发 OSS 预签名 PUT URL
 * @param {{ resource_type: string, title: string, subject?: string, grade?: string,
 *           file_name?: string, file_type?: string, file_size?: number, description?: string }} data - 资源表单
 * @returns {Promise<Result<{upload_id: number, upload_url: string, expires_at: string}>>}
 */
export function createUploadSession(data) {
  return post('/api/v1/admin/public-resources/uploads', data)
}

/**
 * 完成上传（三段式第三段）
 * 后端仅标记 ai_index_status='indexing' 后立即返回，Python 解析在后台线程池执行——前端轮询 processing-status 获取最终状态
 * @param {number} id - 上传会话 ID（upload_id）
 * @returns {Promise<Result<ResourceVO>>} 启用后的资源数据（ai_index_status='indexing'）
 */
export function completeUpload(id) {
  return apiRequest({
    url: `/api/v1/admin/public-resources/uploads/${id}/complete`,
    method: 'post',
    timeout: SYNC_INDEX_TIMEOUT
  })
}

/**
 * 编辑资源元数据（API-87）
 * @param {number} id - 资源 ID
 * @param {{ title?: string, subject?: string, grade?: string, description?: string }} [data] - 可选更新字段
 * @returns {Promise<Result<ResourceVO>>}
 */
export function updateResource(id, data) {
  return apiRequest({
    url: `/api/v1/admin/public-resources/${id}`,
    method: 'patch',
    data,
    timeout: SYNC_INDEX_TIMEOUT
  })
}

/**
 * 删除资源（API-89）：同步清理 PG 向量索引 + OSS 对象 + MySQL 记录
 * @param {number} id - 资源 ID
 * @returns {Promise<Result<ResourceVO>>} 被删除的资源数据
 */
export function deleteResource(id) {
  return del(`/api/v1/admin/public-resources/${id}`)
}

/**
 * 单资源强制重解析（force_reparse=true）
 * 后端异步执行：仅标记 indexing 后立即返回，前端轮询 processing-status 获取最终状态
 * @param {number} id - 资源 ID
 * @returns {Promise<Result<ResourceVO>>} 资源数据（ai_index_status='indexing'）
 */
export function reparseResource(id) {
  return apiRequest({
    url: `/api/v1/admin/public-resources/${id}/reparse`,
    method: 'post',
    timeout: SYNC_INDEX_TIMEOUT
  })
}

/**
 * 获取资源下载 URL（60 分钟预签名 GET）
 * @param {number} id - 资源 ID
 * @returns {Promise<Result<{download_url: string, expires_minutes: number}>>}
 */
export function getDownloadUrl(id) {
  return get(`/api/v1/admin/public-resources/${id}/download-url`)
}

/**
 * 查询资源 AI 索引处理状态（轮询用）
 * index_status 为真实字段（pending/indexing/completed/failed）；security_check/parse_status 为后端固定值
 * @param {number} id - 资源 ID
 * @returns {Promise<Result<{index_status: string, indexed_at: string, error_msg: string}>>}
 */
export function getProcessingStatus(id) {
  return get(`/api/v1/admin/public-resources/${id}/processing-status`)
}

/**
 * 全量重建 AI 索引（public + personal 双域，长耗时）
 * @param {boolean} [forceReparse=true] - 是否强制重解析（false 时按 file_fingerprint 跳过未变化资源）
 * @returns {Promise<Result<{results: Array<{resource_key: string, status: string, error_message?: string}>}>>}
 */
export function bootstrapAiIndex(forceReparse = true) {
  return apiRequest({
    url: '/api/v1/admin/public-resources/ai-index/bootstrap',
    method: 'post',
    params: { force_reparse: forceReparse },
    timeout: AI_INDEX_TIMEOUT
  })
}

/**
 * 获取知识索引总览统计（overview，KPI 数据源）
 * 返回 PostgreSQL a12_resource_index 的真实统计：resource_count/chunk_count/groups 维度分组等
 * @returns {Promise<Result<{postgres_available: boolean, embedding_dimensions: number, resource_count: number,
 *   chunk_count: number, retrieval_log_count: number, groups: Array<{source_type: string, parse_status: string,
 *   available: boolean, allow_ai: boolean, resource_count: number, chunk_count: number}>}>>}
 */
export function getAiIndexOverview() {
  return get(pythonUrl('/api/v1/python/resources/index/overview'))
}

/**
 * 分页查询知识索引任务列表（public + personal 双域真实行）
 * 服务端筛选/分页；effective_status 已由后端用 MySQL ai_index_status 合成（indexing 优先于 PG parse_status）
 * @param {{ source_type?: string, parse_status?: string, keyword?: string, page?: number, size?: number }} [params]
 * @returns {Promise<Result<{total: number, limit: number, offset: number, items: Array<object>}>>}
 */
export function getAiIndexTasks(params) {
  const { page = 1, size = 10, ...filters } = params || {}
  return get(pythonUrl('/api/v1/python/resources/index/resources'), {
    ...filters, limit: size, offset: (page - 1) * size,
  })
}

/**
 * 获取单个资源的真实索引明细（含分块 chunks）
 * @param {string} sourceType - 来源域（public/personal）
 * @param {string|number} resourceId - 资源 ID
 * @param {number} [chunkLimit=50] - 返回分块数上限（0-200）
 * @returns {Promise<Result<object & {chunks: Array<{chunk_id: string, chunk_index: number, content: string}>}>>}
 */
export function getAiIndexResource(sourceType, resourceId, chunkLimit = 50) {
  return get(pythonUrl(`/api/v1/python/resources/index/resources/${sourceType}/${resourceId}`), { chunk_limit: chunkLimit })
}

/**
 * 知识条目真实向量检索（pgvector 混合重排，命中写入 a12_retrieval_log）
 * @param {{ query: string, source_type?: string, top_k?: number }} data - 检索参数
 * @returns {Promise<Result<{query: string, matches: Array<{resource_id: string, chunk_id: string,
 *   content: string, score: number, rank: number, match_type: string, metadata: object}>,
 *   search_mode: string, latency_ms: number}>>}
 */
export function searchAiIndex(data) {
  return post(pythonUrl('/api/v1/python/resources/index/search'), data)
}

export function rebuildCommunityIndex(afterId = 0, limit = 100) {
  return apiRequest({ url: '/api/v1/admin/community-items/reindex', method: 'post',
    params: { after_id: afterId, limit } })
}

/**
 * 单资源强制重解析（public/personal 双域统一入口，后端异步执行）
 * 后端仅标记 indexing 后立即返回，前端轮询任务列表获取最终状态
 * @param {string} sourceType - 来源域（public/personal）
 * @param {string|number} resourceId - 资源 ID
 * @returns {Promise<Result<{source_type: string, resource_id: string, status: string}>>}
 */
export function reparseAiIndex(sourceType, resourceId) {
  if (sourceType === 'community') {
    return apiRequest({ url: `/api/v1/admin/community-items/${resourceId}/reindex`, method: 'post' })
  }
  return apiRequest({
    url: `/api/v1/admin/public-resources/ai-index/${sourceType}/${resourceId}/reparse`,
    method: 'post',
    timeout: SYNC_INDEX_TIMEOUT
  })
}
