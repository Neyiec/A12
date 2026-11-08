export function resourceIndexStatus(resource) {
  const labels = {
    failed: ['解析失败', 'danger'],
    indexing: ['索引中', 'warning'],
    processing: ['解析中', 'warning'],
    pending: ['待解析', 'info'],
    completed: ['已解析', 'success'],
    indexed: ['已解析', 'success'],
  }
  const [label, type] = labels[resource?.ai_index_status] || ['待索引', 'info']
  return { label, type, error: resource?.ai_index_error || '',
    usable: ['completed', 'indexed'].includes(resource?.ai_index_status) && Number(resource?.allow_ai) === 1 }
}

export function indexSyncResult(response) {
  const result = response?.data ?? response
  if (result?.status === 'failed' || result?.parse_status === 'failed') {
    throw new Error(result.error_message || result.error || '资源解析失败，请检查文件后重试')
  }
  return { result, complete: ['indexed', 'completed', 'cached', 'unchanged'].includes(result?.status)
    || result?.parse_status === 'completed' }
}
