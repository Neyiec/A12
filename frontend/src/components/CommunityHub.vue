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
import { createCommunityReport, createCommunitySubmission, favoriteCommunityItem, getCommunityItem, listCommunityFavorites, listCommunityItems, listCommunityRecentViews, listCommunityReports, listCommunitySubmissions, recordCommunityView, removeCommunityRecentView, reuseCommunityItem, saveCommunitySubmissionVersion, submitCommunitySubmission, unfavoriteCommunityItem, updateCommunitySubmission } from '../apis/teacher'

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
const detailVisible = ref(false), submissionVisible = ref(false), collectionVisible = ref(false), reportVisible = ref(false)
const detail = ref(null), favorites = ref([]), recentViews = ref([]), submissions = ref([]), reports = ref([])
const submission = ref({ id: null, content_type: 'lesson_case', title: '', description: '', subject: '', grade: '', lesson_type: '', content_data: '', license: 'CC BY-NC 4.0' })
const reportForm = ref({ target_id: null, reason: '', comment: '' })

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
  if (item.testCaseId) {
    ElMessage.success('测试案例已载入创作工作台')
    router.push({
      path: '/main/workspace',
      query: {
        ...(route.query.preview ? { preview: '1' } : {}),
        testCase: item.testCaseId,
        templateTitle: item.title,
      },
    })
    return
  }
  if (!item.id) {
    ElMessage.info('该内容暂时无法创建派生项目')
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
  const favoriteKey = item.id || item.testCaseId
  if (!favoriteKey) return ElMessage.info('该内容暂不支持收藏')
  const next = !favoriteIds.value.has(favoriteKey)
  if (item.testCaseId) {
    const updated = new Set(favoriteIds.value); next ? updated.add(favoriteKey) : updated.delete(favoriteKey); favoriteIds.value = updated
    ElMessage.success(next ? '已收藏测试案例' : '已取消收藏')
    return
  }
  try {
    if (next) await favoriteCommunityItem(item.id); else await unfavoriteCommunityItem(item.id)
    const updated = new Set(favoriteIds.value); next ? updated.add(favoriteKey) : updated.delete(favoriteKey); favoriteIds.value = updated
  } catch { ElMessage.error('收藏状态未能更新') }
}
const unwrap = (value) => value?.data || value
const records = (value) => { const data = unwrap(value); return data?.records || data?.list || data?.items || [] }
const openDetail = async (item) => { if (!item.id) return; try { detail.value = unwrap(await getCommunityItem(item.id)); detailVisible.value = true; await recordCommunityView(item.id) } catch (error) { ElMessage.error(error?.message || '内容详情加载失败') } }
const openCollections = async () => { collectionVisible.value = true; try { [favorites.value, recentViews.value] = await Promise.all([listCommunityFavorites({ page: 1, size: 30 }).then(records), listCommunityRecentViews({ page: 1, size: 30 }).then(records)]) } catch (error) { ElMessage.error(error?.message || '收藏记录加载失败') } }
const removeView = async (item) => { try { await removeCommunityRecentView(item.item_id || item.id); recentViews.value = recentViews.value.filter((row) => (row.item_id || row.id) !== (item.item_id || item.id)) } catch { ElMessage.error('浏览记录删除失败') } }
const openSubmission = async () => { submission.value = { id: null, content_type: 'lesson_case', title: '', description: '', subject: '', grade: '', lesson_type: '', content_data: '', license: 'CC BY-NC 4.0' }; submissionVisible.value = true; try { submissions.value = await listCommunitySubmissions({ page: 1, size: 20 }).then(records) } catch { submissions.value = [] } }
const saveSubmission = async (submit = false) => { if (!submission.value.title.trim()) return ElMessage.warning('请输入投稿标题'); try { const payload = { ...submission.value }; delete payload.id; const saved = submission.value.id ? unwrap(await updateCommunitySubmission(submission.value.id, payload)) : unwrap(await createCommunitySubmission(payload)); submission.value.id = saved?.id || submission.value.id; await saveCommunitySubmissionVersion(submission.value.id, { description: '教师保存投稿草稿' }); if (submit) await submitCommunitySubmission(submission.value.id, { source_declaration: '本人原创或已获得授权', notes: '' }); ElMessage.success(submit ? '投稿已提交审核' : '投稿草稿已保存') } catch (error) { ElMessage.error(error?.message || '投稿保存失败') } }
const openReports = async () => { reportVisible.value = true; try { reports.value = await listCommunityReports({ page: 1, size: 30 }).then(records) } catch { reports.value = [] } }
const reportItem = async () => { if (!reportForm.value.target_id || !reportForm.value.reason.trim()) return ElMessage.warning('请填写举报原因'); try { await createCommunityReport({ audit_type: 'report', target_type: 'community_item', target_id: reportForm.value.target_id, reason: reportForm.value.reason, comment: reportForm.value.comment }); ElMessage.success('举报已提交'); reportForm.value = { target_id: null, reason: '', comment: '' } } catch (error) { ElMessage.error(error?.message || '举报提交失败') } }
watch([activeTab, selectedStage, selectedSubject], loadCommunity)
onMounted(loadCommunity)
</script>

<template>
  <div class="community-page">
    <header class="community-hero">
      <p>教师共创社区 / Community</p>
      <h1>把好课的经验，变成下一堂课的起点</h1>
      <span>检索公开可用的 Skill 与教学案例；复用后生成独立草稿，不会修改社区原件。</span>
      <div class="community-search-row">
        <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索知识点、学科、课型或 Skill" clearable size="large" @keyup.enter="submitSearch">
          <template #append><el-button type="primary" class="community-search-button" @click="submitSearch">搜索</el-button></template>
        </el-input>
        <el-button type="primary" class="submission-button" @click="openSubmission">我要投稿</el-button>
      </div>
    </header>

    <div class="community-toolbar">
      <div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ tab }}</button></div>
      <div class="toolbar-controls">
        <el-button text @click="openCollections">收藏与浏览</el-button>
        <el-button text @click="openReports">举报进度</el-button>
      <div class="filters">
        <el-select v-model="selectedStage" aria-label="筛选学段"><el-option label="全部学段" value="全部学段" /><el-option label="初中" value="初中" /><el-option label="高中" value="高中" /></el-select>
        <el-select v-model="selectedSubject" aria-label="筛选学科"><el-option label="全部学科" value="全部学科" /><el-option label="数学" value="数学" /><el-option label="物理" value="物理" /><el-option label="语文" value="语文" /><el-option label="生物" value="生物" /></el-select>
      </div>
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
        <div class="card-top"><span>{{ card.type }}</span><el-button text circle :type="favoriteIds.has(card.id || card.testCaseId) ? 'warning' : undefined" aria-label="收藏" @click="toggleFavorite(card)"><el-icon><Star /></el-icon></el-button></div>
        <div class="card-icon"><el-icon><CollectionTag /></el-icon></div>
        <h3>{{ card.title }}</h3>
        <p>{{ card.subject }} · {{ card.tag }}</p>
        <footer><span><el-icon><User /></el-icon>{{ card.author }}</span><button @click="reuse(card)">{{ card.testCaseId ? '进入工作台 →' : `${card.uses} 次使用 →` }}</button></footer>
      </article>
      <el-empty v-if="filteredCards.length === 0" class="community-empty" description="没有符合当前筛选条件的 Skill 或教学案例" />
    </section>
    <p class="source-note">所有内容均标记来源、版本与授权信息；个人私有素材不会写回社区或进入公共索引。</p>
  </div>
    <el-dialog v-model="submissionVisible" title="投稿到教师社区" width="min(700px, 92vw)"><el-form label-position="top"><div class="submission-grid"><el-form-item label="标题"><el-input v-model="submission.title" /></el-form-item><el-form-item label="内容类型"><el-select v-model="submission.content_type"><el-option label="教学案例" value="lesson_case" /><el-option label="Skill" value="skill" /></el-select></el-form-item><el-form-item label="学科"><el-input v-model="submission.subject" /></el-form-item><el-form-item label="学段"><el-input v-model="submission.grade" /></el-form-item></div><el-form-item label="简介"><el-input v-model="submission.description" type="textarea" :rows="2" /></el-form-item><el-form-item label="正文 / 结构化内容"><el-input v-model="submission.content_data" type="textarea" :rows="7" /></el-form-item></el-form><div class="draft-list"><span>我的投稿草稿</span><el-button v-for="item in submissions" :key="item.id" text @click="submission = { ...submission, ...item }">{{ item.title }}</el-button></div><template #footer><el-button @click="saveSubmission(false)">保存草稿</el-button><el-button type="primary" @click="saveSubmission(true)">提交审核</el-button></template></el-dialog>
    <el-dialog v-model="collectionVisible" title="我的收藏与最近浏览" width="min(680px, 92vw)"><section class="collection-section"><h3>我的收藏</h3><p v-for="item in favorites" :key="item.id">{{ item.title }}</p><el-empty v-if="!favorites.length" description="暂无收藏" /></section><section class="collection-section"><h3>最近浏览</h3><p v-for="item in recentViews" :key="item.item_id || item.id"><span>{{ item.title || item.item_title || `内容 #${item.item_id}` }}</span><el-button text size="small" @click="removeView(item)">删除</el-button></p><el-empty v-if="!recentViews.length" description="暂无浏览记录" /></section></el-dialog>
    <el-dialog v-model="reportVisible" title="举报与处理进度" width="min(600px, 92vw)"><el-form label-position="top"><el-form-item label="内容 ID"><el-input v-model="reportForm.target_id" inputmode="numeric" /></el-form-item><el-form-item label="举报原因"><el-input v-model="reportForm.reason" /></el-form-item><el-form-item label="补充说明"><el-input v-model="reportForm.comment" type="textarea" :rows="3" /></el-form-item></el-form><el-button type="primary" @click="reportItem">提交举报</el-button><div class="report-list"><p v-for="report in reports" :key="report.id">#{{ report.id }} · {{ report.status || '处理中' }} · {{ report.reason || report.comment }}</p><el-empty v-if="!reports.length" description="暂无举报记录" /></div></el-dialog>
    <el-dialog v-model="detailVisible" :title="detail?.title || '社区内容详情'" width="min(720px, 92vw)"><p class="detail-meta">{{ detail?.subject }} · {{ detail?.grade }} · {{ detail?.lesson_type }}</p><p>{{ detail?.description }}</p><pre class="detail-content">{{ detail?.content_data || detail?.example_effect }}</pre><template #footer><el-button type="danger" plain @click="reportForm = { target_id: detail?.id, reason: '', comment: '' }; reportVisible = true">举报内容</el-button><el-button type="primary" @click="reuse(detail)">复用此内容</el-button></template></el-dialog>
</template>

<style scoped>
.community-page { width: min(1180px, calc(100% - 48px)); margin: 0 auto; padding: 40px 0 60px; }
.community-hero { width: 100%; padding: 26px 0 20px; }.community-hero > p { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 12px; font-weight: 600; letter-spacing: .08em; }
.community-hero h1 { max-width: 680px; margin: 0; font-size: clamp(32px, 4vw, 48px); line-height: 1.18; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.community-hero > span { display: block; max-width: 650px; margin-top: 16px; color: var(--zh-text-secondary); line-height: 1.7; }
.community-search-row { width: 100%; display: flex; align-items: center; gap: 12px; margin-top: 28px; }.community-search-row :deep(.el-input) { width: min(650px, calc(100% - 140px)); flex: 0 1 650px; }.community-search-row>.submission-button { min-width: 112px; margin: 0 0 0 auto; color: var(--zh-text-white); font-weight: 600; }.community-hero :deep(.el-input__wrapper) { padding-left: 16px; }.community-hero :deep(.el-input-group__append) { padding: 0; background: var(--zh-background-button); box-shadow: none; }.community-hero :deep(.community-search-button) { width: 76px; min-width: 76px; height: 40px; margin: 0; border: 0; border-radius: 0 var(--zh-radius8) var(--zh-radius8) 0; color: var(--zh-text-white) !important; font-weight: 600; letter-spacing: var(--zh-tracking-normal); white-space: nowrap; transition: background 200ms cubic-bezier(.4, 0, .2, 1), transform 200ms cubic-bezier(.4, 0, .2, 1); }.community-hero :deep(.community-search-button:hover), .community-hero :deep(.community-search-button:focus-visible) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); }.community-hero :deep(.community-search-button:active) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); transform: scale(.98); }
.community-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 24px; border-bottom: 1px solid var(--zh-line-border); }
.toolbar-controls { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }.filters { display: flex; gap: 8px; margin-left: 8px; }.submission-button { min-width: 104px; color: var(--zh-text-white); font-weight: 600; }.submission-button:hover, .submission-button:focus-visible { color: var(--zh-text-white); background: var(--zh-background-button-hover); border-color: var(--zh-background-button-hover); }
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
@media (max-width: 600px) { .community-search-row { align-items: stretch; flex-direction: column; }.community-search-row :deep(.el-input) { width: 100%; flex-basis: auto; }.community-search-row>.submission-button { width: 100%; margin-left: 0; }.community-toolbar { align-items: stretch; flex-direction: column; }.filters { padding-bottom: 12px; }.community-grid { grid-template-columns: 1fr; } }
.community-actions{display:flex;justify-content:center;gap:8px;margin-top:24px}.submission-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px}.submission-grid :deep(.el-form-item){margin-bottom:0}.draft-list{display:flex;align-items:center;gap:4px;overflow:auto;padding:10px;border-radius:var(--zh-radius8);background:var(--zh-background-light);font-size:12px}.draft-list span{flex:none;color:var(--zh-text-caption)}.collection-section{margin-bottom:20px}.collection-section h3{font-size:14px}.collection-section p{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--zh-line-parting);color:var(--zh-text-secondary);font-size:13px}.report-list{margin-top:16px;padding-top:12px;border-top:1px solid var(--zh-line-border)}.report-list p{padding:8px 0;border-bottom:1px solid var(--zh-line-parting);color:var(--zh-text-secondary);font-size:12px}.detail-meta{color:var(--zh-text-caption);font-size:12px}.detail-content{max-height:360px;overflow:auto;padding:14px;border-radius:var(--zh-radius8);background:var(--zh-background-light);font:12px/1.65 var(--zh-font-code);white-space:pre-wrap}@media(max-width:600px){.submission-grid{grid-template-columns:1fr}.community-actions{flex-wrap:wrap}}
</style>
