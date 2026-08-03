/**
 * [数据交互说明]
 * - 导出: 统一响应格式构建函数、分页工具、延迟模拟
 * - 依赖: 无外部依赖
 * - 输入: 各 handler 调用构建函数生成模拟响应
 * - 输出: 标准 `Result<T>` 和 `PageResult<T>` 格式响应
 */

/**
 * 构建统一成功响应 Result<T>
 * @param data - 响应数据体
 * @param message - 描述信息，默认 "success"
 */
export function success<T>(data: T, message = 'success') {
  return { code: 200, message, data }
}

/**
 * 构建统一错误响应 Result<T>
 * @param code - 错误码（如 400、401、404 等）
 * @param message - 错误描述
 * @param data - 可选的附加数据
 */
export function error(code: number, message: string, data: unknown = null) {
  return { code, message, data }
}

/**
 * 构建分页响应 PageResult<T>
 * @param records - 当前页数据列表
 * @param total - 总记录数
 * @param page - 当前页码
 * @param size - 每页条数
 */
export function pageResult<T>(records: T[], total: number, page: number, size: number) {
  return { total, page, size, records }
}

/**
 * 从查询参数中提取分页参数
 * @param searchParams - URLSearchParams 实例
 */
export function getPagination(searchParams: URLSearchParams) {
  const page = parseInt(searchParams.get('page') || '1', 10)
  const size = parseInt(searchParams.get('size') || '10', 10)
  return { page, size }
}

/**
 * 模拟网络延迟（200-600ms 随机值，使 mock 更真实）
 */
export async function simulateDelay(): Promise<void> {
  const delay = 200 + Math.random() * 400
  return new Promise((resolve) => setTimeout(resolve, delay))
}

/**
 * 从 Authorization 请求头提取 Bearer token
 * @param authHeader - Authorization 请求头值
 */
export function extractToken(authHeader: string | null): string | null {
  if (!authHeader) return null
  const match = authHeader.match(/^Bearer\s+(.+)$/i)
  return match ? match[1] : null
}

/**
 * 生成 UUID v4 格式的唯一 ID
 */
export function generateId(prefix = ''): string {
  const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
  return prefix ? `${prefix}_${uuid.slice(0, 8)}` : uuid
}

/**
 * 当前时间戳格式化（ISO 字符串）
 */
export function now(): string {
  return new Date().toISOString()
}

/**
 * 基于当前时间偏移生成时间字符串
 * @param daysOffset - 天数偏移（负数表示过去）
 */
export function timeOffset(daysOffset: number): string {
  const date = new Date()
  date.setDate(date.getDate() + daysOffset)
  return date.toISOString()
}
