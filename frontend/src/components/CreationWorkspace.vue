<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, Plus, Promotion } from '@element-plus/icons-vue'
import MarkdownRender from 'markstream-vue'
import { addProjectComponent, addProjectPermission, archiveProject, batchSaveProjectPages, copyProject, createAiRun, createProject, deleteProject, deleteProjectPage, downloadResource, generateInteractiveModule, generatePresentation, getAiPlan, getAiRun, getProject, getProjectPage, getProjectVersionDiff, listProjectPages, listProjectVersions, listProjects, listResources, modifyPresentation, modifyPresentationSlide, patchProject, recognizeIntent, restoreProject, restoreProjectVersion, reviseProjectWithAi, saveProjectVersion, sendAiSessionAudioMessage, sendAiSessionMessage, streamAiRunEvents, streamGeneralChat, transcribeAudio, updateProjectComponent, validatePresentationHtml, validateProjectComponent } from '../apis/teacher'
import IntentClarificationDialog from './IntentClarificationDialog.vue'
import CreationWorkspaceToolbar from './CreationWorkspaceToolbar.vue'
import WorkspacePropertiesPanel from './WorkspacePropertiesPanel.vue'
import LessonPlanEditor from './LessonPlanEditor.vue'
import VoiceRecorderButton from './VoiceRecorderButton.vue'
import SubjectToolRuntime from './SubjectToolRuntime.vue'
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
const interactiveDialogVisible = ref(false)
const interactivePreviewVisible = ref(false)
const interactiveGenerating = ref(false)
const interactiveModule = ref(null)
const interactivePreviewSource = ref('generated')
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
const interactiveModuleTypes = [
  { value: 'animation', label: '知识动画', description: '用动画演示概念变化与过程' },
  { value: 'quiz_game', label: '问答游戏', description: '适合课堂练习与即时反馈' },
  { value: 'matching_game', label: '匹配游戏', description: '将概念、图示或答案进行配对' },
  { value: 'timeline_game', label: '时间线游戏', description: '按时间或步骤组织互动内容' },
  { value: 'simulation', label: '模拟实验', description: '模拟实验过程与参数变化' },
]
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
const activeRunId = ref('')
const activeRunEventId = ref('')
const runStreamConnected = ref(false)
let activeRunStreamAbort = null
let runStreamReconnectCount = 0
let runStreamReconnectTimer = null
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
const htmlElements = ref([])
const htmlSelectedElementId = ref(null)
const htmlSelectedElement = ref(null)
const htmlSelectionRestoreKey = ref('')
let pendingHtmlPanelSelection = null
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
const versionDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const versionLoading = ref(false)
const versions = ref([])
const versionDiff = ref(null)
const permissionUserId = ref('')
const projectManagerVisible = ref(false)
const projectListLoading = ref(false)
const projectActionLoading = ref(false)
const workspaceProjects = ref([])
const workspaceResources = ref([])
const workspaceResourcesLoading = ref(false)
const workspaceResourceBindingOverride = ref(null)
const contextManagerVisible = ref(false)
const contextManagerIds = ref([])
const contextManagerSaving = ref(false)
const lessonPlanVisible = ref(false)
const lessonPlanDraft = ref(null)
const projectNameDraft = ref('')
const autosaveState = ref('已保存')
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
let autosaveTimer = null
let pageSavePromise = null
let orderSavePromise = null
let localChangeVersion = 0
let localStructureVersion = 0
let savedChangeVersion = 0
let savedStructureVersion = 0
let autosaveQueued = false
let workspaceMessageInstance = null
const showWorkspaceMessage = (type, message) => {
  workspaceMessageInstance?.close()
  workspaceMessageInstance = ElMessage({
    type,
    message,
    offset: 76,
    duration: type === 'error' ? 3200 : 1800,
    showClose: type === 'error',
    grouping: true,
    customClass: 'workspace-message',
  })
  return workspaceMessageInstance
}
const WorkspaceMessage = {
  success: (message) => showWorkspaceMessage('success', message),
  warning: (message) => showWorkspaceMessage('warning', message),
  info: (message) => showWorkspaceMessage('info', message),
  error: (message) => showWorkspaceMessage('error', message),
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
  { id: 'h5', type: 'h5', name: 'H5互动组件', content: '互动问答 H5', html: '', moduleId: '', embedMode: 'standalone', position: { x: 54, y: 64, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#ff6b3f', backgroundColor: '#fff7ed', borderColor: '#fed7aa', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'subject', type: 'subject', name: '学科工具', content: '直角三角形测量工具', subjectType: 'geometry', data: { description: '', parameters: '' }, position: { x: 54, y: 43, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#1f993f', backgroundColor: '#f0fdf4', borderColor: '#bbf7d0', borderWidth: 1, borderRadius: 12, opacity: 100 } },
]
const allElementPresets = [...elementPresets, ...extendedElementPresets]
let elementSequence = 1
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
const messages = reactive([
  {
    role: 'assistant',
    text: '课件已进入创作工作台。你可以先讨论教学思路，也可以直接描述要修改的内容，我会自动判断并应用。',
    includeInContext: false,
    kind: 'welcome',
  },
])
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
const syncHtmlCanvasSource = (slide = current.value) => {
  htmlCanvasSourceSlide.value = slide || null
  htmlCanvasSource.value = slide?.html ? String(slide.html) : ''
}
const htmlCanvasFrameSource = computed(() => {
  if (!current.value?.html) return ''
  const source = htmlCanvasSourceSlide.value === current.value
    ? htmlCanvasSource.value
    : String(current.value.html)
  return withHtmlPageBackground(source, current.value)
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
const routeQueryValue = (value) => Array.isArray(value) ? value[0] : value
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
/** 工作台后续讨论、修改、重新生成和互动组件生成共用的上下文。 */
const workspaceContextPayload = () => {
  const storedContext = presentationMetadata.value?.workspace_context || presentationMetadata.value?.workspaceContext || {}
  const routeContext = {
    ...(storedContext && typeof storedContext === 'object' ? storedContext : {}),
    ...parseJson(routeQueryValue(route.query.workspaceContext), {}),
  }
  const resourceIds = workspaceResourceBindingOverride.value !== null
    ? normalizedResourceIds(workspaceResourceBindingOverride.value)
    : normalizedResourceIds([
      ...queryArrayValue(route.query.resourceIds),
      ...(Array.isArray(routeContext.resourceIds) ? routeContext.resourceIds : []),
      ...(Array.isArray(routeContext.resource_ids) ? routeContext.resource_ids : []),
      ...(Array.isArray(routeContext.bound_materials) ? routeContext.bound_materials : []),
      ...(Array.isArray(routeContext.bind_materials) ? routeContext.bind_materials : []),
      current.value?.background?.resource_id,
      current.value?.background?.resourceId,
      current.value?.backgroundResourceId,
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
  setQualityReport(data.quality_report || data.qualityReport || data.reflection || presentationMetadata.value?.quality_report || presentationMetadata.value?.reflection, 'HTML PPT 生成')
  runStatus.value = 'completed'
  runProgress.value = 100
  runStage.value = 'HTML PPT 已生成'

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
  if (!sessionId.value || projectId.value) return
  const existing = readPresentationDraft(sessionId.value) || {}
  savePresentationDraft(sessionId.value, {
    ...existing,
    presentation_id: presentationId.value || existing.presentation_id || '',
    title: existing.title || slides[0]?.title || 'A12 教学课件',
    slide_count: slides.length,
    request_key: String(routeQueryValue(route.query.pptGeneration) || '') || existing.request_key || null,
    slides,
    metadata: presentationMetadata.value || existing.metadata || null,
    workspace_context: workspaceContextPayload(),
  })
}
const htmlDragTargetSelector = '[data-ppt-element],h1,h2,h3,h4,h5,h6,p,li,img,audio,video,iframe,svg,table,header,main,section,article,aside,footer,figure,div[class],.card,.item,.box,.panel'
const htmlTextTargetSelector = 'h1,h2,h3,h4,h5,h6,p,li,span,strong,em,small,td,th,blockquote'
const htmlSlideHistories = new WeakMap()
const previewFrameObservers = new Set()
const parseCssTranslate = (value) => {
  const numbers = String(value || '').match(/-?\d*\.?\d+/g)?.map(Number) || []
  return { x: Number.isFinite(numbers[0]) ? numbers[0] : 0, y: Number.isFinite(numbers[1]) ? numbers[1] : 0 }
}
const parseCssRotation = (value) => {
  const rotation = Number(String(value || '').match(/-?\d*\.?\d+/)?.[0])
  return Number.isFinite(rotation) ? rotation : 0
}
const serializeHtmlSlide = (document) => {
  const root = document.documentElement.cloneNode(true)
  root.querySelector('#a12-html-drag-style')?.remove()
  root.querySelector('.a12-html-editor-overlay')?.remove()
  root.querySelectorAll('.a12-html-element-proxy').forEach((element) => element.remove())
  root.querySelectorAll('[data-a12-drag-selected]').forEach((element) => element.removeAttribute('data-a12-drag-selected'))
  root.querySelectorAll('[data-a12-html-editing]').forEach((element) => {
    element.removeAttribute('data-a12-html-editing')
    element.removeAttribute('contenteditable')
    element.removeAttribute('spellcheck')
  })
  return `<!DOCTYPE html>\n${root.outerHTML}`
}
const htmlHistoryForSlide = (slide) => {
  if (!htmlSlideHistories.has(slide)) htmlSlideHistories.set(slide, { undo: [], redo: [] })
  return htmlSlideHistories.get(slide)
}
const applyHtmlSlideChange = (slide, nextHtml, { record = true } = {}) => {
  if (!slide || !nextHtml || nextHtml === slide.html) return false
  const history = htmlHistoryForSlide(slide)
  if (record) {
    history.undo.push(slide.html)
    if (history.undo.length > 30) history.undo.shift()
    history.redo.length = 0
  }
  slide.html = nextHtml
  // 编辑操作直接修改了 slide.html，而 iframe 的 srcdoc 使用的是单独的快照。
  // 不同步会导致下一次重绘时重新显示删除前的旧元素。
  if (htmlCanvasSourceSlide.value === slide) syncHtmlCanvasSource(slide)
  markSlideComponentDirty(slide)
  saveCurrentPresentationDraft()
  return true
}
const undoHtmlSlideChange = (slide) => {
  const history = htmlHistoryForSlide(slide)
  const previous = history.undo.pop()
  if (!previous) return false
  history.redo.push(slide.html)
  applyHtmlSlideChange(slide, previous, { record: false })
  return true
}
const redoHtmlSlideChange = (slide) => {
  const history = htmlHistoryForSlide(slide)
  const next = history.redo.pop()
  if (!next) return false
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
const attachHtmlDragEditor = (iframe) => {
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
      right: -1px !important;
      bottom: calc(100% + 9px) !important;
      display: flex !important;
      gap: 4px !important;
      padding: 4px !important;
      border-radius: 7px !important;
      background: #1d4ed8 !important;
      box-shadow: 0 5px 16px rgb(15 23 42 / 24%) !important;
      pointer-events: auto !important;
      white-space: nowrap !important;
      transform: scale(var(--a12-editor-toolbar-scale, 1)) !important;
      transform-origin: bottom right !important;
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
  const panelElementById = new Map()
  const elementPanelId = new WeakMap()
  const elementPanelKey = new WeakMap()
  const h5ElementProxies = new Map()

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
    const normalizedRows = rows.map((row) => Array.isArray(row) ? row.map((cell) => String(cell ?? '')) : [String(row ?? '')])
    element.innerHTML = ''
    const table = document.createElement('table')
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
    element.appendChild(table)
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
    const rect = element.getBoundingClientRect()
    return rect.width > 6 && rect.height > 6
  }
  const collectCandidates = () => [...document.querySelectorAll(htmlDragTargetSelector)].filter(isCandidate)
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
      html: type === 'h5' ? String(element.getAttribute('srcdoc') || element.srcdoc || '') : undefined,
      moduleId: type === 'h5' ? String(element.getAttribute('data-module-id') || '') : undefined,
      embedMode: type === 'h5' ? String(element.getAttribute('data-embed-mode') || 'standalone') : undefined,
      subjectType: type === 'subject' ? String(element.getAttribute('data-subject-type') || 'general') : undefined,
      autoplay: ['audio', 'video'].includes(type) ? Boolean(element.autoplay) : undefined,
      controls: ['audio', 'video'].includes(type) ? element.controls !== false : undefined,
      htmlTag: element.tagName.toLowerCase(),
      htmlKey: key,
      position: {
        x: Number(Math.max(0, x).toFixed(2)),
        y: Number(Math.max(0, y).toFixed(2)),
        width: Number(Math.max(1, (rect.width / width) * 100).toFixed(2)),
        height: Number(Math.max(1, (rect.height / height) * 100).toFixed(2)),
        rotation: Number(parseCssRotation(computed.rotate).toFixed(2)),
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
  }
  const updateOverlay = () => {
    if (!selected?.isConnected) {
      overlay.classList.remove('is-visible')
      overlay.classList.remove('is-h5')
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
    syncH5ElementProxies()
    updateGlobalSelection()
  }
  const clearSelection = ({ preserveRestoreKey = false } = {}) => {
    selected?.removeAttribute('data-a12-drag-selected')
    selected = null
    overlay.classList.remove('is-visible')
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
  const resolveTarget = (target) => {
    if (!(target instanceof frameWindow.Element)) return null
    const chartPart = target.closest?.('[data-a12-chart-part]')
    if (chartPart) {
      const chart = chartPart.closest?.('[data-a12-chart]')
      if (chart) return chart
    }
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
    const changed = applyHtmlSlideChange(slide, serializeHtmlSlide(document))
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
      interaction.nextX = Number((interaction.originX + deltaX).toFixed(2))
      interaction.nextY = Number((interaction.originY + deltaY).toFixed(2))
    }
    if (interaction.type === 'resize') {
      interaction.nextWidth = Number(Math.max(20, interaction.originWidth + deltaX).toFixed(2))
      interaction.nextHeight = Number(Math.max(20, interaction.originHeight + deltaY).toFixed(2))
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
    if (event.target.closest?.('.a12-html-editor-overlay') || event.target.closest?.('[data-a12-html-editing]')) return
    const element = resolveTarget(event.target)
    if (!element) {
      clearSelection()
      return
    }
    select(element)
    const origin = parseCssTranslate(frameWindow.getComputedStyle(element).translate)
    interaction = {
      type: 'move',
      element,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: origin.x,
      originY: origin.y,
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
    interaction = {
      type: 'move',
      element: selected,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: origin.x,
      originY: origin.y,
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
    h5Elements.forEach((element) => {
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
    const startAngle = Math.atan2(event.clientY - (rect.top + rect.height / 2), event.clientX - (rect.left + rect.width / 2)) * 180 / Math.PI
    interaction = {
      type,
      element: selected,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originWidth: rect.width,
      originHeight: rect.height,
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
    const element = event.target.closest?.(htmlTextTargetSelector)
    if (!element || element.closest('.a12-html-editor-overlay')) return
    select(element)
    editing = { element, originalHtml: element.innerHTML }
    element.setAttribute('contenteditable', 'true')
    element.setAttribute('spellcheck', 'false')
    element.setAttribute('data-a12-html-editing', '')
    element.focus()
    const selection = frameWindow.getSelection()
    selection?.selectAllChildren(element)
    selection?.collapseToEnd()
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
  const copySelected = () => {
    if (!selected) return
    const clone = selected.cloneNode(true)
    clone.removeAttribute('data-a12-drag-selected')
    clone.removeAttribute('data-a12-html-editing')
    clone.removeAttribute('contenteditable')
    clone.removeAttribute('spellcheck')
    clone.removeAttribute('id')
    clone.setAttribute('data-ppt-element', `copy-${Date.now()}`)
    const origin = parseCssTranslate(frameWindow.getComputedStyle(selected).translate)
    clone.style.translate = `${origin.x + 18}px ${origin.y + 18}px`
    selected.after(clone)
    refreshElements()
    select(clone)
    commitDocument()
  }
  const runHistoryAction = (action) => {
    if (selected?.isConnected) htmlSelectionRestoreKey.value = elementPanelKey.get(selected) || ''
    const changed = action(slide)
    if (changed) syncHtmlCanvasSource(slide)
    return changed
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
    if (editing && modifier && event.key === 'Enter') {
      event.preventDefault()
      finishTextEditing(true)
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
      if (type === 'h5') {
        const titleNode = selected.contentDocument?.querySelector('title')
        if (titleNode) titleNode.textContent = content
      }
    } else if (type === 'table') {
      selected.setAttribute('data-name', content)
    }
    else selected.textContent = content
    updateOverlay()
    commitDocument()
    return true
  }
  const updateField = (key, value) => {
    if (!selected?.isConnected || !['src', 'alt', 'url', 'html', 'moduleId', 'embedMode', 'subjectType', 'autoplay', 'controls'].includes(key)) return false
    const type = elementType(selected)
    if (key === 'src' && ['image', 'audio', 'video'].includes(type)) selected.setAttribute('src', String(value || ''))
    if (key === 'alt' && type === 'image') selected.setAttribute('alt', String(value || '').slice(0, 80))
    if (key === 'url' && ['audio', 'video'].includes(type)) selected.setAttribute('src', String(value || ''))
    if (key === 'html' && type === 'h5') selected.setAttribute('srcdoc', String(value || ''))
    if (key === 'moduleId' && type === 'h5') selected.setAttribute('data-module-id', String(value || ''))
    if (key === 'embedMode' && type === 'h5') selected.setAttribute('data-embed-mode', String(value || 'standalone'))
    if (key === 'subjectType' && type === 'subject') selected.setAttribute('data-subject-type', String(value || 'general'))
    if (key === 'autoplay' && ['audio', 'video'].includes(type)) selected.autoplay = Boolean(value)
    if (key === 'controls' && ['audio', 'video'].includes(type)) selected.controls = Boolean(value)
    updateOverlay()
    commitDocument()
    return true
  }
  const updateData = (value) => {
    if (!selected?.isConnected) return false
    const type = elementType(selected)
    if (type === 'chart' && Array.isArray(value)) renderHtmlChart(selected, value)
    else if (type === 'table' && Array.isArray(value)) renderHtmlTable(selected, value)
    else if (type === 'subject' && value && typeof value === 'object' && !Array.isArray(value)) selected.setAttribute('data-subject-data', JSON.stringify(value))
    else return false
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
    const tagName = { image: 'img', audio: 'audio', video: 'video', h5: 'iframe', table: 'div' }[type] || 'div'
    const node = document.createElement(tagName)
    const id = `a12-${type}-${Date.now()}`
    node.setAttribute('data-ppt-element', id)
    node.setAttribute('data-ppt-type', type)
    node.style.position = 'absolute'
    node.style.boxSizing = 'border-box'
    node.style.left = type === 'chart' ? `${62 + (index % 2) * 4}%` : `${10 + (index % 5) * 5}%`
    node.style.top = type === 'chart' ? `${10 + (index % 3) * 6}%` : `${12 + (index % 4) * 7}%`
    node.style.width = type === 'text' ? '28%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : type === 'table' ? '42%' : ['video', 'h5'].includes(type) ? '36%' : '30%'
    node.style.height = type === 'text' ? '12%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : type === 'table' ? '20%' : ['video', 'h5'].includes(type) ? '24%' : '14%'
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
      node.setAttribute('sandbox', 'allow-scripts')
      node.setAttribute('title', '新增 H5 互动')
      node.srcdoc = '<!doctype html><html lang="zh-CN"><body style="margin:0;display:grid;place-items:center;height:100vh;font:16px sans-serif;color:#c2410c;background:#fff7ed">请在右侧编辑或粘贴 H5 内容</body></html>'
      node.style.border = '1px solid #fed7aa'
      node.style.borderRadius = '12px'
    } else if (type === 'subject') {
      node.setAttribute('data-name', '新增学科工具')
      node.setAttribute('data-subject-type', 'general')
      node.setAttribute('data-subject-data', JSON.stringify({ description: '', parameters: '' }))
      node.textContent = '新增学科工具 · 可在右侧配置'
      node.style.padding = '16px'
      node.style.color = '#166534'
      node.style.backgroundColor = '#f0fdf4'
      node.style.border = '1px solid #bbf7d0'
    }
    document.body.appendChild(node)
    refreshElements()
    select(node)
    commitDocument()
    return true
  }
  const insertInteractive = (module) => {
    if (!isCurrentSlide() || !module?.html) return false
    const index = htmlElements.value.length
    const node = document.createElement('iframe')
    node.setAttribute('data-ppt-element', `a12-h5-${module.module_id || module.moduleId || Date.now()}`)
    node.setAttribute('data-ppt-type', 'h5')
    node.setAttribute('data-name', module.title || '互动模块')
    node.setAttribute('sandbox', 'allow-scripts')
    node.setAttribute('title', module.title || '互动模块')
    node.srcdoc = String(module.html)
    node.style.position = 'absolute'
    node.style.boxSizing = 'border-box'
    node.style.left = `${8 + (index % 3) * 7}%`
    node.style.top = `${36 + (index % 2) * 8}%`
    node.style.width = '42%'
    node.style.height = '42%'
    node.style.zIndex = '12'
    node.style.border = '1px solid #fed7aa'
    node.style.borderRadius = '12px'
    document.body.appendChild(node)
    refreshElements()
    select(node)
    commitDocument()
    return true
  }

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
    updateData,
    updatePageField,
    insertElement,
    insertInteractive,
    copySelected: (id) => { const element = findElement(id); if (element) { select(element); copySelected() } },
    deleteSelected: (id) => { const element = findElement(id); if (element) { select(element); deleteSelected() } },
  }
  const cleanup = () => {
    document.removeEventListener('pointerdown', handlePointerDown)
    document.removeEventListener('pointermove', handlePointerMove)
    document.removeEventListener('pointerup', finishInteraction)
    document.removeEventListener('pointercancel', finishInteraction)
    document.removeEventListener('dblclick', handleDoubleClick)
    document.removeEventListener('keydown', handleKeydown)
    document.removeEventListener('blur', handleDocumentBlur, true)
    moveHandle.removeEventListener('pointerdown', beginMoveInteraction)
    if (interaction?.animationFrame) frameWindow.cancelAnimationFrame(interaction.animationFrame)
    selected?.removeAttribute('data-a12-drag-selected')
    h5ElementProxies.forEach((proxy) => proxy.remove())
    h5ElementProxies.clear()
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
  const editorCleanup = attachHtmlDragEditor(iframe)
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
    htmlFrameObservers.add({ iframe, observer: null, cleanup, controller, slide: current.value })
    if (pendingHtmlPanelSelection?.slide === current.value && controller?.selectById?.(pendingHtmlPanelSelection.id)) pendingHtmlPanelSelection = null
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  htmlFrameObservers.add({ iframe, observer, cleanup, controller, slide: current.value })
  if (pendingHtmlPanelSelection?.slide === current.value && controller?.selectById?.(pendingHtmlPanelSelection.id)) pendingHtmlPanelSelection = null
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
const closePreview = () => {
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
      shapeKind: element?.shapeKind || element?.shape_kind || element?.shapeType || element?.variant || preset.shapeKind,
      src: element?.src || element?.url || element?.image_url || preset.src || (type === 'image' ? createMockImageSrc() : undefined),
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
const selectedElementPanel = computed(() => {
  const element = selectedElement.value
  return element ? { ...element, content: elementContent(element), position: { ...(element.position || {}) }, style: { ...(element.style || {}) } } : null
})
const activeHtmlController = () => [...htmlFrameObservers].find((item) => item.slide === current.value && item.controller)?.controller || null
const workspaceElements = computed(() => current.value?.html ? htmlElements.value : current.value?.elements || [])
const workspaceSelectedElement = computed(() => current.value?.html ? htmlSelectedElement.value : selectedElementPanel.value)
const workspaceSelectedElementId = computed(() => current.value?.html ? htmlSelectedElementId.value : selectedElementId.value)
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
  if (event.button !== 0) return
  if (placementMode.value) {
    event.stopPropagation()
    return
  }
  const element = elementById(id)
  const canvas = event.currentTarget?.closest('.slide-canvas')
  if (!element || !canvas) return
  const rect = canvas.getBoundingClientRect()
  dragState.value = {
    id,
    rect,
    startX: event.clientX,
    startY: event.clientY,
    startPosition: { ...(element.position || {}) },
  }
  draggingElementId.value = id
  selectElement(id, event)
  window.addEventListener('pointermove', handleElementDrag)
  window.addEventListener('pointerup', stopElementDrag, { once: true })
  event.preventDefault()
}
const handleElementDrag = (event) => {
  const state = dragState.value
  const element = state ? elementById(state.id) : null
  if (!state || !element) return
  const width = Number(state.startPosition.width || 20)
  const height = Number(state.startPosition.height || 20)
  const nextX = Number(state.startPosition.x || 0) + ((event.clientX - state.startX) / state.rect.width) * 100
  const nextY = Number(state.startPosition.y || 0) + ((event.clientY - state.startY) / state.rect.height) * 100
  element.position = {
    ...element.position,
    x: Number(clampNumber(nextX, 0, 100 - width).toFixed(2)),
    y: Number(clampNumber(nextY, 0, 100 - height).toFixed(2)),
  }
}
const stopElementDrag = () => {
  if (dragState.value?.id && current.value) markSlideComponentDirty(current.value, dragState.value.id)
  window.removeEventListener('pointermove', handleElementDrag)
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
  if (current.value?.html) {
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
  if (current.value?.html) activeHtmlController()?.clearSelection()
  selectedElementId.value = null
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
}
const updatePageField = ({ key, value } = {}) => {
  if (!current.value || !['title', 'notes', 'pageType', 'backgroundColor'].includes(key)) return
  const nextValue = String(value ?? '')
  if (current.value.html && ['title', 'description'].includes(key)) activeHtmlController()?.updatePageField?.(key, nextValue)
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
  markSlideComponentDirty(current.value, 'page:theme')
}
const updatePageLayout = (layout) => {
  if (!current.value) return
  current.value.layout = String(layout || '') || '图文并置'
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
  if (current.value?.html) {
    activeHtmlController()?.updateStyle(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value) return
  selectedElement.value.style = { ...selectedElement.value.style, [key]: value }
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementPosition = ({ key, value }) => {
  if (current.value?.html) {
    activeHtmlController()?.updatePosition(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value) return
  const numericValue = Number(value)
  const position = { ...selectedElement.value.position, [key]: Number.isFinite(numericValue) ? numericValue : 0 }
  const width = clampNumber(Number(position.width) || 4, 4, 100)
  const height = clampNumber(Number(position.height) || 4, 4, 100)
  selectedElement.value.position = {
    ...position,
    width,
    height,
    x: Number(clampNumber(Number(position.x) || 0, 0, 100 - width).toFixed(2)),
    y: Number(clampNumber(Number(position.y) || 0, 0, 100 - height).toFixed(2)),
    rotation: Number(clampNumber(Number(position.rotation) || 0, -180, 180).toFixed(2)),
    zIndex: Math.round(clampNumber(Number(position.zIndex) || 0, 0, 99)),
  }
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementContent = (value) => {
  if (current.value?.html) {
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
  if (current.value?.html) {
    activeHtmlController()?.updateField(key, value)
    markSlideComponentDirty()
    return
  }
  if (!selectedElement.value || !['src', 'alt', 'url', 'html', 'moduleId', 'embedMode', 'subjectType', 'autoplay', 'controls'].includes(key)) return
  if (key === 'src') selectedElement.value.src = String(value || '') || createMockImageSrc(selectedElement.value.content || '课堂图片')
  if (key === 'alt') selectedElement.value.alt = String(value || '').slice(0, 80)
  if (key === 'url') {
    selectedElement.value.url = String(value || '')
    if (['audio', 'video'].includes(selectedElement.value.type)) selectedElement.value.src = selectedElement.value.url
  }
  if (key === 'html') selectedElement.value.html = String(value || '')
  if (key === 'moduleId') { selectedElement.value.moduleId = String(value || ''); selectedElement.value.module_id = String(value || '') }
  if (key === 'embedMode') { selectedElement.value.embedMode = String(value || 'standalone'); selectedElement.value.embed_mode = selectedElement.value.embedMode }
  if (key === 'subjectType') selectedElement.value.subjectType = String(value || '')
  if (key === 'autoplay' || key === 'controls') selectedElement.value[key] = Boolean(value)
  markSlideComponentDirty(current.value, selectedElement.value.id)
}
const updateElementData = (value) => {
  if (current.value?.html) {
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
    selectedElement.value.data = { ...(selectedElement.value.data || {}), ...value }
  } else return
  markSlideComponentDirty(current.value, selectedElement.value.id)
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
  if (type === 'h5') element.content = '新增 H5 互动'
  if (type === 'subject') element.content = '新增学科工具'
  element.position = { ...element.position, ...positionOverride }
  return element
}
const insertElement = (type, options = {}, positionOverride = {}, preparedElement = null) => {
  if (!current.value) return
  const element = preparedElement ? cloneElementData(preparedElement) : createElement(type, options)
  element.position = { ...(element.position || {}), ...positionOverride }
  current.value.elements.push(element)
  selectedElementId.value = element.id
  markSlideComponentDirty(current.value, element.id)
  WorkspaceMessage.success(`${elementTypeLabels[type] || '元素'}已添加`)
}
const handleToolSelect = (tool) => {
  if (current.value?.html) {
    const inserted = activeHtmlController()?.insertElement(tool?.id || tool, tool || {})
    activeTool.value = ''
    if (!inserted) WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
    return
  }
  beginElementPlacement(tool)
}
const interactiveAssetFromModule = (module) => ({
  module_id: module?.module_id || module?.moduleId,
  title: module?.title || module?.name || module?.content || '互动模块',
  module_type: module?.module_type || module?.moduleType || 'animation',
  topic: module?.topic || '',
  html: module?.html || '',
  embed_mode: module?.embed_mode || module?.embedMode || 'standalone',
  usage_suggestions: Array.isArray(module?.usage_suggestions) ? module.usage_suggestions : (module?.usageSuggestions || []),
  metadata: module?.metadata || {},
})
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
  const moduleId = String(module?.module_id || module?.moduleId || `interactive_${Date.now()}`)
  return {
    id: `h5-${moduleId}`,
    type: 'h5',
    name: module?.title || '互动模块',
    content: module?.title || '互动模块',
    html: module?.html || '',
    moduleId,
    module_id: moduleId,
    moduleType: module?.module_type || module?.moduleType || 'animation',
    topic: module?.topic || '',
    embedMode: module?.embed_mode || module?.embedMode || 'standalone',
    usageSuggestions: Array.isArray(module?.usage_suggestions) ? module.usage_suggestions : (module?.usageSuggestions || []),
    metadata: module?.metadata || {},
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
const openInteractiveDialog = () => {
  const slideTitle = String(current.value?.title || '本页内容').trim()
  const pptContext = interactivePptContext()
  interactiveForm.title = `${slideTitle} · 课堂互动`
  interactiveForm.topic = slideTitle
  interactiveForm.subject = pptContext.subject
  interactiveForm.grade = pptContext.grade
  interactiveForm.knowledge_points = String(current.value?.description || '').trim()
  interactiveForm.requirements = pptContext.requirements
  interactiveForm.theme = theme.value?.name || ''
  interactiveForm.embed_mode = 'standalone'
  interactiveDialogVisible.value = true
}
const handleGenerateInteractiveModule = async () => {
  const title = interactiveForm.title.trim()
  const topic = interactiveForm.topic.trim()
  if (!title || !topic) return WorkspaceMessage.warning('请先填写互动模块标题和主题')
  interactiveGenerating.value = true
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
    if (!response?.html) throw new Error('互动模块接口未返回可预览的 HTML 内容')
    if (response?.metadata?.model_used !== true) throw new Error('互动模块未由真实模型生成，请检查模型服务配置后重试')
    interactiveModule.value = response
    interactivePreviewSource.value = 'generated'
    interactiveDialogVisible.value = false
    interactivePreviewVisible.value = true
    WorkspaceMessage.success('互动模块已生成')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '互动模块生成失败')
  } finally {
    interactiveGenerating.value = false
  }
}
const previewInteractiveElement = (element) => {
  if (!element?.html) return WorkspaceMessage.warning('该互动组件没有可预览内容')
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
const reopenInteractiveDialog = () => {
  interactivePreviewVisible.value = false
  interactiveDialogVisible.value = true
}
const insertGeneratedInteractiveModule = (target = 'current') => {
  if (!interactiveModule.value?.html) return WorkspaceMessage.warning('请先生成互动模块')
  const module = interactiveModule.value
  const element = createInteractiveElement(module, target === 'new-page' ? { x: 10, y: 43, width: 80, height: 43 } : {})
  if (target === 'new-page') {
    const newSlide = {
      ...defaultSlide(slides.length + 1),
      title: module.title || '互动模块',
      eyebrow: '互动模块 · 独立页面',
      description: module.topic || '可独立运行的课堂互动模块。',
      layout: '重点陈述',
      theme: current.value?.theme || 'blue',
      elements: [element],
      interactive_assets: [],
      dirty: true,
    }
    appendInteractiveAsset(newSlide, module)
    slides.splice(selectedSlide.value + 1, 0, newSlide)
    selectedSlide.value += 1
    selectedElementId.value = element.id
    markSlideComponentDirty(newSlide, 'page:add-interactive', { structure: true })
    WorkspaceMessage.success('互动模块已作为独立页面插入，正在自动保存')
  } else {
    if (current.value?.html) {
      const inserted = activeHtmlController()?.insertInteractive?.(module)
      if (!inserted) return WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
    appendInteractiveAsset(current.value, module)
      markSlideComponentDirty(current.value, htmlSelectedElementId.value)
      interactivePreviewVisible.value = false
      interactiveModule.value = null
      WorkspaceMessage.success('互动模块已插入当前 HTML 页面，正在自动保存')
      return
    }
    current.value.elements.push(element)
    appendInteractiveAsset(current.value, module)
    selectedElementId.value = element.id
    markSlideComponentDirty(current.value, element.id)
    WorkspaceMessage.success('互动模块已插入当前页面，正在自动保存')
  }
  interactivePreviewVisible.value = false
  interactiveModule.value = null
}
const removeElement = (id = selectedElementId.value) => {
  if (current.value?.html) {
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
  if (current.value?.html) {
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
  if (current.value.html) {
    if (typeof html !== 'string' || !html.trim()) return false
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
const syncProjectMetadataIfNeeded = async () => {
  const requestedName = String(route.query.templateTitle || '').trim()
  if (!projectId.value || !project.value || !requestedName || requestedName === project.value.project_name) return
  try {
    const response = unwrapResponse(await patchProject(projectId.value, {
      project_name: requestedName,
      project_type: project.value.project_type || 'mixed',
      status: 'editing',
      current_version: Number(project.value.current_version || 1),
    }))
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
    const updated = unwrapResponse(await patchProject(projectId.value, {
      edit_history: JSON.stringify(nextHistory),
      current_version: Number(project.value.current_version || 1),
    }))
    project.value = { ...project.value, ...(updated || {}), edit_history: updated?.edit_history || JSON.stringify(nextHistory) }
    presentationMetadata.value = { ...(presentationMetadata.value || {}), workspace_context: context }
  } catch (error) {
    WorkspaceMessage.warning(workspaceRequestErrorMessage(error, '工作台上下文同步失败，当前页面仍可编辑'))
  }
}
const openLessonPlanEditor = () => {
  if (!slides.length) return WorkspaceMessage.warning('当前还没有可生成教案的页面')
  lessonPlanVisible.value = true
}
const saveLessonPlanDraft = async (plan) => {
  const nextPlan = parseJson(JSON.stringify(plan || {}), {})
  lessonPlanDraft.value = nextPlan
  presentationMetadata.value = { ...(presentationMetadata.value || {}), lesson_plan: nextPlan }
  if (!projectId.value || !project.value) {
    WorkspaceMessage.success('教案已暂存在当前工作台')
    return
  }
  const history = parseJson(project.value.edit_history, {})
  const nextHistory = Array.isArray(history)
    ? { entries: history, lesson_plan: nextPlan, workspace_context: workspaceContextPayload() }
    : { ...(history && typeof history === 'object' ? history : {}), lesson_plan: nextPlan, workspace_context: workspaceContextPayload() }
  try {
    const updated = unwrapResponse(await patchProject(projectId.value, {
      edit_history: JSON.stringify(nextHistory),
      current_version: Number(project.value.current_version || 1),
    }))
    project.value = { ...project.value, ...(updated || {}), edit_history: updated?.edit_history || JSON.stringify(nextHistory) }
    autosaveState.value = '已保存 · 教案已同步'
    WorkspaceMessage.success('教案已保存到项目')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '教案保存失败，已保留在当前页面')
  }
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
  if (element.type === 'subject' || (element.type === 'shape' && element.shapeKind === 'formula-diagram')) {
    return { ...common, type: 'geometry', data: { construction: elementContent(element) || 'right_triangle', commands: ['draw_right_triangle'] } }
  }
  return null
}
const validateSlideComponents = async (slide) => {
  const components = (slide?.elements || []).map(componentValidationPayload).filter(Boolean)
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
const componentsPayloadForSlide = (slide) => (slide?.elements || []).map((element) => (
  componentValidationPayload(element) || element
))
const pagePayloadForSlide = (slide, index, overrides = {}) => {
  const { includePageOrder = true, ...payloadOverrides } = overrides
  return {
    ...(includePageOrder ? { page_order: index + 1 } : {}),
    page_type: slide.pageType || slide.page_type || (index === 0 ? 'cover' : 'content'),
    page_title: slide.title,
    page_content: JSON.stringify(slide),
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
      project_type: 'mixed',
      status: 'editing',
      edit_history: JSON.stringify({ workspace_context: workspaceContextPayload() }),
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
const assistantIntentHint = computed(() => {
  if (intentSubmitting.value) return 'AI 正在判断这条消息是讨论还是页面操作…'
  if (revisionSubmitting.value) return '正在执行页面修改，请稍候…'
  if (discussionSubmitting.value) return '正在思考讨论内容，请稍候…'
  if (!prompt.value.trim()) return 'AI 会根据你的表达自动判断：讨论或执行页面修改'
  return inferredAssistantMode.value === 'revision'
    ? '检测到页面操作，发送时由 AI 结合上下文确认'
    : '发送时由 AI 结合上下文判断是否修改页面'
})
const assistantStatusText = computed(() => {
  if (workspaceVoiceSubmitting.value) return '正在上传语音并续接 AI 会话…'
  if (intentSubmitting.value) return 'AI 正在判断意图…'
  if (discussionSubmitting.value) return 'AI 正在思考…'
  if (revisionSubmitting.value) return revisionStage.value || 'AI 正在执行页面修改…'
  return 'AI 自动判断 · Enter 发送 · Shift + Enter 换行'
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
const inferredAssistantMode = computed(() => inferAssistantMode(prompt.value))
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
  const intentSessionId = String(sessionId.value || '').trim()
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
const persistActiveRun = () => {
  if (!sessionId.value || !activeRunId.value) return
  sessionStorage.setItem(runStorageKey(), JSON.stringify({
    runId: activeRunId.value,
    lastEventId: activeRunEventId.value || '',
    updatedAt: Date.now(),
  }))
}
const clearActiveRun = () => {
  clearTimeout(runStreamReconnectTimer)
  runStreamReconnectTimer = null
  runStreamReconnectCount = 0
  if (sessionId.value) sessionStorage.removeItem(runStorageKey())
  activeRunId.value = ''
  activeRunEventId.value = ''
  runStreamConnected.value = false
}
const resetRunObservability = () => {
  runTimeline.value = []
  runToolCalls.value = []
  runRetrievalSources.value = []
  runReflection.value = null
  runRecoveryNode.value = ''
  runFailureReason.value = ''
}
const arrayValue = (value) => {
  const parsed = parseJson(value, value)
  if (Array.isArray(parsed)) return parsed
  if (parsed && typeof parsed === 'object') return Object.entries(parsed).map(([key, item]) => ({ key, ...(item && typeof item === 'object' ? item : { value: item }) }))
  return []
}
const runItemText = (item, fallback = '') => String(
  item?.message
  || item?.description
  || item?.label
  || item?.title
  || item?.name
  || item?.step_name
  || item?.step
  || item?.key
  || fallback,
).trim()
const runStatusLabel = (status = '') => ({
  pending: '等待', queued: '排队中', running: '执行中', executing: '执行中', processing: '处理中',
  success: '已完成', completed: '已完成', done: '已完成', failed: '失败', error: '失败',
  waiting_for_python_api: '等待生成服务',
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
const updateRunObservability = (task = {}, eventId = '') => {
  const steps = arrayValue(task?.exec_steps || task?.execution_steps || task?.steps)
  const stepTimeline = steps.map((step, index) => ({
    id: String(step?.id || step?.step_id || `${step?.step || step?.name || 'step'}-${index}`),
    kind: 'step',
    label: runItemText(step, `执行步骤 ${index + 1}`),
    status: String(step?.status || 'pending').toLowerCase(),
    statusLabel: runStatusLabel(step?.status),
    detail: String(step?.detail || step?.result || step?.output || '').trim(),
  }))
  const events = arrayValue(task?.events || task?.timeline || task?.execution_trace)
  const eventTimeline = events.map((event, index) => ({
    id: String(event?.id || event?.event_id || `event-${index}`),
    kind: 'event',
    label: runItemText(event, 'Agent 事件'),
    status: String(event?.status || event?.state || 'record').toLowerCase(),
    statusLabel: runStatusLabel(event?.status || event?.state),
    detail: String(event?.detail || event?.output || event?.content || '').trim(),
  }))
  const currentLabel = runItemText(task?.current_step || task?.stage || task?.event || task?.message)
  const currentEvent = currentLabel ? [{
    id: String(eventId || task?.event_id || `current-${currentLabel}`),
    kind: 'event',
    label: currentLabel,
    status: String(task?.status || 'running').toLowerCase(),
    statusLabel: runStatusLabel(task?.status || 'running'),
    detail: String(task?.event_detail || task?.detail || '').trim(),
  }] : []
  const merged = [...stepTimeline, ...eventTimeline, ...currentEvent]
  const seen = new Set()
  runTimeline.value = merged.filter((item) => {
    if (seen.has(item.id)) return false
    seen.add(item.id)
    return true
  }).slice(-30)

  const toolTrace = arrayValue(task?.tool_calls || task?.tool_trace || task?.tools || task?.tool_invocations || task?.last_tool)
  runToolCalls.value = toolTrace.map((tool, index) => ({
    id: String(tool?.id || tool?.tool_call_id || `${tool?.name || 'tool'}-${index}`),
    name: String(tool?.name || tool?.tool_name || tool?.tool || tool?.key || '工具调用'),
    status: runStatusLabel(tool?.status || tool?.state || 'completed'),
    detail: String(tool?.message || tool?.input_summary || tool?.output_summary || tool?.result || '').trim(),
  })).slice(-20)

  const retrieval = task?.rag_sources || task?.retrieval_sources || task?.retrieval || task?.used_resources || task?.resources || task?.rag?.sources
  runRetrievalSources.value = arrayValue(retrieval).map((resource, index) => ({
    id: String(resource?.id || resource?.resource_id || resource?.file_id || `resource-${index}`),
    name: String(resource?.name || resource?.file_name || resource?.filename || resource?.title || `资料 ${index + 1}`),
    detail: String(resource?.chunk || resource?.snippet || resource?.description || resource?.score || '').trim(),
  })).slice(0, 30)
  const reflection = task?.reflections || task?.reflection || task?.self_reflection || task?.quality_report || task?.qualityReport
  const normalizedReflection = normalizeRunReflection(reflection)
  if (normalizedReflection) runReflection.value = normalizedReflection
  runRecoveryNode.value = String(task?.recovery_node || task?.recoveryNode || task?.recovery_step || task?.next_step || task?.resume_from || '').trim()
  runFailureReason.value = String(task?.error_message || task?.error || task?.failure_reason || task?.reason || '').trim()
  const progress = Number(task?.progress ?? task?.percentage ?? task?.percent ?? task?.progress_value)
  if (Number.isFinite(progress)) runProgress.value = Math.max(0, Math.min(100, Math.round(progress <= 1 ? progress * 100 : progress)))
  if (currentLabel) runStage.value = currentLabel
}
const applyRunEvent = (payload, eventId = '') => {
  if (eventId) activeRunEventId.value = String(eventId)
  const task = payload?.data && typeof payload.data === 'object' ? payload.data : payload
  updateRunObservability(task, eventId)
  setQualityReport(task?.reflections || task?.reflection || task?.quality_report || task?.qualityReport, 'AI 生成任务')
  const status = String(task?.status || '').toLowerCase()
  const steps = Array.isArray(task?.exec_steps) ? task.exec_steps : parseJson(task?.exec_steps, [])
  const pendingStep = steps.find((item) => ['running', 'processing', 'waiting_for_python_api'].includes(String(item?.status || '').toLowerCase()))
  if (pendingStep?.step === 'presentation_generate') runStage.value = '任务已创建，正在调用 HTML PPT 生成服务'
  if (status === 'executing') runStatus.value = 'running'
  if (status === 'failed') {
    runStatus.value = 'failed'
    generationError.value = task?.error_message || task?.failure_reason || '课件生成任务失败'
  }
  if (['completed', 'success', 'done'].includes(status)) {
    runStatus.value = 'completed'
    runProgress.value = 100
  }
  persistActiveRun()
}
const readRunEventStream = async (response) => {
  if (!response.ok) throw new Error(`任务事件连接失败（HTTP ${response.status}）`)
  const reader = response.body?.getReader?.()
  if (!reader) return
  const decoder = new TextDecoder()
  let buffer = ''
  const consume = (raw) => {
    const lines = raw.split(/\r?\n/)
    let eventId = ''
    let data = ''
    for (const line of lines) {
      if (line.startsWith('id:')) eventId = line.slice(3).trim()
      if (line.startsWith('data:')) data += line.slice(5).trim()
    }
    if (!data) return
    try { applyRunEvent(JSON.parse(data), eventId) } catch { /* 忽略网关心跳或非 JSON 事件 */ }
  }
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    blocks.forEach(consume)
    if (done) break
  }
  if (buffer.trim()) consume(buffer)
}
const subscribeRunEvents = async () => {
  if (!activeRunId.value) return
  activeRunStreamAbort?.abort()
  const controller = new AbortController()
  activeRunStreamAbort = controller
  runStreamConnected.value = true
  try {
    const response = await streamAiRunEvents(activeRunId.value, activeRunEventId.value, { signal: controller.signal })
    await readRunEventStream(response)
  } catch (error) {
    if (error?.name !== 'AbortError') {
      runStage.value = runStage.value || '任务连接短暂中断，正在续接…'
      if (runStreamReconnectCount < 3 && activeRunId.value) {
        runStreamReconnectCount += 1
        clearTimeout(runStreamReconnectTimer)
        runStreamReconnectTimer = setTimeout(() => { void subscribeRunEvents() }, 1200 * runStreamReconnectCount)
      }
    }
  } finally {
    if (activeRunStreamAbort === controller) activeRunStreamAbort = null
    runStreamConnected.value = false
  }
}
const startTrackedRun = async () => {
  const task = unwrapResponse(await createAiRun(sessionId.value)) || {}
  activeRunId.value = String(task.id || task.task_id || task.run_id || '')
  if (!activeRunId.value) throw new Error('执行任务创建成功但未返回任务编号')
  // 创建后立即回读一次，保证工作台展示的是服务端任务状态而非前端假进度。
  applyRunEvent(unwrapResponse(await getAiRun(activeRunId.value)) || task)
  persistActiveRun()
  void subscribeRunEvents()
}
const restoreTrackedRun = async () => {
  if (!sessionId.value || activeRunId.value) return
  const saved = parseJson(sessionStorage.getItem(runStorageKey()), null)
  if (!saved?.runId) return
  activeRunId.value = String(saved.runId)
  activeRunEventId.value = String(saved.lastEventId || '')
  try {
    const task = unwrapResponse(await getAiRun(activeRunId.value))
    applyRunEvent(task)
    if (String(task?.status || '').toLowerCase() === 'executing') void subscribeRunEvents()
    else clearActiveRun()
  } catch {
    clearActiveRun()
  }
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
  runProgress.value = 6
  runStage.value = '正在读取已确认的大纲'

  try {
    await startTrackedRun()
    // 本地开发时 Java 会话仍为 mock，真实 Python 大纲会保存在本地快照中；
    // 优先读取该快照，避免进入工作台后又退回固定/空的大纲。
    const localOutlineDraft = readOutlineDraft(sessionId.value)
    const planData = localOutlineDraft?.plan_json
      ? localOutlineDraft
      : (unwrapResponse(await getAiPlan(sessionId.value)) || {})
    const outline = {
      ...normalizeOutlinePayload(planData),
      workspace_context: workspaceContextPayload(),
    }
    if (!Object.keys(outline).length) throw new Error('未找到已确认的大纲，请返回对话重新确认')

    runProgress.value = 20
    runStage.value = '正在调用 HTML PPT 生成服务'
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
      asset_policy: 'placeholder',
    }
    const response = await generatePresentation(payload)
    runProgress.value = 88
    runStage.value = '正在校验 HTML 页面'
    const generated = normalizePresentationSlides(getPresentationPayload(response))
    await validateGeneratedSlides(generated)
    runStage.value = '正在装载 HTML 页面'
    applyGeneratedPresentation(response)
    // 从会话进入工作台的课件不能只留在浏览器草稿：生成成功即创建项目与页面，
    // 后续刷新、退出和版本管理均以服务端项目为准。
    runStage.value = '正在保存课件项目'
    await persistGeneratedPresentationProject()
    runStage.value = 'HTML PPT 已生成并保存'
    clearActiveRun()
  } catch (error) {
    runStatus.value = 'failed'
    runProgress.value = 0
    runStage.value = 'HTML PPT 生成失败'
    generationError.value = generationErrorMessage(error)
    messages.push({ role: 'assistant', text: generationError.value, includeInContext: false, kind: 'generation-error' })
    WorkspaceMessage.error(generationError.value)
    clearActiveRun()
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
  const sourceSlide = current.value?.html
    ? current.value
    : slides.find((slide) => String(slide?.html || '').trim())
  let generatedSlide = null

  // 新增页面只调用单页接口生成新页，绝不把整套 slides 交给整套修改接口。
  // 这样 AI 即使重新生成了新增页，也不会有机会覆盖原来的页面。
  if (sourceSlide?.html) {
    try {
      const sourceIndex = Math.max(0, slides.indexOf(sourceSlide))
      const response = unwrapResponse(await modifyPresentationSlide({
        ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
        slide_no: sourceIndex + 1,
        current_html: sourceSlide.html,
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
  if (!slides.length || !slides.every((slide) => String(slide?.html || '').trim())) {
    throw new Error('当前课件包含不可编辑页面，暂不能执行整套 HTML 修改')
  }
  revisionStage.value = '正在规划整套课件修改…'
  const localOutlineDraft = sessionId.value ? readOutlineDraft(sessionId.value) : null
  const response = unwrapResponse(await modifyPresentation({
    ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
    title: String(project.value?.project_name || route.query.templateTitle || slides[0]?.title || 'A12 教学课件'),
    slides: slides.map((slide, index) => ({
      slide_no: index + 1,
      ...(slide.pageId ? { page_id: Number(slide.pageId), source_page_id: Number(slide.pageId) } : {}),
      title: slide.title,
      html: slide.html,
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
    },
    theme: String(routeQueryValue(route.query.pptTheme) || presentationMetadata.value?.theme || current.value?.theme || '').trim() || undefined,
    keep_style: true,
    conversation_context: conversationTranscript || undefined,
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

const rejectDeckRevision = () => {
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
  } catch (error) {
    WorkspaceMessage.error(error?.message || '撤销失败，请稍后重试')
  }
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
    if (current.value?.html) {
      const selectedElement = htmlSelectedElement.value
      revisionStage.value = selectedElement
        ? '正在分析选中元素并生成页面修改…'
        : '正在分析当前页并生成页面修改…'
      const response = unwrapResponse(await modifyPresentationSlide({
        ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
        slide_no: selectedSlide.value + 1,
        current_html: current.value.html,
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
  const tagName = event.target?.tagName?.toLowerCase()
  const isEditingField = ['input', 'textarea', 'select'].includes(tagName) || event.target?.isContentEditable
  if (event.key === 'Escape') {
    cancelCanvasPlacement()
    return clearElementSelection()
  }
  if (isEditingField || !selectedElementId.value) return
  if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    removeElement()
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') {
    event.preventDefault()
    copyElement()
  }
}
onMounted(async () => {
  loadTestCase()
  initializeSessionFlow()
  void loadWorkspaceResources()
  await bootstrapTestCaseProject()
  await loadProject()
  await restoreTrackedRun()
  if (!projectId.value && (sessionId.value || presentationFixtureMode.value)) await startRun()
  await nextTick()
  centerCanvasView()
  if (typeof ResizeObserver !== 'undefined' && canvasAreaRef.value) {
    canvasViewportObserver = new ResizeObserver(() => centerCanvasView())
    canvasViewportObserver.observe(canvasAreaRef.value)
  }
  window.addEventListener('keydown', handleWorkspaceKeydown)
})
onBeforeUnmount(() => { activeRunStreamAbort?.abort(); clearTimeout(runStreamReconnectTimer); if (canvasCenterFrame != null) cancelAnimationFrame(canvasCenterFrame); canvasViewportObserver?.disconnect(); canvasViewportObserver = null; htmlFrameObservers.forEach(({ observer, cleanup }) => { observer?.disconnect(); cleanup?.() }); htmlFrameObservers.clear(); clearPreviewFrameObservers(); stopCanvasPan(); stopElementDrag(); cancelCanvasPlacement(); workspaceMessageInstance?.close(); window.removeEventListener('keydown', handleWorkspaceKeydown) })
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
      const syncTarget = pendingComponentSync.get(slide)
      const componentTarget = syncTarget && syncTarget !== true && !String(syncTarget).startsWith('page:')
        ? String(syncTarget)
        : ''
      // 当前后端 API-30 仍按 pageId 解析路径参数；保留兼容路径，
      // 同时把组件 ID 放入请求体，等后端支持组件实体后即可无损切换。
      const response = slide.pageId
        ? await updateProjectComponent(projectId.value, slide.pageId, {
          ...payload,
          ...(componentTarget ? { component_id: componentTarget } : {}),
          expected_page_version: Number(slide.pageVersion || 1),
        })
        : await addProjectComponent(projectId.value, payload)
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
  versionLoading.value = true; versionDialogVisible.value = true
  try { const result = unwrapResponse(await listProjectVersions(projectId.value, { page: 1, size: 30 })); versions.value = result?.records || result?.list || result?.items || [] }
  catch (error) { WorkspaceMessage.error(error?.message || '版本历史加载失败') } finally { versionLoading.value = false }
}
const createVersion = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('当前是临时课件，生成项目后才能保存版本')
  try {
    clearTimeout(autosaveTimer)
    // 严格按“当前页 → 页面顺序 → 版本快照”执行，保证刚输入的内容不会落在版本之外。
    if (orderSavePromise) {
      const orderResult = await orderSavePromise
      if (orderResult !== true) throw new Error('页面顺序保存失败，未创建版本')
    }
    await persistCurrentSlide({ throwOnError: true })
    await persistSlideOrder({ throwOnError: true })
    await saveProjectVersion(projectId.value, { description: `保存第 ${selectedSlide.value + 1} 页调整` })
    autosaveState.value = '已创建版本'
    await loadVersions()
    WorkspaceMessage.success('项目版本已保存')
  } catch (error) {
    WorkspaceMessage.error(error?.message || '版本保存失败')
  }
}
const showVersionDiff = async (version) => {
  try {
    versionDiff.value = unwrapResponse(await getProjectVersionDiff(projectId.value, version.id || version.version_id))
  } catch (error) { WorkspaceMessage.error(error?.message || '差异加载失败') }
}
const restoreVersion = async (version) => {
  try {
    const restored = unwrapResponse(await restoreProjectVersion(projectId.value, version.id || version.version_id))
    project.value = { ...(project.value || {}), ...(restored || {}) }
    versionDiff.value = null
    // 恢复接口会重建页面记录并生成新的页面 ID，不能继续沿用内存中的旧画布数据。
    await loadProject()
    await loadVersions()
    WorkspaceMessage.success('已恢复历史版本，画布已刷新')
  } catch (error) { WorkspaceMessage.error(error?.message || '版本恢复失败') }
}
const grantPermission = async () => { const userId = Number(permissionUserId.value); if (!Number.isInteger(userId) || userId <= 0) return WorkspaceMessage.warning('请输入有效用户 ID'); try { await addProjectPermission(projectId.value, { user_id: userId }); permissionUserId.value = ''; permissionDialogVisible.value = false; WorkspaceMessage.success('协作者已添加') } catch (error) { WorkspaceMessage.error(error?.message || '授权失败') } }
const projectRecordsFromResponse = (response) => {
  const data = unwrapResponse(response)
  if (Array.isArray(data)) return data
  return data?.records || data?.items || data?.list || data?.projects || []
}
const loadWorkspaceProjects = async () => {
  projectListLoading.value = true
  try { workspaceProjects.value = projectRecordsFromResponse(await listProjects({ page: 1, size: 50 })) }
  catch (error) { WorkspaceMessage.error(error?.message || '项目列表加载失败') }
  finally { projectListLoading.value = false }
}
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
    const updated = unwrapResponse(await patchProject(projectId.value, {
      project_name: name,
      current_version: Number(project.value?.current_version || 1),
    }))
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
    await copyProject(projectId.value, { new_name: `${projectNameDraft.value.trim() || project.value?.project_name || '未命名课件'} 副本` })
    WorkspaceMessage.success('项目副本已创建')
    await loadWorkspaceProjects()
  } catch (error) { WorkspaceMessage.error(error?.message || '复制项目失败') }
  finally { projectActionLoading.value = false }
}
const openWorkspaceProject = async (item) => {
  const id = item?.id || item?.project_id
  if (!id) return
  projectManagerVisible.value = false
  if (String(id) === String(projectId.value)) return
  await router.push({
    path: '/main/workspace',
    query: { projectId: String(id) },
  })
}
const archiveWorkspaceProject = async (id = projectId.value) => {
  if (!id) return
  projectActionLoading.value = true
  try {
    await archiveProject(id)
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
  if (!projectId.value || testCaseBootstrapping.value || hydratingProject.value || savingPage.value) return
  scheduleWorkspaceAutosave(700, { force: true })
}, { deep: true })
watch(selectedSlide, () => {
  selectedElementId.value = null
  pendingHtmlPanelSelection = null
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
})
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const workspaceFlowQuery = (targetProjectId = projectId.value) => {
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
  ...(targetProjectId ? { projectId: String(targetProjectId) } : {}),
  // 导出中心消费此标记后会自动完成“快照 → 预检 → 创建任务”。
  autoExport: '1',
  }
}
const goHome = () => router.push({ path: '/main' })
const createWorkspaceProject = async () => {
  autosaveState.value = '正在创建项目…'
  const context = workspaceContextPayload()
  const created = unwrapResponse(await createProject({
    project_name: String(project.value?.project_name || route.query.templateTitle || `${current.value.title}教学课件`),
    project_type: 'mixed',
    status: 'editing',
    edit_history: JSON.stringify({ workspace_context: context }),
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
const exportProject = async () => {
  clearTimeout(autosaveTimer)
  try {
    // 导出统一使用当前真实登录会话，不再在开发环境强制切换到预览账号。
    const targetProjectId = projectId.value ? String(projectId.value) : await createWorkspaceProject()
    if (projectId.value) {
      await persistCurrentSlide({ throwOnError: true })
      await persistSlideOrder({ throwOnError: true })
    }
    await router.push({ path: '/main/exports', query: workspaceFlowQuery(targetProjectId) })
  } catch (error) {
    autosaveState.value = '导出准备失败'
    WorkspaceMessage.error(error?.message || '项目保存失败，无法创建导出任务')
  }
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
  await openProjectManager()
  const requestedName = normalizedText
    .replace(/^(请|麻烦|帮我|直接)?\s*(打开|切换|进入)\s*(项目)?/i, '')
    .replace(/[“”"「」『』]/g, '')
    .trim()
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
/** 工作台 AI 输入快捷键：Enter 发送，Shift+Enter 换行，兼容中文输入法候选确认。 */
const handleAssistantKeydown = (event) => {
  if (event.isComposing || event.keyCode === 229 || event.shiftKey) return
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
      :html-mode="Boolean(current.html)"
      @back="goHome"
      @generate-interactive="openInteractiveDialog"
      @lesson-plan="openLessonPlanEditor"
      @project-manage="openProjectManager"
      @export="exportProject"
      @tool-select="handleToolSelect"
    />

    <div class="workspace-grid">
      <aside class="assistant-panel" aria-label="AI 教学助手">
        <header><div class="assistant-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div><el-button text size="small" class="context-manager-trigger" @click="openWorkspaceContextManager">上下文</el-button></header>
        <div class="assistant-intent-status" :class="inferredAssistantMode" role="status" aria-live="polite">
          <span class="assistant-intent-dot" aria-hidden="true"></span>
          <span>{{ assistantIntentHint }}</span>
        </div>
        <p class="assistant-mode-hint">明确的页面操作会执行修改；疑问、分析和建议只进行讨论。</p>
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
        <footer class="composer">
          <el-input v-model="prompt" type="textarea" :rows="3" resize="none" :disabled="isAssistantSubmitting" :placeholder="assistantPlaceholder" @keydown.enter="handleAssistantKeydown" />
          <div class="workspace-composer-actions">
            <span>{{ assistantStatusText }}</span>
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
        </footer>
      </aside>

      <section class="editor-stage">
        <aside class="slide-rail" aria-label="课件页面列表">
          <button
            v-for="(slide, index) in slides"
            :key="slide.pageId || slide.componentId || `${slide.title}-${slide.html ? 'html' : 'slide'}`"
            draggable="true"
            :class="{ active: selectedSlide === index, dragging: draggingSlideIndex === index, 'drop-before': slideDropIndex === index, 'drop-after': slideDropIndex === index + 1 }"
            :aria-label="`第 ${index + 1} 页：${slide.title}，可拖动调整顺序`"
            title="拖动页面可调整顺序"
            @dragstart="startSlideDrag(index, $event)"
            @dragover="handleSlideDragOver(index, $event)"
            @drop="dropSlide(index, $event)"
            @dragend="clearSlideDragState"
            @click="selectSlide(index)"
          >
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="thumbnail" :style="{ '--thumb': themes.find((item) => item.id === slide.theme)?.color }"><i></i><b>{{ slide.title }}</b></div>
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
            <span v-if="current.html" class="canvas-placement-status"><b>拖动元素 · 双击文字编辑</b><small>选中后可缩放、旋转、复制或删除</small></span>
            <span v-if="placementMode" class="canvas-placement-status"><b>{{ placementInstruction }}</b><small>Esc 取消</small></span>
            <span>16:9 · 自适应窗口</span>
          </div>
          <div ref="canvasAreaRef" class="canvas-scroll-viewport" @wheel="handleCanvasWheel">
          <div class="canvas-scene" :style="{ '--canvas-zoom': canvasZoom / 100, minWidth: `${Math.ceil(780 * canvasZoom / 100 + 144)}px`, minHeight: `${Math.ceil(438.75 * canvasZoom / 100 + 144)}px` }">
          <div class="canvas-slide-stage" :style="{ width: `${Math.ceil(780 * canvasZoom / 100)}px`, height: `${Math.ceil(438.75 * canvasZoom / 100)}px` }">
          <article v-if="current.html" class="slide-canvas html-slide-canvas" :style="pageCanvasStyle(current, true)" :aria-label="`${current.title} HTML PPT`">
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
                  <audio v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" preload="metadata" @pointerdown.stop @click.stop="selectElement(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未添加音频文件，请在右侧选择本地文件</span>
                </template>
                <template v-else-if="element.type === 'video'">
                  <video v-if="element.url || element.src" class="workspace-media-player" :src="element.url || element.src" :controls="element.controls !== false" :autoplay="Boolean(element.autoplay)" playsinline preload="metadata" @pointerdown.stop @click.stop="selectElement(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未添加视频文件，请在右侧选择本地文件</span>
                </template>
                <template v-else-if="element.type === 'h5'">
                  <iframe v-if="element.html" class="workspace-h5-frame" :srcdoc="element.html" sandbox="allow-scripts allow-forms allow-pointer-lock" :title="elementContent(element) || 'H5 互动内容'" @pointerdown.stop="selectElement(element.id, $event)" />
                  <span v-else class="widget-empty-state">尚未添加 H5 内容，请在右侧粘贴 HTML</span>
                  <button v-if="element.html" type="button" class="widget-action widget-action-button" @click.stop="previewInteractiveElement(element)">放大预览</button>
                </template>
                <SubjectToolRuntime v-else :element="element" />
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
              <iframe v-else-if="placementPreviewElement.type === 'h5' && placementPreviewElement.html" class="workspace-h5-frame" :srcdoc="placementPreviewElement.html" sandbox="allow-scripts allow-forms" title="H5 互动内容" />
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
          <div v-if="projectId" class="project-utilities" aria-label="项目操作">
            <span>{{ autosaveState }}</span>
            <el-button v-if="revisionUndoSnapshot?.length" text size="small" type="warning" @click="undoLastAiRevision">撤销本次 AI 修改</el-button>
            <el-button text size="small" @click="openQualityPanel">质量建议</el-button>
            <el-button text size="small" @click="createVersion">保存版本</el-button>
            <el-button text size="small" @click="loadVersions">版本历史</el-button>
            <el-button text size="small" @click="permissionDialogVisible = true">协作授权</el-button>
          </div>
        </main>
      </section>

      <WorkspacePropertiesPanel
        :elements="workspaceElements"
        :selected-element="workspaceSelectedElement"
        :selected-element-id="workspaceSelectedElementId"
        :page-number="selectedSlide + 1"
        :page="current"
        :themes="themes"
        :layouts="layouts"
        :resources="workspaceResources"
        :resources-loading="workspaceResourcesLoading"
        @update-element-style="updateElementStyle"
        @update-element-position="updateElementPosition"
        @update-element-content="updateElementContent"
        @update-element-field="updateElementField"
        @update-element-data="updateElementData"
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
        @copy-slide="copySlide"
        @remove-slide="removeSlide"
      />
    </div>

    <el-dialog v-model="previewVisible" class="preview-dialog" width="min(960px, 92vw)" title="课件预览 · 全部页面" @closed="clearPreviewFrameObservers">
      <div class="preview">
        <div class="preview-toolbar">
          <span>连续预览 · 共 {{ slides.length }} 页</span>
          <nav aria-label="预览页面导航">
            <button v-for="(slide, index) in slides" :key="`preview-nav-${index}`" type="button" :class="{ active: previewSlideIndex === index }" @click="scrollPreviewTo(index)">{{ String(index + 1).padStart(2, '0') }}</button>
          </nav>
        </div>
        <div ref="previewDeckRef" class="preview-deck">
          <section v-for="(slide, slideIndex) in slides" :key="`preview-page-${slideIndex}-${slide.title}`" class="preview-page" :class="{ 'is-current': previewSlideIndex === slideIndex }" :data-preview-index="slideIndex">
            <div class="preview-page-heading"><span>第 {{ slideIndex + 1 }} 页</span><strong>{{ slide.title }}</strong></div>
            <div v-if="slide.html" class="html-preview-shell">
              <iframe :srcdoc="withHtmlPageBackground(slide.html, slide)" sandbox="allow-scripts" :title="`${slide.title} HTML PPT 预览`" class="preview-html-frame" @load="fitPreviewHtmlFrame"></iframe>
            </div>
            <article v-else class="slide-canvas preview-slide" :class="`layout-${slide.layout}`" :style="pageCanvasStyle(slide)">
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
                    <iframe v-if="element.html" class="workspace-h5-frame" :srcdoc="element.html" sandbox="allow-scripts allow-forms allow-pointer-lock" :title="previewElementContent(element, slide) || 'H5 互动内容'" />
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
      <template #footer><el-button @click="closePreview">继续编辑</el-button></template>
    </el-dialog>
    <el-dialog v-model="revisionPreviewVisible" title="确认 AI 整套修改" width="min(900px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="false">
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
    <el-dialog v-model="interactiveDialogVisible" title="生成互动模块" width="min(720px, 92vw)" destroy-on-close>
      <p class="dialog-hint">将调用真实模型生成完整 HTML 互动内容，通常需要几十秒；生成后可先预览，再插入当前页面或作为独立页面保存。</p>
      <el-form :model="interactiveForm" label-position="top" class="interactive-form">
        <div class="interactive-form-grid">
          <el-form-item label="模块标题" required>
            <el-input v-model="interactiveForm.title" maxlength="80" show-word-limit placeholder="例如：勾股定理快速问答" />
          </el-form-item>
          <el-form-item label="互动主题" required>
            <el-input v-model="interactiveForm.topic" maxlength="120" placeholder="例如：直角三角形三边关系" />
          </el-form-item>
          <el-form-item label="模块类型" required>
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
      <template #footer><el-button @click="interactiveDialogVisible = false">取消</el-button><el-button type="primary" :loading="interactiveGenerating" @click="handleGenerateInteractiveModule">生成互动模块</el-button></template>
    </el-dialog>
    <el-dialog v-model="interactivePreviewVisible" title="互动模块预览" width="min(900px, 94vw)" class="interactive-preview-dialog">
      <div v-if="interactiveModule" class="interactive-preview-meta">
        <div><strong>{{ interactiveModule.title || '互动模块' }}</strong><span>{{ interactiveModuleTypes.find((item) => item.value === (interactiveModule.module_type || interactiveModule.moduleType))?.label || '互动模块' }}</span></div>
        <p>{{ interactiveModule.topic || '暂无主题说明' }}</p>
      </div>
      <iframe v-if="interactiveModule?.html" :srcdoc="interactiveModule.html" sandbox="allow-scripts" class="interactive-preview-frame" title="互动模块预览"></iframe>
      <el-empty v-else description="暂无可预览内容" />
      <ul v-if="interactiveModule?.usage_suggestions?.length" class="interactive-suggestions">
        <li v-for="suggestion in interactiveModule.usage_suggestions" :key="suggestion">{{ suggestion }}</li>
      </ul>
      <template #footer>
        <el-button @click="interactivePreviewVisible = false">关闭</el-button>
        <el-button v-if="interactivePreviewSource === 'generated'" @click="reopenInteractiveDialog">返回修改</el-button>
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
        <span class="generation-hint">真实模型生成通常需要 1–7 分钟，请保持此页面打开。</span>
        <el-progress :percentage="runProgress" :show-text="false" :stroke-width="5" />
        <div class="generation-observability">
          <section v-if="runTimeline.length" class="generation-detail-section">
            <header><strong>执行步骤</strong><span>{{ runTimeline.length }} 条</span></header>
            <ol class="generation-timeline"><li v-for="item in runTimeline" :key="item.id"><i :class="`status-${item.status}`"></i><div><strong>{{ item.label }}</strong><span>{{ item.statusLabel }}<template v-if="item.detail"> · {{ item.detail }}</template></span></div></li></ol>
          </section>
          <section v-if="runToolCalls.length" class="generation-detail-section">
            <header><strong>工具调用</strong><span>{{ runToolCalls.length }} 次</span></header>
            <ul class="generation-compact-list"><li v-for="tool in runToolCalls" :key="tool.id"><b>{{ tool.name }}</b><span>{{ tool.status }}<template v-if="tool.detail"> · {{ tool.detail }}</template></span></li></ul>
          </section>
          <section v-if="runRetrievalSources.length" class="generation-detail-section">
            <header><strong>RAG 引用资料</strong><span>{{ runRetrievalSources.length }} 项</span></header>
            <ul class="generation-compact-list"><li v-for="resource in runRetrievalSources" :key="resource.id"><b>{{ resource.name }}</b><span>{{ resource.detail || resource.id }}</span></li></ul>
          </section>
          <section v-if="runReflection" class="generation-detail-section generation-reflection"><header><strong>反思结果</strong><span>已关联本次生成</span></header><p v-if="runReflection.summary">{{ runReflection.summary }}</p><ul v-if="runReflection.suggestions.length" class="generation-compact-list"><li v-for="(item, index) in runReflection.suggestions" :key="`run-reflection-${index}`"><span>{{ item }}</span></li></ul></section>
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
    <el-dialog v-model="qualityPanelVisible" title="生成质量与改进建议" width="min(680px, 92vw)">
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
    <el-dialog v-model="contextManagerVisible" title="工作台 AI 上下文" width="min(680px, 92vw)" :close-on-click-modal="false">
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
    <el-dialog v-model="versionDialogVisible" title="项目版本历史" width="min(680px, 92vw)"><div v-loading="versionLoading" class="version-list"><article v-for="version in versions" :key="version.id || version.version_id"><div><strong>版本 {{ version.version_number || version.id }}</strong><p>{{ version.description || '未填写说明' }}</p></div><div><el-button text size="small" @click="showVersionDiff(version)">查看差异</el-button><el-button text size="small" type="primary" @click="restoreVersion(version)">恢复此版本</el-button></div></article><p v-if="versionDiff" class="version-diff">{{ versionDiff.summary || JSON.stringify(versionDiff.differences || versionDiff) }}</p><el-empty v-if="!versionLoading && !versions.length" description="暂无历史版本" /></div><template #footer><el-button @click="versionDialogVisible = false">关闭</el-button></template></el-dialog>
    <el-dialog v-model="permissionDialogVisible" title="添加协作者" width="420px"><p class="dialog-hint">协作者将获得项目编辑权限。</p><el-input v-model="permissionUserId" inputmode="numeric" placeholder="输入用户 ID" /><template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" @click="grantPermission">确认授权</el-button></template></el-dialog>
    <el-dialog v-model="projectManagerVisible" title="项目管理" width="min(760px, 92vw)" class="project-manager-dialog">
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
        <article v-for="item in workspaceProjects" :key="item.id || item.project_id">
          <div><strong>{{ item.project_name || item.name || '未命名项目' }}</strong><span>{{ item.status || 'editing' }} · {{ item.project_type || 'ppt' }}</span></div>
          <div class="project-manager-item-actions">
            <el-button text size="small" @click="openWorkspaceProject(item)">打开</el-button>
            <el-button v-if="String(item.status).toLowerCase() === 'archived'" text size="small" :loading="projectActionLoading" @click="restoreWorkspaceProject(item.id || item.project_id)">恢复</el-button>
            <el-button v-else text size="small" :loading="projectActionLoading" @click="archiveWorkspaceProject(item.id || item.project_id)">归档</el-button>
            <el-button text size="small" type="danger" :loading="projectActionLoading" @click="removeWorkspaceProject(item.id || item.project_id)">删除</el-button>
          </div>
        </article>
        <el-empty v-if="!projectListLoading && !workspaceProjects.length" description="暂无可管理项目" />
      </section>
      <template #footer><el-button @click="projectManagerVisible = false">关闭</el-button></template>
    </el-dialog>
    <LessonPlanEditor
      v-model="lessonPlanVisible"
      :title="lessonPlanTitle"
      :subject="lessonPlanSubject"
      :grade="lessonPlanGrade"
      :outline="lessonPlanOutline"
      :slides="slides"
      :initial-plan="lessonPlanDraft"
      @save="saveLessonPlanDraft"
    />
</template>

<style scoped>
.workspace-composer-buttons{display:inline-flex;align-items:center;gap:4px}
.context-manager-trigger{margin-left:auto;flex:none}.context-manager{display:grid;gap:12px}.context-source-card{display:grid;gap:4px;padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.context-source-card span,.context-source-card small{color:var(--zh-text-caption);font-size:11px}.context-source-card strong{color:var(--zh-text-primary);font-size:14px}.context-resource-picker{display:grid;gap:7px;max-height:280px;overflow:auto;padding:10px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.context-resource-picker :deep(.el-checkbox){display:flex;align-items:flex-start;margin:0}.context-resource-picker :deep(.el-checkbox__label){display:flex;align-items:baseline;gap:8px;min-width:0;color:var(--zh-text-secondary);font-size:12px}.context-resource-picker small{color:var(--zh-text-caption);font-size:10px}.context-selected-resources{display:flex;align-items:center;flex-wrap:wrap;gap:6px}.context-selected-resources strong{margin-right:3px;color:var(--zh-text-caption);font-size:11px}
.generation-observability{display:grid;gap:8px;max-height:38vh;overflow:auto;margin-top:12px;padding-top:12px;border-top:1px solid rgb(37 99 235 / 14%);text-align:left}.generation-detail-section{padding:9px 10px;border:1px solid rgb(37 99 235 / 12%);border-radius:8px;background:rgb(255 255 255 / 74%)}.generation-detail-section header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:7px}.generation-detail-section header strong{font-size:11px}.generation-detail-section header span{color:#7c8491;font-size:10px}.generation-timeline{display:grid;gap:6px;margin:0;padding:0;list-style:none}.generation-timeline li{display:flex;align-items:flex-start;gap:7px}.generation-timeline li>i{flex:none;width:7px;height:7px;margin-top:4px;border-radius:50%;background:#9ca3af}.generation-timeline li>i.status-running,.generation-timeline li>i.status-executing,.generation-timeline li>i.status-processing{background:#2563eb;box-shadow:0 0 0 3px rgb(37 99 235 / 14%)}.generation-timeline li>i.status-completed,.generation-timeline li>i.status-success,.generation-timeline li>i.status-done{background:#16a34a}.generation-timeline li>i.status-failed,.generation-timeline li>i.status-error{background:#dc2626}.generation-timeline li div{display:grid;gap:2px;min-width:0}.generation-timeline li strong{overflow:hidden;color:#26364d;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.generation-timeline li span,.generation-compact-list li span{color:#7c8491;font-size:10px;line-height:1.45}.generation-compact-list{display:grid;gap:5px;margin:0;padding:0;list-style:none}.generation-compact-list li{display:flex;gap:6px;min-width:0;color:#526176;font-size:10px;line-height:1.45}.generation-compact-list li b{flex:none;color:#334c70;font-size:10px}.generation-compact-list li span{min-width:0;overflow:hidden;text-overflow:ellipsis}.generation-reflection p{margin:0;color:#526176;font-size:10px;line-height:1.5}.generation-failure-detail,.generation-recovery{padding:8px 10px;border-radius:8px;text-align:left;font-size:11px;line-height:1.5}.generation-failure-detail{color:#9b2c2c;background:#fff3f0}.generation-recovery{color:#7a5a14;background:#fff8e7}.generation-failure-timeline{display:grid;gap:5px;padding:8px 10px;border-radius:8px;color:#7c8491;background:#f8fafc;text-align:left;font-size:10px;line-height:1.45}.generation-failure-timeline strong{color:#526176;font-size:11px}
.revision-preview-dialog{display:grid;gap:14px}.revision-preview-summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.revision-preview-summary div{display:grid;gap:4px;min-width:0}.revision-preview-summary span:first-child{color:var(--zh-text-caption);font-size:11px}.revision-preview-summary strong{color:var(--zh-text-primary);font-size:14px;line-height:1.5}.revision-preview-count{flex:none;padding:5px 9px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-primary);font-size:11px}.revision-preview-section{padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.revision-preview-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}.revision-preview-section-heading strong{font-size:13px}.revision-preview-section-heading span{color:var(--zh-text-caption);font-size:11px}.revision-operation-list{display:grid;gap:7px;max-height:180px;overflow:auto;margin:0;padding:0;list-style:none}.revision-operation-list li{display:flex;align-items:center;gap:8px;min-width:0;padding:7px 8px;border-radius:var(--zh-radius8);background:var(--zh-background-light);color:var(--zh-text-secondary);font-size:12px}.revision-operation-list li>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.revision-comparison-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.revision-comparison-column{min-width:0;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);overflow:hidden}.revision-comparison-column header{padding:9px 11px;color:var(--zh-text-secondary);background:var(--zh-background-light);font-size:12px;font-weight:600}.revision-comparison-column.is-after header{color:var(--zh-text-theme);background:var(--zh-background-weaken)}.revision-comparison-column ol{display:grid;gap:5px;max-height:220px;overflow:auto;margin:0;padding:9px;list-style:none}.revision-comparison-column li{display:flex;align-items:center;gap:8px;min-width:0;color:var(--zh-text-secondary);font-size:12px}.revision-comparison-column li b{display:grid;place-items:center;flex:none;width:24px;height:20px;border-radius:5px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:600 10px var(--zh-font-number)}.revision-comparison-column li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media(max-width:640px){.revision-comparison-grid{grid-template-columns:1fr}.revision-preview-summary{align-items:flex-start;flex-direction:column}}
.workspace{height:100dvh;display:grid;grid-template-rows:60px minmax(0,1fr);overflow:hidden;background:var(--zh-background-light)}.workspace-grid{min-height:0;display:grid;grid-template-columns:286px minmax(500px,1fr) 270px}.assistant-panel,.properties{min-height:0;background:var(--zh-background-primary)}.assistant-panel{display:flex;flex-direction:column;border-right:1px solid var(--zh-line-border)}.assistant-panel>header{display:flex;align-items:center;gap:9px;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.assistant-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:var(--zh-radius8);color:#fff;background:var(--zh-gradient-blue);font-weight:700}.assistant-panel header div:last-child{display:flex;flex-direction:column}.assistant-panel header strong{font-size:13px}.assistant-panel header span{margin-top:2px;color:var(--zh-text-caption);font-size:10px}.conversation{flex:1;padding:16px;overflow:auto}.message{display:flex;align-items:flex-start;gap:8px;margin-bottom:16px}.message>span{display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:6px;color:#fff;background:var(--zh-theme-primary);font-size:10px}.message p{margin:0;padding:10px 12px;border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-answer-card);font-size:12px;line-height:1.65}.message.user{justify-content:flex-end}.message.user p{color:var(--zh-text-primary);background:var(--zh-background-user-query)}.composer{padding:12px;border-top:1px solid var(--zh-line-border)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:8px}.composer span{color:var(--zh-text-caption);font-size:10px}.composer :deep(.el-textarea__inner){background:var(--zh-background-light);box-shadow:none}.editor-stage{display:grid;grid-template-columns:116px minmax(0,1fr);min-width:0}.slide-rail{padding:12px 9px;overflow:auto;border-right:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.slide-rail>button{display:grid;grid-template-columns:18px 1fr;gap:4px;width:100%;margin-bottom:10px;padding:3px;border:1px solid transparent;border-radius:6px;color:var(--zh-text-caption);background:transparent;text-align:left;cursor:pointer}.slide-rail>button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.thumbnail{display:flex;flex-direction:column;justify-content:center;gap:5px;height:54px;padding:8px;border-radius:4px;background:var(--zh-background-light)}.thumbnail i{width:65%;height:3px;background:var(--thumb)}.thumbnail b{overflow:hidden;color:var(--zh-text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}.slide-rail :deep(.el-button){width:100%;justify-content:flex-start}.canvas-area{position:relative;display:grid;place-items:center;min-width:0;padding:44px 34px;overflow:auto;background-color:#eef0f4;background-image:radial-gradient(#c9ced7 1px,transparent 1px);background-size:18px 18px}.canvas-meta{position:absolute;top:12px;inset-inline:20px;display:flex;justify-content:space-between;color:#7c8491;font-size:10px}.slide-canvas{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;padding:clamp(28px,4vw,52px);color:#102d54;background:#f9fbff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.slide-eyebrow,.slide-canvas h1,.slide-canvas>p,.theorem{position:relative;z-index:1}.slide-eyebrow{color:var(--accent);font:600 10px var(--zh-font-number);letter-spacing:.12em}.slide-canvas h1{max-width:76%;margin:18px 0 0;font-size:clamp(26px,3vw,40px);line-height:1.2;letter-spacing:-.04em}.slide-canvas>p{max-width:64%;margin:12px 0;color:#607491;font-size:clamp(11px,1.2vw,15px);line-height:1.65}.theorem{display:grid;grid-template-columns:.8fr 1.2fr;align-items:center;gap:28px;width:76%;margin:28px auto}.triangle{position:relative;width:104px;height:104px;border-right:5px solid var(--accent);border-bottom:5px solid var(--accent);transform:skewY(-35deg) rotate(-10deg)}.triangle i{position:absolute;color:var(--accent);font-style:normal;font-weight:700;transform:skewY(35deg) rotate(10deg)}.triangle i:nth-child(1){bottom:-22px;left:36px}.triangle i:nth-child(2){top:40px;right:-18px}.triangle i:nth-child(3){top:-22px;left:8px}.formula{display:grid;grid-template-columns:auto 24px auto;align-items:center;font-family:var(--zh-font-number)}.formula span,.formula strong{font-size:clamp(22px,3vw,36px)}.formula em{color:#7c8da4;font-style:normal}.formula strong{color:var(--accent)}.formula small{grid-column:1/-1;margin-top:8px;color:#7c8da4;font-size:10px}.slide-canvas footer{position:absolute;z-index:1;right:0;bottom:0;left:0;display:grid;grid-template-columns:110px 1fr;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54)}.slide-canvas footer p{margin:0;font-size:10px;line-height:1.5}.layout-重点陈述 h1{margin-top:54px;font-size:clamp(34px,4.4vw,52px)}.canvas-controls{position:absolute;right:18px;bottom:14px;display:flex;overflow:hidden;border-radius:var(--zh-radius8);background:var(--zh-background-capsule);box-shadow:var(--zh-shadow1)}.canvas-controls button,.canvas-controls span{padding:6px 9px;border:0;color:var(--zh-text-secondary);background:transparent;font-size:11px}.canvas-controls button{cursor:pointer}.properties{overflow:auto;border-left:1px solid var(--zh-line-border)}.properties>header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties header strong{font-size:13px}.properties header span{color:var(--zh-text-caption);font-size:10px}.tabs{display:grid;grid-template-columns:repeat(3,1fr);padding:10px 14px 0;border-bottom:1px solid var(--zh-line-parting)}.tabs button{padding:8px;border:0;border-bottom:2px solid transparent;color:var(--zh-text-caption);background:transparent;cursor:pointer}.tabs button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme)}.properties section{padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties label{display:block;margin:0 0 10px;color:var(--zh-text-secondary);font-size:11px;font-weight:600}.properties label:not(:first-child){margin-top:18px}.theme-picker{display:flex;gap:12px}.theme-picker button{width:24px;height:24px;border:2px solid var(--zh-background-primary);border-radius:50%;box-shadow:0 0 0 1px var(--zh-line-border);cursor:pointer}.theme-picker button.selected{outline:2px solid var(--zh-text-theme);outline-offset:2px}.layout-picker{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.layout-picker button{display:grid;grid-template-rows:26px auto;gap:4px;min-height:66px;padding:7px 4px;border:1px solid var(--zh-line-border);border-radius:6px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:9px;cursor:pointer}.layout-picker button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.layout-picker i{display:block;width:70%;height:4px;margin:auto;background:var(--zh-line-theme50)}.layout-picker i:nth-child(2){width:48%}.page-actions{display:grid;gap:8px}.page-actions :deep(.el-button){justify-content:flex-start;margin:0}.assistant-tip{display:flex;gap:8px;margin:16px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.assistant-tip p,.hint{margin:0;color:var(--zh-text-secondary);font-size:10px;line-height:1.6}.preview{display:grid;place-items:center;padding:18px;background:#eef0f4}.preview-slide{width:min(780px,100%)}.preview-formula{width:max-content;margin:50px auto}.preview-dialog :deep(.el-dialog__body){padding:0}@media(max-width:1120px){.workspace-grid{grid-template-columns:250px minmax(460px,1fr)}.properties{display:none}}@media(max-width:820px){.workspace-grid{grid-template-columns:1fr}.assistant-panel{display:none}.editor-stage{grid-template-columns:88px minmax(0,1fr)}}
.plan-dialog-content .plan-status{margin:0 0 14px;color:var(--zh-text-secondary);font-size:13px}.plan-preview{display:grid;gap:12px;max-height:min(62vh,680px);overflow:auto;padding:2px 4px 4px 0}.plan-overview{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:18px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);background:linear-gradient(135deg,var(--zh-background-weaken),var(--zh-background-primary))}.plan-overview-heading{min-width:0}.plan-eyebrow{color:var(--zh-text-theme);font-size:10px;font-weight:700;letter-spacing:.12em}.plan-overview h3{margin:7px 0 6px;color:var(--zh-text-primary);font-size:19px;line-height:1.35}.plan-overview p{margin:0;color:var(--zh-text-secondary);font-size:12px;line-height:1.7}.plan-slide-count{display:inline-flex;flex:none;align-items:center;padding:7px 10px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-primary);font:700 12px var(--zh-font-number);white-space:nowrap}.plan-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.plan-meta>span{display:grid;gap:4px;padding:11px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-meta small,.slide-details small{color:var(--zh-text-caption);font-size:10px}.plan-meta strong{overflow:hidden;color:var(--zh-text-primary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.plan-section{padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.plan-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}.plan-section-heading strong{color:var(--zh-text-primary);font-size:13px}.plan-section-heading span{color:var(--zh-text-caption);font-size:11px}.plan-bullet-list,.slide-points{display:grid;gap:7px;margin:0;padding-left:18px;color:var(--zh-text-secondary);font-size:12px;line-height:1.6}.plan-bullet-list li::marker,.slide-points li::marker{color:var(--zh-text-theme)}.plan-tags{display:flex;flex-wrap:wrap;gap:7px}.plan-tags span{padding:5px 9px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:11px}.plan-slide-list{display:grid;gap:8px}.plan-slide-card{display:grid;grid-template-columns:36px minmax(0,1fr);gap:10px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.plan-slide-number{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font:700 11px var(--zh-font-number)}.plan-slide-main{min-width:0}.plan-slide-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px}.plan-slide-heading h4{margin:0;color:var(--zh-text-primary);font-size:13px}.plan-slide-heading span{color:var(--zh-text-caption);font-size:10px}.slide-points{margin-bottom:9px}.slide-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-top:9px;border-top:1px solid var(--zh-line-parting)}.slide-details p{margin:3px 0 0;color:var(--zh-text-secondary);font-size:11px;line-height:1.55}.plan-comment{margin-top:14px}.run-progress{position:fixed;z-index:100;right:24px;bottom:24px;width:min(320px,calc(100vw - 48px));padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-pop);box-shadow:var(--zh-shadow2);font-size:12px}.run-progress :deep(.el-progress){margin-top:9px}
  .project-utilities{position:absolute;z-index:5;bottom:52px;left:50%;display:flex;align-items:center;gap:4px;width:max-content;max-width:calc(100% - 32px);overflow-x:auto;padding:5px 8px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);color:var(--zh-text-caption);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1);font-size:11px;transform:translateX(-50%)}.project-utilities span{margin:0 4px;white-space:nowrap}.version-list{display:grid;gap:10px}.version-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.version-list strong{font-size:13px}.version-list p{margin:4px 0 0;color:var(--zh-text-caption);font-size:12px}.version-diff{margin:0;padding:12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-weaken);font-size:12px;line-height:1.6;white-space:pre-wrap}.dialog-hint{margin:0 0 12px;color:var(--zh-text-secondary);font-size:13px}
.quality-report-panel{display:grid;gap:14px}.quality-report-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 16px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.quality-report-heading div{display:grid;gap:4px}.quality-report-heading span:first-child{color:var(--zh-text-caption);font-size:10px}.quality-report-heading strong{color:var(--zh-text-primary);font-size:14px}.quality-score{color:var(--zh-text-theme);font:700 28px var(--zh-font-number)}.quality-score small{margin-left:2px;color:var(--zh-text-caption);font-size:11px}.quality-summary{margin:0;color:var(--zh-text-secondary);font-size:13px;line-height:1.7}.quality-report-section{padding:12px 14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.quality-report-section>strong,.quality-section-heading strong{color:var(--zh-text-primary);font-size:12px}.quality-report-section ul{display:grid;gap:6px;margin:8px 0 0;padding-left:18px;color:var(--zh-text-secondary);font-size:12px;line-height:1.55}.quality-report-risk{border-color:color-mix(in srgb,var(--el-color-warning) 35%,var(--zh-line-border))}.quality-report-suggestions{display:grid;gap:8px}.quality-section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.quality-section-heading span,.quality-retry-hint{color:var(--zh-text-caption);font-size:10px}.quality-report-suggestions article{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 10px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.quality-report-suggestions article span{min-width:0;color:var(--zh-text-secondary);font-size:12px;line-height:1.5}.quality-report-suggestions article :deep(.el-button){flex:none;margin:0}.quality-retry-hint{margin:0}
.project-manager-current{display:grid;gap:10px;padding:14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius10);background:var(--zh-background-weaken)}.project-manager-current>label{color:var(--zh-text-secondary);font-size:12px;font-weight:600}.project-manager-current>div:first-of-type{display:flex;gap:8px}.project-manager-actions{display:flex;flex-wrap:wrap;gap:8px}.project-manager-list{display:grid;gap:8px;margin-top:18px;min-height:100px}.project-manager-list-heading{display:flex;align-items:center;justify-content:space-between}.project-manager-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:11px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.project-manager-list article>div:first-child{display:grid;gap:4px;min-width:0}.project-manager-list strong{overflow:hidden;color:var(--zh-text-primary);font-size:13px;text-overflow:ellipsis;white-space:nowrap}.project-manager-list span{color:var(--zh-text-caption);font-size:11px}.project-manager-item-actions{display:flex;align-items:center;flex:none;gap:2px}
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

@media (max-width: 620px) {
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

.assistant-mode-hint {
  margin: 6px 12px 0;
  color: var(--zh-text-caption);
  font-size: 10px;
  line-height: 1.5;
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

.interactive-preview-meta p {
  margin: 0;
  color: var(--zh-text-secondary);
  font-size: 12px;
}

.interactive-preview-frame {
  display: block;
  width: 100%;
  height: min(62vh, 620px);
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: #f8fafc;
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

@media (max-width: 640px) {
  .interactive-form-grid {
    grid-template-columns: 1fr;
  }

  .interactive-preview-frame {
    height: 58vh;
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

@media (max-width: 640px) {
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

.assistant-intent-status {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 10px 12px 0;
  padding: 8px 10px;
  border: 1px solid var(--zh-line-border);
  border-radius: 8px;
  color: var(--zh-text-caption);
  background: var(--zh-background-light);
  font-size: 10px;
  line-height: 1.45;
}

.assistant-intent-status.revision {
  border-color: var(--zh-line-theme);
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
}

.assistant-intent-dot {
  width: 6px;
  height: 6px;
  flex: none;
  border-radius: 50%;
  background: #9aa4b2;
}

.assistant-intent-status.revision .assistant-intent-dot {
  background: var(--zh-line-theme);
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
