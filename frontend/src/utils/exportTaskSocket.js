export function subscribeExportTasks({ token, onReady, onChanged, onDisconnect }) {
  if (!token || typeof WebSocket === 'undefined') return () => {}
  let socket
  let retryTimer
  let heartbeat
  let deadline
  let stopped = false
  let delay = 1000
  const clearConnectionTimers = () => {
    clearInterval(heartbeat)
    clearTimeout(deadline)
  }

  function connect() {
    if (stopped) return
    try {
      const base = new URL(import.meta.env.VITE_API_BASE_URL || location.origin, location.origin)
      const url = new URL('/ws/export-events', base)
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(url)
    } catch {
      onDisconnect()
      return
    }
    const current = socket
    deadline = setTimeout(() => current.close(), 8000)
    current.onopen = () => current.send(`auth ${token}`)
    current.onmessage = ({ data }) => {
      let event
      try { event = JSON.parse(data) } catch { return }
      if (event?.type === 'ready' && !heartbeat) {
        clearTimeout(deadline)
        delay = 1000
        heartbeat = setInterval(() => {
          if (current.readyState !== WebSocket.OPEN) return
          current.send('ping')
          deadline = setTimeout(() => current.close(), 8000)
        }, 25000)
        onReady()
      } else if (event?.type === 'pong') {
        clearTimeout(deadline)
      } else if (event?.type === 'export_changed' && Number.isInteger(event.taskId)) {
        onChanged(event.taskId)
      }
    }
    current.onclose = (event) => {
      clearConnectionTimers()
      heartbeat = undefined
      if (stopped) return
      onDisconnect()
      if (event.code === 1008) return
      retryTimer = setTimeout(connect, delay + Math.random() * 500)
      delay = Math.min(delay * 2, 30000)
    }
  }

  connect()
  return () => {
    stopped = true
    clearTimeout(retryTimer)
    clearConnectionTimers()
    if (socket) {
      socket.onmessage = null
      socket.onopen = null
      socket.close()
    }
  }
}
