/**
 * [数据交互说明]
 * - 导出:
 *   - `getAiConfigs`: 查询 AI 参数配置（API-102）
 *   - `createAiConfig`: 创建/更新 AI 参数配置（API-103）
 *   - `getSystemLogs`: 分页查询系统日志
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post` HTTP 工具方法
 * - 输入: 接收来自 `SystemSettings.vue` 的配置查询与保存参数、日志分页与筛选参数
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
