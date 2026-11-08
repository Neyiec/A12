import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
import { gradesForStage, normalizePlanningGrade, extractPlanningContext, slideRangeError } from '../src/config/teacherChat.config.js'
const source = parse(readFileSync(new URL('../src/components/ChatView.vue', import.meta.url), 'utf8')).descriptor.scriptSetup.content
const nodes = babelParse(source, { sourceType: 'module' }).program.body
function handler(name, state) {
  const node = nodes.find(n => n.type === 'FunctionDeclaration' && n.id.name === name)
  return vm.runInNewContext(source.slice(node.start, node.end) + ';' + name, state)
}
test('年级按四个学段独立提供，未选学段不提供年级', () => {
  assert.deepEqual(gradesForStage('小学'), ['一年级','二年级','三年级','四年级','五年级','六年级'])
  assert.deepEqual(gradesForStage('初中'), ['七年级','八年级','九年级'])
  assert.deepEqual(gradesForStage('高中'), ['高一','高二','高三'])
  assert.deepEqual(gradesForStage('大学'), ['大一','大二','大三','大四','大五'])
  assert.deepEqual(gradesForStage(''), [])
})
test('兼容历史年级别名但不允许跨学段', () => {
  assert.equal(normalizePlanningGrade('大学','一年级'), '大一')
  assert.equal(normalizePlanningGrade('大学','大学五年级'), '大五')
  assert.equal(normalizePlanningGrade('初中','初中二年级（八年级）'), '八年级')
  assert.equal(normalizePlanningGrade('高中','高中一年级'), '高一')
  assert.equal(normalizePlanningGrade('大学','高三'), '')
  assert.equal(normalizePlanningGrade('小学','大一'), '')
})
test('识别大学五个年级，不误当小学年级', () => {
  for (const year of ['一','二','三','四','五']) {
    const context = extractPlanningContext(`大学${year}年级《微积分入门》`)
    assert.equal(context.stage,'大学')
    assert.equal(context.grade,`大${year}`)
  }
})
test('切换学段后清空旧年级', () => {
  const state = { infoForm: { stage:'大学', grade:'一年级' }, gradeOptions:{value:gradesForStage('大学')} }
  handler('handleStageChange',state)()
  assert.equal(state.infoForm.grade,'')
})
function form() {
  const calls = []
  return { calls, state: { isRequesterLoading:{value:false},
    infoForm:{stage:'大学',subject:'数学',grade:'大一',courseName:'微积分入门'}, normalizePlanningGrade, slideRangeError,
    ElMessage:{warning:msg=>calls.push(['warning',msg])}, addMessage(){throw Error('不应生成标题气泡')},
    buildContextMessage:()=> '大学数学大一，课程名称：微积分入门',
    sendMessageToBackend:async (...args)=>calls.push(args) } }
}
test('确认表单直接生成，不追加标题消息，保留确认动作标记', async () => {
  const {state,calls}=form()
  await handler('confirmInfo',state)()
  assert.equal(calls.length,1)
  assert.match(calls[0][0],/微积分入门/)
  assert.equal(calls[0][1].inputKind,'course_info_confirmation')
})
test('正在生成或年级不匹配时不会重复提交', async () => {
  const {state,calls}=form()
  state.isRequesterLoading.value=true
  await handler('confirmInfo',state)()
  assert.equal(calls.length,0)
  state.isRequesterLoading.value=false;state.infoForm.grade='高三'
  await handler('confirmInfo',state)()
  assert.equal(calls[0][0],'warning')
})

test('页数范围选填，限制整数、完整区间及上下限', () => {
  assert.equal(slideRangeError(undefined, undefined), '')
  assert.equal(slideRangeError(null, null), '')
  assert.equal(slideRangeError(10, 18), '')
  assert.equal(slideRangeError(12, 12), '')
  for (const values of [[10,undefined],[undefined,15],[18,10],[0,20],[10,31],[1.5,8]]) assert.ok(slideRangeError(...values))
})

test('页数区间不完整时拦截提交，留空或有效范围正常提交', async () => {
  const {state,calls} = form()
  state.infoForm.minPages = 10
  await handler('confirmInfo',state)()
  assert.equal(calls[0][0], 'warning')
  calls.length = 0
  state.infoForm.maxPages = 18
  await handler('confirmInfo',state)()
  assert.equal(calls[0][1].inputKind, 'course_info_confirmation')
})

test('页数范围进入结构化字段及教师确认文本，不预选固定页数', () => {
  const state = {infoForm:{stage:'大学',subject:'数学',grade:'大一',textbook:'',courseName:'微积分',classLevel:'良好',requirements:'',minPages:10,maxPages:18}, slideRangeError}
  state.getSlideCountRange = handler('getSlideCountRange',state)
  assert.equal(JSON.stringify(state.getSlideCountRange()), '{"min_pages":10,"max_pages":18}')
  assert.match(handler('buildContextMessage',state)(), /10至18页.*自主规划/)
  state.infoForm.minPages = undefined; state.infoForm.maxPages = undefined
  assert.equal(state.getSlideCountRange(), null)
  assert.doesNotMatch(handler('buildContextMessage',state)(), /PPT 总页数/)
})
