<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { MathfieldElement } from 'mathlive'
import 'mathlive/fonts.css'

const props = defineProps({
  modelValue: { type: String, default: '' },
  displayMode: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

const formulaInput = ref(null)
const mathfieldHost = ref(null)
const formulaMode = ref('visual')
const lastSelection = ref(null)
const insertError = ref('')
let mathfield = null
let lastVisualEmitted = null

const makeSymbolItems = (entries) => entries.map(([label, title, insert, selection]) => ({ label, title, insert, selection }))
const formulaToolGroups = [
  {
    id: 'digits',
    label: '数字 0–9',
    items: Array.from({ length: 10 }, (_, index) => {
      const value = String(index)
      return { label: value, title: `数字 ${value}`, insert: value }
    }),
  },
  {
    id: 'indices',
    label: '上下标',
    items: [
      { label: 'x²', title: '平方上标', insert: '^{2}' },
      { label: 'xⁿ', title: '通用上标', insert: '^{n}', selection: [2, 3] },
      { label: 'x₂', title: '数字下标', insert: '_{2}' },
      { label: 'xₙ', title: '通用下标', insert: '_{n}', selection: [2, 3] },
    ],
  },
  {
    id: 'structures',
    label: '公式结构',
    items: [
      { label: '分数', title: '分数', insert: '\\frac{}{}', selection: [6, 6] },
      { label: '组合数', title: '组合数', insert: '\\binom{}{}', selection: [7, 7] },
      { label: '√', title: '平方根', insert: '\\sqrt{}', selection: [6, 6] },
      { label: '括号', title: '可伸缩括号', insert: '\\left(\\right)', selection: [6, 6] },
      { label: '|x|', title: '绝对值', insert: '\\left|\\right|', selection: [6, 6] },
      { label: '‖x‖', title: '范数', insert: '\\left\\|\\right\\|', selection: [7, 7] },
      { label: '矩阵', title: '二阶方阵', insert: '\\begin{bmatrix}a & b \\\\ c & d\\end{bmatrix}', selection: [15, 16] },
    ],
  },
  {
    id: 'notation',
    label: '角标与修饰',
    items: [
      { label: 'x̂', title: '帽子记号', insert: '\\hat{}', selection: [5, 5] },
      { label: 'x̄', title: '上划线', insert: '\\bar{}', selection: [5, 5] },
      { label: 'x̃', title: '波浪线', insert: '\\tilde{}', selection: [7, 7] },
      { label: 'x⃗', title: '向量箭头', insert: '\\vec{}', selection: [5, 5] },
      { label: 'ẋ', title: '一点导数', insert: '\\dot{}', selection: [5, 5] },
      { label: 'ẍ', title: '两点导数', insert: '\\ddot{}', selection: [6, 6] },
      { label: 'x̅', title: '长上划线', insert: '\\overline{}', selection: [10, 10] },
    ],
  },
  {
    id: 'functions',
    label: '常用函数',
    items: makeSymbolItems([
      ['sin', '正弦函数', '\\sin'], ['cos', '余弦函数', '\\cos'], ['tan', '正切函数', '\\tan'],
      ['cot', '余切函数', '\\cot'], ['sec', '正割函数', '\\sec'], ['csc', '余割函数', '\\csc'],
      ['ln', '自然对数', '\\ln'], ['log', '对数函数', '\\log'], ['exp', '指数函数', '\\exp'],
      ['min', '最小值', '\\min'], ['max', '最大值', '\\max'], ['lim', '极限', '\\lim'],
    ]),
  },
  {
    id: 'calculus',
    label: '微积分',
    items: [
      { label: '∫', title: '定积分', insert: '\\int_{a}^{b}', selection: [6, 7] },
      { label: '∮', title: '闭合曲线积分', insert: '\\oint' },
      { label: '∬', title: '二重积分', insert: '\\iint' },
      { label: '∭', title: '三重积分', insert: '\\iiint' },
      { label: '∑', title: '求和', insert: '\\sum_{i=1}^{n}', selection: [6, 9] },
      { label: '∏', title: '连乘', insert: '\\prod' },
      { label: 'd/dx', title: '导数', insert: '\\frac{dy}{dx}', selection: [11, 12] },
      { label: '∂', title: '偏导数', insert: '\\frac{\\partial f}{\\partial x}', selection: [15, 16] },
      { label: 'lim', title: '极限', insert: '\\lim_{x\\to 0}', selection: [6, 12] },
      { label: '∇', title: '梯度或 Nabla 算子', insert: '\\nabla' },
    ],
  },
  {
    id: 'arithmetic',
    label: '四则与常用运算',
    items: makeSymbolItems([
      ['+', '加号', '+'], ['−', '减号', '-'], ['×', '乘号', '\\times'], ['÷', '除号', '\\div'],
      ['·', '点乘', '\\cdot'], ['±', '正负号', '\\pm'], ['∓', '负正号', '\\mp'],
      ['√', '平方根', '\\sqrt{}', [6, 6]], ['∛', '立方根', '\\sqrt[3]{}', [9, 9]], ['!', '阶乘', '!'], ['%', '百分号', '\\%'],
    ]),
  },
  {
    id: 'relations',
    label: '比较与关系',
    items: makeSymbolItems([
      ['=', '等于', '='], ['≠', '不等于', '\\ne'], ['<', '小于', '\\lt'], ['>', '大于', '\\gt'],
      ['≤', '小于等于', '\\le'], ['≥', '大于等于', '\\ge'], ['≈', '约等于', '\\approx'],
      ['≡', '恒等于', '\\equiv'], ['∝', '正比于', '\\propto'], ['∼', '相似或渐近于', '\\sim'],
      ['≅', '全等或约同', '\\cong'], ['≪', '远小于', '\\ll'], ['≫', '远大于', '\\gg'],
    ]),
  },
  {
    id: 'greek',
    label: '希腊字母',
    items: makeSymbolItems([
      ['α', 'alpha', '\\alpha'], ['β', 'beta', '\\beta'], ['γ', 'gamma', '\\gamma'], ['δ', 'delta', '\\delta'],
      ['ε', 'epsilon', '\\epsilon'], ['ζ', 'zeta', '\\zeta'], ['η', 'eta', '\\eta'], ['θ', 'theta', '\\theta'],
      ['ι', 'iota', '\\iota'], ['κ', 'kappa', '\\kappa'], ['λ', 'lambda', '\\lambda'], ['μ', 'mu', '\\mu'],
      ['ν', 'nu', '\\nu'], ['ξ', 'xi', '\\xi'], ['ο', 'omicron', 'o'], ['π', 'pi', '\\pi'],
      ['ρ', 'rho', '\\rho'], ['σ', 'sigma', '\\sigma'], ['τ', 'tau', '\\tau'], ['υ', 'upsilon', '\\upsilon'],
      ['φ', 'phi', '\\phi'], ['χ', 'chi', '\\chi'], ['ψ', 'psi', '\\psi'], ['ω', 'omega', '\\omega'],
      ['Γ', '大写 Gamma', '\\Gamma'], ['Δ', '大写 Delta', '\\Delta'], ['Θ', '大写 Theta', '\\Theta'],
      ['Λ', '大写 Lambda', '\\Lambda'], ['Ξ', '大写 Xi', '\\Xi'], ['Π', '大写 Pi', '\\Pi'],
      ['Σ', '大写 Sigma', '\\Sigma'], ['Φ', '大写 Phi', '\\Phi'], ['Ψ', '大写 Psi', '\\Psi'], ['Ω', '大写 Omega', '\\Omega'],
    ]),
  },
  {
    id: 'sets',
    label: '集合与逻辑',
    items: makeSymbolItems([
      ['∈', '属于', '\\in'], ['∉', '不属于', '\\notin'], ['∋', '包含元素', '\\ni'], ['∅', '空集', '\\emptyset'],
      ['ℕ', '自然数集', '\\mathbb{N}'], ['ℤ', '整数集', '\\mathbb{Z}'], ['ℚ', '有理数集', '\\mathbb{Q}'],
      ['ℝ', '实数集', '\\mathbb{R}'], ['ℂ', '复数集', '\\mathbb{C}'],
      ['⊂', '真子集', '\\subset'], ['⊆', '子集或等于', '\\subseteq'], ['⊃', '真超集', '\\supset'],
      ['⊇', '超集或等于', '\\supseteq'], ['∪', '并集', '\\cup'], ['∩', '交集', '\\cap'], ['∖', '集合差', '\\setminus'],
      ['∀', '任意', '\\forall'], ['∃', '存在', '\\exists'], ['∧', '逻辑与', '\\land'], ['∨', '逻辑或', '\\lor'],
      ['¬', '逻辑非', '\\neg'], ['⇒', '推出', '\\Rightarrow'], ['⇔', '当且仅当', '\\Leftrightarrow'],
    ]),
  },
  {
    id: 'arrows',
    label: '箭头',
    items: makeSymbolItems([
      ['←', '左箭头', '\\leftarrow'], ['→', '右箭头', '\\rightarrow'], ['↔', '双向箭头', '\\leftrightarrow'],
      ['⇐', '左双箭头', '\\Leftarrow'], ['⇒', '右双箭头', '\\Rightarrow'], ['⇔', '双向双箭头', '\\Leftrightarrow'],
      ['↦', '映射到', '\\mapsto'], ['↑', '上箭头', '\\uparrow'], ['↓', '下箭头', '\\downarrow'],
    ]),
  },
  {
    id: 'common',
    label: '常用符号',
    items: makeSymbolItems([
      ['π', '圆周率', '\\pi'], ['e', '自然常数', 'e'], ['i', '虚数单位', 'i'], ['∞', '无穷大', '\\infty'],
      ['°', '角度', '^\\circ'], ['∠', '角', '\\angle'], ['⊥', '垂直', '\\perp'], ['∥', '平行', '\\parallel'],
      ['∴', '所以', '\\therefore'], ['∵', '因为', '\\because'], ['…', '省略号', '\\ldots'],
    ]),
  },
]

const FORMULA_HISTORY_KEY = 'a12-subject-formula-recent-v1'
const formulaItemKey = (item) => String(item?.insert || '')
const normalizeFormulaHistoryItem = (item) => {
  if (!item || typeof item !== 'object') return null
  const label = String(item.label || '').slice(0, 32)
  const title = String(item.title || '').slice(0, 80)
  const insert = String(item.insert || '').slice(0, 128)
  if (!label || !title || !insert) return null
  const selection = Array.isArray(item.selection) && item.selection.length === 2
    ? item.selection.map(Number)
    : null
  const validSelection = selection?.every((value) => Number.isInteger(value) && value >= 0 && value <= insert.length)
    ? selection
    : null
  return { label, title, insert, ...(validSelection ? { selection: validSelection } : {}) }
}
const loadFormulaHistory = () => {
  try {
    if (typeof window === 'undefined') return []
    const stored = JSON.parse(window.localStorage.getItem(FORMULA_HISTORY_KEY) || '[]')
    if (!Array.isArray(stored)) return []
    const seen = new Set()
    return stored
      .map(normalizeFormulaHistoryItem)
      .filter((item) => {
        if (!item) return false
        const key = formulaItemKey(item)
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      .slice(0, 20)
  } catch {
    return []
  }
}
const recentFormulaItems = ref(loadFormulaHistory())
const visibleFormulaToolGroups = computed(() => [
  { id: 'recent', label: '最近使用', items: recentFormulaItems.value },
  ...formulaToolGroups,
])
const expandedFormulaGroups = ref(new Set(['digits', 'common', 'recent']))
const isFormulaGroupExpanded = (id) => expandedFormulaGroups.value.has(id)
const toggleFormulaGroup = (id) => {
  const next = new Set(expandedFormulaGroups.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedFormulaGroups.value = next
}
const rememberFormulaItem = (item) => {
  const normalized = normalizeFormulaHistoryItem(item)
  if (!normalized) return
  recentFormulaItems.value = [
    normalized,
    ...recentFormulaItems.value.filter((candidate) => formulaItemKey(candidate) !== formulaItemKey(normalized)),
  ].slice(0, 20)
  if (!expandedFormulaGroups.value.has('recent')) {
    expandedFormulaGroups.value = new Set([...expandedFormulaGroups.value, 'recent'])
  }
  try {
    window.localStorage.setItem(FORMULA_HISTORY_KEY, JSON.stringify(recentFormulaItems.value))
  } catch {
    // Keep the in-memory history usable when browser storage is unavailable.
  }
}

const formulaError = computed(() => {
  const latex = String(props.modelValue || '').trim()
  if (!latex) return ''

  try {
    katex.renderToString(latex, { displayMode: props.displayMode, throwOnError: true, output: 'html' })
    return ''
  } catch (error) {
    return error?.message || 'LaTeX 语法错误'
  }
})

const getMathfieldLatex = () => mathfield?.getValue('latex-without-placeholders') || ''
const updateVisualFormula = () => {
  if (!mathfield) return
  const latex = getMathfieldLatex()
  if (latex.length > 2000) {
    insertError.value = '公式最多 2,000 个字符，无法继续输入。'
    mathfield.setValue(String(props.modelValue || ''), { silenceNotifications: true })
    return
  }
  insertError.value = ''
  if (latex === String(props.modelValue || '') || latex === lastVisualEmitted) return
  lastVisualEmitted = latex
  emit('update:modelValue', latex)
}

onMounted(() => {
  const field = new MathfieldElement()
  field.setAttribute('aria-label', '数学公式，可直接编辑')
  field.mathVirtualKeyboardPolicy = 'manual'
  mathfieldHost.value?.appendChild(field)
  mathfield = field
  field.setValue(String(props.modelValue || ''), { silenceNotifications: true })
  field.addEventListener('input', updateVisualFormula)
})
watch(() => props.modelValue, (value) => {
  const latex = String(value || '')
  lastVisualEmitted = null
  if (mathfield && getMathfieldLatex() !== latex) {
    mathfield.setValue(latex, { silenceNotifications: true })
  }
})
onBeforeUnmount(() => {
  mathfield?.removeEventListener('input', updateVisualFormula)
  mathfield?.remove()
  mathfield = null
})

const getTextarea = () => formulaInput.value?.$el?.querySelector('textarea') || null
const updateFormula = (value) => {
  insertError.value = ''
  emit('update:modelValue', value)
}
const captureSelection = () => {
  const textarea = getTextarea()
  if (!textarea) return
  lastSelection.value = { start: textarea.selectionStart, end: textarea.selectionEnd }
}

const insertFormula = async (item) => {
  if (formulaMode.value === 'visual') {
    if (!mathfield) return
    const before = getMathfieldLatex()
    const inserted = mathfield.insert(item.insert, {
      format: 'latex',
      selectionMode: 'placeholder',
      focus: true,
    })
    const after = getMathfieldLatex()
    if (after.length > 2000) {
      mathfield.setValue(before, { silenceNotifications: true })
      insertError.value = '公式最多 2,000 个字符，无法插入此内容。'
      return
    }
    if (inserted && after !== before) {
      updateVisualFormula()
      rememberFormulaItem(item)
    }
    return
  }

  const current = String(props.modelValue || '')
  const textarea = getTextarea()
  const focused = textarea && document.activeElement === textarea
  const selection = focused
    ? { start: textarea.selectionStart, end: textarea.selectionEnd }
    : (lastSelection.value || { start: current.length, end: current.length })
  const start = Math.min(selection.start, current.length)
  const end = Math.min(Math.max(selection.end, start), current.length)
  const left = current.slice(0, start)
  const right = current.slice(end)
  const prefix = /\\[A-Za-z]+$/.test(left) && /^[A-Za-z]/.test(item.insert) ? ' ' : ''
  const suffix = /\\[A-Za-z]+$/.test(item.insert) && /^[A-Za-z]/.test(right) ? ' ' : ''
  const next = `${left}${prefix}${item.insert}${suffix}${right}`

  if (next.length > 2000) {
    insertError.value = '公式最多 2,000 个字符，无法插入此内容。'
    return
  }

  insertError.value = ''
  rememberFormulaItem(item)
  emit('update:modelValue', next)
  await nextTick()

  const nextTextarea = getTextarea()
  if (!nextTextarea) return
  nextTextarea.focus()
  const selectionStart = item.selection
    ? prefix.length + item.selection[0]
    : prefix.length + item.insert.length + suffix.length
  const selectionEnd = item.selection ? prefix.length + item.selection[1] : selectionStart
  nextTextarea.setSelectionRange(start + selectionStart, start + selectionEnd)
  lastSelection.value = { start: start + selectionStart, end: start + selectionEnd }
}
</script>

<template>
  <div class="subject-formula-editor">
    <div class="formula-mode-tabs" role="tablist" aria-label="公式编辑模式">
      <button type="button" role="tab" :aria-selected="formulaMode === 'visual'" :class="{ active: formulaMode === 'visual' }" @click="formulaMode = 'visual'">可视化编辑</button>
      <button type="button" role="tab" :aria-selected="formulaMode === 'source'" :class="{ active: formulaMode === 'source' }" @click="formulaMode = 'source'">LaTeX 代码</button>
    </div>

    <div class="formula-toolbox" aria-label="常用公式元素">
        <section v-for="group in visibleFormulaToolGroups" :key="group.id" class="formula-tool-group">
          <button
            type="button"
            class="formula-group-toggle"
            :aria-expanded="isFormulaGroupExpanded(group.id)"
            :aria-controls="`formula-group-${group.id}`"
            @click="toggleFormulaGroup(group.id)"
          >
            <span>{{ group.label }}</span>
            <span class="formula-group-meta"><small>{{ group.items.length }}</small><i :class="{ expanded: isFormulaGroupExpanded(group.id) }" aria-hidden="true">⌄</i></span>
          </button>
          <div :id="`formula-group-${group.id}`" v-show="isFormulaGroupExpanded(group.id)" class="formula-group-items">
            <span v-if="group.id === 'recent' && !group.items.length" class="formula-history-empty">暂无记录，点击下方符号后会显示在这里</span>
            <button
              v-for="item in group.items"
              :key="item.label"
              type="button"
              class="formula-tool-button"
              :title="`${item.title}：点击插入`"
              :aria-label="`${item.title}，点击插入`"
              @mousedown.prevent="captureSelection"
              @click="insertFormula(item)"
            >{{ item.label }}</button>
          </div>
        </section>
    </div>

    <div v-show="formulaMode === 'visual'" class="formula-visual-panel" :class="{ 'is-inline': !displayMode }">
      <div ref="mathfieldHost" class="formula-visual-host"></div>
      <div class="formula-visual-footer">
        <span>点击公式即可编辑，也可使用上方符号</span>
        <span>{{ String(modelValue || '').length }} / 2000</span>
      </div>
    </div>
    <el-input
        v-if="formulaMode === 'source'"
        ref="formulaInput"
        :model-value="modelValue"
        type="textarea"
        :rows="4"
        maxlength="2000"
        show-word-limit
        aria-label="数学公式 LaTeX 代码"
        placeholder="输入 LaTeX 公式，例如：E=mc^2 或 \\frac{a}{b}"
        @update:model-value="updateFormula"
        @click="captureSelection"
        @keyup="captureSelection"
        @select="captureSelection"
        @blur="captureSelection"
      />
    <p v-if="insertError" class="formula-editor-error" role="alert">{{ insertError }}</p>
    <p v-if="formulaError" class="formula-editor-error" role="status">{{ formulaMode === 'source' ? `LaTeX 语法错误：${formulaError}` : '公式尚未完整，请继续补全。' }}</p>
  </div>
</template>

<style scoped>
.subject-formula-editor { display: grid; gap: 9px; }
.formula-mode-tabs { display: inline-flex; justify-self: start; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.formula-mode-tabs button { padding: 5px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; font-size: 10px; cursor: pointer; }
.formula-mode-tabs button:hover, .formula-mode-tabs button:focus-visible { color: var(--zh-text-theme); outline: none; }
.formula-mode-tabs button.active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: 0 1px 3px rgb(15 23 42 / 10%); font-weight: 700; }
.formula-toolbox { display: grid; gap: 5px; max-height: 280px; padding: 7px; overflow-y: auto; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.formula-tool-group { display: grid; gap: 4px; min-width: 0; }
.formula-group-toggle { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; padding: 5px 7px; border: 1px solid transparent; border-radius: 6px; color: var(--zh-text-secondary); background: transparent; font-size: 10px; font-weight: 600; text-align: left; cursor: pointer; }
.formula-group-toggle:hover, .formula-group-toggle:focus-visible { border-color: var(--zh-line-border); color: var(--zh-text-theme); background: var(--zh-background-primary); outline: none; }
.formula-group-meta { display: inline-flex; align-items: center; gap: 6px; color: var(--zh-text-caption); }
.formula-group-meta small { font-size: 9px; font-weight: 400; }
.formula-group-meta i { display: inline-block; font-size: 14px; font-style: normal; line-height: 1; transition: transform 140ms ease; }
.formula-group-meta i.expanded { transform: rotate(180deg); }
.formula-group-items { display: flex; flex-wrap: wrap; gap: 4px; padding: 1px 4px 3px; }
.formula-history-empty { padding: 5px 4px; color: var(--zh-text-caption); font-size: 9px; }
.formula-tool-button { min-width: 29px; min-height: 27px; padding: 4px 7px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font: 11px var(--zh-font-number); cursor: pointer; }
.formula-tool-button:hover, .formula-tool-button:focus-visible { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.formula-editor-error { margin: 0; color: var(--el-color-danger); font-size: 10px; line-height: 1.5; }
.formula-visual-panel { min-width: 0; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: 8px; color: var(--zh-text-primary); background: var(--zh-background-primary); }
.formula-visual-panel:focus-within { border-color: var(--zh-line-theme); }
.formula-visual-host { min-width: 0; }
.formula-visual-panel :deep(math-field) { display: block; width: 100%; min-height: 110px; padding: 17px; border: 0; outline: none; color: inherit; background: transparent; font-size: 22px; cursor: text; }
.formula-visual-panel :deep(math-field::part(virtual-keyboard-toggle)) { display: none; }
.formula-visual-panel :deep(math-field::part(menu-toggle)) { display: none; }
.formula-visual-footer { display: flex; justify-content: space-between; gap: 10px; padding: 0 10px 8px; color: var(--zh-text-caption); font-size: 10px; }
.formula-visual-footer span:last-child { flex: none; }
</style>
