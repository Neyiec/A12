import assert from 'node:assert/strict'
import test from 'node:test'
import { readOpenAiTextStream } from '../src/utils/openAiSse.js'
import { normalizeModelProfile, normalizeReasoningEffort } from '../src/utils/aiOptions.js'

const responseFromChunks = (...chunks) => ({
  body: new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder()
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  }),
})

test('reads split and merged gateway SSE frames', async () => {
  const parts = []
  const response = responseFromChunks(
    'event:message\ndata:{"choices":[{"delta":{"content":"你',
    '好"}}]}\n\nevent:message\ndata:{"choices":[{"delta":{"content":"，老师"}}]}\n\n',
    'data:[DONE]\n\n',
  )
  assert.equal(await readOpenAiTextStream(response, (part) => parts.push(part)), '你好，老师')
  assert.deepEqual(parts, ['你好', '，老师'])
})

test('keeps session and saved-message metadata alongside streamed text', async () => {
  const events = []
  const response = responseFromChunks(
    'event:session\ndata:{"conversation_id":42,"user_message_id":"u1"}\n\n',
    'data:{"choices":[{"delta":{"content":"已回复"}}]}\n\n',
    'event:message_saved\ndata:{"message_id":"a1","turn_id":"t1"}\n\n',
    'data:[DONE]\n\n',
  )
  assert.equal(await readOpenAiTextStream(response, undefined, (type, payload) => events.push([type, payload])), '已回复')
  assert.deepEqual(events, [
    ['session', { conversation_id: 42, user_message_id: 'u1' }],
    ['message_saved', { message_id: 'a1', turn_id: 't1' }],
  ])
})

test('surfaces the actual upstream SSE error instead of an empty-model message', async () => {
  const response = responseFromChunks('event:error\ndata:{"message":"模型配置错误"}\n\n')
  await assert.rejects(readOpenAiTextStream(response), /模型配置错误/)
})

test('reports a genuinely empty successful stream', async () => {
  await assert.rejects(readOpenAiTextStream(responseFromChunks('data:[DONE]\n\n')), /模型未返回有效内容/)
})

test('accepts a workflow route without model text when explicitly allowed', async () => {
  const events = []
  const response = responseFromChunks(
    'event:session\ndata:{"conversation_id":42}\n\n',
    'event:route\ndata:{"target":"planning","assistant_content":"已进入备课流程"}\n\n',
  )
  assert.equal(await readOpenAiTextStream(response, null, (type, payload) => events.push([type, payload]), { allowEmpty: true }), '')
  assert.equal(events[1][0], 'route')
  assert.equal(events[1][1].target, 'planning')
})

test('rejects stale model settings left by the old chat UI', () => {
  assert.equal(normalizeModelProfile('unknown'), 'standard')
  assert.equal(normalizeReasoningEffort('none'), 'medium')
  assert.equal(normalizeReasoningEffort('high'), 'high')
})
