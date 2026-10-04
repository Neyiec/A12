/** Simple SVG solids for classroom diagrams. All markup is self-contained for slide export. */

export const solidShapeOptions = [
  { value: 'cube', label: '正方体' },
  { value: 'cuboid', label: '长方体' },
  { value: 'pyramid', label: '四棱锥' },
  { value: 'cylinder', label: '圆柱' },
  { value: 'cone', label: '圆锥' },
  { value: 'sphere', label: '球体' },
]

const shapeLabels = Object.fromEntries(solidShapeOptions.map(({ value, label }) => [value, label]))
const defaultDimensions = { length: 4, width: 3, height: 5, radius: 2 }
const blue = '#2563eb'
const lightBlue = '#dbeafe'
const paleBlue = '#eff6ff'
const mutedBlue = '#93c5fd'
const dimensionColor = '#475569'

export const createSolidData = () => ({
  solid: 'cube',
  dimensions: { ...defaultDimensions },
  show_hidden_edges: true,
  show_dimensions: true,
})

const dimension = (value, fallback) => {
  const number = Number(value)
  return Number.isFinite(number) ? Math.round(Math.min(20, Math.max(1, number)) * 10) / 10 : fallback
}

export const normalizeSolidData = (value = {}) => {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const dimensions = source.dimensions && typeof source.dimensions === 'object' && !Array.isArray(source.dimensions)
    ? source.dimensions : {}
  return {
    ...source,
    solid: shapeLabels[source.solid] ? source.solid : 'cube',
    dimensions: Object.fromEntries(Object.entries(defaultDimensions).map(([key, fallback]) => [key, dimension(dimensions[key], fallback)])),
    show_hidden_edges: source.show_hidden_edges !== false,
    show_dimensions: source.show_dimensions !== false,
  }
}

const fmt = (value) => Number(value.toFixed(1)).toString()
const point = (x, y) => `${fmt(x)},${fmt(y)}`
const polygon = (points, fill) => `<polygon points="${points.map(([x, y]) => point(x, y)).join(' ')}" fill="${fill}" stroke="${blue}" stroke-width="2" stroke-linejoin="round"/>`
const path = (d, { fill = 'none', stroke = blue, dash = false, width = 2 } = {}) => `<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${width}"${dash ? ' stroke-dasharray="4 3"' : ''} stroke-linecap="round" stroke-linejoin="round"/>`
const line = (x1, y1, x2, y2, options = {}) => path(`M${point(x1, y1)} L${point(x2, y2)}`, options)
const label = (x, y, value) => `<text x="${fmt(x)}" y="${fmt(y)}" fill="${dimensionColor}" font-size="8" font-weight="600" text-anchor="middle">${value}</text>`
const boundedRatio = (value, maximum) => Math.max(0.5, value / maximum)

const prismMarkup = ({ solid, dimensions: d, show_hidden_edges: hidden, show_dimensions: labels }) => {
  const length = d.length
  const width = solid === 'cube' ? d.length : d.width
  const height = solid === 'cube' ? d.length : d.height
  const maximum = Math.max(length, width, height)
  const frontWidth = 68 * boundedRatio(length, maximum)
  const frontHeight = 60 * boundedRatio(height, maximum)
  const depth = 24 * boundedRatio(width, maximum)
  const rise = depth * 0.68
  const x = (180 - frontWidth - depth) / 2
  const y = (112 - frontHeight + rise) / 2 - 3
  const a = [x, y], b = [x + frontWidth, y], c = [x + frontWidth, y + frontHeight], e = [x, y + frontHeight]
  const f = [x + depth, y - rise], g = [x + frontWidth + depth, y - rise]
  const h = [x + frontWidth + depth, y + frontHeight - rise], i = [x + depth, y + frontHeight - rise]
  return [
    polygon([a, b, g, f], paleBlue),
    polygon([b, g, h, c], lightBlue),
    polygon([a, b, c, e], '#f8fbff'),
    hidden ? line(...f, ...i, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    hidden ? line(...i, ...h, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    hidden ? line(...e, ...i, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    labels ? label(x + frontWidth / 2, Math.min(109, y + frontHeight + 11), solid === 'cube' ? `棱长 ${fmt(length)}` : `长 ${fmt(length)}`) : '',
    labels && solid !== 'cube' ? label(x + frontWidth + depth + 12, y + frontHeight / 2, `高 ${fmt(height)}`) : '',
    labels && solid !== 'cube' ? label(x + frontWidth / 2 + depth / 2, y - rise / 2 + 4, `宽 ${fmt(width)}`) : '',
  ].join('')
}

const pyramidMarkup = ({ dimensions: d, show_hidden_edges: hidden, show_dimensions: labels }) => {
  const maximum = Math.max(d.length, d.height)
  const half = 38 * boundedRatio(d.length, maximum)
  const rise = 62 * boundedRatio(d.height, maximum)
  const baseY = 88
  const backY = baseY - 18
  const apex = [90, backY - rise + 8]
  const left = [90 - half, baseY], right = [90 + half, baseY]
  const backRight = [90 + half + 18, backY], backLeft = [90 - half + 18, backY]
  const center = [99, baseY - 9]
  return [
    polygon([apex, right, backRight], lightBlue),
    polygon([apex, left, right], '#f8fbff'),
    hidden ? line(...backLeft, ...backRight, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    hidden ? line(...left, ...backLeft, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    hidden ? line(...apex, ...backLeft, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    labels ? line(...apex, ...center, { dash: true, stroke: '#f59e0b', width: 1.5 }) : '',
    labels ? label(90, 102, `底边 ${fmt(d.length)}`) : '',
    labels ? label(110, 53, `高 ${fmt(d.height)}`) : '',
  ].join('')
}

const cylinderMarkup = ({ dimensions: d, show_hidden_edges: hidden, show_dimensions: labels }) => {
  const maximum = Math.max(d.radius * 2, d.height)
  const rx = 37 * boundedRatio(d.radius * 2, maximum)
  const bodyHeight = 58 * boundedRatio(d.height, maximum)
  const topY = (112 - bodyHeight) / 2 - 2
  const bottomY = topY + bodyHeight
  const left = 90 - rx, right = 90 + rx
  const ellipse = `M${point(left, topY)} A${fmt(rx)},10 0 1 1 ${point(right, topY)} A${fmt(rx)},10 0 1 1 ${point(left, topY)}`
  return [
    path(`M${point(left, topY)} L${point(left, bottomY)} A${fmt(rx)},10 0 0 0 ${point(right, bottomY)} L${point(right, topY)} Z`, { fill: paleBlue }),
    path(ellipse, { fill: '#f8fbff' }),
    hidden ? path(`M${point(left, bottomY)} A${fmt(rx)},10 0 0 1 ${point(right, bottomY)}`, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    labels ? label(90, Math.min(108, bottomY + 15), `半径 ${fmt(d.radius)}`) : '',
    labels ? label(right + 16, (topY + bottomY) / 2, `高 ${fmt(d.height)}`) : '',
  ].join('')
}

const coneMarkup = ({ dimensions: d, show_hidden_edges: hidden, show_dimensions: labels }) => {
  const maximum = Math.max(d.radius * 2, d.height)
  const rx = 40 * boundedRatio(d.radius * 2, maximum)
  const h = 68 * boundedRatio(d.height, maximum)
  const baseY = 85
  const apexY = baseY - h
  const left = 90 - rx, right = 90 + rx
  return [
    path(`M${point(90, apexY)} L${point(left, baseY)} A${fmt(rx)},11 0 0 0 ${point(right, baseY)} Z`, { fill: paleBlue }),
    hidden ? path(`M${point(left, baseY)} A${fmt(rx)},11 0 0 1 ${point(right, baseY)}`, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    labels ? line(90, apexY, 90, baseY, { dash: true, stroke: '#f59e0b', width: 1.5 }) : '',
    labels ? label(90, 105, `半径 ${fmt(d.radius)}`) : '',
    labels ? label(106, (apexY + baseY) / 2, `高 ${fmt(d.height)}`) : '',
  ].join('')
}

const sphereMarkup = ({ dimensions: d, show_hidden_edges: hidden, show_dimensions: labels }) => {
  const r = 39
  const cx = 90, cy = 54
  return [
    `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${paleBlue}" stroke="${blue}" stroke-width="2"/>`,
    hidden ? path(`M${cx - r},${cy} A${r},13 0 0 1 ${cx + r},${cy}`, { dash: true, stroke: mutedBlue, width: 1.6 }) : '',
    path(`M${cx - r},${cy} A${r},13 0 0 0 ${cx + r},${cy}`, { width: 1.5 }),
    hidden ? path(`M${cx},${cy - r} A13,${r} 0 0 0 ${cx},${cy + r}`, { dash: true, stroke: mutedBlue, width: 1.4 }) : '',
    path(`M${cx},${cy - r} A13,${r} 0 0 1 ${cx},${cy + r}`, { width: 1.4 }),
    labels ? line(cx, cy, cx + r, cy, { stroke: '#f59e0b', width: 1.5 }) : '',
    labels ? label(cx + 18, cy - 4, `r=${fmt(d.radius)}`) : '',
  ].join('')
}

export const solidMarkup = (value = {}) => {
  const data = normalizeSolidData(value)
  const content = {
    cube: prismMarkup,
    cuboid: prismMarkup,
    pyramid: pyramidMarkup,
    cylinder: cylinderMarkup,
    cone: coneMarkup,
    sphere: sphereMarkup,
  }[data.solid](data)
  const name = shapeLabels[data.solid]
  return `<svg xmlns="http://www.w3.org/2000/svg" class="a12-solid-svg" viewBox="0 0 180 112" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${name}示意图" font-family="Microsoft YaHei,Arial,sans-serif"><title>${name}示意图</title>${content}</svg>`
}

const volumeText = (number, approximate = false) => `${approximate ? '约 ' : ''}${Number(number.toFixed(2))} 立方单位`

export const solidFacts = (value = {}) => {
  const { solid, dimensions: d } = normalizeSolidData(value)
  const facts = {
    cube: { structure: '6 个面 · 12 条棱 · 8 个顶点', formula: 'V = a³', volume: d.length ** 3 },
    cuboid: { structure: '6 个面 · 12 条棱 · 8 个顶点', formula: 'V = 长 × 宽 × 高', volume: d.length * d.width * d.height },
    pyramid: { structure: '5 个面 · 8 条棱 · 5 个顶点', formula: 'V = 底面积 × 高 ÷ 3', volume: d.length ** 2 * d.height / 3 },
    cylinder: { structure: '2 个圆形底面和 1 个曲面', formula: 'V = πr²h', volume: Math.PI * d.radius ** 2 * d.height, approximate: true },
    cone: { structure: '1 个圆形底面和 1 个曲面', formula: 'V = πr²h ÷ 3', volume: Math.PI * d.radius ** 2 * d.height / 3, approximate: true },
    sphere: { structure: '1 个连续曲面 · 无棱无顶点', formula: 'V = 4πr³ ÷ 3', volume: 4 * Math.PI * d.radius ** 3 / 3, approximate: true },
  }[solid]
  return { label: shapeLabels[solid], structure: facts.structure, formula: facts.formula, volumeText: volumeText(facts.volume, facts.approximate) }
}
