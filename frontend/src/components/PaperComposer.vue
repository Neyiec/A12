<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { listQuestions } from '../apis/questionBank'
import { questionTypes, subjects, totalScore } from '../utils/questionBank'
import QuestionContent from './QuestionContent.vue'
import MobileSection from './MobileSection.vue'

const props = defineProps({
  modelValue: Boolean, questions: { type: Array, default: () => [] },
  paper: { type: Object, required: true }, busy: Boolean, dirty: Boolean, isMobile: Boolean,
})
const emit = defineEmits(['update:modelValue', 'update:questions', 'update:paper', 'change', 'add', 'save', 'preview'])
const selected = ref(null), panel = ref('settings'), canvas = ref(null), answers = ref(false)
const layout = ref(null)
const keyword = ref(''), subject = ref(''), page = ref(1), rows = ref([]), total = ref(0), loading = ref(false), error = ref('')
const score = computed(() => totalScore(props.questions))
const currentSubject = computed(() => props.questions[0]?.subject || subject.value)
let requestId = 0
watch(() => props.questions.map(q => q.id), ids => {
  if (!ids.includes(selected.value)) selected.value = props.isMobile ? null : ids[0] ?? null
}, { immediate: true })
watch(() => props.modelValue, open => {
  if (!open) {
    requestId++
    loading.value = false
    return
  }
  if (!props.questions.length) {
    openBank()
    return
  }
  panel.value = props.isMobile ? 'outline' : 'settings'
  selected.value = props.isMobile ? null : selected.value ?? props.questions[0].id
})
watch(() => props.isMobile, mobile => {
  if (!mobile && panel.value === 'outline') panel.value = 'settings'
})
watch(panel, () => {
  if (props.isMobile && layout.value) layout.value.scrollTop = 0
})
watch(() => props.questions[0]?.subject, () => {
  if (props.modelValue && panel.value === 'bank') search()
})
onBeforeUnmount(() => { requestId++ })

async function focusQuestion(id) {
  if (props.isMobile) {
    selected.value = selected.value === id ? null : id
    return
  }
  selected.value = id
  await nextTick()
  const target = [...(canvas.value?.querySelectorAll('[data-question-id]') || [])]
    .find(element => element.dataset.questionId === String(id))
  target?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}
function changeQuestions(items) { emit('update:questions', items); emit('change') }
function move(index, offset) {
  const next = index + offset
  if (next < 0 || next >= props.questions.length) return
  const items = [...props.questions]
  ;[items[index], items[next]] = [items[next], items[index]]
  changeQuestions(items)
}
function remove(id) { changeQuestions(props.questions.filter(q => q.id !== id)) }
function setScore(id, value) { changeQuestions(props.questions.map(q => q.id === id ? { ...q, score: value } : q)) }
function setPaper(field, value) { emit('update:paper', { ...props.paper, [field]: value }); emit('change') }
async function loadQuestions() {
  const token = ++requestId
  loading.value = true; error.value = ''
  try {
    const result = await listQuestions({ scope: 'public', subject: currentSubject.value,
      keyword: keyword.value, page: page.value, size: 6 })
    if (token !== requestId) return
    rows.value = result.items; total.value = result.total
  } catch (e) { if (token === requestId) error.value = e.message }
  finally { if (token === requestId) loading.value = false }
}
function search() { page.value = 1; loadQuestions() }
function openBank() { panel.value = 'bank'; search() }
</script>

<template>
  <el-dialog :model-value="modelValue" fullscreen class="paper-composer" :class="{ 'is-mobile-composer': isMobile }" :show-close="false"
    :close-on-click-modal="false" :close-on-press-escape="false" @update:model-value="emit('update:modelValue', $event)">
    <template #header="{ titleId }">
      <header class="composer-header">
        <div class="composer-heading">
          <el-button v-if="isMobile" text circle :icon="ArrowLeft" aria-label="返回题库" :disabled="busy" @click="emit('update:modelValue', false)" />
          <el-button v-else :disabled="busy" @click="emit('update:modelValue', false)">返回题库</el-button>
          <div><h2 :id="titleId">组卷工作台</h2><small v-if="!isMobile">{{ paper.title || '未命名试卷' }} · {{ dirty ? '有未保存修改' : paper.id ? '已保存' : '尚未保存' }}</small></div>
        </div>
        <div v-if="!isMobile" class="composer-actions"><span>{{ questions.length }} 题 · {{ score }} 分</span>
          <el-button :disabled="!questions.length || busy" @click="emit('preview')">预览 / 打印</el-button>
          <el-button type="primary" :disabled="!questions.length" :loading="busy" @click="emit('save')">{{ paper.id ? '保存修改' : '保存试卷' }}</el-button>
        </div>
      </header>
    </template>
    <div v-if="isMobile" class="composer-mobile-nav" role="group" aria-label="组卷视图">
      <el-button :type="panel === 'bank' ? 'primary' : undefined" :aria-pressed="panel === 'bank'" @click="openBank">选题</el-button>
      <el-button :type="panel === 'outline' ? 'primary' : undefined" :aria-pressed="panel === 'outline'" @click="panel = 'outline'">排序</el-button>
      <el-button :type="panel === 'settings' ? 'primary' : undefined" :aria-pressed="panel === 'settings'" @click="panel = 'settings'">设置</el-button>
    </div>
    <div ref="layout" class="composer-layout">
      <aside v-show="!isMobile || panel === 'outline'" class="composer-outline" aria-label="试卷题目目录">
        <div v-if="!isMobile" class="panel-heading"><strong>题目目录</strong><span>{{ questions.length }} / 100</span></div>
        <p v-if="!isMobile" class="composer-muted">点击定位题目，上下移动调整出题顺序。</p>
        <el-empty v-if="!questions.length" description="还没有选题" :image-size="55"/>
        <div v-for="(q, index) in questions" :key="q.id" class="outline-item" :class="{ selected: selected === q.id }">
          <button class="outline-select" :aria-current="!isMobile && selected === q.id ? 'true' : undefined"
            :aria-expanded="isMobile ? selected === q.id : undefined" @click="focusQuestion(q.id)">
            <span class="question-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span><strong>{{ questionTypes[q.question_type] }}</strong><small>{{ q.stem }}</small></span><b>{{ q.score }}分</b>
          </button>
          <div v-if="isMobile && selected === q.id" class="outline-detail"><QuestionContent :question="q" /></div>
          <div class="outline-controls"><el-button text size="small" :disabled="busy || index === 0" @click="move(index, -1)">上移</el-button><el-button text size="small" :disabled="busy || index === questions.length - 1" @click="move(index, 1)">下移</el-button><el-button text size="small" type="danger" :disabled="busy" :aria-label="`移除第${index + 1}题`" @click="remove(q.id)">移除</el-button></div>
        </div>
        <el-button class="add-question" type="primary" plain @click="openBank">＋ 从题库添加</el-button>
      </aside>

      <section v-if="!isMobile" ref="canvas" class="composer-canvas" aria-label="试卷编辑预览">
        <div class="canvas-toolbar"><span>试卷预览 · 按目录顺序排版</span><el-switch v-model="answers" active-text="显示答案"/></div>
        <div class="paper-sheet">
          <h1>{{ paper.title || '请在右侧填写试卷名称' }}</h1>
          <p class="paper-meta">{{ questions[0]?.subject || '学科待选择' }} · {{ paper.duration_minutes }} 分钟 · 满分 {{ score }} 分</p>
          <p class="student-fields">班级：________　姓名：________　日期：________</p>
          <el-empty v-if="!questions.length" description="从右侧题库添加第一道题，开始组卷"><el-button type="primary" @click="openBank">开始选题</el-button></el-empty>
          <article v-for="(q, index) in questions" :key="q.id" :data-question-id="q.id" class="sheet-question" :class="{ selected: selected === q.id }" @click="selected = q.id">
            <h3>{{ index + 1 }}. {{ questionTypes[q.question_type] }}（{{ q.score }} 分）</h3>
            <QuestionContent :question="q" :answers="answers"/>
            <div v-if="!answers && ['short', 'calculation'].includes(q.question_type)" class="sheet-answer-space"></div>
          </article>
        </div>
      </section>

      <aside v-show="!isMobile || panel !== 'outline'" class="composer-properties" aria-label="组卷设置与题库">
        <div v-if="!isMobile" class="panel-tabs"><el-button :type="panel === 'settings' ? 'primary' : 'default'" @click="panel = 'settings'">试卷设置</el-button><el-button :type="panel === 'bank' ? 'primary' : 'default'" @click="openBank">题库选题</el-button></div>
        <template v-if="panel === 'settings'">
          <el-form label-position="top" :disabled="busy">
            <el-form-item label="试卷名称（必填）"><el-input :model-value="paper.title" maxlength="120" show-word-limit placeholder="例如：初二数学单元练习" @update:model-value="setPaper('title', $event)"/></el-form-item>
            <el-form-item label="考试时间（分钟）"><el-input-number :model-value="paper.duration_minutes" :min="5" :max="300" @update:model-value="setPaper('duration_minutes', $event)"/></el-form-item>
          </el-form>
          <div v-if="!isMobile" class="paper-summary"><span>题目 <strong>{{ questions.length }}</strong></span><span>总分 <strong>{{ score }}</strong></span></div>
          <h3 v-if="!isMobile || questions.length">逐题分值</h3><p v-if="!isMobile" class="composer-muted">每题 0.01–100 分，顺序和分值可随时调整。</p>
          <label v-for="(q, index) in questions" :key="q.id" class="question-score"><span>{{ index + 1 }}. {{ questionTypes[q.question_type] }}</span><el-input-number :model-value="q.score" :aria-label="`第${index + 1}题分值`" :min="0.01" :max="100" :precision="2" :disabled="busy" @update:model-value="setScore(q.id, $event)"/></label>
          <p class="save-note">保存后固定题目版本。题库后续修改或下架，不影响已保存试卷。</p>
        </template>
        <template v-else-if="panel === 'bank'">
          <form class="picker-filters" @submit.prevent="search">
            <el-input v-model="keyword" clearable maxlength="120" placeholder="搜索题干 / 知识点" aria-label="搜索题库"/>
            <el-select v-model="subject" :disabled="!!questions.length" :placeholder="questions[0]?.subject || '选择学科'" clearable filterable aria-label="学科" @change="search"><el-option v-for="s in subjects" :key="s" :value="s"/></el-select>
            <el-button type="primary" native-type="submit" :loading="loading">查找题目</el-button>
          </form>
          <p class="composer-muted">{{ isMobile ? (questions.length ? `${currentSubject} · ` : '') : questions.length ? `当前试卷为${currentSubject}，仅展示同学科题目。 ` : '先选学科，添加题目后自动限定同一学科。 ' }}共 {{ total }} 题</p>
          <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button @click="loadQuestions">重试</el-button></el-alert>
          <div v-loading="loading" class="picker-results"><el-empty v-if="!loading && !error && !rows.length" description="暂无匹配的公开题目" :image-size="55"/>
            <article v-for="row in rows" :key="row.id" class="picker-question">
              <el-tag size="small">{{ row.subject }} · {{ questionTypes[row.question_type] }}</el-tag>
              <MobileSection v-if="isMobile" :title="row.content.stem || '查看题目'" lazy>
                <QuestionContent :question="row.content" />
              </MobileSection>
              <QuestionContent v-else :question="row.content" />
              <el-button type="primary" plain :disabled="busy || questions.some(q => q.id === row.id)" @click="emit('add', row)">{{ questions.some(q => q.id === row.id) ? '已加入试卷' : '加入试卷' }}</el-button>
            </article>
          </div>
          <el-pagination v-if="total" v-model:current-page="page" :small="!isMobile" :page-size="6" :total="total"
            :layout="isMobile ? 'prev, slot, next' : 'prev, pager, next'" :hide-on-single-page="isMobile" @current-change="loadQuestions">
            <span>第 {{ page }} / {{ Math.ceil(total / 6) }} 页</span>
          </el-pagination>
        </template>
      </aside>
    </div>
    <template v-if="isMobile" #footer>
      <p class="mobile-composer-summary">{{ questions.length }} 题 · {{ score }} 分 <span>{{ dirty ? '未保存' : paper.id ? '已保存' : '' }}</span></p>
      <el-button :disabled="!questions.length || busy" @click="emit('preview')">预览试卷</el-button>
      <el-button type="primary" :disabled="!questions.length" :loading="busy" @click="emit('save')">{{ paper.id ? '保存修改' : '保存试卷' }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.composer-header,.composer-heading,.composer-actions{display:flex;align-items:center;gap:16px}.composer-header{justify-content:space-between;flex-wrap:wrap}.composer-heading h2{margin:0 0 4px;font-size:18px;color:#17365b}.composer-heading small,.composer-muted{color:#647a95;line-height:1.7}.composer-actions{gap:10px;color:#305b91}.composer-layout{height:100%;min-height:0;display:grid;grid-template-columns:230px minmax(0,1fr) 330px;background:#f0f5fc;color:#17365b}.composer-outline,.composer-properties{padding:18px;overflow:auto;background:white;min-width:0}.composer-outline{border-right:1px solid #dce7f5}.composer-properties{border-left:1px solid #dce7f5}.panel-heading{display:flex;justify-content:space-between}.panel-heading span{color:#647a95;font-size:13px}.composer-muted{font-size:12px;margin:12px 0}.outline-item{border:1px solid #dce7f5;border-radius:10px;margin:12px 0;background:#fff}.outline-item.selected{border-color:#2563eb;background:#eff6ff}.outline-select{width:100%;display:flex;align-items:center;gap:8px;padding:12px 8px;text-align:left;border:0;background:none;cursor:pointer;color:#244a78}.outline-select>span:nth-child(2){min-width:0;flex:1}.outline-select small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:6px;color:#647a95}.outline-select strong{font-size:12px}.outline-select b{font-size:12px;white-space:nowrap}.question-number{font-size:17px;color:#2563eb}.outline-controls{display:flex;justify-content:flex-end;border-top:1px solid #e1eafb}.outline-controls :deep(.el-button){margin:0;padding:6px}.add-question{width:100%;margin:10px 0}.composer-canvas{overflow:auto;padding:18px 28px 48px;min-width:0;scroll-behavior:smooth}.canvas-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:12px;color:#647a95;margin-bottom:18px}.paper-sheet{max-width:794px;min-height:940px;margin:auto;padding:42px;background:#fff;box-shadow:0 8px 30px #244a7810;border:1px solid #e1e9f5}.paper-sheet h1{text-align:center;font-size:24px;overflow-wrap:anywhere}.paper-meta{text-align:center;font-size:13px;color:#647a95}.student-fields{font-size:13px;line-height:2;border-bottom:1px solid #dce7f5;padding:16px 0}.sheet-question{padding:16px 12px;margin:12px -12px;border:1px solid transparent;border-radius:6px;cursor:pointer}.sheet-question.selected{border-color:#93b4fb;background:#fbfdff}.sheet-question h3{font-size:15px;margin:0 0 12px}.sheet-answer-space{height:100px}.panel-tabs{display:flex;gap:8px;margin-bottom:20px}.panel-tabs :deep(.el-button){flex:1;margin:0}.paper-summary{display:flex;justify-content:space-around;padding:18px;background:#eff6ff;border-radius:10px}.paper-summary strong{color:#2563eb;margin-left:10px;font-size:20px}.composer-properties h3{font-size:15px;margin-top:24px}.question-score{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:16px 0;font-size:12px}.question-score :deep(.el-input-number){width:135px;flex-shrink:0}.save-note{font-size:12px;color:#42648c;background:#eff6ff;padding:14px;line-height:1.8;border-radius:8px;margin-top:24px}.picker-filters{display:grid;gap:10px}.picker-question{border:1px solid #dce7f5;border-radius:10px;padding:12px;margin:14px 0;font-size:13px}.picker-question :deep(.question-content){max-height:220px;overflow:auto;margin:10px 0}.picker-question :deep(.el-button){width:100%}.picker-results{min-height:90px}
@media(max-width:1100px){.composer-layout{grid-template-columns:175px minmax(0,1fr) 285px}.composer-canvas{padding:14px}.paper-sheet{padding:24px}.composer-outline,.composer-properties{padding:12px}}
@media(max-width:780px){.composer-layout{display:flex;flex-direction:column;overflow:auto}.composer-outline{overflow:visible;border-right:0;border-bottom:1px solid #dce7f5}.outline-item{display:inline-block;width:170px;margin:5px;vertical-align:top}.composer-outline>.composer-muted{display:none}.composer-canvas{overflow:visible;padding:12px;order:2}.composer-properties{overflow:visible;order:1;border-left:0;border-bottom:1px solid #dce7f5}.paper-sheet{min-height:500px;padding:20px}.composer-header{gap:10px}.composer-actions{flex-wrap:wrap}.composer-actions>span{display:none}.composer-heading{gap:8px}}

.is-mobile-composer .composer-heading { gap: 4px; }
.is-mobile-composer .composer-heading h2 { margin: 0; font-size: 20px; color: var(--zh-text-primary); }
.is-mobile-composer .composer-heading :deep(.el-button) { width: 48px; padding: 0; font-size: 22px; }
.composer-mobile-nav {
  flex: none;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 12px 16px;
  background: var(--zh-background-primary);
}
.composer-mobile-nav :deep(.el-button) { margin: 0; }
.is-mobile-composer .composer-layout {
  display: block;
  flex: 1;
  height: auto;
  overflow: auto;
  overscroll-behavior: contain;
  color: var(--zh-text-primary);
  background: var(--zh-background-light);
}
.is-mobile-composer :is(.composer-outline, .composer-properties) {
  padding: 16px;
  border: 0;
  background: transparent;
  overflow: visible;
}
.is-mobile-composer :is(.outline-item, .picker-question) {
  display: block;
  width: auto;
  margin: 0 0 12px;
  border-radius: 14px;
  border-color: var(--zh-line-parting);
  background: var(--zh-background-primary);
}
.is-mobile-composer .outline-item.selected { border-color: var(--zh-line-theme); }
.is-mobile-composer .outline-select { min-height: 64px; padding: 12px; color: var(--zh-text-primary); }
.is-mobile-composer .outline-select strong,
.is-mobile-composer .outline-select b { font-size: 16px; }
.is-mobile-composer .outline-select small,
.is-mobile-composer .composer-muted,
.is-mobile-composer .save-note { color: var(--zh-text-secondary); }
.outline-detail { padding: 0 12px 12px; }
.is-mobile-composer .outline-controls { border-color: var(--zh-line-parting); }
.is-mobile-composer .outline-controls :deep(.el-button) { flex: 1; }
.is-mobile-composer .question-score {
  padding: 8px 0;
  margin: 0;
  border-bottom: 1px solid var(--zh-line-parting);
  font-size: 16px;
}
.is-mobile-composer .save-note { background: var(--zh-background-primary); }
.is-mobile-composer .picker-question :deep(summary) { padding: 10px 0; }
.is-mobile-composer .picker-question :deep(summary > span) {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-width: 0;
  overflow: hidden;
  overflow-wrap: anywhere;
  font-size: 17px;
}
.is-mobile-composer .picker-question :deep(.mobile-section-content) { padding: 0 0 10px; }
.is-mobile-composer .picker-question :deep(.question-content) { max-height: none; }
.is-mobile-composer :deep(.el-pagination) { justify-content: center; }
.is-mobile-composer :deep(.el-pagination button) { min-width: 44px; height: 44px; }
.mobile-composer-summary {
  display: flex;
  justify-content: space-between;
  flex-basis: 100%;
  margin: 0;
  color: var(--zh-text-secondary);
}
</style>
<style>
.paper-composer.el-dialog{padding:0;display:flex;flex-direction:column;background:white;--el-color-primary:#2563eb;--el-text-color-primary:#17365b;--el-border-color:#d4e2f5}.paper-composer .el-dialog__header{padding:16px 22px;margin:0;border-bottom:1px solid #dce7f5;flex-shrink:0}.paper-composer .el-dialog__body{padding:0;flex:1;min-height:0;overflow:hidden}.paper-composer .el-button:focus-visible,.paper-composer button:focus-visible{outline:2px solid #2563eb;outline-offset:2px}
.paper-composer .el-button--primary:not(.is-plain):not(.is-disabled){background:#2563eb;border-color:#2563eb;color:#fff}.paper-composer .el-button--primary:not(.is-plain):not(.is-disabled):hover{background:#1d4ed8;border-color:#1d4ed8}.paper-composer .el-button--primary.is-disabled{background:#eaf2ff;border-color:#d4e2f5;color:#607a9b}
:root .paper-composer.is-mobile-composer {
  height: 100dvh;
  max-height: none;
  max-width: none;
  padding: 0;
  overflow: hidden;
  background: var(--zh-background-primary);
  --el-color-primary: var(--zh-theme-primary);
  --el-text-color-primary: var(--zh-text-primary);
  --el-border-color: var(--zh-line-border);
}
:root .paper-composer.is-mobile-composer .el-dialog__header {
  padding: var(--zh-safe-top) 12px 0;
  border-color: var(--zh-line-parting);
}
:root .paper-composer.is-mobile-composer .el-dialog__body {
  display: flex;
  flex-direction: column;
  padding: 0;
}
:root .paper-composer.is-mobile-composer .el-dialog__footer {
  flex: none;
  padding: 8px 16px max(12px, var(--zh-safe-bottom));
  border-top: 1px solid var(--zh-line-parting);
}
</style>
