<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FullScreen, Plus, Promotion } from '@element-plus/icons-vue'
import { addProjectPermission, batchSaveProjectPages, createProject, createProjectPage, deleteProjectPage, generateInteractiveModule, generatePresentation, getAiPlan, getProject, getProjectPage, getProjectVersionDiff, listProjectPages, listProjectVersions, modifyPresentationSlide, patchProject, restoreProjectVersion, reviseProjectWithAi, saveProjectVersion, sendAiSessionMessage, saveProjectPage, validateProjectComponent } from '../apis/teacher'
import IntentClarificationDialog from './IntentClarificationDialog.vue'
import CreationWorkspaceToolbar from './CreationWorkspaceToolbar.vue'
import WorkspacePropertiesPanel from './WorkspacePropertiesPanel.vue'
import { readPresentationDraft, savePresentationDraft } from '../utils/presentationDraft.js'
import { createPresentationFixture } from '../mock/data/presentationFixture.js'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const selectedSlide = ref(0)
const activeTool = ref('')
const selectedElementId = ref(null)
const draggingElementId = ref(null)
const activePanel = ref('content')
const canvasZoom = ref(86)
const canvasZoomInput = ref('86')
const CANVAS_ZOOM_MIN = 50
const CANVAS_ZOOM_MAX = 200
const CANVAS_ZOOM_STEP = 10
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
const revisionSubmitting = ref(false)
const presentationId = ref('')
const presentationMetadata = ref(null)
const htmlFrameObservers = new Set()
const htmlCanvasSource = ref('')
const htmlCanvasSourceSlide = ref(null)
const htmlElements = ref([])
const htmlSelectedElementId = ref(null)
const htmlSelectedElement = ref(null)
const htmlSelectionRestoreKey = ref('')
const versionDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const versionLoading = ref(false)
const versions = ref([])
const versionDiff = ref(null)
const permissionUserId = ref('')
const autosaveState = ref('已保存')
const testCaseBootstrapping = ref(false)
const hydratingProject = ref(false)
const savingPage = ref(false)
const workspaceClientVersion = `workspace-${Date.now()}`
const loadedPageDetailIds = new Set()
const componentValidationCache = new Map()
let autosaveTimer = null
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
  { id: 'audio', type: 'audio', name: '音频讲解', content: '教师讲解示例音频', position: { x: 8, y: 48, width: 30, height: 14, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', backgroundColor: '#eff6ff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'video', type: 'video', name: '视频演示', content: '课堂实验演示视频', position: { x: 40, y: 48, width: 30, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#173d78', backgroundColor: '#eef2ff', borderColor: '#c7d2fe', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'table', type: 'table', name: '数据表格', content: '小组测量记录', data: [['小组', '边 a', '边 b'], ['A组', '3', '4'], ['B组', '5', '12']], position: { x: 8, y: 64, width: 44, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', backgroundColor: '#f8fbff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 10, opacity: 100 } },
  { id: 'h5', type: 'h5', name: 'H5互动组件', content: '互动问答 H5', position: { x: 54, y: 64, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#ff6b3f', backgroundColor: '#fff7ed', borderColor: '#fed7aa', borderWidth: 1, borderRadius: 12, opacity: 100 } },
  { id: 'subject', type: 'subject', name: '学科工具', content: '直角三角形测量工具', position: { x: 54, y: 43, width: 36, height: 18, rotation: 0, zIndex: 3 }, style: { color: '#1f993f', backgroundColor: '#f0fdf4', borderColor: '#bbf7d0', borderWidth: 1, borderRadius: 12, opacity: 100 } },
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
slides.forEach((slide) => { slide.elements = createMockElements() })
const current = computed(() => slides[selectedSlide.value])
const syncHtmlCanvasSource = (slide = current.value) => {
  htmlCanvasSourceSlide.value = slide || null
  htmlCanvasSource.value = slide?.html ? String(slide.html) : ''
}
const htmlCanvasFrameSource = computed(() => {
  if (!current.value?.html) return ''
  return htmlCanvasSourceSlide.value === current.value
    ? htmlCanvasSource.value
    : String(current.value.html)
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
}
const adjustCanvasZoom = (delta) => setCanvasZoom(canvasZoom.value + delta)
const resetCanvasZoom = () => setCanvasZoom(86)
const commitCanvasZoomInput = () => setCanvasZoom(canvasZoomInput.value)
watch(current, (slide) => syncHtmlCanvasSource(slide), { immediate: true })
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
const defaultSlide = (index = 1) => ({ title: `新建页面 ${index}`, eyebrow: '教学内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue', elements: createMockElements() })
const parseJson = (value, fallback = {}) => { try { return typeof value === 'string' ? JSON.parse(value) : (value || fallback) } catch { return fallback } }
const normalizeOutlinePayload = (planData = {}) => {
  const parsedPlan = parseJson(planData.plan_json ?? planData.outline ?? planData, {})
  const outline = parsedPlan?.outline
  if (outline && typeof outline === 'object' && !Array.isArray(outline)) return outline
  return parsedPlan && typeof parsedPlan === 'object' && !Array.isArray(parsedPlan) ? parsedPlan : {}
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
      html: String(slide?.html || ''),
      notes: String(slide?.notes || ''),
      slideNo: Number(slide?.slide_no) || index + 1,
      interactiveAssets: slide?.interactive_assets || slide?.metadata?.interactive_assets || [],
      metadata: slide?.metadata || {},
      elements: Array.isArray(slide?.elements) ? slide.elements : []
    }))
    .filter((slide) => slide.html.trim())
}
const applyGeneratedPresentation = (rawResponse, { persist = true, notify = true } = {}) => {
  const data = getPresentationPayload(rawResponse)
  const generatedSlides = normalizePresentationSlides(data)
  if (!generatedSlides.length) throw new Error('HTML PPT 生成服务未返回页面')

  slides.splice(0, slides.length, ...generatedSlides)
  selectedSlide.value = 0
  selectedElementId.value = null
  activePanel.value = 'content'
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
  presentationId.value = String(data.presentation_id || '')
  presentationMetadata.value = data.metadata && typeof data.metadata === 'object' ? data.metadata : null
  runStatus.value = 'completed'
  runProgress.value = 100
  runStage.value = 'HTML PPT 已生成'

  if (persist && sessionId.value) {
    savePresentationDraft(sessionId.value, {
      presentation_id: presentationId.value,
      title: data.title || generatedSlides[0].title,
      slide_count: generatedSlides.length,
      request_key: String(routeQueryValue(route.query.pptGeneration) || '') || null,
      slides: generatedSlides,
      metadata: presentationMetadata.value
    })
  }

  if (notify) {
    messages.push({ role: 'assistant', text: `已生成 ${generatedSlides.length} 页 HTML PPT，可在工作台中预览。` })
    WorkspaceMessage.success(`已生成 ${generatedSlides.length} 页 HTML PPT`)
  }

  return data
}
const loadPresentationFixture = () => {
  const data = applyGeneratedPresentation(createPresentationFixture(), { persist: true, notify: false })
  messages.push({ role: 'assistant', text: `已载入 ${data.slide_count} 页固定 PPT 测试样例，不会调用大模型。` })
  WorkspaceMessage.info('已载入固定 PPT 测试样例，不会消耗 API')
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
  })
}
const htmlDragTargetSelector = '[data-ppt-element],h1,h2,h3,h4,h5,h6,p,li,img,svg,table,header,main,section,article,aside,footer,figure,div[class],.card,.item,.box,.panel'
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
  const panelElementById = new Map()
  const elementPanelId = new WeakMap()
  const elementPanelKey = new WeakMap()

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
    if (element.closest?.('.a12-html-editor-overlay')) return false
    const rect = element.getBoundingClientRect()
    return rect.width > 6 && rect.height > 6
  }
  const collectCandidates = () => [...document.querySelectorAll(htmlDragTargetSelector)].filter(isCandidate)
  const panelText = (element, type) => {
    if (type === 'image') return String(element.getAttribute('alt') || '').trim().slice(0, 160)
    if (type === 'h5') return String(element.getAttribute('data-name') || element.getAttribute('title') || '互动模块').trim().slice(0, 160)
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
      src: type === 'image' ? String(element.currentSrc || element.getAttribute('src') || '') : undefined,
      alt: type === 'image' ? String(element.getAttribute('alt') || '') : undefined,
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
      data: type === 'chart' ? getChartData(element) : undefined,
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
    const restoreKey = htmlSelectionRestoreKey.value
    const restored = restoreKey ? candidates.find((element, index) => elementKey(element, index) === restoreKey) : null
    if (restored) select(restored)
    else updateGlobalSelection()
  }
  const updateOverlay = () => {
    if (!selected?.isConnected) {
      overlay.classList.remove('is-visible')
      updateGlobalSelection()
      return
    }
    const rect = selected.getBoundingClientRect()
    overlay.style.left = `${rect.left}px`
    overlay.style.top = `${rect.top}px`
    overlay.style.width = `${rect.width}px`
    overlay.style.height = `${rect.height}px`
    overlay.classList.add('is-visible')
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
    if (completed.element.hasPointerCapture?.(completed.pointerId)) completed.element.releasePointerCapture(completed.pointerId)
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
    if (elementType(selected) === 'image') selected.setAttribute('alt', content)
    else if (elementType(selected) === 'chart') {
      const titleNode = selected.querySelector('[data-a12-chart-title]')
      if (titleNode) {
        selected.setAttribute('data-a12-chart-title', content)
        titleNode.textContent = content || '数据图表'
      } else renderHtmlChart(selected, getChartData(selected), content)
    }
    else selected.textContent = content
    updateOverlay()
    commitDocument()
    return true
  }
  const updateField = (key, value) => {
    if (!selected?.isConnected || !['src', 'alt'].includes(key)) return false
    if (key === 'src' && elementType(selected) === 'image') selected.setAttribute('src', String(value || ''))
    if (key === 'alt' && elementType(selected) === 'image') selected.setAttribute('alt', String(value || '').slice(0, 80))
    updateOverlay()
    commitDocument()
    return true
  }
  const updateData = (value) => {
    if (!selected?.isConnected || elementType(selected) !== 'chart' || !Array.isArray(value)) return false
    renderHtmlChart(selected, value)
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
    const node = type === 'image' ? document.createElement('img') : document.createElement('div')
    const id = `a12-${type}-${Date.now()}`
    node.setAttribute('data-ppt-element', id)
    node.setAttribute('data-ppt-type', type)
    node.style.position = 'absolute'
    node.style.boxSizing = 'border-box'
    node.style.left = type === 'chart' ? `${62 + (index % 2) * 4}%` : `${10 + (index % 5) * 5}%`
    node.style.top = type === 'chart' ? `${10 + (index % 3) * 6}%` : `${12 + (index % 4) * 7}%`
    node.style.width = type === 'text' ? '28%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : '30%'
    node.style.height = type === 'text' ? '12%' : type === 'image' ? '24%' : type === 'chart' ? '28%' : '16%'
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
  resizeHandle.addEventListener('pointerdown', (event) => beginHandleInteraction('resize', event))
  rotateHandle.addEventListener('pointerdown', (event) => beginHandleInteraction('rotate', event))
  overlay.querySelector('.a12-html-editor-toolbar').addEventListener('click', handleToolbarClick)
  refreshElements()

  const controller = {
    selectById: (id) => { const element = findElement(id); if (element) select(element) },
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
    if (interaction?.animationFrame) frameWindow.cancelAnimationFrame(interaction.animationFrame)
    selected?.removeAttribute('data-a12-drag-selected')
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
  const cleanup = attachHtmlDragEditor(iframe)
  resize()
  if (typeof ResizeObserver === 'undefined') {
    htmlFrameObservers.add({ iframe, observer: null, cleanup, controller: cleanup.controller || null, slide: current.value })
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  htmlFrameObservers.add({ iframe, observer, cleanup, controller: cleanup.controller || null, slide: current.value })
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
  window.removeEventListener('pointermove', handleElementDrag)
  dragState.value = null
  draggingElementId.value = null
}
const selectElement = (id, event) => {
  event?.stopPropagation()
  if (!elementById(id)) return
  selectedElementId.value = id
  activePanel.value = 'style'
}
const selectElementFromPanel = (id) => {
  if (current.value?.html) {
    activeHtmlController()?.selectById(id)
    activePanel.value = 'style'
    return
  }
  selectElement(id)
}
const clearElementSelection = () => {
  if (current.value?.html) activeHtmlController()?.clearSelection()
  selectedElementId.value = null
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
  activePanel.value = 'content'
}
const updateElementStyle = ({ key, value }) => {
  if (current.value?.html) {
    activeHtmlController()?.updateStyle(key, value)
    return
  }
  if (!selectedElement.value) return
  selectedElement.value.style = { ...selectedElement.value.style, [key]: value }
}
const updateElementPosition = ({ key, value }) => {
  if (current.value?.html) {
    activeHtmlController()?.updatePosition(key, value)
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
}
const updateElementContent = (value) => {
  if (current.value?.html) {
    activeHtmlController()?.updateContent(value)
    return
  }
  if (!selectedElement.value) return
  const content = String(value ?? '')
  selectedElement.value.content = content
  if (selectedElement.value.target === 'title') current.value.title = content
  if (selectedElement.value.target === 'description') current.value.description = content
  if (selectedElement.value.target === 'footer') current.value.footer = content
}
const updateElementField = ({ key, value }) => {
  if (current.value?.html) {
    activeHtmlController()?.updateField(key, value)
    return
  }
  if (!selectedElement.value || !['src', 'alt'].includes(key)) return
  if (key === 'src') selectedElement.value.src = String(value || '') || createMockImageSrc(selectedElement.value.content || '课堂图片')
  if (key === 'alt') selectedElement.value.alt = String(value || '').slice(0, 80)
}
const updateElementData = (value) => {
  if (current.value?.html) {
    activeHtmlController()?.updateData(value)
    return
  }
  if (!selectedElement.value || selectedElement.value.type !== 'chart' || !Array.isArray(value)) return
  selectedElement.value.data = value.slice(0, 8).map((item, index) => ({
    label: String(item?.label || `数据${index + 1}`).slice(0, 10),
    value: Math.max(0, Math.min(100, Number(item?.value) || 0)),
  }))
}
const handleImageError = (element) => {
  if (!element || String(element.src || '').startsWith('data:image/svg+xml')) return
  element.src = createMockImageSrc(elementContent(element) || '图片加载失败')
  WorkspaceMessage.warning('图片加载失败，已恢复示例图')
}
const updateSlideField = ({ key, value }) => {
  if (!current.value) return
  current.value[key] = value
  if (current.value.html && ['title', 'description'].includes(key)) activeHtmlController()?.updatePageField(key, value)
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
  activePanel.value = 'style'
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
const openInteractiveDialog = () => {
  const slideTitle = String(current.value?.title || '本页内容').trim()
  const eyebrowParts = String(current.value?.eyebrow || '').split('·')
  interactiveForm.title = `${slideTitle} · 课堂互动`
  interactiveForm.topic = slideTitle
  interactiveForm.subject = eyebrowParts[0]?.trim() || ''
  interactiveForm.grade = ''
  interactiveForm.knowledge_points = String(current.value?.description || '').trim()
  interactiveForm.requirements = ''
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
    const knowledgePoints = interactiveForm.knowledge_points
      .split(/[,，\n]/)
      .map((item) => item.trim())
      .filter(Boolean)
    const response = unwrapResponse(await generateInteractiveModule({
      title,
      topic,
      module_type: interactiveForm.module_type,
      subject: interactiveForm.subject.trim() || undefined,
      grade: interactiveForm.grade.trim() || undefined,
      knowledge_points: knowledgePoints,
      requirements: interactiveForm.requirements.trim() || undefined,
      theme: interactiveForm.theme.trim() || undefined,
      embed_mode: interactiveForm.embed_mode,
      language: interactiveForm.language || 'zh-CN',
    }))
    if (!response?.html) throw new Error('互动模块接口未返回可预览的 HTML 内容')
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
    WorkspaceMessage.success('互动模块已作为独立页面插入，正在自动保存')
  } else {
    if (current.value?.html) {
      const inserted = activeHtmlController()?.insertInteractive?.(module)
      if (!inserted) return WorkspaceMessage.warning('HTML 页面正在加载，请稍后再试')
      appendInteractiveAsset(current.value, module)
      interactivePreviewVisible.value = false
      interactiveModule.value = null
      WorkspaceMessage.success('互动模块已插入当前 HTML 页面，正在自动保存')
      return
    }
    current.value.elements.push(element)
    appendInteractiveAsset(current.value, module)
    selectedElementId.value = element.id
    activePanel.value = 'style'
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
  return {
    ...defaultSlide(index + 1),
    ...content,
    elements: normalizeElements(elements),
    pageId: page.id || page.page_id || content.pageId || content.page_id,
    componentId: page.id || page.component_id || page.page_id || content.componentId,
    pageVersion: Number(page.page_version || content.pageVersion || content.page_version || 1),
    clientVersion: page.client_version || content.clientVersion || workspaceClientVersion,
    autosave: page.autosave ?? content.autosave ?? false,
    dirty: page.dirty ?? content.dirty ?? false,
    lastSavedAt: page.last_saved_at || content.lastSavedAt || null,
    title: content.title || page.page_title || page.title || `第 ${index + 1} 页`,
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
      html: html.trim(),
      elements: [],
    }
    slides.splice(selectedSlide.value, 1, nextSlide)
    htmlSelectionRestoreKey.value = ''
    htmlElements.value = []
    htmlSelectedElementId.value = null
    htmlSelectedElement.value = null
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
    WorkspaceMessage.warning(error?.message || '页面详情加载失败，已使用页面列表数据')
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
    WorkspaceMessage.warning(error?.message || '项目元数据同步失败，页面内容仍可保存')
  }
}
const loadProject = async () => {
  if (!projectId.value) return
  hydratingProject.value = true
  try {
    project.value = unwrapResponse(await getProject(projectId.value))
    let pages = []
    try {
      const listedPages = unwrapResponse(await listProjectPages(projectId.value))
      pages = Array.isArray(listedPages) ? listedPages : []
    } catch (error) {
      pages = Array.isArray(project.value?.pages) ? project.value.pages : []
      WorkspaceMessage.warning(error?.message || '页面列表加载失败，已使用项目详情中的页面')
    }
    loadedPageDetailIds.clear()
    slides.splice(0, slides.length, ...(pages.length ? pages.map(pageToSlide) : [defaultSlide()]))
    selectedSlide.value = 0
  } catch (error) { WorkspaceMessage.error(error?.message || '项目内容加载失败') } finally { hydratingProject.value = false }
  await loadProjectPageDetail(0)
  await syncProjectMetadataIfNeeded()
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
const pagePayloadForSlide = (slide, index, overrides = {}) => ({
  page_order: index + 1,
  page_type: index === 0 ? 'cover' : 'content',
  page_title: slide.title,
  page_content: JSON.stringify(slide),
  components: JSON.stringify(slide.elements || []),
  client_version: slide.clientVersion || workspaceClientVersion,
  autosave: false,
  dirty: Boolean(slide.dirty),
  ...overrides,
})
const batchCreateProjectPages = async (targetProjectId, slideList) => {
  for (const slide of slideList) await validateSlideComponents(slide)
  const result = unwrapResponse(await batchSaveProjectPages(targetProjectId, {
    client_version: workspaceClientVersion,
    autosave: false,
    pages: slideList.map((slide, index) => pagePayloadForSlide(slide, index)),
  }))
  const savedPages = Array.isArray(result) ? result : result?.pages || result?.items || []
  savedPages.forEach((page, index) => {
    const slide = slideList[index]
    if (!slide) return
    slide.pageId = page.id || page.page_id
    slide.componentId = slide.pageId
    slide.pageVersion = Number(page.page_version || 1)
    slide.clientVersion = page.client_version || slide.clientVersion || workspaceClientVersion
    slide.dirty = Boolean(page.dirty)
    slide.lastSavedAt = page.last_saved_at || null
  })
  return savedPages
}

/**
 * 将社区测试案例真正落成项目和页面记录。
 * 预览入口只负责提供可重复的测试数据，后续编辑与导出均使用项目 ID 访问 API。
 */
const bootstrapTestCaseProject = async () => {
  if (!import.meta.env.DEV || route.query.preview !== '1' || !route.query.testCase || projectId.value) return
  testCaseBootstrapping.value = true
  autosaveState.value = '正在创建测试项目…'
  try {
    const created = unwrapResponse(await createProject({
      project_name: String(route.query.templateTitle || '临时测试案例'),
      project_type: 'mixed',
      status: 'editing',
    }))
    const createdId = created?.id || created?.project_id
    if (!createdId) throw new Error('项目创建接口未返回项目 ID')

    await batchCreateProjectPages(createdId, slides)

    await router.replace({ query: { ...route.query, projectId: String(createdId) } })
    project.value = { ...created, id: createdId }
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
      messages.push({ role: 'assistant', text: `已载入 ${cachedDraft.slides.length} 页 HTML PPT 草稿。` })
      return
    } catch {
      // Ignore an invalid session draft and generate a fresh presentation below.
    }
  }

  runStatus.value = 'running'
  runProgress.value = 6
  runStage.value = '正在读取已确认的大纲'

  try {
    const planData = unwrapResponse(await getAiPlan(sessionId.value)) || {}
    const outline = normalizeOutlinePayload(planData)
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
    runStage.value = '正在装载 HTML 页面'
    applyGeneratedPresentation(response)
  } catch (error) {
    runStatus.value = 'failed'
    runProgress.value = 0
    runStage.value = 'HTML PPT 生成失败'
    generationError.value = generationErrorMessage(error)
    messages.push({ role: 'assistant', text: generationError.value })
    WorkspaceMessage.error(generationError.value)
  }
}
const retryPresentationGeneration = () => { void startRun() }
const submitRevision = async () => {
  const instruction = prompt.value.trim(); if (!instruction) return
  if (revisionSubmitting.value) return
  messages.push({ role: 'user', text: instruction }); prompt.value = ''
  revisionSubmitting.value = true
  try {
    let applied = false
    if (current.value?.html) {
      const selectedElement = htmlSelectedElement.value
      const response = unwrapResponse(await modifyPresentationSlide({
        ...(presentationId.value ? { presentation_id: presentationId.value } : {}),
        slide_no: selectedSlide.value + 1,
        current_html: current.value.html,
        instruction,
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
        },
        theme: String(routeQueryValue(route.query.pptTheme) || presentationMetadata.value?.theme || current.value.theme || '').trim() || undefined,
        keep_style: true,
      }))
      if (showClarificationForResponse(response, projectId.value ? 'project' : 'session')) return
      applied = applyGeneratedPage(response)
      if (!applied) throw new Error('AI 修改接口未返回有效的 HTML 页面')
      messages.push({ role: 'assistant', text: String(response?.change_summary || '已根据修改要求更新当前页面，页面元素仍可继续选中和编辑。') })
      WorkspaceMessage.success('页面内容已更新')
      return
    }
    if (projectId.value) {
      const response = unwrapResponse(await reviseProjectWithAi(projectId.value, { target_type: 'slide', target_id: String(current.value.componentId || selectedSlide.value + 1), instruction, context: JSON.stringify(current.value) }))
      applied = applyGeneratedPage(response)
      if (showClarificationForResponse(response, 'project')) return
    }
    else if (sessionId.value) {
      const response = unwrapResponse(await sendAiSessionMessage(sessionId.value, { message: instruction, messages: JSON.stringify([{ role: 'user', content: instruction }]) }))
      if (showClarificationForResponse(response, 'session')) return
    }
    messages.push({ role: 'assistant', text: applied ? '已根据修改要求更新当前页面，页面元素仍可继续选中和编辑。' : '已收到修改要求，正在结合当前页面内容进行调整。' }); WorkspaceMessage.success(applied ? '页面内容已更新' : '修改要求已提交')
  } catch (error) { messages.push({ role: 'assistant', text: '修改请求暂未提交成功，请稍后重试。' }); WorkspaceMessage.error(error?.message || '修改请求失败') } finally { revisionSubmitting.value = false }
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
      applyGeneratedPage(response)
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
  await bootstrapTestCaseProject()
  await loadProject()
  if (!projectId.value && (sessionId.value || presentationFixtureMode.value)) await startRun()
  window.addEventListener('keydown', handleWorkspaceKeydown)
})
onBeforeUnmount(() => { htmlFrameObservers.forEach(({ observer, cleanup }) => { observer?.disconnect(); cleanup?.() }); htmlFrameObservers.clear(); clearPreviewFrameObservers(); stopElementDrag(); cancelCanvasPlacement(); workspaceMessageInstance?.close(); window.removeEventListener('keydown', handleWorkspaceKeydown) })
const currentPagePayload = (slide = current.value, index = selectedSlide.value, overrides = {}) => pagePayloadForSlide(slide, index, {
  autosave: true,
  dirty: false,
  ...overrides,
})
const persistCurrentSlide = async () => {
  if (!projectId.value || savingPage.value || hydratingProject.value) return
  const slideIndex = selectedSlide.value
  const slide = slides[slideIndex]
  if (!slide) return
  savingPage.value = true; autosaveState.value = '保存中…'
  try {
    await validateSlideComponents(slide)
    const payload = currentPagePayload(slide, slideIndex)
    const response = slide.pageId
      ? await saveProjectPage(projectId.value, slide.pageId, { ...payload, expected_page_version: Number(slide.pageVersion || 1) })
      : await createProjectPage(projectId.value, payload)
    const saved = unwrapResponse(response)
    if (slides[slideIndex] === slide) {
      slide.pageId = saved?.id || saved?.page_id || slide.pageId
      slide.componentId = slide.pageId
      slide.pageVersion = Number(saved?.page_version || slide.pageVersion || 1)
      slide.clientVersion = saved?.client_version || slide.clientVersion || workspaceClientVersion
      slide.autosave = Boolean(saved?.autosave ?? true)
      slide.dirty = Boolean(saved?.dirty)
      slide.lastSavedAt = saved?.last_saved_at || slide.lastSavedAt || null
    }
    autosaveState.value = '已保存'
  } catch (error) {
    autosaveState.value = '保存失败'
    const message = error?.response?.data?.message || error?.message || '页面保存失败'
    WorkspaceMessage.error(message.includes('Version conflict') || message.includes('版本冲突') ? '页面版本已变化，请刷新页面后重试' : message)
  } finally { savingPage.value = false }
}
const loadVersions = async () => {
  if (!projectId.value) return WorkspaceMessage.warning('演示项目不支持版本管理')
  versionLoading.value = true; versionDialogVisible.value = true
  try { const result = unwrapResponse(await listProjectVersions(projectId.value, { page: 1, size: 30 })); versions.value = result?.records || result?.list || result?.items || [] }
  catch (error) { WorkspaceMessage.error(error?.message || '版本历史加载失败') } finally { versionLoading.value = false }
}
const createVersion = async () => { if (!projectId.value) return; try { await saveProjectVersion(projectId.value, { description: `保存第 ${selectedSlide.value + 1} 页调整` }); autosaveState.value = '已创建版本'; await loadVersions(); WorkspaceMessage.success('项目版本已保存') } catch (error) { WorkspaceMessage.error(error?.message || '版本保存失败') } }
const showVersionDiff = async (version) => { try { versionDiff.value = unwrapResponse(await getProjectVersionDiff(projectId.value, version.id || version.version_id)) } catch (error) { WorkspaceMessage.error(error?.message || '差异加载失败') } }
const restoreVersion = async (version) => { try { await restoreProjectVersion(projectId.value, version.id || version.version_id); WorkspaceMessage.success('已恢复历史版本'); await loadVersions() } catch (error) { WorkspaceMessage.error(error?.message || '版本恢复失败') } }
const grantPermission = async () => { const userId = Number(permissionUserId.value); if (!Number.isInteger(userId) || userId <= 0) return WorkspaceMessage.warning('请输入有效用户 ID'); try { await addProjectPermission(projectId.value, { user_id: userId }); permissionUserId.value = ''; permissionDialogVisible.value = false; WorkspaceMessage.success('协作者已添加') } catch (error) { WorkspaceMessage.error(error?.message || '授权失败') } }
watch(slides, () => { if (!projectId.value || testCaseBootstrapping.value || hydratingProject.value || savingPage.value) return; autosaveState.value = '待保存'; clearTimeout(autosaveTimer); autosaveTimer = setTimeout(persistCurrentSlide, 700) }, { deep: true })
watch(selectedSlide, () => {
  selectedElementId.value = null
  htmlSelectionRestoreKey.value = ''
  htmlElements.value = []
  htmlSelectedElementId.value = null
  htmlSelectedElement.value = null
})
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const workspaceFlowQuery = (targetProjectId = projectId.value) => ({
  ...(route.query.preview ? { preview: '1' } : {}),
  ...(route.query.testCase ? { testCase: route.query.testCase } : {}),
  ...(route.query.templateTitle ? { templateTitle: route.query.templateTitle } : {}),
  ...(route.query.pptTheme ? { pptTheme: route.query.pptTheme } : {}),
  ...(targetProjectId ? { projectId: String(targetProjectId) } : {}),
  // 导出中心消费此标记后会自动完成“快照 → 预检 → 创建任务”。
  autoExport: '1',
})
const goHome = () => router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
const createWorkspaceProjectForExport = async () => {
  autosaveState.value = '正在创建项目…'
  const created = unwrapResponse(await createProject({
    project_name: String(project.value?.project_name || route.query.templateTitle || `${current.value.title}教学课件`),
    project_type: 'mixed',
    status: 'editing',
  }))
  const createdId = created?.id || created?.project_id
  if (!createdId) throw new Error('项目创建接口未返回项目 ID')

  await batchCreateProjectPages(createdId, slides)
  project.value = { ...created, id: createdId }
  autosaveState.value = '已保存 · 项目已落库'
  return String(createdId)
}
const exportProject = async () => {
  clearTimeout(autosaveTimer)
  try {
    if (import.meta.env.DEV) {
      const { ensureDevelopmentPreviewSession } = await import('../utils/previewSession.js')
      await ensureDevelopmentPreviewSession(true)
    }
    const targetProjectId = projectId.value ? String(projectId.value) : await createWorkspaceProjectForExport()
    if (projectId.value) await persistCurrentSlide()
    await router.push({ path: '/main/exports', query: workspaceFlowQuery(targetProjectId) })
  } catch (error) {
    autosaveState.value = '导出准备失败'
    WorkspaceMessage.error(error?.message || '项目保存失败，无法创建导出任务')
  }
}
const addSlide = () => { slides.push({ ...defaultSlide(slides.length + 1), eyebrow: '新建内容' }); selectedSlide.value = slides.length - 1 }
const copySlide = () => {
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
  selectedSlide.value++
}
const removeSlide = async () => {
  if (slides.length === 1) return WorkspaceMessage.warning('课件至少保留一页')
  const slide = slides[selectedSlide.value]
  if (projectId.value && slide?.pageId) {
    try { await deleteProjectPage(projectId.value, slide.pageId) }
    catch (error) { WorkspaceMessage.error(error?.message || '页面删除失败'); return }
  }
  slides.splice(selectedSlide.value, 1)
  selectedSlide.value = Math.max(0, selectedSlide.value - 1)
}
const sendRevision = () => submitRevision()
const selectSlide = (index) => { selectedSlide.value = index; selectedElementId.value = null; activePanel.value = 'content'; loadProjectPageDetail(index) }
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
      @preview="openPreview"
      @generate-interactive="openInteractiveDialog"
      @export="exportProject"
      @tool-select="handleToolSelect"
    />

    <div class="workspace-grid">
      <aside class="assistant-panel" aria-label="AI 教学助手">
        <header><div class="assistant-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div></header>
        <div class="assistant-actions"><el-button type="primary" plain @click="openInteractiveDialog">生成互动模块</el-button></div>
        <section class="conversation"><article v-for="(message, index) in messages" :key="index" :class="['message', message.role]"><span v-if="message.role === 'assistant'">智</span><p>{{ message.text }}</p></article></section>
        <footer class="composer"><el-input v-model="prompt" type="textarea" :rows="3" resize="none" :disabled="revisionSubmitting" placeholder="例如：把提问改得更有启发性" @keydown.ctrl.enter="sendRevision" /><div><span>{{ revisionSubmitting ? 'AI 正在修改当前页…' : 'Ctrl + Enter 发送' }}</span><el-button type="primary" circle :icon="Promotion" :loading="revisionSubmitting" :disabled="revisionSubmitting || !prompt.trim()" aria-label="发送修改" @click="sendRevision" /></div></footer>
      </aside>

      <section class="editor-stage">
        <aside class="slide-rail" aria-label="课件页面列表">
          <button v-for="(slide, index) in slides" :key="`${slide.title}-${index}`" :class="{ active: selectedSlide === index }" @click="selectSlide(index)">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="thumbnail" :style="{ '--thumb': themes.find((item) => item.id === slide.theme)?.color }"><i></i><b>{{ slide.title }}</b></div>
          </button>
          <el-button text :icon="Plus" @click="addSlide">添加页面</el-button>
        </aside>
        <main class="canvas-area" @click="handleCanvasAreaClick">
          <div class="canvas-meta">
            <span>第 {{ selectedSlide + 1 }} 页，共 {{ slides.length }} 页</span>
            <span v-if="current.html" class="canvas-placement-status"><b>拖动元素 · 双击文字编辑</b><small>选中后可缩放、旋转、复制或删除</small></span>
            <span v-if="placementMode" class="canvas-placement-status"><b>{{ placementInstruction }}</b><small>Esc 取消</small></span>
            <span>16:9 · 自适应窗口</span>
          </div>
          <article v-if="current.html" class="slide-canvas html-slide-canvas" :style="{ '--canvas-zoom': canvasZoom / 100 }" :aria-label="`${current.title} HTML PPT`">
            <iframe class="editable-html-frame" :srcdoc="htmlCanvasFrameSource" sandbox="allow-same-origin" :title="`${current.title} HTML PPT`" @load="fitHtmlFrame"></iframe>
          </article>
          <article v-else class="slide-canvas" :class="[`layout-${current.layout}`, { 'is-placing': placementMode }]" :style="{ '--accent': theme.color, '--canvas-zoom': canvasZoom / 100 }" @pointerdown="startCanvasPlacement" @pointermove="handleCanvasPlacementMove" @click="handleSlideCanvasClick">
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
                <span class="widget-icon">{{ element.type === 'audio' ? '♫' : element.type === 'video' ? '▶' : element.type === 'h5' ? 'H5' : '⌁' }}</span>
                <div><strong>{{ elementContent(element) || element.name }}</strong><small>{{ elementTypeLabels[element.type] }}</small></div>
                <button v-if="element.type === 'h5' && element.html" type="button" class="widget-action widget-action-button" @click.stop="previewInteractiveElement(element)">预览</button>
                <span v-else class="widget-action">{{ element.type === 'audio' ? '播放' : element.type === 'video' ? '预览' : '打开' }}</span>
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
              <span class="widget-icon">{{ placementPreviewElement.type === 'audio' ? '♫' : placementPreviewElement.type === 'video' ? '▶' : placementPreviewElement.type === 'h5' ? 'H5' : '⌁' }}</span>
              <div><strong>{{ elementContent(placementPreviewElement) || placementPreviewElement.name }}</strong><small>{{ elementTypeLabels[placementPreviewElement.type] }}</small></div>
              <span class="widget-action">{{ placementPreviewElement.type === 'audio' ? '播放' : placementPreviewElement.type === 'video' ? '预览' : '打开' }}</span>
            </div>
            <div v-else-if="placementPreviewElement?.type === 'table'" class="workspace-widget table-widget canvas-element placement-element-preview" :style="placementPreviewStyle" aria-hidden="true">
              <strong>{{ elementContent(placementPreviewElement) || '数据表格' }}</strong>
              <div class="mock-table-grid"><span v-for="(cell, cellIndex) in (placementPreviewElement.data?.flat() || [])" :key="`placement-cell-${cellIndex}`">{{ cell }}</span></div>
            </div>
          </article>
          <div class="canvas-controls" @click.stop>
            <button type="button" aria-label="缩小画布" title="缩小画布" :disabled="canvasZoom <= CANVAS_ZOOM_MIN" @click="adjustCanvasZoom(-CANVAS_ZOOM_STEP)">−</button>
            <span class="canvas-zoom-field" role="group" aria-label="画布缩放比例">
              <input v-model="canvasZoomInput" class="canvas-zoom-input" type="number" min="50" max="200" step="1" inputmode="numeric" aria-label="输入画布缩放比例" title="输入 50–200 的缩放比例" @change="commitCanvasZoomInput" @blur="commitCanvasZoomInput" @keyup.enter.prevent="commitCanvasZoomInput" @keydown.esc.prevent="resetCanvasZoom">
              <small>%</small>
            </span>
            <button type="button" aria-label="放大画布" title="放大画布" :disabled="canvasZoom >= CANVAS_ZOOM_MAX" @click="adjustCanvasZoom(CANVAS_ZOOM_STEP)">+</button>
            <button type="button" aria-label="全屏预览" title="全屏预览" @click="openPreview"><el-icon><FullScreen /></el-icon></button>
          </div>
        </main>
      </section>

      <WorkspacePropertiesPanel
        :slide="current"
        :elements="workspaceElements"
        :selected-element="workspaceSelectedElement"
        :selected-element-id="workspaceSelectedElementId"
        :active-panel="activePanel"
        :themes="themes"
        :layouts="layouts"
        :page-number="selectedSlide + 1"
        @update:active-panel="activePanel = $event"
        @update-element-style="updateElementStyle"
        @update-element-position="updateElementPosition"
        @update-element-content="updateElementContent"
        @update-element-field="updateElementField"
        @update-element-data="updateElementData"
        @update-slide-field="updateSlideField"
        @select-element="selectElementFromPanel"
        @clear-element="clearElementSelection"
        @copy-element="copyElement"
        @delete-element="removeElement"
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
              <iframe :srcdoc="slide.html" sandbox="allow-scripts" :title="`${slide.title} HTML PPT 预览`" class="preview-html-frame" @load="fitPreviewHtmlFrame"></iframe>
            </div>
            <article v-else class="slide-canvas preview-slide" :class="`layout-${slide.layout}`" :style="{ '--accent': themeForSlide(slide).color }">
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
                <div v-else-if="['audio', 'video', 'h5', 'subject'].includes(element.type)" class="workspace-widget" :class="[`widget-${element.type}`, previewElementClass(element)]" :style="previewElementStyle(element, slide)"><span class="widget-icon">{{ element.type === 'audio' ? '♫' : element.type === 'video' ? '▶' : element.type === 'h5' ? 'H5' : '⌁' }}</span><div><strong>{{ previewElementContent(element, slide) || element.name }}</strong><small>{{ elementTypeLabels[element.type] }}</small></div><span class="widget-action">{{ element.type === 'audio' ? '播放' : element.type === 'video' ? '预览' : '打开' }}</span></div>
                <div v-else-if="element.type === 'table'" class="workspace-widget table-widget" :class="previewElementClass(element)" :style="previewElementStyle(element, slide)"><strong>{{ previewElementContent(element, slide) || '数据表格' }}</strong><div class="mock-table-grid"><span v-for="(cell, cellIndex) in (element.data?.flat() || [])" :key="`preview-${slideIndex}-${element.id}-${cellIndex}`">{{ cell }}</span></div></div>
              </template>
            </article>
          </section>
        </div>
      </div>
      <template #footer><el-button @click="closePreview">继续编辑</el-button></template>
    </el-dialog>
    <el-dialog v-model="interactiveDialogVisible" title="生成互动模块" width="min(720px, 92vw)" destroy-on-close>
      <p class="dialog-hint">调用互动模块生成服务，生成后可以先预览，再插入当前页面或作为独立页面保存。</p>
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
      </div>
    </div>
    <div v-else-if="runStatus === 'failed'" class="generation-overlay generation-overlay-error" role="alert">
      <div class="generation-state-card">
        <small class="generation-kicker">AI HTML PPT</small>
        <h2>课件生成失败</h2>
        <p>{{ generationError || '暂时无法生成 HTML PPT。' }}</p>
        <div class="generation-actions">
          <el-button type="primary" @click="retryPresentationGeneration">重新生成</el-button>
          <el-button @click="goHome">返回教学助手</el-button>
        </div>
      </div>
    </div>
    <div v-if="projectId" class="project-utilities"><span>{{ autosaveState }}</span><el-button text size="small" @click="createVersion">保存版本</el-button><el-button text size="small" @click="loadVersions">版本历史</el-button><el-button text size="small" @click="permissionDialogVisible = true">协作授权</el-button></div>
    <el-dialog v-model="versionDialogVisible" title="项目版本历史" width="min(680px, 92vw)"><div v-loading="versionLoading" class="version-list"><article v-for="version in versions" :key="version.id || version.version_id"><div><strong>版本 {{ version.version_number || version.id }}</strong><p>{{ version.description || '未填写说明' }}</p></div><div><el-button text size="small" @click="showVersionDiff(version)">查看差异</el-button><el-button text size="small" type="primary" @click="restoreVersion(version)">恢复此版本</el-button></div></article><p v-if="versionDiff" class="version-diff">{{ versionDiff.summary || JSON.stringify(versionDiff.differences || versionDiff) }}</p><el-empty v-if="!versionLoading && !versions.length" description="暂无历史版本" /></div><template #footer><el-button @click="versionDialogVisible = false">关闭</el-button></template></el-dialog>
    <el-dialog v-model="permissionDialogVisible" title="添加协作者" width="420px"><p class="dialog-hint">协作者将获得项目编辑权限。</p><el-input v-model="permissionUserId" inputmode="numeric" placeholder="输入用户 ID" /><template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" @click="grantPermission">确认授权</el-button></template></el-dialog>
</template>

<style scoped>
.workspace{height:100dvh;display:grid;grid-template-rows:60px minmax(0,1fr);overflow:hidden;background:var(--zh-background-light)}.workspace-grid{min-height:0;display:grid;grid-template-columns:286px minmax(500px,1fr) 270px}.assistant-panel,.properties{min-height:0;background:var(--zh-background-primary)}.assistant-panel{display:flex;flex-direction:column;border-right:1px solid var(--zh-line-border)}.assistant-panel>header{display:flex;align-items:center;gap:9px;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.assistant-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:var(--zh-radius8);color:#fff;background:var(--zh-gradient-blue);font-weight:700}.assistant-panel header div:last-child{display:flex;flex-direction:column}.assistant-panel header strong{font-size:13px}.assistant-panel header span{margin-top:2px;color:var(--zh-text-caption);font-size:10px}.conversation{flex:1;padding:16px;overflow:auto}.message{display:flex;align-items:flex-start;gap:8px;margin-bottom:16px}.message>span{display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:6px;color:#fff;background:var(--zh-theme-primary);font-size:10px}.message p{margin:0;padding:10px 12px;border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-answer-card);font-size:12px;line-height:1.65}.message.user{justify-content:flex-end}.message.user p{color:var(--zh-text-primary);background:var(--zh-background-user-query)}.composer{padding:12px;border-top:1px solid var(--zh-line-border)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:8px}.composer span{color:var(--zh-text-caption);font-size:10px}.composer :deep(.el-textarea__inner){background:var(--zh-background-light);box-shadow:none}.editor-stage{display:grid;grid-template-columns:116px minmax(0,1fr);min-width:0}.slide-rail{padding:12px 9px;overflow:auto;border-right:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.slide-rail>button{display:grid;grid-template-columns:18px 1fr;gap:4px;width:100%;margin-bottom:10px;padding:3px;border:1px solid transparent;border-radius:6px;color:var(--zh-text-caption);background:transparent;text-align:left;cursor:pointer}.slide-rail>button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.thumbnail{display:flex;flex-direction:column;justify-content:center;gap:5px;height:54px;padding:8px;border-radius:4px;background:var(--zh-background-light)}.thumbnail i{width:65%;height:3px;background:var(--thumb)}.thumbnail b{overflow:hidden;color:var(--zh-text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}.slide-rail :deep(.el-button){width:100%;justify-content:flex-start}.canvas-area{position:relative;display:grid;place-items:center;min-width:0;padding:44px 34px;overflow:auto;background-color:#eef0f4;background-image:radial-gradient(#c9ced7 1px,transparent 1px);background-size:18px 18px}.canvas-meta{position:absolute;top:12px;inset-inline:20px;display:flex;justify-content:space-between;color:#7c8491;font-size:10px}.slide-canvas{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;padding:clamp(28px,4vw,52px);color:#102d54;background:#f9fbff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.slide-canvas:after{content:'';position:absolute;top:-18%;right:-8%;width:42%;aspect-ratio:1;border-radius:50%;background:color-mix(in srgb,var(--accent) 16%,white)}.slide-eyebrow,.slide-canvas h1,.slide-canvas>p,.theorem{position:relative;z-index:1}.slide-eyebrow{color:var(--accent);font:600 10px var(--zh-font-number);letter-spacing:.12em}.slide-canvas h1{max-width:76%;margin:18px 0 0;font-size:clamp(26px,3vw,40px);line-height:1.2;letter-spacing:-.04em}.slide-canvas>p{max-width:64%;margin:12px 0;color:#607491;font-size:clamp(11px,1.2vw,15px);line-height:1.65}.theorem{display:grid;grid-template-columns:.8fr 1.2fr;align-items:center;gap:28px;width:76%;margin:28px auto}.triangle{position:relative;width:104px;height:104px;border-right:5px solid var(--accent);border-bottom:5px solid var(--accent);transform:skewY(-35deg) rotate(-10deg)}.triangle i{position:absolute;color:var(--accent);font-style:normal;font-weight:700;transform:skewY(35deg) rotate(10deg)}.triangle i:nth-child(1){bottom:-22px;left:36px}.triangle i:nth-child(2){top:40px;right:-18px}.triangle i:nth-child(3){top:-22px;left:8px}.formula{display:grid;grid-template-columns:auto 24px auto;align-items:center;font-family:var(--zh-font-number)}.formula span,.formula strong{font-size:clamp(22px,3vw,36px)}.formula em{color:#7c8da4;font-style:normal}.formula strong{color:var(--accent)}.formula small{grid-column:1/-1;margin-top:8px;color:#7c8da4;font-size:10px}.slide-canvas footer{position:absolute;z-index:1;right:0;bottom:0;left:0;display:grid;grid-template-columns:110px 1fr;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54)}.slide-canvas footer p{margin:0;font-size:10px;line-height:1.5}.layout-重点陈述 h1{margin-top:54px;font-size:clamp(34px,4.4vw,52px)}.canvas-controls{position:absolute;right:18px;bottom:14px;display:flex;overflow:hidden;border-radius:var(--zh-radius8);background:var(--zh-background-capsule);box-shadow:var(--zh-shadow1)}.canvas-controls button,.canvas-controls span{padding:6px 9px;border:0;color:var(--zh-text-secondary);background:transparent;font-size:11px}.canvas-controls button{cursor:pointer}.properties{overflow:auto;border-left:1px solid var(--zh-line-border)}.properties>header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties header strong{font-size:13px}.properties header span{color:var(--zh-text-caption);font-size:10px}.tabs{display:grid;grid-template-columns:repeat(3,1fr);padding:10px 14px 0;border-bottom:1px solid var(--zh-line-parting)}.tabs button{padding:8px;border:0;border-bottom:2px solid transparent;color:var(--zh-text-caption);background:transparent;cursor:pointer}.tabs button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme)}.properties section{padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties label{display:block;margin:0 0 10px;color:var(--zh-text-secondary);font-size:11px;font-weight:600}.properties label:not(:first-child){margin-top:18px}.theme-picker{display:flex;gap:12px}.theme-picker button{width:24px;height:24px;border:2px solid var(--zh-background-primary);border-radius:50%;box-shadow:0 0 0 1px var(--zh-line-border);cursor:pointer}.theme-picker button.selected{outline:2px solid var(--zh-text-theme);outline-offset:2px}.layout-picker{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.layout-picker button{display:grid;grid-template-rows:26px auto;gap:4px;min-height:66px;padding:7px 4px;border:1px solid var(--zh-line-border);border-radius:6px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:9px;cursor:pointer}.layout-picker button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.layout-picker i{display:block;width:70%;height:4px;margin:auto;background:var(--zh-line-theme50)}.layout-picker i:nth-child(2){width:48%}.page-actions{display:grid;gap:8px}.page-actions :deep(.el-button){justify-content:flex-start;margin:0}.assistant-tip{display:flex;gap:8px;margin:16px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.assistant-tip p,.hint{margin:0;color:var(--zh-text-secondary);font-size:10px;line-height:1.6}.preview{display:grid;place-items:center;padding:18px;background:#eef0f4}.preview-slide{width:min(780px,100%)}.preview-formula{width:max-content;margin:50px auto}.preview-dialog :deep(.el-dialog__body){padding:0}@media(max-width:1120px){.workspace-grid{grid-template-columns:250px minmax(460px,1fr)}.properties{display:none}}@media(max-width:820px){.workspace-grid{grid-template-columns:1fr}.assistant-panel{display:none}.editor-stage{grid-template-columns:88px minmax(0,1fr)}}
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

.slide-canvas::after {
  pointer-events: none;
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

.widget-action {
  margin-left: auto;
  padding: 4px 7px;
  border-radius: 999px;
  color: var(--widget-color, var(--accent));
  background: rgb(255 255 255 / 70%);
  font-size: 9px;
  white-space: nowrap;
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

.canvas-area .slide-canvas {
  transform: scale(var(--canvas-zoom, 1));
  transform-origin: center center;
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
</style>
