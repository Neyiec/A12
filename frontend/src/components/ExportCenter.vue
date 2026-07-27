<!--
  [数据交互说明]
  - 导入: 导出中心演示数据、Element Plus 组件
  - 输出: 教学成果导出任务与历史文件页面
-->
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Download, Files, Refresh, Search, Warning } from '@element-plus/icons-vue'
import { EXPORT_PAGE } from '../config/teacherPages.config.js'
import { createExportTask, downloadExportArtifact, listExportTasks, precheckExport, retryExportTask } from '../apis/teacher'

const route = useRoute()

const keyword = ref('')
const activeTab = ref('全部任务')
const tabs = ['全部任务', '进行中', '已完成', '需要处理']
const tasks = ref(EXPORT_PAGE.tasks)
const loading = ref(false)
const normalizeTask = (task) => ({
  id: task.id, project: task.project_name || task.project?.project_name || task.file_name || '未命名项目',
  format: (task.export_type || task.format || '成果包').toUpperCase(), version: task.snapshot_version ? `v${task.snapshot_version}` : task.version || '—',
  time: task.created_at || task.time || '刚刚', status: ({ queued: '排队中', generating: '生成中', checking: '校验中', success: '成功', partial: '部分成功', failed: '失败', cancelled: '已取消' })[task.status] || task.status || '排队中',
  quality: task.quality_report ? '查看报告' : task.quality || '待校验', size: task.file_size_text || task.size || '—', fileStatus: task.file_status,
})
const loadTasks = async () => {
  loading.value = true
  try {
    const status = activeTab.value === '进行中' ? 'generating' : activeTab.value === '已完成' ? 'success' : undefined
    const result = await listExportTasks({ status, page: 1, size: 50 })
    const records = result?.data?.records || result?.data?.list || result?.data?.items || result?.records || []
    if (records.length) tasks.value = records.map(normalizeTask)
  } catch { /* 服务未就绪时展示现有示例任务。 */ } finally { loading.value = false }
}

/** 根据当前状态页签和关键词过滤导出任务。 */
const filteredTasks = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase()
  return tasks.value.filter((task) => {
    const matchesKeyword = !normalizedKeyword || [task.project, task.format, task.version]
      .some((value) => value.toLowerCase().includes(normalizedKeyword))
    const matchesTab = activeTab.value === '全部任务'
      || activeTab.value === '进行中' && ['排队中', '生成中', '校验中'].includes(task.status)
      || activeTab.value === '已完成' && ['成功', '部分成功'].includes(task.status)
      || activeTab.value === '需要处理' && ['部分成功', '已过期', '失败'].includes(task.status)
    return matchesKeyword && matchesTab
  })
})

const createExport = async () => {
  const projectId = route.query.projectId
  if (!projectId) return ElMessage.info('请在工作台选择项目后发起导出')
  try {
    const precheck = await precheckExport(projectId, { snapshot_version: 1, export_type: 'package' })
    const checkData = precheck?.data || precheck || {}
    if (checkData.passed === false) return ElMessage.error(checkData.errors?.[0] || '导出前校验未通过')
    await createExportTask({ project_id: Number(projectId), snapshot_version: 1, export_type: 'package', config: '{}' })
    ElMessage.success('导出任务已创建')
    await loadTasks()
  } catch { ElMessage.error('创建导出任务失败，请稍后重试') }
}
const download = async (row) => {
  if (!row.id) return ElMessage.info('示例任务暂不支持下载')
  try {
    if (row.fileStatus === 'expired' || row.status === '已过期') { await retryExportTask(row.id); ElMessage.success('已重新提交生成任务'); await loadTasks(); return }
    const result = await downloadExportArtifact(row.id)
    const url = result?.data?.download_url || result?.download_url
    if (url) window.open(url, '_blank', 'noopener'); else ElMessage.warning('文件尚未生成完成')
  } catch { ElMessage.error('操作未成功，请稍后重试') }
}
watch(activeTab, loadTasks)
onMounted(loadTasks)
</script>

<template>
  <div class="export-page">
    <header class="export-heading">
      <div><p>成果交付与追溯</p><h1>成果导出中心</h1><span>把已确认的课件、教案与互动组件转换为可编辑、可追溯的标准文件。</span></div>
      <el-button type="primary" :icon="Files" @click="createExport">新建导出</el-button>
    </header>

    <section class="export-stats">
      <article v-for="stat in EXPORT_PAGE.stats" :key="stat.label"><span>{{ stat.label }}</span><strong>{{ stat.value }}</strong><small>{{ stat.detail }}</small></article>
    </section>

    <section class="active-task">
      <div class="task-icon"><el-icon><Refresh /></el-icon></div>
      <div class="task-copy"><span>正在生成</span><h2>《分数的初步认识》教学成果包</h2><p>当前阶段：校验字体与 H5 互动组件兼容性</p></div>
      <div class="task-progress"><div><span>72%</span><small>预计还需 38 秒</small></div><el-progress :percentage="72" :show-text="false" /></div>
      <el-button>查看详情</el-button>
    </section>

    <section class="quality-panel">
      <header><div><el-icon><CircleCheck /></el-icon><span><strong>导出前质量校验</strong><small>最近项目快照 v1.4</small></span></div><el-button type="primary" link>查看完整报告</el-button></header>
      <div class="quality-items">
        <span><el-icon><CircleCheck /></el-icon>页面结构完整</span>
        <span><el-icon><CircleCheck /></el-icon>素材授权有效</span>
        <span class="warning"><el-icon><Warning /></el-icon>1 个字体将自动替换</span>
        <span><el-icon><CircleCheck /></el-icon>未发现敏感信息</span>
      </div>
    </section>

    <section class="history-panel">
      <div class="history-header"><div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ tab }}</button></div><el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索项目或版本" clearable /></div>
      <el-table v-loading="loading" :data="filteredTasks">
        <el-table-column label="项目成果" min-width="240"><template #default="{ row }"><div class="project-cell"><span><el-icon><Files /></el-icon></span><div><strong>{{ row.project }}</strong><small>{{ row.format }} · {{ row.version }}</small></div></div></template></el-table-column>
        <el-table-column prop="time" label="创建时间" min-width="125" />
        <el-table-column label="任务状态" width="120"><template #default="{ row }"><el-tag :type="row.status === '成功' ? 'success' : row.status === '部分成功' ? 'warning' : 'info'">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="quality" label="质量报告" width="120" />
        <el-table-column prop="size" label="文件大小" width="100" />
        <el-table-column label="操作" width="118"><template #default="{ row }"><el-button type="primary" link :icon="row.status === '已过期' ? Refresh : Download" @click="download(row)">{{ row.status === '已过期' ? '重新生成' : '下载' }}</el-button></template></el-table-column>
        <template #empty><el-empty description="没有符合当前筛选条件的导出任务" /></template>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.export-page { width: min(1180px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 60px; }
.export-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; }.export-heading p { margin: 0 0 6px; color: var(--zh-text-theme); font-size: 13px; font-weight: 600; }.export-heading h1 { margin: 0; font-size: 30px; letter-spacing: var(--zh-tracking-tight); }.export-heading span { display: block; margin-top: 8px; color: var(--zh-text-secondary); font-size: 14px; }
.export-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 30px; }.export-stats article { display: grid; padding: 20px 22px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); }.export-stats span { color: var(--zh-text-secondary); font-size: 12px; }.export-stats strong { margin: 10px 0 3px; font: 600 26px var(--zh-font-number); }.export-stats small { color: var(--zh-text-caption); }
.active-task { display: grid; grid-template-columns: auto minmax(250px, 1fr) minmax(200px, .65fr) auto; align-items: center; gap: 18px; margin-top: 18px; padding: 20px 22px; border-radius: var(--zh-radius12); color: white; background: #1d4f91; box-shadow: 0 12px 26px -12px rgb(29 78 216 / 45%); }
.task-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: var(--zh-radius10); background: rgb(255 255 255 / 12%); }.task-icon :deep(.el-icon) { animation: loadingSpin 1.5s linear infinite; }
.task-copy span, .task-progress small { color: rgb(255 255 255 / 65%); font-size: 11px; }.task-copy h2 { margin: 3px 0; font-size: 16px; }.task-copy p { margin: 0; color: rgb(255 255 255 / 72%); font-size: 12px; }
.task-progress > div { display: flex; justify-content: space-between; margin-bottom: 7px; font-family: var(--zh-font-number); }.active-task :deep(.el-progress-bar__outer) { background: rgb(255 255 255 / 18%); }.active-task :deep(.el-progress-bar__inner) { background: #93c5fd; }
.quality-panel, .history-panel { margin-top: 18px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); }
.quality-panel header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--zh-line-parting); }.quality-panel header > div { display: flex; align-items: center; gap: 10px; color: var(--zh-green); }.quality-panel header span { display: flex; flex-direction: column; }.quality-panel header strong { color: var(--zh-text-primary); font-size: 13px; }.quality-panel header small { margin-top: 2px; color: var(--zh-text-caption); }
.quality-items { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 14px 20px; }.quality-items span { display: flex; align-items: center; gap: 6px; color: var(--zh-text-secondary); font-size: 12px; }.quality-items .el-icon { color: var(--zh-green); }.quality-items .warning .el-icon { color: var(--zh-orange); }
.history-header { display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid var(--zh-line-parting); }.tab-list { display: flex; gap: 16px; }.tab-list button { padding: 17px 2px 14px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; cursor: pointer; }.tab-list button.active { color: var(--zh-text-theme); border-color: var(--zh-line-theme); font-weight: 600; }.history-header :deep(.el-input) { width: 230px; }
.project-cell { display: flex; align-items: center; gap: 10px; }.project-cell > span { width: 34px; height: 34px; display: grid; place-items: center; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); }.project-cell > div { display: flex; flex-direction: column; }.project-cell strong { color: var(--zh-text-primary); font-size: 13px; }.project-cell small { margin-top: 3px; color: var(--zh-text-caption); }
.history-panel :deep(.el-table) { --el-table-border-color: var(--zh-line-parting); border-radius: 0 0 var(--zh-radius12) var(--zh-radius12); }
/* design.md：文字按钮采用主题链接色；所有交互态必须保持文字可读。 */
.export-page :deep(.el-button--primary.is-link) { color: var(--zh-text-link); }
.export-page :deep(.el-button--primary.is-link:hover), .export-page :deep(.el-button--primary.is-link:focus-visible) { color: var(--zh-text-link); background: var(--zh-background-weaken); }
.export-page :deep(.el-button--primary.is-link:active) { color: var(--zh-text-link); background: var(--zh-line-theme20); }
@keyframes loadingSpin { to { transform: rotate(360deg); } }
@media (max-width: 900px) { .active-task { grid-template-columns: auto 1fr; }.task-progress { grid-column: 1 / -1; }.quality-items { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 620px) { .export-stats { grid-template-columns: 1fr; }.history-header { align-items: stretch; flex-direction: column; }.history-header :deep(.el-input) { width: 100%; margin-bottom: 12px; }.quality-items { grid-template-columns: 1fr; } }
</style>
