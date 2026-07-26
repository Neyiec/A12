<!--
  [数据交互说明]
  - 导入: 社区演示数据、Vue Router、Element Plus 组件
  - 输出: Skill 与教学案例社区页面
-->
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CollectionTag, Search, Star, User } from '@element-plus/icons-vue'
import { COMMUNITY_PAGE } from '../config/teacherPages.config.js'
import { favoriteCommunityItem, listCommunityItems, reuseCommunityItem, unfavoriteCommunityItem } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const keyword = ref('')
const searchQuery = ref('')
const activeTab = ref('精选')
const selectedStage = ref('全部学段')
const selectedSubject = ref('全部学科')
const tabs = ['精选', '最新', 'Skill', '教学案例']
const communityCards = ref(COMMUNITY_PAGE.cards)
const favoriteIds = ref(new Set())
const loading = ref(false)

const normalizeCard = (item) => ({
  id: item.id, type: item.content_type === 'lesson_case' ? '案例' : 'Skill', title: item.title,
  subject: item.subject || '通用', stage: item.grade || '通用', author: item.author_name || item.author || '社区教师',
  uses: item.use_count ?? 0, tag: item.lesson_type || '教学设计', updatedAt: item.updated_at || '',
})

const loadCommunity = async () => {
  loading.value = true
  try {
    const contentType = activeTab.value === 'Skill' ? 'skill' : activeTab.value === '教学案例' ? 'lesson_case' : undefined
    const result = await listCommunityItems({ content_type: contentType, subject: selectedSubject.value === '全部学科' ? undefined : selectedSubject.value, grade: selectedStage.value === '全部学段' ? undefined : selectedStage.value, keyword: searchQuery.value || undefined, page: 1, size: 50 })
    const records = result?.data?.records || result?.data?.list || result?.data?.items || result?.records || []
    if (records.length) communityCards.value = records.map(normalizeCard)
  } catch { /* 服务未就绪时展示现有示例内容。 */ } finally { loading.value = false }
}

/** 提交关键词，避免输入过程中频繁改变社区结果。 */
const submitSearch = () => {
  searchQuery.value = keyword.value.trim().toLowerCase()
  loadCommunity()
}

/** 判断内容是否符合关键词、学段和学科条件。 */
const matchesFilters = (item) => {
  const searchableText = [item.title, item.subject, item.tag, item.author, item.type].join(' ').toLowerCase()
  const matchesSearch = !searchQuery.value || searchableText.includes(searchQuery.value)
  const matchesStage = selectedStage.value === '全部学段' || item.stage === selectedStage.value || item.stage === '通用'
  const matchesSubject = selectedSubject.value === '全部学科' || item.subject === selectedSubject.value || item.subject === '通用'
  return matchesSearch && matchesStage && matchesSubject
}

/** 根据当前页签和筛选条件生成社区卡片。 */
const filteredCards = computed(() => {
  const filtered = communityCards.value.filter((card) => {
    const matchesTab = activeTab.value === '精选'
      || activeTab.value === 'Skill' && card.type === 'Skill'
      || activeTab.value === '教学案例' && card.type === '案例'
      || activeTab.value === '最新'
    return matchesTab && matchesFilters(card)
  })
  return activeTab.value === '最新' ? [...filtered].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)) : filtered
})

/** 判断精选案例是否仍应展示。 */
const showFeatured = computed(() => activeTab.value === '精选' && matchesFilters(COMMUNITY_PAGE.featured))

/** 复制社区内容并进入个人创作工作台。 */
const reuse = async (item) => {
  if (!item.id) {
    ElMessage.info('示例内容仅用于预览，连接社区服务后可创建派生项目')
    return
  }
  try {
    const result = await reuseCommunityItem(item.id, { new_project_name: `${item.title}（副本）` })
    const projectId = result?.data?.id || result?.id
    ElMessage.success('已复制到个人空间')
    router.push({ path: '/main/workspace', query: { ...(route.query.preview ? { preview: '1' } : {}), ...(projectId ? { projectId } : {}) } })
  } catch { ElMessage.error('无法创建派生项目，请稍后重试') }
}
const toggleFavorite = async (item) => {
  if (!item.id) return ElMessage.info('示例内容暂不支持收藏')
  const next = !favoriteIds.value.has(item.id)
  try {
    if (next) await favoriteCommunityItem(item.id); else await unfavoriteCommunityItem(item.id)
    const updated = new Set(favoriteIds.value); next ? updated.add(item.id) : updated.delete(item.id); favoriteIds.value = updated
  } catch { ElMessage.error('收藏状态未能更新') }
}
watch([activeTab, selectedStage, selectedSubject], loadCommunity)
onMounted(loadCommunity)
</script>

<template>
  <div class="community-page">
    <header class="community-hero">
      <p>教师共创社区 / Community</p>
      <h1>把好课的经验，变成下一堂课的起点</h1>
      <span>检索公开可用的 Skill 与教学案例；复用后生成独立草稿，不会修改社区原件。</span>
      <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索知识点、学科、课型或 Skill" clearable size="large" @keyup.enter="submitSearch">
        <template #append><el-button type="primary" class="community-search-button" @click="submitSearch">搜索</el-button></template>
      </el-input>
    </header>

    <div class="community-toolbar">
      <div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ tab }}</button></div>
      <div class="filters">
        <el-select v-model="selectedStage" aria-label="筛选学段"><el-option label="全部学段" value="全部学段" /><el-option label="初中" value="初中" /><el-option label="高中" value="高中" /></el-select>
        <el-select v-model="selectedSubject" aria-label="筛选学科"><el-option label="全部学科" value="全部学科" /><el-option label="数学" value="数学" /><el-option label="物理" value="物理" /><el-option label="语文" value="语文" /><el-option label="生物" value="生物" /></el-select>
      </div>
    </div>

    <section v-if="showFeatured" class="featured-case">
      <div class="feature-visual">
        <span>3² + 4² = 5²</span>
        <i></i><i></i><i></i>
      </div>
      <div class="feature-copy">
        <el-tag effect="plain">{{ COMMUNITY_PAGE.featured.type }}</el-tag>
        <h2>{{ COMMUNITY_PAGE.featured.title }}</h2>
        <p>{{ COMMUNITY_PAGE.featured.description }}</p>
        <dl><div><dt>适用范围</dt><dd>{{ COMMUNITY_PAGE.featured.meta }}</dd></div><div><dt>作者</dt><dd>{{ COMMUNITY_PAGE.featured.author }}</dd></div></dl>
        <footer><span>{{ COMMUNITY_PAGE.featured.uses }}</span><el-button type="primary" @click="reuse(COMMUNITY_PAGE.featured)">基于此创作</el-button></footer>
      </div>
    </section>

    <section v-loading="loading" class="community-grid" aria-label="社区内容">
      <article v-for="card in filteredCards" :key="card.title" class="community-card">
        <div class="card-top"><span>{{ card.type }}</span><el-button text circle :type="favoriteIds.has(card.id) ? 'warning' : undefined" aria-label="收藏" @click="toggleFavorite(card)"><el-icon><Star /></el-icon></el-button></div>
        <div class="card-icon"><el-icon><CollectionTag /></el-icon></div>
        <h3>{{ card.title }}</h3>
        <p>{{ card.subject }} · {{ card.tag }}</p>
        <footer><span><el-icon><User /></el-icon>{{ card.author }}</span><button @click="reuse(card)">{{ card.uses }} 次使用 →</button></footer>
      </article>
      <el-empty v-if="filteredCards.length === 0" class="community-empty" description="没有符合当前筛选条件的 Skill 或教学案例" />
    </section>
    <p class="source-note">所有内容均标记来源、版本与授权信息；个人私有素材不会写回社区或进入公共索引。</p>
  </div>
</template>

<style scoped>
.community-page { width: min(1180px, calc(100% - 48px)); margin: 0 auto; padding: 40px 0 60px; }
.community-hero { max-width: 780px; padding: 26px 0 20px; }.community-hero > p { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 12px; font-weight: 600; letter-spacing: .08em; }
.community-hero h1 { max-width: 680px; margin: 0; font-size: clamp(32px, 4vw, 48px); line-height: 1.18; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.community-hero > span { display: block; max-width: 650px; margin-top: 16px; color: var(--zh-text-secondary); line-height: 1.7; }
.community-hero :deep(.el-input) { max-width: 650px; margin-top: 28px; }.community-hero :deep(.el-input__wrapper) { padding-left: 16px; }.community-hero :deep(.el-input-group__append) { padding: 0; background: var(--zh-background-button); box-shadow: none; }.community-hero :deep(.community-search-button) { width: 76px; min-width: 76px; height: 40px; margin: 0; border: 0; border-radius: 0 var(--zh-radius8) var(--zh-radius8) 0; color: var(--zh-text-white) !important; font-weight: 600; letter-spacing: var(--zh-tracking-normal); white-space: nowrap; transition: background 200ms cubic-bezier(.4, 0, .2, 1), transform 200ms cubic-bezier(.4, 0, .2, 1); }.community-hero :deep(.community-search-button:hover), .community-hero :deep(.community-search-button:focus-visible) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); }.community-hero :deep(.community-search-button:active) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); transform: scale(.98); }
.community-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 24px; border-bottom: 1px solid var(--zh-line-border); }
.tab-list { display: flex; gap: 20px; }.tab-list button { padding: 14px 2px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; cursor: pointer; }.tab-list button.active { color: var(--zh-text-theme); border-color: var(--zh-line-theme); font-weight: 600; }
.filters { display: flex; gap: 8px; }.filters :deep(.el-select) { width: 120px; }
.featured-case { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr); margin-top: 28px; overflow: hidden; border-radius: var(--zh-radius16); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }
.feature-visual { position: relative; min-height: 330px; display: grid; place-items: center; overflow: hidden; color: white; background: #173d78; }
.feature-visual::before { content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 68% 30%, rgb(96 165 250 / 55%), transparent 28%), linear-gradient(145deg, transparent 45%, rgb(255 255 255 / 8%) 45% 46%, transparent 46%); }
.feature-visual span { position: relative; z-index: 1; font: 600 clamp(30px, 4vw, 52px) var(--zh-font-number); letter-spacing: .03em; }
.feature-visual i { position: absolute; width: 80px; height: 80px; border: 1px solid rgb(255 255 255 / 22%); transform: rotate(45deg); }.feature-visual i:nth-of-type(1) { left: 8%; top: 16%; }.feature-visual i:nth-of-type(2) { right: 9%; bottom: 12%; width: 120px; height: 120px; }.feature-visual i:nth-of-type(3) { left: 36%; bottom: -38px; }
.feature-copy { display: flex; flex-direction: column; padding: 32px; }.feature-copy h2 { margin: 18px 0 10px; font-size: 26px; }.feature-copy > p { margin: 0; color: var(--zh-text-secondary); line-height: 1.75; }
.feature-copy dl { margin: 24px 0; }.feature-copy dl div { display: grid; grid-template-columns: 76px 1fr; padding: 8px 0; border-bottom: 1px solid var(--zh-line-parting); }.feature-copy dt { color: var(--zh-text-caption); font-size: 12px; }.feature-copy dd { margin: 0; font-size: 13px; }
.feature-copy footer { display: flex; align-items: center; justify-content: space-between; margin-top: auto; color: var(--zh-text-caption); font-size: 12px; }
.community-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 18px; }.community-card { padding: 18px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); transition: 200ms ease; }.community-card:hover { transform: translateY(-3px); border-color: var(--zh-line-theme20); box-shadow: var(--zh-shadow2); }
.community-empty { grid-column: 1 / -1; padding: 40px 0; border: 1px dashed var(--zh-line-heavier); border-radius: var(--zh-radius12); }
.card-top, .community-card footer { display: flex; align-items: center; justify-content: space-between; }.card-top > span { color: var(--zh-text-caption); font-size: 11px; }.card-icon { width: 38px; height: 38px; display: grid; place-items: center; margin-top: 18px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.community-card h3 { min-height: 44px; margin: 18px 0 8px; font-size: 15px; line-height: 1.5; }.community-card > p { margin: 0 0 28px; color: var(--zh-text-caption); font-size: 12px; }.community-card footer { gap: 8px; border-top: 1px solid var(--zh-line-parting); padding-top: 12px; font-size: 11px; }.community-card footer span { min-width: 0; display: flex; align-items: center; gap: 4px; overflow: hidden; color: var(--zh-text-caption); text-overflow: ellipsis; white-space: nowrap; }.community-card footer button { flex: none; border: 0; color: var(--zh-text-link); background: transparent; cursor: pointer; font-size: 11px; }
.source-note { margin: 20px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }
@media (max-width: 980px) { .community-grid { grid-template-columns: repeat(2, 1fr); }.featured-case { grid-template-columns: 1fr; }.feature-visual { min-height: 240px; } }
@media (max-width: 600px) { .community-toolbar { align-items: stretch; flex-direction: column; }.filters { padding-bottom: 12px; }.community-grid { grid-template-columns: 1fr; } }
</style>
