<script setup>
import { computed, ref, useId, watch } from 'vue'

const props = defineProps({
  graphs: { type: Object, required: true },
})

const activeKind = ref('knowledge')
watch(() => props.graphs, () => { activeKind.value = 'knowledge' })
const activeGraph = computed(() => props.graphs?.[activeKind.value] || { nodes: [], edges: [] })
const nodes = computed(() => Array.isArray(activeGraph.value.nodes) ? activeGraph.value.nodes.slice(0, 12) : [])
const edges = computed(() => Array.isArray(activeGraph.value.edges) ? activeGraph.value.edges.slice(0, 24) : [])
const columns = 3
const nodeWidth = 194
const nodeHeight = 74
const columnGap = 244
const rowGap = 116
const canvasWidth = 760
const canvasHeight = computed(() => Math.max(144, Math.ceil(nodes.value.length / columns) * rowGap + 38))
const arrowId = `graph-arrow-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
const sourceText = computed(() => {
  if (props.graphs?.status === 'approved_course') return '已审核课程图谱'
  if (props.graphs?.status === 'ai_proposal') return 'AI 生成草案 · 请核对'
  return '基于当前需求的草案 · 请核对'
})

function position(index) {
  return { x: 38 + (index % columns) * columnGap, y: 30 + Math.floor(index / columns) * rowGap }
}

const positionedNodes = computed(() => nodes.value.map((node, index) => ({ ...node, ...position(index) })))
const positionedEdges = computed(() => {
  const byId = new Map(positionedNodes.value.map((node) => [node.id, node]))
  return edges.value.flatMap((edge) => {
    const from = byId.get(edge.source)
    const to = byId.get(edge.target)
    if (!from || !to) return []
    const forward = to.y > from.y
    const x1 = from.x + nodeWidth / 2
    const y1 = forward ? from.y + nodeHeight : from.y + nodeHeight / 2
    const x2 = to.x + nodeWidth / 2
    const y2 = forward ? to.y - 7 : to.y + nodeHeight / 2
    return [{ key: `${edge.source}-${edge.target}`, x1, y1, x2, y2, relation: edge.relation }]
  })
})

function shortLines(label) {
  const chars = Array.from(String(label || ''))
  return [chars.slice(0, 12).join(''), chars.length > 12 ? chars.slice(12, 24).join('') + (chars.length > 24 ? '…' : '') : ''].filter(Boolean)
}

function toggleGraph() {
  activeKind.value = activeKind.value === 'knowledge' ? 'skill' : 'knowledge'
}
</script>

<template>
  <section class="learning-graph-panel" aria-label="教学图谱">
    <header class="learning-graph-header">
      <div>
        <strong>{{ activeKind === 'knowledge' ? '知识图谱' : '技能图谱' }}</strong>
        <p>{{ sourceText }}</p>
      </div>
      <button class="learning-graph-switch" type="button" @click="toggleGraph">
        {{ activeKind === 'knowledge' ? '查看技能图谱' : '查看知识图谱' }}
      </button>
    </header>

    <div class="learning-graph-scroll">
      <svg v-if="nodes.length" class="learning-graph-canvas" :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
           role="img" :aria-label="`${activeKind === 'knowledge' ? '知识' : '技能'}图谱，共 ${nodes.length} 个节点`">
        <defs>
          <marker :id="arrowId" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#91a7c3" />
          </marker>
        </defs>
        <g v-for="edge in positionedEdges" :key="edge.key">
          <line :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2"
                stroke="#91a7c3" stroke-width="2" :marker-end="`url(#${arrowId})`" />
          <title>{{ edge.relation }}</title>
        </g>
        <g v-for="node in positionedNodes" :key="node.id">
          <rect :x="node.x" :y="node.y" :width="nodeWidth" :height="nodeHeight" rx="16"
                :fill="activeKind === 'knowledge' ? '#f3f7ff' : '#effbf7'"
                :stroke="activeKind === 'knowledge' ? '#92b4ef' : '#85cab3'" stroke-width="1.5" />
          <text :x="node.x + nodeWidth / 2" :y="node.y + (shortLines(node.label).length === 1 ? 44 : 33)"
                text-anchor="middle" fill="#203450" font-size="15" font-weight="600">
            <tspan v-for="(line, index) in shortLines(node.label)" :key="index"
                   :x="node.x + nodeWidth / 2" :dy="index ? 22 : 0">{{ line }}</tspan>
          </text>
          <title>{{ node.label }}{{ node.description ? `：${node.description}` : '' }}</title>
        </g>
      </svg>
      <p v-else class="learning-graph-empty">暂无可展示的{{ activeKind === 'knowledge' ? '知识' : '技能' }}节点</p>
    </div>
    <p class="learning-graph-note">箭头表示先修、包含或能力递进关系；具体关系可将鼠标移至连线上查看。</p>
  </section>
</template>

<style scoped>
.learning-graph-panel { width: min(100%, 820px); box-sizing: border-box; margin: 20px 0; border: 1px solid #e4e9f0; border-radius: 20px; padding: 18px 20px 14px; background: #fff; box-shadow: 0 10px 28px rgba(25, 52, 90, .05); }
.learning-graph-header { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.learning-graph-header strong { font-size: 17px; color: #172b48; }
.learning-graph-header p { margin: 5px 0 0; font-size: 12px; color: #6b7890; }
.learning-graph-switch { flex: none; border: 1px solid #c9d8f3; border-radius: 999px; background: #f4f8ff; color: #275cc7; padding: 8px 13px; font: inherit; font-size: 13px; cursor: pointer; }
.learning-graph-switch:hover { background: #e8f0ff; }
.learning-graph-switch:focus-visible { outline: 2px solid #275cc7; outline-offset: 2px; }
.learning-graph-scroll { overflow-x: auto; margin-top: 12px; }
.learning-graph-canvas { display: block; width: 100%; min-width: 620px; height: auto; }
.learning-graph-empty { padding: 28px 0; text-align: center; color: #768297; }
.learning-graph-note { margin: 6px 0 0; color: #8490a0; font-size: 11px; }
@media (max-width: 600px) and (hover: none) and (pointer: coarse) { .learning-graph-panel { padding: 14px; } .learning-graph-header { align-items: flex-start; } .learning-graph-switch { font-size: 12px; padding: 7px 10px; } }
</style>
