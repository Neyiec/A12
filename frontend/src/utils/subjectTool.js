/**
 * 学科工具的前端协议层。
 *
 * 后端 `POST /projects/tools/validate-component` 只接受这里列出的六种
 * component type。这里集中做旧数据兼容、默认值和学科工具的前端预览，
 * 使编辑器、预览和保存都使用同一份组件数据。
 */
import katex from 'katex'
import katexStyles from 'katex/dist/katex.min.css?inline'
import {
  cachedChemicalStructure,
  chemicalStructureKey,
} from './chemicalStructure'

export const subjectToolOptions = [
  { value: 'math_formula', label: '数学公式' },
  { value: 'chemical_formula', label: '化学式 / 分子式' },
  { value: 'mermaid_diagram', label: '流程 / 关系图' },
  { value: 'chart', label: '数据图表' },
  { value: 'table', label: '探究数据表' },
  { value: 'geometry', label: '几何画板' },
]

const supportedTypes = new Set(subjectToolOptions.map((item) => item.value))
const typeAliases = {
  math: 'math_formula',
  formula: 'math_formula',
  physics: 'math_formula',
  chemistry: 'chemical_formula',
  chemistry_formula: 'chemical_formula',
  chemical: 'chemical_formula',
  data: 'chart',
  graph: 'chart',
  flowchart: 'mermaid_diagram',
  diagram: 'mermaid_diagram',
  mermaid: 'mermaid_diagram',
  general: 'mermaid_diagram',
}

const plainObject = (value) => value && typeof value === 'object' && !Array.isArray(value)
const has = (value, key) => Object.prototype.hasOwnProperty.call(value || {}, key)
const text = (value, fallback = '', limit = 4000) => String(value ?? fallback).trim().slice(0, limit)
const clone = (value, fallback = {}) => {
  try { return JSON.parse(JSON.stringify(value)) } catch { return fallback }
}

export const normalizeSubjectToolType = (value) => {
  const raw = String(value || '').trim().toLowerCase().replace(/[\s-]+/g, '_')
  const normalized = typeAliases[raw] || raw
  return supportedTypes.has(normalized) ? normalized : 'geometry'
}

export const subjectToolLabel = (value) => subjectToolOptions
  .find((item) => item.value === normalizeSubjectToolType(value))?.label || '学科工具'

export const parseSubjectToolData = (value) => {
  if (Array.isArray(value)) return { rows: clone(value, []) }
  if (plainObject(value)) return clone(value, {})
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) return { rows: parsed }
      if (plainObject(parsed)) return parsed
    } catch { /* 保留旧版说明文本 */ }
    return value.trim() ? { description: value.trim() } : {}
  }
  return {}
}

const defaultChartOption = () => ({
  title: { text: '数据比较' },
  xAxis: { type: 'category', data: ['A 组', 'B 组', 'C 组'] },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: [68, 82, 56] }],
})

const legacyChartOption = (source = {}) => ({
  title: { text: text(source.description || '数据比较', '数据比较', 40) || '数据比较' },
  xAxis: { type: 'category', data: [text(source.firstLabel, 'A', 12) || 'A', text(source.secondLabel, 'B', 12) || 'B'] },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    data: [Number(source.first ?? source.a ?? 42) || 0, Number(source.second ?? source.b ?? 58) || 0],
  }],
})

export const createSubjectToolData = (type, legacyType = '') => {
  const normalizedType = normalizeSubjectToolType(type)
  const legacy = String(legacyType || '').trim().toLowerCase()
  if (normalizedType === 'math_formula') return {
    latex: legacy === 'physics' ? 'F=ma' : 'a^2 + b^2 = c^2',
    display_mode: true,
  }
  if (normalizedType === 'chemical_formula') return { formula: 'H2O' }
  if (normalizedType === 'mermaid_diagram') return {
    mermaid: 'flowchart LR\nA[提出问题] --> B[观察与探究]\nB --> C[形成结论]',
  }
  if (normalizedType === 'chart') return { option: defaultChartOption(), responsive: true }
  if (normalizedType === 'table') return {
    columns: ['项目', '观察结果'],
    rows: [['实验组', ''], ['对照组', '']],
  }
  return {
    construction: 'right_triangle',
    commands: ['draw_right_triangle'],
  }
}

const normalizedOption = (value, fallback) => {
  if (plainObject(value)) return clone(value, fallback)
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return plainObject(parsed) ? parsed : value.trim()
    } catch { return value.trim() }
  }
  return clone(fallback, {})
}

/**
 * 不会把教师明确输入的空值替换掉，以便后端能给出必填项校验提示；
 * 仅在字段完全缺失时补上可立即运行的默认数据。
 */
export const normalizeSubjectToolData = (value, type) => {
  const source = parseSubjectToolData(value)
  const rawType = String(type || source.subjectType || source.subject_type || '').trim().toLowerCase()
  const normalizedType = normalizeSubjectToolType(rawType)
  const defaults = createSubjectToolData(normalizedType, rawType)
  const base = { ...source }

  if (normalizedType === 'math_formula') return {
    ...base,
    latex: has(source, 'latex') ? text(source.latex, '', 2000) : defaults.latex,
    display_mode: has(source, 'display_mode') ? Boolean(source.display_mode) : true,
  }
  if (normalizedType === 'chemical_formula') return {
    ...base,
    formula: has(source, 'formula') ? text(source.formula, '', 300) : defaults.formula,
    ...(has(source, 'smiles') ? { smiles: text(source.smiles, '', 4000) } : {}),
    ...(has(source, 'molfile') ? { molfile: text(source.molfile, '', 24000) } : {}),
  }
  if (normalizedType === 'mermaid_diagram') return {
    ...base,
    mermaid: has(source, 'mermaid') ? text(source.mermaid, '', 8000) : defaults.mermaid,
  }
  if (normalizedType === 'chart') {
    const chartFallback = rawType === 'data' ? legacyChartOption(source) : defaults.option
    return {
      ...base,
      option: has(source, 'option') ? normalizedOption(source.option, chartFallback) : chartFallback,
      responsive: has(source, 'responsive') ? Boolean(source.responsive) : true,
    }
  }
  if (normalizedType === 'table') return {
    ...base,
    ...(has(source, 'columns') ? { columns: Array.isArray(source.columns) ? source.columns.map((item) => text(item, '', 80)) : source.columns } : { columns: defaults.columns }),
    ...(has(source, 'rows') ? { rows: Array.isArray(source.rows) ? clone(source.rows, []) : source.rows } : { rows: defaults.rows }),
  }
  return {
    ...base,
    construction: has(source, 'construction') ? text(source.construction, '', 400) : defaults.construction,
    commands: has(source, 'commands') ? (Array.isArray(source.commands) ? source.commands.map((item) => text(item, '', 200)).filter(Boolean) : source.commands) : defaults.commands,
  }
}

export const subjectToolDefaultRenderHint = (type) => {
  const normalizedType = normalizeSubjectToolType(type)
  const hints = {
    math_formula: { engine: 'katex', input: 'latex', output: ['html', 'svg'] },
    chemical_formula: { engine: 'kekule', input: ['formula', 'smiles', 'molfile'], output: ['svg', 'canvas'] },
    mermaid_diagram: { engine: 'mermaid', input: 'mermaid', output: ['svg'] },
    chart: { engine: 'echarts', input: 'option', output: ['canvas', 'svg'] },
    table: { engine: 'html_table', input: ['columns', 'rows'], output: ['html'] },
    geometry: { engine: 'jsxgraph', input: ['construction', 'commands'], output: ['svg', 'html'] },
  }
  return clone(hints[normalizedType], {})
}

export const subjectToolPayload = (element = {}) => {
  const type = normalizeSubjectToolType(element.subjectType || element.subject_type || element.type)
  // `render` is the request-side configuration. Older drafts stored this
  // under `subjectRender`, so keep that as a backwards-compatible fallback.
  const render = plainObject(element.render) && Object.keys(element.render).length
    ? element.render
    : (plainObject(element.subjectRender) && Object.keys(element.subjectRender).length
      ? element.subjectRender
      : (plainObject(element.subject_render) && Object.keys(element.subject_render).length ? element.subject_render : {}))
  const subjectStyle = plainObject(element.subjectStyle) && Object.keys(element.subjectStyle).length
    ? element.subjectStyle
    : (plainObject(element.subject_style) && Object.keys(element.subject_style).length
      ? element.subject_style
      : (plainObject(element.style) ? element.style : {}))
  return {
    component_id: String(element.id || element.component_id || ''),
    type,
    data: normalizeSubjectToolData(element.data, element.subjectType || element.subject_type || type),
    render: clone(render, {}),
    style: clone(subjectStyle, {}),
  }
}

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const formatFormula = (value, displayMode = true) => {
  const latex = String(value || '')
  try {
    return katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      output: 'htmlAndMathml',
    })
  } catch {
    return escapeHtml(latex)
  }
}

const formatChemicalFormula = (value) => escapeHtml(value || '')
  .replace(/([A-Za-z)])(\d+)/g, '$1<sub>$2</sub>')

const chartRows = (option) => {
  const source = plainObject(option) ? option : {}
  const xAxis = Array.isArray(source.xAxis) ? source.xAxis[0] : source.xAxis
  const series = Array.isArray(source.series) ? source.series[0] : source.series
  const values = Array.isArray(series?.data) ? series.data : []
  const labels = Array.isArray(xAxis?.data) ? xAxis.data : []
  const count = Math.max(1, Math.min(8, values.length || labels.length || 3))
  return Array.from({ length: count }, (_, index) => ({
    label: text(labels[index], `数据 ${index + 1}`, 16) || `数据 ${index + 1}`,
    value: Number(typeof values[index] === 'object' ? values[index]?.value : values[index]) || 0,
  }))
}

const tableShape = (data) => {
  const rawRows = Array.isArray(data.rows) ? data.rows : []
  const rawColumns = Array.isArray(data.columns) ? data.columns : []
  const objectRow = rawRows.find((row) => plainObject(row))
  const columns = rawColumns.length
    ? rawColumns.map((item, index) => text(plainObject(item) ? item.label || item.name || item.key : item, `列 ${index + 1}`, 60) || `列 ${index + 1}`)
    : (objectRow ? Object.keys(objectRow).slice(0, 8) : ['项目', '内容'])
  const rows = rawRows.slice(0, 8).map((row) => {
    if (Array.isArray(row)) return columns.map((_, index) => text(row[index], '', 120))
    if (plainObject(row)) return columns.map((column) => text(row[column], '', 120))
    return [text(row, '', 120), ...columns.slice(1).map(() => '')]
  })
  return { columns, rows: rows.length ? rows : [['', '']] }
}

const diagramNodes = (source) => {
  const code = String(source || '')
  const matches = [...code.matchAll(/[\[\(]([^\]\)]+)[\]\)]/g)].map((match) => text(match[1], '', 22)).filter(Boolean)
  if (matches.length) return [...new Set(matches)].slice(0, 4)
  return code.split(/-->|==>|-.->|\r?\n/).map((part) => part.replace(/^(flowchart|graph)\s+\w+/i, '').trim()).filter(Boolean).slice(0, 4)
}

export const geometryPoints = (data = {}) => {
  const defaults = [{ x: 18, y: 82 }, { x: 156, y: 82 }, { x: 156, y: 18 }]
  return defaults.map((fallback, index) => {
    const point = data.points?.[index]
    return {
      x: Number.isFinite(Number(point?.x)) ? Math.max(8, Math.min(172, Number(point.x))) : fallback.x,
      y: Number.isFinite(Number(point?.y)) ? Math.max(8, Math.min(92, Number(point.y))) : fallback.y,
    }
  })
}

export const geometryMarkup = (data = {}) => {
  const points = geometryPoints(data)
  const path = points.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.y}`).join(' ') + ' Z'
  return `<svg viewBox="0 0 180 100" role="group" aria-label="几何画板，拖动顶点调整三角形"><path d="${path}"/>${points.map((point, index) => `<circle data-subject-point="${index}" cx="${point.x}" cy="${point.y}" r="5" tabindex="0" role="slider" aria-label="顶点 ${'ABC'[index]}，方向键移动" aria-valuemin="8" aria-valuemax="172" aria-valuenow="${point.x}" aria-valuetext="${point.x}, ${point.y}"/><text x="${point.x}" y="${point.y - 8}">${'ABC'[index]}</text>`).join('')}</svg>`
}

export const subjectToolMarkup = ({ subjectType, data, title } = {}) => {
  const type = normalizeSubjectToolType(subjectType)
  const state = normalizeSubjectToolData(data, subjectType || type)
  const titleText = text(title, '', 80)
  const genericTitles = new Set(['新增学科工具', '学科探究工具', '学科工具'])
  const showCustomTitle = Boolean(titleText)
    && !genericTitles.has(titleText)
    && !/^学科工具\s*\d+$/.test(titleText)
    && titleText !== subjectToolLabel(type)
  const header = `<header class="a12-subject-tool__header" data-a12-subject-v2>${showCustomTitle ? `<strong data-a12-subject-title>${escapeHtml(titleText)}</strong>` : ''}</header>`
  const noteText = text(state.description || state.instruction, '', 240)
  const note = noteText ? `<p class="a12-subject-tool__note">${escapeHtml(noteText)}</p>` : ''
  const withContext = (content) => `${header}${content}${note}`

  if (type === 'math_formula') {
    return withContext(`<div class="a12-subject-tool__formula" aria-label="数学公式">${formatFormula(state.latex, state.display_mode !== false)}</div>`)
  }
  if (type === 'chemical_formula') {
    const hasStructureInput = Boolean(state.molfile || state.smiles)
    if (hasStructureInput) {
      const key = chemicalStructureKey(state)
      const cached = cachedChemicalStructure(state)
      const rendered = cached
        ? ` data-a12-chemical-rendered-key="${escapeHtml(`${key}:24`)}"`
        : ''
      const content = cached?.svg
        ? cached.svg
        : cached?.error
          ? `<span class="a12-subject-tool__molecule-error" role="status">${escapeHtml(cached.error)}</span>`
          : ''
      return withContext(`<div class="a12-subject-tool__chemical a12-subject-tool__chemical--structure" aria-label="化学分子结构"><div class="a12-subject-tool__molecule" data-a12-chemical-key="${escapeHtml(key)}"${rendered}>${content}</div></div>`)
    }
    return withContext(`<div class="a12-subject-tool__chemical" aria-label="化学式"><span>${formatChemicalFormula(state.formula)}</span></div>`)
  }
  if (type === 'mermaid_diagram') {
    const nodes = diagramNodes(state.mermaid)
    const nodeMarkup = nodes.length
      ? nodes.map((node, index) => `<span>${escapeHtml(node)}${index < nodes.length - 1 ? '<i>→</i>' : ''}</span>`).join('')
      : ''
    return withContext(`<div class="a12-subject-tool__diagram" aria-label="流程关系图">${nodeMarkup}</div>`)
  }
  if (type === 'chart') {
    const rows = chartRows(state.option)
    const max = Math.max(1, ...rows.map((item) => Math.abs(item.value)))
    const bars = rows.map((item) => `<div class="a12-subject-tool__bar"><i style="height:${Math.max(8, Math.min(100, Math.round(Math.abs(item.value) / max * 100)))}%"></i><small>${escapeHtml(item.label)}</small></div>`).join('')
    const chartTitle = text(state.option?.title?.text, '', 72)
    const chartTitleMarkup = chartTitle ? `<strong class="a12-subject-tool__chart-title">${escapeHtml(chartTitle)}</strong>` : ''
    return withContext(`<div class="a12-subject-tool__chart-area">${chartTitleMarkup}<div class="a12-subject-tool__chart" aria-label="数据图表">${bars}</div></div>`)
  }
  if (type === 'table') {
    const table = tableShape(state)
    return withContext(`<div class="a12-subject-tool__table-wrap"><table><thead><tr>${table.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${table.rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`)
  }
  return withContext(`<div class="a12-subject-tool__geometry">${geometryMarkup(state)}</div>`)
}

export const subjectToolRuntimeCss = `${katexStyles}
  .a12-subject-tool .a12-subject-tool__geometry svg{height:100%!important;min-height:60px;overflow:visible}
  .a12-subject-tool [data-subject-point]{cursor:crosshair;touch-action:none;pointer-events:all}
  .a12-subject-tool [data-subject-point]:focus{outline:none;stroke:#ea580c;stroke-width:3}
  .a12-subject-tool{display:grid!important;grid-template-rows:auto minmax(0,1fr) auto;gap:7px!important;width:100%;height:100%;box-sizing:border-box;min-width:0!important;padding:10px 12px!important;overflow:hidden!important;border:var(--widget-border-width,1px) solid var(--widget-border-color,#bfdbfe)!important;border-radius:var(--widget-border-radius,10px)!important;color:var(--widget-color,#27405f)!important;background:var(--widget-background,#f7fbff)!important;font:10px/1.35 "Microsoft YaHei",Arial,sans-serif!important;cursor:move}
  .a12-subject-tool *{box-sizing:border-box}.a12-subject-tool__header{display:flex;align-items:baseline;gap:8px;min-width:0}.a12-subject-tool__header span{display:none!important}.a12-subject-tool__header strong{overflow:hidden;color:#173d78;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.a12-subject-tool__note{margin:0;max-height:2.9em;overflow:hidden;color:#607491;font-size:11px;line-height:1.45;white-space:normal}.a12-subject-tool__formula{display:flex;align-items:center;justify-content:center;min-height:0;overflow:auto;color:#1d4ed8;font:700 clamp(15px,2.1vw,25px)/1.25 Georgia,"Times New Roman",serif;text-align:center}.a12-subject-tool__formula sup,.a12-subject-tool__formula sub{font-size:.62em}.a12-subject-tool__chemical{display:grid;place-items:center;min-width:0;min-height:0;overflow:hidden;color:#0f766e;font:700 clamp(20px,3vw,34px)/1.15 Arial,"Microsoft YaHei",sans-serif}.a12-subject-tool__chemical span{white-space:nowrap}.a12-subject-tool__chemical sub{font-size:.58em}.a12-subject-tool__chemical--structure{width:100%;height:100%;padding:2px}.a12-subject-tool__molecule{display:grid;place-items:center;width:100%;height:100%;min-width:0;min-height:0;overflow:hidden}.a12-subject-tool__molecule-image{display:block;width:100%;height:100%;min-width:0;min-height:0;object-fit:contain}.a12-subject-tool__molecule-error{max-width:100%;color:#b42318;font-size:.46em;font-weight:500;text-align:center;white-space:normal}.a12-subject-tool__diagram{display:flex;align-items:center;justify-content:center;gap:5px;min-width:0;min-height:0;overflow:hidden}.a12-subject-tool__diagram span{display:inline-flex;align-items:center;gap:5px;min-width:0;padding:5px 7px;border:1px solid #bfdbfe;border-radius:6px;color:#24558d;background:#eff6ff;font-size:9px;white-space:nowrap}.a12-subject-tool__diagram i{margin-right:-12px;color:#6b8bb4;font-size:12px;font-style:normal}.a12-subject-tool__diagram em{color:#8495aa;font-style:normal}.a12-subject-tool__chart-area{display:flex;flex-direction:column;min-width:0;min-height:0}.a12-subject-tool__chart-title{flex:none;overflow:hidden;color:#24558d;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.a12-subject-tool__chart{display:flex;flex:1;align-items:flex-end;justify-content:space-around;gap:6px;min-height:42px;padding:5px 4px 0;border-bottom:1px solid rgb(96 116 145 / 22%)}.a12-subject-tool__bar{display:flex;flex:1 1 0;align-items:center;justify-content:flex-end;gap:3px;min-width:0;height:100%;flex-direction:column}.a12-subject-tool__bar i{display:block;flex:0 0 auto;width:min(20px,70%);min-height:6px;border-radius:4px 4px 1px 1px;background:#3b82f6}.a12-subject-tool__bar small{overflow:hidden;max-width:100%;color:#607491;font-size:8px;text-overflow:ellipsis;white-space:nowrap}.a12-subject-tool__table-wrap{min-height:0;overflow:auto;border:1px solid rgb(37 99 235 / 16%);border-radius:6px}.a12-subject-tool__table-wrap table{width:100%;border-collapse:collapse;font-size:9px}.a12-subject-tool__table-wrap th,.a12-subject-tool__table-wrap td{padding:4px 6px;border:1px solid rgb(37 99 235 / 14%);text-align:left;white-space:nowrap}.a12-subject-tool__table-wrap th{color:#24558d;background:#eff6ff}.a12-subject-tool__geometry{display:grid;place-items:center;min-height:0}.a12-subject-tool__geometry svg{display:block;width:100%;height:58px}.a12-subject-tool__geometry path{fill:none;stroke:#2563eb;stroke-width:2}.a12-subject-tool__geometry circle{fill:#fff;stroke:#2563eb;stroke-width:2}.a12-subject-tool__geometry text{fill:#315f9f;font-size:9px;text-anchor:middle}
  .a12-subject-tool{font-size:var(--subject-font-size,24px)!important}.a12-subject-tool__header strong{font-size:.6em}.a12-subject-tool__note{font-size:.48em}.a12-subject-tool__formula,.a12-subject-tool__chemical{font-size:1em}.a12-subject-tool__chart-title{font-size:.58em}.a12-subject-tool__bar small{font-size:.4em}.a12-subject-tool__table-wrap table{font-size:.45em}.a12-subject-tool__diagram span{font-size:.42em}.a12-subject-tool__geometry text{font-size:.42em}
  .a12-subject-tool__molecule-svg{display:block;width:100%;height:100%;min-width:0;min-height:0}
  .a12-subject-tool__molecule-svg path[class^="atom-"]{stroke:currentColor;stroke-width:.75px;stroke-linejoin:round}
`
