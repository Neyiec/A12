/**
 * [数据交互说明]
 * - 导出:
 *   - `getModerationTasks`: 分页查询内容审核任务（API-90）
 *   - `createModerationDecision`: 提交审核决定（API-91）
 *   - `getReports`: 分页查询社区举报（API-95）
 *   - `resolveReport`: 处理举报（API-96）
 * - 依赖:
 *   - `../utils/api`: 导入 `get`、`post` HTTP 工具方法
 * - 输入: 接收来自 `ContentAudit.vue` 的审核/举报筛选与分页参数、审核与举报处理参数
 * - 输出: 返回 Promise，resolve 时为 `Result<...>`
 */
import { get, post } from '../utils/api'

/**
 * 分页查询内容审核任务（API-90）
 * 返回 audit_type=audit 的审核记录，支持按状态与目标类型筛选
 * @param {{ status?: string, target_type?: string, handler_id?: number,
 *           page?: number, size?: number }} [params] - 筛选与分页参数
 * @returns {Promise<Result<PageResult<AuditVO>>>} 审核任务分页数据
 */
export function getModerationTasks(params) {
  return get('/api/v1/admin/moderation/tasks', params)
}

/**
 * 提交审核决定（API-91）
 * 仅允许处理 pending 状态的任务；approve→内容公开、reject→内容下架、rework→内容退回草稿
 * @param {number} id - 审核任务 ID
 * @param {{ action: 'approve' | 'reject' | 'rework', comment?: string }} data - 审核动作与处理意见
 * @returns {Promise<Result<void>>} 提交结果
 */
export function createModerationDecision(id, data) {
  return post(`/api/v1/admin/moderation/tasks/${id}/decisions`, data)
}

/**
 * 分页查询社区举报（API-95）
 * 返回 audit_type=report 的举报记录，支持按状态筛选
 * @param {{ status?: string, page?: number, size?: number }} [params] - 筛选与分页参数
 * @returns {Promise<Result<PageResult<AuditVO>>>} 举报分页数据
 */
export function getReports(params) {
  return get('/api/v1/admin/reports', params)
}

/**
 * 处理举报（API-96）
 * 仅允许处理 pending 状态的举报；approve/offline→内容下架、ignore/reject→内容不变、restore→内容恢复公开
 * @param {number} id - 举报 ID
 * @param {{ action: 'approve' | 'offline' | 'ignore' | 'reject' | 'restore', comment?: string }} data - 处理动作与处理意见
 * @returns {Promise<Result<void>>} 处理结果
 */
export function resolveReport(id, data) {
  return post(`/api/v1/admin/reports/${id}/resolution`, data)
}
