import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
import { hasWorkspaceTarget, unwrapWorkspaceResult } from '../src/utils/workspaceEntry.js'

const file = readFileSync(new URL('../src/components/WorkspaceEntry.vue', import.meta.url), 'utf8')
const source = parse(file).descriptor.scriptSetup.content
const declarations = babelParse(source, { sourceType: 'module' }).program.body
function handler(name, state) {
  const node = declarations.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d => d.id.name === name))
  return vm.runInNewContext(source.slice(node.start, node.end) + ';' + name, state)
}
const ref = value => ({ value })
test('ordinary workspace navigation stays on the project chooser', () => {
  assert.equal(hasWorkspaceTarget({}), false)
  assert.equal(hasWorkspaceTarget({manage:'1',preview:'1'}), false)
  for (const key of ['projectId','sessionId','localDraftId','testCase','pptGeneration']) assert.equal(hasWorkspaceTarget({[key]:'17'}), true)
  assert.match(file, /<Editor v-if="hasTarget"/)
})
test('opening or dismissing the new-project dialog does not create data', () => {
  const state = { pendingProjectId:ref(null), name:ref('old'), createVisible:ref(false) }
  handler('beginCreate', state)()
  assert.equal(state.createVisible.value, true)
  assert.equal(state.name.value, '')
  state.createVisible.value = false
  assert.equal(state.pendingProjectId.value, null)
})
test('project creation requires explicit confirmation and includes blank content and a snapshot', async () => {
  const calls = []
  const state = { name:ref('新课件'), creating:ref(false), pendingProjectId:ref(null), pendingPageSaved:ref(false), createVisible:ref(true),
    unwrapWorkspaceResult,
    createProject:async data => { calls.push(['project', data.project_name]); return {code:200,data:{id:77}} },
    createProjectPage:async (id,data) => { calls.push(['page',id]); assert.equal(JSON.parse(data.page_content).elements.length,0); return {code:200,data:{id:88}} },
    saveProjectVersion:async id => {calls.push(['snapshot',id]); return {code:200}},
    openProject:async data => calls.push(['open',data.id]),
    ElMessage:{warning(){},success(){},error(){}},
  }
  await handler('createNewProject', state)()
  assert.deepEqual(calls,[['project','新课件'],['page',77],['snapshot',77],['open',77]])
  assert.equal(state.creating.value,false)
})
test('initialization retry does not create a duplicate project', async () => {
  let projects = 0, pages = 0, failures = 0
  const state = { name:ref('新课件'), creating:ref(false), pendingProjectId:ref(null), pendingPageSaved:ref(false), createVisible:ref(true),
    unwrapWorkspaceResult,
    createProject:async () => { projects++; return {id:77} },
    createProjectPage:async () => {pages++; return {id:88}},
    saveProjectVersion:async () => { if (!failures++) throw Error('snapshot failed'); return {} },
    openProject:async () => {},ElMessage:{warning(){},success(){},error(){}},
  }
  const create = handler('createNewProject',state)
  await create()
  await create()
  assert.equal(projects,1)
  assert.equal(pages,1)
})
