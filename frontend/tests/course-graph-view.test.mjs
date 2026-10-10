import test from 'node:test'
import assert from 'node:assert/strict'
import { courseGraphView } from '../src/utils/courseGraphView.js'
test('course views separate concept and skill topology while retaining support links', () => {
  const nodes = [{id:'k1',kind:'concept'},{id:'k2',kind:'concept'},
    {id:'s1',kind:'skill',task:'画光路',mastery_standard:'角度标注准确'},{id:'s2',kind:'skill'}]
  const edges = [{source:'k1',target:'k2',relation:'contains'},
    {source:'s1',target:'s2',relation:'prerequisite'},{source:'k2',target:'s1',relation:'supports'}]
  const view = courseGraphView(nodes, edges, true)
  assert.equal(view.knowledge.edges.length, 1)
  assert.equal(view.skill.edges.length, 1)
  assert.equal(view.skill.knowledge_links[0].knowledge_id, 'k2')
  assert.equal(view.skill.nodes[0].task, '画光路')
  assert.equal(view.skill.nodes[0].assessment, '角度标注准确')
  assert.equal(view.status, 'approved_course')
})
