<script setup>
import { computed, ref } from 'vue'
import { coordinateMarkup, normalizeCoordinateData } from '../utils/coordinateTool'

const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue'])
const data = computed(() => normalizeCoordinateData(props.modelValue))
const preview = computed(() => coordinateMarkup(data.value))
const segmentStart = ref(0)
const segmentEnd = ref(1)
const canAddSegment = computed(() => {
  const start = segmentStart.value
  const end = segmentEnd.value
  return data.value.segments.length < 36
    && Number.isInteger(start) && Number.isInteger(end)
    && start >= 0 && end >= 0
    && start < data.value.points.length && end < data.value.points.length
    && start !== end
    && !data.value.segments.some(([first, second]) => (first === start && second === end) || (first === end && second === start))
})

const update = (changes) => emit('update:modelValue', normalizeCoordinateData({ ...props.modelValue, ...changes }))
const setRange = (axis, value) => {
  if (value === '' || value === null || value === undefined) return
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return
  update({ [axis]: numeric })
}
const setPoint = (index, field, value) => {
  if (value === '' || value === null || value === undefined) return
  const next = data.value.points.map((point) => ({ ...point }))
  if (!next[index]) return
  if (field === 'label') next[index].label = String(value).slice(0, 8)
  else {
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) return
    next[index][field] = numeric
  }
  update({ points: next })
}
const addPoint = () => {
  if (data.value.points.length >= 10) return
  const labels = new Set(data.value.points.map((point) => point.label))
  const label = Array.from({ length: 10 }, (_, index) => String.fromCharCode(65 + index))
    .find((candidate) => !labels.has(candidate)) || `P${data.value.points.length + 1}`
  update({ points: [...data.value.points, { label, x: 0, y: 0 }] })
}
const removePoint = (index) => {
  const points = data.value.points.filter((_, pointIndex) => pointIndex !== index)
  const segments = data.value.segments
    .filter(([start, end]) => start !== index && end !== index)
    .map(([start, end]) => [start > index ? start - 1 : start, end > index ? end - 1 : end])
  segmentStart.value = 0
  segmentEnd.value = 1
  update({ points, segments })
}
const addSegment = () => {
  if (!canAddSegment.value) return
  update({ segments: [...data.value.segments, [segmentStart.value, segmentEnd.value]] })
}
const removeSegment = (index) => update({ segments: data.value.segments.filter((_, segmentIndex) => segmentIndex !== index) })
</script>

<template>
  <div class="subject-coordinate-editor">
    <div class="coordinate-settings">
      <strong>坐标轴范围</strong>
      <div class="coordinate-range-fields">
        <label>横轴 ±<el-input-number :model-value="data.xRange" :min="2" :max="10" :step="1" controls-position="right" aria-label="横轴正负范围" @update:model-value="setRange('xRange', $event)" /></label>
        <label>纵轴 ±<el-input-number :model-value="data.yRange" :min="2" :max="10" :step="1" controls-position="right" aria-label="纵轴正负范围" @update:model-value="setRange('yRange', $event)" /></label>
      </div>
      <div class="coordinate-switches">
        <label><span>显示网格</span><el-switch :model-value="data.showGrid" @update:model-value="update({ showGrid: $event })" /></label>
        <label><span>依次连线</span><el-switch :model-value="data.connectPoints" @update:model-value="update({ connectPoints: $event })" /></label>
      </div>
    </div>

    <div class="coordinate-points-heading">
      <strong>坐标点 <small>{{ data.points.length }} / 10</small></strong>
      <el-button size="small" :disabled="data.points.length >= 10" @click="addPoint">添加点</el-button>
    </div>
    <div v-if="data.points.length" class="coordinate-point-list">
      <div v-for="(point, index) in data.points" :key="index" class="coordinate-point-row">
        <el-input :model-value="point.label" maxlength="8" :aria-label="`第 ${index + 1} 个点的名称`" @update:model-value="setPoint(index, 'label', $event)" />
        <label><span>X</span><el-input-number :model-value="point.x" :min="-data.xRange" :max="data.xRange" :step="1" controls-position="right" :aria-label="`点 ${point.label} 的 X 坐标`" @update:model-value="setPoint(index, 'x', $event)" /></label>
        <label><span>Y</span><el-input-number :model-value="point.y" :min="-data.yRange" :max="data.yRange" :step="1" controls-position="right" :aria-label="`点 ${point.label} 的 Y 坐标`" @update:model-value="setPoint(index, 'y', $event)" /></label>
        <el-button text type="danger" :aria-label="`删除点 ${point.label}`" @click="removePoint(index)">删除</el-button>
      </div>
    </div>
    <p v-else class="coordinate-help">画板上暂时没有坐标点。点击“添加点”开始标注。</p>
    <div class="coordinate-points-heading">
      <strong>自定义连线 <small>{{ data.segments.length }} / 36</small></strong>
    </div>
    <div class="coordinate-segment-controls">
      <el-select v-model="segmentStart" :disabled="data.points.length < 2" aria-label="连线起点" placeholder="起点">
        <el-option v-for="(point, index) in data.points" :key="index" :label="`起点 ${point.label}`" :value="index" />
      </el-select>
      <el-select v-model="segmentEnd" :disabled="data.points.length < 2" aria-label="连线终点" placeholder="终点">
        <el-option v-for="(point, index) in data.points" :key="index" :label="`终点 ${point.label}`" :value="index" />
      </el-select>
      <el-button size="small" :disabled="!canAddSegment" @click="addSegment">添加连线</el-button>
    </div>
    <div v-if="data.segments.length" class="coordinate-segment-list">
      <div v-for="([start, end], index) in data.segments" :key="`${start}-${end}`" class="coordinate-segment-row">
        <span>{{ data.points[start].label }} — {{ data.points[end].label }}</span>
        <el-button text type="danger" :aria-label="`删除连线 ${data.points[start].label} 到 ${data.points[end].label}`" @click="removeSegment(index)">删除</el-button>
      </div>
    </div>
    <p class="coordinate-help">选择两个点添加连线；“依次连线”可同时使用。删除点时，与它相连的线段也会删除。</p>
    <p class="coordinate-help">可用整数或小数标注点的位置；调整坐标轴范围时，超出范围的点会移到边界。</p>
    <div class="coordinate-preview" aria-label="坐标系预览" v-html="preview"></div>
  </div>
</template>

<style scoped>
.subject-coordinate-editor { display: grid; gap: 10px; }
.coordinate-settings { display: grid; gap: 8px; padding: 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.coordinate-settings > strong, .coordinate-points-heading strong { color: var(--zh-text-secondary); font-size: 11px; }
.coordinate-range-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.coordinate-range-fields label { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 6px; color: var(--zh-text-caption); font-size: 10px; }
.coordinate-range-fields :deep(.el-input-number) { width: 100%; }
.coordinate-switches { display: flex; flex-wrap: wrap; gap: 12px 24px; }
.coordinate-switches label { display: inline-flex; align-items: center; gap: 8px; color: var(--zh-text-secondary); font-size: 10px; }
.coordinate-points-heading { display: flex; align-items: center; justify-content: space-between; }
.coordinate-points-heading small { margin-left: 4px; color: var(--zh-text-caption); font-size: 9px; font-weight: 400; }
.coordinate-point-list { display: grid; gap: 6px; }
.coordinate-point-row { display: grid; grid-template-columns: minmax(50px, .65fr) minmax(70px, 1fr) minmax(70px, 1fr) auto; align-items: center; gap: 6px; }
.coordinate-point-row label { display: grid; grid-template-columns: 10px minmax(0, 1fr); align-items: center; gap: 3px; color: var(--zh-text-caption); font-size: 9px; }
.coordinate-point-row :deep(.el-input-number) { width: 100%; }
.coordinate-point-row > :deep(.el-button) { padding-inline: 4px; font-size: 10px; }
.coordinate-segment-controls { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; align-items: center; gap: 6px; }
.coordinate-segment-controls :deep(.el-select) { min-width: 0; }
.coordinate-segment-controls :deep(.el-button) { padding-inline: 8px; font-size: 10px; }
.coordinate-segment-list { display: grid; gap: 4px; }
.coordinate-segment-row { display: flex; align-items: center; justify-content: space-between; min-height: 26px; padding: 0 8px; border: 1px solid var(--zh-line-border); border-radius: 6px; color: var(--zh-text-secondary); font-size: 10px; }
.coordinate-segment-row :deep(.el-button) { padding-inline: 4px; font-size: 10px; }
.coordinate-help { margin: 0; color: var(--zh-text-caption); font-size: 9px; line-height: 1.5; }
.coordinate-preview { display: grid; place-items: center; min-height: 175px; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: #fff; }
.coordinate-preview :deep(svg) { display: block; width: min(100%, 500px); height: auto; }
@media (max-width: 520px) { .coordinate-point-row { grid-template-columns: minmax(45px, .6fr) minmax(60px, 1fr) minmax(60px, 1fr) auto; gap: 4px; } }
</style>
