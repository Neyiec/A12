import { apiRequest } from '../utils/api'
const base = '/api/v1/python/batch-presentations'
const call = (path, method = 'get', data, timeout = 120000) => apiRequest({ url: base + path, method, data, timeout })
export const createBatchPlan = data => call('/plans', 'post', data)
export const listBatchPlans = session => apiRequest({ url: base + '/plans', params: session ? { session_id: String(session) } : {}, timeout: 15000 })
export const readBatchPlan = id => call('/plans/' + id)
export const editBatchPlan = (id, data) => call('/plans/' + id, 'patch', data)
export const reviseBatchPlan = (id, data) => call('/plans/' + id + '/revise', 'post', data)
export const splitBatchPlan = (id, data) => call('/plans/' + id + '/split', 'post', data)
export const confirmBatchPlan = (id, data) => call('/plans/' + id + '/confirm', 'post', data)
export const listPresentationBatches = () => call('/batches', 'get', undefined, 15000)
export const readPresentationBatch = id => call('/batches/' + id, 'get', undefined, 15000)
export const retryBatchItem = (batch, item) => call(`/batches/${batch}/items/${item}/retry`, 'post')
export const saveBatchItem = (batch, item) => call(`/batches/${batch}/items/${item}/save`, 'post')
export const syncReadyBatches = () => call('/sync-ready', 'post')
export const cancelPresentationBatch = id => call('/batches/' + id + '/cancel', 'post')
export const requestBatchZip = (id, partial) => call('/batches/' + id + '/zip', 'post', { include_partial: partial })
export const downloadBatchZip = id => apiRequest({ url: base + `/batches/${id}/zip`, responseType: 'blob', timeout: 120000 })
export const downloadBatchSource = id => apiRequest({ url: base + `/plans/${id}/source`, responseType: 'blob', timeout: 60000 })
export function saveBatchDownload(response, name) {
  const value = response?.data instanceof Blob ? response.data : response
  if (!(value instanceof Blob)) throw Error('下载未返回有效文件')
  const url = URL.createObjectURL(value), anchor = document.createElement('a')
  anchor.href = url; anchor.download = name; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
