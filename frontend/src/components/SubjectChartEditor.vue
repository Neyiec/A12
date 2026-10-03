<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { subjectToolMarkup } from '../utils/subjectTool'

const props = defineProps({ modelValue: { type: [Object, String], default: () => ({}) } })
const emit = defineEmits(['update:modelValue'])
const mode = ref('visual')
const sourceDraft = ref('')
const sourceError = ref('')
const importDraft = ref('')
const importError = ref('')
const editorRoot = ref(null)
const focusLabel = async (index) => {
  await nextTick()
  const field = editorRoot.value?.querySelector(`[data-chart-label="${index}"]`)
  const input = field?.tagName === 'INPUT' ? field : field?.querySelector('input')
  input?.focus()
  input?.select()
}

const asObject = (value) => value && typeof value === 'object' && !Array.isArray(value) ? value : {}
const sourceOption = computed(() => asObject(props.modelValue))
const firstSeries = computed(() => {
  const list = sourceOption.value.series
  return Array.isArray(list) ? asObject(list[0]) : asObject(list)
})
const chartType = computed(() => ['bar', 'line', 'pie'].includes(firstSeries.value.type) ? firstSeries.value.type : 'bar')
const chartTitle = computed(() => String(sourceOption.value.title?.text ?? ''))
const axisTitleParts = (title) => {
  const value = typeof title === 'string' ? title : ''
  const match = value.match(/^(.*?)（([^（）]{1,12})）$/)
  return match ? { name: match[1], unit: match[2] } : { name: value, unit: '' }
}
const simpleAxisTitle = (title) => title === undefined || (typeof title === 'string'
  && title.length <= 40 && axisTitleParts(title).name.length <= 24)
const xAxisTitle = computed(() => axisTitleParts(sourceOption.value.xAxis?.name))
const yAxisTitle = computed(() => axisTitleParts(sourceOption.value.yAxis?.name))
const axisLabels = computed(() => {
  const axis = Array.isArray(sourceOption.value.xAxis) ? sourceOption.value.xAxis[0] : sourceOption.value.xAxis
  return Array.isArray(axis?.data) ? axis.data : []
})
const chartRows = computed(() => {
  const values = Array.isArray(firstSeries.value.data) ? firstSeries.value.data : []
  const rows = values.slice(0, 8).map((value, index) => ({
    label: String(value && typeof value === 'object' ? (value.name ?? axisLabels.value[index] ?? `数据 ${index + 1}`) : (axisLabels.value[index] ?? `数据 ${index + 1}`)),
    value: Number(value && typeof value === 'object' ? value.value : value) || 0,
  }))
  return rows.length ? rows : [{ label: '数据 1', value: 0 }]
})
const onlyKeys = (value, allowed) => Object.keys(value).every((key) => allowed.includes(key))
const validValue = (value) => typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 1000000
const visualIssue = computed(() => {
  if (typeof props.modelValue === 'string') return '当前配置是文本，请先在配置模式中改为有效 JSON。'
  const option = sourceOption.value
  if (!onlyKeys(option, ['title', 'xAxis', 'yAxis', 'series'])) return '当前配置包含高级 ECharts 选项。'
  if (option.title !== undefined && (!onlyKeys(asObject(option.title), ['text']) || typeof option.title?.text !== 'string' || option.title.text.length > 72)) return '图表标题使用了高级配置。'
  if (!Array.isArray(option.series) || option.series.length !== 1) return '当前配置包含多个数据系列或缺少数据系列。'
  const series = asObject(option.series[0])
  if (!onlyKeys(series, ['type', 'data']) || !['bar', 'line', 'pie'].includes(series.type)) return '当前数据系列无法用简易编辑器完整表示。'
  if (!Array.isArray(series.data) || !series.data.length || series.data.length > 8) return '数据项超过 8 项或尚未设置。'
  if (option.xAxis !== undefined) {
    const axis = asObject(option.xAxis)
    if (!onlyKeys(axis, ['type', 'data', 'name']) || axis.type !== 'category' || !Array.isArray(axis.data)
      || !simpleAxisTitle(axis.name)
      || axis.data.length > 8 || axis.data.some((label) => typeof label !== 'string' || label.length > 24)) return '横轴使用了高级配置。'
  }
  if (series.type === 'pie') {
    if (series.data.some((item) => !item || typeof item !== 'object' || Array.isArray(item)
      || !onlyKeys(item, ['name', 'value']) || typeof item.name !== 'string' || item.name.length > 24
      || !validValue(item.value) || item.value < 0)) return '饼图数据包含简易编辑器无法完整表示的内容。'
  } else {
    const axis = asObject(option.xAxis)
    if (axis.data?.length !== series.data.length || series.data.some((value) => !validValue(value))) return '坐标轴或数据项无法用简易编辑器完整表示。'
  }
  if (option.yAxis !== undefined && (!onlyKeys(asObject(option.yAxis), ['type', 'name']) || option.yAxis?.type !== 'value'
    || !simpleAxisTitle(option.yAxis.name))) return '纵轴使用了高级配置。'
  return ''
})
const draftOption = computed(() => {
  if (mode.value !== 'source') return sourceOption.value
  try {
    const parsed = JSON.parse(sourceDraft.value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch { return null }
})
const previewSeries = computed(() => Array.isArray(draftOption.value?.series) ? draftOption.value.series : [])
const previewAvailable = computed(() => ['bar', 'line', 'pie'].includes(previewSeries.value[0]?.type)
  && Array.isArray(previewSeries.value[0]?.data))
const previewMarkup = computed(() => previewAvailable.value
  ? subjectToolMarkup({ subjectType: 'chart', data: { option: draftOption.value } }) : '')
const previewNote = computed(() => {
  if (!previewAvailable.value) return '输入包含柱状图、折线图或饼图数据的有效 JSON 后可预览。'
  if (previewSeries.value.length > 1 || previewSeries.value[0].data.length > 8) return '画布预览只绘制第一个数据系列的前 8 项；完整配置会保留。'
  if (visualIssue.value) return '画布使用简化预览；高级 ECharts 效果可能无法完整呈现。'
  return mode.value === 'source' ? '草稿预览；点击“应用图表配置”后才会保存到画布。' : '与画布同步更新。'
})

const emitRows = (rows, changes = {}) => {
  if (visualIssue.value) return
  const current = JSON.parse(JSON.stringify(sourceOption.value))
  const nextType = changes.type || chartType.value
  const title = changes.title ?? chartTitle.value
  current.title = { ...asObject(current.title), text: title }
  const seriesList = Array.isArray(current.series) ? [...current.series] : []
  const series = { ...firstSeries.value, type: nextType }
  if (nextType === 'pie') {
    series.data = rows.map((row) => ({ name: row.label, value: Number(row.value) || 0 }))
  } else {
    const xAxisList = Array.isArray(current.xAxis) ? [...current.xAxis] : null
    const axis = { ...asObject(xAxisList ? xAxisList[0] : current.xAxis), type: 'category', data: rows.map((row) => row.label) }
    if (xAxisList) { xAxisList[0] = axis; current.xAxis = xAxisList }
    else current.xAxis = axis
    series.data = rows.map((row) => Number(row.value) || 0)
  }
  seriesList[0] = series
  current.series = seriesList.length ? seriesList : [series]
  emit('update:modelValue', current)
}

const setTitle = (title) => emitRows(chartRows.value, { title })
const setAxisTitle = (axisKey, field, value) => {
  if (visualIssue.value || chartType.value === 'pie') return
  const current = JSON.parse(JSON.stringify(sourceOption.value))
  const axis = { ...asObject(current[axisKey]) }
  const parts = axisTitleParts(axis.name)
  parts[field] = field === 'unit' ? String(value).replace(/[（）]/g, '').slice(0, 12) : String(value).slice(0, 24)
  const name = parts.name.trim()
  const unit = parts.unit.trim()
  if (name || unit) axis.name = unit ? `${name}（${unit}）` : name
  else delete axis.name
  if (axisKey === 'yAxis' && !axis.type) axis.type = 'value'
  current[axisKey] = axis
  emit('update:modelValue', current)
}
const setChartType = (type) => {
  sourceError.value = ''
  emitRows(chartRows.value, { type })
}
const setRow = (index, key, value) => {
  const rows = chartRows.value.map((row) => ({ ...row }))
  rows[index][key] = key === 'value' ? (Number(value) || 0) : String(value).slice(0, 24)
  emitRows(rows)
}
const addRow = async () => {
  if (chartRows.value.length >= 8) return
  const newIndex = chartRows.value.length
  emitRows([...chartRows.value, { label: `数据 ${chartRows.value.length + 1}`, value: 0 }])
  await focusLabel(newIndex)
}
const removeRow = (index) => {
  if (chartRows.value.length <= 1) return
  emitRows(chartRows.value.filter((_, rowIndex) => rowIndex !== index))
}
const importRows = () => {
  const lines = importDraft.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const rows = lines.map((line) => {
    const cells = line.split(/[,，\t]/)
    if (cells.length !== 2) return { label: '', value: NaN }
    const [label, value] = cells
    return { label: label.trim(), value: value.trim() === '' ? NaN : Number(value.trim()) }
  })
  if (!rows.length || rows.some((row) => !row.label || row.label.length > 24 || !validValue(row.value))) {
    importError.value = '请每行输入“名称,数值”，名称不超过 24 字且数值在 ±1000000 范围内。'
    return
  }
  if (rows.length > 8) { importError.value = '简易编辑最多导入 8 项；请减少行数，或使用 ECharts 配置模式。'; return }
  if (chartType.value === 'pie' && rows.some((row) => row.value < 0)) { importError.value = '饼图不能使用负数，请修改后再导入。'; return }
  emitRows(rows)
  importDraft.value = ''
  importError.value = ''
}
const applySource = () => {
  try {
    const parsed = JSON.parse(sourceDraft.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('图表配置必须是 JSON 对象。')
    if (!Array.isArray(parsed.series) || !parsed.series.length || !Array.isArray(parsed.series[0]?.data)) throw new Error('至少需要一个 series，且其中包含 data 数组。')
    emit('update:modelValue', parsed)
    sourceError.value = ''
  } catch (error) { sourceError.value = error?.message || '配置不是有效的 JSON。' }
}
watch(() => JSON.stringify(props.modelValue), (value) => {
  sourceDraft.value = typeof props.modelValue === 'string' ? props.modelValue : JSON.stringify(asObject(props.modelValue), null, 2)
  if (value) sourceError.value = ''
}, { immediate: true })
watch(visualIssue, (issue) => { if (issue) mode.value = 'source' }, { immediate: true })
</script>

<template>
  <div ref="editorRoot" class="subject-chart-editor">
    <div class="chart-mode-tabs" role="tablist" aria-label="图表编辑模式">
      <button type="button" role="tab" :aria-selected="mode === 'visual'" :class="{ active: mode === 'visual' }" :disabled="!!visualIssue" @click="mode = 'visual'">可视化编辑</button>
      <button type="button" role="tab" :aria-selected="mode === 'source'" :class="{ active: mode === 'source' }" @click="mode = 'source'">ECharts 配置</button>
    </div>
    <p v-if="visualIssue" class="chart-editor-notice" role="status">{{ visualIssue }}请在配置模式中编辑，原始数据会保留。</p>

    <template v-if="mode === 'visual'">
      <label>图表类型
        <el-radio-group :model-value="chartType" size="small" @update:model-value="setChartType">
          <el-radio-button value="bar">柱状图</el-radio-button><el-radio-button value="line">折线图</el-radio-button><el-radio-button value="pie" :disabled="chartRows.some((row) => row.value < 0)">饼图</el-radio-button>
        </el-radio-group>
      </label>
      <el-button class="chart-add-button" :disabled="chartRows.length >= 8" @click="addRow">＋ 添加数据项</el-button>
      <label>图表标题<el-input :model-value="chartTitle" maxlength="72" placeholder="输入图表标题" @update:model-value="setTitle" /></label>
      <div v-if="chartType !== 'pie'" class="chart-axis-section">
        <strong>坐标轴</strong>
        <div class="chart-axis-fields">
          <label>横轴名称<el-input :model-value="xAxisTitle.name" maxlength="24" placeholder="例如：时间" @update:model-value="setAxisTitle('xAxis', 'name', $event)" /></label>
          <label>单位<el-input :model-value="xAxisTitle.unit" maxlength="12" placeholder="例如：秒" aria-label="横轴单位" @update:model-value="setAxisTitle('xAxis', 'unit', $event)" /></label>
          <label>纵轴名称<el-input :model-value="yAxisTitle.name" maxlength="24" placeholder="例如：温度" @update:model-value="setAxisTitle('yAxis', 'name', $event)" /></label>
          <label>单位<el-input :model-value="yAxisTitle.unit" maxlength="12" placeholder="例如：℃" aria-label="纵轴单位" @update:model-value="setAxisTitle('yAxis', 'unit', $event)" /></label>
        </div>
        <p class="chart-editor-help">单位会写入轴标题，例如“时间（秒）”。</p>
      </div>
      <p v-else class="chart-editor-help">饼图没有坐标轴；切回柱状图或折线图后可继续编辑已填写的轴标题。</p>
      <div class="chart-data-heading"><strong>数据项</strong><span>{{ chartRows.length }} / 8</span></div>
      <div class="chart-row-list">
        <div v-for="(row, index) in chartRows" :key="`chart-row-${index}`" class="chart-data-row">
          <el-input :data-chart-label="index" :model-value="row.label" :maxlength="24" :aria-label="`第 ${index + 1} 项名称`" placeholder="名称" @update:model-value="setRow(index, 'label', $event)" />
          <el-input-number :model-value="row.value" :min="-1000000" :max="1000000" :step="1" controls-position="right" :aria-label="`第 ${index + 1} 项数值`" @update:model-value="setRow(index, 'value', $event)" />
          <el-button text circle :disabled="chartRows.length <= 1" :aria-label="`删除第 ${index + 1} 项`" @click="removeRow(index)">×</el-button>
        </div>
      </div>
      <details class="chart-import-details">
        <summary>批量粘贴 / 导入</summary>
        <el-input v-model="importDraft" type="textarea" :rows="3" maxlength="800" aria-label="批量粘贴图表数据" placeholder="一行一项，名称和数值用逗号、中文逗号或 Tab 分隔" />
        <el-button class="chart-import-button" @click="importRows">替换当前数据</el-button>
      </details>
      <p v-if="importError" class="chart-editor-error" role="status">{{ importError }}</p>
      <p class="chart-editor-help">简易编辑最多 8 项；批量导入会替换当前数据。</p>
    </template>

    <template v-else>
      <el-input v-model="sourceDraft" type="textarea" :rows="10" maxlength="12000" show-word-limit aria-label="ECharts 图表配置 JSON" placeholder='{"xAxis":{"data":["A","B"]},"series":[{"type":"bar","data":[60,80]}]}' />
      <el-button type="primary" @click="applySource">应用图表配置</el-button>
      <p v-if="sourceError" class="chart-editor-error" role="alert">{{ sourceError }}</p>
      <p class="chart-editor-help">可直接编辑 ECharts JSON；下方预览显示当前草稿。</p>
    </template>

    <section class="chart-preview-section" aria-label="图表预览">
      <strong>预览</strong>
      <div v-if="previewAvailable" class="chart-live-preview" v-html="previewMarkup"></div>
      <div v-else class="chart-preview-empty">{{ previewNote }}</div>
      <p v-if="previewAvailable" class="chart-editor-help">{{ previewNote }}</p>
    </section>
  </div>
</template>

<style scoped>
.subject-chart-editor { display: grid; gap: 9px; }
.chart-mode-tabs { display: inline-flex; justify-self: start; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.chart-mode-tabs button { padding: 5px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; font-size: 10px; cursor: pointer; }
.chart-mode-tabs button.active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: 0 1px 3px rgb(15 23 42 / 10%); font-weight: 700; }
.chart-mode-tabs button:disabled { opacity: .45; cursor: not-allowed; }
.subject-chart-editor > label { display: grid; gap: 6px; color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.chart-axis-section { display: grid; gap: 7px; }
.chart-axis-section > strong { color: var(--zh-text-secondary); font-size: 10px; }
.chart-axis-fields { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .65fr); gap: 7px; }
.chart-axis-fields label { display: grid; gap: 5px; min-width: 0; color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.subject-chart-editor :deep(.el-radio-group) { display: flex; width: 100%; }
.subject-chart-editor :deep(.el-radio-button) { flex: 1; }
.subject-chart-editor :deep(.el-radio-button__inner) { width: 100%; padding-right: 4px; padding-left: 4px; }
.chart-data-heading { display: flex; justify-content: space-between; align-items: baseline; color: var(--zh-text-secondary); font-size: 10px; }
.chart-data-heading span, .chart-editor-help { color: var(--zh-text-caption); font-size: 9px; }
.chart-row-list { display: grid; gap: 6px; }
.chart-data-row { display: grid; grid-template-columns: minmax(0,1fr) 104px 28px; align-items: center; gap: 5px; }
.chart-data-row :deep(.el-button) { width: 28px; height: 28px; margin: 0; color: var(--zh-text-caption); font-size: 18px; }
.chart-data-row :deep(.el-button:hover:not(:disabled)) { color: var(--el-color-danger); }
.chart-add-button, .chart-import-button { width: 100%; margin: 0; }
.chart-add-button { border-style: dashed; }
.chart-import-details { padding: 8px 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; }
.chart-import-details summary { color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; cursor: pointer; }
.chart-import-details :deep(.el-textarea), .chart-import-details :deep(.el-button) { margin-top: 9px; }
.chart-editor-help, .chart-editor-error { margin: 0; line-height: 1.5; }
.chart-editor-error { color: var(--el-color-danger); font-size: 10px; }
.chart-editor-notice { margin: 0; color: #9a6700; font-size: 10px; line-height: 1.5; }
.chart-preview-section { display: grid; gap: 7px; margin-top: 5px; }
.chart-preview-section > strong { color: var(--zh-text-secondary); font-size: 11px; }
.chart-live-preview, .chart-preview-empty { min-height: 175px; padding: 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.chart-live-preview { display: flex; align-items: center; justify-content: center; overflow: hidden; }
.chart-preview-empty { display: grid; place-items: center; color: var(--zh-text-caption); font-size: 10px; text-align: center; }
.chart-live-preview :deep(.a12-subject-tool__header) { display: none; }
.chart-live-preview :deep(.a12-subject-tool__chart-area) { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 150px; min-width: 0; min-height: 0; }
.chart-live-preview :deep(.a12-subject-tool__chart-title) { align-self: flex-start; overflow: hidden; max-width: 100%; color: #24558d; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.chart-live-preview :deep(.a12-subject-tool__chart-svg) { display: block; flex: 1; width: 100%; min-width: 0; min-height: 0; max-height: 100%; }
.chart-live-preview :deep(.a12-subject-tool__chart-svg > path:first-child) { fill: none; stroke: rgb(96 116 145 / 35%); stroke-width: 1; }
.chart-live-preview :deep(.a12-subject-tool__chart-svg text) { fill: #607491; font: 9px "Microsoft YaHei", Arial, sans-serif; }
.chart-live-preview :deep(.a12-subject-tool__chart-legend) { display: flex; flex-wrap: wrap; justify-content: center; gap: 3px 8px; max-height: 2.6em; overflow: hidden; color: #607491; font-size: 9px; }
.chart-live-preview :deep(.a12-subject-tool__chart-legend span) { display: inline-flex; align-items: center; gap: 3px; white-space: nowrap; }
.chart-live-preview :deep(.a12-subject-tool__chart-legend i) { display: inline-block; width: 6px; height: 6px; border-radius: 2px; }
</style>
