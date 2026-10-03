<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { diagramSvgMarkup, parseMermaidDiagram } from '../utils/subjectTool'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const mode = ref('visual')
const sourceInput = ref(null)
const lastSourceSelection = ref(null)
const insertError = ref('')
const directions = ['LR', 'RL', 'TB', 'BT']
const shapePairs = { rect: ['[', ']'], round: ['(', ')'], diamond: ['{', '}'] }
const sourceSnippets = [
  { label: '矩形', title: '插入矩形节点', kind: 'node', open: '[', close: ']', placeholder: '节点' },
  { label: '圆角', title: '插入圆角节点', kind: 'node', open: '(', close: ')', placeholder: '节点' },
  { label: '判断', title: '插入判断节点', kind: 'node', open: '{', close: '}', placeholder: '条件' },
  { label: '→', title: '插入有向连线', insert: ' --> ' },
  { label: '—', title: '插入无向连线', insert: ' --- ' },
  { label: '条件', title: '插入连线条件', insert: '|条件|', selection: [1, 3] },
  { label: '↵', title: '插入换行', insert: '\n' },
]
const graph = computed(() => parseMermaidDiagram(props.modelValue))
const diagramMarkup = computed(() => diagramSvgMarkup(props.modelValue))
const diagramError = computed(() => {
  const source = String(props.modelValue || '').trim()
  if (!source) return '请输入 Mermaid 流程图内容。'
  if (!/^(?:flowchart|graph)\s+/i.test(source)) return ''
  if ([...source].filter((char) => char === '|').length % 2) return '连线文字标记 | 没有成对闭合。'
  if (/(?:-->|---|==>|-\.->|<--)/.test(source) && !graph.value.edges.length) return '没有识别到有效连线，请检查节点 ID 和箭头语法。'
  return ''
})
const diagramWarning = computed(() => {
  const source = String(props.modelValue || '').trim()
  return source && !/^(?:flowchart|graph)\s+/i.test(source)
    ? '源码已保留；此画布的本地预览目前只绘制 flowchart / graph 流程图。'
    : ''
})
const safeLabel = (value) => String(value || '').replace(/[\r\n\[\]{}()]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 32) || '未命名节点'
const editableNodeId = (fragment) => {
  const match = String(fragment || '').trim().match(/^([A-Za-z][A-Za-z0-9_-]*)(?:\[([^\[\]]+)\]|\(([^()]+)\)|\{([^{}]+)\})?$/)
  if (!match) return ''
  const label = match[2] ?? match[3] ?? match[4]
  if (label !== undefined && (
    label.length > 32 || label !== safeLabel(label) || /["'|;%`]/.test(label)
  )) return ''
  return match[1]
}
const visualEditRestriction = computed(() => {
  const source = String(props.modelValue || '').trim()
  if (!source) return ''
  const lines = source.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (!/^flowchart\s+(?:LR|RL|TB|TD|BT)$/i.test(lines[0])) {
    return '当前源码不是基础 flowchart，须在 Mermaid 源码模式编辑，原文会保留。'
  }
  const nodeIds = new Set()
  let edgeCount = 0
  for (const line of lines.slice(1)) {
    const edge = line.match(/^(.+?)\s+-->(?:\|([^|]*)\|)?\s+(.+)$/)
    if (edge) {
      const from = editableNodeId(edge[1])
      const to = editableNodeId(edge[3])
      const label = edge[2] ?? ''
      if (!from || !to || label.length > 24 || (label && label !== safeLabel(label))) {
        return '源码含有可视化编辑器未支持的 Mermaid 语法，须在源码模式编辑，原文会保留。'
      }
      nodeIds.add(from)
      nodeIds.add(to)
      edgeCount += 1
    } else {
      const id = editableNodeId(line)
      if (!id) return '源码含有注释、样式、子图或其他高级 Mermaid 语法，须在源码模式编辑，原文会保留。'
      nodeIds.add(id)
    }
  }
  if (nodeIds.size > 8 || edgeCount > 12) {
    return '源码超过可视化编辑器的 8 个节点或 12 条连线上限，须在源码模式编辑，原文会保留。'
  }
  if (graph.value.nodes.length !== nodeIds.size || graph.value.edges.length !== edgeCount) {
    return '源码包含未被本地解析器完整识别的内容，须在源码模式编辑，原文会保留。'
  }
  return ''
})
watch(visualEditRestriction, (restriction) => {
  if (restriction) mode.value = 'source'
}, { immediate: true })
const definition = (node) => {
  const [open, close] = shapePairs[node.shape] || shapePairs.rect
  return `${node.id}${open}${safeLabel(node.label)}${close}`
}
const serialize = (next) => {
  if (visualEditRestriction.value) return
  const direction = directions.includes(next.direction) ? next.direction : 'LR'
  const edgeNodes = new Set(next.edges.flatMap((edge) => [edge.from, edge.to]))
  const lines = [`flowchart ${direction}`]
  next.edges.forEach((edge) => {
    const from = next.nodes.find((node) => node.id === edge.from)
    const to = next.nodes.find((node) => node.id === edge.to)
    if (!from || !to) return
    const connector = edge.label ? ` -->|${safeLabel(edge.label)}| ` : ' --> '
    lines.push(`${definition(from)}${connector}${definition(to)}`)
  })
  next.nodes.filter((node) => !edgeNodes.has(node.id)).forEach((node) => lines.push(definition(node)))
  emit('update:modelValue', lines.join('\n'))
}
const updateNode = (index, key, value) => {
  const next = { ...graph.value, nodes: graph.value.nodes.map((node, itemIndex) => itemIndex === index ? { ...node, [key]: key === 'label' ? safeLabel(value) : value } : { ...node }) }
  serialize(next)
}
const addNode = () => {
  if (graph.value.nodes.length >= 8) return
  const nodeIds = new Set(graph.value.nodes.map((node) => node.id))
  let sequence = graph.value.nodes.length + 1
  let id = `N${sequence}`
  while (nodeIds.has(id)) { sequence += 1; id = `N${sequence}` }
  const node = { id, label: `节点 ${graph.value.nodes.length + 1}`, shape: 'rect' }
  const nodes = [...graph.value.nodes, node]
  const previous = graph.value.nodes.at(-1)
  const edges = previous ? [...graph.value.edges, { from: previous.id, to: id, label: '' }] : [...graph.value.edges]
  serialize({ ...graph.value, nodes, edges })
}
const removeNode = (index) => {
  if (graph.value.nodes.length <= 1) return
  const node = graph.value.nodes[index]
  serialize({ ...graph.value, nodes: graph.value.nodes.filter((_, itemIndex) => itemIndex !== index), edges: graph.value.edges.filter((edge) => edge.from !== node.id && edge.to !== node.id) })
}
const updateEdge = (index, key, value) => serialize({
  ...graph.value,
  edges: graph.value.edges.map((edge, edgeIndex) => edgeIndex === index ? { ...edge, [key]: value } : { ...edge }),
})
const addEdge = () => {
  if (graph.value.nodes.length < 2 || graph.value.edges.length >= 12) return
  const from = graph.value.nodes[0].id
  const to = graph.value.nodes[graph.value.nodes.length - 1].id
  if (from === to) return
  serialize({ ...graph.value, edges: [...graph.value.edges, { from, to, label: '' }] })
}
const getSourceTextarea = () => sourceInput.value?.$el?.querySelector('textarea') || null
const captureSourceSelection = () => {
  const textarea = getSourceTextarea()
  if (!textarea) return
  lastSourceSelection.value = { start: textarea.selectionStart, end: textarea.selectionEnd }
}
const updateSource = (value) => {
  insertError.value = ''
  emit('update:modelValue', value)
}
const nextSourceNodeId = (source) => {
  let number = 1
  while (new RegExp(`\\bN${number}\\b`).test(source)) number += 1
  return `N${number}`
}
const insertSourceSnippet = async (item) => {
  const current = String(props.modelValue || '')
  const textarea = getSourceTextarea()
  const selection = textarea && document.activeElement === textarea
    ? { start: textarea.selectionStart, end: textarea.selectionEnd }
    : (lastSourceSelection.value || { start: current.length, end: current.length })
  const start = Math.min(selection.start, current.length)
  const end = Math.min(Math.max(selection.end, start), current.length)
  const nodeId = item.kind === 'node' ? nextSourceNodeId(current) : ''
  const before = current.slice(0, start)
  const after = current.slice(end)
  const leadingBreak = item.kind === 'node'
    ? (!current.trim() ? 'flowchart LR\n' : before && !before.endsWith('\n') ? '\n' : '')
    : ''
  const trailingBreak = item.kind === 'node' && after && !after.startsWith('\n') ? '\n' : ''
  const inserted = item.kind === 'node'
    ? `${leadingBreak}${nodeId}${item.open}${item.placeholder}${item.close}${trailingBreak}`
    : item.insert
  const next = `${current.slice(0, start)}${inserted}${current.slice(end)}`
  if (next.length > 8000) {
    insertError.value = 'Mermaid 源码最多 8,000 个字符，无法插入此内容。'
    return
  }
  insertError.value = ''
  emit('update:modelValue', next)
  await nextTick()
  const nextTextarea = getSourceTextarea()
  if (!nextTextarea) return
  nextTextarea.focus()
  const relativeStart = item.kind === 'node' ? leadingBreak.length + nodeId.length + 1 : (item.selection?.[0] ?? inserted.length)
  const relativeEnd = item.kind === 'node' ? relativeStart + item.placeholder.length : (item.selection?.[1] ?? relativeStart)
  nextTextarea.setSelectionRange(start + relativeStart, start + relativeEnd)
  lastSourceSelection.value = { start: start + relativeStart, end: start + relativeEnd }
}
</script>

<template>
  <div class="subject-diagram-editor">
    <div class="diagram-mode-tabs" role="tablist" aria-label="流程图编辑模式">
      <button type="button" role="tab" :aria-selected="mode === 'visual'" :class="{ active: mode === 'visual' }" :disabled="!!visualEditRestriction" :title="visualEditRestriction || '切换到可视化编辑'" @click="mode = 'visual'">可视化编辑</button>
      <button type="button" role="tab" :aria-selected="mode === 'source'" :class="{ active: mode === 'source' }" @click="mode = 'source'">Mermaid 源码</button>
    </div>
    <p v-if="visualEditRestriction" class="diagram-editor-help" role="status">{{ visualEditRestriction }}</p>

    <template v-if="mode === 'visual'">
      <div class="diagram-quick-actions" aria-label="流程图快捷操作">
        <el-button :disabled="graph.nodes.length >= 8" title="添加节点，并自动连接前一个节点" @click="addNode">＋ 添加节点</el-button>
        <el-button :disabled="graph.nodes.length < 2 || graph.edges.length >= 12" title="在第一个与最后一个节点之间添加连线" @click="addEdge">＋ 添加连线</el-button>
      </div>
      <label class="diagram-direction-field">布局方向
        <el-select :model-value="graph.direction" @update:model-value="serialize({ ...graph, direction: $event })">
          <el-option label="从左到右" value="LR" /><el-option label="从右到左" value="RL" /><el-option label="从上到下" value="TB" /><el-option label="从下到上" value="BT" />
        </el-select>
      </label>
      <div class="diagram-section-heading"><strong>流程节点</strong><span>{{ graph.nodes.length }} / 8</span></div>
      <div class="diagram-node-list">
        <div v-for="(node, index) in graph.nodes" :key="node.id" class="diagram-node-row">
          <code>{{ node.id }}</code>
          <el-input :model-value="node.label" maxlength="32" :aria-label="`${node.id} 节点名称`" @update:model-value="updateNode(index, 'label', $event)" />
          <el-select :model-value="node.shape" :aria-label="`${node.id} 节点形状`" @update:model-value="updateNode(index, 'shape', $event)">
            <el-option label="矩形" value="rect" /><el-option label="圆角" value="round" /><el-option label="判断" value="diamond" />
          </el-select>
          <el-button text circle :disabled="graph.nodes.length <= 1" :aria-label="`删除 ${node.id}`" @click="removeNode(index)">×</el-button>
        </div>
      </div>
      <div class="diagram-section-heading"><strong>连线与条件</strong><span>{{ graph.edges.length }} 条</span></div>
      <div v-if="graph.edges.length" class="diagram-edge-list">
        <div v-for="(edge, index) in graph.edges" :key="`${edge.from}-${edge.to}-${index}`" class="diagram-edge-row">
          <el-select :model-value="edge.from" :aria-label="`第 ${index + 1} 条连线起点`" @update:model-value="updateEdge(index, 'from', $event)"><el-option v-for="node in graph.nodes" :key="node.id" :label="node.label || node.id" :value="node.id" /></el-select>
          <span>→</span>
          <el-select :model-value="edge.to" :aria-label="`第 ${index + 1} 条连线终点`" @update:model-value="updateEdge(index, 'to', $event)"><el-option v-for="node in graph.nodes" :key="node.id" :label="node.label || node.id" :value="node.id" /></el-select>
          <el-input :model-value="edge.label" maxlength="24" placeholder="条件（选填）" :aria-label="`第 ${index + 1} 条连线条件`" @update:model-value="updateEdge(index, 'label', $event)" />
          <el-button text circle :aria-label="`删除第 ${index + 1} 条连线`" @click="serialize({ ...graph, edges: graph.edges.filter((_, edgeIndex) => edgeIndex !== index) })">×</el-button>
        </div>
      </div>
      <div class="diagram-live-preview" aria-label="流程图实时预览" v-html="diagramMarkup"></div>
      <p v-if="diagramError" class="diagram-editor-error" role="alert">{{ diagramError }}</p>
      <p class="diagram-editor-help">本地预览支持基础 flowchart / graph 的节点、方向、连线与条件文字。高级 Mermaid 语法请在源码模式编辑。</p>
    </template>

    <template v-else>
      <div class="diagram-source-toolbox" aria-label="常用 Mermaid 片段">
        <span class="diagram-source-toolbox-label">点击插入</span>
        <button
          v-for="item in sourceSnippets"
          :key="item.title"
          type="button"
          class="diagram-source-tool"
          :title="item.title"
          :aria-label="item.title"
          @mousedown.prevent="captureSourceSelection"
          @click="insertSourceSnippet(item)"
        >{{ item.label }}</button>
      </div>
      <el-input ref="sourceInput" :model-value="modelValue" type="textarea" :rows="8" maxlength="8000" show-word-limit aria-label="Mermaid 流程图源码" placeholder="flowchart LR&#10;A[提出问题] --> B[观察与探究]" @update:model-value="updateSource" @click="captureSourceSelection" @keyup="captureSourceSelection" @select="captureSourceSelection" @blur="captureSourceSelection" />
      <p v-if="insertError" class="diagram-editor-error" role="alert">{{ insertError }}</p>
      <div class="diagram-live-preview" aria-label="Mermaid 流程图实时预览" v-html="diagramMarkup"></div>
      <p v-if="diagramError" class="diagram-editor-error" role="alert">{{ diagramError }}</p>
      <p v-else-if="diagramWarning" class="diagram-editor-help" role="status">{{ diagramWarning }}</p>
      <p class="diagram-editor-help">本地预览仅识别基础 flowchart / graph 的节点、方向、连线与条件文字；注释、样式、子图等高级语法不会完整渲染，源码会保留。</p>
    </template>
  </div>
</template>

<style scoped>
.subject-diagram-editor { display: grid; gap: 9px; }
.diagram-mode-tabs { display: inline-flex; justify-self: start; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.diagram-mode-tabs button { padding: 5px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; font-size: 10px; cursor: pointer; }
.diagram-mode-tabs button.active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: 0 1px 3px rgb(15 23 42 / 10%); font-weight: 700; }
.diagram-mode-tabs button:disabled { color: var(--zh-text-caption); opacity: .55; cursor: not-allowed; }
.diagram-direction-field { display: grid; gap: 6px; color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.diagram-quick-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.diagram-quick-actions :deep(.el-button) { width: 100%; margin: 0; }
.diagram-source-toolbox { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; padding: 7px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-light); }
.diagram-source-toolbox-label { flex-basis: 100%; color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.diagram-source-tool { min-width: 29px; min-height: 27px; padding: 4px 7px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-secondary); background: var(--zh-background-primary); font-size: 10px; cursor: pointer; }
.diagram-source-tool:hover, .diagram-source-tool:focus-visible { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.diagram-section-heading { display: flex; align-items: baseline; justify-content: space-between; color: var(--zh-text-secondary); font-size: 10px; }
.diagram-section-heading span, .diagram-editor-help { color: var(--zh-text-caption); font-size: 9px; }
.diagram-node-list, .diagram-edge-list { display: grid; gap: 6px; }
.diagram-node-row { display: grid; grid-template-columns: 30px minmax(0,1fr) 75px 28px; align-items: center; gap: 5px; }
.diagram-node-row code { color: var(--zh-text-caption); font: 9px var(--zh-font-number); }
.diagram-node-row :deep(.el-button), .diagram-edge-row :deep(.el-button) { width: 28px; height: 28px; margin: 0; color: var(--zh-text-caption); font-size: 17px; }
.diagram-edge-row { display: grid; grid-template-columns: minmax(65px,1fr) 10px minmax(65px,1fr) minmax(70px,1fr) 28px; align-items: center; gap: 4px; }
.diagram-edge-row > span { color: var(--zh-text-caption); text-align: center; }
.diagram-live-preview { min-height: 110px; padding: 5px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.diagram-live-preview :deep(span[role="status"]) { display: grid; place-items: center; min-height: 98px; color: var(--zh-text-caption); font-size: 10px; text-align: center; }
.diagram-live-preview :deep(svg) { display: block; width: 100%; max-height: 190px; }
.diagram-live-preview :deep(.diagram-edges path) { fill: none; stroke: #8aa2c1; stroke-width: 2; }
.diagram-live-preview :deep(marker path) { fill: #8aa2c1; }
.diagram-live-preview :deep(.diagram-node rect), .diagram-live-preview :deep(.diagram-node polygon) { fill: #eff6ff; stroke: #93b9ec; stroke-width: 1.5; }
.diagram-live-preview :deep(.diagram-node text) { fill: #24558d; font: 12px "Microsoft YaHei",Arial,sans-serif; text-anchor: middle; }
.diagram-live-preview :deep(.edge-label) { fill: #607491; font: 10px "Microsoft YaHei",Arial,sans-serif; text-anchor: middle; }
.diagram-editor-error { margin: 0; color: var(--el-color-danger); font-size: 10px; line-height: 1.5; }
.diagram-editor-help { margin: 0; line-height: 1.5; }
</style>
