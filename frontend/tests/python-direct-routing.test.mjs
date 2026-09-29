import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const teacherApi = readFileSync(new URL('../src/apis/teacher.js', import.meta.url), 'utf8')
const request = readFileSync(new URL('../src/utils/request.js', import.meta.url), 'utf8')
const vite = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8')
const chatView = readFileSync(new URL('../src/components/ChatView.vue', import.meta.url), 'utf8')
const workspace = readFileSync(new URL('../src/components/CreationWorkspace.vue', import.meta.url), 'utf8')

test('AI engine requests use the Python service while business sessions remain on Java', () => {
  assert.doesNotMatch(teacherApi, /\/api\/v1\/ai\/engine\//)
  assert.match(teacherApi, /\/api\/v1\/python\/presentations\/generate\/stream/)
  assert.match(teacherApi, /\/api\/v1\/python\/outlines\/chat\/stream/)
  assert.match(teacherApi, /\/api\/v1\/python\/intent\/recognize/)
  assert.match(teacherApi, /\/api\/v1\/ai\/sessions/)
  assert.match(request, /VITE_PYTHON_API_BASE_URL/)
  assert.match(vite, /'\/api\/v1\/python'/)
  assert.match(chatView, /routeTeachingChat\(/)
  assert.match(chatView, /streamGeneralChat\(/)
  assert.match(chatView, /streamOutlineChat\(/)
  assert.doesNotMatch(chatView, /streamPersistentGeneralChat\(|streamSendAiSessionMessage\(|sendAiSessionAudioMessage\(/)
  assert.match(workspace, /sendDirectOutlineSessionMessage\(/)
  assert.doesNotMatch(workspace, /sendAiSessionMessage\(|sendAiSessionAudioMessage\(/)
})
