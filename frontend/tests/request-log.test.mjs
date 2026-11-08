import test from 'node:test'
import assert from 'node:assert/strict'
import { startRequestLog,finishRequestLog } from '../src/utils/requestLog.js'

test('request logs status and elapsed without credentials, body or query',()=>{
  const infos=[],errors=[],info=console.info,error=console.error
  console.info=(...args)=>infos.push(args);console.error=(...args)=>errors.push(args)
  try {
    const config=startRequestLog({url:'/api/test?key=private-query',method:'post',headers:{Authorization:'private-token'},data:{password:'private-password'}})
    finishRequestLog(config,200);finishRequestLog(config,503,true)
    assert.equal(infos.length,1);assert.equal(errors.length,1)
    const entry=JSON.parse(infos[0][0].slice(infos[0][0].indexOf('{')))
    assert.equal(entry.path,'/api/test');assert.ok(entry.elapsed_ms>=0)
    assert.doesNotMatch(JSON.stringify([infos,errors]),/private/)
  }finally{console.info=info;console.error=error}
})
