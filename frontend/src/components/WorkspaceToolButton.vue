<script setup>
defineProps({
  icon: { type: Object, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  trailingIcon: { type: Object, default: null },
})

const emit = defineEmits(['click'])

const handleClick = (event) => emit('click', event)
</script>

<template>
  <el-button
    text
    class="workspace-tool-button"
    :class="{ 'is-active': active }"
    :icon="icon"
    :aria-label="label"
    :aria-pressed="active"
    :title="label"
    @click="handleClick"
  >
    <span>{{ label }}</span>
    <el-icon v-if="trailingIcon" class="workspace-tool-button__suffix"><component :is="trailingIcon" /></el-icon>
  </el-button>
</template>

<style scoped>
.workspace-tool-button {
  min-width: 68px;
  height: 34px;
  margin: 0;
  padding: 0 10px;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-secondary);
  font-size: 12px;
  transition: color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.workspace-tool-button:hover,
.workspace-tool-button:focus-visible {
  color: var(--zh-text-theme);
  background: var(--zh-background-primary);
}

.workspace-tool-button.is-active {
  color: var(--zh-text-theme);
  background: var(--zh-background-primary);
  box-shadow: var(--zh-shadow1);
}

.workspace-tool-button:focus-visible {
  outline: 2px solid var(--zh-line-theme);
  outline-offset: 1px;
}

.workspace-tool-button__suffix {
  margin-left: 3px;
  font-size: 10px;
  transition: transform 160ms ease;
}
</style>
