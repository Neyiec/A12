<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FullScreen, Plus, Promotion, VideoPlay } from '@element-plus/icons-vue'
import { addProjectComponent, addProjectPermission, createAiRun, getAiRun, getProject, getProjectVersionDiff, listProjectVersions, restoreProjectVersion, reviseProjectWithAi, saveProjectVersion, sendAiSessionMessage, updateProjectComponent } from '../apis/teacher'
import IntentClarificationDialog from './IntentClarificationDialog.vue'
import CreationWorkspaceToolbar from './CreationWorkspaceToolbar.vue'
import WorkspacePropertiesPanel from './WorkspacePropertiesPanel.vue'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const selectedSlide = ref(0)
const activeTool = ref('')
const selectedElementId = ref(null)
const draggingElementId = ref(null)
const activePanel = ref('style')
const previewVisible = ref(false)
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
  { id: 'visual', type: 'formula', name: '公式', target: 'formula', content: 'a² + b² = c²', position: { x: 8, y: 47, width: 48, height: 28, rotation: 0, zIndex: 3 }, style: { color: '#2563eb', fontSize: 32, fontWeight: 700, opacity: 100, textAlign: 'center', lineHeight: 1.2 } },
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
const theme = computed(() => themes.find((item) => item.id === current.value.theme) || themes[0])
const unwrapResponse = (response) => response?.data || response
const sessionId = computed(() => route.query.sessionId)
const projectId = computed(() => route.query.projectId)
const project = ref(null)
const defaultSlide = (index = 1) => ({ title: `新建页面 ${index}`, eyebrow: '教学内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue', elements: createMockElements() })
const parseJson = (value, fallback = {}) => { try { return typeof value === 'string' ? JSON.parse(value) : (value || fallback) } catch { return fallback } }
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
const normalizeElements = (rawElements) => {
  const parsed = typeof rawElements === 'string' ? parseJson(rawElements, []) : rawElements
  const root = Array.isArray(parsed) && parsed.length === 1 && parsed[0]?.elements ? parsed[0] : parsed
  const nested = Array.isArray(root) ? root : (root?.elements ?? root?.components ?? root?.items ?? [])
  const source = typeof nested === 'string' ? parseJson(nested, []) : nested
  if (!Array.isArray(source) || !source.length) return createMockElements()
  return source.map((element, index) => {
    const type = normalizeElementType(element)
    const rawId = element?.id ?? element?.element_id ?? element?.component_id
    const preset = allElementPresets.find((item) => item.id === rawId) || allElementPresets.find((item) => item.type === type) || elementPresets[0]
    const rawPosition = element?.position || element?.bounds || element?.rect || {}
    const content = extractElementContent(element) || readableElementContent(preset.content)
    return {
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
const elementStyleFromElement = (element) => {
  const style = element?.style || {}
  const position = element?.position || {}
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
  if (element?.type === 'formula') result['--element-color'] = style.color || theme.value.color
  if (element?.type === 'shape') {
    result['--element-color'] = style.fillColor || theme.value.color
    result['--element-border-color'] = style.borderColor || style.fillColor || theme.value.color
    result['--element-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : undefined
    result['--element-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : undefined
  }
  if (element?.type === 'image') {
    result['--element-color'] = style.tintColor || theme.value.color
    result['--element-border-color'] = style.borderColor || '#bfdbfe'
    result['--element-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--element-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '14px'
    result['--element-object-fit'] = style.objectFit || 'cover'
  }
  if (element?.type === 'chart') {
    result['--chart-color'] = style.color || theme.value.color
    result['--chart-background'] = style.backgroundColor || '#eff6ff'
    result['--chart-border-color'] = style.borderColor || '#bfdbfe'
    result['--chart-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--chart-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '14px'
  }
  if (['audio', 'video', 'table', 'h5', 'subject'].includes(element?.type)) {
    result['--widget-color'] = style.color || theme.value.color
    result['--widget-background'] = style.backgroundColor || '#eff6ff'
    result['--widget-border-color'] = style.borderColor || '#bfdbfe'
    result['--widget-border-width'] = style.borderWidth !== undefined ? `${style.borderWidth}px` : '1px'
    result['--widget-border-radius'] = style.borderRadius !== undefined ? `${style.borderRadius}px` : '12px'
  }
  return result
}
const elementStyle = (id) => elementStyleFromElement(elementById(id))
const elementContent = (element) => {
  if (!element) return ''
  if (element.target === 'title') return current.value?.title || element.content || ''
  if (element.target === 'description') return current.value?.description || element.content || ''
  if (element.target === 'footer') return current.value?.footer || element.content || '在观察、猜想与验证中理解核心概念，并用它解决简单的实际问题。'
  return extractElementContent(element)
}
const selectedElementPanel = computed(() => {
  const element = selectedElement.value
  return element ? { ...element, content: elementContent(element), position: { ...(element.position || {}) }, style: { ...(element.style || {}) } } : null
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
const selectElementFromPanel = (id) => selectElement(id)
const clearElementSelection = () => { selectedElementId.value = null }
const updateElementStyle = ({ key, value }) => {
  if (!selectedElement.value) return
  selectedElement.value.style = { ...selectedElement.value.style, [key]: value }
}
const updateElementPosition = ({ key, value }) => {
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
  if (!selectedElement.value) return
  const content = String(value ?? '')
  selectedElement.value.content = content
  if (selectedElement.value.target === 'title') current.value.title = content
  if (selectedElement.value.target === 'description') current.value.description = content
  if (selectedElement.value.target === 'footer') current.value.footer = content
}
const updateElementField = ({ key, value }) => {
  if (!selectedElement.value || !['src', 'alt'].includes(key)) return
  if (key === 'src') selectedElement.value.src = String(value || '') || createMockImageSrc(selectedElement.value.content || '课堂图片')
  if (key === 'alt') selectedElement.value.alt = String(value || '').slice(0, 80)
}
const updateElementData = (value) => {
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
  if (current.value) current.value[key] = value
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
const handleToolSelect = (tool) => beginElementPlacement(tool)
const removeElement = (id = selectedElementId.value) => {
  if (!current.value || !id) return
  const index = current.value.elements.findIndex((element) => element.id === id)
  if (index < 0) return
  const [removed] = current.value.elements.splice(index, 1)
  selectedElementId.value = null
  WorkspaceMessage.success(`${removed?.name || '元素'}已删除`)
}
const copyElement = (id = selectedElementId.value) => {
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
    componentId: page.id || page.component_id || page.page_id || content.componentId,
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
    page_title: candidate.page_title || nextContent.title,
    page_content: JSON.stringify(nextContent),
    components: typeof elementPayload === 'string' ? elementPayload : JSON.stringify(elementPayload),
  }
  slides.splice(selectedSlide.value, 1, pageToSlide(page, selectedSlide.value))
  selectedElementId.value = null
  return true
}
const loadProject = async () => {
  if (!projectId.value) return
  try {
    project.value = unwrapResponse(await getProject(projectId.value))
    const pages = Array.isArray(project.value?.pages) ? project.value.pages : []
    slides.splice(0, slides.length, ...(pages.length ? pages.map(pageToSlide) : [defaultSlide()]))
    selectedSlide.value = 0
  } catch (error) { WorkspaceMessage.error(error?.message || '项目内容加载失败') }
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
  try { const run = unwrapResponse(await createAiRun(sessionId.value)); const runId = run?.id || run?.run_id; if (!runId) throw new Error('未获取到生成任务'); runStatus.value = 'running'; runProgress.value = 0; runStage.value = '正在创建生成任务'; WorkspaceMessage.success('大纲已确认，课件正在生成'); connectRunEvents(runId); const latest = unwrapResponse(await getAiRun(runId)); applyRunPayload(latest || {}) }
  catch (error) { runStatus.value = 'failed'; WorkspaceMessage.error(error?.message || '生成任务创建失败') }
}
const submitRevision = async () => {
  const instruction = prompt.value.trim(); if (!instruction) return
  messages.push({ role: 'user', text: instruction }); prompt.value = ''
  try {
    let applied = false
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
  } catch (error) { messages.push({ role: 'assistant', text: '修改请求暂未提交成功，请稍后重试。' }); WorkspaceMessage.error(error?.message || '修改请求失败') }
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
onMounted(() => { loadTestCase(); initializeSessionFlow(); loadProject(); window.addEventListener('keydown', handleWorkspaceKeydown) })
onBeforeUnmount(() => { eventSource?.close(); clearInterval(runPollTimer); stopElementDrag(); cancelCanvasPlacement(); workspaceMessageInstance?.close(); window.removeEventListener('keydown', handleWorkspaceKeydown) })
const currentPagePayload = () => ({ project_id: Number(projectId.value) || undefined, page_order: selectedSlide.value + 1, page_type: selectedSlide.value === 0 ? 'cover' : 'content', page_title: current.value.title, page_content: JSON.stringify(current.value), components: JSON.stringify(current.value.elements || []) })
const persistCurrentSlide = async () => {
  if (!projectId.value || savingComponent.value) return
  savingComponent.value = true; autosaveState.value = '保存中…'
  try {
    const payload = currentPagePayload()
    const response = current.value.componentId ? await updateProjectComponent(projectId.value, current.value.componentId, payload) : await addProjectComponent(projectId.value, payload)
    const saved = unwrapResponse(response)
    current.value.componentId ||= saved?.id || saved?.component_id
    autosaveState.value = '已保存'
  } catch (error) { autosaveState.value = '保存失败'; WorkspaceMessage.error(error?.message || '页面保存失败') } finally { savingComponent.value = false }
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
watch(slides, () => { if (!projectId.value) return; autosaveState.value = '待保存'; clearTimeout(autosaveTimer); autosaveTimer = setTimeout(persistCurrentSlide, 700) }, { deep: true })
watch(selectedSlide, () => { selectedElementId.value = null })
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const goHome = () => router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
const exportProject = () => router.push({ path: '/main/exports', query: route.query.preview ? { preview: '1' } : {} })
const addSlide = () => { slides.push({ ...defaultSlide(slides.length + 1), eyebrow: '新建内容' }); selectedSlide.value = slides.length - 1 }
const copySlide = () => { slides.splice(selectedSlide.value + 1, 0, { ...current.value, title: `${current.value.title} 副本`, elements: normalizeElements(current.value.elements) }); selectedSlide.value++ }
const removeSlide = () => { if (slides.length === 1) return WorkspaceMessage.warning('课件至少保留一页'); slides.splice(selectedSlide.value, 1); selectedSlide.value = Math.max(0, selectedSlide.value - 1) }
const sendRevision = () => submitRevision()
const selectSlide = (index) => { selectedSlide.value = index; selectedElementId.value = null }
</script>

<template>
  <div class="workspace">
    <CreationWorkspaceToolbar
      v-model="activeTool"
      :title="current.title"
      :autosave-state="autosaveState"
      :project-id="route.query.projectId"
      @back="goHome"
      @preview="previewVisible = true"
      @export="exportProject"
      @tool-select="handleToolSelect"
    />

    <div class="workspace-grid">
      <aside class="assistant-panel" aria-label="AI 教学助手">
        <header><div class="assistant-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div></header>
        <section class="conversation"><article v-for="(message, index) in messages" :key="index" :class="['message', message.role]"><span v-if="message.role === 'assistant'">智</span><p>{{ message.text }}</p></article></section>
        <footer class="composer"><el-input v-model="prompt" type="textarea" :rows="3" resize="none" placeholder="例如：把提问改得更有启发性" @keydown.ctrl.enter="sendRevision" /><div><span>Ctrl + Enter 发送</span><el-button type="primary" circle :icon="Promotion" :disabled="!prompt.trim()" aria-label="发送修改" @click="sendRevision" /></div></footer>
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
            <span v-if="placementMode" class="canvas-placement-status"><b>{{ placementInstruction }}</b><small>Esc 取消</small></span>
            <span>16:9 · 自适应窗口</span>
          </div>
          <article class="slide-canvas" :class="[`layout-${current.layout}`, { 'is-placing': placementMode }]" :style="{ '--accent': theme.color }" @pointerdown="startCanvasPlacement" @pointermove="handleCanvasPlacementMove" @click="handleSlideCanvasClick">
            <span class="slide-eyebrow">{{ current.eyebrow }}</span>
            <template v-for="element in current.elements" :key="element.id">
              <h1 v-if="element.type === 'text' && element.target === 'title'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</h1>
              <p v-else-if="element.type === 'text' && element.target === 'description'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</p>
              <footer v-else-if="element.type === 'text' && element.target === 'footer'" :data-element-id="element.id" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <span>{{ current.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span>
                <p>{{ elementContent(element) }}</p>
              </footer>
              <div v-else-if="element.type === 'text'" :data-element-id="element.id" class="text-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">{{ elementContent(element) }}</div>
              <div v-else-if="element.type === 'formula'" :data-element-id="element.id" class="theorem formula-element" :class="elementClass(element)" :style="elementStyle(element.id)" @pointerdown="startElementDrag(element.id, $event)" @click.stop="selectElement(element.id, $event)">
                <div class="triangle"><i>a</i><i>b</i><i>c</i></div>
                <div class="formula"><strong>{{ elementContent(element) || 'a² + b² = c²' }}</strong><small>公式元素，可在右侧修改内容</small></div>
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
                <span class="widget-action">{{ element.type === 'audio' ? '播放' : element.type === 'video' ? '预览' : '打开' }}</span>
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
            <button aria-label="缩小">−</button><span>86%</span><button aria-label="放大">+</button><button aria-label="全屏预览" @click="previewVisible = true"><el-icon><FullScreen /></el-icon></button>
          </div>
        </main>
      </section>

      <WorkspacePropertiesPanel
        :slide="current"
        :elements="current.elements"
        :selected-element="selectedElementPanel"
        :selected-element-id="selectedElementId"
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

    <el-dialog v-model="previewVisible" class="preview-dialog" width="min(960px, 92vw)" title="课件预览">
      <div class="preview">
        <article class="slide-canvas preview-slide" :class="`layout-${current.layout}`" :style="{ '--accent': theme.color }">
          <span class="slide-eyebrow">{{ current.eyebrow }}</span>
          <template v-for="element in current.elements" :key="`preview-${element.id}`">
            <h1 v-if="element.type === 'text' && element.target === 'title'" :class="previewElementClass(element)" :style="elementStyle(element.id)">{{ elementContent(element) }}</h1>
            <p v-else-if="element.type === 'text' && element.target === 'description'" :class="previewElementClass(element)" :style="elementStyle(element.id)">{{ elementContent(element) }}</p>
            <footer v-else-if="element.type === 'text' && element.target === 'footer'" :class="previewElementClass(element)" :style="elementStyle(element.id)"><span>{{ current.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span><p>{{ elementContent(element) }}</p></footer>
            <div v-else-if="element.type === 'text'" class="text-element" :class="previewElementClass(element)" :style="elementStyle(element.id)">{{ elementContent(element) }}</div>
            <div v-else-if="element.type === 'formula'" class="theorem formula-element" :class="previewElementClass(element)" :style="elementStyle(element.id)"><div class="triangle"><i>a</i><i>b</i><i>c</i></div><div class="formula"><strong>{{ elementContent(element) || 'a² + b² = c²' }}</strong><small>公式元素</small></div></div>
            <div v-else-if="element.type === 'shape'" class="shape-element" :class="[previewElementClass(element), `shape-${element.shapeKind || 'rectangle'}`]" :style="elementStyle(element.id)"><svg class="shape-svg" viewBox="0 0 100 100" :preserveAspectRatio="element.shapeKind === 'circle' ? 'xMidYMid meet' : 'none'" aria-hidden="true"><rect v-if="['rectangle', 'rounded'].includes(element.shapeKind)" class="shape-fill" x="4" y="4" width="92" height="92" :rx="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" :ry="element.shapeKind === 'rounded' ? Number(element.style?.borderRadius ?? 14) : 0" /><circle v-else-if="element.shapeKind === 'circle'" class="shape-fill" cx="50" cy="50" r="46" /><polygon v-else-if="element.shapeKind === 'diamond'" class="shape-fill" points="50,4 96,50 50,96 4,50" /><polygon v-else-if="element.shapeKind === 'triangle'" class="shape-fill" points="50,4 96,96 4,96" /><rect v-else class="shape-fill" x="4" y="4" width="92" height="92" /></svg><span v-if="elementContent(element)">{{ elementContent(element) }}</span></div>
            <div v-else-if="element.type === 'image'" class="image-element" :class="previewElementClass(element)" :style="elementStyle(element.id)"><img :src="element.src || createMockImageSrc()" :alt="element.alt || elementContent(element) || element.name" /><span v-if="element.style?.showCaption !== false">{{ elementContent(element) || '图片 mock' }}</span></div>
            <div v-else-if="element.type === 'chart'" class="chart-element" :class="previewElementClass(element)" :style="elementStyle(element.id)"><header><strong>{{ elementContent(element) || '数据图表' }}</strong><small>MOCK DATA</small></header><div class="chart-plot"><div v-for="(item, itemIndex) in (element.data || [])" :key="`preview-${element.id}-${itemIndex}`" class="chart-bar"><span class="chart-bar-fill" :style="{ height: `${Math.max(8, Math.min(100, Number(item.value) || 0))}%` }"></span><small>{{ item.label }}</small></div></div></div>
            <div v-else-if="['audio', 'video', 'h5', 'subject'].includes(element.type)" class="workspace-widget" :class="[`widget-${element.type}`, previewElementClass(element)]" :style="elementStyle(element.id)"><span class="widget-icon">{{ element.type === 'audio' ? '♫' : element.type === 'video' ? '▶' : element.type === 'h5' ? 'H5' : '⌁' }}</span><div><strong>{{ elementContent(element) || element.name }}</strong><small>{{ elementTypeLabels[element.type] }}</small></div><span class="widget-action">{{ element.type === 'audio' ? '播放' : element.type === 'video' ? '预览' : '打开' }}</span></div>
            <div v-else-if="element.type === 'table'" class="workspace-widget table-widget" :class="previewElementClass(element)" :style="elementStyle(element.id)"><strong>{{ elementContent(element) || '数据表格' }}</strong><div class="mock-table-grid"><span v-for="(cell, cellIndex) in (element.data?.flat() || [])" :key="`preview-${element.id}-${cellIndex}`">{{ cell }}</span></div></div>
          </template>
        </article>
      </div>
      <template #footer><el-button @click="previewVisible = false">继续编辑</el-button><el-button type="primary" :icon="VideoPlay" @click="previewVisible = false">播放预览</el-button></template>
    </el-dialog>
  </div>
    <IntentClarificationDialog v-model="clarificationDialogVisible" :question="clarificationQuestion" :loading="clarificationSubmitting" @submit="submitClarification" />
    <div v-if="runStatus === 'running'" class="run-progress"><span>{{ runStage || 'AI 正在生成课件' }}</span><el-progress :percentage="runProgress" :show-text="false" :stroke-width="4" /></div>
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
</style>
