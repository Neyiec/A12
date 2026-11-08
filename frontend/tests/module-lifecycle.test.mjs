import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { parse,babelParse } from '@vue/compiler-sfc'
const ref=value=>({value})
function handler(file,name,state) {
  const source=parse(readFileSync(new URL(`../src/components/${file}.vue`,import.meta.url),'utf8')).descriptor.scriptSetup.content
  const nodes=babelParse(source,{sourceType:'module'}).program.body
  const node=nodes.find(n=>(n.type==='FunctionDeclaration'&&n.id.name===name)||(n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name===name)))
  return vm.runInNewContext(source.slice(node.start,node.end)+';'+name,state)
}

test('资源检索较早请求不会覆盖新结果，离开后不更新列表',async()=>{
  const pending=[]
  const state={resourceDisposed:false,resourceRequestSeq:0,loading:ref(false),resourcesError:ref(''),selectedRows:ref([]),
    keyword:ref(''),resources:ref([]),resourceTotal:ref(0),listResources:()=>new Promise(resolve=>pending.push(resolve)),normalizeRealResource:x=>x}
  const load=handler('ResourceLibrary','loadResources',state)
  const older=load(),newer=load()
  pending[1]({data:{records:[{id:2}],total:1}});await newer
  pending[0]({data:{records:[{id:1}],total:1}});await older
  assert.equal(state.resources.value[0].id,2)
  const leaving=load();state.resourceDisposed=true
  pending[2]({data:{records:[{id:3}]}});await leaving
  assert.equal(state.resources.value[0].id,2)
})

test('导出列表离开后忽略返回值，不恢复轮询',async()=>{
  let complete,schedules=0
  const state={disposed:false,taskRequestSeq:0,loading:ref(false),pageError:ref(''),project:ref(null),tasks:ref([]),flow:ref({}),
    listExportTasks:()=>new Promise(resolve=>complete=resolve),recordsFrom:x=>x,normalizeTask:x=>x,scheduleTaskPolling:()=>schedules++}
  const loading=handler('ExportCenter','loadTasks',state)()
  state.disposed=true;state.taskRequestSeq++
  complete([{id:1}]);await loading
  assert.equal(state.tasks.value.length,0);assert.equal(schedules,0)
})

test('导出前台跟踪期间不再启动列表轮询，迟到详情不覆盖已离开的页面',async()=>{
  let scheduled=0,merged=0,complete
  const state={disposed:false,activePoll:true,pollEpoch:0,taskPollTimer:null,pushReady:false,progressPulse:0,clearTimeout(){},tasks:ref([{}]),isRunning:()=>true,
    window:{setTimeout:()=>scheduled++},getExportProgress:()=>new Promise(resolve=>complete=resolve),normalizeTask:x=>x,unwrap:x=>x,
    project:ref({}),flow:ref({}),mergeTask:()=>merged++,scheduleTaskPolling:()=>scheduled++,Date,DOMException}
  handler('ExportCenter','scheduleTaskPolling',state)()
  assert.equal(scheduled,0)
  state.activePoll=false
  const promise=handler('ExportCenter','pollTask',state)(1)
  state.disposed=true;state.pollEpoch++;state.activePoll=false
  complete({apiStatus:'success'})
  await assert.rejects(promise,e=>e.name==='AbortError')
  assert.equal(merged,0);assert.equal(scheduled,0)
})

test('导出推送就绪时等状态变化，通知到达后立即回读终态', async () => {
  let reads = 0
  const delays = []
  const state = {
    disposed: false, activePoll: false, pollEpoch: 0, taskPollTimer: null, pushReady: true,
    progressPulse: 0, wakeProgress: undefined, clearTimeout() {}, Date, DOMException,
    window: { setTimeout: (_, delay) => delays.push(delay) },
    getExportTask: async () => ({ apiStatus: ++reads === 1 ? 'generating' : 'success' }),
    normalizeTask: x => x, unwrap: x => x, project: ref({}), flow: ref({}),
    mergeTask() {}, scheduleTaskPolling() {},
  }
  const result = handler('ExportCenter', 'pollTask', state)(1)
  await new Promise(setImmediate)
  assert.deepEqual(delays, [30000])
  state.wakeProgress()
  assert.equal((await result).apiStatus, 'success')
  assert.equal(reads, 2)
})

test('视频任务鉴权失败停止轮询，离开后的响应也不会回写',async()=>{
  let scheduled=0,complete
  const state={disposed:false,requestSeq:0,failures:0,timer:null,jobs:ref([]),error:ref(''),clearTimeout(){},setTimeout:()=>scheduled++,
    listLearningVideos:async()=>{throw {response:{status:403},message:'没有权限'}}}
  const refresh=handler('LearningVideoTasks','refresh',state)
  await refresh();assert.equal(scheduled,0)
  state.listLearningVideos=()=>new Promise(resolve=>complete=resolve)
  const pending=refresh();state.disposed=true
  complete({data:[{job_id:'late'}]});await pending
  assert.equal(state.jobs.value.length,0);assert.equal(scheduled,0)
})

test('上传总大小未知时不传播NaN百分比，正常进度限制在0至100',()=>{
  const source=readFileSync(new URL('../src/utils/api.js',import.meta.url),'utf8')
  const fn=babelParse(source,{sourceType:'module'}).program.body.find(n=>n.declaration?.id?.name==='uploadFile').declaration
  let config
  const upload=vm.runInNewContext(source.slice(fn.start,fn.end)+';uploadFile',{request:{post:(_,__,options)=>{config=options}}})
  const progress=[];upload('/local',null,value=>progress.push(value))
  config.onUploadProgress({loaded:20});config.onUploadProgress({loaded:20,total:0})
  config.onUploadProgress({loaded:20,total:40});config.onUploadProgress({loaded:100,total:40})
  assert.deepEqual(progress,[50,100])
})
