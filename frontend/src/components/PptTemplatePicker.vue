<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  templates: { type: Array, default: () => [] },
  outline: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  applying: { type: Boolean, default: false },
  currentTheme: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'load', 'apply'])
const selectedTheme = ref('')

const outlineSlides = computed(() => {
  const value = props.outline?.slides || props.outline?.pages || []
  return Array.isArray(value) ? value : []
})
const templateCards = computed(() => props.templates.map((template, index) => {
  const theme = String(template?.theme || template?.id || template?.value || template?.name || `template-${index + 1}`)
  return {
    ...template,
    theme,
    label: String(template?.label || template?.title || template?.name || theme),
    description: String(template?.description || template?.desc || '保持课程结构，重新生成 HTML PPT 页面视觉风格'),
  }
}))
const selectedTemplate = computed(() => templateCards.value.find((item) => item.theme === selectedTheme.value) || templateCards.value[0])
const outlineTitle = computed(() => String(props.outline?.title || props.outline?.course_title || '当前课件大纲'))
const slideTitle = (slide, index) => String(slide?.title || slide?.heading || `第 ${index + 1} 页`)
const slidePoints = (slide) => {
  const points = slide?.content_points || slide?.points || slide?.key_points || []
  return Array.isArray(points) ? points.join('、') : String(points || slide?.description || '暂无内容摘要')
}

watch(() => [props.modelValue, props.currentTheme, templateCards.value.length], () => {
  if (props.modelValue && !selectedTheme.value) selectedTheme.value = props.currentTheme || templateCards.value[0]?.theme || ''
  if (props.modelValue && props.currentTheme && !templateCards.value.some((item) => item.theme === selectedTheme.value)) selectedTheme.value = props.currentTheme
}, { immediate: true })

const close = () => emit('update:modelValue', false)
const apply = () => { if (selectedTemplate.value?.theme) emit('apply', selectedTemplate.value.theme) }
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="更换 PPT 模板"
    width="min(980px, 94vw)"
    align-center
    class="template-picker-dialog"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    @open="emit('load')"
  >
    <div class="template-picker-layout">
      <aside class="template-outline-panel">
        <div class="template-panel-heading"><span>结构大纲</span><small>{{ outlineSlides.length }} 页</small></div>
        <p class="template-outline-title">{{ outlineTitle }}</p>
        <el-collapse v-if="outlineSlides.length" accordion>
          <el-collapse-item v-for="(slide, index) in outlineSlides" :key="`template-outline-${index}`" :name="String(index)">
            <template #title><span class="template-outline-item-title"><b>{{ String(index + 1).padStart(2, '0') }}</b>{{ slideTitle(slide, index) }}</span></template>
            <p class="template-outline-copy">{{ slidePoints(slide) }}</p>
            <small v-if="slide?.teaching_intent || slide?.teachingIntent">教学意图：{{ slide.teaching_intent || slide.teachingIntent }}</small>
          </el-collapse-item>
        </el-collapse>
        <el-empty v-else description="当前没有可展示的大纲，将按现有页面重构" :image-size="54" />
      </aside>

      <section class="template-drawer-panel">
        <div class="template-panel-heading"><span>模板风格</span><small>选中后按当前大纲重生成 HTML PPT</small></div>
        <div v-loading="loading" class="template-card-grid">
          <button
            v-for="template in templateCards"
            :key="template.theme"
            type="button"
            class="template-card"
            :class="{ selected: selectedTheme === template.theme }"
            @click="selectedTheme = template.theme"
          >
            <span class="template-card-preview" :data-template-theme="template.theme"><i></i><i></i><i></i></span>
            <strong>{{ template.label }}</strong>
            <small>{{ template.description }}</small>
            <span v-if="selectedTheme === template.theme" class="template-card-selected">当前选择</span>
          </button>
          <el-empty v-if="!loading && !templateCards.length" description="暂无模板，请检查模板服务" :image-size="64" />
        </div>
      </section>
    </div>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="applying" :disabled="!selectedTemplate" @click="apply">按此模板重构课件</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.template-picker-layout { display: grid; grid-template-columns: minmax(230px, .72fr) minmax(0, 1.28fr); gap: 18px; min-height: 430px; }
.template-outline-panel, .template-drawer-panel { min-width: 0; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-light); }
.template-drawer-panel { background: var(--zh-background-primary); }
.template-panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.template-panel-heading span { color: var(--zh-text-primary); font-size: 14px; font-weight: 700; }
.template-panel-heading small { color: var(--zh-text-caption); font-size: 10px; }
.template-outline-title { margin: 0 0 12px; color: var(--zh-text-secondary); font-size: 12px; font-weight: 600; }
.template-outline-item-title { display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-outline-item-title b { color: var(--zh-text-theme); font: 700 10px var(--zh-font-number); }
.template-outline-copy { margin: 0 0 6px; color: var(--zh-text-secondary); font-size: 11px; line-height: 1.6; }
.template-outline-panel small { color: var(--zh-text-caption); font-size: 10px; line-height: 1.5; }
.template-card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-content: start; gap: 10px; min-height: 360px; }
.template-card { position: relative; display: grid; gap: 7px; min-width: 0; padding: 9px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); color: var(--zh-text-secondary); background: var(--zh-background-light); text-align: left; cursor: pointer; transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease; }
.template-card:hover, .template-card.selected { border-color: var(--zh-line-theme); box-shadow: 0 6px 18px rgb(37 99 235 / 12%); transform: translateY(-1px); }
.template-card strong { overflow: hidden; color: var(--zh-text-primary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.template-card small { display: -webkit-box; overflow: hidden; color: var(--zh-text-caption); font-size: 10px; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.template-card-preview { display: grid; gap: 5px; min-height: 78px; padding: 12px; border-radius: 8px; background: linear-gradient(135deg, #e7eefc, #f9fbff); }
.template-card-preview i { display: block; width: 70%; height: 6px; border-radius: 999px; background: #2563eb; opacity: .85; }
.template-card-preview i:nth-child(2) { width: 48%; background: #64748b; opacity: .5; }
.template-card-preview i:nth-child(3) { width: 82%; height: 20px; margin-top: 7px; border-radius: 5px; background: rgb(37 99 235 / 14%); }
.template-card-preview[data-template-theme*="中国"], .template-card-preview[data-template-theme*="书卷"], .template-card-preview[data-template-theme*="宣纸"] { background: linear-gradient(135deg, #f9eee0, #fffaf1); }
.template-card-preview[data-template-theme*="科技"], .template-card-preview[data-template-theme*="赛博"], .template-card-preview[data-template-theme*="终端"] { background: linear-gradient(135deg, #10233d, #233b60); }
.template-card-preview[data-template-theme*="科技"] i, .template-card-preview[data-template-theme*="赛博"] i, .template-card-preview[data-template-theme*="终端"] i { background: #8ed8ff; }
.template-card-selected { position: absolute; top: 7px; right: 7px; padding: 3px 6px; border-radius: 999px; color: #fff; background: var(--zh-text-theme); font-size: 9px; }
@media (max-width: 1023.98px) { .template-picker-layout { grid-template-columns: 1fr; } .template-outline-panel { max-height: 250px; overflow: auto; } .template-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 767.98px) { .template-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .template-card { padding: 10px; } .template-card strong { font-size: 13px; } .template-card small { font-size: 11px; } }
</style>
