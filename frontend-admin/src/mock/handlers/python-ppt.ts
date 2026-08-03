/**
 * [数据交互说明]
 * - 导出: MSW Python PPT 生成服务请求处理器（API-133 ~ API-144）
 * - 依赖: msw, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/python/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { success, error, generateId, now } from '../data/common'

/** 模板列表 */
const mockTemplates = [
  { theme: '素白风', template_name: '素白风', description: '极简白色背景，适合日常教学演示', aliases: ['简约', '白色'], is_default: true, filename: '素白风.json' },
  { theme: '科技风', template_name: '科技风', description: '深色科技感背景，适合信息技术类课程', aliases: ['科技', '技术'], is_default: false, filename: '科技风.json' },
  { theme: '中国风', template_name: '中国风', description: '传统中国元素，适合语文、历史类课程', aliases: ['中国', '传统'], is_default: false, filename: '中国风.json' },
  { theme: '清新风', template_name: '清新风', description: '清新淡雅风格，适合自然科学类课程', aliases: ['清新', '淡雅'], is_default: false, filename: '清新风.json' },
  { theme: '商务', template_name: '商务', description: '专业商务风格，适合教学汇报', aliases: ['商务', '专业'], is_default: false, filename: '商务.json' },
]

/** 内存存储 */
const pythonSessions = new Map<string, Record<string, unknown>>()
const presentations = new Map<string, Record<string, unknown>>()
const lessonPlans = new Map<string, Record<string, unknown>>()

/** 生成模拟 PPT HTML */
function mockSlideHtml(slideNo: number, title: string): string {
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>body{font-family:"Microsoft YaHei",sans-serif;margin:0;padding:60px;width:1280px;height:720px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;align-items:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff} h1{font-size:48px;margin-bottom:20px} p{font-size:24px;opacity:.9}</style></head><body><h1>${title}</h1><p>第 ${slideNo} 页 - 模拟生成内容</p></body></html>`
}

export const pythonPptHandlers = [
  // ========== API-133 健康检查 ==========
  http.get('/api/v1/python/health', async () => {
    return HttpResponse.json(success({
      status: 'ok',
      service: 'a12-python-ppt-service',
      version: '0.1.0',
      model_ready: true,
      asr_model: 'whisper-1',
      quality_pipeline: true,
      max_html_retries: 3,
    }))
  }),

  // ========== API-134A 语音转写 ASR ==========
  http.post('/api/v1/python/audio/asr', async () => {
    return HttpResponse.json(success({
      text: '请帮我设计一个关于细胞分裂的初中生物教学内容，包含8页PPT，要求有课堂互动环节。',
      language: 'zh',
      model: 'whisper-1',
      status: 'completed',
      error_message: null,
      filename: 'audio_recording.wav',
      content_type: 'audio/wav',
    }))
  }),

  // ========== API-134 获取模板列表 ==========
  http.get('/api/v1/python/templates', async () => {
    return HttpResponse.json(success({
      total: mockTemplates.length,
      default_theme: '素白风',
      templates: mockTemplates,
    }))
  }),

  // ========== API-135 上传参考资料 ==========
  http.post('/api/v1/python/resources/upload', async () => {
    return HttpResponse.json(success({
      resource_id: generateId('res'),
      filename: 'reference.pdf',
      content_type: 'application/pdf',
      text_length: 2048,
      text_preview: '这是一段模拟的教材文本内容…光合作用是绿色植物利用光能…',
    }))
  }),

  // ========== API-135-1 同步资源索引 ==========
  http.post('/api/v1/python/resources/index/sync', async () => {
    return HttpResponse.json(success({
      resource_key: `public:1`,
      status: 'indexed',
      text_length: 3500,
      chunk_count: 5,
      error_message: null,
    }))
  }),

  // ========== API-135-2 批量初始化索引 ==========
  http.post('/api/v1/python/resources/index/bootstrap', async () => {
    return HttpResponse.json(success({ total: 3, indexed: 2, skipped: 1, failed: 0, results: [] }))
  }),

  // ========== API-135-3 更新索引metadata ==========
  http.patch('/api/v1/python/resources/index/metadata', async () => {
    return HttpResponse.json(success({ resource_key: 'public:1', status: 'updated', available: false, allow_ai: false }))
  }),

  // ========== API-135-4 删除索引 ==========
  http.delete('/api/v1/python/resources/index/:sourceType/:resourceId', async ({ params }) => {
    return HttpResponse.json(success({ resource_key: `${params.sourceType}:${params.resourceId}`, status: 'deleted' }))
  }),

  // ========== API-136 生成大纲 ==========
  http.post('/api/v1/python/outlines/generate', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const slideCount = (body.slide_count as number) || 8
    const title = (body.title as string) || '未命名课程'

    const outlineId = generateId('outline')
    const slides = Array.from({ length: slideCount }, (_, i) => ({
      slide_no: i + 1,
      title: ['课程导入', '知识讲解(上)', '知识讲解(下)', '案例分析', '课堂互动', '小组讨论', '总结归纳', '课后作业'][i] || `第${i + 1}页`,
      content_points: [`核心要点 ${i + 1}-A：相关概念定义与背景`, `核心要点 ${i + 1}-B：实际应用与拓展思考`],
      teaching_intent: i === 0 ? '激发学习兴趣，建立问题情境' : i === slideCount - 1 ? '巩固所学内容，布置拓展任务' : '理解与掌握核心概念',
      visual_suggestion: i === 0 ? '封面式大标题配合关键词云' : '左文右图，关键概念加粗高亮',
    }))

    return HttpResponse.json(success({
      outline_id: outlineId,
      title,
      summary: `关于「${title}」的教学设计大纲，共 ${slideCount} 页`,
      slide_count: slideCount,
      outline: { outline_id: outlineId, title, summary: '', slide_count: slideCount, slides },
      slides,
    }))
  }),

  // ========== API-137 修改大纲 ==========
  http.post('/api/v1/python/outlines/update', async () => {
    const outlineId = generateId('outline')
    return HttpResponse.json(success({
      outline_id: outlineId,
      title: '已修改的大纲',
      summary: '根据用户要求修改后的教学设计大纲',
      slide_count: 10,
      outline: { outline_id: outlineId, title: '已修改的大纲', slide_count: 10, slides: [] },
      slides: [],
    }))
  }),

  // ========== API-137A 对话式 SSE 大纲生成 ==========
  http.post('/api/v1/python/outlines/chat/stream', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const sessionId = (body.session_id as string) || generateId('outline_chat')
    const userMessage = body.message as string || ''

    // 模拟 SSE 流式响应
    const outlineId = generateId('outline')
    const events = [
      `event: session\ndata: {"user_id":"${body.user_id || '10001'}","session_id":"${sessionId}"}\n`,
      `event: stage\ndata: {"stage":"parse_input","message":"正在解析输入…"}\n`,
      `event: stage\ndata: {"stage":"build_prompt","message":"正在构建生成提示…"}\n`,
    ]

    // 模拟需要澄清
    if (!body.known_context && !userMessage.includes('年级') && !userMessage.includes('学科')) {
      events.push(`event: question\ndata: {"question":"为了更好地为您生成大纲，请补充以下信息：\\n1. 适用的年级和学科\\n2. 希望的教学侧重点（知识讲解/课堂互动/实验探究）"}\n`)
    } else {
      events.push(`event: stage\ndata: {"stage":"generate_outline","message":"正在生成大纲…"}\n`)
      events.push(`event: outline_delta\ndata: {"slide":{"slide_no":1,"title":"课程导入","content_points":["引入主题","激发兴趣"]}}\n`)
      events.push(`event: final\ndata: {"outline_id":"${outlineId}","title":"大纲标题","outline":{"outline_id":"${outlineId}"},"slides":[]}\n`)
    }
    events.push(`event: done\ndata: {}\n`)

    return new HttpResponse(events.join('\n'), {
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
    })
  }),

  // ========== API-137B 查询大纲对话会话 ==========
  http.get('/api/v1/python/outlines/chat/sessions', async ({ request }) => {
    const url = new URL(request.url)
    const userId = url.searchParams.get('user_id')
    return HttpResponse.json(success({
      user_id: userId,
      sessions: [
        { session_id: generateId('outline_chat'), title: '光合作用课件', intent: 'generate_outline', status: 'active', updated_at: now() },
      ],
    }))
  }),

  // ========== API-137C 教师画像 ==========
  http.get('/api/v1/python/teacher-style/profile', async ({ request }) => {
    const url = new URL(request.url)
    const userId = url.searchParams.get('user_id')
    return HttpResponse.json(success({
      user_id: userId,
      profile: { preferred_style: 'interactive', common_subjects: ['生物', '化学'], avg_slide_count: 10 },
      postgres_available: true,
    }))
  }),

  // ========== API-138 生成整套 PPT ==========
  http.post('/api/v1/python/presentations/generate', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const outline = (body.outline as Record<string, unknown>) || {}
    const slidesData = (outline.slides as Array<Record<string, unknown>>) || []
    const slideCount = slidesData.length || 8
    const title = (body.title as string) || '未命名PPT'

    const presentationId = generateId('ppt')
    const slides = slidesData.map((s, i) => ({
      slide_no: s.slide_no || i + 1,
      title: s.title || `第${i + 1}页`,
      html: mockSlideHtml((s.slide_no as number) || i + 1, (s.title as string) || `第${i + 1}页`),
      notes: (s.teaching_intent as string) || '',
      metadata: {},
    }))

    // 补足页数
    while (slides.length < slideCount) {
      const i = slides.length
      slides.push({ slide_no: i + 1, title: `第${i + 1}页`, html: mockSlideHtml(i + 1, `第${i + 1}页`), notes: '', metadata: {} })
    }

    const presentation = {
      presentation_id: presentationId,
      title,
      slide_count: slides.length,
      slides,
      html: slides.map((s) => s.html).join('\n'),
    }
    presentations.set(presentationId, presentation)

    return HttpResponse.json(success(presentation))
  }),

  // ========== API-139 修改单页 PPT ==========
  http.post('/api/v1/python/presentations/slides/modify', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const slideNo = body.slide_no as number
    return HttpResponse.json(success({
      presentation_id: body.presentation_id || '',
      slide_no: slideNo,
      html: mockSlideHtml(slideNo, `已修改 - 第 ${slideNo} 页`),
      change_summary: `根据指令「${body.instruction}」修改了第 ${slideNo} 页`,
      metadata: {},
    }))
  }),

  // ========== API-139A 整套课件修改 ==========
  http.post('/api/v1/python/presentations/modify', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const slidesInput = (body.slides as Array<Record<string, unknown>>) || []

    // 模拟修改后的 slides
    const modifiedSlides = slidesInput.map((s, i) => ({
      ...s,
      title: `${s.title || `第${i + 1}页`} (已修改)`,
      html: mockSlideHtml(i + 1, `${s.title || `第${i + 1}页`} (已修改)`),
    }))

    return HttpResponse.json(success({
      presentation_id: body.presentation_id || generateId('ppt'),
      title: (body.title as string) || '已修改课件',
      slide_count: modifiedSlides.length,
      slides: modifiedSlides,
      html: modifiedSlides.map((s) => s.html).join('\n'),
      change_summary: `根据指令「${body.instruction}」进行了全局修改`,
      operations: [{ type: 'modify', slides: modifiedSlides.map((_, i) => i + 1) }],
      modified_slide_nos: modifiedSlides.map((_, i) => i + 1),
      metadata: {},
    }))
  }),

  // ========== API-140 HTML 校验 ==========
  http.post('/api/v1/python/presentations/html/validate', async () => {
    return HttpResponse.json(success({
      valid: true,
      errors: [],
      warnings: [{ type: 'style', message: '建议使用 CSS 变量统一管理颜色' }],
    }))
  }),

  // ========== API-141 导出 PPTX ==========
  http.post('/api/v1/python/presentations/export/pptx', async () => {
    // 返回模拟的 PPTX 二进制数据
    const mockPptxData = new Uint8Array([80, 75, 3, 4]) // ZIP magic bytes (PPTX 是 ZIP)
    return new HttpResponse(mockPptxData, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'Content-Disposition': 'attachment; filename="mock_presentation.pptx"',
      },
    })
  }),

  // ========== API-142 生成教案 JSON ==========
  http.post('/api/v1/python/lesson-plans/generate', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const lessonPlanId = generateId('lp')
    const lessonPlan = {
      lesson_plan_id: lessonPlanId,
      title: body.title || '未命名教案',
      subject: body.subject || '',
      grade: body.grade || '',
      duration_minutes: body.duration_minutes || 45,
      teaching_goals: body.teaching_goals || '',
      key_points: ['知识点一', '知识点二'],
      difficult_points: ['难点一'],
      teaching_methods: ['讲授法', '探究法'],
      teaching_resources: ['多媒体课件', '实验器材'],
      lesson_process: [
        { stage: '导入', duration: 5, content: '通过生活实例引入课程主题' },
        { stage: '新授', duration: 25, content: '系统讲解核心知识点' },
        { stage: '练习', duration: 10, content: '课堂练习与即时反馈' },
        { stage: '总结', duration: 5, content: '归纳本节课重点内容' },
      ],
      classroom_activities: [{ name: '小组讨论', duration: 8, description: '分组讨论案例分析' }],
      blackboard_design: '板书结构设计…',
      homework: [{ type: '书面', content: '完成课后习题1-5' }],
      assessment: { formative: '课堂提问', summative: '课后作业' },
      reflection: '',
    }
    lessonPlans.set(lessonPlanId, lessonPlan)
    return HttpResponse.json(success(lessonPlan))
  }),

  // ========== API-143 导出教案 DOCX ==========
  http.post('/api/v1/python/lesson-plans/export/docx', async () => {
    const mockDocxData = new Uint8Array([80, 75, 3, 4]) // ZIP magic bytes
    return new HttpResponse(mockDocxData, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'Content-Disposition': 'attachment; filename="mock_lesson_plan.docx"',
      },
    })
  }),

  // ========== API-144 生成互动模块 ==========
  http.post('/api/v1/python/interactive-modules/generate', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const moduleId = generateId('im')
    const moduleType = (body.module_type as string) || 'animation'

    const interactionHtml = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>body{font-family:"Microsoft YaHei",sans-serif;margin:0;padding:40px;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh} .container{text-align:center;max-width:800px} h1{font-size:36px;color:#e94560;margin-bottom:20px} .interactive-area{padding:30px;background:rgba(255,255,255,.05);border-radius:12px;margin:20px 0} button{padding:12px 30px;font-size:18px;background:#e94560;color:#fff;border:none;border-radius:8px;cursor:pointer} button:hover{background:#c73650}</style></head><body><div class="container"><h1>${body.title || '互动模块'}</h1><p>${body.topic || ''}</p><div class="interactive-area"><p>🎯 ${moduleType === 'quiz_game' ? '知识问答互动区' : '动画演示区'}</p><button onclick="alert(\'互动完成！\')">开始互动</button></div></div></body></html>`

    return HttpResponse.json(success({
      module_id: moduleId,
      title: body.title || '互动模块',
      module_type: moduleType,
      topic: body.topic || '',
      html: interactionHtml,
      embed_mode: body.embed_mode || 'standalone',
      usage_suggestions: ['可在新授课环节使用', '建议配合小组合作学习'],
      metadata: {},
    }))
  }),
]
