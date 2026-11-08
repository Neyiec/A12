<!--
  [数据交互说明]
  - 导入: 聊天配置、Element Plus 图标、Python 大纲 SSE、`getAiPlan`（兼容 API-14）、`confirmAiPlan`（API-15）
  - Props: sessionId (Java会话ID), initialPrompt (首条用户消息), resourceIds (引用资源), continuationHistory (切换前的普通对话)
  - Emits: @back (返回欢迎页), @open-workspace (跳转工作台), @planning-request (普通对话切换备课)
  - 输入: 接收来自 TeacherHome 的会话初始参数
  - 输出: 聊天界面完整交互，流程：用户输入 → 补充信息卡片 → API-13 发消息生成大纲 → API-14 拉取并展示 → 确认/修改(API-15 确认) → 资源生成卡片 → 跳转工作台
  - 流程说明: 大纲生成走 Java 网关流式（API-11S SSE）。final 事件到达后直接渲染大纲，question 转入澄清阶段等待教师补充回复后继续。修改要求通过再次发送流式消息实现重生成。
-->
<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Brush, Document, Paperclip, Promotion } from '@element-plus/icons-vue'
import MarkdownRender from 'markstream-vue'
import { useUserStore } from '../storage/user.js'
import MobileSection from './MobileSection.vue'
import { readOutlineDraft, saveOutlineDraft } from '../utils/presentationDraft.js'
import { readOpenAiTextStream } from '../utils/openAiSse.js'
import { upsertLearningGraphMessage } from '../utils/learningGraphMessage.js'
import { normalizeModelProfile, normalizeReasoningEffort } from '../utils/aiOptions.js'
import { beginGeneralChatTurn, completeGeneralChatTurn, confirmAiPlan, getAiPlan, getAiSession, getTeacherPreferences, listPptTemplates, recordAiFeedback, routeTeachingChat, saveDirectOutlineResult, streamGeneralChat, streamOutlineChat, transcribeAudio, uploadTempResource } from '../apis/teacher.js'
import {
  CHAT_COMPOSER, CLASS_LEVEL_OPTIONS, CLARIFICATION_LABELS,
  extractPlanningContext, gradesForStage, normalizePlanningGrade, slideRangeError, CHAT_RESUME, DESIGN_ACTION_BAR, GEN_RESOURCE_DEFAULTS, INFO_FORM_DEFAULTS,
  STAGE_OPTIONS, SUBJECT_OPTIONS,
  latestSessionPush, RESOURCE_CARD_LABELS, SYSTEM_MESSAGES,
} from '../config/teacherChat.config.js'
import IntentClarificationDialog from './IntentClarificationDialog.vue'
import PptTemplatePicker from './PptTemplatePicker.vue'
import VoiceRecorderButton from './VoiceRecorderButton.vue'
import LearningGraphPanel from './LearningGraphPanel.vue'
import BatchPlanCard from './BatchPlanCard.vue'
import BatchTaskPanel from './BatchTaskPanel.vue'
import { createBatchPlan, reviseBatchPlan, listBatchPlans } from '../apis/batchPresentations'
import { updateOutlineLearningGraphs, aiEditOutlineLearningGraphs } from '../apis/teacher.js'

const props = defineProps({
  sessionId: { type: [String, Number], default: null },
  initialPrompt: { type: String, default: '' },
  resourceIds: { type: Array, default: () => [] },
  /** 资料上传明细、社区 Skill/案例等需要继续传给工作台的上下文。 */
  workspaceContext: { type: Object, default: () => ({}) },
  /** 普通对话切换到备课流时，需要在当前消息列表前展示的历史消息。 */
  continuationHistory: { type: Array, default: () => [] },
  /** 普通主对话不进入备课补充信息流程；默认仍为备课工作流。 */
  mode: { type: String, default: 'planning' },
  routePreference: { type: String, default: 'auto' },
  /** 是否为恢复历史会话（来自侧栏历史对话），开启时挂载后拉取消息回显 */
  resume: { type: Boolean, default: false },
})

const emit = defineEmits(['back', 'open-workspace', 'planning-request', 'session-created', 'general-session'])

const publicResourceEnabled = defineModel('publicResourceEnabled', { type: Boolean, default: false })
const userStore = useUserStore()
const isGeneralChat = computed(() => props.mode === 'general')
const activeBatchPlan = ref(null)
const attachedResources = ref([])
const resourceFileInput = ref(null)
const resourceUploading = ref(false)
const activeResourceIds = computed(() => [...new Set([
  ...(props.resourceIds || []).map((id) => String(id)),
  ...attachedResources.value.map((item) => String(item.id)),
])])
const activeWorkspaceContext = computed(() => ({
  ...(props.workspaceContext || {}),
  enable_rag: publicResourceEnabled.value,
  resourceIds: activeResourceIds.value,
  resource_ids: activeResourceIds.value,
  uploadedResources: [...(props.workspaceContext?.uploadedResources || []), ...attachedResources.value],
  uploaded_resources: [...(props.workspaceContext?.uploaded_resources || []), ...attachedResources.value],
}))
const uploadChatResources = async (event) => {
  const files = Array.from(event.target?.files || [])
  if (event.target) event.target.value = ''
  if (!files.length || resourceUploading.value) return
  resourceUploading.value = true
  let uploaded = 0
  try {
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      const response = await uploadTempResource(form)
      if (!isOk(response)) throw new Error(response?.message || `${file.name} 解析失败`)
      const result = response.data || {}
      if (!result.text_length) throw new Error(`${file.name} 未解析出可用内容，请检查PDF文本层或OCR配置`)
      const id = result?.id || result?.resource_id || result?.resourceId
      if (!id) throw new Error(`${file.name} 上传成功但未返回资源 ID`)
      attachedResources.value = [
        ...attachedResources.value.filter((item) => String(item.id) !== String(id)),
        { id: String(id), resource_id: String(id), file_name: file.name, file_type: file.type, file_size: file.size },
      ]
      uploaded += 1
    }
    ElMessage.success(`已添加 ${uploaded} 份资料；后台解析完成后，后续大纲和 PPT 生成即可检索引用`)
  } catch (error) {
    ElMessage.error(error?.message || '资料上传失败')
  } finally {
    resourceUploading.value = false
  }
}
const removeChatResource = (id) => {
  attachedResources.value = attachedResources.value.filter((item) => String(item.id) !== String(id))
}
/** 功能 2：临时上传资料（欢迎页带下来，res_xxx 走 temp 索引），只读展示不提供移除。 */
const tempContextResources = computed(() => (activeWorkspaceContext.value?.uploadedResources || [])
  .filter((item) => item && item.temp && item.resource_id))
const generalSessionId = ref(props.mode === 'general' && props.resume ? props.sessionId : null)
const selectedRoutePreference = ref(props.routePreference)
const selectedModelProfile = ref(normalizeModelProfile(localStorage.getItem('a12:model-profile')))
const selectedReasoningEffort = ref(normalizeReasoningEffort(localStorage.getItem('a12:reasoning-effort')))
watch(selectedModelProfile, (value) => localStorage.setItem('a12:model-profile', value))
watch(selectedReasoningEffort, (value) => localStorage.setItem('a12:reasoning-effort', value))

// ========== 响应式断点（design.md §9.3：手机档 <768px） ==========
/** 手机档断点：补充信息表单由 display:table 降级为卡片堆叠渲染。 */
const isMobile = ref(window.matchMedia('(max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse)').matches)
/** 触屏设备（无 hover + 粗指针）：Enter 不触发发送，避免与移动端键盘回车冲突。 */
const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches
const mobileBreakpointQuery = window.matchMedia('(max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse)')
const syncMobileBreakpoint = () => { isMobile.value = mobileBreakpointQuery.matches }
mobileBreakpointQuery.addEventListener('change', syncMobileBreakpoint)
onUnmounted(() => mobileBreakpointQuery.removeEventListener('change', syncMobileBreakpoint))
/** 大纲单独直连 Python 真实模型；不改变 mock 登录和 Java 会话开关。 */
const useRealOutlineApi = import.meta.env.VITE_USE_REAL_OUTLINE_API === 'true'
/** Python 大纲会话 ID，与 Java mock 会话 ID 分开保存，便于同一对话继续生成/修改。 */
const outlinePythonSessionId = ref('')
/** 流式生成阶段提示，便于确认请求确实进入了真实 Agent。 */
const outlineGenerationStage = ref('')

// ========== 对话阶段控制 ==========
/**
 * 阶段状态机：
 *   'info'      → 显示补充信息卡片，等待教师填写（仅备课工作流）
 *   'general_chat' → 普通主对话，不展示备课表单
 *   'generating_outline' → 正在通过 Python SSE Agent 获取教学设计大纲
 *   'clarifying'         → 后端返回澄清问题，等待教师补充回复
 *   'graph_review'       → 双图谱已生成，等待教师确认后再生成大纲
 *   'outline_ready'      → 大纲已展示，等待确认
 *   'resource_ready'     → 资源生成卡片展示，等待点击生成
 *   'generating_resource' → 正在生成资源
 */
const phase = ref('info')

/** 正在请求提纲/大纲的加载态（用于按钮 loading 与流式指示器） */
const isRequesterLoading = ref(false)
/** 切换前的普通对话只在首次提交备课信息时注入一次，后续由同一 Python 会话继续记忆。 */
const continuationInjected = ref(false)
/** 恢复历史会话的加载态（进入已有对话时短暂展示"恢复历史对话…"） */
const resumeLoading = ref(false)

// ========== 消息列表 ==========
/** 每条消息: { id, role: 'user'|'assistant'|'system', type: 'text'|'outline'|'info_form'|'clarification', content, data? } */
const messages = reactive([])
let messageSeq = 0
/** 实时流式预览的临时消息 id（final 到达后被正式大纲替换） */
let liveMsgId = null
let activeLearningGraphMessageId = null
const messageListRef = ref(null)

// ========== 教学设计方案数据 ==========
/** 完整大纲数据（Markdown + 元数据），由真实 Python SSE 或兼容 API-14 填充 */
const outlineData = ref(null)
const retrievalMatches = computed(() => outlineData.value?.planJson?.retrieval_matches || [])
const webSearchStatus = computed(() => outlineData.value?.planJson?.web_search_status)
const webReferences = computed(() => {
  const references = outlineData.value?.planJson?.web_references
  return Array.isArray(references) ? references.filter((item) => {
    try {
      const url = new URL(item?.url)
      return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password
    } catch { return false }
  }) : []
})
const citeRetrievalMatch = (match) => {
  const id = String(match?.resource_id || '')
  if (!id || activeResourceIds.value.includes(id)) return
  attachedResources.value.push({ id, resource_id: id, file_name: match.title || id, source: 'retrieval' })
  ElMessage.success('已加入引用，后续生成将优先检索这份资料')
}
/** 最新一次用于展示的大纲版本号（提交确认/修改时携带，防并发冲突） */
const planVersion = ref(1)

// ========== 补充信息表单 ==========
/** 使用配置模块的默认值初始化补充信息表单 */
const infoForm = reactive({ ...INFO_FORM_DEFAULTS })
function getSlideCountRange() {
  if (slideRangeError(infoForm.minPages, infoForm.maxPages)) return null
  if (infoForm.minPages == null || infoForm.minPages === '') return null
  return { min_pages: Number(infoForm.minPages), max_pages: Number(infoForm.maxPages) }
}
const gradeOptions = computed(() => gradesForStage(infoForm.stage))
function handleStageChange() {
  if (!gradeOptions.value.includes(infoForm.grade)) infoForm.grade = ''
}
const selectedTeachingModel = ref('boppps')
const selectedTeachingStyle = ref('')

// ========== 澄清交互 ==========
/** 当前待补充的澄清问题文本 */
const lastClarification = ref('')
/** 澄清/修改输入框内容 */
const composerInput = ref('')
/** 后端 Agent 返回复杂澄清问题时使用的结构化征询弹窗。首次信息直接在内嵌卡片中填写。 */
const planningClarificationVisible = ref(false)
const planningClarificationQuestion = ref(null)
const planningClarificationSubmitting = ref(false)
/** 语音消息提交态。备课会话直接调用 API-13A，普通对话仅作转写输入。 */
const voiceSubmitting = ref(false)

// ========== 资源生成卡片数据 ==========
/** 使用配置模块的默认值初始化资源生成卡片 */
const genResource = reactive({ ...GEN_RESOURCE_DEFAULTS })
/** 生成 PPT 前选择的后端模板；工作台只负责编辑生成结果，不在此阶段换肤。 */
const pptTemplateDialogVisible = ref(false)
const pptTemplateLoading = ref(false)
const pptTemplateLoadError = ref('')
const pptTemplates = ref([])
const selectedPptTemplateTheme = ref('')
const pptTemplateDraftTheme = ref('')
let pptTemplateRequest = null

// ========== 大纲对话框 ==========
/** 教学大纲确认/修改模态框 */
const outlineDialogVisible = ref(false)
/** 大纲数据（从后端加载） */
const planTask = ref(null)
/** 对话框加载中 */
const planLoading = ref(false)
/** 对话框提交中 */
const planSubmitting = ref(false)
/** 大纲确认必须以服务端结果为准，避免本地状态先行导致后续生成被拒绝。 */
const outlineConfirming = ref(false)
/** 补充/退回说明 */
const planComment = ref('')

// ========== 辅助函数 ==========

const normalizePptTemplate = (template) => {
  const theme = String(template?.theme || '').trim()
  if (!theme) return null
  return {
    theme,
    name: String(template?.template_name || theme).trim() || theme,
    description: String(template?.description || '适用于课堂课件生成的 PPT 模板。').trim(),
    aliases: Array.isArray(template?.aliases)
      ? template.aliases.map((item) => String(item).trim()).filter(Boolean).slice(0, 4)
      : [],
    isDefault: Boolean(template?.is_default),
    filename: String(template?.filename || '').trim(),
  }
}

const selectedPptTemplate = computed(() => pptTemplates.value.find((item) => item.theme === selectedPptTemplateTheme.value) || null)
const pptTemplateName = computed(() => selectedPptTemplate.value?.name || selectedPptTemplateTheme.value || '')
const pptTemplateStorageKey = () => `a12:ppt-template:session:${props.sessionId}`
const readStoredPptTemplateTheme = () => {
  try { return window.localStorage.getItem(pptTemplateStorageKey()) || '' } catch { return '' }
}
const persistPptTemplateTheme = () => {
  if (!selectedPptTemplateTheme.value) return
  try { window.localStorage.setItem(pptTemplateStorageKey(), selectedPptTemplateTheme.value) } catch { /* 浏览器禁用本地存储时仍保留本次选择 */ }
}

const loadPptTemplates = async (force = false) => {
  if (pptTemplateRequest) return pptTemplateRequest
  if (pptTemplates.value.length && !force) return pptTemplates.value
  pptTemplateLoading.value = true
  pptTemplateLoadError.value = ''
  pptTemplateRequest = (async () => {
    try {
      const response = await listPptTemplates()
      const data = isOk(response) ? response.data : response
      const source = Array.isArray(data) ? data : data?.templates
      const templates = (Array.isArray(source) ? source : []).map(normalizePptTemplate).filter(Boolean)
      if (!templates.length) throw new Error('后端暂未提供可用的 PPT 模板')
      pptTemplates.value = templates
      const availableThemes = new Set(templates.map((item) => item.theme))
      const preferredThemes = [
        readStoredPptTemplateTheme(),
        String(data?.default_theme || '').trim(),
        templates.find((item) => item.isDefault)?.theme || '',
        templates[0].theme,
      ]
      selectedPptTemplateTheme.value = preferredThemes.find((theme) => availableThemes.has(theme)) || templates[0].theme
      persistPptTemplateTheme()
      if (outlineData.value) fillGenResource(outlineData.value)
      return templates
    } catch (error) {
      pptTemplateLoadError.value = error?.response?.data?.message || error?.message || 'PPT 模板加载失败'
      return []
    } finally {
      pptTemplateLoading.value = false
    }
  })()
  try {
    return await pptTemplateRequest
  } finally {
    pptTemplateRequest = null
  }
}

const openPptTemplateDialog = async () => {
  pptTemplateDialogVisible.value = true
  pptTemplateDraftTheme.value = selectedPptTemplateTheme.value
  await loadPptTemplates()
  pptTemplateDraftTheme.value = selectedPptTemplateTheme.value
}

const confirmPptTemplate = (template) => {
  const theme = template?.theme || pptTemplateDraftTheme.value
  const selected = pptTemplates.value.find((item) => item.theme === theme)
  if (!selected) return ElMessage.warning('请先选择一个 PPT 模板')
  selectedPptTemplateTheme.value = selected.theme
  pptTemplateDraftTheme.value = selected.theme
  persistPptTemplateTheme()
  pptTemplateDialogVisible.value = false
  fillGenResource(outlineData.value)
  ElMessage.success(`已选择“${selected.name}”，生成 PPT 时将采用此模板`)
}

/** 添加消息到列表并自动滚动 */
function addMessage(role, type, content, data) {
  messageSeq += 1
  const message = { id: messageSeq, role, type, content, data }
  messages.push(message)
  scrollToBottom()
  // reactive 数组会在读取时返回代理；返回数组中的元素，确保后续流式更新能触发 Vue 渲染。
  return messages[messages.length - 1]
}

/** 规范化普通对话历史，只保留可回显、可交给模型理解的文本消息。 */
function normalizeConversationHistory(history) {
  return (Array.isArray(history) ? history : [])
    .filter((item) => item && (item.role === 'user' || item.role === 'assistant') && String(item.content || '').trim())
    .map((item) => ({ role: item.role, content: String(item.content).trim() }))
    .slice(-16)
}

/** 将切换前的对话整理成首次备课请求可理解的背景文本。 */
function buildContinuationContext() {
  const history = normalizeConversationHistory(props.continuationHistory)
  if (!history.length) return ''
  const transcript = history
    .map((item) => `${item.role === 'assistant' ? 'AI' : '教师'}：${item.content}`)
    .join('\n')
  return [
    '这是教师进入备课流程前与 AI 的已有对话，请将其作为本次备课的背景信息。',
    '请保留其中已经确认的教学目标、受众、内容偏好和修改要求，不要重复询问已经明确的信息。',
    transcript,
  ].join('\n')
}

/** 将切换前的消息接在当前备课请求之前回显。 */
function renderContinuationHistory() {
  normalizeConversationHistory(props.continuationHistory)
    .forEach((item) => addMessage(item.role, 'text', item.content))
}

/** 将首句或澄清回答映射到备课表单，兼容前后端不同字段命名。 */
function applyPlanningContext(context = {}) {
  const valueOf = (...keys) => {
    for (const key of keys) {
      const value = context?.[key]
      if (value !== undefined && value !== null && String(value).trim()) return String(value).trim()
    }
    return ''
  }

  const stage = valueOf('stage', 'school_stage', 'education_stage')
  const subject = valueOf('subject', 'discipline')
  const grade = valueOf('grade', 'class_grade', 'grade_level')
  const textbook = valueOf('textbook', '教材', 'book')
  const courseName = valueOf('course_name', 'courseName', 'title', 'topic', 'theme')
  const requirements = valueOf('requirements', 'personalized_needs', 'personalizedNeeds', 'needs')
  const classLevel = valueOf('class_level', 'classLevel', 'learning_level')

  if (stage) infoForm.stage = stage
  if (subject) infoForm.subject = subject
  if (grade) infoForm.grade = grade
  infoForm.grade = normalizePlanningGrade(infoForm.stage, infoForm.grade)
  if (textbook) infoForm.textbook = textbook
  if (courseName) infoForm.courseName = courseName
  if (requirements) infoForm.requirements = requirements
  if (classLevel) infoForm.classLevel = classLevel
  if (context.slide_count_range) {
    infoForm.minPages = context.slide_count_range.min_pages
    infoForm.maxPages = context.slide_count_range.max_pages
  }
}

/** 新建备课会话时只保留真正的默认偏好，不把示例学科/年级伪装成 AI 识别结果。 */
function prepareInitialInfoForm(prompt) {
  Object.assign(infoForm, {
    ...INFO_FORM_DEFAULTS,
    stage: '',
    subject: '',
    grade: '',
    textbook: '',
    courseName: '',
  })
  applyPlanningContext(extractPlanningContext(prompt))
}

/** 将后端字符串澄清问题也包装成结构化弹窗，避免只显示一段不可操作的追问文本。 */
function normalizePlanningClarification(rawQuestion) {
  if (rawQuestion && typeof rawQuestion === 'object') {
    const question = { ...rawQuestion }
    if (!Array.isArray(question.questions) || !question.questions.length) {
      question.questions = [{
        field: 'clarification',
        label: '补充说明',
        text: String(question.text || question.question || question.title || '请补充说明你的教学需求。'),
        required: true,
        allowCustom: true,
      }]
    }
    question.text = String(question.text || question.question || question.title || '为了更准确地完成备课，请补充以下信息。')
    return question
  }

  const text = String(rawQuestion || '').trim()
  if (!text) return null
  // 个别代理会把结构化问题作为 JSON 字符串返回，先尝试恢复对象。
  if (text.startsWith('{')) {
    try {
      const parsed = JSON.parse(text)
      if (parsed && typeof parsed === 'object') return normalizePlanningClarification(parsed)
    } catch {
      // 不是 JSON 时按普通问题处理。
    }
  }
  return {
    text,
    questions: [{
      field: 'clarification',
      label: '补充说明',
      text,
      required: true,
      allowCustom: true,
      placeholder: '请直接填写你的补充要求',
    }],
  }
}

/** 打开后端 Agent 征询弹窗；关闭后仍保留内嵌表单/底部输入作为可恢复入口。 */
function openPlanningClarification(rawQuestion) {
  const question = normalizePlanningClarification(rawQuestion)
  if (!question) return false
  planningClarificationQuestion.value = question
  planningClarificationVisible.value = true
  return true
}

/** 滚动消息列表到底部（手机档消息区与 composer 同为容器滚动上下文时，兜底滚动 chat-container） */
async function scrollToBottom() {
  await nextTick()
  const el = messageListRef.value
  if (!el) return
  if (el.scrollHeight > el.clientHeight) {
    el.scrollTop = el.scrollHeight
    return
  }
  const container = el.parentElement
  if (container && container.scrollHeight > container.clientHeight) {
    container.scrollTop = container.scrollHeight
  }
}

/** 判断响应是否成功（兼容 code 0 / 200） */
function isOk(res) {
  return res && (res.code === 0 || res.code === 200)
}

/**
 * 将后端 plan_json 结构化大纲转换为 Markdown 文本，供 MarkdownRender 展示。
 * @param {Object} planJson - 来自 API-14 的 plan_json
 * @returns {string} Markdown 大纲文本
 */
function planJsonToMarkdown(planJson) {
  if (!planJson) return ''
  const lines = []
  if (planJson.title) lines.push(`# ${planJson.title}`)
  if (planJson.summary) {
    lines.push('', '> 摘要：' + planJson.summary)
  }
  const slides = Array.isArray(planJson.slides) ? planJson.slides : []
  const phaseLabels = {
    bridge_in: '导入', objective: '学习目标', pre_assessment: '前测',
    participatory_learning: '参与式学习', worked_example: '示例与练习',
    post_assessment: '后测', summary: '总结',
  }
  if (planJson.teaching_model === 'boppps') {
    const present = new Set(slides.map((slide) => String(slide.learning_phase || '')))
    if (present.has('worked_example')) present.add('participatory_learning')
    const stages = ['bridge_in', 'objective', 'pre_assessment', 'participatory_learning', 'post_assessment', 'summary']
    lines.push('', `**BOPPPS 阶段预览**：${stages.map((stage) => `${present.has(stage) ? '✓' : '○'} ${phaseLabels[stage]}`).join(' · ')}`)
  }
  for (const slide of slides) {
    lines.push('', `## ${slide.slide_no ?? ''} ${slide.title || ''}`.trim(), '')
    const points = Array.isArray(slide.content_points) ? slide.content_points : []
    points.forEach((point) => lines.push(`- ${point}`))
    if (slide.teaching_intent) lines.push('', `**教学意图**：${slide.teaching_intent}`)
    if (slide.learner_question) lines.push(`**学生核心问题**：${slide.learner_question}`)
    if (slide.student_task) lines.push(`**学生任务**：${slide.student_task}`)
    const learningMeta = [
      slide.learning_phase ? `阶段：${phaseLabels[slide.learning_phase] || slide.learning_phase}` : '',
      slide.student_action_mode ? `参与：${slide.student_action_mode}` : '',
      slide.cognitive_load ? `认知负荷：${slide.cognitive_load}` : '',
      slide.estimated_minutes ? `用时：${slide.estimated_minutes} 分钟` : '',
    ].filter(Boolean)
    if (learningMeta.length) lines.push(`**学习设计**：${learningMeta.join(' · ')}`)
    if (Array.isArray(slide.learning_theories) && slide.learning_theories.length) {
      lines.push(`**理论依据**：${slide.learning_theories.join('、')}`)
    }
    if (slide.scaffolding) lines.push(`**学习支架**：${slide.scaffolding}`)
    if (slide.feedback_strategy) lines.push(`**反馈策略**：${slide.feedback_strategy}`)
    if (slide.visual_suggestion) lines.push(`**视觉建议**：${slide.visual_suggestion}`)
  }
  return lines.join('\n')
}

/** 解析 Python 大纲接口返回的单个 SSE 事件帧。 */
function parseOutlineSseFrame(frame) {
  let event = 'message'
  const dataLines = []
  String(frame || '').split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) event = line.slice(6).trim() || 'message'
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  })
  const rawData = dataLines.join('\n').trim()
  if (!rawData) return { event, data: {} }
  try {
    return { event, data: JSON.parse(rawData) }
  } catch {
    return { event, data: { _raw: rawData } }
  }
}

/**
 * 读取 Python 大纲 Agent 的 POST SSE 流。
 * 与普通对话的 OpenAI SSE 不同，这里需要消费 session/stage/question/final/done 等业务事件。
 */
async function readOutlineChatStream(response, callbacks = {}) {
  if (!response?.ok) {
    const responseText = await response?.text?.().catch(() => '') || ''
    let message = ''
    try {
      const payload = JSON.parse(responseText)
      message = payload?.message || payload?.detail || payload?.error || ''
    } catch {
      // 保留 HTTP 状态作为错误信息。
    }
    throw new Error(message || `大纲模型请求失败（HTTP ${response?.status || 0}）`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('大纲模型没有返回可读取的数据流')

  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finalData = null
  let doneData = null

  const dispatchFrame = (frame) => {
    const parsed = parseOutlineSseFrame(frame)
    if (!parsed.event || parsed.event === 'message') return
    const data = parsed.data || {}
    switch (parsed.event) {
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
      case 'outline_delta':
        callbacks.onOutlineDelta?.(data)
        break
      case 'final':
        finalData = data
        callbacks.onFinal?.(data)
        break
      case 'error':
        callbacks.onError?.(data)
        throw new Error(data.message || data.detail || '大纲模型生成失败')
      case 'done':
        doneData = data
        callbacks.onDone?.(data)
        break
      default:
        callbacks.onEvent?.(parsed.event, data)
        break
    }
  }

  const consumeFrames = (flush = false) => {
    const chunks = buffer.split(/\r?\n\r?\n/)
    buffer = flush ? '' : (chunks.pop() || '')
    chunks.forEach((chunk) => {
      if (chunk.trim()) dispatchFrame(chunk)
    })
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      consumeFrames(false)
      if (done) break
    }
    // 流结束时处理没有以空行结尾的最后一个事件。
    if (buffer.trim()) consumeFrames(true)
  } finally {
    reader.releaseLock?.()
  }

  if (doneData?.status === 'failed') {
    throw new Error(doneData.message || '大纲模型生成失败')
  }
  if (doneData?.status === 'need_clarification') return null
  if (!finalData) throw new Error('大纲模型未返回有效结果')
  return finalData
}

/** 将真实 Python 返回的 response 归一化为工作台和 Markdown 共用的 plan_json。 */
function normalizeRealOutlineResponse(response = {}) {
  const nestedOutline = response?.outline && typeof response.outline === 'object' && !Array.isArray(response.outline)
    ? response.outline
    : {}
  const nestedSlides = Array.isArray(nestedOutline.slides) ? nestedOutline.slides : []
  const responseSlides = Array.isArray(response.slides) ? response.slides : []
  const slides = nestedSlides.length ? nestedSlides : responseSlides
  const planJson = {
    ...nestedOutline,
    title: nestedOutline.title || response.title || infoForm.courseName.trim() || '教学设计方案',
    summary: nestedOutline.summary || response.summary || '',
    subject: nestedOutline.subject || response.subject || infoForm.subject,
    grade: nestedOutline.grade || response.grade || infoForm.grade,
    requirements: nestedOutline.requirements || response.requirements || infoForm.requirements,
    slide_count: Number(nestedOutline.slide_count) || Number(response.slide_count) || slides.length,
    slides,
  }
  ;['teaching_design_chain', 'interactive_assets', 'diagram_assets', 'learning_graphs', 'quality_report', 'generation_options', 'retrieval_matches', 'enable_web', 'web_references', 'web_search_status']
    .forEach((key) => {
      if (planJson[key] === undefined && response[key] !== undefined) planJson[key] = response[key]
    })
  const outlineId = String(response.outline_id || nestedOutline.outline_id || '').trim()
  if (outlineId) planJson.outline_id = outlineId
  if (response.version !== undefined && planJson.version === undefined) planJson.version = response.version
  return planJson
}

/** 展示并保存真实模型生成的大纲，供确认按钮和创作工作台继续使用。 */
function applyRealOutlineResponse(response) {
  const planJson = normalizeRealOutlineResponse(response)
  if (!Array.isArray(planJson.slides) || !planJson.slides.length) throw new Error('大纲模型未返回页面结构')

  showLearningGraphs(response?.learning_graphs || planJson.learning_graphs)

  const outlineId = String(response?.outline_id || planJson.outline_id || '').trim()
  const version = Number(planJson.version) || 1
  const task = {
    ...(response || {}),
    plan_json: planJson,
    python_session_id: outlinePythonSessionId.value || String(props.sessionId || ''),
    python_outline_id: outlineId || null,
    plan_version: version,
    plan_confirm_status: 'pending',
  }
  planTask.value = task
  planVersion.value = version
  outlineData.value = {
    markdown: planJsonToMarkdown(planJson),
    title: planJson.title || '教学设计方案',
    slideCount: Number(planJson.slide_count) || planJson.slides.length,
    planJson,
    outlineId: outlineId || undefined,
  }
  saveOutlineDraft(props.sessionId, {
    ...task,
    plan_json: planJson,
    python_session_id: task.python_session_id,
    python_outline_id: outlineId || null,
    plan_confirm_status: 'pending',
  })
  phase.value = 'outline_ready'
  addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
  addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
  void scrollToBottom()
}

/** 通过 Python SSE 真实 Agent 生成/修改大纲；请求体直接使用 Python DTO 的字段类型。 */
async function requestRealOutlineChat(message) {
  const resourceIds = activeResourceIds.value
  const response = await streamOutlineChat({
    user_id: String(userStore.userInfo?.user_id || '10001'),
    session_id: outlinePythonSessionId.value || String(props.sessionId || '') || undefined,
    message,
    history: normalizeConversationHistory(props.continuationHistory),
    known_context: {
      title: infoForm.courseName.trim(),
      course_name: infoForm.courseName.trim(),
      stage: infoForm.stage,
      subject: infoForm.subject,
      grade: infoForm.grade,
      textbook: infoForm.textbook,
      class_level: infoForm.classLevel,
      requirements: infoForm.requirements,
      slide_count_range: getSlideCountRange(),
      teaching_model: selectedTeachingModel.value,
      teaching_style: selectedTeachingStyle.value,
      workspace_context: activeWorkspaceContext.value,
    },
    resource_ids: resourceIds,
    enable_rag: publicResourceEnabled.value,
    enable_web: infoForm.enableWeb,
    slide_count: null,
    slide_count_range: getSlideCountRange(),
    language: 'zh-CN',
    teaching_model: selectedTeachingModel.value,
    teaching_style: selectedTeachingStyle.value,
  })

  let clarification = null
  let finalResponse = null
  await readOutlineChatStream(response, {
    onSession: (data) => {
      if (data?.session_id) outlinePythonSessionId.value = String(data.session_id)
    },
    onStage: (data) => {
      outlineGenerationStage.value = String(data?.message || data?.name || '正在生成教学设计大纲…')
    },
    onEvent: (event, data) => {
      if (event === 'learning_graphs') showLearningGraphs(data)
    },
    onQuestion: (data) => {
      clarification = data
    },
    onFinal: (data) => {
      finalResponse = data
    },
  })

  if (clarification) {
    const question = normalizePlanningClarification(clarification.question || clarification)
    if (question) {
      saveOutlineDraft(props.sessionId, {
        ...(readOutlineDraft(props.sessionId) || {}),
        python_session_id: outlinePythonSessionId.value || String(props.sessionId || ''),
        clarification: question,
        enable_web: infoForm.enableWeb,
        plan_confirm_status: 'pending',
      })
      lastClarification.value = question.text
      phase.value = 'clarifying'
      addMessage('assistant', 'clarification', question.text)
      openPlanningClarification(question)
      return { status: 'need_clarification' }
    }
  }

  if (!finalResponse) throw new Error('大纲模型未返回有效结果')
  const qualityCheckedResponse = await ensureOutlineQuality(finalResponse)
  applyRealOutlineResponse(qualityCheckedResponse)
  return { status: 'completed' }
}

// ========== 大纲请求与结果落库 ==========

/**
 * 组合补充信息为 API-13 的 message 输入。
 * @param {string} extra - 追加的澄清回复或修改要求
 * @returns {string} 拼装后的自然语言输入
 */
function buildContextMessage(extra = '') {
  const parts = [
    `${infoForm.stage}${infoForm.subject}${infoForm.grade}${infoForm.textbook}`,
    `课程名称：《${infoForm.courseName.trim()}》`,
    `班级学情：${infoForm.classLevel}`,
    `个性化需求：${infoForm.requirements}`,
  ]
  const pageRange = getSlideCountRange()
  if (pageRange) parts.push(`PPT 总页数：${pageRange.min_pages}至${pageRange.max_pages}页（含封面和总结），由 AI 在范围内自主规划`)
  if (extra) parts.push(`补充要求：${extra}`)
  return parts.join('，')
}

/**
 * 解析 SSE 响应体，按事件边界逐步调用 onEvent(event, data)，直至流结束。
 * @param {Response} res - FastAPI 大纲流返回的 fetch Response
 * @param {(event: string, data: Object) => void} onEvent - 事件回调
 */
async function consumeSseStream(res, onEvent) {
  if (!res.ok) {
    let msg = SYSTEM_MESSAGES.connectionError
    try { const err = await res.json(); msg = err?.message || err?.error || msg } catch { /* 忽略 */ }
    throw new Error(msg)
  }
  const reader = res.body?.getReader?.()
  if (!reader) throw new Error('当前浏览器不支持流式响应')
  const decoder = new TextDecoder('utf-8')
  let pending = ''
  let currentEvent = ''
  let currentData = ''
  const dispatchEvent = async () => {
    if (currentEvent || currentData) {
      if (currentData) {
        let parsed = {}
        try { parsed = JSON.parse(currentData) } catch { parsed = { message: currentData } }
        await onEvent(currentEvent || 'message', parsed)
      }
      currentEvent = ''
      currentData = ''
    }
  }
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    pending += decoder.decode(value, { stream: true })
    let idx
    while ((idx = pending.indexOf('\n')) !== -1) {
      const line = pending.slice(0, idx).replace(/\r$/, '')
      pending = pending.slice(idx + 1)
      if (line === '') {
        await dispatchEvent()
      } else if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        currentData += (currentData ? '\n' : '') + line.slice(5).trim()
      }
    }
  }
  await dispatchEvent()
}

/**
 * 将流式 final 事件中的大纲数据渲染到消息区（等价于 loadPlan 的渲染结果）。
 * @param {Object} data - final 事件 data（含 outline/slides/title/outline_id 等）
 */
function renderStreamedOutline(data) {
  const planJson =
    data && data.outline && typeof data.outline === 'object' ? data.outline : data
  if (!planJson || typeof planJson !== 'object') {
    ElMessage.info('大纲已生成，但数据格式异常，请稍后重试或重新拉取。')
    phase.value = 'info'
    return
  }
  const slides = Array.isArray(planJson.slides) ? planJson.slides : []
  showLearningGraphs(data?.learning_graphs || planJson.learning_graphs)
  const title = data?.title || planJson.title || '教学设计方案'
  planTask.value = {
    ...(planTask.value || {}),
    plan_json: planJson,
    python_outline_id: data?.outline_id || planJson.outline_id,
  }
  planVersion.value = Number(planJson.version) || 1
  outlineData.value = {
    markdown: planJsonToMarkdown(planJson),
    title,
    slideCount: slides.length || Number(planJson.slide_count) || 0,
    planJson,
    outlineId: data?.outline_id || planJson.outline_id,
  }
  phase.value = 'outline_ready'
  addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
  addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
}

/**
 * 实时渲染逐条到达的 outline_delta 页（临时预览消息，final 到达后被正式大纲替换）。
 * @param {Object} slide - 单页大纲增量
 */
function renderLiveOutline(slide) {
  if (!slide || !slide.title) return
  if (liveMsgId == null) {
    liveMsgId = ++messageSeq
    messages.push({ id: liveMsgId, role: 'assistant', type: 'markdown', content: '', data: { slides: [], isLive: true } })
  }
  const msg = messages.find((m) => m.id === liveMsgId)
  if (!msg) return
  const slides = msg.data?.slides || []
  if (!slides.some((s) => s.slide_no === slide.slide_no)) slides.push(slide)
  msg.data = { ...msg.data, slides }
  msg.content = planJsonToMarkdown({ title: '正在生成大纲…', slides })
  scrollToBottom()
}

/** 移除实时预览消息（final/question/error/done 到达时调用）。 */
function finalizeLiveOutline() {
  if (liveMsgId == null) return
  const i = messages.findIndex((m) => m.id === liveMsgId)
  if (i >= 0) messages.splice(i, 1)
  liveMsgId = null
}

/** 图谱先于大纲展示；同一次流的 final 只更新卡片，不重复插入。 */
function showLearningGraphs(graphs) {
  activeLearningGraphMessageId = upsertLearningGraphMessage(messages, graphs, activeLearningGraphMessageId, addMessage)
  void scrollToBottom()
}

function hasCompleteLearningGraphs(graphs) {
  return ['knowledge', 'skill'].every((kind) => Array.isArray(graphs?.[kind]?.nodes) && graphs[kind].nodes.length >= 4)
}

/**
 * 浏览器直连 FastAPI 获取大纲 SSE；Java 仅保存生成结果。
 * 由 final 事件渲染最终大纲；question 进入澄清阶段；error/done(failed) 提示错误。
 * @param {string} message - 本轮自然语言输入
 * @param {Object} options - 是否把切换前的普通对话作为首次备课背景注入
 */
async function sendMessageToBackend(message, { includeContinuation = false, clarificationContext = {}, confirmLearningGraphs = false, inputKind = '' } = {}) {
  phase.value = 'generating_outline'
  isRequesterLoading.value = true
  outlineGenerationStage.value = confirmLearningGraphs ? '正在根据已确认的双图谱生成大纲…' : '正在分析课程信息并生成双图谱…'
  if (!confirmLearningGraphs) activeLearningGraphMessageId = null
  const payload = {
    message,
    resource_ids: JSON.stringify(activeResourceIds.value),
    enable_rag: publicResourceEnabled.value,
    enable_web: infoForm.enableWeb,
    model_profile: selectedModelProfile.value,
    reasoning_effort: selectedReasoningEffort.value,
    known_context: JSON.stringify({
      title: infoForm.courseName.trim(),
      subject: infoForm.subject,
      grade: infoForm.grade,
      slide_count_range: getSlideCountRange(),
      teaching_model: selectedTeachingModel.value,
      teaching_style: selectedTeachingStyle.value,
      workspace_context: activeWorkspaceContext.value,
      ...clarificationContext,
    }),
  }
  let finished = false
  let finalResult = null
  let questionResult = null
  let graphResult = null
  let awaitingGraphConfirmation = false
  let streamError = ''
  try {
    saveOutlineDraft(props.sessionId, { ...(readOutlineDraft(props.sessionId) || {}), enable_web: payload.enable_web })
    const res = await streamOutlineChat({
      user_id: String(userStore.userInfo?.user_id || ''),
      session_id: outlinePythonSessionId.value || undefined,
      message,
      history: includeContinuation ? normalizeConversationHistory(props.continuationHistory) : [],
      resource_ids: activeResourceIds.value,
      enable_rag: payload.enable_rag,
      enable_web: payload.enable_web,
      model_profile: payload.model_profile,
      reasoning_effort: payload.reasoning_effort,
      known_context: JSON.parse(payload.known_context),
      slide_count: null,
      slide_count_range: getSlideCountRange(),
      language: 'zh-CN',
      teaching_model: selectedTeachingModel.value,
      teaching_style: selectedTeachingStyle.value,
      confirm_learning_graphs: confirmLearningGraphs,
    })
    await consumeSseStream(res, (event, data) => {
      if (event === 'stage') {
        outlineGenerationStage.value = String(data?.message || data?.name || '正在处理课程信息…')
        return
      }
      if (event === 'session' && data.session_id) outlinePythonSessionId.value = String(data.session_id)
      if (event === 'learning_graphs') {
        if (!hasCompleteLearningGraphs(data)) {
          streamError = '双图谱生成不完整，请重新生成后再确认'
          return
        }
        showLearningGraphs(data)
        graphResult = data
        return
      }
      if (event === 'outline_delta') {
        // 逐页实时回传，边生成边渲染到预览消息
        renderLiveOutline(data.slide)
        return
      }
      if (event === 'question') {
        finished = true
        questionResult = data
        return
      }
      if (event === 'final') {
        finished = true
        finalResult = data
        return
      }
      if (event === 'error') {
        finished = true
        streamError = data.message || SYSTEM_MESSAGES.connectionError
        return
      }
      if (event === 'done') {
        finished = true
        if (data.status === 'awaiting_graph_confirmation') awaitingGraphConfirmation = true
        if (data.status === 'failed') streamError ||= data.message || SYSTEM_MESSAGES.connectionError
      }
    })
    finalizeLiveOutline()
    const status = finalResult ? 'completed' : questionResult ? 'need_clarification'
      : awaitingGraphConfirmation && graphResult ? 'awaiting_graph_confirmation' : 'failed'
    // A failed confirmation must not overwrite the saved graph-review checkpoint.
    if (confirmLearningGraphs && status === 'failed') throw new Error(streamError || '大纲生成失败，请重试确认')
    const saved = await saveDirectOutlineResult(props.sessionId, {
      message,
      input_kind: inputKind,
      status,
      python_session_id: outlinePythonSessionId.value,
      question: normalizePlanningClarification(questionResult?.question)?.text || '',
      final_data: finalResult,
      graph_data: awaitingGraphConfirmation ? { learning_graphs: graphResult, status, enable_web: payload.enable_web } : undefined,
      error_message: streamError,
    })
    if (!isOk(saved)) throw new Error(saved?.message || '备课结果保存失败')
    if (finalResult) renderStreamedOutline(finalResult)
    else if (awaitingGraphConfirmation && graphResult) {
      phase.value = 'graph_review'
      saveOutlineDraft(props.sessionId, {
        ...(readOutlineDraft(props.sessionId) || {}),
        python_session_id: outlinePythonSessionId.value,
        learning_graphs: graphResult,
        status: 'awaiting_graph_confirmation',
      })
    }
    else if (questionResult) {
      const question = normalizePlanningClarification(questionResult.question || questionResult.message)
      lastClarification.value = question?.text || ''
      phase.value = 'clarifying'
      if (question) {
        addMessage('assistant', 'clarification', question.text)
        openPlanningClarification(question)
      }
    } else if (streamError) throw new Error(streamError)
    if (!finished) {
      finalizeLiveOutline()
      ElMessage.error(SYSTEM_MESSAGES.connectionError)
      phase.value = 'info'
    }
  } catch (error) {
    finalizeLiveOutline()
    ElMessage.error(error?.message || SYSTEM_MESSAGES.connectionError)
    phase.value = confirmLearningGraphs ? 'graph_review' : 'info'
  } finally {
    isRequesterLoading.value = false
    outlineGenerationStage.value = ''
  }
}

async function confirmLearningGraphs() {
  if (phase.value !== 'graph_review' || isRequesterLoading.value) return
  await sendMessageToBackend('教师已确认知识图谱与技能图谱，请据此生成大纲。', { confirmLearningGraphs: true })
}

async function saveLearningGraphs(editedGraphs) {
  if (phase.value !== 'graph_review' || isRequesterLoading.value || !outlinePythonSessionId.value) {
    throw new Error('当前不能修改双图谱')
  }
  isRequesterLoading.value = true
  try {
    const result = await updateOutlineLearningGraphs(outlinePythonSessionId.value, editedGraphs)
    if (!isOk(result)) throw new Error(result?.message || '双图谱保存失败')
    const graphs = result.data.learning_graphs
    showLearningGraphs(graphs)
    saveOutlineDraft(props.sessionId, {
      ...(readOutlineDraft(props.sessionId) || {}), python_session_id: outlinePythonSessionId.value,
      learning_graphs: graphs, status: 'awaiting_graph_confirmation',
    })
    const saved = await saveDirectOutlineResult(props.sessionId, {
      message: '教师确认保存了双图谱修改', status: 'awaiting_graph_confirmation',
      python_session_id: outlinePythonSessionId.value,
      graph_data: { learning_graphs: graphs, status: 'awaiting_graph_confirmation', enable_web: infoForm.enableWeb },
    })
    if (!isOk(saved)) throw new Error(saved?.message || '会话记录同步失败，请再次保存')
    ElMessage.success('双图谱已保存，确认后将据此生成大纲')
  } finally { isRequesterLoading.value = false }
}

async function aiEditLearningGraphs(graphs, kind, instruction) {
  if (phase.value !== 'graph_review' || isRequesterLoading.value || !outlinePythonSessionId.value) throw new Error('当前不能修改双图谱')
  isRequesterLoading.value = true
  try {
    const result = await aiEditOutlineLearningGraphs(outlinePythonSessionId.value, graphs, kind, instruction)
    if (!isOk(result)) throw new Error(result?.message || 'AI 修改失败')
    return result.data.learning_graphs
  } finally { isRequesterLoading.value = false }
}

/** 从 API-13A 返回的完整会话中取出本轮新增内容，避免语音消息只在服务端保存、页面却没有回显。 */
function sessionResponseData(response) {
  if (isOk(response)) return response.data || {}
  if (response && typeof response === 'object' && response.data && typeof response.data === 'object') return response.data
  return response || {}
}

function appendAudioConversation(conversation = {}) {
  const stored = parseStoredMessages(conversation.messages)
    .filter((message) => message && (message.role === 'user' || message.role === 'assistant') && String(message.content || '').trim())
  const latestUser = [...stored].reverse().find((message) => message.role === 'user')
  const latestAssistant = [...stored].reverse().find((message) => message.role === 'assistant')
  const lastVisible = messages[messages.length - 1]
  if (latestUser && !(lastVisible?.role === 'user' && lastVisible.content === String(latestUser.content).trim())) {
    addMessage('user', 'text', String(latestUser.content).trim())
  }

  const question = conversation.last_question || (latestAssistant?.type === 'question' ? latestAssistant.content : '')
  if (question) {
    const normalizedQuestion = normalizePlanningClarification(question)
    lastClarification.value = normalizedQuestion?.text || String(question)
    phase.value = 'clarifying'
    addMessage('assistant', 'clarification', normalizedQuestion?.text || String(question))
    openPlanningClarification(normalizedQuestion)
    return
  }
  if (latestAssistant && String(latestAssistant.content || '').trim()) {
    addMessage('assistant', 'text', String(latestAssistant.content).trim())
  }
}

/** 语音录音完成后的入口：正式备课会话上传到 API-13A，并同步最新会话/大纲状态。 */
async function handleChatVoice(file) {
  if (!file || voiceSubmitting.value) return
  if (isGeneralChat.value) {
    voiceSubmitting.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('language', 'zh')
      const response = await transcribeAudio(formData)
      const text = String(response?.data?.text || response?.text || '').trim()
      if (!text) throw new Error('未能识别到有效语音')
      composerInput.value = composerInput.value.trim()
        ? `${composerInput.value.trim()} ${text}`
        : text
      ElMessage.success('语音已转写，可继续发送')
    } catch (error) {
      ElMessage.error(error?.message || '语音识别失败，请重试')
    } finally {
      voiceSubmitting.value = false
    }
    return
  }

  voiceSubmitting.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('language', 'zh')
    const response = await transcribeAudio(formData)
    const transcript = String(response?.data?.text || response?.text || '').trim()
    if (!transcript) throw new Error('未能识别到有效语音')
    const message = [composerInput.value.trim(), transcript].filter(Boolean).join('\n')
    addMessage('user', 'text', message)
    await sendMessageToBackend(message)
    composerInput.value = ''
  } catch (error) {
    ElMessage.error(error?.message || '语音会话提交失败，请重试')
  } finally {
    voiceSubmitting.value = false
    await scrollToBottom()
  }
}

function handleChatVoiceError(error) {
  ElMessage.error(error?.message || '录音失败，请检查浏览器麦克风权限')
}

/**
 * 调用 API-14 拉取大纲 plan_json，转换为 Markdown 后展示。
 */
async function loadPlan() {
  const res = await getAiPlan(props.sessionId)
  const data = isOk(res) ? res.data : null
  const planJson = data?.plan_json
  if (!planJson || typeof planJson !== 'object') {
    ElMessage.info('大纲尚未生成，请稍后重试或补充信息后继续。')
    phase.value = 'info'
    return
  }
  planTask.value = data
  planVersion.value = Number(data?.plan_version) || Number(planJson.version) || 1
  outlineData.value = {
    markdown: planJsonToMarkdown(planJson),
    title: planJson.title || '教学设计方案',
    slideCount: Number(planJson.slide_count) || 0,
    planJson,
    outlineId: data?.python_outline_id || planJson.outline_id,
  }
  phase.value = 'outline_ready'
  addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
  addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
  await scrollToBottom()
}

// ========== 补充信息确认 ==========

/** 确认补充信息，发起教学大纲生成（真实模式：Python SSE；兼容模式：API-13 → API-14） */
async function confirmInfo() {
  if (isRequesterLoading.value) return
  infoForm.grade = normalizePlanningGrade(infoForm.stage, infoForm.grade)
  if (!infoForm.stage || !infoForm.subject || !infoForm.grade) {
    ElMessage.warning('请先补充学段、学科和年级')
    return
  }
  // 校验课程名称必填
  if (!infoForm.courseName.trim()) {
    ElMessage.warning('请输入课程名称')
    return
  }
  const pageError = slideRangeError(infoForm.minPages, infoForm.maxPages)
  if (pageError) {
    ElMessage.warning(pageError)
    return
  }
  await sendMessageToBackend(buildContextMessage(), { includeContinuation: true, inputKind: 'course_info_confirmation' })
}

/** 澄清回复：把教师针对问题的回复作为下一轮输入继续生成 */
async function handleClarificationReply() {
  const text = composerInput.value.trim()
  if (!text) {
    ElMessage.warning('请输入澄清回复')
    return
  }
  addMessage('user', 'text', text)
  composerInput.value = ''
  await sendMessageToBackend(text)
}

/** 提交后端 Agent 返回的结构化澄清问题。 */
async function submitPlanningClarification(payload = {}) {
  if (planningClarificationSubmitting.value) return
  planningClarificationSubmitting.value = true
  try {
    const answer = String(payload.answer || payload.value || '').trim()
    if (!answer) return
    planningClarificationVisible.value = false
    addMessage('user', 'text', answer)
    await sendMessageToBackend(answer, { clarificationContext: payload.knownContext || {} })
  } finally {
    planningClarificationSubmitting.value = false
  }
}

/** 提取普通主对话的上下文，发送给本地开发代理背后的真实大模型。 */
function getGeneralChatHistory() {
  return messages
    .filter((item) => item.type === 'text' && (item.role === 'user' || item.role === 'assistant') && String(item.content || '').trim())
    .map((item) => ({ role: item.role, content: String(item.content).trim() }))
    .slice(-12)
}

/** 读取 OpenAI-compatible SSE，将模型增量内容实时写入当前消息。 */
async function readGeneralChatStream(response, assistantMessage) {
  await readOpenAiTextStream(response, (_delta, content) => {
    assistantMessage.content = content
    void scrollToBottom()
  })
}

function messageTraceLabel(message) {
  const trace = message.data
  if (!trace?.message_id) return undefined
  const time = trace.created_at ? new Date(trace.created_at).toLocaleString('zh-CN') : '时间未知'
  return `${time} · 消息 ID：${trace.message_id} · 回合 ID：${trace.turn_id || '未知'}`
}

/** 从模型文本中提取 JSON 对象，兼容模型偶尔附带的代码围栏。 */
function parseModelJsonObject(text) {
  const raw = String(text || '').trim()
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const candidate = (fenced?.[1] || raw).trim()
  const start = candidate.indexOf('{')
  const end = candidate.lastIndexOf('}')
  if (start < 0 || end <= start) return null
  try {
    const parsed = JSON.parse(candidate.slice(start, end + 1))
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

/** 兼容 Python 返回顶层 slides 和嵌套 outline.slides 两种结构。 */
function outlineCandidate(value = {}) {
  return value?.outline && typeof value.outline === 'object' && !Array.isArray(value.outline)
    ? value.outline
    : value
}

/** 检测 Python 回退大纲特征，避免重复内容继续进入确认和 PPT 生成。 */
function outlineNeedsRepair(value = {}) {
  const outline = outlineCandidate(value)
  const slides = Array.isArray(outline?.slides) ? outline.slides.filter((slide) => slide && typeof slide === 'object') : []
  if (slides.length < 4) return false

  const fallbackTitleCount = slides
    .slice(1)
    .filter((slide) => /^重点解析\s*\d+$/.test(String(slide.title || '').trim()))
    .length
  if (fallbackTitleCount > 0) return true

  const pointFrequency = new Map()
  slides.forEach((slide) => {
    const points = Array.isArray(slide.content_points)
      ? [...new Set(slide.content_points.map((point) => String(point || '').trim()).filter(Boolean))]
      : []
    points.forEach((point) => pointFrequency.set(point, (pointFrequency.get(point) || 0) + 1))
  })
  const commonPointCount = [...pointFrequency.values()].filter((count) => count >= Math.ceil(slides.length * 0.6)).length
  const intents = new Set(slides.map((slide) => String(slide.teaching_intent || '').trim()).filter(Boolean))
  const visuals = new Set(slides.map((slide) => String(slide.visual_suggestion || '').trim()).filter(Boolean))
  return commonPointCount >= 2 && (intents.size <= Math.ceil(slides.length * 0.5) || visuals.size <= Math.ceil(slides.length * 0.5))
}

function outlineRepairPrompt(response) {
  const outline = outlineCandidate(response) || {}
  const context = {
    title: infoForm.courseName.trim() || outline.title || '教学设计方案',
    subject: infoForm.subject,
    grade: infoForm.grade,
    requirements: infoForm.requirements,
  }
  return [
    '请修复下面这份教学 PPT 大纲。原大纲疑似使用了回退模板，多个页面的教学要点、教学意图和视觉建议重复。',
    '请保留教师的课程主题和真实需求，重新设计每一页的教学任务与内容。每页必须有不同的标题、content_points、teaching_intent 和 visual_suggestion，不能只替换页码或标题。',
    '请保留或补全 cover、agenda、content、activity/practice、summary 等教学结构，页数保持不变。只输出完整 JSON 对象，不要 Markdown、解释或代码围栏。',
    `课程上下文：${JSON.stringify(context, null, 2)}`,
    `待修复大纲：${JSON.stringify(outline, null, 2)}`,
    'JSON 至少包含 title、summary、slides；每个 slide 至少包含 slide_no、title、slide_type、content_points（数组）、teaching_intent、visual_suggestion。',
  ].join('\n\n')
}

/** 使用前端开发代理调用同一大模型，修复后端回退导致的重复大纲；不改后端源码。 */
async function requestOutlineRepairWithModel(response) {
  const modelResponse = await streamGeneralChat({
    mode: 'outline-repair',
    user_id: String(userStore.userInfo?.user_id || '10001'),
      messages: [{ role: 'user', content: outlineRepairPrompt(response) }],
      model_profile: selectedModelProfile.value,
      reasoning_effort: selectedReasoningEffort.value,
  })
  if (!modelResponse.ok) {
    let message = ''
    try {
      const payload = await modelResponse.json()
      message = payload?.message || ''
    } catch {
      // 保留 HTTP 状态作为错误信息。
    }
    throw new Error(message || `大纲重写请求失败（HTTP ${modelResponse.status}）`)
  }

  const assistantMessage = { content: '' }
  await readGeneralChatStream(modelResponse, assistantMessage)
  const parsed = parseModelJsonObject(assistantMessage.content)
  const parsedOutline = outlineCandidate(parsed || {})
  const slides = Array.isArray(parsedOutline?.slides) ? parsedOutline.slides : []
  if (!slides.length) throw new Error('大纲重写模型未返回有效页面结构')

  const originalOutline = outlineCandidate(response) || {}
  const repairedOutline = {
    ...originalOutline,
    ...(parsedOutline || {}),
    slides,
    slide_count: slides.length,
  }
  return {
    ...response,
    ...(parsed || {}),
    outline: repairedOutline,
    slides,
    slide_count: slides.length,
    client_outline_repair: true,
  }
}

async function ensureOutlineQuality(response) {
  if (!useRealOutlineApi || !outlineNeedsRepair(response)) return response
  outlineGenerationStage.value = '检测到大纲内容重复，正在请求模型重新设计…'
  const repaired = await requestOutlineRepairWithModel(response)
  if (outlineNeedsRepair(repaired)) throw new Error('模型重写后仍存在重复内容，请点击重试')
  ElMessage.success('已自动修复重复大纲，页面内容已重新设计')
  return repaired
}

/** 通过本地开发代理调用已配置的 DeepSeek/OpenAI-compatible 大模型。 */
async function requestGeneralChatReply() {
  if (resourceUploading.value) return ElMessage.warning('资料正在上传解析，请完成后再发送')
  const latestUserMessage = [...messages].reverse().find((item) => item.role === 'user' && item.type === 'text')
  if (!latestUserMessage?.content?.trim()) return
  const assistantMessage = addMessage('assistant', 'text', '')
  isRequesterLoading.value = true
  let routedToPlanning = false
  let turn = null
  try {
    const begun = await beginGeneralChatTurn({
      session_id: generalSessionId.value,
      message: latestUserMessage.content,
      model_profile: selectedModelProfile.value,
      reasoning_effort: selectedReasoningEffort.value,
    })
    if (!isOk(begun)) throw new Error(begun?.message || '保存提问失败')
    turn = begun.data
    generalSessionId.value = turn.conversation_id
    latestUserMessage.data = { message_id: turn.user_message_id, turn_id: turn.turn_id, created_at: turn.created_at }
    latestSessionPush.value = { id: turn.conversation_id, title: turn.title, updated_at: turn.created_at, mode: 'general' }
    emit('general-session', { id: turn.conversation_id, title: turn.title })
    const routeResult = await routeTeachingChat({
      user_id: String(userStore.userInfo?.user_id || ''),
      messages: turn.messages.slice(-8),
      route_preference: selectedRoutePreference.value || 'auto',
    })
    if (!isOk(routeResult)) throw new Error(routeResult?.message || '意图分流失败')
    const route = routeResult.data || {}
    routedToPlanning = route.next_stage === 'outline_graph' || route.route === 'planning'
    const routedToBatch = route.next_stage === 'batch_plan' || route.route === 'batch'
    let response
    if (routedToBatch) {
      const current = activeBatchPlan.value
      const planned = current?.status === 'draft'
        ? await reviseBatchPlan(current.id, { revision: current.revision, message: latestUserMessage.content,
            resource_ids: activeResourceIds.value.filter(id => !(current.resource_ids || []).includes(id)),
            enable_rag: publicResourceEnabled.value })
        : await createBatchPlan({ message: latestUserMessage.content, resource_ids: [...activeResourceIds.value],
            session_id: String(generalSessionId.value), single: Boolean(activeWorkspaceContext.value.single),
            enable_rag: publicResourceEnabled.value })
      activeBatchPlan.value = planned.data
      assistantMessage.type = 'batch_plan'; assistantMessage.plan = planned.data
      assistantMessage.content = planned.data.needs_input ? '已进入批量备课，请补充教学计划或目录，或明确选择先使用 AI 建议目录。' : `已整理“${planned.data.title}”的生成计划，共 ${planned.data.items.length} 份候选课件，请核对范围与页数后确认。`
    } else if (routedToPlanning) {
      assistantMessage.content = '已进入备课流程，请补充课程信息。'
    } else {
      response = await streamGeneralChat({
        user_id: String(userStore.userInfo?.user_id || ''),
        mode: 'chat',
        messages: turn.messages,
        resource_ids: [...activeResourceIds.value],
        enable_rag: publicResourceEnabled.value,
        model_profile: selectedModelProfile.value,
        reasoning_effort: selectedReasoningEffort.value,
      })
    }
    if (response && !response.ok) {
      let message = ''
      try {
        const payload = await response.json()
        message = payload?.message || ''
      } catch {
        // 保留 HTTP 状态作为错误信息。
      }
      throw new Error(message || `模型请求失败（HTTP ${response.status}）`)
    }
    if (response) await readOpenAiTextStream(response, (_delta, content) => {
      assistantMessage.content = content
      void scrollToBottom()
    })
    if (!assistantMessage.content.trim()) throw new Error('模型未返回有效内容')
    const completed = await completeGeneralChatTurn(turn.conversation_id, {
      turn_id: turn.turn_id,
      route: routedToBatch ? 'batch' : routedToPlanning ? 'planning' : 'chat',
      reason: route.reason || '',
      content: assistantMessage.content,
      status: 'completed',
      model_profile: selectedModelProfile.value,
      reasoning_effort: selectedReasoningEffort.value,
      resource_ids: JSON.stringify(activeResourceIds.value),
    })
    if (!isOk(completed)) throw new Error(completed?.message || '回复保存失败')
    assistantMessage.data = completed.data
    if (routedToPlanning) {
      emit('planning-request', {
        existingSessionId: generalSessionId.value,
        prompt: latestUserMessage.content,
        resourceIds: [...activeResourceIds.value],
        workspaceContext: activeWorkspaceContext.value,
        history: getGeneralChatHistory().slice(0, -2),
      })
    }
  } catch (error) {
    if (!assistantMessage.content.trim()) {
      assistantMessage.content = `大模型暂时无法回复：${error?.message || '连接失败，请检查模型配置。'}`
    }
    if (turn && !assistantMessage.data?.message_id) {
      try {
        const failed = await completeGeneralChatTurn(turn.conversation_id, {
          turn_id: turn.turn_id, route: 'chat', content: assistantMessage.content,
          status: 'failed', model_profile: selectedModelProfile.value,
          reasoning_effort: selectedReasoningEffort.value,
        })
        if (isOk(failed)) assistantMessage.data = failed.data
      } catch { /* 保留原始请求错误。 */ }
    }
    ElMessage.error(error?.message || '大模型连接失败，请检查配置')
  } finally {
    isRequesterLoading.value = false
    await scrollToBottom()
  }
}

/** 普通主对话发送消息。备课澄清仍沿用 API-13 流程。 */
async function handleGeneralMessage() {
  if (isRequesterLoading.value) return
  const text = composerInput.value.trim()
  if (!text) return
  addMessage('user', 'text', text)
  composerInput.value = ''

  await requestGeneralChatReply()
}

function handleComposerSubmit() {
  if (isGeneralChat.value) {
    void handleGeneralMessage()
    return
  }
  if (phase.value === 'clarifying') void handleClarificationReply()
}

/** 聊天快捷键：Enter 发送，Shift+Enter 换行；中文输入法候选确认不触发发送；触屏设备 Enter 仅换行，发送走按钮。 */
function handleComposerKeydown(event) {
  if (event.isComposing || event.keyCode === 229 || event.shiftKey) return
  if (isTouchDevice) return
  event.preventDefault()
  handleComposerSubmit()
}

// ========== 大纲操作 ==========

/** 依据已确认大纲的大纲数据填充资源生成卡片信息（确认与历史恢复共用）。 */
function fillGenResource(data) {
  if (!data) return
  const slideCount = data?.slideCount || 0
  genResource.name = (infoForm.courseName.trim() || data?.title || '教学设计') + ' 课件'
  genResource.slideCount = slideCount || GEN_RESOURCE_DEFAULTS.slideCount
  genResource.theme = pptTemplateName.value || GEN_RESOURCE_DEFAULTS.theme
  genResource.description = RESOURCE_CARD_LABELS.pptDesc
    .replace('{count}', genResource.slideCount)
    .replace('{theme}', genResource.theme)
}

/** 确认教学设计方案：提交确认动作并切换到资源生成卡片阶段 */
async function confirmOutline() {
  const data = outlineData.value
  if (!data || outlineConfirming.value) return false
  outlineConfirming.value = true
  try {
    const confirmation = await confirmAiPlan(props.sessionId, { action: 'confirm', plan_version: planVersion.value })
    if (!isOk(confirmation)) throw new Error(confirmation?.message || '大纲确认请求未成功')

    // 不能只相信确认接口的 HTTP 成功响应；回读状态后才允许进入生成阶段。
    const confirmedPlanResponse = await getAiPlan(props.sessionId)
    const confirmedPlan = isOk(confirmedPlanResponse) ? confirmedPlanResponse.data : null
    if (String(confirmedPlan?.plan_confirm_status || '').toLowerCase() !== 'confirmed') {
      throw new Error(confirmedPlanResponse?.message || '服务端尚未确认教学设计大纲')
    }

    planTask.value = { ...(planTask.value || {}), ...confirmedPlan, plan_confirm_status: 'confirmed' }
    const localOutlineDraft = readOutlineDraft(props.sessionId)
    if (localOutlineDraft) {
      saveOutlineDraft(props.sessionId, {
        ...localOutlineDraft,
        plan_confirm_status: 'confirmed',
        plan_version: planVersion.value,
      })
    }
    await loadPptTemplates()
    fillGenResource(data)
    phase.value = 'resource_ready'
    const feedbackSession = confirmedPlan.python_session_id || outlinePythonSessionId.value
    if (feedbackSession) {
      void recordAiFeedback({ session_id: String(feedbackSession), action: 'accept', target_type: 'outline' }).catch(() => {})
    }
    return true
  } catch (error) {
    // 不允许把浏览器草稿标记为已确认；生成入口只认可服务端确认状态。
    phase.value = 'outline_ready'
    ElMessage.error(error?.message || '大纲确认失败，请检查网络后重试；尚未进入课件生成。')
    return false
  } finally {
    outlineConfirming.value = false
  }
}

/** 打开教学设计方案修改模态框 */
async function modifyOutline() {
  outlineDialogVisible.value = true
  // 若尚未加载大纲数据，从后端拉取
  if (!planTask.value && !outlineData.value?.markdown) {
    planLoading.value = true
    try {
      const res = await getAiPlan(props.sessionId)
      planTask.value = isOk(res) ? res.data : null
      if (!planTask.value) ElMessage.error('教学方案加载失败')
    } catch {
      ElMessage.error('教学方案加载失败')
      outlineDialogVisible.value = false
    } finally {
      planLoading.value = false
    }
  }
}

/** 修改要求：必须填写说明 → 在同一 Agent 会话中重新生成大纲 */
async function submitModifyRequirement() {
  if (!planComment.value.trim()) {
    ElMessage.warning('请填写修改要求')
    return
  }
  planSubmitting.value = true
  outlineDialogVisible.value = false
  const requirement = planComment.value.trim()
  planComment.value = ''
  planSubmitting.value = false
  if (outlinePythonSessionId.value) {
    void recordAiFeedback({
      session_id: String(outlinePythonSessionId.value), action: 'regenerate', target_type: 'outline',
      instruction: requirement,
    }).catch(() => {})
  }
  await sendMessageToBackend(buildContextMessage(requirement))
}

/** 从模态框确认大纲，功能等同大纲卡片上的"确认大纲"按钮 */
async function confirmOutlineFromDialog() {
  const confirmed = await confirmOutline()
  if (confirmed) outlineDialogVisible.value = false
}

// ========== 资源生成 ==========

/** 点击"生成"按钮：确认模板后跳转到创作工作台编辑生成结果。 */
function startGenerateResource() {
  if (phase.value === 'generating_resource') return
  if (!selectedPptTemplateTheme.value) {
    ElMessage.warning('请先选择 PPT 生成模板')
    void openPptTemplateDialog()
    return
  }
  phase.value = 'generating_resource'
  // 模板选择发生在生成前；进入工作台后继续编辑 AI 生成的页面内容。
  emit('open-workspace', {
    pptTheme: selectedPptTemplateTheme.value,
    generationKey: String(Date.now()),
    resourceIds: [...activeResourceIds.value],
    workspaceContext: activeWorkspaceContext.value,
    onNavigationSettled: () => {
      if (phase.value === 'generating_resource') phase.value = 'resource_ready'
    },
  })
}

/** 普通对话切换到备课后，在同一条消息时间线里追加补充信息卡片。 */
async function enterPlanningInCurrentConversation() {
  outlineData.value = null
  activeLearningGraphMessageId = null
  planVersion.value = 1
  outlinePythonSessionId.value = String(props.sessionId || '')
  outlineGenerationStage.value = ''
  phase.value = 'info'
  isRequesterLoading.value = false
  continuationInjected.value = false
  lastClarification.value = ''
  planningClarificationVisible.value = false
  planningClarificationQuestion.value = null
  prepareInitialInfoForm(props.initialPrompt)
  addMessage('assistant', 'info_form', '补充信息')
  void loadPptTemplates()
  latestSessionPush.value = {
    id: props.sessionId,
    title: props.initialPrompt.trim().slice(0, 40) || '未命名对话',
    updated_at: new Date().toISOString(),
  }
  await scrollToBottom()
}

/** 只监听普通→备课的内部状态变化，避免切换时销毁并重建 ChatView。 */
watch(
  () => [props.mode, props.sessionId, props.resume],
  async ([mode, sessionId, resume], previous = []) => {
    const [previousMode, previousSessionId, previousResume] = previous
    if (resume || mode !== 'planning' || previousMode !== 'general' || !sessionId || previousResume) return
    await enterPlanningInCurrentConversation()
  },
  { flush: 'post' }
)

// ========== 生命周期 ==========
onMounted(async () => {
  void getTeacherPreferences().then((result) => {
    selectedTeachingStyle.value = String(result?.data?.teaching_style || '')
  }).catch(() => {})
  // 恢复历史会话：拉取会话详情与大纲重建消息与阶段，不透传首条消息
  if (props.resume) {
    await restoreSession()
    return
  }
  // 普通主对话：只显示消息和普通回复，不进入备课表单。
  if (isGeneralChat.value) {
    addMessage('user', 'text', props.initialPrompt)
    phase.value = 'general_chat'
    await requestGeneralChatReply()
    return
  }

  // 备课会话：先接上切换前的普通对话，再显示本次备课请求和内嵌补充信息卡片。
  outlinePythonSessionId.value = String(props.sessionId || '')
  renderContinuationHistory()
  addMessage('user', 'text', props.initialPrompt)
  prepareInitialInfoForm(props.initialPrompt)
  addMessage('assistant', 'info_form', '补充信息')
  void loadPptTemplates()
  // 将最新会话推送到 TeacherLayout 历史列表（页面未刷新时的暂时性显示）
  latestSessionPush.value = {
    id: props.sessionId,
    title: props.initialPrompt.trim().slice(0, 40) || '未命名对话',
    updated_at: new Date().toISOString(),
  }
})

/** 将后端 messages JSON 字符串解析为消息数组，非法或为空时返回空数组。 */
function parseStoredMessages(raw) {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/** 解析 plan_json（后端可能是 JSON 字符串，也可能已是对象），非法或为空时返回 null。 */
function parsePlanJson(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return parsed && typeof parsed === 'object' ? parsed : null
    } catch {
      return null
    }
  }
  return null
}

/** 只有真正包含页面结构的大纲才算已生成；新会话的初始化 plan_json 只有标题和空 slides。 */
function hasGeneratedOutline(value) {
  const outline = outlineCandidate(value)
  return Array.isArray(outline?.slides)
    && outline.slides.some((slide) => slide && typeof slide === 'object')
}

/**
 * 恢复已有会话：按后端 messages 的原始顺序还原用户与 AI 文本消息，再渲染当前阶段卡片。
 * 大纲和澄清问题分别由独立的结构化消息渲染，避免与 messages 中的摘要重复出现。
 */
async function restoreSession() {
  resumeLoading.value = true
  try {
    if (isGeneralChat.value) {
      const sessionRes = await getAiSession(props.sessionId)
      if (!isOk(sessionRes)) throw new Error('聊天历史加载失败')
      const session = sessionRes.data
      generalSessionId.value = session.id
      parseStoredMessages(session.messages)
        .filter((item) => item.type !== 'course_info_confirmation' && (item.role === 'user' || item.role === 'assistant') && String(item.content || '').trim())
        .forEach((item) => addMessage(item.role, 'text', item.content, {
          message_id: item.message_id,
          turn_id: item.turn_id,
          created_at: item.created_at,
          status: item.status,
        }))
      const restoredPlans = await listBatchPlans(String(generalSessionId.value))
      for (const plan of (restoredPlans.data || []).reverse()) {
        const message = addMessage('assistant', 'batch_plan', '批量备课计划')
        message.plan = plan
        activeBatchPlan.value = plan
        if (plan.status === 'confirmed') addMessage('assistant', 'batch_task', '', { batchId: plan.id })
      }
      phase.value = 'general_chat'
      return
    }
    const [sessionRes, planRes] = await Promise.all([
      getAiSession(props.sessionId),
      getAiPlan(props.sessionId).catch(() => null),
    ])
    const session = isOk(sessionRes) ? sessionRes.data : null
    const task = isOk(planRes) ? planRes.data : null
    const localOutlineDraft = readOutlineDraft(props.sessionId)
    outlinePythonSessionId.value = String(
      task?.python_session_id
      || localOutlineDraft?.python_session_id
      || props.sessionId
      || '',
    )

    // 有最新大纲：渲染大纲 + 操作栏，并按确认状态进入资源生成或待确认。
    // 新会话的 Java 初始化 plan_json 只有标题和空 slides，不能把它当作已生成的大纲，
    // 否则恢复历史会话时会跳过补充信息卡片，直接显示一个空标题。
    // Java mock 会话并不知道真实 Python 流生成的 plan_json，因此优先使用本地真实大纲快照。
    const backendPlanJson = parsePlanJson(task?.plan_json)
    const localPlanJson = parsePlanJson(localOutlineDraft?.plan_json ?? localOutlineDraft?.outline)
    infoForm.enableWeb = (backendPlanJson?.enable_web ?? localPlanJson?.enable_web ?? localOutlineDraft?.enable_web) === true
    let planJson = backendPlanJson?.status === 'awaiting_graph_confirmation'
      ? null
      : hasGeneratedOutline(backendPlanJson)
        ? backendPlanJson
        : (hasGeneratedOutline(localPlanJson) ? localPlanJson : null)
    let outlineWasRepaired = false

    // 历史会话可能保存过 Python 回退大纲；恢复时也要先做质量检查，避免绕过新生成流程。
    if (planJson && useRealOutlineApi && outlineNeedsRepair(planJson)) {
      try {
        const repairedResponse = await ensureOutlineQuality({
          ...planJson,
          outline: planJson,
          slides: planJson.slides,
        })
        planJson = normalizeRealOutlineResponse(repairedResponse)
        outlineWasRepaired = true
        saveOutlineDraft(props.sessionId, {
          ...(localOutlineDraft || {}),
          plan_json: planJson,
          client_outline_repair: true,
          python_session_id: outlinePythonSessionId.value || String(props.sessionId || ''),
          // 修复会产生新版本，必须重新确认后才能进入 PPT 生成。
          plan_confirm_status: 'pending',
        })
      } catch (error) {
        planJson = null
        ElMessage.warning(error?.message || '历史大纲内容重复，请重新生成')
      } finally {
        outlineGenerationStage.value = ''
      }
    }

    // 恢复完整文本消息。旧实现只保留 user，导致已有 AI 回复在重新打开会话时消失。
    // 当前阶段的结构化问题/大纲稍后单独渲染，因此跳过对应的摘要消息，避免重复。
    const storedMessages = parseStoredMessages(session?.messages)
      .filter((msg) => msg && (msg.role === 'user' || msg.role === 'assistant') && String(msg.content || '').trim())
    storedMessages.forEach((msg) => {
      const isCurrentStructuredReply = msg.role === 'assistant' && (
        (msg.type === 'question' && session?.last_question)
        || (planJson && msg.outline_id)
      )
      if (!isCurrentStructuredReply && msg.type !== 'graph_review' && msg.type !== 'course_info_confirmation') {
        addMessage(msg.role, 'text', String(msg.content).trim())
      }
    })

    if (planJson) {
      activeLearningGraphMessageId = null
      showLearningGraphs(planJson.learning_graphs || localOutlineDraft?.learning_graphs)
      outlineData.value = {
        markdown: planJsonToMarkdown(planJson),
        title: planJson.title || '教学设计方案',
        slideCount: Number(planJson.slide_count) || 0,
        planJson,
        outlineId: task?.python_outline_id || localOutlineDraft?.python_outline_id || planJson.outline_id,
      }
      planTask.value = {
        ...(localOutlineDraft || {}),
        ...(task || {}),
        plan_json: planJson,
        python_session_id: task?.python_session_id || localOutlineDraft?.python_session_id || outlinePythonSessionId.value,
        python_outline_id: task?.python_outline_id || localOutlineDraft?.python_outline_id || planJson.outline_id || null,
      }
      planVersion.value = Number(task?.plan_version) || Number(localOutlineDraft?.plan_version) || Number(planJson.version) || 1
      addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
      addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
      // 恢复时也只信任服务端确认状态，不能让旧的本地草稿绕过确认闸门。
      if (!outlineWasRepaired && task?.plan_confirm_status === 'confirmed') {
        await loadPptTemplates()
        fillGenResource(outlineData.value)
        phase.value = 'resource_ready'
      } else {
        phase.value = 'outline_ready'
      }
      await scrollToBottom()
      return
    }

    const pendingGraphs = backendPlanJson?.status === 'awaiting_graph_confirmation'
      ? backendPlanJson.learning_graphs
      : localOutlineDraft?.status === 'awaiting_graph_confirmation' ? localOutlineDraft.learning_graphs : null
    if (hasCompleteLearningGraphs(pendingGraphs)) {
      activeLearningGraphMessageId = null
      showLearningGraphs(pendingGraphs)
      phase.value = 'graph_review'
      await scrollToBottom()
      return
    }
    if (pendingGraphs) {
      addMessage('assistant', 'text', '上次生成的双图谱不完整，请重新生成；系统不会用空图谱继续生成大纲。')
    }

    // 尚未生成大纲：有待答澄清 → 澄清；否则回落到补充信息卡继续发起
    const restoredQuestion = session?.last_question || localOutlineDraft?.clarification
    if (restoredQuestion) {
      const question = normalizePlanningClarification(restoredQuestion)
      lastClarification.value = question?.text || ''
      phase.value = 'clarifying'
      addMessage('assistant', 'clarification', question?.text || String(restoredQuestion))
      openPlanningClarification(question)
    } else {
      phase.value = 'info'
      const latestUser = [...storedMessages].reverse().find((item) => item.role === 'user')
      const enableWeb = infoForm.enableWeb
      prepareInitialInfoForm(latestUser?.content || session?.title || '')
      infoForm.enableWeb = enableWeb
      addMessage('assistant', 'info_form', '补充信息')
    }
    await scrollToBottom()
  } catch { /* 请求层会统一处理失效会话 */ } finally {
    resumeLoading.value = false
  }
}
</script>

<template>
  <div class="chat-container">
    <!-- 消息列表 -->
    <div ref="messageListRef" class="chat-messages">
      <div v-if="resumeLoading" class="resume-loading">{{ CHAT_RESUME.loading }}</div>
      <TransitionGroup name="msg-enter">
        <article
          v-for="msg in messages"
          :key="msg.id"
          :class="['chat-message', `msg-${msg.role}`, `msg-type-${msg.type}`]"
        >
          <!-- 用户消息：右对齐气泡 -->
          <div v-if="msg.role === 'user'" class="user-bubble" :title="messageTraceLabel(msg)">
            {{ msg.content }}
          </div>

          <!-- AI 消息：根据 type 不同渲染 -->
          <template v-else-if="msg.role === 'assistant'">
            <!-- 补充信息卡片（表格样式表单） -->
            <div v-if="msg.type === 'info_form'" class="info-card">
              <div class="info-card-header">
                <strong>补充信息</strong>
              </div>

              <div v-if="!isMobile" class="info-table">
                <!-- 基础信息行 -->
                <div class="info-row">
                  <span class="info-label">基础信息</span>
                  <span class="info-desc">学段/学科/年级/教材</span>
                  <span class="info-value-cell info-basic-fields">
                    <el-select v-model="infoForm.stage" size="small" placeholder="学段" :disabled="phase !== 'info'" clearable @change="handleStageChange">
                      <el-option v-for="stage in STAGE_OPTIONS" :key="stage" :label="stage" :value="stage" />
                    </el-select>
                    <el-select v-model="infoForm.subject" size="small" placeholder="学科" :disabled="phase !== 'info'" filterable allow-create default-first-option clearable>
                      <el-option v-for="subject in SUBJECT_OPTIONS" :key="subject" :label="subject" :value="subject" />
                    </el-select>
                    <el-select v-model="infoForm.grade" size="small" :placeholder="infoForm.stage ? '年级' : '请先选择学段'" :disabled="phase !== 'info' || !infoForm.stage" filterable clearable>
                      <el-option v-for="grade in gradeOptions" :key="grade" :label="grade" :value="grade" />
                    </el-select>
                    <el-input v-model="infoForm.textbook" size="small" placeholder="教材版本（可选）" :disabled="phase !== 'info'" />
                  </span>
                </div>
                <!-- 班级学情行 -->
                <div class="info-row">
                  <span class="info-label">班级学情</span>
                  <span class="info-desc">学生整体基础水平</span>
                  <span class="info-value-cell">
                    <el-select
                      v-model="infoForm.classLevel"
                      size="small"
                      :disabled="phase !== 'info'"
                    >
                      <el-option
                        v-for="level in CLASS_LEVEL_OPTIONS"
                        :key="level"
                        :label="level"
                        :value="level"
                      />
                    </el-select>
                  </span>
                </div>
                <!-- 课程名称行 -->
                <div class="info-row">
                  <span class="info-label">课程名称</span>
                  <span class="info-desc">教学内容主题</span>
                  <span class="info-value-cell">
                    <el-input
                      v-model="infoForm.courseName"
                      size="small"
                      placeholder="请输入课程名称"
                      :disabled="phase !== 'info'"
                    />
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">PPT 页数范围</span>
                  <span class="info-desc">选填，AI 在范围内规划，含封面与总结</span>
                  <span class="info-value-cell">
                    <div class="page-range-fields">
                      <el-input-number v-model="infoForm.minPages" :min="1" :max="30" :precision="0" :controls="false" size="small" placeholder="最少页数" aria-label="PPT 最少页数" :disabled="phase !== 'info'" />
                      <span>至</span>
                      <el-input-number v-model="infoForm.maxPages" :min="1" :max="30" :precision="0" :controls="false" size="small" placeholder="最多页数" aria-label="PPT 最多页数" :disabled="phase !== 'info'" />
                      <span>页</span>
                    </div>
                    <span class="page-range-hint">支持 1–30 页，留空由 AI 自动规划</span>
                  </span>
                </div>
                <!-- 个性化需求行 -->
                <div class="info-row">
                  <span class="info-label">教学模型</span>
                  <span class="info-desc">控制大纲、课件与教案的教学阶段</span>
                  <span class="info-value-cell">
                    <el-select v-model="selectedTeachingModel" size="small" :disabled="phase !== 'info'">
                      <el-option label="BOPPPS 六环节" value="boppps" />
                      <el-option label="通用教学设计" value="general" />
                    </el-select>
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">个性化需求</span>
                  <span class="info-desc">教学侧重点与风格偏好</span>
                  <span class="info-value-cell">
                    <el-input
                      v-model="infoForm.requirements"
                      type="textarea"
                      :autosize="{ minRows: 2, maxRows: 4 }"
                      size="small"
                      :disabled="phase !== 'info'"
                    />
                  </span>
                </div>
              </div>

              <!-- 手机档：display:table 降级为卡片堆叠（<768px，响应式基线） -->
              <div v-else class="info-stack">
                <div class="info-stack-field">
                  <div class="info-stack-head">
                    <span class="info-stack-label">基础信息</span>
                    <span class="info-stack-desc">学段/学科/年级/教材</span>
                  </div>
                  <div class="info-basic-fields">
                    <el-select v-model="infoForm.stage" size="small" placeholder="学段" :disabled="phase !== 'info'" clearable @change="handleStageChange">
                      <el-option v-for="stage in STAGE_OPTIONS" :key="stage" :label="stage" :value="stage" />
                    </el-select>
                    <el-select v-model="infoForm.subject" size="small" placeholder="学科" :disabled="phase !== 'info'" filterable allow-create default-first-option clearable>
                      <el-option v-for="subject in SUBJECT_OPTIONS" :key="subject" :label="subject" :value="subject" />
                    </el-select>
                    <el-select v-model="infoForm.grade" size="small" :placeholder="infoForm.stage ? '年级' : '请先选择学段'" :disabled="phase !== 'info' || !infoForm.stage" filterable clearable>
                      <el-option v-for="grade in gradeOptions" :key="grade" :label="grade" :value="grade" />
                    </el-select>
                    <el-input v-model="infoForm.textbook" size="small" placeholder="教材版本（可选）" :disabled="phase !== 'info'" />
                  </div>
                </div>
                <div class="info-stack-field">
                  <div class="info-stack-head">
                    <span class="info-stack-label">班级学情</span>
                    <span class="info-stack-desc">学生整体基础水平</span>
                  </div>
                  <el-select v-model="infoForm.classLevel" size="small" :disabled="phase !== 'info'">
                    <el-option v-for="level in CLASS_LEVEL_OPTIONS" :key="level" :label="level" :value="level" />
                  </el-select>
                </div>
                <div class="info-stack-field">
                  <div class="info-stack-head">
                    <span class="info-stack-label">课程名称</span>
                    <span class="info-stack-desc">教学内容主题</span>
                  </div>
                  <el-input v-model="infoForm.courseName" size="small" placeholder="请输入课程名称" :disabled="phase !== 'info'" />
                </div>
                <div class="info-stack-field">
                  <div class="info-stack-head"><span class="info-stack-label">PPT 页数范围（选填）</span></div>
                  <div class="page-range-fields">
                    <el-input-number v-model="infoForm.minPages" :min="1" :max="30" :precision="0" :controls="false" size="small" placeholder="最少页数" aria-label="PPT 最少页数" :disabled="phase !== 'info'" />
                    <span>至</span>
                    <el-input-number v-model="infoForm.maxPages" :min="1" :max="30" :precision="0" :controls="false" size="small" placeholder="最多页数" aria-label="PPT 最多页数" :disabled="phase !== 'info'" />
                    <span>页</span>
                  </div>
                  <span class="page-range-hint">含封面与总结，支持 1–30 页；留空由 AI 自动规划</span>
                </div>
                <div class="info-stack-field">
                  <div class="info-stack-head"><span class="info-stack-label">教学模型</span></div>
                  <el-select v-model="selectedTeachingModel" size="small" :disabled="phase !== 'info'">
                    <el-option label="BOPPPS 六环节" value="boppps" />
                    <el-option label="通用教学设计" value="general" />
                  </el-select>
                </div>
                <div class="info-stack-field">
                  <div class="info-stack-head">
                    <span class="info-stack-label">个性化需求</span>
                    <span class="info-stack-desc">教学侧重点与风格偏好</span>
                  </div>
                  <el-input
                    v-model="infoForm.requirements"
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 4 }"
                    size="small"
                    :disabled="phase !== 'info'"
                  />
                </div>
              </div>

              <div class="info-web-search">
                <el-switch v-model="infoForm.enableWeb" aria-label="联网查找参考资料" :disabled="phase !== 'info'" />
                <span>联网查找参考资料</span>
                <small>使用课程名、学科和年级搜索公开网页。</small>
              </div>
              <!-- 确认按钮 -->
              <div class="info-actions">
                <el-button
                  type="primary"
                  :loading="isRequesterLoading"
                  :disabled="phase !== 'info'"
                  @click="confirmInfo"
                >
                  确认
                </el-button>
              </div>
            </div>

            <!-- 澄清问题消息（后端需要补充信息时展示） -->
            <div v-else-if="msg.type === 'clarification'" class="clarification-card">
              <div class="clarification-card-header">
                <strong>{{ CLARIFICATION_LABELS.title }}</strong>
              </div>
              <p class="clarification-question">{{ msg.content }}</p>
              <p class="clarification-hint">{{ CLARIFICATION_LABELS.hint }}</p>
            </div>

            <!-- 双图谱：默认知识图谱，按钮切换技能图谱。 -->
            <LearningGraphPanel v-else-if="msg.type === 'learning_graph'" :graphs="msg.data"
                                :confirmable="phase === 'graph_review' && hasCompleteLearningGraphs(msg.data) && msg.id === activeLearningGraphMessageId"
                                :confirming="isRequesterLoading" :graph-saver="saveLearningGraphs" :graph-ai-editor="aiEditLearningGraphs" @confirm="confirmLearningGraphs" />

            <BatchPlanCard v-else-if="msg.type === 'batch_plan'" :plan="msg.plan" :public-resource-enabled="publicResourceEnabled"
              @updated="value => { msg.plan = value; activeBatchPlan = value }"
              @confirmed="id => addMessage('assistant','batch_task','',{batchId:id})" />
            <BatchTaskPanel v-else-if="msg.type === 'batch_task'" :batch-id="msg.data.batchId" />
            <!-- AI Markdown 大纲消息：使用 markstream-vue 渲染，占满全宽 -->
            <div v-else-if="msg.type === 'markdown'" class="ai-bubble">
              <div class="ai-markdown-body">
                <MarkdownRender
                  mode="chat"
                  :content="msg.content"
                  :final="true"
                  :fade="false"
                  max-live-nodes="0"
                />
              </div>
            </div>

            <!-- 大纲操作栏（独立消息类型，在 Markdown 方案下方） -->
            <div v-else-if="msg.type === 'outline_actions'" class="outline-actions-bar">
              <el-button
                v-if="phase === 'outline_ready'"
                size="small"
                @click="modifyOutline"
              >
                {{ DESIGN_ACTION_BAR.modify }}
              </el-button>
              <el-button
                v-if="phase === 'outline_ready'"
                type="primary"
                size="small"
                :loading="outlineConfirming || isRequesterLoading"
                :disabled="outlineConfirming || isRequesterLoading"
                @click="confirmOutline"
              >
                {{ DESIGN_ACTION_BAR.confirm }}
              </el-button>
              <span v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="confirmed-badge">{{ DESIGN_ACTION_BAR.confirmed }}</span>
              <div v-if="retrievalMatches.length" class="retrieval-suggestions">
                <span>检索到的相关素材：</span>
                <el-button v-for="match in retrievalMatches" :key="match.resource_id" size="small" plain :disabled="activeResourceIds.includes(match.resource_id)" :title="match.snippet" @click="citeRetrievalMatch(match)">
                  {{ activeResourceIds.includes(match.resource_id) ? '已引用' : '引用' }} {{ match.title }}
                </el-button>
              </div>
              <div v-if="webReferences.length" class="retrieval-suggestions">
                <span>联网参考资料：</span>
                <el-link v-for="source in webReferences" :key="source.url" :href="source.url"
                  target="_blank" rel="noopener noreferrer" :title="source.snippet" type="primary">
                  {{ source.title || '查看来源' }}
                </el-link>
              </div>
              <small v-else-if="['failed', 'empty'].includes(webSearchStatus)">
                {{ webSearchStatus === 'failed' ? '联网搜索暂时不可用，本次大纲使用现有资料生成。' : '本次联网搜索未找到可用的参考资料。' }}
              </small>
            </div>

            <!-- 普通 AI 文本消息（同样使用 MarkdownRender 渲染以支持 MD 格式，占满全宽） -->
            <div v-else class="ai-bubble" :title="messageTraceLabel(msg)">
              <div class="ai-markdown-body">
                <MarkdownRender
                  mode="chat"
                  :content="msg.content"
                  :final="true"
                  :fade="false"
                  max-live-nodes="0"
                />
              </div>
            </div>
          </template>
        </article>
      </TransitionGroup>

      <!-- 加载指示器：正在请求大纲时显示三个依次闪烁的点 -->
      <div v-if="isRequesterLoading" class="streaming-indicator">
        <span class="dot-pulse"><i></i><i></i><i></i></span>
        <span v-if="outlineGenerationStage" class="streaming-stage">{{ outlineGenerationStage }}</span>
      </div>

      <!-- 资源生成卡片：大纲确认后先选生成模板，再进入工作台编辑结果 -->
      <div v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="resource-cards-area">
        <div class="resource-card">
          <el-icon class="resource-icon" :size="28">
            <Document />
          </el-icon>
          <div class="resource-info">
            <strong>{{ genResource.name }}</strong>
            <span>{{ genResource.description }}</span>
            <div class="resource-template-choice">
              <span>生成模板：{{ pptTemplateName || '加载中…' }}</span>
              <el-button
                class="resource-template-change"
                type="primary"
                plain
                round
                size="small"
                :icon="Brush"
                :disabled="phase === 'generating_resource'"
                @click="openPptTemplateDialog"
              >
                {{ pptTemplateName ? '更换模板' : '选择模板' }}
              </el-button>
            </div>
          </div>
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedPptTemplateTheme"
            :loading="phase === 'generating_resource'"
            @click="startGenerateResource"
          >
            生成 PPT
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部输入区（flex 布局固定在页面底部，不随消息滚动）
         澄清阶段启用输入框，供教师补充回复后端提出的澄清问题 -->
    <footer class="chat-composer">
      <MobileSection :title="`参考资料${activeResourceIds.length ? `（${activeResourceIds.length}）` : ''}`" class="chat-resource-section"><div class="composer-resource-row">
        <input ref="resourceFileInput" class="composer-resource-input" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.tsv,.txt,.md,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.ogg,.mp4,.avi,.mov,.mkv,.webm" @change="uploadChatResources" />
        <el-button text size="small" :icon="Paperclip" :loading="resourceUploading" :disabled="resourceUploading" @click="resourceFileInput?.click()">添加资料</el-button>
        <span v-if="activeResourceIds.length" class="composer-resource-count">已绑定 {{ activeResourceIds.length }} 份资料 · 用于问答与生成</span>
        <el-tag v-for="resource in attachedResources" :key="resource.id" size="small" closable class="composer-resource-tag" @close="removeChatResource(resource.id)">{{ resource.file_name }}</el-tag>
        <el-tag v-for="resource in tempContextResources" :key="`temp-${resource.resource_id}`" size="small" type="warning" effect="plain" class="composer-resource-tag" title="临时上传资料：仅本次生成引用，会话结束自动清理">{{ resource.file_name }}</el-tag>
      </div>
      </MobileSection><MobileSection v-if="isGeneralChat" title="对话设置" class="chat-preference-section"><div class="route-preference-row">
        <span>任务方式</span>
        <el-select v-model="selectedRoutePreference" size="small" aria-label="任务分流方式" style="width: 126px">
          <el-option label="自动判断" value="auto" />
          <el-option label="仅对话" value="chat" />
          <el-option label="直接备课" value="planning" /><el-option label="批量备课" value="batch" />
        </el-select>
      </div>
      </MobileSection><div class="composer-input-row" :class="{ 'is-editable': isGeneralChat || phase === 'info' || phase === 'clarifying' }">
        <el-input
          v-model="composerInput"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          resize="none"
          :placeholder="isGeneralChat ? CHAT_COMPOSER.generalPlaceholder : (phase === 'clarifying' ? CHAT_COMPOSER.clarificationPlaceholder : CHAT_COMPOSER.placeholder)"
          :readonly="isRequesterLoading || (!isGeneralChat && phase !== 'clarifying')"
          @keydown.enter="handleComposerKeydown"
        />
        <span class="composer-actions">
          <VoiceRecorderButton
            :disabled="isRequesterLoading || (!isGeneralChat && !['info', 'clarifying'].includes(phase))"
            :busy="voiceSubmitting"
            label="使用语音继续会话"
            @recorded="handleChatVoice"
            @error="handleChatVoiceError"
          />
          <el-button
            type="primary"
            circle
            :icon="Promotion"
            :disabled="isRequesterLoading || (!isGeneralChat && phase !== 'clarifying')"
            :loading="isRequesterLoading"
            :aria-label="CHAT_COMPOSER.send"
            @click="handleComposerSubmit"
          />
        </span>
      </div>
      <div class="public-resource-option">
        <el-switch v-model="publicResourceEnabled" size="small" active-text="启用公共资源库（RAG）" aria-label="启用公共资源库（RAG）" :disabled="isRequesterLoading" />
      </div>
      <p class="composer-hint">{{ CHAT_COMPOSER.hint }}{{ isTouchDevice ? ' · 点击右侧按钮发送' : ' · Enter 发送 · Shift + Enter 换行' }}</p>
    </footer>
  </div>

  <!-- 教学设计方案确认/修改模态框（由操作栏"修改"按钮触发） -->
  <el-dialog v-model="outlineDialogVisible" title="教学设计方案" width="min(700px, 92vw)" align-center destroy-on-close>
    <div v-loading="planLoading" class="plan-dialog-content">
      <p class="plan-status">请确认以下教学设计方案，或填写修改要求后重新生成。</p>

      <!-- Markdown 方案内容 -->
      <div v-if="outlineData?.markdown" class="plan-markdown-body">
        <MarkdownRender
          mode="chat"
          :content="outlineData.markdown"
          :final="true"
          :fade="false"
          max-live-nodes="0"
        />
      </div>
      <!-- 回退：方案数据暂不可用时显示提示 -->
      <p v-else class="plan-fallback">方案数据暂未就绪，请关闭后重试。</p>

      <el-input v-model="planComment" type="textarea" :rows="3" placeholder="请描述您希望调整的内容，例如：增加互动环节、调整难度、精简内容…" />
    </div>
    <template #footer>
      <el-button :loading="planSubmitting" :disabled="!planComment.trim()" @click="submitModifyRequirement">修改要求</el-button>
      <el-button type="primary" :loading="outlineConfirming" :disabled="outlineConfirming" @click="confirmOutlineFromDialog">确认大纲</el-button>
    </template>
  </el-dialog>

  <PptTemplatePicker
    v-model="pptTemplateDialogVisible"
    :selected-theme="pptTemplateDraftTheme"
    :templates="pptTemplates"
    :loading="pptTemplateLoading"
      :error="pptTemplateLoadError"
      @update:selected-theme="pptTemplateDraftTheme = $event"
      @retry="loadPptTemplates(true)"
      @confirm="confirmPptTemplate"
    />

  <!-- Agent 意图澄清：仅承载后端返回的复杂澄清问题；首次备课信息直接填写上方卡片。 -->
  <IntentClarificationDialog
    v-model="planningClarificationVisible"
    :question="planningClarificationQuestion"
    :loading="planningClarificationSubmitting || isRequesterLoading"
    @submit="submitPlanningClarification"
  />
</template>

<style scoped>
/* ===== 容器 ===== */
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 68px); /* 减去 topbar 高度 */
  max-width: 880px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ===== 顶部导航栏 ===== */
.chat-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--zh-line-parting);
}

/* ===== 消息滚动区 ===== */
.info-web-search { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 8px 0; }
.info-web-search small { color: var(--el-text-color-secondary); }

.route-preference-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 8px;
  color: var(--zh-text-secondary);
  font-size: 12px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
  scroll-behavior: smooth;
}
/* 自定义滚动条（遵循设计规范：宽 4px，色 --zh-line-border） */
.chat-messages::-webkit-scrollbar {
  width: 4px;
}
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}
.chat-messages::-webkit-scrollbar-thumb {
  border-radius: var(--zh-radius4);
  background: var(--zh-line-border);
}
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--zh-line-heavier);
}

/* ===== 用户气泡 ===== */
.user-bubble {
  max-width: 75%;
  margin: 20px 0 20px auto;
  padding: 12px 18px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius8) var(--zh-radius18);
  background: var(--zh-background-user-query);
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== AI 气泡（全宽，无头像） ===== */
.ai-bubble {
  width: 100%;
  margin: 20px 0;
}
/* Markdown 渲染内容容器：全宽展示 */
.ai-markdown-body {
  width: 100%;
  padding: 12px 18px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius18) var(--zh-radius8);
  background: var(--zh-background-answer-card);
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
}

/* ===== 补充信息卡片 ===== */
.info-card {
  width: 100%;
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--zh-line-heavier);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
  box-shadow: var(--zh-shadow1);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.info-card:hover {
  box-shadow: var(--zh-shadow2);
  transform: translateY(-1px);
}
.info-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.info-icon {
  font-size: var(--zh-font-size18);
}
.info-card-header strong {
  font-size: var(--zh-font-size15);
  color: var(--zh-text-primary);
}

/* CSS Table 布局 */
.info-table {
  display: table;
  width: 100%;
  border-collapse: collapse;
}
.info-row {
  display: table-row;
}
.info-label,
.info-desc,
.info-value-cell {
  display: table-cell;
  padding: 10px 12px;
  vertical-align: middle;
  border-bottom: 1px solid var(--zh-line-parting);
}
.info-row:last-child .info-label,
.info-row:last-child .info-desc,
.info-row:last-child .info-value-cell {
  border-bottom: none;
}
.info-label {
  font-weight: 600;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size13);
  white-space: nowrap;
  width: 1%;
}
.info-desc {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
  width: 1%;
  white-space: nowrap;
}
.info-value-cell {
  width: auto;
}
.info-basic-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.page-range-fields {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #344563;
}
.page-range-fields :deep(.el-input-number) {
  width: 120px;
  min-width: 0;
  flex: 0 1 120px;
}
.page-range-hint {
  display: block;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}
.info-basic-fields :deep(.el-select) {
  width: 128px;
}
.info-basic-fields :deep(.el-input) {
  flex: 1 1 150px;
  width: auto;
  min-width: 150px;
}
.info-readonly {
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
}
.info-value-cell:not(.info-basic-fields) :deep(.el-select) {
  width: 140px;
}
.info-value-cell:not(.info-basic-fields) :deep(.el-input) {
  width: 100%;
}
.info-value-cell :deep(.el-textarea__inner) {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
}

/* 补充信息确认按钮 */
.info-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--zh-line-parting);
}

/* 手机档补充信息卡片堆叠（isMobile 渲染，替代 display:table 隐藏列降级） */
.info-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.info-stack-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--zh-line-parting);
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}
.info-stack-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.info-stack-label {
  font-weight: 600;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size13);
}
.info-stack-desc {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
}
.info-stack-field :deep(.el-select),
.info-stack-field :deep(.el-input) {
  width: 100%;
}
.info-stack-field .info-basic-fields :deep(.el-select) {
  flex: 1 1 40%;
  width: auto;
}

/* ===== 澄清问题卡片（后端需要补充信息时展示） ===== */
.clarification-card {
  width: 100%;
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--zh-line-heavier);
  border-left: 3px solid var(--zh-text-theme);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
}
.clarification-card-header strong {
  font-size: var(--zh-font-size15);
  color: var(--zh-text-primary);
}
.clarification-question {
  margin: 12px 0 4px;
  font-size: var(--zh-font-size14);
  line-height: 1.65;
  color: var(--zh-text-primary);
}
.clarification-hint {
  margin: 0;
  font-size: var(--zh-font-size12);
  color: var(--zh-text-caption);
}

/* ===== 大纲操作栏（Markdown 方案下方独立消息条） ===== */
.outline-actions-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0;
  margin: 4px 0 20px 0;
}
.retrieval-suggestions { flex-basis: 100%; display: flex; align-items: center; flex-wrap: wrap; gap: 6px; color: #64748b; font-size: 12px; }

/* ===== 流式加载指示器 ===== */
.streaming-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
}
.dot-pulse {
  display: flex;
  gap: 4px;
}
.dot-pulse i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--zh-text-theme);
  animation: dotPulse 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
.dot-pulse i:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse i:nth-child(3) { animation-delay: 0.4s; }
.streaming-stage {
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 资源卡片 ===== */
.resource-cards-area {
  padding: 0 0 16px;
  display: grid;
  gap: 8px;
}
.resource-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: var(--zh-background-light);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.resource-card:hover {
  box-shadow: var(--zh-shadow1);
  transform: translateY(-1px);
}
.resource-icon {
  flex-shrink: 0;
  color: var(--zh-text-theme);
}
.resource-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.resource-info strong {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.resource-info span {
  font-size: var(--zh-font-size11);
  color: var(--zh-text-caption);
}
.resource-template-choice {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-top: 2px;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size11);
}
.resource-template-change {
  height: 24px;
  padding: 0 9px;
  border-radius: var(--zh-radius20);
  font-size: var(--zh-font-size11);
  font-weight: 600;
}

/* ===== 底部输入区（flex 布局固定在页面底部，不随消息滚动） ===== */
.chat-composer {
  flex-shrink: 0;
  padding: 12px 0 16px;
  border-top: 1px solid var(--zh-line-parting);
  background: var(--zh-background-primary);
}
.composer-resource-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding-bottom: 7px; }
.composer-resource-input { display: none; }
.composer-resource-count { color: var(--zh-text-caption); font-size: var(--zh-font-size11); }
/* 资料/临时上传标签：长文件名截断，避免撑破 composer-resource-row */
.composer-resource-tag { max-width: 180px; }
.composer-resource-tag :deep(.el-tag__content) { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }
.composer-input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 9px 10px 10px;
  border: 1px solid var(--zh-line-parting);
  border-radius: var(--zh-radius16);
  background: var(--zh-background-light-gray);
  box-shadow: none;
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}
/* 澄清阶段启用输入框 */
.composer-input-row.is-editable {
  opacity: 1;
  cursor: text;
  pointer-events: auto;
  border-color: var(--zh-line-heavier);
  background: var(--zh-background-light);
}
.composer-actions { display: inline-flex; align-items: center; gap: 3px; flex: none; }
.composer-input-row :deep(.el-textarea__inner) {
  min-height: 52px !important;
  padding: 6px 8px;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.6;
}
.public-resource-option { margin: 4px 0; }

.composer-hint {
  margin: 8px 0 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
  text-align: center;
}

/* ===== 无障碍：键盘焦点可见指示器 ===== */
.info-card:focus-visible,
.resource-card:focus-visible {
  outline: 2px solid var(--zh-line-theme);
  outline-offset: 2px;
}

/* ===== 历史会话恢复加载提示 ===== */
.resume-loading {
  padding: 48px 0;
  text-align: center;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
}

/* ===== 动画 ===== */
.msg-enter-enter-active {
  transition: opacity 300ms cubic-bezier(0, 0, 0.2, 1), transform 300ms cubic-bezier(0, 0, 0.2, 1);
}
.msg-enter-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

@keyframes dotPulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* ===== 响应式（断点收敛：手机档 max-width 767.98px，design.md §9.3） ===== */
@media (max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse) {
  .chat-container {
    padding: 0 12px;
    height: 100%;
    min-height: 0;
  }
  .chat-messages {
    min-height: 0;
    overscroll-behavior-y: contain;
  }
  .chat-composer {
    padding-bottom: 16px;
  }
  .ai-option-select { width: 78px; }
  .ai-option-select + .ai-option-select { width: 92px; }
  .user-bubble {
    max-width: 92%;
  }
  .outline-actions-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .outline-actions-bar .el-button {
    width: 100%;
    margin-left: 0;
  }
  .resource-card {
    align-items: flex-start;
  }
  .resource-card > .el-button {
    flex-shrink: 0;
  }
}

/* ===== 方案确认模态框内容 ===== */
.plan-dialog-content .plan-status {
  margin: 0 0 14px;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
}
.plan-fallback {
  margin: 0 0 16px;
  padding: 24px;
  text-align: center;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
  background: var(--zh-background-light);
  border-radius: var(--zh-radius8);
}
/* 模态框内 Markdown 方案内容：限高滚动 */
.plan-markdown-body {
  max-height: 360px;
  overflow: auto;
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--zh-line-parting);
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}
</style>
