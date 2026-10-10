import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { parse, babelParse } from '@vue/compiler-sfc'
import { communityLoadError } from '../src/utils/communityLoadError.js'
const component = parse(readFileSync(new URL('../src/components/CommunityHub.vue', import.meta.url), 'utf8')).descriptor
const source = component.scriptSetup.content
const node = babelParse(source, { sourceType: 'module' }).program.body.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d => d.id.name === 'loadCommunity'))
const ref = value => ({ value })
test('skill and ppt responses populate cards using real API rows', async () => {
  for (const [tab, type] of [['Skill', 'skill'], ['PPT 课件', 'ppt']]) {
    const state = {
      communityRequestSeq: 0, loading: ref(false), communityError: ref(''), activeTab: ref(tab),
      selectedSubject: ref('全部学科'), selectedStage: ref('全部学段'), searchQuery: ref(''), sortBy: ref(''),
      communityPage: ref(1), communityPageSize: ref(12), communityCards: ref([]), communityTotal: ref(0), usingDemoCards: ref(false),
      listCommunityItems: async params => { assert.equal(params.content_type, type); return { data: { records: [{ id: 1, content_type: type }], total: 1 } } },
      assertApiSuccess: x => x, extractRecords: x => x.data.records, extractTotal: x => x.data.total,
      normalizeCard: x => x, syncLikeState() {},
    }
    await vm.runInNewContext(source.slice(node.start, node.end) + ';loadCommunity', state)()
    assert.equal(state.communityCards.value[0].content_type, type)
    assert.equal(state.communityTotal.value, 1)
    assert.equal(state.loading.value, false)
  }
})
test('unavailable backend is not presented as empty published content', () => {
  assert.match(communityLoadError({ request: {}, response: { status: 500, data: '' } }), /Java 后端已启动/)
  assert.match(communityLoadError({ request: {} }), /8088/)
  assert.equal(communityLoadError({ response: { status: 400, data: { message: '参数错误' } } }), '参数错误')
  assert.match(component.template.content, /!loading && !communityError && filteredCards.length === 0/)
  assert.match(component.template.content, /审核通过后才会展示/)
})
