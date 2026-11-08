import test from 'node:test'
import assert from 'node:assert/strict'
import { safeLoginTarget, loginLocation } from '../src/utils/sessionRedirect.js'
test('登录过期后保留工作台项目及会话参数',()=>{
  const path='/main/workspace?projectId=18&sessionId=abc'
  assert.equal(safeLoginTarget(path),path)
  assert.deepEqual(loginLocation(path),{path:'/login',query:{redirect:path}})
})
test('不允许外站、协议相对地址或逃逸的重定向',()=>{
  for(const path of ['https://evil.test','//evil.test','/main/../../evil','/mainland','/login',null,['/main/workspace']]) assert.equal(safeLoginTarget(path),'/main')
})
