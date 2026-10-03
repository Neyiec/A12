<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  ariaLabel: { type: String, default: '选择颜色' },
})
const emit = defineEmits(['update:modelValue'])

const isTransparent = computed(() => String(props.modelValue).toLowerCase() === 'transparent')
const pickerValue = computed(() => isTransparent.value ? '' : props.modelValue)
const updateColor = (value) => emit('update:modelValue', value || 'transparent')
</script>

<template>
  <div class="workspace-color-field">
    <el-color-picker
      :aria-label="ariaLabel"
      :model-value="pickerValue"
      value-on-clear="transparent"
      @update:model-value="updateColor"
    />
    <span v-if="!isTransparent" class="workspace-color-field__value">{{ modelValue }}</span>
    <button
      type="button"
      class="workspace-color-field__transparent"
      :class="{ active: isTransparent }"
      :aria-pressed="isTransparent"
      @click="updateColor('transparent')"
    >无色透明</button>
  </div>
</template>

<style scoped>
.workspace-color-field { display: flex; align-items: center; gap: 9px; min-width: 0; }
.workspace-color-field__value { min-width: 0; overflow: hidden; color: var(--zh-text-caption); font: 11px var(--zh-font-number); text-overflow: ellipsis; text-transform: uppercase; white-space: nowrap; }
.workspace-color-field__transparent { flex: none; margin-left: auto; padding: 5px 7px; border: 1px solid var(--zh-line-border); border-radius: 6px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 10px; cursor: pointer; }
.workspace-color-field__transparent:hover, .workspace-color-field__transparent:focus-visible, .workspace-color-field__transparent.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.workspace-color-field__transparent:focus-visible { outline: 2px solid var(--zh-line-theme); outline-offset: 2px; }
</style>
