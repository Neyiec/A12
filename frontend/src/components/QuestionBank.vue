<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Document, EditPen, Filter, Plus, Search } from '@element-plus/icons-vue'
import { listQuestions, getQuestion, saveQuestion, listPapers, getPaper, savePaper } from '../apis/questionBank'
import { subjects, grades, questionTypes, difficulties, questionStatuses, emptyQuestion, addToBasket, totalScore, paperItems } from '../utils/questionBank'
import { useMobileViewport } from '../composables/useMobileViewport'
import QuestionContent from './QuestionContent.vue'
import QuestionEditor from './QuestionEditor.vue'
import PaperComposer from './PaperComposer.vue'
import MobileSection from './MobileSection.vue'

const isMobile = useMobileViewport()
const filtersOpen = ref(false)
const tab=ref('public'), rows=ref([]), total=ref(0), loading=ref(false), error=ref(''), busy=ref(false)
const filter=reactive({keyword:'',subject:'',grade:'',question_type:'',difficulty:'',page:1,size:12})
const basket=ref([]), compose=ref(false), editor=ref(false), question=ref(emptyQuestion()), detail=ref(null), showAnswer=ref(false), papers=ref([])
const paper=ref({title:'',duration_minutes:45}), preview=ref(false), answerSheet=ref(false), dirty=ref(false)
const papersLoading = ref(false)
const papersError = ref('')
const score=computed(()=>totalScore(basket.value))
const activeFilterCount = computed(() => [filter.subject, filter.grade, filter.question_type, filter.difficulty].filter(Boolean).length)
const canEdit = row => tab.value === 'mine' && ['draft', 'rejected'].includes(row.status)
const canAdd = row => row.status === 'approved' || (tab.value === 'mine' && row.status === 'draft')
const isInBasket = row => basket.value.some(item => item.id === row.id)
const addLabel = row => isInBasket(row) ? '已加入' : row.status === 'draft' ? '加入题篮（自用）' : '加入题篮'
const statusType = status => ({ approved: 'success', rejected: 'danger' })[status] || 'warning'
let requestId=0
async function load(){const token=++requestId;loading.value=true;error.value='';try{const result=await listQuestions({...filter,scope:tab.value==='mine'?'mine':'public'});if(token===requestId){rows.value=result.items;total.value=result.total}}catch(e){if(token===requestId)error.value=e.message}finally{if(token===requestId)loading.value=false}}
async function loadPapers() {
  if (papersLoading.value) return
  papersLoading.value = true
  papersError.value = ''
  try { papers.value = await listPapers() }
  catch (error) { papersError.value = error.message }
  finally { papersLoading.value = false }
}
function switchTab() {
  filter.page = 1
  filtersOpen.value = false
  return tab.value === 'papers' ? loadPapers() : load()
}
function search() {
  filter.page = 1
  filtersOpen.value = false
  return load()
}
function resetFilters() {
  Object.assign(filter, { subject: '', grade: '', question_type: '', difficulty: '' })
  return search()
}
async function openDetail(row){try{detail.value=await getQuestion(row.id);showAnswer.value=false}catch(e){ElMessage.error(e.message)}}
function notifySuccess(message) {
  ElMessage.success(isMobile.value ? { message, customClass: 'question-bank-toast' } : message)
}
function add(row) {
  const { stem, answer, analysis, options } = row.content
  if (!stem?.trim() || !answer?.trim() || !analysis?.trim() || options?.some(option => !option.trim())) {
    ElMessage.warning('草稿尚未完成，请先补齐题干、选项、答案和解析')
    return
  }
  try {
    basket.value = addToBasket(basket.value, { ...row.content, id: row.id })
    dirty.value = true
    notifySuccess(compose.value ? '已加入试卷' : '已加入题篮')
  } catch (error) {
    ElMessage.warning(error.message)
  }
}
function edit(row){question.value=row?{...JSON.parse(JSON.stringify(row.content)),id:row.id,revision:row.revision}:emptyQuestion();editor.value=true}
function copy(row){question.value=JSON.parse(JSON.stringify(row.content));editor.value=true}
function editFromDetail(asCopy) {
  const row = detail.value
  detail.value = null
  if (asCopy) copy(row)
  else edit(row)
}
async function persistQuestion(action) {
  if (busy.value) return
  busy.value = true
  try {
    await saveQuestion(question.value, action)
    editor.value = false
    notifySuccess(action === 'submit' ? '已提交审核；通过后进入公共题库' : '草稿已保存')
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    busy.value = false
  }
}
async function persistPaper() {
  if (busy.value) return
  if (!basket.value.length) return ElMessage.warning('请先从题库选择题目')
  if (!paper.value.title?.trim()) return ElMessage.warning('请先在试卷设置中填写试卷名称')
  busy.value = true
  try {
    const saved = await savePaper({
      ...paper.value,
      subject: basket.value[0].subject,
      items: basket.value.map(item => ({ question_id: item.id, score: item.score })),
    })
    paper.value = { id: saved.id, revision: saved.revision, title: saved.title, duration_minutes: saved.duration_minutes }
    basket.value = paperItems(saved)
    await nextTick()
    dirty.value = false
    notifySuccess('试卷已保存，题目内容已固定')
    if (tab.value === 'papers') await switchTab()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    busy.value = false
  }
}
async function loadPaper(row){if(dirty.value){try{await ElMessageBox.confirm('当前试卷有未保存内容，打开试卷会替换它。是否继续？','打开试卷')}catch{return}}try{const saved=await getPaper(row.id);basket.value=paperItems(saved);paper.value={id:saved.id,revision:saved.revision,title:saved.title,duration_minutes:saved.duration_minutes};await nextTick();dirty.value=false;compose.value=true}catch(e){ElMessage.error(e.message)}}
async function newPaper(){if(dirty.value){try{await ElMessageBox.confirm('新建会清空当前题篮，请先保存需要保留的试卷。','新建试卷')}catch{return}}basket.value=[];paper.value={title:'',duration_minutes:45};dirty.value=false;compose.value=true}
watch(tab,switchTab)
watch(()=>[paper.value.title,paper.value.duration_minutes],()=>{if(basket.value.length)dirty.value=true})
onMounted(load)
onBeforeRouteLeave(async()=>{if(!dirty.value)return true;try{await ElMessageBox.confirm('试卷有未保存的修改，离开后将丢失。请先保存试卷，或确认放弃。','离开题库',{confirmButtonText:'放弃并离开',cancelButtonText:'返回保存'});return true}catch{return false}})
const warnUnload=(event)=>{if(dirty.value){event.preventDefault();event.returnValue=''}}
onMounted(()=>window.addEventListener('beforeunload',warnUnload))
onBeforeUnmount(()=>window.removeEventListener('beforeunload',warnUnload))
function print(){window.print()}
</script>
<template>
  <main class="question-bank" :class="{ 'is-mobile-bank': isMobile }">
    <header class="hero">
      <div v-if="!isMobile"><span class="eyebrow">QUESTION BANK / 教学评价</span><h1>题库与组卷</h1><p>先按学科找题，加入题篮，再到组卷工作台设置顺序与分值。也可以投稿你的题目，经审核后共享给教师。</p></div>
      <div v-if="isMobile" class="mobile-bank-actions">
        <el-button v-if="tab === 'papers'" :icon="Plus" @click="newPaper">新建试卷</el-button>
        <el-button v-else :icon="EditPen" @click="edit()">设计题目</el-button>
        <el-button type="primary" :icon="Document" @click="compose = true">
          {{ basket.length ? `组卷（${basket.length}）` : '组卷' }}
        </el-button>
      </div>
      <div v-else class="actions"><el-button @click="edit()">＋ 设计题目</el-button><el-badge :value="basket.length" :hidden="!basket.length" type="primary"><el-button type="primary" @click="compose=true">组卷</el-button></el-badge></div>
    </header>
    <div v-if="!isMobile" class="steps"><span>① 公共题库找题</span><span>② 加入题篮</span><span>③ 设置分值并保存 / 打印</span></div>
    <el-tabs v-model="tab"><el-tab-pane label="公共题库" name="public"/><el-tab-pane label="我的投稿" name="mine"/><el-tab-pane label="我的试卷" name="papers"/></el-tabs>
    <template v-if="tab!=='papers'">
      <form class="filters" @submit.prevent="search">
        <el-input v-model="filter.keyword" clearable maxlength="120" aria-label="搜索题干或知识点"
          :prefix-icon="isMobile ? Search : undefined" :placeholder="isMobile ? '搜索题干、知识点' : '搜索题干或知识点，如：勾股定理'">
          <template v-if="isMobile" #append><el-button class="mobile-search-action" native-type="submit">搜索</el-button></template>
        </el-input>
        <el-button v-if="isMobile" class="mobile-icon-button" :icon="Filter"
          :type="activeFilterCount || filtersOpen ? 'primary' : undefined" :plain="Boolean(activeFilterCount || filtersOpen)"
          :aria-label="activeFilterCount ? `筛选题目，已选 ${activeFilterCount} 项` : '筛选题目'"
          :aria-expanded="filtersOpen" aria-controls="question-bank-filters" @click="filtersOpen = !filtersOpen" />
        <div v-show="!isMobile || filtersOpen" id="question-bank-filters" class="advanced-filters">
          <el-select v-model="filter.subject" placeholder="全部学科" aria-label="学科" clearable filterable><el-option v-for="s in subjects" :key="s" :value="s"/></el-select>
          <el-select v-model="filter.grade" placeholder="全部年级" aria-label="年级" clearable><el-option v-for="s in grades" :key="s" :value="s"/></el-select>
          <el-select v-model="filter.question_type" placeholder="全部题型" aria-label="题型" clearable><el-option v-for="(label,key) in questionTypes" :key="key" :label="label" :value="key"/></el-select>
          <el-select v-model="filter.difficulty" placeholder="全部难度" aria-label="难度" clearable><el-option v-for="(label,key) in difficulties" :key="key" :label="label" :value="key"/></el-select>
          <div v-if="isMobile" class="filter-actions">
            <el-button text @click="resetFilters">重置</el-button>
            <el-button type="primary" native-type="submit">应用筛选</el-button>
          </div>
        </div>
        <el-button v-if="!isMobile" type="primary" native-type="submit">查找题目</el-button>
      </form>
      <p v-if="!isMobile" class="muted">{{ total }} 道题目 · {{ tab==='public'?'仅展示审核通过的题目，答案可在详情中查看':'草稿可继续编辑；被退回的题目可修改后再次提交' }}</p>
      <p v-else-if="!error" class="mobile-bank-count" aria-live="polite">{{ loading ? '正在加载题目…' : `${total} 道题目` }}</p>
      <el-alert v-if="error" type="error" :title="error" show-icon :closable="false"><el-button @click="load">重试</el-button></el-alert>
      <section v-loading="loading" class="question-list">
        <el-empty v-if="!rows.length&&!loading&&!error" :image-size="isMobile ? 76 : undefined"
          :description="tab === 'mine' ? '还没有符合条件的投稿' : '暂无符合条件的题目'" />
        <article v-for="row in rows" :key="row.id" class="card">
          <template v-if="isMobile">
            <button type="button" class="question-card-link" @click="openDetail(row)">
              <span class="question-card-copy">
                <span class="question-card-meta">{{ row.subject }} · {{ row.grade }} · {{ questionTypes[row.question_type] }}</span>
                <strong class="question-card-title">{{ row.content.stem || '未填写题干' }}</strong>
              </span>
              <el-icon aria-hidden="true"><ArrowRight /></el-icon>
            </button>
            <footer class="question-card-footer">
              <el-tag v-if="tab === 'mine'" :type="statusType(row.status)">{{ questionStatuses[row.status] }}</el-tag>
              <span v-else class="question-card-meta">{{ difficulties[row.difficulty] }}</span>
              <el-button v-if="canAdd(row)" type="primary" plain :disabled="isInBasket(row)" @click="add(row)">{{ addLabel(row) }}</el-button>
            </footer>
          </template>
          <template v-else>
            <div class="tags"><el-tag>{{ row.subject }} · {{ row.grade }}</el-tag><el-tag type="info">{{ questionTypes[row.question_type] }}</el-tag><el-tag type="info">{{ difficulties[row.difficulty] }}</el-tag><el-tag v-if="tab==='mine'" :type="statusType(row.status)">{{ questionStatuses[row.status] }}</el-tag></div>
            <QuestionContent :question="row.content" />
            <p v-if="row.knowledge_points" class="muted">知识点：{{ row.knowledge_points }}</p>
            <el-alert v-if="row.review_note&&tab==='mine'" :title="`审核意见：${row.review_note}`" :closable="false" type="warning"/>
            <footer><el-button @click="openDetail(row)">查看答案与解析</el-button><el-button v-if="canEdit(row)" @click="edit(row)">编辑 / 提交审核</el-button><el-button @click="copy(row)">复制改编</el-button><el-button v-if="canAdd(row)" type="primary" :disabled="isInBasket(row)" @click="add(row)">{{ addLabel(row) }}</el-button></footer>
          </template>
        </article>
      </section>
      <el-pagination v-if="total" v-model:current-page="filter.page" :page-size="filter.size" :total="total"
        :layout="isMobile ? 'prev, slot, next' : 'prev, pager, next, total'" :hide-on-single-page="isMobile" @current-change="load">
        <span class="mobile-bank-count">第 {{ filter.page }} / {{ Math.ceil(total / filter.size) }} 页</span>
      </el-pagination>
    </template>
    <template v-else>
      <el-button v-if="!isMobile" @click="newPaper">新建试卷</el-button>
      <el-alert v-if="papersError" type="error" :title="papersError" :closable="false"><el-button @click="loadPapers">重试</el-button></el-alert>
      <section v-loading="papersLoading" class="paper-list">
        <el-empty v-if="!papers.length && !papersLoading && !papersError" description="还没有保存的试卷" :image-size="isMobile ? 76 : undefined" />
        <article v-for="p in papers" :key="p.id" class="card paper-row">
          <button v-if="isMobile" type="button" class="question-card-link" @click="loadPaper(p)">
            <span class="question-card-copy">
              <strong class="question-card-title">{{ p.title }}</strong>
              <span class="question-card-meta">{{ p.subject }} · {{ p.total_score }} 分 · {{ p.duration_minutes }} 分钟</span>
            </span>
            <el-icon aria-hidden="true"><ArrowRight /></el-icon>
          </button>
          <template v-else>
            <div><h3>{{ p.title }}</h3><p class="muted">{{ p.subject }} · {{ p.total_score }} 分 · {{ p.duration_minutes }} 分钟 · v{{ p.revision }}</p></div>
            <el-button type="primary" @click="loadPaper(p)">打开 / 打印</el-button>
          </template>
        </article>
      </section>
    </template>
    <el-dialog v-model="editor" class="question-edit-dialog" :class="{ 'is-mobile-question-dialog': isMobile }"
      :title="isMobile ? '设计题目' : '设计题目 · 草稿保存后可继续完善'"
      :width="isMobile ? 'calc(100vw - 32px)' : 'min(860px,95vw)'" :close-on-click-modal="false">
      <QuestionEditor v-model="question" />
      <template #footer>
        <el-button v-if="!isMobile" @click="editor=false">取消</el-button>
        <el-button :loading="busy" @click="persistQuestion('draft')">保存草稿</el-button>
        <el-button type="primary" :loading="busy" @click="persistQuestion('submit')">{{ isMobile ? '提交审核' : '提交后台审核' }}</el-button>
      </template>
    </el-dialog>
    <el-dialog :model-value="!!detail" title="题目详情" class="question-detail-dialog" :class="{ 'is-mobile-question-dialog': isMobile }"
      :width="isMobile ? 'calc(100vw - 32px)' : 'min(800px,95vw)'" @close="detail = null">
      <template v-if="detail">
        <div v-if="isMobile" class="detail-meta">
          <span>{{ detail.subject }} · {{ detail.grade }} · {{ questionTypes[detail.question_type] }}</span>
          <span>{{ difficulties[detail.difficulty] }}</span>
        </div>
        <QuestionContent :question="detail.content" :answers="showAnswer" />
        <el-button :class="{ 'answer-toggle': isMobile }" :aria-expanded="showAnswer" @click="showAnswer = !showAnswer">{{ showAnswer ? '隐藏答案' : '显示答案与解析' }}</el-button>
        <MobileSection v-if="isMobile && (detail.knowledge_points || detail.review_note || detail.reviews?.length)" title="题目信息">
          <p v-if="detail.knowledge_points" class="muted">知识点：{{ detail.knowledge_points }}</p>
          <p v-if="detail.review_note && !detail.reviews?.length" class="muted">审核意见：{{ detail.review_note }}</p>
          <p v-for="(r, i) in detail.reviews || []" :key="i" class="muted">{{ r.created_at }} · {{ r.decision }} · {{ r.note }}</p>
        </MobileSection>
        <template v-if="!isMobile && detail.reviews?.length">
          <el-divider /><p v-for="(r, i) in detail.reviews" :key="i" class="muted">{{ r.created_at }} · {{ r.decision }} · {{ r.note }}</p>
        </template>
      </template>
      <template v-if="isMobile && detail" #footer>
        <el-button @click="editFromDetail(true)">复制改编</el-button>
        <el-button v-if="canEdit(detail)" type="primary" @click="editFromDetail(false)">编辑题目</el-button>
        <el-button v-else-if="canAdd(detail)" type="primary" :disabled="isInBasket(detail)" @click="add(detail)">{{ addLabel(detail) }}</el-button>
      </template>
    </el-dialog>
    <PaperComposer v-model="compose" v-model:questions="basket" v-model:paper="paper" :is-mobile="isMobile"
      :busy="busy" :dirty="dirty" @change="dirty=true" @add="add" @save="persistPaper" @preview="preview=true"/>
    <el-dialog v-model="preview" title="试卷预览" class="paper-preview" :class="{ 'is-mobile-question-dialog': isMobile }"
      :width="isMobile ? 'calc(100vw - 32px)' : 'min(900px,96vw)'">
      <div class="print-controls"><el-switch v-model="answerSheet" active-text="答案解析版" inactive-text="学生作答版"/><el-button type="primary" @click="print">打印 / 另存 PDF</el-button><p class="muted">打印窗口可选择“另存为 PDF”。{{ dirty?'当前预览含未保存修改，请先保存需要保留的试卷。':'' }}</p></div>
      <section class="print-paper"><h1>{{ paper.title||'课堂练习' }}</h1><p>{{ basket[0]?.subject }} · {{ paper.duration_minutes }} 分钟 · 满分 {{ score }} 分</p><p v-if="!answerSheet">班级：________ 姓名：________ 日期：________</p><article v-for="(q,i) in basket" :key="q.id" class="print-question"><h3>{{ i+1 }}. {{ questionTypes[q.question_type] }}（{{ q.score }} 分）</h3><QuestionContent :question="q" :answers="answerSheet"/><div v-if="!answerSheet&&['short','calculation'].includes(q.question_type)" class="answer-space"></div></article></section>
    </el-dialog>
  </main>
</template>
<style scoped>
.question-bank{max-width:1240px;margin:auto;padding:36px 24px 100px;background:#fff;color:#183451}.hero{display:flex;align-items:center;justify-content:space-between;gap:24px}.hero h1{font-size:30px;margin:12px 0;line-height:1.4}.hero p,.muted{color:#6b7e96;line-height:1.7}.eyebrow{color:#2563eb;font-weight:600}.actions,footer,.tags{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.actions{flex-shrink:0}.steps{display:flex;gap:32px;background:#eff6ff;border-radius:12px;padding:18px;margin:24px 0;color:#305e97;flex-wrap:wrap}.filters{display:grid;grid-template-columns:2fr repeat(4,1fr) auto;gap:12px}.card{border:1px solid #dce7f5;border-radius:14px;padding:22px;margin:16px 0;background:#fff}.card footer{margin-top:18px;justify-content:flex-end}.paper-row{display:flex;justify-content:space-between;align-items:center}.paper-settings{margin:20px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.print-paper{color:#182b45;background:white;padding:16px}.print-paper h1{text-align:center}.print-question{padding:16px 0;border-bottom:1px solid #eee;break-inside:avoid}.answer-space{height:100px}.print-controls{padding-bottom:20px}@media(max-width:1000px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.question-bank{padding:20px 12px}.hero h1{font-size:24px}.card{padding:16px}.steps{gap:12px;font-size:13px}}
.advanced-filters { display: contents; }

.is-mobile-bank {
  padding: 16px 16px 28px;
  background: transparent;
  color: var(--zh-text-primary);
}
.is-mobile-bank .hero { display: block; }
.mobile-bank-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.mobile-bank-actions :deep(.el-button) { margin: 0; }
.mobile-bank-actions :deep(.el-icon) { font-size: 19px; }
.is-mobile-bank :deep(.el-tabs__header) { margin: 8px 0 14px; }
.is-mobile-bank :deep(.el-tabs__nav-scroll) { display: flex; }
.is-mobile-bank :deep(.el-tabs__nav) { flex: 1; display: flex; }
.is-mobile-bank :deep(.el-tabs__item) {
  flex: 1;
  height: 48px;
  padding: 0 6px;
  font-size: 16px;
}
.is-mobile-bank .filters { grid-template-columns: minmax(0, 1fr) 48px; gap: 10px; }
.is-mobile-bank .advanced-filters {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--zh-line-parting);
  border-radius: 14px;
  background: var(--zh-background-primary);
}
.filter-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.filter-actions :deep(.el-button) { margin: 0; }
.mobile-bank-count { margin: 14px 0 8px; color: var(--zh-text-secondary); font-size: 14px; }
.is-mobile-bank .card {
  display: block;
  padding: 0;
  margin: 10px 0;
  border-color: var(--zh-line-parting);
  background: var(--zh-background-primary);
}
.question-card-link {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 15px;
  border: 0;
  border-radius: inherit;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.question-card-link:focus-visible { outline: 2px solid var(--zh-line-theme); outline-offset: -2px; }
.question-card-link .el-icon { font-size: 21px; color: var(--zh-text-secondary); }
.question-card-copy { display: grid; gap: 5px; min-width: 0; }
.question-card-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
  font-size: 18px;
  line-height: 1.45;
  font-weight: 600;
}
.question-card-meta { color: var(--zh-text-secondary); font-size: 14px; overflow-wrap: anywhere; }
.is-mobile-bank .question-card-footer {
  justify-content: space-between;
  min-height: 44px;
  margin: 0 15px;
  padding: 8px 0;
  border-top: 1px solid var(--zh-line-parting);
}
.is-mobile-bank :deep(.el-pagination) { justify-content: center; margin-top: 14px; }
.is-mobile-bank :deep(.el-pagination button) { min-width: 44px; height: 44px; }
.is-mobile-bank :deep(.el-pagination .mobile-bank-count) { margin: 0 4px; }
.is-mobile-bank :deep(.el-alert__title) { overflow-wrap: anywhere; }
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--zh-text-secondary);
  font-size: 14px;
}
.answer-toggle { width: 100%; margin: 14px 0; }
.question-detail-dialog.is-mobile-question-dialog .muted { color: var(--zh-text-secondary); }
.is-mobile-question-dialog .print-controls {
  display: grid;
  gap: 8px;
  padding-bottom: 14px;
}
.is-mobile-question-dialog .print-controls .muted { margin: 0; font-size: 14px; }
.is-mobile-question-dialog .print-paper { padding: 12px; border-radius: 12px; overflow-wrap: anywhere; }
.is-mobile-question-dialog .print-paper h1 { margin: 8px 0; font-size: 22px; }
.is-mobile-question-dialog .print-question h3 { font-size: 16px; }
</style>
<style>
.el-dialog.is-mobile-question-dialog { margin: max(12px, var(--zh-safe-top)) auto; }
.el-message.question-bank-toast { pointer-events: none; }
@media print{body:has(.paper-preview)>#app,body:has(.paper-preview)>.el-overlay:not(:has(.paper-preview)){display:none!important}.paper-preview{position:static!important;width:100%!important;margin:0!important;box-shadow:none!important}.paper-preview .el-dialog__header,.paper-preview .print-controls{display:none!important}.paper-preview .el-dialog__body{overflow:visible!important;padding:0!important;max-height:none!important}.paper-preview .print-paper{padding:0!important}body:has(.paper-preview),body:has(.paper-preview) .el-overlay,body:has(.paper-preview) .el-overlay-dialog{position:static!important;overflow:visible!important;height:auto!important;background:white!important}.paper-preview .question-content .answer{background:white!important}}
</style>
