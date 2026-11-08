import test from 'node:test'
import assert from 'node:assert/strict'
import { resourceIndexStatus, indexSyncResult } from '../src/utils/resourceIndexStatus.js'

test('AI授权不能把失败或待解析素材变成已解析', () => {
  for (const state of ['failed', 'pending', 'indexing', undefined]) {
    const result = resourceIndexStatus({ allow_ai: 1, ai_index_status: state })
    assert.equal(result.usable, false)
    assert.notEqual(result.label, '已解析')
  }
  assert.equal(resourceIndexStatus({ allow_ai: 1, ai_index_status: 'failed' }).type, 'danger')
})
test('已解析但未授权的资源不计入可供AI引用', () => {
  assert.equal(resourceIndexStatus({ allow_ai: '1', ai_index_status: 'completed' }).usable, true)
  assert.equal(resourceIndexStatus({ allow_ai: 0, ai_index_status: 'completed' }).usable, false)
})
test('HTTP200内的解析失败必须显示失败，排队不宣称已完成', () => {
  assert.throws(() => indexSyncResult({ data: { status: 'failed', error_message: '没有有效文本' } }), /没有有效文本/)
  assert.equal(indexSyncResult({ data: { status: 'indexing' } }).complete, false)
  assert.equal(indexSyncResult({ data: { status: 'indexed' } }).complete, true)
})
