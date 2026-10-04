<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { geometryMarkup, geometryPoints, geometryPresetPoints, geometrySegments } from '../utils/subjectTool'
import { bindSubjectInteractions } from '../utils/subjectInteraction'

const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue'])
const mode = ref('visual')
const sourceDraft = ref('')
const sourceError = ref('')
const board = ref(null)
let cleanupInteractions = null
const constructions = [
  { id: 'right_triangle', label: '直角三角形' },
  { id: 'triangle', label: '三角形' },
  { id: 'equilateral_triangle', label: '等边三角形' },
  { id: 'rectangle', label: '矩形' },
  { id: 'square', label: '正方形' },
  { id: 'parallelogram', label: '平行四边形' },
  { id: 'rhombus', label: '菱形' },
  { id: 'custom', label: '自定义图形' },
]
const construction = computed(() => String(props.modelValue?.construction || 'right_triangle'))
const custom = computed(() => construction.value === 'custom')
const points = computed(() => geometryPoints(props.modelValue))
const segments = computed(() => geometrySegments(props.modelValue, points.value.length))
const preview = computed(() => geometryMarkup(props.modelValue))
const pointLabel = (index) => String.fromCharCode(65 + index)
const segmentStart = ref(0)
const segmentEnd = ref(1)
const canAddSegment = computed(() => segmentStart.value !== segmentEnd.value
  && Number.isInteger(segmentStart.value) && Number.isInteger(segmentEnd.value)
  && segmentStart.value >= 0 && segmentEnd.value >= 0
  && segmentStart.value < points.value.length && segmentEnd.value < points.value.length
  && segments.value.length < 36
  && !segments.value.some(([start, end]) => (start === segmentStart.value && end === segmentEnd.value)
    || (start === segmentEnd.value && end === segmentStart.value)))
const measurements = computed(() => custom.value ? [] : points.value.map((point, index, all) => {
  const previous = all[(index - 1 + all.length) % all.length]
  const next = all[(index + 1) % all.length]
  const edge = Math.hypot(next.x - point.x, next.y - point.y)
  const ax = previous.x - point.x
  const ay = previous.y - point.y
  const bx = next.x - point.x
  const by = next.y - point.y
  const divisor = Math.hypot(ax, ay) * Math.hypot(bx, by)
  const angle = divisor ? Math.acos(Math.max(-1, Math.min(1, (ax * bx + ay * by) / divisor))) * 180 / Math.PI : NaN
  return {
    edge: `${String.fromCharCode(65 + index)}${String.fromCharCode(65 + ((index + 1) % all.length))}`,
    length: edge.toFixed(1),
    vertex: String.fromCharCode(65 + index),
    angle: Number.isFinite(angle) ? `${angle.toFixed(1)}°` : '—',
  }
}))
const segmentMeasurements = computed(() => segments.value.map(([start, end]) => ({
  edge: `${pointLabel(start)}${pointLabel(end)}`,
  length: Math.hypot(points.value[end].x - points.value[start].x, points.value[end].y - points.value[start].y).toFixed(1),
})))
const constrainPoints = (draft, movedIndex) => {
  if (!Array.isArray(draft) || movedIndex < 0) return draft
  const next = draft.map((point) => ({ ...point }))
  if (construction.value === 'right_triangle' && next.length === 3) {
    // A-B stays horizontal and B-C stays vertical, keeping the right angle at B.
    if (movedIndex === 0) next[1].y = next[0].y
    if (movedIndex === 1) { next[0].y = next[1].y; next[2].x = next[1].x }
    if (movedIndex === 2) next[1].x = next[2].x
    return next
  }
  if (!['rectangle', 'square'].includes(construction.value) || next.length !== 4) return next
  const opposite = next[(movedIndex + 2) % 4]
  const moved = next[movedIndex]
  if (construction.value === 'square') {
    const previous = points.value[movedIndex]
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
const sourcePreview = computed(() => {
  try {
    const draft = JSON.parse(sourceDraft.value || '{}')
    if (!draft || typeof draft !== 'object' || Array.isArray(draft)) return ''
    return geometryMarkup(draft).replaceAll('tabindex="0" role="slider"', 'tabindex="-1" role="img"')
  } catch { return '' }
})
const setPreset = (value) => {
  segmentStart.value = 0
  segmentEnd.value = 1
  emit('update:modelValue', {
    ...props.modelValue,
    construction: value,
    commands: [`draw_${value}`],
    points: geometryPresetPoints(value),
    segments: [],
  })
}
const addPoint = () => {
  if (!custom.value || points.value.length >= 12) return
  const index = points.value.length
  const nextPoint = { x: 30 + (index % 4) * 38, y: 25 + Math.floor(index / 4) * 25 }
  if (index === 1) { segmentStart.value = 0; segmentEnd.value = 1 }
  emit('update:modelValue', { ...props.modelValue, points: [...points.value, nextPoint] })
}
const removePoint = (index) => {
  if (!custom.value) return
  const nextPoints = points.value.filter((_, pointIndex) => pointIndex !== index)
  const nextSegments = segments.value.filter(([start, end]) => start !== index && end !== index)
    .map(([start, end]) => [start > index ? start - 1 : start, end > index ? end - 1 : end])
  segmentStart.value = 0
  segmentEnd.value = Math.min(1, nextPoints.length - 1)
  emit('update:modelValue', { ...props.modelValue, points: nextPoints, segments: nextSegments })
}
const addSegment = () => {
  if (!custom.value || !canAddSegment.value) return
  emit('update:modelValue', { ...props.modelValue, segments: [...segments.value, [segmentStart.value, segmentEnd.value]] })
}
const removeSegment = (index) => {
  if (!custom.value) return
  emit('update:modelValue', { ...props.modelValue, segments: segments.value.filter((_, segmentIndex) => segmentIndex !== index) })
}
const setPoint = (index, key, value) => {
  if (value === '' || value === null || value === undefined) return
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return
  const nextPoints = points.value.map((point) => ({ ...point }))
  if (!nextPoints[index]) return
  const [min, max] = key === 'x' ? [8, 172] : [8, 92]
  nextPoints[index][key] = Math.min(max, Math.max(min, numeric))
  emit('update:modelValue', { ...props.modelValue, points: constrainPoints(nextPoints, index) })
}
const applySource = () => {
  try {
    const parsed = JSON.parse(sourceDraft.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('几何配置必须是 JSON 对象。')
    const nextConstruction = constructions.some((item) => item.id === parsed.construction) ? parsed.construction : construction.value
    const nextPoints = geometryPoints({ ...parsed, construction: nextConstruction })
    emit('update:modelValue', {
      ...parsed,
      construction: nextConstruction,
      commands: Array.isArray(parsed.commands) ? parsed.commands : [`draw_${nextConstruction}`],
      points: nextPoints,
      segments: geometrySegments({ ...parsed, construction: nextConstruction }, nextPoints.length),
    })
    sourceError.value = ''
  } catch (error) { sourceError.value = error?.message || '配置不是有效的 JSON。' }
}
watch(() => JSON.stringify(props.modelValue), () => {
  sourceDraft.value = JSON.stringify({ ...props.modelValue, points: points.value }, null, 2)
  sourceError.value = ''
}, { immediate: true })
const bindBoardInteractions = () => {
  if (mode.value !== 'visual' || !board.value) return
  cleanupInteractions = bindSubjectInteractions(board.value, (_, data) => {
    const updated = data && typeof data === 'object' ? data : {}
    const updatedPoints = Array.isArray(updated.points) ? updated.points : points.value
    emit('update:modelValue', { ...props.modelValue, ...updated, points: updatedPoints })
  })
}
onMounted(bindBoardInteractions)
watch(mode, async () => {
  cleanupInteractions?.()
  await nextTick()
  bindBoardInteractions()
})
onBeforeUnmount(() => cleanupInteractions?.())
</script>

<template>
  <div class="subject-geometry-editor">
    <div class="geometry-mode-tabs" role="tablist" aria-label="几何图形编辑模式">
      <button type="button" role="tab" :aria-selected="mode === 'visual'" :class="{ active: mode === 'visual' }" @click="mode = 'visual'">画板编辑</button>
      <button type="button" role="tab" :aria-selected="mode === 'source'" :class="{ active: mode === 'source' }" @click="mode = 'source'">JSON 源码</button>
    </div>

    <template v-if="mode === 'visual'">
      <div class="geometry-construction-tools" role="group" aria-label="几何构造预设">
        <strong>几何构造</strong>
        <div class="geometry-preset-list">
          <button
            v-for="item in constructions"
            :key="item.id"
            type="button"
            class="geometry-preset-button"
            :class="{ active: construction === item.id }"
            :aria-pressed="construction === item.id"
            :title="`点击切换为${item.label}`"
            @click="setPreset(item.id)"
          >{{ item.label }}</button>
        </div>
      </div>
      <div class="geometry-points-heading">
        <strong>{{ custom ? '点坐标' : '顶点坐标' }}</strong>
        <div class="geometry-heading-actions"><span>{{ points.length }} 个点</span><button v-if="custom" type="button" :disabled="points.length >= 12" @click="addPoint">+ 添加点</button></div>
      </div>
      <div class="geometry-point-list">
        <div v-for="(point, index) in points" :key="`point-${index}`" class="geometry-point-row" :class="{ 'geometry-point-row--custom': custom }">
          <strong>{{ pointLabel(index) }}</strong>
          <label><span>X</span><el-input-number :model-value="point.x" :min="8" :max="172" :step="1" controls-position="right" :aria-label="`点 ${pointLabel(index)} X 坐标`" @update:model-value="setPoint(index, 'x', $event)" /></label>
          <label><span>Y</span><el-input-number :model-value="point.y" :min="8" :max="92" :step="1" controls-position="right" :aria-label="`点 ${pointLabel(index)} Y 坐标`" @update:model-value="setPoint(index, 'y', $event)" /></label>
          <button v-if="custom" type="button" class="geometry-remove-button" :aria-label="`删除点 ${pointLabel(index)}`" @click="removePoint(index)">×</button>
        </div>
      </div>
      <div v-if="custom" class="geometry-segment-tools">
        <div class="geometry-points-heading"><strong>线段</strong><span>{{ segments.length }} 条线段</span></div>
        <div class="geometry-segment-form">
          <el-select v-model="segmentStart" size="small" aria-label="线段起点" :disabled="points.length < 2" placeholder="起点">
            <el-option v-for="(_, index) in points" :key="`from-${index}`" :label="pointLabel(index)" :value="index" />
          </el-select>
          <span>—</span>
          <el-select v-model="segmentEnd" size="small" aria-label="线段终点" :disabled="points.length < 2" placeholder="终点">
            <el-option v-for="(_, index) in points" :key="`to-${index}`" :label="pointLabel(index)" :value="index" />
          </el-select>
          <button type="button" class="geometry-add-segment" :disabled="!canAddSegment" @click="addSegment">+ 添加线段</button>
        </div>
        <div v-if="segments.length" class="geometry-segment-list">
          <span v-for="([start, end], index) in segments" :key="`segment-${start}-${end}`">{{ pointLabel(start) }}{{ pointLabel(end) }}<button type="button" :aria-label="`删除线段 ${pointLabel(start)}${pointLabel(end)}`" @click="removeSegment(index)">×</button></span>
        </div>
        <p v-else class="geometry-editor-help">选择两个点并添加线段，图形会立即显示在画板上。</p>
      </div>
      <p class="geometry-editor-help">坐标范围：X 8–172，Y 8–92。可输入坐标、拖动点或用方向键微调；{{ custom ? '自定义图形只连接已添加的线段。' : '直角三角形、矩形和正方形会保持对应的图形约束。' }}</p>
      <div ref="board" class="geometry-live-board" data-subject-interaction-owner :data-subject-data="JSON.stringify(modelValue)" aria-label="可拖动的几何图形预览" v-html="preview"></div>
      <p v-if="custom && !points.length" class="geometry-editor-help">点击“添加点”开始绘制。</p>
      <div class="geometry-measurements" aria-label="图形测量结果">
        <strong>即时测量 <small>长度为画布单位</small></strong>
        <div class="geometry-measurement-list">
          <template v-if="custom"><span v-for="item in segmentMeasurements" :key="`edge-${item.edge}`">{{ item.edge }}：{{ item.length }}</span><span v-if="!segments.length">添加线段后显示长度。</span></template>
          <span v-for="item in measurements" :key="`edge-${item.edge}`">{{ item.edge }}：{{ item.length }}</span>
        </div>
        <div v-if="!custom" class="geometry-measurement-list">
          <span v-for="item in measurements" :key="`angle-${item.vertex}`">∠{{ item.vertex }}：{{ item.angle }}</span>
        </div>
      </div>
    </template>

    <template v-else>
      <el-input v-model="sourceDraft" type="textarea" :rows="10" maxlength="12000" show-word-limit aria-label="几何画板 JSON 配置" placeholder='{"construction":"right_triangle","commands":["draw_right_triangle"],"points":[{"x":18,"y":82},{"x":156,"y":82},{"x":156,"y":18}]}' />
      <el-button type="primary" @click="applySource">应用几何配置</el-button>
      <p v-if="sourceError" class="geometry-editor-error" role="alert">{{ sourceError }}</p>
      <p class="geometry-editor-help">JSON 支持 construction、commands 和 points 坐标；自定义图形可用 segments: [[0, 1]] 指定线段两端的点序号（最多 12 个点、36 条线段）。下方显示当前草稿，应用后才会保存。</p>
      <div v-if="sourcePreview" class="geometry-live-board geometry-live-board--readonly" aria-label="几何画板草稿预览" v-html="sourcePreview"></div>
      <div v-else class="geometry-live-board geometry-live-board--readonly geometry-preview-empty">输入有效的 JSON 后可预览。</div>
    </template>
  </div>
</template>

<style scoped>
.subject-geometry-editor { display: grid; gap: 9px; }
.geometry-mode-tabs { display: inline-flex; justify-self: start; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.geometry-mode-tabs button { padding: 5px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; font-size: 10px; cursor: pointer; }
.geometry-mode-tabs button.active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: 0 1px 3px rgb(15 23 42 / 10%); font-weight: 700; }
.geometry-construction-tools { display: grid; gap: 6px; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.geometry-construction-tools > strong { color: var(--zh-text-secondary); font-size: 10px; }
.geometry-preset-list { display: flex; flex-wrap: wrap; gap: 5px; }
.geometry-preset-button { min-height: 29px; padding: 5px 8px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 10px; cursor: pointer; }
.geometry-preset-button:hover, .geometry-preset-button:focus-visible { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.geometry-preset-button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); font-weight: 700; }
.geometry-live-board { display: grid; place-items: center; min-height: 160px; padding: 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.geometry-live-board :deep(svg) { display: block; width: min(100%, 400px); height: 150px; overflow: visible; }
.geometry-live-board :deep(path) { fill: rgb(37 99 235 / 5%); stroke: #2563eb; stroke-width: 1.7; }
.geometry-live-board :deep(circle) { fill: white; stroke: #2563eb; stroke-width: 1.7; cursor: crosshair; }
.geometry-live-board :deep(text) { fill: #315f9f; font-size: 8px; text-anchor: middle; }
.geometry-live-board--readonly :deep(circle) { cursor: default; pointer-events: none; }
.geometry-preview-empty { color: var(--zh-text-caption); font-size: 10px; }
.geometry-editor-help { margin: 0; color: var(--zh-text-caption); font-size: 9px; line-height: 1.5; }
.geometry-measurements { display: grid; gap: 6px; padding: 9px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); color: var(--zh-text-secondary); font-size: 10px; }
.geometry-measurements > strong { color: var(--zh-text-theme); }
.geometry-measurements small { margin-left: 5px; color: var(--zh-text-caption); font-size: 9px; font-weight: 400; }
.geometry-measurement-list { display: flex; flex-wrap: wrap; gap: 5px 12px; }
.geometry-points-heading { display: flex; justify-content: space-between; color: var(--zh-text-secondary); font-size: 10px; }
.geometry-points-heading span { color: var(--zh-text-caption); font-size: 9px; }
.geometry-heading-actions { display: flex; align-items: center; gap: 8px; }
.geometry-heading-actions button, .geometry-add-segment { padding: 3px 7px; border: 1px solid var(--zh-line-theme); border-radius: 5px; color: var(--zh-text-theme); background: var(--zh-background-primary); font-size: 9px; cursor: pointer; }
.geometry-heading-actions button:disabled, .geometry-add-segment:disabled { border-color: var(--zh-line-border); color: var(--zh-text-caption); cursor: not-allowed; }
.geometry-point-list { display: grid; gap: 6px; }
.geometry-point-row { display: grid; grid-template-columns: 24px minmax(0,1fr) minmax(0,1fr); align-items: center; gap: 6px; }
.geometry-point-row--custom { grid-template-columns: 24px minmax(0,1fr) minmax(0,1fr) 24px; }
.geometry-point-row > strong { color: var(--zh-text-theme); font: 700 10px var(--zh-font-number); text-align: center; }
.geometry-point-row label { display: grid; grid-template-columns: 12px minmax(0,1fr); align-items: center; gap: 4px; color: var(--zh-text-caption); font-size: 9px; }
.geometry-point-row :deep(.el-input-number) { width: 100%; }
.geometry-point-row :deep(.el-input-number .el-input__wrapper) { padding-right: 26px; padding-left: 5px; }
.geometry-remove-button { width: 24px; height: 24px; border: 0; border-radius: 5px; color: var(--zh-text-caption); background: transparent; font-size: 16px; cursor: pointer; }
.geometry-remove-button:hover, .geometry-segment-list button:hover { color: var(--el-color-danger); background: var(--zh-background-weaken); }
.geometry-segment-tools { display: grid; gap: 7px; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.geometry-segment-form { display: grid; grid-template-columns: minmax(0,1fr) auto minmax(0,1fr) auto; align-items: center; gap: 6px; }
.geometry-segment-form :deep(.el-select) { min-width: 0; }
.geometry-segment-form > span { color: var(--zh-text-caption); }
.geometry-segment-list { display: flex; flex-wrap: wrap; gap: 5px; }
.geometry-segment-list > span { display: inline-flex; align-items: center; gap: 4px; padding: 2px 4px 2px 7px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 9px; }
.geometry-segment-list button { width: 16px; height: 16px; padding: 0; border: 0; border-radius: 3px; color: var(--zh-text-caption); background: transparent; font-size: 13px; line-height: 1; cursor: pointer; }
.geometry-editor-error { margin: 0; color: var(--el-color-danger); font-size: 10px; }
</style>
