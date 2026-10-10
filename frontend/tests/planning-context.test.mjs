import test from 'node:test'
import assert from 'node:assert/strict'

import { extractPlanningContext, isPlanningPrompt } from '../src/config/teacherChat.config.js'

test('初中科学二年级识别为八年级，保留学段和课题', () => {
  const context = extractPlanningContext('初中科学二年级《光的折射》')
  assert.equal(context.stage, '初中')
  assert.equal(context.subject, '科学')
  assert.equal(context.grade, '八年级')
  assert.equal(context.courseName, '光的折射')
})

test('简短的光的折射课件请求识别课程主题并进入备课', () => {
  assert.equal(extractPlanningContext('光的折射课件').courseName, '光的折射')
  assert.equal(extractPlanningContext('帮我生成光的折射课件').courseName, '光的折射')
  assert.equal(isPlanningPrompt('光的折射课件'), true)
  assert.equal(isPlanningPrompt('课件是什么'), false)
})

test('备课短句完整回填水解反应、化学、高三和高中', () => {
  for (const prompt of ['备课水解反应，高三', '备课 水解反应，高三', '帮我备课高三化学水解反应', '备课水解反应，高中三年级']) {
    const context = extractPlanningContext(prompt)
    assert.equal(context.courseName, '水解反应', prompt)
    assert.equal(context.subject, '化学', prompt)
    assert.equal(context.grade, '高三', prompt)
    assert.equal(context.stage, '高中', prompt)
  }
})

test('显式学科不被主题推断覆盖，不把通用反应一词当作化学', () => {
  assert.equal(extractPlanningContext('备课科学《水解反应》，八年级').subject, '科学')
  assert.equal(extractPlanningContext('备课条件反应，高三').subject, '')
  assert.equal(extractPlanningContext('备课水解反应课件，高三').courseName, '水解反应')
})
