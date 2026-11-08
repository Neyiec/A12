/** One request at a time; stopping also discards late responses after navigation. */
export function pollStatus({ request, onResult, onError, onTimeout, onStop,
  interval = 4000, timeout = 600000, maxErrors = 3,
  schedule = setTimeout, unschedule = clearTimeout, now = Date.now }) {
  let stopped = false
  let timer
  let errors = 0
  const started = now()
  const stop = () => {
    if (stopped) return
    stopped = true
    unschedule(timer)
    onStop?.()
  }
  const tick = async () => {
    if (stopped) return
    if (now() - started >= timeout) {
      stop()
      onTimeout?.()
      return
    }
    try {
      const payload = await request()
      if (stopped) return
      errors = 0
      if (onResult(payload)) {
        stop()
        return
      }
    } catch (error) {
      if (stopped) return
      errors += 1
      const status = error?.response?.status ?? error?.status
      if (status === 401 || status === 403 || errors >= maxErrors) {
        stop()
        onError?.(error)
        return
      }
    }
    if (!stopped) timer = schedule(tick, interval)
  }
  timer = schedule(tick, interval)
  return stop
}
