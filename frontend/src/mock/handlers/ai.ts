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
import { success, error, extractToken, generateId, now, timeOffset } from '../data/common'

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

/** 常见课件页类型的真实教学要点模板，避免生成重复的大纲内容 */
const SLIDE_TEMPLATES = [
  {
    title: '课程导入',
    content_points: [
      '播放一段与本课主题相关的生活情境短片，引发学生好奇心',
      '抛出核心问题，请学生带着疑问进入本课学习',
    ],
    teaching_intent: '创设真实情境，激活学生已有经验，激发学习动机',
    visual_suggestion: '全屏情境大图 + 顶部醒目标题，下方给出导入问题',
  },
  {
    title: '学习目标',
    content_points: [
      '知道并说出本课的核心概念和基本方法',
      '能运用所学知识解决同类情境中的实际问题',
      '在探究与合作中体会知识的形成过程',
    ],
    teaching_intent: '让学生明确本课要达成的知识与能力、过程与方法、情感态度三维目标',
    visual_suggestion: '用三栏卡片分别呈现三维目标，配对应图标',
  },
  {
    title: '知识讲解',
    content_points: [
      '结合教材要点，分步讲解概念的定义、条件和适用范围',
      '通过典型正反例对比，帮助学生理解易混淆之处',
      '辅以板书式要点归纳，形成结构化认知',
    ],
    teaching_intent: '系统讲授核心知识，突破重难点',
    visual_suggestion: '左侧提纲式标题 + 右侧图文解析，标注关键术语',
  },
  {
    title: '案例分析',
    content_points: [
      '呈现一个贴近生活的真实案例，供学生分析与讨论',
      '围绕案例设置递进式提问，引导学生归纳规律',
    ],
    teaching_intent: '通过真实案例促进知识迁移与应用',
    visual_suggestion: '案例文本 + 思路流程图，关键结论高亮',
  },
  {
    title: '课堂互动',
    content_points: [
      '设计 2-3 个开放性问题，组织小组讨论',
      '结合趣味小游戏或抢答，增强参与感',
    ],
    teaching_intent: '调动学生主动参与，促进思维碰撞',
    visual_suggestion: '互动题目卡片 + 小组分工提示，预留计分区',
  },
  {
    title: '实验探究',
    content_points: [
      '明确实验目的、材料与步骤，强调安全注意事项',
      '引导学生记录现象、收集数据并得出结论',
    ],
    teaching_intent: '通过动手实践培养证据推理与探究能力',
    visual_suggestion: '步骤分步示意图 + 记录表格 + 现象对照图',
  },
  {
    title: '总结归纳',
    content_points: [
      '带领学生回顾本课核心概念与关键结论',
      '用结构图或思维导图梳理知识点之间的联系',
    ],
    teaching_intent: '帮助学生对所学内容进行结构化梳理与巩固',
    visual_suggestion: '思维导图式总结，重点用主题色标注',
  },
  {
    title: '课后作业',
    content_points: [
      '布置分层作业：基础巩固题与拓展探究题',
      '布置与生活相关的实践任务，鼓励知识运用',
    ],
    teaching_intent: '检测目标达成情况，推动课后延伸学习',
    visual_suggestion: '作业清单分栏呈现，标注建议时长',
  },
  {
    title: '拓展延伸',
    content_points: [
      '引用学科前沿或生活实例，开阔学生视野',
      '提出开放性思考题，鼓励课后自主探究',
    ],
    teaching_intent: '拓展知识边界，培养批判性与创造性思维',
    visual_suggestion: '延伸资料卡片 + 相关链接或二维码',
  },
  {
    title: '评价反馈',
    content_points: [
      '设计课堂小测或小组互评，当堂检验学习效果',
      '针对反馈及时调整讲评，查漏补缺',
    ],
    teaching_intent: '实现教学评一体化，即时掌握学情',
    visual_suggestion: '评价量表 + 得分统计表格',
  },
]

const buildMockPlan = (session: Record<string, unknown>) => {
  const context = parseRecord(session.context)
  const focusLabel = context.teaching_focus === 'interaction' ? '课堂互动' : context.teaching_focus === 'inquiry' ? '实验探究' : '知识讲解'
  const slideCount = Number(session.slide_count) || 8
  return {
    version: 1,
    title: session.title || '未命名大纲',
    summary: `围绕"${session.title || '当前课程'}"展开，以${focusLabel}为主要教学侧重点，注重情境化导入与结构化讲解，兼顾课堂互动与课后迁移。`,
    subject: session.subject || context.subject || '',
    grade: session.grade || context.grade || '',
    teaching_focus: context.teaching_focus || 'knowledge',
    slide_count: slideCount,
    slides: Array.from({ length: slideCount }, (_, i) => {
      const tpl = SLIDE_TEMPLATES[i % SLIDE_TEMPLATES.length]
      const repeatRound = Math.floor(i / SLIDE_TEMPLATES.length)
      return {
        slide_no: i + 1,
        title: repeatRound > 0 ? `${tpl.title}·第${repeatRound + 1}轮` : tpl.title,
        content_points: tpl.content_points,
        teaching_intent: tpl.teaching_intent,
        visual_suggestion: tpl.visual_suggestion,
      }
    }),
  }
}

/**
 * 可恢复的预置演示会话：用于演示"点击历史对话恢复"。
 * 每条含 messages（体现 初始输入→补充信息→大纲），并决定是否已有大纲与确认状态：
 *   - 会话1：已确认（恢复后进入资源生成）；
 *   - 会话2：已生成待确认（含一次修改轮次，但恢复只展示最新大纲）；
 *   - 会话3：未生成大纲、有待答澄清（恢复后进入澄清阶段）。
 */
const presetSessions: Record<string, unknown>[] = [
  {
    id: '1', user_id: 0, title: '《背影》公开课教学设计', subject: '语文', grade: '八年级',
    status: 'active', plan_confirm_status: 'confirmed',
    python_session_id: 'preset_py_1', python_outline_id: 'preset_outline_1',
    context_summary: '', last_question: null,
    created_at: timeOffset(-3), updated_at: timeOffset(-2),
    messages: JSON.stringify([
      { role: 'user', content: '帮我设计一节初中语文《背影》的公开课' },
      { role: 'user', content: '初中语文八年级人教版，课程名称：《背影》，班级学情：良好，个性化需求：注重情感体验与课堂互动' },
      { role: 'assistant', content: '已生成《背影》的大纲，共 9 页。' },
    ]),
  },
  {
    id: '2', user_id: 0, title: '勾股定理互动课件', subject: '数学', grade: '八年级',
    status: 'active', plan_confirm_status: 'pending',
    python_session_id: 'preset_py_2', python_outline_id: 'preset_outline_2',
    context_summary: '', last_question: null,
    created_at: timeOffset(-30), updated_at: timeOffset(-4),
    messages: JSON.stringify([
      { role: 'user', content: '制作一份勾股定理的互动课件' },
      { role: 'user', content: '初中数学八年级人教版，课程名称：勾股定理，班级学情：一般，个性化需求：多加入趣味互动与生活案例' },
      { role: 'user', content: '希望多加入小组探究环节' },
      { role: 'assistant', content: '已生成《勾股定理》的大纲，共 8 页。' },
    ]),
  },
  {
    id: '3', user_id: 0, title: '光合作用实验活动设计', subject: '生物', grade: '七年级',
    status: 'completed', plan_confirm_status: 'pending',
    python_session_id: 'preset_py_3', python_outline_id: null,
    context_summary: '', last_question: '请确认本课以实验探究为侧重点，还是更偏向知识讲解？',
    created_at: timeOffset(-14), updated_at: timeOffset(-7),
    messages: JSON.stringify([
      { role: 'user', content: '设计一个光合作用相关的课堂实验活动' },
    ]),
  },
]

/** 对当前用户生成"最近对话"历史（预置演示数据 + 本次运行创建的会话），按更新时间倒序。 */
const buildHistoryList = () => {
  const preset = presetSessions.map((s) => ({
    id: s.id,
    user_id: s.user_id,
    title: s.title,
    status: s.status,
    messages: s.messages,
    context_summary: s.context_summary,
    python_session_id: s.python_session_id,
    last_question: s.last_question,
    created_at: s.created_at,
    updated_at: s.updated_at,
  }))
  const dynamic = Array.from(aiSessions.values())
    .filter((session) => typeof session.user_id === 'number')
    .map((session) => ({
      id: session.conversation_id,
      user_id: session.user_id,
      title: session.title,
      status: session.status,
      messages: session.messages,
      context_summary: session.context_summary,
      python_session_id: session.python_session_id,
      last_question: session.last_question,
      created_at: session.created_at,
      updated_at: session.updated_at,
    }))
  return [...preset, ...dynamic].sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))
}

export const aiHandlers = [
  // ========== 获取单个会话详情（侧栏历史对话点击后恢复用） ==========
  http.get('/api/v1/ai/sessions/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = params.id as string
    const session = aiSessions.get(id)
    if (session) return HttpResponse.json(success({ ...session, id: session.conversation_id }))
    // 预置演示会话：按 id 兜底返回
    const preset = presetSessions.find((s) => String(s.id) === id)
    if (!preset) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })
    return HttpResponse.json(success(preset))
  }),

  // ========== 获取会话历史（最近对话） ==========
  http.get('/api/v1/ai/sessions', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    return HttpResponse.json(success(buildHistoryList()))
  }),

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
    // 大纲只在 API-13 时生成：动态会话仅当已持久化 plan_json 才返回，否则视为未生成（走澄清/补充回落）
    const planJson = session?.pending_clarification ? null : session?.plan_json || null
    if (session && planJson && !session.plan_json) session.plan_json = planJson
    if (taskRecord && planJson && !taskRecord.plan_json) taskRecord.plan_json = planJson

    // 预置演示会话：有已确认/待确认大纲则返回大纲，否则返回空（走澄清/补充回落）
    const preset = presetSessions.find((s) => String(s.id) === sessionId)
    if (preset && !session) {
      const presetPlan = preset.python_outline_id ? buildMockPlan(preset) : null
      return HttpResponse.json(success({
        id: Number(preset.id),
        conversation_id: Number(preset.id),
        title: preset.title,
        status: preset.status,
        plan_json: presetPlan,
        python_session_id: preset.python_session_id || null,
        python_outline_id: preset.python_outline_id || null,
        plan_confirm_status: preset.plan_confirm_status || 'pending',
      }))
    }

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

  // ========== API-12C 重命名会话 ==========
  http.patch('/api/v1/ai/sessions/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = params.id as string
    const body = (await request.json()) as { title?: string }
    const newTitle = (body.title || '').trim()
    if (!newTitle) return HttpResponse.json(error(400, '会话名称不能为空'), { status: 400 })

    // 动态会话：更新内存存储中的标题
    const session = aiSessions.get(id)
    if (session) {
      session.title = newTitle
      session.updated_at = now()
      return HttpResponse.json(success({ id, title: newTitle, updated_at: session.updated_at }))
    }
    // 预置演示会话：原地更新标题
    const preset = presetSessions.find((s) => String(s.id) === id)
    if (!preset) return HttpResponse.json(error(404, '会话不存在'), { status: 404 })
    preset.title = newTitle
    preset.updated_at = now()
    return HttpResponse.json(success({ id, title: newTitle, updated_at: preset.updated_at }))
  }),

  // ========== API-12D 删除会话 ==========
  http.delete('/api/v1/ai/sessions/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    if (!mockSessions.get(token || '')) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = params.id as string

    // 动态会话：从内存存储移除
    const removed = aiSessions.delete(id)
    if (removed) return HttpResponse.json(success(null, '删除成功'))
    // 预置演示会话：从预置列表中移除
    const presetIndex = presetSessions.findIndex((s) => String(s.id) === id)
    if (presetIndex >= 0) {
      presetSessions.splice(presetIndex, 1)
      return HttpResponse.json(success(null, '删除成功'))
    }
    return HttpResponse.json(error(404, '会话不存在'), { status: 404 })
  }),
]
