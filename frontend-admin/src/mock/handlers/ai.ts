/**
 * [数据交互说明]
 * - 导出: MSW AI 教学引擎请求处理器（API-12 ~ API-18）
 * - 依赖:
 *   - `msw`: http, HttpResponse
 *   - `../data/users`: mockSessions
 *   - `../data/common`: success, error, extractToken, generateId, now
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/ai/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { success, error, extractToken, generateId, now } from '../data/common'

/** AI 会话内存存储 */
const aiSessions = new Map<string, Record<string, unknown>>()
const aiTasks = new Map<string, Record<string, unknown>>()

export const aiHandlers = [
  // ========== API-12 创建备课会话 ==========
  http.post('/api/v1/ai/sessions', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const conversationId = generateId('conv')
    const session = {
      conversation_id: conversationId,
      user_id: user.id,
      title: body.title || '未命名会话',
      subject: body.subject || '',
      grade: body.grade || '',
      status: 'active',
      messages: body.messages || '[]',
      uploaded_refs: body.uploaded_refs || '[]',
      resource_ids: body.resource_ids || '[]',
      enable_rag: body.enable_rag ?? false,
      enable_web: body.enable_web ?? false,
      slide_count: body.slide_count || 8,
      python_session_id: null,
      plan_json: null,
      plan_confirm_status: 'pending',
      created_at: now(),
      updated_at: now(),
    }
    aiSessions.set(conversationId, session)

    // 同时创建 Java 侧任务记录
    const taskId = generateId('task')
    aiTasks.set(taskId, {
      id: taskId,
      conversation_id: conversationId,
      user_id: user.id,
      title: session.title,
      subject: session.subject,
      grade: session.grade,
      status: 'draft',
      plan_json: null,
      python_session_id: null,
      python_outline_id: null,
      plan_confirm_status: 'pending',
      exec_steps: '[]',
      created_at: now(),
      updated_at: now(),
    })

    return HttpResponse.json(success(session))
  }),

  // ========== API-13 对话中发送消息 ==========
  http.post('/api/v1/ai/sessions/:id/messages', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const sessionId = params.id as string
    const session = aiSessions.get(sessionId)
    if (!session) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })

    const body = (await request.json()) as Record<string, unknown>
    const message = body.message || body.messages || ''

    // 更新会话消息
    const messages = JSON.parse(session.messages as string || '[]')
    messages.push({ role: 'user', content: message, created_at: now() })
    // 模拟 AI 回复
    messages.push({ role: 'assistant', content: `已收到您的需求「${message}」，正在为您生成教学内容…`, created_at: now() })
    session.messages = JSON.stringify(messages)
    session.updated_at = now()
    if (body.title) session.title = body.title

    // 模拟可能的澄清问题
    const lastQuestion = Math.random() > 0.6
      ? { text: '请确认您希望的教学侧重点：A.知识讲解为主 B.课堂互动为主 C.实验探究为主？', options: ['A', 'B', 'C'] }
      : null

    return HttpResponse.json(success({
      conversation_id: sessionId,
      title: session.title,
      messages: session.messages,
      last_question: lastQuestion,
      updated_at: session.updated_at,
    }))
  }),

  // ========== API-13A 语音输入对话编排 ==========
  http.post('/api/v1/ai/sessions/:id/audio-messages', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const sessionId = params.id as string
    const session = aiSessions.get(sessionId)
    if (!session) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })

    // 模拟 ASR 转写结果
    const mockTranscript = '这是一段模拟的语音转写结果：请帮我设计一个关于细胞分裂的教学内容'
    session.messages = JSON.stringify([
      ...JSON.parse(session.messages as string || '[]'),
      { role: 'user', content: `[语音] ${mockTranscript}`, created_at: now() },
    ])
    session.updated_at = now()

    return HttpResponse.json(success({
      conversation_id: sessionId,
      title: session.title,
      messages: session.messages,
      transcript: mockTranscript,
      updated_at: session.updated_at,
    }))
  }),

  // ========== API-14 获取教学大纲 ==========
  http.get('/api/v1/ai/sessions/:id/plan', async ({ params }) => {
    const sessionId = params.id as string
    const session = aiSessions.get(sessionId)

    // 为首次请求动态生成模拟大纲
    const planJson = session?.plan_json || {
      title: session?.title || '未命名大纲',
      summary: '模拟 AI 生成的教学设计大纲',
      slide_count: (session?.slide_count as number) || 8,
      slides: Array.from({ length: (session?.slide_count as number) || 8 }, (_, i) => ({
        slide_no: i + 1,
        title: ['课程导入', '知识讲解', '案例分析', '课堂互动', '实验探究', '小组讨论', '总结归纳', '课后作业'][i] || `第${i + 1}页`,
        content_points: [`知识点 ${i + 1}-A`, `知识点 ${i + 1}-B`],
        teaching_intent: `理解与掌握核心概念`,
        visual_suggestion: '图文结合，突出重点',
      })),
    }

    const taskRecord = Array.from(aiTasks.values()).find((t) => t.conversation_id === sessionId)

    return HttpResponse.json(success({
      ...(taskRecord || {}),
      plan_json: planJson,
      python_session_id: session?.python_session_id || null,
      python_outline_id: `outline_${generateId()}`,
      plan_confirm_status: session?.plan_confirm_status || 'pending',
    }))
  }),

  // ========== API-15 确认/退回/补充大纲 ==========
  http.post('/api/v1/ai/sessions/:id/plan-confirmations', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const sessionId = params.id as string
    const session = aiSessions.get(sessionId)
    if (!session) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })

    const body = (await request.json()) as { action: string; comment?: string; plan_version: number }
    const validActions = ['confirm', 'reject', 'supplement']
    if (!validActions.includes(body.action)) {
      return HttpResponse.json(error(400, '无效操作，可选值: confirm / reject / supplement'), { status: 400 })
    }

    session.plan_confirm_status = body.action === 'confirm' ? 'confirmed' : body.action === 'reject' ? 'rejected' : 'pending'
    return HttpResponse.json(success(null, `操作成功: ${body.action}`))
  }),

  // ========== API-16 标记执行任务 ==========
  http.post('/api/v1/ai/sessions/:id/runs', async ({ params }) => {
    const sessionId = params.id as string
    const session = aiSessions.get(sessionId)
    if (!session) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })

    const taskRecord = Array.from(aiTasks.values()).find((t) => t.conversation_id === sessionId)
    if (taskRecord) {
      taskRecord.status = 'executing'
      taskRecord.exec_steps = JSON.stringify([{ step: 'waiting_python_ppt', started_at: now() }])
    }

    return HttpResponse.json(success(taskRecord || {}))
  }),

  // ========== API-17 查询任务状态 ==========
  http.get('/api/v1/ai/runs/:runId', async ({ params }) => {
    const runId = params.runId as string
    const task = aiTasks.get(runId)
    if (!task) return HttpResponse.json(error(404, '任务不存在'), { status: 404 })

    return HttpResponse.json(success({
      ...task,
      progress: 65,
      current_stage: 'generating_slides',
    }))
  }),

  // ========== API-18 SSE 事件流（简化返回 JSON 格式的模拟事件） ==========
  http.get('/api/v1/ai/runs/:runId/events', async () => {
    // SSE 在 MSW mock 中较难实现真正流式，返回模拟事件列表
    const events = [
      { event: 'stage', data: { stage: 'prepare', message: '准备生成…' } },
      { event: 'stage', data: { stage: 'generating', message: '正在生成 PPT 页面…' } },
      { event: 'progress', data: { percent: 30, message: '已完成 3/8 页' } },
      { event: 'progress', data: { percent: 60, message: '已完成 5/8 页' } },
      { event: 'stage', data: { stage: 'finalizing', message: '正在优化排版…' } },
      { event: 'complete', data: { message: '生成完毕' } },
    ]

    // 返回 SSE 格式流
    const sseText = events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n`).join('\n')
    return new HttpResponse(sseText, {
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }),
]
