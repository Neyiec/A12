/**
 * [数据交互说明]
 * - 导出: `startMockServer` — 在 Node.js 环境启动 MSW Server（用于测试）
 * - 依赖:
 *   - `msw/node`: setupServer
 *   - `./handlers`: 聚合的全部 API mock 处理器
 * - 输入: 被 Vitest/Jest 等测试 setup 文件引用
 * - 输出: 启动 Node 端请求拦截，返回 mock 响应
 *
 * 使用方式（在 vitest.setup.ts 中）：
 *   import { startMockServer } from './mock/node'
 *   beforeAll(() => startMockServer())
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/** Node 端 MSW Server 实例 */
export const server = setupServer(...handlers)

/**
 * 启动 MSW Server（Node 端，用于单元/集成测试）
 * 默认 listen 拦截所有请求
 */
export function startMockServer(): void {
  server.listen({
    onUnhandledRequest: 'bypass',
  })
  console.log('[MSW] Mock Server 已启动（Node 环境）')
}

/**
 * 关闭 MSW Server，清理拦截器
 */
export function stopMockServer(): void {
  server.close()
}

/**
 * 重置 MSW Server 中的所有处理器到初始状态
 */
export function resetMockServer(): void {
  server.resetHandlers()
}
