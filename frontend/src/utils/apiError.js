const databaseDetail = /SQLSyntaxErrorException|SQLIntegrityConstraintViolationException|DataIntegrityViolationException|MysqlDataTruncation|Data too long for column|SQLSTATE|### (?:Error|The error|SQL:)|(?:Unknown column|Table '[^']+' doesn't exist)|java\.sql\.|org\.springframework\./i

/** Convert both FastAPI validation errors and Java Result failures into safe, actionable UI text. */
export function apiErrorMessage(payload, status = 0, fallback = '请求失败，请稍后重试') {
  const detail = typeof payload === 'string' ? payload : payload?.detail ?? payload?.message ?? payload?.msg
  const message = Array.isArray(detail)
    ? detail.map(item => {
      const field = Array.isArray(item?.loc) ? item.loc.filter(part => !['body', 'query'].includes(part)).join('.') : ''
      return field ? `${field}：${item?.msg || '参数无效'}` : item?.msg || '参数无效'
    }).join('；')
    : typeof detail === 'string' ? detail.trim() : ''
  if (databaseDetail.test(message)) return '数据服务异常，请联系管理员检查数据库结构；本次操作未完成'
  if (message && !/^Request failed with status code|^<!doctype|^<html/i.test(message)) return message.slice(0, 500)
  if (status === 401) return '登录已过期，请重新登录后继续'
  if (status === 403) return '没有操作权限，请联系管理员'
  if (status === 404) return '接口或资源不存在，请检查服务版本后重试'
  if (status === 413) return '上传内容超过服务限制，请减小文件或分批上传'
  if (status === 429) return '请求过于频繁，请稍后重试'
  if ([502, 503, 504].includes(status)) return '服务暂时不可用，请确认后端和数据库已启动后重试'
  if (status >= 500) return '服务器处理失败，请稍后重试'
  return fallback
}

export function assertApiSuccess(payload, response) {
  if (payload?.code == null || [0, 200].includes(Number(payload.code))) return payload
  const error = new Error(apiErrorMessage(payload, Number(payload.code)))
  error.code = payload.code
  error.status = response?.status || payload.status
  error.response = response || { status: 200, data: payload }
  throw error
}

export async function responsePayload(response) {
  const data = response?.data === undefined ? response : response.data
  // A failed download can still be HTTP 200 with a Java Result JSON body.
  // Do not save that JSON as a misleading .pptx/.zip success file.
  if (typeof Blob !== 'undefined' && data instanceof Blob && /json/i.test(data.type)) {
    try { return JSON.parse(await data.text()) } catch { return data }
  }
  return data
}

export async function normalizeRequestError(error) {
  if (error?.code === 'ERR_CANCELED' || error?.name === 'AbortError') return error
  const payload = error?.response ? await responsePayload(error.response) : null
  const fallback = error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT'
    ? '请求超时，请稍后重试' : error?.request ? '无法连接服务，请检查网络和后端服务是否启动' : error?.message || '请求失败'
  const status = error?.response?.status || error?.status
  const message = apiErrorMessage(payload, status || 0, fallback)
  const normalized = error instanceof Error ? error : new Error(message)
  normalized.message = message
  normalized.status = status
  normalized.code = payload?.code ?? error?.code
  normalized.response = error?.response
  return normalized
}
