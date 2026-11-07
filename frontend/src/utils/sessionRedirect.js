const DEFAULT_TARGET = '/main'

/** Accept only an in-app absolute route; reject external and malformed redirect targets. */
export function safeLoginTarget(target) {
  if (typeof target !== 'string') return DEFAULT_TARGET
  const value = target.trim()
  if (!value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) {
    return DEFAULT_TARGET
  }
  return value
}

/** Build the login route while preserving a safe destination after authentication. */
export function loginLocation(target) {
  const safeTarget = safeLoginTarget(target)
  return safeTarget === DEFAULT_TARGET
    ? { path: '/login' }
    : { path: '/login', query: { redirect: safeTarget } }
}
