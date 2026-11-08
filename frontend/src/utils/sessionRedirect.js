/** Only return to local teacher workspace routes; never honor an external redirect. */
export function safeLoginTarget(value) {
  if (typeof value !== 'string') return '/main'
  value = value.trim()
  if (!value.startsWith('/main') || /[\\\u0000-\u001f]/.test(value)) return '/main'
  try {
    const url = new URL(value, 'http://a12.local')
    if (url.origin !== 'http://a12.local' || (url.pathname !== '/main' && !url.pathname.startsWith('/main/'))) return '/main'
    return url.pathname + url.search + url.hash
  } catch { return '/main' }
}
export function loginLocation(fullPath) {
  const target = safeLoginTarget(fullPath)
  return target === '/main' ? { path: '/login' } : { path: '/login', query: { redirect: target } }
}
