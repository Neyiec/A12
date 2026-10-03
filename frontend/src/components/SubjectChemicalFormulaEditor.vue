<script setup>
import { computed, nextTick, ref } from 'vue'
import { chemicalElementSymbols, chemicalFormulaError, chemicalFormulaMarkup } from '../utils/subjectTool'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

const editor = ref(null)
const lastSelection = ref(null)
const insertError = ref('')
const commonAtoms = ['H', 'C', 'N', 'O', 'P', 'S', 'Na', 'Mg', 'Al', 'Cl', 'K', 'Ca', 'Fe', 'Cu', 'Zn', 'Br', 'Ag', 'I']
const allAtoms = chemicalElementSymbols
const atomItem = (symbol) => ({ label: symbol, title: '元素 ' + symbol, insert: symbol })
const toolGroups = [
  { id: 'digits', label: '数字 0–9', items: Array.from({ length: 10 }, (_, index) => ({ label: String(index), title: '数字 ' + index, insert: String(index) })) },
  { id: 'common', label: '常见元素', items: commonAtoms.map(atomItem) },
  { id: 'scripts', label: '下标、上标与离子电荷', items: [
    { label: 'x₂', title: '显式下标，选中待修改的数字', insert: '_{2}', selection: [2, 3], wrapSelection: ['_{', '}'] },
    { label: 'xₙ', title: '字母下标，选中待修改的字母', insert: '_{n}', selection: [2, 3], wrapSelection: ['_{', '}'] },
    { label: 'x²', title: '显式上标，选中待修改的数字', insert: '^{2}', selection: [2, 3], wrapSelection: ['^{', '}'] },
    { label: 'xⁿ', title: '字母上标，选中待修改的字母', insert: '^{n}', selection: [2, 3], wrapSelection: ['^{', '}'] },
    { label: '⁺', title: '一价正离子电荷，标在右上角', insert: '^+', annotateSelection: true },
    { label: '⁻', title: '一价负离子电荷，标在右上角', insert: '^-', annotateSelection: true },
    { label: '²⁺', title: '多价正离子电荷，选中电荷数', insert: '^2+', selection: [1, 2], annotateSelection: true },
    { label: '²⁻', title: '多价负离子电荷，选中电荷数', insert: '^2-', selection: [1, 2], annotateSelection: true },
  ] },
  { id: 'structure', label: '括号与结晶水', items: [
    { label: '( )', title: '圆括号，光标停在中间', insert: '()', selection: [1, 1], wrap: true },
    { label: '[ ]', title: '方括号，光标停在中间', insert: '[]', selection: [1, 1], wrap: true },
    { label: '·', title: '结晶水分隔符', insert: '·' },
  ] },
  { id: 'reaction', label: '反应与化学符号', items: [
    { label: '+', title: '反应物或生成物之间的加号', insert: '+' },
    { label: '−', title: '减号', insert: '−' },
    { label: '→', title: '反应箭头', insert: '→' },
    { label: '⇌', title: '可逆反应箭头', insert: '⇌' },
    { label: '⇄', title: '双向箭头', insert: '⇄' },
    { label: '↑', title: '上箭头，可表示气体或自旋向上', insert: '↑' },
    { label: '↓', title: '下箭头，可表示沉淀或自旋向下', insert: '↓' },
    { label: 'Δ', title: '加热符号', insert: 'Δ' },
    { label: '=', title: '等号或双键', insert: '=' },
    { label: '≡', title: '三键', insert: '≡' },
  ] },
  { id: 'valence', label: '化合价（元素正上方）', items: [
    { label: '+1', title: '选中元素或将光标放在元素后，添加正一价', insert: '{+1}', selection: [2, 3], annotateSelection: true },
    { label: '+2', title: '选中元素或将光标放在元素后，添加正二价', insert: '{+2}', selection: [2, 3], annotateSelection: true },
    { label: '+3', title: '选中元素或将光标放在元素后，添加正三价', insert: '{+3}', selection: [2, 3], annotateSelection: true },
    { label: '+4', title: '选中元素或将光标放在元素后，添加正四价', insert: '{+4}', selection: [2, 3], annotateSelection: true },
    { label: '+5', title: '选中元素或将光标放在元素后，添加正五价', insert: '{+5}', selection: [2, 3], annotateSelection: true },
    { label: '+6', title: '选中元素或将光标放在元素后，添加正六价', insert: '{+6}', selection: [2, 3], annotateSelection: true },
    { label: '+7', title: '选中元素或将光标放在元素后，添加正七价', insert: '{+7}', selection: [2, 3], annotateSelection: true },
    { label: '0', title: '选中元素或将光标放在元素后，添加零价', insert: '{0}', selection: [1, 2], annotateSelection: true },
    { label: '−1', title: '选中元素或将光标放在元素后，添加负一价', insert: '{-1}', selection: [2, 3], annotateSelection: true },
    { label: '−2', title: '选中元素或将光标放在元素后，添加负二价', insert: '{-2}', selection: [2, 3], annotateSelection: true },
    { label: '−3', title: '选中元素或将光标放在元素后，添加负三价', insert: '{-3}', selection: [2, 3], annotateSelection: true },
    { label: '−4', title: '选中元素或将光标放在元素后，添加负四价', insert: '{-4}', selection: [2, 3], annotateSelection: true },
  ] },
  { id: 'electrons', label: '电子与电子点', items: [
    { label: 'e⁻', title: '电子 e⁻', insert: 'e^-' },
    { label: '•', title: '单电子点', insert: '•' },
    { label: '×', title: '交叉电子点', insert: '×' },
    { label: ':', title: '电子对符号', insert: ':' },
    { label: '↑↓', title: '成对电子', insert: '↑↓' },
    ...[1, 2, 3, 4, 5, 6, 7, 8].map((count) => ({
      label: count + ' 点',
      title: '在所选元素周围标注 ' + count + ' 个价电子点',
      insert: '{e:' + count + '}',
      annotateSelection: true,
    })),
  ] },
  { id: 'ions', label: '常见离子与基团', items: ['NH4', 'OH', 'NO3', 'SO4', 'CO3', 'HCO3', 'PO4'].map((part) => ({
    label: part.replace(/\d/g, (digit) => '₀₁₂₃₄₅₆₇₈₉'[Number(digit)]),
    title: '基团 ' + part,
    insert: part,
  })) },
  { id: 'other', label: '更多元素', items: allAtoms.filter((atom) => !commonAtoms.includes(atom)).map(atomItem) },
]
const recentKey = 'a12-subject-chemical-recent-v1'
const readRecent = () => {
  try {
    if (typeof window === 'undefined') return []
    const value = JSON.parse(window.localStorage.getItem(recentKey) || '[]')
    const available = new Set(toolGroups.flatMap((group) => group.items.map((item) => item.insert)))
    return Array.isArray(value) ? value.filter((item) => typeof item === 'string' && available.has(item)).slice(0, 20) : []
  } catch { return [] }
}
const recentItems = ref(readRecent())
const itemsByInsert = new Map(toolGroups.flatMap((group) => group.items.map((item) => [item.insert, item])))
const visibleToolGroups = computed(() => [
  { id: 'recent', label: '最近使用', items: recentItems.value.map((insert) => itemsByInsert.get(insert) || { label: insert, title: '插入 ' + insert, insert }) },
  ...toolGroups,
])
const expandedGroups = ref(new Set(['recent', 'digits', 'common', 'scripts']))
const isGroupExpanded = (id) => expandedGroups.value.has(id)
const toggleGroup = (id) => {
  const next = new Set(expandedGroups.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedGroups.value = next
}
const formulaError = computed(() => chemicalFormulaError(props.modelValue))
const previewMarkup = computed(() => chemicalFormulaMarkup(props.modelValue))

const remember = (item) => {
  const insert = String(item?.insert || '')
  if (!insert) return
  recentItems.value = [insert, ...recentItems.value.filter((candidate) => candidate !== insert)].slice(0, 20)
  if (!expandedGroups.value.has('recent')) expandedGroups.value = new Set([...expandedGroups.value, 'recent'])
  try { window.localStorage.setItem(recentKey, JSON.stringify(recentItems.value)) } catch { /* Storage is optional. */ }
}

const getInput = () => editor.value?.$el?.querySelector('input,textarea')
const captureSelection = () => {
  const input = getInput()
  if (input) lastSelection.value = { start: input.selectionStart, end: input.selectionEnd }
}
const annotationKind = (insert) => {
  if (/^[_^]\{[A-Za-z0-9+−-]{1,16}\}$/.test(insert)) return 'script'
  if (/^\{e:[1-8]\}$/.test(insert)) return 'electrons'
  if (/^\{[+−-]?\d{1,3}\}$/.test(insert)) return 'valence'
  if (/^\^\d{0,3}[+−-]$/.test(insert)) return 'charge'
  return ''
}
const markerAtSelection = (formula, start, end, requestedKind) => {
  const markers = /[_^]\{[A-Za-z0-9+−-]{1,16}\}|\{e:[1-8]\}|\{[+−-]?\d{1,3}\}|\^\d{0,3}[+−-]/g
  for (const match of formula.matchAll(markers)) {
    const markerStart = match.index
    const markerEnd = markerStart + match[0].length
    const kind = annotationKind(match[0])
    if (start > markerStart && end < markerEnd) return { start: markerStart, end: markerEnd, kind }
    if (start === end && start === markerEnd && kind === requestedKind) {
      return { start: markerStart, end: markerEnd, kind }
    }
  }
  return null
}
const insertPart = async (item) => {
  const current = String(props.modelValue || '')
  const input = getInput()
  const selection = input && document.activeElement === input
    ? { start: input.selectionStart, end: input.selectionEnd }
    : (lastSelection.value || { start: current.length, end: current.length })
  let start = Math.min(selection.start, current.length)
  let end = Math.min(Math.max(selection.end, start), current.length)
  const insert = String(item.insert || '')
  const requestedKind = annotationKind(insert)
  const marker = markerAtSelection(current, start, end, requestedKind)
  let replacingMarker = false
  let caretAfterMarker = null
  if (marker) {
    if (/^\d$/.test(insert)) {
      if (start !== end) caretAfterMarker = marker.end + insert.length - (end - start)
    } else if (requestedKind && requestedKind === marker.kind) {
      start = marker.start
      end = marker.end
      replacingMarker = true
    } else {
      start = marker.end
      end = marker.end
    }
  }
  const selectedText = current.slice(start, end)
  const wrapsSelection = Boolean(!replacingMarker && item.wrap && selectedText)
  const scriptsSelection = Boolean(!replacingMarker && item.wrapSelection && selectedText)
  const annotatesSelection = Boolean(!replacingMarker && item.annotateSelection && selectedText)
  const insertion = replacingMarker
    ? insert
    : wrapsSelection
    ? item.insert[0] + selectedText + item.insert[item.insert.length - 1]
    : scriptsSelection
      ? item.wrapSelection[0] + selectedText + item.wrapSelection[1]
      : annotatesSelection
        ? selectedText + item.insert
        : insert
  const next = `${current.slice(0, start)}${insertion}${current.slice(end)}`
  if (next.length > 300) {
    insertError.value = '化学式最多输入 300 个字符。'
    return
  }
  insertError.value = ''
  emit('update:modelValue', next)
  remember(item)
  await nextTick()
  const nextInput = editor.value?.$el?.querySelector('input,textarea')
  nextInput?.focus()
  const offset = annotatesSelection ? selectedText.length : 0
  const selectionStart = caretAfterMarker ?? start + (wrapsSelection || scriptsSelection ? insertion.length : offset + (item.selection?.[0] ?? insert.length))
  const selectionEnd = caretAfterMarker ?? start + (wrapsSelection || scriptsSelection ? insertion.length : offset + (item.selection?.[1] ?? insert.length))
  nextInput?.setSelectionRange(selectionStart, selectionEnd)
  lastSelection.value = { start: selectionStart, end: selectionEnd }
}

const updateFormula = (value) => {
  insertError.value = ''
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="chemical-formula-editor">
    <div class="chemical-toolbox" aria-label="化学符号工具栏">
      <section v-for="group in visibleToolGroups" :key="group.id" class="chemical-tool-group">
        <button
          type="button"
          class="chemical-group-toggle"
          :aria-expanded="isGroupExpanded(group.id)"
          :aria-controls="'chemical-group-' + group.id"
          @click="toggleGroup(group.id)"
        >
          <span>{{ group.label }}</span>
          <span class="chemical-group-meta"><small>{{ group.items.length }}</small><i :class="{ expanded: isGroupExpanded(group.id) }" aria-hidden="true">⌄</i></span>
        </button>
        <div :id="'chemical-group-' + group.id" v-show="isGroupExpanded(group.id)" class="chemical-group-items">
          <span v-if="group.id === 'recent' && !group.items.length" class="chemical-history-empty">暂无记录，点击下方元素后会显示在这里</span>
          <button
            v-for="item in group.items"
            :key="item.insert"
            type="button"
            class="chemical-tool-button"
            :title="item.title + '：点击插入'"
            :aria-label="item.title + '，点击插入'"
            @mousedown.prevent="captureSelection"
            @click="insertPart(item)"
          >{{ item.label }}</button>
        </div>
      </section>
    </div>

    <div class="chemical-input-panel">
      <label for="chemical-formula-input">化学式</label>
      <el-input
        id="chemical-formula-input"
        ref="editor"
        :model-value="modelValue"
        maxlength="300"
        clearable
        aria-label="化学式，可键盘输入或点击上方符号插入"
        placeholder="例如：H2O、Ca(OH)2、SO4^2-"
        @update:model-value="updateFormula"
        @focus="captureSelection"
        @click="captureSelection"
        @keyup="captureSelection"
        @mouseup="captureSelection"
        @select="captureSelection"
        @blur="captureSelection"
      />
      <div class="chemical-input-footer">
        <span>键盘直接输入，或点击上方符号插入</span>
        <span>{{ String(modelValue || '').length }} / 300</span>
      </div>
    </div>

    <div class="chemical-formula-composer" aria-label="化学式实时预览" role="status">
      <span class="chemical-composer-label">预览</span>
      <strong v-if="modelValue" class="chemical-formula-preview" v-html="previewMarkup"></strong>
      <span v-else class="chemical-formula-empty">在上方输入化学式</span>
    </div>
    <p v-if="insertError || formulaError" class="chemical-editor-error" role="alert">{{ insertError || formulaError }}</p>
    <p v-else class="chemical-editor-help">数字自动排成下标；化合价标在元素上方，离子电荷标在右上角。</p>
  </div>
</template>

<style scoped>
.chemical-formula-editor { display: grid; gap: 9px; }
.chemical-toolbox { display: grid; gap: 5px; max-height: 280px; padding: 7px; overflow-y: auto; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.chemical-tool-group { display: grid; gap: 4px; min-width: 0; }
.chemical-group-toggle { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; padding: 5px 7px; border: 1px solid transparent; border-radius: 6px; color: var(--zh-text-secondary); background: transparent; font-size: 10px; font-weight: 600; text-align: left; cursor: pointer; }
.chemical-group-toggle:hover, .chemical-group-toggle:focus-visible { border-color: var(--zh-line-border); color: var(--zh-text-theme); background: var(--zh-background-primary); outline: none; }
.chemical-group-meta { display: inline-flex; align-items: center; gap: 6px; color: var(--zh-text-caption); }
.chemical-group-meta small { font-size: 9px; font-weight: 400; }
.chemical-group-meta i { display: inline-block; font-size: 14px; font-style: normal; line-height: 1; transition: transform 140ms ease; }
.chemical-group-meta i.expanded { transform: rotate(180deg); }
.chemical-group-items { display: flex; flex-wrap: wrap; gap: 4px; padding: 1px 4px 3px; }
.chemical-history-empty { padding: 5px 4px; color: var(--zh-text-caption); font-size: 9px; }
.chemical-tool-button { min-width: 29px; min-height: 27px; padding: 4px 7px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font: 11px var(--zh-font-number); cursor: pointer; }
.chemical-tool-button:hover, .chemical-tool-button:focus-visible { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.chemical-input-panel { display: grid; gap: 6px; min-width: 0; padding: 10px 11px 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.chemical-input-panel:focus-within { border-color: var(--zh-line-theme); }
.chemical-input-panel > label { color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.chemical-input-panel :deep(.el-input__wrapper) { padding: 6px 2px; border-radius: 0; background: transparent; box-shadow: none !important; }
.chemical-input-panel :deep(.el-input__inner) { font: 600 17px/1.4 var(--zh-font-number); }
.chemical-input-footer { display: flex; justify-content: space-between; gap: 10px; color: var(--zh-text-caption); font-size: 10px; }
.chemical-input-footer span:last-child { flex: none; }
.chemical-formula-composer { display: flex; align-items: center; gap: 10px; min-height: 88px; padding: 16px 12px; overflow: auto; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.chemical-composer-label { flex: none; color: var(--zh-text-caption); font-size: 10px; }
.chemical-formula-preview { display: inline-block; flex: none; padding: .24em .6em .38em; color: #0f766e; font: 700 22px/1.2 Arial, "Microsoft YaHei", sans-serif; white-space: nowrap; }
.chemical-formula-preview :deep(sub), .chemical-formula-preview :deep(sup) { font-size: .6em; }
.chemical-formula-preview :deep(.a12-chem-atom) { position: relative; display: inline-block; vertical-align: baseline; line-height: 1; white-space: nowrap; }
.chemical-formula-preview :deep(.a12-chem-atom__symbol) { display: inline-block; }
.chemical-formula-preview :deep(.a12-chem-atom--valence) { padding-top: .62em; }
.chemical-formula-preview :deep(.a12-chem-atom__valence) { position: absolute; top: 0; left: 50%; transform: translateX(-50%); font-size: .5em; line-height: 1; }
.chemical-formula-preview :deep(.a12-chem-atom--electrons) { margin: 0 .32em; padding-top: .44em; padding-bottom: .34em; }
.chemical-formula-preview :deep(.a12-chem-atom--valence.a12-chem-atom--electrons) { padding-top: 1em; }
.chemical-formula-preview :deep(.a12-chem-atom__electron) { position: absolute; font-size: .34em; line-height: 1; letter-spacing: -.14em; }
.chemical-formula-preview :deep(.a12-chem-atom__electron--top) { top: 0; left: 50%; transform: translateX(-50%); }
.chemical-formula-preview :deep(.a12-chem-atom--valence .a12-chem-atom__electron--top) { top: .62em; }
.chemical-formula-preview :deep(.a12-chem-atom__electron--right) { top: 50%; right: -.66em; transform: translateY(-50%); }
.chemical-formula-preview :deep(.a12-chem-atom__electron--bottom) { bottom: 0; left: 50%; transform: translateX(-50%); }
.chemical-formula-preview :deep(.a12-chem-atom__electron--left) { top: 50%; left: -.66em; transform: translateY(-50%); }
.chemical-formula-preview :deep(.a12-chem-operator) { display: inline-block; margin: 0 .22em; }
.chemical-formula-preview :deep(.a12-chem-arrow) { display: inline-block; margin: 0 .3em; }
.chemical-formula-empty, .chemical-editor-help { color: var(--zh-text-caption); font-size: 10px; }
.chemical-editor-help, .chemical-editor-error { margin: 0; line-height: 1.5; }
.chemical-editor-error { color: var(--el-color-danger); font-size: 10px; }
</style>
