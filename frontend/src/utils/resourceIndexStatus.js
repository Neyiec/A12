const enabled = value => value === true || value === 1 || value === '1'

/** Normalize Java resource metadata and Python index statuses for the library UI. */
export function resourceIndexStatus(resource = {}) {
  const error = String(resource.ai_index_error || resource.error_message || '')
  const status = String(resource.ai_index_status || resource.parse_status || '').toLowerCase()
  if (resource.status === 0 || resource.status === '0' || resource.available === false) {
    return { label: '已停用', type: 'info', error, usable: false }
  }
  if (!enabled(resource.allow_ai)) {
    return { label: '未开启 AI 引用', type: 'info', error, usable: false }
  }
  switch (status) {
    case 'completed':
    case 'indexed':
      return { label: '已就绪', type: 'success', error: '', usable: true }
    case 'indexing':
    case 'processing':
    case 'parsing':
      return { label: '解析中', type: 'warning', error, usable: false }
    case 'failed':
    case 'error':
      return { label: '解析失败', type: 'danger', error: error || '资源解析或索引失败，请重试或查看索引日志。', usable: false }
    case 'disabled':
      return { label: '索引已停用', type: 'info', error, usable: false }
    default:
      return { label: '待处理', type: 'info', error, usable: false }
  }
}

/** A 200 envelope may still contain a failed index operation; never report it as success. */
export function indexSyncResult(response) {
  if (response?.code != null && ![0, 200].includes(Number(response.code))) {
    throw new Error(response.message || '资源索引同步失败')
  }
  const data = response?.data ?? response ?? {}
  const status = String(data.status || data.parse_status || '').toLowerCase()
  if (status === 'failed' || status === 'error') {
    throw new Error(data.error_message || data.error || data.message || '资源索引同步失败')
  }
  const complete = status === 'indexed' || status === 'completed'
    || (status === 'skipped' && data.reason === 'content_sha256_unchanged')
  return { ...data, complete }
}
