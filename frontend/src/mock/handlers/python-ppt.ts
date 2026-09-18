/**
 * [数据交互说明]
 * - 导出: MSW Python PPT 生成服务请求处理器（API-133 ~ API-144）
 * - 依赖: msw, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/ai/engine/* 请求并返回模拟响应
 */

import { http, HttpResponse, passthrough } from 'msw'
import { success, error, generateId, now } from '../data/common'
import { mockMaterials } from '../data/resources'

const useRealPptApi = import.meta.env.VITE_USE_REAL_PPT_API === 'true'
const useRealAiApi = import.meta.env.VITE_USE_REAL_AI_API === 'true'
const useRealOutlineApi = import.meta.env.VITE_USE_REAL_OUTLINE_API === 'true'
const useRealPptOperations = useRealPptApi || useRealAiApi

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
const mockIndexResources = new Map<string, Record<string, unknown>>()
const mockIndexLogs: Record<string, unknown>[] = []

function parseIndexList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String)
  try {
    const parsed = JSON.parse(String(value || '[]'))
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch { return [] }
}

function toMockIndexResource(material: typeof mockMaterials[number]) {
  return {
    resource_key: `personal:${material.id}`,
    source_type: 'personal',
    resource_id: String(material.id),
    title: material.file_name,
    available: material.status === 1,
    allow_ai: material.allow_ai === 1,
    parse_status: material.allow_ai === 1 ? 'completed' : 'disabled',
    error_message: null,
    text_length: material.file_size > 0 ? 2048 : 0,
    chunk_count: material.allow_ai === 1 ? 5 : 0,
    metadata: {
      title: material.file_name,
      source_type: 'personal',
      resource_id: String(material.id),
      file_url: material.file_url,
      file_type: material.file_type,
      file_size: material.file_size,
      owner_user_id: String(material.user_id),
      categories: parseIndexList(material.categories),
      tags: parseIndexList(material.tags),
      access_type: material.access_type,
    },
    indexed_at: material.ai_indexed_at,
    updated_at: material.updated_at,
  }
}

function ensureMockIndexResources() {
  if (mockIndexResources.size) return
  mockMaterials.forEach((material) => mockIndexResources.set(`personal:${material.id}`, toMockIndexResource(material)))
}

/** 生成模拟 PPT HTML；Mock 模式同样体现用户选择的模板，便于离线联调。 */
function mockSlideHtml(slideNo: number, title: string, theme = '素白风'): string {
  const palettes: Record<string, { background: string; color: string; accent: string }> = {
    素白风: { background: '#f8fafc', color: '#172033', accent: '#2563eb' },
    科技风: { background: 'linear-gradient(135deg,#071426 0%,#102e52 100%)', color: '#e6f7ff', accent: '#22d3ee' },
    中国风: { background: 'linear-gradient(135deg,#f4ead7 0%,#e7d4b5 100%)', color: '#3f2d20', accent: '#a33a32' },
    清新风: { background: 'linear-gradient(135deg,#effcf6 0%,#dff4eb 100%)', color: '#173e32', accent: '#20a875' },
    商务: { background: 'linear-gradient(135deg,#edf3fb 0%,#dbe7f5 100%)', color: '#152d4f', accent: '#315f9a' },
  }
  const palette = palettes[theme] || palettes['素白风']
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>body{font-family:"Microsoft YaHei",sans-serif;margin:0;padding:60px;width:1280px;height:720px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;align-items:center;background:${palette.background};color:${palette.color}} h1{font-size:48px;margin-bottom:20px;border-bottom:5px solid ${palette.accent};padding-bottom:16px} p{font-size:24px;opacity:.82}.theme{position:absolute;right:54px;bottom:36px;color:${palette.accent};font-size:16px;font-weight:700}</style></head><body><h1>${title}</h1><p>第 ${slideNo} 页 - 模拟生成内容</p><span class="theme">${theme}</span></body></html>`
}

export const pythonPptHandlers = [
  // ========== API-133 健康检查 ==========
  http.get('/api/v1/ai/engine/health', async () => {
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
  http.post('/api/v1/ai/engine/audio/asr', async () => {
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
  http.get('/api/v1/ai/engine/templates', async () => {
    if (useRealPptApi) {
      return passthrough()
    }
    return HttpResponse.json(success({
      total: mockTemplates.length,
      default_theme: '素白风',
      templates: mockTemplates,
    }))
  }),

  // ========== API-135 上传参考资料 ==========
  http.post('/api/v1/ai/engine/resources/upload', async () => {
    return HttpResponse.json(success({
      resource_id: generateId('res'),
      filename: 'reference.pdf',
      content_type: 'application/pdf',
      text_length: 2048,
      text_preview: '这是一段模拟的教材文本内容…光合作用是绿色植物利用光能…',
    }))
  }),

  // ========== API-135-1 同步资源索引 ==========
  http.post('/api/v1/ai/engine/resources/index/sync', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    const sourceType = body.source_type === 'public' ? 'public' : 'personal'
    const resourceId = String(body.resource_id || '1')
    const resourceKey = `${sourceType}:${resourceId}`
    const current = {
      resource_key: resourceKey,
      source_type: sourceType,
      resource_id: resourceId,
      title: body.title || '未命名资源',
      available: body.available !== false,
      allow_ai: body.allow_ai !== false,
      parse_status: 'completed',
      error_message: null,
      text_length: 3500,
      chunk_count: 5,
      metadata: body.metadata || { file_url: body.file_url, file_type: body.file_type, file_size: body.file_size },
      indexed_at: now(),
      updated_at: now(),
    }
    mockIndexResources.set(resourceKey, current)
    return HttpResponse.json(success({ resource_key: resourceKey, status: 'indexed', text_length: 3500, chunk_count: 5, error_message: null }))
  }),

  // ========== API-135-2 批量初始化索引 ==========
  http.post('/api/v1/ai/engine/resources/index/bootstrap', async ({ request }) => {
    const body = await request.json() as { resources?: Record<string, unknown>[]; force_reparse?: boolean }
    const resources = body.resources || []
    resources.forEach((resource) => {
      const sourceType = resource.source_type === 'public' ? 'public' : 'personal'
      const resourceId = String(resource.resource_id || '')
      if (!resourceId) return
      const resourceKey = `${sourceType}:${resourceId}`
      mockIndexResources.set(resourceKey, {
        resource_key: resourceKey,
        source_type: sourceType,
        resource_id: resourceId,
        title: resource.title || '未命名资源',
        available: resource.available !== false,
        allow_ai: resource.allow_ai !== false,
        parse_status: 'completed',
        error_message: null,
        text_length: 3500,
        chunk_count: 5,
        metadata: resource.metadata || {},
        indexed_at: now(),
        updated_at: now(),
      })
    })
    return HttpResponse.json(success({ total: resources.length, indexed: resources.length, skipped: 0, failed: 0, results: [] }))
  }),

  // ========== API-135-3 更新索引metadata ==========
  http.patch('/api/v1/ai/engine/resources/index/metadata', async () => {
    return HttpResponse.json(success({ resource_key: 'public:1', status: 'updated', available: false, allow_ai: false }))
  }),

  // ========== API-135-4 删除索引 ==========
  http.delete('/api/v1/ai/engine/resources/index/:sourceType/:resourceId', async ({ params }) => {
    const resourceKey = `${params.sourceType}:${params.resourceId}`
    mockIndexResources.delete(resourceKey)
    return HttpResponse.json(success({ resource_key: resourceKey, status: 'deleted' }))
  }),

  // ========== API-135-5 索引概览 ==========
  http.get('/api/v1/ai/engine/resources/index/overview', async () => {
    ensureMockIndexResources()
    const resources = [...mockIndexResources.values()]
    return HttpResponse.json(success({
      postgres_available: false,
      embedding_dimensions: 1536,
      resource_count: resources.length,
      chunk_count: resources.reduce((sum, item) => sum + Number(item.chunk_count || 0), 0),
      retrieval_log_count: mockIndexLogs.length,
      groups: [{ source_type: 'personal', parse_status: 'completed', available: true, allow_ai: true, resource_count: resources.length, chunk_count: resources.reduce((sum, item) => sum + Number(item.chunk_count || 0), 0) }],
      fallback_path: 'mock://a12-resource-index.json',
    }))
  }),

  // ========== API-135-6 索引资源列表 ==========
  http.get('/api/v1/ai/engine/resources/index/resources', async ({ request }) => {
    ensureMockIndexResources()
    const url = new URL(request.url)
    const sourceType = url.searchParams.get('source_type')
    const available = url.searchParams.get('available')
    const limit = Math.min(Number(url.searchParams.get('limit') || 50), 200)
    const offset = Number(url.searchParams.get('offset') || 0)
    let items = [...mockIndexResources.values()]
    if (sourceType) items = items.filter((item) => item.source_type === sourceType)
    if (available !== null) items = items.filter((item) => String(item.available) === available)
    return HttpResponse.json(success({ total: items.length, limit, offset, items: items.slice(offset, offset + limit) }))
  }),

  // ========== API-135-9 检索日志 ==========
  http.get('/api/v1/ai/engine/resources/index/logs', async ({ request }) => {
    const url = new URL(request.url)
    const limit = Math.min(Number(url.searchParams.get('limit') || 50), 200)
    const offset = Number(url.searchParams.get('offset') || 0)
    return HttpResponse.json(success({ total: mockIndexLogs.length, limit, offset, items: mockIndexLogs.slice(offset, offset + limit) }))
  }),

  // ========== API-135-8 索引检索 ==========
  http.post('/api/v1/ai/engine/resources/index/search', async ({ request }) => {
    ensureMockIndexResources()
    const body = await request.json() as { query?: string; top_k?: number }
    const query = String(body.query || '')
    const matches = [...mockIndexResources.values()].slice(0, Number(body.top_k) || 8).map((item, index) => ({
      resource_id: item.resource_id,
      chunk_id: `${item.resource_key}-chunk-${index + 1}`,
      content: `模拟检索片段：${query} 与 ${item.title} 相关的教学资料内容。`,
      metadata: item.metadata,
      base_score: 0.9 - index * 0.05,
      rerank_score: 0.9 - index * 0.05,
      score: 0.9 - index * 0.05,
      rank: index + 1,
      match_type: 'mock_hybrid',
    }))
    mockIndexLogs.unshift({ id: generateId('log'), query, resource_ids: [], match_count: matches.length, top_score: matches[0]?.score || 0, search_mode: 'mock', latency_ms: 18, metadata: {}, created_at: now() })
    return HttpResponse.json(success({ query, context: matches.map((item) => item.content).join('\n\n'), matches, search_mode: 'mock', latency_ms: 18 }))
  }),

  // ========== API-136 生成大纲 ==========
  http.post('/api/v1/ai/engine/outlines/generate', async ({ request }) => {
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
  http.post('/api/v1/ai/engine/outlines/update', async () => {
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
  http.post('/api/v1/ai/engine/outlines/chat/stream', async ({ request }) => {
    // 大纲可独立切换到真实 Python 流；不要复用 VITE_USE_REAL_AI_API，
    // 后者同时控制认证/会话 mock，打开后会让 mock 登录 token 无法访问 Java。
    if (useRealOutlineApi || useRealAiApi) {
      return passthrough()
    }

    const body = (await request.json()) as Record<string, unknown>
    const sessionId = (body.session_id as string) || generateId('outline_chat')
    const userMessage = body.message as string || ''

    // 模拟 SSE 流式响应
    const outlineId = generateId('outline')
    const extractedTitle = userMessage.length > 20 ? userMessage.slice(0, 20) : userMessage
    const outlineTitle = extractedTitle || '未命名教学设计'
    const events = [
      `event: session\ndata: {"user_id":"${body.user_id || '10001'}","session_id":"${sessionId}"}\n`,
    ]

    // 模拟需要澄清（无年级/学科信息时）
    if (!body.known_context && !userMessage.includes('年级') && !userMessage.includes('学科')) {
      events.push(`event: question\ndata: {"question":"为了更好地为您生成大纲，请补充以下信息：\\n1. 适用的年级和学科\\n2. 希望的教学侧重点（知识讲解/课堂互动/实验探究）"}\n`)
    } else {
      // 构建完整的大纲数据
      const slideCount = (body.slide_count as number) || 8
      const slideTemplates = [
        { title: '课程导入', content_points: ['通过生活情境或实验现象引入课题', '提出核心问题，激发学生探究兴趣'], teaching_intent: '创设问题情境，激活学生前概念，建立学习动机', visual_suggestion: '封面式大标题配合关键词云，搭配与课题相关的高质量实拍图或示意图' },
        { title: '知识讲解（一）', content_points: ['核心概念的定义与内涵解析', '概念产生背景与学科发展脉络'], teaching_intent: '帮助学生建立科学概念，理解知识本质', visual_suggestion: '左文右图布局，概念用加粗高亮标注，配合思维导图展示概念关系' },
        { title: '知识讲解（二）', content_points: ['原理推导与逻辑论证过程', '公式/定律的适用条件与范围'], teaching_intent: '培养逻辑推理能力，避免机械记忆', visual_suggestion: '分步骤展示推导过程，使用动画呈现逻辑链条，关键步骤用色块强调' },
        { title: '案例分析', content_points: ['典型例题的完整解析过程', '常见错误类型与纠正策略'], teaching_intent: '学以致用，在解题中巩固知识、暴露认知误区', visual_suggestion: '左侧题目原文，右侧分步解析，错误类型用红色警示框标注' },
        { title: '实验探究', content_points: ['实验目的、器材与操作步骤', '数据记录表格与结果分析'], teaching_intent: '培养科学探究能力，体验"做中学"', visual_suggestion: '实验装置示意图 + 数据记录表格，关键操作步骤配实拍照片或插画' },
        { title: '课堂互动', content_points: ['小组讨论/头脑风暴活动设计', '即时反馈问答环节'], teaching_intent: '促进深度参与，检测实时理解水平', visual_suggestion: '活泼的卡片式布局，问答区用对比色突出，活动规则用编号列表展示' },
        { title: '拓展延伸', content_points: ['跨学科联系与前沿应用', '分层拓展任务设计'], teaching_intent: '拓展学科视野，满足不同层次学生的学习需求', visual_suggestion: '时间线或知识地图布局，拓展内容用虚线框区分，配合推荐阅读链接' },
        { title: '课堂总结', content_points: ['本课知识框架回顾', '课后作业与预习任务'], teaching_intent: '结构化梳理所学内容，建立完整知识网络', visual_suggestion: '思维导图总结全课，作业区用清单样式，预习任务用箭头指向下一课' },
      ]

      const slides = slideTemplates.slice(0, slideCount).map((tpl, i) => ({
        slide_no: i + 1,
        title: tpl.title,
        content_points: tpl.content_points,
        teaching_intent: tpl.teaching_intent,
        visual_suggestion: tpl.visual_suggestion,
      }))

      // 逐页发送 outline_delta 事件
      for (const slide of slides) {
        events.push(`event: outline_delta\ndata: {"slide":${JSON.stringify(slide)}}\n`)
      }

      // 发送最终的完整大纲
      events.push(`event: final\ndata: ${JSON.stringify({
        outline_id: outlineId,
        title: outlineTitle,
        summary: `关于「${outlineTitle}」的教学设计大纲，共 ${slideCount} 页，涵盖导入、讲解、探究、互动、总结等完整教学环节`,
        slide_count: slideCount,
        outline: { outline_id: outlineId, title: outlineTitle, summary: '', slide_count: slideCount, slides },
        slides,
      })}\n`)
    }
    events.push(`event: done\ndata: {}\n`)

    return new HttpResponse(events.join('\n'), {
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
    })
  }),

  // ========== [已弃用] 假 designs/stream 端点 ==========
  // 前端大纲生成已改走 Java 网关（API-13 → API-14），不再直连当前端点。
  // 保留仅作历史参考，可直接删除；如需恢复前端直连流式可回滚。
  http.post('/api/v1/ai/engine/designs/stream', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const sessionId = (body.session_id as string) || generateId('design_chat')
    const userMessage = (body.message as string) || ''
    const designId = (body.design_id as string) || generateId('design')

    // 提取课程名称（从 message 中解析"课程名称：《xxx》"）
    const courseMatch = userMessage.match(/课程名称：《(.+?)》/)
    const courseName = courseMatch ? courseMatch[1] : '未命名课程'

    // 提取学段学科信息
    const stageMatch = userMessage.match(/(小学|初中|高中)/)
    const subjectMatch = userMessage.match(/(语文|数学|英语|物理|化学|生物|历史|地理|政治)/)
    const stage = stageMatch ? stageMatch[1] : '初中'
    const subject = subjectMatch ? subjectMatch[1] : '语文'

    const title = `《${courseName}》教学设计`

    // 构造完整的 Markdown 教学设计方案
    const markdown = `# 《${courseName}》教案

## 教材分析

《${courseName}》选自部编版${stage}${subject}教材。本课是${stage}${subject}教学体系中的重要篇目，文本语言优美、意蕴丰富，具有极高的文学鉴赏价值和教学价值。通过本课的学习，学生不仅能够掌握基础的字词句知识，还能在阅读与鉴赏中提升审美能力，培养对祖国语言文字的热爱之情。

本课在单元中处于承上启下的关键位置，既承接前文对基础知识的铺垫，又为后续类似体裁文本的学习奠定方法基础。教材编排体现了由浅入深、循序渐进的原则，符合学生的认知发展规律。

## 学情分析

${stage}学生已具备一定的自主学习能力和合作探究意识。经过前一阶段的学习，学生对本单元的知识框架有了初步了解，但仍需在教师的引导下深入理解文本内涵。

学生的主要优势在于：具备基本的信息提取能力和初步的分析概括能力；对与生活实际相关的内容有较强的兴趣。

学生可能存在的困难包括：对文本深层含义的理解不够透彻；部分学生缺乏将所学知识迁移到新情境的能力；个别学生在表达交流方面存在自信心不足的问题。

班级整体学情为**良好**水平，教学中应考虑分层设计，兼顾不同层次学生的学习需求。

## 教学目标

1. **知识与能力目标**：准确理解课文内容，掌握文中重点字词的音、形、义；能够流利、有感情地朗读课文；学习并运用本文的写作手法进行片段仿写。
2. **过程与方法目标**：通过自主阅读、小组合作探究等方式，培养分析文本、品味语言的能力；在讨论与交流中提升思维品质和语言表达能力。
3. **情感态度与价值观目标**：感受文本所蕴含的思想情感，培养健康的审美情趣；激发对中华优秀传统文化的认同感和自豪感。

## 教学重难点

1. **重点**：深入理解课文内容，把握文章的结构层次和主题思想；品味文中优美的语言，学习作者的表达技巧。
2. **难点**：理解文中关键句子的深层含义；体会作者通过语言文字所传达的细腻情感；将阅读所得转化为写作能力。

## 课时安排

本课安排 **2 课时**。

- 第一课时：整体感知课文内容，梳理文章结构，解决字词障碍，完成初步阅读理解。
- 第二课时：深入品析重点段落，探究写作特色，进行拓展延伸与当堂练笔。

## 教学过程

### 第一课时

#### 一、导入新课（约5分钟）

教师展示与课文主题相关的图片或短视频，引导学生观察并思考：

> 看到这幅画面，你想到了什么？如果用几个词语来描述你的感受，你会选择哪些词？

请2-3位学生分享感受，教师顺势引出课题，板书课题名称，并简要介绍作者及创作背景。

**设计意图**：通过直观的视觉素材创设情境，唤起学生的生活经验和情感体验，激发阅读期待，为深入理解课文做好情感铺垫。同时，以开放式问题引导学生主动思考，培养观察与表达能力。

#### 二、初读课文，整体感知（约10分钟）

1. 学生自由朗读课文，要求读准字音、读通句子，用笔圈画出不认识的生字词。
2. 教师范读或播放名家朗读音频，学生边听边标注节奏和重音。
3. 检查预习情况：通过PPT出示重点字词，指名认读，全班齐读巩固。
4. 学生默读课文，思考：这篇课文主要写了什么？用简洁的语言概括文章大意。

**设计意图**：遵循"由浅入深"的阅读规律，先解决字词障碍，再通过多种形式的朗读帮助学生熟悉文本。默读概括环节旨在培养学生的信息提取和整体把握能力，为深入分析奠定基础。

#### 三、梳理结构，划分层次（约12分钟）

1. 引导学生再次浏览课文，思考文章的段落划分依据。
2. 小组讨论：课文可以分为几个部分？每部分的主要内容是什么？
3. 各组代表汇报讨论结果，教师在黑板上绘制文章结构图。
4. 全班齐读结构图中的关键段落，巩固对文章脉络的把握。

**设计意图**：通过小组合作探究的方式，培养学生的逻辑分析能力和协作能力。结构图的绘制能够帮助学生建立文章的"骨架"，形成整体认知框架，训练结构化思维。

#### 四、精读第一部分（约13分钟）

1. 指名朗读第一部分内容。
2. 设置问题链引导学生深入思考：
   - 这一部分中，哪些词语给你留下了深刻印象？为什么？
   - 作者运用了什么样的写作手法？这样写有什么好处？
   - 从这部分内容中，你能感受到作者怎样的情感？
3. 学生自主批注，然后在小组内交流，最后全班分享。
4. 教师适时点拨关键语句的赏析角度和鉴赏方法。

**设计意图**：通过"自主批注→小组交流→全班分享"的三层递进模式，让每个学生都有思考和表达的机会。问题链的设计从感知到分析再到评价，指向不同层次的思维训练，落实语文核心素养的培养。

#### 五、课堂小结与作业布置（约5分钟）

教师带领学生回顾本节课所学内容，重申文章结构框架。

**布置作业**：
1. 熟读课文，背诵指定段落。
2. 思考：文中还有哪些你认为写得好的句子？选出一句并写一段简短的赏析文字。

### 第二课时

#### 一、复习导入（约3分钟）

通过提问方式回顾第一课时所学内容："上节课我们梳理了课文的结构，谁能来说说课文分为哪几个部分？"

**设计意图**：以复习旧知的方式快速激活学生的知识储备，建立新旧知识之间的联系，为第二课时的深入学习做好过渡。

#### 二、精读重点段落（约15分钟）

1. 聚焦课文的核心段落，学生带着问题默读。
2. 教师出示核心问题："这一段落中，作者是如何表达思想感情的？请找出具体的词句并加以分析。"
3. 学生独立完成批注（约5分钟），然后四人小组交流讨论（约5分钟）。
4. 全班分享交流，教师进行点拨和总结，适时补充背景资料帮助理解。
5. 指导学生通过朗读来表达对文本情感的理解——尝试用不同的语气、节奏朗读同一段文字，体会表达效果的差异。

**设计意图**：精读环节是阅读教学的核心。通过聚焦重点、深入品析，培养学生的文本细读能力。"朗读体验"的设计让学生在实践中感受语言文字的表现力，实现从"理解"到"感受"的升华。

#### 三、探究写作特色（约10分钟）

1. 引导学生回顾全文，思考：这篇文章在写作上有什么突出的特点？
2. 教师可以从以下角度引导学生归纳：
   - 语言特色（修辞手法的运用）
   - 结构特色（文章的谋篇布局）
   - 表达方式（叙述、描写、抒情等的综合运用）
3. 学生分组讨论，每组聚焦一个角度，做好记录准备汇报。
4. 各组汇报，教师归纳总结，板书写作特色要点。

**设计意图**：从"读"过渡到"写"，引导学生关注作者的写作技巧，为后续的写作迁移训练做铺垫。分角度讨论的方式降低了任务难度，确保每位学生都能参与其中。

#### 四、拓展延伸（约8分钟）

1. 联系生活实际：课文中所表达的情感/道理在你的生活中有过类似的体验吗？
2. 比较阅读：展示一篇与课文主题相近的短文，引导学生比较两篇文章在内容、写法上的异同。
3. 学生自由发言，教师适当引导和点评。

**设计意图**：通过联系生活实际和比较阅读，拓展学生的阅读视野，培养知识迁移能力和批判性思维。将课内学习与课外阅读有机结合，落实"大语文"教学理念。

#### 五、当堂练笔（约9分钟）

1. 教师出示练笔任务：模仿文中的写作手法，写一个100字左右的片段。
2. 学生独立写作，教师巡视指导。
3. 选取2-3篇优秀练笔进行展示和点评。
4. 同桌互评，给出改进建议。

**设计意图**：以读促写、读写结合是语文教学的重要策略。当堂练笔能够及时巩固所学的写作方法，互评环节培养学生的鉴赏能力和反思意识，实现"教—学—评"一体化。

## 课堂小结

本节课我们通过深入品析重点段落，体会了作者精湛的语言艺术和独特的写作手法。同学们在精读中学会了如何赏析文本，在练笔中尝试将阅读所得转化为写作能力。

希望同学们在今后的阅读中，也能运用今天学到的赏析方法，做一名"会读书、善思考、能表达"的优秀读者。

## 布置作业

1. **基础作业**：完成课后练习题，巩固课堂所学知识。
2. **拓展作业**：选择一篇与本文主题相似的课外文章进行阅读，写一篇200字左右的读后感。
3. **实践作业**：运用本节课学习的写作手法，完成一篇不少于400字的作文。

## 板书设计

\`\`\`
                      《${courseName}》教案

  一、整体感知 ──→ 二、精读品析 ──→ 三、拓展延伸
       │                  │                  │
   字词过关          语言赏析           比较阅读
   结构梳理          手法探究           当堂练笔
   内容概括          情感体验           联系生活
       │                  │                  │
       └──────────────────┴──────────────────┘
                    以读促写 · 读写结合
\`\`\`

## 教学反思

本教学设计以学生为主体，注重阅读方法的指导和思维能力的培养。在实施过程中，教师需要注意以下几点：

1. **时间的合理分配**：两课时内容量较为充实，教师应根据班级实际情况灵活调整各环节时间，确保重点突出、难点突破。
2. **分层教学的落实**：关注不同层次学生的学习状态，对学有余力的学生提供拓展材料，对学习有困难的学生给予更多个别指导。
3. **生成性资源的利用**：课堂上可能会出现预设之外的学生回答或疑问，教师应善于捕捉这些宝贵的"生成性资源"，因势利导，让课堂更具生命力和灵动性。
4. **评价的多元化**：综合运用教师评价、学生自评、同伴互评等多种评价方式，让评价成为促进学生学习的有效手段。`

    // 将 Markdown 按段落拆分为多个 delta 用于模拟流式推送
    const paragraphs = markdown.split('\n\n')
    const events: string[] = []

    // 1. session 事件
    events.push(`event: session\ndata: ${JSON.stringify({ session_id: sessionId, design_id: designId })}\n`)

    // 2. stage 事件序列
    events.push(`event: stage\ndata: ${JSON.stringify({ stage: 'parse_input', message: '正在分析需求…' })}\n`)
    events.push(`event: stage\ndata: ${JSON.stringify({ stage: 'tools', message: '正在检索相关资料…' })}\n`)
    events.push(`event: stage\ndata: ${JSON.stringify({ stage: 'build_prompt', message: '正在构建教学方案…' })}\n`)
    events.push(`event: stage\ndata: ${JSON.stringify({ stage: 'generate_design', message: '正在生成教学设计方案…' })}\n`)

    // 3. design_text_delta 事件 — 逐段推送 Markdown 内容
    paragraphs.forEach((para, index) => {
      if (!para.trim()) return
      // 每个段落后面加上两个换行，保持 Markdown 段落间距
      const delta = index < paragraphs.length - 1 ? para + '\n\n' : para
      events.push(`event: design_text_delta\ndata: ${JSON.stringify({ delta, index })}\n`)
    })

    // 4. final 事件
    events.push(`event: final\ndata: ${JSON.stringify({
      title,
      design_id: designId,
      markdown,
      slide_count: 12,
      session_id: sessionId,
    })}\n`)

    // 5. done 事件
    events.push(`event: done\ndata: {}\n`)

    return new HttpResponse(events.join('\n'), {
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
    })
  }),

  // ========== API-137B 查询大纲对话会话 ==========
  http.get('/api/v1/ai/engine/outlines/chat/sessions', async ({ request }) => {
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
  http.get('/api/v1/ai/engine/teacher-style/profile', async ({ request }) => {
    const url = new URL(request.url)
    const userId = url.searchParams.get('user_id')
    return HttpResponse.json(success({
      user_id: userId,
      profile: { preferred_style: 'interactive', common_subjects: ['生物', '化学'], avg_slide_count: 10 },
      postgres_available: true,
    }))
  }),

  // ========== API-138 生成整套 PPT ==========
  http.post('/api/v1/ai/engine/presentations/generate', async ({ request }) => {
    if (useRealPptApi) {
      return passthrough()
    }

    const body = (await request.json()) as Record<string, unknown>
    const outline = (body.outline as Record<string, unknown>) || {}
    const slidesData = (outline.slides as Array<Record<string, unknown>>) || []
    const slideCount = slidesData.length || 8
    const title = (body.title as string) || '未命名PPT'
    const theme = String(body.theme || '素白风')

    const presentationId = generateId('ppt')
    const slides = slidesData.map((s, i) => ({
      slide_no: s.slide_no || i + 1,
      title: s.title || `第${i + 1}页`,
      html: mockSlideHtml((s.slide_no as number) || i + 1, (s.title as string) || `第${i + 1}页`, theme),
      notes: (s.teaching_intent as string) || '',
      metadata: { theme },
    }))

    // 补足页数
    while (slides.length < slideCount) {
      const i = slides.length
      slides.push({ slide_no: i + 1, title: `第${i + 1}页`, html: mockSlideHtml(i + 1, `第${i + 1}页`, theme), notes: '', metadata: { theme } })
    }

    const presentation = {
      presentation_id: presentationId,
      title,
      slide_count: slides.length,
      slides,
      html: slides.map((s) => s.html).join('\n'),
      metadata: { theme },
    }
    presentations.set(presentationId, presentation)

    return HttpResponse.json(success(presentation))
  }),

  // ========== API-139 修改单页 PPT ==========
  http.post('/api/v1/ai/engine/presentations/slides/modify', async ({ request }) => {
    if (useRealPptOperations) {
      return passthrough()
    }

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
  http.post('/api/v1/ai/engine/presentations/modify', async ({ request }) => {
    if (useRealPptOperations) {
      return passthrough()
    }

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
  http.post('/api/v1/ai/engine/presentations/html/validate', async () => {
    return HttpResponse.json(success({
      valid: true,
      errors: [],
      warnings: [{ type: 'style', message: '建议使用 CSS 变量统一管理颜色' }],
    }))
  }),

  // ========== API-141 导出 PPTX ==========
  http.post('/api/v1/ai/engine/presentations/export/pptx', async () => {
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
  http.post('/api/v1/ai/engine/lesson-plans/generate', async ({ request }) => {
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
  http.post('/api/v1/ai/engine/lesson-plans/export/docx', async () => {
    const mockDocxData = new Uint8Array([80, 75, 3, 4]) // ZIP magic bytes
    return new HttpResponse(mockDocxData, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'Content-Disposition': 'attachment; filename="mock_lesson_plan.docx"',
      },
    })
  }),

  // ========== API-144 生成互动模块 ==========
  http.post('/api/v1/ai/engine/interactive-modules/generate', async ({ request }) => {
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
