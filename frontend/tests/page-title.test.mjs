import test from 'node:test'
import assert from 'node:assert/strict'
import { persistedPageTitle } from '../src/utils/pageTitle.js'

test('short titles and empty titles are normalized', () => {
  assert.equal(persistedPageTitle('  水解反应  '), '水解反应')
  assert.equal(persistedPageTitle(null, '第 7 页'), '第 7 页')
})
test('long titles are bounded without changing the source text', () => {
  const title = '计算机'.repeat(100)
  assert.equal(Array.from(persistedPageTitle(title)).length, 200)
  assert.equal(persistedPageTitle(title).endsWith('…'), true)
  assert.equal(title.length, 300)
  assert.equal(persistedPageTitle('字'.repeat(200)), '字'.repeat(200))
})
test('unicode characters are not split', () => {
  assert.equal(persistedPageTitle('😀'.repeat(201)), '😀'.repeat(199) + '…')
})
