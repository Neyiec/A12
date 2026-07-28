import { apiRequest, del, get, post, put, uploadFile } from '../utils/api'

export const listResources = (params) => get('/api/v1/resources', params)
export const uploadResource = (formData, onProgress) => uploadFile('/api/v1/resources/uploads', formData, onProgress)
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
