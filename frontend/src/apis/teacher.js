import axios from 'axios'
import { apiRequest, del, get, post, put } from '../utils/api'

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

export const listCommunityItems = (params) => get('/api/v1/community/items', params)
export const favoriteCommunityItem = (id) => put(`/api/v1/community/items/${id}/favorite`)
export const unfavoriteCommunityItem = (id) => del(`/api/v1/community/items/${id}/favorite`)
export const reuseCommunityItem = (id, data) => post(`/api/v1/community/items/${id}/reuse`, data)

export const listExportTasks = (params) => get('/api/v1/export-tasks', params)
export const getExportTask = (id) => get(`/api/v1/export-tasks/${id}`)
export const retryExportTask = (id) => post(`/api/v1/export-tasks/${id}/retry`)
export const downloadExportArtifact = (id) => post(`/api/v1/export-artifacts/${id}/download-url`)
export const createExportTask = (data) => post('/api/v1/export-tasks', data)

export const patchProject = (id, data) => apiRequest({ url: `/api/v1/projects/${id}`, method: 'patch', data })

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
