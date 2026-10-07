/**
 * 学科工具的前端协议层。
 *
 * 这里集中做旧数据兼容、默认值和学科工具的前端预览，
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
  { value: 'chinese_tianzige', label: '语文田字格 / 拼音' },
  { value: 'english_four_line', label: '英语四线格' },
  { value: 'chemical_formula', label: '化学式 / 分子式' },
  { value: 'mermaid_diagram', label: '流程图' },
  { value: 'chart', label: '数据图表' },
  { value: 'table', label: '探究数据表' },
  { value: 'geometry', label: '几何图形' },
]

// 图表和表格使用同一份组件协议，但在工作台中由外层工具栏提供入口。
export const subjectToolMenuOptions = subjectToolOptions.filter((item) => !['chart', 'table'].includes(item.value))

const supportedTypes = new Set(subjectToolOptions.map((item) => item.value))
const typeAliases = {
  math: 'math_formula',
  formula: 'math_formula',
  physics: 'math_formula',
  chinese: 'chinese_tianzige',
  tianzige: 'chinese_tianzige',
  chinese_pinyin: 'chinese_tianzige',
  english: 'english_four_line',
  four_line: 'english_four_line',
  fourline: 'english_four_line',
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
  if (normalizedType === 'chinese_tianzige') return {
    entries: [{ character: '你', pinyin: 'nǐ' }, { character: '好', pinyin: 'hǎo' }],
    show_pinyin: true,
  }
  if (normalizedType === 'english_four_line') return { text: 'Aa Bb Cc' }
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
  if (normalizedType === 'chinese_tianzige') {
    const rawEntries = Array.isArray(source.entries)
      ? source.entries
      : has(source, 'text')
        ? Array.from(String(source.text ?? '').replace(/\s/g, '')).map((character, index) => ({
          character,
          pinyin: String(source.pinyin ?? '').trim().split(/\s+/)[index] || '',
        }))
        : defaults.entries
    return {
      ...base,
      entries: rawEntries.slice(0, 80).map((entry) => ({
        character: Array.from(String((plainObject(entry) ? entry.character : entry) ?? '').trim())[0] || '',
        pinyin: text(plainObject(entry) ? entry.pinyin : '', '', 32),
      })),
      show_pinyin: has(source, 'show_pinyin') ? Boolean(source.show_pinyin) : true,
    }
  }
  if (normalizedType === 'english_four_line') return {
    ...base,
    text: has(source, 'text') ? String(source.text ?? '').replace(/\r\n?/g, '\n').slice(0, 1000).split('\n').slice(0, 40).join('\n') : defaults.text,
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
    chinese_tianzige: { engine: 'html_grid', input: ['entries', 'show_pinyin'], output: ['html'] },
    english_four_line: { engine: 'html_grid', input: 'text', output: ['html'] },
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

export const chemicalElementSymbols = 'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split(' ')
const chemicalElementSet = new Set(chemicalElementSymbols)
const chemicalLiteralSymbols = new Set('+-−=≡~·.•×:→⇌↔⇄⇆⇋⇔↑↓Δ,;⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉'.split(''))

const chemicalAtomMarkup = (symbol, valence, electronCount) => {
  if (valence === null && electronCount === null) return escapeHtml(symbol)
  const hasValence = valence !== null
  const hasElectrons = electronCount !== null
  const classes = 'a12-chem-atom'
    + (hasValence ? ' a12-chem-atom--valence' : '')
    + (hasElectrons ? ' a12-chem-atom--electrons' : '')
  const valenceMarkup = hasValence
    ? '<span class="a12-chem-atom__valence">' + escapeHtml(valence) + '</span>'
    : ''
  const sides = ['top', 'right', 'bottom', 'left']
  const electronMarkup = hasElectrons
    ? sides.map((side, index) => {
      const count = Number(electronCount > index) + Number(electronCount > index + 4)
      return count
        ? '<span class="a12-chem-atom__electron a12-chem-atom__electron--' + side + '">' + '•'.repeat(count) + '</span>'
        : ''
    }).join('')
    : ''
  return '<span class="' + classes + '">' + valenceMarkup
    + '<span class="a12-chem-atom__symbol">' + escapeHtml(symbol) + '</span>'
    + electronMarkup + '</span>'
}

const scanChemicalFormula = (value) => {
  const formula = String(value ?? '')
  let markup = ''
  let error = ''
  let index = 0
  let canSubscript = false
  const brackets = []
  const report = (message) => { if (!error) error = message }

  while (index < formula.length) {
    const rest = formula.slice(index)
    const character = formula[index]

    // Physical-state suffixes are text, not sequences of element symbols.
    const physicalState = /^\((?:aq|s|l|g)\)/.exec(rest)
    if (physicalState) {
      markup += escapeHtml(physicalState[0])
      index += physicalState[0].length
      canSubscript = false
      continue
    }

    if (/^[A-Z]/.test(character)) {
      const symbol = /^[A-Z][a-z]?/.exec(rest)[0]
      if (!chemicalElementSet.has(symbol)) report('“' + symbol + '”不是有效的元素符号。')
      index += symbol.length
      let valence = null
      let electronCount = null
      while (formula[index] === '{') {
        const decoration = formula.slice(index)
        const oxidation = /^\{([+−-]?\d{1,3}|[+−-])\}/.exec(decoration)
        const electrons = /^\{e:([1-8])\}/.exec(decoration)
        if (oxidation) {
          if (valence !== null) report('同一元素只能标注一次化合价。')
          valence = oxidation[1]
          index += oxidation[0].length
        } else if (electrons) {
          if (electronCount !== null) report('同一元素只能标注一次价电子点。')
          electronCount = Number(electrons[1])
          index += electrons[0].length
        } else {
          report(decoration.includes('}')
            ? '元素上方的化合价请写为 Fe{+3}；价电子点请写为 O{e:6}。'
            : '请补全元素标注右侧的 }，例如 Fe{+3}。')
          break
        }
      }
      markup += chemicalAtomMarkup(symbol, valence, electronCount)
      canSubscript = true
      continue
    }

    // The lower-case e is reserved for an electron, such as e^-.
    if (character === 'e' && formula[index + 1] === '^') {
      markup += 'e'
      index += 1
      canSubscript = false
      continue
    }

    if (character === '_' || character === '^') {
      const tag = character === '_' ? 'sub' : 'sup'
      if (formula[index + 1] === '{') {
        const closing = formula.indexOf('}', index + 2)
        if (closing < 0) {
          report(character === '_' ? '请补全下标右侧的 }，例如 H_{2}。' : '请补全上标右侧的 }，例如 Fe^{3+}。')
          markup += escapeHtml(formula.slice(index))
          break
        }
        const label = formula.slice(index + 2, closing)
        if (!/^[A-Za-z0-9+−-]{1,16}$/.test(label)) {
          report(character === '_' ? '下标内容请使用数字、字母或正负号。' : '上标内容请使用数字、字母或正负号。')
        }
        markup += '<' + tag + '>' + escapeHtml(label) + '</' + tag + '>'
        index = closing + 1
        canSubscript = false
        continue
      }
      const charge = character === '^' ? /^\^(\d{0,3})([+−-])/.exec(rest) : null
      if (charge) {
        markup += '<sup>' + escapeHtml(charge[1] + charge[2]) + '</sup>'
        index += charge[0].length
        canSubscript = false
        continue
      }
      report(character === '_' ? '下标请写为 _{2}；普通化学计量数可直接输入数字。' : '上标请写为 ^{2}；电荷也可写为 ^2-。')
      markup += escapeHtml(character)
      index += 1
      canSubscript = false
      continue
    }

    if (/^\d/.test(character)) {
      const digits = /^\d+/.exec(rest)[0]
      markup += canSubscript ? '<sub>' + digits + '</sub>' : digits
      index += digits.length
      canSubscript = false
      continue
    }

    if (character === '(' || character === '[') {
      brackets.push(character)
      markup += character
      canSubscript = false
      index += 1
      continue
    }
    if (character === ')' || character === ']') {
      const opening = brackets.pop()
      if ((character === ')' && opening !== '(') || (character === ']' && opening !== '[')) {
        report('括号没有正确配对。')
      }
      markup += character
      canSubscript = true
      index += 1
      continue
    }

    if (character === '+') {
      markup += '<span class="a12-chem-operator">+</span>'
      canSubscript = false
      index += 1
      continue
    }
    if ('→⇌↔⇄⇆⇋⇔'.includes(character)) {
      markup += '<span class="a12-chem-arrow">' + escapeHtml(character) + '</span>'
      canSubscript = false
      index += 1
      continue
    }
    if (chemicalLiteralSymbols.has(character) || /\s/.test(character)) {
      markup += escapeHtml(character)
      canSubscript = false
      index += 1
      continue
    }

    if (character === '{' && !formula.slice(index).includes('}')) {
      report('请补全标注右侧的 }。')
    } else {
      report('包含暂不支持的字符“' + character + '”。')
    }
    markup += escapeHtml(character)
    canSubscript = false
    index += 1
  }

  if (brackets.length) report('括号没有正确配对。')
  if (/[.·]$|^[.·]|[.·]{2}/.test(formula.trim())) report('结晶水分隔符两侧都需要有内容。')
  return { markup, error }
}

export const chemicalFormulaMarkup = (value) => scanChemicalFormula(value).markup
export const chemicalFormulaError = (value) => scanChemicalFormula(value).error

const chartRows = (option) => {
  const source = plainObject(option) ? option : {}
  const xAxis = Array.isArray(source.xAxis) ? source.xAxis[0] : source.xAxis
  const series = Array.isArray(source.series) ? source.series[0] : source.series
  const values = Array.isArray(series?.data) ? series.data : []
  const labels = Array.isArray(xAxis?.data) ? xAxis.data : []
  const count = Math.max(1, Math.min(source.a12_function_graph ? 81 : 8, values.length || labels.length || 3))
  return Array.from({ length: count }, (_, index) => ({
    label: text(labels[index] ?? (typeof values[index] === 'object' ? values[index]?.name : ''), `数据 ${index + 1}`, 16) || `数据 ${index + 1}`,
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
  const rows = rawRows.slice(0, 12).map((row) => {
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

const geometryPresets = {
  right_triangle: [{ x: 18, y: 82 }, { x: 156, y: 82 }, { x: 156, y: 18 }],
  triangle: [{ x: 28, y: 82 }, { x: 90, y: 16 }, { x: 152, y: 82 }],
  equilateral_triangle: [{ x: 34, y: 82 }, { x: 90, y: 18 }, { x: 146, y: 82 }],
  rectangle: [{ x: 34, y: 22 }, { x: 146, y: 22 }, { x: 146, y: 78 }, { x: 34, y: 78 }],
  square: [{ x: 55, y: 15 }, { x: 125, y: 15 }, { x: 125, y: 85 }, { x: 55, y: 85 }],
  parallelogram: [{ x: 50, y: 22 }, { x: 150, y: 22 }, { x: 130, y: 78 }, { x: 30, y: 78 }],
  rhombus: [{ x: 90, y: 12 }, { x: 154, y: 50 }, { x: 90, y: 88 }, { x: 26, y: 50 }],
}

export const geometryPresetPoints = (construction = 'right_triangle') => clone(
  geometryPresets[String(construction || '').toLowerCase()] || geometryPresets.right_triangle,
  geometryPresets.right_triangle,
)

export const geometryPoints = (data = {}) => {
  const preset = geometryPresetPoints(data.construction)
  const supplied = Array.isArray(data.points) ? data.points : []
  const pointCount = supplied.length >= 3 && supplied.length <= 8 ? supplied.length : preset.length
  const defaults = Array.from({ length: pointCount }, (_, index) => preset[index] || {
    x: 90 + Math.cos((index / pointCount) * Math.PI * 2) * 42,
    y: 50 + Math.sin((index / pointCount) * Math.PI * 2) * 34,
  })
  return defaults.map((fallback, index) => {
    const point = supplied[index]
    return {
      x: Number.isFinite(Number(point?.x)) ? Math.max(8, Math.min(172, Number(point.x))) : fallback.x,
      y: Number.isFinite(Number(point?.y)) ? Math.max(8, Math.min(92, Number(point.y))) : fallback.y,
    }
  })
}

const geometryPointLabel = (index) => String.fromCharCode(65 + (index % 26))

export const geometryMarkup = (data = {}) => {
  const points = geometryPoints(data)
  const path = points.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.y}`).join(' ') + ' Z'
  return `<svg viewBox="0 0 180 100" role="group" aria-label="几何图形，拖动顶点调整形状"><path d="${path}"/>${points.map((point, index) => `<circle data-subject-point="${index}" cx="${point.x}" cy="${point.y}" r="5" tabindex="0" role="slider" aria-label="顶点 ${geometryPointLabel(index)}，方向键移动" aria-valuemin="8" aria-valuemax="172" aria-valuenow="${point.x}" aria-valuetext="${point.x}, ${point.y}"/><text x="${point.x}" y="${point.y - 8}">${geometryPointLabel(index)}</text>`).join('')}</svg>`
}

const diagramNodeFromMatch = (match) => {
  const [, id, square, round, diamond] = match
  const rawLabel = square ?? round ?? diamond
  const label = rawLabel === undefined ? '' : (text(rawLabel.replace(/^['"]|['"]$/g, ''), id, 36) || id)
  const shape = rawLabel === undefined ? '' : diamond !== undefined ? 'diamond' : round !== undefined ? 'round' : 'rect'
  return { id, label, shape }
}

/** Parse the editable flowchart subset while leaving advanced Mermaid in source mode. */
export const parseMermaidDiagram = (source = '') => {
  const lines = String(source || '').split(/\r?\n/)
  const header = lines.find((line) => /^\s*(?:flowchart|graph)\s+(LR|RL|TB|TD|BT)\b/i.test(line)) || ''
  const directionRaw = String(header.match(/\b(LR|RL|TB|TD|BT)\b/i)?.[1] || 'LR').toUpperCase()
  const graph = { direction: directionRaw === 'TD' ? 'TB' : directionRaw, nodes: [], edges: [] }
  const nodesById = new Map()
  const rememberNode = (node) => {
    if (!node?.id || ['end', 'subgraph'].includes(node.id.toLowerCase())) return
    const previous = nodesById.get(node.id)
    nodesById.set(node.id, previous ? { ...previous, ...node, label: node.label || previous.label, shape: node.shape || previous.shape } : node)
  }
  const tokenPattern = /([A-Za-z][A-Za-z0-9_-]*)(?:\[([^\]]*)\]|\(([^()]*)\)|\{([^}]*)\})?/g

  lines.forEach((rawLine) => {
    const line = rawLine.trim()
    if (!line || /^(?:flowchart|graph)\s+/i.test(line) || /^(?:%%|subgraph\b|end\b|style\b|classDef\b|class\b|linkStyle\b|click\b)/i.test(line)) return
    const edgeLabels = [...line.matchAll(/\|([^|]*)\|/g)].map((match) => text(match[1], '', 24))
    const lineWithoutEdgeLabels = line.replace(/\|[^|]*\|/g, '|')
    const matches = [...lineWithoutEdgeLabels.matchAll(tokenPattern)]
    if (!matches.length) return
    matches.forEach((match) => rememberNode(diagramNodeFromMatch(match)))
    let edgeLabelIndex = 0
    for (let index = 0; index < matches.length - 1; index += 1) {
      const fromMatch = matches[index]
      const toMatch = matches[index + 1]
      const connector = lineWithoutEdgeLabels.slice(fromMatch.index + fromMatch[0].length, toMatch.index)
      const operator = connector.match(/<-->|<--|-->|==>|-\.->|---|--o|--x/)?.[0]
      if (!operator) continue
      const edgeLabel = connector.includes('|') ? (edgeLabels[edgeLabelIndex++] || '') : ''
      const reverse = operator === '<--'
      graph.edges.push({ from: reverse ? toMatch[1] : fromMatch[1], to: reverse ? fromMatch[1] : toMatch[1], label: text(edgeLabel, '', 24) })
    }
  })
  graph.nodes = [...nodesById.values()].slice(0, 12).map((node) => ({
    ...node,
    label: node.label || node.id,
    shape: node.shape || 'rect',
  }))
  const knownIds = new Set(graph.nodes.map((node) => node.id))
  graph.edges = graph.edges.filter((edge) => knownIds.has(edge.from) && knownIds.has(edge.to)).slice(0, 16)
  if (!graph.nodes.length) graph.nodes = [{ id: 'A', label: '开始', shape: 'round' }, { id: 'B', label: '探究', shape: 'rect' }]
  if (!graph.edges.length && graph.nodes.length > 1 && !String(source || '').trim()) graph.edges.push({ from: graph.nodes[0].id, to: graph.nodes[1].id, label: '' })
  return graph
}

export const diagramSvgMarkup = (source = '') => {
  const sourceText = String(source || '').trim()
  if (sourceText && !/^(?:flowchart|graph)\s+(?:LR|RL|TB|TD|BT)\b/i.test(sourceText)) {
    return '<span role="status">当前图类型暂不支持本地预览</span>'
  }
  const graph = parseMermaidDiagram(source)
  const nodeWidth = 108
  const nodeHeight = 42
  const rank = new Map(graph.nodes.map((node) => [node.id, 0]))
  for (let pass = 0; pass < graph.nodes.length; pass += 1) {
    let changed = false
    graph.edges.forEach((edge) => {
      const next = Math.min(graph.nodes.length - 1, (rank.get(edge.from) || 0) + 1)
      if ((rank.get(edge.to) || 0) < next) { rank.set(edge.to, next); changed = true }
    })
    if (!changed) break
  }
  const groups = new Map()
  graph.nodes.forEach((node) => {
    const level = rank.get(node.id) || 0
    groups.set(level, [...(groups.get(level) || []), node])
  })
  const levels = [...groups.keys()].sort((a, b) => a - b)
  const vertical = ['TB', 'BT'].includes(graph.direction)
  const largestRank = Math.max(1, ...[...groups.values()].map((group) => group.length))
  const width = vertical ? Math.max(280, largestRank * 142) : Math.max(360, levels.length * 148 + 64)
  const height = vertical ? Math.max(170, levels.length * 84 + 56) : Math.max(170, largestRank * 76 + 54)
  const positions = new Map()
  levels.forEach((level, levelIndex) => {
    const group = groups.get(level) || []
    group.forEach((node, index) => {
      let x = vertical ? ((index + 1) * width / (group.length + 1)) : 32 + levelIndex * (width - nodeWidth - 64) / Math.max(1, levels.length - 1)
      let y = vertical ? 26 + levelIndex * (height - nodeHeight - 52) / Math.max(1, levels.length - 1) : ((index + 1) * height / (group.length + 1))
      if (['RL', 'BT'].includes(graph.direction)) {
        if (vertical) y = height - y - nodeHeight
        else x = width - x - nodeWidth
      }
      positions.set(node.id, { x, y, cx: x + nodeWidth / 2, cy: y + nodeHeight / 2 })
    })
  })
  const lines = graph.edges.map((edge) => {
    const from = positions.get(edge.from)
    const to = positions.get(edge.to)
    if (!from || !to) return ''
    const midX = (from.cx + to.cx) / 2
    const midY = (from.cy + to.cy) / 2
    return `<g><path d="M${from.cx} ${from.cy} L${to.cx} ${to.cy}" marker-end="url(#a12-diagram-arrow)"/>${edge.label ? `<text class="edge-label" x="${midX}" y="${midY - 5}">${escapeHtml(edge.label)}</text>` : ''}</g>`
  }).join('')
  const nodes = graph.nodes.map((node) => {
    const point = positions.get(node.id)
    if (!point) return ''
    let shape
    if (node.shape === 'diamond') shape = `<polygon points="${point.cx},${point.y} ${point.x + nodeWidth},${point.cy} ${point.cx},${point.y + nodeHeight} ${point.x},${point.cy}"/>`
    else if (node.shape === 'round') shape = `<rect x="${point.x}" y="${point.y}" width="${nodeWidth}" height="${nodeHeight}" rx="21"/>`
    else shape = `<rect x="${point.x}" y="${point.y}" width="${nodeWidth}" height="${nodeHeight}" rx="7"/>`
    return `<g class="diagram-node">${shape}<text x="${point.cx}" y="${point.cy + 4}">${escapeHtml(node.label)}</text></g>`
  }).join('')
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="流程图实时预览" xmlns="http://www.w3.org/2000/svg"><defs><marker id="a12-diagram-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z"/></marker></defs><g class="diagram-edges">${lines}</g>${nodes}</svg>`
}

const chartPalette = ['#3b82f6', '#14b8a6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#84cc16', '#f97316']

const chartSvgMarkup = (option) => {
  const rows = chartRows(option)
  const source = plainObject(option) ? option : {}
  const series = Array.isArray(source.series) ? source.series[0] : source.series
  const xAxis = Array.isArray(source.xAxis) ? source.xAxis[0] : source.xAxis
  const yAxis = Array.isArray(source.yAxis) ? source.yAxis[0] : source.yAxis
  const xAxisName = text(xAxis?.name, '', 72)
  const yAxisName = text(yAxis?.name, '', 72)
  const chartType = ['line', 'pie'].includes(series?.type) ? series.type : 'bar'
  if (chartType === 'pie') {
    const total = rows.reduce((sum, row) => sum + Math.max(0, row.value), 0) || 1
    const radius = 42
    const circumference = 2 * Math.PI * radius
    let offset = 0
    const slices = rows.map((row, index) => {
      const length = circumference * Math.max(0, row.value) / total
      const slice = `<circle cx="76" cy="72" r="${radius}" fill="none" stroke="${chartPalette[index % chartPalette.length]}" stroke-width="28" stroke-dasharray="${length} ${circumference - length}" stroke-dashoffset="${-offset}" transform="rotate(-90 76 72)"/>`
      offset += length
      return slice
    }).join('')
    return `<svg class="a12-subject-tool__chart-svg" viewBox="0 0 152 144" role="img" aria-label="饼图数据预览"><circle cx="76" cy="72" r="${radius}" fill="none" stroke="#e8eef7" stroke-width="28"/>${slices}</svg><div class="a12-subject-tool__chart-legend">${rows.map((row, index) => `<span><i style="background:${chartPalette[index % chartPalette.length]}"></i>${escapeHtml(row.label)}</span>`).join('')}</div>`
  }

  const width = 320
  const height = 168
  const left = 20
  const right = 8
  const top = 22
  const plotHeight = 100
  const plotWidth = width - left - right
  const values = rows.map((row) => row.value)
  const minValue = Math.min(0, ...values)
  const maxValue = Math.max(1, ...values)
  const valueSpan = maxValue - minValue || 1
  const baseline = top + maxValue / valueSpan * plotHeight
  const xAt = (index) => left + plotWidth * (index + 0.5) / rows.length
  const yAt = (value) => top + (maxValue - value) / valueSpan * plotHeight
  const functionGraph = Boolean(source.a12_function_graph) && chartType === 'line'
  const numericXs = rows.map((row) => Number(row.label))
  const zeroIndex = numericXs.findIndex((value) => value >= 0)
  const zeroX = zeroIndex > 0 && numericXs[zeroIndex] !== numericXs[zeroIndex - 1]
    ? xAt(zeroIndex - 1) + (xAt(zeroIndex) - xAt(zeroIndex - 1)) * -numericXs[zeroIndex - 1] / (numericXs[zeroIndex] - numericXs[zeroIndex - 1])
    : left
  let seriesMarkup = ''
  if (chartType === 'line') {
    const points = rows.map((row, index) => `${xAt(index)},${yAt(row.value)}`).join(' ')
    seriesMarkup = `<polyline points="${points}" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${rows.map((row, index) => `<circle cx="${xAt(index)}" cy="${yAt(row.value)}" r="3.5" fill="#ffffff" stroke="#3b82f6" stroke-width="2"/>`).join('')}`
  } else {
    const barWidth = Math.max(7, Math.min(30, plotWidth / rows.length * 0.52))
    seriesMarkup = rows.map((row, index) => {
      const valueY = yAt(row.value)
      const barY = Math.min(valueY, baseline)
      const barHeight = Math.max(2, Math.abs(baseline - valueY))
      return `<rect x="${xAt(index) - barWidth / 2}" y="${barY}" width="${barWidth}" height="${barHeight}" rx="3" fill="${chartPalette[index % chartPalette.length]}"/>`
    }).join('')
  }
  const labels = rows.filter((row, index) => !functionGraph || Number(row.label) === 0 || index % Math.ceil(rows.length / 6) === 0 || index === rows.length - 1)
    .map((row) => `<text x="${xAt(rows.indexOf(row))}" y="132" text-anchor="middle">${escapeHtml(row.label.slice(0, 10))}</text>`).join('')
  const axisNames = `${yAxisName ? `<text x="${left}" y="14">${escapeHtml(yAxisName)}</text>` : ''}${xAxisName ? `<text x="${width / 2}" y="158" text-anchor="middle">${escapeHtml(xAxisName)}</text>` : ''}`
  const axes = functionGraph
    ? `<path d="M${left} ${baseline}H${width - right}M${zeroX} ${top}V${top + plotHeight}"/>`
    : `<path d="M${left} ${top}V${top + plotHeight}H${width - right}"/>`
  return `<svg class="a12-subject-tool__chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${functionGraph ? '函数坐标图' : chartType === 'line' ? '折线图' : '柱状图'}数据预览">${axes}<path class="a12-subject-tool__chart-data" d=""/>${axisNames}${seriesMarkup}${labels}</svg>`
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
  if (type === 'chinese_tianzige') {
    const entries = state.entries.length ? state.entries : [{ character: '', pinyin: '' }]
    const cells = entries.map(({ character, pinyin }) => `<span class="a12-tianzige-item${state.show_pinyin ? '' : ' a12-tianzige-item--no-pinyin'}">${state.show_pinyin ? `<span class="a12-tianzige-pinyin">${escapeHtml(pinyin) || '&nbsp;'}</span>` : ''}<span class="a12-tianzige-cell"><span class="a12-tianzige-character">${escapeHtml(character) || '&nbsp;'}</span></span></span>`).join('')
    return withContext(`<div class="a12-subject-tool__tianzige" aria-label="语文田字格${state.show_pinyin ? '和拼音' : ''}">${cells}</div>`)
  }
  if (type === 'english_four_line') {
    const rows = state.text.split('\n').map((line) => `<span class="a12-fourline-row"><span class="a12-fourline-text">${escapeHtml(line) || '&nbsp;'}</span></span>`).join('')
    return withContext(`<div class="a12-subject-tool__fourline" aria-label="英语四线格">${rows}</div>`)
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
    return withContext(`<div class="a12-subject-tool__chemical" aria-label="化学式"><span>${chemicalFormulaMarkup(state.formula)}</span></div>`)
  }
  if (type === 'mermaid_diagram') {
    return withContext(`<div class="a12-subject-tool__diagram" aria-label="流程关系图">${diagramSvgMarkup(state.mermaid)}</div>`)
  }
  if (type === 'chart') {
    const chartTitle = text(state.option?.title?.text, '', 72)
    const chartTitleMarkup = chartTitle ? `<strong class="a12-subject-tool__chart-title">${escapeHtml(chartTitle)}</strong>` : ''
    return withContext(`<div class="a12-subject-tool__chart-area">${chartTitleMarkup}${chartSvgMarkup(state.option)}</div>`)
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
  .a12-subject-tool__chemical sup{font-size:.58em}
  .a12-subject-tool__chemical{overflow:auto}
  .a12-subject-tool__chemical:not(.a12-subject-tool__chemical--structure)>span{display:inline-block;padding:.24em .6em .38em;max-width:none}
  .a12-subject-tool__chemical .a12-chem-atom{position:relative;display:inline-block;vertical-align:baseline;line-height:1;white-space:nowrap}
  .a12-subject-tool__chemical .a12-chem-atom__symbol{display:inline-block}
  .a12-subject-tool__chemical .a12-chem-atom--valence{padding-top:.62em}
  .a12-subject-tool__chemical .a12-chem-atom__valence{position:absolute;top:0;left:50%;transform:translateX(-50%);font-size:.5em;line-height:1}
  .a12-subject-tool__chemical .a12-chem-atom--electrons{margin:0 .32em;padding-top:.44em;padding-bottom:.34em}
  .a12-subject-tool__chemical .a12-chem-atom--valence.a12-chem-atom--electrons{padding-top:1em}
  .a12-subject-tool__chemical .a12-chem-atom__electron{position:absolute;font-size:.34em;line-height:1;letter-spacing:-.14em}
  .a12-subject-tool__chemical .a12-chem-atom__electron--top{top:0;left:50%;transform:translateX(-50%)}
  .a12-subject-tool__chemical .a12-chem-atom--valence .a12-chem-atom__electron--top{top:.62em}
  .a12-subject-tool__chemical .a12-chem-atom__electron--right{top:50%;right:-.66em;transform:translateY(-50%)}
  .a12-subject-tool__chemical .a12-chem-atom__electron--bottom{bottom:0;left:50%;transform:translateX(-50%)}
  .a12-subject-tool__chemical .a12-chem-atom__electron--left{top:50%;left:-.66em;transform:translateY(-50%)}
  .a12-subject-tool__chemical .a12-chem-operator{display:inline-block;margin:0 .22em}
  .a12-subject-tool__chemical .a12-chem-arrow{display:inline-block;margin:0 .3em}
  .a12-subject-tool__tianzige{display:flex;flex-wrap:wrap;align-content:flex-start;justify-content:center;column-gap:.08em;row-gap:.22em;min-width:0;min-height:0;overflow:auto;padding:.08em;font-size:1em}
  .a12-tianzige-item{display:grid;grid-template-rows:.82em 2.16em;justify-items:center;flex:none;width:2.16em;min-width:0}
  .a12-tianzige-item--no-pinyin{grid-template-rows:2.16em}
  .a12-tianzige-pinyin{max-width:100%;overflow:hidden;align-self:end;color:inherit;font-size:.61em;font-weight:500;line-height:1.2;text-align:center;text-overflow:ellipsis;white-space:nowrap}
  .a12-tianzige-cell{position:relative;display:grid;place-items:center;width:2.16em;height:2.16em;overflow:hidden;border:1px solid #d78f97;background:rgb(255 255 255 / 55%)}
  .a12-tianzige-cell::before,.a12-tianzige-cell::after{position:absolute;z-index:0;content:"";pointer-events:none}
  .a12-tianzige-cell::before{top:0;bottom:0;left:50%;border-left:1px dashed #e9aeb4}
  .a12-tianzige-cell::after{top:50%;right:0;left:0;border-top:1px dashed #e9aeb4}
  .a12-tianzige-character{position:relative;z-index:1;color:inherit;font:400 1.66em/1 "KaiTi","STKaiti","SimKai","Microsoft YaHei",sans-serif;white-space:nowrap}
  .a12-subject-tool__fourline{display:flex;flex-direction:column;align-items:stretch;gap:.28em;min-width:0;min-height:0;overflow:auto;padding:.08em .02em;font-size:1em}
  .a12-fourline-row{position:relative;display:flex;align-items:flex-start;flex:none;width:max-content;min-width:100%;height:2.25em;border-top:1px solid #a7b9d5;border-bottom:1px solid #a7b9d5}
  .a12-fourline-row::before,.a12-fourline-row::after{position:absolute;right:0;left:0;border-top:1px dashed #b4c5df;content:"";pointer-events:none}
  .a12-fourline-row::before{top:33.333%}.a12-fourline-row::after{top:66.666%}
  .a12-fourline-text{position:relative;z-index:1;top:-.11em;display:inline-block;min-width:100%;padding:0 .18em;color:inherit;font:400 2em/1 "Comic Sans MS",Arial,sans-serif;letter-spacing:.015em;white-space:pre}
  .a12-subject-tool__diagram svg{display:block;width:100%;height:auto;max-height:100%;overflow:visible}.a12-subject-tool__diagram .diagram-edges path{fill:none;stroke:#8aa2c1;stroke-width:2}.a12-subject-tool__diagram marker path{fill:#8aa2c1}.a12-subject-tool__diagram .diagram-node rect,.a12-subject-tool__diagram .diagram-node polygon{fill:#eff6ff;stroke:#93b9ec;stroke-width:1.5}.a12-subject-tool__diagram .diagram-node text{fill:#24558d;font-size:12px;text-anchor:middle;font-family:"Microsoft YaHei",Arial,sans-serif}.a12-subject-tool__diagram .edge-label{fill:#607491;font-size:10px;text-anchor:middle;font-family:"Microsoft YaHei",Arial,sans-serif}
  .a12-subject-tool__chart-area{align-items:center;justify-content:center;overflow:hidden}.a12-subject-tool__chart-svg{display:block;flex:1;min-width:0;min-height:0;width:100%;height:100%;max-height:100%;overflow:visible}.a12-subject-tool__chart-svg>path:first-child{fill:none;stroke:rgb(96 116 145 / 35%);stroke-width:1}.a12-subject-tool__chart-svg text{fill:#607491;font-size:9px;font-family:"Microsoft YaHei",Arial,sans-serif}.a12-subject-tool__chart-legend{display:flex;flex-wrap:wrap;justify-content:center;gap:3px 8px;width:100%;max-height:2.6em;overflow:hidden;color:#607491;font-size:.38em}.a12-subject-tool__chart-legend span{display:inline-flex;align-items:center;gap:3px;white-space:nowrap}.a12-subject-tool__chart-legend i{display:inline-block;width:6px;height:6px;border-radius:2px}
  .a12-subject-tool__geometry path{fill:rgb(37 99 235 / 5%);stroke:#2563eb;stroke-width:2}
`
