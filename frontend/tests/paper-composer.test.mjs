import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse } from '@vue/compiler-sfc'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { questionTypes, subjects, totalScore } from '../src/utils/questionBank.js'
const { descriptor } = parse(readFileSync(new URL('../src/components/PaperComposer.vue', import.meta.url), 'utf8'))
function composer(extra = {}) {
  const props = reactive({ modelValue: true, questions: [{ id: 1, subject: '数学', score: 3 }, { id: 2, subject: '数学', score: 5 }], paper: { title: '练习', revision: 4 }, busy: false })
  const events = [], unmount = []
  const dependencies = { computed, nextTick, ref, watch, questionTypes, subjects, totalScore,
    defineProps: () => props, defineEmits: () => (...args) => events.push(args), onBeforeUnmount: fn => unmount.push(fn),
    listQuestions: async () => ({ items: [], total: 0 }), ...extra }
  const script = descriptor.scriptSetup.content.replace(/^import[^\n]+\r?\n/gm, '')
  const state = new Function(...Object.keys(dependencies), script + '\nreturn {move,remove,setScore,setPaper,loadQuestions,page,rows,loading,selected}')(...Object.values(dependencies))
  return { ...state, props, events, unmount: () => unmount.forEach(fn => fn()) }
}
test('题序调整和移除发出新数组，保留原题快照与原数组', () => {
  const s = composer(), original = s.props.questions
  s.move(0, 1)
  assert.deepEqual(s.events[0][1].map(q => q.id), [2, 1])
  assert.deepEqual(original.map(q => q.id), [1, 2])
  s.remove(1)
  assert.deepEqual(s.events[2][1].map(q => q.id), [2])
})
test('修改分值与名称不丢失其他字段或服务端revision', () => {
  const s = composer()
  s.setScore(1, 8)
  assert.equal(s.events[0][1][0].score, 8)
  assert.equal(s.props.questions[0].score, 3)
  s.setPaper('title', '期末练习')
  assert.equal(s.events[2][1].revision, 4)
  assert.equal(s.events[2][1].title, '期末练习')
})
test('组卷选题限定当前学科，旧查询结果不会覆盖新查询', async () => {
  const calls = [], resolve = []
  const s = composer({ listQuestions: query => { calls.push(query); return new Promise(r => resolve.push(r)) } })
  const old = s.loadQuestions()
  s.page.value = 2
  const latest = s.loadQuestions()
  assert.equal(calls[1].subject, '数学')
  assert.equal(calls[1].scope, 'public')
  resolve[1]({ items: [{ id: 9 }], total: 1 }); await latest
  resolve[0]({ items: [{ id: 8 }], total: 1 }); await old
  assert.equal(s.rows.value[0].id, 9)
})
test('关闭工作台后丢弃未完成的题库查询', async () => {
  let finish
  const s = composer({ listQuestions: () => new Promise(r => { finish = r }) })
  const pending = s.loadQuestions()
  s.props.modelValue = false
  await nextTick()
  finish({ items: [{ id: 9 }], total: 1 }); await pending
  assert.equal(s.rows.value.length, 0)
  assert.equal(s.loading.value, false)
})
