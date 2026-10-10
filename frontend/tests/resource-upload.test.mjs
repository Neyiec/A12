import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
import { resourceUploadError } from '../src/utils/resourceUploadError.js'

const component = parse(readFileSync(new URL('../src/components/ResourceLibrary.vue', import.meta.url), 'utf8')).descriptor
const source = component.scriptSetup.content
const node = babelParse(source, { sourceType: 'module' }).program.body.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d => d.id.name === 'handleUpload'))

test('retry uploads failed files only, preserves successful files, resets busy state', async () => {
  const queue = [{ name: 'done', status: 'success' }, { name: 'retry', status: 'error' }, { name: 'new', status: 'ready' }]
  const calls = []
  const state = {
    uploadQueue: { value: queue }, uploading: { value: false }, resources: { value: [] },
    createUploadFile: item => item, startProgressFallback() {}, stopProgressFallback() {},
    uploadResource: async item => { calls.push(item.name); return { id: item.name } },
    normalizeRealResource: x => x, loadResources: async () => {},
    ElMessage: { success() {}, warning() {}, error() {} },
  }
  await vm.runInNewContext(source.slice(node.start, node.end) + ';handleUpload', state)()
  assert.deepEqual(calls, ['retry', 'new'])
  assert.equal(queue.every(item => item.status === 'success'), true)
  assert.equal(state.uploading.value, false)
  assert.match(component.template.content, /重试失败文件/)
})

test('OSS error messages identify missing bucket, permission and network errors', () => {
  assert.match(resourceUploadError({ response: { status: 404, data: '<Error><Code>NoSuchBucket</Code></Error>' } }), /存储桶不存在/)
  assert.match(resourceUploadError({ response: { status: 403, data: '<Code>AccessDenied</Code>' } }), /上传权限/)
  assert.match(resourceUploadError({}), /跨域/)
  assert.match(resourceUploadError({ response: { status: 500 } }), /500/)
})
