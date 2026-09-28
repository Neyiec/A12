import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'

// Execute the actual SFC handlers with isolated API dependencies; no live project is changed.
const descriptor = parse(readFileSync(new URL('../src/components/CreationWorkspace.vue', import.meta.url), 'utf8')).descriptor
const source = descriptor.scriptSetup.content
const template = descriptor.template.content
const declarations = babelParse(source, { sourceType: 'module' }).program.body
function handler(name, state) {
  const node = declarations.find(node => node.type === 'VariableDeclaration' && node.declarations.some(item => item.id.name === name))
  assert.ok(node, name + ' exists')
  return vm.runInNewContext(source.slice(node.start, node.end) + ';' + name, state)
}
const ref = value => ({ value })
test('audio player starts element dragging without cancelling its native controls', () => {
  const element = { id: 'audio-1', type: 'audio', position: { x: 8, y: 48 } }
  const canvas = { getBoundingClientRect: () => ({ width: 780, height: 438 }) }
  let prevented = false
  let capturedPointer = null
  const state = {
    placementMode: ref(false), elementById: id => id === element.id ? element : null,
    isMobile: ref(false),
    dragState: ref(null), draggingElementId: ref(null), current: ref({ elements: [element] }),
    selectElement() {}, handleElementDrag() {}, stopElementDrag() {},
    window: { addEventListener() {} },
  }
  const startDrag = handler('startElementDrag', state)
  startDrag(element.id, {
    button: 0, pointerId: 7, clientX: 120, clientY: 80,
    currentTarget: {
      closest: selector => selector === '.slide-canvas' ? canvas : null,
      classList: { contains: name => name === 'workspace-media-player' },
      setPointerCapture: pointerId => { capturedPointer = pointerId },
    },
    preventDefault: () => { prevented = true },
  })
  assert.equal(state.draggingElementId.value, element.id)
  assert.equal(state.dragState.value.captureTarget.classList.contains('workspace-media-player'), true)
  assert.equal(capturedPointer, 7)
  assert.equal(prevented, false)
  assert.match(template, /<audio[^>]*@pointerdown\.stop="startElementDrag\(element\.id, \$event\)"/)
})
test('workspace keyboard shortcuts copy, paste and delete only selected canvas elements', () => {
  const calls = []
  const state = {
    presentationMode: ref(false), workspaceSelectedElementId: ref('chart-1'),
    saveWorkspaceNow() { calls.push('save') }, cancelCanvasPlacement() { calls.push('cancel-placement') },
    clearElementSelection() { calls.push('clear-selection') },
    copyElementToClipboard: id => { calls.push(`copy:${id}`); return true },
    pasteElementFromClipboard: () => { calls.push('paste'); return true },
    removeElement: id => calls.push(`remove:${id}`), copyElement: id => calls.push(`duplicate:${id}`),
  }
  const keydown = handler('handleWorkspaceKeydown', state)
  const press = (key, { ctrlKey = false, target = {} } = {}) => {
    let prevented = false
    keydown({ key, ctrlKey, metaKey: false, target, preventDefault: () => { prevented = true } })
    return prevented
  }
  assert.equal(press('c', { ctrlKey: true }), true)
  assert.equal(press('v', { ctrlKey: true }), true)
  assert.equal(press('Delete'), true)
  assert.equal(press('d', { ctrlKey: true }), true)
  assert.equal(press('c', { ctrlKey: true, target: { tagName: 'INPUT' } }), false)
  assert.deepEqual(calls, ['copy:chart-1', 'paste', 'remove:chart-1', 'duplicate:chart-1'])
  assert.match(source, /copyToClipboard: \(id\)/)
  assert.match(source, /pasteFromClipboard: pasteClipboard/)
})
test('remounting the PPT canvas uses the edited HTML without reloading during live edits', () => {
  const slide = { html: '<p>original</p>' }
  const state = {
    current: ref(slide), htmlCanvasSourceSlide: ref(slide), htmlCanvasSource: ref(slide.html),
    structuredHtmlCanvasSourceSlide: ref(null), structuredHtmlCanvasSource: ref(''), htmlCanvasFrameRevision: ref(0),
    workspaceMode: ref('ppt'),
  }
  state.syncHtmlCanvasSource = handler('syncHtmlCanvasSource', state)
  let onModeChange
  state.watch = (target, callback) => { assert.equal(target, state.workspaceMode); onModeChange = callback }
  const node = declarations.find(node => node.type === 'ExpressionStatement' && node.expression.callee?.name === 'watch' && node.expression.arguments[0]?.name === 'workspaceMode')
  assert.ok(node)
  vm.runInNewContext(source.slice(node.start, node.end), state)
  slide.html = '<p>original</p><div>new element</div>'
  assert.equal(state.htmlCanvasSource.value, '<p>original</p>')
  onModeChange('ppt')
  assert.equal(state.htmlCanvasSource.value, slide.html)
  assert.equal(state.htmlCanvasFrameRevision.value, 0)
})
test('toolbar selects only the live document after switching editor modes', () => {
  const slide = {}
  const oldDocument = {}
  const liveDocument = {}
  const liveController = { insertElement() {} }
  const state = { current: ref(slide), htmlFrameObservers: new Set([
    { slide, iframe: { isConnected: false, contentDocument: oldDocument }, document: oldDocument, controller: {} },
    { slide, iframe: { isConnected: true, contentDocument: liveDocument }, document: oldDocument, controller: {} },
    { slide, iframe: { isConnected: true, contentDocument: liveDocument }, document: liveDocument, controller: liveController },
  ]) }
  const active = handler('activeHtmlController', state)
  assert.equal(active(), liveController)
  state.current.value = {}
  assert.equal(active(), null)
})
function projectState(api) {
  const state = {
    projectListRequest: 0, projectListLoading: ref(false), projectListError: ref(''),
    projectFilters: { keyword: '  数学  ', project_type: 'ppt', status: 'draft', page: 1, size: 10 },
    workspaceProjects: ref([]), projectTotal: ref(0), listProjects: api,
    unwrapResponse: response => { if (response.code !== 200) throw Error(response.message); return response.data },
  }
  state.workspaceRequestErrorMessage = handler('workspaceRequestErrorMessage', state)
  state.projectRecordsFromResponse = handler('projectRecordsFromResponse', state)
  state.loadWorkspaceProjects = handler('loadWorkspaceProjects', state)
  return state
}
test('project search sends documented filters and uses server pagination total', async () => {
  let params
  const state = projectState(async query => { params = query; return { code: 200, data: { records: [{ id: 21 }], total: 52 } } })
  await state.loadWorkspaceProjects()
  assert.equal(params.keyword, '数学')
  assert.equal(params.project_type, 'ppt')
  assert.equal(params.status, 'draft')
  assert.equal(params.size, 10)
  assert.equal(state.projectTotal.value, 52)
  assert.equal(state.workspaceProjects.value[0].id, 21)
})
test('slower obsolete searches cannot replace newer results', async () => {
  const pending = []
  const state = projectState(() => new Promise(resolve => pending.push(resolve)))
  const first = state.loadWorkspaceProjects()
  const second = state.loadWorkspaceProjects()
  pending[1]({ code: 200, data: { records: [{ id: 2 }], total: 1 } })
  await second
  pending[0]({ code: 200, data: { records: [{ id: 1 }], total: 1 } })
  await first
  assert.equal(state.workspaceProjects.value[0].id, 2)
  assert.equal(state.projectListLoading.value, false)
})
test('business errors clear stale rows and expose a retryable error', async () => {
  const state = projectState(async () => ({ code: 403, message: '无权访问' }))
  state.workspaceProjects.value = [{ id: 9 }]
  await state.loadWorkspaceProjects()
  assert.equal(state.projectListError.value, '无权访问')
  assert.equal(state.workspaceProjects.value.length, 0)
  assert.equal(state.projectListLoading.value, false)
})
test('empty last page after deletion returns to a valid page', async () => {
  const pages = []
  const state = projectState(async ({page}) => { pages.push(page); return { code: 200, data: { records: page === 2 ? [] : [{id:1}], total: 10 } } })
  state.projectFilters.page = 2
  await state.loadWorkspaceProjects()
  assert.deepEqual(pages, [2, 1])
  assert.equal(state.projectFilters.page, 1)
})
function restoreState(failSave = false) {
  const calls = []
  const state = {
    versionActionLoading: ref(false), projectId: ref('7'), project: ref({}), versionDiff: ref({}), versionPage: ref(3),
    ElMessageBox: { confirm: async () => calls.push('confirm') },
    WorkspaceMessage: { success: () => calls.push('success'), error: () => calls.push('error') },
    clearTimeout() {}, autosaveTimer: null, unwrapResponse: value => value,
    lessonPlanEditorRef: ref(null), saveLessonPlanDraft: async () => calls.push('document'),
    persistSlideOrder: async () => { calls.push('save'); if (failSave) throw Error('conflict') },
    saveProjectVersion: async () => { calls.push('backup'); return {} },
    restoreProjectVersion: async () => { calls.push('restore'); return {current_version: 12} },
    loadProject: async () => calls.push('reload'), loadVersions: async () => calls.push('versions'),
  }
  state.persistVersionContent = handler('persistVersionContent', state)
  return { state, calls }
}
test('restoring first saves and backs up current content, then reloads page IDs', async () => {
  const {state, calls} = restoreState()
  await handler('restoreVersion', state)({version_id: 4})
  assert.deepEqual(calls, ['confirm', 'save', 'backup', 'restore', 'reload', 'versions', 'success'])
  assert.equal(state.versionPage.value, 1)
  assert.equal(state.versionActionLoading.value, false)
})
test('save conflicts prevent backup and restoration', async () => {
  const {state, calls} = restoreState(true)
  await handler('restoreVersion', state)({version_id: 4})
  assert.deepEqual(calls, ['confirm', 'save', 'error'])
  assert.equal(state.versionActionLoading.value, false)
})

test('document edits are persisted before the shared project backup', async () => {
  const {state, calls} = restoreState()
  state.lessonPlanEditorRef.value = { getLessonPlan: () => ({title: '修改后的教学案'}) }
  await handler('restoreVersion', state)({version_id: 4})
  assert.deepEqual(calls, ['confirm', 'save', 'document', 'backup', 'restore', 'reload', 'versions', 'success'])
})
test('document save failure blocks restoration and does not create an incomplete backup', async () => {
  const {state, calls} = restoreState()
  state.lessonPlanEditorRef.value = { getLessonPlan: () => ({title: '尚未保存的教学案'}) }
  state.saveLessonPlanDraft = async () => { calls.push('document'); throw Error('document conflict') }
  await handler('restoreVersion', state)({version_id: 4})
  assert.deepEqual(calls, ['confirm', 'save', 'document', 'error'])
  assert.equal(state.versionActionLoading.value, false)
})
