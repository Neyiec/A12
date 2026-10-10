export const graphNodeWidth = 194
export const graphNodeHeight = 74

export const graphRelationLabel = (relation) => ({
  prerequisite: '先修', contains: '包含', related: '关联', supports: '支撑', applies: '应用', assesses: '评价',
}[relation] || relation || '关联')

/** Rank dependencies after collapsing cycles; association/evaluation edges do not imply a learning order. */
export function layoutLearningGraph(nodes, edges, kind = 'knowledge') {
  const ids = new Set(nodes.map(node => node.id))
  const adjacency = new Map(nodes.map(node => [node.id, []]))
  const ordering = edges.filter(edge => ids.has(edge.source) && ids.has(edge.target) && edge.source !== edge.target
    && !['related', 'assesses', '关联', '相关', '评价', '考核', '相关规律'].includes(edge.relation))
  ordering.forEach(edge => adjacency.get(edge.source).push(edge.target))
  const indexes = new Map(), lows = new Map(), stack = [], onStack = new Set(), groups = []
  let index = 0
  function visit(id) {
    indexes.set(id, index); lows.set(id, index); index += 1
    stack.push(id); onStack.add(id)
    for (const target of adjacency.get(id)) {
      if (!indexes.has(target)) { visit(target); lows.set(id, Math.min(lows.get(id), lows.get(target))) }
      else if (onStack.has(target)) lows.set(id, Math.min(lows.get(id), indexes.get(target)))
    }
    if (lows.get(id) !== indexes.get(id)) return
    const group = []
    let member
    do { member = stack.pop(); onStack.delete(member); group.push(member) } while (member !== id)
    groups.push(group)
  }
  nodes.forEach(node => { if (!indexes.has(node.id)) visit(node.id) })
  const groupOf = new Map()
  groups.forEach((group, groupIndex) => group.forEach(id => groupOf.set(id, groupIndex)))
  const next = groups.map(() => new Set()), incoming = groups.map(() => 0), ranks = groups.map(() => 0)
  for (const edge of ordering) {
    const from = groupOf.get(edge.source), to = groupOf.get(edge.target)
    if (from !== to && !next[from].has(to)) { next[from].add(to); incoming[to] += 1 }
  }
  const queue = incoming.flatMap((count, i) => count === 0 ? [i] : [])
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const from = queue[cursor]
    for (const to of next[from]) {
      ranks[to] = Math.max(ranks[to], ranks[from] + 1)
      incoming[to] -= 1
      if (incoming[to] === 0) queue.push(to)
    }
  }
  const layers = []
  nodes.forEach(node => { (layers[ranks[groupOf.get(node.id)]] ||= []).push(node) })
  const horizontal = kind === 'skill'
  const width = horizontal ? Math.max(760, layers.length * 254 + 56) : 760
  const positions = new Map()
  let offset = 38
  layers.forEach((layer, rank) => {
    if (horizontal) {
      layer.forEach((node, row) => positions.set(node.id, { x: 38 + rank * 254, y: 38 + row * 132 }))
    } else {
      layer.forEach((node, column) => {
        const countInRow = Math.min(3, layer.length - Math.floor(column / 3) * 3)
        const start = (width - countInRow * graphNodeWidth - (countInRow - 1) * 50) / 2
        positions.set(node.id, { x: start + (column % 3) * 244, y: offset + Math.floor(column / 3) * 132 })
      })
      offset += Math.ceil(layer.length / 3) * 132
    }
  })
  const positioned = nodes.map(node => ({ ...node, ...positions.get(node.id) }))
  return { nodes: positioned, width, height: Math.max(160, ...positioned.map(node => node.y + graphNodeHeight + 38)),
    hasCycle: groups.some(group => group.length > 1) }
}
