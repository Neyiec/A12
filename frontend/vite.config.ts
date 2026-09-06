import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

const frontendDir = fileURLToPath(new URL('.', import.meta.url))

/** 读取本地配置文件，不把密钥暴露给 Vite 客户端 bundle。 */
function readKeyValueFile(filePath: string) {
  try {
    return Object.fromEntries(
      readFileSync(filePath, 'utf8')
        .split(/\r?\n/)
        .map((line) => line.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/))
        .filter(Boolean)
        .map((match) => [match![1], match![2].replace(/^(['"])(.*)\1$/, '$2')])
    )
  } catch {
    return {}
  }
}

function readLlmConfig(env: Record<string, string>) {
  const pythonEnv = readKeyValueFile(resolve(frontendDir, '../backend-python/A12-PY/.env'))
  return {
    apiKey: env.OPENAI_API_KEY || process.env.OPENAI_API_KEY || pythonEnv.OPENAI_API_KEY || '',
    baseUrl: env.OPENAI_BASE_URL || process.env.OPENAI_BASE_URL || pythonEnv.OPENAI_BASE_URL || 'https://api.openai.com/v1',
    model: env.OPENAI_MODEL || process.env.OPENAI_MODEL || pythonEnv.OPENAI_MODEL || 'gpt-4o-mini',
  }
}

function readRequestBody(req: any): Promise<Record<string, unknown>> {
  return new Promise((resolveBody, reject) => {
    let raw = ''
    req.on('data', (chunk: Buffer | string) => {
      raw += chunk.toString()
      if (raw.length > 512 * 1024) reject(new Error('请求内容过大'))
    })
    req.on('end', () => {
      try {
        const parsed = JSON.parse(raw || '{}')
        resolveBody(parsed && typeof parsed === 'object' ? parsed : {})
      } catch {
        reject(new Error('请求格式无效'))
      }
    })
    req.on('error', reject)
  })
}

function sendJson(res: any, status: number, body: Record<string, unknown>) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(body))
}

/**
 * 本地开发专用的大模型转发入口。
 * API Key 只在 Vite Node 进程中读取并转发到 OpenAI-compatible 服务，不进入浏览器。
 */
function createLocalLlmChatMiddleware(env: Record<string, string>) {
  const config = readLlmConfig(env)
  const baseUrl = config.baseUrl.replace(/\/+$/, '')
  const endpoint = baseUrl.endsWith('/chat/completions') ? baseUrl : `${baseUrl}/chat/completions`

  return async (req: any, res: any, next: () => void) => {
    if (req.method !== 'POST') return next()

    try {
      if (!config.apiKey) {
        return sendJson(res, 503, { code: 503, message: '未配置大模型 API Key，请检查 Python 服务 .env' })
      }
      const body = await readRequestBody(req)
      const inputMessages = Array.isArray(body.messages) ? body.messages : []
      const isOutlineRepair = body.mode === 'outline-repair'
      const isWorkbenchIntent = body.mode === 'workbench-intent'
      const messages = inputMessages
        .filter((item: any) => item && (item.role === 'user' || item.role === 'assistant') && String(item.content || '').trim())
        .map((item: any) => ({ role: item.role, content: String(item.content).trim() }))
        .slice(-16)
      if (!messages.length) return sendJson(res, 400, { code: 400, message: '消息不能为空' })

      const systemPrompt = isOutlineRepair
        ? '你是资深教学设计专家。当前任务是修复一份重复的大纲，只输出严格 JSON，不要 Markdown、解释或代码围栏。必须让每一页承担不同的教学任务，标题、要点、教学意图和视觉建议都要与页面主题匹配。'
        : isWorkbenchIntent
          ? '你是创作工作台的意图路由器。请以最后一条教师消息为准，结合当前页面和最近对话判断教师是在讨论，还是要求系统实际改变当前 PPT。只要教师要求新增、删除、重写、替换、调整、移动、排版、补充、应用方案，或用自然表达要求“把它做出来/按这个改/继续完成”，即使没有出现“修改”二字，也属于 revision；只有提问、分析、解释、征求建议、评价、寒暄，且没有要求落地执行时才属于 discussion。不要根据 AI 之前说“会做/已完成”就把教师的确认句当成 discussion。只输出严格 JSON，不要 Markdown、解释或代码围栏，格式必须是 {"intent":"discussion"或"revision"}。'
          : '你是智核，面向教师的中文教学助手。当前是普通主对话，不要擅自进入备课表单，不要强制索取课程、年级或学科。请直接、自然、简洁地回答用户问题；不要虚构“讨论模式”或“修改模式”，也不要要求教师切换模式。只有用户明确要求生成课件、PPT、教案或备课时，才说明可以开始备课。'

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${config.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: config.model,
          stream: true,
          temperature: isWorkbenchIntent ? 0 : 0.45,
          ...(isWorkbenchIntent ? { max_tokens: 48 } : {}),
          messages: [
            {
              role: 'system',
              content: systemPrompt,
            },
            ...messages,
          ],
        }),
      })

      if (!response.ok || !response.body) {
        const detail = await response.text()
        return sendJson(res, response.status || 502, {
          code: response.status || 502,
          message: `大模型请求失败${detail ? `：${detail.slice(0, 240)}` : ''}`,
        })
      }

      res.statusCode = 200
      res.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
      res.setHeader('Cache-Control', 'no-cache, no-transform')
      res.setHeader('Connection', 'keep-alive')
      res.setHeader('X-Accel-Buffering', 'no')

      const reader = response.body.getReader()
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          res.write(Buffer.from(value))
        }
      } finally {
        res.end()
      }
    } catch (error: any) {
      if (res.headersSent) {
        res.end()
      } else {
        sendJson(res, 502, { code: 502, message: error?.message || '大模型连接失败' })
      }
    }
  }
}

function localLlmChatPlugin(env: Record<string, string>) {
  return {
    name: 'a12-local-llm-chat',
    configureServer(server: any) {
      server.middlewares.use('/api/dev/llm/chat', createLocalLlmChatMiddleware(env))
    },
  }
}

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  const defaultApiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8088'
  const javaApiProxyTarget = env.VITE_JAVA_API_PROXY_TARGET || defaultApiProxyTarget
  const pythonApiProxyTarget = env.VITE_PYTHON_API_PROXY_TARGET || defaultApiProxyTarget
  
  return {
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    plugins: [vue(), tailwindcss(), localLlmChatPlugin(env)],
    server: {
      port: 5173,
      proxy: {
        // 开发环境可将大模型/PPT请求直接发给 Python 服务；业务会话请求仍走 Java 网关。
        '/api/v1/python': {
          target: pythonApiProxyTarget,
          changeOrigin: true
        },
        '/api': {
          target: javaApiProxyTarget,
          changeOrigin: true
        },
        // '/content': {
        //   target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL,
        //   changeOrigin: true,
        //   rewrite: (path) => path
        // }
      }
    }
  }
})
