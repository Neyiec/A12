import test from 'node:test'
import assert from 'node:assert/strict'
import { createGenerationTiming } from '../src/utils/generationTiming.js'

test('PPT耗时按阶段计时，进度更新不重置计时，完成仅输出一次', () => {
  let now = 0
  const logs=[]
  const timing=createGenerationTiming({now:()=>now,log:(_,entry)=>logs.push(entry)})
  timing.stage('generation')
  now=20;timing.stage('generation')
  now=80;timing.stage('generation','completed')
  timing.mark('python.completed',{backend_run_id:'run_abc123',token:'PRIVATE'})
  timing.finish();timing.finish()
  assert.equal(logs.filter(l=>l.stage==='generation').length,2)
  assert.equal(logs.find(l=>l.status==='completed').elapsed_ms,80)
  assert.equal(logs.filter(l=>l.stage==='browser.total').length,1)
  assert.equal(logs.find(l=>l.stage==='python.completed').backend_run_id,'run_abc123')
  assert.doesNotMatch(JSON.stringify(logs),/PRIVATE/)
})

test('PPT接口失败记录耗时并保留原异常', async () => {
  const logs=[]
  const timing=createGenerationTiming({now:()=>10,log:(_,entry)=>logs.push(entry)})
  const failure=Error('PRIVATE-DATABASE-DETAIL')
  await assert.rejects(timing.measure('project-save',()=>{throw failure}),error=>error===failure)
  assert.equal(logs.at(-1).status,'failed')
  assert.doesNotMatch(JSON.stringify(logs),/PRIVATE/)
})
