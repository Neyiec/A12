import { geometryPoints } from './subjectTool.js'

// Event delegation works in both the native canvas and same-origin HTML slides.
export function bindSubjectInteractions(root, onChange) {
  let gesture = null
  const getOwner = target => target.closest?.('[data-ppt-type="subject"],.a12-subject-tool')
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
    gesture.points[gesture.index] = {
      x: Math.round(Math.max(8, Math.min(172, position.x)) * 10) / 10,
      y: Math.round(Math.max(8, Math.min(92, position.y)) * 10) / 10,
    }
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
    const point = points[Number(handle.dataset.subjectPoint)]
    const step = event.shiftKey ? 5 : 1
    point.x = Math.max(8, Math.min(172, point.x + delta[0] * step))
    point.y = Math.max(8, Math.min(92, point.y + delta[1] * step))
    paint(handle.closest('svg'), points)
    owner.setAttribute('data-subject-data', JSON.stringify({ ...data, points }))
    onChange?.(owner, { ...data, points })
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
