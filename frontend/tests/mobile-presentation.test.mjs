import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizePreviewPages, parsePresentationValue } from '../src/utils/mobilePresentation.js'

test('cloud pages retain their saved HTML, notes and page order', () => {
  const input = [
    { id: 2, page_order: 2, page_title: '练习', page_content: JSON.stringify({ html: '<section>第二页</section>', notes: '分组讨论' }) },
    { id: 1, page_order: 1, page_content: { title: '封面', html: '<section>第一页</section>' } },
  ]
  const slides = normalizePreviewPages(input)
  assert.deepEqual(slides.map(slide => slide.title), ['封面', '练习'])
  assert.equal(slides[1].html, '<section>第二页</section>')
  assert.equal(slides[1].notes, '分组讨论')
  assert.equal(input[0].id, 2, 'normalization must not reorder or mutate the saved pages')
})

test('local drafts and legacy component pages remain readable', () => {
  const elements = [{ type: 'text', content: '课堂目标' }]
  assert.deepEqual(normalizePreviewPages({ records: [{ components: JSON.stringify(elements) }] })[0].elements, elements)
  assert.equal(normalizePreviewPages(['<section>草稿</section>'])[0].html, '<section>草稿</section>')
  assert.equal(normalizePreviewPages([{ title: '本地课件', html: '<p>内容</p>' }])[0].title, '本地课件')
})

test('empty and invalid server collections produce an empty preview', () => {
  for (const value of [undefined, null, {}, { records: {} }]) assert.deepEqual(normalizePreviewPages(value), [])
  assert.deepEqual(parsePresentationValue('invalid JSON'), {})
})
