<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { secureHtmlForSandbox } from '../utils/htmlSecurity'

const props = defineProps({ slide: { type: Object, required: true }, decorative: Boolean })
const frame = ref(null)
const width = ref(0)
let observer
watch(frame, element => {
  observer?.disconnect()
  if (!element) return
  width.value = element.clientWidth
  observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width })
  observer.observe(element)
}, { flush: 'post' })
onBeforeUnmount(() => observer?.disconnect())
const srcdoc = computed(() => secureHtmlForSandbox(props.slide.html))
const elements = computed(() => Array.isArray(props.slide.elements) ? props.slide.elements : [])
const background = computed(() => typeof props.slide.background === 'string' ? props.slide.background : props.slide.background?.color || '#fff')
const elementStyle = element => {
  const position = element.position || {}
  const style = element.style || {}
  return {
    left: `${Number(position.x) || 0}%`, top: `${Number(position.y) || 0}%`,
    width: `${Number(position.width) || 30}%`, height: `${Number(position.height) || 15}%`,
    transform: `rotate(${Number(position.rotation) || 0}deg)`, zIndex: Number(position.zIndex) || 0,
    color: style.color, background: style.fillColor || style.backgroundColor,
    fontSize: `${Number(style.fontSize) || 24}px`, fontWeight: style.fontWeight || 400,
    textAlign: style.textAlign || 'left', lineHeight: style.lineHeight || 1.4,
    opacity: style.opacity == null ? 1 : Number(style.opacity) / 100,
    border: `${Number(style.borderWidth) || 0}px solid ${style.borderColor || 'transparent'}`,
    borderRadius: element.shapeKind === 'circle' ? '50%' : `${Number(style.borderRadius) || 0}px`,
    objectFit: style.objectFit || 'contain',
    clipPath: element.shapeKind === 'triangle' ? 'polygon(50% 0,100% 100%,0 100%)' : element.shapeKind === 'diamond' ? 'polygon(50% 0,100% 50%,50% 100%,0 50%)' : undefined,
  }
}
</script>

<template>
  <div ref="frame" class="slide-preview-frame" :aria-hidden="decorative ? 'true' : undefined">
    <div class="slide-preview-canvas" :style="{ transform: `scale(${width / 1280})`, background }">
      <!-- Generated content is isolated and cannot edit the app or make network requests. -->
      <iframe v-if="srcdoc" :title="slide.title" :srcdoc="srcdoc" sandbox="allow-scripts" tabindex="-1" />
      <template v-else-if="elements.length">
        <template v-for="(element, index) in elements" :key="element.id || index">
          <img v-if="element.type === 'image'" class="slide-element" :style="elementStyle(element)" :src="element.src" alt="" />
          <div v-else-if="element.type === 'chart'" class="slide-element legacy-chart" :style="elementStyle(element)"><strong>{{ element.content }}</strong><div class="legacy-bars"><div v-for="(bar, barIndex) in (element.data || [])" :key="barIndex"><i :style="{ height: `${Math.max(0, Math.min(100, Number(bar.value) || 0))}%`, background: element.style?.color || '#2563eb' }" /><span>{{ bar.label }}</span></div></div></div>
          <div v-else-if="element.type === 'table'" class="slide-element legacy-table" :style="elementStyle(element)"><strong>{{ element.content }}</strong><table><tbody><tr v-for="(row, rowIndex) in (Array.isArray(element.data) ? element.data : [])" :key="rowIndex"><td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td></tr></tbody></table></div>
          <div v-else class="slide-element" :style="elementStyle(element)">{{ element.content || element.text || '' }}</div>
        </template>
      </template>
      <div v-else class="slide-unavailable"><strong>{{ slide.title }}</strong><span>此页暂无可预览内容</span></div>
    </div>
  </div>
</template>

<style scoped>
.slide-preview-frame{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;background:#fff;border-radius:inherit;pointer-events:none}
.slide-preview-canvas{position:absolute;top:0;left:0;width:1280px;height:720px;transform-origin:top left;overflow:hidden;color:#172b4d}
iframe{display:block;width:1280px;height:720px;border:0;background:#fff}
.slide-element{position:absolute;white-space:pre-wrap;overflow:hidden}
.legacy-chart{padding:18px;display:flex;flex-direction:column;gap:12px}.legacy-chart>strong{font-size:20px}.legacy-bars{flex:1;min-height:0;display:flex;gap:18px}.legacy-bars>div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;position:relative;padding-bottom:25px}.legacy-bars i{display:block;width:65%;border-radius:6px 6px 0 0}.legacy-bars span{position:absolute;bottom:0;font-size:15px;color:#607491}.legacy-table{padding:16px;font-size:20px}.legacy-table table{width:100%;border-collapse:collapse;margin-top:10px}.legacy-table td{border:1px solid #bfdbfe;padding:8px}
.slide-unavailable{height:100%;display:grid;place-content:center;gap:24px;text-align:center;font-size:30px}.slide-unavailable strong{font-size:48px}
</style>
