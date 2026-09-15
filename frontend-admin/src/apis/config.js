/**
 * [数据交互说明]
 * - 导出:
 *   - `getAiConfigs`: 查询 AI 参数配置（API-102）
 *   - `createAiConfig`: 创建/更新 AI 参数配置（API-103）
 *   - `getSystemLogs`: 分页查询系统日志
 *   - `getDashboard`: 获取数据看板聚合数据（API-107，Dashboard.vue KPI 四卡）
 *   - `listAlerts`: 分页查询派生式告警（API-108，Dashboard.vue「需要关注」区）
 *   - `acknowledgeAlert`: 确认告警（API-110，仅记审计日志）
 *   - `resolveAlert`: 解决告警（API-111，resolution 必填，仅记审计日志）
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post` HTTP 工具方法
 * - 输入: 接收来自 `SystemSettings.vue` 的配置查询与保存参数、日志分页与筛选参数；
 *   接收来自 `Dashboard.vue` 的告警筛选与处置参数
 * - 输出: 返回 Promise，resolve 时为 `Result<...>`
 */
import { get, post } from '../utils/api'

/**
 * 查询 AI 参数配置（API-102）
 * @param {{ config_group?: string }} [params] - 配置分组筛选项（如 ai_model）
 * @returns {Promise<Result<Array<ConfigVO>>>} 配置项数组（config_key/config_value 键值对）
 */
export function getAiConfigs(params) {
  return get('/api/v1/admin/ai-configs', params)
}

/**
 * 创建/更新 AI 参数配置（API-103）
 * config_key 已存在时后端执行版本递增更新（保存历史版本），否则新建配置
 * @param {{ config_group: string, config_key: string, config_value: string, description?: string }} data - 配置项
 * @returns {Promise<Result<ConfigVO>>} 保存后的配置信息
 */
export function createAiConfig(data) {
  return post('/api/v1/admin/ai-configs', data)
}

/**
 * 分页查询系统日志（API-106）
 * 支持按日志类型(log_type)、模块(module)、关键词(keyword，模糊匹配 action/detail)
 * 和时间范围(start_time/end_time，ISO 格式)筛选，结果按创建时间倒序
 * @param {{ user_id?: number, log_type?: string, module?: string, keyword?: string,
 *           start_time?: string, end_time?: string, page?: number, size?: number }} params - 分页与筛选参数
 * @returns {Promise<Result<PageResult<LogVO>>>} 后端返回日志分页数据
 */
export function getSystemLogs(params) {
  return get('/api/v1/admin/system-logs', params)
}

/**
 * 获取数据看板聚合数据（API-107）
 * 返回平铺 totals（user_count/moderation_pending_count 等 11 项）+ today（今日 6 项新增）
 * + trend_7d（近 7 日逐日 6 指标）+ distribution（8 组分布）+ quality（成功率/失败数）
 * + recent_activities（最新 10 条 sys_log）+ generated_at（数据截至时刻）
 * 后端 Redis 缓存 60s（admin:dashboard），管理端任意审计写路径自动失效缓存
 * @returns {Promise<Result<Object>>} 看板聚合 payload
 */
export function getDashboard() {
  return get('/api/v1/admin/dashboard')
}

/**
 * 分页查询告警（API-108，派生式告警：无持久化存储，恒为 open 状态）
 * level/source 为可选过滤；status 仅支持 open（查询 acknowledged/resolved 返回空页）
 * @param {{ level?: string, source?: string, status?: string, page?: number, size?: number }} [params] - 筛选与分页参数
 * @returns {Promise<Result<PageResult<Object>>>} 告警分页数据（id 为派生指纹，如 derived:export_failed）
 */
export function listAlerts(params) {
  return get('/api/v1/admin/alerts', params)
}

/**
 * 确认告警（API-110）
 * 派生式告警无持久化：仅记审计日志，告警随数据恢复自动消失
 * @param {number|string} id - 告警 ID（派生指纹）
 * @returns {Promise<Result<void>>} 确认结果
 */
export function acknowledgeAlert(id) {
  return post(`/api/v1/admin/alerts/${id}/acknowledge`)
}

/**
 * 解决告警（API-111）
 * 派生式告警无持久化：仅记审计日志（resolution 必填），告警随数据恢复自动消失
 * @param {number|string} id - 告警 ID（派生指纹）
 * @param {{ resolution: string }} data - 解决说明
 * @returns {Promise<Result<void>>} 处理结果
 */
export function resolveAlert(id, data) {
  return post(`/api/v1/admin/alerts/${id}/resolve`, data)
}
