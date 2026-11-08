<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listPresentationBatches, readPresentationBatch, listBatchPlans, retryBatchItem, saveBatchItem,
  cancelPresentationBatch, requestBatchZip, downloadBatchZip, saveBatchDownload } from '../apis/batchPresentations'
import BatchPlanCard from './BatchPlanCard.vue'
const props = defineProps({ batchId: { type:String, default:'' } })
const batches = ref([]), plans = ref([]), selectedPlan = ref(null), loading = ref(false), error = ref(''), busy = ref('')
let active = true, timer = null, failures = 0, fetching = false
const archiveFailures = new Map()
const label = status => ({queued:'等待生成',running:'正在生成',ready:'生成完成，待同步项目',completed:'已保存到个人项目',failed:'生成失败',partial_failed:'部分章节失败',cancelled:'已取消'})[status] || status
async function load() {
  if (!active || fetching) return
  fetching = true
  try {
    const response = props.batchId ? {data:[(await readPresentationBatch(props.batchId)).data]} : await listPresentationBatches()
    if (!active) return
    batches.value = response.data || []; error.value = ''; failures = 0
    // Only archive actual ready output; server checks ownership and Java imports idempotently.
    let archived = false
    for (const batch of batches.value) {
      for (const item of batch.items) {
        if (!active) return
        if (item.status === 'ready' && (archiveFailures.get(item.id) || 0) < 3) {
          try { await saveBatchItem(batch.id,item.id); archived = true; archiveFailures.delete(item.id) }
          catch (cause) {
            archiveFailures.set(item.id,(archiveFailures.get(item.id) || 0) + 1)
            if (active) error.value = cause.message || '课件已保留，项目待同步；可稍后手动同步'
          }
        }
      }
    }
    if (archived && active) {
      const latest = props.batchId ? {data:[(await readPresentationBatch(props.batchId)).data]} : await listPresentationBatches()
      if (active) batches.value = latest.data || []
    }
    if (!props.batchId) {
      const result = await listBatchPlans()
      if (active) plans.value = (result.data || []).filter(plan => plan.status === 'draft')
    }
  } catch (cause) {
    failures++
    if (active) error.value = cause.message || '批量任务读取失败'
    if (cause.response?.status === 401 || cause.response?.status === 403) failures = 3
  } finally {
    fetching = false; loading.value = false
    const pending = batches.value.some(batch => ['queued','running'].includes(batch.status) || ['queued','running'].includes(batch.zip_status)
      || batch.items.some(item => item.status === 'ready' && (archiveFailures.get(item.id) || 0) < 3))
    if (active && failures < 3 && (pending || failures)) timer = setTimeout(load, 4000)
  }
}
async function perform(key, work) {
  if (busy.value) return
  busy.value = key
  try { await work(); clearTimeout(timer); await load() }
  catch (cause) { error.value = cause.message || '操作失败，已保留原有产物' }
  finally { busy.value = '' }
}
async function cancel(batch) {
  try { await ElMessageBox.confirm('已生成的章节会保留，尚未完成的章节将停止。','取消剩余生成') }
  catch { return }
  await perform(batch.id,() => cancelPresentationBatch(batch.id))
}
async function zip(batch, partial = false) {
  await perform(batch.id,async () => {
    await requestBatchZip(batch.id,partial)
    ElMessage.success('正在后台生成 PPTX 并打包，请稍后下载')
  })
}
function refresh() { failures = 0; clearTimeout(timer); void load() }
onMounted(() => { loading.value = true; void load() })
onBeforeUnmount(() => { active = false; clearTimeout(timer) })
</script>

<template>
  <section class="batch-tasks" v-loading="loading">
    <header><div><span>整门课，分章完成</span><h2>批量备课任务</h2><p>先确认计划，再生成每章课件。完成后可进入工作台精修，也可打包下载。</p></div><el-button @click="refresh">刷新</el-button></header>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template v-if="!batchId && plans.length"><p>尚未提交的计划</p><div class="task-actions"><el-button v-for="plan in plans" :key="plan.id" @click="selectedPlan = plan">{{ plan.title }}</el-button></div></template>
    <BatchPlanCard v-if="selectedPlan" :plan="selectedPlan" @updated="value => selectedPlan = value" @confirmed="selectedPlan = null; refresh()" />
    <p v-if="!loading && !batches.length">还没有批量任务。在 AI 教学助手上传教学计划，或输入“按这份大纲每章生成一份 PPT”即可开始。</p>
    <article v-for="batch in batches" :key="batch.id" class="batch-task">
      <div class="task-heading"><h3>{{ batch.title }}</h3><el-tag>{{ label(batch.status) }}</el-tag></div>
      <el-progress :percentage="batch.progress" />
      <p>{{ batch.items.length }} 份课件 · {{ batch.theme }} · 每章独立保存</p><p>批次 ZIP 使用本次生成的版本；在工作台修改后，可从项目或导出中心导出最新版本。</p>
      <div v-for="item in batch.items" :key="item.id" class="task-item">
        <div><strong>{{ String(item.item_order).padStart(2,'0') }} · {{ item.title }}</strong><p>{{ item.stage }} <span v-if="item.status === 'running'">{{ item.progress }}%</span></p><p v-if="item.error" class="task-error">{{ item.error }}</p></div>
        <router-link v-if="item.project_id" :to="{path:'/main/workspace',query:{projectId:item.project_id}}">进入工作台</router-link>
        <el-button v-else-if="item.status === 'failed' && item.attempts < 3" :loading="busy === item.id" @click="perform(item.id,() => retryBatchItem(batch.id,item.id))">重试本章</el-button>
        <el-button v-else-if="item.status === 'ready'" :loading="busy === item.id" @click="perform(item.id,() => saveBatchItem(batch.id,item.id))">同步到个人项目</el-button>
      </div>
      <div class="task-actions">
        <el-button v-if="batch.status === 'running' || batch.status === 'queued'" :disabled="Boolean(busy)" @click="cancel(batch)">取消剩余生成</el-button>
        <el-button v-if="batch.zip_status === 'ready'" type="primary" :loading="busy === batch.id" @click="perform(batch.id,async () => saveBatchDownload(await downloadBatchZip(batch.id),'课程课件批次.zip'))">下载整批 ZIP</el-button>
        <template v-else-if="!['queued','running'].includes(batch.zip_status)"><el-button type="primary" :disabled="Boolean(busy) || !batch.items.every(item => ['ready','completed'].includes(item.status))" @click="zip(batch)">生成整批 PPTX / ZIP</el-button><el-button v-if="batch.items.some(item => ['failed','cancelled'].includes(item.status)) && batch.items.some(item => ['ready','completed'].includes(item.status))" :disabled="Boolean(busy)" @click="zip(batch,true)">只打包已完成章节</el-button></template>
        <span v-else>正在将各章导出为可编辑 PPTX 并打包…</span>
      </div><p v-if="batch.zip_error" class="task-error">{{ batch.zip_error }}</p>
    </article>
  </section>
</template>

<style scoped>
.batch-tasks { width:100%; max-width:1120px; margin:0 auto; padding:24px; box-sizing:border-box; color:#223653; }header,.task-heading { display:flex; justify-content:space-between; align-items:center; gap:16px; }header span { color:#2861d8; font-size:13px; }h2 { margin:8px 0; }p { color:#697b94; line-height:1.7; font-size:13px; }.batch-task { margin:20px 0; padding:24px; background:#fff; border:1px solid #dce7fb; border-radius:18px; }.task-item { padding:16px 0; border-top:1px solid #edf1f8; display:flex; justify-content:space-between; gap:16px; align-items:center; }.task-item p { margin:6px 0; }.task-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:16px 0; }.task-actions :deep(.el-button) { margin-left:0; }a { color:#2861d8; white-space:nowrap; }.task-error { color:#b94747; }@media(max-width:600px) { .batch-tasks { padding:12px; }.batch-task { padding:16px; }header { align-items:flex-start; } }
</style>
