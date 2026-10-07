<!--
  [数据交互说明]
  - 导入: 首页配置、Element Plus 图标
  - 输出: 教师端默认首页内容，由 `TeacherLayout.vue` 承载全局导航
-->
<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCheck,
  CircleClose,
  Close,
  Collection,
  Document,
  EditPen,
  Loading,
  MagicStick,
  Microphone,
  Monitor,
  More,
  Paperclip,
  Promotion,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'
import { INFO_FORM_DEFAULTS, requestNewChat, openChatSession } from '../config/teacherChat.config.js'
import { useUserStore } from '../storage/user'
import ChatView from './ChatView.vue'
import { archiveProject, cleanupTempResources, copyProject, createAiSession, createProject, deleteProject, forgetTempResource, listProjects, listResources, listTempResourceIds, rememberTempResource, transcribeAudio, uploadResource, uploadTempResource } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const currentTime = ref(new Date())
let greetingClockTimer = null
const teacherSurname = computed(() => {
  const realName = String(userStore.userInfo?.real_name || '').trim()
  return realName ? Array.from(realName)[0] : ''
})
const greetingPeriod = computed(() => {
  const hour = currentTime.value.getHours()
  if (hour >= 5 && hour < 9) return '清晨好'
  if (hour >= 9 && hour < 12) return '上午好'
  if (hour >= 12 && hour < 14) return '中午好'
  if (hour >= 14 && hour < 18) return '下午好'
  return '晚上好'
})
const teacherGreeting = computed(() => `${greetingPeriod.value}，${teacherSurname.value ? `${teacherSurname.value}老师` : '老师'}`)
const prompt = ref('')
const routePreference = ref('auto')
const canSend = computed(() => prompt.value.trim().length > 0)
const composerInput = ref(null)
const activeSuggestionId = ref(null)
const iconMap = { Presentation: Monitor, Document, MagicStick }
const projects = ref([])
const projectsLoading = ref(true)
const resourcesLoading = ref(false)
const availableResources = ref([])
const selectedResourceIds = ref([])
const knowledgeDialogVisible = ref(false)
const resourceSearch = ref('')
const voiceDialogVisible = ref(false)
const voiceLanguage = ref('zh-CN')
/** 语音录音与转写状态 */
const voiceRecording = ref(false)
const voiceTranscribing = ref(false)
const voiceSeconds = ref(0)
let voiceMediaStream = null
let voiceRecorder = null
let voiceChunks = []
let voiceTimer = null
const projectManagerVisible = ref(false)
const managedProjects = ref([])
const projectManagerLoading = ref(false)
/** 聊天视图状态管理 */
const viewMode = ref('welcome') // 'welcome' | 'chat'
const chatSessionId = ref(null)
const chatPrompt = ref('')
const chatResourceIds = ref([])
/** 从欢迎页/聊天页一路带到工作台的资料、上传文件和社区内容上下文。 */
const chatWorkspaceContext = ref({ resourceIds: [], resource_ids: [], uploadedResources: [], uploaded_resources: [], community: null })
const pendingUploadedResources = ref([])
/** 功能 2（临时上传）：不入素材库的本次引用资料；status: parsing | ready | error。 */
const tempUploads = ref([])
const tempFileInput = ref(null)
/** 普通对话切换到备课流时，保留切换前的消息用于页面续接和首次模型上下文。 */
const chatContinuationHistory = ref([])
/** 欢迎页输入的会话类型：普通对话不进入备课补充信息流程。 */
const chatMode = ref('planning') // 'planning' | 'general'
/** 是否以"恢复历史"方式打开会话（由侧栏历史对话触发，ChatView 据此拉取消息回显） */
const chatResume = ref(false)

const filteredAvailableResources = computed(() => {
  const query = resourceSearch.value.trim().toLowerCase()
  return query ? availableResources.value.filter((item) => (item.file_name || '').toLowerCase().includes(query)) : availableResources.value
})

/** 语音状态栏文案：随录音/转写状态实时变化。 */
const voiceStatusText = computed(() => {
  if (voiceTranscribing.value) return '正在识别语音，请稍候…'
  if (voiceRecording.value) return '正在录音，请说出你的备课需求'
  return '点击开始录音，说出你的备课需求'
})

const openProject = (project) => router.push({
  path: '/main/workspace',
  query: { projectId: project.id },
})
const openNewWorkspace = () => router.push({
  path: '/main/workspace',
  query: route.query.preview ? { preview: '1' } : {},
})

const normalizeResourceIds = (resourceIds = []) => [...new Set(
  (Array.isArray(resourceIds) ? resourceIds : [resourceIds])
    .map((item) => String(item ?? '').trim())
    .filter(Boolean),
)]
const normalizeWorkspaceContext = (context = {}, resourceIds = []) => {
  const ids = normalizeResourceIds(resourceIds.length ? resourceIds : (context.resourceIds || context.resource_ids || []))
  const uploaded = Array.isArray(context.uploadedResources)
    ? context.uploadedResources
    : Array.isArray(context.uploaded_resources) ? context.uploaded_resources : []
  return {
    ...context,
    resourceIds: ids,
    resource_ids: ids,
    uploadedResources: uploaded.slice(0, 30),
    uploaded_resources: uploaded.slice(0, 30),
    community: context.community || null,
  }
}

const loadProjects = async () => {
  projectsLoading.value = true
  try {
    const result = await listProjects({ page: 1, size: 4, status: 'draft' })
    projects.value = result?.data?.records || result?.data?.list || result?.data?.items || []
  } catch {
    projects.value = []
  } finally {
    projectsLoading.value = false
  }
}

/** 将推荐任务写入输入框。 */
const applySuggestion = (suggestion) => {
  prompt.value = suggestion.prompt
  activeSuggestionId.value = suggestion.id
  requestAnimationFrame(() => composerInput.value?.focus())
}

/** 将播放录音时长格式化为 mm:ss。 */
const formatVoiceSeconds = (total) => {
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

/** 开始录音：申请麦克风权限并用 MediaRecorder 采集音频。 */
const startVoiceRecording = async () => {
  if (voiceRecording.value || voiceTranscribing.value) return
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    ElMessage.error('当前浏览器不支持录音，请使用最新版 Chrome/Edge')
    return
  }
  try {
    voiceMediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    voiceChunks = []
    voiceRecorder = new MediaRecorder(voiceMediaStream)
    voiceRecorder.ondataavailable = (event) => {
      if (event.data?.size) voiceChunks.push(event.data)
    }
    voiceRecorder.onstop = handleVoiceRecordingStop
    voiceRecorder.start()
    voiceRecording.value = true
    voiceSeconds.value = 0
    voiceTimer = window.setInterval(() => { voiceSeconds.value += 1 }, 1000)
  } catch {
    ElMessage.error('无法访问麦克风，请检查浏览器权限设置')
  }
}

/** 停止录音并释放麦克风，recorder 停止时触发 onstop 回调。 */
const stopVoiceRecording = () => {
  if (!voiceRecording.value || !voiceRecorder) return
  voiceRecorder.stop()
  voiceRecorder = null
}

/** 切换录音状态：空闲时开始，录音中停止（点击圆形麦克风调用）。 */
const toggleVoiceRecording = () => {
  if (voiceTranscribing.value) return
  if (voiceRecording.value) stopVoiceRecording()
  else startVoiceRecording()
}

/** 关闭语音对话框时兜底清理：结束未停止的录音并重置计时器。 */
const handleVoiceDialogClosed = () => {
  window.clearInterval(voiceTimer)
  voiceSeconds.value = 0
  if (voiceRecorder) {
    try { voiceRecorder.stop() } catch { /* ignore */ }
    voiceRecorder = null
  }
  if (voiceMediaStream) {
    voiceMediaStream.getTracks().forEach((track) => track.stop())
    voiceMediaStream = null
  }
  voiceRecording.value = false
  voiceTranscribing.value = false
}

/** 录音结束后：构造音频文件上传 ASR，成功后把识别文本填入输入框。 */
const handleVoiceRecordingStop = async () => {
  voiceRecording.value = false
  window.clearInterval(voiceTimer)
  if (voiceMediaStream) {
    voiceMediaStream.getTracks().forEach((track) => track.stop())
    voiceMediaStream = null
  }
  if (!voiceChunks.length) {
    ElMessage.warning('未录制到有效音频')
    voiceChunks = []
    return
  }
  const blob = new Blob(voiceChunks, { type: 'audio/webm' })
  voiceChunks = []
  voiceTranscribing.value = true
  try {
    const file = new File([blob], 'voice_recording.webm', { type: 'audio/webm' })
    const formData = new FormData()
    formData.append('file', file)
    formData.append('language', /^en/i.test(voiceLanguage.value) ? 'en' : 'zh')
    const res = await transcribeAudio(formData)
    const text = (res?.data?.text || '').trim()
    if (!text) {
      ElMessage.warning('未能识别到有效语音，请再试一次')
      return
    }
    // 将识别文本追加到欢迎页输入框已有内容之后，用户确认后可手动发送
    const current = prompt.value.trim()
    prompt.value = current ? `${current} ${text}` : text
    activeSuggestionId.value = null
    voiceDialogVisible.value = false
    requestAnimationFrame(() => composerInput.value?.focus())
    ElMessage.success('语音已识别，正在整理你的备课需求')
  } catch {
    ElMessage.error('语音识别失败，请检查网络后重试')
  } finally {
    voiceTranscribing.value = false
  }
}

/**
 * 创建备课会话并进入 ChatView。
 * 备课上下文由 ChatView 的结构化征询卡补齐后才提交 API-13；这里只创建会话，
 * 不因为 Java 接口的必填字段而偷偷替教师做出学科/年级判断；若从普通对话切换，
 * 同时把切换前的历史交给 ChatView 做回显和首次请求上下文注入。
 */
const startPlanningSession = async (text, resourceIds = [], history = null, workspaceContext = {}) => {
  const previousMode = chatMode.value
  const normalizedText = String(text || '').trim()
  // 功能 2：兜底并入已就绪的临时上传 id，保证 resource_ids 与 uploadedResources 一致。
  const normalizedResourceIds = normalizeResourceIds([...(resourceIds || []), ...readyTempIds.value])
  const normalizedWorkspaceContext = normalizeWorkspaceContext({
    ...workspaceContext,
    uploadedResources: [
      ...(workspaceContext.uploadedResources || workspaceContext.uploaded_resources || pendingUploadedResources.value),
      ...tempContextEntries.value,
    ],
  }, normalizedResourceIds)
  const normalizedPreviousHistory = Array.isArray(history)
    ? history
      .filter((item) => item && (item.role === 'user' || item.role === 'assistant') && String(item.content || '').trim())
      .map((item) => ({ role: item.role, content: String(item.content).trim() }))
      .slice(-16)
    : []
  // 兼容调用方把本次切换请求也放进 history 的旧写法，避免页面和模型上下文重复一条。
  const lastHistoryItem = normalizedPreviousHistory[normalizedPreviousHistory.length - 1]
  if (lastHistoryItem?.role === 'user' && lastHistoryItem.content === normalizedText) {
    normalizedPreviousHistory.pop()
  }
  const normalizedHistory = [...normalizedPreviousHistory, { role: 'user', content: normalizedText }]

  try {
    const result = await createAiSession({
      title: normalizedText.slice(0, 40),
      // Java 会话接口要求 subject/grade 非空；ChatView 会在征询后用真实值覆盖上下文。
      subject: INFO_FORM_DEFAULTS.subject,
      grade: INFO_FORM_DEFAULTS.grade,
      status: 'active',
      messages: JSON.stringify(normalizedHistory),
      uploaded_refs: JSON.stringify(normalizedResourceIds),
    })
    const task = result?.data || result
    const sessionId = task?.conversation_id || task?.id
    if (!sessionId) throw new Error(result?.message || '创建备课会话失败')

    chatSessionId.value = sessionId
    chatPrompt.value = normalizedText
    chatResourceIds.value = normalizedResourceIds
    chatWorkspaceContext.value = normalizedWorkspaceContext
    chatContinuationHistory.value = normalizedPreviousHistory
    chatMode.value = 'planning'
    chatResume.value = false
    viewMode.value = 'chat'
    ElMessage.success('已进入备课流程，请先确认课程信息')
  } catch (error) {
    // 普通对话中途切换失败时，保留原聊天模式，避免输入区被锁死。
    chatMode.value = previousMode
    ElMessage.error(error?.message || '创建会话失败，请登录后重试')
  }
}

/**
 * 所有首句先交给 Java 保存并分流；用户可在发送前覆盖自动判断。
 */
const sendPrompt = async () => {
  if (!canSend.value) return
  const text = prompt.value.trim()

  chatMode.value = 'general'
  chatSessionId.value = null
  chatPrompt.value = text
  // 功能 2：临时上传 res_xxx 与素材库勾选一并并入本次引用集合与会话上下文。
  const workspaceContext = buildChatContext(selectedResourceIds.value)
  chatResourceIds.value = workspaceContext.resourceIds
  chatWorkspaceContext.value = workspaceContext
  chatContinuationHistory.value = []
  chatResume.value = false
  viewMode.value = 'chat'
  prompt.value = ''
  activeSuggestionId.value = null
}

/** 欢迎页快捷键：Enter 发送，Shift+Enter 保留换行；中文输入法确认候选词时不抢占 Enter。
 *  触屏设备禁用 Enter 发送（软键盘回车仅换行），与 ChatView 行为一致。 */
const isTouchDevice = typeof window !== 'undefined'
  && window.matchMedia('(hover: none) and (pointer: coarse)').matches

const handlePromptKeydown = (event) => {
  if (isTouchDevice) return
  if (event.isComposing || event.keyCode === 229 || event.shiftKey) return
  event.preventDefault()
  void sendPrompt()
}

/** 普通对话中途识别到明确备课请求时，切换为带征询卡片的备课流程。 */
const handlePlanningRequest = async (payload) => {
  const text = typeof payload === 'string' ? payload : payload?.prompt
  const history = typeof payload === 'object' ? payload?.history : null
  const resourceIds = typeof payload === 'object' && Array.isArray(payload?.resourceIds)
    ? payload.resourceIds
    : chatResourceIds.value
  const workspaceContext = typeof payload === 'object' && payload?.workspaceContext
    ? payload.workspaceContext
    : chatWorkspaceContext.value
  if (!String(text || '').trim()) return
  if (payload?.existingSessionId) {
    // Java 已把同一会话升级为备课任务，无需再次创建会话或复制历史消息。
    chatSessionId.value = payload.existingSessionId
    chatPrompt.value = text
    chatResourceIds.value = normalizeResourceIds(resourceIds)
    chatWorkspaceContext.value = normalizeWorkspaceContext(workspaceContext || {}, chatResourceIds.value)
    chatContinuationHistory.value = Array.isArray(history) ? history : []
    chatMode.value = 'planning'
    return
  }
  await startPlanningSession(text, resourceIds, history, workspaceContext)
}

/** 关闭聊天视图，返回欢迎页 */
const closeChatView = () => {
  viewMode.value = 'welcome'
  chatSessionId.value = null
  chatPrompt.value = ''
  chatResourceIds.value = []
  chatWorkspaceContext.value = { resourceIds: [], resource_ids: [], uploadedResources: [], uploaded_resources: [], community: null }
  pendingUploadedResources.value = []
  chatContinuationHistory.value = []
  chatMode.value = 'planning'
  chatResume.value = false
  prompt.value = ''
  loadProjects()
}

/**
 * 监听 TeacherLayout 侧栏"新建对话"按钮触发的跨组件信号。
 * 当前已在聊天视图时，关闭聊天并返回欢迎页。
 */
watch(requestNewChat, (val) => {
  if (val) {
    closeChatView()
    requestNewChat.value = false
  }
})

/**
 * 监听 TeacherLayout 侧栏"历史对话"跨组件信号，切换到对应会话的聊天视图。
 * 使用 immediate：支持"先导航到首页再发信号"的场景，挂载时即读取当前信号打开会话。
 */
watch(openChatSession, (target) => {
  if (!target?.id) return
  chatMode.value = target.mode === 'general' ? 'general' : 'planning'
  chatSessionId.value = target.id
  chatPrompt.value = target.title || ''
  chatResourceIds.value = []
  chatWorkspaceContext.value = { resourceIds: [], resource_ids: [], uploadedResources: [], uploaded_resources: [], community: null }
  chatContinuationHistory.value = []
  chatResume.value = true
  viewMode.value = 'chat'
  openChatSession.value = null
}, { immediate: true })

const handleGeneralSession = (session) => {
  if (chatMode.value === 'general' && session?.id) chatSessionId.value = session.id
}

/** 从聊天视图跳转到创作工作台，并携带生成前已选定的 PPT 模板 */
const openWorkspaceFromChat = (payload) => {
  const projectId = payload && typeof payload === 'object' ? payload.projectId : payload
  const pptTheme = payload && typeof payload === 'object' ? payload.pptTheme : ''
  const generationKey = payload && typeof payload === 'object' ? payload.generationKey : ''
  const resourceIds = normalizeResourceIds(payload && typeof payload === 'object' ? payload.resourceIds : chatResourceIds.value)
  const workspaceContext = normalizeWorkspaceContext(
    payload && typeof payload === 'object' ? (payload.workspaceContext || {}) : chatWorkspaceContext.value,
    resourceIds,
  )
  router.push({
    path: '/main/workspace',
    query: {
      sessionId: chatSessionId.value,
      ...(projectId ? { projectId } : {}),
      ...(pptTheme ? { pptTheme } : {}),
      ...(generationKey ? { pptGeneration: generationKey } : {}),
      resourceIds: JSON.stringify(resourceIds),
      workspaceContext: JSON.stringify(workspaceContext),
    },
  })
}

const createProjectFromPrompt = async () => {
  if (!canSend.value) return
  try {
    const result = await createProject({
      project_name: prompt.value.trim().slice(0, 40),
      project_type: 'courseware',
      status: 'draft',
    })
    const project = result?.data || result
    if (!project?.id) throw new Error(result?.message || '创建项目失败')
    ElMessage.success('已创建教学项目')
    openProject(project)
  } catch (error) {
    ElMessage.error(error?.message || '创建项目失败，请登录后重试')
  }
}

const loadAvailableResources = async () => {
  resourcesLoading.value = true
  try {
    const result = await listResources({ page: 1, size: 30 })
    availableResources.value = result?.data?.records || result?.data?.list || result?.data?.items || []
  } catch { availableResources.value = [] } finally { resourcesLoading.value = false }
}
const openKnowledgeDialog = async () => {
  resourceSearch.value = ''
  knowledgeDialogVisible.value = true
  await loadAvailableResources()
}

// ========== 功能 2：临时上传（「添加资料」直达，不入素材库仅本次引用；需要入库时用芯片上的「转存」） ==========
const TEMP_BADGES = [
  { match: ['doc', 'docx'], label: 'W', type: 'word' },
  { match: ['ppt', 'pptx'], label: 'P', type: 'ppt' },
  { match: ['pdf'], label: 'PDF', type: 'pdf' },
  { match: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'], label: '图', type: 'image' },
  { match: ['mp3', 'wav', 'm4a', 'ogg'], label: '音', type: 'audio' },
  { match: ['mp4', 'avi', 'mov', 'mkv', 'webm'], label: '视', type: 'video' },
  { match: ['txt', 'md'], label: 'T', type: 'text' },
]
const tempBadgeFor = (filename) => {
  const ext = String(filename || '').split('.').pop()?.toLowerCase() || ''
  const badge = TEMP_BADGES.find((item) => item.match.includes(ext))
  return badge ? { badgeLabel: badge.label, badgeType: badge.type } : { badgeLabel: '文', badgeType: 'other' }
}
const triggerTempUpload = () => tempFileInput.value?.click()
const handleTempFilesPicked = async (event) => {
  const files = Array.from(event.target?.files || [])
  if (event.target) event.target.value = ''
  await uploadTempFiles(files)
}
/** 直连 Python 上传临时资料；请求期间芯片显示「解析中」，返回 res_xxx 即转「已就绪」。 */
const uploadTempFiles = async (rawFiles) => {
  // 与素材库上传共用同一扩展名白名单，绕过 accept 的文件提前拦截
  const supportedExtensions = [
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'md',
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
    'mp3', 'wav', 'm4a', 'ogg', 'mp4', 'avi', 'mov', 'mkv', 'webm',
  ]
  const candidates = Array.from(rawFiles || [])
  const files = candidates.filter((file) => supportedExtensions.includes(file.name.split('.').pop()?.toLowerCase()))
  if (files.length !== candidates.length) ElMessage.warning('已忽略不支持的文件格式')
  if (!files.length) return
  for (const file of files) {
    const entry = reactive({
      key: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      file,
      name: file.name,
      size: file.size,
      status: 'parsing',
      resourceId: '',
      error: '',
      transferring: false,
      cancelled: false,
      ...tempBadgeFor(file.name),
    })
    tempUploads.value.push(entry)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await uploadTempResource(formData)
      const resourceId = result?.resource_id || result?.data?.resource_id
      if (!resourceId) throw new Error(result?.message || '上传成功但未返回资源 ID')
      if (entry.cancelled) {
        // 「解析中」时已移除芯片：登记表未写入，直接回收服务端临时索引，避免孤儿残留
        cleanupTempResources([String(resourceId)]).catch(() => {})
        continue
      }
      entry.resourceId = String(resourceId)
      entry.status = 'ready'
      rememberTempResource(entry.resourceId)
    } catch (error) {
      if (entry.cancelled) continue
      entry.status = 'error'
      // FastAPI HTTPException 返回 {"detail"}（如 413 限额），优先透出中文提示
      entry.error = error?.response?.data?.detail || error?.message || '临时上传失败'
    }
  }
}
const readyTempUploads = computed(() => tempUploads.value.filter((item) => item.status === 'ready' && item.resourceId))
const readyTempIds = computed(() => readyTempUploads.value.map((item) => item.resourceId))
/** 已就绪临时资料的上下文明细（并入 uploadedResources，带 temp 标记）。 */
const tempContextEntries = computed(() => readyTempUploads.value.map((item) => ({
  resource_id: item.resourceId,
  id: item.resourceId,
  file_name: item.name,
  file_type: item.file?.type || item.name.split('.').pop()?.toLowerCase() || '',
  file_size: item.size,
  temp: true,
  source: 'temp_upload',
})))
const removeTempUpload = (entry) => {
  // 解析中移除：标记取消，待上传返回后回收服务端临时索引（见 uploadTempFiles）
  entry.cancelled = true
  tempUploads.value = tempUploads.value.filter((item) => item.key !== entry.key)
  if (entry.resourceId) {
    forgetTempResource(entry.resourceId)
    cleanupTempResources([entry.resourceId]).catch(() => {})
  }
}
/** 一键转存：复用素材库 OSS 三段式上传链路，成功后自动勾选并清理临时索引。 */
const transferTempToLibrary = async (entry) => {
  if (entry.status !== 'ready' || entry.transferring) return
  entry.transferring = true
  try {
    const resource = await uploadResource(entry.file, undefined, { allowAi: true })
    const resourceId = String(resource?.id || resource?.resource_id || '')
    if (!resourceId) throw new Error('转存成功但未返回资源 ID')
    if (!selectedResourceIds.value.includes(resourceId)) selectedResourceIds.value.push(resourceId)
    pendingUploadedResources.value = [
      ...pendingUploadedResources.value.filter((item) => String(item.resource_id || item.id) !== resourceId),
      { resource_id: resourceId, id: resourceId, file_name: entry.name, file_type: entry.file?.type || '', file_size: entry.size, source: 'teacher_upload' },
    ]
    if (entry.resourceId) {
      forgetTempResource(entry.resourceId)
      cleanupTempResources([entry.resourceId]).catch(() => {})
    }
    tempUploads.value = tempUploads.value.filter((item) => item.key !== entry.key)
    ElMessage.success('已转存到个人素材库并引用')
  } catch (error) {
    ElMessage.error(error?.message || '转存失败，请重试')
  } finally {
    entry.transferring = false
  }
}
/** 会话删除会清空临时登记表：回到欢迎页时同步摘除已被清理的芯片。 */
const pruneMissingTempUploads = () => {
  const registry = listTempResourceIds()
  tempUploads.value = tempUploads.value.filter((item) => !item.resourceId || registry.includes(item.resourceId))
}
/** 组装本次会话的引用上下文：素材库勾选 + 已就绪临时上传（双写由 normalizeWorkspaceContext 收口）。 */
const buildChatContext = (baseResourceIds = []) => {
  const ids = normalizeResourceIds([...(baseResourceIds || []), ...readyTempIds.value])
  const uploaded = [...pendingUploadedResources.value, ...tempContextEntries.value]
  return normalizeWorkspaceContext({ uploadedResources: uploaded }, ids)
}
const openProjectManager = async () => {
  projectManagerVisible.value = true; projectManagerLoading.value = true
  try { const result = await listProjects({ page: 1, size: 50 }); managedProjects.value = result?.data?.records || result?.data?.list || result?.data?.items || [] }
  catch (error) { ElMessage.error(error?.message || '项目列表加载失败') } finally { projectManagerLoading.value = false }
}
const copyManagedProject = async (project) => {
  try { await copyProject(project.id, { new_name: `${project.project_name} 副本` }); ElMessage.success('项目已复制'); await openProjectManager(); await loadProjects() }
  catch (error) { ElMessage.error(error?.message || '项目复制失败') }
}
const archiveManagedProject = async (project) => {
  try { await archiveProject(project.id); ElMessage.success('项目已归档'); await openProjectManager(); await loadProjects() }
  catch (error) { ElMessage.error(error?.message || '项目归档失败') }
}
const deleteManagedProject = async (project) => {
  try { await ElMessageBox.confirm(`确定删除“${project.project_name}”吗？此操作不可恢复。`, '删除项目', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }); await deleteProject(project.id); ElMessage.success('项目已删除'); await openProjectManager(); await loadProjects() }
  catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error?.message || '项目删除失败') }
}

/** 手机档项目管理「更多」下拉命令分发：复用桌面端同批项目操作。 */
const handleManagedProjectCommand = ({ action, project }) => {
  if (action === 'copy') copyManagedProject(project)
  else if (action === 'archive') archiveManagedProject(project)
  else if (action === 'delete') deleteManagedProject(project)
}

/** 手机档视口判断（<768px）：项目操作收进下拉、上传改「选择文件」等触屏降级。 */
const mobileViewport = window.matchMedia('(max-width: 767.98px)')
const isMobile = ref(mobileViewport.matches)
const handleMobileViewportChange = (event) => { isMobile.value = event.matches }
onMounted(() => mobileViewport.addEventListener('change', handleMobileViewportChange))
onUnmounted(() => {
  mobileViewport.removeEventListener('change', handleMobileViewportChange)
  if (greetingClockTimer) window.clearInterval(greetingClockTimer)
})

onMounted(() => {
  loadProjects()
  pruneMissingTempUploads()
  greetingClockTimer = window.setInterval(() => { currentTime.value = new Date() }, 60_000)
})
// 聊天侧栏删除会话会清空临时登记表：切回欢迎页时同步摘除已被清理的芯片
watch(viewMode, (value) => {
  if (value === 'welcome') pruneMissingTempUploads()
})
</script>

<template>
  <section class="home-welcome" :class="{ 'is-chat-mode': viewMode === 'chat' }">
    <!-- 欢迎视图 -->
    <template v-if="viewMode === 'welcome'">
    <div class="welcome-scroll">
    <div class="welcome-copy motion-stage motion-stage-1">
      <div class="welcome-greeting">
        <img src="/branding/logo-intro.png" alt="" aria-hidden="true" />
        <p class="eyebrow">{{ teacherGreeting }}</p>
      </div>
      <h1>{{ TEACHER_HOME.greeting.title }}</h1>
      <p class="intro">{{ TEACHER_HOME.greeting.description }}</p>
      <div class="welcome-actions motion-stage motion-stage-2">
        <el-button type="primary" :icon="EditPen" @click="openNewWorkspace">新建课件</el-button>
      </div>
    </div>

    <section
      v-if="projectsLoading || projects.length"
      class="recent-projects motion-stage motion-stage-2"
      aria-label="最近项目"
      :aria-busy="projectsLoading"
    >
      <div class="recent-projects-heading"><h2>最近项目</h2><span><el-button text size="small" @click="openProjectManager">管理项目</el-button></span></div>
      <div v-if="projectsLoading" class="project-grid" aria-hidden="true">
        <el-skeleton v-for="index in 4" :key="index" animated class="project-skeleton">
          <template #template>
            <el-skeleton-item variant="text" class="project-skeleton-title" />
            <el-skeleton-item variant="text" class="project-skeleton-meta" />
          </template>
        </el-skeleton>
      </div>
      <div v-else class="project-grid">
        <button v-for="project in projects" :key="project.id" type="button" class="project-card" data-hover-lift @click="openProject(project)">
          <strong>{{ project.project_name }}</strong>
          <span>{{ project.project_type || '教学项目' }} · v{{ project.current_version || 1 }}</span>
        </button>
      </div>
    </section>

    <section class="suggestions-section motion-stage motion-stage-3" aria-label="快速开始">
      <div class="suggestions-heading">
        <h2>快速开始</h2>
        <span>选择一项，快速填入需求</span>
      </div>
      <div class="suggestion-grid">
      <el-card
        v-for="suggestion in TEACHER_HOME.suggestions"
        :key="suggestion.id"
        shadow="never"
        class="suggestion-card"
        :class="{ 'is-selected': activeSuggestionId === suggestion.id }"
        tabindex="0"
        @click="applySuggestion(suggestion)"
        @keyup.enter="applySuggestion(suggestion)"
      >
        <div class="suggestion-icon">
          <el-icon><component :is="iconMap[suggestion.icon]" /></el-icon>
        </div>
        <h2>{{ suggestion.title }}</h2>
        <p>{{ suggestion.description }}</p>
        <el-icon class="card-arrow"><Promotion /></el-icon>
      </el-card>
      </div>
    </section>

    </div>

    <section class="composer motion-stage motion-stage-4" aria-label="AI 教学任务输入">
      <!-- 功能 2：临时上传芯片（不入素材库，仅本次生成引用） -->
      <div v-if="tempUploads.length" class="temp-resource-list" role="list" aria-label="本次临时引用资料">
        <div v-for="entry in tempUploads" :key="entry.key" class="temp-resource-chip" role="listitem">
          <span class="temp-resource-badge" :class="`badge-${entry.badgeType}`" aria-hidden="true">{{ entry.badgeLabel }}</span>
          <div class="temp-resource-meta">
            <p class="temp-resource-name" :title="entry.name">{{ entry.name }}</p>
            <p
              class="temp-resource-status"
              :class="{ 'is-ready': entry.status === 'ready', 'is-error': entry.status === 'error' }"
              aria-live="polite"
            >
              <template v-if="entry.status === 'parsing'"><el-icon class="is-loading"><Loading /></el-icon><span>解析中</span></template>
              <template v-else-if="entry.status === 'ready'"><el-icon><CircleCheck /></el-icon><span>已就绪 · 本次生成可引用</span></template>
              <template v-else><el-icon><CircleClose /></el-icon><span>{{ entry.error }}</span></template>
            </p>
          </div>
          <div class="temp-resource-actions">
            <el-tooltip content="转存到个人素材库" placement="top"><span><el-button text size="small" :icon="Collection" :loading="entry.transferring" :disabled="entry.status !== 'ready'" aria-label="转存到个人素材库" @click="transferTempToLibrary(entry)" /></span></el-tooltip>
            <el-tooltip content="移除临时资料" placement="top"><span><el-button text size="small" :icon="Close" :disabled="entry.transferring" aria-label="移除临时资料" @click="removeTempUpload(entry)" /></span></el-tooltip>
          </div>
        </div>
      </div>
      <el-input
        ref="composerInput"
        v-model="prompt"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 7 }"
        resize="none"
        :placeholder="TEACHER_HOME.composer.placeholder"
        @keydown.enter="handlePromptKeydown"
      />
      <div class="composer-toolbar">
        <div class="composer-tools">
          <el-select v-model="routePreference" size="small" aria-label="任务分流方式" style="width: 118px">
            <el-option label="自动判断" value="auto" />
            <el-option label="仅对话" value="chat" />
            <el-option label="直接备课" value="planning" />
          </el-select>
          <el-tooltip content="上传本地资料：本次生成直接引用，可一键转存到素材库"><span><el-button text :icon="Paperclip" aria-label="添加资料" @click="triggerTempUpload"><span class="composer-tool-label">{{ TEACHER_HOME.composer.attach }}</span></el-button></span></el-tooltip>
          <input ref="tempFileInput" class="resource-file-input" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.jpg,.jpeg,.png,.gif,.webp,.svg,.mp3,.wav,.m4a,.ogg,.mp4,.avi,.mov,.mkv,.webm" @change="handleTempFilesPicked" />
          <el-tooltip content="从个人知识库中检索并引用已有资料"><span><el-button text :icon="Collection" aria-label="引用知识库" @click="openKnowledgeDialog"><span class="composer-tool-label">{{ TEACHER_HOME.composer.knowledge }}</span></el-button></span></el-tooltip>
          <el-tooltip content="打开语音输入"><span><el-button text circle aria-label="语音输入" @click="voiceDialogVisible = true"><el-icon><Microphone /></el-icon></el-button></span></el-tooltip>
        </div>
        <el-button
          type="primary"
          circle
          :icon="Promotion"
          :class="{ 'is-ready': canSend }"
          :disabled="!canSend"
          :aria-label="TEACHER_HOME.composer.send"
          @click="sendPrompt"
        />
      </div>
    </section>

    <p class="composer-hint motion-stage motion-stage-4">
      <span>{{ TEACHER_HOME.composer.hint }}</span>
      <span class="composer-shortcut-hint"> · Enter 发送 · Shift + Enter 换行</span>
    </p>
    </template>

    <!-- 聊天视图 -->
        <!-- 普通对话转备课时保留同一个组件和消息列表；打开历史会话时才重新挂载。 -->
        <ChatView
          v-if="viewMode === 'chat'"
      :key="chatResume ? `resume-${chatSessionId}` : 'active-chat'"
      :session-id="chatSessionId"
      :initial-prompt="chatPrompt"
      :resource-ids="chatResourceIds"
      :workspace-context="chatWorkspaceContext"
      :continuation-history="chatContinuationHistory"
      :mode="chatMode"
      :route-preference="routePreference"
      :resume="chatResume"
      @back="closeChatView"
      @open-workspace="openWorkspaceFromChat"
      @planning-request="handlePlanningRequest"
      @general-session="handleGeneralSession"
    />

    <!-- 知识库 / 语音对话框（欢迎视图和聊天视图共用）-->

    <el-dialog v-model="knowledgeDialogVisible" title="引用知识库" width="min(640px, 92vw)">
      <div class="knowledge-picker-header"><p>从已经上传并入库的资料中选择，AI 将结合这些内容生成大纲。</p><el-input v-model="resourceSearch" placeholder="搜索知识库资料" clearable /></div>
      <el-checkbox-group v-model="selectedResourceIds" v-loading="resourcesLoading" class="resource-picker resource-picker-dialog"><el-checkbox v-for="item in filteredAvailableResources" :key="item.id" :value="item.id">{{ item.file_name }}</el-checkbox><el-empty v-if="!resourcesLoading && !filteredAvailableResources.length" description="没有找到可引用的知识资料" /></el-checkbox-group>
      <template #footer><span class="selected-resource-count">已选择 {{ selectedResourceIds.length }} 项</span><el-button type="primary" @click="knowledgeDialogVisible = false">完成引用</el-button></template>
    </el-dialog>

    <el-dialog v-model="voiceDialogVisible" title="语音输入" width="min(480px, 92vw)" @closed="handleVoiceDialogClosed">
      <div class="voice-panel">
        <button
          type="button"
          class="voice-orb"
          :class="{ 'is-recording': voiceRecording, 'is-busy': voiceTranscribing }"
          :aria-label="voiceRecording ? '停止录音' : '开始录音'"
          :disabled="voiceTranscribing"
          @click="toggleVoiceRecording"
        >
          <el-icon><Microphone /></el-icon>
        </button>
        <strong>{{ voiceRecording ? '录音中，再次点击可结束' : '说出你的备课需求' }}</strong>
        <p>例如：“帮我设计一节八年级物理光的折射互动课”。</p>
        <div class="voice-wave" :class="{ 'is-recording': voiceRecording }" aria-hidden="true"><i v-for="index in 9" :key="index"></i></div>
        <div class="voice-status">
          <span class="voice-status-dot" :class="{ 'is-recording': voiceRecording, 'is-busy': voiceTranscribing }"></span>
          <span>{{ voiceStatusText }}</span>
          <time>{{ formatVoiceSeconds(voiceSeconds) }}</time>
        </div>
        <el-form label-position="top" class="voice-settings">
          <el-form-item label="识别语言">
            <el-select v-model="voiceLanguage">
              <el-option label="普通话" value="zh-CN" />
              <el-option label="英语" value="en-US" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>

  </section>

  <el-dialog v-model="projectManagerVisible" title="项目管理" width="min(720px, 92vw)">
    <div v-loading="projectManagerLoading" class="managed-project-list">
      <article v-for="project in managedProjects" :key="project.id"><div><strong>{{ project.project_name }}</strong><span>{{ project.project_type || '教学项目' }} · {{ project.status }}</span></div><div class="managed-project-actions"><el-button text size="small" @click="openProject(project)">打开</el-button><template v-if="!isMobile"><el-button text size="small" @click="copyManagedProject(project)">复制</el-button><el-button v-if="project.status !== 'archived'" text size="small" @click="archiveManagedProject(project)">归档</el-button><el-button type="danger" text size="small" @click="deleteManagedProject(project)">删除</el-button></template><el-dropdown v-else trigger="click" popper-class="managed-project-dropdown" @command="handleManagedProjectCommand"><el-button text size="small" :icon="More">更多</el-button><template #dropdown><el-dropdown-menu><el-dropdown-item :command="{ action: 'copy', project }">复制</el-dropdown-item><el-dropdown-item v-if="project.status !== 'archived'" :command="{ action: 'archive', project }">归档</el-dropdown-item><el-dropdown-item :command="{ action: 'delete', project }" class="managed-project-danger">删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></article><el-empty v-if="!projectManagerLoading && !managedProjects.length" description="暂无项目" />
    </div>
  </el-dialog>
</template>

<style scoped>
.home-welcome {
  width: min(880px, calc(100% - 48px));
  margin: 0 auto;
  padding: clamp(70px, 10vh, 124px) 0 42px;
}
/* 欢迎视图固定布局：内容区独立滚动，composer 固定底部（不随页面滚动） */
.home-welcome:not(.is-chat-mode) {
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 68px); /* 桌面/平板/中屏顶栏 68px */
  padding: 0 0 14px;
  overflow: hidden;
}
.welcome-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: clamp(48px, 7vh, 96px);
  scrollbar-gutter: stable;
}
.welcome-scroll::-webkit-scrollbar { width: 4px; }
.welcome-scroll::-webkit-scrollbar-track { background: transparent; }
.welcome-scroll::-webkit-scrollbar-thumb { border-radius: var(--zh-radius4); background: var(--zh-line-border); }
/* 聊天模式下移除欢迎页内边距，让 ChatView 撑满可用空间 */
.home-welcome.is-chat-mode {
  width: 100%;
  max-width: 100%;
  padding: 0;
}

.welcome-copy { max-width: 720px; }
.welcome-greeting { display: block; }
.welcome-greeting img { display: none; }
.welcome-actions { display: flex; gap: 10px; margin-top: 24px; }
.motion-stage { animation: fadeIn 300ms cubic-bezier(0, 0, 0.2, 1) both; }
.motion-stage-1 { animation-delay: 0ms; }
.motion-stage-2 { animation-delay: 50ms; }
.motion-stage-3 { animation-delay: 100ms; }
.motion-stage-4 { animation-delay: 200ms; }
.eyebrow { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 14px; font-weight: 600; }
h1 { margin: 0; font-size: clamp(36px, 4vw, 48px); line-height: 1.15; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.intro { max-width: 660px; margin: 18px 0 0; color: var(--zh-text-secondary); font-size: 16px; line-height: 1.75; text-wrap: pretty; }
.suggestion-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 38px; }
.suggestions-section { margin-top: 34px; }
.suggestions-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.suggestions-heading h2 { margin: 0; font-size: 16px; font-weight: 600; }
.suggestions-heading span { color: var(--zh-text-caption); font-size: 12px; }
.suggestions-section .suggestion-grid { margin-top: 12px; }
.suggestion-card { position: relative; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), background-color 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover, .suggestion-card:focus-visible { transform: translateY(-3px); border-color: var(--zh-line-theme20); box-shadow: var(--zh-shadow2); }
.suggestion-card:focus-visible { outline: 3px solid var(--zh-line-theme20); outline-offset: 2px; }
.suggestion-card:active { transform: translateY(-1px) scale(.99); }
.suggestion-card.is-selected { border-color: var(--zh-line-theme50); background: var(--zh-background-weaken); animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card :deep(.el-card__body) { min-height: 150px; padding: 18px; }
.suggestion-icon { width: 36px; height: 36px; display: grid; place-items: center; margin-bottom: 24px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover .suggestion-icon, .suggestion-card:focus-visible .suggestion-icon { transform: scale(1.04); }
.suggestion-card h2 { margin: 0; font-size: 15px; font-weight: 600; }
.suggestion-card p { margin: 7px 24px 0 0; color: var(--zh-text-caption); font-size: 12px; line-height: 1.6; }
.card-arrow { position: absolute; right: 16px; bottom: 18px; color: var(--zh-text-disabled); transform: rotate(-45deg); transition: color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover .card-arrow, .suggestion-card:focus-visible .card-arrow { color: var(--zh-text-theme); transform: rotate(-45deg) translateX(3px); }
.recent-projects { margin-top: 30px; }.recent-projects-heading { display: flex; align-items: baseline; justify-content: space-between; }.recent-projects-heading h2 { margin: 0; font-size: 16px; }.recent-projects-heading span { color: var(--zh-text-caption); font-size: 12px; }.project-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }.project-card { display: flex; min-width: 0; flex-direction: column; gap: 5px; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); color: var(--zh-text-primary); background: var(--zh-background-primary); text-align: left; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1); }.project-card:hover, .project-card:focus-visible { transform: translateY(-2px); border-color: var(--zh-line-theme50); background: var(--zh-background-weaken); box-shadow: var(--zh-shadow1); }.project-card:active { transform: translateY(-1px) scale(.99); transition-duration: 150ms; }.project-card strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.project-card span { color: var(--zh-text-caption); font-size: 11px; }
.project-skeleton { min-width: 0; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }.project-skeleton-title { width: 76%; }.project-skeleton-meta { width: 52%; margin-top: 8px; }
.composer { margin-top: 24px; padding: 9px 10px 10px; border: 1px solid var(--zh-line-heavier); border-radius: var(--zh-radius16); background: var(--zh-background-input); box-shadow: var(--zh-shadow1); transition: border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer:focus-within { border-color: var(--zh-line-theme50); box-shadow: 0 0 0 3px var(--zh-line-theme20), var(--zh-shadow2); }
.composer :deep(.el-textarea__inner) { min-height: 78px !important; padding: 10px 12px 6px; border: 0; background: transparent; box-shadow: none; color: var(--zh-text-primary); font-size: 15px; line-height: 1.65; }
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 2px 2px 0; }
.composer-tools { display: flex; align-items: center; }
.composer-tools :deep(.el-button) { color: var(--zh-text-secondary); }
.composer-toolbar :deep(.el-button.is-ready) { animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer-hint { margin: 10px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }

/* 功能 2：临时上传芯片（横向单行 + 固定宽度卡片 + 超宽横向滚动），见 doc/pending-specs/TempResourceChip.md */
.temp-resource-list { display: flex; flex-direction: row; align-items: stretch; gap: 8px; margin-bottom: 8px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: thin; }
.temp-resource-list::-webkit-scrollbar { height: 6px; }
.temp-resource-list::-webkit-scrollbar-thumb { background: var(--zh-line-heavier); border-radius: 3px; }
.temp-resource-chip { flex: 0 0 auto; width: 230px; display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-pop); box-shadow: var(--zh-shadow1); }
.temp-resource-badge { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: var(--zh-radius8); color: var(--zh-text-white); font-size: var(--zh-font-size11); font-weight: 700; letter-spacing: 0.02em; flex-shrink: 0; }
.temp-resource-badge.badge-word { background: #2563eb; }
.temp-resource-badge.badge-ppt { background: #d97706; }
.temp-resource-badge.badge-pdf { background: #dc2626; }
.temp-resource-badge.badge-image { background: #059669; }
.temp-resource-badge.badge-audio, .temp-resource-badge.badge-video { background: #7c3aed; }
.temp-resource-badge.badge-text, .temp-resource-badge.badge-other { background: #64748b; }
.temp-resource-meta { min-width: 0; flex: 1; }
.temp-resource-name { margin: 0; color: var(--zh-text-primary); font-size: var(--zh-font-size13); font-weight: 600; line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.temp-resource-status { display: flex; align-items: center; gap: 4px; margin: 2px 0 0; color: var(--zh-text-caption); font-size: var(--zh-font-size11); white-space: nowrap; overflow: hidden; }
.temp-resource-status.is-ready { color: var(--zh-green); }
.temp-resource-status.is-error { color: var(--zh-red); }
.temp-resource-actions { display: flex; align-items: center; gap: 2px; opacity: 0; transition: opacity 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.temp-resource-chip:hover .temp-resource-actions, .temp-resource-chip:focus-within .temp-resource-actions { opacity: 1; }
/* 无 hover（触屏/平板）常显动作按钮，避免转存/移除不可达 */
@media (hover: none) and (pointer: coarse), (max-width: 767.98px) {
  .temp-resource-actions { opacity: 1; }
}
.session-fields { display:grid; grid-template-columns: 1.5fr 1fr 1fr; gap:12px; }.session-fields :deep(.el-form-item){margin-bottom:0}.prompt-preview{width:100%;padding:10px 12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);line-height:1.65;white-space:pre-wrap}.resource-picker{display:grid;gap:8px;max-height:160px;overflow:auto;padding:10px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.empty-resources{color:var(--zh-text-caption);font-size:12px}
.resource-file-input{display:none}.resource-picker-dialog{max-height:280px;margin-top:12px}.knowledge-picker-header{display:grid;grid-template-columns:minmax(0,1fr) 240px;align-items:center;gap:16px}.knowledge-picker-header p{margin:0;color:var(--zh-text-secondary);font-size:13px;line-height:1.6}.selected-resource-count{display:inline-block;margin-right:16px;color:var(--zh-text-caption);font-size:12px}
.voice-panel{display:grid;justify-items:center;padding:8px 8px 0;text-align:center}.voice-orb{width:78px;height:78px;display:grid;place-items:center;padding:0;margin:4px 0 18px;border:1px solid var(--zh-line-theme20);border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);box-shadow:0 0 0 10px var(--zh-background-weaken);font-family:inherit;cursor:pointer;transition:border-color 200ms cubic-bezier(.4,0,.2,1),background-color 200ms cubic-bezier(.4,0,.2,1),box-shadow 200ms cubic-bezier(.4,0,.2,1),transform 200ms cubic-bezier(.4,0,.2,1)}.voice-orb:hover,.voice-orb:focus-visible{border-color:var(--zh-line-theme);box-shadow:0 0 0 10px var(--zh-line-theme20);transform:translateY(-1px)}.voice-orb:active{transform:scale(.96)}.voice-orb:disabled{cursor:wait;opacity:.75}.voice-orb.is-recording{border-color:var(--zh-red);color:var(--zh-red);background:var(--zh-danger-background);box-shadow:0 0 0 10px var(--zh-danger-background)}.voice-orb .el-icon{font-size:30px}.voice-panel>strong{font-size:18px}.voice-panel>p{max-width:350px;margin:8px 0 20px;color:var(--zh-text-secondary);font-size:13px;line-height:1.65}.voice-wave{height:42px;display:flex;align-items:center;gap:5px}.voice-wave i{width:3px;height:10px;border-radius:999px;background:var(--zh-line-theme50)}.voice-wave i:nth-child(2),.voice-wave i:nth-child(8){height:16px}.voice-wave i:nth-child(3),.voice-wave i:nth-child(7){height:24px}.voice-wave i:nth-child(4),.voice-wave i:nth-child(6){height:32px}.voice-wave i:nth-child(5){height:40px}.voice-status{width:100%;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;margin-top:16px;padding:12px 14px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);font-size:12px;text-align:left}.voice-status-dot{width:7px;height:7px;border-radius:50%;background:var(--zh-text-disabled)}
.voice-status-dot.is-recording{background:var(--zh-red);animation:pulse 200ms cubic-bezier(.4,0,.2,1) infinite}
.voice-status-dot.is-busy{background:var(--zh-text-theme)}.voice-status time{color:var(--zh-text-caption);font-family:var(--zh-font-number)}.voice-settings{width:100%;margin-top:18px;text-align:left}.voice-settings :deep(.el-select){width:100%}
.voice-wave.is-recording i{height:40px;background:var(--zh-line-theme);transform-origin:center;animation:waveMove .8s cubic-bezier(.4,0,.2,1) infinite}
.voice-wave.is-recording i:nth-child(1){animation-delay:0s}.voice-wave.is-recording i:nth-child(2){animation-delay:.08s}.voice-wave.is-recording i:nth-child(3){animation-delay:.16s}.voice-wave.is-recording i:nth-child(4){animation-delay:.24s}.voice-wave.is-recording i:nth-child(5){animation-delay:.32s}.voice-wave.is-recording i:nth-child(6){animation-delay:.4s}.voice-wave.is-recording i:nth-child(7){animation-delay:.48s}.voice-wave.is-recording i:nth-child(8){animation-delay:.56s}.voice-wave.is-recording i:nth-child(9){animation-delay:.64s}
@keyframes waveMove{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}

@media (max-width: 767.98px) {
  .home-welcome:not(.is-chat-mode) {
    /* 手机档顶栏 48px+safe-top，底部 TabBar 56px+safe-bottom */
    width: 100%;
    max-width: none;
    margin: 0;
    height: calc(100dvh - 48px - var(--zh-safe-top) - var(--zh-tabbar-h) - var(--zh-safe-bottom));
    padding: 0 0 10px;
  }
  .welcome-scroll {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
    width: 100%;
    min-width: 0;
    padding: 18px calc(18px + var(--zh-safe-right)) 20px calc(18px + var(--zh-safe-left));
    scrollbar-gutter: auto;
    overscroll-behavior-y: contain;
    text-align: left;
  }
  .composer-hint { display: none; }
  .welcome-copy { max-width: none; padding: 0 2px; }
  .welcome-greeting {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 8px;
  }
  .welcome-greeting img {
    display: block;
    width: 30px;
    height: 30px;
    flex: 0 0 30px;
    object-fit: contain;
  }
  .eyebrow { margin: 0; font-size: 12px; }
  .welcome-copy h1 { max-width: 16em; font-size: clamp(22px, 6vw, 26px); line-height: 1.3; letter-spacing: -0.035em; }
  .intro { max-width: 42ch; margin-top: 8px; font-size: 13px; line-height: 1.6; }
  .welcome-actions { display: none; }

  .suggestions-section { order: 1; margin-top: 22px; }
  .suggestions-heading h2 { font-size: 16px; }
  .suggestions-heading span { font-size: 10px; white-space: nowrap; }
  .suggestion-grid {
    display: flex;
    gap: 9px;
    margin: 10px calc(-18px - var(--zh-safe-right)) 0 calc(-18px - var(--zh-safe-left));
    padding: 2px calc(18px + var(--zh-safe-right)) 8px calc(18px + var(--zh-safe-left));
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
  }
  .suggestion-grid::-webkit-scrollbar { display: none; }
  .suggestion-card { flex: 0 0 min(216px, calc(100vw - 82px)); scroll-snap-align: start; }
  .suggestion-card :deep(.el-card) { border-color: var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-light); }
  .suggestion-card :deep(.el-card__body) { min-height: 108px; padding: 13px; }
  .suggestion-icon { width: 30px; height: 30px; margin-bottom: 10px; }
  .suggestion-card h2 { font-size: 14px; }
  .suggestion-card p { margin-top: 5px; font-size: 11px; line-height: 1.45; }
  .suggestion-card .card-arrow { right: 12px; bottom: 13px; }

  .recent-projects { order: 2; margin-top: 20px; }
  .recent-projects-heading { align-items: center; }
  .recent-projects-heading h2 { font-size: 16px; }
  .project-grid {
    display: flex;
    gap: 9px;
    margin: 10px calc(-18px - var(--zh-safe-right)) 0 calc(-18px - var(--zh-safe-left));
    padding: 0 calc(18px + var(--zh-safe-right)) 4px calc(18px + var(--zh-safe-left));
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
  }
  .project-grid::-webkit-scrollbar { display: none; }
  .project-card, .project-skeleton { flex: 0 0 min(236px, calc(100vw - 74px)); scroll-snap-align: start; }
  .project-card { min-height: 66px; justify-content: center; padding: 11px 13px; border-radius: var(--zh-radius12); }

  .composer {
    margin: 12px calc(12px + var(--zh-safe-right)) 0 calc(12px + var(--zh-safe-left));
    padding: 8px;
    border-radius: var(--zh-radius16);
    box-shadow: 0 -4px 18px rgb(31 63 120 / 6%);
  }
  .composer :deep(.el-textarea__inner) { min-height: 70px !important; padding: 8px 10px 4px; font-size: 16px; }
  .composer-toolbar { gap: 4px; }
  .composer-tools { min-width: 0; gap: 0; }
  .composer-tools :deep(.el-select) { width: 90px !important; flex: 0 0 90px; }
  .composer-tools :deep(.el-select .el-input__wrapper) { padding-inline: 8px; }
  .composer-tools :deep(.el-button) { padding-inline: 8px; }
  .composer-tool-label { display: none; }
  .composer-hint { margin-top: 7px; font-size: 11px; text-align: left; }
  .composer-shortcut-hint { display: none; }

  .session-fields { grid-template-columns:1fr; }
  .knowledge-picker-header { grid-template-columns:1fr; }
}

/* 平板档（768–1023.98）：双 grid 降 2 列、间距收敛 12px；知识库弹窗头部单列堆叠 */
@media (min-width: 768px) and (max-width: 1023.98px) {
  .project-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .suggestion-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .knowledge-picker-header { grid-template-columns:1fr; }
}

.managed-project-list{display:grid;gap:10px}.managed-project-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.managed-project-list article>div:first-child{display:grid;gap:4px;min-width:0}.managed-project-list strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.managed-project-list span{color:var(--zh-text-caption);font-size:12px}.managed-project-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:2px}
/* 手机档「更多」下拉渲染在弹窗 popper（teleport 到 body），危险项配色需全局命中 */
:global(.managed-project-dropdown .managed-project-danger) { color: var(--zh-red); }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}
</style>
