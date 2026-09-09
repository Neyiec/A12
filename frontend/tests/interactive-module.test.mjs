import test from 'node:test'
import assert from 'node:assert/strict'
import { interactiveModuleTypeInfo, normalizeInteractiveModuleType } from '../src/utils/interactiveModule.js'

test('API-144 module types stay explicit and unknown values are not guessed', () => {
  assert.equal(normalizeInteractiveModuleType('animation'), 'animation')
  assert.equal(normalizeInteractiveModuleType('quiz-game'), 'quiz_game')
  assert.equal(normalizeInteractiveModuleType(''), 'unknown')
  assert.equal(normalizeInteractiveModuleType('server_new_type'), 'unknown')
  assert.equal(interactiveModuleTypeInfo('server_new_type').label, '未识别类型')
})
