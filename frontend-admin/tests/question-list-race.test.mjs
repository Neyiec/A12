import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { parse,babelParse } from '@vue/compiler-sfc'

test('审核列表快速筛选只保留最新结果，离开后不再回写',async()=>{
  const source=parse(readFileSync(new URL('../src/views/admin/QuestionManagement.vue',import.meta.url),'utf8')).descriptor.scriptSetup.content
  const node=babelParse(source,{sourceType:'module'}).program.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='load')
  const pending=[]
  const ref=value=>({value})
  const state={disposed:false,requestSeq:0,canView:ref(true),rows:ref([]),total:ref(0),loading:ref(false),error:ref(''),filters:{status:'pending'},
    api:()=>new Promise(resolve=>pending.push(resolve))}
  const load=vm.runInNewContext(source.slice(node.start,node.end)+';load',state)
  const first=load();state.filters.status='approved';const second=load()
  pending[1]({items:[{id:2}],total:1});await second
  pending[0]({items:[{id:1}],total:1});await first
  assert.equal(state.rows.value[0].id,2)
  const leaving=load();state.disposed=true;state.requestSeq++
  pending[2]({items:[{id:3}],total:1});await leaving
  assert.equal(state.rows.value[0].id,2)
})
