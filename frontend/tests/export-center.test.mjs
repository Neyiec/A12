import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
const component = parse(readFileSync(new URL('../src/components/ExportCenter.vue', import.meta.url), 'utf8')).descriptor
const source = component.scriptSetup.content
const node = babelParse(source, { sourceType: 'module' }).program.body.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d => d.id.name === 'submitExport'))
const ref = value => ({ value })
function state(fail = false) {
  const calls = []
  const value = {
    exportSubmitting: ref(false), prechecking: ref(false), exportDialogVisible: ref(true),
    exportForm: ref({ project_id: '1', snapshot_version: 'auto', export_type: 'pptx' }),
    precheck: ref(null), precheckSignature: ref(''), project: ref({}),
    buildExportConfig: () => ({}),
    runPrecheck: async () => {
      calls.push('precheck'); value.exportForm.value.snapshot_version = '2'; value.precheck.value = { passed: true };
      value.precheckSignature.value = JSON.stringify({ projectId: '1', snapshotVersion: 2, exportType: 'pptx', config: {} });
    },
    createExportTask: async () => { calls.push('create'); if (fail) throw Error('export failed'); return { data: { id: 10 } } },
    unwrap: x => x.data || x, normalizeTask: x => x, mergeTask: () => calls.push('merge'),
    loadTasks: async () => calls.push('refresh'),
    ElMessage: { warning: () => calls.push('warning'), error: () => calls.push('error'), success: () => calls.push('success') },
  }
  return { value, calls }
}
test('create export automatically prechecks and releases its lock', async () => {
  const { value, calls } = state()
  await vm.runInNewContext(source.slice(node.start, node.end) + ';submitExport', value)()
  assert.deepEqual(calls, ['precheck', 'create', 'merge', 'success', 'refresh'])
  assert.equal(value.exportSubmitting.value, false)
  assert.equal(value.exportDialogVisible.value, false)
})
test('failed export refreshes failed task and permits retry; busy clicks do nothing', async () => {
  const { value, calls } = state(true)
  const submit = vm.runInNewContext(source.slice(node.start, node.end) + ';submitExport', value)
  value.exportSubmitting.value = true
  await submit()
  assert.equal(calls.length, 0)
  value.exportSubmitting.value = false
  await submit()
  assert.deepEqual(calls, ['precheck', 'create', 'error', 'refresh'])
  assert.equal(value.exportSubmitting.value, false)
  assert.equal(value.exportDialogVisible.value, true)
})
