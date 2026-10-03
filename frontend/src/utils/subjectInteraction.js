import { geometryPoints } from './subjectTool.js'

const constrainPoints = (draft, construction, movedIndex, previous) => {
  if (!Array.isArray(draft) || movedIndex < 0) return draft
  const next = draft.map(point => ({ ...point }))
  if (construction === 'right_triangle' && next.length === 3) {
    if (movedIndex === 0) next[1].y = next[0].y
    if (movedIndex === 1) { next[0].y = next[1].y; next[2].x = next[1].x }
    if (movedIndex === 2) next[1].x = next[2].x
    return next
  }
  if (!['rectangle', 'square'].includes(construction) || next.length !== 4) return next
  const opposite = next[(movedIndex + 2) % 4]
  const moved = next[movedIndex]
  if (construction === 'square') {
    const xDirection = Math.sign(moved.x - opposite.x) || Math.sign(previous.x - opposite.x) || 1
    const yDirection = Math.sign(moved.y - opposite.y) || Math.sign(previous.y - opposite.y) || 1
    const side = Math.max(1, Math.min(Math.abs(moved.x - opposite.x), Math.abs(moved.y - opposite.y)))
    moved.x = opposite.x + xDirection * side
    moved.y = opposite.y + yDirection * side
  }
  if (movedIndex === 0) { next[1] = { x: opposite.x, y: moved.y }; next[3] = { x: moved.x, y: opposite.y } }
  if (movedIndex === 1) { next[0] = { x: opposite.x, y: moved.y }; next[2] = { x: moved.x, y: opposite.y } }
  if (movedIndex === 2) { next[1] = { x: moved.x, y: opposite.y }; next[3] = { x: opposite.x, y: moved.y } }
  if (movedIndex === 3) { next[0] = { x: moved.x, y: opposite.y }; next[2] = { x: opposite.x, y: moved.y } }
  return next
}

// Event delegation works in both the native canvas and same-origin HTML slides.
export function bindSubjectInteractions(root, onChange) {
  let gesture = null
  const getOwner = target => target.closest?.('[data-ppt-type="subject"],.a12-subject-tool,[data-subject-interaction-owner]')
  const readData = owner => {
    try { return JSON.parse(owner.getAttribute('data-subject-data') || '{}') } catch { return {} }
  }
  const paint = (svg, points) => {
    svg.querySelector('path').setAttribute('d', points.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.y}`).join(' ') + ' Z')
    points.forEach((point, index) => {
      const handle = svg.querySelector(`[data-subject-point="${index}"]`)
      handle.setAttribute('cx', point.x)
      handle.setAttribute('cy', point.y)
      handle.setAttribute('aria-valuenow', point.x)
      handle.setAttribute('aria-valuetext', `${point.x}, ${point.y}`)
      const label = handle.nextElementSibling
      label?.setAttribute('x', point.x)
      label?.setAttribute('y', point.y - 8)
    })
  }
  const down = event => {
    const handle = event.target.closest?.('[data-subject-point]')
    if (!handle || event.button !== 0) return
    const owner = getOwner(handle)
    const svg = handle.closest('svg')
    if (!owner || !svg) return
    const data = readData(owner)
    gesture = { owner, svg, handle, data, points: geometryPoints(data), index: Number(handle.dataset.subjectPoint), pointerId: event.pointerId }
    handle.setPointerCapture?.(event.pointerId)
    event.preventDefault()
    event.stopPropagation()
  }
  const move = event => {
    if (!gesture || gesture.pointerId !== event.pointerId) return
    const matrix = gesture.svg.getScreenCTM()
    if (!matrix) return
    const point = gesture.svg.createSVGPoint()
    point.x = event.clientX
    point.y = event.clientY
    const position = point.matrixTransform(matrix.inverse())
    const previous = gesture.points[gesture.index]
    gesture.points[gesture.index] = {
      x: Math.round(Math.max(8, Math.min(172, position.x)) * 10) / 10,
      y: Math.round(Math.max(8, Math.min(92, position.y)) * 10) / 10,
    }
    gesture.points = constrainPoints(gesture.points, gesture.data.construction, gesture.index, previous)
    paint(gesture.svg, gesture.points)
    event.preventDefault()
    event.stopPropagation()
  }
  const finish = event => {
    if (!gesture || event.pointerId !== gesture.pointerId) return
    const current = gesture
    gesture = null
    if (current.handle.hasPointerCapture?.(current.pointerId)) current.handle.releasePointerCapture(current.pointerId)
    const data = { ...current.data, points: current.points }
    current.owner.setAttribute('data-subject-data', JSON.stringify(data))
    onChange?.(current.owner, data)
    event.stopPropagation()
  }
  const keydown = event => {
    const handle = event.target.closest?.('[data-subject-point]')
    const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key]
    if (!handle || !delta) return
    const owner = getOwner(handle)
    const data = readData(owner)
    const points = geometryPoints(data)
    const index = Number(handle.dataset.subjectPoint)
    const point = points[index]
    const previous = { ...point }
    const step = event.shiftKey ? 5 : 1
    point.x = Math.max(8, Math.min(172, point.x + delta[0] * step))
    point.y = Math.max(8, Math.min(92, point.y + delta[1] * step))
    const constrained = constrainPoints(points, data.construction, index, previous)
    paint(handle.closest('svg'), constrained)
    owner.setAttribute('data-subject-data', JSON.stringify({ ...data, points: constrained }))
    onChange?.(owner, { ...data, points: constrained })
    event.preventDefault()
    event.stopPropagation()
  }
  const listeners = { pointerdown: down, pointermove: move, pointerup: finish, pointercancel: finish, keydown }
  Object.entries(listeners).forEach(([name, listener]) => root.addEventListener(name, listener))
  return () => {
    Object.entries(listeners).forEach(([name, listener]) => root.removeEventListener(name, listener))
    if (gesture?.handle.hasPointerCapture?.(gesture.pointerId)) gesture.handle.releasePointerCapture(gesture.pointerId)
    gesture = null
  }
}
