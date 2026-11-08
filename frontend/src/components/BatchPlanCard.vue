<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { editBatchPlan, reviseBatchPlan, splitBatchPlan, confirmBatchPlan, downloadBatchSource, saveBatchDownload } from '../apis/batchPresentations'
import { listPptTemplates, uploadWordConversionSource } from '../apis/teacher'
const props = defineProps({ plan: { type: Object, required: true }, publicResourceEnabled: { type: Boolean, default: undefined } })
const emit = defineEmits(['updated', 'confirmed'])
const draft = ref({}), selected = ref([]), theme = ref('素白风'), templates = ref([])
const busy = ref(false), error = ref(''), instruction = ref(''), sourceText = ref(''), acceptSuggested = ref(false)
const fileInput = ref(null)
watch(() => props.plan, value => {
  const ids = new Set(selected.value)
  draft.value = JSON.parse(JSON.stringify(value))
  const retained = value.items.filter(item => ids.has(item.id)).map(item => item.id)
  selected.value = retained.length ? retained : value.items.map(item => item.id)
}, { immediate: true })
const chosen = computed(() => (draft.value.items || []).filter(item => selected.value.includes(item.id)))
const bounds = computed(() => ({ min: chosen.value.reduce((n,item) => n + Number(item.min_pages || 0), 0), max: chosen.value.reduce((n,item) => n + Number(item.max_pages || 0), 0) }))
async function perform(work) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await work() }
  catch (cause) { error.value = cause.message || '操作失败，请重试' }
  finally { busy.value = false }
}
const update = response => { emit('updated', response.data); return response.data }
async function saveChoices() {
  if (!chosen.value.length || chosen.value.length > 24 || bounds.value.max > 240) throw Error('请选择 1–24 份课件，单批不超过 240 页')
  const response = await editBatchPlan(props.plan.id, { revision: props.plan.revision, title: draft.value.title,
    subject: draft.value.subject, grade: draft.value.grade, textbook_version: draft.value.textbook_version || '',
    reasoning_effort: draft.value.reasoning_effort || 'low',
    items: draft.value.items.map(({ id, title, hours, objectives, min_pages, max_pages }) => ({ id, title, hours, objectives, min_pages, max_pages })) })
  return update(response)
}
async function confirm() {
  await perform(async () => {
    if (draft.value.basis === 'suggested' && !acceptSuggested.value) throw Error('请先确认这是 AI 建议目录')
    const itemIds = chosen.value.map(item => item.id)
    const saved = await saveChoices()
    const response = await confirmBatchPlan(saved.id, { revision: saved.revision,
      item_ids: itemIds, theme: theme.value, accept_suggested: acceptSuggested.value, enable_rag: props.publicResourceEnabled })
    emit('updated', { ...saved, status: 'confirmed' }); emit('confirmed', response.data.id)
  })
}
async function revise(allow = false, resourceIds = []) {
  await perform(async () => update(await reviseBatchPlan(props.plan.id, { revision: props.plan.revision,
    message: instruction.value || draft.value.requirements || '根据补充的教学计划重新安排章节',
    source_text: sourceText.value, allow_suggested: allow, resource_ids: resourceIds })))
}
async function uploadSource(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  if (!/\.docx$/i.test(file.name) || file.size > 50*1024*1024) { error.value = '请选择不超过 50MB 的 .docx 文件'; return }
  await perform(async () => {
    const form = new FormData(); form.append('file', file)
    const uploaded = (await uploadWordConversionSource(form)).data
    if (!uploaded?.resource_id) throw Error('Word 上传失败')
    update(await reviseBatchPlan(props.plan.id, { revision: props.plan.revision,
      message: instruction.value || '按这份教学计划逐章安排课件', resource_ids: [uploaded.resource_id] }))
  })
}
onMounted(async () => { try { templates.value = (await listPptTemplates()).data || [] } catch { /* 内置默认主题仍可用。 */ } })
</script>

<template>
  <section class="batch-plan" :aria-busy="busy">
    <div class="batch-heading"><div><span>批量备课计划</span><h3>{{ draft.title }}</h3></div><router-link to="/main/batch-tasks">所有批量任务</router-link></div>
    <el-alert v-for="warning in draft.warnings || []" :key="warning" :title="warning" type="warning" :closable="false" />
    <template v-if="draft.status === 'confirmed'"><p>计划已确认，生成会在后台继续。可到批量任务查看进度，或打开已完成章节继续编辑。</p><router-link to="/main/batch-tasks">查看生成进度</router-link></template>
    <template v-else>
      <p v-if="draft.needs_input">{{ draft.questions?.join(' ') }}</p>
      <div class="batch-actions"><el-button :disabled="busy" @click="fileInput.click()">补充 Word 教学计划</el-button><el-button v-if="draft.source_name" :disabled="busy" @click="perform(async () => saveBatchDownload(await downloadBatchSource(plan.id), draft.source_name))">查看原始 Word</el-button></div>
      <input ref="fileInput" type="file" accept=".docx" hidden @change="uploadSource" />
      <template v-if="!draft.needs_input">
        <div class="batch-fields"><label>课程名称<el-input v-model="draft.title" :disabled="busy" /></label><label>学科 *<el-input v-model="draft.subject" placeholder="如数学" :disabled="busy" /></label><label>适用年级 *<el-input v-model="draft.grade" placeholder="如九年级" :disabled="busy" /></label><label>教材版本 / 上下册<el-input v-model="draft.textbook_version" :disabled="busy" /></label></div>
        <div class="batch-actions"><span>推理强度</span><el-select v-model="draft.reasoning_effort" :disabled="busy" placeholder="轻度推理（默认）"><el-option value="low" label="轻度 · 批量优先" /><el-option value="medium" label="标准" /><el-option value="high" label="深度" /></el-select><small>始终使用项目默认模型，较高强度通常耗时更长。</small></div>
        <details v-if="draft.chapter_tree?.length"><summary>原文目录</summary><el-tree :data="draft.chapter_tree" :props="{label:'title',children:'children'}" default-expand-all /></details>
        <div class="batch-actions"><el-button size="small" :disabled="busy" @click="selected = draft.items.map(item => item.id)">全选</el-button><el-button size="small" :disabled="busy" @click="selected = draft.items.slice(0,3).map(item => item.id)">只选前三份</el-button><span>将生成 {{ chosen.length }} 份，合计 {{ bounds.min }}–{{ bounds.max }} 页</span></div>
        <div v-for="(item, index) in draft.items" :key="item.id" class="batch-chapter">
          <el-checkbox :model-value="selected.includes(item.id)" :disabled="busy" @change="checked => selected = checked ? [...selected, item.id] : selected.filter(id => id !== item.id)">{{ String(index + 1).padStart(2,'0') }}</el-checkbox>
          <div class="chapter-body"><el-input v-model="item.title" :disabled="busy" aria-label="章节标题" /><el-input v-model="item.hours" :disabled="busy" placeholder="学时 / 课时（可选，如2课时）" aria-label="学时或课时" /><el-input v-model="item.objectives" :disabled="busy" placeholder="教学要求与重点" type="textarea" :rows="2" /><div class="chapter-range"><span>预估页数</span><input v-model.number="item.min_pages" type="number" min="1" max="30" :disabled="busy" aria-label="最少页数" />至<input v-model.number="item.max_pages" type="number" min="1" max="30" :disabled="busy" aria-label="最多页数" /><span>{{ item.image_count || 0 }} 张原文插图</span><el-button v-if="item.source_node_ids?.length" size="small" :disabled="busy" @click="perform(async () => update(await splitBatchPlan(plan.id,{revision:plan.revision,item_id:item.id})))">按小节拆分</el-button></div></div>
        </div>
        <label v-if="draft.basis === 'suggested'"><el-checkbox v-model="acceptSuggested" :disabled="busy">我已核对并接受此建议目录，后续仍需校核具体教学内容</el-checkbox></label>
        <div class="batch-actions"><el-select v-model="theme" :disabled="busy" placeholder="课件主题"><el-option v-for="template in templates" :key="template.theme" :value="template.theme" :label="template.name || template.theme" /><el-option v-if="!templates.length" value="素白风" label="素白风" /></el-select><el-button :loading="busy" @click="perform(saveChoices)">保存计划</el-button><el-button type="primary" :loading="busy" @click="confirm">确认并生成所选课件</el-button></div>
      </template>
      <details :open="draft.needs_input"><summary>补充目录或让 AI 调整方案</summary><el-input v-model="sourceText" type="textarea" :rows="4" :disabled="busy" placeholder="粘贴教学计划或章节目录；不需要重复填写已有内容" /><el-input v-model="instruction" :disabled="busy" placeholder="如：第二章拆成两份，每份6到8页" /><div class="batch-actions"><el-button :loading="busy" @click="revise(false)">根据补充内容更新方案</el-button><el-button v-if="draft.needs_input" :loading="busy" @click="revise(true)">先用 AI 建议目录规划</el-button></div></details>
    </template>
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
  </section>
</template>

<style scoped>
.batch-plan { padding:24px; border:1px solid #d5e3ff; background:#fff; border-radius:18px; color:#223653; width:100%; box-sizing:border-box; }
.batch-heading { display:flex; justify-content:space-between; gap:16px; align-items:center; }.batch-heading span { color:#2861d8; font-size:13px; } h3 { margin:8px 0 16px; } a { color:#2861d8; }
.batch-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:16px 0; }.batch-fields label { display:grid; gap:6px; font-size:13px; }
.batch-actions,.chapter-range { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:14px 0; }.batch-actions :deep(.el-button) { margin-left:0; }.batch-actions :deep(.el-select) { width:180px; }
.batch-chapter { display:flex; align-items:flex-start; gap:12px; border-top:1px solid #e8eef8; padding:16px 0; }.chapter-body { flex:1; min-width:0; display:grid; gap:8px; }.chapter-range input[type="number"] { width:78px; padding:8px 10px; border:1px solid #d5e3ff; border-radius:8px; background:#f7faff; color:#223653; box-sizing:border-box; }.chapter-range input[type="number"]:focus { outline:none; border-color:#2861d8; }.chapter-range { font-size:12px; color:#62728a; margin:0; }
details { margin:14px 0; }summary { cursor:pointer; color:#2861d8; margin-bottom:12px; }p { line-height:1.7; }.batch-plan :deep(.el-alert) { margin:10px 0; }
@media(max-width:600px) { .batch-plan { padding:16px; }.batch-fields { grid-template-columns:1fr; }.batch-heading { align-items:flex-start; }.batch-chapter { gap:6px; } }
</style>
