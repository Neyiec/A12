<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({ modelValue: { type: Object, default: () => ({ columns: [], rows: [] }) } })
const emit = defineEmits(['update:modelValue'])
const mode = ref('visual')
const sourceDraft = ref('')
const sourceError = ref('')
const pasteDraft = ref('')
const pasteError = ref('')
const pasteInfo = ref('')
const pasteFirstRowHeader = ref(true)
const editorRoot = ref(null)
const focusField = async (selector, selectValue = false) => {
  await nextTick()
  const field = editorRoot.value?.querySelector(selector)
  const input = field?.tagName === 'INPUT' ? field : field?.querySelector('input')
  input?.focus()
  if (selectValue) input?.select()
}

const plainObject = (value) => value && typeof value === 'object' && !Array.isArray(value)
const visualIssue = computed(() => {
  const rawColumns = props.modelValue?.columns
  const rawRows = props.modelValue?.rows
  if (Array.isArray(rawColumns) && (rawColumns.length > 8 || rawColumns.some((column) => typeof column !== 'string' || column.length > 60))) return '当前列标题包含高级数据、过长文本或超过 8 列。'
  if (Array.isArray(rawRows) && (rawRows.length > 12 || rawRows.some((row) => !Array.isArray(row)))) return '当前表格包含对象行或超过 12 行。'
  const width = Array.isArray(rawColumns) && rawColumns.length ? rawColumns.length : 2
  if (Array.isArray(rawRows) && rawRows.some((row) => row.length > width)) return '部分数据行的单元格多于列标题。'
  if (Array.isArray(rawRows) && rawRows.some((row) => row.some((cell) => typeof cell !== 'string' || cell.length > 120))) return '当前单元格包含非文本数据或过长文本。'
  return ''
})

const columns = computed(() => Array.isArray(props.modelValue?.columns) && props.modelValue.columns.length
  ? props.modelValue.columns.slice(0, 8).map((column) => String(typeof column === 'object' ? (column.label || column.name || column.key || '') : column))
  : ['项目', '观察结果'])
const rows = computed(() => {
  const raw = Array.isArray(props.modelValue?.rows) ? props.modelValue.rows.slice(0, 12) : []
  const normalized = raw.map((row) => Array.isArray(row) ? row.slice(0, columns.value.length).map((cell) => String(cell ?? '')) : columns.value.map((column) => String(row?.[column] ?? '')))
  return normalized.length ? normalized : [['', '']]
})
const emitGrid = (nextColumns = columns.value, nextRows = rows.value) => {
  if (visualIssue.value) return
  emit('update:modelValue', {
    ...props.modelValue,
    columns: nextColumns.slice(0, 8),
    rows: nextRows.slice(0, 12).map((row) => Array.from({ length: nextColumns.length }, (_, index) => String(row[index] ?? '').slice(0, 120))),
  })
}
const setColumn = (index, value) => {
  const next = [...columns.value]
  next[index] = String(value).slice(0, 60)
  emitGrid(next)
}
const setCell = (rowIndex, columnIndex, value) => {
  const next = rows.value.map((row) => [...row])
  next[rowIndex][columnIndex] = String(value).slice(0, 120)
  emitGrid(columns.value, next)
}
const addColumn = async () => {
  if (columns.value.length >= 8) return
  const newIndex = columns.value.length
  emitGrid([...columns.value, `列 ${columns.value.length + 1}`], rows.value.map((row) => [...row, '']))
  await focusField(`[data-table-column="${newIndex}"]`, true)
}
const removeColumn = (columnIndex) => {
  if (columns.value.length <= 1) return
  emitGrid(columns.value.filter((_, index) => index !== columnIndex), rows.value.map((row) => row.filter((_, index) => index !== columnIndex)))
}
const addRow = async () => {
  if (rows.value.length >= 12) return
  const newIndex = rows.value.length
  emitGrid(columns.value, [...rows.value, columns.value.map(() => '')])
  await focusField(`[data-table-cell="${newIndex}-0"]`)
}
const removeRow = (rowIndex) => {
  if (rows.value.length <= 1) return
  emitGrid(columns.value, rows.value.filter((_, index) => index !== rowIndex))
}
const parseDelimitedText = (input) => {
  const source = String(input || '').replace(/\r\n?/g, '\n')
  const tabSeparated = source.includes('\t')
  const grid = []
  let row = []
  let cell = ''
  let quoted = false
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index]
    if (char === '"') {
      if (quoted && source[index + 1] === '"') { cell += '"'; index += 1 }
      else quoted = !quoted
    } else if (!quoted && (char === '\n' || char === '\t' && tabSeparated || !tabSeparated && (char === ',' || char === '，'))) {
      row.push(cell.trim())
      cell = ''
      if (char === '\n') {
        if (row.some((entry) => entry !== '')) grid.push(row)
        row = []
      }
    } else cell += char
  }
  row.push(cell.trim())
  if (row.some((entry) => entry !== '')) grid.push(row)
  return grid
}
const importPaste = () => {
  const grid = parseDelimitedText(pasteDraft.value)
  pasteInfo.value = ''
  if (!grid.length) { pasteError.value = '请粘贴至少一行表格数据。'; return }
  const dataRows = pasteFirstRowHeader.value ? grid.slice(1) : grid
  if (grid.some((row) => row.length > 8) || dataRows.length > 12) {
    pasteError.value = '最多导入 8 列、12 行数据；请缩减粘贴内容后重试。'
    return
  }
  if (grid.some((row) => row.some((cell) => cell.length > 120))
    || pasteFirstRowHeader.value && grid[0].some((cell) => cell.length > 60)) {
    pasteError.value = '列标题最多 60 字，单元格最多 120 字；请缩短内容后重试。'
    return
  }
  const width = Math.min(8, Math.max(1, pasteFirstRowHeader.value ? grid[0].length : columns.value.length, ...dataRows.map((row) => row.length)))
  const nextColumns = pasteFirstRowHeader.value
    ? Array.from({ length: width }, (_, index) => String(grid[0][index] || `列 ${index + 1}`).slice(0, 60))
    : Array.from({ length: width }, (_, index) => columns.value[index] || `列 ${index + 1}`)
  const nextRows = dataRows.slice(0, 12).map((row) => Array.from({ length: width }, (_, index) => row[index] || ''))
  emitGrid(nextColumns, nextRows.length ? nextRows : [nextColumns.map(() => '')])
  pasteError.value = ''
  pasteInfo.value = dataRows.length ? `已导入 ${nextRows.length} 行数据。` : '已更新列标题。'
  pasteDraft.value = ''
}
const sourceGrid = computed(() => {
  if (mode.value !== 'source') return props.modelValue
  try {
    const parsed = JSON.parse(sourceDraft.value)
    return plainObject(parsed) ? parsed : null
  } catch { return null }
})
const previewColumns = computed(() => {
  const raw = sourceGrid.value?.columns
  return Array.isArray(raw) ? raw.slice(0, 8).map((column, index) => String(plainObject(column)
    ? column.label || column.name || column.key || `列 ${index + 1}` : column || `列 ${index + 1}`)) : []
})
const previewRows = computed(() => {
  const raw = sourceGrid.value?.rows
  if (!Array.isArray(raw)) return []
  return raw.slice(0, 12).map((row) => previewColumns.value.map((column, index) => String(
    Array.isArray(row) ? row[index] ?? '' : plainObject(row) ? row[column] ?? '' : '',
  )))
})
const applySource = () => {
  try {
    const parsed = JSON.parse(sourceDraft.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('表格配置必须是 JSON 对象。')
    if (!Array.isArray(parsed.columns) || parsed.columns.length < 1 || !Array.isArray(parsed.rows)) throw new Error('配置需要包含 columns 和 rows 数组。')
    if (parsed.columns.length > 8 || parsed.rows.length > 12) throw new Error('表格最多支持 8 列、12 行数据。')
    if (parsed.columns.some((column) => typeof column !== 'string' || column.length > 60)) throw new Error('列标题必须是长度不超过 60 字的文本。')
    if (parsed.rows.some((row) => !Array.isArray(row) && !plainObject(row))) throw new Error('数据行必须是数组或对象。')
    if (parsed.rows.some((row) => Array.isArray(row) && row.length > parsed.columns.length)) throw new Error('数据行的单元格数不能超过列数。')
    emit('update:modelValue', parsed)
    sourceError.value = ''
  } catch (error) { sourceError.value = error?.message || '配置不是有效的 JSON。' }
}
watch(() => JSON.stringify(props.modelValue), () => {
  sourceDraft.value = JSON.stringify(props.modelValue || { columns: [], rows: [] }, null, 2)
  sourceError.value = ''
}, { immediate: true })
watch(visualIssue, (issue) => { if (issue) mode.value = 'source' }, { immediate: true })
</script>

<template>
  <div ref="editorRoot" class="subject-table-editor">
    <div class="table-mode-tabs" role="tablist" aria-label="探究数据表编辑模式">
      <button type="button" role="tab" :aria-selected="mode === 'visual'" :class="{ active: mode === 'visual' }" :disabled="!!visualIssue" @click="mode = 'visual'">表格编辑</button>
      <button type="button" role="tab" :aria-selected="mode === 'source'" :class="{ active: mode === 'source' }" @click="mode = 'source'">JSON 源码</button>
    </div>
    <p v-if="visualIssue" class="table-editor-notice" role="status">{{ visualIssue }}请在 JSON 模式中编辑，原始数据会保留。</p>

    <template v-if="mode === 'visual'">
      <div class="table-quick-actions" aria-label="表格快捷操作">
        <el-button :disabled="columns.length >= 8" @click="addColumn">＋ 添加列</el-button>
        <el-button :disabled="rows.length >= 12" @click="addRow">＋ 添加数据行</el-button>
      </div>
      <div class="table-editor-heading"><strong>列标题</strong><span>{{ columns.length }} / 8 列</span></div>
      <div class="table-column-list">
        <div v-for="(column, index) in columns" :key="`column-${index}`" class="table-column-row">
          <span>{{ index + 1 }}</span><el-input :data-table-column="index" :model-value="column" :maxlength="60" :aria-label="`第 ${index + 1} 列标题`" @update:model-value="setColumn(index, $event)" />
          <el-button text circle :disabled="columns.length <= 1" :aria-label="`删除第 ${index + 1} 列`" @click="removeColumn(index)">×</el-button>
        </div>
      </div>
      <div class="table-editor-heading"><strong>数据行</strong><span>{{ rows.length }} / 12 行</span></div>
      <div class="table-row-list">
        <div v-for="(row, rowIndex) in rows" :key="`row-${rowIndex}`" class="table-data-row" :style="{ '--subject-table-columns': columns.length }">
          <span class="table-row-number">{{ rowIndex + 1 }}</span>
          <el-input v-for="(column, columnIndex) in columns" :key="`cell-${rowIndex}-${columnIndex}`" :data-table-cell="`${rowIndex}-${columnIndex}`" :model-value="row[columnIndex]" :maxlength="120" :aria-label="`第 ${rowIndex + 1} 行，${column || `第 ${columnIndex + 1} 列`}`" :placeholder="column || `第 ${columnIndex + 1} 列`" @update:model-value="setCell(rowIndex, columnIndex, $event)" />
          <el-button text circle :disabled="rows.length <= 1" :aria-label="`删除第 ${rowIndex + 1} 行`" @click="removeRow(rowIndex)">×</el-button>
        </div>
      </div>
      <details class="table-import-details">
        <summary>批量粘贴 / 导入</summary>
        <el-input v-model="pasteDraft" type="textarea" :rows="3" maxlength="6000" aria-label="粘贴表格数据" placeholder="从 Excel 粘贴，或输入逗号 / Tab 分隔的数据" />
        <el-checkbox v-model="pasteFirstRowHeader">首行作为列标题</el-checkbox>
        <el-button @click="importPaste">替换当前表格</el-button>
      </details>
      <p v-if="pasteError" class="table-editor-error" role="status">{{ pasteError }}</p>
      <p v-else-if="pasteInfo" class="table-editor-help" role="status">{{ pasteInfo }}</p>
    </template>

    <template v-else>
      <el-input v-model="sourceDraft" type="textarea" :rows="10" maxlength="12000" show-word-limit aria-label="探究数据表 JSON 配置" placeholder='{"columns":["项目","观察结果"],"rows":[["实验组",""],["对照组",""]]}' />
      <el-button type="primary" @click="applySource">应用表格配置</el-button>
      <p v-if="sourceError" class="table-editor-error" role="alert">{{ sourceError }}</p>
      <p class="table-editor-help">编辑 JSON 后点击“应用表格配置”保存。</p>
    </template>

    <section class="table-preview-section" aria-label="表格预览">
      <strong>预览</strong>
      <div v-if="previewColumns.length" class="table-live-preview">
        <table>
          <thead><tr><th v-for="(column, index) in previewColumns" :key="`preview-column-${index}`">{{ column }}</th></tr></thead>
          <tbody>
            <tr v-for="(row, rowIndex) in previewRows" :key="`preview-row-${rowIndex}`">
              <td v-for="(cell, columnIndex) in row" :key="`preview-cell-${rowIndex}-${columnIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="table-preview-empty">{{ mode === 'source' ? '输入有效的表格 JSON 后可预览。' : '添加列标题后可预览。' }}</div>
      <p v-if="mode === 'source' && previewColumns.length" class="table-editor-help">当前草稿预览；点击“应用表格配置”后才会保存到画布。</p>
    </section>
  </div>
</template>

<style scoped>
.subject-table-editor { display: grid; gap: 9px; }
.table-mode-tabs { display: inline-flex; justify-self: start; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.table-mode-tabs button { padding: 5px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; font-size: 10px; cursor: pointer; }
.table-mode-tabs button.active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: 0 1px 3px rgb(15 23 42 / 10%); font-weight: 700; }
.table-mode-tabs button:disabled { opacity: .45; cursor: not-allowed; }
.table-editor-heading { display: flex; justify-content: space-between; align-items: baseline; color: var(--zh-text-secondary); font-size: 10px; }
.table-editor-heading span, .table-editor-help { color: var(--zh-text-caption); font-size: 9px; }
.table-column-list, .table-row-list { display: grid; gap: 6px; min-width: 0; overflow-x: auto; }
.table-column-row { display: grid; grid-template-columns: 20px minmax(0,1fr) 28px; align-items: center; gap: 5px; }
.table-column-row > span, .table-row-number { color: var(--zh-text-caption); font: 10px var(--zh-font-number); text-align: center; }
.table-column-row :deep(.el-button), .table-data-row :deep(.el-button) { width: 28px; height: 28px; margin: 0; color: var(--zh-text-caption); font-size: 18px; }
.table-data-row { display: grid; grid-template-columns: 20px repeat(var(--subject-table-columns, 2), minmax(75px,1fr)) 28px; align-items: center; gap: 5px; min-width: 300px; }
.table-data-row :deep(.el-input) { min-width: 0; }
.table-quick-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.table-quick-actions :deep(.el-button) { width: 100%; min-width: 0; margin: 0; border-style: dashed; font-size: 10px; }
.table-import-details { padding: 8px 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; }
.table-import-details summary { color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; cursor: pointer; }
.table-import-details :deep(.el-textarea), .table-import-details :deep(.el-checkbox), .table-import-details :deep(.el-button) { margin-top: 9px; }
.table-import-details :deep(.el-button) { width: 100%; margin-left: 0; }
.table-editor-help, .table-editor-error { margin: 0; line-height: 1.5; }
.table-editor-error { color: var(--el-color-danger); font-size: 10px; }
.table-editor-notice { margin: 0; color: #9a6700; font-size: 10px; line-height: 1.5; }
.table-preview-section { display: grid; gap: 7px; margin-top: 5px; }
.table-preview-section > strong { color: var(--zh-text-secondary); font-size: 11px; }
.table-live-preview, .table-preview-empty { min-height: 90px; overflow: auto; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.table-live-preview table { width: 100%; border-collapse: collapse; font-size: 10px; }
.table-live-preview th, .table-live-preview td { min-width: 70px; padding: 6px 8px; border: 1px solid rgb(37 99 235 / 14%); text-align: left; white-space: pre-wrap; overflow-wrap: anywhere; }
.table-live-preview th { color: #24558d; background: #eff6ff; }
.table-preview-empty { display: grid; place-items: center; color: var(--zh-text-caption); font-size: 10px; text-align: center; }
</style>
