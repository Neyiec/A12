import { apiRequest, del, get, post, put } from '../utils/api'
import axios from 'axios'
import { useUserStore } from '../storage/user.js'

export const listResources = (params) => get('/api/v1/resources', params)
export const uploadResource = async (file, onProgress, { allowAi = false, description = '' } = {}) => {
  if (!file?.name || !Number.isFinite(file.size)) throw new Error('请选择有效文件')
  const tokenResult = await post('/api/v1/resources/upload-tokens', {
    file_name: file.name,
    file_type: file.type || 'application/octet-stream',
  })
  if (tokenResult?.code !== 200 && tokenResult?.code !== 0) throw new Error(tokenResult?.message || '获取上传地址失败')
  const token = tokenResult?.data || {}
  if (!token.object_key || !token.upload_url) throw new Error('上传服务未返回对象地址')
  await axios.put(token.upload_url, file, {
    timeout: 30 * 60 * 1000,
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) onProgress(Math.min(95, Math.round(event.loaded / event.total * 95)))
    },
  })
  const confirmed = await post('/api/v1/resources/uploaded-files', {
    object_key: token.object_key,
    file_name: file.name,
    file_size: file.size,
    file_type: file.type || 'application/octet-stream',
    description: String(description || '').slice(0, 240),
  })
  if (confirmed?.code !== 200 && confirmed?.code !== 0) throw new Error(confirmed?.message || '素材入库失败')
  let resource = confirmed?.data || confirmed
  if (allowAi && resource?.id) {
    const enabled = await apiRequest({ url: `/api/v1/resources/${resource.id}`, method: 'patch', data: { allow_ai: 1 } })
    if (enabled?.code !== 200 && enabled?.code !== 0) throw new Error(enabled?.message || '素材已上传，但 AI 引用权限设置失败')
    resource = enabled?.data || resource
  }
  onProgress?.(100)
  return resource
}
export const deleteResource = (id) => del(`/api/v1/resources/${id}`)
/**
 * 功能 2（临时上传）：直连 Python 上传临时资料——解析落盘并向量化入 temp 分区索引，
 * 不进个人素材库，仅本次大纲/页面生成可检索；会话结束由 deleteAiSession 统一清理。
 * timeout 放宽：大文件（PPT/视频）解析+向量化耗时远超默认 10s，超时会产生服务端已建索引但前端未登记的孤儿。
 */
export const uploadTempResource = (file) => apiRequest({ url: '/api/v1/python/resources/upload', method: 'post', data: file, timeout: 120000 })
/** 清理临时上传：删除 temp 向量索引与 Python 磁盘目录（resource_ids 为 res_xxx 数组）。 */
export const cleanupTempResources = (resourceIds) => apiRequest({
  url: `/api/v1/python/resources/temp?resource_ids=${encodeURIComponent((resourceIds || []).join(','))}`,
  method: 'delete',
})

// ---------- 临时上传登记表（sessionStorage，标签页内生效） ----------
const TEMP_RESOURCE_KEY = (userId) => `a12:temp-resources:${userId || 'anon'}`
const readTempRegistry = () => {
  try {
    const userId = useUserStore().userInfo?.user_id
    const raw = sessionStorage.getItem(TEMP_RESOURCE_KEY(userId))
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch { return [] }
}
const writeTempRegistry = (ids) => {
  try {
    const userId = useUserStore().userInfo?.user_id
    sessionStorage.setItem(TEMP_RESOURCE_KEY(userId), JSON.stringify([...new Set(ids.map(String))]))
  } catch { /* 存储不可用时静默：清理退化为依赖芯片列表本身 */ }
}
/** 临时资料上传成功后登记，供 deleteAiSession 会话结束时统一清理。 */
export const rememberTempResource = (resourceId) => {
  if (!resourceId) return
  writeTempRegistry([...readTempRegistry(), String(resourceId)])
}
/** 转存/手动移除后撤销登记。 */
export const forgetTempResource = (resourceId) => {
  if (!resourceId) return
  const target = String(resourceId)
  writeTempRegistry(readTempRegistry().filter((id) => id !== target))
}
export const listTempResourceIds = () => readTempRegistry()
export const downloadResource = (id) => post(`/api/v1/resources/${id}/download-url`)
export const updateResource = (id, data) => apiRequest({ url: `/api/v1/resources/${id}`, method: 'patch', data })
export const batchResourceAction = (data) => post('/api/v1/resources/batch-actions', data)
export const getResourcePermission = (id) => get(`/api/v1/resources/${id}/permission`)
export const setResourcePermission = (id, data) => put(`/api/v1/resources/${id}/permission`, data)
export const listResourceTags = () => get('/api/v1/resources/tags')
export const createResourceTag = (data) => post('/api/v1/resources/tags', data)
export const updateResourceTag = (id, data) => apiRequest({ url: `/api/v1/resources/tags/${id}`, method: 'patch', data })
export const deleteResourceTag = (id) => del(`/api/v1/resources/tags/${id}`)
export const listResourceCategories = () => get('/api/v1/resources/categories')
export const createResourceCategory = (data) => post('/api/v1/resources/categories', data)
export const updateResourceCategory = (id, data) => apiRequest({ url: `/api/v1/resources/categories/${id}`, method: 'patch', data })
export const deleteResourceCategory = (id) => del(`/api/v1/resources/categories/${id}`)

export const syncResourceIndex = (data) => post('/api/v1/python/resources/index/sync', data)
// 资源索引 bootstrap 需要处理全量素材，后端耗时较长，单独放宽超时，避免被默认 10 秒超时误判失败。
const RESOURCE_INDEX_BOOTSTRAP_TIMEOUT = 210000
export const bootstrapResourceIndex = (data) => apiRequest({
  url: '/api/v1/python/resources/index/bootstrap',
  method: 'post',
  data,
  timeout: RESOURCE_INDEX_BOOTSTRAP_TIMEOUT,
})
export const updateResourceIndexMetadata = (data) => apiRequest({ url: '/api/v1/python/resources/index/metadata', method: 'patch', data })
export const getResourceIndexOverview = () => get('/api/v1/python/resources/index/overview')
export const listResourceIndexResources = (params) => get('/api/v1/python/resources/index/resources', params)
export const getResourceIndexResource = (sourceType, resourceId, params) => get(`/api/v1/python/resources/index/resources/${sourceType}/${resourceId}`, params)
export const listResourceIndexLogs = (params) => get('/api/v1/python/resources/index/logs', params)
export const searchResourceIndex = (data) => post('/api/v1/python/resources/index/search', data)
export const deleteResourceIndex = (sourceType, resourceId) => del(`/api/v1/python/resources/index/${sourceType}/${resourceId}`)

export const listCommunityItems = (params) => get('/api/v1/community/items', params)
export const favoriteCommunityItem = (id) => put(`/api/v1/community/items/${id}/favorite`)
export const unfavoriteCommunityItem = (id) => del(`/api/v1/community/items/${id}/favorite`)
// 功能11：点赞/取消点赞与热门榜单
export const likeCommunityItem = (id) => put(`/api/v1/community/items/${id}/like`)
export const unlikeCommunityItem = (id) => del(`/api/v1/community/items/${id}/like`)
export const listCommunityRankings = (params) => get('/api/v1/community/rankings', params)
export const reuseCommunityItem = (id, data) => post(`/api/v1/community/items/${id}/reuse`, data)
export const getCommunityItem = (id) => get(`/api/v1/community/items/${id}`)
export const recordCommunityView = (id) => post(`/api/v1/community/items/${id}/view-events`)
export const listCommunityFavorites = (params) => get('/api/v1/community/favorites', params)
export const listCommunityRecentViews = (params) => get('/api/v1/community/recent-views', params)
export const removeCommunityRecentView = (id) => del(`/api/v1/community/recent-views/${id}`)
export const createCommunitySubmission = (data) => post('/api/v1/community/submissions', data)
export const listCommunitySubmissions = (params) => get('/api/v1/community/submissions', params)
export const getCommunitySubmission = (id) => get(`/api/v1/community/submissions/${id}`)
export const updateCommunitySubmission = (id, data) => apiRequest({ url: `/api/v1/community/submissions/${id}`, method: 'patch', data })
export const saveCommunitySubmissionVersion = (id, data) => post(`/api/v1/community/submissions/${id}/versions`, data)
export const submitCommunitySubmission = (id, data) => post(`/api/v1/community/submissions/${id}/submit`, data)
export const createCommunityReport = (data) => post('/api/v1/community/reports', data)
export const listCommunityReports = (params) => get('/api/v1/community/reports', params)
export const getCommunityReport = (id) => get(`/api/v1/community/reports/${id}`)

export const listExportTasks = (params) => get('/api/v1/export-tasks', params)
export const getExportTask = (id) => get(`/api/v1/export-tasks/${id}`)
// 导出接口会等待文件生成服务返回成果，单独放宽超时，避免大课件被默认 10 秒超时误判失败。
const EXPORT_TASK_TIMEOUT = 210000
export const retryExportTask = async (id) => {
  const created = await post(`/api/v1/export-tasks/${id}/retry`)
  if (created?.code !== 200 && created?.code !== 0) return created
  return runClientExport(created.data)
}
export const downloadExportArtifact = (id) => post(`/api/v1/export-artifacts/${id}/download-url`)
export const createExportTask = async (data) => {
  const created = await post('/api/v1/export-tasks', data)
  if (created?.code !== 200 && created?.code !== 0) return created
  return runClientExport(created.data)
}

async function runClientExport(task) {
  if (!task?.id) throw new Error('导出任务未返回 ID')
  try {
    const prepared = await get(`/api/v1/export-tasks/${task.id}/payload`)
    if (prepared?.code !== 200 && prepared?.code !== 0) throw new Error(prepared?.message || '读取导出页面失败')
    const payload = prepared.data || {}
    let generated
    if (['word', 'docx'].includes(task.export_type)) {
      let lessonPlan = payload.lesson_plan
      if (!lessonPlan) {
        const response = await generateLessonPlan({
          title: payload.title, subject: payload.subject, grade: payload.grade,
          teaching_goals: payload.teaching_goals, requirements: payload.requirements,
          reference_text: payload.reference_text, slides: payload.slides,
          outline: { slides: payload.slides },
        })
        if (response?.code !== 200 && response?.code !== 0) throw new Error(response?.message || '教案生成失败')
        lessonPlan = response.data?.lesson_plan
      }
      generated = await exportLessonPlanDocx({ title: payload.title, filename: payload.filename, lesson_plan: lessonPlan })
    } else {
      if (!Array.isArray(payload.slides) || !payload.slides.length) throw new Error('项目没有可导出的课件页面')
      generated = await exportPresentationPptx({
        title: payload.title, filename: payload.filename, slides: payload.slides,
        fidelity: payload.fidelity, package_static_assets: payload.package_static_assets,
      })
    }
    const blob = generated?.data
    if (!(blob instanceof Blob) || !blob.size) throw new Error('Python 未返回有效导出文件')
    const disposition = generated?.headers?.['content-disposition'] || ''
    const encodedName = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
    const plainName = disposition.match(/filename="?([^";]+)"?/i)?.[1]
    let filename = payload.filename || `export-${task.id}.${task.export_type === 'word' ? 'docx' : 'pptx'}`
    try { filename = encodedName ? decodeURIComponent(encodedName) : plainName || filename } catch { /* 保留默认名称。 */ }
    if (generated?.headers?.['content-type']?.includes('zip')) filename = filename.replace(/\.[^.]+$/, '.zip')
    const body = new FormData()
    body.append('file', new File([blob], filename, { type: blob.type || 'application/octet-stream' }))
    const saved = await apiRequest({ url: `/api/v1/export-tasks/${task.id}/artifact`, method: 'post', data: body, timeout: EXPORT_TASK_TIMEOUT })
    if (saved?.code !== 200 && saved?.code !== 0) throw new Error(saved?.message || '登记导出文件失败')
    return saved
  } catch (error) {
    await post(`/api/v1/export-tasks/${task.id}/failure`, { error: String(error?.message || '导出失败') }).catch(() => {})
    throw error
  }
}
export const precheckProjectExport = (id, data) => post(`/api/v1/projects/${id}/export-prechecks`, data)
export const cancelExportTask = (id) => post(`/api/v1/export-tasks/${id}/cancel`)
export const getExportQualityReport = (id) => get(`/api/v1/export-tasks/${id}/quality-report`)
export const getExportArtifact = (id) => get(`/api/v1/export-artifacts/${id}`)
export const createExportPreviewUrl = (id) => post(`/api/v1/export-artifacts/${id}/preview-url`)

export const patchProject = (id, data) => apiRequest({ url: `/api/v1/projects/${id}`, method: 'patch', data })
export const createAiSession = (data) => post('/api/v1/ai/sessions', data)
export const saveDirectOutlineResult = (id, data) => apiRequest({ url: `/api/v1/ai/sessions/${id}/outline-results`, method: 'post', data, timeout: 30000 })
/** 工作台的非流式交互同样由浏览器直连 FastAPI；Java 只接收最终业务快照。 */
export async function sendDirectOutlineSessionMessage(id, message, knownContext = {}, pythonSessionId = '') {
  const userId = String(useUserStore().userInfo?.user_id || '')
  const response = await streamOutlineChat({
    user_id: userId, session_id: pythonSessionId || undefined, message,
    known_context: knownContext,
    resource_ids: (knownContext?.workspace_context?.resource_ids || []).map((id) => String(id)),
    enable_rag: false, enable_web: false, slide_count: 8, language: 'zh-CN',
  })
  if (!response.ok) throw new Error(`大纲请求失败（HTTP ${response.status}）`)
  const reader = response.body?.getReader()
  if (!reader) throw new Error('大纲服务未返回数据流')
  const decoder = new TextDecoder()
  let buffer = '', session = pythonSessionId, final = null, question = null, error = ''
  const dispatch = (frame) => {
    const event = frame.match(/(?:^|\n)event:\s*([^\n]+)/)?.[1]?.trim()
    const raw = frame.match(/(?:^|\n)data:\s*([^\n]+)/)?.[1]
    if (!raw) return
    let data
    try { data = JSON.parse(raw) } catch { return }
    if (event === 'session') session = String(data.session_id || session)
    if (event === 'final') final = data
    if (event === 'question') question = data
    if (event === 'error') error = data.message || '大纲生成失败'
  }
  for (;;) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() || ''
    frames.forEach(dispatch)
    if (done) break
  }
  if (buffer.trim()) dispatch(buffer)
  const saved = await saveDirectOutlineResult(id, {
    message, python_session_id: session,
    status: final ? 'completed' : question ? 'need_clarification' : 'failed',
    final_data: final, question: question?.question || '', error_message: error,
  })
  if (saved?.code !== 200 && saved?.code !== 0) throw new Error(saved?.message || '大纲结果保存失败')
  if (!final && !question) throw new Error(error || '大纲服务未返回有效结果')
  return saved
}
export const listAiSessions = () => get('/api/v1/ai/sessions')
export const getAiSession = (id) => get(`/api/v1/ai/sessions/${id}`)
export const updateAiSession = async (id, data) => {
  const existing = await getAiSession(id)
  const result = await apiRequest({ url: `/api/v1/ai/sessions/${id}`, method: 'patch', data })
  const pythonId = existing?.data?.python_session_id
  const userId = useUserStore().userInfo?.user_id
  if (pythonId && userId && data?.title) {
    await apiRequest({ url: `/api/v1/python/outlines/chat/sessions/${encodeURIComponent(pythonId)}?user_id=${encodeURIComponent(userId)}`, method: 'patch', data: { title: data.title } }).catch(() => {})
  }
  return result
}
export const deleteAiSession = async (id) => {
  const existing = await getAiSession(id)
  const session = existing?.data || {}
  let refs = session.uploaded_refs || session.uploadedRefs || []
  if (typeof refs === 'string') {
    try { refs = JSON.parse(refs) } catch { refs = [] }
  }
  // 仅清理当前会话引用且尚未转存的临时资料，不能误删其他会话正在使用的资源。
  const registered = new Set(readTempRegistry())
  const tempIds = Array.isArray(refs) ? refs.map(String).filter((value) => /^res_[a-f0-9]+$/i.test(value) && registered.has(value)) : []
  if (tempIds.length) {
    const cleaned = await cleanupTempResources(tempIds).then(() => true).catch(() => false)
    if (cleaned) writeTempRegistry(readTempRegistry().filter((value) => !tempIds.includes(value)))
  }
  const pythonId = existing?.data?.python_session_id
  const userId = useUserStore().userInfo?.user_id
  if (pythonId && userId) {
    await apiRequest({ url: `/api/v1/python/outlines/chat/sessions/${encodeURIComponent(pythonId)}?user_id=${encodeURIComponent(userId)}`, method: 'delete' }).catch(() => {})
  }
  return del(`/api/v1/ai/sessions/${id}`)
}
export const getAiPlan = (id) => get(`/api/v1/ai/sessions/${id}/plan`)
export const confirmAiPlan = (id, data) => post(`/api/v1/ai/sessions/${id}/plan-confirmations`, data)
export const createAiRun = (id) => post(`/api/v1/ai/sessions/${id}/runs`)
export const getAiRun = (runId) => get(`/api/v1/ai/runs/${runId}`)
/**
 * 工作台教学意图识别由 FastAPI 处理；Java 仍保存正式会话与项目状态。
 */
const parseIntentField = (value, fallback) => {
  if (typeof value !== 'string') return value ?? fallback
  try { return JSON.parse(value) } catch { return fallback }
}
export const recognizeIntent = (data, options = {}) => apiRequest({
  url: '/api/v1/python/intent/recognize',
  method: 'post',
  data: {
    ...data,
    history: parseIntentField(data.history, []),
    known_context: parseIntentField(data.known_context, {}),
    resource_ids: parseIntentField(data.resource_ids, []),
  },
  timeout: options.timeout || 45000,
  signal: options.signal,
})
/**
 * 读取执行任务事件流。使用 fetch 而非 EventSource，便于携带登录令牌和断线续传游标。
 */
export function streamAiRunEvents(runId, lastEventId, options = {}) {
  const userStore = useUserStore()
  const params = new URLSearchParams()
  if (lastEventId) params.set('lastEventId', String(lastEventId))
  const query = params.size ? `?${params.toString()}` : ''
  return fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/ai/runs/${runId}/events${query}`, {
    headers: {
      Accept: 'text/event-stream',
      ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}),
    },
    signal: options.signal,
  })
}
export const reviseProjectWithAi = (id, data) => post(`/api/v1/projects/${id}/ai-revisions`, data)

/**
 * 直接调用 FastAPI SSE 大纲/资源生成对话流（POST 端点）
 * 注意：浏览器原生 EventSource 仅支持 GET，API-137A 需要 POST JSON body
 * 因此返回原生 fetch Response，由调用方通过 ReadableStream 读取 SSE 事件
 * @param {Object} body - 请求体 { user_id, session_id, message, history?, ... }
 * @returns {Promise<Response>}
 */
export function streamOutlineChat(body) {
  const userStore = useUserStore()
  return fetch(
    `${import.meta.env.VITE_PYTHON_API_BASE_URL || ''}/api/v1/python/outlines/chat/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${userStore.token}`,
      },
      body: JSON.stringify(body),
    }
  )
}

/** 正式工作台聊天/分类流，浏览器直连 FastAPI；浏览器不持有模型密钥。 */
export function streamGeneralChat(body, options = {}) {
  const userStore = useUserStore()
  return fetch(`${import.meta.env.VITE_PYTHON_API_BASE_URL || ''}/api/v1/python/workspace/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: options.signal,
  })
}

/** LangGraph 分流直接请求 FastAPI；Java 不参与推理。 */
export const routeTeachingChat = (data) => post('/api/v1/python/workspace/chat/route', data)
/** Java 仅记录消息和会话状态，不转发 Python。 */
export const beginGeneralChatTurn = (data) => post('/api/v1/ai/general-chat/turns', data)
export const completeGeneralChatTurn = (id, data) => post(`/api/v1/ai/general-chat/turns/${id}/result`, data)

// 教师端项目管理
export const createProject = (data) => post('/api/v1/projects', data)
export const listProjects = (params) => get('/api/v1/projects', params)
export const getProject = (id) => get(`/api/v1/projects/${id}`)
export const listProjectPages = (id) => get(`/api/v1/projects/${id}/pages`)
export const getProjectPage = (id, pageId) => get(`/api/v1/projects/${id}/pages/${pageId}`)
export const createProjectPage = (id, data) => post(`/api/v1/projects/${id}/pages`, data)
export const saveProjectPage = (id, pageId, data) => put(`/api/v1/projects/${id}/pages/${pageId}`, data)
export const batchSaveProjectPages = (id, data) => post(`/api/v1/projects/${id}/pages/batch-save`, data)
export const deleteProjectPage = (id, pageId) => del(`/api/v1/projects/${id}/pages/${pageId}`)
export const validateProjectComponent = (data) => post('/api/v1/projects/tools/validate-component', data)
export const copyProject = (id, data = {}) => post(`/api/v1/projects/${id}/copies`, data)
export const archiveProject = (id) => post(`/api/v1/projects/${id}/archive`)
export const restoreProject = (id) => post(`/api/v1/projects/${id}/restore`)
export const deleteProject = (id) => del(`/api/v1/projects/${id}`)
export const saveProjectVersion = (id, data) => post(`/api/v1/projects/${id}/versions`, data)
export const listProjectVersions = (id, params) => get(`/api/v1/projects/${id}/versions`, params)
export const restoreProjectVersion = (id, versionId) => post(`/api/v1/projects/${id}/versions/${versionId}/restore`)
export const addProjectComponent = (id, data) => post(`/api/v1/projects/${id}/components`, data)
/**
 * @deprecated 旧服务将 componentId 当作 pageId 处理。新代码请使用
 * createProjectPage / saveProjectPage，页面中的组件随 page_content 一并保存。
 */
export const updateProjectComponent = (id, componentId, data) => apiRequest({ url: `/api/v1/projects/${id}/components/${componentId}`, method: 'patch', data })
export const getProjectVersionDiff = (id, versionId, compareVersionId) => get(`/api/v1/projects/${id}/versions/${versionId}/diff`, compareVersionId ? { compare_version_id: compareVersionId } : undefined)
// 项目授权接口放宽超时：后端虽为轻量 DB 操作，但网络抖动或 DB 压力下仍可能超时，避免被默认 10 秒超时误判失败。
const PROJECT_PERMISSION_TIMEOUT = 210000
export const addProjectPermission = (id, data) => apiRequest({
  url: `/api/v1/projects/${id}/permissions`,
  method: 'post',
  data,
  timeout: PROJECT_PERMISSION_TIMEOUT,
})
export const findUserByUsername = (username) => get('/api/v1/users/by-username', { username })
export const findUserByEmail = (email) => get('/api/v1/users/by-email', { email })

/**
 * 获取当前教师个人偏好设置
 * @returns {Promise} 后端返回 { teaching_style, template_style, interaction_forms }
 */
export const getTeacherPreferences = () => get('/api/v1/teachers/me/preferences')

/**
 * 调用 Python 语音转写 ASR，返回识别文本。
 * @param {FormData} formData - 表单数据，含语音文件（file）与可选语言（language）
 * @returns {Promise} 后端返回 { text, language, model, ... }
 */
export const transcribeAudio = (formData) => apiRequest({ url: '/api/v1/python/audio/asr', method: 'post', data: formData })

/**
 * 生成可独立运行或嵌入课件页面的互动模块。
 * 服务端最多尝试模型生成 35 秒，超时后会返回可运行的降级模板；客户端
 * 保留少量网络余量，避免“生成中”无限等待。
 * @param {Object} data - API-144 InteractiveModuleGenerateRequest
 * @returns {Promise} 后端返回 { module_id, html, usage_suggestions, metadata, ... }
 */
const INTERACTIVE_MODULE_GENERATION_TIMEOUT = 50000

export const generateInteractiveModule = (data) => apiRequest({
  url: '/api/v1/python/interactive-modules/generate',
  method: 'post',
  data,
  timeout: INTERACTIVE_MODULE_GENERATION_TIMEOUT,
})

/**
 * 获取 Python PPT 生成模板列表。
 * `theme` 是后续调用 PPT 生成接口时应传入的模板值。
 */
export const listPptTemplates = () => get('/api/v1/python/templates')
export const createPptTemplate = (data) => post('/api/v1/python/templates', data)
export const replacePptTemplate = (theme, data) => apiRequest({ url: `/api/v1/python/templates/${encodeURIComponent(theme)}`, method: 'patch', data })
export const setPptTemplateStatus = (theme, status) => apiRequest({ url: `/api/v1/python/templates/${encodeURIComponent(theme)}/status`, method: 'put', params: { status } })
export const deletePptTemplate = (theme) => del(`/api/v1/python/templates/${encodeURIComponent(theme)}`)
export const downloadPptTemplate = (theme) => apiRequest({ url: `/api/v1/python/templates/${encodeURIComponent(theme)}/file`, responseType: 'blob' })

// Python 端单次模型请求为 120 秒，兼容客户端可能自动重试 2 次；前端留出完整响应时间。
const PYTHON_PPT_REQUEST_TIMEOUT = 420000

export const generatePresentation = (data) => apiRequest({
  url: '/api/v1/python/presentations/generate',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT
})

/** 直连 FastAPI 流式生成 HTML PPT；每完成一页即调用 onSlide，最终返回完整 presentation。 */
export async function generatePresentationStream(data, options = {}) {
  const userStore = useUserStore()
  const response = await fetch(`${import.meta.env.VITE_PYTHON_API_BASE_URL || ''}/api/v1/python/presentations/generate/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}),
    },
    body: JSON.stringify(data),
    signal: options.signal,
  })
  if (!response.ok) throw new Error(`HTML PPT 生成失败 (${response.status})`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let final = null
  const consume = (block) => {
    let event = 'message'
    const dataLines = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (!dataLines.length) return
    const payload = JSON.parse(dataLines.join('\n'))
    if (event === 'presentation_slide') options.onSlide?.(payload)
    else if (event === 'final') final = payload
    else if (event === 'error') throw new Error(payload.message || 'HTML PPT 流式生成失败')
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    blocks.filter(Boolean).forEach(consume)
    if (done) break
  }
  if (buffer.trim()) consume(buffer)
  if (!final) throw new Error('HTML PPT 生成流结束，但未收到最终结果')
  return final
}

/** 记录教师对 AI 生成结果的接受、拒绝、撤销和手工修改，供个性化学习使用。 */
export const recordAiFeedback = (data) => post('/api/v1/python/teacher-style/feedback', data)

/** 获取 AI 运行质量、耗时、Token 与反馈指标。 */
export const getAiMetrics = (params) => get('/api/v1/python/ai/metrics', params)

/** 生成可在线编辑的结构化教案（API-142）。 */
export const generateLessonPlan = (data) => apiRequest({
  url: '/api/v1/python/lesson-plans/generate',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT,
})

/** 直接导出当前 HTML PPT 为 PPTX/ZIP（API-141）。 */
export const exportPresentationPptx = (data) => apiRequest({
  url: '/api/v1/python/presentations/export/pptx',
  method: 'post',
  data,
  responseType: 'blob',
  timeout: PYTHON_PPT_REQUEST_TIMEOUT,
})

/** 导出当前教案为 DOCX（API-143）。 */
export const exportLessonPlanDocx = (data) => apiRequest({
  url: '/api/v1/python/lesson-plans/export/docx',
  method: 'post',
  data,
  responseType: 'blob',
  timeout: PYTHON_PPT_REQUEST_TIMEOUT,
})

/**
 * 根据自然语言修改当前 HTML PPT 页面。
 * @param {Object} data - API-139 SlideModifyRequest
 * @returns {Promise} 后端返回 { presentation_id, slide_no, html, change_summary, ... }
 */
export const modifyPresentationSlide = (data) => apiRequest({
  url: '/api/v1/python/presentations/slides/modify',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT
})

/**
 * 根据自然语言修改整套 HTML PPT。
 * @param {Object} data - API-139A PresentationModifyRequest
 * @returns {Promise} 后端返回修改后的 slides
 */
export const modifyPresentation = (data) => apiRequest({
  url: '/api/v1/python/presentations/modify',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT
})

export const generateSlideImage = (data) => apiRequest({
  url: '/api/v1/python/presentations/images/generate',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT,
})

/** 校验模型返回的单页 HTML 是否可安全加载到工作台 iframe。 */
export const validatePresentationHtml = (data) => apiRequest({
  url: '/api/v1/python/presentations/html/validate',
  method: 'post',
  data,
  timeout: 60000,
})

/**
 * 保存教师个人偏好设置
 * @param {{ teaching_style: string, template_style: string, interaction_forms: string[] }} data - 偏好数据
 * @returns {Promise} 后端返回更新后的偏好配置
 */
export const saveTeacherPreferences = (data) => put('/api/v1/teachers/me/preferences', data)

/** 长期教学画像由 Python AI 服务维护，账号偏好仍由 Java 保存。 */
export const getTeacherStyleProfile = (userId) => get('/api/v1/python/teacher-style/profile', { user_id: userId })
export const updateTeacherStyleProfile = (enabled) => put('/api/v1/python/teacher-style/profile', { enabled })
export const updateTeacherStyleTags = (tags) => put('/api/v1/python/teacher-style/profile/tags', { tags })
export const relearnTeacherStyleProfile = () => post('/api/v1/python/teacher-style/profile/relearn', {})
export const learnTeacherMaterialStyle = (file) => {
  const data = new FormData()
  data.append('file', file)
  return apiRequest({ url: '/api/v1/python/teacher-style/profile/learn-file', method: 'post', data, timeout: 120000 })
}
