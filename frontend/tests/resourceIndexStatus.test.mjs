import test from 'node:test'
import assert from 'node:assert/strict'
import { resourceIndexStatus, indexSyncResult } from '../src/utils/resourceIndexStatus.js'

test('only an available, allowed and completed resource counts as AI usable', () => {
  const ready = { status: 1, allow_ai: 1, ai_index_status: 'completed' }
  assert.equal(resourceIndexStatus(ready).usable, true)
  for (const blocked of [
    { ...ready, allow_ai: 0 }, { ...ready, status: 0 },
    { ...ready, available: false }, { ...ready, ai_index_status: 'indexing' },
    { ...ready, ai_index_status: 'unrecognized' }, {},
  ]) assert.equal(resourceIndexStatus(blocked).usable, false)
})

test('seeded resources with AI disabled remain visible without inflating usable count', () => {
  const result = resourceIndexStatus({ status: 1, allow_ai: 0, ai_index_status: 'disabled' })
  assert.equal(result.label, '未开启 AI 引用')
  assert.equal(result.usable, false)
})

test('index failures retain the backend cause', () => {
  const message = '向量化失败：模型尚未配置'
  assert.equal(resourceIndexStatus({ allow_ai: 1, ai_index_status: 'failed', ai_index_error: message }).error, message)
  assert.throws(() => indexSyncResult({ code: 200, data: { status: 'failed', error_message: message } }), { message })
  assert.throws(() => indexSyncResult({ code: 403, message: '无权同步此素材' }), { message: '无权同步此素材' })
})

test('queued and generic skipped responses are not treated as completed', () => {
  assert.equal(indexSyncResult({ data: { status: 'queued' } }).complete, false)
  assert.equal(indexSyncResult({ data: { status: 'skipped' } }).complete, false)
  assert.equal(indexSyncResult({ data: { status: 'skipped', reason: 'content_sha256_unchanged' } }).complete, true)
  assert.equal(indexSyncResult({ data: { status: 'indexed' } }).complete, true)
})
