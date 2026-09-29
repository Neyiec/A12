/**
 * [数据交互说明]
 * - 导出:
 *   - `useSSEChat`: SSE 流式通信 composable，封装 POST 方式的 SSE 连接
 *   - `parseSSEChunks`: 底层 SSE 帧解析函数
 * - 依赖:
 *   - `../storage/user.js`: 导入 `useUserStore` 获取认证 token
 * - 输入: 接收 SSE 请求 URL、JSON body、事件回调映射
 * - 输出: 返回 `{ connectStream, abort, isConnecting }` 控制对象
 */
import { ref } from 'vue'
import { useUserStore } from '../storage/user.js'

/**
 * 解析原始 SSE 文本缓冲区，提取完整事件帧
 * 处理跨 chunk 分割的帧：将不完整的数据保留在 remainder 中
 * @param {string} raw - 原始 SSE 文本
 * @returns {{ parsed: Array<{event: string, data: object}>, remainder: string }}
 */
export function parseSSEChunks(raw) {
  const parsed = []
  const chunks = raw.split('\n\n')
  // 最后一个 chunk 可能不完整，保留到下次解析
  const remainder = raw.endsWith('\n\n') ? '' : chunks.pop() || ''

  for (const chunk of chunks) {
    if (!chunk.trim()) continue
    const eventMatch = chunk.match(/^event:\s*(.+)$/m)
    const dataMatch = chunk.match(/^data:\s*(.+)$/m)
    if (!eventMatch || !dataMatch) continue

    const event = eventMatch[1].trim()
    let data = {}
    try {
      data = JSON.parse(dataMatch[1].trim())
    } catch {
      // 非 JSON 数据，保留原始文本
      data = { _raw: dataMatch[1].trim() }
    }
    parsed.push({ event, data })
  }

  return { parsed, remainder }
}

/**
 * SSE 流式通信 composable
 * 使用 fetch + ReadableStream 实现 POST 方式的 SSE 连接
 * （浏览器原生 EventSource 仅支持 GET 请求，API-137A 需要 POST JSON body）
 */
export function useSSEChat() {
  /** 当前 AbortController 实例，用于取消连接 */
  let abortController = null
  /** 是否正在连接中 */
  const isConnecting = ref(false)

  /**
   * 发起 POST SSE 流式连接
   * @param {string} url - SSE 端点 URL
   * @param {Object} body - JSON 请求体
   * @param {Object} callbacks - 事件回调映射
   * @param {Function} callbacks.onSession - session 事件回调
   * @param {Function} callbacks.onStage - stage 事件回调
   * @param {Function} callbacks.onQuestion - question 事件回调
   * @param {Function} callbacks.onToolResult - tool_result 事件回调
   * @param {Function} callbacks.onPrompt - prompt 事件回调
   * @param {Function} callbacks.onProgress - progress 事件回调
   * @param {Function} callbacks.onOutlineDelta - outline_delta 事件回调（旧版幻灯片大纲，已弃用）
   * @param {Function} callbacks.onDesignTextDelta - design_text_delta 事件回调（新版 Markdown 流式方案文本）
   * @param {Function} callbacks.onFinal - final 事件回调
   * @param {Function} callbacks.onError - error 事件回调
   * @param {Function} callbacks.onDone - done 事件回调
   * @returns {Promise<{abort: Function}>} 返回取消函数
   */
  async function connectStream(url, body, callbacks = {}) {
    // 取消之前的连接
    abort()

    abortController = new AbortController()
    isConnecting.value = true

    const userStore = useUserStore()
    const baseURL = url.startsWith('/api/v1/python/')
      ? (import.meta.env.VITE_PYTHON_API_BASE_URL || '')
      : (import.meta.env.VITE_API_BASE_URL || '')

    try {
      const response = await fetch(`${baseURL}${url}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${userStore.token}`,
        },
        body: JSON.stringify(body),
        signal: abortController.signal,
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        let errorMsg = `请求失败 (${response.status})`
        try {
          const errorJson = JSON.parse(errorText)
          errorMsg = errorJson.message || errorJson.detail || errorMsg
        } catch { /* 使用默认错误消息 */ }
        callbacks.onError?.({ message: errorMsg })
        isConnecting.value = false
        return { abort }
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { parsed, remainder } = parseSSEChunks(buffer)
        buffer = remainder

        for (const { event, data } of parsed) {
          dispatchEvent(event, data, callbacks)
        }
      }

      // 处理流结束后剩余的缓冲区数据
      if (buffer.trim()) {
        const { parsed } = parseSSEChunks(buffer + '\n\n')
        for (const { event, data } of parsed) {
          dispatchEvent(event, data, callbacks)
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        callbacks.onError?.({ message: error.message || '网络连接失败' })
      }
    } finally {
      isConnecting.value = false
    }

    return { abort }
  }

  /**
   * 取消当前 SSE 连接
   */
  function abort() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isConnecting.value = false
  }

  return { connectStream, abort, isConnecting }
}

/**
 * 根据事件类型分发到对应回调
 * @param {string} event - SSE 事件名
 * @param {Object} data - 解析后的事件数据
 * @param {Object} callbacks - 回调映射
 */
function dispatchEvent(event, data, callbacks) {
  switch (event) {
    case 'session':
      callbacks.onSession?.(data)
      break
    case 'stage':
      callbacks.onStage?.(data)
      break
    case 'question':
      callbacks.onQuestion?.(data)
      break
    case 'tool_result':
      callbacks.onToolResult?.(data)
      break
    case 'prompt':
      callbacks.onPrompt?.(data)
      break
    case 'progress':
      callbacks.onProgress?.(data)
      break
    case 'outline_delta':
      callbacks.onOutlineDelta?.(data)
      break
    case 'design_text_delta':
      callbacks.onDesignTextDelta?.(data)
      break
    case 'final':
      callbacks.onFinal?.(data)
      break
    case 'error':
      callbacks.onError?.(data)
      break
    case 'done':
      callbacks.onDone?.()
      break
    default:
      // 未知事件类型，静默忽略
      break
  }
}
