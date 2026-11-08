import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
test('后台先安装Pinia再启动路由，路由不再使用next回调',()=>{
  const main=read('../src/main.ts'),router=read('../src/router/index.js')
  assert.ok(main.indexOf('app.use(pinia)')<main.indexOf('app.use(router)'))
  assert.doesNotMatch(router,/\bnext\s*\(/)
  assert.match(router,/await getCurrentUser\(\)/)
  assert.match(router,/firstAdminPath/)
  assert.match(router,/router.onError/)
})
test('未授权录入和审核操作不会展示为可点击按钮',()=>{
  const view=read('../src/views/admin/QuestionManagement.vue')
  assert.match(view,/v-if="canCreate"/)
  assert.match(view,/v-if="canReview&&selected\?\.status==='pending'"/)
  assert.match(view,/if\(!canView.value\)/)
  assert.match(view,/if\(busy.value\|\|!canCreate.value\)return/)
})
test('教师端和管理端AI代理使用同一Python端口',()=>{
  assert.match(read('../vite.config.ts'),/127\.0\.0\.1:8001/)
  assert.match(read('../.env.development'),/VITE_PYTHON_API_PROXY_TARGET=http:\/\/127\.0\.0\.1:8001/)
  assert.match(read('../src/utils/request.js'),/VITE_PYTHON_API_BASE_URL/)
})
