import test from 'node:test'
import assert from 'node:assert/strict'
import { bindSubjectInteractions } from '../src/utils/subjectInteraction.js'
import { geometryPoints } from '../src/utils/subjectTool.js'

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
