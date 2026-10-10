import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
const component = parse(readFileSync(new URL('../src/components/CommunityHub.vue', import.meta.url), 'utf8')).descriptor
const source = component.scriptSetup.content
const node = babelParse(source, { sourceType: 'module' }).program.body.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d => d.id.name === 'uploadSubmissionCourseware'))
const ref = value => ({ value })
test('upload stores actual slide HTML for preview and submission, fills title and unlocks', async () => {
  const state = {
    coursewareUploading: ref(false), submissionSaving: ref(false), submissionReadOnly: ref(false), submissionError: ref(''),
    submission: ref({ title: '', content_type: 'skill' }), submissionContentObject: ref({ objective: '教学目标' }), coursewareWarnings: ref([]),
    syncSubmissionContentEditor() {}, hydrateSubmissionEditors() {}, unwrap: x => x.data, assertApiSuccess: x => x,
    importCommunityPptx: async () => ({ data: { title: '水解反应', page_count: 1, content_data: { slides: [{ title: '水解', html: '<p>真实内容</p>' }] }, warnings: ['核对图表'] } }),
    ElMessage: { warning() {}, success() {}, error() {} },
  }
  const handler = vm.runInNewContext(source.slice(node.start, node.end) + ';uploadSubmissionCourseware', state)
  await handler({ target: { files: [{ name: '化学.pptx', size: 1024 }], value: 'file' } })
  assert.equal(state.submission.value.content_type, 'ppt')
  assert.equal(state.submission.value.title, '水解反应')
  assert.equal(JSON.parse(state.submission.value.content_data).slides[0].html, '<p>真实内容</p>')
  assert.equal(JSON.parse(state.submission.value.content_data).objective, '教学目标')
  assert.equal(state.coursewareUploading.value, false)
  assert.match(component.template.content, /accept="\.pptx"/)
  assert.doesNotMatch(component.template.content, /value="ppt" disabled/)
})
