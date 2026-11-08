<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listQuestions, getQuestion, saveQuestion, listPapers, getPaper, savePaper } from '../apis/questionBank'
import { subjects, grades, questionTypes, difficulties, questionStatuses, emptyQuestion, addToBasket, totalScore, paperItems } from '../utils/questionBank'
import QuestionContent from './QuestionContent.vue'
import QuestionEditor from './QuestionEditor.vue'
import PaperComposer from './PaperComposer.vue'
const tab=ref('public'), rows=ref([]), total=ref(0), loading=ref(false), error=ref(''), busy=ref(false)
const filter=reactive({keyword:'',subject:'',grade:'',question_type:'',difficulty:'',page:1,size:12})
const basket=ref([]), compose=ref(false), editor=ref(false), question=ref(emptyQuestion()), detail=ref(null), showAnswer=ref(false), papers=ref([])
const paper=ref({title:'',duration_minutes:45}), preview=ref(false), answerSheet=ref(false), dirty=ref(false)
const score=computed(()=>totalScore(basket.value))
let requestId=0
async function load(){const token=++requestId;loading.value=true;error.value='';try{const result=await listQuestions({...filter,scope:tab.value==='mine'?'mine':'public'});if(token===requestId){rows.value=result.items;total.value=result.total}}catch(e){if(token===requestId)error.value=e.message}finally{if(token===requestId)loading.value=false}}
async function switchTab(){filter.page=1;if(tab.value==='papers'){try{papers.value=await listPapers()}catch(e){ElMessage.error(e.message)}}else await load()}
function search(){filter.page=1;load()}
async function openDetail(row){try{detail.value=await getQuestion(row.id);showAnswer.value=false}catch(e){ElMessage.error(e.message)}}
function add(row){try{if(!row.content.stem?.trim()||!row.content.answer?.trim()||!row.content.analysis?.trim()||row.content.options?.some(s=>!s.trim()))throw new Error('草稿尚未完成，请先补齐题干、选项、答案和解析');basket.value=addToBasket(basket.value,{...row.content,id:row.id});dirty.value=true;ElMessage.success(compose.value?'已加入试卷':'已加入题篮，点击右上角“组卷”设置试卷')}catch(e){ElMessage.warning(e.message)}}
function edit(row){question.value=row?{...JSON.parse(JSON.stringify(row.content)),id:row.id,revision:row.revision}:emptyQuestion();editor.value=true}
function copy(row){question.value=JSON.parse(JSON.stringify(row.content));editor.value=true}
async function persistQuestion(action){busy.value=true;try{await saveQuestion(question.value,action);editor.value=false;ElMessage.success(action==='submit'?'已提交审核；通过后进入公共题库':'草稿已保存');await load()}catch(e){ElMessage.error(e.message)}finally{busy.value=false}}
async function persistPaper(){if(busy.value)return;if(!basket.value.length)return ElMessage.warning('请先从题库选择题目');if(!paper.value.title?.trim())return ElMessage.warning('请先在试卷设置中填写试卷名称');busy.value=true;try{const saved=await savePaper({...paper.value,subject:basket.value[0].subject,items:basket.value.map(q=>({question_id:q.id,score:q.score}))});paper.value={id:saved.id,revision:saved.revision,title:saved.title,duration_minutes:saved.duration_minutes};basket.value=paperItems(saved);await nextTick();dirty.value=false;ElMessage.success('试卷已保存，题目内容已固定');if(tab.value==='papers')await switchTab()}catch(e){ElMessage.error(e.message)}finally{busy.value=false}}
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
  <main class="question-bank">
    <header class="hero"><div><span class="eyebrow">QUESTION BANK / 教学评价</span><h1>题库与组卷</h1><p>先按学科找题，加入题篮，再到组卷工作台设置顺序与分值。也可以投稿你的题目，经审核后共享给教师。</p></div><div class="actions"><el-button @click="edit()">＋ 设计题目</el-button><el-badge :value="basket.length" :hidden="!basket.length" type="primary"><el-button type="primary" @click="compose=true">组卷</el-button></el-badge></div></header>
    <div class="steps"><span>① 公共题库找题</span><span>② 加入题篮</span><span>③ 设置分值并保存 / 打印</span></div>
    <el-tabs v-model="tab"><el-tab-pane label="公共题库" name="public"/><el-tab-pane label="我的投稿" name="mine"/><el-tab-pane label="我的试卷" name="papers"/></el-tabs>
    <template v-if="tab!=='papers'">
      <form class="filters" @submit.prevent="search">
        <el-input v-model="filter.keyword" clearable maxlength="120" placeholder="搜索题干或知识点，如：勾股定理" />
        <el-select v-model="filter.subject" placeholder="全部学科" clearable filterable><el-option v-for="s in subjects" :key="s" :value="s"/></el-select>
        <el-select v-model="filter.grade" placeholder="全部年级" clearable><el-option v-for="s in grades" :key="s" :value="s"/></el-select>
        <el-select v-model="filter.question_type" placeholder="全部题型" clearable><el-option v-for="(label,key) in questionTypes" :key="key" :label="label" :value="key"/></el-select>
        <el-select v-model="filter.difficulty" placeholder="全部难度" clearable><el-option v-for="(label,key) in difficulties" :key="key" :label="label" :value="key"/></el-select>
        <el-button type="primary" native-type="submit">查找题目</el-button>
      </form>
      <p class="muted">{{ total }} 道题目 · {{ tab==='public'?'仅展示审核通过的题目，答案可在详情中查看':'草稿可继续编辑；被退回的题目可修改后再次提交' }}</p>
      <el-alert v-if="error" type="error" :title="error" show-icon :closable="false"><el-button @click="load">重试</el-button></el-alert>
      <section v-loading="loading" class="question-list">
        <el-empty v-if="!rows.length&&!loading&&!error" :description="tab==='mine'?'还没有投稿，点击右上角“设计题目”开始':'暂无符合条件的公开题目；可调整筛选或投稿题目'"/>
        <article v-for="row in rows" :key="row.id" class="card">
          <div class="tags"><el-tag>{{ row.subject }} · {{ row.grade }}</el-tag><el-tag type="info">{{ questionTypes[row.question_type] }}</el-tag><el-tag type="info">{{ difficulties[row.difficulty] }}</el-tag><el-tag v-if="tab==='mine'" :type="row.status==='approved'?'success':row.status==='rejected'?'danger':'warning'">{{ questionStatuses[row.status] }}</el-tag></div>
          <QuestionContent :question="row.content" />
          <p v-if="row.knowledge_points" class="muted">知识点：{{ row.knowledge_points }}</p>
          <el-alert v-if="row.review_note&&tab==='mine'" :title="`审核意见：${row.review_note}`" :closable="false" type="warning"/>
          <footer><el-button @click="openDetail(row)">查看答案与解析</el-button><el-button v-if="tab==='mine'&&['draft','rejected'].includes(row.status)" @click="edit(row)">编辑 / 提交审核</el-button><el-button @click="copy(row)">复制改编</el-button><el-button v-if="row.status==='approved'||(tab==='mine'&&row.status==='draft')" type="primary" :disabled="basket.some(q=>q.id===row.id)" @click="add(row)">{{ basket.some(q=>q.id===row.id)?'已加入':row.status==='draft'?'加入题篮（自用）':'加入题篮' }}</el-button></footer>
        </article>
      </section>
      <el-pagination v-if="total" v-model:current-page="filter.page" :page-size="filter.size" :total="total" layout="prev, pager, next, total" @current-change="load" />
    </template>
    <template v-else><el-button @click="newPaper">新建试卷</el-button><el-empty v-if="!papers.length" description="尚未保存试卷，点击右上角“组卷”开始"/><article v-for="p in papers" :key="p.id" class="card paper-row"><div><h3>{{ p.title }}</h3><p class="muted">{{ p.subject }} · {{ p.total_score }} 分 · {{ p.duration_minutes }} 分钟 · v{{ p.revision }}</p></div><el-button type="primary" @click="loadPaper(p)">打开 / 打印</el-button></article></template>
    <el-dialog v-model="editor" class="question-edit-dialog" title="设计题目 · 草稿保存后可继续完善" width="min(860px,95vw)" :close-on-click-modal="false"><QuestionEditor v-model="question"/><template #footer><el-button @click="editor=false">取消</el-button><el-button :loading="busy" @click="persistQuestion('draft')">保存草稿</el-button><el-button type="primary" :loading="busy" @click="persistQuestion('submit')">提交后台审核</el-button></template></el-dialog>
    <el-dialog :model-value="!!detail" title="题目详情" width="min(800px,95vw)" @close="detail=null"><template v-if="detail"><QuestionContent :question="detail.content" :answers="showAnswer"/><el-button @click="showAnswer=!showAnswer">{{ showAnswer?'隐藏答案':'显示答案与解析' }}</el-button><el-divider v-if="detail.reviews?.length"/><p v-for="(r,i) in detail.reviews||[]" :key="i" class="muted">{{ r.created_at }} · {{ r.decision }} · {{ r.note }}</p></template></el-dialog>
    <PaperComposer v-model="compose" v-model:questions="basket" v-model:paper="paper" :busy="busy" :dirty="dirty" @change="dirty=true" @add="add" @save="persistPaper" @preview="preview=true"/>
    <el-dialog v-model="preview" title="试卷预览" width="min(900px,96vw)" class="paper-preview">
      <div class="print-controls"><el-switch v-model="answerSheet" active-text="答案解析版" inactive-text="学生作答版"/><el-button type="primary" @click="print">打印 / 另存 PDF</el-button><p class="muted">打印窗口可选择“另存为 PDF”。{{ dirty?'当前预览含未保存修改，请先保存需要保留的试卷。':'' }}</p></div>
      <section class="print-paper"><h1>{{ paper.title||'课堂练习' }}</h1><p>{{ basket[0]?.subject }} · {{ paper.duration_minutes }} 分钟 · 满分 {{ score }} 分</p><p v-if="!answerSheet">班级：________ 姓名：________ 日期：________</p><article v-for="(q,i) in basket" :key="q.id" class="print-question"><h3>{{ i+1 }}. {{ questionTypes[q.question_type] }}（{{ q.score }} 分）</h3><QuestionContent :question="q" :answers="answerSheet"/><div v-if="!answerSheet&&['short','calculation'].includes(q.question_type)" class="answer-space"></div></article></section>
    </el-dialog>
  </main>
</template>
<style scoped>
.question-bank{max-width:1240px;margin:auto;padding:36px 24px 100px;background:#fff;color:#183451}.hero{display:flex;align-items:center;justify-content:space-between;gap:24px}.hero h1{font-size:30px;margin:12px 0;line-height:1.4}.hero p,.muted{color:#6b7e96;line-height:1.7}.eyebrow{color:#2563eb;font-weight:600}.actions,footer,.tags{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.actions{flex-shrink:0}.steps{display:flex;gap:32px;background:#eff6ff;border-radius:12px;padding:18px;margin:24px 0;color:#305e97;flex-wrap:wrap}.filters{display:grid;grid-template-columns:2fr repeat(4,1fr) auto;gap:12px}.card{border:1px solid #dce7f5;border-radius:14px;padding:22px;margin:16px 0;background:#fff}.card footer{margin-top:18px;justify-content:flex-end}.paper-row{display:flex;justify-content:space-between;align-items:center}.paper-settings{margin:20px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.print-paper{color:#182b45;background:white;padding:16px}.print-paper h1{text-align:center}.print-question{padding:16px 0;border-bottom:1px solid #eee;break-inside:avoid}.answer-space{height:100px}.print-controls{padding-bottom:20px}@media(max-width:1000px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.question-bank{padding:20px 12px}.hero h1{font-size:24px}.card{padding:16px}.steps{gap:12px;font-size:13px}}
</style>
<style>
@media print{body:has(.paper-preview)>#app,body:has(.paper-preview)>.el-overlay:not(:has(.paper-preview)){display:none!important}.paper-preview{position:static!important;width:100%!important;margin:0!important;box-shadow:none!important}.paper-preview .el-dialog__header,.paper-preview .print-controls{display:none!important}.paper-preview .el-dialog__body{overflow:visible!important;padding:0!important;max-height:none!important}.paper-preview .print-paper{padding:0!important}body:has(.paper-preview),body:has(.paper-preview) .el-overlay,body:has(.paper-preview) .el-overlay-dialog{position:static!important;overflow:visible!important;height:auto!important;background:white!important}.paper-preview .question-content .answer{background:white!important}}
</style>
