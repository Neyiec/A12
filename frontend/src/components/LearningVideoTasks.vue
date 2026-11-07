<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listLearningVideos, downloadLearningVideo, retryLearningVideo, cancelLearningVideo, uploadResource } from '../apis/teacher'
const jobs = ref([]), error = ref(''), busy = ref('')
const labels = { queued: '排队中', running: '生成中', ready: '已完成', failed: '失败', cancelled: '已取消' }
let timer = null, disposed = false
let requestSeq = 0, failures = 0
async function refresh() {
  if (disposed) return
  clearTimeout(timer)
  const sequence = ++requestSeq
  let stop = false
  try {
    const result = await listLearningVideos()
    if (disposed || sequence !== requestSeq) return
    jobs.value = result?.data || result || []; error.value = ''; failures = 0
  } catch (e) {
    if (disposed || sequence !== requestSeq) return
    failures += 1
    stop = [401,403].includes(e?.response?.status ?? e?.code) || failures >= 3
    error.value = e?.message || '学习视频任务加载失败'
  } finally { if (!disposed && sequence === requestSeq && !stop) timer = setTimeout(refresh, 5000) }
}
onMounted(refresh)
onBeforeUnmount(() => { disposed = true; requestSeq += 1; clearTimeout(timer) })
async function action(job, type) {
  if (busy.value) return
  busy.value = job.job_id
  try {
    if (type === 'retry') await retryLearningVideo(job.job_id)
    else if (type === 'cancel') await cancelLearningVideo(job.job_id)
    else {
      const response = await downloadLearningVideo(job.job_id)
      const blob = response instanceof Blob ? response : response.data
      if (type === 'save') {
        await uploadResource(new File([blob], `${job.title}.mp4`, { type: 'video/mp4' }))
        ElMessage.success('已保存视频到个人资源库')
      } else {
        const url = URL.createObjectURL(blob), a = document.createElement('a')
        a.href = url; a.download = `${job.title}.mp4`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
    }
    clearTimeout(timer); await refresh()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败') }
  finally { busy.value = '' }
}
</script>
<template>
  <section class="video-tasks"><header><h2>学习视频任务</h2><small>课件静态画面 + TTS 旁白 · 完成后24小时内下载或转存资源库</small></header>
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <el-empty v-else-if="!jobs.length" description="在课程双图谱页面生成课件后，可提交学习视频任务" :image-size="50" />
    <article v-for="job in jobs" :key="job.job_id"><div><strong>{{ job.title }}</strong><p>{{ labels[job.status] }} · 已尝试 {{ job.attempts }} 次<span v-if="job.error"> · {{ job.error }}</span></p><el-progress :percentage="job.progress" :status="job.status === 'failed' ? 'exception' : job.status === 'ready' ? 'success' : undefined" /></div>
      <div class="actions"><el-button v-if="job.status === 'ready'" :disabled="!!busy" @click="action(job,'download')">下载MP4</el-button><el-button v-if="job.status === 'ready'" :disabled="!!busy" @click="action(job,'save')">转存资源库</el-button><el-button v-if="job.status === 'failed' && job.attempts < 2" :disabled="!!busy" @click="action(job,'retry')">重试</el-button><el-button v-if="['queued','running'].includes(job.status)" :disabled="!!busy" @click="action(job,'cancel')">取消</el-button></div></article>
  </section>
</template>
<style scoped>
.video-tasks{margin:24px 0;padding:22px;border:1px solid #e2e8f0;border-radius:18px;background:var(--zh-surface,#fff)}h2{font-size:20px;margin:0 0 8px}small,p{color:#64748b}article{display:flex;justify-content:space-between;gap:24px;padding:18px 0;border-top:1px solid #e2e8f0;margin-top:14px}article>div:first-child{flex:1;min-width:0}.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}p{font-size:13px}@media(max-width:767px){article{flex-direction:column}.video-tasks{padding:14px}}
</style>
