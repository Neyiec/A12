<!--
  [数据交互说明]
  - 导入: 导出任务、项目、预检、质量报告与成果链接 API
  - 输出: 真实导出任务创建、轮询、预览、下载与质量报告交互
  - 说明: 开发预览入口也走 mock API，不生成本地演示任务或本地假文件
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, CircleClose, DocumentChecked, Download, Files, FolderOpened, Refresh, Search, Timer, View, Warning } from '@element-plus/icons-vue'
import { EXPORT_PAGE } from '../config/teacherPages.config.js'
import { cancelExportTask, createExportPreviewUrl, createExportTask, downloadExportArtifact, getExportArtifact, getExportQualityReport, getExportTask, getProject, listExportTasks, precheckProjectExport, retryExportTask, saveProjectVersion } from '../apis/teacher'

const route = useRoute()
const router = useRouter()
const testCase = EXPORT_PAGE.testCase
const isDevelopmentPreview = computed(() => import.meta.env.DEV && route.query.preview === '1')
const showFlowTest = computed(() => isDevelopmentPreview.value && route.query.testCase === testCase.id)
const projectId = computed(() => route.query.projectId ? String(route.query.projectId) : '')
const autoExportRequested = computed(() => route.query.autoExport === '1')
const autoExportFlowVisible = ref(false)
const flowDetailVisible = ref(false)
const showFlowPanel = computed(() => autoExportFlowVisible.value && flowDetailVisible.value)

const keyword = ref('')
const activeTab = ref('全部任务')
const tabs = ['全部任务', '进行中', '已完成', '需要处理']
const tasks = ref([])
const loading = ref(false)
const pageError = ref('')
const exportDialogVisible = ref(false)
const reportVisible = ref(false)
const previewVisible = ref(false)
const taskDetailVisible = ref(false)
const exportForm = ref({ project_id: '', export_type: 'package', snapshot_version: '', template_version: 'zh-teaching-v1', header_enabled: true, header_text: '', footer_text: '', teacher_notes: '', interaction_mode: 'package', page_range: 'all' })
const precheck = ref(null)
const precheckSignature = ref('')
const qualityReport = ref(null)
const previewUrl = ref('')
const taskDetail = ref(null)
const taskDetailRow = ref(null)
const project = ref(null)

const flow = ref({
  status: 'idle',
  step: 0,
  taskId: null,
  progress: 0,
  message: '正在准备项目快照和导出配置。',
  error: '',
  precheck: null,
  downloaded: false,
})

let taskPollTimer = null
let activePoll = false
let autoExportStarted = false

const flowSteps = [
  { title: '项目已保存', detail: '当前工作台内容已写入项目' },
  { title: '快照已固化', detail: '导出内容绑定不可变项目版本' },
  { title: '导出前校验', detail: '检查结构、素材与格式兼容性' },
  { title: '文件生成', detail: '异步生成成果并执行质量检查' },
  { title: '成果交付', detail: '完成后可预览、查看报告和下载' },
]

const statusText = {
  queued: '排队中',
  generating: '生成中',
  checking: '校验中',
  success: '成功',
  partial: '部分成功',
  failed: '失败',
  cancelled: '已取消',
}
const runningStatuses = ['queued', 'generating', 'checking']
const completedStatuses = ['success', 'partial']

const unwrap = (response) => response?.data || response
const recordsFrom = (response) => {
  const data = unwrap(response)
  return data?.records || data?.list || data?.items || []
}
const statusTagType = (status) => ({ 成功: 'success', 部分成功: 'warning', 失败: 'danger', 已取消: 'info' }[status] || 'info')
const isRunning = (row) => runningStatuses.includes(row?.apiStatus)
const canDownload = (row) => completedStatuses.includes(row?.apiStatus) && row?.fileStatus !== 'expired'
const safeFilename = (value) => String(value || 'export').replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, ' ').trim()
const exportExtension = (type) => ({ pptx: 'pptx', word: 'docx', package: 'zip' }[String(type)] || 'zip')
const formatDate = (value) => {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date)
}
const formatSize = (value) => {
  if (!value && value !== 0) return '—'
  if (typeof value === 'string') return value
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

const normalizeTask = (task, context = {}) => {
  const apiStatus = task?.status || 'queued'
  const projectName = task?.project_name || task?.project?.project_name || context.project_name || (String(task?.project_id) === projectId.value ? testCase.projectName : '')
  const subject = task?.subject || task?.project?.subject || context.subject || (String(task?.project_id) === projectId.value ? testCase.subject : '—')
  return {
    ...task,
    id: task?.id,
    project: projectName || task?.file_name || '未命名项目',
    format: ({ pptx: 'PPTX', word: 'Word', package: '成果包' }[String(task?.export_type || '').toLowerCase()] || task?.format || '成果包'),
    version: task?.snapshot_version ? `v${task.snapshot_version}` : task?.version || '—',
    time: formatDate(task?.created_at || task?.time),
    apiStatus,
    status: statusText[apiStatus] || apiStatus || '排队中',
    progress: Number.isFinite(Number(task?.progress)) ? Math.max(0, Math.min(100, Number(task.progress))) : apiStatus === 'success' ? 100 : 0,
    quality: task?.quality_report ? '查看报告' : task?.quality || (apiStatus === 'success' ? '待查看' : '待校验'),
    size: formatSize(task?.file_size ?? task?.file_size_text ?? task?.size),
    fileStatus: task?.file_status,
    subject,
    pages: task?.page_count || task?.pages || context.page_count || '—',
    stage: task?.stage || task?.status_message || ({ queued: '等待导出服务接管', generating: '正在生成成果文件', checking: '正在进行导出校验', success: '成果文件已生成' }[apiStatus] || '—'),
    source: task?.data_source || '导出服务',
  }
}

const mergeTask = (row) => {
  const index = tasks.value.findIndex((task) => String(task.id) === String(row.id))
  if (index === -1) tasks.value = [row, ...tasks.value]
  else tasks.value.splice(index, 1, row)
}

const loadProjectContext = async () => {
  if (!projectId.value) return
  try {
    project.value = unwrap(await getProject(projectId.value))
    if (showFlowPanel.value) {
      flow.value.step = 1
      flow.value.message = `项目“${project.value?.project_name || testCase.projectName}”已准备，等待导出。`
    }
  } catch (error) {
    project.value = null
    if (showFlowPanel.value) flow.value.error = error?.message || '项目加载失败，无法创建导出任务'
  }
}

const loadTasks = async () => {
  loading.value = true
  pageError.value = ''
  try {
    // 预览入口也调用分页接口，保证任务列表来自服务端内存状态。
    const result = await listExportTasks({ page: 1, size: 50 })
    const context = project.value || {}
    tasks.value = recordsFrom(result).map((task) => normalizeTask(task, context))
    const flowTask = flow.value.taskId && tasks.value.find((row) => String(row.id) === String(flow.value.taskId))
    if (flowTask) {
      flow.value.progress = flowTask.progress
      flow.value.status = flowTask.apiStatus
    }
  } catch (error) {
    pageError.value = error?.message || '导出任务加载失败'
    tasks.value = []
  } finally {
    loading.value = false
    scheduleTaskPolling()
  }
}

const scheduleTaskPolling = () => {
  clearTimeout(taskPollTimer)
  if (!tasks.value.some(isRunning)) return
  taskPollTimer = window.setTimeout(async () => {
    await loadTasks()
  }, 900)
}

const pollTask = async (taskId) => {
  const timeoutAt = Date.now() + 20_000
  activePoll = true
  try {
    while (Date.now() < timeoutAt) {
      const latest = normalizeTask(unwrap(await getExportTask(taskId)), project.value || {})
      mergeTask(latest)
      flow.value.progress = latest.progress
      flow.value.status = latest.apiStatus
      flow.value.message = latest.stage
      if (latest.apiStatus === 'success' || latest.apiStatus === 'partial') return latest
      if (['failed', 'cancelled'].includes(latest.apiStatus)) throw new Error(latest.error_msg || `导出任务${latest.status}`)
      await new Promise((resolve) => window.setTimeout(resolve, 400))
    }
    throw new Error('导出任务轮询超时，请查看任务列表')
  } finally {
    activePoll = false
    scheduleTaskPolling()
  }
}

const flowStepState = (index) => {
  if (flow.value.downloaded || flow.value.step > index) return 'complete'
  if (flow.value.step === index) return 'current'
  return ''
}

const buildExportConfig = (extra = {}) => ({
  template_version: exportForm.value.template_version.trim() || 'zh-teaching-v1',
  header_footer: { enabled: Boolean(exportForm.value.header_enabled), header: exportForm.value.header_text.trim(), footer: exportForm.value.footer_text.trim() },
  teacher_notes: exportForm.value.teacher_notes.trim(),
  interaction_mode: exportForm.value.interaction_mode,
  page_range: exportForm.value.page_range.trim() || 'all',
  ...extra,
})
const clearPrecheck = () => { precheck.value = null; precheckSignature.value = '' }
const saveImmutableSnapshot = async (id, description = '导出前自动固化快照') => {
  const saved = unwrap(await saveProjectVersion(id, { description }))
  const version = Number(saved?.version_number)
  if (!Number.isFinite(version) || version <= 0) throw new Error('项目版本接口未返回有效快照版本')
  if (String(id) === projectId.value) project.value = { ...(project.value || {}), current_version: version }
  return version
}

const runFullFlow = async () => {
  if (!projectId.value) {
    flow.value.error = '项目尚未保存，无法创建导出任务。'
    return
  }
  if (activePoll) return

  flow.value = { ...flow.value, status: 'snapshotting', step: 1, taskId: null, progress: 0, error: '', precheck: null, downloaded: false, message: '正在保存不可变项目快照…' }
  try {
    const snapshotVersion = await saveImmutableSnapshot(projectId.value, '社区全流程测试案例导出快照')
    const exportType = showFlowTest.value ? testCase.exportType : 'package'
    const config = buildExportConfig({ source: showFlowTest.value ? 'community-test-case' : 'workspace-export', ...(showFlowTest.value ? { test_case_id: testCase.id } : {}) })
    flow.value.step = 2
    flow.value.status = 'prechecking'
    flow.value.message = `快照 v${snapshotVersion} 已固化，正在调用导出预检接口…`
    const check = unwrap(await precheckProjectExport(projectId.value, {
      export_type: exportType,
      snapshot_version: snapshotVersion,
      config,
      ...(showFlowTest.value ? { test_case_id: testCase.id } : {}),
    }))
    flow.value.precheck = check
    if (!check?.passed) throw new Error(check?.errors?.[0]?.message || '导出预检未通过')

    flow.value.step = 3
    flow.value.status = 'queued'
    flow.value.message = '预检通过，正在创建导出任务…'
    const created = unwrap(await createExportTask({
      project_id: Number(projectId.value),
      export_type: exportType,
      snapshot_version: snapshotVersion,
      ...(showFlowTest.value ? { test_case_id: testCase.id } : {}),
      precheck_confirmed: true,
      config: JSON.stringify(config),
    }))
    if (!created?.id) throw new Error('导出任务接口未返回任务 ID')
    flow.value.taskId = created.id
    mergeTask(normalizeTask(created, project.value || {}))
    const completed = await pollTask(created.id)
    flow.value.step = 5
    flow.value.status = completed.apiStatus
    flow.value.progress = completed.progress
    flow.value.message = '导出任务已完成，可继续打开质量报告、在线预览或下载成果。'
    await loadTasks()
    ElMessage.success('导出任务已创建并完成')
  } catch (error) {
    flow.value.status = 'failed'
    flow.value.error = error?.message || '导出流程执行失败'
    flow.value.message = '流程未完成，请根据错误信息处理后重试。'
    flowDetailVisible.value = true
    await loadTasks()
    ElMessage.error(flow.value.error)
  }
}

const filteredTasks = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase()
  return tasks.value.filter((task) => {
    const matchesKeyword = !normalizedKeyword || [task.project, task.format, task.version, task.subject]
      .some((value) => String(value ?? '').toLowerCase().includes(normalizedKeyword))
    const matchesTab = activeTab.value === '全部任务'
      || activeTab.value === '进行中' && runningStatuses.includes(task.apiStatus)
      || activeTab.value === '已完成' && completedStatuses.includes(task.apiStatus)
      || activeTab.value === '需要处理' && ['partial', 'failed', 'cancelled'].includes(task.apiStatus)
    return matchesKeyword && matchesTab
  })
})

const stats = computed(() => {
  const completed = tasks.value.filter((task) => completedStatuses.includes(task.apiStatus))
  const durations = completed.map((task) => {
    if (!task.created_at || !task.completed_at) return 0
    return Math.max(0, new Date(task.completed_at).getTime() - new Date(task.created_at).getTime())
  }).filter(Boolean)
  const averageSeconds = durations.length ? Math.round(durations.reduce((sum, value) => sum + value, 0) / durations.length / 1000) : 0
  const average = averageSeconds ? `${Math.floor(averageSeconds / 60)}m ${averageSeconds % 60}s` : '—'
  return [
    { label: '导出任务', value: String(tasks.value.length), detail: '来自当前教师账号的导出记录' },
    { label: '可下载成果', value: String(completed.filter(canDownload).length), detail: '由服务端任务状态决定' },
    { label: '平均生成时间', value: average, detail: durations.length ? `基于最近 ${durations.length} 个已完成任务` : '完成任务后自动计算' },
  ]
})

const flowTask = computed(() => flow.value.taskId ? tasks.value.find((row) => String(row.id) === String(flow.value.taskId)) : null)
const activeTaskView = computed(() => tasks.value.find(isRunning) || null)
const primaryTaskView = computed(() => flowTask.value || activeTaskView.value)
const latestCompletedTask = computed(() => tasks.value.find((task) => completedStatuses.includes(task.apiStatus)) || null)
const activeTaskLabel = computed(() => flowTask.value ? '本次导出' : primaryTaskView.value?.status || '暂无进行中的任务')
const activeTaskEstimate = computed(() => primaryTaskView.value ? `当前进度 ${primaryTaskView.value.progress}%` : '可从当前项目或已有项目创建导出任务')
const flowStatusLabel = computed(() => ({
  idle: '准备中', snapshotting: '正在固化快照', prechecking: '正在预检', queued: '等待生成',
  generating: '正在生成', checking: '质量校验中', success: '已完成', partial: '部分完成',
  failed: '需要处理', cancelled: '已取消',
}[flow.value.status] || '处理中'))
const flowStatusType = computed(() => ({ success: 'success', partial: 'warning', failed: 'danger', cancelled: 'info' }[flow.value.status] || 'primary'))

const openTaskDetail = async (row) => {
  taskDetailRow.value = row
  taskDetail.value = row?.id ? unwrap(await getExportTask(row.id)) : row
  taskDetailVisible.value = true
}

const taskDetailView = computed(() => {
  const row = taskDetailRow.value || {}
  const raw = taskDetail.value || {}
  return {
    title: raw.project_name || raw.file_name || row.project || '未命名成果',
    format: String(raw.export_type || row.format || '成果包').toUpperCase(),
    version: raw.snapshot_version ? `v${raw.snapshot_version}` : row.version || '—',
    status: statusText[raw.status] || row.status || '未知',
    progress: Number(raw.progress ?? row.progress ?? 0),
    stage: raw.stage || raw.status_message || row.stage || '—',
    createdAt: formatDate(raw.created_at || row.created_at || row.time),
    completedAt: formatDate(raw.completed_at),
    size: formatSize(raw.file_size ?? row.size),
    projectId: raw.project_id || row.project_id || '—',
    source: raw.test_case_id ? '社区案例' : row.source,
  }
})

const parseReportValue = (value) => {
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}
const qualityReportView = computed(() => {
  const outer = qualityReport.value || {}
  const nested = parseReportValue(outer.quality_report)
  const source = nested && typeof nested === 'object' ? nested : outer
  const read = (...keys) => keys.map((key) => source[key]).find((value) => value !== undefined && value !== null && value !== '') ?? '—'
  const rawItems = read('检查项', 'checks', 'items', 'results')
  const items = (Array.isArray(rawItems) ? rawItems : []).map((item, index) => ({
    name: item?.名称 || item?.name || item?.title || `检查项 ${index + 1}`,
    result: item?.结果 || item?.result || item?.status || '待确认',
    detail: item?.说明 || item?.detail || item?.message || '',
  }))
  const rawScore = Number(read('总分', 'score', 'total_score'))
  return {
    title: read('成果名称', 'project_name', 'title') === '—' ? taskDetailRow.value?.project || '未命名成果' : read('成果名称', 'project_name', 'title'),
    marker: read('report_id'),
    conclusion: read('校验结论', 'conclusion', 'status'),
    score: Number.isFinite(rawScore) ? Math.max(0, Math.min(100, rawScore)) : 0,
    items,
  }
})
const reportPassed = (value) => ['通过', 'passed', 'pass', 'success', 'ok'].includes(String(value).toLowerCase())
const qualityScoreStatus = computed(() => qualityReportView.value.score >= 80 ? 'success' : qualityReportView.value.score >= 60 ? 'warning' : 'exception')
const qualityTagType = computed(() => qualityReportView.value.score >= 80 ? 'success' : qualityReportView.value.score >= 60 ? 'warning' : 'danger')

const openQualityReport = async (row) => {
  if (!row?.id) return ElMessage.info('当前任务还没有可读取的质量报告')
  try {
    qualityReport.value = unwrap(await getExportQualityReport(row.id))
    taskDetailRow.value = row
    reportVisible.value = true
  } catch (error) {
    ElMessage.error(error?.message || '质量报告加载失败')
  }
}
const openLatestQualityReport = () => {
  if (!latestCompletedTask.value) return ElMessage.info('完成一次导出后，这里会显示真实质量报告')
  openQualityReport(latestCompletedTask.value)
}

const triggerDownload = (url, filename) => {
  if (!url) return false
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  anchor.target = url.startsWith('data:') || url.startsWith('blob:') ? '_self' : '_blank'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  return true
}

const download = async (row) => {
  if (!row?.id) return ElMessage.info('当前任务暂不支持下载')
  if (!canDownload(row)) return ElMessage.info('成果正在生成，请稍候再下载')
  try {
    const result = unwrap(await downloadExportArtifact(row.id))
    const url = result?.download_url
    if (!triggerDownload(url, `${safeFilename(row.project)}-${safeFilename(row.version)}.${exportExtension(row.export_type)}`)) return ElMessage.warning('服务端暂未返回下载链接')
    if (autoExportFlowVisible.value && String(row.id) === String(flow.value.taskId)) {
      flow.value.downloaded = true
      flow.value.step = 5
      flow.value.message = '成果文件已交付，可继续在任务列表中查看和下载。'
    }
    ElMessage.success('成果下载已开始')
  } catch (error) {
    if (row.fileStatus === 'expired' || row.status === '已过期') {
      await retry(row)
      return
    }
    ElMessage.error(error?.message || '下载链接获取失败')
  }
}

const retry = async (row) => {
  if (!row?.id) return
  try {
    await retryExportTask(row.id)
    ElMessage.success('已重新提交生成任务')
    await loadTasks()
  } catch (error) { ElMessage.error(error?.message || '重试失败') }
}

const cancel = async (row) => {
  if (!row?.id) return
  try {
    await cancelExportTask(row.id)
    ElMessage.success('任务已取消')
    await loadTasks()
  } catch (error) { ElMessage.error(error?.message || '取消任务失败') }
}

const openPreview = async (row) => {
  if (!canDownload(row)) return ElMessage.info('成果生成完成后才可预览')
  try {
    const artifact = unwrap(await getExportArtifact(row.id))
    const preview = unwrap(await createExportPreviewUrl(row.id))
    previewUrl.value = preview?.preview_url || artifact?.preview_url || artifact?.download_url || ''
    if (!previewUrl.value) return ElMessage.warning('服务端暂未返回预览链接')
    taskDetailRow.value = row
    previewVisible.value = true
  } catch (error) { ElMessage.error(error?.message || '预览链接获取失败') }
}

const resetExportForm = () => {
  exportForm.value = {
    project_id: projectId.value || '',
    export_type: showFlowTest.value ? testCase.exportType : 'package', snapshot_version: '', template_version: 'zh-teaching-v1', header_enabled: true, header_text: '', footer_text: '', teacher_notes: '', interaction_mode: showFlowTest.value ? 'package' : 'static', page_range: 'all',
  }
  clearPrecheck()
}
const openExportDialog = () => { resetExportForm(); exportDialogVisible.value = true }
const runPrecheck = async () => {
  if (!exportForm.value.project_id) return ElMessage.warning('请输入项目 ID')
  try {
    const snapshotVersion = Number(exportForm.value.snapshot_version) || await saveImmutableSnapshot(exportForm.value.project_id)
    exportForm.value.snapshot_version = String(snapshotVersion)
    const config = buildExportConfig()
    precheck.value = unwrap(await precheckProjectExport(exportForm.value.project_id, {
      export_type: exportForm.value.export_type,
      snapshot_version: snapshotVersion,
      config,
      ...(showFlowTest.value ? { test_case_id: testCase.id } : {}),
    }))
    precheckSignature.value = JSON.stringify({ projectId: exportForm.value.project_id, snapshotVersion, exportType: exportForm.value.export_type, config })
    if (precheck.value?.passed) ElMessage.success(precheck.value.warnings?.length ? '导出预检通过，存在需确认的警告' : '导出预检通过')
    else ElMessage.warning('导出预检未通过，请处理错误项')
  } catch (error) { ElMessage.error(error?.message || '导出预检失败') }
}
const submitExport = async () => {
  if (!exportForm.value.project_id) return ElMessage.warning('请输入项目 ID')
  try {
    const snapshotVersion = Number(exportForm.value.snapshot_version)
    const config = buildExportConfig()
    const signature = JSON.stringify({ projectId: exportForm.value.project_id, snapshotVersion, exportType: exportForm.value.export_type, config })
    if (!precheck.value?.passed || precheckSignature.value !== signature) return ElMessage.warning('请先对当前快照和导出配置运行预检')
    if (precheck.value.warnings?.length) {
      await ElMessageBox.confirm('预检存在警告，继续后将按当前导出配置处理。是否确认创建任务？', '确认导出警告', { type: 'warning', confirmButtonText: '确认继续', cancelButtonText: '返回修改' })
    }
    const created = unwrap(await createExportTask({
      ...exportForm.value,
      project_id: Number(exportForm.value.project_id),
      snapshot_version: snapshotVersion,
      precheck_confirmed: true,
      config: JSON.stringify(config),
      ...(showFlowTest.value ? { test_case_id: testCase.id } : {}),
    }))
    if (!created?.id) throw new Error('导出任务接口未返回任务 ID')
    mergeTask(normalizeTask(created, project.value || {}))
    exportDialogVisible.value = false
    ElMessage.success('导出任务已创建')
    await loadTasks()
  } catch (error) { ElMessage.error(error?.message || '导出任务创建失败') }
}

const handleCreateTask = () => openExportDialog()
const handleActiveTaskDetail = () => {
  if (flowTask.value && autoExportFlowVisible.value) {
    flowDetailVisible.value = !flowDetailVisible.value
    return
  }
  if (primaryTaskView.value) openTaskDetail(primaryTaskView.value)
}

watch(projectId, async () => {
  await loadProjectContext()
  await loadTasks()
})

onMounted(async () => {
  await loadProjectContext()
  await loadTasks()
  if (autoExportRequested.value && !autoExportStarted) {
    autoExportStarted = true
    autoExportFlowVisible.value = true
    // 消费一次性标记，避免刷新导出中心时重复创建任务。
    const { autoExport, ...query } = route.query
    await router.replace({ path: route.path, query })
    if (!projectId.value) {
      flow.value.status = 'failed'
      flow.value.error = '工作台没有生成项目 ID，无法创建导出任务。请返回工作台重新点击导出。'
      flow.value.message = '自动导出未启动。'
      flowDetailVisible.value = true
      return
    }
    await runFullFlow()
  }
})
onBeforeUnmount(() => clearTimeout(taskPollTimer))
</script>

<template>
  <main class="export-page">
    <header class="export-heading">
      <div>
        <p class="eyebrow">成果管理</p>
        <h1>成果导出中心</h1>
        <span>从项目快照创建成果文件，并在这里跟踪生成、校验与交付状态。</span>
      </div>
      <div class="heading-actions">
        <el-button type="primary" :icon="Files" @click="openExportDialog">新建导出</el-button>
      </div>
    </header>

    <section class="export-stats" aria-label="导出概览">
      <article v-for="stat in stats" :key="stat.label">
        <span>{{ stat.label }}</span>
        <strong>{{ stat.value }}</strong>
        <small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="active-task" :class="{ empty: !primaryTaskView }" aria-label="当前导出">
      <div class="active-task-icon"><Timer v-if="primaryTaskView && isRunning(primaryTaskView)" /><CircleCheck v-else /></div>
      <div class="active-task-copy">
        <p>{{ activeTaskLabel }}</p>
        <h2>{{ primaryTaskView?.project || '当前没有进行中的导出任务' }}</h2>
        <span>{{ primaryTaskView ? primaryTaskView.stage : activeTaskEstimate }}</span>
      </div>
      <div v-if="primaryTaskView" class="active-task-progress">
        <div><strong>{{ primaryTaskView.progress }}%</strong><span>{{ activeTaskEstimate }}</span></div>
        <el-progress :percentage="primaryTaskView.progress" :status="primaryTaskView.apiStatus === 'failed' ? 'exception' : undefined" :show-text="false" />
      </div>
      <el-button v-if="primaryTaskView" plain @click="handleActiveTaskDetail">{{ flowTask && flowDetailVisible ? '收起详情' : '查看详情' }}</el-button>
      <el-button v-else class="empty-task-action" type="primary" plain @click="handleCreateTask">创建任务</el-button>
    </section>

    <section v-if="showFlowPanel" class="flow-console" aria-labelledby="flow-console-title">
      <header class="flow-console-header">
        <div>
          <p class="eyebrow">导出详情</p>
          <h2 id="flow-console-title">{{ project?.project_name || '正在创建导出任务' }}</h2>
          <p class="flow-message">{{ flow.message }}</p>
        </div>
        <div class="flow-header-actions">
          <el-tag class="flow-status" :type="flowStatusType" effect="light" round>{{ flowStatusLabel }}</el-tag>
        </div>
      </header>

      <div class="flow-context">
        <span><FolderOpened /> 项目：{{ project?.project_name || '等待项目创建' }}</span>
        <span>项目 ID：{{ projectId || '—' }}</span>
        <span>快照：{{ project?.current_version ? `v${project.current_version}` : '等待固化' }}</span>
        <span v-if="flowTask">任务 ID：{{ flowTask.id }}</span>
        <el-tag size="small" effect="plain">教学成果包</el-tag>
      </div>

      <ol class="flow-steps">
        <li v-for="(item, index) in flowSteps" :key="item.title" :class="flowStepState(index)">
          <span class="flow-step-index">
            <CircleCheck v-if="flowStepState(index) === 'complete'" />
            <span v-else>{{ index + 1 }}</span>
          </span>
          <span class="flow-step-copy"><strong>{{ item.title }}</strong><small>{{ item.detail }}</small></span>
        </li>
      </ol>

      <div v-if="flow.error" class="inline-error" role="alert"><Warning /><span>{{ flow.error }}</span></div>
      <div v-if="flow.precheck" class="precheck-strip" :class="{ failed: !flow.precheck.passed }">
        <DocumentChecked />
        <div><strong>{{ flow.precheck.passed ? '导出预检通过' : '导出预检未通过' }}</strong><span>{{ flow.precheck.warnings?.length || 0 }} 条提示 · {{ flow.precheck.errors?.length || 0 }} 条错误</span></div>
      </div>
      <div v-if="flowTask && canDownload(flowTask)" class="flow-delivery-strip">
        <div><strong>成果文件已就绪</strong><span>可预览、查看质量报告或下载到本地</span></div>
        <div class="flow-task-actions">
          <el-button text type="primary" @click="openPreview(flowTask)"><View /> 在线预览</el-button>
          <el-button text type="primary" @click="openQualityReport(flowTask)"><DocumentChecked /> 质量报告</el-button>
          <el-button type="primary" @click="download(flowTask)"><Download /> 下载成果</el-button>
        </div>
      </div>
      <small class="flow-footnote">导出基于当前不可变快照执行，任务完成后仍可从下方任务记录查看成果。</small>
    </section>

    <section class="quality-card">
      <div class="quality-card-heading">
        <div class="quality-title"><CircleCheck /><div><strong>最近一次导出质量</strong><span>{{ latestCompletedTask ? `${latestCompletedTask.project} · ${latestCompletedTask.version}` : '完成任务后显示服务端报告' }}</span></div></div>
        <el-button text type="primary" :disabled="!latestCompletedTask" @click="openLatestQualityReport">查看完整报告</el-button>
      </div>
      <div v-if="latestCompletedTask" class="quality-meta"><span><CircleCheck /> 任务状态：{{ latestCompletedTask.status }}</span><span><Files /> 文件大小：{{ latestCompletedTask.size }}</span><span><DocumentChecked /> 质量报告：{{ latestCompletedTask.quality }}</span></div>
      <el-empty v-else :image-size="46" description="暂无已完成的导出任务" />
    </section>

    <section class="history-section" aria-labelledby="history-title">
      <header class="history-header">
        <div><p class="eyebrow">任务记录</p><h2 id="history-title">导出任务</h2><span>查看当前账号的生成进度、质量状态和成果交付记录。</span></div>
        <div class="history-controls"><el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索项目、格式或版本" /><el-button :icon="Refresh" :loading="loading" @click="loadTasks">刷新</el-button></div>
      </header>
      <el-tabs v-model="activeTab" class="history-tabs">
        <el-tab-pane v-for="tab in tabs" :key="tab" :label="tab" :name="tab" />
      </el-tabs>

      <div v-if="pageError" class="inline-error history-error" role="alert"><Warning /><span>{{ pageError }}</span><el-button text type="primary" @click="loadTasks">重试</el-button></div>
      <el-table v-loading="loading" :data="filteredTasks" data-testid="export-task-list" class="task-table" row-key="id">
        <el-table-column label="项目与版本" min-width="270">
          <template #default="{ row }"><div class="project-cell"><strong>{{ row.project }}</strong><span>{{ row.subject }} · {{ row.version }} · {{ row.time }}</span></div></template>
        </el-table-column>
        <el-table-column label="格式" width="110"><template #default="{ row }"><span class="format-label">{{ row.format }}</span></template></el-table-column>
        <el-table-column label="生成进度" min-width="190"><template #default="{ row }"><div class="progress-cell"><el-progress :percentage="row.progress" :status="row.apiStatus === 'failed' ? 'exception' : undefined" :show-text="false" /><span>{{ row.progress }}%</span></div></template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="质量" width="110"><template #default="{ row }"><span class="quality-label">{{ row.quality }}</span></template></el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button text type="primary" @click="openTaskDetail(row)">详情</el-button>
              <el-button text type="primary" :disabled="!canDownload(row)" @click="openPreview(row)">预览</el-button>
              <el-button text type="primary" :disabled="!canDownload(row)" @click="openQualityReport(row)">报告</el-button>
              <el-button text type="primary" :disabled="!canDownload(row)" @click="download(row)">下载</el-button>
              <el-button v-if="isRunning(row)" text type="danger" @click="cancel(row)">取消</el-button>
              <el-button v-else-if="row.apiStatus === 'failed'" text type="primary" @click="retry(row)">重试</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !pageError && filteredTasks.length === 0" :image-size="64" description="还没有符合条件的导出任务" />
    </section>

    <el-dialog v-model="exportDialogVisible" title="创建导出任务" width="460px" class="export-dialog">
      <el-form label-position="top">
        <el-form-item label="项目 ID"><el-input v-model="exportForm.project_id" placeholder="请输入已保存项目的 ID" /></el-form-item>
        <el-form-item label="导出格式"><el-select v-model="exportForm.export_type" style="width: 100%" @change="clearPrecheck"><el-option label="PowerPoint 课件（PPTX）" value="pptx" /><el-option label="Word 教案（DOCX）" value="word" /><el-option label="教学成果包（ZIP）" value="package" /></el-select></el-form-item>
        <el-form-item label="快照版本"><el-input v-model="exportForm.snapshot_version" placeholder="运行预检时自动保存不可变快照" @input="clearPrecheck" /></el-form-item>
        <el-form-item label="模板版本"><el-input v-model="exportForm.template_version" placeholder="例如 zh-teaching-v1" @input="clearPrecheck" /></el-form-item>
        <el-form-item label="互动内容处理"><el-radio-group v-model="exportForm.interaction_mode" @change="clearPrecheck"><el-radio value="static">静态截图</el-radio><el-radio value="link">访问链接</el-radio><el-radio value="package">随成果包附带</el-radio></el-radio-group></el-form-item>
        <el-form-item label="页码范围"><el-input v-model="exportForm.page_range" placeholder="all 或 1-6" @input="clearPrecheck" /></el-form-item>
        <el-form-item><el-checkbox v-model="exportForm.header_enabled" @change="clearPrecheck">添加页眉页脚</el-checkbox></el-form-item>
        <template v-if="exportForm.header_enabled"><el-form-item label="页眉"><el-input v-model="exportForm.header_text" placeholder="可选" @input="clearPrecheck" /></el-form-item><el-form-item label="页脚"><el-input v-model="exportForm.footer_text" placeholder="可选" @input="clearPrecheck" /></el-form-item></template>
        <el-form-item label="教师备注"><el-input v-model="exportForm.teacher_notes" type="textarea" :rows="2" placeholder="可选，会随导出配置保存" @input="clearPrecheck" /></el-form-item>
      </el-form>
      <div v-if="precheck" class="dialog-precheck" :class="{ failed: !precheck.passed }"><strong>{{ precheck.passed ? '预检通过' : '预检未通过' }}</strong><span>{{ precheck.warnings?.length || 0 }} 条提示 · {{ precheck.errors?.length || 0 }} 条错误</span></div>
      <template #footer><el-button @click="runPrecheck">运行预检</el-button><el-button type="primary" @click="submitExport">创建导出</el-button></template>
    </el-dialog>

    <el-dialog v-model="taskDetailVisible" title="任务详情" width="520px" class="detail-dialog">
      <div class="detail-grid"><div><span>成果名称</span><strong>{{ taskDetailView.title }}</strong></div><div><span>状态</span><el-tag :type="statusTagType(taskDetailView.status)" effect="plain">{{ taskDetailView.status }}</el-tag></div><div><span>格式 / 版本</span><strong>{{ taskDetailView.format }} · {{ taskDetailView.version }}</strong></div><div><span>生成进度</span><strong>{{ taskDetailView.progress }}%</strong></div><div><span>任务创建</span><strong>{{ taskDetailView.createdAt }}</strong></div><div><span>任务完成</span><strong>{{ taskDetailView.completedAt }}</strong></div><div><span>项目 ID</span><strong>{{ taskDetailView.projectId }}</strong></div><div><span>数据来源</span><strong>{{ taskDetailView.source }}</strong></div></div><div class="detail-stage"><Timer /><span>{{ taskDetailView.stage }}</span></div>
      <template #footer><el-button @click="taskDetailVisible = false">关闭</el-button><el-button type="primary" :disabled="!canDownload(taskDetailRow)" @click="download(taskDetailRow)">下载成果</el-button></template>
    </el-dialog>

    <el-dialog v-model="reportVisible" title="导出质量报告" width="620px" class="quality-dialog">
      <div class="report-summary"><div><span>成果</span><strong>{{ qualityReportView.title }}</strong><small>{{ qualityReportView.marker }}</small></div><div class="report-score"><el-progress type="circle" :percentage="qualityReportView.score" :status="qualityScoreStatus" :width="72" /><el-tag :type="qualityTagType" effect="plain">{{ qualityReportView.conclusion }}</el-tag></div></div>
      <div class="report-items"><div v-for="item in qualityReportView.items" :key="item.name" class="report-item"><CircleCheck v-if="reportPassed(item.result)" /><CircleClose v-else /><div><strong>{{ item.name }}</strong><span>{{ item.detail || item.result }}</span></div><el-tag size="small" :type="reportPassed(item.result) ? 'success' : 'warning'" effect="plain">{{ item.result }}</el-tag></div><el-empty v-if="qualityReportView.items.length === 0" :image-size="48" description="服务端暂未返回检查明细" /></div>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="`${taskDetailRow?.project || '成果'} · 在线预览`" width="860px" class="preview-dialog" destroy-on-close>
      <iframe v-if="previewUrl" :src="previewUrl" title="导出成果预览" class="preview-frame" />
      <el-empty v-else description="没有可用的预览地址" />
    </el-dialog>
  </main>
</template>

<style scoped>
.export-page { width: min(1220px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 72px; color: var(--zh-text-primary); }
.export-heading, .flow-console-header, .history-header, .quality-card-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.eyebrow { margin: 0 0 8px; color: var(--zh-text-theme); font-size: 11px; font-weight: 700; letter-spacing: .12em; }
.export-heading h1 { margin: 0; font-size: clamp(28px, 3vw, 36px); line-height: 1.15; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.export-heading > div:first-child > span, .history-header > div:first-child > span { display: block; max-width: 620px; margin-top: 10px; color: var(--zh-text-secondary); font-size: 14px; line-height: 1.65; }
.heading-actions, .history-controls, .table-actions, .flow-task-actions { display: flex; align-items: center; gap: 10px; }
.flow-console { margin-top: 12px; padding: 24px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius16); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }
.flow-console-header { align-items: flex-start; }
.flow-console-header h2 { margin: 0; font-size: 20px; letter-spacing: var(--zh-tracking-tight); }
.flow-message { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.6; }
.flow-status { flex: none; font-weight: 600; }
.flow-header-actions { display: flex; align-items: center; gap: 8px; }
.flow-context { display: flex; flex-wrap: wrap; align-items: center; gap: 18px; margin-top: 20px; padding: 11px 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-capsule); font-size: 12px; }
.flow-context span { display: inline-flex; align-items: center; gap: 5px; }
.flow-context svg { width: 14px; color: var(--zh-text-theme); }
.flow-steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 22px 0 0; padding: 0; list-style: none; }
.flow-steps li { position: relative; display: flex; gap: 10px; min-width: 0; padding: 14px 12px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-capsule); transition: border-color 200ms ease, background 200ms ease, transform 200ms ease; }
.flow-steps li.current { border-color: var(--zh-line-theme); background: var(--zh-background-option-on); transform: translateY(-2px); }
.flow-steps li.complete { border-color: color-mix(in srgb, var(--zh-green) 35%, var(--zh-line-border)); }
.flow-step-index { display: grid; flex: none; place-items: center; width: 24px; height: 24px; border-radius: 50%; color: var(--zh-text-caption); background: var(--zh-background-light); font: 600 12px var(--zh-font-number); }
.flow-steps li.current .flow-step-index { color: var(--zh-text-white); background: var(--zh-theme-primary); }
.flow-steps li.complete .flow-step-index { color: var(--zh-green); background: color-mix(in srgb, var(--zh-green) 12%, transparent); }
.flow-step-index svg { width: 16px; }
.flow-step-copy { display: grid; gap: 3px; min-width: 0; }
.flow-step-copy strong { font-size: 13px; font-weight: 600; }
.flow-step-copy small { color: var(--zh-text-caption); font-size: 11px; line-height: 1.45; }
.inline-error { display: flex; align-items: center; gap: 8px; margin-top: 14px; padding: 11px 13px; border: 1px solid color-mix(in srgb, var(--zh-red) 30%, var(--zh-line-border)); border-radius: var(--zh-radius8); color: var(--zh-red); background: var(--zh-danger-background); font-size: 12px; }
.inline-error svg { width: 15px; flex: none; }
.history-error .el-button { margin-left: auto; }
.precheck-strip { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 12px; margin-top: 14px; padding: 12px 14px; border: 1px solid color-mix(in srgb, var(--zh-green) 30%, var(--zh-line-border)); border-radius: var(--zh-radius8); background: var(--zh-background-capsule); }
.precheck-strip > svg { width: 20px; color: var(--zh-green); }
.precheck-strip.failed { border-color: color-mix(in srgb, var(--zh-red) 35%, var(--zh-line-border)); }
.precheck-strip.failed > svg { color: var(--zh-red); }
.precheck-strip strong, .flow-delivery-strip strong { display: block; font-size: 13px; font-weight: 600; }
.precheck-strip span, .flow-delivery-strip span { display: block; margin-top: 3px; color: var(--zh-text-caption); font-size: 11px; }
.flow-delivery-strip { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-top: 14px; padding: 12px 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.flow-task-actions { justify-content: flex-end; }
.flow-footnote { display: block; margin-top: 13px; color: var(--zh-text-caption); font-size: 11px; }
.export-stats { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 30px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); }
.export-stats article { position: relative; display: grid; min-height: 118px; padding: 20px 22px; }
.export-stats article + article::before { position: absolute; top: 20px; bottom: 20px; left: 0; width: 1px; background: var(--zh-line-parting); content: ''; }
.export-stats span { color: var(--zh-text-secondary); font-size: 12px; }
.export-stats strong { margin: 9px 0 3px; font: 600 28px var(--zh-font-number); font-variant-numeric: tabular-nums; letter-spacing: -.04em; }
.export-stats small { color: var(--zh-text-caption); font-size: 11px; }
.active-task { display: grid; grid-template-columns: auto minmax(200px, 1.2fr) minmax(260px, 1fr) auto; align-items: center; gap: 18px; margin-top: 12px; padding: 18px 22px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius12); background: var(--zh-theme-primary); color: var(--zh-text-white); box-shadow: 0 12px 28px color-mix(in srgb, var(--zh-theme-primary) 22%, transparent); }
.active-task.empty { grid-template-columns: auto minmax(0, 1fr) auto; border-color: var(--zh-line-border); color: var(--zh-text-primary); background: var(--zh-background-capsule); box-shadow: none; }
.active-task-icon { display: grid; place-items: center; width: 44px; height: 44px; border-radius: var(--zh-radius10); color: var(--zh-text-white); background: color-mix(in srgb, var(--zh-text-white) 16%, transparent); }
.active-task.empty .active-task-icon { color: var(--zh-green); background: color-mix(in srgb, var(--zh-green) 12%, transparent); }
.active-task-icon svg { width: 21px; }
.active-task-copy { min-width: 0; }
.active-task-copy p { margin: 0; color: color-mix(in srgb, var(--zh-text-white) 72%, transparent); font-size: 12px; }
.active-task.empty .active-task-copy p { color: var(--zh-text-caption); }
.active-task-copy h2 { overflow: hidden; margin: 5px 0 4px; font-size: 16px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.active-task-copy span { display: block; overflow: hidden; color: color-mix(in srgb, var(--zh-text-white) 74%, transparent); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.active-task.empty .active-task-copy span { color: var(--zh-text-secondary); }
.active-task-progress > div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.active-task-progress strong { font: 600 22px var(--zh-font-number); font-variant-numeric: tabular-nums; }
.active-task-progress span { color: color-mix(in srgb, var(--zh-text-white) 72%, transparent); font-size: 11px; }
.active-task :deep(.el-progress-bar__outer) { background: color-mix(in srgb, var(--zh-text-white) 22%, transparent); }
.active-task :deep(.el-progress-bar__inner) { background: var(--zh-text-white); }
.active-task > .el-button { color: var(--zh-text-white); border-color: color-mix(in srgb, var(--zh-text-white) 45%, transparent); background: transparent; }
.active-task > .el-button:hover, .active-task > .el-button:focus-visible { color: var(--zh-theme-primary); border-color: var(--zh-text-white); background: var(--zh-text-white); }
.active-task.empty > .el-button { color: var(--zh-text-theme); border-color: var(--zh-line-theme20); }
.active-task.empty > .empty-task-action { width: min(100%, 136px); min-height: 38px; justify-self: end; }
.quality-card { margin-top: 30px; padding: 20px 22px 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); }
.quality-title { display: flex; align-items: center; gap: 11px; }
.quality-title > svg { width: 22px; color: var(--zh-green); }
.quality-title strong, .quality-title span { display: block; }
.quality-title strong { font-size: 15px; font-weight: 600; }
.quality-title span { margin-top: 4px; color: var(--zh-text-caption); font-size: 12px; }
.quality-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--zh-line-parting); color: var(--zh-text-secondary); font-size: 12px; }
.quality-meta span { display: flex; align-items: center; gap: 7px; }
.quality-meta svg { width: 15px; color: var(--zh-green); }
.quality-card :deep(.el-empty) { padding: 20px 0 5px; }
.history-section { margin-top: 34px; }
.history-header { align-items: flex-end; }
.history-header h2 { margin: 0; font-size: 22px; letter-spacing: var(--zh-tracking-tight); }
.history-controls .el-input { width: 240px; }
.history-tabs { margin-top: 20px; }
.history-tabs :deep(.el-tabs__header) { margin-bottom: 13px; }
.history-tabs :deep(.el-tabs__item) { color: var(--zh-text-secondary); font-size: 13px; }
.history-tabs :deep(.el-tabs__item.is-active) { color: var(--zh-text-theme); font-weight: 600; }
.task-table { overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); }
.task-table :deep(.el-table__inner-wrapper::before) { display: none; }
.task-table :deep(.el-table__header th) { height: 44px; color: var(--zh-text-caption); background: var(--zh-background-light); font-size: 11px; font-weight: 600; }
.task-table :deep(.el-table__row td) { height: 68px; border-bottom-color: var(--zh-line-parting); }
.project-cell, .progress-cell { display: grid; gap: 4px; }
.project-cell strong { overflow: hidden; color: var(--zh-text-primary); font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.project-cell span, .progress-cell span { color: var(--zh-text-caption); font-size: 11px; }
.format-label, .quality-label { color: var(--zh-text-secondary); font-size: 12px; }
.progress-cell { grid-template-columns: minmax(72px, 1fr) 35px; align-items: center; gap: 8px; }
.progress-cell :deep(.el-progress-bar__outer) { background: var(--zh-background-light-grey); }
.progress-cell span { text-align: right; font-family: var(--zh-font-number); }
.table-actions { justify-content: flex-start; gap: 2px; }
.table-actions :deep(.el-button) { padding: 5px 4px; font-size: 12px; }
.history-section > :deep(.el-empty) { padding: 42px 0; border: 1px dashed var(--zh-line-heavier); border-top: 0; border-radius: 0 0 var(--zh-radius12) var(--zh-radius12); }
.dialog-precheck { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-radius: var(--zh-radius8); color: var(--zh-green); background: color-mix(in srgb, var(--zh-green) 10%, transparent); font-size: 12px; }
.dialog-precheck.failed { color: var(--zh-red); background: var(--zh-danger-background); }
.dialog-precheck span { color: inherit; opacity: .8; }
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.detail-grid > div { display: grid; gap: 4px; padding-bottom: 10px; border-bottom: 1px solid var(--zh-line-parting); }
.detail-grid span { color: var(--zh-text-caption); font-size: 11px; }
.detail-grid strong { color: var(--zh-text-primary); font-size: 13px; font-weight: 500; }
.detail-stage { display: flex; align-items: center; gap: 8px; margin-top: 18px; padding: 11px 12px; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-light); font-size: 12px; }
.detail-stage svg { width: 15px; color: var(--zh-text-theme); }
.report-summary { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding-bottom: 18px; border-bottom: 1px solid var(--zh-line-parting); }
.report-summary > div:first-child { display: grid; gap: 4px; }
.report-summary span, .report-summary small { color: var(--zh-text-caption); font-size: 11px; }
.report-summary strong { font-size: 16px; font-weight: 600; }
.report-score { display: flex; align-items: center; gap: 14px; }
.report-items { display: grid; gap: 8px; margin-top: 16px; }
.report-item { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 9px; padding: 11px 12px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); }
.report-item > svg { width: 16px; color: var(--zh-green); }
.report-item > svg:not(:first-child) { color: var(--zh-orange); }
.report-item strong, .report-item span { display: block; }
.report-item strong { font-size: 13px; font-weight: 500; }
.report-item span { margin-top: 3px; color: var(--zh-text-caption); font-size: 11px; }
.preview-frame { display: block; width: 100%; height: min(66vh, 620px); border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.export-page :deep(.el-button:focus-visible), .export-page :deep(.el-input__wrapper:focus-within), .export-page :deep(.el-tabs__item:focus-visible) { outline: 2px solid var(--zh-line-theme); outline-offset: 2px; }
.export-page :deep(.el-button) { transition: background 200ms cubic-bezier(.4, 0, .2, 1), border-color 200ms ease, color 200ms ease, transform 150ms ease; }
.export-page :deep(.el-button:active) { transform: scale(.98); }

@media (max-width: 960px) {
  .flow-steps { grid-template-columns: repeat(3, 1fr); }
  .active-task { grid-template-columns: auto 1fr; }
  .active-task-progress { grid-column: 2; }
  .active-task > .el-button { grid-column: 2; justify-self: start; }
}
@media (max-width: 680px) {
  .export-page { width: min(100% - 28px, 1220px); padding-top: 26px; }
  .export-heading, .flow-console-header, .history-header, .quality-card-heading { align-items: stretch; flex-direction: column; }
  .heading-actions, .history-controls { justify-content: space-between; }
  .history-controls .el-input { width: 100%; }
  .flow-console { padding: 17px; }
  .flow-steps { grid-template-columns: 1fr; }
  .flow-context { align-items: flex-start; flex-direction: column; gap: 7px; }
  .export-stats { grid-template-columns: 1fr; }
  .export-stats article + article::before { top: 0; right: 20px; bottom: auto; left: 20px; width: auto; height: 1px; }
  .active-task { grid-template-columns: auto 1fr; padding: 16px; }
  .active-task-progress { grid-column: 1 / -1; }
  .active-task > .el-button { grid-column: 1 / -1; justify-self: stretch; }
  .quality-meta { grid-template-columns: 1fr; }
  .quality-card-heading .el-button { align-self: flex-start; padding-left: 0; }
  .flow-task-actions { align-items: stretch; flex-wrap: wrap; justify-content: flex-start; }
  .flow-delivery-strip { align-items: stretch; flex-direction: column; }
  .detail-grid { grid-template-columns: 1fr; }
  .task-table { overflow-x: auto; }
}
</style>
