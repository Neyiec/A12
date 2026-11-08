/** 浏览器端 INFO 阶段耗时，不输出请求正文、HTML、令牌及资源地址。 */
export function createGenerationTiming({ now = () => performance.now(), log = (...args) => console.info(...args) } = {}) {
  const started = now()
  const runId = `ppt-ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
  const stages = new Map()
  let finished = false
  const write = (stage, status, elapsed, fields = {}) => log('[PPT耗时][INFO]', {
    run_id: runId, stage, status, elapsed_ms: Math.round(elapsed), elapsed_s: Number((elapsed / 1000).toFixed(3)),
    ...(Number.isFinite(fields.count) ? { count: fields.count } : {}),
    ...(/^run_[a-z0-9]+$/i.test(fields.backend_run_id || '') ? { backend_run_id: fields.backend_run_id } : {}),
  })
  return {
    stage(id, status = 'running') {
      if (!id) return
      if (status === 'running') {
        if (!stages.has(id)) { stages.set(id, now()); write(id, 'start', 0) }
      } else if (stages.has(id)) {
        write(id, status, now() - stages.get(id)); stages.delete(id)
      }
    },
    mark(id, fields) { write(id, 'milestone', now() - started, fields) },
    async measure(id, operation) {
      const at = now()
      write(id, 'start', 0)
      try { const result = await operation(); write(id, 'success', now() - at); return result }
      catch (error) { write(id, 'failed', now() - at); throw error }
    },
    finish(status = 'success') {
      if (finished) return
      finished = true
      for (const [id, at] of stages) write(id, status === 'success' ? 'completed' : 'failed', now() - at)
      stages.clear()
      write('browser.total', status, now() - started)
    },
  }
}
