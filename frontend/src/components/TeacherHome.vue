<!--
  [数据交互说明]
  - 导入: 首页配置、Element Plus 图标
  - 输出: 教师端默认首页内容，由 `TeacherLayout.vue` 承载全局导航
-->
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Collection,
  Document,
  EditPen,
  MagicStick,
  Microphone,
  Monitor,
  More,
  Paperclip,
  Plus,
  Promotion,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'
import { INFO_FORM_DEFAULTS, isPlanningPrompt, requestNewChat, openChatSession } from '../config/teacherChat.config.js'
import { useUserStore } from '../storage/user'
import ChatView from './ChatView.vue'
import { archiveProject, copyProject, createAiSession, createProject, deleteProject, listProjects, listResources, transcribeAudio, uploadResource } from '../apis/teacher'

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
const canSend = computed(() => prompt.value.trim().length > 0)
const homeModelOptions = [
  { value: 'qwen3.7-max', label: 'Qwen 3.7 Max', description: '复杂教学与内容创作' },
  { value: 'qwen-plus', label: 'Qwen Plus', description: '日常任务，速度均衡' },
  { value: 'qwen-turbo', label: 'Qwen Turbo', description: '快速问答与整理' },
]
const homeReasoningOptions = [
  { value: 'none', label: '快速回答' },
  { value: 'low', label: '轻度推理' },
  { value: 'medium', label: '中度推理' },
  { value: 'high', label: '深度推理' },
]
const homeTaskModeOptions = [
  { value: 'general', label: '自由对话', hint: '问答、建议与通用协作' },
  { value: 'lesson_design', label: '课件与教案', hint: '进入结构化教学设计流程' },
  { value: 'content', label: '内容创作', hint: '讲稿、通知、文案与学习材料' },
  { value: 'assessment', label: '题目与测验', hint: '试题、答案、解析与评价量规' },
  { value: 'research', label: '研究与总结', hint: '调研、归纳、对比与报告' },
  { value: 'data_analysis', label: '资料分析', hint: '提取重点并形成结论' },
  { value: 'interactive', label: '互动与代码', hint: '小游戏、HTML 与互动组件' },
]
const selectedHomeModel = ref(window.localStorage.getItem('a12:chat-model') || homeModelOptions[0].value)
const selectedHomeReasoning = ref(window.localStorage.getItem('a12:reasoning-effort') || 'low')
const selectedHomeTaskMode = ref('general')
const currentHomeModel = computed(() => homeModelOptions.find((item) => item.value === selectedHomeModel.value) || homeModelOptions[0])
const currentHomeReasoning = computed(() => homeReasoningOptions.find((item) => item.value === selectedHomeReasoning.value) || homeReasoningOptions[1])
const currentHomeTaskMode = computed(() => homeTaskModeOptions.find((item) => item.value === selectedHomeTaskMode.value) || homeTaskModeOptions[0])
watch(selectedHomeModel, value => window.localStorage.setItem('a12:chat-model', value))
watch(selectedHomeReasoning, value => window.localStorage.setItem('a12:reasoning-effort', value))
const composerInput = ref(null)
const activeSuggestionId = ref(null)
const iconMap = { Presentation: Monitor, Document, MagicStick }
const projects = ref([])
const projectsLoading = ref(true)
const resourcesLoading = ref(false)
const availableResources = ref([])
const selectedResourceIds = ref([])
const uploadDialogVisible = ref(false)
const knowledgeDialogVisible = ref(false)
const resourceSearch = ref('')
const resourceUploading = ref(false)
const resourceUploadProgress = ref(0)
const resourceFileInput = ref(null)
const uploadedResourceNames = ref([])
const uploadDragging = ref(false)
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

const handleHomeAddCommand = (command) => {
  if (command === 'upload_files') {
    openUploadDialog()
    return
  }
  if (command === 'knowledge') {
    void openKnowledgeDialog()
    return
  }
  selectedHomeTaskMode.value = command
}

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
  const normalizedResourceIds = normalizeResourceIds(resourceIds)
  const normalizedWorkspaceContext = normalizeWorkspaceContext({
    ...workspaceContext,
    uploadedResources: workspaceContext.uploadedResources || workspaceContext.uploaded_resources || pendingUploadedResources.value,
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
 * 从欢迎页发送提示词：明确的教学设计需求进入备课流程，其他内容进入普通对话。
 * 普通对话使用本地会话 ID，不创建后端“备课会话”。
 */
const sendPrompt = async () => {
  if (!canSend.value) return
  const text = prompt.value.trim()

  if (selectedHomeTaskMode.value !== 'lesson_design' && !isPlanningPrompt(text)) {
    chatMode.value = 'general'
    chatSessionId.value = `local-chat-${Date.now()}`
    chatPrompt.value = text
    chatResourceIds.value = [...selectedResourceIds.value]
    // 普通对话后续也可以切换到生成工作台；提前保留资料/上传文件上下文，
    // 避免只有备课流能把资源带进工作台。
    chatWorkspaceContext.value = normalizeWorkspaceContext({
      uploadedResources: pendingUploadedResources.value,
    }, selectedResourceIds.value)
    chatContinuationHistory.value = []
    chatResume.value = false
    viewMode.value = 'chat'
    prompt.value = ''
    activeSuggestionId.value = null
    return
  }

  prompt.value = ''
  activeSuggestionId.value = null
  await startPlanningSession(text, [...selectedResourceIds.value], [], normalizeWorkspaceContext({
    uploadedResources: pendingUploadedResources.value,
  }, selectedResourceIds.value))
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
  chatMode.value = 'planning'
  chatSessionId.value = target.id
  chatPrompt.value = target.title || ''
  chatResourceIds.value = []
  chatWorkspaceContext.value = { resourceIds: [], resource_ids: [], uploadedResources: [], uploaded_resources: [], community: null }
  chatContinuationHistory.value = []
  chatResume.value = true
  viewMode.value = 'chat'
  openChatSession.value = null
}, { immediate: true })

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
const openUploadDialog = () => {
  uploadedResourceNames.value = []
  resourceUploadProgress.value = 0
  uploadDialogVisible.value = true
}
const openKnowledgeDialog = async () => {
  resourceSearch.value = ''
  knowledgeDialogVisible.value = true
  await loadAvailableResources()
}
const triggerResourceUpload = () => resourceFileInput.value?.click()
const uploadLocalFiles = async (rawFiles) => {
  const supportedExtensions = [
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'md', 'csv', 'srt', 'vtt', 'ass',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
    'mp3', 'wav', 'm4a', 'aac', 'ogg', 'mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv', 'flv',
  ]
  const candidates = Array.from(rawFiles || [])
  const files = candidates.filter((file) => supportedExtensions.includes(file.name.split('.').pop()?.toLowerCase()))
  if (files.length !== candidates.length) ElMessage.warning('已忽略不支持的文件格式')
  if (!files.length) return
  resourceUploading.value = true; resourceUploadProgress.value = 0
  try {
    for (let index = 0; index < files.length; index += 1) {
      const file = files[index]
      const resource = await uploadResource(file, (progress) => { resourceUploadProgress.value = Math.round(((index + progress / 100) / files.length) * 100) })
      const resourceId = resource?.id || resource?.resource_id
      if (resourceId && !selectedResourceIds.value.includes(resourceId)) selectedResourceIds.value.push(resourceId)
      if (resourceId) {
        pendingUploadedResources.value = [
          ...pendingUploadedResources.value.filter((item) => String(item.resource_id || item.id) !== String(resourceId)),
          {
            resource_id: String(resourceId),
            id: String(resourceId),
            file_name: file.name,
            file_type: file.type || file.name.split('.').pop()?.toLowerCase() || '',
            file_size: file.size,
            source: 'teacher_upload',
          },
        ]
      }
      uploadedResourceNames.value.push(file.name)
    }
    ElMessage.success(`${files.length} 份资料已上传并引用`)
  } catch (error) { ElMessage.error(error?.message || '资料上传失败') }
  finally { resourceUploading.value = false }
}
const uploadPickedResource = async (event) => {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  await uploadLocalFiles(files)
}
const dropResourceFiles = async (event) => {
  uploadDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  if (!files.length) return
  await uploadLocalFiles(files)
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
  greetingClockTimer = window.setInterval(() => { currentTime.value = new Date() }, 60_000)
})
</script>

<template>
  <section class="home-welcome" :class="{ 'is-chat-mode': viewMode === 'chat' }">
    <!-- 欢迎视图 -->
    <template v-if="viewMode === 'welcome'">
    <div class="welcome-scroll">
    <div class="welcome-copy motion-stage motion-stage-1">
      <p class="eyebrow">{{ teacherGreeting }}</p>
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

    <div class="suggestion-grid motion-stage motion-stage-3">
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
    </div>

    <section class="composer motion-stage motion-stage-4" aria-label="AI 教学任务输入">
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
          <el-dropdown trigger="click" placement="top-start" @command="handleHomeAddCommand">
            <button type="button" class="home-composer-tool home-composer-add" aria-label="添加文件、知识库或选择任务类型"><el-icon><Plus /></el-icon></button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="upload_files">
                  <span class="home-menu-item"><strong><el-icon><Paperclip /></el-icon>文件和资料</strong><small>文档、表格、演示文稿、图片、音频和视频</small></span>
                </el-dropdown-item>
                <el-dropdown-item command="knowledge">
                  <span class="home-menu-item"><strong><el-icon><Collection /></el-icon>引用知识库</strong><small>使用个人资源库中的已有资料</small></span>
                </el-dropdown-item>
                <el-dropdown-item v-for="(item, index) in homeTaskModeOptions" :key="item.value" :command="item.value" :divided="index === 0" :class="{ selected: selectedHomeTaskMode === item.value }">
                  <span class="home-menu-item"><strong>{{ item.label }}</strong><small>{{ item.hint }}</small></span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <span class="home-mode-pill">{{ currentHomeTaskMode.label }}</span>

          <el-dropdown trigger="click" placement="top-start" @command="selectedHomeModel = $event">
            <button type="button" class="home-composer-tool"><span>{{ currentHomeModel.label }}</span><el-icon><ArrowDown /></el-icon></button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="item in homeModelOptions" :key="item.value" :command="item.value" :class="{ selected: selectedHomeModel === item.value }">
                  <span class="home-menu-item"><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown trigger="click" placement="top-start" @command="selectedHomeReasoning = $event">
            <button type="button" class="home-composer-tool"><span>{{ currentHomeReasoning.label }}</span><el-icon><ArrowDown /></el-icon></button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="item in homeReasoningOptions" :key="item.value" :command="item.value" :class="{ selected: selectedHomeReasoning === item.value }">{{ item.label }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <button v-if="selectedResourceIds.length" type="button" class="home-resource-count" @click="openKnowledgeDialog">已引用 {{ selectedResourceIds.length }} 项</button>
        </div>
        <div class="home-composer-actions">
          <el-tooltip content="打开语音输入"><span><el-button text circle aria-label="语音输入" @click="voiceDialogVisible = true"><el-icon><Microphone /></el-icon></el-button></span></el-tooltip>
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
      </div>
    </section>

    <p class="composer-hint motion-stage motion-stage-4">{{ TEACHER_HOME.composer.hint }} · Enter 发送 · Shift + Enter 换行</p>
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
      :resume="chatResume"
      :initial-model="selectedHomeModel"
      :initial-reasoning="selectedHomeReasoning"
      :initial-task-mode="selectedHomeTaskMode"
      @back="closeChatView"
      @open-workspace="openWorkspaceFromChat"
      @planning-request="handlePlanningRequest"
    />

    <!-- 资料上传 / 知识库 / 语音对话框（欢迎视图和聊天视图共用）-->
    <el-dialog v-model="uploadDialogVisible" title="添加资料" width="min(560px, 92vw)">
      <input ref="resourceFileInput" class="resource-file-input" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.csv,.srt,.vtt,.ass,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp3,.wav,.m4a,.aac,.ogg,.mp4,.avi,.mov,.mkv,.webm,.wmv,.flv" @change="uploadPickedResource" />
      <button
        type="button"
        :class="['upload-dropzone', { 'is-dragging': uploadDragging, 'is-touch': isMobile }]"
        :disabled="resourceUploading"
        @click="triggerResourceUpload"
        @dragenter.prevent="uploadDragging = true"
        @dragover.prevent="uploadDragging = true"
        @dragleave.prevent="uploadDragging = false"
        @drop.prevent="dropResourceFiles"
      >
        <el-icon><Paperclip /></el-icon>
        <strong class="dropzone-title-default">{{ uploadDragging ? '松开即可添加资料' : '点击选择或拖入本地资料' }}</strong>
        <strong class="dropzone-title-touch">选择文件</strong>
        <span>支持文档、图片、音视频与字幕文件，可多选</span>
      </button>
      <el-progress v-if="resourceUploading" :percentage="resourceUploadProgress" :show-text="true" />
      <div v-if="uploadedResourceNames.length" class="uploaded-resource-list"><span>已自动引用</span><p v-for="name in uploadedResourceNames" :key="name">{{ name }}</p></div>
      <template #footer><el-button @click="uploadDialogVisible = false">完成</el-button></template>
    </el-dialog>

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
.composer { margin-top:24px; padding: 9px 10px 10px; border: 1px solid var(--zh-line-heavier); border-radius: 24px; background: var(--zh-background-input); box-shadow: var(--zh-shadow1); transition: border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer:focus-within {
  border-color: var(--zh-line-theme50);
  box-shadow: var(--zh-shadow1);
}
.composer :deep(.el-textarea__inner) { min-height: 78px !important; padding: 10px 12px 6px; border: 0; background: transparent; box-shadow: none; color: var(--zh-text-primary); font-size: 15px; line-height: 1.65; }
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; gap:10px;padding: 2px 2px 0; }
.composer-tools { display:flex;min-width:0;align-items:center;gap:4px;overflow-x:auto;scrollbar-width:none; }
.composer-tools::-webkit-scrollbar { display:none; }
.home-composer-tool { display:inline-flex;min-height:30px;align-items:center;gap:5px;padding:0 9px;border:0;border-radius:9px;color:var(--zh-text-secondary);background:transparent;font:inherit;font-size:12px;white-space:nowrap;cursor:pointer; }
.home-composer-tool:hover { color:var(--zh-text-primary);background:var(--zh-background-option); }
.home-composer-add { width:32px;justify-content:center;padding:0;border:1px solid var(--zh-line-border);border-radius:50%; }
.home-mode-pill { display:inline-flex;min-height:28px;align-items:center;padding:0 10px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-option-on);font-size:12px;font-weight:600;white-space:nowrap; }
.home-resource-count { min-height:28px;padding:0 9px;border:0;border-radius:999px;color:var(--zh-text-secondary);background:var(--zh-background-option);font-size:11px;white-space:nowrap;cursor:pointer; }
.home-composer-actions { display:inline-flex;flex:none;align-items:center;gap:4px; }
.home-composer-actions :deep(.el-button) { color:var(--zh-text-secondary); }
.home-composer-actions :deep(.el-button--primary) { color:#fff; }
.home-menu-item { display:grid;min-width:225px;gap:2px;padding:3px 0; }
.home-menu-item strong { display:inline-flex;align-items:center;gap:7px;color:var(--zh-text-primary);font-size:13px; }
.home-menu-item small { color:var(--zh-text-caption);font-size:11px; }
.composer-toolbar :deep(.el-button.is-ready) { animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer-hint { margin: 10px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }
.session-fields { display:grid; grid-template-columns: 1.5fr 1fr 1fr; gap:12px; }.session-fields :deep(.el-form-item){margin-bottom:0}.prompt-preview{width:100%;padding:10px 12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);line-height:1.65;white-space:pre-wrap}.resource-picker{display:grid;gap:8px;max-height:160px;overflow:auto;padding:10px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.empty-resources{color:var(--zh-text-caption);font-size:12px}
.resource-file-input{display:none}.resource-picker-dialog{max-height:280px;margin-top:12px}.upload-dropzone{width:100%;min-height:180px;display:grid;place-items:center;align-content:center;gap:9px;padding:24px;border:1px dashed var(--zh-line-theme50);border-radius:var(--zh-radius12);color:var(--zh-text-theme);background:var(--zh-background-weaken);cursor:pointer;transition:border-color 200ms cubic-bezier(.4,0,.2,1),background-color 200ms cubic-bezier(.4,0,.2,1),transform 200ms cubic-bezier(.4,0,.2,1),box-shadow 200ms cubic-bezier(.4,0,.2,1)}.upload-dropzone:hover,.upload-dropzone:focus-visible{border-color:var(--zh-line-theme);background:var(--zh-background-option-on);transform:translateY(-1px)}.upload-dropzone.is-dragging{border-color:var(--zh-line-theme);background:var(--zh-background-option-on);box-shadow:0 0 0 4px var(--zh-line-theme20);transform:scale(1.01)}.upload-dropzone:disabled{cursor:wait;opacity:.65}.upload-dropzone .el-icon{font-size:28px}.upload-dropzone strong{color:var(--zh-text-primary);font-size:16px}.upload-dropzone span{color:var(--zh-text-caption);font-size:12px}.uploaded-resource-list{display:grid;gap:6px;margin-top:14px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-light)}.uploaded-resource-list>span{color:var(--zh-text-caption);font-size:12px}.uploaded-resource-list p{margin:0;color:var(--zh-text-secondary);font-size:13px}.knowledge-picker-header{display:grid;grid-template-columns:minmax(0,1fr) 240px;align-items:center;gap:16px}.knowledge-picker-header p{margin:0;color:var(--zh-text-secondary);font-size:13px;line-height:1.6}.selected-resource-count{display:inline-block;margin-right:16px;color:var(--zh-text-caption);font-size:12px}
/* 触屏降级：无拖拽能力，隐藏拖拽提示文案；dropzone 本体即「选择文件」按钮，点击复用既有文件选择入口 */
.dropzone-title-touch{display:none}
.upload-dropzone.is-touch .dropzone-title-default{display:none}
.upload-dropzone.is-touch .dropzone-title-touch{display:block}
@media (hover: none) and (pointer: coarse) {
  .upload-dropzone .dropzone-title-default{display:none}
  .upload-dropzone .dropzone-title-touch{display:block}
}
.voice-panel{display:grid;justify-items:center;padding:8px 8px 0;text-align:center}.voice-orb{width:78px;height:78px;display:grid;place-items:center;padding:0;margin:4px 0 18px;border:1px solid var(--zh-line-theme20);border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);box-shadow:0 0 0 10px var(--zh-background-weaken);font-family:inherit;cursor:pointer;transition:border-color 200ms cubic-bezier(.4,0,.2,1),background-color 200ms cubic-bezier(.4,0,.2,1),box-shadow 200ms cubic-bezier(.4,0,.2,1),transform 200ms cubic-bezier(.4,0,.2,1)}.voice-orb:hover,.voice-orb:focus-visible{border-color:var(--zh-line-theme);box-shadow:0 0 0 10px var(--zh-line-theme20);transform:translateY(-1px)}.voice-orb:active{transform:scale(.96)}.voice-orb:disabled{cursor:wait;opacity:.75}.voice-orb.is-recording{border-color:var(--zh-red);color:var(--zh-red);background:var(--zh-danger-background);box-shadow:0 0 0 10px var(--zh-danger-background)}.voice-orb .el-icon{font-size:30px}.voice-panel>strong{font-size:18px}.voice-panel>p{max-width:350px;margin:8px 0 20px;color:var(--zh-text-secondary);font-size:13px;line-height:1.65}.voice-wave{height:42px;display:flex;align-items:center;gap:5px}.voice-wave i{width:3px;height:10px;border-radius:999px;background:var(--zh-line-theme50)}.voice-wave i:nth-child(2),.voice-wave i:nth-child(8){height:16px}.voice-wave i:nth-child(3),.voice-wave i:nth-child(7){height:24px}.voice-wave i:nth-child(4),.voice-wave i:nth-child(6){height:32px}.voice-wave i:nth-child(5){height:40px}.voice-status{width:100%;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;margin-top:16px;padding:12px 14px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);font-size:12px;text-align:left}.voice-status-dot{width:7px;height:7px;border-radius:50%;background:var(--zh-text-disabled)}
.voice-status-dot.is-recording{background:var(--zh-red);animation:pulse 200ms cubic-bezier(.4,0,.2,1) infinite}
.voice-status-dot.is-busy{background:var(--zh-text-theme)}.voice-status time{color:var(--zh-text-caption);font-family:var(--zh-font-number)}.voice-settings{width:100%;margin-top:18px;text-align:left}.voice-settings :deep(.el-select){width:100%}
.voice-wave.is-recording i{height:40px;background:var(--zh-line-theme);transform-origin:center;animation:waveMove .8s cubic-bezier(.4,0,.2,1) infinite}
.voice-wave.is-recording i:nth-child(1){animation-delay:0s}.voice-wave.is-recording i:nth-child(2){animation-delay:.08s}.voice-wave.is-recording i:nth-child(3){animation-delay:.16s}.voice-wave.is-recording i:nth-child(4){animation-delay:.24s}.voice-wave.is-recording i:nth-child(5){animation-delay:.32s}.voice-wave.is-recording i:nth-child(6){animation-delay:.4s}.voice-wave.is-recording i:nth-child(7){animation-delay:.48s}.voice-wave.is-recording i:nth-child(8){animation-delay:.56s}.voice-wave.is-recording i:nth-child(9){animation-delay:.64s}
@keyframes waveMove{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}

@media (max-width: 767.98px) {
  .home-welcome:not(.is-chat-mode) {
    /* 手机档顶栏 48px+safe-top，底部 TabBar 56px+safe-bottom */
    height: calc(100dvh - 48px - var(--zh-safe-top) - var(--zh-tabbar-h) - var(--zh-safe-bottom));
  }
  .home-welcome:not(.is-chat-mode),
  .welcome-scroll { width: min(100% - 28px, 540px); }
  .welcome-scroll { padding-top: 32px; }
  .suggestion-grid, .project-grid { grid-template-columns: 1fr; }
  .suggestion-card :deep(.el-card__body) { min-height: 118px; }
  .suggestion-icon { margin-bottom: 16px; }
  .session-fields { grid-template-columns:1fr; }
  .knowledge-picker-header { grid-template-columns:1fr; }
  .composer-toolbar { align-items:flex-end;flex-wrap:wrap; }
  .composer-tools { width:100%; }
  .home-composer-actions { margin-left:auto; }
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
