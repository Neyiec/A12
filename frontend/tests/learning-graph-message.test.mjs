import test from 'node:test'
import assert from 'node:assert/strict'

import { upsertLearningGraphMessage } from '../src/utils/learningGraphMessage.js'

test('SSE 双图谱首次展示与大纲完成后的更新使用同一数据结构', () => {
  const messages = []
  const addMessage = (role, type, content, data) => {
    const message = { id: messages.length + 1, role, type, content, data }
    messages.push(message)
    return message
  }
  const first = { knowledge: { nodes: [{ id: 'k1' }] }, skill: { nodes: [{ id: 's1' }] } }
  const id = upsertLearningGraphMessage(messages, first, null, addMessage)
  assert.equal(messages[0].data, first)
  assert.equal(messages[0].data.knowledge.nodes.length, 1)

  const completed = { knowledge: { nodes: [{ id: 'k1' }, { id: 'k2' }] }, skill: { nodes: [{ id: 's1' }] } }
  assert.equal(upsertLearningGraphMessage(messages, completed, id, addMessage), id)
  assert.equal(messages.length, 1)
  assert.equal(messages[0].data, completed)
})
