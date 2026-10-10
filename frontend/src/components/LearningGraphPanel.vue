<script setup>
import { computed, ref, useId, watch } from 'vue'
import LearningGraphEditor from './LearningGraphEditor.vue'
import { graphNodeHeight as nodeHeight, graphNodeWidth as nodeWidth, graphRelationLabel, layoutLearningGraph } from '../utils/learningGraphLayout.js'

const props = defineProps({
  graphs: { type: Object, required: true },
  maxNodes: { type: Number, default: 12 },
  editable: { type: Boolean, default: false },
  confirmable: { type: Boolean, default: false },
  confirming: { type: Boolean, default: false },
  graphSaver: { type: Function, default: null },
  graphAiEditor: { type: Function, default: null },
})
const emit = defineEmits(['node-move', 'confirm'])
const draggedPositions = ref({})
let dragging = null

const activeKind = ref('knowledge')
const selectedNodeId = ref(null)
const editingSkill = ref(false)
const editingKind = ref('skill')
const startWithAI = ref(false)
function openEditor(ai) { editingKind.value = activeKind.value; startWithAI.value = ai; editingSkill.value = true }
watch(() => props.graphs, () => { if (!props.editable) activeKind.value = 'knowledge'; draggedPositions.value = {} })
watch(activeKind, () => { selectedNodeId.value = null })
const activeGraph = computed(() => props.graphs?.[activeKind.value] || { nodes: [], edges: [] })
const nodes = computed(() => Array.isArray(activeGraph.value.nodes) ? activeGraph.value.nodes.slice(0, props.maxNodes) : [])
const edges = computed(() => Array.isArray(activeGraph.value.edges) ? activeGraph.value.edges.slice(0, props.maxNodes * 3) : [])
const layout = computed(() => layoutLearningGraph(nodes.value, edges.value, activeKind.value))
const arrowId = `graph-arrow-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
const sourceText = computed(() => {
  if (props.graphs?.status === 'approved_course') return '教师已确认的课程图谱'
  if (props.graphs?.status === 'ai_proposal') return 'AI 生成草案 · 请核对'
  return '基于当前需求的草案 · 请核对'
})

const positionedNodes = computed(() => layout.value.nodes.map((node) => ({ ...node,
  ...(node.position || {}), ...(draggedPositions.value[node.id] || {}) })))
const canvasWidth = computed(() => Math.max(layout.value.width, ...positionedNodes.value.map(node => node.x + nodeWidth + 38)))
const canvasHeight = computed(() => Math.max(layout.value.height, ...positionedNodes.value.map(node => node.y + nodeHeight + 38)))
const selectedNode = computed(() => nodes.value.find(node => node.id === selectedNodeId.value) || nodes.value[0])
const supportRows = computed(() => {
  const knowledge = new Map((props.graphs?.knowledge?.nodes || []).map(node => [node.id, node.label]))
  const links = [...(props.graphs?.skill?.knowledge_links || [])]
  // The course editor also provides mixed course edges rather than a separate link list.
  for (const edge of props.graphs?.knowledge?.edges || []) {
    if (knowledge.has(edge.source) && ['supports', 'applies', 'prerequisite', '支撑', '支持', '先修', '应用'].includes(edge.relation)) {
      links.push({ knowledge_id: edge.source, skill_id: edge.target })
    }
  }
  return (props.graphs?.skill?.nodes || []).slice(0, props.maxNodes).flatMap(node => {
    const labels = [...new Set(links.filter(link => link.skill_id === node.id).map(link => knowledge.get(link.knowledge_id)).filter(Boolean))]
    return labels.length ? [{ id: node.id, skill: node.label, knowledge: labels.join('、') }] : []
  })
})
function pointerPosition(event) {
  const svg = event.currentTarget.ownerSVGElement
  const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY
  return point.matrixTransform(svg.getScreenCTM().inverse())
}
function beginMove(event, node) {
  if (!props.editable) return
  const point = pointerPosition(event)
  dragging = { id: node.id, dx: point.x - node.x, dy: point.y - node.y }
  event.currentTarget.setPointerCapture(event.pointerId)
}
function moveNode(event) {
  if (!dragging) return
  const point = pointerPosition(event)
  draggedPositions.value = { ...draggedPositions.value, [dragging.id]: {
    x: Math.max(0, Math.min(canvasWidth.value - nodeWidth - 20, point.x - dragging.dx)), y: Math.max(0, Math.min(12000, point.y - dragging.dy)),
  } }
}
function finishMove() {
  if (!dragging) return
  const id = dragging.id, position = draggedPositions.value[id]
  dragging = null
  if (position) emit('node-move', { id, position })
}
const positionedEdges = computed(() => {
  const byId = new Map(positionedNodes.value.map((node) => [node.id, node]))
  return edges.value.flatMap((edge) => {
    const from = byId.get(edge.source)
    const to = byId.get(edge.target)
    if (!from || !to) return []
    const dx = to.x - from.x, dy = to.y - from.y
    const length = Math.hypot(dx, dy)
    if (!length) return []
    const boundary = Math.min(nodeWidth / 2 / (Math.abs(dx) || 1e-9), nodeHeight / 2 / (Math.abs(dy) || 1e-9))
    const x1 = from.x + nodeWidth / 2 + dx * boundary
    const y1 = from.y + nodeHeight / 2 + dy * boundary
    const x2 = to.x + nodeWidth / 2 - dx * (boundary + 7 / length)
    const y2 = to.y + nodeHeight / 2 - dy * (boundary + 7 / length)
    return [{ key: `${edge.source}-${edge.target}`, x1, y1, x2, y2, relation: graphRelationLabel(edge.relation),
      labelX: (x1 + x2) / 2, labelY: (y1 + y2) / 2 }]
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
      <div class="learning-graph-actions">
      <button v-if="confirmable && graphSaver" class="learning-graph-switch" type="button" :disabled="confirming" @click="openEditor(false)">修改{{ activeKind === 'knowledge' ? '知识图谱' : '技能图谱' }}</button>
      <button v-if="confirmable && graphAiEditor" class="learning-graph-switch" type="button" :disabled="confirming" @click="openEditor(true)">让 AI 修改</button>
      <button class="learning-graph-switch" type="button" @click="toggleGraph">
        {{ activeKind === 'knowledge' ? '查看技能图谱' : '查看知识图谱' }}
      </button>
      </div>
    </header>
    <p class="learning-graph-purpose">{{ activeKind === 'knowledge'
      ? '需要理解什么：概念、原理及它们的先修、包含和应用关系。'
      : '能够做什么：从基础操作到分析、迁移的能力递进。点击节点查看课堂任务和达标依据。' }}</p>

    <div class="learning-graph-scroll" :style="{ maxHeight: maxNodes > 12 ? '520px' : '580px', overflow: 'auto' }">
      <svg v-if="nodes.length" class="learning-graph-canvas" :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
           :style="{ width: `${canvasWidth}px` }"
           role="img" :aria-label="`${activeKind === 'knowledge' ? '知识' : '技能'}图谱，共 ${nodes.length} 个节点`">
        <defs>
          <marker :id="arrowId" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#91a7c3" />
          </marker>
        </defs>
        <g v-for="edge in positionedEdges" :key="edge.key">
          <line :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2"
                stroke="#91a7c3" stroke-width="2" :marker-end="`url(#${arrowId})`" />
          <rect :x="edge.labelX - (edge.relation.length * 6 + 7)" :y="edge.labelY - 10"
                :width="edge.relation.length * 12 + 14" height="20" rx="5" fill="white" />
          <text :x="edge.labelX" :y="edge.labelY + 4" text-anchor="middle" fill="#64758c" font-size="11">{{ edge.relation }}</text>
          <title>{{ edge.relation }}</title>
        </g>
        <g v-for="node in positionedNodes" :key="node.id" :style="editable ? 'cursor:grab;touch-action:none' : 'cursor:pointer'"
           role="button" tabindex="0" :aria-label="`查看${node.label}`" :aria-pressed="selectedNode?.id === node.id"
           @click="selectedNodeId = node.id" @keydown.enter.prevent="selectedNodeId = node.id" @keydown.space.prevent="selectedNodeId = node.id"
           @pointerdown="beginMove($event,node)" @pointermove="moveNode" @pointerup="finishMove" @pointercancel="finishMove">
          <rect :x="node.x" :y="node.y" :width="nodeWidth" :height="nodeHeight" rx="16"
                :fill="activeKind === 'knowledge' ? '#f3f7ff' : '#effbf7'"
                :stroke="activeKind === 'knowledge' ? '#92b4ef' : '#85cab3'" :stroke-width="selectedNode?.id === node.id ? 3 : 1.5" />
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
    <p class="learning-graph-note">{{ layout.hasCycle ? '部分节点存在循环依赖，请核对关系。' : '箭头和连线文字表示节点之间的教学关系。' }}</p>
    <div v-if="selectedNode" class="learning-node-detail">
      <strong>{{ selectedNode.label }}</strong>
      <span v-if="selectedNode.category || selectedNode.level || selectedNode.bloom" class="learning-level">{{ selectedNode.category || selectedNode.level || ({ remember: '记忆', understand: '理解', apply: '应用', analyze: '分析', evaluate: '评价', create: '创造' }[selectedNode.bloom] || selectedNode.bloom) }}</span>
      <p v-if="selectedNode.description">{{ selectedNode.description }}</p>
      <p v-if="activeKind === 'skill'"><b>课堂任务：</b>{{ selectedNode.task || '待教师补充具体课堂任务' }}</p>
      <p v-if="activeKind === 'skill' || selectedNode.mastery_standard"><b>达标依据：</b>{{ selectedNode.assessment || selectedNode.mastery_standard || '待教师补充达标依据' }}</p>
    </div>
    <details v-if="supportRows.length" class="learning-support">
      <summary>知识与技能的支撑关系（{{ supportRows.length }} 项能力）</summary>
      <dl><template v-for="row in supportRows" :key="row.id"><dt>{{ row.skill }}</dt><dd>支撑知识：{{ row.knowledge }}</dd></template></dl>
    </details>
    <div v-if="confirmable && !editingSkill" class="learning-graph-confirm">
      <span>请切换查看两张图谱，核对内容后再生成大纲。</span>
      <button type="button" :disabled="confirming" @click="emit('confirm')">
        {{ confirming ? '正在生成大纲…' : '确认双图谱，生成大纲' }}
      </button>
    </div>
    <LearningGraphEditor v-if="editingSkill" :graphs="graphs" :kind="editingKind" :save="graphSaver" :ai-edit="graphAiEditor" :start-with-ai="startWithAI" @close="editingSkill = false; activeKind = editingKind" />
  </section>
</template>

<style scoped>
.learning-graph-panel { width: min(100%, 820px); box-sizing: border-box; margin: 20px 0; border: 1px solid #e4e9f0; border-radius: 20px; padding: 18px 20px 14px; background: #fff; box-shadow: 0 10px 28px rgba(25, 52, 90, .05); }
.learning-graph-header { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.learning-graph-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.learning-graph-header strong { font-size: 17px; color: #172b48; }
.learning-graph-header p { margin: 5px 0 0; font-size: 12px; color: #6b7890; }
.learning-graph-switch { flex: none; border: 1px solid #c9d8f3; border-radius: 999px; background: #f4f8ff; color: #275cc7; padding: 8px 13px; font: inherit; font-size: 13px; cursor: pointer; }
.learning-graph-switch:hover { background: #e8f0ff; }
.learning-graph-switch:focus-visible { outline: 2px solid #275cc7; outline-offset: 2px; }
.learning-graph-scroll { overflow-x: auto; margin-top: 12px; }
.learning-graph-canvas { display: block; max-width: none; height: auto; }
.learning-graph-purpose { margin: 12px 0 0; color: #65748b; font-size: 12px; line-height: 1.7; }
.learning-node-detail { margin-top: 12px; padding: 12px 14px; border-radius: 12px; background: #f8fafc; font-size: 12px; color: #354761; }
.learning-node-detail p { margin: 7px 0 0; line-height: 1.7; }
.learning-level { display: inline-block; margin-left: 8px; color: #207b5b; font-size: 11px; }
.learning-support { margin-top: 12px; color: #54677f; font-size: 12px; }
.learning-support summary { cursor: pointer; padding: 7px 0; }
.learning-support dl { margin: 6px 0; }
.learning-support dt { margin-top: 10px; font-weight: 600; }
.learning-support dd { margin: 4px 0 0; line-height: 1.7; }
.learning-graph-empty { padding: 28px 0; text-align: center; color: #768297; }
.learning-graph-note { margin: 6px 0 0; color: #8490a0; font-size: 11px; }
.learning-graph-confirm { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; }
.learning-graph-confirm span { color: #65748b; font-size: 12px; }
.learning-graph-confirm button { border: 0; border-radius: 9px; padding: 9px 14px; color: #fff; background: #2862d8; cursor: pointer; font: inherit; font-size: 13px; }
.learning-graph-confirm button:disabled { opacity: .65; cursor: wait; }
@media (max-width: 600px) and (hover: none) and (pointer: coarse) { .learning-graph-panel { padding: 14px; } .learning-graph-header { align-items: flex-start; } .learning-graph-switch { font-size: 12px; padding: 7px 10px; } }
</style>
