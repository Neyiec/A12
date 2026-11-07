import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// 学科渲染依赖 ?inline CSS 与扩展名省略解析，应使用同生产代码一致的 Vite 加载器。
const cacheDir = await mkdtemp(join(tmpdir(), 'a12-subject-interaction-'))
const server = await createServer({ configFile: false, cacheDir, server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true } })
const { bindSubjectInteractions } = await server.ssrLoadModule('/src/utils/subjectInteraction.js')
const { geometryPoints } = await server.ssrLoadModule('/src/utils/subjectTool.js')
test.after(async () => { await server.close(); await rm(cacheDir, { recursive: true, force: true }) })

test('geometry drag converts screen coordinates and persists only at gesture completion', () => {
  const listeners = {}
  let data = JSON.stringify({ construction: 'right_triangle' })
  const owner = { getAttribute: () => data, setAttribute: (_, value) => { data = value } }
  const handles = [0, 1, 2].map(index => ({ dataset: { subjectPoint: String(index) }, setAttribute() {}, nextElementSibling: { setAttribute() {} } }))
  const svg = {
    getScreenCTM: () => ({ inverse: () => ({}) }),
    createSVGPoint: () => ({ matrixTransform() { return { x: this.x / 2, y: this.y / 2 } } }),
    querySelector: selector => selector === 'path' ? { setAttribute() {} } : handles[Number(selector.match(/"(\d)"/)[1])],
  }
  handles[0].closest = selector => selector === 'svg' ? svg : selector.includes('data-subject-point') ? handles[0] : owner
  let changes = 0
  const cleanup = bindSubjectInteractions({
    addEventListener: (name, listener) => { listeners[name] = listener },
    removeEventListener: name => { delete listeners[name] },
  }, (_, nextData) => { changes++; assert.deepEqual(nextData.points[0], { x: 60, y: 40 }) })
  const event = { target: handles[0], button: 0, pointerId: 7, clientX: 120, clientY: 80, preventDefault() {}, stopPropagation() {} }
  listeners.pointerdown(event)
  listeners.pointermove(event)
  assert.equal(changes, 0)
  listeners.pointerup(event)
  assert.equal(changes, 1)
  assert.equal(JSON.parse(data).construction, 'right_triangle')
  assert.deepEqual(geometryPoints(JSON.parse(data))[0], { x: 60, y: 40 })
  cleanup()
  assert.equal(Object.keys(listeners).length, 0)
})
