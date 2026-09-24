<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, ArrowDown, ArrowUp, Plus, Promotion } from '@element-plus/icons-vue'
import MarkdownRender from 'markstream-vue'
import { addProjectPermission, archiveProject, batchSaveProjectPages, copyProject, createCommunitySubmission, createProject, createProjectPage, deleteProject, deleteProjectPage, downloadResource, exportLessonPlanDocx, exportPresentationPptx, findUserByEmail, findUserByUsername, generateInteractiveModule, generateLessonPlan, generatePresentationStream, getAiPlan, getProject, getProjectPage, getProjectVersionDiff, listProjectPages, listProjectVersions, listProjects, listResources, modifyPresentation, modifyPresentationSlide, patchProject, recognizeIntent, recordAiFeedback, restoreProject, restoreProjectVersion, reviseProjectWithAi, saveCommunitySubmissionVersion, saveProjectPage, saveProjectVersion, sendAiSessionAudioMessage, sendAiSessionMessage, streamGeneralChat, submitCommunitySubmission, transcribeAudio, uploadResource, validatePresentationHtml, validateProjectComponent } from '../apis/teacher'
import { secureHtmlForSandbox } from '../utils/htmlSecurity'
import { bindSubjectInteractions } from '../utils/subjectInteraction'
import { canLandPptDirectEdit, placeLandPptCaret, serializeLandPptEditableDocument, shouldCommitLandPptInlineEdit } from '../utils/landpptQuickEdit'
import IntentClarificationDialog from './IntentClarificationDialog.vue'
import CreationWorkspaceToolbar from './CreationWorkspaceToolbar.vue'
import WorkspaceProjectActions from './WorkspaceProjectActions.vue'
import WorkspacePropertiesPanel from './WorkspacePropertiesPanel.vue'
import LessonPlanEditor from './LessonPlanEditor.vue'
import LessonPlanPreview from './LessonPlanPreview.vue'
import VoiceRecorderButton from './VoiceRecorderButton.vue'
import SubjectToolRuntime from './SubjectToolRuntime.vue'
import { createSubjectToolData, normalizeSubjectToolData, normalizeSubjectToolType, subjectToolDefaultRenderHint, subjectToolMarkup, subjectToolPayload, subjectToolRuntimeCss } from '../utils/subjectTool'
import { INTERACTIVE_MODULE_TYPES, interactiveModuleTypeInfo, normalizeInteractiveModuleType } from '../utils/interactiveModule'
import { useUserStore } from '../storage/user.js'
import { readOutlineDraft, readPresentationDraft, savePresentationDraft } from '../utils/presentationDraft.js'
import { createPresentationFixture } from '../mock/data/presentationFixture.js'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const prompt = ref('')
const selectedSlide = ref(0)
const draggingSlideIndex = ref(null)
const slideDropIndex = ref(null)
const activeTool = ref('')
const selectedElementId = ref(null)
const draggingElementId = ref(null)
const canvasZoom = ref(86)
const canvasZoomInput = ref('86')
const CANVAS_ZOOM_MIN = 50
const CANVAS_ZOOM_MAX = 200
const CANVAS_ZOOM_STEP = 10
const CANVAS_WHEEL_ZOOM_STEP = 8
const canvasAreaRef = ref(null)
const canvasPanning = ref(false)
let canvasPanGesture = null
let canvasCenterFrame = null
let canvasViewportObserver = null
const previewVisible = ref(false)
const previewSlideIndex = ref(0)
const previewDeckRef = ref(null)
const previewStageRef = ref(null)
const presentationMode = ref(false)
const presentationLaserEnabled = ref(false)
const presentationNotesVisible = ref(false)
const presentationLaserPosition = reactive({ x: 50, y: 50, visible: false })
const onlinePreviewLoading = ref(false)
const interactiveDialogVisible = ref(false)
const interactivePreviewVisible = ref(false)
const interactiveGenerating = ref(false)
const interactiveModule = ref(null)
const interactiveRegenerateTarget = ref(null)
const interactivePreviewSource = ref('generated')
const interactivePreviewViewportRef = ref(null)
const interactivePreviewScale = ref(1)
let interactivePreviewResizeObserver = null
const interactiveForm = reactive({
  title: '',
  topic: '',
  module_type: 'animation',
  subject: '',
  grade: '',
  knowledge_points: '',
  requirements: '',
  theme: '',
  embed_mode: 'standalone',
  language: 'zh-CN',
})
const interactiveModuleTypes = INTERACTIVE_MODULE_TYPES
const clarificationDialogVisible = ref(false)
const clarificationSubmitting = ref(false)
const clarificationQuestion = ref(null)
const clarificationOrigin = ref('session')
const runStatus = ref('idle')
const runProgress = ref(0)
const runStage = ref('')
const generationError = ref('')
const runTimeline = ref([])
const runToolCalls = ref([])
const runRetrievalSources = ref([])
const runReflection = ref(null)
const runRecoveryNode = ref('')
const runFailureReason = ref('')
// 当前后端 Run 端点只会写入静态状态，无法承载真实生成过程。
// 因此工作台只记录本次浏览器实际发起并完成的调用，不再创建会永久卡住的服务端任务。
const activeRunId = ref('')
const clientRunStartedAt = ref(0)
const revisionSubmitting = ref(false)
const discussionSubmitting = ref(false)
const workspaceVoiceSubmitting = ref(false)
const revisionStage = ref('')
const assistantConversationRef = ref(null)
const presentationId = ref('')
const presentationMetadata = ref(null)
const htmlFrameObservers = new Set()
const htmlCanvasSource = ref('')
const htmlCanvasSourceSlide = ref(null)
// `srcdoc` 只应在切页、撤销/重做或外部更新页面时刷新。
// 画布内的拖拽、插入等操作已经直接改到了 iframe 文档，若再更新 srcdoc，
// 浏览器会重新装载整个 iframe，表现为画面闪白一下。
const htmlCanvasFrameRevision = ref(0)
// 普通结构化页面也使用 iframe 作为编辑视图，但仍以 slide.elements 作为持久化数据。
// 这里的 HTML 只是一份前端编辑投影，避免为了复用编辑器而强制迁移整页数据。
const structuredHtmlCanvasSource = ref('')
const structuredHtmlCanvasSourceSlide = ref(null)
const structuredHtmlLiveDocuments = new WeakMap()
const htmlElements = ref([])
const htmlSelectedElementId = ref(null)
const htmlSelectedElement = ref(null)
const htmlSelectionRestoreKey = ref('')
let pendingHtmlPanelSelection = null
let pendingHtmlToolbarTool = null
const pageBackgroundImage = (slide) => String(slide?.backgroundImage || slide?.background_image || slide?.background?.src || '').trim()
const pageBackgroundColor = (slide) => String(slide?.backgroundColor || slide?.background_color || slide?.background?.color || '').trim()
const safeCssUrl = (value) => String(value || '').replace(/["'()\\]/g, '')
const pageCanvasStyle = (slide, includeZoom = false) => {
  const style = {
    '--accent': (themes.find((item) => item.id === slide?.theme) || themes[0]).color,
    backgroundImage: 'none',
  }
  const image = pageBackgroundImage(slide)
  const color = pageBackgroundColor(slide)
  if (includeZoom) style['--canvas-zoom'] = canvasZoom.value / 100
  if (/^(#[0-9a-f]{3,8}|rgba?\([^)]{1,80}\)|hsla?\([^)]{1,100}\)|transparent|white|black)$/i.test(color)) style.backgroundColor = color
  if (image) {
    style.backgroundImage = `url("${safeCssUrl(image)}")`
    style.backgroundSize = 'cover'
    style.backgroundPosition = 'center'
  }
  return style
}
// 清除旧项目和旧模板遗留在 slide 根节点上的右上角装饰伪元素。
// 该元素不是 PPT 内容，不能被选中或编辑，因此在加载页面时直接从 HTML 中移除。
const stripSlideDecorativeCircle = (source) => String(source || '')
  .replace(/\.slide(?:\.dark)?\s*:{1,2}before\s*\{[^{}]*\}/gi, '')
const withHtmlPageBackground = (source, slide) => {
  const html = stripSlideDecorativeCircle(source)
  const image = pageBackgroundImage(slide)
  const color = pageBackgroundColor(slide)
  if (!image && !color) return html
  const background = [
    color ? `background-color:${color} !important;` : '',
    image ? `background-image:url("${safeCssUrl(image)}") !important;background-size:cover !important;background-position:center !important;` : '',
  ].join('')
  // HTML 幻灯片通常由内部 `.slide` 根节点铺满画布，单独设置 html/body
  // 会被该节点自己的 background 覆盖，因此页面背景需要同时作用于实际画布根节点。
  const style = `<style data-a12-page-background>html,body,.slide,.slide.dark{${background}}html,body{background-repeat:no-repeat !important;}</style>`
  const marker = /<style data-a12-page-background>[\s\S]*?<\/style>/i
  if (marker.test(html)) return html.replace(marker, style)
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, `${style}</head>`)
  return `${style}${html}`
}
const normalizeH5RuntimeConfig = (value = {}) => {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const text = (key, limit) => String(source[key] ?? '').trim().slice(0, limit)
  return {
    type: ['quiz', 'poll', 'simulation', 'game'].includes(String(source.type || '')) ? String(source.type) : 'quiz',
    question: text('question', 500),
    answer: text('answer', 300),
    positive_feedback: text('positive_feedback', 180),
    negative_feedback: text('negative_feedback', 180),
    score: Math.max(0, Math.min(100, Number(source.score) || 0)),
    max_attempts: Math.max(1, Math.min(10, Math.round(Number(source.max_attempts) || 1))),
  }
}
const h5RuntimeConfigAttribute = (value = {}) => {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  return Object.keys(source).length ? JSON.stringify(normalizeH5RuntimeConfig(source)) : '{}'
}
// API-144 的 H5 以 1280x720 固定画布生成。缩放由宿主组件框统一完成，
// 不再改写 H5 内部 body；内部页面参与缩放会与拖拽帧竞争，造成闪烁和位移。
const H5_DESIGN_WIDTH = 1280
const H5_DESIGN_HEIGHT = 720
const withH5RuntimeConfig = (source, config = {}) => {
  const html = String(source || '')
  if (!html) return ''
  const configSource = config && typeof config === 'object' && !Array.isArray(config) ? config : {}
  const safeConfig = h5RuntimeConfigAttribute(configSource)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
  const configRuntime = Object.keys(configSource).length
    ? `<script id="a12-h5-runtime-config">window.A12_H5_CONFIG=Object.freeze(${safeConfig});window.dispatchEvent(new CustomEvent('a12:h5-config',{detail:window.A12_H5_CONFIG}));<${'/script'}>`
    : ''
  const withoutPreviousRuntime = html
    .replace(/<script\b[^>]*\bid\s*=\s*(["'])a12-h5-runtime-config\1[^>]*>[\s\S]*?<\/script\s*>/gi, '')
    .replace(/<style\b[^>]*\bid\s*=\s*(["'])a12-h5-responsive-style\1[^>]*>[\s\S]*?<\/style\s*>/gi, '')
    .replace(/<script\b[^>]*\bid\s*=\s*(["'])a12-h5-responsive-scale\1[^>]*>[\s\S]*?<\/script\s*>/gi, '')
  const runtime = configRuntime
  if (/<\/head>/i.test(withoutPreviousRuntime)) return withoutPreviousRuntime.replace(/<\/head>/i, `${runtime}</head>`)
  if (/<html\b[^>]*>/i.test(withoutPreviousRuntime)) return withoutPreviousRuntime.replace(/<html\b[^>]*>/i, (match) => `${match}<head>${runtime}</head>`)
  return `<!doctype html><html lang="zh-CN"><head>${runtime}</head><body>${withoutPreviousRuntime}</body></html>`
}
const versionDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const versionLoading = ref(false)
const versions = ref([])
const versionDiff = ref(null)
const versionPage = ref(1)
const versionTotal = ref(0)
const versionError = ref('')
const versionDescription = ref('')
const versionActionLoading = ref(false)
const versionDiffLoading = ref(false)
const compareVersionId = ref('')
const manualSaveLoading = ref(false)
const permissionSearchType = ref('username')
const permissionSearchQuery = ref('')
const permissionSearchResult = ref(null)
const permissionSearchLoading = ref(false)
const permissionAddLoading = ref(false)
const permissionRemoveLoading = ref('')
const projectManagerVisible = ref(false)
const projectListLoading = ref(false)
const projectActionLoading = ref(false)
const workspaceProjects = ref([])
const projectFilters = reactive({ keyword: '', project_type: '', status: '', page: 1, size: 10 })
const projectTotal = ref(0)
const projectListError = ref('')
let projectListRequest = 0
const projectTypeLabels = { ppt: 'PPT 课件', word: '教学案', h5: '互动页面', mixed: '综合项目' }
const projectStatusLabels = { draft: '草稿', editing: '编辑中', confirmed: '已确认', exported: '已导出', archived: '已归档' }
const formatWorkspaceDate = (value) => value ? String(value).replace('T', ' ').slice(0, 16) : '暂无时间记录'
const workspaceResources = ref([])
const workspaceResourcesLoading = ref(false)
const workspaceResourceBindingOverride = ref(null)
const contextManagerVisible = ref(false)
const contextManagerIds = ref([])
const contextManagerSaving = ref(false)
const lessonPlanEditorRef = ref(null)
const lessonPlanPreviewVisible = ref(false)
const lessonPlanPreviewDraft = ref(null)
const lessonPlanDraft = ref(null)
const projectNameDraft = ref('')
const communityPublishVisible = ref(false)
const communityPublishLoading = ref(false)
const communityPublishForm = reactive({
  content_type: 'lesson_case',
  title: '',
  description: '',
  subject: '',
  grade: '',
  lesson_type: '',
  license: 'CC BY-NC 4.0',
  source_declaration: '本人原创或已获得授权',
  notes: '',
})
const quickExportLoading = ref('')
const autosaveState = ref('本地草稿 · 尚未保存为项目')
const testCaseBootstrapping = ref(false)
const hydratingProject = ref(false)
const savingPage = ref(false)
const qualityPanelVisible = ref(false)
const qualityReport = ref(null)
const qualityReportSource = ref('')
const revisionPreviewVisible = ref(false)
const pendingDeckRevision = ref(null)
const revisionUndoSnapshot = ref(null)
const workspaceClientVersion = `workspace-${Date.now()}`
const loadedPageDetailIds = new Set()
const componentValidationCache = new Map()
const pendingComponentSync = new WeakMap()
const subjectValidationPending = ref(false)
let autosaveTimer = null
let pageSavePromise = null
let orderSavePromise = null
let localChangeVersion = 0
let localStructureVersion = 0
let savedChangeVersion = 0
let savedStructureVersion = 0
let autosaveQueued = false
let workspaceMessageInstance = null
const showWorkspaceMessage = (type, message, options = {}) => {
  workspaceMessageInstance?.close()
  workspaceMessageInstance = ElMessage({
    type,
    message,
    offset: 76,
    duration: type === 'error' ? 3200 : 1800,
    showClose: type === 'error',
    grouping: true,
    customClass: 'workspace-message',
    ...options,
  })
  return workspaceMessageInstance
}
const WorkspaceMessage = {
  success: (message, options) => showWorkspaceMessage('success', message, options),
  warning: (message, options) => showWorkspaceMessage('warning', message, options),
  info: (message, options) => showWorkspaceMessage('info', message, options),
  error: (message, options) => showWorkspaceMessage('error', message, options),
}
const themes = [
  { id: 'blue', name: '经典蓝', color: '#2563eb' },
  { id: 'navy', name: '沉静蓝', color: '#173d78' },
  { id: 'green', name: '自然绿', color: '#1f993f' },
  { id: 'orange', name: '活力橙', color: '#ff6b3f' },
]
const layouts = ['重点陈述', '图文并置', '双栏探究']
const createMockImageSrc = (label = '课堂观察') => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#dbeafe"/><stop offset="1" stop-color="#eff6ff"/></linearGradient></defs><rect width="640" height="360" rx="28" fill="url(#g)"/><circle cx="150" cy="148" r="62" fill="#93c5fd"/><path d="M85 275c42-86 91-98 142-40 33-31 75-35 120 40" fill="none" stroke="#2563eb" stroke-width="18" stroke-linecap="round"/><rect x="350" y="88" width="188" height="24" rx="12" fill="#93c5fd"/><rect x="350" y="132" width="144" height="18" rx="9" fill="#bfdbfe"/><text x="350" y="222" fill="#173d78" font-family="Arial, sans-serif" font-size="26" font-weight="700">${label}</text><text x="350" y="258" fill="#607491" font-family="Arial, sans-serif" font-size="18">MOCK IMAGE</text></svg>`
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}
const elementPresets = [
  { id: 'title', type: 'text', name: '页面标题', target: 'title', content: '', position: { x: 8, y: 13, width: 62, height: 15, rotation: 0, zIndex: 4 }, style: { color: '#102d54', fontSize: 40, fontWeight: 700, opacity: 100, textAlign: 'left', lineHeight: 1.2 } },
  { id: 'description', type: 'text', name: '引导文案', target: 'description', content: '', position: { x: 8, y: 30, width: 57, height: 14, rotation: 0, zIndex: 4 }, style: { color: '#607491', fontSize: 15, fontWeight: 400, opacity: 100, textAlign: 'left', lineHeight: 1.65 } },
  { id: 'formula-diagram', type: 'shape', name: '公式示意图', target: null, shapeKind: 'formula-diagram', content: '', position: { x: 8, y: 48, width: 14, height: 25, rotation: 0, zIndex: 3 }, style: { fillColor: '#2563eb', borderColor: '#2563eb', borderWidth: 5, borderRadius: 0, opacity: 100 } },
  { id: 'formula-text', type: 'formula', name: '公式文字', target: null, content: 'a² + b² = c²', position: { x: 25, y: 50, width: 31, height: 12, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', fontSize: 32, fontWeight: 700, opacity: 100, textAlign: 'center', lineHeight: 1.2 } },
  { id: 'formula-caption', type: 'text', name: '公式说明', target: null, content: '公式元素，可在右侧修改内容', position: { x: 25, y: 64, width: 31, height: 7, rotation: 0, zIndex: 3 }, style: { color: '#7c8da4', fontSize: 10, fontWeight: 600, opacity: 100, textAlign: 'center', lineHeight: 1.4 } },
  { id: 'shape', type: 'shape', name: '几何形状', target: 'shape', shapeKind: 'circle', content: '', position: { x: 57, y: 54, width: 7, height: 11, rotation: 0, zIndex: 3 }, style: { fillColor: '#dbeafe', borderColor: '#2563eb', borderWidth: 2, borderRadius: 50, opacity: 100 } },
  { id: 'image', type: 'image', name: '课堂图片', target: 'image', content: '校园测量示意图', src: createMockImageSrc(), position: { x: 66, y: 46, width: 25, height: 29, rotation: 0, zIndex: 3 }, style: { tintColor: '#2563eb', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, opacity: 100, objectFit: 'cover' } },
  { id: 'chart', type: 'chart', name: '测量图表', target: 'chart', content: '三组测量数据', data: [{ label: 'A组', value: 68 }, { label: 'B组', value: 82 }, { label: 'C组', value: 56 }, { label: 'D组', value: 91 }], position: { x: 64, y: 13, width: 27, height: 27, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', backgroundColor: '#eff6ff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, opacity: 100 } },
  { id: 'footer', type: 'text', name: '页脚说明', target: 'footer', content: '', position: { x: 0, y: 86, width: 100, height: 14, rotation: 0, zIndex: 5 }, style: { color: '#ffffff', fontSize: 10, fontWeight: 400, opacity: 100, textAlign: 'left', lineHeight: 1.5 } },
]
const extendedElementPresets = [
  { id: 'audio', type: 'audio', name: '音频讲解', content: '教师讲解示例音频', url: '', src: '', autoplay: false, controls: true, position: { x: 8, y: 48, width: 30, height: 14, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', backgroundColor: '#eff6ff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'video', type: 'video', name: '视频演示', content: '课堂实验演示视频', url: '', src: '', autoplay: false, controls: true, position: { x: 40, y: 48, width: 30, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#173d78', backgroundColor: '#eef2ff', borderColor: '#c7d2fe', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'table', type: 'table', name: '数据表格', content: '小组测量记录', data: [['小组', '边 a', '边 b'], ['A组', '3', '4'], ['B组', '5', '12']], position: { x: 8, y: 64, width: 44, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', backgroundColor: '#f8fbff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 10, opacity: 100 } },
  { id: 'h5', type: 'h5', name: 'H5 组件', content: '互动问答 H5', html: '', moduleId: '', embedMode: 'standalone', position: { x: 54, y: 64, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#ff6b3f', backgroundColor: '#fff7ed', borderColor: '#fed7aa', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'subject', type: 'subject', name: '学科工具', content: '直角三角形测量工具', subjectType: 'geometry', data: createSubjectToolData('geometry'), subjectRender: subjectToolDefaultRenderHint('geometry'), position: { x: 54, y: 43, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#1f993f', backgroundColor: '#f0fdf4', borderColor: '#bbf7d0', borderWidth: 1, borderRadius: 12, opacity: 100 } },
]
const allElementPresets = [...elementPresets, ...extendedElementPresets]
let elementSequence = 1
// 工作台内元素剪贴板：仅保存当前会话中的可编辑元素，不写入系统剪贴板。
// 这样可避免将课件的内部 HTML、资源地址暴露到其他应用，同时仍支持 Ctrl/Cmd+C、V。
let workspaceElementClipboard = null
const cloneElementListData = (data) => Array.isArray(data)
  ? data.map((item) => Array.isArray(item) ? [...item] : (item && typeof item === 'object' ? { ...item } : item))
  : data
const cloneElementData = (element) => ({
  ...element,
  position: { ...(element.position || {}) },
  style: { ...(element.style || {}) },
  data: cloneElementListData(element.data),
})
const createMockElements = () => elementPresets.map((element) => cloneElementData(element))
const messages = reactive([])
const slides = reactive([
  { title: '勾股定理', eyebrow: '八年级数学 · 第 1 课时', description: '从实际测量出发，发现直角三角形三边之间恒定而优雅的关系。', layout: '重点陈述', theme: 'blue' },
  { title: '情境导入', eyebrow: '01 / 生活中的直角', description: '校园里有哪些直角三角形？用旗杆与影子的测量任务开启今天的探索。', layout: '图文并置', theme: 'blue' },
  { title: '观察与猜想', eyebrow: '02 / 发现关系', description: '拖动顶点，观察两条直角边所对应正方形面积与斜边面积的变化。', layout: '图文并置', theme: 'navy' },
  { title: '公式推导', eyebrow: '03 / 建立模型', description: '将三边长度转化为面积，归纳勾股定理的表达式。', layout: '双栏探究', theme: 'green' },
  { title: '互动练习', eyebrow: '04 / 动手验证', description: '完成三组测量与计算，检验你的发现是否始终成立。', layout: '双栏探究', theme: 'orange' },
])
slides.forEach((slide, index) => {
  slide.elements = createMockElements()
  slide.pageType = index === 0 ? 'cover' : 'content'
  slide.page_type = slide.pageType
})
const current = computed(() => slides[selectedSlide.value])
const syncHtmlCanvasSource = (slide = current.value, { forceReload = false } = {}) => {
  htmlCanvasSourceSlide.value = slide || null
  htmlCanvasSource.value = slide?.html ? String(slide.html) : ''
  structuredHtmlCanvasSourceSlide.value = slide && !slide.html ? slide : null
  structuredHtmlCanvasSource.value = ''
  if (forceReload && slide === current.value) htmlCanvasFrameRevision.value += 1
}
const withHtmlCanvasFrameRevision = (source) => `${String(source || '')}\n<!-- a12-html-canvas-revision:${htmlCanvasFrameRevision.value} -->`
const htmlCanvasFrameSource = computed(() => {
  if (!current.value) return ''
  const source = current.value.html
    ? (htmlCanvasSourceSlide.value === current.value ? htmlCanvasSource.value : String(current.value.html))
    : (structuredHtmlCanvasSourceSlide.value === current.value && structuredHtmlCanvasSource.value
      ? structuredHtmlCanvasSource.value
      : buildStructuredHtmlSlide(current.value))
  return withHtmlCanvasFrameRevision(secureHtmlForSandbox(withHtmlPageBackground(source, current.value)))
})
const setCanvasZoom = (value) => {
  const rawValue = String(value ?? '').trim()
  const numericValue = Number(rawValue)
  if (!rawValue || !Number.isFinite(numericValue)) {
    canvasZoomInput.value = String(canvasZoom.value)
    return
  }
  canvasZoom.value = Math.round(Math.min(CANVAS_ZOOM_MAX, Math.max(CANVAS_ZOOM_MIN, numericValue)))
  canvasZoomInput.value = String(canvasZoom.value)
  // 当前不开放画布拖动，因此缩放始终保持页面位于工作区几何中心。
  void nextTick(centerCanvasView)
}
const adjustCanvasZoom = (delta) => setCanvasZoom(canvasZoom.value + delta)
const resetCanvasZoom = () => setCanvasZoom(86)
const commitCanvasZoomInput = () => setCanvasZoom(canvasZoomInput.value)
const applyCanvasCenter = () => {
  const canvasArea = canvasAreaRef.value
  if (!canvasArea) return
  canvasArea.scrollTo({
    left: Math.max(0, (canvasArea.scrollWidth - canvasArea.clientWidth) / 2),
    top: Math.max(0, (canvasArea.scrollHeight - canvasArea.clientHeight) / 2),
    behavior: 'auto',
  })
}
const centerCanvasView = () => {
  // 尺寸在 Vue 更新、HTML iframe 完成布局后才稳定；连续两帧校准确保
  // 无滚动条时由 CSS 居中，有滚动条时则同时回到 X/Y 中点。
  if (canvasCenterFrame != null) cancelAnimationFrame(canvasCenterFrame)
  applyCanvasCenter()
  canvasCenterFrame = requestAnimationFrame(() => {
    canvasCenterFrame = requestAnimationFrame(() => {
      canvasCenterFrame = null
      applyCanvasCenter()
    })
  })
}
const preventCanvasMiddleMouse = (event) => {
  if (event.button === 1) event.preventDefault()
}
const handleCanvasWheel = (event, canvasArea = event.currentTarget) => {
  const delta = Number(event.deltaY || 0)
  if (!delta || !canvasArea?.getBoundingClientRect) return
  event.preventDefault()
  const previousZoom = canvasZoom.value
  const nextZoom = Math.round(Math.min(CANVAS_ZOOM_MAX, Math.max(CANVAS_ZOOM_MIN, previousZoom + (delta < 0 ? CANVAS_WHEEL_ZOOM_STEP : -CANVAS_WHEEL_ZOOM_STEP))))
  if (nextZoom === previousZoom) return
  setCanvasZoom(nextZoom)
}
const startCanvasPan = (event, canvasArea = event.currentTarget) => {
  if (event.button !== 1 || !canvasArea) return
  event.preventDefault()
  event.stopPropagation()
  canvasPanning.value = true
  canvasPanGesture = {
    pointerId: event.pointerId,
    canvasArea,
    capturesPointer: event.currentTarget === canvasArea,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startScrollLeft: canvasArea.scrollLeft,
    startScrollTop: canvasArea.scrollTop,
  }
  // iframe 内的事件必须保留在 iframe 文档中处理；跨文档抢占指针会造成浏览器重绘抖动。
  if (canvasPanGesture.capturesPointer) {
    try { canvasArea.setPointerCapture?.(event.pointerId) } catch { /* 浏览器已接管指针 */ }
  }
}
const moveCanvasPan = (event) => {
  const gesture = canvasPanGesture
  if (!gesture || event.pointerId !== gesture.pointerId) return
  event.preventDefault()
  gesture.canvasArea.scrollLeft = gesture.startScrollLeft - (event.clientX - gesture.startClientX)
  gesture.canvasArea.scrollTop = gesture.startScrollTop - (event.clientY - gesture.startClientY)
}
const stopCanvasPan = (event) => {
  const gesture = canvasPanGesture
  if (!gesture || (event?.pointerId != null && event.pointerId !== gesture.pointerId)) return
  try {
    if (gesture.capturesPointer && gesture.canvasArea?.hasPointerCapture?.(gesture.pointerId)) gesture.canvasArea.releasePointerCapture(gesture.pointerId)
  } catch { /* 已由浏览器释放指针捕获 */ }
  canvasPanGesture = null
  canvasPanning.value = false
}
watch(current, (slide) => syncHtmlCanvasSource(slide), { immediate: true })
watch(selectedSlide, () => {
  // 切页后总从画布中心展示，不把上一页的平移视角带到新页面。
  void nextTick(centerCanvasView)
})
const themeForSlide = (slide) => themes.find((item) => item.id === slide?.theme) || themes[0]
const theme = computed(() => themeForSlide(current.value))
const unwrapResponse = (response) => {
  if (response && typeof response === 'object' && Object.prototype.hasOwnProperty.call(response, 'code')) {
    const code = Number(response.code)
    if (![0, 200].includes(code)) {
      const error = new Error(response.message || '请求失败')
      error.code = code
      throw error
    }
    return Object.prototype.hasOwnProperty.call(response, 'data') ? response.data : response
  }
  return response
}
const sessionId = computed(() => route.query.sessionId)
const projectId = computed(() => route.query.projectId)
const presentationFixtureMode = computed(() => import.meta.env.DEV && (
  String(route.query.pptFixture || '') === '1' || import.meta.env.VITE_PPT_FIXTURE_MODE === 'true'
))
const project = ref(null)
const projectLoadError = ref('')
const defaultSlide = (index = 1) => ({ title: `新建页面 ${index}`, eyebrow: '教学内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue', pageType: index === 1 ? 'cover' : 'content', page_type: index === 1 ? 'cover' : 'content', elements: createMockElements() })
const parseJson = (value, fallback = {}) => { try { return typeof value === 'string' ? JSON.parse(value) : (value || fallback) } catch { return fallback } }
const nonEmptyObject = (value) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length ? value : null
const routeQueryValue = (value) => Array.isArray(value) ? value[0] : value
const workspaceModes = [
  { value: 'ppt', label: 'PPT 课件', projectType: 'ppt' },
  { value: 'document', label: '教学案文档', projectType: 'word' },
]
const normalizeWorkspaceMode = (value) => {
  const normalized = String(value || '').trim().toLowerCase()
  if (['document', 'lesson_plan', 'lesson-plan', 'word', 'teaching_plan'].includes(normalized)) return 'document'
  // 兼容旧项目与旧链接：H5 已收敛为课件内的互动组件，不再作为独立工作台。
  if (['h5', 'html', 'interactive'].includes(normalized)) return 'ppt'
  return 'ppt'
}
const workspaceMode = ref(normalizeWorkspaceMode(routeQueryValue(route.query.workspaceMode || route.query.mode)))
// Live edits deliberately keep srcdoc stable. A newly mounted canvas must start
// from the latest saved HTML, rather than the source used by the previous iframe.
watch(workspaceMode, () => syncHtmlCanvasSource())
const workspaceModeLabel = computed(() => workspaceModes.find((item) => item.value === workspaceMode.value)?.label || 'PPT 课件')
const workspaceProjectType = computed(() => workspaceModes.find((item) => item.value === workspaceMode.value)?.projectType || 'ppt')
const isLocalDraft = computed(() => !projectId.value)
const localDraftId = ref(String(routeQueryValue(route.query.localDraftId) || `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`))
const currentDraftStorageId = computed(() => String(sessionId.value || localDraftId.value))
const assistantDrawerVisible = ref(false)
const propertiesDrawerVisible = ref(false)
const assistantDock = ref('side')
const assistantTargetScope = ref('auto')
// ===== 手机档（<768px）分段切换：对话 / 大纲 / 预览 / 教案，同一时刻只渲染一段 =====
const isMobile = ref(window.matchMedia('(max-width: 767.98px)').matches)
const activeSegment = ref('chat')
// hover: none 的触屏设备没有鼠标指针，激光笔（mousemove）与拖拽不可用。
const presentationPointerAvailable = typeof window !== 'undefined' && !window.matchMedia?.('(hover: none)')?.matches
// 触屏设备（无 hover + 粗指针）一次性判定：Enter 仅换行不发送，发送走按钮（参照 ChatView.vue）。
const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches
let mobileViewportMq = null
const handleMobileViewportChange = (event) => { isMobile.value = Boolean(event?.matches) }
const mobileSegments = computed(() => (
  workspaceMode.value === 'document'
    ? [{ label: '对话', value: 'chat' }, { label: '教案', value: 'plan' }]
    : [{ label: '对话', value: 'chat' }, { label: '大纲', value: 'outline' }, { label: '预览', value: 'preview' }, { label: '教案', value: 'plan' }]
))
const handleMobileSegmentChange = (value) => {
  activeSegment.value = value
  // PPT 模式下切到教案段：直接进入教案工作台（document 模式），分段随之收敛为 对话/教案。
  if (value === 'plan' && workspaceMode.value !== 'document') openLessonPlanWorkspace()
}
watch(workspaceMode, (mode) => {
  if (!isMobile.value) return
  if (mode === 'document') {
    if (!['chat', 'plan'].includes(activeSegment.value)) activeSegment.value = 'plan'
  } else if (!['chat', 'outline', 'preview'].includes(activeSegment.value)) {
    activeSegment.value = 'preview'
  }
})
// 手机档大纲段：以上下移按钮替代 HTML5 拖拽排序（复用 reorderSlides）。
const moveSlideRelative = (index, delta) => {
  const target = index + delta
  if (target < 0 || target >= slides.length) return
  reorderSlides(index, delta < 0 ? target : target + 1)
}
// 手机档放映：点击左右半屏翻页（激光笔已禁用，鼠标依赖降级）。
const handlePresentationStageClick = (event) => {
  // 仅触屏场景启用点击翻页（无指针设备或手机档）；桌面保持键盘/按钮翻页不变。
  if (!presentationMode.value || (presentationPointerAvailable && !isMobile.value)) return
  if (event.target?.closest?.('button, a, input, textarea, .preview-toolbar, .presentation-notes')) return
  const rect = previewStageRef.value?.getBoundingClientRect()
  if (!rect?.width) return
  const ratio = (event.clientX - rect.left) / rect.width
  if (ratio < 0.3) scrollPreviewTo(previewSlideIndex.value - 1)
  else scrollPreviewTo(previewSlideIndex.value + 1)
}
const queryArrayValue = (value) => {
  const parsed = parseJson(routeQueryValue(value), null)
  if (Array.isArray(parsed)) return parsed
  if (typeof value === 'string') return value.split(',').map((item) => item.trim()).filter(Boolean)
  return value == null || value === '' ? [] : [value]
}
const workspaceRequestErrorMessage = (error, fallback) => {
  const status = Number(error?.response?.status ?? error?.status ?? (Number.isFinite(Number(error?.code)) ? error.code : 0))
  const detail = String(error?.response?.data?.message || error?.message || '')
  if (status === 502 || /502|ECONNREFUSED|Network Error|网络错误/i.test(detail)) {
    return '教师端服务暂时未连接（Java 网关 8088），项目内容无法从服务器读取；请启动教师端服务后点击“重新加载”。'
  }
  if (status === 401) return '登录状态已失效，请重新登录后再打开课件。'
  if (status === 403) return '当前账号没有权限打开这个课件。'
  if (status === 404) return '课件或页面不存在，可能已被删除。'
  return detail || fallback
}
const pageRecords = (value) => {
  if (Array.isArray(value)) return value
  if (!value || typeof value !== 'object') return []
  const nested = value.records || value.items || value.list || value.pages || value.data || []
  return Array.isArray(nested) ? nested : pageRecords(nested)
}
const lessonPlanTitle = computed(() => String(
  project.value?.project_name
  || routeQueryValue(route.query.templateTitle)
  || current.value?.title
  || 'A12 教学教案',
))
const lessonPlanSubject = computed(() => String(
  routeQueryValue(route.query.subject)
  || project.value?.subject
  || presentationMetadata.value?.subject
  || '',
))
const lessonPlanGrade = computed(() => String(
  routeQueryValue(route.query.grade)
  || project.value?.grade
  || presentationMetadata.value?.grade
  || '',
))
const documentPlan = computed(() => lessonPlanDraft.value && typeof lessonPlanDraft.value === 'object' ? lessonPlanDraft.value : {})
const normalizedResourceIds = (values = []) => [...new Set(
  (Array.isArray(values) ? values : [values])
    .map((item) => String(item ?? '').trim())
    .filter(Boolean),
)]
const normalizeWorkspaceResource = (resource = {}) => {
  const id = resource.id ?? resource.resource_id ?? resource.resourceId
  return {
    id: id == null ? '' : String(id),
    name: String(resource.name || resource.file_name || resource.filename || resource.title || `资源 ${id || ''}`),
    fileType: String(resource.file_type || resource.fileType || resource.mime_type || resource.mimeType || ''),
    fileUrl: resource.file_url || resource.fileUrl || resource.url || '',
    thumbnail: resource.thumbnail || resource.thumbnail_url || resource.cover_url || '',
    previewUrl: resource.preview_url || resource.previewUrl || '',
    description: resource.description || '',
    allowAi: resource.allow_ai !== false && resource.allowAi !== false,
    raw: resource,
  }
}
const loadWorkspaceResources = async () => {
  workspaceResourcesLoading.value = true
  try {
    const response = unwrapResponse(await listResources({ page: 1, size: 100 }))
    const records = Array.isArray(response)
      ? response
      : response?.records || response?.items || response?.list || response?.resources || []
    workspaceResources.value = records.map(normalizeWorkspaceResource).filter((resource) => resource.id)
  } catch (error) {
    workspaceResources.value = []
    WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '个人资源库加载失败，仍可继续编辑页面'))
  } finally {
    workspaceResourcesLoading.value = false
  }
}
const workspaceBoundElementResourceIds = () => slides.flatMap((slide) => {
  const structuredIds = (slide?.elements || []).map((element) => element?.resourceId || element?.resource_id)
  const htmlIds = [...String(slide?.html || '').matchAll(/\bdata-resource-id\s*=\s*["']([^"']+)["']/gi)].map((match) => match[1])
  return [slide?.background?.resource_id, slide?.background?.resourceId, slide?.backgroundResourceId, ...structuredIds, ...htmlIds]
}).map((id) => String(id || '').trim()).filter(Boolean)
/** 工作台后续讨论、修改、重新生成和互动组件生成共用的上下文。 */
const workspaceContextPayload = () => {
  const storedContext = presentationMetadata.value?.workspace_context || presentationMetadata.value?.workspaceContext || {}
  const routeContext = {
    ...(storedContext && typeof storedContext === 'object' ? storedContext : {}),
    ...parseJson(routeQueryValue(route.query.workspaceContext), {}),
  }
  const explicitlyBoundResourceIds = workspaceResourceBindingOverride.value !== null
    ? workspaceResourceBindingOverride.value
    : [
      ...queryArrayValue(route.query.resourceIds),
      ...(Array.isArray(routeContext.resourceIds) ? routeContext.resourceIds : []),
      ...(Array.isArray(routeContext.resource_ids) ? routeContext.resource_ids : []),
      ...(Array.isArray(routeContext.bound_materials) ? routeContext.bound_materials : []),
      ...(Array.isArray(routeContext.bind_materials) ? routeContext.bind_materials : []),
      current.value?.background?.resource_id,
      current.value?.background?.resourceId,
      current.value?.backgroundResourceId,
    ]
  // 画布中的素材属于页面内容，不应因为教师在“AI 上下文”中做了筛选就丢掉权限
  // 追踪；资源 ID 与下载授权路径会一并进入项目上下文和后续生成请求。
  const resourceIds = normalizedResourceIds([
    ...explicitlyBoundResourceIds,
    ...workspaceBoundElementResourceIds(),
  ])
  const uploadedResources = Array.isArray(routeContext.uploadedResources)
    ? routeContext.uploadedResources
    : Array.isArray(routeContext.uploaded_resources) ? routeContext.uploaded_resources : []
  const community = routeContext.community || (route.query.communityId ? {
    id: routeQueryValue(route.query.communityId),
    type: routeQueryValue(route.query.communityType) || '',
    title: routeQueryValue(route.query.templateTitle) || '',
  } : null)
  return {
    ...routeContext,
    session_id: sessionId.value ? String(sessionId.value) : undefined,
    project_id: projectId.value ? String(projectId.value) : undefined,
    workspace_mode: workspaceMode.value,
    assistant_target: {
      scope: assistantTargetScope.value,
      label: assistantTargetLabel.value,
      page_id: current.value?.pageId || current.value?.page_id || null,
      page_number: selectedSlide.value + 1,
      component_id: assistantTargetScope.value === 'component'
        ? (workspaceSelectedElement.value?.id || null)
        : null,
    },
    resourceIds,
    resource_ids: resourceIds,
    bound_materials: resourceIds,
    bind_materials: resourceIds,
    uploadedResources: uploadedResources.slice(0, 30),
    uploaded_resources: uploadedResources.slice(0, 30),
    workspace_resource_bindings: workspaceResources.value
      .filter((resource) => resourceIds.includes(String(resource.id)))
      .slice(0, 30)
      .map((resource) => ({ id: String(resource.id), name: resource.name, file_type: resource.fileType || resource.file_type || '' })),
    current_page: current.value ? {
      page_id: current.value.pageId || current.value.page_id || null,
      title: current.value.title || '',
      background_resource_id: current.value.background?.resource_id || current.value.backgroundResourceId || null,
    } : null,
    community,
    community_skill: community?.type === 'Skill' ? community : (routeContext.community_skill || null),
    community_case: community?.type === '案例' || community?.type === '测试案例' ? community : (routeContext.community_case || null),
  }
}
const openWorkspaceContextManager = () => {
  contextManagerIds.value = [...workspaceContextPayload().resource_ids]
  contextManagerVisible.value = true
}
const removeContextResource = (id) => {
  contextManagerIds.value = contextManagerIds.value.filter((item) => String(item) !== String(id))
}
const saveWorkspaceContextBindings = async () => {
  contextManagerSaving.value = true
  try {
    workspaceResourceBindingOverride.value = normalizedResourceIds(contextManagerIds.value)
    contextManagerVisible.value = false
    if (projectId.value) await syncProjectWorkspaceContextIfNeeded()
    else if (sessionId.value) saveCurrentPresentationDraft()
    WorkspaceMessage.success('AI 资料绑定已保存')
  } catch (error) {
    WorkspaceMessage.error(error?.message || 'AI 资料绑定保存失败')
  } finally {
    contextManagerSaving.value = false
  }
}
const qualityArray = (value) => {
  if (Array.isArray(value)) return value.map((item) => typeof item === 'object' ? (item?.message || item?.text || item?.description || item?.title || JSON.stringify(item)) : String(item)).filter(Boolean)
  if (typeof value === 'string') return value.split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
  return value ? [String(value)] : []
}
const normalizeQualityReport = (raw) => {
  let value = raw
  if (typeof value === 'string') value = parseJson(value, null)
  if (Array.isArray(value)) value = { suggestions: value }
  if (!value || typeof value !== 'object') return null
  const nested = value.quality_report || value.qualityReport || value.report
  if (nested && nested !== value) {
    const normalized = normalizeQualityReport(nested)
    if (normalized) {
      return {
        ...normalized,
        summary: normalized.summary || String(value.summary || value.reflection || value.message || ''),
        suggestions: [...new Set([...normalized.suggestions, ...qualityArray(value.suggestions || value.fixes || value.recommendations)])],
      }
    }
  }
  const scoreValue = value.score ?? value.quality_score ?? value.qualityScore ?? value.overall_score ?? value.total_score
  const score = Number(scoreValue)
  const normalizedScore = Number.isFinite(score) ? (score <= 1 ? Math.round(score * 100) : Math.round(score)) : null
  const issues = qualityArray(value.issues || value.problems || value.structure_issues || value.structureProblems)
  const risks = qualityArray(value.risks || value.content_risks || value.contentRisks || value.warnings)
  const suggestions = qualityArray(value.suggestions || value.fixes || value.recommendations || value.improvements)
  const summary = String(value.summary || value.reflection || value.analysis || value.message || '').trim()
  const retryCount = Number(value.retry_count ?? value.retryCount ?? 0)
  if (normalizedScore == null && !issues.length && !risks.length && !suggestions.length && !summary) return null
  return { score: normalizedScore, summary, issues, risks, suggestions, retryCount: Number.isFinite(retryCount) ? retryCount : 0, raw: value }
}
const setQualityReport = (raw, source = '') => {
  const normalized = normalizeQualityReport(raw)
  if (normalized) {
    qualityReport.value = normalized
    qualityReportSource.value = source
  }
  return normalized
}
const openQualityPanel = () => {
  if (!qualityReport.value) WorkspaceMessage.info('当前还没有生成质量报告；完成一次 AI 生成或重新生成后会在这里显示。')
  qualityPanelVisible.value = true
}
const applyQualitySuggestion = async (suggestion) => {
  const instruction = String(suggestion || '').trim()
  if (!instruction) return
  qualityPanelVisible.value = false
  prompt.value = `请根据质量建议修改当前页面：${instruction}`
  await nextTick()
  await sendAssistantMessage()
}
const normalizeOutlinePayload = (planData = {}) => {
  const parsedPlan = parseJson(planData.plan_json ?? planData.outline ?? planData, {})
  const outline = parsedPlan?.outline
  if (outline && typeof outline === 'object' && !Array.isArray(outline)) return outline
  return parsedPlan && typeof parsedPlan === 'object' && !Array.isArray(parsedPlan) ? parsedPlan : {}
}
const lessonPlanOutline = computed(() => {
  const localDraft = sessionId.value ? readOutlineDraft(sessionId.value) : null
  return normalizeOutlinePayload(localDraft || presentationMetadata.value || {})
})
// 工作台路由中的 sessionId 是 Java 备课会话 ID；API-13B 的 session_id
// 指向 Python 大纲会话，优先从本地大纲快照或生成元数据读取，不能混用两者。
const workspacePythonSessionId = () => {
  const localDraft = sessionId.value ? readOutlineDraft(sessionId.value) : null
  return String(
    localDraft?.python_session_id
    || localDraft?.pythonSessionId
    || presentationMetadata.value?.python_session_id
    || presentationMetadata.value?.pythonSessionId
    || '',
  ).trim()
}
const getPresentationPayload = (rawResponse) => {
  const response = unwrapResponse(rawResponse)
  const candidate = response?.presentation || response?.result || response
  return candidate && typeof candidate === 'object' && !Array.isArray(candidate) ? candidate : {}
}
const normalizePresentationSlides = (data = {}) => {
  const rawSlides = Array.isArray(data.slides) ? data.slides : []
  return rawSlides
    .map((slide, index) => ({
      ...slide,
      title: String(slide?.title || `第 ${index + 1} 页`),
      eyebrow: `${String(Number(slide?.slide_no) || index + 1).padStart(2, '0')} / HTML PPT`,
      description: String(slide?.description || ''),
      footer: String(slide?.footer || ''),
      layout: slide?.layout || '重点陈述',
      theme: slide?.theme || 'blue',
      html: stripSlideDecorativeCircle(slide?.html || ''),
      notes: String(slide?.notes || ''),
      slideNo: Number(slide?.slide_no) || index + 1,
      interactiveAssets: slide?.interactive_assets || slide?.metadata?.interactive_assets || [],
      metadata: slide?.metadata || {},
      elements: Array.isArray(slide?.elements) ? slide.elements : [],
      pageOrder: Number(slide?.page_order ?? slide?.pageOrder ?? index + 1),
      page_order: Number(slide?.page_order ?? slide?.pageOrder ?? index + 1),
    }))
    .filter((slide) => slide.html.trim())
}
const scrollAssistantConversation = async () => {
  await nextTick()
  const element = assistantConversationRef.value
  if (element) element.scrollTop = element.scrollHeight
}
const clearGenerationFailureMessages = () => {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]
    const isLegacyGenerationError = String(message?.text || '') === '无法连接 HTML PPT 生成服务，请确认 Python 服务已启动。'
    if (message?.kind === 'generation-error' || isLegacyGenerationError) messages.splice(index, 1)
  }
  generationError.value = ''
}
const applyGeneratedPresentation = (rawResponse, { persist = true, notify = true } = {}) => {
  const data = getPresentationPayload(rawResponse)
  const generatedSlides = normalizePresentationSlides(data)
  if (!generatedSlides.length) throw new Error('HTML PPT 生成服务未返回页面')

  clearGenerationFailureMessages()
  // API-139A 只返回 slide_no/title/html 时，必须把现有项目页的身份合并回来。
  // 否则后续批量保存会把每一页当成新页，表现为“整体修改后重复页面”。
  const previousSlides = [...slides]
  const usedPreviousSlides = new Set()
  const generatedWithIdentity = generatedSlides.map((generatedSlide, index) => {
    const explicitPageId = generatedSlide.pageId
      || generatedSlide.page_id
      || generatedSlide.metadata?.pageId
      || generatedSlide.metadata?.page_id
      || generatedSlide.metadata?.source_page_id
    const generatedTitle = String(generatedSlide.title || '').trim()
    const generatedSlideNo = Number(generatedSlide.slideNo || generatedSlide.slide_no || index + 1)
    const previous = previousSlides.find((candidate) => {
      if (!candidate || usedPreviousSlides.has(candidate)) return false
      if (explicitPageId && String(candidate.pageId || candidate.page_id) === String(explicitPageId)) return true
      return false
    }) || previousSlides.find((candidate) => {
      if (!candidate || usedPreviousSlides.has(candidate) || !generatedTitle) return false
      return String(candidate.title || '').trim() === generatedTitle
    }) || previousSlides.find((candidate) => {
      if (!candidate || usedPreviousSlides.has(candidate)) return false
      return Number(candidate.slideNo || candidate.slide_no || 0) === generatedSlideNo
    }) || previousSlides[index]
    if (previous) usedPreviousSlides.add(previous)
    const pageId = explicitPageId || previous?.pageId || previous?.page_id || null
    return {
      ...generatedSlide,
      ...(pageId ? { pageId, page_id: pageId, componentId: pageId } : {}),
      ...((previous?.pageOrder ?? previous?.page_order) != null
        ? { pageOrder: previous.pageOrder ?? previous.page_order, page_order: previous.pageOrder ?? previous.page_order }
        : {}),
      ...(previous?.pageVersion ? { pageVersion: previous.pageVersion } : {}),
      ...(previous?.clientVersion ? { clientVersion: previous.clientVersion } : {}),
      ...(projectId.value ? { dirty: true } : {}),
    }
  })
  slides.splice(0, slides.length, ...generatedWithIdentity)
  if (projectId.value) markSlideComponentDirty(slides[0], 'deck:ai', { structure: true })
  selectedSlide.value = 0
  selectedElementId.value = null
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
  presentationId.value = String(data.presentation_id || '')
  presentationMetadata.value = data.metadata && typeof data.metadata === 'object'
    ? {
      ...data.metadata,
      ...(data.workspace_context || data.workspaceContext ? { workspace_context: data.workspace_context || data.workspaceContext } : {}),
    }
    : ((data.workspace_context || data.workspaceContext) ? { workspace_context: data.workspace_context || data.workspaceContext } : null)
  const qualityPayload = data.quality_report || data.qualityReport || data.reflection || presentationMetadata.value?.quality_report || presentationMetadata.value?.reflection
  setQualityReport(qualityPayload, 'HTML PPT 生成')
  // 首次生成的完整生命周期由 startRun 负责收尾；这里不能提前宣布完成，
  // 否则“页面已装载但项目尚未保存”会被错误展示成生成成功。
  if (activeRunId.value && runStatus.value === 'running') {
    attachClientRunReflection(qualityPayload)
    upsertClientToolCall({
      id: 'generation-quality-check',
      name: '生成质量检查',
      status: 'completed',
      detail: qualityReport.value?.score == null ? '已返回质量建议' : `评分 ${qualityReport.value.score}/100`,
    })
    setClientRunStage({ id: 'presentation-load', label: 'HTML 页面已装载', status: 'completed', progress: 92 })
  } else {
    runStatus.value = 'completed'
    runProgress.value = 100
    runStage.value = 'HTML PPT 已生成'
  }

  if (persist && sessionId.value) {
    savePresentationDraft(sessionId.value, {
      presentation_id: presentationId.value,
      title: data.title || generatedSlides[0].title,
      slide_count: generatedSlides.length,
      request_key: String(routeQueryValue(route.query.pptGeneration) || '') || null,
      slides: generatedWithIdentity,
      metadata: presentationMetadata.value,
      workspace_context: workspaceContextPayload(),
    })
  }

  if (notify) {
    messages.push({ role: 'assistant', text: `已生成 ${generatedSlides.length} 页 HTML PPT，可在工作台中预览。`, includeInContext: false, kind: 'generation-success' })
    WorkspaceMessage.success(`已生成 ${generatedSlides.length} 页 HTML PPT`)
  }
  void scrollAssistantConversation()

  return data
}
const loadPresentationFixture = () => {
  const data = applyGeneratedPresentation(createPresentationFixture(), { persist: true, notify: false })
  messages.push({ role: 'assistant', text: `已载入 ${data.slide_count} 页固定 PPT 测试样例，不会调用大模型。`, includeInContext: false, kind: 'generation-success' })
  WorkspaceMessage.info('已载入固定 PPT 测试样例，不会消耗 API')
  void scrollAssistantConversation()
  return data
}
const saveCurrentPresentationDraft = () => {
  if (projectId.value) return
  const draftId = currentDraftStorageId.value
  if (!draftId) return
  const existing = readPresentationDraft(draftId) || {}
  savePresentationDraft(draftId, {
    ...existing,
    presentation_id: presentationId.value || existing.presentation_id || '',
    title: existing.title || slides[0]?.title || 'A12 教学课件',
    slide_count: slides.length,
    request_key: String(routeQueryValue(route.query.pptGeneration) || '') || existing.request_key || null,
    slides,
    metadata: presentationMetadata.value || existing.metadata || null,
    workspace_context: workspaceContextPayload(),
    workspace_mode: workspaceMode.value,
    lesson_plan: lessonPlanDraft.value || existing.lesson_plan || null,
  })
  if (!savingPage.value && !testCaseBootstrapping.value) autosaveState.value = '本地草稿 · 尚未保存为项目'
}
const htmlDragTargetSelector = '[data-ppt-element],h1,h2,h3,h4,h5,h6,p,li,img,audio,video,iframe,svg,table,header,main,section,article,aside,footer,figure,div[class],.card,.item,.box,.panel'
const htmlTextTargetSelector = 'h1,h2,h3,h4,h5,h6,p,li,span,strong,em,small,td,th,blockquote,[data-ppt-type="text"],[data-ppt-type="formula"]'
const htmlSlideHistories = new WeakMap()
const previewFrameObservers = new Set()
const h5FrameObservers = new WeakMap()
const sendH5FrameViewport = (iframe) => {
  if (!iframe?.contentWindow) return
  const width = Math.max(1, Number(iframe.clientWidth || 0))
  const height = Math.max(1, Number(iframe.clientHeight || 0))
  if (!width || !height) return
  const previous = h5FrameObservers.get(iframe) || {}
  if (previous.width === width && previous.height === height) return
  h5FrameObservers.set(iframe, { ...previous, width, height })
  iframe.contentWindow.postMessage({ source: 'a12-h5-host', type: 'a12-h5-viewport', width, height }, '*')
}
const syncH5FrameViewport = (eventOrFrame) => {
  const iframe = eventOrFrame?.currentTarget || eventOrFrame
  if (!iframe || String(iframe.tagName || '').toLowerCase() !== 'iframe') return
  let state = h5FrameObservers.get(iframe)
  if (!state) {
    state = { width: 0, height: 0, observer: null }
    if (typeof ResizeObserver !== 'undefined') {
      state.observer = new ResizeObserver(() => sendH5FrameViewport(iframe))
      state.observer.observe(iframe)
    }
    h5FrameObservers.set(iframe, state)
  }
  sendH5FrameViewport(iframe)
}
const parseCssTranslate = (value) => {
  const numbers = String(value || '').match(/-?\d*\.?\d+/g)?.map(Number) || []
  return { x: Number.isFinite(numbers[0]) ? numbers[0] : 0, y: Number.isFinite(numbers[1]) ? numbers[1] : 0 }
}
const parseCssRotation = (value) => {
  const rotation = Number(String(value || '').match(/-?\d*\.?\d+/)?.[0])
  return Number.isFinite(rotation) ? rotation : 0
}
const serializeHtmlSlide = (document) => serializeLandPptEditableDocument(document)
const htmlHistoryForSlide = (slide) => {
  if (!htmlSlideHistories.has(slide)) htmlSlideHistories.set(slide, { undo: [], redo: [] })
  return htmlSlideHistories.get(slide)
}
const applyHtmlSlideChange = (slide, nextHtml, { record = true, refreshFrame = true } = {}) => {
  if (!slide || !nextHtml || nextHtml === slide.html) return false
  const history = htmlHistoryForSlide(slide)
  if (record) {
    history.undo.push(slide.html)
    if (history.undo.length > 30) history.undo.shift()
    history.redo.length = 0
  }
  slide.html = nextHtml
  // 画布内编辑已经在当前 iframe 中完成，保存时不应重载 srcdoc；
  // 只有撤销/重做或来自画布外的更新才需要把持久化内容重新载入。
  if (refreshFrame && htmlCanvasSourceSlide.value === slide) syncHtmlCanvasSource(slide, { forceReload: true })
  markSlideComponentDirty(slide)
  saveCurrentPresentationDraft()
  return true
}
const undoHtmlSlideChange = (slide) => {
  const history = htmlHistoryForSlide(slide)
  const previous = history.undo.pop()
  if (!previous) return false
  if (!slide?.html && previous?.mode === 'structured') {
    history.redo.push(structuredHistorySnapshot(slide, structuredHtmlLiveDocumentForSlide(slide)))
    return restoreStructuredHistorySnapshot(slide, previous)
  }
  history.redo.push(slide.html)
  applyHtmlSlideChange(slide, previous, { record: false })
  return true
}
const redoHtmlSlideChange = (slide) => {
  const history = htmlHistoryForSlide(slide)
  const next = history.redo.pop()
  if (!next) return false
  if (!slide?.html && next?.mode === 'structured') {
    history.undo.push(structuredHistorySnapshot(slide, structuredHtmlLiveDocumentForSlide(slide)))
    return restoreStructuredHistorySnapshot(slide, next)
  }
  history.undo.push(slide.html)
  applyHtmlSlideChange(slide, next, { record: false })
  return true
}
const HTML_CANVAS_WIDTH = 1280
const HTML_CANVAS_HEIGHT = 720
const htmlTextTags = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'span', 'strong', 'em', 'small', 'td', 'th', 'blockquote'])
const htmlTypeAliases = { textbox: 'text', paragraph: 'text', rich_text: 'text', text_box: 'text', picture: 'image', photo: 'image', rectangle: 'shape', rect: 'shape', graph: 'chart' }
const htmlColorToHex = (value, fallback) => {
  const raw = String(value || '').trim()
  if (!raw || raw === 'transparent') return fallback
  if (/^#[\da-f]{3,8}$/i.test(raw)) return raw
  const match = raw.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?\s*\)$/i)
  if (!match) return fallback
  const alpha = match[4] === undefined ? 1 : Number(match[4])
  if (Number.isFinite(alpha) && alpha <= 0) return fallback
  return `#${[match[1], match[2], match[3]].map((item) => Number(item).toString(16).padStart(2, '0')).join('')}`
}
const htmlNoopCleanup = () => {}
const attachHtmlDragEditor = (iframe, { structuredMode = false, onCommit = null } = {}) => {
  if (!iframe.classList.contains('editable-html-frame')) return htmlNoopCleanup
  const document = iframe.contentDocument
  const frameWindow = iframe.contentWindow
  const slide = current.value
  if (!document?.body || !frameWindow || !slide) return htmlNoopCleanup

  const editorStyle = document.createElement('style')
  editorStyle.id = 'a12-html-drag-style'
  editorStyle.textContent = `
    [data-a12-drag-selected] {
      outline: 3px solid #2563eb !important;
      outline-offset: 4px !important;
      cursor: move !important;
      transition: none !important;
      animation-play-state: paused !important;
      touch-action: none !important;
      user-select: none !important;
      will-change: translate, width, height, rotate;
    }
    [data-a12-drag-selected] * {
      cursor: move !important;
      transition: none !important;
      animation-play-state: paused !important;
      user-select: none !important;
    }
    [data-a12-html-editing], [data-a12-html-editing] * {
      cursor: text !important;
      user-select: text !important;
    }
    .a12-html-editor-overlay {
      position: fixed !important;
      z-index: 2147483646 !important;
      display: none;
      box-sizing: border-box !important;
      border: 1px solid rgb(37 99 235 / 75%) !important;
      pointer-events: none !important;
    }
    .a12-html-editor-overlay.is-visible { display: block; }
    .a12-html-move-handle {
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      z-index: 0 !important;
      display: none;
      box-sizing: border-box !important;
      border-radius: inherit !important;
      background: transparent !important;
      cursor: move !important;
      pointer-events: auto !important;
      touch-action: none !important;
      user-select: none !important;
    }
    .a12-html-editor-overlay.is-h5 .a12-html-move-handle { display: flex; }
    .a12-html-element-proxy {
      position: fixed !important;
      z-index: 2147483645 !important;
      display: block !important;
      box-sizing: border-box !important;
      border: 1px solid transparent !important;
      background: transparent !important;
      cursor: grab !important;
      pointer-events: auto !important;
      touch-action: none !important;
      user-select: none !important;
    }
    .a12-html-element-proxy:active { cursor: grabbing !important; }
    .a12-html-editor-toolbar {
      position: absolute !important;
      /* 与上方的旋转圆点同列，操作条从圆点右侧开始。 */
      top: -40px !important;
      right: auto !important;
      bottom: auto !important;
      left: calc(50% + 20px) !important;
      display: flex !important;
      gap: 4px !important;
      padding: 4px !important;
      border-radius: 7px !important;
      background: #1d4ed8 !important;
      box-shadow: 0 5px 16px rgb(15 23 42 / 24%) !important;
      pointer-events: auto !important;
      white-space: nowrap !important;
      transform: scale(var(--a12-editor-toolbar-scale, 1)) !important;
      transform-origin: center left !important;
    }
    .a12-html-editor-overlay.is-toolbar-left .a12-html-editor-toolbar {
      right: calc(50% + 20px) !important;
      left: auto !important;
      transform-origin: center right !important;
    }
    .a12-html-editor-overlay.is-toolbar-bottom .a12-html-editor-toolbar {
      top: auto !important;
      bottom: -4px !important;
    }
    .a12-html-editor-toolbar button {
      all: initial !important;
      min-width: 42px !important;
      padding: 6px 10px !important;
      border-radius: 4px !important;
      color: #fff !important;
      background: transparent !important;
      font: 600 13px/1.2 "Microsoft YaHei", sans-serif !important;
      cursor: pointer !important;
      user-select: none !important;
    }
    .a12-html-editor-toolbar button:hover { background: rgb(255 255 255 / 18%) !important; }
    .a12-html-resize-handle, .a12-html-rotate-handle {
      position: absolute !important;
      box-sizing: border-box !important;
      width: 14px !important;
      height: 14px !important;
      border: 2px solid #fff !important;
      border-radius: 50% !important;
      background: #2563eb !important;
      box-shadow: 0 1px 5px rgb(15 23 42 / 35%) !important;
      pointer-events: auto !important;
      touch-action: none !important;
    }
    .a12-html-resize-handle { right: -8px !important; bottom: -8px !important; cursor: nwse-resize !important; }
    .a12-html-rotate-handle { top: -29px !important; left: calc(50% - 7px) !important; cursor: grab !important; }
    .a12-html-rotate-line {
      position: absolute !important;
      top: -17px !important;
      left: 50% !important;
      width: 1px !important;
      height: 17px !important;
      background: #2563eb !important;
    }
  `
  editorStyle.textContent += subjectToolRuntimeCss
  document.head?.appendChild(editorStyle)

  const overlay = document.createElement('div')
  overlay.className = 'a12-html-editor-overlay'
  overlay.innerHTML = `
    <div class="a12-html-move-handle" aria-label="移动 H5 元素"></div>
    <div class="a12-html-editor-toolbar">
      <button type="button" data-action="undo" title="撤销 Ctrl+Z">撤销</button>
      <button type="button" data-action="redo" title="重做 Ctrl+Y">重做</button>
      <button type="button" data-action="copy">复制</button>
      <button type="button" data-action="delete">删除</button>
    </div>
    <span class="a12-html-rotate-line"></span>
    <span class="a12-html-rotate-handle" title="旋转"></span>
    <span class="a12-html-resize-handle" title="调整大小"></span>
  `
  document.body.appendChild(overlay)
  const resizeHandle = overlay.querySelector('.a12-html-resize-handle')
  const rotateHandle = overlay.querySelector('.a12-html-rotate-handle')
  const moveHandle = overlay.querySelector('.a12-html-move-handle')
  const editorToolbar = overlay.querySelector('.a12-html-editor-toolbar')
  const panelElementById = new Map()
  const elementPanelId = new WeakMap()
  const elementPanelKey = new WeakMap()
  const h5ElementProxies = new Map()
  const h5ElementViewportObservers = new Map()

  const h5FrameForElement = (element) => {
    if (!element) return null
    if (String(element.tagName || '').toLowerCase() === 'iframe') return element
    return element.querySelector?.(':scope > iframe[data-a12-h5-frame], :scope > iframe') || null
  }
  const layoutH5Element = (element) => {
    const frame = h5FrameForElement(element)
    if (!frame) return
    const width = Math.max(1, Number(element.clientWidth || 0))
    const height = Math.max(1, Number(element.clientHeight || 0))
    const scale = Math.max(0.01, Math.min(width / H5_DESIGN_WIDTH, height / H5_DESIGN_HEIGHT))
    const renderedWidth = H5_DESIGN_WIDTH * scale
    const renderedHeight = H5_DESIGN_HEIGHT * scale
    frame.style.position = 'absolute'
    frame.style.left = `${(width - renderedWidth) / 2}px`
    frame.style.top = `${(height - renderedHeight) / 2}px`
    frame.style.width = `${H5_DESIGN_WIDTH}px`
    frame.style.height = `${H5_DESIGN_HEIGHT}px`
    frame.style.maxWidth = 'none'
    frame.style.maxHeight = 'none'
    frame.style.margin = '0'
    frame.style.border = '0'
    frame.style.borderRadius = '0'
    frame.style.transformOrigin = 'top left'
    frame.style.transform = `scale(${scale})`
  }
  const createH5Host = ({ html = '', config = {}, title = 'H5 互动内容' } = {}) => {
    const host = document.createElement('div')
    host.setAttribute('data-a12-h5-host', '')
    host.style.overflow = 'hidden'
    host.style.padding = '0'
    const frame = document.createElement('iframe')
    frame.setAttribute('data-a12-h5-frame', '')
    frame.setAttribute('sandbox', 'allow-scripts')
    frame.setAttribute('title', title)
    frame.srcdoc = secureHtmlForSandbox(withH5RuntimeConfig(html, config))
    host.appendChild(frame)
    return { host, frame }
  }
  const normalizeLegacyH5Elements = () => {
    const frames = [...document.querySelectorAll('iframe[data-ppt-type="h5"], iframe[data-h5-generated]')]
    frames.forEach((legacyFrame) => {
      if (legacyFrame.closest('[data-a12-h5-host]')) return
      const config = parseJson(legacyFrame.getAttribute('data-h5-config'), {})
      const { host, frame } = createH5Host({
        html: legacyFrame.getAttribute('srcdoc') || legacyFrame.srcdoc || '',
        config,
        title: legacyFrame.getAttribute('title') || 'H5 互动内容',
      })
      ;[...legacyFrame.attributes].forEach((attribute) => {
        if (['srcdoc', 'sandbox', 'style', 'class', 'title'].includes(attribute.name)) return
        host.setAttribute(attribute.name, attribute.value)
      })
      host.className = legacyFrame.className
      host.style.cssText = legacyFrame.style.cssText
      host.style.overflow = 'hidden'
      host.style.padding = '0'
      host.setAttribute('title', legacyFrame.getAttribute('title') || 'H5 互动内容')
      legacyFrame.replaceWith(host)
      layoutH5Element(host)
    })
  }
  const sendH5ElementEditing = (element, active) => {
    if (elementType(element) !== 'h5') return
    element.toggleAttribute('data-a12-h5-editing', Boolean(active))
  }
  const observeH5ElementViewport = (element) => {
    let state = h5ElementViewportObservers.get(element)
    if (!state) {
      const frame = h5FrameForElement(element)
      state = { observer: null, frame, loadListener: null }
      state.loadListener = () => layoutH5Element(element)
      frame?.addEventListener('load', state.loadListener)
      if (typeof frameWindow.ResizeObserver !== 'undefined') {
        state.observer = new frameWindow.ResizeObserver(() => layoutH5Element(element))
        state.observer.observe(element)
      }
      h5ElementViewportObservers.set(element, state)
    }
    layoutH5Element(element)
  }

  const defaultChartData = [
    { label: '一', value: 68 },
    { label: '二', value: 82 },
    { label: '三', value: 55 },
  ]
  const normalizeChartData = (value) => {
    const source = Array.isArray(value) && value.length ? value : defaultChartData
    return source.slice(0, 8).map((item, index) => ({
      label: String(item?.label || `数据${index + 1}`).trim().slice(0, 10),
      value: Math.max(0, Math.min(100, Number(item?.value) || 0)),
    }))
  }
  const getChartData = (element) => normalizeChartData(parseJson(element?.getAttribute('data-a12-chart-data'), []))
  const getTableData = (element) => [...(element?.querySelectorAll?.('tr') || [])]
    .map((row) => [...row.querySelectorAll('th,td')].map((cell) => String(cell.textContent || '').trim()))
    .filter((row) => row.length)
  const renderHtmlTable = (element, value = getTableData(element)) => {
    if (!element) return
    const rows = Array.isArray(value) && value.length ? value : [['列 1', '列 2'], ['内容 1', '内容 2']]
    const columnCount = Math.max(1, ...rows.map((row) => Array.isArray(row) ? row.length : 1))
    // 始终保存为规则的矩形数据：属性面板修改行、列后，画布和持久化数据保持一致。
    const normalizedRows = rows.map((row, rowIndex) => Array.from({ length: columnCount }, (_, columnIndex) => {
      const cell = Array.isArray(row) ? row[columnIndex] : (columnIndex === 0 ? row : undefined)
      if (cell !== undefined) return String(cell ?? '')
      return rowIndex === 0 ? `列 ${columnIndex + 1}` : ''
    }))
    const isTableElement = element.tagName?.toLowerCase() === 'table'
    // 结构化表格会带一个容器标题；调整行列时保留它，避免只剩下网格。
    const tableLabel = !isTableElement ? element.querySelector(':scope > strong')?.cloneNode(true) : null
    element.innerHTML = ''
    const table = isTableElement ? element : document.createElement('table')
    table.style.width = '100%'
    table.style.height = '100%'
    table.style.borderCollapse = 'collapse'
    table.style.color = 'inherit'
    normalizedRows.forEach((row, rowIndex) => {
      const tr = document.createElement('tr')
      row.forEach((cell) => {
        const cellNode = document.createElement(rowIndex === 0 ? 'th' : 'td')
        cellNode.textContent = cell
        cellNode.style.padding = '6px 8px'
        cellNode.style.border = '1px solid rgb(37 99 235 / 18%)'
        cellNode.style.textAlign = 'left'
        cellNode.style.background = rowIndex === 0 ? 'rgb(219 234 254 / 70%)' : 'transparent'
        tr.appendChild(cellNode)
      })
      table.appendChild(tr)
    })
    if (!isTableElement) {
      if (tableLabel) element.appendChild(tableLabel)
      element.appendChild(table)
    }
    element.setAttribute('data-a12-table-data', JSON.stringify(normalizedRows))
    element.style.overflow = 'hidden'
    element.style.padding = element.style.padding || '8px'
    element.style.backgroundColor = element.style.backgroundColor || '#f8fbff'
    element.style.border = element.style.border || '1px solid #bfdbfe'
    element.style.borderRadius = element.style.borderRadius || '10px'
  }
  const markChartPart = (element) => {
    element.setAttribute('data-a12-chart-part', '')
    return element
  }
  const setChartPartStyle = (element, styles) => {
    Object.entries(styles).forEach(([key, value]) => { element.style[key] = value })
    return markChartPart(element)
  }
  const renderHtmlChart = (element, data = getChartData(element), title = null) => {
    if (!element) return
    const currentTitle = element.querySelector('[data-a12-chart-title]')?.textContent
      || element.getAttribute('data-a12-chart-title')
      || element.textContent
      || '数据图表'
    const chartTitle = String(title ?? currentTitle).trim().slice(0, 40) || '数据图表'
    const normalizedData = normalizeChartData(data)
    const color = element.style.getPropertyValue('--a12-chart-color').trim() || '#2563eb'

    element.classList.add('a12-html-chart')
    element.setAttribute('data-ppt-type', 'chart')
    element.setAttribute('data-a12-chart', 'true')
    element.setAttribute('data-a12-chart-title', chartTitle)
    element.setAttribute('data-a12-chart-data', JSON.stringify(normalizedData))
    element.style.display = 'flex'
    element.style.flexDirection = 'column'
    element.style.gap = '8px'
    element.style.padding = element.style.padding || '12px'
    element.style.boxSizing = 'border-box'
    element.style.overflow = 'hidden'
    element.style.backgroundColor = element.style.backgroundColor || '#eff6ff'
    element.style.border = element.style.border || '1px solid #bfdbfe'
    element.style.borderRadius = element.style.borderRadius || '14px'
    element.style.setProperty('--a12-chart-color', color)

    element.innerHTML = ''
    const header = setChartPartStyle(document.createElement('div'), {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '8px',
      minHeight: '18px',
    })
    const titleNode = setChartPartStyle(document.createElement('strong'), {
      overflow: 'hidden',
      color: 'var(--a12-chart-color)',
      fontSize: '11px',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    })
    titleNode.setAttribute('data-a12-chart-title', '')
    titleNode.textContent = chartTitle
    const tagNode = setChartPartStyle(document.createElement('small'), {
      flex: 'none',
      color: 'var(--a12-chart-color)',
      fontSize: '8px',
      fontWeight: '700',
      letterSpacing: '.08em',
    })
    tagNode.textContent = 'DATA'
    header.append(titleNode, tagNode)

    const plot = setChartPartStyle(document.createElement('div'), {
      display: 'flex',
      flex: '1 1 auto',
      alignItems: 'flex-end',
      justifyContent: 'space-around',
      gap: '8px',
      minHeight: '60px',
      padding: '8px 6px 0',
      borderBottom: '1px solid rgb(96 116 145 / 22%)',
    })
    plot.setAttribute('data-a12-chart-plot', '')
    normalizedData.forEach((item) => {
      const bar = setChartPartStyle(document.createElement('div'), {
        display: 'flex',
        flex: '1 1 0',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: '4px',
        minWidth: '0',
        height: '100%',
        flexDirection: 'column',
      })
      const fill = setChartPartStyle(document.createElement('span'), {
        display: 'block',
        flex: '0 0 auto',
        width: '22px',
        maxWidth: '70%',
        minHeight: '8%',
        height: `${Math.max(8, item.value)}%`,
        borderRadius: '5px 5px 2px 2px',
        background: 'var(--a12-chart-color)',
      })
      fill.setAttribute('data-a12-chart-bar', '')
      const label = setChartPartStyle(document.createElement('small'), {
        overflow: 'hidden',
        maxWidth: '100%',
        color: '#607491',
        fontSize: '8px',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      })
      label.textContent = item.label
      bar.append(fill, label)
      plot.append(bar)
    })
    element.append(header, plot)
  }

  const getSubjectData = (element) => parseJson(element?.getAttribute('data-subject-data'), {})
  // `data-subject-render` is the request-side render configuration. Newer
  // drafts keep the backend's response hint separately so editing data does
  // not accidentally replace the configured renderer with a stale default.
  const getSubjectRender = (element, type) => {
    const render = parseJson(element?.getAttribute('data-subject-render'), {})
    return render && typeof render === 'object' && !Array.isArray(render) && Object.keys(render).length
      ? render
      : subjectToolDefaultRenderHint(type)
  }
  const getSubjectRenderHint = (element, type) => {
    const hint = parseJson(element?.getAttribute('data-subject-render-hint'), {})
    if (hint && typeof hint === 'object' && !Array.isArray(hint) && Object.keys(hint).length) return hint
    return getSubjectRender(element, type)
  }
  const applySubjectStyleToElement = (element, style) => {
    if (!element || !style || typeof style !== 'object' || Array.isArray(style)) return
    const setLength = (property, value) => {
      if (value === undefined || value === null || value === '') return
      element.style[property] = typeof value === 'number' ? `${value}px` : String(value)
    }
    if (style.color !== undefined) {
      element.style.color = String(style.color)
      element.style.setProperty('--widget-color', String(style.color))
    }
    if (style.backgroundColor !== undefined || style.fillColor !== undefined) {
      const background = style.backgroundColor ?? style.fillColor
      element.style.backgroundColor = String(background)
      element.style.setProperty('--widget-background', String(background))
    }
    if (style.borderColor !== undefined) {
      element.style.borderColor = String(style.borderColor)
      element.style.setProperty('--widget-border-color', String(style.borderColor))
    }
    if (style.borderWidth !== undefined) {
      setLength('borderWidth', style.borderWidth)
      element.style.setProperty('--widget-border-width', typeof style.borderWidth === 'number' ? `${style.borderWidth}px` : String(style.borderWidth))
    }
    if (style.borderRadius !== undefined) {
      setLength('borderRadius', style.borderRadius)
      element.style.setProperty('--widget-border-radius', typeof style.borderRadius === 'number' ? `${style.borderRadius}px` : String(style.borderRadius))
    }
    if (style.opacity !== undefined) {
      const opacity = Number(style.opacity)
      if (Number.isFinite(opacity)) element.style.opacity = String(opacity > 1 ? opacity / 100 : opacity)
    }
    if (style.fontSize !== undefined) setLength('fontSize', style.fontSize)
    if (style.fontWeight !== undefined) element.style.fontWeight = String(style.fontWeight)
    if (style.textAlign !== undefined) element.style.textAlign = String(style.textAlign)
    if (style.lineHeight !== undefined) element.style.lineHeight = String(style.lineHeight)
  }
  const renderHtmlSubjectTool = (element, { subjectType, data, title, renderHint, render, style } = {}) => {
    if (!element) return
    if (!document.getElementById('a12-subject-tool-runtime-style')) {
      const runtimeStyle = document.createElement('style')
      runtimeStyle.id = 'a12-subject-tool-runtime-style'
      runtimeStyle.textContent = subjectToolRuntimeCss
      document.head.appendChild(runtimeStyle)
    }
    const rawType = subjectType || element.getAttribute('data-subject-type') || 'geometry'
    const normalizedType = normalizeSubjectToolType(rawType)
    const normalizedData = normalizeSubjectToolData(data === undefined ? getSubjectData(element) : data, rawType)
    const normalizedHint = renderHint && typeof renderHint === 'object' && !Array.isArray(renderHint) && Object.keys(renderHint).length
      ? renderHint
      : getSubjectRenderHint(element, normalizedType)
    const normalizedRender = render && typeof render === 'object' && !Array.isArray(render)
      ? render
      : getSubjectRender(element, normalizedType)
    const currentTitle = title ?? element.getAttribute('data-name') ?? element.getAttribute('title')
      ?? element.querySelector?.('[data-a12-subject-title]')?.textContent ?? '学科探究工具'

    element.classList.add('a12-subject-tool')
    element.setAttribute('data-ppt-type', 'subject')
    element.setAttribute('data-subject-type', normalizedType)
    element.setAttribute('data-subject-data', JSON.stringify(normalizedData))
    element.setAttribute('data-subject-render', JSON.stringify(normalizedRender || {}))
    element.setAttribute('data-subject-render-hint', JSON.stringify(normalizedHint || subjectToolDefaultRenderHint(normalizedType)))
    if (style && typeof style === 'object' && !Array.isArray(style)) {
      element.setAttribute('data-subject-style', JSON.stringify(style))
      applySubjectStyleToElement(element, style)
    }
    element.setAttribute('data-name', String(currentTitle || '学科探究工具').slice(0, 80))
    element.setAttribute('title', String(currentTitle || '学科探究工具').slice(0, 80))
    element.style.boxSizing = 'border-box'
    element.style.overflow = 'hidden'
    element.innerHTML = subjectToolMarkup({
      subjectType: normalizedType,
      data: normalizedData,
      title: currentTitle,
      renderHint: normalizedHint,
    })
  }

  let selected = null
  let interaction = null
  let editing = null

  const isCurrentSlide = () => current.value === slide
  const elementKey = (element, index = 0) => {
    const explicit = element.getAttribute('data-ppt-element') || element.id
    return explicit ? `explicit:${explicit}` : `index:${index}:${element.tagName.toLowerCase()}`
  }
  const elementType = (element) => {
    const explicit = String(element.getAttribute('data-ppt-type') || element.getAttribute('data-element-type') || '').trim().toLowerCase().replace(/[\s-]+/g, '_')
    const inferred = htmlTypeAliases[explicit] || explicit
    if (element.hasAttribute('data-a12-chart') || element.classList.contains('a12-html-chart')) return 'chart'
    if (['text', 'formula', 'image', 'shape', 'chart', 'table', 'audio', 'video', 'h5', 'subject'].includes(inferred)) return inferred
    const tag = element.tagName.toLowerCase()
    if (tag === 'img' || tag === 'picture') return 'image'
    if (tag === 'table') return 'table'
    if (tag === 'svg' || tag === 'canvas') return 'shape'
    if (htmlTextTags.has(tag)) return 'text'
    return 'shape'
  }
  const isCandidate = (element) => {
    if (!element || element === document.body || element.classList?.contains('slide') || ['HTML', 'HEAD', 'SCRIPT', 'STYLE', 'META', 'LINK', 'TITLE'].includes(element.tagName)) return false
    if (element.hasAttribute?.('data-a12-chart-part')) return false
    if (element.closest?.('.a12-html-editor-overlay, .a12-html-element-proxy')) return false
    // 学科工具作为一个整体参与选择，内部公式、表格和 SVG 不单独列出。
    if (element.parentElement?.closest?.('[data-ppt-type="subject"],.a12-subject-tool')) return false
    // H5 的内层 iframe 只是固定 1280x720 的渲染面，选择、移动和缩放只作用于外层宿主。
    const h5Owner = element.parentElement?.closest?.('[data-ppt-type="h5"],[data-a12-h5-host]')
    if (h5Owner && h5Owner !== element) return false
    // 表格内部的 <table>/<td> 只是表格容器的内容，不应再次出现在元素列表中。
    const tableOwner = element.parentElement?.closest?.('[data-ppt-type="table"],[data-a12-table-data],.table-widget')
    if (tableOwner && tableOwner !== element && !element.hasAttribute?.('data-ppt-element')) return false
    const rect = element.getBoundingClientRect()
    return rect.width > 6 && rect.height > 6
  }
  const collectCandidates = () => {
    // 结构化页面的编辑投影给每个根元素打上 data-ppt-element，避免把公式、图表
    // 等内部装饰节点再次识别成独立元素；HTML PPT 原有的宽松候选规则保持不变。
    if (structuredMode && document.querySelector('[data-a12-structured-element]')) {
      return [...document.querySelectorAll('[data-ppt-element]')].filter(isCandidate)
    }
    return [...document.querySelectorAll(htmlDragTargetSelector)].filter(isCandidate)
  }
  const panelText = (element, type) => {
    if (type === 'image') return String(element.getAttribute('alt') || '').trim().slice(0, 160)
    if (['audio', 'video', 'h5', 'subject', 'table'].includes(type)) return String(element.getAttribute('data-name') || element.getAttribute('title') || element.innerText || element.textContent || `${type} 组件`).replace(/\s+/g, ' ').trim().slice(0, 160)
    if (type === 'chart') return String(element.querySelector('[data-a12-chart-title]')?.textContent || element.getAttribute('data-a12-chart-title') || element.textContent || '数据图表').replace(/\s+/g, ' ').trim().slice(0, 160)
    return String(element.innerText || element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160)
  }
  const panelName = (element, type, index) => {
    const explicit = element.getAttribute('data-name') || element.getAttribute('aria-label') || element.getAttribute('title')
    const text = panelText(element, type)
    return String(explicit || text || `${element.tagName.toUpperCase()} 元素 ${index + 1}`).slice(0, 24)
  }
  const panelElement = (element, index, id, key) => {
    const computed = frameWindow.getComputedStyle(element)
    const rect = element.getBoundingClientRect()
    const type = elementType(element)
    const moduleId = type === 'h5' ? String(element.getAttribute('data-module-id') || '') : ''
    const linkedInteractiveAsset = type === 'h5'
      ? (Array.isArray(current.value?.interactive_assets || current.value?.interactiveAssets)
          ? (current.value.interactive_assets || current.value.interactiveAssets).find((asset) => String(asset?.module_id || asset?.moduleId || '') === moduleId)
          : null)
      : null
    const linkedMetadata = linkedInteractiveAsset?.metadata && typeof linkedInteractiveAsset.metadata === 'object' && !Array.isArray(linkedInteractiveAsset.metadata) ? linkedInteractiveAsset.metadata : {}
    const attributeModuleType = type === 'h5' ? normalizeInteractiveModuleType(element.getAttribute('data-module-type')) : 'unknown'
    const linkedModuleType = type === 'h5' ? normalizeInteractiveModuleType(linkedInteractiveAsset?.module_type || linkedInteractiveAsset?.moduleType || linkedMetadata.module_type) : 'unknown'
    const moduleType = type === 'h5' ? (attributeModuleType === 'unknown' ? linkedModuleType : attributeModuleType) : undefined
    const moduleTypeRaw = type === 'h5' ? String(element.getAttribute('data-module-type-raw') || linkedInteractiveAsset?.module_type_raw || element.getAttribute('data-module-type') || linkedInteractiveAsset?.module_type || '') : undefined
    const fontSize = Number.parseFloat(computed.fontSize) || 16
    const lineHeight = computed.lineHeight === 'normal' ? 1.5 : (Number.parseFloat(computed.lineHeight) || fontSize) / fontSize
    const width = Math.max(1, HTML_CANVAS_WIDTH)
    const height = Math.max(1, HTML_CANVAS_HEIGHT)
    const x = ((rect.left + frameWindow.scrollX) / width) * 100
    const y = ((rect.top + frameWindow.scrollY) / height) * 100
    return {
      id,
      type,
      name: panelName(element, type, index),
      content: panelText(element, type),
      src: ['image', 'audio', 'video'].includes(type) ? String(element.currentSrc || element.getAttribute('src') || '') : undefined,
      alt: type === 'image' ? String(element.getAttribute('alt') || '') : undefined,
      url: ['audio', 'video'].includes(type) ? String(element.currentSrc || element.getAttribute('src') || '') : undefined,
      html: type === 'h5' ? String(h5FrameForElement(element)?.getAttribute('srcdoc') || h5FrameForElement(element)?.srcdoc || '') : undefined,
      h5Config: type === 'h5' ? parseJson(element.getAttribute('data-h5-config'), {}) : undefined,
      h5_config: type === 'h5' ? parseJson(element.getAttribute('data-h5-config'), {}) : undefined,
      resourceId: String(element.getAttribute('data-resource-id') || ''),
      resource_id: String(element.getAttribute('data-resource-id') || ''),
      resourceName: String(element.getAttribute('data-resource-name') || ''),
      resourceType: String(element.getAttribute('data-resource-type') || ''),
      moduleId: type === 'h5' ? moduleId : undefined,
      module_id: type === 'h5' ? moduleId : undefined,
      moduleType: moduleType,
      module_type: moduleType,
      module_type_raw: moduleTypeRaw || (type === 'h5' ? 'unknown' : undefined),
      topic: type === 'h5' ? String(element.getAttribute('data-h5-topic') || linkedInteractiveAsset?.topic || linkedMetadata.topic || '') : undefined,
      usageSuggestions: type === 'h5' ? (Array.isArray(parseJson(element.getAttribute('data-h5-usage-suggestions'), linkedInteractiveAsset?.usage_suggestions || linkedInteractiveAsset?.usageSuggestions || [])) ? parseJson(element.getAttribute('data-h5-usage-suggestions'), linkedInteractiveAsset?.usage_suggestions || linkedInteractiveAsset?.usageSuggestions || []) : []) : undefined,
      usage_suggestions: type === 'h5' ? (Array.isArray(parseJson(element.getAttribute('data-h5-usage-suggestions'), linkedInteractiveAsset?.usage_suggestions || linkedInteractiveAsset?.usageSuggestions || [])) ? parseJson(element.getAttribute('data-h5-usage-suggestions'), linkedInteractiveAsset?.usage_suggestions || linkedInteractiveAsset?.usageSuggestions || []) : []) : undefined,
      metadata: type === 'h5' ? { ...linkedMetadata, ...parseJson(element.getAttribute('data-h5-metadata'), {}) } : undefined,
      generatedBy: type === 'h5' ? String(element.getAttribute('data-h5-generated') || '') : undefined,
      generated_by: type === 'h5' ? String(element.getAttribute('data-h5-generated') || '') : undefined,
      embedMode: type === 'h5' ? String(element.getAttribute('data-embed-mode') || 'standalone') : undefined,
      subjectType: type === 'subject' ? String(element.getAttribute('data-subject-type') || 'general') : undefined,
      render: type === 'subject' ? parseJson(element.getAttribute('data-subject-render'), {}) : undefined,
      subjectStyle: type === 'subject' ? parseJson(element.getAttribute('data-subject-style'), {}) : undefined,
      subjectRender: type === 'subject' ? getSubjectRenderHint(element, element.getAttribute('data-subject-type')) : undefined,
      subjectRenderHint: type === 'subject' ? parseJson(element.getAttribute('data-subject-render-hint'), null) : undefined,
      subjectValidation: type === 'subject' ? parseJson(element.getAttribute('data-subject-validation'), null) : undefined,
      autoplay: ['audio', 'video'].includes(type) ? Boolean(element.autoplay) : undefined,
      controls: ['audio', 'video'].includes(type) ? element.controls !== false : undefined,
      htmlTag: element.tagName.toLowerCase(),
      htmlKey: key,
      target: String(element.getAttribute('data-ppt-target') || '').trim() || undefined,
      shapeKind: String(element.getAttribute('data-shape-kind') || '').trim() || undefined,
      position: {
        // 移动允许元素部分离开画布；这里不能把负坐标截回 0，
        // 否则结构化页面在拖动结束后会再次跳回边缘。
        x: Number((Number.isFinite(x) ? x : 0).toFixed(2)),
        y: Number((Number.isFinite(y) ? y : 0).toFixed(2)),
        width: Number(Math.max(1, (rect.width / width) * 100).toFixed(2)),
        height: Number(Math.max(1, (rect.height / height) * 100).toFixed(2)),
        rotation: Number(parseCssRotation(computed.rotate && computed.rotate !== 'none' ? computed.rotate : computed.transform).toFixed(2)),
        zIndex: Number.parseInt(computed.zIndex, 10) || 0,
      },
      style: {
        color: htmlColorToHex(computed.color, '#102d54'),
        fontSize: Math.round(fontSize),
        fontWeight: Number(computed.fontWeight) || 400,
        textAlign: computed.textAlign || 'left',
        lineHeight: Number(lineHeight.toFixed(2)),
        fillColor: htmlColorToHex(computed.backgroundColor, '#eff6ff'),
        backgroundColor: htmlColorToHex(computed.backgroundColor, '#eff6ff'),
        borderColor: htmlColorToHex(computed.borderColor, '#bfdbfe'),
        borderWidth: Number.parseFloat(computed.borderWidth) || 0,
        borderRadius: Number.parseFloat(computed.borderRadius) || 0,
        opacity: Math.round((Number.parseFloat(computed.opacity) || 1) * 100),
        objectFit: computed.objectFit || 'cover',
        showCaption: true,
      },
      data: type === 'chart' ? getChartData(element) : type === 'table' ? getTableData(element) : type === 'subject' ? parseJson(element.getAttribute('data-subject-data'), {}) : undefined,
    }
  }
  const updateGlobalSelection = () => {
    if (!isCurrentSlide()) return
    if (!selected?.isConnected) {
      htmlSelectedElementId.value = null
      htmlSelectedElement.value = null
      return
    }
    const id = elementPanelId.get(selected)
    const index = htmlElements.value.findIndex((item) => item.id === id)
    if (!id || index < 0) return
    htmlSelectedElementId.value = id
    htmlSelectedElement.value = panelElement(selected, index, id, elementPanelKey.get(selected) || '')
  }
  const refreshElements = () => {
    const candidates = collectCandidates()
    panelElementById.clear()
    const usedIds = new Set()
    const nextElements = candidates.map((element, index) => {
      const type = elementType(element)
      if (type === 'chart' && !element.querySelector('[data-a12-chart-title]')) renderHtmlChart(element)
      if (type === 'subject' && !element.querySelector('.a12-subject-tool__header')) renderHtmlSubjectTool(element)
      const preferredId = element.getAttribute('data-ppt-element') || element.id || `html-${index + 1}`
      let id = preferredId
      let suffix = 2
      while (usedIds.has(id)) id = `${preferredId}-${suffix++}`
      usedIds.add(id)
      const key = elementKey(element, index)
      elementPanelId.set(element, id)
      elementPanelKey.set(element, key)
      panelElementById.set(id, element)
      return panelElement(element, index, id, key)
    })
    htmlElements.value = nextElements
    syncH5ElementProxies(candidates)
    const restoreKey = htmlSelectionRestoreKey.value
    const restored = restoreKey ? candidates.find((element, index) => elementKey(element, index) === restoreKey) : null
    if (restored) select(restored)
    else updateGlobalSelection()
    return nextElements
  }
  const updateOverlay = () => {
    if (!selected?.isConnected) {
      overlay.classList.remove('is-visible')
      overlay.classList.remove('is-h5')
      overlay.classList.remove('is-toolbar-left', 'is-toolbar-bottom')
      updateGlobalSelection()
      return
    }
    const rect = selected.getBoundingClientRect()
    overlay.style.left = `${rect.left}px`
    overlay.style.top = `${rect.top}px`
    overlay.style.width = `${rect.width}px`
    overlay.style.height = `${rect.height}px`
    overlay.classList.toggle('is-h5', elementType(selected) === 'h5')
    overlay.classList.add('is-visible')
    // 操作条贴在旋转圆点的右侧；靠近画布边缘时自动切到圆点左侧。
    overlay.classList.remove('is-toolbar-left', 'is-toolbar-bottom')
    const toolbarRect = editorToolbar?.getBoundingClientRect?.()
    const viewportWidth = document.documentElement?.clientWidth || frameWindow.innerWidth || 0
    const viewportHeight = document.documentElement?.clientHeight || frameWindow.innerHeight || 0
    const rotateCenterX = rect.left + rect.width / 2
    if (toolbarRect && viewportWidth && rotateCenterX + 20 + toolbarRect.width > viewportWidth - 8 && rotateCenterX - 20 - toolbarRect.width >= 8) {
      overlay.classList.add('is-toolbar-left')
    }
    if (toolbarRect && viewportHeight && rect.top - 40 < 8 && rect.bottom + toolbarRect.height <= viewportHeight - 8) {
      overlay.classList.add('is-toolbar-bottom')
    }
    syncH5ElementProxies()
    updateGlobalSelection()
  }
  const clearSelection = ({ preserveRestoreKey = false } = {}) => {
    selected?.removeAttribute('data-a12-drag-selected')
    selected = null
    overlay.classList.remove('is-visible')
    overlay.classList.remove('is-toolbar-left', 'is-toolbar-bottom')
    if (!preserveRestoreKey) htmlSelectionRestoreKey.value = ''
    if (isCurrentSlide()) {
      htmlSelectedElementId.value = null
      htmlSelectedElement.value = null
    }
  }
  const select = (element) => {
    if (!element || !isCandidate(element)) return
    if (selected !== element) {
      selected?.removeAttribute('data-a12-drag-selected')
      selected = element
      selected.setAttribute('data-a12-drag-selected', '')
    }
    htmlSelectionRestoreKey.value = elementPanelKey.get(element) || ''
    updateOverlay()
  }
  // 拖动时以画布坐标计算位置，避免元素被 iframe 的可视区域或内部内容
  // 误判成“边界”。移动只改变 translate，永远不修改元素尺寸。
  const canvasRect = () => {
    const canvas = document.querySelector('.slide') || document.body
    const rect = canvas?.getBoundingClientRect?.()
    if (!rect || !rect.width || !rect.height) {
      return { left: 0, top: 0, right: HTML_CANVAS_WIDTH, bottom: HTML_CANVAS_HEIGHT }
    }
    return {
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
    }
  }
  const resizeKeepsAspectRatio = (element) => ['image', 'video', 'h5'].includes(elementType(element))
  const clampResizeSize = (activeInteraction, deltaX, deltaY) => {
    const minSize = 20
    let nextWidth = Math.max(minSize, activeInteraction.originWidth + deltaX)
    let nextHeight = Math.max(minSize, activeInteraction.originHeight + deltaY)
    if (resizeKeepsAspectRatio(activeInteraction.element)) {
      const ratio = activeInteraction.originWidth > 0 && activeInteraction.originHeight > 0
        ? activeInteraction.originWidth / activeInteraction.originHeight
        : 1
      const widthFromHeight = nextHeight * ratio
      nextWidth = Math.abs(deltaX) >= Math.abs(deltaY * ratio) ? nextWidth : widthFromHeight
      nextWidth = Math.max(minSize, nextWidth)
      nextHeight = Math.max(minSize, nextWidth / ratio)
    }
    return { width: Number(nextWidth.toFixed(2)), height: Number(nextHeight.toFixed(2)) }
  }
  const resolveTarget = (target) => {
    if (!(target instanceof frameWindow.Element)) return null
    const subjectOwner = target.closest('[data-ppt-type="subject"],.a12-subject-tool')
    if (subjectOwner) return subjectOwner
    if (structuredMode) {
      const structuredTarget = target.closest?.('[data-ppt-element]')
      if (structuredTarget && structuredTarget !== document.body) return structuredTarget
    }
    const chartPart = target.closest?.('[data-a12-chart-part]')
    if (chartPart) {
      const chart = chartPart.closest?.('[data-a12-chart]')
      if (chart) return chart
    }
    // 点击表格内任意单元格时都选择表格容器，而不是内部的 <table>/<td>。
    const tableOwner = target.closest?.('[data-ppt-type="table"],[data-a12-table-data],.table-widget')
    if (tableOwner && tableOwner !== document.body) return tableOwner
    const svg = target.closest('svg')
    const direct = svg || target.closest(htmlDragTargetSelector)
    if (direct && direct !== document.body && !direct.classList.contains('slide')) return direct

    let candidate = target
    while (candidate && candidate !== document.body) {
      if (candidate.classList?.contains('slide')) return null
      const rect = candidate.getBoundingClientRect()
      const coversCanvas = rect.width >= frameWindow.innerWidth * 0.92 && rect.height >= frameWindow.innerHeight * 0.92
      if (!coversCanvas && rect.width > 8 && rect.height > 8) return candidate
      candidate = candidate.parentElement
    }
    return null
  }
  const commitDocument = () => {
    if (selected?.isConnected) htmlSelectionRestoreKey.value = elementPanelKey.get(selected) || ''
    const serialized = serializeHtmlSlide(document)
    const nextElements = onCommit ? refreshElements() : null
    const changed = onCommit
      ? Boolean(onCommit({ slide, html: serialized, document, elements: nextElements || [] }))
      : applyHtmlSlideChange(slide, serialized, { refreshFrame: false })
    if (!changed) updateGlobalSelection()
    return changed
  }
  const applyInteractionFrame = (activeInteraction) => {
    activeInteraction.animationFrame = 0
    if (activeInteraction.type === 'move') activeInteraction.element.style.translate = `${activeInteraction.nextX}px ${activeInteraction.nextY}px`
    if (activeInteraction.type === 'resize') {
      activeInteraction.element.style.boxSizing = 'border-box'
      activeInteraction.element.style.maxWidth = 'none'
      activeInteraction.element.style.maxHeight = 'none'
      activeInteraction.element.style.width = `${activeInteraction.nextWidth}px`
      activeInteraction.element.style.height = `${activeInteraction.nextHeight}px`
      activeInteraction.element.style.flex = 'none'
      if (elementType(activeInteraction.element) === 'h5') layoutH5Element(activeInteraction.element)
    }
    if (activeInteraction.type === 'rotate') activeInteraction.element.style.rotate = `${activeInteraction.nextRotation}deg`
    updateOverlay()
  }
  const scheduleInteractionFrame = () => {
    if (!interaction || interaction.animationFrame) return
    const activeInteraction = interaction
    interaction.animationFrame = frameWindow.requestAnimationFrame(() => applyInteractionFrame(activeInteraction))
  }
  const finishInteraction = () => {
    if (!interaction) return
    const completed = interaction
    interaction = null
    if (completed.animationFrame) frameWindow.cancelAnimationFrame(completed.animationFrame)
    applyInteractionFrame(completed)
    const captureTarget = completed.captureTarget || completed.element
    if (captureTarget.hasPointerCapture?.(completed.pointerId)) captureTarget.releasePointerCapture(completed.pointerId)
    sendH5ElementEditing(completed.element, false)
    if (completed.pointerEvents !== null && completed.pointerEvents !== undefined) completed.element.style.pointerEvents = completed.pointerEvents
    if (!completed.moved || !isCurrentSlide()) return
    commitDocument()
  }
  const handlePointerMove = (event) => {
    if (!interaction || event.pointerId !== interaction.pointerId) return
    const deltaX = event.clientX - interaction.startX
    const deltaY = event.clientY - interaction.startY
    interaction.moved ||= Math.hypot(deltaX, deltaY) >= 2
    if (!interaction.moved) return
    if (interaction.type === 'move') {
      // 移动不做画布边界裁剪，允许元素部分移出画布；只更新 translate，
      // 因此拖动不会改变元素自身的宽高。
      interaction.nextX = Number((interaction.originTranslate.x + deltaX).toFixed(2))
      interaction.nextY = Number((interaction.originTranslate.y + deltaY).toFixed(2))
    }
    if (interaction.type === 'resize') {
      const nextSize = clampResizeSize(interaction, deltaX, deltaY)
      interaction.nextWidth = nextSize.width
      interaction.nextHeight = nextSize.height
    }
    if (interaction.type === 'rotate') {
      const angle = Math.atan2(event.clientY - interaction.centerY, event.clientX - interaction.centerX) * 180 / Math.PI
      interaction.nextRotation = Number((interaction.originRotation + angle - interaction.startAngle).toFixed(2))
    }
    scheduleInteractionFrame()
    event.preventDefault()
  }
  const handlePointerDown = (event) => {
    if (event.button !== 0) return
    if (event.target.closest?.('[data-subject-point]')) return
    if (event.target.closest?.('.a12-html-editor-overlay')) return
    if (event.target.closest?.('[data-a12-html-editing]')) return
    if (shouldCommitLandPptInlineEdit(editing?.element, event.target)) finishTextEditing(true)
    const element = resolveTarget(event.target)
    if (!element) {
      clearSelection()
      return
    }
    select(element)
    const origin = parseCssTranslate(frameWindow.getComputedStyle(element).translate)
    const pointerEvents = elementType(element) === 'h5' ? element.style.pointerEvents : null
    if (pointerEvents !== null) element.style.pointerEvents = 'none'
    sendH5ElementEditing(element, true)
    interaction = {
      type: 'move',
      element,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originTranslate: origin,
      pointerEvents,
      nextX: origin.x,
      nextY: origin.y,
      animationFrame: 0,
      moved: false,
    }
    element.setPointerCapture?.(event.pointerId)
    event.preventDefault()
  }
  const beginMoveInteraction = (event) => {
    if (!selected || event.button !== 0) return
    const computed = frameWindow.getComputedStyle(selected)
    const origin = parseCssTranslate(computed.translate)
    const pointerEvents = elementType(selected) === 'h5' ? selected.style.pointerEvents : null
    if (pointerEvents !== null) selected.style.pointerEvents = 'none'
    sendH5ElementEditing(selected, true)
    interaction = {
      type: 'move',
      element: selected,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originTranslate: origin,
      pointerEvents,
      nextX: origin.x,
      nextY: origin.y,
      animationFrame: 0,
      moved: false,
      captureTarget: event.currentTarget,
    }
    event.currentTarget.setPointerCapture?.(event.pointerId)
    event.preventDefault()
    event.stopPropagation()
  }
  const syncH5ElementProxies = (candidates = collectCandidates()) => {
    const h5Elements = candidates.filter((element) => elementType(element) === 'h5' && element.isConnected)
    const activeElements = new Set(h5Elements)
    for (const [element, proxy] of h5ElementProxies) {
      if (activeElements.has(element)) continue
      proxy.remove()
      h5ElementProxies.delete(element)
    }
    for (const [element, state] of h5ElementViewportObservers) {
      if (activeElements.has(element)) continue
      state.observer?.disconnect?.()
      if (state.loadListener) state.frame?.removeEventListener('load', state.loadListener)
      h5ElementViewportObservers.delete(element)
    }
    h5Elements.forEach((element) => {
      observeH5ElementViewport(element)
      let proxy = h5ElementProxies.get(element)
      if (!proxy) {
        proxy = document.createElement('div')
        proxy.className = 'a12-html-element-proxy'
        proxy.setAttribute('role', 'button')
        proxy.setAttribute('aria-label', '选择 H5 元素')
        proxy.title = '点击选择 H5，拖动可移动'
        proxy.addEventListener('pointerdown', (event) => {
          if (event.button !== 0 || !element.isConnected) return
          select(element)
          beginMoveInteraction(event)
        })
        document.body.appendChild(proxy)
        h5ElementProxies.set(element, proxy)
      }
      const rect = element.getBoundingClientRect()
      proxy.style.left = `${rect.left}px`
      proxy.style.top = `${rect.top}px`
      proxy.style.width = `${rect.width}px`
      proxy.style.height = `${rect.height}px`
      proxy.style.visibility = rect.width > 6 && rect.height > 6 ? 'visible' : 'hidden'
    })
  }
  const beginHandleInteraction = (type, event) => {
    if (!selected || event.button !== 0) return
    const rect = selected.getBoundingClientRect()
    const computed = frameWindow.getComputedStyle(selected)
    const pointerEvents = elementType(selected) === 'h5' ? selected.style.pointerEvents : null
    if (pointerEvents !== null) selected.style.pointerEvents = 'none'
    sendH5ElementEditing(selected, true)
    const startAngle = Math.atan2(event.clientY - (rect.top + rect.height / 2), event.clientX - (rect.left + rect.width / 2)) * 180 / Math.PI
    interaction = {
      type,
      element: selected,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originWidth: rect.width,
      originHeight: rect.height,
      originRect: rect,
      canvasBounds: canvasRect(),
      pointerEvents,
      nextWidth: rect.width,
      nextHeight: rect.height,
      centerX: rect.left + rect.width / 2,
      centerY: rect.top + rect.height / 2,
      startAngle,
      originRotation: parseCssRotation(computed.rotate),
      nextRotation: parseCssRotation(computed.rotate),
      animationFrame: 0,
      moved: false,
      captureTarget: event.currentTarget,
    }
    event.currentTarget.setPointerCapture?.(event.pointerId)
    event.preventDefault()
    event.stopPropagation()
  }
  const finishTextEditing = (commit = true) => {
    if (!editing) return
    const { element, originalHtml } = editing
    editing = null
    element.removeAttribute('contenteditable')
    element.removeAttribute('spellcheck')
    element.removeAttribute('data-a12-html-editing')
    if (!commit) element.innerHTML = originalHtml
    if (commit && element.innerHTML !== originalHtml) commitDocument()
    else updateOverlay()
  }
  const handleDoubleClick = (event) => {
    const subjectOwner = event.target.closest?.('[data-ppt-type="subject"],.a12-subject-tool')
    if (subjectOwner) { select(subjectOwner); return }
    const textElement = event.target.closest?.(htmlTextTargetSelector)
    if (!textElement || textElement.closest('.a12-html-editor-overlay') || !canLandPptDirectEdit(textElement)) return
    const element = structuredMode ? textElement.closest?.('[data-ppt-element]') || textElement : textElement
    if (!element || element.closest('.a12-html-editor-overlay')) return
    // 结构化页面需要选中外层元素来完成拖动和属性同步，但编辑时只修改实际的文字节点。
    // 工具栏新增的文本元素本身就是 div[data-ppt-type="text"]，此时两者是同一个节点。
    const editableElement = structuredMode && element !== textElement ? textElement : element
    select(element)
    editing = { element: editableElement, originalHtml: editableElement.innerHTML }
    editableElement.setAttribute('contenteditable', 'true')
    editableElement.setAttribute('spellcheck', 'false')
    editableElement.setAttribute('data-a12-html-editing', '')
    editableElement.focus()
    placeLandPptCaret(editableElement, event)
    event.preventDefault()
    event.stopPropagation()
  }
  const deleteSelected = () => {
    if (!selected) return
    selected.remove()
    clearSelection()
    refreshElements()
    commitDocument()
  }
  const cloneSelectedForClipboard = () => {
    if (!selected) return
    const clone = selected.cloneNode(true)
    clone.removeAttribute('data-a12-drag-selected')
    clone.removeAttribute('data-a12-html-editing')
    clone.removeAttribute('contenteditable')
    clone.removeAttribute('spellcheck')
    clone.removeAttribute('id')
    return clone
  }
  const copySelectedToClipboard = () => {
    const clone = cloneSelectedForClipboard()
    if (!clone) return false
    workspaceElementClipboard = { kind: 'html', markup: clone.outerHTML }
    return true
  }
  const pasteClipboard = () => {
    if (workspaceElementClipboard?.kind !== 'html' || !workspaceElementClipboard.markup) return false
    const template = document.createElement('template')
    template.innerHTML = workspaceElementClipboard.markup
    const clone = template.content.firstElementChild
    if (!clone) return false
    clone.removeAttribute('data-a12-drag-selected')
    clone.removeAttribute('data-a12-html-editing')
    clone.removeAttribute('contenteditable')
    clone.removeAttribute('spellcheck')
    clone.removeAttribute('id')
    clone.setAttribute('data-ppt-element', `copy-${Date.now()}`)
    const origin = selected?.isConnected
      ? parseCssTranslate(frameWindow.getComputedStyle(selected).translate)
      : parseCssTranslate(clone.style.translate)
    clone.style.translate = `${origin.x + 18}px ${origin.y + 18}px`
    if (selected?.isConnected) selected.after(clone)
    else (document.querySelector('.slide') || document.body).appendChild(clone)
    refreshElements()
    select(clone)
    commitDocument()
    return true
  }
  const copySelected = () => {
    if (!copySelectedToClipboard()) return false
    return pasteClipboard()
  }
  const runHistoryAction = (action) => {
    if (selected?.isConnected) htmlSelectionRestoreKey.value = elementPanelKey.get(selected) || ''
    return action(slide)
  }
  const handleToolbarClick = (event) => {
    const action = event.target.closest('button')?.dataset.action
    if (!action) return
    if (action === 'delete') deleteSelected()
    if (action === 'copy') copySelected()
    if (action === 'undo') runHistoryAction(undoHtmlSlideChange)
    if (action === 'redo') runHistoryAction(redoHtmlSlideChange)
    event.preventDefault()
    event.stopPropagation()
  }
  const handleKeydown = (event) => {
    const modifier = event.ctrlKey || event.metaKey
    if (modifier && event.key.toLowerCase() === 's') {
      event.preventDefault()
      if (editing) finishTextEditing(true)
      void nextTick().then(() => saveWorkspaceNow())
      return
    }
    if (!editing && modifier && event.key.toLowerCase() === 'z') {
      event.preventDefault()
      runHistoryAction((targetSlide) => event.shiftKey ? redoHtmlSlideChange(targetSlide) : undoHtmlSlideChange(targetSlide))
      return
    }
    if (!editing && modifier && event.key.toLowerCase() === 'y') {
      event.preventDefault()
      runHistoryAction(redoHtmlSlideChange)
      return
    }
    if (editing && event.key === 'Escape') {
      event.preventDefault()
      finishTextEditing(false)
      return
    }
    if (editing && event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      finishTextEditing(true)
      return
    }
    if (!editing && modifier && event.key.toLowerCase() === 'c' && selected) {
      event.preventDefault()
      copySelectedToClipboard()
      return
    }
    if (!editing && modifier && event.key.toLowerCase() === 'v') {
      if (pasteClipboard()) event.preventDefault()
      return
    }
    if (!editing && selected && ['Delete', 'Backspace'].includes(event.key)) {
      event.preventDefault()
      deleteSelected()
    }
  }
  const handleDocumentBlur = (event) => {
    if (editing?.element === event.target) finishTextEditing(true)
  }
  const findElement = (id) => panelElementById.get(String(id)) || null
  const setSvgStyle = (element, property, value) => {
    const svg = element.tagName.toLowerCase() === 'svg' ? element : element.closest?.('svg')
    if (!svg) return false
    const targets = element.tagName.toLowerCase() === 'svg' ? [element, ...svg.querySelectorAll('*')] : [element]
    targets.forEach((target) => { target.style[property] = value })
    return true
  }
  const updateStyle = (key, value) => {
    if (!selected?.isConnected) return false
    const numeric = Number(value)
    if (key === 'fontSize') selected.style.fontSize = `${Math.max(10, Math.min(96, Number.isFinite(numeric) ? numeric : 16))}px`
    else if (key === 'fontWeight') selected.style.fontWeight = String(Number.isFinite(numeric) ? numeric : 400)
    else if (key === 'lineHeight') selected.style.lineHeight = String(Number.isFinite(numeric) ? numeric : 1.5)
    else if (key === 'opacity') selected.style.opacity = String(Math.max(0, Math.min(100, Number.isFinite(numeric) ? numeric : 100)) / 100)
    else if (key === 'color') {
      selected.style.color = String(value || '#102d54')
      if (elementType(selected) === 'chart') selected.style.setProperty('--a12-chart-color', String(value || '#2563eb'))
    }
    else if (key === 'textAlign') selected.style.textAlign = String(value || 'left')
    else if (key === 'fillColor') {
      if (!setSvgStyle(selected, 'fill', String(value || '#eff6ff'))) selected.style.backgroundColor = String(value || '#eff6ff')
    } else if (key === 'backgroundColor') selected.style.backgroundColor = String(value || '#eff6ff')
    else if (key === 'borderColor') {
      selected.style.borderColor = String(value || '#bfdbfe')
      setSvgStyle(selected, 'stroke', String(value || '#bfdbfe'))
    } else if (key === 'borderWidth') {
      selected.style.borderWidth = `${Math.max(0, Math.min(12, Number.isFinite(numeric) ? numeric : 0))}px`
      setSvgStyle(selected, 'strokeWidth', String(Math.max(0, Number.isFinite(numeric) ? numeric : 0)))
    } else if (key === 'borderRadius') selected.style.borderRadius = `${Math.max(0, Math.min(80, Number.isFinite(numeric) ? numeric : 0))}px`
    else if (key === 'objectFit') selected.style.objectFit = String(value || 'cover')
    else if (key === 'tintColor') selected.style.setProperty('--a12-tint-color', String(value || '#2563eb'))
    else return false
    if (elementType(selected) === 'subject') {
      const style = parseJson(selected.getAttribute('data-subject-style'), {})
      style[key] = value
      selected.setAttribute('data-subject-style', JSON.stringify(style))
      selected.removeAttribute('data-subject-validation')
    }
    updateOverlay()
    commitDocument()
    return true
  }
  const updatePosition = (key, value) => {
    if (!selected?.isConnected) return false
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) return false
    const rect = selected.getBoundingClientRect()
    const computed = frameWindow.getComputedStyle(selected)
    const translate = parseCssTranslate(computed.translate)
    if (key === 'x') selected.style.translate = `${translate.x + (numeric / 100) * HTML_CANVAS_WIDTH - (rect.left + frameWindow.scrollX)}px ${translate.y}px`
    else if (key === 'y') selected.style.translate = `${translate.x}px ${translate.y + (numeric / 100) * HTML_CANVAS_HEIGHT - (rect.top + frameWindow.scrollY)}px`
    else if (key === 'width') { selected.style.boxSizing = 'border-box'; selected.style.width = `${Math.max(20, (Math.min(100, numeric) / 100) * HTML_CANVAS_WIDTH)}px` }
    else if (key === 'height') { selected.style.boxSizing = 'border-box'; selected.style.height = `${Math.max(20, (Math.min(100, numeric) / 100) * HTML_CANVAS_HEIGHT)}px` }
    else if (key === 'rotation') selected.style.rotate = `${Math.max(-180, Math.min(180, numeric))}deg`
    else if (key === 'zIndex') selected.style.zIndex = String(Math.round(Math.max(0, Math.min(99, numeric))))
    else return false
    updateOverlay()
    commitDocument()
    return true
  }
  const updateContent = (value) => {
    if (!selected?.isConnected) return false
    const content = String(value ?? '')
    const type = elementType(selected)
    if (type === 'image') selected.setAttribute('alt', content)
    else if (type === 'chart') {
      const titleNode = selected.querySelector('[data-a12-chart-title]')
      if (titleNode) {
        selected.setAttribute('data-a12-chart-title', content)
        titleNode.textContent = content || '数据图表'
      } else renderHtmlChart(selected, getChartData(selected), content)
    } else if (['audio', 'video', 'h5', 'subject'].includes(type)) {
      selected.setAttribute('data-name', content)
      selected.setAttribute('title', content)
      if (type === 'subject') renderHtmlSubjectTool(selected, { title: content })
    } else if (type === 'table') {
      selected.setAttribute('data-name', content)
      const tableLabel = selected.querySelector(':scope > strong')
      if (tableLabel) tableLabel.textContent = content || '数据表格'
    }
    else if (type === 'formula') {
      const formulaNode = selected.querySelector('strong')
      if (formulaNode) formulaNode.textContent = content || 'a² + b² = c²'
      else selected.textContent = content
    }
    else selected.textContent = content
    updateOverlay()
    commitDocument()
    return true
  }
  const updateField = (key, value) => {
    if (!selected?.isConnected || !['src', 'alt', 'url', 'subjectType', 'autoplay', 'controls', 'resourceId', 'resourceName', 'resourceType'].includes(key)) return false
    const type = elementType(selected)
    if (key === 'src' && ['image', 'audio', 'video'].includes(type)) selected.setAttribute('src', String(value || ''))
    if (key === 'alt' && type === 'image') selected.setAttribute('alt', String(value || '').slice(0, 80))
    if (key === 'url' && ['audio', 'video'].includes(type)) selected.setAttribute('src', String(value || ''))
    if (key === 'subjectType' && type === 'subject') {
      const rawType = String(value || 'geometry')
      const nextType = normalizeSubjectToolType(rawType)
      const nextData = normalizeSubjectToolData(getSubjectData(selected), rawType)
      selected.removeAttribute('data-subject-validation')
      renderHtmlSubjectTool(selected, { subjectType: nextType, data: nextData, render: subjectToolDefaultRenderHint(nextType), renderHint: subjectToolDefaultRenderHint(nextType) })
    }
    if (key === 'autoplay' && ['audio', 'video'].includes(type)) selected.autoplay = Boolean(value)
    if (key === 'controls' && ['audio', 'video'].includes(type)) selected.controls = Boolean(value)
    if (key === 'resourceId' && ['image', 'audio', 'video'].includes(type)) selected.setAttribute('data-resource-id', String(value || ''))
    if (key === 'resourceName' && ['image', 'audio', 'video'].includes(type)) selected.setAttribute('data-resource-name', String(value || ''))
    if (key === 'resourceType' && ['image', 'audio', 'video'].includes(type)) selected.setAttribute('data-resource-type', String(value || ''))
    updateOverlay()
    commitDocument()
    return true
  }
  const updateRender = (value) => {
    if (!selected?.isConnected || elementType(selected) !== 'subject') return false
    const render = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
    selected.removeAttribute('data-subject-validation')
    renderHtmlSubjectTool(selected, { render, renderHint: Object.keys(render).length ? render : undefined })
    updateOverlay()
    commitDocument()
    return true
  }
  const updateStyleMap = (value) => {
    if (!selected?.isConnected || elementType(selected) !== 'subject') return false
    const style = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
    selected.removeAttribute('data-subject-validation')
    selected.setAttribute('data-subject-style', JSON.stringify(style))
    // Keep the canvas immediately in sync for the style keys understood by
    // the shared element style controls; unknown API style keys remain in the
    // data attribute and round-trip through the page payload.
    const supported = ['color', 'backgroundColor', 'borderColor', 'borderWidth', 'borderRadius', 'opacity', 'fontSize', 'fontWeight', 'textAlign', 'lineHeight']
    supported.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(style, key)) updateStyle(key, style[key])
    })
    updateOverlay()
    commitDocument()
    return true
  }
  const updateH5Config = (value) => {
    if (!selected?.isConnected || elementType(selected) !== 'h5') return false
    return false
  }
  const updateData = (value) => {
    if (!selected?.isConnected) return false
    const type = elementType(selected)
    if (type === 'chart' && Array.isArray(value)) renderHtmlChart(selected, value)
    else if (type === 'table' && Array.isArray(value)) renderHtmlTable(selected, value)
    else if (type === 'subject' && value && typeof value === 'object' && !Array.isArray(value)) {
      const subjectType = normalizeSubjectToolType(selected.getAttribute('data-subject-type'))
      const nextData = normalizeSubjectToolData(value, subjectType)
      selected.removeAttribute('data-subject-validation')
      renderHtmlSubjectTool(selected, { subjectType, data: nextData })
    }
    else return false
    updateOverlay()
    commitDocument()
    return true
  }
  const applySubjectValidation = (result) => {
    if (!selected?.isConnected || elementType(selected) !== 'subject' || !result || typeof result !== 'object') return false
    const normalized = result.normalized && typeof result.normalized === 'object' ? result.normalized : {}
    const rawType = normalized.type || selected.getAttribute('data-subject-type') || 'geometry'
    const nextType = normalizeSubjectToolType(rawType)
    const nextData = normalizeSubjectToolData(normalized.data === undefined ? getSubjectData(selected) : normalized.data, rawType)
    const hint = result.render_hint && typeof result.render_hint === 'object' && !Array.isArray(result.render_hint)
      ? result.render_hint
      : subjectToolDefaultRenderHint(nextType)
    const normalizedRender = normalized.render && typeof normalized.render === 'object' && !Array.isArray(normalized.render)
      ? normalized.render
      : getSubjectRenderHint(selected, nextType)
    const validation = {
      valid: result.valid !== false,
      errors: Array.isArray(result.errors) ? result.errors : [],
      warnings: Array.isArray(result.warnings) ? result.warnings : [],
      normalized: { ...normalized, type: nextType, data: nextData, render: normalizedRender },
      render_hint: hint,
    }
    selected.setAttribute('data-subject-validation', JSON.stringify(validation))
    renderHtmlSubjectTool(selected, {
      subjectType: nextType,
      data: nextData,
      render: normalizedRender,
      renderHint: hint,
      style: normalized.style && typeof normalized.style === 'object' && !Array.isArray(normalized.style)
        ? normalized.style
        : undefined,
    })
    updateOverlay()
    commitDocument()
    return true
  }
  const updatePageField = (key, value) => {
    if (!isCurrentSlide() || !['title', 'description'].includes(key)) return false
    const selector = key === 'title' ? 'h1,h2,h3' : 'p'
    const target = document.querySelector(selector)
    if (!target) return false
    target.textContent = String(value ?? '')
    if (selected === target) updateOverlay()
    commitDocument()
    return true
  }
  const insertElement = (type, options = {}) => {
    if (!isCurrentSlide()) return false
    const index = htmlElements.value.length
    const tagName = { image: 'img', audio: 'audio', video: 'video', table: 'div' }[type] || 'div'
    const h5Parts = type === 'h5' ? createH5Host({
      html: '<!doctype html><html lang="zh-CN"><body style="margin:0;display:grid;place-items:center;height:100vh;font:16px sans-serif;color:#c2410c;background:#fff7ed">请使用工具栏生成 H5 组件</body></html>',
      config: {},
      title: '新增 H5 互动',
    }) : null
    const node = h5Parts?.host || document.createElement(tagName)
    const id = `a12-${type}-${Date.now()}`
    node.setAttribute('data-ppt-element', id)
    node.setAttribute('data-ppt-type', type)
    if (type === 'shape') node.setAttribute('data-shape-kind', String(options.shapeKind || 'rectangle'))
    node.style.position = 'absolute'
    node.style.boxSizing = 'border-box'
    node.style.left = type === 'chart' ? `${62 + (index % 2) * 4}%` : `${10 + (index % 5) * 5}%`
    node.style.top = type === 'chart' ? `${10 + (index % 3) * 6}%` : `${12 + (index % 4) * 7}%`
    node.style.width = type === 'text' ? '28%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : type === 'table' ? '42%' : ['video', 'h5', 'subject'].includes(type) ? '36%' : '30%'
    node.style.height = type === 'text' ? '12%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : type === 'table' ? '20%' : type === 'subject' ? '28%' : ['video', 'h5'].includes(type) ? '24%' : '14%'
    node.style.zIndex = '8'
    node.style.borderRadius = type === 'shape' && options.shapeKind === 'circle' ? '50%' : '12px'
    if (type === 'text') {
      node.textContent = '新增文本，可在右侧编辑'
      node.style.padding = '12px'
      node.style.color = '#102d54'
      node.style.fontSize = '20px'
      node.style.fontWeight = '500'
      node.style.backgroundColor = 'rgb(255 255 255 / 82%)'
    } else if (type === 'image') {
      const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect width="640" height="360" rx="28" fill="#dbeafe"/><circle cx="170" cy="150" r="60" fill="#93c5fd"/><path d="M92 280c44-88 95-98 150-40 34-31 75-35 119 40" fill="none" stroke="#2563eb" stroke-width="18" stroke-linecap="round"/><text x="360" y="214" fill="#173d78" font-size="26" font-family="Arial" font-weight="700">新增图片</text></svg>'
      node.setAttribute('src', `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`)
      node.setAttribute('alt', '新增图片')
      node.style.objectFit = 'cover'
      node.style.border = '1px solid #bfdbfe'
    } else if (type === 'shape') {
      node.setAttribute('aria-label', `${options.shapeKind || 'rectangle'} 形状`)
      node.style.backgroundColor = '#dbeafe'
      node.style.border = '2px solid #2563eb'
      if (options.shapeKind === 'diamond') node.style.transform = 'rotate(45deg)'
    } else if (type === 'chart') {
      node.textContent = '新增图表 · 可在右侧修改标题与数据'
      node.style.padding = '16px'
      node.style.color = '#173d78'
      node.style.backgroundColor = '#eff6ff'
      node.style.border = '1px solid #bfdbfe'
      node.setAttribute('data-a12-chart-data', JSON.stringify([{ label: '一', value: 68 }, { label: '二', value: 82 }, { label: '三', value: 55 }]))
      renderHtmlChart(node, undefined, '新增图表')
    } else if (type === 'audio' || type === 'video') {
      node.setAttribute('data-name', type === 'audio' ? '新增音频讲解' : '新增视频演示')
      node.setAttribute('title', type === 'audio' ? '新增音频讲解' : '新增视频演示')
      node.controls = true
      node.style.padding = '8px'
      node.style.backgroundColor = type === 'audio' ? '#eff6ff' : '#eef2ff'
      node.style.border = '1px solid #bfdbfe'
    } else if (type === 'table') {
      node.setAttribute('data-name', '新增数据表格')
      node.style.color = '#173d78'
      node.setAttribute('data-a12-table-data', JSON.stringify([['列 1', '列 2'], ['内容 1', '内容 2']]))
      renderHtmlTable(node, [['列 1', '列 2'], ['内容 1', '内容 2']])
    } else if (type === 'h5') {
      node.setAttribute('data-name', '新增 H5 互动')
      node.setAttribute('data-embed-mode', 'standalone')
      node.setAttribute('data-h5-config', h5RuntimeConfigAttribute({}))
      node.setAttribute('title', '新增 H5 互动')
      node.setAttribute('data-module-type', 'unknown')
      node.setAttribute('data-h5-generated', 'false')
      node.style.border = '1px solid #fed7aa'
      node.style.borderRadius = '12px'
    } else if (type === 'subject') {
      const subjectType = normalizeSubjectToolType(options.subjectType || 'geometry')
      node.setAttribute('data-name', '新增学科工具')
      node.style.color = '#166534'
      node.style.backgroundColor = '#f0fdf4'
      node.style.border = '1px solid #bbf7d0'
      renderHtmlSubjectTool(node, {
        subjectType,
        data: createSubjectToolData(subjectType),
        title: '新增学科工具',
        render: subjectToolDefaultRenderHint(subjectType),
        renderHint: subjectToolDefaultRenderHint(subjectType),
        style: { color: '#166534', backgroundColor: '#f0fdf4', borderColor: '#bbf7d0', borderWidth: 1, borderRadius: 12, opacity: 100 },
      })
    }
    // 新元素必须与页面内容处于同一定位/堆叠上下文，否则会被整页背景盖住。
    const pageRoot = document.querySelector('.slide') || document.body
    if (frameWindow.getComputedStyle(pageRoot).position === 'static') pageRoot.style.position = 'relative'
    node.style.zIndex = String(Math.max(8, ...[...pageRoot.children].map((child) => Number.parseInt(frameWindow.getComputedStyle(child).zIndex, 10) || 0)) + 1)
    pageRoot.appendChild(node)
    refreshElements()
    select(node)
    commitDocument()
    return true
  }
  const insertInteractive = (module, position = null) => {
    if (!isCurrentSlide() || !module?.html) return false
    const index = htmlElements.value.length
    const { host: node } = createH5Host({
      html: module.html,
      config: module.h5_config || module.h5Config || {},
      title: module.title || 'H5 组件',
    })
    node.setAttribute('data-ppt-element', `a12-h5-${module.module_id || module.moduleId || Date.now()}`)
    node.setAttribute('data-ppt-type', 'h5')
    node.setAttribute('data-name', module.title || 'H5 组件')
    if (module.module_id || module.moduleId) node.setAttribute('data-module-id', String(module.module_id || module.moduleId))
    const rawModuleType = String(module.module_type_raw || module.module_type || module.moduleType || module.metadata?.module_type || '').trim()
    node.setAttribute('data-module-type', normalizeInteractiveModuleType(rawModuleType))
    if (rawModuleType) node.setAttribute('data-module-type-raw', rawModuleType)
    if (module.topic) node.setAttribute('data-h5-topic', String(module.topic))
    node.setAttribute('data-h5-generated', 'api-144')
    if (Array.isArray(module.usage_suggestions || module.usageSuggestions) && (module.usage_suggestions || module.usageSuggestions).length) node.setAttribute('data-h5-usage-suggestions', JSON.stringify(module.usage_suggestions || module.usageSuggestions))
    if (module.metadata && typeof module.metadata === 'object' && !Array.isArray(module.metadata)) node.setAttribute('data-h5-metadata', JSON.stringify(module.metadata))
    node.setAttribute('data-embed-mode', String(module.embed_mode || module.embedMode || 'standalone'))
    node.setAttribute('data-h5-config', h5RuntimeConfigAttribute(module.h5_config || module.h5Config || {}))
    node.setAttribute('title', module.title || 'H5 组件')
    node.style.position = 'absolute'
    node.style.boxSizing = 'border-box'
    node.style.left = `${Number.isFinite(Number(position?.x)) ? Number(position.x) : 8 + (index % 3) * 7}%`
    node.style.top = `${Number.isFinite(Number(position?.y)) ? Number(position.y) : 36 + (index % 2) * 8}%`
    node.style.width = `${Number.isFinite(Number(position?.width)) ? Number(position.width) : 42}%`
    node.style.height = `${Number.isFinite(Number(position?.height)) ? Number(position.height) : 42}%`
    node.style.zIndex = '12'
    node.style.border = '1px solid #fed7aa'
    node.style.borderRadius = '12px'
    const pageRoot = document.querySelector('.slide') || document.body
    if (frameWindow.getComputedStyle(pageRoot).position === 'static') pageRoot.style.position = 'relative'
    node.style.zIndex = String(Math.max(12, ...[...pageRoot.children].map((child) => Number.parseInt(frameWindow.getComputedStyle(child).zIndex, 10) || 0)) + 1)
    pageRoot.appendChild(node)
    refreshElements()
    select(node)
    commitDocument()
    return true
  }

  const cleanupSubjectInteractions = bindSubjectInteractions(document, (owner) => {
    select(owner)
    commitDocument()
    refreshElements()
  })
  document.addEventListener('pointerdown', handlePointerDown)
  document.addEventListener('pointermove', handlePointerMove)
  document.addEventListener('pointerup', finishInteraction)
  document.addEventListener('pointercancel', finishInteraction)
  document.addEventListener('dblclick', handleDoubleClick)
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('blur', handleDocumentBlur, true)
  moveHandle.addEventListener('pointerdown', beginMoveInteraction)
  resizeHandle.addEventListener('pointerdown', (event) => beginHandleInteraction('resize', event))
  rotateHandle.addEventListener('pointerdown', (event) => beginHandleInteraction('rotate', event))
  overlay.querySelector('.a12-html-editor-toolbar').addEventListener('click', handleToolbarClick)
  normalizeLegacyH5Elements()
  refreshElements()

  const controller = {
    selectById: (id) => {
      const element = findElement(id)
      if (!element) return false
      select(element)
      element.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
      return true
    },
    clearSelection,
    updateStyle,
    updatePosition,
    updateContent,
    updateField,
    updateRender,
    updateStyleMap,
    updateH5Config,
    updateData,
    applySubjectValidation,
    updatePageField,
    insertElement,
    insertInteractive,
    copySelected: (id) => { const element = findElement(id); if (element) { select(element); copySelected() } },
    copyToClipboard: (id) => { const element = findElement(id); if (element) { select(element); return copySelectedToClipboard() } return false },
    pasteFromClipboard: pasteClipboard,
    deleteSelected: (id) => { const element = findElement(id); if (element) { select(element); deleteSelected() } },
  }
  const cleanup = () => {
    if (editing) finishTextEditing(true)
    cleanupSubjectInteractions()
    document.removeEventListener('pointerdown', handlePointerDown)
    document.removeEventListener('pointermove', handlePointerMove)
    document.removeEventListener('pointerup', finishInteraction)
    document.removeEventListener('pointercancel', finishInteraction)
    document.removeEventListener('dblclick', handleDoubleClick)
    document.removeEventListener('keydown', handleKeydown)
    document.removeEventListener('blur', handleDocumentBlur, true)
    moveHandle.removeEventListener('pointerdown', beginMoveInteraction)
    if (interaction?.animationFrame) frameWindow.cancelAnimationFrame(interaction.animationFrame)
    if (interaction) {
      sendH5ElementEditing(interaction.element, false)
      if (interaction.pointerEvents !== null && interaction.pointerEvents !== undefined) interaction.element.style.pointerEvents = interaction.pointerEvents
    }
    selected?.removeAttribute('data-a12-drag-selected')
    h5ElementProxies.forEach((proxy) => proxy.remove())
    h5ElementProxies.clear()
    h5ElementViewportObservers.forEach((state, element) => {
      state.observer?.disconnect?.()
      if (state.loadListener) state.frame?.removeEventListener('load', state.loadListener)
    })
    h5ElementViewportObservers.clear()
    overlay.remove()
    editorStyle.remove()
    if (isCurrentSlide()) {
      htmlElements.value = []
      htmlSelectedElementId.value = null
      htmlSelectedElement.value = null
    }
  }
  cleanup.controller = controller
  return cleanup
}
const fitHtmlFrame = (event) => {
  const iframe = event?.currentTarget
  const container = iframe?.parentElement
  if (!iframe || !container) return

  const previous = [...htmlFrameObservers].find((item) => item.iframe === iframe)
  previous?.observer?.disconnect()
  previous?.cleanup?.()
  if (previous) htmlFrameObservers.delete(previous)

  const resize = () => {
    const width = container.clientWidth
    const height = container.clientHeight
    if (!width || !height) return
    const scale = Math.min(width / 1280, height / 720)
    iframe.style.transform = `scale(${scale})`
    const overlay = iframe.contentDocument?.querySelector('.a12-html-editor-overlay')
    overlay?.style.setProperty('--a12-editor-toolbar-scale', String(scale ? 1 / scale : 1))
  }

  resize()
  const structuredMode = !current.value?.html
  const editorCleanup = attachHtmlDragEditor(iframe, {
    structuredMode,
    // 当前 iframe 已经反映了编辑结果；只持久化，不在每次操作后重载 srcdoc。
    onCommit: structuredMode ? (payload) => commitStructuredHtmlDocument(payload, { refreshFrame: false }) : null,
  })
  // attachHtmlDragEditor 将 HTML 编辑控制器挂在清理函数上；这里需要把控制器一并登记，
  // 否则工具栏点击时 activeHtmlController() 始终拿不到 insertElement 等操作方法。
  const controller = editorCleanup?.controller || null
  const frameDocument = iframe.contentDocument
  const canvasArea = container.closest('.canvas-scroll-viewport')
  // iframe 内的滚轮不会冒泡到外层画布，仅转发缩放；中键平移暂不启用。
  const handleFrameWheel = (event) => handleCanvasWheel(event, canvasArea)
  frameDocument?.addEventListener('wheel', handleFrameWheel, { passive: false })
  const cleanup = () => {
    frameDocument?.removeEventListener('wheel', handleFrameWheel)
    editorCleanup?.()
  }
  resize()
  if (typeof ResizeObserver === 'undefined') {
    htmlFrameObservers.add({ iframe, document: frameDocument, observer: null, cleanup, controller, slide: current.value })
    if (pendingHtmlPanelSelection?.slide === current.value && controller?.selectById?.(pendingHtmlPanelSelection.id)) pendingHtmlPanelSelection = null
    flushPendingHtmlToolbarTool()
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  htmlFrameObservers.add({ iframe, document: frameDocument, observer, cleanup, controller, slide: current.value })
  if (pendingHtmlPanelSelection?.slide === current.value && controller?.selectById?.(pendingHtmlPanelSelection.id)) pendingHtmlPanelSelection = null
  flushPendingHtmlToolbarTool()
}
const clearPreviewFrameObservers = () => {
  previewFrameObservers.forEach(({ observer }) => observer?.disconnect())
  previewFrameObservers.clear()
}
const fitPreviewHtmlFrame = (event) => {
  const iframe = event?.currentTarget
  const container = iframe?.parentElement
  if (!iframe || !container) return

  const previous = [...previewFrameObservers].find((item) => item.iframe === iframe)
  previous?.observer?.disconnect()
  if (previous) previewFrameObservers.delete(previous)

  const resize = () => {
    const width = container.clientWidth
    const height = container.clientHeight
    if (!width || !height) return
    iframe.style.transform = `scale(${Math.min(width / 1280, height / 720)})`
  }

  resize()
  if (typeof ResizeObserver === 'undefined') {
    previewFrameObservers.add({ iframe, observer: null })
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  previewFrameObservers.add({ iframe, observer })
}
const openPreview = () => {
  previewSlideIndex.value = selectedSlide.value
  previewVisible.value = true
}
const previewSpeakerNotes = (slide) => String(slide?.notes || slide?.speaker_notes || slide?.speakerNotes || slide?.description || '暂无备注提示')
const updatePresentationPointer = (event) => {
  // 触屏设备（hover: none）没有鼠标指针，禁用激光笔；放映改用点击翻页。
  if (!presentationPointerAvailable) return
  if (!presentationMode.value || !presentationLaserEnabled.value || !previewStageRef.value) return
  const rect = previewStageRef.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  presentationLaserPosition.x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100))
  presentationLaserPosition.y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100))
  presentationLaserPosition.visible = true
}
const hidePresentationPointer = () => { presentationLaserPosition.visible = false }
const handlePresentationFullscreenChange = () => {
  if (presentationMode.value && !document.fullscreenElement) presentationMode.value = false
}
const requestPresentationFullscreen = async () => {
  await nextTick()
  try {
    if (previewStageRef.value?.requestFullscreen && !document.fullscreenElement) await previewStageRef.value.requestFullscreen()
  } catch {
    WorkspaceMessage.info('浏览器未授权全屏，已保留放映模式；可继续使用键盘翻页')
  }
}
const enterPresentationMode = async () => {
  previewSlideIndex.value = selectedSlide.value
  presentationMode.value = true
  presentationLaserEnabled.value = false
  presentationNotesVisible.value = false
  previewVisible.value = true
  await requestPresentationFullscreen()
}
const exitPresentationMode = async () => {
  presentationMode.value = false
  presentationLaserEnabled.value = false
  presentationNotesVisible.value = false
  presentationLaserPosition.visible = false
  try {
    if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen()
  } catch { /* 浏览器可能已经退出全屏 */ }
}
const handlePresentationKeydown = (event) => {
  if (!presentationMode.value) return
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target?.tagName)) return
  if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(event.key)) {
    event.preventDefault()
    scrollPreviewTo(Math.min(slides.length - 1, previewSlideIndex.value + 1))
  } else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) {
    event.preventDefault()
    scrollPreviewTo(Math.max(0, previewSlideIndex.value - 1))
  } else if (event.key === 'Home') {
    event.preventDefault()
    scrollPreviewTo(0)
  } else if (event.key === 'End') {
    event.preventDefault()
    scrollPreviewTo(slides.length - 1)
  } else if (event.key === 'Escape') {
    event.preventDefault()
    void exitPresentationMode()
  }
}
const closePreview = () => {
  if (presentationMode.value || document.fullscreenElement) void exitPresentationMode()
  previewVisible.value = false
  clearPreviewFrameObservers()
}
const scrollPreviewTo = (index) => {
  const nextIndex = Math.min(Math.max(0, Number(index) || 0), Math.max(0, slides.length - 1))
  previewSlideIndex.value = nextIndex
  window.setTimeout(() => {
    previewDeckRef.value?.querySelector(`[data-preview-index="${nextIndex}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, 0)
}
const normalizeElementType = (element) => {
  const raw = String(element?.type ?? element?.kind ?? element?.element_type ?? element?.component_type ?? 'text').trim().toLowerCase().replace(/[\s-]+/g, '_')
  const aliases = {
    textbox: 'text', text_box: 'text', paragraph: 'text', rich_text: 'text', text_element: 'text',
    equation: 'formula', math_formula: 'formula', formula: 'formula',
    rect: 'shape', rectangle: 'shape', basic_shape: 'shape', geometry: 'shape',
    picture: 'image', photo: 'image', image_element: 'image',
    graph: 'chart', bar_chart: 'chart', line_chart: 'chart', chart_element: 'chart',
  }
  const inferred = aliases[raw] || raw
  const visualType = String(element?.visualType ?? element?.visual_type ?? '').toLowerCase()
  const contentType = String(element?.content_type ?? element?.contentType ?? '').toLowerCase()
  const formulaFlag = element?.is_formula === true || element?.isFormula === true || ['formula', 'equation'].includes(contentType)
  return (inferred === 'shape' && ['formula', 'equation'].includes(visualType)) || (formulaFlag && ['text', 'shape'].includes(inferred)) ? 'formula' : inferred || 'text'
}
const readableElementContent = (value) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map(readableElementContent).filter(Boolean).join(' ')
  if (typeof value === 'object') return readableElementContent(value.text ?? value.content ?? value.value ?? value.label ?? value.title ?? value.plain_text ?? value.html ?? '')
  return ''
}
const extractElementContent = (element) => [
  element?.content,
  element?.text,
  element?.text_content,
  element?.textContent,
  element?.value,
  element?.label,
  element?.equation,
  element?.formula,
  element?.props?.content,
  element?.props?.text,
  element?.props?.value,
  element?.plain_text,
  element?.rich_text,
  element?.body,
  element?.data?.text,
  element?.data?.content,
  element?.data?.value,
].map(readableElementContent).find((value) => value.trim()) || ''
const expandLegacyFormulaElement = (element, normalized, content, index) => {
  const baseId = normalized.id || `formula-${index + 1}`
  const basePosition = normalized.position || {}
  const baseStyle = normalized.style || {}
  const makePart = (presetId, suffix, relative, overrides = {}) => {
    const preset = elementPresets.find((item) => item.id === presetId)
    const part = cloneElementData(preset)
    part.id = `${baseId}-${suffix}`
    part.name = overrides.name || part.name
    part.target = null
    part.position = {
      ...part.position,
      x: Number((Number(basePosition.x || 0) + Number(basePosition.width || 48) * relative.x).toFixed(2)),
      y: Number((Number(basePosition.y || 0) + Number(basePosition.height || 28) * relative.y).toFixed(2)),
      width: Number((Number(basePosition.width || 48) * relative.width).toFixed(2)),
      height: Number((Number(basePosition.height || 28) * relative.height).toFixed(2)),
      zIndex: basePosition.zIndex ?? 3,
    }
    if (baseStyle.color && presetId === 'formula-diagram') part.style = { ...part.style, fillColor: baseStyle.color, borderColor: baseStyle.color }
    if (baseStyle.color && presetId === 'formula-text') part.style = { ...part.style, color: baseStyle.color }
    part.content = overrides.content ?? part.content
    return part
  }
  return [
    makePart('formula-diagram', 'diagram', { x: 0, y: 0.08, width: 0.31, height: 0.82 }, { name: '公式示意图' }),
    makePart('formula-text', 'text', { x: 0.35, y: 0.12, width: 0.65, height: 0.42 }, { name: '公式文字', content }),
    makePart('formula-caption', 'caption', { x: 0.35, y: 0.62, width: 0.65, height: 0.22 }, { name: '公式说明' }),
  ]
}
const normalizeElements = (rawElements) => {
  const parsed = typeof rawElements === 'string' ? parseJson(rawElements, []) : rawElements
  const root = Array.isArray(parsed) && parsed.length === 1 && parsed[0]?.elements ? parsed[0] : parsed
  const nested = Array.isArray(root) ? root : (root?.elements ?? root?.components ?? root?.items ?? [])
  const source = typeof nested === 'string' ? parseJson(nested, []) : nested
  if (!Array.isArray(source) || !source.length) return createMockElements()
  return source.flatMap((element, index) => {
    const type = normalizeElementType(element)
    const rawId = element?.id ?? element?.element_id ?? element?.component_id
    const preset = allElementPresets.find((item) => item.id === rawId) || allElementPresets.find((item) => item.type === type) || elementPresets[0]
    const rawPosition = element?.position || element?.bounds || element?.rect || {}
    const content = extractElementContent(element) || readableElementContent(preset.content)
    const normalized = {
      ...cloneElementData(preset),
      ...element,
      id: rawId || `${type}-${index + 1}`,
      type,
      name: element?.name || element?.label || preset.name,
      target: element?.target ?? (rawId === 'title' || rawId === 'description' || rawId === 'footer' ? rawId : preset.target || null),
      content,
      position: {
        ...preset.position,
        ...rawPosition,
        x: element?.x ?? rawPosition.x ?? rawPosition.left ?? preset.position?.x,
        y: element?.y ?? rawPosition.y ?? rawPosition.top ?? preset.position?.y,
        width: element?.width ?? rawPosition.width ?? preset.position?.width,
        height: element?.height ?? rawPosition.height ?? preset.position?.height,
        rotation: element?.rotation ?? rawPosition.rotation ?? preset.position?.rotation,
      },
      style: { ...preset.style, ...(element?.style || element?.styles || {}) },
      data: Array.isArray(element?.data) ? cloneElementListData(element.data) : (element?.data || element?.items || cloneElementListData(preset.data)),
      h5Config: type === 'h5' ? normalizeH5RuntimeConfig(element?.h5Config || element?.h5_config || {}) : undefined,
      h5_config: type === 'h5' ? normalizeH5RuntimeConfig(element?.h5Config || element?.h5_config || {}) : undefined,
      shapeKind: element?.shapeKind || element?.shape_kind || element?.shapeType || element?.variant || preset.shapeKind,
      src: element?.src || element?.url || element?.image_url || preset.src || (type === 'image' ? createMockImageSrc() : undefined),
    }
    if (type === 'subject') {
      const rawSubjectType = element?.subjectType || element?.subject_type || element?.tool_type || 'geometry'
      normalized.subjectType = normalizeSubjectToolType(rawSubjectType)
      normalized.subject_type = normalized.subjectType
      normalized.data = normalizeSubjectToolData(element?.data ?? element?.config ?? preset.data, rawSubjectType)
      normalized.render = nonEmptyObject(element?.render)
        || nonEmptyObject(element?.subjectRender)
        || nonEmptyObject(element?.subject_render)
        || subjectToolDefaultRenderHint(normalized.subjectType)
      normalized.subjectRender = normalized.render
      normalized.subject_render = normalized.subjectRender
      normalized.subjectStyle = nonEmptyObject(element?.subjectStyle)
        || nonEmptyObject(element?.subject_style)
        || nonEmptyObject(element?.style)
        || {}
      normalized.subject_style = normalized.subjectStyle
      normalized.subjectRenderHint = element?.subjectRenderHint || element?.subject_render_hint || element?.render_hint || null
      normalized.subject_render_hint = normalized.subjectRenderHint
    }
    return type === 'formula' && (rawId === 'visual' || element?.target === 'formula')
      ? expandLegacyFormulaElement(element, normalized, content || 'a² + b² = c²', index)
      : [normalized]
  })
}
const elementById = (id) => current.value?.elements?.find((element) => element.id === id)
const selectedElement = computed(() => elementById(selectedElementId.value) || null)
const elementClass = (elementOrId) => {
  const element = typeof elementOrId === 'string' ? elementById(elementOrId) : elementOrId
  const id = element?.id || elementOrId
  return {
    'canvas-element': true,
    'canvas-element-selected': selectedElementId.value === id,
    'canvas-element-dragging': draggingElementId.value === id,
    [`canvas-element-${element?.type || 'unknown'}`]: true,
  }
}
const previewElementClass = (element) => ({ [`canvas-element-${element?.type || 'unknown'}`]: true })
const elementStyleFromElement = (element, slide = current.value) => {
  const style = element?.style || {}
  const position = element?.position || {}
  const slideTheme = themeForSlide(slide)
  const result = {
    position: 'absolute',
    left: `${Number(position.x ?? 0)}%`,
    top: `${Number(position.y ?? 0)}%`,
    width: `${Number(position.width ?? 30)}%`,
    height: `${Number(position.height ?? 20)}%`,
    right: 'auto',
    bottom: 'auto',
    zIndex: Number(position.zIndex ?? 1),
    transform: `rotate(${Number(position.rotation ?? 0)}deg)`,
    boxSizing: 'border-box',
    display: element?.visible === false ? 'none' : undefined,
    opacity: Number(style.opacity ?? 100) / 100,
  }
  if (['text', 'formula'].includes(element?.type)) {
    result.color = style.color
    result.fontSize = style.fontSize ? `${style.fontSize}px` : undefined
    result.fontWeight = style.fontWeight
    result.textAlign = style.textAlign
    result.lineHeight = style.lineHeight
    result.margin = '0'
    result.maxWidth = 'none'
    result.overflow = 'hidden'
    result.whiteSpace = 'pre-wrap'
  }
  if (element?.type === 'formula') result['--element-color'] = style.color || slideTheme.color
  if (element?.type === 'shape') {
    result['--element-color'] = style.fillColor || slideTheme.color
    result['--element-border-color'] = style.borderColor || style.fillColor || slideTheme.color
    result['--element-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : undefined
    result['--element-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : undefined
  }
  if (element?.type === 'image') {
    result['--element-color'] = style.tintColor || slideTheme.color
    result['--element-border-color'] = style.borderColor || '#bfdbfe'
    result['--element-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--element-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '14px'
    result['--element-object-fit'] = style.objectFit || 'cover'
  }
  if (element?.type === 'chart') {
    result['--chart-color'] = style.color || slideTheme.color
    result['--chart-background'] = style.backgroundColor || '#eff6ff'
    result['--chart-border-color'] = style.borderColor || '#bfdbfe'
    result['--chart-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--chart-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '14px'
  }
  if (['audio', 'video', 'table', 'h5', 'subject'].includes(element?.type)) {
    result['--widget-color'] = style.color || slideTheme.color
    result['--widget-background'] = style.backgroundColor || '#eff6ff'
    result['--widget-border-color'] = style.borderColor || '#bfdbfe'
    result['--widget-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--widget-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '12px'
  }
  return result
}
const elementStyle = (id) => elementStyleFromElement(elementById(id))
const elementContentForSlide = (element, slide = current.value) => {
  if (!element) return ''
  if (element.target === 'title') return slide?.title || element.content || ''
  if (element.target === 'description') return slide?.description || element.content || ''
  if (element.target === 'footer') return slide?.footer || element.content || '在观察、猜想与验证中理解核心概念，并用它解决简单的实际问题。'
  return extractElementContent(element)
}
const elementContent = (element) => elementContentForSlide(element, current.value)
const previewElementStyle = (element, slide) => elementStyleFromElement(element, slide)
const previewElementContent = (element, slide) => elementContentForSlide(element, slide)

const escapeStructuredHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')
const escapeStructuredAttribute = escapeStructuredHtml
const structuredCssPropertyName = (key) => String(key).startsWith('--')
  ? String(key)
  : String(key).replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)
const serializeStructuredStyle = (style = {}) => Object.entries(style)
  .filter(([, value]) => value !== undefined && value !== null && String(value) !== '')
  .map(([key, value]) => `${structuredCssPropertyName(key)}:${String(value).replace(/[<>;]/g, '')}`)
  .join(';')
const structuredJsonAttribute = (value) => escapeStructuredAttribute(JSON.stringify(value ?? []))
const structuredElementAttributes = (element, type) => {
  const attrs = [
    `data-ppt-element="${escapeStructuredAttribute(element?.id || `${type}-${Date.now()}`)}"`,
    `data-ppt-type="${escapeStructuredAttribute(type)}"`,
    'data-a12-structured-element',
    `data-name="${escapeStructuredAttribute(element?.name || elementTypeLabels[type] || '页面元素')}"`,
  ]
  if (element?.target) attrs.push(`data-ppt-target="${escapeStructuredAttribute(element.target)}"`)
  if (element?.shapeKind) attrs.push(`data-shape-kind="${escapeStructuredAttribute(element.shapeKind)}"`)
  if (element?.moduleId || element?.module_id) attrs.push(`data-module-id="${escapeStructuredAttribute(element.moduleId || element.module_id)}"`)
  if (element?.embedMode || element?.embed_mode) attrs.push(`data-embed-mode="${escapeStructuredAttribute(element.embedMode || element.embed_mode)}"`)
  if (type === 'h5') {
    const rawModuleType = String(element?.module_type_raw || element?.module_type || element?.moduleType || element?.metadata?.module_type || '').trim()
    const moduleType = normalizeInteractiveModuleType(rawModuleType)
    attrs.push(`data-module-type="${escapeStructuredAttribute(moduleType)}"`)
    if (rawModuleType) attrs.push(`data-module-type-raw="${escapeStructuredAttribute(rawModuleType)}"`)
    if (element?.topic) attrs.push(`data-h5-topic="${escapeStructuredAttribute(element.topic)}"`)
    const generatedMarker = String(element?.generatedBy || element?.generated_by || '').trim().toLowerCase()
    if (generatedMarker === 'api-144' || element?.moduleId || element?.module_id) attrs.push('data-h5-generated="api-144"')
    if (Array.isArray(element?.usageSuggestions || element?.usage_suggestions) && (element.usageSuggestions || element.usage_suggestions).length) {
      attrs.push(`data-h5-usage-suggestions="${structuredJsonAttribute(element.usageSuggestions || element.usage_suggestions)}"`)
    }
    if (element?.metadata && typeof element.metadata === 'object' && !Array.isArray(element.metadata)) attrs.push(`data-h5-metadata="${structuredJsonAttribute(element.metadata)}"`)
    attrs.push(`data-h5-config="${escapeStructuredAttribute(h5RuntimeConfigAttribute(element?.h5Config || element?.h5_config || {}))}"`)
  }
  if (type === 'subject') {
    const subjectType = normalizeSubjectToolType(element?.subjectType || element?.subject_type || 'geometry')
    const subjectData = normalizeSubjectToolData(element?.data, element?.subjectType || element?.subject_type || subjectType)
    const subjectRender = nonEmptyObject(element?.render)
      || nonEmptyObject(element?.subjectRender)
      || nonEmptyObject(element?.subject_render)
      || subjectToolDefaultRenderHint(subjectType)
    const subjectStyle = nonEmptyObject(element?.subjectStyle)
      || nonEmptyObject(element?.subject_style)
      || nonEmptyObject(element?.style)
    attrs.push(`data-subject-type="${escapeStructuredAttribute(subjectType)}"`)
    attrs.push(`data-subject-data="${structuredJsonAttribute(subjectData)}"`)
    attrs.push(`data-subject-render="${structuredJsonAttribute(subjectRender)}"`)
    if (subjectStyle) attrs.push(`data-subject-style="${structuredJsonAttribute(subjectStyle)}"`)
    if (element?.subjectRenderHint || element?.subject_render_hint || element?.render_hint) attrs.push(`data-subject-render-hint="${structuredJsonAttribute(element.subjectRenderHint || element.subject_render_hint || element.render_hint)}"`)
    if (element?.subjectValidation || element?.subject_validation) attrs.push(`data-subject-validation="${structuredJsonAttribute(element.subjectValidation || element.subject_validation)}"`)
  }
  if (element?.resourceId || element?.resource_id) attrs.push(`data-resource-id="${escapeStructuredAttribute(element.resourceId || element.resource_id)}"`)
  if (element?.resourceName) attrs.push(`data-resource-name="${escapeStructuredAttribute(element.resourceName)}"`)
  if (element?.resourceType) attrs.push(`data-resource-type="${escapeStructuredAttribute(element.resourceType)}"`)
  if (type === 'chart') attrs.push(`data-a12-chart-data="${structuredJsonAttribute(Array.isArray(element?.data) ? element.data : [])}"`)
  if (type === 'table') attrs.push(`data-a12-table-data="${structuredJsonAttribute(Array.isArray(element?.data) ? element.data : [])}"`)
  if (['audio', 'video'].includes(type)) {
    if (element?.controls !== false) attrs.push('controls')
    if (element?.autoplay) attrs.push('autoplay')
    attrs.push(`title="${escapeStructuredAttribute(element?.name || (type === 'audio' ? '新增音频讲解' : '新增视频演示'))}"`)
  }
  return attrs.join(' ')
}
const structuredElementClass = (element, type) => {
  const classes = [`structured-element`, `structured-element-${type}`]
  if (type === 'text') classes.push('structured-text-element')
  if (type === 'shape') classes.push('shape-element', `shape-${element?.shapeKind || 'rectangle'}`)
  if (type === 'formula') classes.push('formula-text-element')
  if (type === 'chart') classes.push('chart-element')
  if (type === 'table') classes.push('workspace-widget', 'table-widget')
  if (['audio', 'video', 'h5'].includes(type)) classes.push('workspace-widget', `widget-${type}`)
  if (type === 'subject') classes.push('a12-subject-tool')
  return classes.join(' ')
}
const structuredShapeSvg = (shapeKind = 'rectangle') => {
  if (shapeKind === 'circle') return '<circle class="shape-fill" cx="50" cy="50" r="46" />'
  if (shapeKind === 'diamond') return '<polygon class="shape-fill" points="50,4 96,50 50,96 4,50" />'
  if (shapeKind === 'triangle') return '<polygon class="shape-fill" points="50,4 96,96 4,96" />'
  if (shapeKind === 'rounded') return '<rect class="shape-fill" x="4" y="4" width="92" height="92" rx="14" ry="14" />'
  return '<rect class="shape-fill" x="4" y="4" width="92" height="92" />'
}
const structuredTableMarkup = (rows) => {
  const normalizedRows = Array.isArray(rows) && rows.length ? rows : [['列 1', '列 2'], ['内容 1', '内容 2']]
  return normalizedRows.map((row, rowIndex) => {
    const cells = Array.isArray(row) ? row : [row]
    return `<tr>${cells.map((cell) => `<${rowIndex === 0 ? 'th' : 'td'}>${escapeStructuredHtml(cell)}</${rowIndex === 0 ? 'th' : 'td'}>`).join('')}</tr>`
  }).join('')
}
const structuredElementMarkup = (element, slide) => {
  const type = normalizeElementType(element)
  const attrs = structuredElementAttributes(element, type)
  const className = structuredElementClass(element, type)
  const style = escapeStructuredAttribute(serializeStructuredStyle(elementStyleFromElement(element, slide)))
  const content = elementContentForSlide(element, slide)
  const common = `${attrs} class="${className}" style="${style}"`

  if (type === 'text') {
    if (element.target === 'title') return `<h1 ${common}>${escapeStructuredHtml(content)}</h1>`
    if (element.target === 'description') return `<p ${common}>${escapeStructuredHtml(content)}</p>`
    if (element.target === 'footer') return `<footer ${common}>${escapeStructuredHtml(content)}</footer>`
    return `<div ${common}>${escapeStructuredHtml(content)}</div>`
  }
  if (type === 'formula') return `<div ${common}><strong>${escapeStructuredHtml(content || 'a² + b² = c²')}</strong></div>`
  if (type === 'shape' && element.shapeKind === 'formula-diagram') {
    const formulaDiagramCommon = `${attrs} class="${className} formula-diagram-element" style="${style}"`
    return `<div ${formulaDiagramCommon}><svg class="triangle-svg" viewBox="0 0 100 100" role="img" aria-label="直角三角形示意图"><path class="triangle-outline" d="M 12 88 L 82 88 L 82 12 Z" /><text class="triangle-label" x="47" y="98" text-anchor="middle">a</text><text class="triangle-label" x="90" y="53" text-anchor="middle">b</text><text class="triangle-label" x="38" y="43" text-anchor="middle">c</text></svg></div>`
  }
  if (type === 'shape') return `<div ${common}><svg class="shape-svg" viewBox="0 0 100 100" preserveAspectRatio="${element.shapeKind === 'circle' ? 'xMidYMid meet' : 'none'}" aria-hidden="true">${structuredShapeSvg(element.shapeKind)}</svg>${content ? `<span>${escapeStructuredHtml(content)}</span>` : ''}</div>`
  if (type === 'image') {
    const src = element.src || createMockImageSrc(content || '课堂图片')
    return `<img ${common} src="${escapeStructuredAttribute(src)}" alt="${escapeStructuredAttribute(element.alt || content || element.name || '课堂图片')}" />`
  }
  if (type === 'chart') return `<div ${common}><span class="structured-chart-placeholder">${escapeStructuredHtml(content || '数据图表')}</span></div>`
  if (type === 'audio' || type === 'video') {
    const source = element.url || element.src || ''
    const sourceAttribute = source ? ` src="${escapeStructuredAttribute(source)}"` : ''
    return `<${type} ${common}${sourceAttribute} preload="metadata"></${type}>`
  }
  if (type === 'h5') {
    const html = secureHtmlForSandbox(withH5RuntimeConfig(element.html || '<!doctype html><html lang="zh-CN"><body style="margin:0;display:grid;place-items:center;height:100vh;font:16px sans-serif;color:#c2410c;background:#fff7ed">请使用工具栏生成 H5 组件</body></html>', element.h5Config || element.h5_config || {}))
    return `<div ${common} data-a12-h5-host><iframe data-a12-h5-frame srcdoc="${escapeStructuredAttribute(html)}" sandbox="allow-scripts" title="${escapeStructuredAttribute(element.name || 'H5 互动内容')}"></iframe></div>`
  }
  if (type === 'subject') return `<div ${common}>${subjectToolMarkup({
    subjectType: element?.subjectType || element?.subject_type,
    data: element?.data,
    title: content || element?.name || '学科探究工具',
      renderHint: element?.subjectRenderHint || element?.subject_render_hint || element?.render_hint || element?.subjectRender || element?.subject_render,
  })}</div>`
  if (type === 'table') {
    const rows = Array.isArray(element.data) ? element.data : []
    return `<div ${common}><strong>${escapeStructuredHtml(content || '数据表格')}</strong><table><tbody>${structuredTableMarkup(rows)}</tbody></table></div>`
  }
  return `<div ${common}>${escapeStructuredHtml(content)}</div>`
}
function buildStructuredHtmlSlide(slide) {
  const elements = Array.isArray(slide?.elements) && slide.elements.length ? slide.elements : createMockElements()
  const accent = themeForSlide(slide).color
  const background = pageBackgroundColor(slide) || '#f9fbff'
  const backgroundImage = pageBackgroundImage(slide)
  const rootStyle = [
    `--accent:${accent}`,
    `background-color:${background}`,
    backgroundImage ? `background-image:url("${safeCssUrl(backgroundImage)}");background-size:cover;background-position:center` : '',
  ].filter(Boolean).join(';')
  const pageEyebrow = escapeStructuredHtml(slide?.eyebrow || '')
  const layoutClass = String(slide?.layout || '').replace(/[^\w\u4e00-\u9fa5-]/g, '') || '重点陈述'
  const styles = `
    *{box-sizing:border-box}
    html,body{width:${HTML_CANVAS_WIDTH}px;height:${HTML_CANVAS_HEIGHT}px;margin:0;padding:0;overflow:hidden;background:transparent}
    body{font-family:"Microsoft YaHei",Arial,sans-serif;color:#102d54}
    .slide{position:relative;width:${HTML_CANVAS_WIDTH}px;height:${HTML_CANVAS_HEIGHT}px;overflow:hidden;padding:0;color:#102d54}
    .structured-slide-eyebrow{position:absolute;z-index:6;top:7%;left:8%;color:var(--accent);font:600 14px Arial,"Microsoft YaHei",sans-serif;letter-spacing:.12em;white-space:nowrap}
    [data-ppt-element]{transform-origin:center center}
    .structured-text-element{display:block;margin:0;overflow:hidden;line-height:1.5;white-space:pre-wrap}
    h1.structured-text-element{line-height:1.2;letter-spacing:-.04em}
    footer.structured-text-element{display:flex;align-items:center;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54);line-height:1.5}
    .formula-text-element{display:flex;align-items:center;justify-content:center;min-width:0;padding:4px;font-family:Arial,"Microsoft YaHei",sans-serif;text-align:center}
    .formula-text-element strong{max-width:100%;overflow:hidden;color:var(--element-color,var(--accent));font-size:inherit;text-overflow:ellipsis;white-space:nowrap}
    .formula-diagram-element{display:grid;place-items:center;overflow:visible;padding:4px}
    .triangle-svg,.shape-svg{display:block;width:100%;height:100%;overflow:visible}
    .triangle-outline{fill:none;stroke:var(--element-border-color,var(--accent));stroke-width:5}
    .triangle-label{fill:var(--element-border-color,var(--accent));font:700 10px Arial,sans-serif}
    .shape-element{display:flex;align-items:center;justify-content:center;overflow:visible;padding:4px}
    .shape-fill{fill:var(--element-color,#dbeafe);stroke:var(--element-border-color,var(--accent));stroke-width:var(--element-border-width,2px)}
    .shape-element>span{position:relative;z-index:1;max-width:90%;overflow:hidden;color:var(--element-border-color,var(--element-color,var(--accent)));font-size:11px;font-weight:700;text-overflow:ellipsis;white-space:nowrap}
    .structured-element-image{display:block;overflow:hidden;border:var(--element-border-width,1px) solid var(--element-border-color,#bfdbfe);border-radius:var(--element-border-radius,14px);background:#dbeafe;object-fit:var(--element-object-fit,cover);box-shadow:0 10px 24px rgb(37 99 235 / 12%)}
    .structured-element-image::after{content:''}
    .chart-element{display:flex;flex-direction:column;gap:8px;padding:12px;overflow:hidden;border:var(--chart-border-width,1px) solid var(--chart-border-color,#bfdbfe);border-radius:var(--chart-border-radius,14px);background:var(--chart-background,#eff6ff)}
    .structured-chart-placeholder{color:var(--chart-color,var(--accent));font-size:11px}
    .workspace-widget{display:flex;align-items:center;gap:9px;padding:10px 12px;overflow:hidden;border:var(--widget-border-width,1px) solid var(--widget-border-color,#bfdbfe);border-radius:var(--widget-border-radius,12px);background:var(--widget-background,#eff6ff);color:var(--widget-color,var(--accent))}
    .workspace-widget strong,.workspace-widget small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .workspace-widget strong{color:#173d78;font-size:11px}.workspace-widget small{color:#607491;font-size:9px}
    .structured-element-audio,.structured-element-video{display:block;min-height:42px;padding:8px;background:var(--widget-background,#eff6ff);color:var(--widget-color,var(--accent))}
    .structured-element-h5{position:absolute;display:block;overflow:hidden;padding:0;background:var(--widget-background,#fff7ed)}
    [data-a12-h5-host]>iframe[data-a12-h5-frame]{position:absolute;top:0;left:0;display:block;width:${H5_DESIGN_WIDTH}px;height:${H5_DESIGN_HEIGHT}px;max-width:none;max-height:none;margin:0;border:0;border-radius:0;transform-origin:top left}
    .structured-element-h5,.structured-element-audio,.structured-element-video{border:var(--widget-border-width,1px) solid var(--widget-border-color,#bfdbfe);border-radius:var(--widget-border-radius,12px)}
    .table-widget{display:block;color:var(--widget-color,var(--accent))}.table-widget table{width:100%;height:100%;border-collapse:collapse;font-size:10px}.table-widget th,.table-widget td{padding:6px 8px;border:1px solid rgb(37 99 235 / 18%);text-align:left}.table-widget th{background:rgb(219 234 254 / 70%)}
    ${subjectToolRuntimeCss}
  `
  const body = elements.map((element) => structuredElementMarkup(element, slide)).join('')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${escapeStructuredHtml(slide?.title || '教学页面')}</title><style>${styles}</style></head><body><main class="slide structured-slide layout-${layoutClass}" style="${escapeStructuredAttribute(rootStyle)}"><span class="structured-slide-eyebrow">${pageEyebrow}</span>${body}</main></body></html>`
}
// 所有页面（包括新建页面和服务端生成页面）都以固定 1280x720 HTML 作为
// 工作台的唯一渲染源。结构化页面仍保留 elements 作为持久化/编辑数据，
// 这里仅把它投影成与 AI PPT 相同的 HTML 画布。
function slideHtmlSource(slide) {
  if (!slide) return ''
  const persistedHtml = String(slide.html || '').trim()
  return persistedHtml || buildStructuredHtmlSlide(slide)
}
const structuredHistoryClone = (value) => {
  try { return JSON.parse(JSON.stringify(value)) } catch { return [] }
}
const structuredHtmlLiveDocumentForSlide = (slide) => {
  if (!slide) return ''
  const cached = structuredHtmlLiveDocuments.get(slide)
  if (cached) return cached
  if (structuredHtmlCanvasSourceSlide.value === slide && structuredHtmlCanvasSource.value) return structuredHtmlCanvasSource.value
  return buildStructuredHtmlSlide(slide)
}
const rememberStructuredHtmlLiveDocument = (slide, html) => {
  if (!slide || !html) return
  structuredHtmlLiveDocuments.set(slide, String(html))
}
const structuredHistorySnapshot = (slide, html) => ({
  mode: 'structured',
  html: String(html || structuredHtmlLiveDocumentForSlide(slide)),
  elements: structuredHistoryClone(slide?.elements || []),
  title: slide?.title || '',
  description: slide?.description || '',
  footer: slide?.footer || '',
})
const restoreStructuredHistorySnapshot = (slide, snapshot) => {
  if (!slide || !snapshot || !Array.isArray(snapshot.elements)) return false
  slide.elements = structuredHistoryClone(snapshot.elements)
  if (snapshot.title !== undefined) slide.title = snapshot.title
  if (snapshot.description !== undefined) slide.description = snapshot.description
  if (snapshot.footer !== undefined) slide.footer = snapshot.footer
  const restoredHtml = String(snapshot.html || buildStructuredHtmlSlide(slide))
  rememberStructuredHtmlLiveDocument(slide, restoredHtml)
  structuredHtmlCanvasSourceSlide.value = slide
  structuredHtmlCanvasSource.value = restoredHtml
  if (slide === current.value) htmlCanvasFrameRevision.value += 1
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
  markSlideComponentDirty(slide, 'structured:history')
  saveCurrentPresentationDraft()
  return true
}
const commitStructuredHtmlDocument = ({ slide, html, elements } = {}, { refreshFrame = false } = {}) => {
  if (!slide || slide !== current.value) return false
  const previousHtml = structuredHtmlLiveDocumentForSlide(slide)
  if (previousHtml === html) return false

  const history = htmlHistoryForSlide(slide)
  history.undo.push(structuredHistorySnapshot(slide, previousHtml))
  if (history.undo.length > 30) history.undo.shift()
  history.redo.length = 0

  const previousById = new Map((slide.elements || []).map((element) => [String(element.id), element]))
  const nextElements = (Array.isArray(elements) ? elements : []).map((element, index) => {
    const previous = previousById.get(String(element?.id || ''))
    const merged = {
      ...(previous ? cloneElementData(previous) : {}),
      ...(element || {}),
      id: previous?.id || element?.id || `element-${index + 1}`,
      type: normalizeElementType(element),
      name: element?.name || previous?.name || `${elementTypeLabels[normalizeElementType(element)] || '元素'} ${index + 1}`,
      target: element?.target ?? previous?.target ?? null,
      shapeKind: element?.shapeKind ?? previous?.shapeKind,
      position: { ...(previous?.position || {}), ...(element?.position || {}) },
      style: { ...(previous?.style || {}), ...(element?.style || {}) },
    }
    if (element?.data === undefined && previous?.data !== undefined) merged.data = structuredHistoryClone(previous.data)
    if (element?.src === undefined && previous?.src !== undefined) merged.src = previous.src
    if (element?.url === undefined && previous?.url !== undefined) merged.url = previous.url
    if (element?.html === undefined && previous?.html !== undefined) merged.html = previous.html
    return merged
  })
  slide.elements = nextElements
  const titleElement = nextElements.find((element) => element.target === 'title')
  const descriptionElement = nextElements.find((element) => element.target === 'description')
  const footerElement = nextElements.find((element) => element.target === 'footer')
  if (titleElement?.content) { slide.title = titleElement.content; slide.page_title = titleElement.content }
  if (descriptionElement) slide.description = descriptionElement.content || ''
  if (footerElement) slide.footer = footerElement.content || ''
  rememberStructuredHtmlLiveDocument(slide, html)
  if (refreshFrame) {
    structuredHtmlCanvasSourceSlide.value = slide
    structuredHtmlCanvasSource.value = html
    if (slide === current.value) htmlCanvasFrameRevision.value += 1
  }
  markSlideComponentDirty(slide, htmlSelectedElementId.value || 'structured:html')
  saveCurrentPresentationDraft()
  return true
}
const refreshStructuredHtmlCanvas = (slide = current.value) => {
  if (!slide || slide.html) return
  const nextHtml = buildStructuredHtmlSlide(slide)
  rememberStructuredHtmlLiveDocument(slide, nextHtml)
  structuredHtmlCanvasSourceSlide.value = slide
  structuredHtmlCanvasSource.value = nextHtml
  if (slide === current.value) htmlCanvasFrameRevision.value += 1
}
const selectedElementPanel = computed(() => {
  const element = selectedElement.value
  return element ? { ...element, content: elementContent(element), position: { ...(element.position || {}) }, style: { ...(element.style || {}) } } : null
})
const htmlControllerForSlide = (slide = current.value) => [...htmlFrameObservers]
  .reverse()
  .find((item) => item.slide === slide && item.iframe?.isConnected && item.iframe.contentDocument === item.document && item.controller)
  ?.controller || null
const activeHtmlController = () => {
  const observers = [...htmlFrameObservers].reverse()
  const live = observers.find((item) => item.slide === current.value && item.iframe?.isConnected && item.iframe.contentDocument === item.document && item.controller)
  return live?.controller || null
}
const waitForHtmlController = async (slide = current.value, { reload = true } = {}) => {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const controller = htmlControllerForSlide(slide)
    if (controller) return controller
    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 20))
  }
  if (!reload || slide !== current.value) return null
  syncHtmlCanvasSource(slide, { forceReload: true })
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const controller = htmlControllerForSlide(slide)
    if (controller) return controller
    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 20))
  }
  return null
}
// PPT 工作模式统一使用 AI PPT 的固定 1280x720 HTML 编辑器。没有持久化
// html 的新建页会由 buildStructuredHtmlSlide() 生成同规格的编辑投影，
// 避免再走另一套原生画布、缩放和元素交互逻辑；教学案文档仍由文档编辑器处理。
const workspaceUsesHtmlEditor = computed(() => workspaceMode.value === 'ppt' && Boolean(current.value))
const flushPendingHtmlToolbarTool = () => {
  const pending = pendingHtmlToolbarTool
  if (!pending || pending.slide !== current.value) return false
  const controller = activeHtmlController()
  if (!controller) return false
  pendingHtmlToolbarTool = null
  const inserted = controller.insertElement(pending.tool?.id || pending.tool, pending.tool || {})
  activeTool.value = ''
  if (!inserted) WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
  return Boolean(inserted)
}
const workspaceElements = computed(() => workspaceUsesHtmlEditor.value ? htmlElements.value : current.value?.elements || [])
const workspaceSelectedElement = computed(() => workspaceUsesHtmlEditor.value ? htmlSelectedElement.value : selectedElementPanel.value)
const workspaceSelectedElementId = computed(() => workspaceUsesHtmlEditor.value ? htmlSelectedElementId.value : selectedElementId.value)
const assistantComponentOptionLabel = (element, index) => {
  const name = String(element?.name || element?.content || element?.type || `组件 ${index + 1}`).replace(/\s+/g, ' ').trim()
  const type = elementTypeLabels[element?.type] || '页面组件'
  return `${name.slice(0, 32)} · ${type}`
}
const selectAssistantTargetComponent = (id) => {
  const normalizedId = String(id ?? '').trim()
  if (!normalizedId) {
    clearElementSelection()
    assistantTargetScope.value = 'auto'
    return
  }
  selectElementFromPanel(normalizedId)
  // 由统一的 HTML/结构化画布选择逻辑完成实际定位，避免 AI 指向一个孤立的 ID。
  assistantTargetScope.value = 'component'
}
const assistantTargetLabel = computed(() => {
  if (assistantTargetScope.value === 'auto') return 'AI 自行判断'
  if (assistantTargetScope.value === 'deck') return '整套课件'
  if (assistantTargetScope.value === 'component') {
    const element = workspaceSelectedElement.value
    return element ? `组件 · ${element.name || element.content || element.type || '未命名元素'}` : '组件 · 请先选择元素'
  }
  return `第 ${selectedSlide.value + 1} 页 · ${current.value?.title || '当前页面'}`
})
const assistantTargetDescription = computed(() => {
  if (assistantTargetScope.value === 'auto') return 'AI 将结合请求、当前页面与已选元素，自行判断最合适的处理范围。'
  if (assistantTargetScope.value === 'deck') return 'AI 将按整套课件的结构、页面与教学节奏理解本次请求。'
  if (assistantTargetScope.value === 'component') return workspaceSelectedElement.value
    ? 'AI 将优先围绕当前选中的元素提出建议或执行修改。'
    : '请选择一个页面元素，或改为“当前页”后再发送。'
  return 'AI 将围绕当前页面的内容和教学活动响应本次请求。'
})
const clampNumber = (value, min, max) => Math.min(max, Math.max(min, value))
const dragState = ref(null)
const placementMode = ref(null)
const placementDragState = ref(null)
const placementPreview = ref(null)
const placementDraft = ref(null)
const suppressNextCanvasClick = ref(false)
const placementPreviewElement = computed(() => {
  if (!placementDraft.value || !placementPreview.value) return null
  return {
    ...placementDraft.value,
    position: { ...(placementDraft.value.position || {}), ...placementPreview.value, zIndex: 20 },
  }
})
const placementPreviewStyle = computed(() => {
  const element = placementPreviewElement.value
  if (!element) return {}
  return { ...elementStyleFromElement(element), pointerEvents: 'none' }
})
const placementInstruction = computed(() => {
  if (!placementMode.value) return ''
  if (placementMode.value.type === 'text') return '点击画布放置文本'
  const label = placementMode.value.type === 'shape'
    ? shapeDefaults[placementMode.value.shapeKind]?.label || '形状'
    : elementTypeLabels[placementMode.value.type] || '元素'
  return `拖动生成${label}`
})
const placementTypes = ['text', 'image', 'shape', 'chart', 'audio', 'video', 'table', 'h5', 'subject']
const placementMinimumSizes = {
  shape: { width: 4, height: 4 },
  image: { width: 12, height: 10 },
  chart: { width: 14, height: 14 },
  audio: { width: 16, height: 8 },
  video: { width: 16, height: 10 },
  table: { width: 18, height: 12 },
  h5: { width: 16, height: 9 },
  subject: { width: 16, height: 9 },
}
const cancelCanvasPlacement = () => {
  window.removeEventListener('pointermove', handleCanvasPlacementMove)
  window.removeEventListener('pointerup', finishCanvasPlacement)
  placementMode.value = null
  placementDragState.value = null
  placementPreview.value = null
  placementDraft.value = null
  activeTool.value = ''
}
const beginElementPlacement = (tool) => {
  const type = tool?.id || tool
  if (!placementTypes.includes(type)) return
  cancelCanvasPlacement()
  suppressNextCanvasClick.value = false
  placementMode.value = { type, shapeKind: tool?.shapeKind }
  placementDraft.value = createElement(type, { shapeKind: tool?.shapeKind })
  activeTool.value = type
  selectedElementId.value = null
}
const canvasPoint = (event, canvas) => {
  const rect = canvas.getBoundingClientRect()
  return {
    x: clampNumber(((event.clientX - rect.left) / rect.width) * 100, 0, 100),
    y: clampNumber(((event.clientY - rect.top) / rect.height) * 100, 0, 100),
  }
}
const updatePlacementPreview = (event) => {
  const state = placementDragState.value
  if (!state) return
  const point = canvasPoint(event, state.canvas)
  const minimum = placementMinimumSizes[placementMode.value?.type] || { width: 3, height: 3 }
  const movingRight = point.x >= state.start.x
  const movingDown = point.y >= state.start.y
  const width = Math.min(Math.max(Math.abs(point.x - state.start.x), minimum.width), movingRight ? 100 - state.start.x : state.start.x)
  const height = Math.min(Math.max(Math.abs(point.y - state.start.y), minimum.height), movingDown ? 100 - state.start.y : state.start.y)
  const x = movingRight ? state.start.x : state.start.x - width
  const y = movingDown ? state.start.y : state.start.y - height
  state.hasDragged ||= Math.hypot(event.clientX - state.startClientX, event.clientY - state.startClientY) >= 4
  placementPreview.value = {
    x,
    y,
    width,
    height,
  }
}
const finishCanvasPlacement = () => {
  const mode = placementMode.value
  const preview = placementPreview.value
  const draft = placementDraft.value
  const state = placementDragState.value
  window.removeEventListener('pointermove', handleCanvasPlacementMove)
  window.removeEventListener('pointerup', finishCanvasPlacement)
  if (state?.canvas?.hasPointerCapture?.(state.pointerId)) state.canvas.releasePointerCapture(state.pointerId)
  placementDragState.value = null
  suppressNextCanvasClick.value = true
  if (mode && preview && state?.hasDragged) {
    insertElement(mode.type, { shapeKind: mode.shapeKind }, preview, draft)
  } else if (mode) {
    WorkspaceMessage.warning('拖动范围太小，请重新拖动生成元素')
  }
  placementMode.value = null
  placementPreview.value = null
  placementDraft.value = null
  activeTool.value = ''
}
const handleCanvasPlacementMove = (event) => {
  if (!placementDragState.value) return
  event.preventDefault()
  updatePlacementPreview(event)
}
const startCanvasPlacement = (event) => {
  const mode = placementMode.value
  if (!mode || mode.type === 'text' || event.button !== 0) return
  if (event.target?.closest?.('[data-element-id]')) {
    event.stopPropagation()
    return
  }
  const canvas = event.currentTarget
  placementDragState.value = { canvas, pointerId: event.pointerId, start: canvasPoint(event, canvas), startClientX: event.clientX, startClientY: event.clientY, hasDragged: false }
  placementPreview.value = { ...placementDragState.value.start, width: 0, height: 0 }
  canvas.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleCanvasPlacementMove)
  window.addEventListener('pointerup', finishCanvasPlacement)
  event.preventDefault()
}
const handleSlideCanvasClick = (event) => {
  if (suppressNextCanvasClick.value) {
    suppressNextCanvasClick.value = false
    event.stopPropagation()
    return
  }
  const mode = placementMode.value
  if (mode?.type === 'text') {
    const point = canvasPoint(event, event.currentTarget)
    insertElement('text', {}, { x: clampNumber(point.x, 0, 72), y: clampNumber(point.y, 0, 82), width: 28, height: 12 }, placementDraft.value)
    cancelCanvasPlacement()
    event.stopPropagation()
    return
  }
  if (!mode) {
    clearElementSelection()
    event.stopPropagation()
  }
}
const handleCanvasAreaClick = (event) => {
  if (event.target?.closest?.('.slide-canvas')) return
  cancelCanvasPlacement()
  clearElementSelection()
}
const startElementDrag = (id, event) => {
  // 手机档禁用指针拖拽：改为点击选中 + 浮动操作按钮（编辑/删除）。
  if (isMobile.value) return
  if (event.button !== 0) return
  if (placementMode.value) {
    event.stopPropagation()
    return
  }
  const element = elementById(id)
  const canvas = event.currentTarget?.closest('.slide-canvas')
  if (!element || !canvas) return
  const rect = canvas.getBoundingClientRect()
  const h5Frame = element.type === 'h5' && String(event.currentTarget?.tagName || '').toLowerCase() === 'iframe'
    ? event.currentTarget
    : null
  h5Frame?.contentWindow?.postMessage({ source: 'a12-h5-host', type: 'a12-h5-editing', active: true }, '*')
  dragState.value = {
    id,
    rect,
    pointerId: event.pointerId,
    captureTarget: event.currentTarget,
    startX: event.clientX,
    startY: event.clientY,
    startPosition: { ...(element.position || {}) },
    h5Frame,
  }
  draggingElementId.value = id
  selectElement(id, event)
  window.addEventListener('pointermove', handleElementDrag)
  window.addEventListener('pointerup', stopElementDrag, { once: true })
  window.addEventListener('pointercancel', stopElementDrag, { once: true })
  event.currentTarget.setPointerCapture?.(event.pointerId)
  // 音视频播放器覆盖了整个组件。允许播放器的 pointerdown 启动拖动，但不
  // 阻止它的默认点击行为，这样点击播放/暂停等原生控件仍然可用。
  const isNativeMediaPlayer = event.currentTarget?.classList?.contains('workspace-media-player')
  if (!isNativeMediaPlayer) event.preventDefault()
}
const handleElementDrag = (event) => {
  const state = dragState.value
  const element = state ? elementById(state.id) : null
  if (!state || !element) return
  const nextX = Number(state.startPosition.x || 0) + ((event.clientX - state.startX) / state.rect.width) * 100
  const nextY = Number(state.startPosition.y || 0) + ((event.clientY - state.startY) / state.rect.height) * 100
  element.position = {
    ...element.position,
    // 普通结构化画布也允许拖到画布外，保留真实坐标而不是吸回边缘。
    x: Number(nextX.toFixed(2)),
    y: Number(nextY.toFixed(2)),
  }
}
const stopElementDrag = () => {
  if (dragState.value?.id && current.value) markSlideComponentDirty(current.value, dragState.value.id)
  window.removeEventListener('pointermove', handleElementDrag)
  window.removeEventListener('pointercancel', stopElementDrag)
  const captureTarget = dragState.value?.captureTarget
  dragState.value?.h5Frame?.contentWindow?.postMessage({ source: 'a12-h5-host', type: 'a12-h5-editing', active: false }, '*')
  if (captureTarget?.hasPointerCapture?.(dragState.value?.pointerId)) captureTarget.releasePointerCapture(dragState.value.pointerId)
  dragState.value = null
  draggingElementId.value = null
}
const selectElement = (id, event) => {
  event?.stopPropagation()
  const element = current.value?.elements?.find((item) => String(item.id) === String(id))
  if (!element) return
  pendingHtmlPanelSelection = null
  selectedElementId.value = element.id
}
const selectElementFromPanel = (id) => {
  if (workspaceUsesHtmlEditor.value) {
    const normalizedId = String(id ?? '')
    if (!normalizedId) return
    const controller = activeHtmlController()
    if (controller?.selectById?.(normalizedId)) {
      pendingHtmlPanelSelection = null
      return
    }
    // 右侧列表可能先于 iframe 的编辑控制器完成初始化，记录一次选择，
    // 在 iframe load 后补选，避免右侧已选中但左侧没有选择框。
    pendingHtmlPanelSelection = { slide: current.value, id: normalizedId }
    void nextTick(() => {
      if (pendingHtmlPanelSelection?.slide !== current.value) return
      const retryController = activeHtmlController()
      if (retryController?.selectById?.(normalizedId)) pendingHtmlPanelSelection = null
    })
    return
  }
  selectElement(id)
}
const markSlideComponentDirty = (slide = current.value, componentId = selectedElementId.value, { structure = false } = {}) => {
  if (!slide) return
  pendingComponentSync.set(slide, componentId || true)
  slide.dirty = true
  localChangeVersion += 1
  if (structure) localStructureVersion = localChangeVersion
  if (projectId.value && (savingPage.value || pageSavePromise || orderSavePromise)) autosaveQueued = true
}
const clearElementSelection = () => {
  if (workspaceUsesHtmlEditor.value) activeHtmlController()?.clearSelection()
  selectedElementId.value = null
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
}
const updatePageField = ({ key, value } = {}) => {
  if (!current.value || !['title', 'notes', 'pageType', 'backgroundColor'].includes(key)) return
  const nextValue = String(value ?? '')
  if (workspaceUsesHtmlEditor.value && ['title', 'description'].includes(key)) activeHtmlController()?.updatePageField?.(key, nextValue)
  if (key === 'title') {
    current.value.title = nextValue
    current.value.page_title = nextValue
    const titleElement = current.value.elements?.find((element) => element.target === 'title')
    if (titleElement) titleElement.content = nextValue
  } else if (key === 'notes') {
    current.value.notes = nextValue
  } else if (key === 'pageType') {
    const pageType = nextValue || 'content'
    current.value.pageType = pageType
    current.value.page_type = pageType
  } else if (key === 'backgroundColor') {
    current.value.backgroundColor = /^#[0-9a-f]{3,8}$/i.test(nextValue) ? nextValue : '#f9fbff'
    current.value.background_color = current.value.backgroundColor
  }
  markSlideComponentDirty(current.value, `page:${key}`)
  // 非项目模式没有项目页面的深度 watch，需要主动回写本地草稿。
  if (!projectId.value) saveCurrentPresentationDraft()
}
const updatePageTheme = (themeId) => {
  if (!current.value || !themes.some((item) => item.id === themeId)) return
  current.value.theme = themeId
  if (!current.value.html) refreshStructuredHtmlCanvas(current.value)
  markSlideComponentDirty(current.value, 'page:theme')
}
const updatePageLayout = (layout) => {
  if (!current.value) return
  current.value.layout = String(layout || '') || '图文并置'
  if (!current.value.html) refreshStructuredHtmlCanvas(current.value)
  markSlideComponentDirty(current.value, 'page:layout')
}
const updatePageBackground = async ({ resourceId, resource } = {}) => {
  const id = String(resourceId || resource?.id || '').trim()
  if (!current.value || !id) return
  try {
    const downloaded = unwrapResponse(await downloadResource(id))
    const source = downloaded?.download_url || downloaded?.downloadUrl || downloaded?.url || downloaded?.preview_url
      || resource?.fileUrl || resource?.file_url || resource?.raw?.file_url || resource?.thumbnail || ''
    if (!source) throw new Error('该图片暂时没有可用的预览地址')
    const name = String(resource?.name || resource?.file_name || `图片资源 ${id}`)
    current.value.background = { resource_id: id, resourceId: id, name, src: String(source), type: 'image' }
    current.value.backgroundResourceId = id
    current.value.backgroundResourceName = name
    current.value.backgroundImage = String(source)
    current.value.background_image = String(source)
    markSlideComponentDirty(current.value, `page-background:${id}`)
    WorkspaceMessage.success('页面背景已更新')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '页面背景更新失败')
  }
}
const clearPageBackground = () => {
  if (!current.value) return
  current.value.background = null
  current.value.backgroundResourceId = ''
  current.value.backgroundResourceName = ''
  current.value.backgroundImage = ''
  current.value.background_image = ''
  markSlideComponentDirty(current.value, 'page:background')
}
const updateElementStyle = ({ key, value }) => {
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateStyle(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value) return
  selectedElement.value.style = { ...selectedElement.value.style, [key]: value }
  if (selectedElement.value.type === 'subject') {
    selectedElement.value.subjectStyle = { ...(selectedElement.value.subjectStyle || selectedElement.value.style), [key]: value }
    selectedElement.value.subject_style = selectedElement.value.subjectStyle
    selectedElement.value.subjectValidation = null
    selectedElement.value.subject_validation = null
  }
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementStyleMap = (value) => {
  const style = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateStyleMap?.(style)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || selectedElement.value.type !== 'subject') return
  selectedElement.value.style = { ...selectedElement.value.style, ...style }
  selectedElement.value.subjectStyle = { ...style }
  selectedElement.value.subject_style = selectedElement.value.subjectStyle
  selectedElement.value.subjectValidation = null
  selectedElement.value.subject_validation = null
  refreshStructuredHtmlCanvas(current.value)
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementPosition = ({ key, value }) => {
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updatePosition(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value) return
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return
  const position = { ...selectedElement.value.position, [key]: Number.isFinite(numericValue) ? numericValue : 0 }
  const width = clampNumber(Number(position.width) || 4, 4, 100)
  const height = clampNumber(Number(position.height) || 4, 4, 100)
  selectedElement.value.position = {
    ...position,
    width,
    height,
    // 位置允许为负数或超过 100%，以支持元素部分移出画布。
    x: Number((Number.isFinite(Number(position.x)) ? Number(position.x) : 0).toFixed(2)),
    y: Number((Number.isFinite(Number(position.y)) ? Number(position.y) : 0).toFixed(2)),
    rotation: Number(clampNumber(Number(position.rotation) || 0, -180, 180).toFixed(2)),
    zIndex: Math.round(clampNumber(Number(position.zIndex) || 0, 0, 99)),
  }
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateWorkspaceElementPosition = (id, key, value) => {
  if (!id) return false
  if (workspaceUsesHtmlEditor.value) {
    const controller = activeHtmlController()
    if (!controller?.selectById?.(id)) return false
    controller.updatePosition(key, value)
    markSlideComponentDirty(current.value, id)
    return true
  }
  selectedElementId.value = id
  updateElementPosition({ key, value })
  return true
}
const arrangeSelectedElement = (action) => {
  const selected = workspaceSelectedElement.value
  const elements = workspaceElements.value || []
  if (!selected?.id || !elements.length) return WorkspaceMessage.info('请先选择一个页面组件')
  const zValues = elements.map((element) => Number(element?.position?.zIndex ?? 0)).filter(Number.isFinite)
  const currentZ = Number(selected.position?.zIndex ?? 0)
  const maxZ = Math.max(0, ...zValues)
  const minZ = Math.min(0, ...zValues)
  const nextZ = action === 'front'
    ? Math.min(99, maxZ + 1)
    : action === 'back'
      ? Math.max(0, minZ)
      : action === 'up'
        ? Math.min(99, currentZ + 1)
        : Math.max(0, currentZ - 1)
  updateWorkspaceElementPosition(selected.id, 'zIndex', nextZ)
}
const alignSelectedElement = (alignment) => {
  const selected = workspaceSelectedElement.value
  if (!selected?.id) return WorkspaceMessage.info('请先选择一个页面组件')
  const position = selected.position || {}
  const width = Math.min(100, Math.max(1, Number(position.width) || 30))
  const height = Math.min(100, Math.max(1, Number(position.height) || 20))
  const nextPosition = {
    left: { x: 0 },
    center: { x: (100 - width) / 2 },
    right: { x: 100 - width },
    top: { y: 0 },
    middle: { y: (100 - height) / 2 },
    bottom: { y: 100 - height },
  }[alignment]
  if (!nextPosition) return
  Object.entries(nextPosition).forEach(([key, value]) => updateWorkspaceElementPosition(selected.id, key, Number(value.toFixed(2))))
}
const distributeElements = (direction) => {
  const elements = (workspaceElements.value || []).filter((element) => element?.id && element?.position)
  if (elements.length < 3) return WorkspaceMessage.info('至少需要 3 个页面组件才能均匀分布')
  const horizontal = direction === 'horizontal'
  const ordered = [...elements].sort((a, b) => Number(a.position?.[horizontal ? 'x' : 'y'] || 0) - Number(b.position?.[horizontal ? 'x' : 'y'] || 0))
  const sizeKey = horizontal ? 'width' : 'height'
  const positionKey = horizontal ? 'x' : 'y'
  const totalSize = ordered.reduce((sum, element) => sum + Math.max(1, Number(element.position?.[sizeKey]) || 1), 0)
  const gap = Math.max(0, (100 - totalSize) / (ordered.length - 1))
  let cursor = 0
  ordered.forEach((element) => {
    updateWorkspaceElementPosition(element.id, positionKey, Number(cursor.toFixed(2)))
    cursor += Math.max(1, Number(element.position?.[sizeKey]) || 1) + gap
  })
}
const updateElementContent = (value) => {
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateContent(value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value) return
  const content = String(value ?? '')
  selectedElement.value.content = content
  if (selectedElement.value.target === 'title') current.value.title = content
  if (selectedElement.value.target === 'description') current.value.description = content
  if (selectedElement.value.target === 'footer') current.value.footer = content
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementField = ({ key, value }) => {
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateField(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || !['src', 'alt', 'url', 'subjectType', 'autoplay', 'controls', 'resourceId', 'resourceName', 'resourceType'].includes(key)) return
  if (key === 'src') selectedElement.value.src = String(value || '') || createMockImageSrc(selectedElement.value.content || '课堂图片')
  if (key === 'alt') selectedElement.value.alt = String(value || '').slice(0, 80)
  if (key === 'url') {
    selectedElement.value.url = String(value || '')
    if (['audio', 'video'].includes(selectedElement.value.type)) selectedElement.value.src = selectedElement.value.url
  }
  if (key === 'subjectType') {
    const rawType = String(value || 'geometry')
    selectedElement.value.subjectType = normalizeSubjectToolType(rawType)
    selectedElement.value.subject_type = selectedElement.value.subjectType
    selectedElement.value.data = normalizeSubjectToolData(selectedElement.value.data, rawType)
    selectedElement.value.render = subjectToolDefaultRenderHint(selectedElement.value.subjectType)
    selectedElement.value.subjectRender = selectedElement.value.render
    selectedElement.value.subject_render = selectedElement.value.subjectRender
    selectedElement.value.subjectValidation = null
    selectedElement.value.subject_validation = null
    refreshStructuredHtmlCanvas(current.value)
  }
  if (key === 'autoplay' || key === 'controls') selectedElement.value[key] = Boolean(value)
  if (key === 'resourceId') { selectedElement.value.resourceId = String(value || ''); selectedElement.value.resource_id = selectedElement.value.resourceId }
  if (key === 'resourceName') selectedElement.value.resourceName = String(value || '')
  if (key === 'resourceType') selectedElement.value.resourceType = String(value || '')
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementRender = (value) => {
  const render = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateRender?.(render)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || selectedElement.value.type !== 'subject') return
  selectedElement.value.render = { ...render }
  selectedElement.value.subjectRender = selectedElement.value.render
  selectedElement.value.subject_render = selectedElement.value.render
  selectedElement.value.subjectRenderHint = Object.keys(render).length
    ? selectedElement.value.render
    : subjectToolDefaultRenderHint(selectedElement.value.subjectType || 'geometry')
  selectedElement.value.subject_render_hint = selectedElement.value.subjectRenderHint
  selectedElement.value.subjectValidation = null
  selectedElement.value.subject_validation = null
  refreshStructuredHtmlCanvas(current.value)
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementH5Config = ({ key, value } = {}) => {
  if (!key) return
  if (workspaceSelectedElement.value?.type === 'h5') return WorkspaceMessage.warning('H5 运行参数由生成结果提供，请使用“重新生成 H5”修改')
  const previous = workspaceSelectedElement.value?.h5Config || workspaceSelectedElement.value?.h5_config || {}
  const next = normalizeH5RuntimeConfig({ ...previous, [key]: value })
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateH5Config(next)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || selectedElement.value.type !== 'h5') return
  selectedElement.value.h5Config = next
  selectedElement.value.h5_config = next
  refreshStructuredHtmlCanvas(current.value)
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const resourceDownloadUrl = (downloaded, resource) => downloaded?.download_url || downloaded?.downloadUrl || downloaded?.url || downloaded?.preview_url
  || resource?.fileUrl || resource?.file_url || resource?.raw?.file_url || resource?.previewUrl || resource?.thumbnail || ''
const bindElementResource = async ({ resource, type } = {}) => {
  const resourceId = String(resource?.id || resource?.resource_id || '').trim()
  const elementType = String(type || workspaceSelectedElement.value?.type || '').trim()
  if (!resourceId || !['image', 'audio', 'video'].includes(elementType)) return
  if (workspaceSelectedElement.value?.type && workspaceSelectedElement.value.type !== elementType) {
    return WorkspaceMessage.warning('请选择与当前元素类型一致的素材')
  }
  try {
    const downloaded = unwrapResponse(await downloadResource(resourceId))
    const source = String(resourceDownloadUrl(downloaded, resource) || '').trim()
    if (!source) throw new Error('素材暂时没有可用的访问地址')
    const name = String(resource?.name || resource?.file_name || `资源 ${resourceId}`).trim()
    updateElementField({ key: elementType === 'image' ? 'src' : 'url', value: source })
    updateElementField({ key: 'resourceId', value: resourceId })
    updateElementField({ key: 'resourceName', value: name })
    updateElementField({ key: 'resourceType', value: elementType })
    WorkspaceMessage.success(`${elementType === 'image' ? '图片' : elementType === 'audio' ? '音频' : '视频'}已从个人资源库插入`)
  } catch (error) {
    WorkspaceMessage.error(error?.message || '素材插入失败，请确认访问权限')
  }
}
const uploadElementResource = async ({ file, type } = {}) => {
  if (!(file instanceof File) || !['image', 'audio', 'video'].includes(String(type || ''))) return
  try {
    const uploaded = unwrapResponse(await uploadResource(file)) || {}
    const resourceId = uploaded?.id || uploaded?.resource_id || uploaded?.resourceId
    if (!resourceId) throw new Error('上传成功但未返回资源 ID')
    const resource = normalizeWorkspaceResource({ ...uploaded, id: resourceId, file_name: uploaded.file_name || file.name, file_type: uploaded.file_type || file.type })
    workspaceResources.value = [resource, ...workspaceResources.value.filter((item) => String(item.id) !== String(resourceId))]
    await bindElementResource({ resource, type })
  } catch (error) {
    WorkspaceMessage.error(error?.message || '上传素材失败，请稍后重试')
  }
}
const updateElementData = (value) => {
  if (workspaceUsesHtmlEditor.value) {
    activeHtmlController()?.updateData(value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || (selectedElement.value.type === 'subject' ? (!value || typeof value !== 'object' || Array.isArray(value)) : !Array.isArray(value))) return
  if (selectedElement.value.type === 'chart') {
    selectedElement.value.data = value.slice(0, 8).map((item, index) => ({
      label: String(item?.label || `数据${index + 1}`).slice(0, 10),
      value: Math.max(0, Math.min(100, Number(item?.value) || 0)),
    }))
  } else if (selectedElement.value.type === 'table') {
    selectedElement.value.data = value
  } else if (selectedElement.value.type === 'subject') {
    const subjectType = normalizeSubjectToolType(selectedElement.value.subjectType || selectedElement.value.subject_type)
    selectedElement.value.data = normalizeSubjectToolData(value, subjectType)
    selectedElement.value.subjectValidation = null
    selectedElement.value.subject_validation = null
    refreshStructuredHtmlCanvas(current.value)
  } else return
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const validateSubjectTool = async () => {
  const target = workspaceSelectedElement.value
  if (!target || target.type !== 'subject') return
  const targetId = String(target.id || '')
  const payload = componentValidationPayload(target)
  if (!payload) return

  subjectValidationPending.value = true
  try {
    // 这是显式的“验证并应用”操作，始终命中后端，不使用保存时的本地缓存。
    const result = unwrapResponse(await validateProjectComponent(payload)) || {}
    if (String(workspaceSelectedElement.value?.id || '') !== targetId) return

    const controllerApplied = workspaceUsesHtmlEditor.value
      ? Boolean(activeHtmlController()?.applySubjectValidation?.(result))
      : false
    if (!controllerApplied && selectedElement.value?.type === 'subject' && String(selectedElement.value.id) === targetId) {
      const normalized = result.normalized && typeof result.normalized === 'object' ? result.normalized : {}
      const rawType = normalized.type || selectedElement.value.subjectType || 'geometry'
      const nextType = normalizeSubjectToolType(rawType)
      selectedElement.value.subjectType = nextType
      selectedElement.value.subject_type = nextType
      selectedElement.value.data = normalizeSubjectToolData(normalized.data === undefined ? selectedElement.value.data : normalized.data, rawType)
      selectedElement.value.render = normalized.render && typeof normalized.render === 'object' && !Array.isArray(normalized.render)
        ? normalized.render
        : (selectedElement.value.render || selectedElement.value.subjectRender || {})
      selectedElement.value.subjectRender = selectedElement.value.render
      selectedElement.value.subject_render = selectedElement.value.subjectRender
      selectedElement.value.subjectStyle = normalized.style && typeof normalized.style === 'object' && !Array.isArray(normalized.style)
        ? normalized.style
        : (selectedElement.value.subjectStyle || selectedElement.value.style || {})
      selectedElement.value.subject_style = selectedElement.value.subjectStyle
      selectedElement.value.style = { ...(selectedElement.value.style || {}), ...selectedElement.value.subjectStyle }
      selectedElement.value.subjectRenderHint = result.render_hint && typeof result.render_hint === 'object' && !Array.isArray(result.render_hint)
        ? result.render_hint
        : subjectToolDefaultRenderHint(nextType)
      selectedElement.value.subject_render_hint = selectedElement.value.subjectRenderHint
      selectedElement.value.subjectValidation = {
        valid: result.valid !== false,
        errors: Array.isArray(result.errors) ? result.errors : [],
        warnings: Array.isArray(result.warnings) ? result.warnings : [],
        normalized: {
          ...normalized,
          type: nextType,
          data: selectedElement.value.data,
          render: selectedElement.value.render,
          style: selectedElement.value.subjectStyle,
        },
        render_hint: selectedElement.value.subjectRenderHint,
      }
      selectedElement.value.subject_validation = selectedElement.value.subjectValidation
      refreshStructuredHtmlCanvas(current.value)
      markSlideComponentDirty(current.value, selectedElement.value.id)
    }

    const errors = Array.isArray(result.errors) ? result.errors.filter(Boolean) : []
    const warnings = Array.isArray(result.warnings) ? result.warnings.filter(Boolean) : []
    if (result.valid === false) {
      WorkspaceMessage.warning(`学科工具未通过后端校验${errors.length ? `：${errors.join('；')}` : ''}`)
    } else {
      WorkspaceMessage.success(warnings.length ? `已通过校验：${warnings.join('；')}` : '学科工具已通过后端校验并应用规范化配置')
    }
  } catch (error) {
    WorkspaceMessage.error(error?.message || '学科工具校验失败，请稍后重试')
  } finally {
    subjectValidationPending.value = false
  }
}
const handleImageError = (element) => {
  if (!element || String(element.src || '').startsWith('data:image/svg+xml')) return
  element.src = createMockImageSrc(elementContent(element) || '图片加载失败')
  WorkspaceMessage.warning('图片加载失败，已恢复示例图')
}
const elementTypeLabels = { text: '文本', formula: '公式', image: '图片', shape: '形状', chart: '图表', audio: '音频', video: '视频', table: '表格', h5: 'H5组件', subject: '学科工具' }
const shapeDefaults = {
  rectangle: { shapeKind: 'rectangle', label: '矩形', borderRadius: 0 },
  rounded: { shapeKind: 'rounded', label: '圆角矩形', borderRadius: 14 },
  circle: { shapeKind: 'circle', label: '圆形', borderRadius: 50 },
  diamond: { shapeKind: 'diamond', label: '菱形', borderRadius: 8 },
  triangle: { shapeKind: 'triangle', label: '三角形', borderRadius: 8 },
}
const createElement = (type, options = {}, positionOverride = {}) => {
  const preset = allElementPresets.find((item) => item.type === type) || elementPresets[0]
  const count = (current.value?.elements || []).filter((item) => item.type === type).length + 1
  const id = `${type}-${Date.now()}-${elementSequence++}`
  const element = cloneElementData(preset)
  element.id = id
  element.name = `${elementTypeLabels[type] || '元素'} ${count}`
  element.target = null
  element.position = { ...element.position, x: Math.min(74, Number(element.position?.x || 8) + (count - 1) * 3), y: Math.min(72, Number(element.position?.y || 12) + (count - 1) * 3) }
  if (type === 'shape') {
    const shape = shapeDefaults[options.shapeKind] || shapeDefaults.rectangle
    element.shapeKind = shape.shapeKind
    element.name = `${elementTypeLabels[type]}·${shape.label} ${count}`
    element.content = ''
    element.style = { ...element.style, borderRadius: shape.borderRadius }
  }
  if (type === 'text') {
    element.content = '新增文本，可在右侧编辑'
    element.position = { ...element.position, width: 28, height: 12 }
    element.style = { ...element.style, fontSize: 20, fontWeight: 500, lineHeight: 1.4 }
  }
  if (type === 'formula') element.content = 'a² + b² = c²'
  if (type === 'image') { element.content = '新增图片'; element.src = createMockImageSrc('新增图片') }
  if (type === 'chart') { element.content = '新增图表'; element.data = [{ label: '一', value: 68 }, { label: '二', value: 82 }, { label: '三', value: 55 }] }
  if (type === 'audio') element.content = '新增音频讲解'
  if (type === 'video') element.content = '新增视频演示'
  if (type === 'table') element.content = '新增数据表格'
  if (type === 'h5') {
    element.content = '新增 H5 互动'
    element.moduleType = 'unknown'
    element.module_type = 'unknown'
    element.h5Config = normalizeH5RuntimeConfig(element.h5Config || element.h5_config || {})
    element.h5_config = element.h5Config
  }
  if (type === 'subject') {
    const subjectType = normalizeSubjectToolType(options.subjectType || 'geometry')
    element.content = '新增学科工具'
    element.subjectType = subjectType
    element.subject_type = subjectType
    element.data = createSubjectToolData(subjectType)
    element.render = subjectToolDefaultRenderHint(subjectType)
    element.subjectRender = element.render
    element.subject_render = element.subjectRender
    element.subjectStyle = { ...(element.style || {}) }
    element.subject_style = element.subjectStyle
  }
  element.position = { ...element.position, ...positionOverride }
  return element
}
const insertElement = (type, options = {}, positionOverride = {}, preparedElement = null) => {
  if (!current.value) return
  const element = preparedElement ? cloneElementData(preparedElement) : createElement(type, options)
  element.position = { ...(element.position || {}), ...positionOverride }
  if (workspaceUsesHtmlEditor.value) {
    const controller = activeHtmlController()
    if (!controller) {
      pendingHtmlToolbarTool = { slide: current.value, tool: { id: type, ...options } }
      activeTool.value = type
      return
    }
    const inserted = controller.insertElement(type, options)
    if (!inserted) {
      WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
      return
    }
    return
  }
  current.value.elements.push(element)
  selectedElementId.value = element.id
  markSlideComponentDirty(current.value, element.id)
  WorkspaceMessage.success(`${elementTypeLabels[type] || '元素'}已添加`)
}
const handleToolSelect = (tool) => {
  if (!current.value) return
  if (!workspaceUsesHtmlEditor.value) {
    beginElementPlacement(tool)
    return
  }
  const controller = activeHtmlController()
  if (!controller) {
    pendingHtmlToolbarTool = { slide: current.value, tool }
    activeTool.value = tool?.id || tool || ''
    return
  }
  const inserted = controller.insertElement(tool?.id || tool, tool || {})
  activeTool.value = ''
  if (!inserted) {
    pendingHtmlToolbarTool = { slide: current.value, tool }
    WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
  }
}
const interactiveAssetFromModule = (module) => {
  const moduleId = module?.module_id || module?.moduleId
  const metadata = module?.metadata && typeof module.metadata === 'object' && !Array.isArray(module.metadata) ? module.metadata : {}
  const rawModuleType = String(module?.module_type || module?.moduleType || metadata.module_type || '').trim()
  const moduleType = normalizeInteractiveModuleType(rawModuleType)
  const h5Config = module?.h5_config || module?.h5Config
  const usageSuggestions = Array.isArray(module?.usage_suggestions)
    ? module.usage_suggestions
    : (Array.isArray(module?.usageSuggestions) ? module.usageSuggestions : [])
  return {
    module_id: moduleId,
    title: module?.title || module?.name || module?.content || 'H5 组件',
    module_type: moduleType,
    moduleType,
    module_type_raw: rawModuleType || 'unknown',
    topic: module?.topic || metadata.topic || '',
    html: module?.html || '',
    h5_config: h5Config && typeof h5Config === 'object' && !Array.isArray(h5Config) ? h5Config : {},
    h5Config: h5Config && typeof h5Config === 'object' && !Array.isArray(h5Config) ? h5Config : {},
    embed_mode: ['standalone', 'slide_fragment'].includes(module?.embed_mode || module?.embedMode) ? (module.embed_mode || module.embedMode) : 'standalone',
    usage_suggestions: usageSuggestions,
    usageSuggestions,
    metadata,
    generatedBy: module?.generatedBy || module?.generated_by || (module?.html ? 'api-144' : ''),
    generated_by: module?.generated_by || module?.generatedBy || (module?.html ? 'api-144' : ''),
  }
}
const appendInteractiveAsset = (slide, module) => {
  if (!slide || !module?.html) return
  const asset = interactiveAssetFromModule(module)
  const moduleId = String(asset.module_id || '')
  const assets = Array.isArray(slide.interactive_assets) ? slide.interactive_assets : []
  slide.interactive_assets = [
    ...assets.filter((item) => String(item?.module_id || '') !== moduleId),
    asset,
  ]
}
const createInteractiveElement = (module, position = {}) => {
  const asset = interactiveAssetFromModule(module)
  const moduleId = String(asset.module_id || `interactive_${Date.now()}`)
  const sourceH5Config = module?.h5_config || module?.h5Config
  const h5Config = sourceH5Config && typeof sourceH5Config === 'object' && !Array.isArray(sourceH5Config) && Object.keys(sourceH5Config).length
    ? normalizeH5RuntimeConfig(sourceH5Config)
    : {}
  return {
    id: `h5-${moduleId}`,
    type: 'h5',
    name: asset.title,
    content: asset.title,
    html: asset.html,
    moduleId,
    module_id: moduleId,
    moduleType: asset.module_type,
    module_type: asset.module_type,
    module_type_raw: asset.module_type_raw,
    topic: asset.topic,
    h5Config,
    h5_config: h5Config,
    embedMode: asset.embed_mode,
    embed_mode: asset.embed_mode,
    usageSuggestions: asset.usage_suggestions,
    usage_suggestions: asset.usage_suggestions,
    metadata: asset.metadata,
    generatedBy: asset.generatedBy || 'api-144',
    generated_by: asset.generated_by || 'api-144',
    position: { x: 8, y: 47, width: 84, height: 38, rotation: 0, zIndex: 3, ...position },
    style: { color: '#ff6b3f', backgroundColor: '#fff7ed', borderColor: '#fed7aa', borderWidth: 1, borderRadius: 12, opacity: 100 },
  }
}
const interactivePptContext = () => {
  const asRecord = (value) => {
    if (!value) return null
    if (typeof value === 'string') return parseJson(value, null)
    return typeof value === 'object' && !Array.isArray(value) ? value : null
  }
  const roots = [project.value, current.value, route.query]
  const contexts = []
  const visit = (value, depth = 0) => {
    const record = asRecord(value)
    if (!record || depth > 2 || contexts.includes(record)) return
    contexts.push(record)
    ;['metadata', 'outline', 'plan_json', 'generation_options', 'known_context', 'context', 'request_context'].forEach((key) => visit(record[key], depth + 1))
  }
  roots.forEach((root) => visit(root))
  slides.forEach((slide) => visit(slide?.metadata))
  const field = (...names) => {
    for (const context of contexts) {
      for (const name of names) {
        const value = String(context?.[name] ?? '').trim()
        if (value) return value
      }
    }
    return ''
  }
  const headers = slides.map((slide) => String(slide?.eyebrow || '')).filter(Boolean).join(' · ')
  const grade = field('grade', 'stage', 'class_level', 'audience') || (headers.match(/(小学|初中|高中|大学|[一二三四五六七八九十\d]+年级)/)?.[0] || '')
  const subject = field('subject', 'course_subject', 'discipline') || (headers.match(/(语文|数学|英语|物理|化学|生物|历史|地理|政治|道德与法治|科学|信息技术|音乐|美术|体育)/)?.[0] || '')
  return {
    subject,
    grade,
    requirements: field('requirements', 'interactive_requirements'),
  }
}
const openInteractiveDialog = (sourceElement = null) => {
  cancelCanvasPlacement()
  interactiveRegenerateTarget.value = sourceElement?.type === 'h5' && sourceElement?.id ? { id: String(sourceElement.id) } : null
  const slideTitle = String(current.value?.title || '本页内容').trim()
  const pptContext = interactivePptContext()
  const sourceMetadata = sourceElement?.metadata && typeof sourceElement.metadata === 'object' && !Array.isArray(sourceElement.metadata) ? sourceElement.metadata : {}
  const sourceType = normalizeInteractiveModuleType(sourceElement?.module_type || sourceElement?.moduleType || sourceMetadata.module_type)
  const sourceKnowledgePoints = sourceMetadata.knowledge_points || sourceMetadata.knowledgePoints
  interactiveForm.title = sourceElement?.name || sourceElement?.content || `${slideTitle} · 课堂互动`
  interactiveForm.topic = sourceElement?.topic || sourceMetadata.topic || slideTitle
  interactiveForm.module_type = sourceType === 'unknown' ? 'animation' : sourceType
  interactiveForm.subject = sourceMetadata.subject || pptContext.subject
  interactiveForm.grade = sourceMetadata.grade || pptContext.grade
  interactiveForm.knowledge_points = Array.isArray(sourceKnowledgePoints) ? sourceKnowledgePoints.join('，') : String(sourceKnowledgePoints || current.value?.description || '').trim()
  interactiveForm.requirements = sourceMetadata.requirements || pptContext.requirements
  interactiveForm.theme = theme.value?.name || ''
  interactiveForm.embed_mode = ['standalone', 'slide_fragment'].includes(sourceElement?.embed_mode || sourceElement?.embedMode) ? (sourceElement.embed_mode || sourceElement.embedMode) : 'standalone'
  interactiveDialogVisible.value = true
}
const regenerateSelectedH5 = () => {
  const element = workspaceSelectedElement.value
  if (!element || element.type !== 'h5') return WorkspaceMessage.warning('请先选择一个 H5 组件')
  openInteractiveDialog(element)
}
const interactiveGenerationErrorMessage = (error) => {
  const detail = String(error?.response?.data?.message || error?.message || '')
  if (error?.code === 'ECONNABORTED' || /timeout|超时/i.test(detail)) {
    return 'H5 组件生成超时，请重试；系统会优先返回可直接使用的课堂互动模板。'
  }
  return detail || 'H5 组件生成失败'
}
const handleGenerateInteractiveModule = async () => {
  const title = interactiveForm.title.trim()
  const topic = interactiveForm.topic.trim()
  if (!title || !topic) return WorkspaceMessage.warning('请先填写 H5 标题和主题')
  interactiveGenerating.value = true
  WorkspaceMessage.info('正在生成 H5 组件，请稍候…', { duration: 0, showClose: false })
  try {
    const context = workspaceContextPayload()
    const knowledgePoints = interactiveForm.knowledge_points
      .split(/[,，\n]/)
      .map((item) => item.trim())
      .filter(Boolean)
    const contextRequirements = [
      interactiveForm.requirements.trim(),
      context.resource_ids.length ? `可参考资料资源 ID：${context.resource_ids.join('、')}` : '',
      context.community?.title ? `社区参考：${context.community.title}` : '',
    ].filter(Boolean).join('\n')
    const response = unwrapResponse(await generateInteractiveModule({
      title,
      topic,
      module_type: interactiveForm.module_type,
      subject: interactiveForm.subject.trim() || undefined,
      grade: interactiveForm.grade.trim() || undefined,
      knowledge_points: knowledgePoints,
      requirements: contextRequirements || undefined,
      theme: interactiveForm.theme.trim() || undefined,
      embed_mode: interactiveForm.embed_mode,
      language: interactiveForm.language || 'zh-CN',
    }))
    if (!response?.html) throw new Error('H5 组件接口未返回可预览的 HTML 内容')
    // API-144 在未配置模型时会返回本地可运行的降级 HTML（metadata.model_used=false）。
    // 只要服务返回完整 HTML，就应该允许教师预览和插入，不能把可用结果误报成失败。
    interactiveModule.value = interactiveAssetFromModule(response)
    if (interactiveModule.value.module_type === 'unknown') WorkspaceMessage.warning('接口未返回可识别的 module_type，已标记为未识别类型；请重新选择类型后生成')
    interactivePreviewSource.value = 'generated'
    interactiveDialogVisible.value = false
    interactivePreviewVisible.value = true
    WorkspaceMessage.success('H5 组件已生成')
  } catch (error) {
    WorkspaceMessage.error(interactiveGenerationErrorMessage(error))
  } finally {
    interactiveGenerating.value = false
  }
}
const previewInteractiveElement = (element) => {
  if (!element?.html) return WorkspaceMessage.warning('该 H5 组件没有可预览内容')
  interactiveModule.value = interactiveAssetFromModule({
    ...element,
    module_id: element.module_id || element.moduleId,
    module_type: element.module_type || element.moduleType,
    embed_mode: element.embed_mode || element.embedMode,
    usage_suggestions: element.usage_suggestions || element.usageSuggestions,
  })
  interactivePreviewSource.value = 'existing'
  interactivePreviewVisible.value = true
}
const updateInteractivePreviewScale = () => {
  const viewportWidth = interactivePreviewViewportRef.value?.clientWidth || 1280
  interactivePreviewScale.value = Math.min(1, Math.max(0.1, viewportWidth / 1280))
}
watch(interactivePreviewVisible, async (visible) => {
  interactivePreviewResizeObserver?.disconnect()
  interactivePreviewResizeObserver = null
  if (!visible) return
  await nextTick()
  updateInteractivePreviewScale()
  if (typeof ResizeObserver !== 'undefined' && interactivePreviewViewportRef.value) {
    interactivePreviewResizeObserver = new ResizeObserver(updateInteractivePreviewScale)
    interactivePreviewResizeObserver.observe(interactivePreviewViewportRef.value)
  }
})
const reopenInteractiveDialog = () => {
  interactivePreviewVisible.value = false
  interactiveDialogVisible.value = true
}
const insertGeneratedInteractiveModule = async (target = 'current') => {
  if (!interactiveModule.value?.html) return WorkspaceMessage.warning('请先生成 H5 组件')
  const module = interactiveModule.value
  const replacementTarget = interactiveRegenerateTarget.value
  if (target === 'current' && replacementTarget?.id) {
    if (workspaceUsesHtmlEditor.value) {
      const controller = await waitForHtmlController(current.value)
      const existing = htmlElements.value.find((item) => String(item?.id) === replacementTarget.id)
      if (!existing) return WorkspaceMessage.warning('H5 替换目标已不存在，请先刷新页面后重试')
      if (!controller) return WorkspaceMessage.warning('当前页面尚未完成加载，请重新打开工作台后重试')
      controller.deleteSelected?.(replacementTarget.id)
      const inserted = controller.insertInteractive?.(module, existing.position)
      if (!inserted) return WorkspaceMessage.warning('H5 替换失败，请先刷新页面后重试')
      if (Array.isArray(current.value?.interactive_assets)) {
        const previousModuleId = String(existing.module_id || existing.moduleId || '')
        current.value.interactive_assets = current.value.interactive_assets.filter((asset) => String(asset?.module_id || asset?.moduleId || '') !== previousModuleId)
      }
      appendInteractiveAsset(current.value, module)
      markSlideComponentDirty(current.value, replacementTarget.id)
      interactiveRegenerateTarget.value = null
      interactivePreviewVisible.value = false
      interactiveModule.value = null
      WorkspaceMessage.success('H5 已重新生成并替换，正在自动保存')
      return
    }
    const index = current.value?.elements?.findIndex((item) => String(item?.id) === replacementTarget.id) ?? -1
    if (index >= 0) {
      const previous = current.value.elements[index]
      const replacement = createInteractiveElement(module, previous.position || {})
      replacement.id = previous.id
      replacement.style = { ...(previous.style || {}), ...(replacement.style || {}) }
      current.value.elements.splice(index, 1, replacement)
      if (Array.isArray(current.value.interactive_assets)) {
        const previousModuleId = String(previous.module_id || previous.moduleId || '')
        current.value.interactive_assets = current.value.interactive_assets.filter((asset) => String(asset?.module_id || asset?.moduleId || '') !== previousModuleId)
      }
      appendInteractiveAsset(current.value, module)
      selectedElementId.value = replacement.id
      markSlideComponentDirty(current.value, replacement.id)
      interactiveRegenerateTarget.value = null
      interactivePreviewVisible.value = false
      interactiveModule.value = null
      WorkspaceMessage.success('H5 已重新生成并替换，正在自动保存')
      return
    }
    interactiveRegenerateTarget.value = null
  }
  const element = createInteractiveElement(module, target === 'new-page' ? { x: 10, y: 43, width: 80, height: 43 } : {})
  if (target === 'new-page') {
    const newSlide = {
      ...defaultSlide(slides.length + 1),
      title: module.title || 'H5 组件',
      eyebrow: 'H5 组件 · 独立页面',
      description: module.topic || '可独立运行的 H5 互动内容。',
      layout: '重点陈述',
      theme: current.value?.theme || 'blue',
      elements: [element],
      interactive_assets: [],
      dirty: true,
    }
    appendInteractiveAsset(newSlide, module)
    slides.splice(selectedSlide.value + 1, 0, newSlide)
    selectedSlide.value += 1
    pendingHtmlPanelSelection = { slide: newSlide, id: element.id }
    markSlideComponentDirty(newSlide, 'page:add-interactive', { structure: true })
    WorkspaceMessage.success('H5 组件已作为独立页面插入，正在自动保存')
  } else {
    if (workspaceUsesHtmlEditor.value) {
      const controller = await waitForHtmlController(current.value)
      if (!controller) return WorkspaceMessage.warning('当前页面尚未完成加载，请重新打开工作台后重试')
      const inserted = controller.insertInteractive?.(module)
      if (!inserted) return WorkspaceMessage.warning('H5 组件插入失败，请重新生成后重试')
      appendInteractiveAsset(current.value, module)
      markSlideComponentDirty(current.value, htmlSelectedElementId.value)
      interactivePreviewVisible.value = false
      interactiveModule.value = null
      WorkspaceMessage.success('H5 组件已插入当前 HTML 页面，正在自动保存')
      return
    }
    current.value.elements.push(element)
    appendInteractiveAsset(current.value, module)
    selectedElementId.value = element.id
    markSlideComponentDirty(current.value, element.id)
    WorkspaceMessage.success('H5 组件已插入当前页面，正在自动保存')
  }
  interactivePreviewVisible.value = false
  interactiveModule.value = null
  interactiveRegenerateTarget.value = null
}
const removeElement = (id = selectedElementId.value) => {
  if (workspaceUsesHtmlEditor.value) {
    const targetId = id || htmlSelectedElementId.value
    if (!targetId) return
    activeHtmlController()?.deleteSelected?.(targetId)
    return
  }
  if (!current.value || !id) return
  const index = current.value.elements.findIndex((element) => element.id === id)
  if (index < 0) return
  const [removed] = current.value.elements.splice(index, 1)
  if (removed?.type === 'h5' && removed?.moduleId && Array.isArray(current.value.interactive_assets)) {
    current.value.interactive_assets = current.value.interactive_assets.filter((asset) => String(asset?.module_id || '') !== String(removed.moduleId))
  }
  selectedElementId.value = null
  markSlideComponentDirty(current.value, removed?.id || id)
  WorkspaceMessage.success(`${removed?.name || '元素'}已删除`)
}
const copyElement = (id = selectedElementId.value) => {
  if (workspaceUsesHtmlEditor.value) {
    const targetId = id || htmlSelectedElementId.value
    if (!targetId) return
    activeHtmlController()?.copySelected?.(targetId)
    return
  }
  const source = elementById(id)
  if (!source || !current.value) return
  const copy = cloneElementData(source)
  copy.id = `${source.type}-${Date.now()}-${elementSequence++}`
  copy.name = `${source.name || elementTypeLabels[source.type] || '元素'} 副本`
  copy.target = null
  copy.content = elementContent(source)
  copy.position = { ...copy.position, x: Math.min(82, Number(copy.position?.x || 0) + 4), y: Math.min(78, Number(copy.position?.y || 0) + 4) }
  current.value.elements.push(copy)
  selectedElementId.value = copy.id
  markSlideComponentDirty(current.value, copy.id)
  WorkspaceMessage.success('元素已复制')
}
const copyElementToClipboard = (id = workspaceSelectedElementId.value) => {
  if (workspaceUsesHtmlEditor.value) {
    const targetId = id || htmlSelectedElementId.value
    if (!targetId) return false
    const copied = activeHtmlController()?.copyToClipboard?.(targetId) || false
    if (copied) WorkspaceMessage.success('元素已复制，可使用 Ctrl+V 粘贴')
    return copied
  }
  const source = elementById(id)
  if (!source) return false
  workspaceElementClipboard = {
    kind: 'structured',
    // 标题、说明等绑定字段复制后可能粘贴到另一页，因此此处固化当前展示内容。
    element: { ...cloneElementData(source), content: elementContent(source) },
  }
  WorkspaceMessage.success('元素已复制，可使用 Ctrl+V 粘贴')
  return true
}
const pasteElementFromClipboard = () => {
  if (!current.value) return false
  if (workspaceUsesHtmlEditor.value) {
    const pasted = activeHtmlController()?.pasteFromClipboard?.() || false
    if (pasted) WorkspaceMessage.success('元素已粘贴')
    return pasted
  }
  if (workspaceElementClipboard?.kind !== 'structured' || !workspaceElementClipboard.element) return false
  const source = cloneElementData(workspaceElementClipboard.element)
  const copy = cloneElementData(source)
  copy.id = `${source.type}-${Date.now()}-${elementSequence++}`
  copy.name = `${source.name || elementTypeLabels[source.type] || '元素'} 副本`
  copy.target = null
  copy.content = source.content
  copy.position = {
    ...copy.position,
    x: Math.min(82, Number(copy.position?.x || 0) + 4),
    y: Math.min(78, Number(copy.position?.y || 0) + 4),
  }
  current.value.elements.push(copy)
  selectedElementId.value = copy.id
  markSlideComponentDirty(current.value, copy.id)
  WorkspaceMessage.success('元素已粘贴')
  return true
}
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
const pageToSlide = (page = {}, index) => {
  const contentValue = page.page_content ?? page.content ?? page.data
  const parsedContent = parseJson(contentValue, {})
  const content = parsedContent && typeof parsedContent === 'object' && !Array.isArray(parsedContent) ? parsedContent : {}
  const elements = content.elements ?? content.components ?? page.elements ?? page.components ?? page.items
  const pageType = content.pageType || content.page_type || page.page_type || page.pageType || (index === 0 ? 'cover' : 'content')
  return {
    ...defaultSlide(index + 1),
    ...content,
    html: stripSlideDecorativeCircle(content.html ?? page.html ?? ''),
    elements: normalizeElements(elements),
    pageId: page.id || page.page_id || content.pageId || content.page_id,
    componentId: page.id || page.component_id || page.page_id || content.componentId,
    pageOrder: Number(page.page_order ?? content.pageOrder ?? content.page_order ?? index + 1),
    page_order: Number(page.page_order ?? content.pageOrder ?? content.page_order ?? index + 1),
    pageVersion: Number(page.page_version || content.pageVersion || content.page_version || 1),
    clientVersion: page.client_version || content.clientVersion || workspaceClientVersion,
    autosave: page.autosave ?? content.autosave ?? false,
    dirty: page.dirty ?? content.dirty ?? false,
    lastSavedAt: page.last_saved_at || content.lastSavedAt || null,
    title: content.title || page.page_title || page.title || `第 ${index + 1} 页`,
    pageType,
    page_type: pageType,
    notes: content.notes || page.notes || '',
  }
}
const getGeneratedPagePayload = (rawResponse) => {
  const response = unwrapResponse(rawResponse)
  const candidate = response?.page || response?.result?.page || response?.result || response
  if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) return null
  const parsedContent = parseJson(candidate.page_content ?? candidate.content ?? candidate.data, {})
  const content = parsedContent && typeof parsedContent === 'object' && !Array.isArray(parsedContent) ? parsedContent : {}
  const hasPageSignal = candidate.page_content !== undefined
    || candidate.html !== undefined
    || content.html !== undefined
    || candidate.elements !== undefined
    || candidate.components !== undefined
    || candidate.page_title !== undefined
    || candidate.title !== undefined
    || Object.keys(content).length > 0
  return hasPageSignal ? { candidate, content } : null
}
const applyGeneratedPage = (rawResponse) => {
  const payload = getGeneratedPagePayload(rawResponse)
  if (!payload || !current.value) return false
  const { candidate, content } = payload
  const html = content.html ?? candidate.html ?? content.page_html ?? candidate.page_html
  if (typeof html === 'string' && html.trim()) {
    const nextSlide = {
      ...current.value,
      ...content,
      ...(candidate.title ? { title: candidate.title } : {}),
      ...(candidate.description ? { description: candidate.description } : {}),
      html: stripSlideDecorativeCircle(html.trim()),
      elements: [],
    }
    slides.splice(selectedSlide.value, 1, nextSlide)
    htmlSelectionRestoreKey.value = ''
    htmlElements.value = []
    htmlSelectedElementId.value = null
    htmlSelectedElement.value = null
    markSlideComponentDirty(nextSlide, 'page:ai')
    saveCurrentPresentationDraft()
    return true
  }
  // 已经是 AI HTML 页时，不能把一个没有 HTML 的响应降级成结构化页面。
  if (current.value.html) return false
  const elementPayload = content.elements ?? content.components ?? candidate.elements ?? candidate.components ?? current.value.elements
  const nextContent = {
    ...current.value,
    ...content,
    ...(candidate.title ? { title: candidate.title } : {}),
    ...(candidate.description ? { description: candidate.description } : {}),
    elements: elementPayload,
  }
  const page = {
    ...candidate,
    id: candidate.id || candidate.component_id || candidate.page_id || current.value.componentId,
    page_version: candidate.page_version || current.value.pageVersion || 1,
    client_version: candidate.client_version || current.value.clientVersion || workspaceClientVersion,
    page_title: candidate.page_title || nextContent.title,
    page_content: JSON.stringify(nextContent),
    components: typeof elementPayload === 'string' ? elementPayload : JSON.stringify(elementPayload),
  }
  slides.splice(selectedSlide.value, 1, pageToSlide(page, selectedSlide.value))
  markSlideComponentDirty(slides[selectedSlide.value], 'page:ai')
  selectedElementId.value = null
  return true
}
const loadProjectPageDetail = async (index) => {
  const slide = slides[index]
  if (!projectId.value || !slide?.pageId) return
  const detailKey = `${projectId.value}:${slide.pageId}`
  if (loadedPageDetailIds.has(detailKey)) return
  loadedPageDetailIds.add(detailKey)
  hydratingProject.value = true
  try {
    const detail = unwrapResponse(await getProjectPage(projectId.value, slide.pageId))
    if (detail && slides[index] === slide) slides.splice(index, 1, pageToSlide(detail, index))
  } catch (error) {
    loadedPageDetailIds.delete(detailKey)
    WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '页面详情加载失败，已使用页面列表数据'))
  } finally {
    hydratingProject.value = false
  }
}
const isProjectVersionConflict = (error) => {
  const message = error?.response?.data?.message || error?.message || ''
  return /版本冲突|version conflict/i.test(String(message))
}
const waitForPendingProjectWrites = async () => {
  // 页面自动保存会递增项目 current_version；项目级保存必须等这些请求完成，
  // 否则即使刚刚读取过项目详情，也可能读到页面保存前的旧版本。
  const pending = [...new Set([pageSavePromise, orderSavePromise].filter(Boolean))]
  if (pending.length) await Promise.all(pending)
}
const refreshProjectForWrite = async () => {
  if (!projectId.value) return project.value
  await waitForPendingProjectWrites()
  const latest = unwrapResponse(await getProject(projectId.value))
  if (latest && typeof latest === 'object') project.value = { ...(project.value || {}), ...latest }
  return project.value
}
const patchProjectWithFreshVersion = async (payload) => {
  if (!projectId.value) throw new Error('当前项目尚未创建')
  await refreshProjectForWrite()
  const send = () => patchProject(projectId.value, {
    ...payload,
    current_version: Number(project.value?.current_version || 1),
  }).then(unwrapResponse)
  try {
    const updated = await send()
    if (updated && typeof updated === 'object') project.value = { ...(project.value || {}), ...updated }
    return updated
  } catch (error) {
    // 处理 GET 与 PATCH 之间极短窗口内的并发写入；真正持续的多人冲突仍然会返回给用户。
    if (!isProjectVersionConflict(error)) throw error
    await refreshProjectForWrite()
    const updated = await send()
    if (updated && typeof updated === 'object') project.value = { ...(project.value || {}), ...updated }
    return updated
  }
}
const setWorkspaceMode = async (nextMode) => {
  const normalized = normalizeWorkspaceMode(nextMode)
  if (normalized === workspaceMode.value) return
  const previous = workspaceMode.value
  workspaceMode.value = normalized
  const query = { ...route.query, workspaceMode: normalized }
  try {
    if (projectId.value) {
      autosaveState.value = '正在同步工作模式…'
      const updated = await patchProjectWithFreshVersion({
        project_type: workspaceProjectType.value,
        status: 'editing',
      })
      project.value = { ...(project.value || {}), ...(updated || {}), project_type: workspaceProjectType.value }
      autosaveState.value = '已保存 · 工作模式已同步'
    } else {
      saveCurrentPresentationDraft()
    }
    await router.replace({ query })
  } catch (error) {
    workspaceMode.value = previous
    autosaveState.value = projectId.value ? '保存失败' : '本地草稿 · 尚未保存为项目'
    WorkspaceMessage.error(workspaceRequestErrorMessage(error, '工作模式切换失败'))
  }
}
const syncProjectMetadataIfNeeded = async () => {
  const requestedName = String(route.query.templateTitle || '').trim()
  if (!projectId.value || !project.value || !requestedName || requestedName === project.value.project_name) return
  try {
    const response = await patchProjectWithFreshVersion({
      project_name: requestedName,
      project_type: project.value.project_type || workspaceProjectType.value,
      status: 'editing',
    })
    project.value = { ...project.value, ...(response || {}) }
  } catch (error) {
    WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '项目元数据同步失败，页面内容仍可保存'))
  }
}
const syncProjectWorkspaceContextIfNeeded = async () => {
  if (!projectId.value || !project.value) return
  const context = workspaceContextPayload()
  const hasContext = Boolean(context.resource_ids.length || context.uploaded_resources.length || context.community)
  if (!hasContext) return
  const history = parseJson(project.value.edit_history, {})
  const savedContext = history?.workspace_context || history?.workspaceContext
  if (JSON.stringify(savedContext || {}) === JSON.stringify(context)) return
  const nextHistory = Array.isArray(history)
    ? { entries: history, workspace_context: context }
    : { ...(history && typeof history === 'object' ? history : {}), workspace_context: context }
  try {
    const updated = await patchProjectWithFreshVersion({
      edit_history: JSON.stringify(nextHistory),
    })
    project.value = { ...project.value, ...(updated || {}), edit_history: updated?.edit_history || JSON.stringify(nextHistory) }
    presentationMetadata.value = { ...(presentationMetadata.value || {}), workspace_context: context }
  } catch (error) {
    WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '工作台上下文同步失败，当前页面仍可编辑'))
  }
}
const openLessonPlanWorkspace = () => setWorkspaceMode('document')
const returnToPptWorkspace = () => setWorkspaceMode('ppt')
const openLessonPlanPreview = () => {
  const currentPlan = lessonPlanEditorRef.value?.getLessonPlan?.()
  const candidate = currentPlan || lessonPlanDraft.value
  if (!candidate || typeof candidate !== 'object' || !Object.keys(candidate).length) {
    WorkspaceMessage.warning('请先生成教学案后再预览')
    return
  }
  lessonPlanPreviewDraft.value = parseJson(JSON.stringify(candidate), {})
  lessonPlanPreviewVisible.value = true
}
const saveLessonPlanDraft = async (plan, { throwOnError = false, notify = true } = {}) => {
  const nextPlan = parseJson(JSON.stringify(plan || {}), {})
  lessonPlanDraft.value = nextPlan
  presentationMetadata.value = { ...(presentationMetadata.value || {}), lesson_plan: nextPlan }
  if (!projectId.value || !project.value) {
    saveCurrentPresentationDraft()
    if (notify) WorkspaceMessage.success('教案已保存到本地草稿，保存为项目后可跨设备继续编辑')
    return
  }
  const history = parseJson(project.value.edit_history, {})
  const nextHistory = Array.isArray(history)
    ? { entries: history, lesson_plan: nextPlan, workspace_context: workspaceContextPayload() }
    : { ...(history && typeof history === 'object' ? history : {}), lesson_plan: nextPlan, workspace_context: workspaceContextPayload() }
  try {
    const updated = await patchProjectWithFreshVersion({
      edit_history: JSON.stringify(nextHistory),
    })
    project.value = { ...project.value, ...(updated || {}), edit_history: updated?.edit_history || JSON.stringify(nextHistory) }
    autosaveState.value = '已保存 · 教案已同步'
    if (notify) WorkspaceMessage.success('教案已保存到项目')
  } catch (error) {
    if (notify) WorkspaceMessage.error(error?.message || '教案保存失败，已保留在当前页面')
    else autosaveState.value = '保存失败'
    if (throwOnError) throw error
  }
}
let lessonPlanAutosavePromise = Promise.resolve()
const autosaveLessonPlanDraft = (plan) => {
  lessonPlanAutosavePromise = lessonPlanAutosavePromise
    .catch(() => {})
    .then(() => saveLessonPlanDraft(plan, { notify: false }))
  return lessonPlanAutosavePromise
}
const loadProject = async () => {
  if (!projectId.value) return
  hydratingProject.value = true
  projectLoadError.value = ''
  presentationMetadata.value = null
  qualityReport.value = null
  qualityReportSource.value = ''
  try {
    project.value = unwrapResponse(await getProject(projectId.value))
    workspaceMode.value = normalizeWorkspaceMode(project.value?.project_type || routeQueryValue(route.query.workspaceMode || route.query.mode))
    const projectHistory = parseJson(project.value?.edit_history, {})
    const savedWorkspaceContext = projectHistory?.workspace_context || projectHistory?.workspaceContext
    lessonPlanDraft.value = projectHistory?.lesson_plan || projectHistory?.lessonPlan || null
    if (savedWorkspaceContext && typeof savedWorkspaceContext === 'object') {
      presentationMetadata.value = { ...(presentationMetadata.value || {}), workspace_context: savedWorkspaceContext }
    }
    setQualityReport(project.value?.reflections || project.value?.reflection || project.value?.quality_report || project.value?.qualityReport, '项目记录')
    let pages = []
    try {
      const listedPages = unwrapResponse(await listProjectPages(projectId.value))
      pages = pageRecords(listedPages)
    } catch (error) {
      pages = pageRecords(project.value?.pages)
      WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '页面列表加载失败，已使用项目详情中的页面'))
    }
    loadedPageDetailIds.clear()
    const fallbackPages = pageRecords(project.value?.pages)
    const sourcePages = pages.length ? pages : fallbackPages
    slides.splice(0, slides.length, ...(sourcePages.length ? sourcePages.map(pageToSlide) : [defaultSlide()]))
    selectedSlide.value = 0
    savedChangeVersion = localChangeVersion
    savedStructureVersion = localStructureVersion
    autosaveQueued = false
    autosaveState.value = '已保存 · 云端项目'
  } catch (error) {
    projectLoadError.value = workspaceRequestErrorMessage(error, '项目内容加载失败')
    WorkspaceMessage.error(projectLoadError.value)
  } finally { hydratingProject.value = false }
  await loadProjectPageDetail(0)
  await syncProjectMetadataIfNeeded()
  await syncProjectWorkspaceContextIfNeeded()
}
const retryProjectLoad = async () => {
  if (!projectId.value) return
  await loadProject()
  await nextTick()
  centerCanvasView()
}
// 工作台组件在切换项目时会被 Vue 复用，不会重新执行 onMounted；监听项目 ID，确保“打开”真正加载新项目。
watch(projectId, async (nextId, previousId) => {
  if (!nextId || String(nextId) === String(previousId) || testCaseBootstrapping.value) return
  clearTimeout(autosaveTimer)
  versionPage.value = 1
  versions.value = []
  versionDiff.value = null
  compareVersionId.value = ''
  versionDescription.value = ''
  localChangeVersion += 1
  autosaveQueued = false
  project.value = null
  workspaceResourceBindingOverride.value = null
  autosaveState.value = '正在打开项目…'
  selectedSlide.value = 0
  selectedElementId.value = null
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
  await loadProject()
  await nextTick()
  centerCanvasView()
})
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
  slides.forEach((slide) => { slide.elements = normalizeElements(slide.elements) })
  messages.splice(0, messages.length, { role: 'assistant', text: `已载入“${title}”测试案例。你可以编辑页面内容，或继续描述希望调整的方向。` })
  selectedSlide.value = 0
}

const componentValidationPayload = (element) => {
  if (!element) return null
  const common = {
    component_id: String(element.id || ''),
    render: { ...(element.render || {}) },
    style: { ...(element.style || {}) },
  }
  if (element.type === 'formula') {
    return { ...common, type: 'math_formula', data: { latex: elementContent(element) || 'a^2+b^2=c^2', display_mode: true } }
  }
  if (element.type === 'chart') {
    const items = Array.isArray(element.data) ? element.data : []
    return {
      ...common,
      type: 'chart',
      data: {
        option: {
          xAxis: { type: 'category', data: items.map((item) => String(item?.label || '')) },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: items.map((item) => Number(item?.value) || 0) }],
        },
      },
    }
  }
  if (element.type === 'table') return { ...common, type: 'table', data: { rows: Array.isArray(element.data) ? element.data : [] } }
  if (element.type === 'subject') return subjectToolPayload(element)
  if (element.type === 'shape' && element.shapeKind === 'formula-diagram') {
    return { ...common, type: 'geometry', data: { construction: elementContent(element) || 'right_triangle', commands: ['draw_right_triangle'] } }
  }
  return null
}
const subjectComponentsFromHtml = (slide) => {
  const source = String(slide?.html || '').trim()
  if (!source || typeof DOMParser === 'undefined') return []
  try {
    const document = new DOMParser().parseFromString(source, 'text/html')
    const seen = new Set()
    return [...document.querySelectorAll('[data-ppt-type="subject"],[data-subject-type],[data-subject-data]')]
      .map((node, index) => {
        const id = String(node.getAttribute('data-ppt-element') || node.id || `html-subject-${index + 1}`)
        if (seen.has(id)) return null
        seen.add(id)
        return subjectToolPayload({
          id,
          subjectType: node.getAttribute('data-subject-type') || 'geometry',
          data: parseJson(node.getAttribute('data-subject-data'), {}),
          render: parseJson(node.getAttribute('data-subject-render'), {}),
          subjectStyle: parseJson(node.getAttribute('data-subject-style'), {}),
          style: parseJson(node.getAttribute('data-subject-style'), {}),
        })
      })
      .filter(Boolean)
  } catch {
    return []
  }
}
const validationPayloadsForSlide = (slide) => {
  const components = (slide?.elements || []).map(componentValidationPayload).filter(Boolean)
  const componentIds = new Set(components.map((component) => String(component.component_id || '')))
  subjectComponentsFromHtml(slide).forEach((component) => {
    if (!componentIds.has(String(component.component_id || ''))) components.push(component)
  })
  return components
}
const validateSlideComponents = async (slide) => {
  const components = validationPayloadsForSlide(slide)
  for (const component of components) {
    const signature = JSON.stringify(component)
    const cached = componentValidationCache.get(signature)
    const result = cached || unwrapResponse(await validateProjectComponent(component))
    if (!cached) componentValidationCache.set(signature, result)
    if (result?.valid === false) {
      const errors = Array.isArray(result.errors) ? result.errors.filter(Boolean).join('；') : ''
      throw new Error(`${component.type} 组件校验失败${errors ? `：${errors}` : ''}`)
    }
  }
}
// 项目接口会校验学科组件的 data 字段必须是对象；编辑器中的图表、表格
// 则以数组保存实际数据。持久化时统一转换为接口约定，画布内容仍保存在
// page_content 中，不改变编辑器的本地元素结构。
const componentsPayloadForSlide = (slide) => {
  const components = (slide?.elements || []).map((element) => componentValidationPayload(element) || element)
  const componentIds = new Set(components.map((component) => String(component?.component_id || component?.id || '')))
  subjectComponentsFromHtml(slide).forEach((component) => {
    if (!componentIds.has(String(component.component_id || ''))) components.push(component)
  })
  return components
}
const pagePayloadForSlide = (slide, index, overrides = {}) => {
  const { includePageOrder = true, ...payloadOverrides } = overrides
  // 结构化页面也以同一份固定画布 HTML 持久化，后端导出、预览和重新打开
  // 时不再需要猜测页面属于哪一种渲染分支。
  const persistedSlide = slide?.html
    ? slide
    : { ...slide, html: slideHtmlSource(slide) }
  return {
    ...(includePageOrder ? { page_order: index + 1 } : {}),
    page_type: slide.pageType || slide.page_type || (index === 0 ? 'cover' : 'content'),
    page_title: slide.title,
    page_content: JSON.stringify(persistedSlide),
    components: JSON.stringify(componentsPayloadForSlide(slide)),
    client_version: slide.clientVersion || workspaceClientVersion,
    autosave: false,
    dirty: Boolean(slide.dirty),
    ...payloadOverrides,
  }
}
const savedPageList = (response) => {
  const result = unwrapResponse(response)
  return Array.isArray(result) ? result : result?.pages || result?.items || []
}
const applySavedPageMetadata = (savedPages, targetSlides = slides, { clearPending = false, updateOrder = true } = {}) => {
  savedPages.forEach((page, index) => {
    const pageId = page?.id || page?.page_id || page?.component_id
    const slide = (pageId && targetSlides.find((item) => String(item.pageId || item.page_id || item.componentId) === String(pageId))) || targetSlides[index]
    if (!slide) return
    slide.pageId = pageId || slide.pageId
    slide.componentId = page?.component_id || slide.pageId
    const pageOrder = Number(page?.page_order ?? page?.pageOrder)
    if (updateOrder && Number.isFinite(pageOrder)) {
      slide.pageOrder = pageOrder
      slide.page_order = pageOrder
    }
    slide.pageVersion = Number(page?.page_version || slide.pageVersion || 1)
    slide.clientVersion = page?.client_version || slide.clientVersion || workspaceClientVersion
    slide.autosave = Boolean(page?.autosave ?? true)
    slide.dirty = Boolean(page?.dirty)
    slide.lastSavedAt = page?.last_saved_at || slide.lastSavedAt || null
    if (clearPending) pendingComponentSync.delete(slide)
  })
  return savedPages
}
const projectPagePayload = (slide, index, order = index + 1) => ({
  ...pagePayloadForSlide(slide, index, { autosave: true, dirty: Boolean(slide.dirty), page_order: order }),
  ...(slide.pageId ? {
    page_id: Number(slide.pageId),
    expected_page_version: Number(slide.pageVersion || 1),
  } : {}),
})
const batchCreateProjectPages = async (targetProjectId, slideList) => {
  for (const slide of slideList) await validateSlideComponents(slide)
  const result = unwrapResponse(await batchSaveProjectPages(targetProjectId, {
    client_version: workspaceClientVersion,
    autosave: false,
    pages: slideList.map((slide, index) => pagePayloadForSlide(slide, index)),
  }))
  const savedPages = savedPageList(result)
  applySavedPageMetadata(savedPages, slideList, { clearPending: true })
  return savedPages
}

/**
 * 将社区测试案例真正落成项目和页面记录。
 * 预览入口只负责提供可重复的测试数据，后续编辑与导出均使用项目 ID 访问 API。
 */
const bootstrapTestCaseProject = async () => {
  if (!import.meta.env.DEV || !route.query.testCase || projectId.value) return
  testCaseBootstrapping.value = true
  autosaveState.value = '正在创建测试项目…'
  try {
    const created = unwrapResponse(await createProject({
      project_name: String(route.query.templateTitle || '临时测试案例'),
      project_type: workspaceProjectType.value,
      status: 'editing',
      edit_history: JSON.stringify({ workspace_context: workspaceContextPayload(), workspace_mode: workspaceMode.value }),
    }))
    const createdId = created?.id || created?.project_id
    if (!createdId) throw new Error('项目创建接口未返回项目 ID')

    await batchCreateProjectPages(createdId, slides)

    await router.replace({ query: { ...route.query, projectId: String(createdId) } })
    project.value = { ...created, id: createdId }
    savedChangeVersion = localChangeVersion
    savedStructureVersion = localStructureVersion
    autosaveQueued = false
    autosaveState.value = '已保存 · 测试项目已落库'
    WorkspaceMessage.success('测试项目已创建，页面内容已保存')
  } catch (error) {
    autosaveState.value = '创建失败'
    WorkspaceMessage.error(error?.message || '测试项目创建失败')
  } finally {
    testCaseBootstrapping.value = false
  }
}

const generationErrorMessage = (error) => {
  const backendMessage = error?.response?.data?.message || error?.response?.data?.error
  if (backendMessage) return String(backendMessage)
  if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') return 'HTML PPT 生成超时，请稍后点击“重新生成”。'
  if (error?.request && !error?.response) return '无法连接 HTML PPT 生成服务，请确认 Python 服务已启动。'
  return String(error?.message || 'HTML PPT 生成失败，请稍后重试。')
}

/**
 * 工作台只保留一条对话时间线，发送后由 AI 结合当前页和上下文判断：
 * 普通问题进入讨论，明确的页面操作进入修改。不向教师暴露或要求手动切换模式。
 */
const intentSubmitting = ref(false)
const isAssistantSubmitting = computed(() => intentSubmitting.value || discussionSubmitting.value || revisionSubmitting.value || workspaceVoiceSubmitting.value)
const assistantPlaceholder = computed(() => '例如：讨论一下怎样让导入更贴近学生，或把当前页标题改得更简洁')
const assistantStatusText = computed(() => {
  if (workspaceVoiceSubmitting.value) return '正在上传语音并续接 AI 会话…'
  if (intentSubmitting.value) return 'AI 正在判断意图…'
  if (discussionSubmitting.value) return 'AI 正在思考…'
  if (revisionSubmitting.value) return revisionStage.value || 'AI 正在执行页面修改…'
  return ''
})
/**
 * 讨论上下文只保存尚未落地的讨论。
 *
 * 页面修改完成后，旧的「需求 + 确认」会被关闭，不能再被下一次确认当作待办；
 * 否则模型会把多轮历史修改和最新问题合并，重复确认或重复执行旧操作。
 */
const workspaceDiscussionHistory = () => messages
  .filter((message) => message?.includeInContext === true
    && (message?.role === 'user' || message?.role === 'assistant')
    && String(message?.text || '').trim())
  .map((message) => ({ role: message.role, content: String(message.text).trim() }))
  .slice(-6)
const workspaceConversationTranscript = () => workspaceDiscussionHistory()
  .slice(-8)
  .map((message) => `${message.role === 'user' ? '教师' : 'AI'}：${message.content}`)
  .join('\n')
const closeDiscussionContext = () => {
  messages.forEach((message) => {
    if (message?.includeInContext === true) message.includeInContext = false
  })
}
const inferAssistantMode = (text = '') => {
  const value = String(text).trim().replace(/\s+/g, '')
  if (!value) return 'discussion'

  const discussionPrefix = /^(你好|嗨|您好|请问|为什么|为何|怎么回事|怎么看|你觉得|你认为|分析一下|讨论一下|聊聊|建议一下|帮我想想|解释一下|介绍一下|是什么|如何理解)/i
  if (discussionPrefix.test(value)) return 'discussion'

  const explicitRevisionCommand = /^(?:那|所以|就)?(?:请|麻烦)?(?:你)?(?:执行|应用|开始|继续|执行修改|应用修改|开始修改|继续修改|修改|修改当前页|页面修改|改|改吧|改啊|改一下|调整一下)$/
  if (explicitRevisionCommand.test(value)) return 'revision'

  const revisionAction = /(修改|改一下|调整|替换|交换|互换|换一下|换成|改成|改为|删除|移除|添加|增加|新增|插入|补充|新建|追加|加上|加个|加一|移动|拖到|缩放|放大|缩小|旋转|复制|重做|撤销|恢复|改变|设置|隐藏|显示|去掉|删掉|清空|重排|排版|对齐|换图|换色|优化|润色|精简|丰富|补充|重写|太大|太小|看不清|不清晰|居中|靠左|靠右|上移|下移)/
  const revisionTarget = /(当前页|本页|这一页|第\d+页|页面|幻灯片|界面|封面|开场页|首页|结束页|尾页|PPT|标题|文案|图片|图表|元素|组件|画布|布局|颜色|字体|字号|透明度|位置|右侧|左侧|上方|下方|背景|边框|间距|内容|列表|文字|导入|情境|案例|知识点|卡片|页眉|页脚|模块)/i
  const imperative = /^(请|帮我|把|将|给我|麻烦|直接|能不能把|可以把)/
  const naturalRevision = /^(让|使).{0,24}(更|更加|变得|优化|精简|丰富|清晰|简洁|生活化|有启发性)/

  if (revisionAction.test(value) && revisionTarget.test(value)) return 'revision'
  if ((revisionAction.test(value) || naturalRevision.test(value))
    && (imperative.test(value) || /(这个|这里|它|那张|这一处|页)/.test(value))) return 'revision'
  return 'discussion'
}
const isDiscussionQuestion = (text = '') => /^(你好|嗨|您好|请问|为什么|为何|怎么回事|怎么看|你觉得|你认为|分析一下|讨论一下|聊聊|建议一下|帮我想想|解释一下|介绍一下|是什么|如何理解)/i.test(String(text).trim().replace(/\s+/g, ''))
const isAddPageInstruction = (text = '') => {
  const value = String(text).trim().replace(/\s+/g, '')
  if (!value || isDiscussionQuestion(value)) return false
  return /(?:添加|增加|新增|插入|补充|新建|追加|加(?:上)?)(?:一个|个|一张|一页)?\s*.{0,16}(?:一页|\d+页|页面|幻灯片|界面|封面|开场页|首页|结束页|尾页)/i.test(value)
}
const isExplicitPageOperation = (text = '') => {
  const value = String(text).trim().replace(/\s+/g, '')
  if (!value || isDiscussionQuestion(value)) return false
  const action = /(修改|改一下|调整|替换|交换|互换|换一下|换成|改成|改为|删除|移除|添加|增加|新增|插入|补充|新建|追加|加上|加个|加一|移动|拖到|缩放|放大|缩小|旋转|复制|撤销|恢复|设置|隐藏|显示|去掉|删掉|清空|重排|排版|对齐|换图|换色|优化|润色|精简|丰富|补充|重写)/
  const target = /(当前页|本页|这一页|第\d+页|页面|页|幻灯片|界面|封面|开场页|首页|结束页|尾页|PPT|标题|文案|图片|图表|元素|组件|画布|布局|颜色|字体|字号|位置|背景|内容|文字)/i
  return action.test(value) && target.test(value)
}
const isExplicitComponentOperation = (text = '') => {
  const value = String(text).trim().replace(/\s+/g, '')
  if (!value || isDiscussionQuestion(value)) return false
  return /(修改|改一下|调整|替换|交换|互换|换一下|换成|改成|改为|删除|移除|添加|增加|新增|插入|移动|缩放|放大|缩小|旋转|设置|隐藏|显示|去掉|删掉|清空|优化|润色|精简|丰富|补充|重写)/.test(value)
    && /(组件|元素|控件|模块)/.test(value)
}
const isRevisionConfirmation = (text = '') => {
  const value = String(text).trim().replace(/\s+/g, '')
  if (!value || !workspaceDiscussionHistory().length) return false
  return /^(?:那|所以|就)?(?:请|麻烦)?(?:你)?(?:执行|应用|开始|继续|执行修改|应用修改|开始修改|继续修改|修改|修改当前页|页面修改|改|改吧|改啊|改一下|调整一下)[！!。？?]*$/.test(value)
}
const WORKSPACE_CHAT_TIMEOUT_MS = 30_000
const withWorkspaceChatTimeout = async (handler) => {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), WORKSPACE_CHAT_TIMEOUT_MS)
  try {
    return await handler(controller.signal)
  } catch (error) {
    if (controller.signal.aborted || error?.name === 'AbortError') {
      throw new Error('大模型响应超时，请检查模型服务后重试。')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}
const intentFallbackShown = ref(false)
const parseWorkspaceModelJson = (text) => {
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
const readWorkspaceClassifierStream = async (response) => {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('意图模型没有返回可读取的数据流')
  const decoder = new TextDecoder()
  let buffer = ''
  let content = ''
  const consumeLine = (line) => {
    if (!line.startsWith('data:')) return
    const data = line.slice(5).trim()
    if (!data || data === '[DONE]') return
    try {
      const payload = JSON.parse(data)
      const delta = payload?.choices?.[0]?.delta?.content ?? payload?.choices?.[0]?.message?.content
      if (typeof delta === 'string') content += delta
    } catch {
      // 等待下一块 SSE 数据补全 JSON 行。
    }
  }
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() || ''
    lines.forEach(consumeLine)
    if (done) break
  }
  if (buffer.trim()) consumeLine(buffer)
  if (!content.trim()) throw new Error('意图模型未返回有效结果')
  return content
}
const requestWorkbenchOperation = async (text) => {
  const response = await withWorkspaceChatTimeout((signal) => streamGeneralChat({
    mode: 'workbench-intent',
    user_id: String(userStore.userInfo?.user_id || userStore.userInfo?.id || '10001'),
    messages: [
      ...workspaceDiscussionHistory().slice(-6),
      { role: 'user', content: String(text) },
    ],
  }, { signal }))
  if (!response.ok) {
    let message = ''
    try {
      const payload = await response.json()
      message = payload?.message || ''
    } catch {
      // 保留 HTTP 状态。
    }
    throw new Error(message || `意图模型请求失败（HTTP ${response.status}）`)
  }
  const raw = await readWorkspaceClassifierStream(response)
  const parsed = parseWorkspaceModelJson(raw)
  if (!parsed) throw new Error('意图模型返回格式无法解析')
  return parsed
}
const workspaceOperationFromIntent = (formalData, text = '') => {
  const intent = formalData?.intent && typeof formalData.intent === 'object' ? formalData.intent : {}
  const raw = [
    formalData?.operation,
    formalData?.action,
    formalData?.intent_type,
    formalData?.intentType,
    formalData?.target_type,
    formalData?.targetType,
    formalData?.mode,
    formalData?.type,
    typeof formalData?.intent === 'string' ? formalData.intent : '',
    intent.operation,
    intent.action,
    intent.intent_type,
    intent.intentType,
    intent.target_type,
    intent.targetType,
    intent.type,
    intent.name,
    intent.code,
  ].filter(Boolean).join(' ').toLowerCase()
  if (/(export|download|导出|下载)/.test(raw) || /导出|下载|生成文件|保存为/.test(text)) return 'export'
  if (/(open[_ -]?project|project[_ -]?open|select[_ -]?project|打开项目|切换项目)/.test(raw) || /打开项目|切换项目|进入项目/.test(text)) return 'open_project'
  if (/(component|element|widget|module|组件|元素|控件|模块)/.test(raw) || /组件|元素|控件|模块/.test(text)) return 'modify_component'
  if (/(generate|create|content|compose|生成|创作|新增内容)/.test(raw) || /生成内容|创作内容|补充内容|写一段|生成一段/.test(text)) return 'generate_content'
  if (/(modify|edit|update|revise|page|slide|页面|幻灯片|修改|编辑)/.test(raw) || isExplicitPageOperation(text) || isRevisionConfirmation(text)) return 'modify_page'
  if (isDiscussionQuestion(text)) return 'discussion'
  return (isAddPageInstruction(text) || isExplicitPageOperation(text) || isRevisionConfirmation(text) || inferAssistantMode(text) === 'revision') ? 'modify_page' : 'discussion'
}
const requestAssistantIntent = async (text) => {
  const context = workspaceContextPayload()
  // API-13B 的 DTO 将 user_id/session_id 定义为字符串；不要把业务会话 ID
  // 强制转换成数字，否则 UUID 或带前缀的会话会被丢弃，正式接口会退回默认会话。
  const intentUserId = String(userStore.userInfo?.user_id || userStore.userInfo?.id || '10001')
  const intentSessionId = workspacePythonSessionId()
  const knownContext = {
    page: {
      page_id: current.value?.pageId || current.value?.page_id || current.value?.componentId || null,
      title: current.value?.title || '',
      slide_no: selectedSlide.value + 1,
      element_count: Array.isArray(current.value?.elements) ? current.value.elements.length : 0,
    },
    selected_element: selectedElement.value ? {
      id: selectedElement.value.id,
      name: selectedElement.value.name,
      type: selectedElement.value.type,
      content: selectedElement.value.content,
    } : htmlSelectedElement.value ? {
      id: htmlSelectedElement.value.id,
      name: htmlSelectedElement.value.name,
      type: htmlSelectedElement.value.type,
      content: htmlSelectedElement.value.content,
    } : null,
    workspace_context: context,
  }
  const data = await withWorkspaceChatTimeout((signal) => recognizeIntent({
    user_id: intentUserId,
    ...(intentSessionId ? { session_id: intentSessionId } : {}),
    title: String(project.value?.project_name || current.value?.title || route.query.templateTitle || 'A12 教学课件'),
    message: String(text),
    history: JSON.stringify(workspaceDiscussionHistory()),
    known_context: JSON.stringify(knownContext),
    resource_ids: JSON.stringify(context.resource_ids || []),
    enable_rag: Boolean(context.resource_ids?.length),
    enable_web: false,
    slide_count: slides.length,
    language: 'zh-CN',
  }, { signal }))
  const formalData = unwrapResponse(data) || {}
  const returnedSessionId = formalData?.session_id || formalData?.python_session_id
  if (returnedSessionId) {
    presentationMetadata.value = {
      ...(presentationMetadata.value || {}),
      python_session_id: String(returnedSessionId),
    }
  }
  return {
    operation: workspaceOperationFromIntent(formalData, text),
    data: formalData,
  }
}
const resolveAssistantIntent = async (text) => {
  const fallbackOperation = workspaceOperationFromIntent({}, text)
  // 明确的问题或页面指令不需要再额外请求一次意图模型，避免“意图识别 → 普通回答”
  // 的双重等待；同时保证“添加一页/结束页/感谢观看界面”等指令直接进入执行链路。
  if (isDiscussionQuestion(text)) return { operation: 'discussion', data: { source: 'local-rule' }, local: true }
  if (isExplicitComponentOperation(text)) return { operation: 'modify_component', data: { source: 'local-rule' }, local: true }
  if (isAddPageInstruction(text) || isExplicitPageOperation(text) || isRevisionConfirmation(text)) {
    return { operation: 'modify_page', data: { source: 'local-rule' }, local: true }
  }
  try {
    // 对无法由快速路径确定的自然表达，使用工作台专用分类器。
    // 现有 API-13B 是“大纲字段提取”接口，不是工作台操作分类接口，不能直接拿它的结果
    // 判断“讨论/修改”，否则就会出现等待很久后仍然只回复文字的情况。
    const classifierData = await requestWorkbenchOperation(text)
    const result = {
      operation: workspaceOperationFromIntent(classifierData, text),
      data: classifierData,
    }
    intentFallbackShown.value = false
    // 明确的页面命令和上一轮方案确认优先执行，避免正式接口把“执行”误报成普通咨询。
    if (isExplicitComponentOperation(text)) return { ...result, operation: 'modify_component' }
    if (isExplicitPageOperation(text) || isRevisionConfirmation(text)) return { ...result, operation: 'modify_page' }
    if (isDiscussionQuestion(text)) return { ...result, operation: 'discussion' }
    return result
  } catch (error) {
    // 生产环境未提供工作台分类流时，保留 API-13B 和本地规则作为兼容回退。
    try {
      const result = await requestAssistantIntent(text)
      intentFallbackShown.value = false
      return result
    } catch (fallbackError) {
      error = fallbackError || error
    }
    if (!intentFallbackShown.value) {
      intentFallbackShown.value = true
      WorkspaceMessage.warning('正式意图识别暂时不可用，已使用本地规则继续处理；如分类不准确，请明确说“修改页面”“修改组件”“导出”或“打开项目”。')
    }
    return { operation: fallbackOperation, fallback: true, error }
  }
}
const buildRevisionInstruction = (instruction) => {
  const transcript = workspaceConversationTranscript()
  if (!transcript) return instruction
  return [
    '请继续执行创作工作台上一轮对话中已经讨论并确认的页面修改方案。',
    '最近对话记录：',
    transcript,
    `当前执行指令：${instruction}`,
    '如果当前执行指令是“执行”“应用”或“继续”，请根据对话中已经明确的具体方案直接修改当前页面，不要只回复说明。',
  ].join('\n\n')
}
const workspaceDiscussionContext = () => {
  const slide = current.value
  if (!slide) return ''
  const title = String(slide.title || '').trim()
  const notes = String(slide.notes || '').trim()
  const context = workspaceContextPayload()
  const resourceHint = context.resource_ids?.length ? `可用资料资源：${context.resource_ids.join('、')}` : ''
  const communityHint = context.community?.title ? `社区上下文：${context.community.title}` : ''
  return [
    '你正在为创作工作台生成一条文字回复。页面操作会由系统自动分流执行，不存在需要教师手动切换的“讨论模式”或“修改模式”。如果最后一条消息是在表达明确修改需求，不要声称无法修改、不要要求切换模式；只在需求确实不清楚时，针对该条消息提出一个简短问题。不要输出 HTML。',
    '只围绕最后一条教师消息回答或确认。前序对话仅用于理解其中的指代；不要重提、合并或重新确认前序页面操作。除非最后一条教师消息明确要求“继续”“按刚才方案”“撤销”或指向此前操作，否则视为那些操作已完成。',
    `本次目标锁定：${assistantTargetLabel.value}。${assistantTargetDescription.value}`,
    title ? `当前页面：${title}` : '',
    notes ? `当前页面备注：${notes.slice(0, 600)}` : '',
    resourceHint,
    communityHint,
  ].filter(Boolean).join('\n')
}
const readWorkspaceDiscussionStream = async (response, assistantMessage) => {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('模型没有返回可读取的数据流')
  const decoder = new TextDecoder()
  let buffer = ''
  let content = ''
  const consumeLine = (line) => {
    if (!line.startsWith('data:')) return
    const data = line.slice(5).trim()
    if (!data || data === '[DONE]') return
    try {
      const payload = JSON.parse(data)
      const delta = payload?.choices?.[0]?.delta?.content ?? payload?.choices?.[0]?.message?.content
      if (typeof delta === 'string' && delta) {
        content += delta
        assistantMessage.text = content
        void scrollAssistantConversation()
      }
    } catch {
      // 不完整的 SSE 行会在下一次读取时拼接后再解析。
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() || ''
    lines.forEach(consumeLine)
    if (done) break
  }
  if (buffer.trim()) consumeLine(buffer)
  if (!content.trim()) throw new Error('模型未返回有效内容')
  assistantMessage.text = content
  assistantMessage.streaming = false
  return content
}
const submitDiscussion = async () => {
  const text = prompt.value.trim()
  if (!text || isAssistantSubmitting.value) return
  const history = workspaceDiscussionHistory()
  const context = workspaceDiscussionContext()
  messages.push({ role: 'user', text, includeInContext: true, kind: 'discussion-request' })
  prompt.value = ''
  // 流式读取会持续写入 text / streaming；必须保留代理对象，才能即时触发侧边对话重绘。
  const assistantMessage = reactive({
    role: 'assistant',
    text: '',
    streaming: true,
    includeInContext: true,
    kind: 'discussion-reply',
  })
  messages.push(assistantMessage)
  discussionSubmitting.value = true
  void scrollAssistantConversation()
  try {
    await withWorkspaceChatTimeout(async (signal) => {
      const response = await streamGeneralChat({
        user_id: String(userStore.userInfo?.user_id || '10001'),
        messages: [
          ...history,
          ...(context ? [{ role: 'user', content: context }] : []),
          { role: 'user', content: text },
        ],
      }, { signal })
      if (!response.ok) {
        let message = ''
        try {
          const payload = await response.json()
          message = payload?.message || ''
        } catch {
          // 保留 HTTP 状态作为错误信息。
        }
        throw new Error(message || `模型请求失败（HTTP ${response.status}）`)
      }
      return readWorkspaceDiscussionStream(response, assistantMessage)
    })
  } catch (error) {
    assistantMessage.streaming = false
    assistantMessage.kind = 'discussion-error'
    assistantMessage.includeInContext = false
    assistantMessage.text = `讨论暂时无法继续：${error?.message || '连接失败，请检查模型配置。'}`
    WorkspaceMessage.error(error?.message || '大模型连接失败，请检查配置')
  } finally {
    discussionSubmitting.value = false
    void scrollAssistantConversation()
  }
}

const runStorageKey = () => `a12:workspace-run:${String(sessionId.value || '')}`
const formatRunDuration = (startedAt = clientRunStartedAt.value, finishedAt = Date.now()) => {
  const elapsedMs = Math.max(0, Number(finishedAt || 0) - Number(startedAt || 0))
  if (elapsedMs < 1_000) return `${elapsedMs}ms`
  const seconds = Math.round(elapsedMs / 100) / 10
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`
}
const runStatusLabel = (status = '') => ({
  pending: '等待', queued: '排队中', running: '执行中', executing: '执行中', processing: '处理中',
  success: '已完成', completed: '已完成', done: '已完成', failed: '失败', error: '失败',
}[String(status).toLowerCase()] || String(status || '记录'))
const normalizeRunReflection = (raw) => {
  if (!raw) return null
  const parsed = parseJson(raw, raw)
  if (typeof parsed === 'string') return { summary: parsed, suggestions: [], relation: '', raw: parsed }
  if (!parsed || typeof parsed !== 'object') return null
  return {
    summary: String(parsed.summary || parsed.reflection || parsed.analysis || parsed.message || '').trim(),
    strengths: qualityArray(parsed.strengths || parsed.good_points || parsed.positives),
    issues: qualityArray(parsed.issues || parsed.problems || parsed.risks),
    suggestions: qualityArray(parsed.suggestions || parsed.fixes || parsed.recommendations || parsed.improvements),
    relation: String(parsed.relation || parsed.change_relation || parsed.before_after || parsed.modification_relation || '').trim(),
    raw: parsed,
  }
}
const clientRunSnapshot = () => ({
  version: 1,
  kind: 'browser-html-ppt',
  runId: activeRunId.value,
  status: runStatus.value,
  progress: runProgress.value,
  stage: runStage.value,
  startedAt: clientRunStartedAt.value,
  updatedAt: Date.now(),
  timeline: runTimeline.value,
  toolCalls: runToolCalls.value,
  requestedResources: runRetrievalSources.value,
  reflection: runReflection.value,
  failureReason: runFailureReason.value,
  recoveryNode: runRecoveryNode.value,
})
const persistActiveRun = () => {
  if (!sessionId.value || !activeRunId.value || typeof window === 'undefined') return
  try { sessionStorage.setItem(runStorageKey(), JSON.stringify(clientRunSnapshot())) } catch { /* 私密模式或空间不足时不阻断生成 */ }
}
const clearActiveRun = ({ retainSnapshot = false } = {}) => {
  if (!retainSnapshot && sessionId.value && typeof window !== 'undefined') sessionStorage.removeItem(runStorageKey())
  activeRunId.value = ''
}
const resetRunObservability = () => {
  runTimeline.value = []
  runToolCalls.value = []
  runRetrievalSources.value = []
  runReflection.value = null
  runRecoveryNode.value = ''
  runFailureReason.value = ''
  clientRunStartedAt.value = 0
}
const upsertClientRunStep = ({ id, label, status = 'running', detail = '' } = {}) => {
  const stepId = String(id || label || `step-${runTimeline.value.length + 1}`)
  const next = {
    id: stepId,
    kind: 'browser-call',
    label: String(label || '浏览器执行步骤'),
    status: String(status || 'running').toLowerCase(),
    statusLabel: runStatusLabel(status),
    detail: String(detail || '').trim(),
  }
  const index = runTimeline.value.findIndex((item) => item.id === stepId)
  if (index >= 0) runTimeline.value.splice(index, 1, { ...runTimeline.value[index], ...next })
  else runTimeline.value.push(next)
  if (runTimeline.value.length > 30) runTimeline.value.splice(0, runTimeline.value.length - 30)
}
const upsertClientToolCall = ({ id, name, status = 'running', detail = '' } = {}) => {
  const toolId = String(id || name || `tool-${runToolCalls.value.length + 1}`)
  const next = {
    id: toolId,
    name: String(name || '浏览器请求'),
    status: runStatusLabel(status),
    detail: String(detail || '').trim(),
  }
  const index = runToolCalls.value.findIndex((item) => item.id === toolId)
  if (index >= 0) runToolCalls.value.splice(index, 1, { ...runToolCalls.value[index], ...next })
  else runToolCalls.value.push(next)
  if (runToolCalls.value.length > 20) runToolCalls.value.splice(0, runToolCalls.value.length - 20)
}
const setClientRunStage = ({ id, label, status = 'running', progress, detail = '' } = {}) => {
  if (label) runStage.value = String(label)
  if (Number.isFinite(Number(progress))) runProgress.value = Math.max(0, Math.min(100, Math.round(Number(progress))))
  upsertClientRunStep({ id, label: label || runStage.value, status, detail })
  persistActiveRun()
}
const setClientRunRequestedResources = () => {
  const context = workspaceContextPayload()
  const resourceIds = normalizedResourceIds(context.resource_ids || context.resourceIds || [])
  runRetrievalSources.value = resourceIds.map((id) => {
    const resource = workspaceResources.value.find((item) => String(item.id) === String(id))
    return {
      id: String(id),
      name: resource?.name || `资料 ${id}`,
      detail: '已绑定到本次生成请求',
    }
  })
}
const attachClientRunReflection = (raw) => {
  const report = normalizeQualityReport(raw)
  if (!report) return
  runReflection.value = {
    summary: report.summary || (report.score === null ? '已完成生成质量检查。' : `生成质量评分：${report.score}/100。`),
    strengths: [],
    issues: report.issues,
    suggestions: report.suggestions,
    relation: 'HTML PPT 生成质量检查',
    raw: report.raw,
  }
}
const startTrackedRun = () => {
  activeRunId.value = `browser-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  clientRunStartedAt.value = Date.now()
  setClientRunRequestedResources()
  setClientRunStage({
    id: 'confirmed-plan',
    label: '正在核验已确认的大纲',
    status: 'running',
    progress: 6,
    detail: '以服务端确认状态为准',
  })
}
const finishTrackedRun = () => {
  const elapsed = formatRunDuration()
  setClientRunStage({
    id: 'project-save',
    label: 'HTML PPT 已生成并保存',
    status: 'completed',
    progress: 100,
    detail: `本次浏览器实际执行用时 ${elapsed}`,
  })
  runStatus.value = 'completed'
  persistActiveRun()
  clearActiveRun()
}
const failTrackedRun = (error) => {
  const message = generationErrorMessage(error)
  runStatus.value = 'failed'
  runProgress.value = 0
  runStage.value = 'HTML PPT 生成失败'
  runFailureReason.value = message
  runRecoveryNode.value = '修复问题后可点击“重新生成”，系统会重新核验大纲。'
  setClientRunStage({ id: 'generation-failed', label: runStage.value, status: 'failed', detail: message })
  persistActiveRun()
  clearActiveRun()
  return message
}
const restoreTrackedRun = () => {
  if (!sessionId.value || activeRunId.value || typeof window === 'undefined') return false
  const saved = parseJson(sessionStorage.getItem(runStorageKey()), null)
  if (!saved?.runId) return false
  // 清理旧版服务端 Run 快照；它无法反映真实生成状态，不能再续接。
  if (saved.kind !== 'browser-html-ppt') {
    sessionStorage.removeItem(runStorageKey())
    return false
  }
  activeRunId.value = String(saved.runId)
  clientRunStartedAt.value = Number(saved.startedAt) || 0
  runTimeline.value = Array.isArray(saved.timeline) ? saved.timeline : []
  runToolCalls.value = Array.isArray(saved.toolCalls) ? saved.toolCalls : []
  runRetrievalSources.value = Array.isArray(saved.requestedResources) ? saved.requestedResources : []
  runReflection.value = saved.reflection || null
  if (saved.status === 'running') {
    const message = '上一次生成因页面刷新或浏览器关闭而中断；已保留可用草稿，点击“重新生成”即可安全恢复。'
    runStatus.value = 'failed'
    runProgress.value = Number(saved.progress) || 0
    runStage.value = '上一次生成已中断'
    runFailureReason.value = message
    runRecoveryNode.value = '重新生成会重新读取服务端已确认的大纲。'
    upsertClientRunStep({ id: 'interrupted', label: runStage.value, status: 'failed', detail: message })
    clearActiveRun()
    return true
  }
  clearActiveRun()
  return false
}
const validateGeneratedSlides = async (candidateSlides, label = 'AI 返回的课件') => {
  const htmlSlides = candidateSlides.filter((slide) => String(slide?.html || '').trim())
  if (!htmlSlides.length) throw new Error(`${label}未包含可校验的 HTML 页面`)
  const validations = await Promise.all(htmlSlides.map(async (slide, index) => {
    const result = unwrapResponse(await validatePresentationHtml({ html: slide.html, strict: false })) || {}
    return { index, result }
  }))
  const failed = validations.find(({ result }) => result.valid === false)
  if (failed) {
    const details = Array.isArray(failed.result.errors) ? failed.result.errors.filter(Boolean).join('；') : ''
    throw new Error(`第 ${failed.index + 1} 页 HTML 校验未通过${details ? `：${details}` : ''}`)
  }
}

const startRun = async () => {
  if (projectId.value || runStatus.value === 'running') return
  if (presentationFixtureMode.value) {
    try {
      loadPresentationFixture()
    } catch (error) {
      runStatus.value = 'failed'
      runProgress.value = 0
      runStage.value = '测试样例加载失败'
      generationError.value = error?.message || '固定 PPT 测试样例加载失败'
      WorkspaceMessage.error(generationError.value)
    }
    return
  }
  if (!sessionId.value) {
    if (!route.query.pptGeneration) return
    runStatus.value = 'failed'
    runStage.value = 'HTML PPT 生成失败'
    generationError.value = '当前页面缺少备课会话，无法读取已确认的大纲。'
    return
  }

  generationError.value = ''

  // 无论是恢复浏览器草稿还是发起新的生成，都必须先以服务端确认状态为准。
  // 否则旧草稿可能在“大纲未确认/确认已失效”的情况下被直接写回项目。
  let serverPlan = null
  try {
    serverPlan = unwrapResponse(await getAiPlan(sessionId.value)) || {}
    if (String(serverPlan?.plan_confirm_status || '').toLowerCase() !== 'confirmed') {
      throw new Error('教学设计大纲尚未在服务端确认，请返回对话确认后再生成课件。')
    }
  } catch (error) {
    runStatus.value = 'failed'
    runProgress.value = 0
    runStage.value = '教学设计大纲未确认'
    generationError.value = generationErrorMessage(error)
    runFailureReason.value = generationError.value
    runRecoveryNode.value = '请返回教学助手确认大纲后，再重新生成或恢复草稿。'
    WorkspaceMessage.error(generationError.value)
    return
  }

  const generationKey = String(routeQueryValue(route.query.pptGeneration) || '')
  const cachedDraft = readPresentationDraft(sessionId.value)
  if (cachedDraft?.slides?.length && (!generationKey || cachedDraft.request_key === generationKey)) {
    try {
      applyGeneratedPresentation(cachedDraft, { persist: false, notify: false })
      messages.push({ role: 'assistant', text: `已载入 ${cachedDraft.slides.length} 页 HTML PPT 草稿。`, includeInContext: false, kind: 'generation-success' })
      // 恢复本地草稿后立即创建/回写项目，避免只恢复了界面状态，刷新或换设备又丢失内容。
      runStage.value = '正在将本地草稿回写项目'
      await persistGeneratedPresentationProject()
      autosaveState.value = '已保存 · 草稿已回写'
      runStatus.value = 'completed'
      runProgress.value = 100
      runStage.value = 'HTML PPT 草稿已回写项目'
      void scrollAssistantConversation()
      return
    } catch (error) {
      WorkspaceMessage.warning(error?.message || '本地草稿已载入，但服务器回写失败；请稍后重试保存。')
      void scrollAssistantConversation()
      return
    }
  }

  resetRunObservability()
  runStatus.value = 'running'

  try {
    startTrackedRun()
    setClientRunStage({ id: 'confirmed-plan', label: '已核验教学设计大纲', status: 'completed', progress: 16 })

    // 本地开发时真实 Python 大纲保存在本地快照；生产环境仍以服务端确认状态为准。
    const localOutlineDraft = readOutlineDraft(sessionId.value)
    const planData = localOutlineDraft?.plan_json
      ? localOutlineDraft
      : serverPlan
    const outline = {
      ...normalizeOutlinePayload(planData),
      workspace_context: workspaceContextPayload(),
    }
    if (!Object.keys(outline).length) throw new Error('未找到已确认的大纲，请返回对话重新确认')

    setClientRunStage({ id: 'presentation-generate', label: '正在调用 HTML PPT 生成服务', status: 'running', progress: 22 })
    const generationStartedAt = Date.now()
    upsertClientToolCall({ id: 'presentation-generate', name: 'HTML PPT 生成服务', status: 'running' })
    const numericSessionId = Number(sessionId.value)
    const selectedTheme = String(routeQueryValue(route.query.pptTheme) || '').trim()
    const outlineId = planData.python_outline_id || outline.outline_id
    const payload = {
      ...(Number.isInteger(numericSessionId) && numericSessionId > 0 ? { session_id: numericSessionId } : {}),
      ...(outlineId ? { outline_id: String(outlineId) } : {}),
      title: String(outline.title || planData.title || 'A12 教学课件'),
      outline,
      ...(selectedTheme ? { theme: selectedTheme } : {}),
      aspect_ratio: '16:9',
      language: 'zh-CN',
      // 由服务端结合用户原始要求、学科和逐页内容自动判断无图/占位/AI 配图。
      asset_policy: 'auto',
    }
    const streamedSlides = []
    const response = await generatePresentationStream(payload, {
      onSlide: ({ slide, completed, total }) => {
        if (!slide) return
        streamedSlides.push(slide)
        const ordered = [...streamedSlides].sort((a, b) => Number(a.slide_no || 0) - Number(b.slide_no || 0))
        applyGeneratedPresentation({ data: { title: payload.title, slides: ordered } }, { persist: false, notify: false })
        const progress = 22 + Math.round((Number(completed || ordered.length) / Math.max(1, Number(total || ordered.length))) * 58)
        setClientRunStage({
          id: 'presentation-generate',
          label: `正在生成 HTML 页面（${completed || ordered.length}/${total || ordered.length}）`,
          status: 'running',
          progress,
        })
      },
    })
    upsertClientToolCall({
      id: 'presentation-generate',
      name: 'HTML PPT 生成服务',
      status: 'completed',
      detail: `响应耗时 ${formatRunDuration(generationStartedAt)}`,
    })
    setClientRunStage({ id: 'presentation-generate', label: 'HTML PPT 已返回，正在校验页面', status: 'completed', progress: 84 })
    setClientRunStage({ id: 'html-validate', label: '正在校验 HTML 页面', status: 'running', progress: 88 })
    upsertClientToolCall({ id: 'html-validate', name: 'HTML 页面校验', status: 'running' })
    const generated = normalizePresentationSlides(getPresentationPayload(response))
    await validateGeneratedSlides(generated)
    upsertClientToolCall({ id: 'html-validate', name: 'HTML 页面校验', status: 'completed', detail: `已通过 ${generated.length} 页校验` })
    setClientRunStage({ id: 'html-validate', label: 'HTML 页面校验通过', status: 'completed', progress: 90 })
    setClientRunStage({ id: 'presentation-load', label: '正在装载 HTML 页面', status: 'running', progress: 91 })
    applyGeneratedPresentation(response)
    // 从会话进入工作台的课件不能只留在浏览器草稿：生成成功即创建项目与页面，
    // 后续刷新、退出和版本管理均以服务端项目为准。
    setClientRunStage({ id: 'project-save', label: '正在保存课件项目', status: 'running', progress: 95 })
    upsertClientToolCall({ id: 'project-save', name: '项目与页面保存', status: 'running' })
    await persistGeneratedPresentationProject()
    upsertClientToolCall({ id: 'project-save', name: '项目与页面保存', status: 'completed', detail: '课件已写入项目' })
    finishTrackedRun()
  } catch (error) {
    generationError.value = failTrackedRun(error)
    messages.push({ role: 'assistant', text: generationError.value, includeInContext: false, kind: 'generation-error' })
    WorkspaceMessage.error(generationError.value)
    void scrollAssistantConversation()
  }
}
const retryPresentationGeneration = () => { void startRun() }
const pageInsertionIndex = (instruction = '') => {
  const value = String(instruction).trim().replace(/\s+/g, '')
  const afterMatch = value.match(/第\s*(\d{1,3})\s*页(?:后|之后)/)
  if (afterMatch) return Math.max(0, Math.min(slides.length, Number(afterMatch[1])))
  const beforeMatch = value.match(/第\s*(\d{1,3})\s*页(?:前|之前)/)
  if (beforeMatch) return Math.max(0, Math.min(slides.length, Number(beforeMatch[1]) - 1))
  if (/(末尾|最后|结尾)/.test(value)) return slides.length
  return Math.max(0, Math.min(slides.length, selectedSlide.value + 1))
}
const addedPageTitle = (instruction = '') => {
  const value = String(instruction).trim()
  const quoted = value.match(/[“"「『](.+?)[”"」』]/)
  if (quoted?.[1]?.trim()) return quoted[1].trim().slice(0, 40)
  const namedPage = value.match(/(?:添加|增加|新增|插入|补充|新建|追加|加(?:上)?)(?:一个|个|一张|一页)?(?:名为|标题为|叫做)?\s*([^，。；,;]{1,30}?)(?:的)?(?:页面|幻灯片|界面|封面|开场页|首页|结束页|尾页)/)
  if (namedPage?.[1]?.trim()) return namedPage[1].trim().replace(/^(一个|一张|一页)/, '').slice(0, 40)
  const keyword = value.match(/(感谢观看|感谢|封面|开场|首页|结束|总结|小结|练习|活动|案例|导入|拓展|互动|讨论)/)
  return keyword ? `${keyword[1]}页` : '新增页面'
}
const executeAddPageInstruction = async (instruction) => {
  const insertAt = pageInsertionIndex(instruction)
  const title = addedPageTitle(instruction)
  const sourceSlide = current.value || slides.find((slide) => slide)
  const sourceHtml = slideHtmlSource(sourceSlide)
  let generatedSlide = null

  // 新增页面只调用单页接口生成新页，绝不把整套 slides 交给整套修改接口。
  // 这样 AI 即使重新生成了新增页，也不会有机会覆盖原来的页面。
  if (sourceSlide && sourceHtml) {
    try {
      const sourceIndex = Math.max(0, slides.indexOf(sourceSlide))
      const response = unwrapResponse(await modifyPresentationSlide({
        ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
        slide_no: sourceIndex + 1,
        current_html: sourceHtml,
        instruction: [
          '这是一个新增页面生成请求，不是对原页面的修改。',
          `请生成一张独立的新页面，页面标题为“${title}”。`,
          `新增页面要求：${instruction}`,
          '只返回这张新增页面的完整 HTML，保持当前课件的视觉风格；不要修改或重写其他页面。',
        ].join('\n'),
          outline_context: {
          deck_title: String(project.value?.project_name || route.query.templateTitle || sourceSlide.title || 'A12 教学课件'),
          current_slide_title: title,
          current_slide_no: insertAt + 1,
          selected_element: null,
          conversation_context: workspaceConversationTranscript() || null,
          workspace_context: workspaceContextPayload(),
        },
        theme: String(routeQueryValue(route.query.pptTheme) || presentationMetadata.value?.theme || sourceSlide.theme || '').trim() || undefined,
        keep_style: true,
      }))
      const payload = getGeneratedPagePayload(response)
      const html = payload?.content?.html ?? payload?.candidate?.html ?? payload?.content?.page_html ?? payload?.candidate?.page_html
      if (typeof html === 'string' && html.trim()) {
        generatedSlide = normalizePresentationSlides({ slides: [{
          ...sourceSlide,
          ...(payload.candidate || {}),
          ...(payload.content || {}),
          title,
          slide_no: insertAt + 1,
          html: html.trim(),
          elements: [],
          metadata: {
            ...(sourceSlide.metadata || {}),
            ...(payload.candidate?.metadata || {}),
            ...(payload.content?.metadata || {}),
            added_by_ai: true,
          },
        }] })[0] || null
      }
    } catch {
      // 单页生成失败时保留本地新增页面，不能退化为整套课件重生成。
    }
  }

  const isCoverPage = /(封面|开场页|首页|开场)/.test(String(instruction).replace(/\s+/g, ''))
  const slide = await addSlide({
    insertAt,
    title,
    slideData: generatedSlide || (isCoverPage ? {
      layout: '重点陈述',
      pageType: 'cover',
      page_type: 'cover',
      eyebrow: '课程封面',
    } : null),
  })
  return { title: slide.title, generated: Boolean(generatedSlide) }
}
const isDeckRevisionInstruction = (instruction = '') => /(?:整套|全套|所有页|全部页面|每一页|全局|整体).{0,18}(?:课件|幻灯片|页面|字体|配色|风格|版式)|统一.{0,18}(?:课件|幻灯片|页面|字体|配色|风格|版式)/.test(String(instruction).replace(/\s+/g, ''))
const cloneRevisionSlides = (value) => {
  try { return JSON.parse(JSON.stringify(Array.isArray(value) ? value : [])) } catch { return [] }
}
const revisionSlideKey = (slide, index = 0) => String(
  slide?.pageId
  || slide?.page_id
  || slide?.componentId
  || slide?.metadata?.source_page_id
  || slide?.metadata?.page_id
  || `slide-${index + 1}`,
)
const revisionOperationType = (operation = {}) => {
  const raw = String(
    operation?.type
    || operation?.operation
    || operation?.action
    || operation?.kind
    || operation?.change_type
    || operation?.changeType
    || '',
  ).toLowerCase()
  if (/(add|insert|create|新增|添加|插入)/.test(raw)) return 'add'
  if (/(delete|remove|drop|删除|移除)/.test(raw)) return 'delete'
  if (/(reorder|move|sort|重排|移动|调整顺序)/.test(raw)) return 'reorder'
  return 'modify'
}
const revisionOperationLabel = (type) => ({ add: '新增', delete: '删除', reorder: '重排', modify: '修改' }[type] || '修改')
const revisionOperationDescription = (operation = {}, fallbackType = 'modify') => {
  const type = revisionOperationType({ ...operation, type: operation?.type || fallbackType })
  const page = operation?.slide_no ?? operation?.slideNo ?? operation?.page_no ?? operation?.pageNo
  const from = operation?.from ?? operation?.from_index ?? operation?.fromIndex
  const to = operation?.to ?? operation?.to_index ?? operation?.toIndex
  const title = String(operation?.title || operation?.slide_title || operation?.page_title || '').trim()
  if (type === 'reorder' && (from !== undefined || to !== undefined)) return `第 ${Number(from) + 1} 页 → 第 ${Number(to) + 1} 页`
  if (title) return page ? `第 ${page} 页 · ${title}` : title
  if (page) return `第 ${page} 页`
  return String(operation?.description || operation?.summary || operation?.message || '页面内容')
}
const computedRevisionOperations = (before = [], after = []) => {
  const operations = []
  const beforeMap = new Map(before.map((slide, index) => [revisionSlideKey(slide, index), { slide, index }]))
  const afterMap = new Map(after.map((slide, index) => [revisionSlideKey(slide, index), { slide, index }]))
  after.forEach((slide, index) => {
    const key = revisionSlideKey(slide, index)
    const previous = beforeMap.get(key)
    if (!previous) {
      operations.push({ type: 'add', page_no: index + 1, title: slide.title, description: `第 ${index + 1} 页 · ${slide.title}` })
      return
    }
    if (previous.index !== index) operations.push({ type: 'reorder', from_index: previous.index, to_index: index, title: slide.title })
    if (String(previous.slide?.title || '') !== String(slide?.title || '') || String(previous.slide?.html || '') !== String(slide?.html || '')) {
      operations.push({ type: 'modify', page_no: index + 1, title: slide.title })
    }
  })
  before.forEach((slide, index) => {
    if (!afterMap.has(revisionSlideKey(slide, index))) operations.push({ type: 'delete', page_no: index + 1, title: slide.title, description: `第 ${index + 1} 页 · ${slide.title}` })
  })
  return operations
}
const normalizeRevisionOperations = (data = {}, before = [], after = []) => {
  const raw = data?.operations || data?.changes || data?.change_operations || data?.changeOperations
  const parsed = parseJson(raw, raw)
  const source = Array.isArray(parsed)
    ? parsed
    : Array.isArray(data?.added_slides) || Array.isArray(data?.deleted_slides) || Array.isArray(data?.reordered_slides)
      ? [
        ...(Array.isArray(data.added_slides) ? data.added_slides.map((item) => ({ ...item, type: 'add' })) : []),
        ...(Array.isArray(data.deleted_slides) ? data.deleted_slides.map((item) => ({ ...item, type: 'delete' })) : []),
        ...(Array.isArray(data.reordered_slides) ? data.reordered_slides.map((item) => ({ ...item, type: 'reorder' })) : []),
      ]
      : []
  const normalized = source.map((operation, index) => {
    const type = revisionOperationType(operation)
    return {
      ...operation,
      id: operation?.id || `revision-operation-${index}`,
      type,
      label: revisionOperationLabel(type),
      description: revisionOperationDescription(operation, type),
    }
  })
  if (normalized.length) return normalized
  return computedRevisionOperations(before, after).map((operation, index) => ({
    ...operation,
    id: `computed-revision-operation-${index}`,
    label: revisionOperationLabel(operation.type),
    description: revisionOperationDescription(operation, operation.type),
  }))
}
const revisionChangeSummary = (data = {}, operations = [], before = [], after = []) => {
  const raw = data?.change_summary ?? data?.changeSummary
  if (typeof raw === 'string' && raw.trim()) return raw.trim()
  if (raw && typeof raw === 'object') {
    const summary = raw.summary || raw.description || raw.text || raw.message
    if (summary) return String(summary)
  }
  const count = (type) => operations.filter((operation) => operation.type === type).length
  const parts = [
    count('add') ? `新增 ${count('add')} 页` : '',
    count('delete') ? `删除 ${count('delete')} 页` : '',
    count('reorder') ? `重排 ${count('reorder')} 页` : '',
    count('modify') ? `修改 ${count('modify')} 页` : '',
  ].filter(Boolean)
  return parts.length ? parts.join('，') : `页面数量由 ${before.length} 页调整为 ${after.length} 页`
}
const applyDeckRevision = async (instruction, conversationTranscript) => {
  if (!slides.length) throw new Error('当前课件没有可修改的页面')
  revisionStage.value = '正在规划整套课件修改…'
  const localOutlineDraft = sessionId.value ? readOutlineDraft(sessionId.value) : null
  const response = unwrapResponse(await modifyPresentation({
    ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
    title: String(project.value?.project_name || route.query.templateTitle || slides[0]?.title || 'A12 教学课件'),
    slides: slides.map((slide, index) => ({
      slide_no: index + 1,
      ...(slide.pageId ? { page_id: Number(slide.pageId), source_page_id: Number(slide.pageId) } : {}),
      title: slide.title,
      html: slideHtmlSource(slide),
      notes: slide.notes || '',
      metadata: {
        ...(slide.metadata || {}),
        ...(slide.pageId ? { source_page_id: Number(slide.pageId), page_id: Number(slide.pageId) } : {}),
      },
    })),
    instruction,
    outline: {
      ...normalizeOutlinePayload(localOutlineDraft || presentationMetadata.value || {}),
      workspace_context: workspaceContextPayload(),
      ...(conversationTranscript ? { conversation_context: conversationTranscript } : {}),
    },
    theme: String(routeQueryValue(route.query.pptTheme) || presentationMetadata.value?.theme || current.value?.theme || '').trim() || undefined,
    keep_style: true,
  }))
  const data = getPresentationPayload(response)
  const nextSlides = normalizePresentationSlides(data)
  revisionStage.value = '正在校验整套 HTML 页面…'
  await validateGeneratedSlides(nextSlides, '整套课件修改结果')
  const previousPageIds = slides.map((slide) => slide.pageId || slide.page_id || slide.componentId).filter(Boolean)
  const before = cloneRevisionSlides(slides)
  const after = cloneRevisionSlides(nextSlides)
  const operations = normalizeRevisionOperations(data, before, after)
  pendingDeckRevision.value = {
    data,
    before,
    after,
    previousPageIds,
    operations,
    summary: revisionChangeSummary(data, operations, before, after),
    instruction,
  }
  revisionPreviewVisible.value = true
  return pendingDeckRevision.value
}

const sendRevisionFeedback = (action, preview, extra = {}) => recordAiFeedback({
  session_id: sessionId.value ? String(sessionId.value) : null,
  project_id: projectId.value ? String(projectId.value) : null,
  action,
  target_type: 'presentation',
  instruction: preview?.instruction || '',
  change_summary: preview?.summary || '',
  before_data: { slide_count: preview?.before?.length || 0 },
  after_data: { slide_count: preview?.after?.length || 0 },
  metadata: { ...extra, theme: current.value?.theme || '' },
}).catch(() => null)

const rejectDeckRevision = () => {
  const preview = pendingDeckRevision.value
  if (preview) sendRevisionFeedback('reject', preview)
  pendingDeckRevision.value = null
  revisionPreviewVisible.value = false
  messages.push({ role: 'assistant', text: '已取消这次整套课件修改，当前页面保持不变。', includeInContext: false, kind: 'revision-preview-rejected' })
}

const acceptDeckRevision = async () => {
  const preview = pendingDeckRevision.value
  if (!preview) return
  revisionPreviewVisible.value = false
  revisionStage.value = '正在应用已确认的整套课件修改…'
  try {
    revisionUndoSnapshot.value = cloneRevisionSlides(preview.before)
    applyGeneratedPresentation(preview.data, { persist: true, notify: false })
    if (projectId.value) {
      const retainedPageIds = new Set(slides.map((slide) => String(slide.pageId || slide.page_id || slide.componentId || '')).filter(Boolean))
      await persistSlideOrder({
        deletedPageIds: preview.previousPageIds.filter((id) => !retainedPageIds.has(String(id))),
        throwOnError: true,
      })
    }
    closeDiscussionContext()
    messages.push({
      role: 'assistant',
      text: `已按预览应用整套课件修改${preview.after.length ? `，共 ${preview.after.length} 页` : ''}。如需恢复，可点击“撤销本次 AI 修改”。`,
      includeInContext: false,
      kind: 'revision-result',
    })
    WorkspaceMessage.success('整套课件修改已确认并保存')
    sendRevisionFeedback('accept', preview)
    pendingDeckRevision.value = null
  } catch (error) {
    revisionPreviewVisible.value = true
    WorkspaceMessage.error(error?.message || '确认后的整套修改保存失败，当前预览仍可继续处理')
  } finally {
    revisionStage.value = ''
  }
}

const undoLastAiRevision = async () => {
  const snapshot = revisionUndoSnapshot.value
  if (!snapshot?.length) return
  try {
    const currentPageIds = slides.map((slide) => slide.pageId || slide.page_id || slide.componentId).filter(Boolean)
    slides.splice(0, slides.length, ...cloneRevisionSlides(snapshot))
    selectedSlide.value = Math.min(selectedSlide.value, Math.max(0, slides.length - 1))
    selectedElementId.value = null
    htmlSelectionRestoreKey.value = ''
    htmlElements.value = []
    htmlSelectedElementId.value = null
    htmlSelectedElement.value = null
    markSlideComponentDirty(slides[selectedSlide.value], 'deck:undo', { structure: true })
    if (projectId.value) {
      await persistSlideOrder({
        deletedPageIds: currentPageIds.filter((id) => !new Set(slides.map((slide) => String(slide.pageId || slide.page_id || slide.componentId || '')).filter(Boolean)).has(String(id))),
        throwOnError: true,
      })
    } else if (sessionId.value) saveCurrentPresentationDraft()
    revisionUndoSnapshot.value = null
    messages.push({ role: 'assistant', text: '已撤销最近一次 AI 整套修改，恢复到修改前版本。', includeInContext: false, kind: 'revision-undo' })
    WorkspaceMessage.success('已撤销本次 AI 修改')
    sendRevisionFeedback('undo', { before: snapshot, after: slides, summary: '撤销最近一次AI整套修改' })
  } catch (error) {
    WorkspaceMessage.error(error?.message || '撤销失败，请稍后重试')
  }
}
const comparableH5Html = (source) => String(source || '')
  .replace(/<meta\b[^>]*http-equiv\s*=\s*(['"]?)content-security-policy\1[^>]*>/gi, '')
  .replace(/<script\b[^>]*\bid\s*=\s*(['"])a12-h5-runtime-config\1[^>]*>[\s\S]*?<\/script\s*>/gi, '')
  .replace(/\s+/g, ' ')
  .trim()
const reviseSelectedH5WithAi = async (selectedElement, instruction) => {
  const controller = await waitForHtmlController(current.value)
  if (!controller) throw new Error('当前页面尚未完成加载，无法修改 H5 组件')
  const metadata = selectedElement?.metadata && typeof selectedElement.metadata === 'object' && !Array.isArray(selectedElement.metadata)
    ? selectedElement.metadata
    : {}
  const pptContext = interactivePptContext()
  const rawKnowledgePoints = metadata.knowledge_points || metadata.knowledgePoints || []
  const knowledgePoints = Array.isArray(rawKnowledgePoints)
    ? rawKnowledgePoints.map((item) => String(item || '').trim()).filter(Boolean)
    : String(rawKnowledgePoints || current.value?.description || '').split(/[,，\n]/).map((item) => item.trim()).filter(Boolean)
  const moduleType = normalizeInteractiveModuleType(selectedElement.module_type || selectedElement.moduleType || metadata.module_type)
  const response = unwrapResponse(await generateInteractiveModule({
    title: selectedElement.name || selectedElement.content || current.value?.title || 'H5 课堂互动',
    topic: selectedElement.topic || metadata.topic || current.value?.title || '课堂互动',
    module_type: moduleType === 'unknown' ? 'animation' : moduleType,
    subject: metadata.subject || pptContext.subject || undefined,
    grade: metadata.grade || pptContext.grade || undefined,
    knowledge_points: knowledgePoints,
    requirements: [metadata.requirements, `本次修改要求：${instruction}`, '必须在现有 H5 基础上产生可见、可操作的真实变化。'].filter(Boolean).join('\n'),
    theme: metadata.theme || theme.value?.name || undefined,
    embed_mode: selectedElement.embed_mode || selectedElement.embedMode || 'standalone',
    language: metadata.language || 'zh-CN',
    current_html: selectedElement.html || '',
    regenerate_instruction: instruction,
  }))
  if (!response?.html) throw new Error('H5 修改接口未返回可用的 HTML')
  if (comparableH5Html(response.html) === comparableH5Html(selectedElement.html)) {
    throw new Error('H5 修改结果与原组件完全相同，未应用本次修改')
  }
  const revisedModule = interactiveAssetFromModule(response)
  const inserted = controller.insertInteractive?.(revisedModule, selectedElement.position)
  if (!inserted) throw new Error('修改后的 H5 无法插入当前页面')
  controller.deleteSelected?.(selectedElement.id)
  const revisedId = `a12-h5-${revisedModule.module_id || revisedModule.moduleId}`
  controller.selectById?.(revisedId)
  const previousModuleId = String(selectedElement.module_id || selectedElement.moduleId || '')
  if (Array.isArray(current.value?.interactive_assets)) {
    current.value.interactive_assets = current.value.interactive_assets.filter((asset) => String(asset?.module_id || asset?.moduleId || '') !== previousModuleId)
  }
  appendInteractiveAsset(current.value, revisedModule)
  markSlideComponentDirty(current.value, revisedId)
  return revisedModule
}
const submitRevision = async ({ operation = 'modify_page' } = {}) => {
  const instruction = prompt.value.trim(); if (!instruction) return
  if (revisionSubmitting.value) return
  const conversationTranscript = workspaceConversationTranscript()
  const revisionInstruction = buildRevisionInstruction(instruction)
  // 修改指令本身不是下一轮讨论的上下文；成功后会连同此前确认方案一起关闭。
  messages.push({ role: 'user', text: instruction, includeInContext: false, kind: 'revision-request' }); prompt.value = ''
  revisionSubmitting.value = true
  revisionStage.value = '正在理解修改指令…'
  try {
    if (isAddPageInstruction(instruction) && !isDeckRevisionInstruction(instruction)) {
      revisionStage.value = '正在新增页面…'
      const result = await executeAddPageInstruction(instruction)
      closeDiscussionContext()
      messages.push({
        role: 'assistant',
        text: result.generated
          ? `已新增“${result.title}”，并保持当前课件模板风格。`
          : `已新增“${result.title}”，请在画布中继续编辑页面内容。`,
        includeInContext: false,
        kind: 'revision-result',
      })
      WorkspaceMessage.success('页面已添加')
      return
    }
    if (isDeckRevisionInstruction(instruction)) {
      await applyDeckRevision(revisionInstruction, conversationTranscript)
      messages.push({
        role: 'assistant',
        text: 'AI 已生成整套课件修改预览，请检查修改清单和前后页面后选择“接受并应用”或“拒绝修改”。',
        includeInContext: false,
        kind: 'revision-preview',
      })
      return
    }
    let applied = false
    if (workspaceUsesHtmlEditor.value) {
      const selectedElement = htmlSelectedElement.value
      if (selectedElement?.type === 'h5') {
        revisionStage.value = '正在重新生成并替换选中的 H5 组件…'
        const revisedModule = await reviseSelectedH5WithAi(selectedElement, revisionInstruction)
        if (projectId.value) await persistCurrentSlide({ throwOnError: true })
        closeDiscussionContext()
        messages.push({
          role: 'assistant',
          text: `已真实替换选中的 H5 组件（${revisedModule.title || selectedElement.name || '课堂互动'}）。本次修改要求：${instruction}`,
          includeInContext: false,
          kind: 'revision-result',
        })
        WorkspaceMessage.success('H5 组件已重新生成并替换')
        return
      }
      revisionStage.value = selectedElement
        ? '正在分析选中元素并生成页面修改…'
        : '正在分析当前页并生成页面修改…'
      const response = unwrapResponse(await modifyPresentationSlide({
        ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
        slide_no: selectedSlide.value + 1,
        current_html: slideHtmlSource(current.value),
        instruction: revisionInstruction,
        outline_context: {
          deck_title: String(project.value?.project_name || route.query.templateTitle || current.value.title || 'A12 教学课件'),
          current_slide_title: String(current.value.title || ''),
          current_slide_no: selectedSlide.value + 1,
            selected_element: selectedElement ? {
              id: selectedElement.id,
              name: selectedElement.name,
              type: selectedElement.type,
              content: selectedElement.content,
              module_type: selectedElement.type === 'h5' ? (selectedElement.module_type || selectedElement.moduleType || 'unknown') : undefined,
              topic: selectedElement.type === 'h5' ? selectedElement.topic : undefined,
              // H5 的真实内容位于受控 iframe 的 srcdoc 中；将其作为明确上下文提供给
              // 修改接口，避免模型只改外层占位框而没有改到互动组件本身。
              html: selectedElement.type === 'h5' ? String(selectedElement.html || '').slice(0, 18000) : undefined,
            } : null,
          conversation_context: conversationTranscript || null,
          workspace_context: workspaceContextPayload(),
        },
        theme: String(routeQueryValue(route.query.pptTheme) || presentationMetadata.value?.theme || current.value.theme || '').trim() || undefined,
        keep_style: true,
      }))
      if (showClarificationForResponse(response, projectId.value ? 'project' : 'session')) return
      revisionStage.value = '正在应用 AI 返回的页面…'
      const pagePayload = getGeneratedPagePayload(response)
      const nextHtml = pagePayload?.content?.html ?? pagePayload?.candidate?.html ?? pagePayload?.content?.page_html ?? pagePayload?.candidate?.page_html
      if (typeof nextHtml === 'string' && nextHtml.trim()) await validateGeneratedSlides([{ html: nextHtml.trim() }], '页面修改结果')
      applied = applyGeneratedPage(response)
      if (!applied) throw new Error('AI 修改接口未返回有效的 HTML 页面')
      if (projectId.value) await persistCurrentSlide({ throwOnError: true })
      closeDiscussionContext()
      messages.push({
        role: 'assistant',
        // change_summary 可能回显供接口理解的完整上下文，不应暴露给教师。
        text: '已完成当前页面修改。',
        includeInContext: false,
        kind: 'revision-result',
      })
      WorkspaceMessage.success('页面内容已更新')
      return
    }
    if (projectId.value) {
      revisionStage.value = '正在提交项目页面修改…'
      const selectedTarget = selectedElement.value || htmlSelectedElement.value
      const targetType = operation === 'modify_component' && selectedTarget?.id ? 'component' : 'page'
      const targetId = targetType === 'component'
        ? String(selectedTarget.id)
        : String(current.value.pageId || current.value.componentId || '')
      const response = unwrapResponse(await reviseProjectWithAi(projectId.value, {
        target_type: targetType,
        target_id: targetId,
        instruction: revisionInstruction,
        context: JSON.stringify({
          page: current.value,
          selected_element: selectedTarget ? {
            id: selectedTarget.id,
            name: selectedTarget.name,
            type: selectedTarget.type,
            content: selectedTarget.content,
          } : null,
          workspace_operation: operation,
          conversation_context: conversationTranscript || null,
          workspace_context: workspaceContextPayload(),
        }),
      }))
      revisionStage.value = '正在应用 AI 返回的页面…'
      applied = applyGeneratedPage(response)
      if (showClarificationForResponse(response, 'project')) return
      if (applied) await persistCurrentSlide({ throwOnError: true })
    }
    else if (sessionId.value) {
      revisionStage.value = '正在处理页面修改请求…'
      const response = unwrapResponse(await sendAiSessionMessage(sessionId.value, {
        message: revisionInstruction,
        messages: JSON.stringify([{ role: 'user', content: revisionInstruction }]),
        known_context: JSON.stringify({ workspace_context: workspaceContextPayload() }),
      }))
      if (showClarificationForResponse(response, 'session')) return
    }
    if (applied) closeDiscussionContext()
    messages.push({
      role: 'assistant',
      text: applied ? '已根据修改要求更新当前页面，页面元素仍可继续选中和编辑。' : '已收到修改要求，正在结合当前页面内容进行调整。',
      includeInContext: false,
      kind: 'revision-result',
    }); WorkspaceMessage.success(applied ? '页面内容已更新' : '修改要求已提交')
  } catch (error) {
    messages.push({ role: 'assistant', text: '修改请求暂未提交成功，请稍后重试。', includeInContext: false, kind: 'revision-error' })
    WorkspaceMessage.error(error?.message || '修改请求失败')
  } finally {
    revisionSubmitting.value = false
    revisionStage.value = ''
  }
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
        known_context: JSON.stringify({ ...knownContext, workspace_context: workspaceContextPayload() }),
      }))
    } else {
      response = unwrapResponse(await reviseProjectWithAi(projectId.value, {
        target_type: 'page',
        target_id: String(current.value.pageId || current.value.componentId || ''),
        instruction: selection.answer,
        context: JSON.stringify({ page: current.value, clarification: knownContext, workspace_context: workspaceContextPayload() }),
      }))
      applyGeneratedPage(response)
      await persistCurrentSlide({ throwOnError: true })
    }
    if (showClarificationForResponse(response, clarificationOrigin.value)) return
    clarificationDialogVisible.value = false
    clarificationQuestion.value = null
    messages.push({ role: 'assistant', text: sessionId.value ? '已收到补充信息，我会沿着这个方向继续生成教学大纲。' : '已收到补充信息，我会沿着这个方向继续调整当前页面。' })
    WorkspaceMessage.success(sessionId.value ? '已收到补充信息，大纲正在更新' : '已收到补充信息')
  } catch (error) {
    messages.push({ role: 'assistant', text: '补充信息暂未提交成功，请稍后重试。' })
    WorkspaceMessage.error(error?.message || '补充信息提交失败')
  } finally { clarificationSubmitting.value = false }
}
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
}
const handleWorkspaceKeydown = (event) => {
  if (presentationMode.value) return
  const modifier = event.ctrlKey || event.metaKey
  if (modifier && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void saveWorkspaceNow()
    return
  }
  const tagName = event.target?.tagName?.toLowerCase()
  const isEditingField = ['input', 'textarea', 'select'].includes(tagName) || event.target?.isContentEditable
  if (event.key === 'Escape') {
    cancelCanvasPlacement()
    return clearElementSelection()
  }
  if (isEditingField) return
  if (modifier && event.key.toLowerCase() === 'v') {
    if (pasteElementFromClipboard()) event.preventDefault()
    return
  }
  const selectedId = workspaceSelectedElementId.value
  if (!selectedId) return
  if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    removeElement(selectedId)
    return
  }
  if (modifier && event.key.toLowerCase() === 'c') {
    event.preventDefault()
    copyElementToClipboard(selectedId)
    return
  }
  if (modifier && event.key.toLowerCase() === 'd') {
    event.preventDefault()
    copyElement(selectedId)
  }
}
const restoreLocalWorkspaceDraft = () => {
  if (projectId.value || sessionId.value || route.query.testCase) return false
  const cached = readPresentationDraft(currentDraftStorageId.value)
  if (!cached?.slides?.length) return false
  const restoredSlides = cached.slides.map((slide, index) => ({
    ...defaultSlide(index + 1),
    ...(slide && typeof slide === 'object' ? slide : {}),
    elements: normalizeElements(slide?.elements),
  }))
  slides.splice(0, slides.length, ...restoredSlides)
  presentationId.value = String(cached.presentation_id || '')
  presentationMetadata.value = cached.metadata && typeof cached.metadata === 'object' ? cached.metadata : null
  lessonPlanDraft.value = cached.lesson_plan && typeof cached.lesson_plan === 'object' ? cached.lesson_plan : null
  workspaceMode.value = normalizeWorkspaceMode(cached.workspace_mode || workspaceMode.value)
  selectedSlide.value = 0
  autosaveState.value = '本地草稿 · 尚未保存为项目'
  messages.push({ role: 'assistant', text: `已恢复本地草稿，共 ${restoredSlides.length} 页。可继续编辑，或点击“保存为项目”同步到云端。`, includeInContext: false, kind: 'local-draft-restored' })
  return true
}
onMounted(async () => {
  if (!projectId.value && !sessionId.value && !route.query.localDraftId) {
    await router.replace({ query: { ...route.query, localDraftId: localDraftId.value, workspaceMode: workspaceMode.value } })
  }
  loadTestCase()
  restoreLocalWorkspaceDraft()
  initializeSessionFlow()
  void loadWorkspaceResources()
  await bootstrapTestCaseProject()
  await loadProject()
  const interruptedRunNeedsAttention = restoreTrackedRun()
  if (!interruptedRunNeedsAttention && !projectId.value && (sessionId.value || presentationFixtureMode.value)) await startRun()
  await nextTick()
  centerCanvasView()
  if (typeof ResizeObserver !== 'undefined' && canvasAreaRef.value) {
    canvasViewportObserver = new ResizeObserver(() => centerCanvasView())
    canvasViewportObserver.observe(canvasAreaRef.value)
  }
  mobileViewportMq = window.matchMedia('(max-width: 767.98px)')
  mobileViewportMq.addEventListener('change', handleMobileViewportChange)
  window.addEventListener('keydown', handleWorkspaceKeydown)
  window.addEventListener('keydown', handlePresentationKeydown)
  document.addEventListener('fullscreenchange', handlePresentationFullscreenChange)
})
onBeforeUnmount(() => { mobileViewportMq?.removeEventListener('change', handleMobileViewportChange); mobileViewportMq = null; if (canvasCenterFrame != null) cancelAnimationFrame(canvasCenterFrame); canvasViewportObserver?.disconnect(); canvasViewportObserver = null; interactivePreviewResizeObserver?.disconnect(); interactivePreviewResizeObserver = null; htmlFrameObservers.forEach(({ observer, cleanup }) => { observer?.disconnect(); cleanup?.() }); htmlFrameObservers.clear(); clearPreviewFrameObservers(); stopCanvasPan(); stopElementDrag(); cancelCanvasPlacement(); workspaceMessageInstance?.close(); window.removeEventListener('keydown', handleWorkspaceKeydown); window.removeEventListener('keydown', handlePresentationKeydown); document.removeEventListener('fullscreenchange', handlePresentationFullscreenChange); if (document.fullscreenElement && document.exitFullscreen) void document.exitFullscreen() })
const currentPagePayload = (slide = current.value, index = selectedSlide.value, overrides = {}) => pagePayloadForSlide(slide, index, {
  // 普通内容保存不修改页面顺序，避免旧顺序与当前数组索引不一致时触发唯一索引冲突。
  includePageOrder: false,
  autosave: true,
  dirty: false,
  ...overrides,
})
const persistCurrentSlide = async ({ throwOnError = false } = {}) => {
  if (pageSavePromise) {
    const result = await pageSavePromise
    if (result === true && localChangeVersion > savedChangeVersion && projectId.value && !hydratingProject.value) {
      return persistCurrentSlide({ throwOnError })
    }
    if (throwOnError && result !== true) throw new Error('当前页面保存失败，未继续后续操作')
    return result
  }
  if (!projectId.value || hydratingProject.value) return true
  const slideIndex = selectedSlide.value
  const slide = slides[slideIndex]
  if (!slide) return true
  const saveVersion = localChangeVersion
  const structureVersionAtStart = localStructureVersion
  autosaveQueued = false

  let task
  task = (async () => {
    savingPage.value = true
    autosaveState.value = '保存中…'
    try {
      await validateSlideComponents(slide)
      const payload = currentPagePayload(slide, slideIndex)
      // 页面记录承载完整的 page_content / components 快照；不再把 pageId 伪装为
      // “componentId”调用旧接口，避免 API 语义和持久化对象不一致。
      const response = slide.pageId
        ? await saveProjectPage(projectId.value, slide.pageId, {
          ...payload,
          expected_page_version: Number(slide.pageVersion || 1),
        })
        : await createProjectPage(projectId.value, payload)
      const saved = unwrapResponse(response)
      const isLatest = localChangeVersion === saveVersion && localStructureVersion === structureVersionAtStart
      if (slides[slideIndex] === slide) {
        slide.pageId = saved?.id || saved?.page_id || saved?.component_id || slide.pageId
        slide.componentId = saved?.component_id || slide.pageId
        const pageOrder = Number(saved?.page_order ?? saved?.pageOrder)
        if (Number.isFinite(pageOrder)) {
          slide.pageOrder = pageOrder
          slide.page_order = pageOrder
        }
        slide.pageVersion = Number(saved?.page_version || slide.pageVersion || 1)
        slide.clientVersion = saved?.client_version || slide.clientVersion || workspaceClientVersion
        slide.autosave = Boolean(saved?.autosave ?? true)
        slide.dirty = isLatest ? Boolean(saved?.dirty) : true
        slide.lastSavedAt = saved?.last_saved_at || slide.lastSavedAt || null
        if (isLatest) pendingComponentSync.delete(slide)
      }
      if (isLatest) {
        savedChangeVersion = Math.max(savedChangeVersion, saveVersion)
        if (structureVersionAtStart <= savedStructureVersion) autosaveState.value = '已保存'
        else { autosaveState.value = '待保存'; autosaveQueued = true }
      } else {
        autosaveState.value = '待保存'
        autosaveQueued = true
      }
      return true
    } catch (error) {
      autosaveState.value = '保存失败'
      const message = error?.response?.data?.message || error?.message || '页面保存失败'
      WorkspaceMessage.error(message.includes('Version conflict') || message.includes('版本冲突') ? '页面版本已变化，请刷新页面后重试' : message)
      return false
    } finally {
      // 保存接口返回后会同步 pageId、版本号等字段；先让深度监听完成本轮刷新，避免把这些内部更新误判为新的编辑。
      await nextTick()
      savingPage.value = false
      if (pageSavePromise === task) pageSavePromise = null
      if (localChangeVersion > saveVersion || localStructureVersion > structureVersionAtStart || autosaveQueued) scheduleWorkspaceAutosave()
    }
  })()
  pageSavePromise = task
  const result = await task
  if (throwOnError && result !== true) throw new Error('当前页面保存失败，未继续后续操作')
  return result
}
const clearSlideDragState = () => {
  draggingSlideIndex.value = null
  slideDropIndex.value = null
}
const slideDropIndexFromEvent = (index, event) => {
  const rect = event.currentTarget?.getBoundingClientRect?.()
  if (!rect) return index
  return index + (event.clientY >= rect.top + rect.height / 2 ? 1 : 0)
}
const startSlideDrag = (index, event) => {
  if (slides.length < 2) return
  draggingSlideIndex.value = index
  slideDropIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
  }
}
const handleSlideDragOver = (index, event) => {
  if (draggingSlideIndex.value === null) return
  event.preventDefault()
  slideDropIndex.value = slideDropIndexFromEvent(index, event)
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}
const persistSlideOrder = async ({ deletedPageIds = [], throwOnError = false } = {}) => {
  if (orderSavePromise) {
    const result = await orderSavePromise
    if (result === true && projectId.value && !hydratingProject.value
      && (localChangeVersion > savedChangeVersion || localStructureVersion > savedStructureVersion)) {
      return persistSlideOrder({ deletedPageIds, throwOnError })
    }
    if (throwOnError && result !== true) throw new Error('页面顺序保存失败，未继续后续操作')
    return result
  }
  if (!projectId.value || hydratingProject.value) return true

  let task
  task = (async () => {
    // 页面内容先落库，再批量同步顺序，避免新页面或刚编辑的页面被顺序请求覆盖。
    if (pageSavePromise) {
      const pageResult = await pageSavePromise
      if (pageResult !== true) {
        if (throwOnError) throw new Error('当前页面保存失败，未继续保存页面顺序')
        return false
      }
    }
    if (!projectId.value || hydratingProject.value) return true
    clearTimeout(autosaveTimer)
    const saveVersion = localChangeVersion
    const structureVersionAtStart = localStructureVersion
    autosaveQueued = false
    savingPage.value = true
    autosaveState.value = '保存顺序中…'
    try {
      for (const slide of slides) await validateSlideComponents(slide)
      const savePageBatch = async (pages) => savedPageList(await batchSaveProjectPages(projectId.value, {
        client_version: workspaceClientVersion,
        autosave: true,
        pages,
      }))
      // 后端按数组顺序逐条更新唯一索引 (project_id, page_order)。
      // 页面交换时直接从旧序号改到新序号会撞上仍未更新的页面，因此先全部
      // 放到临时负序号，再提交最终的 1..N 顺序。
      const needsStaging = slides.some((slide, index) => {
        if (!slide.pageId) return true
        const pageOrder = Number(slide.pageOrder ?? slide.page_order)
        return !Number.isFinite(pageOrder) || pageOrder !== index + 1
      })
      if (needsStaging && slides.length) {
        const temporaryBase = -1000000000 + (Date.now() % 100000)
        const stagedPages = slides.map((slide, index) => projectPagePayload(slide, index, temporaryBase - index))
        const stagedResult = await savePageBatch(stagedPages)
        if (stagedResult.length < slides.length) throw new Error('页面顺序保存接口未返回完整页面结果')
        // 临时序号只用于释放唯一索引，不写回画布的真实顺序。
        applySavedPageMetadata(stagedResult, slides, { updateOrder: false })
      }
      const savedPages = await savePageBatch(slides.map((slide, index) => projectPagePayload(slide, index)))
      if (savedPages.length < slides.length) throw new Error('页面顺序保存接口未返回完整页面结果')
      const isLatest = localChangeVersion === saveVersion && localStructureVersion === structureVersionAtStart
      applySavedPageMetadata(savedPages, slides, { clearPending: isLatest })
      const currentPageIds = new Set(slides.map((slide) => String(slide.pageId || slide.page_id || slide.componentId || '')).filter(Boolean))
      const stalePageIds = [...new Set(deletedPageIds.map((id) => String(id || '')).filter((id) => id && !currentPageIds.has(id)))]
      if (stalePageIds.length) await Promise.all(stalePageIds.map((pageId) => deleteProjectPage(projectId.value, pageId)))
      if (isLatest) {
        savedChangeVersion = Math.max(savedChangeVersion, saveVersion)
        savedStructureVersion = Math.max(savedStructureVersion, structureVersionAtStart)
        autosaveState.value = '已保存'
      } else {
        autosaveState.value = '待保存'
        autosaveQueued = true
      }
      return true
    } catch (error) {
      autosaveState.value = '保存失败'
      const message = error?.response?.data?.message || error?.message || '页面顺序保存失败'
      WorkspaceMessage.error(message.includes('Version conflict') || message.includes('版本冲突') ? '页面版本已变化，请刷新页面后重试' : message)
      return false
    } finally {
      // 批量保存同样会回写每页的服务端字段，等监听队列清空后再解除保存保护。
      await nextTick()
      savingPage.value = false
      if (orderSavePromise === task) orderSavePromise = null
      if (localChangeVersion > saveVersion || localStructureVersion > structureVersionAtStart || autosaveQueued) scheduleWorkspaceAutosave()
    }
  })()
  orderSavePromise = task
  const result = await task
  if (throwOnError && result !== true) throw new Error('页面顺序保存失败，未继续后续操作')
  return result
}
const syncPageStructure = async ({ deletedPageIds = [], successMessage = '', throwOnError = false } = {}) => {
  clearTimeout(autosaveTimer)
  const pageSaved = await persistCurrentSlide({ throwOnError })
  if (pageSaved === false) return false
  const orderSaved = await persistSlideOrder({ deletedPageIds, throwOnError })
  if (orderSaved === false) return false
  if (successMessage) WorkspaceMessage.success(successMessage)
  return true
}
const openOnlinePreview = async () => {
  if (onlinePreviewLoading.value) return
  onlinePreviewLoading.value = true
  try {
    clearTimeout(autosaveTimer)
    if (projectId.value) {
      await syncPageStructure({ throwOnError: true })
    } else if (sessionId.value) {
      saveCurrentPresentationDraft()
    }
    openPreview()
    await nextTick()
    scrollPreviewTo(selectedSlide.value)
  } catch (error) {
    WorkspaceMessage.error(error?.message || '在线预览准备失败，请稍后重试')
  } finally {
    onlinePreviewLoading.value = false
  }
}
const openWorkspacePreview = () => {
  if (workspaceMode.value === 'document') {
    openLessonPlanPreview()
    return
  }
  return openOnlinePreview()
}
const reorderSlides = (sourceIndex, dropIndex) => {
  if (!Number.isInteger(sourceIndex) || !Number.isInteger(dropIndex)) return
  if (sourceIndex < 0 || sourceIndex >= slides.length) return
  const targetIndex = dropIndex > sourceIndex ? dropIndex - 1 : dropIndex
  if (targetIndex === sourceIndex || targetIndex < 0 || targetIndex >= slides.length) return

  const selectedSlideObject = slides[selectedSlide.value]
  const [movedSlide] = slides.splice(sourceIndex, 1)
  slides.splice(targetIndex, 0, movedSlide)
  slides.forEach((slide, index) => {
    slide.slideNo = index + 1
    slide.slide_no = index + 1
    if (slide.html) slide.eyebrow = `${String(index + 1).padStart(2, '0')} / HTML PPT`
  })
  const nextSelectedIndex = slides.indexOf(selectedSlideObject)
  if (nextSelectedIndex >= 0) selectedSlide.value = nextSelectedIndex
  markSlideComponentDirty(slides[selectedSlide.value], 'page:order', { structure: true })
  if (sessionId.value && !projectId.value) saveCurrentPresentationDraft()
  if (projectId.value) void persistSlideOrder()
}
const dropSlide = (index, event) => {
  if (draggingSlideIndex.value === null) return
  event.preventDefault()
  const sourceIndex = draggingSlideIndex.value
  const dropIndex = slideDropIndex.value ?? slideDropIndexFromEvent(index, event)
  clearSlideDragState()
  reorderSlides(sourceIndex, dropIndex)
}
const loadVersions = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('演示项目不支持版本管理')
  if (versionLoading.value) return
  versionLoading.value = true; versionDialogVisible.value = true
  versionError.value = ''
  try {
    const result = unwrapResponse(await listProjectVersions(projectId.value, { page: versionPage.value, size: 10 }))
    versions.value = Array.isArray(result) ? result : result?.records || result?.list || result?.items || []
    versionTotal.value = Number(result?.total ?? versions.value.length)
  } catch (error) { versionError.value = workspaceRequestErrorMessage(error, '版本历史加载失败'); versions.value = [] }
  finally { versionLoading.value = false }
}
const persistVersionContent = async () => {
  await persistSlideOrder({ throwOnError: true })
  if (typeof lessonPlanAutosavePromise !== 'undefined' && lessonPlanAutosavePromise) await lessonPlanAutosavePromise.catch(() => {})
  const plan = lessonPlanEditorRef.value?.getLessonPlan?.()
  if (plan) await saveLessonPlanDraft(plan, { throwOnError: true })
}
const createVersion = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('当前是临时课件，生成项目后才能保存版本')
  if (versionActionLoading.value) return
  versionActionLoading.value = true
  try {
    clearTimeout(autosaveTimer)
    // 严格按“当前页 → 页面顺序 → 版本快照”执行，保证刚输入的内容不会落在版本之外。
    if (orderSavePromise) {
      const orderResult = await orderSavePromise
      if (orderResult !== true) throw new Error('页面顺序保存失败，未创建版本')
    }
    await persistCurrentSlide({ throwOnError: true })
    await persistVersionContent()
    unwrapResponse(await saveProjectVersion(projectId.value, { description: versionDescription.value.trim() || (workspaceMode.value === 'document' ? '保存教学案调整' : `保存第 ${selectedSlide.value + 1} 页调整`) }))
    versionDescription.value = ''
    versionPage.value = 1
    versionDiff.value = null
    autosaveState.value = '已创建版本'
    await loadVersions()
    WorkspaceMessage.success('项目版本已保存')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '版本保存失败')
  } finally { versionActionLoading.value = false }
}
const showVersionDiff = async (version) => {
  if (versionDiffLoading.value) return
  versionDiff.value = null
  versionDiffLoading.value = true
  try {
    versionDiff.value = unwrapResponse(await getProjectVersionDiff(projectId.value, version.id || version.version_id, compareVersionId.value))
  } catch (error) { WorkspaceMessage.error(error?.message || '差异加载失败') }
  finally { versionDiffLoading.value = false }
}
const restoreVersion = async (version) => {
  if (versionActionLoading.value) return
  try { await ElMessageBox.confirm('将当前内容保存为备份版本后恢复此版本，恢复后可在版本历史中找回当前内容。', '恢复历史版本', { confirmButtonText: '备份并恢复', cancelButtonText: '取消', type: 'warning' }) }
  catch { return }
  versionActionLoading.value = true
  try {
    clearTimeout(autosaveTimer)
    await persistVersionContent()
    unwrapResponse(await saveProjectVersion(projectId.value, { description: '恢复历史版本前的自动备份' }))
    const restored = unwrapResponse(await restoreProjectVersion(projectId.value, version.id || version.version_id))
    project.value = { ...(project.value || {}), ...(restored || {}) }
    versionDiff.value = null
    // 恢复接口会重建页面记录并生成新的页面 ID，不能继续沿用内存中的旧画布数据。
    await loadProject()
    versionPage.value = 1
    await loadVersions()
    WorkspaceMessage.success('已恢复历史版本，画布已刷新')
  } catch (error) { WorkspaceMessage.error(error?.message || '版本恢复失败') }
  finally { versionActionLoading.value = false }
}
const parsePermissionIds = (value) => {
  const parsed = typeof value === 'string' ? parseJson(value, []) : value
  const values = Array.isArray(parsed) ? parsed : []
  return [...new Set(values.map((item) => Number(item)).filter((item) => Number.isInteger(item) && item > 0))]
}
const projectPermissionIds = computed(() => parsePermissionIds(project.value?.permissions))
const isPermissionGranted = (id) => projectPermissionIds.value.includes(Number(id))
const openPermissionDialog = () => {
  if (!projectId.value) return WorkspaceMessage.warning('当前是临时课件，保存为项目后才能管理协作者')
  permissionSearchType.value = 'username'
  permissionSearchQuery.value = ''
  permissionSearchResult.value = null
  permissionDialogVisible.value = true
}
const searchPermissionUser = async () => {
  const query = permissionSearchQuery.value.trim()
  if (!query) return WorkspaceMessage.warning(`请输入${permissionSearchType.value === 'email' ? '邮箱' : '用户名'}`)
  permissionSearchLoading.value = true
  permissionSearchResult.value = null
  try {
    const result = permissionSearchType.value === 'email'
      ? await findUserByEmail(query)
      : await findUserByUsername(query)
    const user = unwrapResponse(result)
    if (!user?.id) throw new Error('未找到对应教师账号')
    permissionSearchResult.value = user
  } catch (error) {
    WorkspaceMessage.error(error?.message || '教师账号查询失败')
  } finally { permissionSearchLoading.value = false }
}
const addSearchedPermission = async () => {
  const userId = Number(permissionSearchResult.value?.id)
  if (!Number.isInteger(userId) || userId <= 0) return WorkspaceMessage.warning('请先搜索有效教师账号')
  if (isPermissionGranted(userId)) return WorkspaceMessage.info('该教师已经在协作者列表中')
  permissionAddLoading.value = true
  try {
    const updated = unwrapResponse(await addProjectPermission(projectId.value, { user_id: userId }))
    project.value = { ...(project.value || {}), ...(updated || {}) }
    permissionSearchResult.value = { ...permissionSearchResult.value, added: true }
    WorkspaceMessage.success('协作者已添加')
  } catch (error) { WorkspaceMessage.error(error?.message || '授权失败') }
  finally { permissionAddLoading.value = false }
}
const removePermission = async (id) => {
  const userId = Number(id)
  if (!Number.isInteger(userId) || userId <= 0) return
  try { await ElMessageBox.confirm(`确定移除用户 #${userId} 的项目权限吗？`, '移除协作者', { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' }) }
  catch { return }
  permissionRemoveLoading.value = String(userId)
  try {
    const nextPermissions = projectPermissionIds.value.filter((item) => item !== userId)
    const updated = await patchProjectWithFreshVersion({ permissions: JSON.stringify(nextPermissions) })
    project.value = { ...(project.value || {}), ...(updated || {}), permissions: updated?.permissions || JSON.stringify(nextPermissions) }
    if (Number(permissionSearchResult.value?.id) === userId) permissionSearchResult.value = { ...permissionSearchResult.value, added: false }
    WorkspaceMessage.success('协作者权限已移除')
  } catch (error) { WorkspaceMessage.error(error?.message || '移除协作者失败') }
  finally { permissionRemoveLoading.value = '' }
}
const resetCommunityPublishForm = () => {
  Object.assign(communityPublishForm, {
    content_type: 'lesson_case',
    title: String(project.value?.project_name || routeQueryValue(route.query.templateTitle) || current.value?.title || '未命名 HTML PPT'),
    description: `由 A12 创作工作台生成的 HTML PPT，共 ${slides.length} 页，可继续复用和编辑。`,
    subject: String(routeQueryValue(route.query.subject) || project.value?.subject || presentationMetadata.value?.subject || ''),
    grade: String(routeQueryValue(route.query.grade) || project.value?.grade || presentationMetadata.value?.grade || ''),
    lesson_type: '多媒体课件',
    license: 'CC BY-NC 4.0',
    source_declaration: '本人原创或已获得授权',
    notes: '',
  })
}
const openCommunityPublish = () => {
  if (!slides.length) return WorkspaceMessage.warning('当前没有可发布的课件页面')
  resetCommunityPublishForm()
  communityPublishVisible.value = true
}
const buildCommunityContentData = () => ({
  source: 'a12-html-ppt-workspace',
  project_id: projectId.value ? Number(projectId.value) : null,
  presentation_id: presentationId.value || null,
  workspace_mode: workspaceMode.value,
  slides: slides.map((slide, index) => ({
    slide_no: Number(slide?.slideNo || slide?.slide_no || index + 1),
    title: slide?.title || `第 ${index + 1} 页`,
    html: slide?.html || '',
    notes: slide?.notes || slide?.speaker_notes || slide?.description || '',
    layout: slide?.layout || '',
    theme: slide?.theme || '',
    elements: Array.isArray(slide?.elements) ? slide.elements : [],
    metadata: slide?.metadata || {},
  })),
  lesson_plan: lessonPlanDraft.value || presentationMetadata.value?.lesson_plan || null,
  workspace_context: workspaceContextPayload(),
})
const publishCommunity = async (submit = false) => {
  const title = communityPublishForm.title.trim()
  if (!title) return WorkspaceMessage.warning('请输入社区内容标题')
  if (!communityPublishForm.license) return WorkspaceMessage.warning('请选择授权协议')
  if (submit && !communityPublishForm.source_declaration.trim()) return WorkspaceMessage.warning('请填写来源声明')
  communityPublishLoading.value = true
  try {
    const created = unwrapResponse(await createCommunitySubmission({
      content_type: communityPublishForm.content_type,
      title,
      description: communityPublishForm.description.trim(),
      subject: communityPublishForm.subject.trim(),
      grade: communityPublishForm.grade.trim(),
      lesson_type: communityPublishForm.lesson_type.trim(),
      content_data: JSON.stringify(buildCommunityContentData()),
      input_variables: JSON.stringify({ project_id: projectId.value ? Number(projectId.value) : null, resource_ids: workspaceContextPayload().resource_ids }),
      example_effect: '可复用的 AI HTML PPT 课件草稿，保留页面结构、互动组件和备注信息。',
      license: communityPublishForm.license,
    }))
    const submissionId = created?.id || created?.content_id
    if (!submissionId) throw new Error('投稿接口未返回投稿 ID')
    await saveCommunitySubmissionVersion(submissionId, { description: '从创作工作台发布前保存版本' })
    if (submit) {
      await submitCommunitySubmission(submissionId, {
        source_declaration: communityPublishForm.source_declaration.trim(),
        notes: communityPublishForm.notes.trim(),
      })
    }
    communityPublishVisible.value = false
    WorkspaceMessage.success(submit ? '社区投稿已提交审核' : '社区投稿草稿已保存')
  } catch (error) { WorkspaceMessage.error(error?.message || '社区投稿失败') }
  finally { communityPublishLoading.value = false }
}
const workspaceOutlinePayload = () => {
  const existing = lessonPlanOutline.value
  if (Array.isArray(existing?.slides) && existing.slides.length) return { ...existing, title: existing.title || lessonPlanTitle.value }
  return {
    title: lessonPlanTitle.value,
    slides: slides.map((slide, index) => ({
      slide_no: index + 1,
      title: slide?.title || `第 ${index + 1} 页`,
      content_points: [slide?.description || slide?.notes || '围绕本页教学目标组织课堂内容'].filter(Boolean),
      teaching_intent: slide?.notes || slide?.description || '',
      visual_suggestion: slide?.layout || '保持当前页面结构并优化视觉风格',
    })),
  }
}
const projectRecordsFromResponse = (response) => {
  const data = unwrapResponse(response)
  if (Array.isArray(data)) return data
  return data?.records || data?.items || data?.list || data?.projects || []
}
const loadWorkspaceProjects = async () => {
  const requestId = ++projectListRequest
  projectListLoading.value = true
  projectListError.value = ''
  try {
    const response = await listProjects({ ...projectFilters, keyword: projectFilters.keyword.trim() || undefined, project_type: projectFilters.project_type || undefined, status: projectFilters.status || undefined })
    if (requestId !== projectListRequest) return
    const data = unwrapResponse(response)
    workspaceProjects.value = projectRecordsFromResponse(response)
    projectTotal.value = Number(data?.total ?? workspaceProjects.value.length)
    if (!workspaceProjects.value.length && projectFilters.page > 1) {
      projectFilters.page = Math.max(1, Math.ceil(projectTotal.value / projectFilters.size))
      return await loadWorkspaceProjects()
    }
  } catch (error) {
    if (requestId !== projectListRequest) return
    projectListError.value = workspaceRequestErrorMessage(error, '项目列表加载失败')
    workspaceProjects.value = []
    projectTotal.value = 0
  } finally { if (requestId === projectListRequest) projectListLoading.value = false }
}
const searchWorkspaceProjects = () => { projectFilters.page = 1; return loadWorkspaceProjects() }
const openProjectManager = async () => {
  projectNameDraft.value = String(project.value?.project_name || current.value?.title || '')
  projectManagerVisible.value = true
  await loadWorkspaceProjects()
}
const renameWorkspaceProject = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('当前是临时课件，生成项目后才能重命名')
  const name = projectNameDraft.value.trim()
  if (!name) return WorkspaceMessage.warning('请输入项目名称')
  projectActionLoading.value = true
  try {
    const updated = await patchProjectWithFreshVersion({
      project_name: name,
    })
    project.value = { ...(project.value || {}), ...(updated || {}), project_name: updated?.project_name || name }
    WorkspaceMessage.success('项目名称已保存')
    await loadWorkspaceProjects()
  } catch (error) { WorkspaceMessage.error(error?.message || '项目重命名失败') }
  finally { projectActionLoading.value = false }
}
const copyWorkspaceProject = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('当前是临时课件，生成项目后才能复制')
  projectActionLoading.value = true
  try {
    await persistSlideOrder({ throwOnError: true })
    unwrapResponse(await copyProject(projectId.value, { new_name: `${projectNameDraft.value.trim() || project.value?.project_name || '未命名课件'} 副本` }))
    WorkspaceMessage.success('项目副本已创建')
    await loadWorkspaceProjects()
  } catch (error) { WorkspaceMessage.error(error?.message || '复制项目失败') }
  finally { projectActionLoading.value = false }
}
const openWorkspaceProject = async (item) => {
  if (item?.status === 'archived') return WorkspaceMessage.warning('请先恢复归档项目再打开')
  const id = item?.id || item?.project_id
  if (!id) return
  if (String(id) === String(projectId.value)) return
  try {
    if (projectId.value) await persistSlideOrder({ throwOnError: true })
    else saveCurrentPresentationDraft()
  } catch (error) { WorkspaceMessage.error(error?.message || '当前项目保存失败，未切换项目'); return }
  projectManagerVisible.value = false
  await router.push({
    path: '/main/workspace',
    query: { projectId: String(id) },
  })
}
const archiveWorkspaceProject = async (id = projectId.value) => {
  if (!id) return
  projectActionLoading.value = true
  try {
    if (String(id) === String(projectId.value)) await persistSlideOrder({ throwOnError: true })
    unwrapResponse(await archiveProject(id))
    WorkspaceMessage.success('项目已归档')
    if (String(id) === String(projectId.value)) { projectManagerVisible.value = false; goHome(); return }
    await loadWorkspaceProjects()
  } catch (error) { WorkspaceMessage.error(error?.message || '归档项目失败') }
  finally { projectActionLoading.value = false }
}
const restoreWorkspaceProject = async (id) => {
  if (!id) return
  projectActionLoading.value = true
  try { await restoreProject(id); WorkspaceMessage.success('项目已恢复'); await loadWorkspaceProjects() }
  catch (error) { WorkspaceMessage.error(error?.message || '恢复项目失败') }
  finally { projectActionLoading.value = false }
}
const removeWorkspaceProject = async (id = projectId.value) => {
  if (!id) return
  try { await ElMessageBox.confirm('删除后可通过项目恢复接口找回。确定删除此项目吗？', '删除项目', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }) }
  catch { return }
  projectActionLoading.value = true
  try {
    await deleteProject(id)
    WorkspaceMessage.success('项目已删除')
    if (String(id) === String(projectId.value)) { projectManagerVisible.value = false; goHome(); return }
    await loadWorkspaceProjects()
  } catch (error) { WorkspaceMessage.error(error?.message || '删除项目失败') }
  finally { projectActionLoading.value = false }
}
const scheduleWorkspaceAutosave = (delay = 700, { force = false } = {}) => {
  if (!projectId.value || testCaseBootstrapping.value || hydratingProject.value) return
  clearTimeout(autosaveTimer)
  autosaveState.value = '待保存'
  autosaveTimer = setTimeout(() => {
    autosaveTimer = null
    if (!projectId.value || hydratingProject.value) return
    if (savingPage.value || pageSavePromise || orderSavePromise) {
      autosaveQueued = true
      return
    }
    const structurePending = localStructureVersion > savedStructureVersion
    const contentPending = force || localChangeVersion > savedChangeVersion
    if (structurePending) void persistSlideOrder()
    else if (contentPending) void persistCurrentSlide()
  }, delay)
}
watch(slides, () => {
  if (!projectId.value) {
    if (!testCaseBootstrapping.value && !hydratingProject.value) saveCurrentPresentationDraft()
    return
  }
  if (testCaseBootstrapping.value || hydratingProject.value || savingPage.value) return
  scheduleWorkspaceAutosave(700, { force: true })
}, { deep: true })
watch(selectedSlide, () => {
  selectedElementId.value = null
  pendingHtmlPanelSelection = null
  pendingHtmlToolbarTool = null
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
})
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const workspaceFlowQuery = (targetProjectId = projectId.value, { autoExport = false, exportType = '', precheck = false } = {}) => {
  const context = workspaceContextPayload()
  return {
  ...(route.query.testCase ? { testCase: route.query.testCase } : {}),
  ...(route.query.templateTitle ? { templateTitle: route.query.templateTitle } : {}),
  ...(route.query.pptTheme ? { pptTheme: route.query.pptTheme } : {}),
  ...(sessionId.value ? { sessionId: String(sessionId.value) } : {}),
  ...(context.resource_ids.length ? { resourceIds: JSON.stringify(context.resource_ids) } : {}),
  workspaceContext: JSON.stringify(context),
  ...(context.community?.id ? { communityId: String(context.community.id) } : {}),
  ...(context.community?.type ? { communityType: String(context.community.type) } : {}),
  workspaceMode: workspaceMode.value,
  ...(targetProjectId ? { projectId: String(targetProjectId) } : {}),
  ...(autoExport ? { autoExport: '1' } : {}),
  ...(exportType ? { exportType } : {}),
  ...(precheck ? { precheck: '1' } : {}),
  }
}
const goHome = () => router.push({ path: '/main' })
const saveWorkspaceNow = async () => {
  if (manualSaveLoading.value || hydratingProject.value) return
  manualSaveLoading.value = true
  try {
    if (typeof lessonPlanAutosavePromise !== 'undefined' && lessonPlanAutosavePromise) await lessonPlanAutosavePromise.catch(() => {})
    const plan = workspaceMode.value === 'document' ? lessonPlanEditorRef.value?.getLessonPlan?.() : null
    if (plan) await saveLessonPlanDraft(plan, { throwOnError: true })
    if (!projectId.value) { await saveWorkspaceAsProject(); return }
    clearTimeout(autosaveTimer)
    await persistSlideOrder({ throwOnError: true })
    autosaveState.value = '已保存'
    WorkspaceMessage.success('所有页面已保存')
  } catch (error) {
    autosaveState.value = '保存失败'
    WorkspaceMessage.error(error?.message || '保存失败，请重试')
  } finally { manualSaveLoading.value = false }
}
const createWorkspaceProject = async () => {
  autosaveState.value = '正在创建项目…'
  const liveLessonPlan = workspaceMode.value === 'document' ? lessonPlanEditorRef.value?.getLessonPlan?.() : null
  if (liveLessonPlan && typeof liveLessonPlan === 'object') lessonPlanDraft.value = parseJson(JSON.stringify(liveLessonPlan), {})
  const context = workspaceContextPayload()
  const created = unwrapResponse(await createProject({
    project_name: String(project.value?.project_name || route.query.templateTitle || `${current.value.title}${workspaceMode.value === 'document' ? '教学案' : '教学课件'}`),
    project_type: workspaceProjectType.value,
    status: 'editing',
    edit_history: JSON.stringify({ workspace_context: context, workspace_mode: workspaceMode.value, lesson_plan: lessonPlanDraft.value || null }),
  }))
  const createdId = created?.id || created?.project_id
  if (!createdId) throw new Error('项目创建接口未返回项目 ID')

  await batchCreateProjectPages(createdId, slides)
  project.value = { ...created, id: createdId }
  savedChangeVersion = localChangeVersion
  savedStructureVersion = localStructureVersion
  autosaveQueued = false
  autosaveState.value = '已保存 · 项目已落库'
  return String(createdId)
}
const persistGeneratedPresentationProject = async () => {
  if (projectId.value) return String(projectId.value)
  const createdId = await createWorkspaceProject()
  // 保留会话与主题参数，便于返回主对话；后续工作台加载则直接从项目页恢复。
  await router.replace({ query: { ...route.query, projectId: createdId } })
  return createdId
}
const saveWorkspaceAsProject = async () => {
  if (projectId.value) return
  try {
    const createdId = await createWorkspaceProject()
    await router.replace({
      query: {
        ...route.query,
        projectId: createdId,
        workspaceMode: workspaceMode.value,
      },
    })
    WorkspaceMessage.success('本地草稿已保存为云端项目')
  } catch (error) {
    autosaveState.value = '本地草稿 · 保存为项目失败'
    WorkspaceMessage.error(workspaceRequestErrorMessage(error, '保存为项目失败，本地草稿仍已保留'))
  }
}
const openExportCenter = async ({ autoExport = false, exportType = '', precheck = false } = {}) => {
  clearTimeout(autosaveTimer)
  try {
    if (typeof lessonPlanAutosavePromise !== 'undefined' && lessonPlanAutosavePromise) await lessonPlanAutosavePromise.catch(() => {})
    const liveLessonPlan = workspaceMode.value === 'document' ? lessonPlanEditorRef.value?.getLessonPlan?.() : null
    if (liveLessonPlan && typeof liveLessonPlan === 'object' && projectId.value) {
      await saveLessonPlanDraft(liveLessonPlan, { throwOnError: true, notify: false })
    }
    // 导出统一使用当前真实登录会话，不再在开发环境强制切换到预览账号。
    const targetProjectId = projectId.value ? String(projectId.value) : await createWorkspaceProject()
    if (projectId.value) {
      await persistCurrentSlide({ throwOnError: true })
      await persistSlideOrder({ throwOnError: true })
    }
    await router.push({ path: '/main/exports', query: workspaceFlowQuery(targetProjectId, { autoExport, exportType, precheck }) })
  } catch (error) {
    autosaveState.value = '导出准备失败'
    WorkspaceMessage.error(error?.message || '项目保存失败，无法创建导出任务')
  }
}
const safeExportFilename = (value, fallback) => String(value || fallback).replace(/[\\/:*?"<>|]/g, '').trim().slice(0, 80) || fallback
const blobFromExportResponse = (response) => response?.data instanceof Blob ? response.data : response instanceof Blob ? response : null
const exportResponseFilename = (response, fallback) => {
  const disposition = response?.headers?.['content-disposition'] || response?.headers?.get?.('content-disposition') || ''
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
  if (encoded) {
    try { return decodeURIComponent(encoded.trim()) } catch { /* 使用普通文件名 */ }
  }
  return /filename="?([^";]+)"?/i.exec(disposition)?.[1]?.trim() || fallback
}
const downloadExportBlob = (response, fallbackFilename) => {
  const blob = blobFromExportResponse(response)
  if (!blob) throw new Error('导出接口未返回文件')
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = exportResponseFilename(response, fallbackFilename)
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500)
}
const exportSlidesPayload = () => slides
  .map((slide, index) => ({
    slide_no: Number(slide?.slideNo || slide?.slide_no || index + 1),
    title: String(slide?.title || `第 ${index + 1} 页`),
    html: slideHtmlSource(slide),
    notes: String(slide?.notes || slide?.speaker_notes || ''),
    metadata: slide?.metadata || {},
    interactive_assets: slide?.interactive_assets || slide?.interactiveAssets || slide?.metadata?.interactive_assets || [],
  }))
  .filter((slide) => slide.html.trim())
const quickExportPptx = async () => {
  const payload = exportSlidesPayload()
  if (!payload.length) return WorkspaceMessage.warning('当前课件没有可导出的 HTML PPT 页面')
  quickExportLoading.value = 'pptx'
  try {
    if (projectId.value) {
      await persistCurrentSlide({ throwOnError: true })
      await persistSlideOrder({ throwOnError: true })
    }
    const title = String(project.value?.project_name || current.value?.title || 'A12 HTML PPT')
    const filename = `${safeExportFilename(title, 'A12 HTML PPT')}.pptx`
    const response = await exportPresentationPptx({ title, filename, slides: payload, fidelity: 'dom_editable' })
    downloadExportBlob(response, filename)
    WorkspaceMessage.success('可编辑 PPTX 已开始下载')
  } catch (error) { WorkspaceMessage.error(error?.message || 'PPTX 导出失败') }
  finally { quickExportLoading.value = '' }
}
const quickExportDocx = async () => {
  quickExportLoading.value = 'word'
  try {
    if (typeof lessonPlanAutosavePromise !== 'undefined' && lessonPlanAutosavePromise) await lessonPlanAutosavePromise.catch(() => {})
    const liveEditorPlan = lessonPlanEditorRef.value?.getLessonPlan?.()
    let lessonPlan = liveEditorPlan && typeof liveEditorPlan === 'object'
      ? parseJson(JSON.stringify(liveEditorPlan), {})
      : lessonPlanDraft.value && typeof lessonPlanDraft.value === 'object' && Object.keys(lessonPlanDraft.value).length
        ? parseJson(JSON.stringify(lessonPlanDraft.value), {})
        : null
    if (!lessonPlan) {
      const title = String(project.value?.project_name || current.value?.title || 'A12 教学案')
      const generated = unwrapResponse(await generateLessonPlan({
        title,
        subject: String(project.value?.subject || presentationMetadata.value?.subject || ''),
        grade: String(project.value?.grade || presentationMetadata.value?.grade || ''),
        outline: workspaceOutlinePayload(),
        slides: exportSlidesPayload().map(({ html, metadata, interactive_assets, ...slide }) => slide),
        language: 'zh-CN',
      })) || {}
      lessonPlan = generated.lesson_plan && typeof generated.lesson_plan === 'object' ? generated.lesson_plan : generated
    }
    const title = String(lessonPlan.title || project.value?.project_name || current.value?.title || 'A12 教学案')
    const filename = `${safeExportFilename(title, 'A12 教学案')}.docx`
    const response = await exportLessonPlanDocx({ title, filename, lesson_plan: lessonPlan })
    downloadExportBlob(response, filename)
    WorkspaceMessage.success('DOCX 已开始下载')
  } catch (error) { WorkspaceMessage.error(error?.message || 'DOCX 导出失败') }
  finally { quickExportLoading.value = '' }
}
const workspaceDefaultExportType = computed(() => workspaceMode.value === 'document' ? 'word' : 'pptx')
const exportProject = () => openExportCenter({ autoExport: true, exportType: workspaceDefaultExportType.value })
const handleExportQuick = (command) => {
  if (command === 'quick-pptx') return quickExportPptx()
  if (command === 'quick-word') return quickExportDocx()
  if (command === 'precheck') return openExportCenter({ precheck: true, exportType: 'pptx' })
  if (command === 'advanced') return openExportCenter({ autoExport: true, exportType: workspaceDefaultExportType.value })
  return openExportCenter()
}
const addSlide = async ({ insertAt = slides.length, title = '', slideData = null } = {}) => {
  const safeInsertAt = Math.max(0, Math.min(slides.length, Number(insertAt) || 0))
  const slide = {
    ...defaultSlide(safeInsertAt + 1),
    ...(slideData && typeof slideData === 'object' ? slideData : {}),
    title: String(title || '').trim() || `新建页面 ${safeInsertAt + 1}`,
    eyebrow: slideData?.html
      ? `${String(safeInsertAt + 1).padStart(2, '0')} / HTML PPT`
      : slideData?.eyebrow || (slideData?.pageType === 'cover' ? '课程封面' : '新建内容'),
    slideNo: safeInsertAt + 1,
    slide_no: safeInsertAt + 1,
  }
  slides.splice(safeInsertAt, 0, slide)
  slides.forEach((item, index) => {
    item.slideNo = index + 1
    item.slide_no = index + 1
    if (item.html) item.eyebrow = `${String(index + 1).padStart(2, '0')} / HTML PPT`
  })
  selectedSlide.value = safeInsertAt
  markSlideComponentDirty(slide, 'page:add', { structure: true })
  if (sessionId.value && !projectId.value) saveCurrentPresentationDraft()
  if (projectId.value) await syncPageStructure({ successMessage: '页面已保存' })
  return slide
}
const copySlide = async () => {
  if (!current.value) return
  const copiedSlide = {
    ...current.value,
    title: `${current.value.title} 副本`,
    elements: normalizeElements(current.value.elements),
    pageId: null,
    componentId: null,
    pageVersion: 1,
    clientVersion: workspaceClientVersion,
    dirty: true,
  }
  slides.splice(selectedSlide.value + 1, 0, copiedSlide)
  slides.forEach((item, index) => {
    item.slideNo = index + 1
    item.slide_no = index + 1
    if (item.html) item.eyebrow = `${String(index + 1).padStart(2, '0')} / HTML PPT`
  })
  selectedSlide.value++
  markSlideComponentDirty(copiedSlide, 'page:copy', { structure: true })
  if (sessionId.value && !projectId.value) saveCurrentPresentationDraft()
  if (projectId.value) await syncPageStructure({ successMessage: '页面副本已保存' })
}
const removeSlide = async () => {
  if (slides.length === 1) return WorkspaceMessage.warning('课件至少保留一页')
  const slide = slides[selectedSlide.value]
  if (projectId.value && slide?.pageId) {
    try { await deleteProjectPage(projectId.value, slide.pageId) }
    catch (error) { WorkspaceMessage.error(error?.message || '页面删除失败'); return }
  }
  slides.splice(selectedSlide.value, 1)
  slides.forEach((item, index) => {
    item.slideNo = index + 1
    item.slide_no = index + 1
    if (item.html) item.eyebrow = `${String(index + 1).padStart(2, '0')} / HTML PPT`
  })
  selectedSlide.value = Math.max(0, selectedSlide.value - 1)
  markSlideComponentDirty(slides[selectedSlide.value], 'page:delete', { structure: true })
  if (sessionId.value && !projectId.value) saveCurrentPresentationDraft()
  if (projectId.value) await persistSlideOrder()
}
const openProjectFromIntent = async (text) => {
  const normalizedText = String(text || '').trim()
  const requestedName = normalizedText
    .replace(/^(请|麻烦|帮我|直接)?\s*(打开|切换|进入)\s*(项目)?/i, '')
    .replace(/[“”"「」『』]/g, '')
    .trim()
  Object.assign(projectFilters, { keyword: requestedName, project_type: '', status: '', page: 1 })
  await openProjectManager()
  if (requestedName) {
    const target = workspaceProjects.value.find((item) => {
      const name = String(item?.project_name || item?.name || '').trim()
      return name && (name === requestedName || name.includes(requestedName) || requestedName.includes(name))
    })
    if (target) {
      await openWorkspaceProject(target)
      return
    }
  }
  WorkspaceMessage.info('已打开项目管理，请选择要进入的项目。')
}
const sendAssistantMessage = async () => {
  const text = prompt.value.trim()
  if (!text || isAssistantSubmitting.value) return
  intentSubmitting.value = true
  let result = { operation: 'discussion' }
  try {
    result = await resolveAssistantIntent(text)
  } finally {
    intentSubmitting.value = false
  }
  if (result.operation === 'export' || result.operation === 'open_project') {
    messages.push({ role: 'user', text, includeInContext: false, kind: 'workspace-command' })
    prompt.value = ''
    if (result.operation === 'export') {
      messages.push({ role: 'assistant', text: '正在准备导出当前课件…', includeInContext: false, kind: 'workspace-command-result' })
      return exportProject()
    }
    messages.push({ role: 'assistant', text: '正在打开项目管理…', includeInContext: false, kind: 'workspace-command-result' })
    return openProjectFromIntent(text)
  }
  if (['modify_page', 'modify_component', 'generate_content'].includes(result.operation)) return submitRevision({ operation: result.operation })
  return submitDiscussion()
}
/** 工作台语音输入：有正式 AI 会话时走 API-13A，确保语音和文字共享同一条会话上下文。 */
const handleWorkspaceVoice = async (file) => {
  if (!file || workspaceVoiceSubmitting.value || isAssistantSubmitting.value) return
  workspaceVoiceSubmitting.value = true
  try {
    if (!sessionId.value) {
      // 直接打开项目时可能没有备课会话；此时仍允许录音转写，随后由教师发送进入 API-13B。
      const formData = new FormData()
      formData.append('file', file)
      formData.append('language', 'zh')
      const response = await transcribeAudio(formData)
      const transcript = String(response?.data?.text || response?.text || '').trim()
      if (!transcript) throw new Error('未能识别到有效语音')
      prompt.value = prompt.value.trim() ? `${prompt.value.trim()} ${transcript}` : transcript
      WorkspaceMessage.success('语音已转写，请确认后发送')
      return
    }

    const context = workspaceContextPayload()
    const formData = new FormData()
    formData.append('file', file)
    formData.append('language', 'zh')
    formData.append('resource_ids', JSON.stringify(context.resource_ids || []))
    formData.append('enable_rag', String(Boolean(context.resource_ids?.length)))
    formData.append('enable_web', 'false')
    formData.append('known_context', JSON.stringify({
      page: current.value ? {
        page_id: current.value.pageId || current.value.page_id || current.value.componentId || null,
        title: current.value.title || '',
        slide_no: selectedSlide.value + 1,
      } : null,
      workspace_context: context,
    }))
    formData.append('context_summary', workspaceDiscussionContext())
    const response = await sendAiSessionAudioMessage(sessionId.value, formData)
    const conversation = unwrapResponse(response) || {}
    const storedMessages = parseJson(conversation.messages, [])
      .filter((message) => message && (message.role === 'user' || message.role === 'assistant') && String(message.content || '').trim())
    const latestUser = [...storedMessages].reverse().find((message) => message.role === 'user')
    const latestAssistant = [...storedMessages].reverse().find((message) => message.role === 'assistant')
    if (latestUser) {
      const text = String(latestUser.content).trim()
      prompt.value = text
      messages.push({ role: 'user', text, includeInContext: false, kind: 'voice-session' })
    }
    if (latestAssistant) {
      messages.push({ role: 'assistant', text: String(latestAssistant.content).trim(), includeInContext: false, kind: 'voice-session-reply' })
    }
    WorkspaceMessage.success('语音已上传，AI 已沿用当前工作台会话继续处理；确认文字后点击发送即可执行页面操作')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '语音会话提交失败，请检查麦克风权限后重试')
  } finally {
    workspaceVoiceSubmitting.value = false
    void scrollAssistantConversation()
  }
}
const handleWorkspaceVoiceError = (error) => WorkspaceMessage.error(error?.message || '录音失败，请检查浏览器麦克风权限')
/** 工作台 AI 输入快捷键：Enter 发送，Shift+Enter 换行，兼容中文输入法候选确认；触屏设备 Enter 仅换行，发送走按钮。 */
const handleAssistantKeydown = (event) => {
  if (event.isComposing || event.keyCode === 229 || event.shiftKey) return
  if (isTouchDevice) return
  event.preventDefault()
  sendAssistantMessage()
}
const selectSlide = (index) => { selectedSlide.value = index; selectedElementId.value = null; pendingHtmlPanelSelection = null; loadProjectPageDetail(index) }
</script>

<template>
  <div class="workspace">
    <CreationWorkspaceToolbar
      v-model="activeTool"
      :title="current.title"
      :autosave-state="autosaveState"
      :project-id="route.query.projectId"
      :workspace-mode="workspaceMode"
      :is-local-draft="isLocalDraft"
      :online-preview-loading="onlinePreviewLoading"
      :quick-export-loading="quickExportLoading"
      :saving="manualSaveLoading || savingPage || hydratingProject"
      @save="saveWorkspaceNow"
      @versions="loadVersions"
      @permissions="openPermissionDialog"
      @back="goHome"
      @generate-h5="openInteractiveDialog"
      @lesson-plan="openLessonPlanWorkspace"
      @return-ppt="returnToPptWorkspace"
      @project-manage="openProjectManager"
      @save-as-project="saveWorkspaceAsProject"
      @toggle-assistant="isMobile ? (activeSegment = 'chat') : (assistantDrawerVisible = !assistantDrawerVisible)"
      @toggle-properties="propertiesDrawerVisible = !propertiesDrawerVisible"
      @online-preview="openWorkspacePreview"
      @export="exportProject"
      @export-quick="handleExportQuick"
      @publish-community="openCommunityPublish"
      @present="enterPresentationMode"

      @tool-select="handleToolSelect"
    />

    <div v-if="isMobile" class="workspace-mobile-segments">
      <el-segmented
        v-model="activeSegment"
        :options="mobileSegments"
        block
        aria-label="工作台分区切换"
        @change="handleMobileSegmentChange"
      />
    </div>

    <div class="workspace-grid" :class="{ 'is-assistant-bottom': assistantDock === 'bottom', 'is-mobile-segmented': isMobile }" :data-mobile-segment="activeSegment">
      <aside v-if="!isMobile || activeSegment === 'chat'" class="assistant-panel" :class="{ 'is-mobile-open': assistantDrawerVisible }" aria-label="AI 教学助手">
        <header class="assistant-header">
          <div class="assistant-identity">
            <div class="assistant-mark" aria-hidden="true"><span>AI</span></div>
            <div class="assistant-title"><strong>教学助手</strong><span>课件协作</span></div>
          </div>
          <div class="assistant-header-actions">
            <el-button text size="small" class="assistant-context-button" @click="openWorkspaceContextManager">上下文</el-button>
            <el-tooltip :content="assistantDock === 'bottom' ? '移至左侧' : '移至底部'" placement="bottom">
              <el-button text circle size="small" class="assistant-dock-trigger assistant-icon-button" :aria-label="assistantDock === 'bottom' ? '将 AI 面板移至左侧' : '将 AI 面板移至底部'" @click="assistantDock = assistantDock === 'bottom' ? 'side' : 'bottom'"><span aria-hidden="true">{{ assistantDock === 'bottom' ? '←' : '↓' }}</span></el-button>
            </el-tooltip>
            <el-button text size="small" class="mobile-panel-close" @click="assistantDrawerVisible = false">关闭</el-button>
          </div>
        </header>
        <div class="assistant-target-bar">
          <span class="assistant-target-caption">编辑范围</span>
          <div class="assistant-target-controls">
            <el-select v-model="assistantTargetScope" size="small" aria-label="AI 当前目标">
              <el-option label="自行判断" value="auto" />
              <el-option label="整套课件" value="deck" />
              <el-option label="当前页" value="page" />
              <el-option label="当前组件" value="component" />
            </el-select>
            <el-select
              v-if="assistantTargetScope === 'component'"
              class="assistant-component-picker"
              :model-value="workspaceSelectedElementId"
              size="small"
              clearable
              filterable
              :disabled="!workspaceElements.length"
              :placeholder="workspaceElements.length ? '选择要锁定的组件' : '当前页没有可选组件'"
              aria-label="选择 AI 要修改的组件"
              @update:model-value="selectAssistantTargetComponent"
            >
              <el-option
                v-for="(element, index) in workspaceElements"
                :key="element.id"
                :value="element.id"
                :label="assistantComponentOptionLabel(element, index)"
              />
            </el-select>
          </div>
        </div>
        <section ref="assistantConversationRef" class="conversation workspace-conversation">
          <TransitionGroup name="workspace-msg-enter" tag="div" class="workspace-message-list">
            <article v-for="(message, index) in messages" :key="`${message.kind || message.role}-${index}`" :class="['workspace-chat-message', `is-${message.role}`]">
              <div v-if="message.role === 'user'" class="workspace-user-bubble">{{ message.text }}</div>
              <div v-else class="workspace-ai-bubble">
                <div v-if="message.text" class="workspace-ai-markdown">
                  <MarkdownRender mode="chat" :content="message.text" :final="!message.streaming" :fade="false" max-live-nodes="0" />
                </div>
                <div v-else-if="message.streaming" class="workspace-bubble-typing" role="status" aria-label="AI 正在回复"><i></i><i></i><i></i></div>
              </div>
            </article>
          </TransitionGroup>
          <div v-if="intentSubmitting || revisionSubmitting" class="workspace-streaming-indicator" role="status" aria-live="polite">
            <span class="workspace-dot-pulse" aria-hidden="true"><i></i><i></i><i></i></span>
            <span>{{ revisionSubmitting ? (revisionStage || '正在执行页面修改…') : '正在理解本次请求…' }}</span>
          </div>
        </section>
        <footer class="composer assistant-composer">
          <div class="assistant-input-shell">
            <el-input v-model="prompt" type="textarea" :rows="2" resize="none" :disabled="isAssistantSubmitting" :placeholder="assistantPlaceholder" @keydown.enter="handleAssistantKeydown" />
            <div class="workspace-composer-buttons">
              <VoiceRecorderButton
                :disabled="isAssistantSubmitting"
                :busy="workspaceVoiceSubmitting"
                label="上传语音并继续工作台会话"
                @recorded="handleWorkspaceVoice"
                @error="handleWorkspaceVoiceError"
              />
              <el-button type="primary" circle :icon="Promotion" :loading="isAssistantSubmitting" :disabled="isAssistantSubmitting || !prompt.trim()" aria-label="发送消息" @click="sendAssistantMessage" />
            </div>
          </div>
          <span v-if="isAssistantSubmitting" class="assistant-composer-status" role="status">{{ assistantStatusText }}</span>
        </footer>
      </aside>

      <section v-if="workspaceMode === 'document' && (!isMobile || activeSegment === 'plan')" class="editor-stage document-editor-stage">
        <main class="document-workspace" aria-label="教学案文档工作区">
          <header class="document-workspace-header">
            <div>
              <span>教学案文档</span>
              <h1>{{ lessonPlanTitle }}</h1>
              <p>{{ lessonPlanSubject || '未设置学科' }}<template v-if="lessonPlanGrade"> · {{ lessonPlanGrade }}</template> · {{ documentPlan.duration_minutes || 45 }} 分钟</p>
            </div>
            <div class="document-workspace-actions">
              <el-button class="document-mobile-return" @click="returnToPptWorkspace">返回 PPT</el-button>
              <el-button class="document-mobile-preview" type="primary" plain @click="openLessonPlanPreview">预览教学案</el-button>
            </div>
          </header>
          <LessonPlanEditor
            ref="lessonPlanEditorRef"
            :key="`${projectId || currentDraftStorageId}:${workspaceMode}`"
            :title="lessonPlanTitle"
            :subject="lessonPlanSubject"
            :grade="lessonPlanGrade"
            :outline="lessonPlanOutline"
            :slides="slides"
            :initial-plan="lessonPlanDraft"
            @save="saveLessonPlanDraft"
            @autosave="autosaveLessonPlanDraft"
          />
          <WorkspaceProjectActions v-if="projectId" class="document-project-actions" :status="autosaveState" :saving-version="versionActionLoading" :can-undo="Boolean(revisionUndoSnapshot?.length)" @undo="undoLastAiRevision" @quality="openQualityPanel" @save-version="createVersion" @versions="loadVersions" @permissions="openPermissionDialog" />
        </main>
      </section>

      <section v-else-if="workspaceMode !== 'document' && (!isMobile || activeSegment === 'outline' || activeSegment === 'preview')" class="editor-stage">
        <aside class="slide-rail" aria-label="课件页面列表">
          <button
            v-for="(slide, index) in slides"
            :key="slide.pageId || slide.componentId || `${slide.title}-${slide.html ? 'html' : 'slide'}`"
            :draggable="!isMobile"
            :class="{ active: selectedSlide === index, dragging: draggingSlideIndex === index, 'drop-before': slideDropIndex === index, 'drop-after': slideDropIndex === index + 1 }"
            :aria-label="`第 ${index + 1} 页：${slide.title}${isMobile ? '，使用上下按钮调整顺序' : '，可拖动调整顺序'}`"
            :title="isMobile ? '使用上下按钮调整顺序' : '拖动页面可调整顺序'"
            @dragstart="startSlideDrag(index, $event)"
            @dragover="handleSlideDragOver(index, $event)"
            @drop="dropSlide(index, $event)"
            @dragend="clearSlideDragState"
            @click="selectSlide(index)"
          >
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="thumbnail" :style="{ '--thumb': themes.find((item) => item.id === slide.theme)?.color }"><i></i><b>{{ slide.title }}</b></div>
            <span v-if="isMobile && slides.length > 1" class="rail-reorder rail-reorder-down" data-hover-reveal role="button" aria-label="下移本页" @pointerdown.stop @click.stop="moveSlideRelative(index, 1)"><el-icon><ArrowDown /></el-icon></span>
            <span v-if="isMobile && slides.length > 1" class="rail-reorder rail-reorder-up" data-hover-reveal role="button" aria-label="上移本页" @pointerdown.stop @click.stop="moveSlideRelative(index, -1)"><el-icon><ArrowUp /></el-icon></span>
          </button>
          <el-button text :icon="Plus" @click="addSlide">添加页面</el-button>
       </aside>
       <main class="canvas-area" @click="handleCanvasAreaClick">
           <div v-if="projectId && projectLoadError" class="workspace-load-error" role="alert" @click.stop>
             <div class="workspace-load-error-card">
               <span class="workspace-load-error-icon" aria-hidden="true">!</span>
               <strong>课件暂时无法打开</strong>
               <p>{{ projectLoadError }}</p>
               <div class="workspace-load-error-actions">
                 <el-button type="primary" :loading="hydratingProject" @click="retryProjectLoad">重新加载</el-button>
                 <el-button @click="goHome">返回项目列表</el-button>
               </div>
             </div>
           </div>
           <div v-if="!slides.length && !projectLoadError" class="canvas-empty-state" role="status">
             <el-empty description="暂无课件页面" :image-size="80">
               <el-button v-if="isMobile" type="primary" @click="activeSegment = 'chat'">去对话生成大纲</el-button>
               <el-button v-else type="primary" @click="addSlide">添加页面</el-button>
             </el-empty>
           </div>
           <div v-if="revisionSubmitting" class="revision-overlay" role="status" aria-live="polite" @click.stop>
            <div class="revision-overlay-card">
              <span class="revision-orbit" aria-hidden="true"><i></i><i></i><i></i></span>
              <div>
                <strong>AI 正在修改当前页</strong>
                <span>{{ revisionStage || '正在分析页面内容…' }}</span>
              </div>
              <div class="revision-progress" aria-hidden="true"><i></i></div>
            </div>
          </div>
          <div class="canvas-meta">
            <span>第 {{ selectedSlide + 1 }} 页，共 {{ slides.length }} 页</span>
            <span v-if="workspaceUsesHtmlEditor" class="canvas-placement-status"><b>{{ isMobile ? '点击元素选中 · 浮动按钮编辑' : '拖动元素 · 双击文字编辑' }}</b><small>选中后可缩放、旋转、复制或删除</small></span>
            <span v-if="placementMode" class="canvas-placement-status"><b>{{ placementInstruction }}</b><small>Esc 取消</small></span>
            <span>16:9 · 自适应窗口</span>
          </div>
          <div ref="canvasAreaRef" class="canvas-scroll-viewport" @wheel="handleCanvasWheel">
          <div class="canvas-scene" :style="{ '--canvas-zoom': canvasZoom / 100, minWidth: `${Math.ceil(780 * canvasZoom / 100 + 144)}px`, minHeight: `${Math.ceil(438.75 * canvasZoom / 100 + 144)}px` }">
          <div class="canvas-slide-stage" :style="{ width: `${Math.ceil(780 * canvasZoom / 100)}px`, height: `${Math.ceil(438.75 * canvasZoom / 100)}px` }">
          <article v-if="workspaceUsesHtmlEditor" class="slide-canvas html-slide-canvas" :style="pageCanvasStyle(current, true)" :aria-label="`${current.title} HTML PPT`">
            <iframe class="editable-html-frame" :srcdoc="htmlCanvasFrameSource" sandbox="allow-same-origin" :title="`${current.title} HTML PPT`" @load="fitHtmlFrame"></iframe>
          </article>
          <article v-else class="slide-canvas" :class="[`layout-${current.layout}`, { 'is-placing': placementMode }]" :style="pageCanvasStyle(current, true)" @pointerdown="startCanvasPlacement" @pointermove="handleCanvasPlacementMove" @click="handleSlideCanvasClick">
            <span class="slide-eyebrow">{{ current.eyebrow }}</span>
            <template v-for="element in current.elements" :key="element.id">
              <h1 v-if="element.type === 'text' && element.target === 'title'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</h1>
              <p v-else-if="element.type === 'text' && element.target === 'description'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</p>
              <footer v-else-if="element.type === 'text' && element.target === 'footer'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <span>{{ current.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span>
                <p>{{ elementContent(element) }}</p>
              </footer>
              <div v-else-if="element.type === 'text'" :data-element-id="element.id" class="text-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</div>
              <div v-else-if="element.type === 'formula'" :data-element-id="element.id" class="formula-text-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <strong>{{ elementContent(element) || 'a² + b² = c²' }}</strong>
              </div>
              <div v-else-if="element.type === 'shape' && element.shapeKind === 'formula-diagram'" :data-element-id="element.id" class="formula-diagram-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <svg class="triangle-svg" viewBox="0 0 100 100" role="img" aria-label="直角三角形示意图">
                  <path class="triangle-outline" d="M 12 88 L 82 88 L 82 12 Z" />
                  <text class="triangle-label" x="47" y="98" text-anchor="middle">a</text>
                  <text class="triangle-label" x="90" y="53" text-anchor="middle">b</text>
                  <text class="triangle-label" x="38" y="43" text-anchor="middle">c</text>
                </svg>
              </div>
              <div v-else-if="element.type === 'shape'" :data-element-id="element.id" class="shape-element" :class="[elementClass(element), `shape-${element.shapeKind || 'rectangle'}`]" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <svg class="shape-svg" viewBox="0 0 100 100" :preserveAspectRatio="element.shapeKind === 'circle' ? 'xMidYMid meet' : 'none'" aria-hidden="true">
                  <rect v-if="['rectangle', 'rounded'].includes(element.shapeKind)" class="shape-fill" x="4" y="4" width="92" height="92" :rx="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" :ry="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" />
                  <circle v-else-if="element.shapeKind === 'circle'" class="shape-fill" cx="50" cy="50" r="46" />
                  <polygon v-else-if="element.shapeKind === 'diamond'" class="shape-fill" points="50,4 96,50 50,96 4,50" />
                  <polygon v-else-if="element.shapeKind === 'triangle'" class="shape-fill" points="50,4 96,96 4,96" />
                  <rect v-else class="shape-fill" x="4" y="4" width="92" height="92" />
                </svg>
                <span v-if="elementContent(element)">{{ elementContent(element) }}</span>
              </div>
              <div v-else-if="element.type === 'image'" :data-element-id="element.id" class="image-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <img :src="element.src || createMockImageSrc()" :alt="element.alt || elementContent(element) || element.name" @error="handleImageError(element)" />
                <span v-if="element.style?.showCaption !== false">{{ elementContent(element) || '图片 mock' }}</span>
              </div>
              <div v-else-if="element.type === 'chart'" :data-element-id="element.id" class="chart-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <header><strong>{{ elementContent(element) || '数据图表' }}</strong><small>MOCK DATA</small></header>
                <div class="chart-plot">
                  <div v-for="(item, itemIndex) in (element.data || [])" :key="`${element.id}-${itemIndex}`" class="chart-bar">
                    <span class="chart-bar-fill" :style="{ height: `${Math.max(8, Math.min(100, Number(item.value) || 0))}%` }"></span>
                    <small>{{ item.label }}</small>
                  </div>
                </div>
              </div>
              <div v-else-if="['audio', 'video', 'h5', 'subject'].includes(element.type)" :data-element-id="element.id" class="workspace-widget" :class="[`widget-${element.type}`, elementClass(element)]" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <template v-if="element.type === 'audio'">
                  <audio v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" preload="metadata" @pointerdown.stop="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未添加音频文件，请在右侧选择本地文件</span>
                </template>
                <template v-else-if="element.type === 'video'">
                  <video v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" playsinline preload="metadata" @pointerdown.stop="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未添加视频文件，请在右侧选择本地文件</span>
                </template>
                <template v-else-if="element.type === 'h5'">
                  <iframe v-if="element.html" class="workspace-h5-frame" :srcdoc="secureHtmlForSandbox(withH5RuntimeConfig(element.html, element.h5Config || element.h5_config || {}))" sandbox="allow-scripts" :title="elementContent(element) || 'H5 互动内容'" @load="syncH5FrameViewport" @pointerdown.stop="startElementDrag(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未生成 H5 内容，请使用工具栏生成 H5</span>
                  <button v-if="element.html" type="button" class="widget-action widget-action-button" @click.stop="previewInteractiveElement(element)">放大预览</button>
                </template>
                <SubjectToolRuntime v-else :element="element" @update:data="element.data = $event; markSlideComponentDirty(current, element.id)" />
              </div>
              <div v-else-if="element.type === 'table'" :data-element-id="element.id" class="workspace-widget table-widget" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <strong>{{ elementContent(element) || '数据表格' }}</strong>
                <div class="mock-table-grid"><span v-for="(cell, cellIndex) in (element.data?.flat() || [])" :key="`${element.id}-${cellIndex}`">{{ cell }}</span></div>
              </div>
            </template>
            <div v-if="placementPreviewElement?.type === 'shape'" class="shape-element canvas-element placement-element-preview" :class="`shape-${placementPreviewElement.shapeKind || 'rectangle'}`" :style="placementPreviewStyle" aria-hidden="true">
              <svg class="shape-svg" viewBox="0 0 100 100" :preserveAspectRatio="placementPreviewElement.shapeKind === 'circle' ? 'xMidYMid meet' : 'none'">
                <rect v-if="['rectangle', 'rounded'].includes(placementPreviewElement.shapeKind)" class="shape-fill" x="4" y="4" width="92" height="92" :rx="placementPreviewElement.shapeKind === 'rounded' ? Number(placementPreviewElement.style?.borderRadius ?? 14) : 0" :ry="placementPreviewElement.shapeKind === 'rounded' ? Number(placementPreviewElement.style?.borderRadius ?? 14) : 0" />
                <circle v-else-if="placementPreviewElement.shapeKind === 'circle'" class="shape-fill" cx="50" cy="50" r="46" />
                <polygon v-else-if="placementPreviewElement.shapeKind === 'diamond'" class="shape-fill" points="50,4 96,50 50,96 4,50" />
                <polygon v-else-if="placementPreviewElement.shapeKind === 'triangle'" class="shape-fill" points="50,4 96,96 4,96" />
                <rect v-else class="shape-fill" x="4" y="4" width="92" height="92" />
              </svg>
              <span v-if="elementContent(placementPreviewElement)">{{ elementContent(placementPreviewElement) }}</span>
            </div>
            <div v-else-if="placementPreviewElement?.type === 'image'" class="image-element canvas-element placement-element-preview" :style="placementPreviewStyle" aria-hidden="true">
              <img :src="placementPreviewElement.src || createMockImageSrc()" alt="" />
              <span v-if="placementPreviewElement.style?.showCaption !== false">{{ elementContent(placementPreviewElement) || '图片 mock' }}</span>
            </div>
            <div v-else-if="placementPreviewElement?.type === 'chart'" class="chart-element canvas-element placement-element-preview" :style="placementPreviewStyle" aria-hidden="true">
              <header><strong>{{ elementContent(placementPreviewElement) || '数据图表' }}</strong><small>MOCK DATA</small></header>
              <div class="chart-plot">
                <div v-for="(item, itemIndex) in (placementPreviewElement.data || [])" :key="`placement-${itemIndex}`" class="chart-bar">
                  <span class="chart-bar-fill" :style="{ height: `${Math.max(8, Math.min(100, Number(item.value) || 0))}%` }"></span>
                  <small>{{ item.label }}</small>
                </div>
              </div>
            </div>
            <div v-else-if="['audio', 'video', 'h5', 'subject'].includes(placementPreviewElement?.type)" class="workspace-widget canvas-element placement-element-preview" :class="`widget-${placementPreviewElement.type}`" :style="placementPreviewStyle" aria-hidden="true">
              <audio v-if="placementPreviewElement.type === 'audio' && (placementPreviewElement.url || placementPreviewElement.src)" class="workspace-media-player" :src="placementPreviewElement.url || placementPreviewElement.src" controls preload="metadata" />
              <video v-else-if="placementPreviewElement.type === 'video' && (placementPreviewElement.url || placementPreviewElement.src)" class="workspace-media-player" :src="placementPreviewElement.url || placementPreviewElement.src" controls playsinline preload="metadata" />
              <iframe v-else-if="placementPreviewElement.type === 'h5' && placementPreviewElement.html" class="workspace-h5-frame" :srcdoc="secureHtmlForSandbox(withH5RuntimeConfig(placementPreviewElement.html, placementPreviewElement.h5Config || placementPreviewElement.h5_config || {}))" sandbox="allow-scripts" title="H5 互动内容" @load="syncH5FrameViewport" />
              <SubjectToolRuntime v-else-if="placementPreviewElement.type === 'subject'" :element="placementPreviewElement" compact />
              <span v-else class="widget-empty-state">请在右侧配置{{ elementTypeLabels[placementPreviewElement.type] }}</span>
            </div>
            <div v-else-if="placementPreviewElement?.type === 'table'" class="workspace-widget table-widget canvas-element placement-element-preview" :style="placementPreviewStyle" aria-hidden="true">
              <strong>{{ elementContent(placementPreviewElement) || '数据表格' }}</strong>
              <div class="mock-table-grid"><span v-for="(cell, cellIndex) in (placementPreviewElement.data?.flat() || [])" :key="`placement-cell-${cellIndex}`">{{ cell }}</span></div>
            </div>
          </article>
          </div>
          </div>
          </div>
          <div class="canvas-controls" @click.stop>
            <button type="button" aria-label="缩小画布" title="缩小画布" :disabled="canvasZoom <= CANVAS_ZOOM_MIN" @click="adjustCanvasZoom(-CANVAS_ZOOM_STEP)">−</button>
            <span class="canvas-zoom-field" role="group" aria-label="画布缩放比例">
              <input v-model="canvasZoomInput" class="canvas-zoom-input" type="number" min="50" max="200" step="1" inputmode="numeric" aria-label="输入画布缩放比例" title="输入 50–200 的缩放比例" @change="commitCanvasZoomInput" @blur="commitCanvasZoomInput" @keyup.enter.prevent="commitCanvasZoomInput" @keydown.esc.prevent="resetCanvasZoom">
              <small>%</small>
            </span>
            <button type="button" aria-label="放大画布" title="放大画布" :disabled="canvasZoom >= CANVAS_ZOOM_MAX" @click="adjustCanvasZoom(CANVAS_ZOOM_STEP)">+</button>
            <button type="button" aria-label="将画布回到中心" title="将画布回到中心" @click="centerCanvasView"><el-icon><Aim /></el-icon></button>
          </div>
          <div v-if="isMobile && workspaceSelectedElementId" class="mobile-element-actions" role="toolbar" aria-label="选中元素操作" @click.stop>
            <el-button size="small" type="primary" plain @click="propertiesDrawerVisible = true">编辑</el-button>
            <el-button size="small" type="danger" plain @click="removeElement(workspaceSelectedElementId)">删除</el-button>
          </div>
          <WorkspaceProjectActions v-if="projectId" :status="autosaveState" :saving-version="versionActionLoading" :can-undo="Boolean(revisionUndoSnapshot?.length)" @undo="undoLastAiRevision" @quality="openQualityPanel" @save-version="createVersion" @versions="loadVersions" @permissions="openPermissionDialog" />
        </main>
      </section>

      <WorkspacePropertiesPanel
        :class="{ 'is-mobile-open': propertiesDrawerVisible }"
        :elements="workspaceElements"
        :selected-element="workspaceSelectedElement"
        :selected-element-id="workspaceSelectedElementId"
        :page-number="selectedSlide + 1"
        :page="current"
        :themes="themes"
        :layouts="layouts"
        :resources="workspaceResources"
        :resources-loading="workspaceResourcesLoading"
        :subject-validation-pending="subjectValidationPending"
         @update-element-style="updateElementStyle"
         @update-element-style-map="updateElementStyleMap"
        @update-element-position="updateElementPosition"
        @arrange-element="arrangeSelectedElement"
        @align-element="alignSelectedElement"
        @distribute-elements="distributeElements"
         @update-element-content="updateElementContent"
         @update-element-field="updateElementField"
        @update-element-render="updateElementRender"
        @update-element-h5-config="updateElementH5Config"
        @regenerate-h5="regenerateSelectedH5"
        @update-element-data="updateElementData"
        @validate-subject-tool="validateSubjectTool"
        @select-element="selectElementFromPanel"
        @clear-element="clearElementSelection"
        @copy-element="copyElement"
        @delete-element="removeElement"
        @update-page-field="updatePageField"
        @update-page-theme="updatePageTheme"
        @update-page-layout="updatePageLayout"
        @update-page-background="updatePageBackground"
        @clear-page-background="clearPageBackground"
        @refresh-resources="loadWorkspaceResources"
        @bind-element-resource="bindElementResource"
        @upload-element-resource="uploadElementResource"
        @copy-slide="copySlide"
        @remove-slide="removeSlide"
      />
    </div>
    <button
      v-if="assistantDrawerVisible || propertiesDrawerVisible"
      class="workspace-mobile-overlay"
      type="button"
      aria-label="关闭打开的面板"
      @click="assistantDrawerVisible = false; propertiesDrawerVisible = false"
    ></button>

    <el-dialog v-model="previewVisible" class="preview-dialog" :class="{ 'presentation-dialog': presentationMode }" align-center width="min(960px, 92vw)" title="在线预览 · 全部页面" @closed="clearPreviewFrameObservers">
      <div ref="previewStageRef" class="preview presentation-stage" :class="{ 'is-presenting': presentationMode }" @mousemove="updatePresentationPointer" @mouseleave="hidePresentationPointer" @click="handlePresentationStageClick">
        <div class="preview-toolbar">
          <span>{{ presentationMode ? `放映模式 · 第 ${previewSlideIndex + 1} / ${slides.length} 页` : `连续预览 · 共 ${slides.length} 页` }}</span>
          <div class="preview-toolbar-actions">
            <el-button v-if="!presentationMode" text size="small" :icon="VideoPlay" @click="enterPresentationMode">放映</el-button>
            <el-button v-if="presentationMode && presentationPointerAvailable" text size="small" :type="presentationLaserEnabled ? 'primary' : 'default'" @click="presentationLaserEnabled = !presentationLaserEnabled">激光笔</el-button>
            <el-button v-if="presentationMode" text size="small" :type="presentationNotesVisible ? 'primary' : 'default'" @click="presentationNotesVisible = !presentationNotesVisible">备注提示</el-button>
            <el-button v-if="presentationMode" text size="small" @click="exitPresentationMode">退出放映</el-button>
          </div>
          <nav aria-label="预览页面导航">
            <button v-for="(slide, index) in slides" :key="`preview-nav-${index}`" type="button" :class="{ active: previewSlideIndex === index }" @click="scrollPreviewTo(index)">{{ String(index + 1).padStart(2, '0') }}</button>
          </nav>
        </div>
        <span v-if="presentationMode && presentationLaserEnabled && presentationLaserPosition.visible" class="presentation-laser-pointer" :style="{ left: `${presentationLaserPosition.x}%`, top: `${presentationLaserPosition.y}%` }" aria-hidden="true"></span>
        <aside v-if="presentationMode && presentationNotesVisible" class="presentation-notes"><strong>备注提示</strong><p>{{ previewSpeakerNotes(slides[previewSlideIndex]) }}</p></aside>
        <div ref="previewDeckRef" class="preview-deck">
          <section v-for="(slide, slideIndex) in slides" :key="`preview-page-${slideIndex}-${slide.title}`" class="preview-page" :class="{ 'is-current': previewSlideIndex === slideIndex }" :data-preview-index="slideIndex">
            <div class="preview-page-heading"><span>第 {{ slideIndex + 1 }} 页</span><strong>{{ slide.title }}</strong></div>
            <div class="html-preview-shell">
              <iframe :srcdoc="secureHtmlForSandbox(withHtmlPageBackground(slideHtmlSource(slide), slide))" sandbox="allow-scripts" :title="`${slide.title} HTML PPT 预览`" class="preview-html-frame" @load="fitPreviewHtmlFrame"></iframe>
            </div>
            <article v-if="false" class="slide-canvas preview-slide" :class="`layout-${slide.layout}`" :style="pageCanvasStyle(slide)">
              <span class="slide-eyebrow">{{ slide.eyebrow }}</span>
              <template v-for="element in (slide.elements || [])" :key="`preview-${slideIndex}-${element.id}`">
                <h1 v-if="element.type === 'text' && element.target === 'title'" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)">{{ previewElementContent(element, slide) }}</h1>
                <p v-else-if="element.type === 'text' && element.target === 'description'" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)">{{ previewElementContent(element, slide) }}</p>
                <footer v-else-if="element.type === 'text' && element.target === 'footer'" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><span>{{ slide.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span><p>{{ previewElementContent(element, slide) }}</p></footer>
                <div v-else-if="element.type === 'text'" class="text-element" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)">{{ previewElementContent(element, slide) }}</div>
                <div v-else-if="element.type === 'formula'" class="formula-text-element" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><strong>{{ previewElementContent(element, slide) || 'a² + b² = c²' }}</strong></div>
                <div v-else-if="element.type === 'shape' && element.shapeKind === 'formula-diagram'" class="formula-diagram-element" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><svg class="triangle-svg" viewBox="0 0 100 100" role="img" aria-label="直角三角形示意图"><path class="triangle-outline" d="M 12 88 L 82 88 L 82 12 Z" /><text class="triangle-label" x="47" y="98" text-anchor="middle">a</text><text class="triangle-label" x="90" y="53" text-anchor="middle">b</text><text class="triangle-label" x="38" y="43" text-anchor="middle">c</text></svg></div>
                <div v-else-if="element.type === 'shape'" class="shape-element" :class="[previewElementClass(element), `shape-${element.shapeKind || 'rectangle'}`]" :style="previewElementStyle(element, slide)"><svg class="shape-svg" viewBox="0 0 100 100" :preserveAspectRatio="element.shapeKind === 'circle' ? 'xMidYMid meet' : 'none'" aria-hidden="true"><rect v-if="['rectangle', 'rounded'].includes(element.shapeKind)" class="shape-fill" x="4" y="4" width="92" height="92" :rx="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" :ry="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" /><circle v-else-if="element.shapeKind === 'circle'" class="shape-fill" cx="50" cy="50" r="46" /><polygon v-else-if="element.shapeKind === 'diamond'" class="shape-fill" points="50,4 96,50 50,96 4,50" /><polygon v-else-if="element.shapeKind === 'triangle'" class="shape-fill" points="50,4 96,96 4,96" /><rect v-else class="shape-fill" x="4" y="4" width="92" height="92" /></svg><span v-if="previewElementContent(element, slide)">{{ previewElementContent(element, slide) }}</span></div>
                <div v-else-if="element.type === 'image'" class="image-element" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><img :src="element.src || createMockImageSrc()" :alt="element.alt || previewElementContent(element, slide) || element.name" /><span v-if="element.style?.showCaption !== false">{{ previewElementContent(element, slide) || '图片 mock' }}</span></div>
                <div v-else-if="element.type === 'chart'" class="chart-element" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><header><strong>{{ previewElementContent(element, slide) || '数据图表' }}</strong><small>DATA</small></header><div class="chart-plot"><div v-for="(item, itemIndex) in (element.data || [])" :key="`preview-${slideIndex}-${element.id}-${itemIndex}`" class="chart-bar"><span class="chart-bar-fill" :style="{ height: `${Math.max(8, Math.min(100, Number(item.value) || 0))}%` }"></span><small>{{ item.label }}</small></div></div></div>
                <div v-else-if="['audio', 'video', 'h5', 'subject'].includes(element.type)" class="workspace-widget" :class="[`widget-${element.type}`, previewElementClass(element)]" :style="previewElementStyle(element, slide)">
                  <template v-if="element.type === 'audio'">
                    <audio v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" preload="metadata" />
                    <span v-else class="widget-empty-state">未配置音频文件</span>
                  </template>
                  <template v-else-if="element.type === 'video'">
                    <video v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" playsinline preload="metadata" />
                    <span v-else class="widget-empty-state">未配置视频文件</span>
                  </template>
                  <template v-else-if="element.type === 'h5'">
                    <iframe v-if="element.html" class="workspace-h5-frame" :srcdoc="secureHtmlForSandbox(withH5RuntimeConfig(element.html, element.h5Config || element.h5_config || {}))" sandbox="allow-scripts" :title="previewElementContent(element, slide) || 'H5 互动内容'" @load="syncH5FrameViewport" />
                    <span v-else class="widget-empty-state">未配置 H5 内容</span>
                  </template>
                  <SubjectToolRuntime v-else :element="element" compact />
                </div>
                <div v-else-if="element.type === 'table'" class="workspace-widget table-widget" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><strong>{{ previewElementContent(element, slide) || '数据表格' }}</strong><div class="mock-table-grid"><span v-for="(cell, cellIndex) in (element.data?.flat() || [])" :key="`preview-${slideIndex}-${element.id}-${cellIndex}`">{{ cell }}</span></div></div>
              </template>
            </article>
          </section>
        </div>
      </div>
      <template #footer><el-button v-if="presentationMode" @click="exitPresentationMode">退出放映</el-button><el-button v-else @click="closePreview">继续编辑</el-button></template>
    </el-dialog>
    <el-dialog v-model="revisionPreviewVisible" align-center title="确认 AI 整套修改" width="min(900px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="false">
      <div v-if="pendingDeckRevision" class="revision-preview-dialog">
        <div class="revision-preview-summary">
          <div><span>变更摘要</span><strong>{{ pendingDeckRevision.summary }}</strong></div>
          <span class="revision-preview-count">{{ pendingDeckRevision.operations.length }} 项变更</span>
        </div>
        <section class="revision-preview-section">
          <div class="revision-preview-section-heading"><strong>操作清单</strong><span>API-139A 返回 / 前端校验</span></div>
          <ul class="revision-operation-list">
            <li v-for="operation in pendingDeckRevision.operations" :key="operation.id">
              <el-tag size="small" :type="operation.type === 'delete' ? 'danger' : operation.type === 'add' ? 'success' : operation.type === 'reorder' ? 'warning' : 'info'">{{ operation.label }}</el-tag>
              <span>{{ operation.description }}</span>
            </li>
          </ul>
        </section>
        <section class="revision-preview-section">
          <div class="revision-preview-section-heading"><strong>页面前后对比</strong><span>确认前不会改动画布或项目数据</span></div>
          <div class="revision-comparison-grid">
            <div class="revision-comparison-column">
              <header>修改前 · {{ pendingDeckRevision.before.length }} 页</header>
              <ol><li v-for="(slide, index) in pendingDeckRevision.before" :key="`before-${index}-${slide.title}`"><b>{{ String(index + 1).padStart(2, '0') }}</b><span>{{ slide.title }}</span></li></ol>
            </div>
            <div class="revision-comparison-column is-after">
              <header>修改后 · {{ pendingDeckRevision.after.length }} 页</header>
              <ol><li v-for="(slide, index) in pendingDeckRevision.after" :key="`after-${index}-${slide.title}`"><b>{{ String(index + 1).padStart(2, '0') }}</b><span>{{ slide.title }}</span></li></ol>
            </div>
          </div>
        </section>
      </div>
      <el-empty v-else description="修改预览已失效，请重新发起修改" />
      <template #footer>
        <el-button @click="rejectDeckRevision">拒绝修改</el-button>
        <el-button type="primary" :disabled="!pendingDeckRevision" @click="acceptDeckRevision">接受并应用</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="interactiveDialogVisible" align-center title="生成 H5 组件" width="min(720px, 92vw)" destroy-on-close>
      <el-form :model="interactiveForm" label-position="top" class="interactive-form">
        <div class="interactive-form-grid">
          <el-form-item label="组件标题" required>
            <el-input v-model="interactiveForm.title" maxlength="80" show-word-limit placeholder="例如：勾股定理快速问答" />
          </el-form-item>
          <el-form-item label="知识主题" required>
            <el-input v-model="interactiveForm.topic" maxlength="120" placeholder="例如：直角三角形三边关系" />
          </el-form-item>
          <el-form-item label="H5 类型" required>
            <el-select v-model="interactiveForm.module_type" class="full-width" placeholder="选择模块类型">
              <el-option v-for="item in interactiveModuleTypes" :key="item.value" :label="item.label" :value="item.value">
                <span>{{ item.label }}</span><small class="interactive-option-description">{{ item.description }}</small>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="嵌入方式">
            <el-radio-group v-model="interactiveForm.embed_mode">
              <el-radio-button label="standalone">独立运行</el-radio-button>
              <el-radio-button label="slide_fragment">嵌入页面</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="学科">
            <el-input v-model="interactiveForm.subject" placeholder="例如：数学" />
          </el-form-item>
          <el-form-item label="年级或受众">
            <el-input v-model="interactiveForm.grade" placeholder="例如：八年级" />
          </el-form-item>
        </div>
        <el-form-item label="知识点（可用逗号或换行分隔）">
          <el-input v-model="interactiveForm.knowledge_points" type="textarea" :rows="2" resize="none" placeholder="例如：直角三角形、平方关系、实际测量" />
        </el-form-item>
        <el-form-item label="生成要求（可选）">
          <el-input v-model="interactiveForm.requirements" type="textarea" :rows="3" resize="none" placeholder="例如：适合课堂投屏，交互步骤不超过三步，提供即时反馈" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="interactiveDialogVisible = false">取消</el-button><el-button type="primary" :loading="interactiveGenerating" @click="handleGenerateInteractiveModule">生成 H5 组件</el-button></template>
    </el-dialog>
    <el-dialog v-model="interactivePreviewVisible" align-center title="H5 组件预览" width="min(900px, 94vw)" class="interactive-preview-dialog">
      <div v-if="interactiveModule" class="interactive-preview-meta">
        <div><strong>{{ interactiveModule.title || 'H5 组件' }}</strong><span>{{ interactiveModuleTypeInfo(interactiveModule.module_type || interactiveModule.moduleType).label }}</span><code>{{ interactiveModule.module_type_raw || interactiveModule.module_type || 'unknown' }}</code></div>
        <p>{{ interactiveModule.topic || '暂无主题说明' }}</p>
        <small class="interactive-preview-source">API-144 · {{ interactiveModule.module_id || '未返回模块 ID' }}<template v-if="interactiveModule.metadata?.model_used === false"> · 服务端降级模板</template></small>
      </div>
      <div v-if="interactiveModule?.html" ref="interactivePreviewViewportRef" class="interactive-preview-frame-viewport">
        <iframe :srcdoc="secureHtmlForSandbox(withH5RuntimeConfig(interactiveModule.html, interactiveModule.h5_config || interactiveModule.h5Config || {}))" sandbox="allow-scripts" class="interactive-preview-frame" :style="{ transform: `scale(${interactivePreviewScale})` }" title="H5 组件预览" @load="syncH5FrameViewport"></iframe>
      </div>
      <el-empty v-else description="暂无可预览内容" />
      <ul v-if="interactiveModule?.usage_suggestions?.length" class="interactive-suggestions">
        <li v-for="suggestion in interactiveModule.usage_suggestions" :key="suggestion">{{ suggestion }}</li>
      </ul>
      <template #footer>
        <el-button @click="interactivePreviewVisible = false">关闭</el-button>
        <el-button v-if="interactivePreviewSource === 'generated'" @click="reopenInteractiveDialog">修改生成参数</el-button>
        <template v-if="interactivePreviewSource === 'generated'">
          <el-button @click="insertGeneratedInteractiveModule('current')">插入当前页面</el-button>
          <el-button type="primary" @click="insertGeneratedInteractiveModule('new-page')">作为独立页面插入</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
    <IntentClarificationDialog v-model="clarificationDialogVisible" :question="clarificationQuestion" :loading="clarificationSubmitting" @submit="submitClarification" />
    <div v-if="runStatus === 'running'" class="generation-overlay" role="status" aria-live="polite">
      <div class="generation-state-card">
        <span class="generation-spinner" aria-hidden="true"></span>
        <small class="generation-kicker">AI HTML PPT</small>
        <h2>正在生成课件</h2>
        <p>{{ runStage || '正在准备页面内容…' }}</p>
        <span class="generation-hint">此处仅展示浏览器实际发起的请求与校验步骤；刷新页面会中断当前生成。</span>
        <el-progress :percentage="runProgress" :show-text="false" :stroke-width="5" />
        <div class="generation-observability">
          <section v-if="runTimeline.length" class="generation-detail-section">
            <header><strong>执行步骤</strong><span>{{ runTimeline.length }} 条</span></header>
            <ol class="generation-timeline"><li v-for="item in runTimeline" :key="item.id"><i :class="`status-${item.status}`"></i><div><strong>{{ item.label }}</strong><span>{{ item.statusLabel }}<template v-if="item.detail"> · {{ item.detail }}</template></span></div></li></ol>
          </section>
          <section v-if="runToolCalls.length" class="generation-detail-section">
            <header><strong>实际请求</strong><span>{{ runToolCalls.length }} 次</span></header>
            <ul class="generation-compact-list"><li v-for="tool in runToolCalls" :key="tool.id"><b>{{ tool.name }}</b><span>{{ tool.status }}<template v-if="tool.detail"> · {{ tool.detail }}</template></span></li></ul>
          </section>
          <section v-if="runRetrievalSources.length" class="generation-detail-section">
            <header><strong>本次请求资料</strong><span>{{ runRetrievalSources.length }} 项</span></header>
            <ul class="generation-compact-list"><li v-for="resource in runRetrievalSources" :key="resource.id"><b>{{ resource.name }}</b><span>{{ resource.detail || resource.id }}</span></li></ul>
          </section>
          <section v-if="runReflection" class="generation-detail-section generation-reflection"><header><strong>质量与改进建议</strong><span>已关联本次生成</span></header><p v-if="runReflection.summary">{{ runReflection.summary }}</p><ul v-if="runReflection.suggestions.length" class="generation-compact-list"><li v-for="(item, index) in runReflection.suggestions" :key="`run-reflection-${index}`"><span>{{ item }}</span></li></ul></section>
        </div>
      </div>
    </div>
    <div v-else-if="runStatus === 'failed'" class="generation-overlay generation-overlay-error" role="alert">
      <div class="generation-state-card">
        <small class="generation-kicker">AI HTML PPT</small>
        <h2>课件生成失败</h2>
        <p>{{ generationError || '暂时无法生成 HTML PPT。' }}</p>
        <p v-if="runFailureReason && runFailureReason !== generationError" class="generation-failure-detail">失败原因：{{ runFailureReason }}</p>
        <p v-if="runRecoveryNode" class="generation-recovery">可恢复节点：{{ runRecoveryNode }}</p>
        <div v-if="runTimeline.length" class="generation-failure-timeline"><strong>已执行节点</strong><span v-for="item in runTimeline" :key="`failed-${item.id}`">{{ item.label }} · {{ item.statusLabel }}</span></div>
        <div class="generation-actions">
          <el-button type="primary" @click="retryPresentationGeneration">重新生成</el-button>
          <el-button @click="goHome">返回教学助手</el-button>
        </div>
      </div>
    </div>
    <el-dialog v-model="qualityPanelVisible" align-center title="生成质量与改进建议" width="min(680px, 92vw)">
      <div v-if="qualityReport" class="quality-report-panel">
        <header class="quality-report-heading">
          <div><span>报告来源</span><strong>{{ qualityReportSource || '最近一次生成' }}</strong></div>
          <span v-if="qualityReport.score !== null" class="quality-score">{{ qualityReport.score }}<small>/100</small></span>
        </header>
        <p v-if="qualityReport.summary" class="quality-summary">{{ qualityReport.summary }}</p>
        <section v-if="qualityReport.issues.length" class="quality-report-section">
          <strong>结构问题</strong>
          <ul><li v-for="(item, index) in qualityReport.issues" :key="`quality-issue-${index}`">{{ item }}</li></ul>
        </section>
        <section v-if="qualityReport.risks.length" class="quality-report-section quality-report-risk">
          <strong>内容风险</strong>
          <ul><li v-for="(item, index) in qualityReport.risks" :key="`quality-risk-${index}`">{{ item }}</li></ul>
        </section>
        <section v-if="qualityReport.suggestions.length" class="quality-report-section quality-report-suggestions">
          <div class="quality-section-heading"><strong>可改进建议</strong><span>点击即可交给 AI 执行</span></div>
          <article v-for="(item, index) in qualityReport.suggestions" :key="`quality-suggestion-${index}`">
            <span>{{ item }}</span>
            <el-button text type="primary" size="small" @click="applyQualitySuggestion(item)">一键修改</el-button>
          </article>
        </section>
        <p v-if="qualityReport.retryCount" class="quality-retry-hint">本次生成经历了 {{ qualityReport.retryCount }} 次自动修复。</p>
      </div>
      <el-empty v-else description="暂无质量报告" />
      <template #footer><el-button @click="qualityPanelVisible = false">关闭</el-button></template>
    </el-dialog>
    <el-dialog v-model="contextManagerVisible" align-center title="工作台 AI 上下文" width="min(680px, 92vw)" :close-on-click-modal="false">
      <div class="context-manager">
        <section v-if="workspaceContextPayload().community" class="context-source-card">
          <span>社区来源</span>
          <strong>{{ workspaceContextPayload().community.title || '未命名内容' }}</strong>
          <small>v{{ workspaceContextPayload().community.version || 1 }} · {{ workspaceContextPayload().community.license || '授权未说明' }}</small>
        </section>
        <p class="dialog-hint">选择后续讨论、修改和生成时允许 AI 检索的个人资料。绑定关系只保存在当前项目，不会写回社区。</p>
        <el-checkbox-group v-model="contextManagerIds" v-loading="workspaceResourcesLoading" class="context-resource-picker">
          <el-checkbox v-for="resource in workspaceResources" :key="resource.id" :value="resource.id"><span>{{ resource.name }}</span><small>{{ resource.fileType || '资料' }}</small></el-checkbox>
          <el-empty v-if="!workspaceResourcesLoading && !workspaceResources.length" description="暂无个人资料，请先在首页上传资料" />
        </el-checkbox-group>
        <div v-if="contextManagerIds.length" class="context-selected-resources"><strong>当前绑定</strong><el-tag v-for="id in contextManagerIds" :key="id" closable @close="removeContextResource(id)">{{ workspaceResources.find((resource) => resource.id === String(id))?.name || `资源 ${id}` }}</el-tag></div>
      </div>
      <template #footer><el-button @click="contextManagerVisible = false">取消</el-button><el-button type="primary" :loading="contextManagerSaving" @click="saveWorkspaceContextBindings">保存绑定</el-button></template>
    </el-dialog>
    <el-dialog v-model="versionDialogVisible" align-center title="项目版本历史" width="min(720px, 92vw)" :close-on-click-modal="!versionActionLoading" :close-on-press-escape="!versionActionLoading" :show-close="!versionActionLoading">
      <p class="dialog-hint">保存关键阶段的课件，随时比较或恢复；恢复前会自动备份当前内容。</p>
      <div class="workspace-version-create">
        <el-input v-model="versionDescription" aria-label="版本说明" placeholder="版本说明，例如：完成课堂练习与讲解备注" maxlength="200" show-word-limit :disabled="versionActionLoading" />
        <el-button type="primary" :loading="versionActionLoading" @click="createVersion">保存新版本</el-button>
      </div>
      <div class="workspace-version-compare">
        <span>差异对比基准</span>
        <el-select v-model="compareVersionId" aria-label="差异对比基准" @change="versionDiff = null">
          <el-option label="当前云端版本" value="" />
          <el-option v-for="item in versions" :key="item.version_id || item.id" :label="'版本 ' + item.version_number" :value="item.version_id || item.id" />
        </el-select>
        <el-button text :disabled="versionLoading || versionActionLoading" @click="loadVersions">刷新</el-button>
      </div>
      <el-alert v-if="versionError" :title="versionError" type="error" show-icon :closable="false"><el-button text @click="loadVersions">重新加载</el-button></el-alert>
      <div v-loading="versionLoading" class="version-list" :aria-busy="versionLoading">
        <article v-for="version in versions" :key="version.version_id || version.id">
          <div><strong>版本 {{ version.version_number || version.id }}</strong><p>{{ version.description || '未填写说明' }}</p><small>{{ formatWorkspaceDate(version.created_at) }} · 创建人 {{ version.created_by || '未知' }}</small></div>
          <div class="workspace-version-actions"><el-button text size="small" :disabled="versionDiffLoading || versionActionLoading || compareVersionId === (version.version_id || version.id)" @click="showVersionDiff(version)">查看差异</el-button><el-button text size="small" type="primary" :disabled="versionActionLoading" @click="restoreVersion(version)">恢复此版本</el-button></div>
        </article>
        <el-empty v-if="!versionLoading && !versionError && !versions.length" description="还没有历史版本，保存首个版本以记录当前成果" />
      </div>
      <el-pagination v-if="versionTotal > 10" v-model:current-page="versionPage" :page-size="10" :total="versionTotal" :disabled="versionLoading || versionActionLoading" layout="prev, pager, next, total" @current-change="loadVersions" />
      <section v-if="versionDiff || versionDiffLoading" class="workspace-version-result" v-loading="versionDiffLoading" aria-live="polite">
        <strong>版本差异</strong><p>{{ versionDiff?.summary || '正在比较…' }}</p>
        <pre v-if="versionDiff?.differences?.length" class="version-diff">{{ JSON.stringify(versionDiff.differences, null, 2) }}</pre>
      </section>
      <template #footer><el-button :disabled="versionActionLoading" @click="versionDialogVisible = false">关闭</el-button></template>
    </el-dialog>
    <el-dialog v-model="permissionDialogVisible" align-center title="协作者管理" width="min(620px, 92vw)" :close-on-click-modal="false">
      <div class="permission-manager">
        <section class="permission-search-card">
          <div class="permission-section-heading"><strong>添加协作者</strong><span>通过用户名或邮箱查找</span></div>
          <div class="permission-search-row">
            <el-select v-model="permissionSearchType" aria-label="协作者搜索方式" style="width: 112px">
              <el-option label="用户名" value="username" />
              <el-option label="邮箱" value="email" />
            </el-select>
            <el-input v-model="permissionSearchQuery" :placeholder="permissionSearchType === 'email' ? '输入邮箱地址' : '输入用户名'" clearable @keyup.enter="searchPermissionUser" />
            <el-button type="primary" :loading="permissionSearchLoading" @click="searchPermissionUser">查找</el-button>
          </div>
          <article v-if="permissionSearchResult" class="permission-search-result">
            <div><strong>{{ permissionSearchResult.real_name || permissionSearchResult.username || permissionSearchResult.email || `用户 #${permissionSearchResult.id}` }}</strong><span>{{ permissionSearchResult.email || `用户 ID ${permissionSearchResult.id}` }}</span></div>
            <el-button v-if="!isPermissionGranted(permissionSearchResult.id)" type="primary" size="small" :loading="permissionAddLoading" @click="addSearchedPermission">添加</el-button>
            <el-button v-else type="success" plain size="small" disabled>已授权</el-button>
          </article>
          <el-empty v-else-if="!permissionSearchLoading" :image-size="52" description="查找后可添加协作者" />
        </section>
        <section class="permission-list-card">
          <div class="permission-section-heading"><strong>已授权用户</strong><span>{{ projectPermissionIds.length }} 人</span></div>
          <div v-if="projectPermissionIds.length" class="permission-list">
            <article v-for="userId in projectPermissionIds" :key="userId" class="permission-list-item">
              <div><span class="permission-user-avatar">{{ String(userId).slice(-2) }}</span><div><strong>用户 #{{ userId }}</strong><small>已获得项目编辑权限</small></div></div>
              <el-button text type="danger" size="small" :loading="permissionRemoveLoading === String(userId)" @click="removePermission(userId)">移除</el-button>
            </article>
          </div>
          <el-empty v-else :image-size="52" description="当前项目还没有协作者" />
          <p class="dialog-hint permission-note">项目接口仅返回已授权用户 ID；查找结果会展示用户公开资料，移除操作会同步更新项目权限列表。</p>
        </section>
      </div>
      <template #footer><el-button @click="permissionDialogVisible = false">关闭</el-button></template>
    </el-dialog>
    <el-dialog v-model="communityPublishVisible" align-center title="发布到社区" width="min(680px, 92vw)" :close-on-click-modal="false">
      <el-form :model="communityPublishForm" label-position="top" class="community-publish-form">
        <div class="community-form-grid">
          <el-form-item label="内容类型"><el-select v-model="communityPublishForm.content_type"><el-option label="课程案例" value="lesson_case" /><el-option label="教学技能" value="skill" /></el-select></el-form-item>
          <el-form-item label="授权方式"><el-select v-model="communityPublishForm.license"><el-option label="CC BY-NC 4.0" value="CC BY-NC 4.0" /><el-option label="CC BY 4.0" value="CC BY 4.0" /><el-option label="保留所有权利" value="All Rights Reserved" /></el-select></el-form-item>
        </div>
        <el-form-item label="标题" required><el-input v-model="communityPublishForm.title" maxlength="120" show-word-limit placeholder="给社区内容起一个清晰的标题" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="communityPublishForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="说明适用场景、教学目标或使用方法" /></el-form-item>
        <div class="community-form-grid">
          <el-form-item label="学科"><el-input v-model="communityPublishForm.subject" placeholder="如：数学" /></el-form-item>
          <el-form-item label="年级"><el-input v-model="communityPublishForm.grade" placeholder="如：八年级" /></el-form-item>
          <el-form-item label="课型"><el-input v-model="communityPublishForm.lesson_type" placeholder="如：新授课" /></el-form-item>
        </div>
        <el-form-item label="内容声明"><el-input v-model="communityPublishForm.source_declaration" placeholder="本人原创或已获得授权" /></el-form-item>
        <el-form-item label="提交备注"><el-input v-model="communityPublishForm.notes" type="textarea" :rows="2" maxlength="300" show-word-limit placeholder="可填写给审核人员的补充说明" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="communityPublishVisible = false">取消</el-button><el-button :loading="communityPublishLoading" @click="publishCommunity(false)">保存草稿</el-button><el-button type="primary" :loading="communityPublishLoading" @click="publishCommunity(true)">提交审核</el-button></template>
    </el-dialog>

    <el-dialog v-model="projectManagerVisible" align-center title="项目管理" width="min(760px, 92vw)" class="project-manager-dialog">
      <section v-if="projectId" class="project-manager-current">
        <label>当前项目名称</label>
        <div><el-input v-model="projectNameDraft" maxlength="80" show-word-limit /><el-button type="primary" :loading="projectActionLoading" @click="renameWorkspaceProject">保存名称</el-button></div>
        <div class="project-manager-actions">
          <el-button :loading="projectActionLoading" @click="copyWorkspaceProject">复制项目</el-button>
          <el-button :loading="projectActionLoading" @click="archiveWorkspaceProject()">归档项目</el-button>
          <el-button type="danger" plain :loading="projectActionLoading" @click="removeWorkspaceProject()">删除项目</el-button>
        </div>
      </section>
      <p v-else class="dialog-hint">当前课件尚未保存为项目；导出或保存后即可使用重命名、复制、归档和删除。</p>
      <section class="project-manager-list" v-loading="projectListLoading">
        <div class="project-manager-list-heading"><strong>我的项目</strong><el-button text size="small" @click="loadWorkspaceProjects">刷新</el-button></div>
        <form class="workspace-project-filters" @submit.prevent="searchWorkspaceProjects">
          <el-input v-model="projectFilters.keyword" aria-label="项目名称或课程关键词" placeholder="搜索项目名称或课程" clearable @clear="searchWorkspaceProjects" />
          <el-select v-model="projectFilters.project_type" aria-label="项目类型" placeholder="全部类型" clearable @change="searchWorkspaceProjects"><el-option v-for="(label, value) in projectTypeLabels" :key="value" :label="label" :value="value" /></el-select>
          <el-select v-model="projectFilters.status" aria-label="项目状态" placeholder="全部状态" clearable @change="searchWorkspaceProjects"><el-option v-for="(label, value) in projectStatusLabels" :key="value" :label="label" :value="value" /></el-select>
          <el-button native-type="submit" :disabled="projectListLoading">搜索</el-button>
        </form>
        <el-alert v-if="projectListError" :title="projectListError" type="error" show-icon :closable="false"><el-button text @click="loadWorkspaceProjects">重新加载</el-button></el-alert>
        <article v-for="item in workspaceProjects" :key="item.id || item.project_id">
          <div><strong>{{ item.project_name || item.name || '未命名项目' }}<el-tag v-if="String(item.id || item.project_id) === String(projectId)" size="small">当前项目</el-tag></strong><span>{{ projectStatusLabels[item.status] || item.status }} · {{ projectTypeLabels[item.project_type] || item.project_type }} · {{ formatWorkspaceDate(item.updated_at) }}</span></div>
          <div class="project-manager-item-actions">
            <el-button text size="small" :disabled="projectActionLoading || item.status === 'archived'" @click="openWorkspaceProject(item)">打开</el-button>
            <el-button v-if="String(item.status).toLowerCase() === 'archived'" text size="small" :loading="projectActionLoading" @click="restoreWorkspaceProject(item.id || item.project_id)">恢复</el-button>
            <el-button v-else text size="small" :loading="projectActionLoading" @click="archiveWorkspaceProject(item.id || item.project_id)">归档</el-button>
            <el-button text size="small" type="danger" :loading="projectActionLoading" @click="removeWorkspaceProject(item.id || item.project_id)">删除</el-button>
          </div>
        </article>
        <el-empty v-if="!projectListLoading && !projectListError && !workspaceProjects.length" :description="projectFilters.keyword || projectFilters.project_type || projectFilters.status ? '没有符合筛选条件的项目' : '还没有项目，保存当前课件即可开始'" />
        <el-pagination v-if="projectTotal > projectFilters.size" v-model:current-page="projectFilters.page" :page-size="projectFilters.size" :total="projectTotal" :disabled="projectListLoading" layout="prev, pager, next, total" @current-change="loadWorkspaceProjects" />
      </section>
      <template #footer><el-button @click="projectManagerVisible = false">关闭</el-button></template>
    </el-dialog>
    <LessonPlanPreview
      v-model="lessonPlanPreviewVisible"
      :title="lessonPlanTitle"
      :subject="lessonPlanSubject"
      :grade="lessonPlanGrade"
      :plan="lessonPlanPreviewDraft || lessonPlanDraft"
    />
</template>

<style scoped>
.workspace-project-filters{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,1fr) auto;gap:8px}
.workspace-version-create{display:flex;gap:10px;margin-bottom:16px}
.workspace-version-compare{display:flex;align-items:center;gap:12px;margin-bottom:14px;color:var(--zh-text-secondary);font-size:12px}
.workspace-version-compare .el-select{width:180px}
.workspace-version-actions{display:flex;flex-shrink:0}
.workspace-version-result{min-height:70px;margin-top:16px;padding:14px;background:var(--zh-background-light);border-radius:var(--zh-radius8);font-size:12px}
.version-list small{display:block;margin-top:7px;color:var(--zh-text-caption);font-size:11px;font-variant-numeric:tabular-nums}
.version-list article>div:first-child{min-width:0;overflow-wrap:anywhere}
.version-list{max-height:400px;overflow:auto;margin:14px 0}
.project-manager-list .el-tag{margin-left:8px}
.project-manager-list .el-pagination{justify-content:center}
@media(max-width:767.98px){.workspace-project-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.workspace-project-filters>.el-input{grid-column:1/-1}.workspace-version-create{flex-wrap:wrap}.workspace-version-actions{flex-direction:column}.workspace-version-compare{flex-wrap:wrap}}

.workspace-composer-buttons{display:inline-flex;align-items:center;gap:4px}
.context-manager-trigger{margin-left:auto;flex:none}.context-manager{display:grid;gap:12px}.context-source-card{display:grid;gap:4px;padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.context-source-card span,.context-source-card small{color:var(--zh-text-caption);font-size:11px}.context-source-card strong{color:var(--zh-text-primary);font-size:14px}.context-resource-picker{display:grid;gap:7px;max-height:280px;overflow:auto;padding:10px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.context-resource-picker :deep(.el-checkbox){display:flex;align-items:flex-start;margin:0}.context-resource-picker :deep(.el-checkbox__label){display:flex;align-items:baseline;gap:8px;min-width:0;color:var(--zh-text-secondary);font-size:12px}.context-resource-picker small{color:var(--zh-text-caption);font-size:10px}.context-selected-resources{display:flex;align-items:center;flex-wrap:wrap;gap:6px}.context-selected-resources strong{margin-right:3px;color:var(--zh-text-caption);font-size:11px}
.generation-observability{display:grid;gap:8px;max-height:38vh;overflow:auto;margin-top:12px;padding-top:12px;border-top:1px solid rgb(37 99 235 / 14%);text-align:left}.generation-detail-section{padding:9px 10px;border:1px solid rgb(37 99 235 / 12%);border-radius:8px;background:rgb(255 255 255 / 74%)}.generation-detail-section header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:7px}.generation-detail-section header strong{font-size:11px}.generation-detail-section header span{color:#7c8491;font-size:10px}.generation-timeline{display:grid;gap:6px;margin:0;padding:0;list-style:none}.generation-timeline li{display:flex;align-items:flex-start;gap:7px}.generation-timeline li>i{flex:none;width:7px;height:7px;margin-top:4px;border-radius:50%;background:#9ca3af}.generation-timeline li>i.status-running,.generation-timeline li>i.status-executing,.generation-timeline li>i.status-processing{background:#2563eb;box-shadow:0 0 0 3px rgb(37 99 235 / 14%)}.generation-timeline li>i.status-completed,.generation-timeline li>i.status-success,.generation-timeline li>i.status-done{background:#16a34a}.generation-timeline li>i.status-failed,.generation-timeline li>i.status-error{background:#dc2626}.generation-timeline li div{display:grid;gap:2px;min-width:0}.generation-timeline li strong{overflow:hidden;color:#26364d;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.generation-timeline li span,.generation-compact-list li span{color:#7c8491;font-size:10px;line-height:1.45}.generation-compact-list{display:grid;gap:5px;margin:0;padding:0;list-style:none}.generation-compact-list li{display:flex;gap:6px;min-width:0;color:#526176;font-size:10px;line-height:1.45}.generation-compact-list li b{flex:none;color:#334c70;font-size:10px}.generation-compact-list li span{min-width:0;overflow:hidden;text-overflow:ellipsis}.generation-reflection p{margin:0;color:#526176;font-size:10px;line-height:1.5}.generation-failure-detail,.generation-recovery{padding:8px 10px;border-radius:8px;text-align:left;font-size:11px;line-height:1.5}.generation-failure-detail{color:#9b2c2c;background:#fff3f0}.generation-recovery{color:#7a5a14;background:#fff8e7}.generation-failure-timeline{display:grid;gap:5px;padding:8px 10px;border-radius:8px;color:#7c8491;background:#f8fafc;text-align:left;font-size:10px;line-height:1.45}.generation-failure-timeline strong{color:#526176;font-size:11px}
.revision-preview-dialog{display:grid;gap:14px}.revision-preview-summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.revision-preview-summary div{display:grid;gap:4px;min-width:0}.revision-preview-summary span:first-child{color:var(--zh-text-caption);font-size:11px}.revision-preview-summary strong{color:var(--zh-text-primary);font-size:14px;line-height:1.5}.revision-preview-count{flex:none;padding:5px 9px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-primary);font-size:11px}.revision-preview-section{padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.revision-preview-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}.revision-preview-section-heading strong{font-size:13px}.revision-preview-section-heading span{color:var(--zh-text-caption);font-size:11px}.revision-operation-list{display:grid;gap:7px;max-height:180px;overflow:auto;margin:0;padding:0;list-style:none}.revision-operation-list li{display:flex;align-items:center;gap:8px;min-width:0;padding:7px 8px;border-radius:var(--zh-radius8);background:var(--zh-background-light);color:var(--zh-text-secondary);font-size:12px}.revision-operation-list li>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.revision-comparison-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.revision-comparison-column{min-width:0;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);overflow:hidden}.revision-comparison-column header{padding:9px 11px;color:var(--zh-text-secondary);background:var(--zh-background-light);font-size:12px;font-weight:600}.revision-comparison-column.is-after header{color:var(--zh-text-theme);background:var(--zh-background-weaken)}.revision-comparison-column ol{display:grid;gap:5px;max-height:220px;overflow:auto;margin:0;padding:9px;list-style:none}.revision-comparison-column li{display:flex;align-items:center;gap:8px;min-width:0;color:var(--zh-text-secondary);font-size:12px}.revision-comparison-column li b{display:grid;place-items:center;flex:none;width:24px;height:20px;border-radius:5px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:600 10px var(--zh-font-number)}.revision-comparison-column li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media(max-width:767.98px){.revision-comparison-grid{grid-template-columns:1fr}.revision-preview-summary{align-items:flex-start;flex-direction:column}}
.workspace{height:100dvh;display:grid;grid-template-rows:auto minmax(0,1fr);overflow:hidden;background:var(--zh-background-light)}.workspace-grid{min-height:0;display:grid;grid-template-columns:286px minmax(500px,1fr) 270px}.assistant-panel,.properties{min-height:0;background:var(--zh-background-primary)}.assistant-panel{display:flex;flex-direction:column;border-right:1px solid var(--zh-line-border)}.assistant-panel>header{display:flex;align-items:center;gap:9px;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.assistant-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:var(--zh-radius8);color:#fff;background:var(--zh-gradient-blue);font-weight:700}.assistant-panel header div:last-child{display:flex;flex-direction:column}.assistant-panel header strong{font-size:13px}.assistant-panel header span{margin-top:2px;color:var(--zh-text-caption);font-size:10px}.conversation{flex:1;padding:16px;overflow:auto}.message{display:flex;align-items:flex-start;gap:8px;margin-bottom:16px}.message>span{display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:6px;color:#fff;background:var(--zh-theme-primary);font-size:10px}.message p{margin:0;padding:10px 12px;border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-answer-card);font-size:12px;line-height:1.65}.message.user{justify-content:flex-end}.message.user p{color:var(--zh-text-primary);background:var(--zh-background-user-query)}.composer{padding:12px;border-top:1px solid var(--zh-line-border)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:8px}.composer span{color:var(--zh-text-caption);font-size:10px}.composer :deep(.el-textarea__inner){background:var(--zh-background-light);box-shadow:none}.editor-stage{display:grid;grid-template-columns:116px minmax(0,1fr);min-width:0}.slide-rail{padding:12px 9px;overflow:auto;border-right:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.slide-rail>button{display:grid;grid-template-columns:18px 1fr;gap:4px;width:100%;margin-bottom:10px;padding:3px;border:1px solid transparent;border-radius:6px;color:var(--zh-text-caption);background:transparent;text-align:left;cursor:pointer}.slide-rail>button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.thumbnail{display:flex;flex-direction:column;justify-content:center;gap:5px;height:54px;padding:8px;border-radius:4px;background:var(--zh-background-light)}.thumbnail i{width:65%;height:3px;background:var(--thumb)}.thumbnail b{overflow:hidden;color:var(--zh-text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}.slide-rail :deep(.el-button){width:100%;justify-content:flex-start}.canvas-area{position:relative;display:grid;place-items:center;min-width:0;padding:44px 34px;overflow:auto;background-color:#eef0f4;background-image:radial-gradient(#c9ced7 1px,transparent 1px);background-size:18px 18px}.canvas-meta{position:absolute;top:12px;inset-inline:20px;display:flex;justify-content:space-between;color:#7c8491;font-size:10px}.slide-canvas{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;padding:clamp(28px,4vw,52px);color:#102d54;background:#f9fbff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.slide-eyebrow,.slide-canvas h1,.slide-canvas>p,.theorem{position:relative;z-index:1}.slide-eyebrow{color:var(--accent);font:600 10px var(--zh-font-number);letter-spacing:.12em}.slide-canvas h1{max-width:76%;margin:18px 0 0;font-size:clamp(26px,3vw,40px);line-height:1.2;letter-spacing:-.04em}.slide-canvas>p{max-width:64%;margin:12px 0;color:#607491;font-size:clamp(11px,1.2vw,15px);line-height:1.65}.theorem{display:grid;grid-template-columns:.8fr 1.2fr;align-items:center;gap:28px;width:76%;margin:28px auto}.triangle{position:relative;width:104px;height:104px;border-right:5px solid var(--accent);border-bottom:5px solid var(--accent);transform:skewY(-35deg) rotate(-10deg)}.triangle i{position:absolute;color:var(--accent);font-style:normal;font-weight:700;transform:skewY(35deg) rotate(10deg)}.triangle i:nth-child(1){bottom:-22px;left:36px}.triangle i:nth-child(2){top:40px;right:-18px}.triangle i:nth-child(3){top:-22px;left:8px}.formula{display:grid;grid-template-columns:auto 24px auto;align-items:center;font-family:var(--zh-font-number)}.formula span,.formula strong{font-size:clamp(22px,3vw,36px)}.formula em{color:#7c8da4;font-style:normal}.formula strong{color:var(--accent)}.formula small{grid-column:1/-1;margin-top:8px;color:#7c8da4;font-size:10px}.slide-canvas footer{position:absolute;z-index:1;right:0;bottom:0;left:0;display:grid;grid-template-columns:110px 1fr;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54)}.slide-canvas footer p{margin:0;font-size:10px;line-height:1.5}.layout-重点陈述 h1{margin-top:54px;font-size:clamp(34px,4.4vw,52px)}.canvas-controls{position:absolute;right:18px;bottom:14px;display:flex;overflow:hidden;border-radius:var(--zh-radius8);background:var(--zh-background-capsule);box-shadow:var(--zh-shadow1)}.canvas-controls button,.canvas-controls span{padding:6px 9px;border:0;color:var(--zh-text-secondary);background:transparent;font-size:11px}.canvas-controls button{cursor:pointer}.properties{overflow:auto;border-left:1px solid var(--zh-line-border)}.properties>header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties header strong{font-size:13px}.properties header span{color:var(--zh-text-caption);font-size:10px}.tabs{display:grid;grid-template-columns:repeat(3,1fr);padding:10px 14px 0;border-bottom:1px solid var(--zh-line-parting)}.tabs button{padding:8px;border:0;border-bottom:2px solid transparent;color:var(--zh-text-caption);background:transparent;cursor:pointer}.tabs button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme)}.properties section{padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties label{display:block;margin:0 0 10px;color:var(--zh-text-secondary);font-size:11px;font-weight:600}.properties label:not(:first-child){margin-top:18px}.theme-picker{display:flex;gap:12px}.theme-picker button{width:24px;height:24px;border:2px solid var(--zh-background-primary);border-radius:50%;box-shadow:0 0 0 1px var(--zh-line-border);cursor:pointer}.theme-picker button.selected{outline:2px solid var(--zh-text-theme);outline-offset:2px}.layout-picker{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.layout-picker button{display:grid;grid-template-rows:26px auto;gap:4px;min-height:66px;padding:7px 4px;border:1px solid var(--zh-line-border);border-radius:6px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:9px;cursor:pointer}.layout-picker button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.layout-picker i{display:block;width:70%;height:4px;margin:auto;background:var(--zh-line-theme50)}.layout-picker i:nth-child(2){width:48%}.page-actions{display:grid;gap:8px}.page-actions :deep(.el-button){justify-content:flex-start;margin:0}.assistant-tip{display:flex;gap:8px;margin:16px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.assistant-tip p,.hint{margin:0;color:var(--zh-text-secondary);font-size:10px;line-height:1.6}.preview{display:grid;place-items:center;padding:18px;background:#eef0f4}.preview-slide{width:min(780px,100%)}.preview-formula{width:max-content;margin:50px auto}.preview-dialog :deep(.el-dialog__body){padding:0}@media(max-width:1023.98px){.workspace-grid{grid-template-columns:250px minmax(460px,1fr)}.properties{display:none}}@media(max-width:767.98px){.workspace-grid{grid-template-columns:1fr}.assistant-panel{display:none}.editor-stage{grid-template-columns:88px minmax(0,1fr)}}
.plan-dialog-content .plan-status{margin:0 0 14px;color:var(--zh-text-secondary);font-size:13px}.plan-preview{display:grid;gap:12px;max-height:min(62vh,680px);overflow:auto;padding:2px 4px 4px 0}.plan-overview{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:18px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);background:linear-gradient(135deg,var(--zh-background-weaken),var(--zh-background-primary))}.plan-overview-heading{min-width:0}.plan-eyebrow{color:var(--zh-text-theme);font-size:10px;font-weight:700;letter-spacing:.12em}.plan-overview h3{margin:7px 0 6px;color:var(--zh-text-primary);font-size:19px;line-height:1.35}.plan-overview p{margin:0;color:var(--zh-text-secondary);font-size:12px;line-height:1.7}.plan-slide-count{display:inline-flex;flex:none;align-items:center;padding:7px 10px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-primary);font:700 12px var(--zh-font-number);white-space:nowrap}.plan-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.plan-meta>span{display:grid;gap:4px;padding:11px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-meta small,.slide-details small{color:var(--zh-text-caption);font-size:10px}.plan-meta strong{overflow:hidden;color:var(--zh-text-primary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.plan-section{padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.plan-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}.plan-section-heading strong{color:var(--zh-text-primary);font-size:13px}.plan-section-heading span{color:var(--zh-text-caption);font-size:11px}.plan-bullet-list,.slide-points{display:grid;gap:7px;margin:0;padding-left:18px;color:var(--zh-text-secondary);font-size:12px;line-height:1.6}.plan-bullet-list li::marker,.slide-points li::marker{color:var(--zh-text-theme)}.plan-tags{display:flex;flex-wrap:wrap;gap:7px}.plan-tags span{padding:5px 9px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:11px}.plan-slide-list{display:grid;gap:8px}.plan-slide-card{display:grid;grid-template-columns:36px minmax(0,1fr);gap:10px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-slide-number{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:700 11px var(--zh-font-number)}.plan-slide-main{min-width:0}.plan-slide-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px}.plan-slide-heading h4{margin:0;color:var(--zh-text-primary);font-size:13px}.plan-slide-heading span{color:var(--zh-text-caption);font-size:10px}.slide-points{margin-bottom:9px}.slide-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-top:9px;border-top:1px solid var(--zh-line-parting)}.slide-details p{margin:3px 0 0;color:var(--zh-text-secondary);font-size:11px;line-height:1.55}.plan-comment{margin-top:14px}.run-progress{position:fixed;z-index:100;right:24px;bottom:24px;width:min(320px,calc(100vw - 48px));padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-pop);box-shadow:var(--zh-shadow2);font-size:12px}.run-progress :deep(.el-progress){margin-top:9px}
  .version-list{display:grid;gap:10px}.version-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.version-list strong{font-size:13px}.version-list p{margin:4px 0 0;color:var(--zh-text-caption);font-size:12px}.version-diff{margin:0;padding:12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-weaken);font-size:12px;line-height:1.6;white-space:pre-wrap}.dialog-hint{margin:0 0 12px;color:var(--zh-text-secondary);font-size:13px}
.quality-report-panel{display:grid;gap:14px}.quality-report-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 16px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.quality-report-heading div{display:grid;gap:4px}.quality-report-heading span:first-child{color:var(--zh-text-caption);font-size:10px}.quality-report-heading strong{color:var(--zh-text-primary);font-size:14px}.quality-score{color:var(--zh-text-theme);font:700 28px var(--zh-font-number)}.quality-score small{margin-left:2px;color:var(--zh-text-caption);font-size:11px}.quality-summary{margin:0;color:var(--zh-text-secondary);font-size:13px;line-height:1.7}.quality-report-section{padding:12px 14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.quality-report-section>strong,.quality-section-heading strong{color:var(--zh-text-primary);font-size:12px}.quality-report-section ul{display:grid;gap:6px;margin:8px 0 0;padding-left:18px;color:var(--zh-text-secondary);font-size:12px;line-height:1.55}.quality-report-risk{border-color:color-mix(in srgb,var(--el-color-warning) 35%,var(--zh-line-border))}.quality-report-suggestions{display:grid;gap:8px}.quality-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.quality-section-heading span,.quality-retry-hint{color:var(--zh-text-caption);font-size:10px}.quality-report-suggestions article{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 10px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.quality-report-suggestions article span{min-width:0;color:var(--zh-text-secondary);font-size:12px;line-height:1.5}.quality-report-suggestions article :deep(.el-button){flex:none;margin:0}.quality-retry-hint{margin:0}
.project-manager-current{display:grid;gap:10px;padding:14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.project-manager-current>label{color:var(--zh-text-secondary);font-size:12px;font-weight:600}.project-manager-current>div:first-of-type{display:flex;gap:8px}.project-manager-actions{display:flex;flex-wrap:wrap;gap:8px}.project-manager-list{display:grid;gap:8px;margin-top:18px;min-height:100px}.project-manager-list-heading{display:flex;align-items:center;justify-content:space-between}.project-manager-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:11px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.project-manager-list article>div:first-child{display:grid;gap:4px;min-width:0}.project-manager-list strong{overflow:hidden;color:var(--zh-text-primary);font-size:13px;text-overflow:ellipsis;white-space:nowrap}.project-manager-list span{color:var(--zh-text-caption);font-size:11px}.project-manager-item-actions{display:flex;align-items:center;flex:none;gap:2px}
.permission-manager{display:grid;gap:14px}.permission-search-card,.permission-list-card{display:grid;gap:10px;padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-light)}.permission-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.permission-section-heading strong{color:var(--zh-text-primary);font-size:13px}.permission-section-heading span{color:var(--zh-text-caption);font-size:11px}.permission-search-row{display:grid;grid-template-columns:112px minmax(0,1fr) auto;gap:8px}.permission-search-row :deep(.el-button){margin:0}.permission-search-result{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.permission-search-result div{display:grid;gap:3px;min-width:0}.permission-search-result strong{overflow:hidden;color:var(--zh-text-primary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.permission-search-result span{overflow:hidden;color:var(--zh-text-caption);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.permission-list{display:grid;gap:7px;max-height:220px;overflow:auto}.permission-list-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 10px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-primary)}.permission-list-item>div{display:flex;align-items:center;gap:9px;min-width:0}.permission-user-avatar{display:grid;place-items:center;flex:none;width:30px;height:30px;border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:700 10px var(--zh-font-number)}.permission-list-item>div>div{display:grid;gap:3px;min-width:0}.permission-list-item strong{color:var(--zh-text-primary);font-size:12px}.permission-list-item small{color:var(--zh-text-caption);font-size:10px}.permission-note{margin:0}.community-publish-form{display:grid;gap:2px}.community-form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.community-form-grid:first-child{grid-template-columns:repeat(2,minmax(0,1fr))}.community-publish-form :deep(.el-form-item){margin-bottom:12px}.community-publish-form :deep(.el-form-item__label){padding-bottom:5px;color:var(--zh-text-secondary);font-size:11px}.presentation-dialog :deep(.el-dialog){max-width:none;background:#0d1117}.presentation-dialog :deep(.el-dialog__header){background:#0d1117}.presentation-dialog :deep(.el-dialog__title),.presentation-dialog :deep(.el-dialog__headerbtn){color:#f8fafc}.presentation-dialog :deep(.el-dialog__body){padding:0}.presentation-stage.is-presenting{position:relative;max-height:none;min-height:min(78vh,820px);padding:18px;background:#080b10}.presentation-stage:fullscreen{display:grid;place-items:center;max-height:none;padding:24px;background:#080b10}.presentation-stage:fullscreen .preview-deck{width:min(1200px,100%)}.presentation-stage:fullscreen .preview-toolbar{position:fixed;right:24px;left:24px;width:auto;margin:0}.preview-toolbar-actions{display:flex;align-items:center;gap:2px;margin-left:auto}.preview-toolbar-actions :deep(.el-button){margin:0}.presentation-stage.is-presenting .preview-page:not(.is-current){display:none}.presentation-stage.is-presenting .preview-page.is-current .preview-page-heading{display:none}.presentation-stage.is-presenting .preview-page.is-current .preview-slide,.presentation-stage.is-presenting .preview-page.is-current .html-preview-shell{width:min(1120px,100%);margin:0 auto}.presentation-stage.is-presenting .preview-deck{display:block;width:min(1120px,100%);margin:auto}.presentation-stage.is-presenting .preview-html-frame{min-height:min(70vh,720px)}.presentation-laser-pointer{position:absolute;z-index:8;width:18px;height:18px;border:3px solid #fff;border-radius:50%;background:#ef4444;box-shadow:0 0 0 5px rgb(239 68 68 / 25%),0 0 22px rgb(239 68 68 / 85%);pointer-events:none;transform:translate(-50%,-50%)}.presentation-notes{position:absolute;z-index:7;right:24px;bottom:24px;width:min(290px,calc(100% - 48px));padding:12px 14px;border:1px solid rgb(255 255 255 / 18%);border-radius:var(--zh-radius10);color:#e5e7eb;background:rgb(15 23 42 / 92%);box-shadow:0 12px 32px rgb(0 0 0 / 25%)}.presentation-notes strong{font-size:12px}.presentation-notes p{margin:6px 0 0;color:#cbd5e1;font-size:11px;line-height:1.6}
.generic-visual{grid-column:1/-1;display:flex;align-items:center;justify-content:center;gap:14px;padding:24px;border:1px solid color-mix(in srgb,var(--accent) 24%,transparent);border-radius:var(--zh-radius12);background:color-mix(in srgb,var(--accent) 8%,white)}.generic-visual span{color:var(--accent);font-size:clamp(15px,2vw,22px);font-weight:600}.generic-visual em{color:#8a98aa;font-style:normal}

/* PPT 缩略图：阻止长标题撑开网格，并在固定画布内最多展示两行。 */
.slide-rail > button {
  grid-template-columns: 18px minmax(0, 1fr);
  min-width: 0;
  position: relative;
  overflow: visible;
  cursor: grab;
  user-select: none;
}
.slide-rail > button:active {
  cursor: grabbing;
}
.slide-rail > button.dragging {
  opacity: .45;
}
.slide-rail > button.drop-before::before,
.slide-rail > button.drop-after::after {
  position: absolute;
  z-index: 4;
  right: 2px;
  left: 2px;
  height: 2px;
  border-radius: 999px;
  background: var(--zh-text-theme);
  box-shadow: 0 0 0 2px rgb(37 99 235 / 16%);
  content: '';
  pointer-events: none;
}
.slide-rail > button.drop-before::before {
  top: -5px;
}
.slide-rail > button.drop-after::after {
  bottom: -5px;
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

.formula-element {
  display: grid;
  grid-template-columns: minmax(72px, .8fr) minmax(0, 1.2fr);
  align-items: center;
  gap: 18px;
  padding: 10px;
}

.formula-element .formula {
  grid-template-columns: 1fr;
  min-width: 0;
  text-align: center;
}

.formula-element .formula strong {
  overflow: hidden;
  color: var(--element-color, var(--accent));
  font-size: inherit;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shape-element {
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 0;
  background: transparent;
}

.shape-svg {
  position: absolute;
  inset: 0;
  z-index: 0;
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.shape-fill {
  fill: var(--element-color, var(--accent));
  fill-opacity: .14;
  stroke: var(--element-border-color, var(--element-color, var(--accent)));
  stroke-width: var(--element-border-width, 2px);
  vector-effect: non-scaling-stroke;
  stroke-linejoin: round;
}

.slide-canvas.is-placing {
  cursor: crosshair;
  user-select: none;
  touch-action: none;
}

.slide-canvas.is-placing [data-element-id] {
  pointer-events: none;
}

.placement-element-preview {
  z-index: 20 !important;
  min-width: 2px;
  min-height: 2px;
  outline: 2px dashed color-mix(in srgb, var(--accent) 76%, white);
  outline-offset: 3px;
  cursor: crosshair;
  pointer-events: none;
  transition: none;
  will-change: left, top, width, height;
}

.shape-element > span {
  max-width: 90%;
  overflow: hidden;
  color: var(--element-border-color, var(--element-color, var(--accent)));
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.shape-element.canvas-element-selected {
  overflow: visible;
  outline: 2px dashed color-mix(in srgb, var(--zh-text-theme) 82%, white);
  outline-offset: 7px;
}

.preview-slide .canvas-element-shape.theorem { display: none; }

@media (max-width: 767.98px) {
  .plan-overview { flex-direction: column; gap: 10px; }
  .plan-slide-count { align-self: flex-start; }
  .plan-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .slide-details { grid-template-columns: 1fr; }
}

.canvas-element {
  cursor: grab;
  transition: outline 160ms ease, outline-offset 160ms ease, opacity 160ms ease;
  touch-action: none;
}

.canvas-element-dragging {
  cursor: grabbing;
  user-select: none;
  transition: none;
}

.canvas-element:hover {
  outline: 1px dashed color-mix(in srgb, var(--zh-text-theme) 64%, transparent);
  outline-offset: 4px;
}

.canvas-element-selected {
  outline: 2px dashed color-mix(in srgb, var(--zh-text-theme) 82%, white);
  outline-offset: 7px;
}

.slide-canvas h1.canvas-element-selected,
.slide-canvas > p.canvas-element-selected {
  border-radius: 4px;
}

.triangle {
  border-right: var(--element-border-width, 5px) solid var(--element-border-color, var(--element-color, var(--accent)));
  border-bottom: var(--element-border-width, 5px) solid var(--element-border-color, var(--element-color, var(--accent)));
  border-radius: var(--element-border-radius, 0);
}

.triangle i,
.formula strong {
  color: var(--element-color, var(--accent));
}

.generic-visual {
  border-color: color-mix(in srgb, var(--element-color, var(--accent)) 24%, transparent);
  background: color-mix(in srgb, var(--element-color, var(--accent)) 8%, white);
}

.generic-visual span {
  color: var(--element-color, var(--accent));
}

/* 公式示意图、公式文字和说明文字是三个独立画布元素，各自可选中和编辑。 */
.formula-text-element {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 4px;
  font-family: var(--zh-font-number);
  text-align: center;
}

.formula-text-element strong {
  max-width: 100%;
  overflow: hidden;
  color: var(--element-color, var(--accent));
  font-size: inherit;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.formula-diagram-element {
  display: grid;
  place-items: center;
  overflow: visible;
  padding: 4px;
}

.triangle-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.triangle-outline {
  fill: none;
  stroke: var(--element-border-color, var(--element-color, var(--accent)));
  stroke-width: var(--element-border-width, 5px);
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.triangle-label {
  fill: var(--element-color, var(--accent));
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}

.slide-canvas .canvas-element {
  position: absolute;
  box-sizing: border-box;
  margin: 0;
}

.slide-eyebrow {
  position: absolute;
  z-index: 6;
  top: 7%;
  left: 8%;
}

.slide-canvas .text-element {
  display: block;
  overflow: hidden;
  line-height: 1.5;
  white-space: pre-wrap;
}

.slide-canvas h1.canvas-element {
  line-height: 1.2;
}

.slide-canvas footer.canvas-element {
  display: grid;
  grid-template-columns: 110px 1fr;
  align-items: center;
  padding: 14px 28px;
  overflow: hidden;
}

.slide-canvas footer.canvas-element p {
  margin: 0;
  overflow: hidden;
  white-space: pre-wrap;
}

.image-element {
  overflow: hidden;
  border: var(--element-border-width, 1px) solid var(--element-border-color, #bfdbfe);
  border-radius: var(--element-border-radius, 14px);
  background: #dbeafe;
  box-shadow: 0 10px 24px rgb(37 99 235 / 12%);
}

.image-element::after {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: color-mix(in srgb, var(--element-color, var(--accent)) 12%, transparent);
  content: '';
  pointer-events: none;
}

.image-element img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: var(--element-object-fit, cover);
}

.image-element > span {
  position: absolute;
  right: 10px;
  bottom: 8px;
  left: 10px;
  z-index: 2;
  overflow: hidden;
  padding: 5px 7px;
  border-radius: 5px;
  color: #fff;
  background: rgb(16 45 84 / 68%);
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chart-element {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  overflow: hidden;
  border: var(--chart-border-width, 1px) solid var(--chart-border-color, #bfdbfe);
  border-radius: var(--chart-border-radius, 14px);
  background: var(--chart-background, #eff6ff);
  box-shadow: 0 10px 24px rgb(37 99 235 / 10%);
}

.chart-element > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chart-element > header strong {
  overflow: hidden;
  color: #173d78;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chart-element > header small {
  flex: none;
  color: var(--chart-color, var(--accent));
  font: 700 8px var(--zh-font-number);
}

.chart-plot {
  display: flex;
  flex: 1;
  align-items: flex-end;
  justify-content: space-around;
  gap: 8px;
  min-height: 0;
  padding: 8px 6px 0;
  border-bottom: 1px solid rgb(96 116 145 / 22%);
}

.chart-bar {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
  height: 100%;
  flex-direction: column;
}

.chart-bar-fill {
  display: block;
  width: min(22px, 70%);
  min-height: 8%;
  border-radius: 5px 5px 2px 2px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--chart-color, var(--accent)) 72%, white), var(--chart-color, var(--accent)));
}

.chart-bar small {
  overflow: hidden;
  color: #607491;
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.html-slide-canvas{padding:0;background:#fff}.html-slide-canvas iframe{position:absolute;top:0;left:0;display:block;width:1280px;height:720px;border:0;background:#fff;transform-origin:top left}.html-preview-shell{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;background:#fff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.preview-html-frame{position:absolute;top:0;left:0;display:block;width:1280px;height:720px;border:0;background:#fff;transform-origin:top left}
.workspace-widget {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 12px;
  overflow: hidden;
  border: var(--widget-border-width, 1px) solid var(--widget-border-color, #bfdbfe);
  border-radius: var(--widget-border-radius, 12px);
  background: var(--widget-background, #eff6ff);
  color: var(--widget-color, var(--accent));
  box-shadow: 0 10px 24px rgb(37 99 235 / 9%);
}

.widget-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  color: #fff;
  background: var(--widget-color, var(--accent));
  font-size: 13px;
  font-weight: 700;
}

.workspace-widget > div {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.workspace-widget strong,
.workspace-widget small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-widget strong {
  color: #173d78;
  font-size: 11px;
}

.workspace-widget small {
  color: #607491;
  font-size: 9px;
}

.workspace-media-player {
  display: block;
  width: 100%;
  min-width: 0;
  min-height: 34px;
  max-height: 100%;
  border-radius: 7px;
  background: rgb(255 255 255 / 76%);
}

.workspace-widget.widget-audio,
.workspace-widget.widget-video,
.workspace-widget.widget-h5 {
  align-content: center;
  flex-wrap: wrap;
}

.workspace-widget.widget-audio .workspace-media-player,
.workspace-widget.widget-video .workspace-media-player {
  flex: 1 1 100%;
}

.workspace-h5-frame {
  display: block;
  flex: 1 1 100%;
  width: 100%;
  min-width: 0;
  min-height: 70px;
  height: 100%;
  border: 0;
  border-radius: 7px;
  background: #fff;
}

.widget-empty-state {
  display: block;
  width: 100%;
  color: #8192aa;
  font-size: 10px;
  line-height: 1.5;
  text-align: center;
}

.widget-action-button {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.widget-action {
  margin-left: auto;
  padding: 4px 7px;
  border-radius: 999px;
  color: var(--widget-color, var(--accent));
  background: rgb(255 255 255 / 70%);
  font-size: 9px;
  white-space: nowrap;
}

.workspace-load-error {
  position: absolute;
  z-index: 30;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(241 245 251 / 82%);
  backdrop-filter: blur(3px);
}

/* 画布空状态：无页面时兜底，防止预览段白屏（移动端分段切换 / 桌面空草稿通用） */
.canvas-empty-state {
  position: absolute;
  z-index: 20;
  inset: 0;
  display: grid;
  place-items: center;
  background: var(--zh-background-light);
}

.workspace-load-error-card {
  display: grid;
  justify-items: center;
  gap: 10px;
  width: min(470px, 90%);
  padding: 28px 30px;
  border: 1px solid #d7e2f0;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 18px 48px rgb(35 61 95 / 14%);
  text-align: center;
}

.workspace-load-error-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #fff;
  background: #e46b67;
  font-size: 21px;
  font-weight: 700;
}

.workspace-load-error-card strong {
  color: #203d64;
  font-size: 18px;
}

.workspace-load-error-card p {
  margin: 0;
  color: #6b7d96;
  font-size: 13px;
  line-height: 1.7;
}

.workspace-load-error-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 4px;
}

.table-widget {
  display: block;
}

.table-widget > strong {
  display: block;
  margin-bottom: 7px;
}

.mock-table-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid rgb(96 116 145 / 18%);
  border-radius: 6px;
  background: rgb(255 255 255 / 60%);
}

.mock-table-grid span {
  min-width: 0;
  padding: 5px 4px;
  overflow: hidden;
  border-right: 1px solid rgb(96 116 145 / 14%);
  border-bottom: 1px solid rgb(96 116 145 / 14%);
  color: #607491;
  font-size: 8px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-meta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  pointer-events: none;
}

.canvas-meta > span:last-child {
  grid-column: 3;
  text-align: right;
}

.canvas-placement-status {
  display: inline-flex;
  grid-column: 2;
  align-items: center;
  gap: 8px;
  justify-self: center;
  padding: 5px 9px;
  border: 1px solid color-mix(in srgb, var(--zh-text-theme) 24%, transparent);
  border-radius: 999px;
  color: var(--zh-text-theme);
  background: color-mix(in srgb, var(--zh-background-primary) 92%, transparent);
  box-shadow: var(--zh-shadow1);
}

.canvas-placement-status b {
  font-size: 10px;
  font-weight: 700;
}

.canvas-placement-status small {
  color: var(--zh-text-caption);
  font-size: 9px;
}

:global(.workspace-message.el-message) {
  max-width: min(420px, calc(100vw - 32px));
  border-radius: 10px;
  box-shadow: 0 12px 32px rgb(16 45 84 / 16%);
}

:global(.workspace-message.el-message.el-message-fade-enter-from.is-center),
:global(.workspace-message.el-message.el-message-fade-leave-to.is-center) {
  opacity: 0;
  transform: translateX(-50%);
}

.assistant-actions {
  padding: 10px 12px 0;
}

.assistant-actions :deep(.el-button) {
  width: 100%;
  margin: 0;
}

/* 工作台侧栏对话与主对话保持同一套气泡、流式提示和入场节奏。 */
.workspace-conversation {
  padding: 18px 12px;
  scroll-behavior: smooth;
}

.workspace-message-list {
  display: block;
}

.workspace-chat-message {
  min-width: 0;
}

.workspace-user-bubble {
  max-width: 86%;
  margin: 16px 0 16px auto;
  padding: 10px 14px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius8) var(--zh-radius18);
  color: var(--zh-text-primary);
  background: var(--zh-background-user-query);
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.workspace-ai-bubble {
  width: 100%;
  min-height: 1px;
  margin: 16px 0;
}

.workspace-ai-markdown {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius18) var(--zh-radius8);
  color: var(--zh-text-primary);
  background: var(--zh-background-answer-card);
  font-size: 12px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.workspace-ai-markdown :deep(p:first-child) { margin-top: 0; }
.workspace-ai-markdown :deep(p:last-child) { margin-bottom: 0; }

.workspace-bubble-typing,
.workspace-streaming-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--zh-text-caption);
}

.workspace-bubble-typing {
  width: max-content;
  min-height: 38px;
  padding: 10px 14px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius18) var(--zh-radius8);
  background: var(--zh-background-answer-card);
}

.workspace-streaming-indicator {
  justify-content: center;
  min-height: 30px;
  padding: 6px 0 10px;
  font-size: 10px;
}

.workspace-bubble-typing i,
.workspace-dot-pulse i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--zh-text-theme);
  animation: workspace-dot-pulse 1.2s cubic-bezier(.4, 0, .2, 1) infinite;
}

.workspace-dot-pulse { display: flex; gap: 4px; }
.workspace-bubble-typing i:nth-child(2), .workspace-dot-pulse i:nth-child(2) { animation-delay: .2s; }
.workspace-bubble-typing i:nth-child(3), .workspace-dot-pulse i:nth-child(3) { animation-delay: .4s; }

.workspace-msg-enter-enter-active {
  transition: opacity 300ms cubic-bezier(0, 0, .2, 1), transform 300ms cubic-bezier(0, 0, .2, 1);
}

.workspace-msg-enter-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

@keyframes workspace-dot-pulse {
  0%, 100% { opacity: .3; transform: scale(.8); }
  50% { opacity: 1; transform: scale(1); }
}

.widget-action-button {
  border: 0;
  cursor: pointer;
  font-family: inherit;
}

.interactive-form {
  padding-top: 4px;
}

.interactive-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.interactive-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.interactive-form :deep(.el-form-item__label) {
  padding-bottom: 6px;
  color: var(--zh-text-secondary);
  font-size: 12px;
}

.full-width {
  width: 100%;
}

.interactive-option-description {
  float: right;
  margin-left: 18px;
  color: var(--zh-text-caption);
  font-size: 11px;
}

.interactive-preview-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}

.interactive-preview-meta {
  display: grid;
  gap: 5px;
  margin-bottom: 12px;
}

.interactive-preview-meta > div {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.interactive-preview-meta strong {
  overflow: hidden;
  color: var(--zh-text-primary);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.interactive-preview-meta span {
  flex: none;
  padding: 4px 8px;
  border-radius: 999px;
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font-size: 11px;
}

.interactive-preview-meta code {
  flex: none;
  color: var(--zh-text-caption);
  font: 10px var(--zh-font-number);
}

.interactive-preview-source {
  color: var(--zh-text-caption);
  font: 10px var(--zh-font-number);
}

.interactive-preview-meta p {
  margin: 0;
  color: var(--zh-text-secondary);
  font-size: 12px;
}

.interactive-preview-frame-viewport {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: #f8fafc;
}

.interactive-preview-frame {
  position: absolute;
  inset: 0 auto auto 0;
  display: block;
  width: 1280px;
  height: 720px;
  border: 0;
  border-radius: 0;
  background: #f8fafc;
  transform-origin: top left;
}

.interactive-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--zh-text-caption);
  font-size: 11px;
}

@media (max-width: 767.98px) {
  .interactive-form-grid {
    grid-template-columns: 1fr;
  }

}
.generation-overlay {
  position: fixed;
  z-index: 90;
  inset: 60px 0 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(238 240 244 / 78%);
  backdrop-filter: blur(2px);
}

.generation-state-card {
  display: grid;
  justify-items: center;
  width: min(440px, 100%);
  padding: 30px 32px;
  border: 1px solid var(--zh-line-theme20);
  border-radius: 18px;
  color: var(--zh-text-secondary);
  background: var(--zh-background-pop);
  box-shadow: 0 24px 70px rgb(40 57 82 / 18%);
  text-align: center;
}

.generation-kicker {
  color: var(--zh-text-theme);
  font: 700 10px var(--zh-font-number);
  letter-spacing: .14em;
  text-transform: uppercase;
}

.generation-state-card h2 {
  margin: 10px 0 8px;
  color: var(--zh-text-primary);
  font-size: 22px;
}

.generation-state-card p {
  max-width: 360px;
  margin: 0;
  color: var(--zh-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.generation-hint {
  margin: 12px 0 18px;
  color: var(--zh-text-caption);
  font-size: 11px;
  line-height: 1.6;
}

.generation-state-card :deep(.el-progress) {
  width: 100%;
}

.generation-spinner {
  width: 30px;
  height: 30px;
  margin-bottom: 13px;
  border: 3px solid var(--zh-line-theme20);
  border-top-color: var(--zh-text-theme);
  border-radius: 50%;
  animation: generation-spin 900ms linear infinite;
}

.generation-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
}

.generation-overlay-error .generation-state-card {
  border-color: rgb(239 95 93 / 28%);
}

@keyframes generation-spin {
  to { transform: rotate(360deg); }
}

.preview {
  display: block;
  max-height: min(72vh, 760px);
  overflow: auto;
  padding: 16px;
  background: #eef0f4;
}

.preview-toolbar {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: min(780px, 100%);
  margin: 0 auto 16px;
  padding: 9px 12px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius8);
  background: rgb(255 255 255 / 92%);
  box-shadow: 0 8px 22px rgb(40 57 82 / 10%);
  backdrop-filter: blur(8px);
}

.preview-toolbar > span {
  color: var(--zh-text-secondary);
  font-size: 11px;
  white-space: nowrap;
}

.preview-toolbar nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px;
}

.preview-toolbar button {
  min-width: 28px;
  padding: 4px 6px;
  border: 1px solid transparent;
  border-radius: 5px;
  color: var(--zh-text-caption);
  background: transparent;
  font: 10px var(--zh-font-number);
  cursor: pointer;
}

.preview-toolbar button:hover,
.preview-toolbar button.active {
  border-color: var(--zh-line-theme);
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
}

.preview-deck {
  display: grid;
  gap: 24px;
  width: 100%;
  min-width: 0;
}

.preview-page {
  display: grid;
  gap: 7px;
  width: 100%;
  min-width: 0;
  scroll-margin-top: 70px;
}

.preview-page-heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: min(780px, 100%);
  margin: 0 auto;
  color: var(--zh-text-caption);
  font-size: 10px;
}

.preview-page-heading strong {
  overflow: hidden;
  color: var(--zh-text-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-page.is-current .preview-page-heading span {
  color: var(--zh-text-theme);
  font-weight: 700;
}

.preview-page .html-preview-shell,
.preview-page .preview-slide {
  margin: 0 auto;
}

@media (max-width: 767.98px) {
  .preview-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .preview-toolbar nav {
    justify-content: flex-start;
  }
}

.canvas-area {
  display: block;
  padding: 0;
  overflow: hidden;
}

.canvas-scroll-viewport {
  position: absolute;
  inset: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

.canvas-meta,
.canvas-controls {
  z-index: 10;
}

.canvas-meta {
  pointer-events: none;
}

.canvas-scene {
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: 100%;
  min-height: 100%;
  padding: 72px;
}

.canvas-slide-stage {
  position: relative;
  flex: none;
}

.canvas-slide-stage .slide-canvas {
  width: 780px;
  max-width: none;
  transform: scale(var(--canvas-zoom, 1));
  transform-origin: top left;
  will-change: transform;
}

.canvas-controls button:disabled {
  cursor: not-allowed;
  opacity: .4;
}

.canvas-controls .canvas-zoom-field {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 5px;
  color: var(--zh-text-secondary);
  font-size: 11px;
}

.canvas-controls .canvas-zoom-input {
  box-sizing: border-box;
  width: 44px;
  height: 24px;
  padding: 0 3px;
  border: 1px solid var(--zh-line-border);
  border-radius: 5px;
  outline: none;
  color: var(--zh-text-secondary);
  background: var(--zh-background-light);
  font: inherit;
  text-align: center;
}

.canvas-controls .canvas-zoom-input:focus {
  border-color: var(--zh-line-theme);
  box-shadow: 0 0 0 2px var(--zh-line-theme20);
}

.canvas-controls .canvas-zoom-input::-webkit-inner-spin-button,
.canvas-controls .canvas-zoom-input::-webkit-outer-spin-button {
  margin: 0;
}

.canvas-controls .canvas-zoom-field small {
  font-size: 11px;
}

.assistant-execution {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0 12px 10px;
  padding: 9px 10px;
  border: 1px solid color-mix(in srgb, var(--zh-line-theme) 40%, var(--zh-line-border));
  border-radius: 9px;
  color: var(--zh-text-secondary);
  background: var(--zh-background-weaken);
}

.assistant-execution-spinner {
  position: relative;
  width: 24px;
  height: 24px;
  flex: none;
  border: 2px solid var(--zh-line-border);
  border-top-color: var(--zh-line-theme);
  border-radius: 50%;
  animation: a12-spin .9s linear infinite;
}

.assistant-execution-spinner i {
  position: absolute;
  inset: 5px;
  border: 2px solid transparent;
  border-left-color: var(--zh-line-theme);
  border-radius: 50%;
  animation: a12-spin .6s linear reverse infinite;
}

.assistant-execution > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.assistant-execution strong {
  color: var(--zh-text-primary);
  font-size: 11px;
}

.assistant-execution-detail {
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assistant-execution-dots {
  display: flex;
  gap: 3px;
  margin-left: auto;
}

.assistant-execution-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--zh-line-theme);
  animation: a12-dot 1s ease-in-out infinite;
}

.assistant-execution-dots i:nth-child(2) {
  animation-delay: .15s;
}

.assistant-execution-dots i:nth-child(3) {
  animation-delay: .3s;
}

.revision-overlay {
  position: absolute;
  z-index: 20;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(238 240 244 / 52%);
  backdrop-filter: blur(2px);
  pointer-events: auto;
}

.revision-overlay-card {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 10px 12px;
  width: min(310px, 100%);
  padding: 14px 16px;
  border: 1px solid color-mix(in srgb, var(--zh-line-theme) 40%, var(--zh-line-border));
  border-radius: 12px;
  background: rgb(255 255 255 / 92%);
  box-shadow: 0 14px 34px rgb(16 45 84 / 14%);
}

.revision-orbit {
  position: relative;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 2px solid var(--zh-line-border);
  border-top-color: var(--zh-line-theme);
  border-radius: 50%;
  animation: a12-spin 1s linear infinite;
}

.revision-orbit i {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--zh-line-theme);
  animation: a12-orbit 1.4s linear infinite;
}

.revision-orbit i:nth-child(2) {
  animation-delay: .2s;
}

.revision-orbit i:nth-child(3) {
  animation-delay: .4s;
}

.revision-overlay-card > div:not(.revision-progress) {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.revision-overlay-card strong {
  color: var(--zh-text-primary);
  font-size: 12px;
}

.revision-overlay-card > div:not(.revision-progress) > span {
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.revision-progress {
  grid-column: 1 / -1;
  height: 3px;
  overflow: hidden;
  border-radius: 99px;
  background: var(--zh-line-border);
}

.revision-progress i {
  display: block;
  width: 38%;
  height: 100%;
  border-radius: inherit;
  background: var(--zh-line-theme);
  animation: a12-progress 1.2s ease-in-out infinite;
}

.assistant-target-bar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--zh-line-parting);
  background: var(--zh-background-light);
}

.assistant-target-bar > span {
  flex: none;
  color: var(--zh-text-caption);
  font-size: 10px;
  font-weight: 600;
}

.assistant-target-controls { display: grid; flex: 1; min-width: 0; gap: 6px; }
.assistant-target-controls :deep(.el-select) { min-width: 0; width: 100%; }
.assistant-dock-trigger { margin-left: 2px; }
.mobile-panel-close { display: none; }

.document-workspace > .document-project-actions { position: sticky; bottom: 14px; left: auto; justify-self: center; transform: none; max-width: 100%; }
.document-editor-stage { display: block; min-width: 0; overflow: auto; background: #eef0f4; }
.document-workspace { display: grid; gap: 16px; width: min(980px, calc(100% - 40px)); margin: 26px auto; }
.document-workspace-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding: 22px 24px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius12); background: var(--zh-background-primary); box-shadow: var(--zh-shadow1); }
.document-workspace-header > div:first-child { min-width: 0; }
.document-workspace-header > div:first-child > span { color: var(--zh-text-theme); font-size: 10px; font-weight: 700; letter-spacing: .12em; }
.document-workspace-header h1 { margin: 7px 0 5px; color: var(--zh-text-primary); font-size: 23px; line-height: 1.35; }
.document-workspace-header p { margin: 0; color: var(--zh-text-caption); font-size: 12px; }
.document-workspace-actions { display: flex; flex: none; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.document-mobile-return, .document-mobile-preview { display: none; }

/* AI 助手：将身份、作用范围和对话输入分成三个克制的层级，适配窄侧栏。 */
.assistant-panel {
  background: var(--zh-background-primary);
}

.assistant-panel > .assistant-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 14px 14px 12px;
  border-bottom: 0;
}

.assistant-identity {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
}

.assistant-panel .assistant-mark {
  position: relative;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--zh-line-theme20);
  border-radius: 10px;
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 72%);
  font: 700 10px/1 var(--zh-font-number);
  letter-spacing: -.04em;
}

.assistant-panel .assistant-mark::after {
  position: absolute;
  right: -6px;
  bottom: -7px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--zh-theme-primary);
  content: '';
  opacity: .12;
}

.assistant-panel .assistant-mark span { position: relative; z-index: 1; }

.assistant-panel > .assistant-header .assistant-identity > .assistant-title {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.assistant-panel .assistant-title strong {
  overflow: hidden;
  color: var(--zh-text-primary);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: var(--zh-tracking-tight);
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assistant-panel .assistant-title span {
  overflow: hidden;
  margin: 0;
  color: var(--zh-text-caption);
  font-size: 10px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assistant-panel > .assistant-header > .assistant-header-actions {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

.assistant-context-button,
.assistant-icon-button {
  min-width: 0;
  height: 28px;
  padding: 0 7px;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-secondary);
  font-size: 11px;
  transition: color 200ms cubic-bezier(.4, 0, .2, 1), background-color 200ms cubic-bezier(.4, 0, .2, 1), transform 200ms cubic-bezier(.4, 0, .2, 1);
}

.assistant-icon-button { width: 28px; padding: 0; font-size: 16px; }
.assistant-context-button:hover,
.assistant-context-button:focus-visible,
.assistant-icon-button:hover,
.assistant-icon-button:focus-visible { color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.assistant-context-button:active,
.assistant-icon-button:active { transform: translateY(1px); }

.assistant-target-bar {
  align-items: flex-start;
  gap: 9px;
  margin: 0 12px 10px;
  padding: 10px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-light);
}

.assistant-target-bar > .assistant-target-caption {
  padding-top: 6px;
  color: var(--zh-text-caption);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .04em;
  white-space: nowrap;
}

.assistant-target-controls { gap: 6px; }
.assistant-target-controls :deep(.el-select__wrapper) { min-height: 30px; border-radius: var(--zh-radius8); box-shadow: 0 0 0 1px var(--zh-line-border) inset; }
.assistant-target-controls :deep(.el-select__wrapper.is-focused) { box-shadow: 0 0 0 1px var(--zh-line-theme) inset, 0 0 0 3px var(--zh-line-theme20); }

.workspace-conversation {
  padding: 8px 12px 18px;
  background: linear-gradient(180deg, var(--zh-background-primary) 0%, color-mix(in srgb, var(--zh-background-light) 42%, var(--zh-background-primary)) 100%);
}

.workspace-user-bubble { margin-top: 14px; margin-bottom: 14px; }
.workspace-ai-bubble { margin: 14px 0; }
.workspace-ai-markdown { border: 1px solid var(--zh-line-border); box-shadow: 0 4px 12px rgb(16 45 84 / 4%); }

.assistant-composer {
  display: grid;
  gap: 7px;
  padding: 12px;
  border-top: 1px solid var(--zh-line-parting);
  background: var(--zh-background-primary);
}

.assistant-input-shell { position: relative; }
.assistant-input-shell :deep(.el-textarea__inner) {
  min-height: 70px !important;
  padding: 10px 74px 10px 11px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius12);
  color: var(--zh-text-primary);
  background: var(--zh-background-light);
  box-shadow: none;
  font-size: 12px;
  line-height: 1.6;
  transition: border-color 200ms cubic-bezier(.4, 0, .2, 1), box-shadow 200ms cubic-bezier(.4, 0, .2, 1), background-color 200ms cubic-bezier(.4, 0, .2, 1);
}
.assistant-input-shell :deep(.el-textarea__inner:hover) { border-color: var(--zh-line-heavier); background: var(--zh-background-primary); }
.assistant-input-shell :deep(.el-textarea__inner:focus) { border-color: var(--zh-line-theme); background: var(--zh-background-primary); box-shadow: 0 0 0 3px var(--zh-line-theme20); }
.assistant-composer .workspace-composer-buttons {
  position: absolute;
  right: 7px;
  bottom: 7px;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius8);
  background: var(--zh-background-primary);
  box-shadow: 0 3px 8px rgb(16 45 84 / 5%);
}
.assistant-composer .workspace-composer-buttons :deep(.el-button) { width: 26px; height: 26px; }
.assistant-composer .workspace-composer-buttons :deep(.el-button--primary) { box-shadow: none; }
.assistant-composer-status { overflow: hidden; color: var(--zh-text-caption); font-size: 10px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }

.workspace-grid.is-assistant-bottom { grid-template-columns: minmax(500px, 1fr) 270px; grid-template-rows: minmax(0, 1fr) minmax(220px, 34vh); }
.workspace-grid.is-assistant-bottom .assistant-panel { grid-column: 1 / -1; grid-row: 2; border-top: 1px solid var(--zh-line-border); border-right: 0; }
.workspace-grid.is-assistant-bottom .editor-stage { grid-column: 1; grid-row: 1; }
.workspace-grid.is-assistant-bottom .properties { grid-column: 2; grid-row: 1; }
.workspace-mobile-overlay { display: none; }

@media (max-width: 1023.98px) {
  .workspace-grid { grid-template-columns: 250px minmax(0, 1fr); }
  .workspace-grid.is-assistant-bottom { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr) minmax(220px, 34vh); }
  .workspace-grid.is-assistant-bottom .editor-stage { grid-column: 1; }
  .workspace-grid.is-assistant-bottom .assistant-panel { grid-column: 1; }
  .workspace-grid.is-assistant-bottom .properties { grid-column: auto; grid-row: auto; }
  .properties { display: none; }
  .properties.is-mobile-open { position: fixed; z-index: 90; top: 60px; right: 0; bottom: 0; display: block; width: min(390px, calc(100vw - 28px)); border-left: 1px solid var(--zh-line-border); box-shadow: var(--zh-shadow2); }
  .workspace-mobile-overlay { position: fixed; z-index: 89; inset: 60px 0 0; display: block; padding: 0; border: 0; background: rgb(16 24 40 / 35%); cursor: default; }
}

@media (max-width: 767.98px) {
  .workspace-grid, .workspace-grid.is-assistant-bottom { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .workspace-grid.is-assistant-bottom .editor-stage { grid-column: 1; grid-row: 1; }
  .assistant-panel, .workspace-grid.is-assistant-bottom .assistant-panel { display: none; }
  .assistant-panel.is-mobile-open { position: fixed; z-index: 90; top: 60px; bottom: 0; left: 0; display: flex; width: min(390px, calc(100vw - 28px)); border-right: 1px solid var(--zh-line-border); box-shadow: var(--zh-shadow2); }
  .assistant-dock-trigger { display: none; }
  .mobile-panel-close { display: inline-flex; margin-left: 2px; }
  .assistant-panel > header { padding: 12px; }
  .assistant-target-bar { margin-right: 12px; margin-left: 12px; }
  .editor-stage { grid-template-columns: 82px minmax(0, 1fr); }
  .document-workspace { width: min(100% - 24px, 980px); margin: 12px auto; }
  .document-workspace-header { flex-direction: column; padding: 18px; }
  .document-workspace-actions { justify-content: flex-start; }
  .document-mobile-return, .document-mobile-preview { display: inline-flex; }
}

/* ===== 手机档（<768px）分段切换：方案 doc/responsive-design/08-creation-workspace.md ===== */
.workspace-mobile-segments { display: none; }
.rail-reorder { display: none; }
.mobile-element-actions { display: none; }

@media (max-width: 767.98px) {
  /* 视口可滚 + 100dvh：composer 用 sticky bottom 而非 fixed，软键盘弹起靠页面滚动缓解遮挡 */
  .workspace { height: auto; min-height: 100dvh; overflow: visible; padding-top: var(--zh-safe-top); padding-bottom: var(--zh-safe-bottom); }
  .workspace-mobile-segments { display: block; padding: 8px 12px; border-bottom: 1px solid var(--zh-line-border); background: var(--zh-background-primary); }
  .workspace-mobile-segments :deep(.el-segmented) { width: 100%; }
  .workspace-mobile-segments :deep(.el-segmented__group) { width: 100%; }
  .workspace-mobile-segments :deep(.el-segmented__item) { flex: 1; min-height: 40px; }
  /* 分段单栏：消除三栏 500px 硬下限（桌面基线 286px / minmax(500px,1fr) / 270px 不受影响） */
  .workspace-grid.is-mobile-segmented,
  .workspace-grid.is-mobile-segmented.is-assistant-bottom { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  /* 手机档不存在「AI 面板停靠底部」，中和 is-assistant-bottom 的网格占位 */
  .workspace-grid.is-mobile-segmented.is-assistant-bottom .assistant-panel,
  .workspace-grid.is-mobile-segmented.is-assistant-bottom .editor-stage,
  .workspace-grid.is-mobile-segmented.is-assistant-bottom .properties { grid-column: auto; grid-row: auto; }
  .workspace-grid.is-mobile-segmented.is-assistant-bottom .assistant-panel { border-top: 0; border-right: 1px solid var(--zh-line-border); }
  .workspace-grid.is-mobile-segmented .editor-stage {
    grid-template-columns: minmax(0, 1fr);
    /* workspace 高度 auto 后 1fr 行塌陷，画布（absolute 定位）无固有高度 → 显式给高 */
    height: calc(100dvh - 150px);
    min-height: 420px;
    overflow: auto;
  }
  .workspace-grid.is-mobile-segmented[data-mobile-segment='outline'] .canvas-area { display: none; }
  .workspace-grid.is-mobile-segmented[data-mobile-segment='preview'] .slide-rail { display: none; }
  /* 手机档画布元信息：中间操作提示让位（触屏已有浮动操作条），左右两项平铺防竖排 */
  .workspace-grid.is-mobile-segmented .canvas-meta { grid-template-columns: auto auto; justify-content: space-between; font-size: var(--zh-font-size10); }
  .workspace-grid.is-mobile-segmented .canvas-meta .canvas-placement-status { display: none; }
  .workspace-grid.is-mobile-segmented .canvas-meta > span:last-child { grid-column: auto; }
  .workspace-grid.is-mobile-segmented[data-mobile-segment='chat'] .assistant-panel { display: flex; }
  /* 手机档不再使用左/右抽屉（平板档能力）：AI 面板回到文档流，属性面板改为底部面板 */
  .workspace-grid.is-mobile-segmented .assistant-panel.is-mobile-open { position: static; inset: auto; width: auto; box-shadow: none; }
  .workspace-grid.is-mobile-segmented .properties.is-mobile-open { position: fixed; z-index: 90; top: auto; right: 0; bottom: 0; display: block; width: min(390px, 100vw); max-height: min(72dvh, 640px); border-left: 1px solid var(--zh-line-border); box-shadow: var(--zh-shadow2); }
  .workspace-mobile-overlay { inset: 0; }
  /* 对话段 composer：sticky 贴底 + 底部安全区 */
  .workspace-grid.is-mobile-segmented[data-mobile-segment='chat'] .assistant-composer { position: sticky; z-index: 5; bottom: 0; padding-bottom: calc(12px + var(--zh-safe-bottom)); }
  /* 大纲段：页面列表铺满 + 上下移按钮（替代 HTML5 拖拽排序） */
  .workspace-grid.is-mobile-segmented[data-mobile-segment='outline'] .slide-rail { padding: 12px; }
  .workspace-grid.is-mobile-segmented[data-mobile-segment='outline'] .slide-rail > button { grid-template-columns: auto minmax(0, 1fr); align-items: center; min-height: 44px; padding: 8px 54px 8px 8px; }
  .rail-reorder { position: absolute; z-index: 3; top: 50%; display: grid; place-items: center; width: 34px; height: 34px; margin-top: -17px; border: 1px solid var(--zh-line-border); border-radius: 50%; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 15px; line-height: 1; }
  /* 触控目标 ≥44×44：视觉保留 34px 圆钮，伪元素外扩热区 */
  .rail-reorder::before { content: ''; position: absolute; inset: -5px; }
  .rail-reorder:active { transform: scale(0.94); }
  .rail-reorder-down { right: 8px; }
  .rail-reorder-up { right: 50px; }
  /* 预览段：选中元素的浮动操作（替代拖拽 / 双击编辑） */
  .mobile-element-actions { position: fixed; z-index: 88; right: 14px; bottom: calc(18px + var(--zh-safe-bottom)); display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 1px solid var(--zh-line-border); border-radius: 999px; background: var(--zh-background-pop); box-shadow: var(--zh-shadow2); }
  /* 触屏无鼠标指针：激光笔样式兜底隐藏（mousemove 守卫已在 JS 中禁用） */
  .presentation-laser-pointer { display: none; }
}

@keyframes a12-spin {
  to { transform: rotate(360deg); }
}

@keyframes a12-dot {
  0%, 80%, 100% { transform: scale(.65); opacity: .4; }
  40% { transform: scale(1); opacity: 1; }
}

@keyframes a12-orbit {
  from { transform: rotate(0deg) translateX(11px) rotate(0deg); }
  to { transform: rotate(360deg) translateX(11px) rotate(-360deg); }
}

@keyframes a12-progress {
  0% { transform: translateX(-140%); }
  50% { transform: translateX(120%); }
  100% { transform: translateX(280%); }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-bubble-typing i,
  .workspace-dot-pulse i,
  .assistant-execution-spinner,
  .assistant-execution-spinner i,
  .assistant-execution-dots i,
  .revision-orbit,
  .revision-orbit i,
  .revision-progress i {
    animation: none;
  }
}

</style>
