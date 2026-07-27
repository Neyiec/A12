import { apiRequest, del, get, post, put } from '../utils/api'

export const getCurrentUser = () => get('/api/v1/users/me')

export const createAiSession = (data) => post('/api/v1/ai/sessions', data)
export const sendAiMessage = (id, data) => post(`/api/v1/ai/sessions/${id}/messages`, data)
export const createAiRun = (id) => post(`/api/v1/ai/sessions/${id}/runs`)

export const createProject = (data) => post('/api/v1/projects', data)
export const listProjects = (params) => get('/api/v1/projects', params)
export const getProject = (id) => get(`/api/v1/projects/${id}`)
export const reviseProject = (id, data) => post(`/api/v1/projects/${id}/ai-revisions`, data)
export const saveProjectVersion = (id, data) => post(`/api/v1/projects/${id}/versions`, data)

export const listResources = (params) => get('/api/v1/resources', params)
export const createResourceUpload = (data) => post('/api/v1/resources/uploads', data)
export const completeResourceUpload = (id) => post(`/api/v1/resources/uploads/${id}/complete`)
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
export const precheckExport = (projectId, data) => post(`/api/v1/projects/${projectId}/export-prechecks`, data)

export const patchProject = (id, data) => apiRequest({ url: `/api/v1/projects/${id}`, method: 'patch', data })
