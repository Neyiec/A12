import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { computed, ref, watch } from 'vue'
import { parse, compileTemplate } from '@vue/compiler-sfc'

const source = readFileSync(new URL('../src/components/CourseGraphWorkspace.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
function workspace(extra = {}) {
  const unmount = []
  const dependencies = { computed, ref, watch, onMounted() {}, onBeforeUnmount(fn) { unmount.push(fn) },
    useRouter: () => ({ push() {} }), useUserStore: () => ({ userInfo: { id: 7 } }),
    ElMessage: { error() {}, success() {}, warning() {} }, cleanupTempResources: async () => {}, ...extra }
  const script = descriptor.scriptSetup.content.replace(/^import[\s\S]*?from ['"][^'"]+['"]\r?\n/gm, '')
  const state = new Function(...Object.keys(dependencies), script + '\nreturn {path,metrics,outline,slides,page,savedProjectId,generatedPagesSaved,targetIds,masteredIds,startId,subject,grade,dirty,busy,move,generate,abort:()=>abort,unmount:()=>{}}')(...Object.values(dependencies))
  state.unmount = () => unmount.forEach(fn => fn())
  return state
}
function seed(state) {
  state.path.value = { nodes: [{ id: 'a' }, { id: 'b' }] }
  state.metrics.value = {}; state.outline.value = { slides: [] }; state.slides.value = [{ html: 'old' }]
  state.savedProjectId.value = 'old-project'; state.generatedPagesSaved.value = true
}
for (const field of ['targetIds', 'masteredIds', 'startId', 'subject', 'grade']) {
  test(`${field} changes invalidate derived results without marking graph dirty`, () => {
    const state = workspace(); seed(state)
    state[field].value = ['targetIds', 'masteredIds'].includes(field) ? ['a'] : 'new'
    for (const key of ['path', 'metrics', 'outline']) assert.equal(state[key].value, null)
    assert.equal(state.slides.value.length, 0)
    assert.equal(state.savedProjectId.value, '')
    assert.equal(state.generatedPagesSaved.value, false)
    assert.equal(state.dirty.value, false)
  })
}
test('in-place target changes also invalidate old path', () => {
  const state = workspace(); seed(state); state.targetIds.value.push('a')
  assert.equal(state.path.value, null)
})
test('loading state does not invalidate programmatically loaded data or reorder a running path', () => {
  const state = workspace(); seed(state); state.busy.value = '加载图谱'
  state.subject.value = '数学'; state.move(0, 1)
  assert.equal(state.path.value.nodes[0].id, 'a')
  assert.equal(state.slides.value.length, 1)
})
test('unmount aborts generation and rejects late stream callbacks and final results', async () => {
  let callbacks, finish
  const state = workspace({ generatePresentationStream: (_, options) => {
    callbacks = options; return new Promise(resolve => { finish = resolve })
  } })
  seed(state)
  const pending = state.generate()
  callbacks.onSlide({ html: 'first', slide_no: 1 }); assert.equal(state.slides.value.length, 1)
  state.unmount(); assert.equal(callbacks.signal.aborted, true)
  callbacks.onSlide({ html: 'late', slide_no: 2 })
  finish({ slides: [{ html: 'late-final' }] }); await pending
  assert.equal(state.slides.value.length, 1); assert.equal(state.slides.value[0].html, 'first')
})
test('template locks form controls but keeps stop button outside disabled form', () => {
  const result = compileTemplate({ source: descriptor.template.content, filename: 'CourseGraphWorkspace.vue', id: 'course-test' })
  assert.deepEqual(result.errors, [])
  assert.match(descriptor.template.content, /<el-form :disabled="!!busy">/)
  assert.match(descriptor.template.content, /:closable="!busy"/)
  assert.match(descriptor.template.content, /v-model="courseId" :disabled="version > 0 \|\| !!busy"/)
  assert.match(descriptor.template.content, /<\/el-form>\s*<el-button[^>]*@click="abort\?\.abort\(\)"/)
})
