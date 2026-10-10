import test from 'node:test'
import assert from 'node:assert/strict'
import { layoutLearningGraph } from '../src/utils/learningGraphLayout.js'

test('分层由依赖关系决定，支持分支汇合而非按数组顺序排布', () => {
  const nodes = [{ id: 'result' }, { id: 'prerequisite-a' }, { id: 'prerequisite-b' }]
  const edges = [{ source: 'prerequisite-a', target: 'result', relation: '先修' },
                 { source: 'prerequisite-b', target: 'result', relation: '先修' }]
  const knowledge = layoutLearningGraph(nodes, edges, 'knowledge')
  const byId = new Map(knowledge.nodes.map(node => [node.id, node]))
  assert.equal(byId.get('prerequisite-a').y, byId.get('prerequisite-b').y)
  assert.ok(byId.get('result').y > byId.get('prerequisite-a').y)
  assert.notEqual(byId.get('prerequisite-a').x, byId.get('prerequisite-b').x)
  const skill = layoutLearningGraph(nodes, edges, 'skill')
  const skillById = new Map(skill.nodes.map(node => [node.id, node]))
  assert.ok(skillById.get('result').x > skillById.get('prerequisite-a').x)
})

test('评价回边保留展示，但不改变能力递进的分层', () => {
  const graph = layoutLearningGraph([{ id: 'use' }, { id: 'test' }], [
    { source: 'use', target: 'test', relation: 'prerequisite' },
    { source: 'test', target: 'use', relation: 'assesses' },
  ], 'skill')
  assert.equal(graph.hasCycle, false)
  assert.ok(graph.nodes[1].x > graph.nodes[0].x)
})

test('循环依赖也能完成布局，孤立节点不丢失或重叠', () => {
  const graph = layoutLearningGraph([{ id: 'a' }, { id: 'b' }, { id: 'isolated' }], [
    { source: 'a', target: 'b', relation: '先修' }, { source: 'b', target: 'a', relation: '先修' },
  ], 'knowledge')
  assert.equal(graph.hasCycle, true)
  assert.equal(new Set(graph.nodes.map(node => `${node.x},${node.y}`)).size, 3)
  assert.ok(graph.nodes.every(node => Number.isFinite(node.x) && Number.isFinite(node.y)))
})
