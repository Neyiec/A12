import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, babelParse } from '@vue/compiler-sfc'
import vm from 'node:vm'

const source = parse(readFileSync(new URL('../src/components/BatchPlanCard.vue',import.meta.url),'utf8')).descriptor.scriptSetup.content
const declarations = babelParse(source,{sourceType:'module'}).program.body
function handler(name,state) {
  const node=declarations.find(node=>node.type==='FunctionDeclaration'&&node.id.name===name)
  return vm.runInNewContext(source.slice(node.start,node.end)+';'+name,state)
}
test('confirm preserves unselected plan chapters but submits only selected items with latest revision',async()=>{
  const calls=[]
  const state={draft:{value:{basis:'document'}},acceptSuggested:{value:false},chosen:{value:[{id:'a'}]},
    props:{plan:{id:'plan',revision:1}},theme:{value:'素白风'},
    perform:async fn=>fn(),saveChoices:async()=>({id:'plan',revision:2,items:[{id:'a'},{id:'b'}]}),
    confirmBatchPlan:async(id,data)=>{calls.push(data);return {data:{id:'batch'}}},emit(){},}
  await handler('confirm',state)()
  assert.equal(calls[0].revision,2)
  assert.deepEqual(Array.from(calls[0].item_ids),['a'])
})
test('suggested textbook directory requires explicit teacher acknowledgement',async()=>{
  const state={draft:{value:{basis:'suggested'}},acceptSuggested:{value:false},perform:async fn=>fn()}
  await assert.rejects(handler('confirm',state)(),/建议目录/)
})
test('task panel stops polling after completion and ignores response after leaving',async()=>{
  const descriptor=parse(readFileSync(new URL('../src/components/BatchTaskPanel.vue',import.meta.url),'utf8')).descriptor
  const text=descriptor.scriptSetup.content
  const nodes=babelParse(text,{sourceType:'module'}).program.body
  const node=nodes.find(node=>node.type==='FunctionDeclaration'&&node.id.name==='load')
  let timers=0,resolve
  const state={active:true,fetching:false,props:{batchId:'b'},batches:{value:[]},plans:{value:[]},
    error:{value:''},failures:0,archiveFailures:new Map(),loading:{value:true},timer:null,setTimeout:()=>{timers++},
    readPresentationBatch:async()=>({data:{id:'b',status:'completed',zip_status:'ready',items:[]}}),}
  const load=vm.runInNewContext(text.slice(node.start,node.end)+';load',state)
  await load();assert.equal(timers,0)
  state.readPresentationBatch=()=>new Promise(r=>{resolve=r})
  const pending=load();state.active=false;resolve({data:{id:'obsolete',status:'running',items:[]}});await pending
  assert.equal(state.batches.value[0].id,'b')
})

test('ready chapters stop automatic archiving after three failures and keep manual recovery available',async()=>{
  const text=parse(readFileSync(new URL('../src/components/BatchTaskPanel.vue',import.meta.url),'utf8')).descriptor.scriptSetup.content
  const node=babelParse(text,{sourceType:'module'}).program.body.find(node=>node.type==='FunctionDeclaration'&&node.id.name==='load')
  let saves=0,timers=0
  const state={active:true,fetching:false,props:{batchId:'b'},batches:{value:[]},plans:{value:[]},
    error:{value:''},failures:0,archiveFailures:new Map(),loading:{value:true},timer:null,setTimeout:()=>{timers++},
    readPresentationBatch:async()=>({data:{id:'b',status:'ready',zip_status:'idle',items:[{id:'chapter',status:'ready'}]}}),
    saveBatchItem:async()=>{saves++;throw Error('Java unavailable')},}
  const load=vm.runInNewContext(text.slice(node.start,node.end)+';load',state)
  await load();await load();await load();await load()
  assert.equal(saves,3);assert.equal(timers,2)
  assert.equal(state.batches.value[0].items[0].status,'ready')
})
