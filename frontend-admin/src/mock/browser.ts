/**
 * [数据交互说明]
 * - 导出: `startMockWorker` — 在浏览器环境启动 MSW Service Worker
 * - 依赖:
 *   - `msw/browser`: setupWorker
 *   - `./handlers`: 聚合的全部 API mock 处理器
 * - 输入: 被 main.ts 在 DEV 模式下调用
 * - 输出: 启动 Service Worker，拦截匹配的 HTTP 请求并返回 mock 响应
 *
 * 使用方式（在 main.ts 中）：
 *   if (import.meta.env.DEV) {
 *     const { startMockWorker } = await import('../mock/browser')
 *     await startMockWorker()
 *   }
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

/**
 * 创建 MSW Service Worker 实例
 * 配置项：onUnhandledRequest 设为 'bypass'，未匹配的请求透传给真实后端
 */
export const worker = setupWorker(...handlers)

/**
 * 启动 MSW Service Worker
 * 读取 `public/mockServiceWorker.js` 文件
 * 若 Service Worker 未就绪，控制台会打印注册 URL 以便手动复制
 */
export async function startMockWorker(): Promise<void> {
  return worker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: {
      url: '/mockServiceWorker.js',
    },
  }).then(() => {
    console.log('[MSW] Mock Service Worker 已启动，API 请求将被拦截')
  }).catch((err) => {
    console.error('[MSW] Service Worker 启动失败:', err)
  })
}
