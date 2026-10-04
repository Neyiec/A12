/** A small, self-contained Cartesian board for classroom diagrams. */
const DEFAULT_POINTS = [
  { label: 'A', x: 2, y: 3 },
  { label: 'B', x: -2, y: -1 },
]

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))
const numberOr = (value, fallback) => {
  if (value === '' || value === null || value === undefined) return fallback
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}
const pointName = (index) => String.fromCharCode(65 + index)
const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

export const createCoordinateData = () => ({
  xRange: 5,
  yRange: 4,
  showGrid: true,
  connectPoints: false,
  segments: [],
  points: DEFAULT_POINTS.map((point) => ({ ...point })),
})

export const normalizeCoordinateData = (value = {}) => {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const xRange = clamp(Math.round(numberOr(source.xRange, 5)), 2, 10)
  const yRange = clamp(Math.round(numberOr(source.yRange, 4)), 2, 10)
  const rawPoints = Array.isArray(source.points) ? source.points : DEFAULT_POINTS
  const points = rawPoints.slice(0, 10).map((point, index) => ({
    label: String(point?.label ?? '').trim().slice(0, 8) || pointName(index),
    x: Math.round(clamp(numberOr(point?.x, 0), -xRange, xRange) * 100) / 100,
    y: Math.round(clamp(numberOr(point?.y, 0), -yRange, yRange) * 100) / 100,
  }))
  const seenSegments = new Set()
  const segments = []
  for (const segment of Array.isArray(source.segments) ? source.segments : []) {
    if (!Array.isArray(segment) || segment.length !== 2) continue
    const [start, end] = segment
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < 0 || start >= points.length || end >= points.length || start === end) continue
    const pair = [Math.min(start, end), Math.max(start, end)]
    const key = pair.join('-')
    if (seenSegments.has(key)) continue
    seenSegments.add(key)
    segments.push(pair)
    if (segments.length >= 36) break
  }
  return {
    ...source,
    xRange,
    yRange,
    showGrid: source.showGrid !== false,
    connectPoints: source.connectPoints === true,
    points,
    segments,
  }
}

export const coordinateMarkup = (value = {}) => {
  const data = normalizeCoordinateData(value)
  const { xRange, yRange } = data
  const left = 34
  const top = 20
  const width = 344
  const height = 226
  const originX = left + width / 2
  const originY = top + height / 2
  const px = (x) => originX + x * width / (2 * xRange)
  const py = (y) => originY - y * height / (2 * yRange)
  const tickStepX = xRange > 6 ? 2 : 1
  const tickStepY = yRange > 6 ? 2 : 1
  const xTicks = Array.from({ length: 2 * xRange + 1 }, (_, index) => index - xRange)
  const yTicks = Array.from({ length: 2 * yRange + 1 }, (_, index) => index - yRange)
  const grid = data.showGrid
    ? `<g stroke="#e4ebf5" stroke-width="1">${xTicks.filter((x) => x !== 0).map((x) => `<line x1="${px(x)}" y1="${top}" x2="${px(x)}" y2="${top + height}"/>`).join('')}${yTicks.filter((y) => y !== 0).map((y) => `<line x1="${left}" y1="${py(y)}" x2="${left + width}" y2="${py(y)}"/>`).join('')}</g>`
    : ''
  const ticks = `<g fill="#64748b" font-family="Arial, sans-serif" font-size="9">${xTicks.filter((x) => x !== 0).map((x) => `<line x1="${px(x)}" y1="${originY - 3}" x2="${px(x)}" y2="${originY + 3}" stroke="#475569" stroke-width="1"/>${x % tickStepX === 0 ? `<text x="${px(x)}" y="${originY + 15}" text-anchor="middle">${x}</text>` : ''}`).join('')}${yTicks.filter((y) => y !== 0).map((y) => `<line x1="${originX - 3}" y1="${py(y)}" x2="${originX + 3}" y2="${py(y)}" stroke="#475569" stroke-width="1"/>${y % tickStepY === 0 ? `<text x="${originX - 8}" y="${py(y) + 3}" text-anchor="end">${y}</text>` : ''}`).join('')}<text x="${originX - 8}" y="${originY + 15}" text-anchor="end">0</text></g>`
  const line = data.connectPoints && data.points.length > 1
    ? `<polyline points="${data.points.map((point) => `${px(point.x)},${py(point.y)}`).join(' ')}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>`
    : ''
  const segments = data.segments.map(([start, end]) => {
    const first = data.points[start]
    const second = data.points[end]
    return `<line x1="${px(first.x)}" y1="${py(first.y)}" x2="${px(second.x)}" y2="${py(second.y)}"/>`
  }).join('')
  const segmentLines = segments ? `<g fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round">${segments}</g>` : ''
  const points = data.points.map((point) => {
    const x = px(point.x)
    const y = py(point.y)
    const labelY = y < top + 18 ? y + 17 : y - 9
    const labelX = x > left + width - 17 ? x - 11 : x + 9
    return `<g><circle cx="${x}" cy="${y}" r="4.5" fill="#fff" stroke="#2563eb" stroke-width="2.5"/><text x="${labelX}" y="${labelY}" fill="#1d4ed8" font-family="Arial, sans-serif" font-size="12" font-weight="700">${escapeHtml(point.label)}</text></g>`
  }).join('')
  return `<svg viewBox="0 0 400 276" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="平面直角坐标系，${data.points.length} 个点"><rect x="${left}" y="${top}" width="${width}" height="${height}" fill="#fff" stroke="#e2e8f0"/>${grid}<g stroke="#334155" stroke-width="1.6" fill="#334155"><line x1="${left}" y1="${originY}" x2="${left + width + 6}" y2="${originY}"/><path d="M${left + width + 6} ${originY} l-6 -3 v6 z"/><line x1="${originX}" y1="${top + height}" x2="${originX}" y2="${top - 6}"/><path d="M${originX} ${top - 6} l-3 6 h6 z"/></g>${ticks}<g fill="#334155" font-family="Arial, sans-serif" font-size="12" font-weight="700"><text x="${left + width + 11}" y="${originY - 6}">x</text><text x="${originX + 8}" y="${top - 6}">y</text></g>${line}${segmentLines}${points}</svg>`
}

export const coordinateRuntimeCss = '.a12-subject-tool__coordinate{display:grid;place-items:center;min-width:0;min-height:0;overflow:hidden}.a12-subject-tool__coordinate svg{display:block;width:100%;height:100%;min-height:60px;max-height:100%}'
