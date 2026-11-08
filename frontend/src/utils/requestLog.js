// Deliberately omit headers, bodies, URL query strings and raw Axios errors.
export function startRequestLog(config) {
  config.__a12StartedAt = Date.now()
  return config
}
export function finishRequestLog(config, status, failure = false) {
  const path = String(config?.url || '').split(/[?#]/)[0]
  const elapsedMs = Math.max(0, Date.now() - (config?.__a12StartedAt || Date.now()))
  const entry = { method: String(config?.method || 'get').toUpperCase(), path, status, elapsed_ms: elapsedMs }
  if (failure) console.error('[ERROR] API request '+JSON.stringify(entry))
  else console.info('[INFO] API request '+JSON.stringify(entry))
}
