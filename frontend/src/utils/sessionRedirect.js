/** Only return to local teacher workspace routes; never honor an external redirect. */
export function safeLoginTarget(value) {
  if (typeof value !== 'string' || !value.startsWith('/main')) return '/main'
  try {
    const url = new URL(value, 'http://a12.local')
    if (url.origin !== 'http://a12.local' || (url.pathname !== '/main' && !url.pathname.startsWith('/main/'))) return '/main'
    return url.pathname + url.search + url.hash
  } catch { return '/main' }
}
export function loginLocation(fullPath) {
  const target = safeLoginTarget(fullPath)
  return { path: '/login', query: target === '/main' ? {} : { redirect: target } }
}
