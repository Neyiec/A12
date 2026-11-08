import test from 'node:test'
import assert from 'node:assert/strict'
import { permissionList, hasPermission, canAccessAdminPath, firstAdminPath, filterAdminMenus } from '../src/utils/adminAccess.js'
import { isTokenExpired } from '../src/utils/JWTParser.js'
const token=payload=>`header.${Buffer.from(JSON.stringify(payload)).toString('base64url')}.signature`
globalThis.window={atob}

test('异常、旧格式、base64url令牌不会使路由守卫抛错',()=>{
  for(const value of ['',null,'broken','a.not-json.c',token({})])assert.equal(isTokenExpired(value),true)
  assert.equal(isTokenExpired(token({exp:Date.now()/1000+1000})),false)
  assert.equal(isTokenExpired(token({exp:Date.now()/1000-1})),true)
  assert.equal(isTokenExpired(token({iat:Date.now()/1000-13*3600})),true)
})
test('角色名称或损坏的JSON不能被当作授权',()=>{
  for(const value of ['admin','[broken]',{},null])assert.deepEqual(permissionList(value),[])
  assert.equal(hasPermission(['audit:view'],'audit:audit'),false)
  assert.equal(canAccessAdminPath('/main/users',['audit:view']),false)
})
test('没有看板权限时直接进入已授权模块，不向看板发起请求',()=>{
  assert.equal(firstAdminPath(['audit:view']),'/main/questions')
  assert.equal(firstAdminPath([]),'/main/access')
  assert.equal(firstAdminPath(['resources:view']),'/main/resources')
  assert.equal(firstAdminPath(['dashboard:view']),'/main/dashboard')
})
test('题目录入和审核浏览是独立权限',()=>{
  assert.equal(canAccessAdminPath('/main/questions',['resources:edit']),true)
  assert.equal(canAccessAdminPath('/main/questions',['audit:view']),true)
  assert.equal(canAccessAdminPath('/main/questions',['users:edit']),false)
})
test('菜单过滤保留合法子项并移除空分组，不修改原始配置',()=>{
  const input=[{path:'/main/dashboard'},{key:'system',children:[{path:'/main/users'},{path:'/main/settings'}]}]
  assert.deepEqual(filterAdminMenus(input,['users:view']),[{key:'system',children:[{path:'/main/users'}]}])
  assert.equal(input[1].children.length,2)
  assert.deepEqual(filterAdminMenus(input,[]),[])
})
