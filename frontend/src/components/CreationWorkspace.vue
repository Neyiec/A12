<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Brush, ChatDotRound, CircleCheck, CopyDocument, DataBoard, Delete, Download, EditPen, FullScreen, Monitor, Picture, Plus, Promotion, VideoPlay } from '@element-plus/icons-vue'
import { addProjectComponent, addProjectPermission, confirmAiPlan, createAiRun, getAiPlan, getAiRun, getProject, getProjectVersionDiff, listProjectVersions, restoreProjectVersion, reviseProjectWithAi, saveProjectVersion, sendAiSessionMessage, updateProjectComponent } from '../apis/teacher'
import IntentClarificationDialog from './IntentClarificationDialog.vue'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const selectedSlide = ref(0)
const activePanel = ref('style')
const previewVisible = ref(false)
const planDialogVisible = ref(false)
const planLoading = ref(false)
const planSubmitting = ref(false)
const planTask = ref(null)
const planComment = ref('')
const clarificationDialogVisible = ref(false)
const clarificationSubmitting = ref(false)
const clarificationQuestion = ref(null)
const clarificationOrigin = ref('session')
const runStatus = ref('idle')
const runProgress = ref(0)
const runStage = ref('')
const versionDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const versionLoading = ref(false)
const savingComponent = ref(false)
const versions = ref([])
const versionDiff = ref(null)
const permissionUserId = ref('')
const autosaveState = ref('已保存')
let eventSource = null
let runPollTimer = null
let autosaveTimer = null
const themes = [
  { id: 'blue', name: '经典蓝', color: '#2563eb' },
  { id: 'navy', name: '沉静蓝', color: '#173d78' },
  { id: 'green', name: '自然绿', color: '#1f993f' },
  { id: 'orange', name: '活力橙', color: '#ff6b3f' },
]
const layouts = ['重点陈述', '图文并置', '双栏探究']
const messages = reactive([
  { role: 'assistant', text: '我已根据教学目标整理出一份 6 页课件。你可以直接描述想调整的内容，或在右侧细化当前页面。' },
  { role: 'user', text: '让情境导入更贴近校园生活。' },
  { role: 'assistant', text: '已将导入场景调整为校园旗杆测量任务，并保留小组讨论环节。' },
])
const slides = reactive([
  { title: '勾股定理', eyebrow: '八年级数学 · 第 1 课时', description: '从实际测量出发，发现直角三角形三边之间恒定而优雅的关系。', layout: '重点陈述', theme: 'blue' },
  { title: '情境导入', eyebrow: '01 / 生活中的直角', description: '校园里有哪些直角三角形？用旗杆与影子的测量任务开启今天的探索。', layout: '图文并置', theme: 'blue' },
  { title: '观察与猜想', eyebrow: '02 / 发现关系', description: '拖动顶点，观察两条直角边所对应正方形面积与斜边面积的变化。', layout: '图文并置', theme: 'navy' },
  { title: '公式推导', eyebrow: '03 / 建立模型', description: '将三边长度转化为面积，归纳勾股定理的表达式。', layout: '双栏探究', theme: 'green' },
  { title: '互动练习', eyebrow: '04 / 动手验证', description: '完成三组测量与计算，检验你的发现是否始终成立。', layout: '双栏探究', theme: 'orange' },
])
const current = computed(() => slides[selectedSlide.value])
const theme = computed(() => themes.find((item) => item.id === current.value.theme) || themes[0])
const unwrapResponse = (response) => response?.data || response
const sessionId = computed(() => route.query.sessionId)
const projectId = computed(() => route.query.projectId)
const project = ref(null)
const defaultSlide = (index = 1) => ({ title: `新建页面 ${index}`, eyebrow: '教学内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue' })
const parseJson = (value, fallback = {}) => { try { return typeof value === 'string' ? JSON.parse(value) : (value || fallback) } catch { return fallback } }
const clarificationFieldMeta = {
  title: { label: '课程/PPT主题', text: '你希望这次备课围绕什么课程主题展开？', options: [], placeholder: '例如：勾股定理与生活测量' },
  subject: { label: '学科', text: '这份内容属于哪一门学科？', options: ['语文', '数学', '英语', '物理', '生物'].map((value) => ({ value, label: value })), placeholder: '例如：数学' },
  grade: { label: '年级或受众', text: '这份内容主要面向哪个年级或学习群体？', options: [{ value: '小学', label: '小学', description: '更直观，适合基础认知建立' }, { value: '初中', label: '初中', description: '兼顾概念理解与课堂探究' }, { value: '高中', label: '高中', description: '强调结构化理解与迁移应用' }, { value: '大学或成人学习者', label: '大学或成人学习者', description: '侧重专业理解与实际应用' }], placeholder: '例如：八年级' },
  slide_count: { label: '课件页数', text: '你希望最终课件大约包含多少页？', options: ['6', '8', '10', '12'].map((value) => ({ value, label: `${value} 页` })), placeholder: '例如：8 页' },
  teaching_focus: { label: '教学侧重点', text: '你希望本次教学设计更侧重哪一种课堂目标？', options: [{ value: 'knowledge', label: '知识讲解为主', description: '聚焦概念、方法和关键例题' }, { value: 'interaction', label: '课堂互动为主', description: '加入提问、讨论和即时反馈' }, { value: 'inquiry', label: '实验探究为主', description: '通过观察、实践和证据形成理解' }], placeholder: '例如：希望多加入小组讨论' },
}
const inferClarificationField = (text = '') => {
  if (/学科|科目/.test(text)) return 'subject'
  if (/年级|学段|受众/.test(text)) return 'grade'
  if (/主题|课题|标题|课程/.test(text)) return 'title'
  if (/页数|页面数量|几页/.test(text)) return 'slide_count'
  if (/侧重点|重点|方向|互动|探究/.test(text)) return 'teaching_focus'
  return ''
}
const normalizeOptions = (rawOptions) => (Array.isArray(rawOptions) ? rawOptions : []).map((option, index) => {
  if (typeof option === 'string') return { value: option, label: option, description: '' }
  if (!option || typeof option !== 'object') return null
  const value = String(option.value ?? option.id ?? option.key ?? option.label ?? `option-${index + 1}`)
  return {
    value,
    label: String(option.label ?? option.title ?? option.name ?? value),
    description: String(option.description ?? option.detail ?? ''),
  }
}).filter(Boolean)

const createClarificationItem = (field, overrides = {}) => {
  const meta = clarificationFieldMeta[field] || clarificationFieldMeta.teaching_focus
  return {
    field,
    label: String(overrides.label || meta.label),
    text: String(overrides.text || meta.text),
    options: normalizeOptions(overrides.options ?? meta.options),
    allowCustom: overrides.allowCustom !== false,
    required: overrides.required !== false,
    placeholder: String(overrides.placeholder || meta.placeholder || ''),
  }
}

const missingFieldsFromQuestion = (text = '') => {
  const fields = [
    ['title', /课程\/PPT主题|课程主题|PPT主题|主题|课题|标题/],
    ['grade', /年级|学段|受众/],
    ['subject', /学科|科目/],
    ['slide_count', /页数|页面数量|几页/],
    ['teaching_focus', /侧重点|教学重点|方向|互动|探究/],
  ]
  return fields.filter(([, pattern]) => pattern.test(text)).map(([field]) => field)
}

const normalizeClarificationQuestion = (raw) => {
  if (!raw) return null
  let value = raw
  if (typeof value === 'string') {
    const parsed = parseJson(value, null)
    value = parsed && typeof parsed === 'object' ? parsed : { text: value }
  }
  if (Array.isArray(value)) value = { options: value }
  if (!value || typeof value !== 'object') return null

  const text = String(value.text || value.question || value.prompt || value.message || '为了更准确地完成创作，请补充以下信息。').trim()
  const rawQuestionItems = parseJson(value.questions, null)
  const questionItems = Array.isArray(rawQuestionItems) ? rawQuestionItems : (rawQuestionItems ? [rawQuestionItems] : [])
  const structuredItems = questionItems
    .filter((item) => item && typeof item === 'object' && (item.field || item.intent_field || item.question || item.text || item.options))
    .map((item, index) => {
      const field = String(item.field || item.intent_field || (index === 0 ? value.field || value.intent_field : '') || inferClarificationField(item.text || item.question || text) || `clarification_${index + 1}`)
      const rawOptions = parseJson(item.options || item.choices, [])
      return createClarificationItem(field, {
        ...item,
        text: item.text || item.question,
        options: normalizeOptions(rawOptions).length ? rawOptions : undefined,
        allowCustom: item.allowCustom !== false && item.allow_custom !== false,
      })
    })

  const rawOptions = parseJson(value.options || value.choices, [])
  const singleField = String(value.field || value.intent_field || inferClarificationField(text) || 'teaching_focus')
  const singleItem = createClarificationItem(singleField, {
    ...value,
    text: value.item_question || value.sub_question || '',
    options: normalizeOptions(rawOptions).length ? rawOptions : undefined,
  })
  const inferredFields = missingFieldsFromQuestion(text)
  const items = structuredItems.length
    ? structuredItems
    : inferredFields.length > 1
      ? inferredFields.map((field) => createClarificationItem(field))
      : [singleItem]

  return {
    title: String(value.title || value.heading || '需要确认的教学信息'),
    text,
    field: items[0]?.field || singleField,
    questions: items,
    options: items[0]?.options || [],
    allowCustom: value.allowCustom !== false && value.allow_custom !== false,
  }
}
const showClarificationForResponse = (response, origin = clarificationOrigin.value) => {
  const data = unwrapResponse(response) || {}
  const rawQuestion = data.last_question ?? data.clarification_question ?? data.clarification ?? data.question
  const question = normalizeClarificationQuestion(rawQuestion || (data.status === 'need_clarification' ? data : null))
  if (!question) return false
  clarificationOrigin.value = origin
  clarificationQuestion.value = question
  clarificationDialogVisible.value = true
  messages.push({ role: 'assistant', text: question.text })
  return true
}
const readableValue = (value, fallback = '') => {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'string') return value.trim() || fallback
  return String(value)
}
const readableList = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => {
      if (item && typeof item === 'object') return readableValue(item.text || item.label || item.title || item.content, '')
      return readableValue(item)
    }).filter(Boolean)
  }
  if (typeof value === 'string') return value.split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
  return value ? [readableValue(value)] : []
}
const teachingFocusLabels = { knowledge: '知识讲解', interaction: '课堂互动', inquiry: '实验探究' }
const slideTypeLabels = { cover: '课程导入', content: '核心内容', summary: '总结归纳', activity: '课堂活动', exercise: '互动练习' }
const planView = computed(() => {
  const raw = planTask.value?.plan_json
  const parsed = parseJson(raw, {})
  const root = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  const source = root.outline && typeof root.outline === 'object' ? { ...root, ...root.outline } : root
  const rawSlides = source.slides || source.pages || source.sections || []
  const slideItems = Array.isArray(rawSlides) ? rawSlides : []
  const slides = slideItems.map((slide, index) => ({
    number: Number(slide?.slide_no || slide?.page_no || index + 1) || index + 1,
    title: readableValue(slide?.title || slide?.name, `第 ${index + 1} 页`),
    type: slideTypeLabels[slide?.slide_type || slide?.type] || readableValue(slide?.slide_type || slide?.type, '教学内容'),
    points: readableList(slide?.content_points || slide?.points || slide?.key_points || slide?.content),
    intent: readableValue(slide?.teaching_intent || slide?.teaching_goal || slide?.purpose),
    visual: readableValue(slide?.visual_suggestion || slide?.visual || slide?.activity),
  }))
  return {
    available: Boolean(raw && Object.keys(source).length),
    title: readableValue(source.title, '未命名教学设计'),
    summary: readableValue(source.summary || source.description, 'AI 已根据当前备课需求整理教学结构。'),
    subject: readableValue(source.subject),
    grade: readableValue(source.grade || source.audience),
    duration: source.duration_minutes ? `${source.duration_minutes} 分钟` : '',
    focus: teachingFocusLabels[source.teaching_focus] || readableValue(source.teaching_focus, '综合教学'),
    slideCount: Number(source.slide_count || source.page_count || slides.length) || slides.length,
    goals: readableList(source.teaching_goals || source.goals || source.objectives),
    knowledgePoints: readableList(source.knowledge_points || source.key_points),
    slides,
  }
})
const pageToSlide = (page, index) => {
  const content = parseJson(page.page_content)
  return { ...defaultSlide(index + 1), ...content, componentId: page.id || page.component_id, title: content.title || page.page_title || `第 ${index + 1} 页` }
}
const loadProject = async () => {
  if (!projectId.value) return
  try {
    project.value = unwrapResponse(await getProject(projectId.value))
    const pages = Array.isArray(project.value?.pages) ? project.value.pages : []
    slides.splice(0, slides.length, ...(pages.length ? pages.map(pageToSlide) : [defaultSlide()]))
    selectedSlide.value = 0
  } catch (error) { ElMessage.error(error?.message || '项目内容加载失败') }
}
const loadTestCase = () => {
  if (!route.query.testCase) return
  const title = String(route.query.templateTitle || '临时测试案例')
  const presets = {
    'pythagorean-lab': { subject: '八年级数学', activity: '校园测量与直角三角形验证', theme: 'blue' },
    'concept-question-chain': { subject: '通用概念课', activity: '从已有认知到核心概念的问题链', theme: 'navy' },
    'circuit-interaction': { subject: '初中物理', activity: '串并联电路连接、观察与归纳', theme: 'orange' },
    'classical-chinese-intro': { subject: '高中语文', activity: '历史语境、人物关系与文本初读', theme: 'navy' },
    'photosynthesis-evidence': { subject: '初中生物', activity: '基于实验现象建立证据链', theme: 'green' },
  }
  const preset = presets[route.query.testCase] || presets['concept-question-chain']
  const visualType = route.query.testCase === 'pythagorean-lab' ? 'formula' : 'generic'
  slides.splice(0, slides.length,
    { title, eyebrow: `${preset.subject} · 测试案例`, description: `这是可编辑的临时测试案例，可继续调整内容、布局与视觉风格。`, footer: `围绕“${title}”展开完整教学活动。`, layout: '重点陈述', theme: preset.theme, visualType },
    { title: '学习目标', eyebrow: '01 / 明确方向', description: `围绕“${title}”建立知识理解、实践应用与课堂表达目标。`, footer: '明确本节课需要理解、应用和表达的核心内容。', layout: '图文并置', theme: preset.theme, visualType },
    { title: '探究活动', eyebrow: '02 / 课堂任务', description: preset.activity, footer: '在观察、讨论和实践中形成对核心问题的理解。', layout: '双栏探究', theme: preset.theme, visualType },
    { title: '交流与总结', eyebrow: '03 / 形成理解', description: '组织学生展示过程、比较证据并用自己的语言归纳本课核心结论。', footer: '用证据说明结论，并反思本节课的学习过程。', layout: '图文并置', theme: preset.theme, visualType },
  )
  messages.splice(0, messages.length, { role: 'assistant', text: `已载入“${title}”测试案例。你可以编辑页面内容，或继续描述希望调整的方向。` })
  selectedSlide.value = 0
}

const loadPlan = async ({ open = true } = {}) => {
  if (!sessionId.value) return
  planLoading.value = true
  try {
    planTask.value = unwrapResponse(await getAiPlan(sessionId.value))
    if (open && planTask.value?.plan_json) planDialogVisible.value = true
    return planTask.value
  }
  catch (error) { ElMessage.error(error?.message || '教学大纲加载失败') }
  finally { planLoading.value = false }
}
const submitPlan = async (action) => {
  if (!sessionId.value || !planTask.value) return
  const comment = planComment.value.trim()
  if (action !== 'confirm' && !comment) return ElMessage.warning('请填写补充或退回说明')
  planSubmitting.value = true
  try {
    await confirmAiPlan(sessionId.value, { action, comment, plan_version: Number(planTask.value.plan_version || planTask.value.version) || 1 })
    planDialogVisible.value = false
    if (action === 'confirm') {
      await startRun()
      return
    }

    const response = unwrapResponse(await sendAiSessionMessage(sessionId.value, {
      message: comment,
      messages: JSON.stringify([{ role: 'user', content: comment }]),
      context_summary: JSON.stringify({ plan_feedback: comment }),
    }))
    if (showClarificationForResponse(response)) return
    planComment.value = ''
    await loadPlan({ open: true })
    ElMessage.success(action === 'reject' ? '已退回大纲并重新规划' : '补充要求已提交，大纲已更新')
  } catch (error) { ElMessage.error(error?.message || '大纲操作失败') } finally { planSubmitting.value = false }
}
const normalizeRunStatus = (status) => {
  const value = String(status || '').toLowerCase()
  if (['pending', 'queued', 'running', 'executing', 'processing', 'generating'].includes(value)) return 'running'
  if (['completed', 'complete', 'success', 'succeeded', 'done'].includes(value)) return 'completed'
  if (['failed', 'failure', 'error'].includes(value)) return 'failed'
  return value || 'idle'
}
const runStageLabel = (stage) => ({
  prepare: '正在准备生成任务',
  generating: '正在生成 PPT 页面',
  generating_slides: '正在生成 PPT 页面',
  finalizing: '正在优化排版',
  presentation_generate: '正在生成课件',
  waiting_for_python_api: '等待课件生成服务响应',
}[String(stage || '')] || stage || '')
const applyRunPayload = (payload = {}, eventName = '') => {
  const status = payload.status || (eventName === 'complete' ? 'completed' : eventName === 'error' ? 'failed' : '')
  if (status) runStatus.value = normalizeRunStatus(status)
  const progress = payload.progress ?? payload.percent ?? payload.percentage
  if (progress !== undefined && progress !== null && Number.isFinite(Number(progress))) runProgress.value = Math.max(0, Math.min(100, Number(progress)))
  const stage = payload.stage || payload.current_stage || payload.status_message || payload.message
  if (stage) runStage.value = runStageLabel(stage)
  if (payload.preview?.slides && Array.isArray(payload.preview.slides)) slides.splice(0, slides.length, ...payload.preview.slides)
  if (['completed', 'failed'].includes(runStatus.value)) {
    eventSource?.close()
    clearInterval(runPollTimer)
  }
}
const connectRunEvents = (runId) => {
  eventSource?.close(); eventSource = new EventSource(`/api/v1/ai/runs/${runId}/events`)
  const handleEvent = (eventName, event) => {
    try { applyRunPayload(JSON.parse(event.data || '{}'), eventName) }
    catch { if (event.data) runStage.value = event.data }
  }
  eventSource.onmessage = (event) => handleEvent('message', event)
  ;['status', 'stage', 'progress', 'complete', 'error'].forEach((eventName) => eventSource.addEventListener(eventName, (event) => handleEvent(eventName, event)))
  eventSource.onerror = () => eventSource?.close()
  clearInterval(runPollTimer)
  runPollTimer = setInterval(async () => {
    try {
      const latest = unwrapResponse(await getAiRun(runId))
      applyRunPayload(latest || {})
      if (['completed', 'failed'].includes(runStatus.value)) clearInterval(runPollTimer)
    } catch { /* SSE remains the primary status channel */ }
  }, 3000)
}
const startRun = async () => {
  if (!sessionId.value) return
  try { const run = unwrapResponse(await createAiRun(sessionId.value)); const runId = run?.id || run?.run_id; if (!runId) throw new Error('未获取到生成任务'); runStatus.value = 'running'; runProgress.value = 0; runStage.value = '正在创建生成任务'; ElMessage.success('大纲已确认，课件正在生成'); connectRunEvents(runId); const latest = unwrapResponse(await getAiRun(runId)); applyRunPayload(latest || {}) }
  catch (error) { runStatus.value = 'failed'; ElMessage.error(error?.message || '生成任务创建失败') }
}
const submitRevision = async () => {
  const instruction = prompt.value.trim(); if (!instruction) return
  messages.push({ role: 'user', text: instruction }); prompt.value = ''
  try {
    if (projectId.value) {
      const response = unwrapResponse(await reviseProjectWithAi(projectId.value, { target_type: 'slide', target_id: String(current.value.componentId || selectedSlide.value + 1), instruction, context: JSON.stringify(current.value) }))
      const page = response?.page || response
      if (page?.id || page?.component_id) slides.splice(selectedSlide.value, 1, pageToSlide(page, selectedSlide.value))
      if (showClarificationForResponse(response, 'project')) return
    }
    else if (sessionId.value) {
      const response = unwrapResponse(await sendAiSessionMessage(sessionId.value, { message: instruction, messages: JSON.stringify([{ role: 'user', content: instruction }]) }))
      if (showClarificationForResponse(response, 'session')) return
    }
    messages.push({ role: 'assistant', text: '已收到修改要求，正在结合当前页面内容进行调整。' }); ElMessage.success('修改要求已提交')
  } catch (error) { messages.push({ role: 'assistant', text: '修改请求暂未提交成功，请稍后重试。' }); ElMessage.error(error?.message || '修改请求失败') }
}
const submitClarification = async (selection) => {
  if ((!sessionId.value && !projectId.value) || clarificationSubmitting.value || !selection?.answer) return
  clarificationSubmitting.value = true
  messages.push({ role: 'user', text: selection.answer })
  const answers = Array.isArray(selection.answers) && selection.answers.length
    ? selection.answers
    : [{ field: clarificationQuestion.value?.field || '', value: selection.value || selection.label, label: selection.label, answer: selection.answer }]
  const knownContext = selection.knownContext || answers.reduce((context, answer) => {
    if (answer.field) context[answer.field] = answer.value || answer.label || answer.answer
    return context
  }, {})
  try {
    let response
    if (sessionId.value) {
      response = unwrapResponse(await sendAiSessionMessage(sessionId.value, {
        message: selection.answer,
        messages: JSON.stringify([{ role: 'user', content: selection.answer }]),
        known_context: JSON.stringify(knownContext),
      }))
    } else {
      response = unwrapResponse(await reviseProjectWithAi(projectId.value, {
        target_type: 'slide',
        target_id: String(current.value.componentId || selectedSlide.value + 1),
        instruction: selection.answer,
        context: JSON.stringify({ page: current.value, clarification: knownContext }),
      }))
      const page = response?.page || response
      if (page?.id || page?.component_id) slides.splice(selectedSlide.value, 1, pageToSlide(page, selectedSlide.value))
    }
    if (showClarificationForResponse(response, clarificationOrigin.value)) return
    clarificationDialogVisible.value = false
    clarificationQuestion.value = null
    messages.push({ role: 'assistant', text: sessionId.value ? '已收到补充信息，我会沿着这个方向继续生成教学大纲。' : '已收到补充信息，我会沿着这个方向继续调整当前页面。' })
    if (sessionId.value) {
      await loadPlan({ open: true })
      ElMessage.success('已收到补充信息，大纲正在更新')
    } else {
      ElMessage.success('已收到补充信息')
    }
  } catch (error) {
    messages.push({ role: 'assistant', text: '补充信息暂未提交成功，请稍后重试。' })
    ElMessage.error(error?.message || '补充信息提交失败')
  } finally { clarificationSubmitting.value = false }
}
const routeQueryValue = (value) => Array.isArray(value) ? value[0] : value
const clearInitialClarification = async () => {
  if (!route.query.initialClarification) return
  const query = { ...route.query }
  delete query.initialClarification
  await router.replace({ query })
}
const initializeSessionFlow = async () => {
  if (!sessionId.value) return
  const initialRaw = routeQueryValue(route.query.initialClarification)
  if (initialRaw) {
    const initialQuestion = parseJson(initialRaw, initialRaw)
    showClarificationForResponse({ last_question: initialQuestion }, 'session')
    await clearInitialClarification()
    return
  }
  await loadPlan({ open: true })
}
onMounted(() => { loadTestCase(); initializeSessionFlow(); loadProject() })
onBeforeUnmount(() => { eventSource?.close(); clearInterval(runPollTimer) })
const currentPagePayload = () => ({ page_order: selectedSlide.value + 1, page_type: selectedSlide.value === 0 ? 'cover' : 'content', page_title: current.value.title, page_content: JSON.stringify(current.value), components: JSON.stringify([current.value]) })
const persistCurrentSlide = async () => {
  if (!projectId.value || savingComponent.value) return
  savingComponent.value = true; autosaveState.value = '保存中…'
  try {
    const payload = currentPagePayload()
    const response = current.value.componentId ? await updateProjectComponent(projectId.value, current.value.componentId, payload) : await addProjectComponent(projectId.value, payload)
    const saved = unwrapResponse(response)
    current.value.componentId ||= saved?.id || saved?.component_id
    autosaveState.value = '已保存'
  } catch (error) { autosaveState.value = '保存失败'; ElMessage.error(error?.message || '页面保存失败') } finally { savingComponent.value = false }
}
const loadVersions = async () => {
  if (!projectId.value) return ElMessage.warning('演示项目不支持版本管理')
  versionLoading.value = true; versionDialogVisible.value = true
  try { const result = unwrapResponse(await listProjectVersions(projectId.value, { page: 1, size: 30 })); versions.value = result?.records || result?.list || result?.items || [] }
  catch (error) { ElMessage.error(error?.message || '版本历史加载失败') } finally { versionLoading.value = false }
}
const createVersion = async () => { if (!projectId.value) return; try { await saveProjectVersion(projectId.value, { description: `保存第 ${selectedSlide.value + 1} 页调整` }); autosaveState.value = '已创建版本'; await loadVersions(); ElMessage.success('项目版本已保存') } catch (error) { ElMessage.error(error?.message || '版本保存失败') } }
const showVersionDiff = async (version) => { try { versionDiff.value = unwrapResponse(await getProjectVersionDiff(projectId.value, version.id || version.version_id)) } catch (error) { ElMessage.error(error?.message || '差异加载失败') } }
const restoreVersion = async (version) => { try { await restoreProjectVersion(projectId.value, version.id || version.version_id); ElMessage.success('已恢复历史版本'); await loadVersions() } catch (error) { ElMessage.error(error?.message || '版本恢复失败') } }
const grantPermission = async () => { const userId = Number(permissionUserId.value); if (!Number.isInteger(userId) || userId <= 0) return ElMessage.warning('请输入有效用户 ID'); try { await addProjectPermission(projectId.value, { user_id: userId }); permissionUserId.value = ''; permissionDialogVisible.value = false; ElMessage.success('协作者已添加') } catch (error) { ElMessage.error(error?.message || '授权失败') } }
watch(slides, () => { if (!projectId.value) return; autosaveState.value = '待保存'; clearTimeout(autosaveTimer); autosaveTimer = setTimeout(persistCurrentSlide, 700) }, { deep: true })
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const goHome = () => router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
const exportProject = () => router.push({ path: '/main/exports', query: route.query.preview ? { preview: '1' } : {} })
const addSlide = () => { slides.push({ title: `新建页面 ${slides.length + 1}`, eyebrow: '新建内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue' }); selectedSlide.value = slides.length - 1 }
const copySlide = () => { slides.splice(selectedSlide.value + 1, 0, { ...current.value, title: `${current.value.title} 副本` }); selectedSlide.value++ }
const removeSlide = () => { if (slides.length === 1) return ElMessage.warning('课件至少保留一页'); slides.splice(selectedSlide.value, 1); selectedSlide.value = Math.max(0, selectedSlide.value - 1) }
const sendRevision = () => submitRevision()
</script>

<template>
  <div class="workspace">
    <header class="toolbar">
      <div class="project-title"><el-button text circle aria-label="返回教学助手" @click="goHome"><el-icon><ArrowLeft /></el-icon></el-button><div><strong>{{ current.title }}教学设计</strong><span><el-icon><CircleCheck /></el-icon> 已保存 · 项目 {{ route.query.projectId || '演示' }}</span></div></div>
      <div class="editing-tools"><el-button text :icon="EditPen">文本</el-button><el-button text :icon="Picture">图片</el-button><el-button text :icon="DataBoard">互动组件</el-button><el-button text :icon="Brush">背景</el-button></div>
      <div class="toolbar-actions"><el-button :icon="Monitor" @click="previewVisible = true">预览</el-button><el-button type="primary" :icon="Download" @click="exportProject">导出</el-button></div>
    </header>

    <div class="workspace-grid">
      <aside class="assistant-panel" aria-label="AI 教学助手">
        <header><div class="assistant-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div></header>
        <section class="conversation"><article v-for="(message, index) in messages" :key="index" :class="['message', message.role]"><span v-if="message.role === 'assistant'">智</span><p>{{ message.text }}</p></article></section>
        <footer class="composer"><el-input v-model="prompt" type="textarea" :rows="3" resize="none" placeholder="例如：把提问改得更有启发性" @keydown.ctrl.enter="sendRevision" /><div><span>Ctrl + Enter 发送</span><el-button type="primary" circle :icon="Promotion" :disabled="!prompt.trim()" aria-label="发送修改" @click="sendRevision" /></div></footer>
      </aside>

      <section class="editor-stage">
        <aside class="slide-rail" aria-label="课件页面列表"><button v-for="(slide, index) in slides" :key="`${slide.title}-${index}`" :class="{ active: selectedSlide === index }" @click="selectedSlide = index"><span>{{ String(index + 1).padStart(2, '0') }}</span><div class="thumbnail" :style="{ '--thumb': themes.find((item) => item.id === slide.theme)?.color }"><i></i><b>{{ slide.title }}</b></div></button><el-button text :icon="Plus" @click="addSlide">添加页面</el-button></aside>
        <main class="canvas-area"><div class="canvas-meta"><span>第 {{ selectedSlide + 1 }} 页，共 {{ slides.length }} 页</span><span>16:9 · 自适应窗口</span></div><article class="slide-canvas" :class="`layout-${current.layout}`" :style="{ '--accent': theme.color }"><span class="slide-eyebrow">{{ current.eyebrow }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p><div v-if="current.layout !== '重点陈述'" class="theorem"><template v-if="current.visualType !== 'generic'"><div class="triangle"><i>a</i><i>b</i><i>c</i></div><div class="formula"><span>a² + b²</span><em>=</em><strong>c²</strong><small>拖动顶点，观察面积变化</small></div></template><div v-else class="generic-visual"><span>观察</span><em>→</em><span>探究</span><em>→</em><span>表达</span></div></div><footer><span>{{ current.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span><p>{{ current.footer || '在测量、猜想与验证中理解勾股定理，并用它解决简单的实际问题。' }}</p></footer></article><div class="canvas-controls"><button aria-label="缩小">−</button><span>86%</span><button aria-label="放大">+</button><button aria-label="全屏预览" @click="previewVisible = true"><el-icon><FullScreen /></el-icon></button></div></main>
      </section>

      <aside class="properties" aria-label="页面属性设置"><header><strong>页面属性</strong><span>页面 {{ String(selectedSlide + 1).padStart(2, '0') }}</span></header><div class="tabs"><button :class="{ active: activePanel === 'style' }" @click="activePanel = 'style'">样式</button><button :class="{ active: activePanel === 'layout' }" @click="activePanel = 'layout'">布局</button><button :class="{ active: activePanel === 'animation' }" @click="activePanel = 'animation'">动画</button></div><section v-if="activePanel === 'style'"><label>页面标题</label><el-input v-model="current.title" maxlength="20" show-word-limit /><label>引导文案</label><el-input v-model="current.description" type="textarea" :rows="4" maxlength="70" show-word-limit /><label>主题色</label><div class="theme-picker"><button v-for="item in themes" :key="item.id" :class="{ selected: current.theme === item.id }" :style="{ background: item.color }" :title="item.name" @click="current.theme = item.id"></button></div></section><section v-else-if="activePanel === 'layout'"><label>页面布局</label><div class="layout-picker"><button v-for="item in layouts" :key="item" :class="{ active: current.layout === item }" @click="current.layout = item"><i></i><i></i><span>{{ item }}</span></button></div></section><section v-else><label>页面进入动画</label><el-select model-value="fade"><el-option label="淡入出现" value="fade" /><el-option label="向上浮现" value="rise" /><el-option label="无动画" value="none" /></el-select><label>讲解节奏</label><el-slider :model-value="60" :show-tooltip="false" /><p class="hint">建议保留简洁动画，避免影响学生对知识点的注意力。</p></section><section class="page-actions"><label>页面操作</label><el-button :icon="CopyDocument" @click="copySlide">复制页面</el-button><el-button :icon="Delete" @click="removeSlide">删除页面</el-button></section><div class="assistant-tip"><el-icon><ChatDotRound /></el-icon><p>也可以在左侧直接描述希望调整的内容、语气或活动设计。</p></div></aside>
    </div>

    <el-dialog v-model="previewVisible" class="preview-dialog" width="min(960px, 92vw)" title="课件预览"><div class="preview"><article class="slide-canvas preview-slide" :style="{ '--accent': theme.color }"><span class="slide-eyebrow">{{ current.eyebrow }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p><div class="formula preview-formula"><span>a² + b²</span><em>=</em><strong>c²</strong></div></article></div><template #footer><el-button @click="previewVisible = false">继续编辑</el-button><el-button type="primary" :icon="VideoPlay" @click="previewVisible = false">播放预览</el-button></template></el-dialog>
  </div>
    <el-dialog v-model="planDialogVisible" title="教学设计大纲确认" width="min(760px, 92vw)" destroy-on-close>
      <div v-loading="planLoading" class="plan-dialog-content">
        <p class="plan-status">请先确认教学大纲，确认后将开始生成课件。</p>
        <div v-if="planView.available" class="plan-preview">
          <header class="plan-overview">
            <div class="plan-overview-heading">
              <span class="plan-eyebrow">教学设计大纲</span>
              <h3>{{ planView.title }}</h3>
              <p>{{ planView.summary }}</p>
            </div>
            <span class="plan-slide-count">{{ planView.slideCount }} 页</span>
          </header>

          <div class="plan-meta">
            <span v-if="planView.subject"><small>学科</small><strong>{{ planView.subject }}</strong></span>
            <span v-if="planView.grade"><small>适用对象</small><strong>{{ planView.grade }}</strong></span>
            <span v-if="planView.focus"><small>教学侧重点</small><strong>{{ planView.focus }}</strong></span>
            <span v-if="planView.duration"><small>建议时长</small><strong>{{ planView.duration }}</strong></span>
          </div>

          <section v-if="planView.goals.length" class="plan-section">
            <div class="plan-section-heading"><strong>教学目标</strong><span>本节课希望学生达成的结果</span></div>
            <ul class="plan-bullet-list"><li v-for="goal in planView.goals" :key="goal">{{ goal }}</li></ul>
          </section>

          <section v-if="planView.knowledgePoints.length" class="plan-section">
            <div class="plan-section-heading"><strong>核心知识点</strong><span>课堂内容主线</span></div>
            <div class="plan-tags"><span v-for="point in planView.knowledgePoints" :key="point">{{ point }}</span></div>
          </section>

          <section class="plan-section plan-structure">
            <div class="plan-section-heading"><strong>课件结构</strong><span>{{ planView.slides.length || planView.slideCount }} 个页面</span></div>
            <div v-if="planView.slides.length" class="plan-slide-list">
              <article v-for="slide in planView.slides" :key="`${slide.number}-${slide.title}`" class="plan-slide-card">
                <span class="plan-slide-number">{{ String(slide.number).padStart(2, '0') }}</span>
                <div class="plan-slide-main">
                  <div class="plan-slide-heading"><h4>{{ slide.title }}</h4><span>{{ slide.type }}</span></div>
                  <ul v-if="slide.points.length" class="slide-points"><li v-for="point in slide.points" :key="point">{{ point }}</li></ul>
                  <div v-if="slide.intent || slide.visual" class="slide-details">
                    <div v-if="slide.intent"><small>教学意图</small><p>{{ slide.intent }}</p></div>
                    <div v-if="slide.visual"><small>呈现建议</small><p>{{ slide.visual }}</p></div>
                  </div>
                </div>
              </article>
            </div>
            <el-empty v-else description="暂未返回课件页面结构" />
          </section>
        </div>
        <el-empty v-else description="大纲暂未返回，请稍后刷新" />
        <el-input v-model="planComment" class="plan-comment" type="textarea" :rows="3" placeholder="如需补充或退回，请说明具体要求" />
      </div>
      <template #footer><el-button type="primary" :loading="planSubmitting" @click="submitPlan('supplement')">补充要求</el-button><el-button :loading="planSubmitting" @click="submitPlan('reject')">退回修改</el-button><el-button type="primary" :loading="planSubmitting" @click="submitPlan('confirm')">确认并生成</el-button></template>
    </el-dialog>
    <IntentClarificationDialog v-model="clarificationDialogVisible" :question="clarificationQuestion" :loading="clarificationSubmitting" @submit="submitClarification" />
    <div v-if="runStatus === 'running'" class="run-progress"><span>{{ runStage || 'AI 正在生成课件' }}</span><el-progress :percentage="runProgress" :show-text="false" :stroke-width="4" /></div>
    <div v-if="projectId" class="project-utilities"><span>{{ autosaveState }}</span><el-button text size="small" @click="createVersion">保存版本</el-button><el-button text size="small" @click="loadVersions">版本历史</el-button><el-button text size="small" @click="permissionDialogVisible = true">协作授权</el-button></div>
    <el-dialog v-model="versionDialogVisible" title="项目版本历史" width="min(680px, 92vw)"><div v-loading="versionLoading" class="version-list"><article v-for="version in versions" :key="version.id || version.version_id"><div><strong>版本 {{ version.version_number || version.id }}</strong><p>{{ version.description || '未填写说明' }}</p></div><div><el-button text size="small" @click="showVersionDiff(version)">查看差异</el-button><el-button text size="small" type="primary" @click="restoreVersion(version)">恢复此版本</el-button></div></article><p v-if="versionDiff" class="version-diff">{{ versionDiff.summary || JSON.stringify(versionDiff.differences || versionDiff) }}</p><el-empty v-if="!versionLoading && !versions.length" description="暂无历史版本" /></div><template #footer><el-button @click="versionDialogVisible = false">关闭</el-button></template></el-dialog>
    <el-dialog v-model="permissionDialogVisible" title="添加协作者" width="420px"><p class="dialog-hint">协作者将获得项目编辑权限。</p><el-input v-model="permissionUserId" inputmode="numeric" placeholder="输入用户 ID" /><template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" @click="grantPermission">确认授权</el-button></template></el-dialog>
</template>

<style scoped>
.workspace{height:100dvh;display:grid;grid-template-rows:60px minmax(0,1fr);overflow:hidden;background:var(--zh-background-light)}.toolbar{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 16px;border-bottom:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.project-title{display:flex;align-items:center;gap:8px}.project-title div{display:flex;flex-direction:column}.project-title strong{font-size:13px}.project-title span{display:flex;align-items:center;gap:4px;margin-top:3px;color:var(--zh-text-caption);font-size:10px}.project-title span .el-icon{color:var(--zh-green)}.editing-tools{display:flex;padding:3px;border-radius:var(--zh-radius8);background:var(--zh-background-light)}.toolbar-actions{justify-self:end;display:flex;gap:8px}.workspace-grid{min-height:0;display:grid;grid-template-columns:286px minmax(500px,1fr) 270px}.assistant-panel,.properties{min-height:0;background:var(--zh-background-primary)}.assistant-panel{display:flex;flex-direction:column;border-right:1px solid var(--zh-line-border)}.assistant-panel>header{display:flex;align-items:center;gap:9px;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.assistant-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:var(--zh-radius8);color:#fff;background:var(--zh-gradient-blue);font-weight:700}.assistant-panel header div:last-child{display:flex;flex-direction:column}.assistant-panel header strong{font-size:13px}.assistant-panel header span{margin-top:2px;color:var(--zh-text-caption);font-size:10px}.conversation{flex:1;padding:16px;overflow:auto}.message{display:flex;align-items:flex-start;gap:8px;margin-bottom:16px}.message>span{display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:6px;color:#fff;background:var(--zh-theme-primary);font-size:10px}.message p{margin:0;padding:10px 12px;border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-answer-card);font-size:12px;line-height:1.65}.message.user{justify-content:flex-end}.message.user p{color:var(--zh-text-primary);background:var(--zh-background-user-query)}.composer{padding:12px;border-top:1px solid var(--zh-line-border)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:8px}.composer span{color:var(--zh-text-caption);font-size:10px}.composer :deep(.el-textarea__inner){background:var(--zh-background-light);box-shadow:none}.editor-stage{display:grid;grid-template-columns:116px minmax(0,1fr);min-width:0}.slide-rail{padding:12px 9px;overflow:auto;border-right:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.slide-rail>button{display:grid;grid-template-columns:18px 1fr;gap:4px;width:100%;margin-bottom:10px;padding:3px;border:1px solid transparent;border-radius:6px;color:var(--zh-text-caption);background:transparent;text-align:left;cursor:pointer}.slide-rail>button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.thumbnail{display:flex;flex-direction:column;justify-content:center;gap:5px;height:54px;padding:8px;border-radius:4px;background:var(--zh-background-light)}.thumbnail i{width:65%;height:3px;background:var(--thumb)}.thumbnail b{overflow:hidden;color:var(--zh-text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}.slide-rail :deep(.el-button){width:100%;justify-content:flex-start}.canvas-area{position:relative;display:grid;place-items:center;min-width:0;padding:44px 34px;overflow:auto;background-color:#eef0f4;background-image:radial-gradient(#c9ced7 1px,transparent 1px);background-size:18px 18px}.canvas-meta{position:absolute;top:12px;inset-inline:20px;display:flex;justify-content:space-between;color:#7c8491;font-size:10px}.slide-canvas{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;padding:clamp(28px,4vw,52px);color:#102d54;background:#f9fbff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.slide-canvas:after{content:'';position:absolute;top:-18%;right:-8%;width:42%;aspect-ratio:1;border-radius:50%;background:color-mix(in srgb,var(--accent) 16%,white)}.slide-eyebrow,.slide-canvas h1,.slide-canvas>p,.theorem{position:relative;z-index:1}.slide-eyebrow{color:var(--accent);font:600 10px var(--zh-font-number);letter-spacing:.12em}.slide-canvas h1{max-width:76%;margin:18px 0 0;font-size:clamp(26px,3vw,40px);line-height:1.2;letter-spacing:-.04em}.slide-canvas>p{max-width:64%;margin:12px 0;color:#607491;font-size:clamp(11px,1.2vw,15px);line-height:1.65}.theorem{display:grid;grid-template-columns:.8fr 1.2fr;align-items:center;gap:28px;width:76%;margin:28px auto}.triangle{position:relative;width:104px;height:104px;border-right:5px solid var(--accent);border-bottom:5px solid var(--accent);transform:skewY(-35deg) rotate(-10deg)}.triangle i{position:absolute;color:var(--accent);font-style:normal;font-weight:700;transform:skewY(35deg) rotate(10deg)}.triangle i:nth-child(1){bottom:-22px;left:36px}.triangle i:nth-child(2){top:40px;right:-18px}.triangle i:nth-child(3){top:-22px;left:8px}.formula{display:grid;grid-template-columns:auto 24px auto;align-items:center;font-family:var(--zh-font-number)}.formula span,.formula strong{font-size:clamp(22px,3vw,36px)}.formula em{color:#7c8da4;font-style:normal}.formula strong{color:var(--accent)}.formula small{grid-column:1/-1;margin-top:8px;color:#7c8da4;font-size:10px}.slide-canvas footer{position:absolute;z-index:1;right:0;bottom:0;left:0;display:grid;grid-template-columns:110px 1fr;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54)}.slide-canvas footer p{margin:0;font-size:10px;line-height:1.5}.layout-重点陈述 h1{margin-top:54px;font-size:clamp(34px,4.4vw,52px)}.canvas-controls{position:absolute;right:18px;bottom:14px;display:flex;overflow:hidden;border-radius:var(--zh-radius8);background:var(--zh-background-capsule);box-shadow:var(--zh-shadow1)}.canvas-controls button,.canvas-controls span{padding:6px 9px;border:0;color:var(--zh-text-secondary);background:transparent;font-size:11px}.canvas-controls button{cursor:pointer}.properties{overflow:auto;border-left:1px solid var(--zh-line-border)}.properties>header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties header strong{font-size:13px}.properties header span{color:var(--zh-text-caption);font-size:10px}.tabs{display:grid;grid-template-columns:repeat(3,1fr);padding:10px 14px 0;border-bottom:1px solid var(--zh-line-parting)}.tabs button{padding:8px;border:0;border-bottom:2px solid transparent;color:var(--zh-text-caption);background:transparent;cursor:pointer}.tabs button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme)}.properties section{padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties label{display:block;margin:0 0 10px;color:var(--zh-text-secondary);font-size:11px;font-weight:600}.properties label:not(:first-child){margin-top:18px}.theme-picker{display:flex;gap:12px}.theme-picker button{width:24px;height:24px;border:2px solid var(--zh-background-primary);border-radius:50%;box-shadow:0 0 0 1px var(--zh-line-border);cursor:pointer}.theme-picker button.selected{outline:2px solid var(--zh-text-theme);outline-offset:2px}.layout-picker{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.layout-picker button{display:grid;grid-template-rows:26px auto;gap:4px;min-height:66px;padding:7px 4px;border:1px solid var(--zh-line-border);border-radius:6px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:9px;cursor:pointer}.layout-picker button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.layout-picker i{display:block;width:70%;height:4px;margin:auto;background:var(--zh-line-theme50)}.layout-picker i:nth-child(2){width:48%}.page-actions{display:grid;gap:8px}.page-actions :deep(.el-button){justify-content:flex-start;margin:0}.assistant-tip{display:flex;gap:8px;margin:16px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.assistant-tip p,.hint{margin:0;color:var(--zh-text-secondary);font-size:10px;line-height:1.6}.preview{display:grid;place-items:center;padding:18px;background:#eef0f4}.preview-slide{width:min(780px,100%)}.preview-formula{width:max-content;margin:50px auto}.preview-dialog :deep(.el-dialog__body){padding:0}@media(max-width:1120px){.workspace-grid{grid-template-columns:250px minmax(460px,1fr)}.properties{display:none}}@media(max-width:820px){.toolbar{grid-template-columns:1fr auto}.editing-tools{display:none}.workspace-grid{grid-template-columns:1fr}.assistant-panel{display:none}.editor-stage{grid-template-columns:88px minmax(0,1fr)}}
.plan-dialog-content .plan-status{margin:0 0 14px;color:var(--zh-text-secondary);font-size:13px}.plan-preview{display:grid;gap:12px;max-height:min(62vh,680px);overflow:auto;padding:2px 4px 4px 0}.plan-overview{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:18px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);background:linear-gradient(135deg,var(--zh-background-weaken),var(--zh-background-primary))}.plan-overview-heading{min-width:0}.plan-eyebrow{color:var(--zh-text-theme);font-size:10px;font-weight:700;letter-spacing:.12em}.plan-overview h3{margin:7px 0 6px;color:var(--zh-text-primary);font-size:19px;line-height:1.35}.plan-overview p{margin:0;color:var(--zh-text-secondary);font-size:12px;line-height:1.7}.plan-slide-count{display:inline-flex;flex:none;align-items:center;padding:7px 10px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-primary);font:700 12px var(--zh-font-number);white-space:nowrap}.plan-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.plan-meta>span{display:grid;gap:4px;padding:11px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-meta small,.slide-details small{color:var(--zh-text-caption);font-size:10px}.plan-meta strong{overflow:hidden;color:var(--zh-text-primary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.plan-section{padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.plan-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}.plan-section-heading strong{color:var(--zh-text-primary);font-size:13px}.plan-section-heading span{color:var(--zh-text-caption);font-size:11px}.plan-bullet-list,.slide-points{display:grid;gap:7px;margin:0;padding-left:18px;color:var(--zh-text-secondary);font-size:12px;line-height:1.6}.plan-bullet-list li::marker,.slide-points li::marker{color:var(--zh-text-theme)}.plan-tags{display:flex;flex-wrap:wrap;gap:7px}.plan-tags span{padding:5px 9px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:11px}.plan-slide-list{display:grid;gap:8px}.plan-slide-card{display:grid;grid-template-columns:36px minmax(0,1fr);gap:10px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-slide-number{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:700 11px var(--zh-font-number)}.plan-slide-main{min-width:0}.plan-slide-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px}.plan-slide-heading h4{margin:0;color:var(--zh-text-primary);font-size:13px}.plan-slide-heading span{color:var(--zh-text-caption);font-size:10px}.slide-points{margin-bottom:9px}.slide-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-top:9px;border-top:1px solid var(--zh-line-parting)}.slide-details p{margin:3px 0 0;color:var(--zh-text-secondary);font-size:11px;line-height:1.55}.plan-comment{margin-top:14px}.run-progress{position:fixed;z-index:100;right:24px;bottom:24px;width:min(320px,calc(100vw - 48px));padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-pop);box-shadow:var(--zh-shadow2);font-size:12px}.run-progress :deep(.el-progress){margin-top:9px}
.project-utilities{position:fixed;z-index:100;right:24px;top:72px;display:flex;align-items:center;gap:4px;padding:5px 8px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);color:var(--zh-text-caption);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1);font-size:11px}.project-utilities span{margin:0 4px}.version-list{display:grid;gap:10px}.version-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.version-list strong{font-size:13px}.version-list p{margin:4px 0 0;color:var(--zh-text-caption);font-size:12px}.version-diff{margin:0;padding:12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-weaken);font-size:12px;line-height:1.6;white-space:pre-wrap}.dialog-hint{margin:0 0 12px;color:var(--zh-text-secondary);font-size:13px}
.generic-visual{grid-column:1/-1;display:flex;align-items:center;justify-content:center;gap:14px;padding:24px;border:1px solid color-mix(in srgb,var(--accent) 24%,transparent);border-radius:var(--zh-radius12);background:color-mix(in srgb,var(--accent) 8%,white)}.generic-visual span{color:var(--accent);font-size:clamp(15px,2vw,22px);font-weight:600}.generic-visual em{color:#8a98aa;font-style:normal}

/* PPT 缩略图：阻止长标题撑开网格，并在固定画布内最多展示两行。 */
.slide-rail > button {
  grid-template-columns: 18px minmax(0, 1fr);
  min-width: 0;
  overflow: hidden;
}
.thumbnail {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
.thumbnail i {
  flex: none;
}
.thumbnail b {
  display: -webkit-box;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  line-height: 1.35;
  overflow-wrap: anywhere;
  white-space: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
@media (max-width: 620px) {
  .plan-overview { flex-direction: column; gap: 10px; }
  .plan-slide-count { align-self: flex-start; }
  .plan-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .slide-details { grid-template-columns: 1fr; }
}
</style>
