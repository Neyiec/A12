<script setup>
import { ref } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { useMobileViewport } from '../composables/useMobileViewport'
const props = defineProps({ title: { type: String, required: true }, initiallyOpen: Boolean, lazy: Boolean })
const isMobile = useMobileViewport()
const expanded = ref(props.initiallyOpen)
const visited = ref(props.initiallyOpen)
const toggle = event => {
  if (!isMobile.value) return
  expanded.value = event.target.open
  if (expanded.value) visited.value = true
}
</script>
<template>
  <details class="mobile-section" :class="{ 'is-phone': isMobile }" :open="!isMobile || expanded" @toggle="toggle">
    <summary :aria-hidden="!isMobile" :tabindex="isMobile ? 0 : -1"><span>{{ title }}</span><el-icon><ArrowDown /></el-icon></summary>
    <div v-if="!lazy || !isMobile || visited" class="mobile-section-content"><slot /></div>
  </details>
</template>
<style scoped>
.mobile-section{min-width:0}.mobile-section.is-phone{border-radius:14px;background:var(--zh-background-primary);overflow:clip}
.mobile-section:not(.is-phone)>summary{display:none}
summary{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:58px;padding:14px 16px;color:var(--zh-text-primary);font-size:18px;font-weight:600;cursor:pointer;list-style:none}summary::-webkit-details-marker{display:none}summary .el-icon{flex:none;font-size:19px;color:var(--zh-text-caption);transition:transform .18s}.mobile-section[open]>summary .el-icon{transform:rotate(180deg)}.is-phone .mobile-section-content{padding:0 16px 16px}
</style>
