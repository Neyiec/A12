<script setup>
// 数据交互：接收四线格文字，向属性面板提交输入，并复用学科画布渲染实时预览。
import { computed } from 'vue'
import SubjectToolRuntime from './SubjectToolRuntime.vue'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

const MAX_LENGTH = 500
/** 将键盘输入的文字提交给属性面板。 */
const updateText = (value) => {
  emit('update:modelValue', value)
}
const previewElement = computed(() => ({
  type: 'subject',
  subjectType: 'english_four_line',
  name: '英语四线格',
  data: { text: props.modelValue },
}))
</script>

<template>
  <div class="english-four-line-editor">
    <div class="four-line-input-panel">
      <label for="english-four-line-input">英语内容</label>
      <el-input
        id="english-four-line-input"
        :model-value="modelValue"
        type="textarea"
        :rows="3"
        :maxlength="MAX_LENGTH"
        aria-label="英语四线格内容"
        placeholder="输入单词或句子"
        @update:model-value="updateText"
      />
      <div class="four-line-input-footer">
        <span>可输入空格与换行</span>
        <span>{{ String(modelValue || '').length }} / {{ MAX_LENGTH }}</span>
      </div>
    </div>

    <div class="four-line-preview" aria-label="英语四线格实时预览" role="status">
      <span class="four-line-preview-label">预览</span>
      <SubjectToolRuntime :element="previewElement" compact />
    </div>
  </div>
</template>

<style scoped>
.english-four-line-editor { display: grid; gap: 9px; min-width: 0; }
.four-line-input-panel { display: grid; gap: 6px; min-width: 0; padding: 10px 11px 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.four-line-input-panel:focus-within { border-color: var(--zh-line-theme); }
.four-line-input-panel > label { color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.four-line-input-panel :deep(.el-textarea__inner) { padding: 8px; font: 16px/1.5 Georgia, 'Times New Roman', serif; resize: vertical; }
.four-line-input-footer { display: flex; justify-content: space-between; gap: 10px; color: var(--zh-text-caption); font-size: 10px; }
.four-line-input-footer span:last-child { flex: none; }
.four-line-preview { display: grid; gap: 6px; min-width: 0; min-height: 160px; padding: 9px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.four-line-preview-label { color: var(--zh-text-caption); font-size: 10px; }
.four-line-preview :deep(.subject-runtime) { min-height: 124px; }
.four-line-preview :deep(.a12-subject-tool) { cursor: default; }
</style>
