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

const parseRecord = (value: unknown): Record<string, unknown> => {
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    } catch {
      return {}
    }
  }
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

const findTask = (sessionId: string) => Array.from(aiTasks.values()).find((task) => task.conversation_id === sessionId)

const clarificationOptions = {
  title: [],
  subject: [
    { value: '语文', label: '语文', description: '阅读、表达与语言文字运用' },
    { value: '数学', label: '数学', description: '概念理解、方法推导与问题解决' },
    { value: '英语', label: '英语', description: '语言输入、表达与情境应用' },
    { value: '物理', label: '物理', description: '规律理解、实验观察与模型建立' },
    { value: '生物', label: '生物', description: '生命现象、证据推理与探究活动' },
  ],
  grade: [
    { value: '小学', label: '小学', description: '更直观，适合基础认知建立' },
    { value: '初中', label: '初中', description: '兼顾概念理解与课堂探究' },
    { value: '高中', label: '高中', description: '强调结构化理解与迁移应用' },
    { value: '大学或成人学习者', label: '大学或成人学习者', description: '侧重专业理解与实际应用' },
  ],
  slide_count: ['6', '8', '10', '12'].map((value) => ({ value, label: `${value} 页` })),
  teaching_focus: [
    { value: 'knowledge', label: '知识讲解为主', description: '聚焦概念、方法和关键例题' },
    { value: 'interaction', label: '课堂互动为主', description: '加入提问、讨论和即时反馈' },
    { value: 'inquiry', label: '实验探究为主', description: '通过观察、实践和证据形成理解' },
  ],
}

const clarificationMeta = {
  title: { label: '课程/PPT主题', text: '你希望这次备课围绕什么课程主题展开？', placeholder: '例如：勾股定理与生活测量' },
  subject: { label: '学科', text: '这份内容属于哪一门学科？', placeholder: '例如：数学' },
  grade: { label: '年级或受众', text: '这份内容主要面向哪个年级或学习群体？', placeholder: '例如：八年级' },
  slide_count: { label: '课件页数', text: '你希望最终课件大约包含多少页？', placeholder: '例如：8 页' },
  teaching_focus: { label: '教学侧重点', text: '你希望本次教学设计更侧重哪一种课堂目标？', placeholder: '例如：希望多加入小组讨论' },
}

const createClarificationItem = (field) => ({
  field,
  label: clarificationMeta[field]?.label || field,
  text: clarificationMeta[field]?.text || '请补充这项教学信息。',
  options: clarificationOptions[field] || [],
  allowCustom: true,
  required: true,
  placeholder: clarificationMeta[field]?.placeholder || '',
})

const buildClarificationQuestion = (session: Record<string, unknown>, message: string, context: Record<string, unknown>) => {
  const missingFields = []
  if (!session.title || session.title === '未命名会话') missingFields.push('title')
  if (!session.subject) missingFields.push('subject')
  if (!session.grade) missingFields.push('grade')

  const forceFocus = /不确定|不清楚|没想好|几个方向|侧重点|侧重/.test(message) && !context.teaching_focus
  if (forceFocus) missingFields.push('teaching_focus')
  if (!missingFields.length) return null

  const uniqueFields = [...new Set(missingFields)]
  const items = uniqueFields.map(createClarificationItem)
  const labels = items.map((item) => item.label).join('、')
  return {
    title: '需要确认的教学信息',
    text: forceFocus && uniqueFields.length === 1
      ? items[0].text
      : `为了生成更贴近你意图的大纲，请补充：${labels}。`,
    field: items[0].field,
    questions: items,
    options: items[0].options,
    allowCustom: true,
  }
}

const buildMockPlan = (session: Record<string, unknown>) => {
  const context = parseRecord(session.context)
  const focusLabel = context.teaching_focus === 'interaction' ? '课堂互动' : context.teaching_focus === 'inquiry' ? '实验探究' : '知识讲解'
  const slideCount = Number(session.slide_count) || 8
  return {
    version: 1,
    title: session.title || '未命名大纲',
    summary: `围绕${session.title || '当前课程'}展开，以${focusLabel}为主要教学侧重点。`,
    subject: session.subject || context.subject || '',
    grade: session.grade || context.grade || '',
    teaching_focus: context.teaching_focus || 'knowledge',
    slide_count: slideCount,
    slides: Array.from({ length: slideCount }, (_, i) => ({
      slide_no: i + 1,
      title: ['课程导入', '学习目标', '知识讲解', '案例分析', '课堂互动', '实验探究', '总结归纳', '课后作业'][i] || `第${i + 1}页`,
      content_points: [`核心内容 ${i + 1}-A`, `核心内容 ${i + 1}-B`],
      teaching_intent: `落实${focusLabel}目标`,
      visual_suggestion: '图文结合，突出重点',
    })),
  }
}

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
      messages: typeof body.messages === 'string' ? body.messages : JSON.stringify(body.messages || []),
      uploaded_refs: body.uploaded_refs || '[]',
      resource_ids: body.resource_ids || '[]',
      enable_rag: body.enable_rag ?? false,
      enable_web: body.enable_web ?? false,
      slide_count: body.slide_count || 8,
      python_session_id: null,
      plan_json: null,
      context: parseRecord(body.known_context),
      pending_clarification: null,
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
      status: 'planning',
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
    const message = String(body.message || body.messages || '')
    const knownContext = parseRecord(body.known_context)
    const context = { ...parseRecord(session.context), ...knownContext }
    session.context = context
    if (context.title) session.title = context.title
    if (context.subject) session.subject = context.subject
    if (context.grade) session.grade = context.grade
    if (context.slide_count) session.slide_count = Number(context.slide_count) || session.slide_count

    // 更新会话消息
    const messages = JSON.parse(session.messages as string || '[]')
    messages.push({ role: 'user', content: message, created_at: now() })
    session.messages = JSON.stringify(messages)
    session.updated_at = now()
    if (body.title) session.title = body.title

    const lastQuestion = buildClarificationQuestion(session, message, context)
    const task = findTask(sessionId)
    if (lastQuestion) {
      session.pending_clarification = lastQuestion
      messages.push({ role: 'assistant', content: lastQuestion.text, type: 'clarification', created_at: now() })
      if (task) {
        task.status = 'planning'
        task.plan_confirm_status = 'pending'
        task.plan_json = null
        task.reflections = JSON.stringify([{ type: 'clarification', question: lastQuestion.text }])
        task.updated_at = now()
      }
    } else {
      session.pending_clarification = null
      session.plan_json = buildMockPlan(session)
      messages.push({ role: 'assistant', content: '已完成意图确认，教学设计大纲已生成，等待你确认。', type: 'outline', created_at: now() })
      if (task) {
        task.status = 'planning'
        task.plan_confirm_status = 'pending'
        task.plan_json = session.plan_json
        task.python_outline_id = task.python_outline_id || `outline_${generateId()}`
        task.reflections = '[]'
        task.updated_at = now()
      }
    }
    session.messages = JSON.stringify(messages)

    return HttpResponse.json(success({
      conversation_id: sessionId,
      title: session.title,
      messages: session.messages,
      last_question: lastQuestion,
      status: lastQuestion ? 'need_clarification' : 'completed',
      outline_ready: !lastQuestion,
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

    const taskRecord = findTask(sessionId)
    const planJson = session?.pending_clarification
      ? null
      : session?.plan_json || (session ? buildMockPlan(session) : null)
    if (session && planJson && !session.plan_json) session.plan_json = planJson
    if (taskRecord && planJson && !taskRecord.plan_json) taskRecord.plan_json = planJson

    return HttpResponse.json(success({
      ...(taskRecord || {}),
      plan_json: planJson,
      python_session_id: session?.python_session_id || null,
      python_outline_id: taskRecord?.python_outline_id || (planJson ? `outline_${generateId()}` : null),
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
