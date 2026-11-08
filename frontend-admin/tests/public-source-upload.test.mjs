import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
const text = parse(readFileSync(new URL('../src/views/admin/ResourceKnowledge.vue', import.meta.url), 'utf8')).descriptor.scriptSetup.content
const declarations = babelParse(text, { sourceType:'module' }).program.body
function handler(name, state) {
  const node = declarations.find(node => node.type === 'VariableDeclaration' && node.declarations.some(item => item.id.name === name))
  return vm.runInNewContext(text.slice(node.start, node.end) + ';' + name, state)
}

test('public upload sends source registration and calls Python directly after durable upload', async () => {
  const calls = [], messages = []
  const source = { source_kind:'curriculum', source_url:'https://www.moe.gov.cn/test', version_year:'2022' }
  const state = { uploadCategory:{}, uploadSource:{value:source},
    createUploadSession:async data => { calls.push('create'); assert.deepEqual(JSON.parse(data.source_metadata),source); return {data:{upload_id:3,upload_url:'local'}} },
    unwrapResult:value => value.data, uploadToOss:async () => calls.push('put'),
    completeUpload:async () => { calls.push('complete'); return {data:{}} },
    syncPublicAiResource:async id => { calls.push('python'); assert.equal(id,3); return {data:{status:'indexed',business_status_saved:true}} },
    ElMessage:{ warning: message => messages.push(message) },
  }
  const file = {name:'test.pdf',size:100,mimeType:'application/pdf'}
  const upload = handler('uploadSingleFile',state)
  assert.equal(await upload(file),3)
  assert.deepEqual(calls,['create','put','complete','python'])
  assert.equal(file.status,'success')
  // An indexing outage preserves uploaded state and permits parser retry, never reupload.
  state.syncPublicAiResource = async () => { throw Error('embedding unavailable') }
  assert.equal(await upload({name:'next.pdf'}),3)
  assert.ok(messages.some(message => message.includes('已上传')))
})

test('source save sends its registration before starting AI reindexing', async () => {
  const calls = []
  const state = { sourceSaving:{value:false}, sourceResourceId:{value:7}, editingSource:{value:{version_label:'v2'}},
    sourceEditorVisible:{value:true}, updateResource:async () => calls.push('business'),
    syncPublicAiResource:async () => { calls.push('python'); return {data:{status:'indexed'}} },
    fetchResources:async () => calls.push('refresh'), governanceRef:{value:{load:async () => calls.push('governance')}},
    resourceList:{value:[{id:7,status:'indexing'}]},pollAiIndexStatus:()=>calls.push('poll'),
    ElMessage:{success(){},error:message => {throw Error(message)}},
  }
  const node = declarations.find(node => node.type === 'FunctionDeclaration' && node.id.name === 'saveSource')
  await vm.runInNewContext(text.slice(node.start,node.end) + ';saveSource',state)()
  assert.deepEqual(calls,['business','python','refresh','poll','governance'])
  assert.equal(state.sourceSaving.value,false)
})
