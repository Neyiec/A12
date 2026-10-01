<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { bindSubjectInteractions } from '../utils/subjectInteraction'
import { renderChemicalStructure } from '../utils/chemicalStructure'
import {
  normalizeSubjectToolType,
  subjectToolMarkup,
  subjectToolRuntimeCss,
} from '../utils/subjectTool'

const props = defineProps({
  element: { type: Object, default: () => ({}) },
  compact: { type: Boolean, default: false },
})

const STYLE_ID = 'a12-subject-tool-runtime-style'
const emit = defineEmits(['update:data'])
const root = ref(null)
let cleanup = null
let chemicalRenderRevision = 0

const subjectType = computed(() => normalizeSubjectToolType(
  props.element?.subjectType || props.element?.subject_type || props.element?.type,
))

const markup = computed(() => subjectToolMarkup({
  subjectType: subjectType.value,
  data: props.element?.data,
  title: props.element?.name || props.element?.content,
  renderHint: props.element?.subjectRenderHint || props.element?.subject_render_hint || props.element?.subjectRender || props.element?.subject_render || props.element?.render,
}))

const renderChemicalPreview = async () => {
  const revision = ++chemicalRenderRevision
  await nextTick()
  const target = root.value?.querySelector('.a12-subject-tool__molecule')
  if (!target || revision !== chemicalRenderRevision) return
  await renderChemicalStructure(target, props.element?.data || {})
}

watch(() => [
  subjectType.value,
  props.element?.data?.smiles || '',
  props.element?.data?.molfile || '',
  props.element?.style?.fontSize ?? props.element?.subjectStyle?.fontSize ?? props.element?.subject_style?.fontSize ?? '',
], () => { void renderChemicalPreview() })

// 结构化页面的在线预览不在 iframe 中，注入与画布同一份运行时样式，保证
// 展示结果与编辑页一致。实际数据仍由右侧属性面板和后端校验接口管理。
onMounted(() => {
  cleanup = bindSubjectInteractions(root.value, (_, data) => emit('update:data', data))
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement('style')
    style.id = STYLE_ID
    style.textContent = subjectToolRuntimeCss
    document.head.appendChild(style)
  }
  void renderChemicalPreview()
})
onBeforeUnmount(() => {
  chemicalRenderRevision += 1
  cleanup?.()
})
</script>

<template>
  <div ref="root" class="subject-runtime" :class="{ 'is-compact': compact }">
    <div class="a12-subject-tool" :data-subject-data="JSON.stringify(element.data || {})" v-html="markup"></div>
  </div>
</template>

<style scoped>
.subject-runtime {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
}

.subject-runtime.is-compact {
  min-height: 92px;
}

.subject-runtime.is-compact :deep(.a12-subject-tool) {
  padding: 8px 10px !important;
}
</style>
