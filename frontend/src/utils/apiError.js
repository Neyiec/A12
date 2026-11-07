/** Return the response body for JSON APIs and preserve the original value otherwise. */
export function responsePayload(response) {
  return response?.data === undefined ? response : response.data
}

/** Throw for an API-level failure while allowing non-envelope responses through. */
export function assertApiSuccess(payload, response) {
  if (!payload || typeof payload !== 'object' || payload.code === undefined) return payload

  const code = Number(payload.code)
  if (code === 0 || code === 200) return payload

  const error = new Error(payload.message || payload.msg || '请求失败')
  error.code = payload.code
  error.status = response?.status || payload.status
  error.response = response
  throw error
}

/** Normalize Axios errors into a useful Error while retaining status and response data. */
export function normalizeRequestError(error) {
  const body = error?.response?.data
  const message = typeof body === 'string'
    ? body
    : body?.message || body?.msg || error?.message || '网络请求失败'
  const normalized = error instanceof Error ? error : new Error(message)

  if (!normalized.message || /^Request failed with status code \d+$/.test(normalized.message)) {
    normalized.message = message
  }
  normalized.status = error?.response?.status || error?.status
  normalized.code = body?.code || error?.code
  normalized.response = error?.response
  return normalized
}
