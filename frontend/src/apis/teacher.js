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
    file_type: file.type || undefined,
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
export const retryExportTask = (id) => post(`/api/v1/export-tasks/${id}/retry`)
export const downloadExportArtifact = (id) => post(`/api/v1/export-artifacts/${id}/download-url`)
export const createExportTask = (data) => post('/api/v1/export-tasks', data)
export const precheckProjectExport = (id, data) => post(`/api/v1/projects/${id}/export-prechecks`, data)
export const cancelExportTask = (id) => post(`/api/v1/export-tasks/${id}/cancel`)
export const getExportQualityReport = (id) => get(`/api/v1/export-tasks/${id}/quality-report`)
export const getExportArtifact = (id) => get(`/api/v1/export-artifacts/${id}`)
export const createExportPreviewUrl = (id) => post(`/api/v1/export-artifacts/${id}/preview-url`)

export const patchProject = (id, data) => apiRequest({ url: `/api/v1/projects/${id}`, method: 'patch', data })
export const createAiSession = (data) => post('/api/v1/ai/sessions', data)
export const sendAiSessionMessage = (id, data) => post(`/api/v1/ai/sessions/${id}/messages`, data)
export const getAiPlan = (id) => get(`/api/v1/ai/sessions/${id}/plan`)
export const confirmAiPlan = (id, data) => post(`/api/v1/ai/sessions/${id}/plan-confirmations`, data)
export const createAiRun = (id) => post(`/api/v1/ai/sessions/${id}/runs`)
export const getAiRun = (runId) => get(`/api/v1/ai/runs/${runId}`)
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

// 教师端项目管理
export const createProject = (data) => post('/api/v1/projects', data)
export const listProjects = (params) => get('/api/v1/projects', params)
export const getProject = (id) => get(`/api/v1/projects/${id}`)
export const copyProject = (id, data = {}) => post(`/api/v1/projects/${id}/copies`, data)
export const archiveProject = (id) => post(`/api/v1/projects/${id}/archive`)
export const restoreProject = (id) => post(`/api/v1/projects/${id}/restore`)
export const deleteProject = (id) => del(`/api/v1/projects/${id}`)
export const saveProjectVersion = (id, data) => post(`/api/v1/projects/${id}/versions`, data)
export const listProjectVersions = (id, params) => get(`/api/v1/projects/${id}/versions`, params)
export const restoreProjectVersion = (id, versionId) => post(`/api/v1/projects/${id}/versions/${versionId}/restore`)
export const addProjectComponent = (id, data) => post(`/api/v1/projects/${id}/components`, data)
export const updateProjectComponent = (id, componentId, data) => apiRequest({ url: `/api/v1/projects/${id}/components/${componentId}`, method: 'patch', data })
export const getProjectVersionDiff = (id, versionId, compareVersionId) => get(`/api/v1/projects/${id}/versions/${versionId}/diff`, compareVersionId ? { compare_version_id: compareVersionId } : undefined)
export const addProjectPermission = (id, data) => post(`/api/v1/projects/${id}/permissions`, data)
