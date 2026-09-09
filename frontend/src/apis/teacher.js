import axios from 'axios'
import { apiRequest, del, get, post, put } from '../utils/api'
import { useUserStore } from '../storage/user.js'

export const listResources = (params) => get('/api/v1/resources', params)
export const uploadResource = async (file, onProgress) => {
  const uploadTokenResult = await post('/api/v1/resources/upload-tokens', {
    file_name: file.name,
    file_type: file.type || undefined,
  })
  if (uploadTokenResult?.code && uploadTokenResult.code !== 200 && uploadTokenResult.code !== 0) {
    throw new Error(uploadTokenResult.message || '获取上传凭证失败')
  }

  const uploadToken = uploadTokenResult?.data || uploadTokenResult
  if (!uploadToken?.upload_url || !uploadToken?.object_key) {
    throw new Error('上传凭证无效，请稍后重试')
  }

  await axios.put(uploadToken.upload_url, file, {
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    onUploadProgress: (event) => {
      if (event.total && onProgress) onProgress(Math.round((event.loaded / event.total) * 100))
    },
  })

  const confirmResult = await post('/api/v1/resources/uploaded-files', {
    object_key: uploadToken.object_key,
    file_name: file.name,
    file_size: file.size,
    // API-37 accepts the type as an optional business category.  The MIME
    // value is only needed when signing the OSS PUT request above; sending it
    // here would persist values such as `image/png` instead of the documented
    // `image`/`ppt`/`word` categories.  Leaving it out lets Java detect the
    // category from the filename.
  })
  if (confirmResult?.code && confirmResult.code !== 200 && confirmResult.code !== 0) {
    throw new Error(confirmResult.message || '素材入库失败')
  }
  return confirmResult?.data || confirmResult
}
export const deleteResource = (id) => del(`/api/v1/resources/${id}`)
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
export const bootstrapResourceIndex = (data) => post('/api/v1/python/resources/index/bootstrap', data)
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
export const retryExportTask = (id) => apiRequest({ url: `/api/v1/export-tasks/${id}/retry`, method: 'post', timeout: EXPORT_TASK_TIMEOUT })
export const downloadExportArtifact = (id) => post(`/api/v1/export-artifacts/${id}/download-url`)
export const createExportTask = (data) => apiRequest({ url: '/api/v1/export-tasks', method: 'post', data, timeout: EXPORT_TASK_TIMEOUT })
export const precheckProjectExport = (id, data) => post(`/api/v1/projects/${id}/export-prechecks`, data)
export const cancelExportTask = (id) => post(`/api/v1/export-tasks/${id}/cancel`)
export const getExportQualityReport = (id) => get(`/api/v1/export-tasks/${id}/quality-report`)
export const getExportArtifact = (id) => get(`/api/v1/export-artifacts/${id}`)
export const createExportPreviewUrl = (id) => post(`/api/v1/export-artifacts/${id}/preview-url`)

export const patchProject = (id, data) => apiRequest({ url: `/api/v1/projects/${id}`, method: 'patch', data })
export const createAiSession = (data) => post('/api/v1/ai/sessions', data)
export const listAiSessions = () => get('/api/v1/ai/sessions')
export const getAiSession = (id) => get(`/api/v1/ai/sessions/${id}`)
export const updateAiSession = (id, data) => apiRequest({ url: `/api/v1/ai/sessions/${id}`, method: 'patch', data })
export const deleteAiSession = (id) => del(`/api/v1/ai/sessions/${id}`)
// 大纲生成同步阻塞、耗时较长（后端 request-timeout-seconds 已放宽到 600s），
// 单独使用长超时，避免被默认 10s 超时取消导致"已取消"或后端完成前被掐断。
export const sendAiSessionMessage = (id, data) =>
  apiRequest({ url: `/api/v1/ai/sessions/${id}/messages`, method: 'post', data, timeout: 620000 })

/**
 * 发送语音消息到正式 AI 会话接口。
 * 语音先由网关完成转写，再沿用同一条会话上下文执行意图分流。
 */
export const sendAiSessionAudioMessage = (id, formData, options = {}) =>
  apiRequest({
    url: `/api/v1/ai/sessions/${id}/audio-messages`,
    method: 'post',
    data: formData,
    timeout: options.timeout || 620000,
    signal: options.signal,
  })

/**
 * 流式发送 AI 会话消息（SSE）
 * 走 Java 网关 /api/v1/ai/sessions/{id}/messages/stream，
 * 边生成边回传 session/outline_delta/question/final/error/done 事件。
 * 浏览器原生 EventSource 仅支持 GET，因此用原生 fetch 返回 Response，由调用方读取 ReadableStream 解析 SSE。
 * @returns {Promise<Response>}
 */
export function streamSendAiSessionMessage(id, data) {
  const userStore = useUserStore()
  return fetch(
    `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/ai/sessions/${id}/messages/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${userStore.token}`,
      },
      body: JSON.stringify(data),
    }
  )
}
export const getAiPlan = (id) => get(`/api/v1/ai/sessions/${id}/plan`)
export const confirmAiPlan = (id, data) => post(`/api/v1/ai/sessions/${id}/plan-confirmations`, data)
export const createAiRun = (id) => post(`/api/v1/ai/sessions/${id}/runs`)
export const getAiRun = (runId) => get(`/api/v1/ai/runs/${runId}`)
/**
 * 正式业务意图识别接口（API-13B）。
 * 工作台的“讨论 / 页面修改 / 生成 / 导出 / 打开项目”分流必须先经过 Java
 * 业务网关，不依赖前端开发服务器注入的模型中间件。
 */
export const recognizeIntent = (data, options = {}) => apiRequest({
  url: '/api/v1/ai/intent/recognize',
  method: 'post',
  data,
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
 * 调用 Python SSE 大纲/资源生成对话流（POST 端点）
 * 注意：浏览器原生 EventSource 仅支持 GET，API-137A 需要 POST JSON body
 * 因此返回原生 fetch Response，由调用方通过 ReadableStream 读取 SSE 事件
 * @param {Object} body - 请求体 { user_id, session_id, message, history?, ... }
 * @returns {Promise<Response>}
 */
export function streamOutlineChat(body) {
  const userStore = useUserStore()
  return fetch(
    `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/python/outlines/chat/stream`,
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

/** 正式工作台聊天/分类流，经 Java 网关转发 Python 服务；浏览器不持有模型密钥。 */
export function streamGeneralChat(body, options = {}) {
  const userStore = useUserStore()
  return fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/python/workspace/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: options.signal,
  })
}

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
export const addProjectPermission = (id, data) => post(`/api/v1/projects/${id}/permissions`, data)
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

// Python 端单次模型请求为 120 秒，兼容客户端可能自动重试 2 次；前端留出完整响应时间。
const PYTHON_PPT_REQUEST_TIMEOUT = 420000

export const generatePresentation = (data) => apiRequest({
  url: '/api/v1/python/presentations/generate',
  method: 'post',
  data,
  timeout: PYTHON_PPT_REQUEST_TIMEOUT
})

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
