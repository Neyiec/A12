import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('favorite success opens a paginated time-ordered folder with server favorite timestamp', () => {
  const source = readFileSync(new URL('../src/components/CommunityHub.vue', import.meta.url), 'utf8')
  assert.match(source, /collectionFavoritesOnly\.value = true/)
  assert.match(source, /favoritesPage\.value = 1/)
  assert.match(source, /按收藏时间从新到旧/)
  assert.match(source, /row\.favorited_at/)
  assert.match(source, /favoritePending\.value\.has/)
  assert.match(source, /v-if="favoritesTotal > 30"/)
})

test('favorites sort by interaction creation time with stable tie-breaking', () => {
  const mapper = readFileSync(new URL('../../backend-java/A12/src/main/resources/edu/zstu/mapper/ComInteractionMapper.xml', import.meta.url), 'utf8')
  const query = mapper.match(/<select id="findByUserAndAction"[\s\S]*?<\/select>/)[0]
  assert.match(query, /ORDER BY created_at DESC, id DESC/)
})
