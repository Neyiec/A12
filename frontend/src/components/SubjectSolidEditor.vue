<script setup>
import { computed } from 'vue'
import { normalizeSolidData, solidFacts, solidMarkup, solidShapeOptions } from '../utils/subjectSolid'

const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue'])

const data = computed(() => normalizeSolidData(props.modelValue))
const preview = computed(() => solidMarkup(data.value))
const facts = computed(() => solidFacts(data.value))
const dimensionControls = computed(() => ({
  cube: [{ key: 'length', label: '棱长' }],
  cuboid: [{ key: 'length', label: '长' }, { key: 'width', label: '宽' }, { key: 'height', label: '高' }],
  pyramid: [{ key: 'length', label: '底边长' }, { key: 'height', label: '高' }],
  cylinder: [{ key: 'radius', label: '底面半径' }, { key: 'height', label: '高' }],
  cone: [{ key: 'radius', label: '底面半径' }, { key: 'height', label: '高' }],
  sphere: [{ key: 'radius', label: '半径' }],
})[data.value.solid])

const change = (patch) => emit('update:modelValue', normalizeSolidData({ ...data.value, ...patch }))
const setSolid = (solid) => change({ solid })
const setDimension = (key, value) => {
  if (value === '' || value === null || !Number.isFinite(Number(value))) return
  change({ dimensions: { ...data.value.dimensions, [key]: Number(value) } })
}
const setOption = (key, event) => change({ [key]: event.target.checked })
</script>

<template>
  <div class="subject-solid-editor">
    <div class="solid-section">
      <strong class="solid-section-title">选择立体图形</strong>
      <div class="solid-shape-list" role="group" aria-label="立体图形类型">
        <button
          v-for="item in solidShapeOptions"
          :key="item.value"
          type="button"
          class="solid-shape-button"
          :class="{ active: data.solid === item.value }"
          :aria-pressed="data.solid === item.value"
          @click="setSolid(item.value)"
        >{{ item.label }}</button>
      </div>
    </div>

    <div class="solid-section">
      <strong class="solid-section-title">图形尺寸 <small>单位自定</small></strong>
      <div class="solid-dimensions">
        <label v-for="control in dimensionControls" :key="control.key">
          <span>{{ control.label }}</span>
          <el-input-number
            :model-value="data.dimensions[control.key]"
            :min="1"
            :max="20"
            :step="1"
            :precision="1"
            controls-position="right"
            :aria-label="`${facts.label}${control.label}`"
            @update:model-value="setDimension(control.key, $event)"
          />
        </label>
      </div>
    </div>

    <div class="solid-options" role="group" aria-label="图形显示选项">
      <label><input type="checkbox" :checked="data.show_hidden_edges" @change="setOption('show_hidden_edges', $event)">显示隐藏棱虚线</label>
      <label><input type="checkbox" :checked="data.show_dimensions" @change="setOption('show_dimensions', $event)">显示尺寸标注</label>
    </div>

    <div class="solid-preview" :aria-label="`${facts.label}预览`" v-html="preview"></div>

    <div class="solid-facts" aria-label="图形教学信息">
      <strong>{{ facts.label }}</strong>
      <span>{{ facts.structure }}</span>
      <span>体积公式：{{ facts.formula }}</span>
      <span>按当前尺寸计算：{{ facts.volumeText }}</span>
    </div>
    <p class="solid-help">图形为教学示意图；可调整尺寸，并选择是否显示隐藏棱和标注。</p>
  </div>
</template>

<style scoped>
.subject-solid-editor { display: grid; gap: 10px; }
.solid-section { display: grid; gap: 7px; padding: 9px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.solid-section-title { color: var(--zh-text-secondary); font-size: 10px; }
.solid-section-title small { margin-left: 5px; color: var(--zh-text-caption); font-size: 9px; font-weight: 400; }
.solid-shape-list { display: flex; flex-wrap: wrap; gap: 5px; }
.solid-shape-button { min-height: 29px; padding: 5px 10px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 10px; cursor: pointer; }
.solid-shape-button:hover, .solid-shape-button:focus-visible { border-color: var(--zh-line-theme); color: var(--zh-text-theme); outline: none; }
.solid-shape-button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); font-weight: 700; }
.solid-dimensions { display: grid; gap: 7px; }
.solid-dimensions label { display: grid; grid-template-columns: 56px minmax(0, 1fr); align-items: center; gap: 7px; color: var(--zh-text-secondary); font-size: 10px; }
.solid-dimensions :deep(.el-input-number) { width: 100%; }
.solid-dimensions :deep(.el-input-number .el-input__wrapper) { padding-right: 26px; padding-left: 8px; }
.solid-options { display: flex; flex-wrap: wrap; gap: 8px 16px; padding: 2px 1px; }
.solid-options label { display: inline-flex; align-items: center; gap: 5px; color: var(--zh-text-secondary); font-size: 10px; cursor: pointer; }
.solid-options input { accent-color: #2563eb; }
.solid-preview { display: grid; place-items: center; height: 190px; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.solid-preview :deep(svg) { display: block; width: 100%; height: 100%; }
.solid-facts { display: grid; gap: 5px; padding: 10px; border: 1px solid var(--zh-line-border); border-radius: 8px; color: var(--zh-text-secondary); background: var(--zh-background-light); font-size: 10px; }
.solid-facts strong { color: var(--zh-text-theme); }
.solid-help { margin: 0; color: var(--zh-text-caption); font-size: 9px; line-height: 1.5; }
</style>
