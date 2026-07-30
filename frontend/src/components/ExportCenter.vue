<!--
  [数据交互说明]
  - 导入: 导出中心演示数据、Element Plus 组件
  - 输出: 教学成果导出任务与历史文件页面
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Download, Files, Refresh, Search, Warning } from '@element-plus/icons-vue'
import { EXPORT_PAGE } from '../config/teacherPages.config.js'
import { cancelExportTask, createExportPreviewUrl, createExportTask, downloadExportArtifact, getExportArtifact, getExportQualityReport, getExportTask, listExportTasks, precheckProjectExport, retryExportTask } from '../apis/teacher'

const keyword = ref('')
const activeTab = ref('全部任务')
const tabs = ['全部任务', '进行中', '已完成', '需要处理']
const tasks = ref([])
const loading = ref(false)
const exportDialogVisible = ref(false), reportVisible = ref(false), previewVisible = ref(false)
const exportForm = ref({ project_id: '', export_type: 'pdf', snapshot_version: '' })
const precheck = ref(null), qualityReport = ref(null), previewUrl = ref('')
const taskDetailVisible = ref(false), taskDetail = ref(null), taskDetailRow = ref(null)
let localPreviewUrl = ''
const normalizeTask = (task) => ({
  id: task.id, project: task.project_name || task.project?.project_name || task.file_name || '未命名项目',
  format: (task.export_type || task.format || '成果包').toUpperCase(), version: task.snapshot_version ? `v${task.snapshot_version}` : task.version || '—',
  time: task.created_at || task.time || '刚刚', status: ({ queued: '排队中', generating: '生成中', checking: '校验中', success: '成功', partial: '部分成功', failed: '失败', cancelled: '已取消' })[task.status] || task.status || '排队中',
  quality: task.quality_report ? '查看报告' : task.quality || '待校验', size: task.file_size_text || task.size || '—', fileStatus: task.file_status,
})
const testTasks = EXPORT_PAGE.tasks.map((task) => ({ ...task }))
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character])
const createTestArtifact = (row) => {
  const lessons = {
    'test-export-pythagorean': ['真实情境：如何测量梯子的斜边', '观察三组直角三角形边长', '拖动顶点验证 a²+b²=c²', '分层练习与课堂小结'],
    'test-export-classical': ['学习目标与学情分析', '从父亲背影切入文本细读', '品味动作描写与情感变化', '迁移写作与课后反思'],
    'test-export-photosynthesis': ['提出问题：绿叶在光下制造什么', '设置遮光与见光对照组', '脱色、滴加碘液并记录现象', '依据证据形成实验结论'],
  }
  const sections = lessons[row.id] || ['课程导入', '核心探究', '课堂练习', '学习评价']
  if (row.artifactType === 'json') {
    return {
      content: JSON.stringify({ title: row.project, subject: row.subject, version: row.version, generatedAt: '2026-07-29', sections, assets: ['实验步骤卡', '观察记录表', '评价量规'], quality: { structure: 'passed', copyright: 'passed', sensitiveContent: 'passed' } }, null, 2),
      mime: 'application/json;charset=utf-8',
      extension: 'json',
    }
  }
  if (row.artifactType === 'md') {
    return {
      content: `# ${row.project}\n\n- 学科：${row.subject}\n- 版本：${row.version}\n- 类型：前端测试成果\n\n## 教学目标\n\n引导学生在真实任务中提取关键信息，形成有依据的表达。\n\n## 教学流程\n\n${sections.map((section, index) => `${index + 1}. ${section}`).join('\n')}\n\n## 评价方式\n\n课堂观察、任务单与学生作品相结合。\n`,
      mime: 'text/markdown;charset=utf-8',
      extension: 'md',
    }
  }
  return {
    content: `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(row.project)}</title><style>body{margin:0;font-family:"Microsoft YaHei",sans-serif;color:#172033;background:#eef4ff}.deck{width:min(920px,calc(100% - 40px));margin:40px auto}.cover,.section{padding:48px;border-radius:20px;background:#fff;box-shadow:0 16px 42px #1d4ed81f}.cover{color:#fff;background:#2563eb}.cover small{opacity:.72}.cover h1{margin:16px 0 8px;font-size:42px}.section{margin-top:18px}.section span{color:#2563eb;font-weight:700}.section h2{margin:10px 0}.section p{color:#64748b;line-height:1.8}</style></head><body><main class="deck"><section class="cover"><small>${escapeHtml(row.subject)} · ${escapeHtml(row.version)}</small><h1>${escapeHtml(row.project)}</h1><p>可预览、可下载的前端测试成果</p></section>${sections.map((section, index) => `<section class="section"><span>0${index + 1}</span><h2>${escapeHtml(section)}</h2><p>围绕学习任务组织观察、探究、表达与评价活动，教师可根据课堂实际继续编辑。</p></section>`).join('')}</main></body></html>`,
    mime: 'text/html;charset=utf-8',
    extension: 'html',
  }
}
const createTestReport = (row) => ({
  成果名称: row.project,
  测试标识: '前端本地测试成果',
  校验结论: '通过',
  总分: 96,
  检查项: [
    { 名称: '页面结构完整', 结果: '通过' },
    { 名称: '素材授权有效', 结果: '通过' },
    { 名称: '敏感信息检查', 结果: '通过' },
    { 名称: '导出文件可读取', 结果: '通过' },
  ],
})
const loadTasks = async () => {
  loading.value = true
  try {
    const status = activeTab.value === '进行中' ? 'generating' : activeTab.value === '已完成' ? 'success' : undefined
    const result = await listExportTasks({ status, page: 1, size: 50 })
    const records = result?.data?.records || result?.data?.list || result?.data?.items || result?.records || []
    tasks.value = [...testTasks, ...records.map(normalizeTask)]
  } catch { tasks.value = [...testTasks] } finally { loading.value = false }
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

const detailValue = (...keys) => {
  const source = taskDetail.value || {}
  for (const key of keys) {
    const value = source[key]
    if (value !== undefined && value !== null && value !== '') return value
  }
  return '—'
}

const taskDetailView = computed(() => {
  const row = taskDetailRow.value || {}
  const rawStatus = detailValue('状态', 'status')
  const statusMap = { queued: '排队中', generating: '生成中', checking: '校验中', success: '成功', partial: '部分成功', failed: '失败', cancelled: '已取消' }
  const actions = detailValue('可用操作', 'available_actions')
  return {
    title: detailValue('成果名称', 'project_name', 'file_name') === '—' ? row.project || '未命名成果' : detailValue('成果名称', 'project_name', 'file_name'),
    format: detailValue('成果类型', 'export_type', 'format') === '—' ? row.format || '成果包' : String(detailValue('成果类型', 'export_type', 'format')).toUpperCase(),
    subject: detailValue('学科', 'subject'),
    version: detailValue('版本', 'snapshot_version', 'version') === '—' ? row.version || '—' : detailValue('版本', 'snapshot_version', 'version'),
    status: rawStatus === '—' ? row.status || '未知' : statusMap[rawStatus] || rawStatus,
    pages: detailValue('页面或章节数', 'page_count', 'pages', 'chapter_count'),
    createdAt: detailValue('创建时间', 'created_at', 'create_at'),
    size: detailValue('文件大小', 'file_size_text', 'size'),
    source: detailValue('数据来源', 'data_source', 'source'),
    actions: Array.isArray(actions) ? actions : actions === '—' ? [] : [actions],
  }
})

const taskDetailStatusType = computed(() => ({
  成功: 'success',
  部分成功: 'warning',
  失败: 'danger',
  已取消: 'info',
})[taskDetailView.value.status] || 'info')

const parseReportValue = (value) => {
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

const qualityReportView = computed(() => {
  const outer = qualityReport.value || {}
  const nested = parseReportValue(outer.quality_report)
  const source = nested && typeof nested === 'object' ? nested : outer
  const pick = (...keys) => {
    for (const key of keys) {
      const value = source[key]
      if (value !== undefined && value !== null && value !== '') return value
    }
    return '—'
  }
  const rawItems = pick('检查项', 'checks', 'items', 'results')
  const items = (Array.isArray(rawItems) ? rawItems : []).map((item, index) => ({
    name: item?.名称 || item?.name || item?.title || `检查项 ${index + 1}`,
    result: item?.结果 || item?.result || item?.status || '待确认',
    detail: item?.说明 || item?.detail || item?.message || '',
  }))
  const rawScore = Number(pick('总分', 'score', 'total_score'))
  const score = Number.isFinite(rawScore) ? Math.min(100, Math.max(0, rawScore)) : 0
  return {
    title: pick('成果名称', 'project_name', 'title') === '—' ? taskDetailRow.value?.project || '未命名成果' : pick('成果名称', 'project_name', 'title'),
    marker: pick('测试标识', 'test_marker', 'report_id'),
    conclusion: pick('校验结论', 'conclusion', 'status'),
    score,
    items,
  }
})

const reportPassed = (result) => ['通过', 'passed', 'pass', 'success', 'ok'].includes(String(result).toLowerCase())
const qualityScoreStatus = computed(() => qualityReportView.value.score >= 80 ? 'success' : qualityReportView.value.score >= 60 ? 'warning' : 'exception')
const qualityTagType = computed(() => {
  const conclusion = String(qualityReportView.value.conclusion).toLowerCase()
  if (conclusion.includes('失败') || conclusion.includes('不通过') || conclusion.includes('failed')) return 'danger'
  if (conclusion.includes('需处理') || conclusion.includes('警告') || conclusion.includes('warning')) return 'warning'
  return qualityReportView.value.score >= 80 ? 'success' : qualityReportView.value.score >= 60 ? 'warning' : 'danger'
})

const activeExportTask = {
  id: 'active-export-fraction',
  isTest: true,
  project: '《分数的初步认识》教学成果包',
  format: '教学成果包',
  subject: '三年级数学',
  version: 'v1.4',
  status: '生成中',
  pages: 8,
  time: '今天 10:26',
  size: '生成中',
  actions: ['查看生成进度'],
}

const openActiveTaskDetail = () => openTaskDetail(activeExportTask)
const openLatestQualityReport = () => {
  qualityReport.value = {
    成果名称: '最近项目快照 v1.4',
    测试标识: '导出前自动校验',
    校验结论: '需处理 1 项',
    总分: 92,
    检查项: [
      { 名称: '页面结构完整', 结果: '通过' },
      { 名称: '素材授权有效', 结果: '通过' },
      { 名称: '字体兼容性', 结果: '需处理', 说明: '1 个字体将在导出时自动替换' },
      { 名称: '敏感信息检查', 结果: '通过' },
    ],
  }
  reportVisible.value = true
}

const taskActionAvailable = (action) => taskDetailView.value.actions.includes(action)

/** 模拟创建标准格式导出任务。 */
const createExport = () => openExportDialog()
const download = async (row) => {
  if (row.isTest) {
    const artifact = createTestArtifact(row)
    const url = URL.createObjectURL(new Blob([artifact.content], { type: artifact.mime }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${row.project}-${row.version}.${artifact.extension}`
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success('测试成果已下载')
    return
  }
  if (!row.id) return ElMessage.info('当前任务暂不支持下载')
  try {
    if (row.fileStatus === 'expired' || row.status === '已过期') { await retryExportTask(row.id); ElMessage.success('已重新提交生成任务'); await loadTasks(); return }
    const result = await downloadExportArtifact(row.id)
    const url = result?.data?.download_url || result?.download_url
    if (url) window.open(url, '_blank', 'noopener'); else ElMessage.warning('文件尚未生成完成')
  } catch { ElMessage.error('操作未成功，请稍后重试') }
}
const openExportDialog = () => { exportForm.value = { project_id: '', export_type: 'pdf', snapshot_version: '' }; precheck.value = null; exportDialogVisible.value = true }
const runPrecheck = async () => { if (!exportForm.value.project_id) return ElMessage.warning('请输入项目 ID'); try { precheck.value = (await precheckProjectExport(exportForm.value.project_id, { export_type: exportForm.value.export_type, snapshot_version: exportForm.value.snapshot_version || undefined }))?.data || null } catch (error) { ElMessage.error(error?.message || '导出预检失败') } }
const submitExport = async () => { if (!exportForm.value.project_id) return ElMessage.warning('请输入项目 ID'); try { await createExportTask({ ...exportForm.value, snapshot_version: Number(exportForm.value.snapshot_version) || undefined }); exportDialogVisible.value = false; ElMessage.success('导出任务已创建'); await loadTasks() } catch (error) { ElMessage.error(error?.message || '导出任务创建失败') } }
const cancelTask = async (row) => { try { await cancelExportTask(row.id); ElMessage.success('任务已取消'); await loadTasks() } catch (error) { ElMessage.error(error?.message || '任务取消失败') } }
const openQualityReport = async (row) => {
  if (row.isTest) { qualityReport.value = createTestReport(row); reportVisible.value = true; return }
  try { qualityReport.value = (await getExportQualityReport(row.id))?.data || null; reportVisible.value = true } catch (error) { ElMessage.error(error?.message || '质量报告加载失败') }
}
const previewArtifact = async (row) => {
  if (row.isTest) {
    const artifact = createTestArtifact(row)
    const content = row.artifactType === 'html' ? artifact.content : `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><style>body{margin:0;padding:36px;font:15px/1.75 ui-monospace,monospace;color:#24324a;background:#f7f9fc}pre{max-width:920px;margin:auto;padding:30px;white-space:pre-wrap;border:1px solid #dbe3ef;border-radius:14px;background:#fff}</style></head><body><pre>${escapeHtml(artifact.content)}</pre></body></html>`
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl)
    localPreviewUrl = URL.createObjectURL(new Blob([content], { type: 'text/html;charset=utf-8' }))
    previewUrl.value = localPreviewUrl
    previewVisible.value = true
    return
  }
  try { const artifact = (await getExportArtifact(row.id))?.data || {}; const result = await createExportPreviewUrl(artifact.id || artifact.artifact_id || row.id); previewUrl.value = result?.data?.preview_url || result?.preview_url || ''; if (!previewUrl.value) throw new Error('预览地址未返回'); previewVisible.value = true } catch (error) { ElMessage.error(error?.message || '预览地址获取失败') }
}
const openTaskDetail = async (row) => {
  taskDetailRow.value = row
  if (row.isTest) {
    taskDetail.value = { 成果名称: row.project, 成果类型: row.format, 学科: row.subject, 版本: row.version, 状态: row.status, 页面或章节数: row.pages, 创建时间: row.time, 文件大小: row.size, 数据来源: '前端本地测试数据', 可用操作: row.actions || ['在线预览', '质量报告', '下载文件'] }
    taskDetailVisible.value = true
    return
  }
  if (!row.id) return
  try { taskDetail.value = (await getExportTask(row.id))?.data || null; taskDetailVisible.value = true } catch (error) { ElMessage.error(error?.message || '任务详情加载失败') }
}
watch(activeTab, loadTasks)
onMounted(loadTasks)
onBeforeUnmount(() => { if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl) })
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
      <el-button @click="openActiveTaskDetail">查看详情</el-button>
    </section>

    <section class="quality-panel">
      <header><div><el-icon><CircleCheck /></el-icon><span><strong>导出前质量校验</strong><small>最近项目快照 v1.4</small></span></div><el-button type="primary" link @click="openLatestQualityReport">查看完整报告</el-button></header>
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
        <el-table-column label="操作" width="176"><template #default="{ row }"><el-button type="primary" link @click="openTaskDetail(row)">详情</el-button><el-button type="primary" link :icon="row.status === '已过期' ? Refresh : Download" @click="download(row)">{{ row.status === '已过期' ? '重新生成' : '下载' }}</el-button></template></el-table-column>
        <template #empty><el-empty description="没有符合当前筛选条件的导出任务" /></template>
      </el-table>
    </section>
  </div>
    <el-dialog v-model="exportDialogVisible" title="配置导出任务" width="460px"><el-form label-position="top"><el-form-item label="项目 ID"><el-input v-model="exportForm.project_id" /></el-form-item><el-form-item label="导出格式"><el-select v-model="exportForm.export_type"><el-option label="PDF" value="pdf" /><el-option label="Word" value="word" /><el-option label="PowerPoint" value="ppt" /></el-select></el-form-item><el-form-item label="快照版本"><el-input v-model="exportForm.snapshot_version" /></el-form-item></el-form><div v-if="precheck" class="precheck-result"><strong>预检完成</strong><pre>{{ JSON.stringify(precheck, null, 2) }}</pre></div><template #footer><el-button @click="runPrecheck">运行预检</el-button><el-button type="primary" @click="submitExport">创建导出</el-button></template></el-dialog>
    <el-dialog
      v-model="reportVisible"
      class="quality-report-dialog"
      width="min(760px, 94vw)"
      align-center
      destroy-on-close
    >
      <template #header>
        <div class="task-detail-title">
          <span>完整质量报告</span>
          <small>导出前自动校验结果</small>
        </div>
      </template>
      <article v-if="qualityReport" class="quality-report-card">
        <header class="quality-report-summary">
          <div class="quality-report-emblem">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="quality-report-identity">
            <p>校验结论 · {{ qualityReportView.conclusion }}</p>
            <h2>{{ qualityReportView.title }}</h2>
            <span v-if="qualityReportView.marker !== '—'">{{ qualityReportView.marker }}</span>
          </div>
          <div class="quality-score">
            <el-progress
              type="circle"
              :percentage="qualityReportView.score"
              :width="92"
              :stroke-width="7"
              :status="qualityScoreStatus"
            >
              <template #default="{ percentage }">
                <strong>{{ percentage }}</strong>
                <small>总分</small>
              </template>
            </el-progress>
          </div>
        </header>

        <section class="quality-checks">
          <header>
            <div><span>检查明细</span><small>共 {{ qualityReportView.items.length }} 项</small></div>
            <el-tag :type="qualityTagType" effect="light">{{ qualityReportView.conclusion }}</el-tag>
          </header>
          <ul v-if="qualityReportView.items.length">
            <li v-for="(item, index) in qualityReportView.items" :key="`${item.name}-${index}`" :class="{ warning: !reportPassed(item.result) }">
              <span class="quality-check-icon">
                <el-icon><CircleCheck v-if="reportPassed(item.result)" /><Warning v-else /></el-icon>
              </span>
              <div>
                <strong>{{ item.name }}</strong>
                <small v-if="item.detail">{{ item.detail }}</small>
              </div>
              <el-tag :type="reportPassed(item.result) ? 'success' : 'warning'" effect="plain" size="small">{{ item.result }}</el-tag>
            </li>
          </ul>
          <el-empty v-else description="暂无检查项明细" :image-size="64" />
        </section>
      </article>
      <el-empty v-else description="暂无质量报告" :image-size="72" />
      <template #footer>
        <el-button type="primary" @click="reportVisible = false">完成</el-button>
      </template>
    </el-dialog>
    <el-dialog
      v-model="taskDetailVisible"
      class="task-detail-dialog"
      width="min(760px, 94vw)"
      align-center
      destroy-on-close
    >
      <template #header>
        <div class="task-detail-title">
          <span>导出任务详情</span>
          <small>查看成果信息与后续操作</small>
        </div>
      </template>
      <article v-if="taskDetail" class="task-detail-card">
        <header class="task-detail-hero">
          <div class="task-detail-file-icon"><el-icon><Files /></el-icon></div>
          <div class="task-detail-identity">
            <p>教学成果文件</p>
            <h2>{{ taskDetailView.title }}</h2>
            <div class="task-detail-meta">
              <span>{{ taskDetailView.format }}</span>
              <i aria-hidden="true"></i>
              <span>{{ taskDetailView.version }}</span>
            </div>
          </div>
          <el-tag :type="taskDetailStatusType" effect="light" size="large">
            <el-icon><Refresh v-if="taskDetailView.status === '生成中'" /><CircleCheck v-else /></el-icon>
            {{ taskDetailView.status }}
          </el-tag>
        </header>

        <section class="task-detail-metrics" aria-label="成果概览">
          <div>
            <span>学科</span>
            <strong>{{ taskDetailView.subject }}</strong>
          </div>
          <div>
            <span>页面或章节</span>
            <strong class="number">{{ taskDetailView.pages }}</strong>
          </div>
          <div>
            <span>文件大小</span>
            <strong class="number">{{ taskDetailView.size }}</strong>
          </div>
        </section>

        <section class="task-detail-info">
          <header><span>任务信息</span><small>文件生成与追溯记录</small></header>
          <dl>
            <div><dt>创建时间</dt><dd>{{ taskDetailView.createdAt }}</dd></div>
            <div><dt>数据来源</dt><dd>{{ taskDetailView.source }}</dd></div>
          </dl>
        </section>

        <section v-if="taskDetailView.actions.length" class="task-detail-capabilities">
          <span>可用能力</span>
          <div>
            <span v-for="action in taskDetailView.actions" :key="action">
              <el-icon><CircleCheck /></el-icon>{{ action }}
            </span>
          </div>
        </section>
      </article>
      <el-empty v-else description="暂无任务详情" :image-size="72" />
      <template #footer>
        <div class="task-detail-actions">
          <el-button @click="taskDetailVisible = false">关闭</el-button>
          <div v-if="taskDetailRow">
            <el-button v-if="taskActionAvailable('质量报告')" @click="openQualityReport(taskDetailRow)">质量报告</el-button>
            <el-button v-if="taskActionAvailable('在线预览')" @click="previewArtifact(taskDetailRow)">在线预览</el-button>
            <el-button v-if="taskActionAvailable('下载文件')" type="primary" :icon="Download" @click="download(taskDetailRow)">下载文件</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
    <el-dialog v-model="previewVisible" title="成果在线预览" width="min(1000px, 94vw)"><iframe v-if="previewUrl" :src="previewUrl" class="artifact-preview" title="导出成果预览" /></el-dialog>
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
.precheck-result{padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.precheck-result pre,.report-content{max-height:380px;overflow:auto;margin:8px 0 0;white-space:pre-wrap;font:12px/1.65 var(--zh-font-code)}.report-content{padding:16px;border-radius:var(--zh-radius8);background:var(--zh-background-light)}.artifact-preview{width:100%;height:min(70vh,720px);border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8)}

.task-detail-title { display: flex; flex-direction: column; gap: 3px; }
.task-detail-title span { color: var(--zh-text-primary); font-size: 20px; font-weight: 600; letter-spacing: var(--zh-tracking-tight); }
.task-detail-title small { color: var(--zh-text-caption); font-size: 12px; font-weight: 400; }
:deep(.task-detail-dialog) { overflow: hidden; border-radius: var(--zh-radius16); box-shadow: var(--zh-shadow3); }
:deep(.task-detail-dialog .el-dialog__header) { margin: 0; padding: 22px 26px 18px; border-bottom: 1px solid var(--zh-line-parting); }
:deep(.task-detail-dialog .el-dialog__headerbtn) { top: 15px; right: 18px; width: 40px; height: 40px; border-radius: var(--zh-radius8); transition: background 200ms ease, transform 150ms ease; }
:deep(.task-detail-dialog .el-dialog__headerbtn:hover) { background: var(--zh-background-weaken); }
:deep(.task-detail-dialog .el-dialog__headerbtn:active) { transform: scale(.96); }
:deep(.task-detail-dialog .el-dialog__body) { padding: 0; }
:deep(.task-detail-dialog .el-dialog__footer) { padding: 18px 26px 22px; border-top: 1px solid var(--zh-line-parting); }
.task-detail-card { padding: 24px 26px 26px; background: var(--zh-background-pop); }
.task-detail-hero { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 16px; }
.task-detail-file-icon { display: grid; place-items: center; width: 52px; height: 58px; border: 1px solid var(--zh-line-capsule); border-radius: var(--zh-radius10); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.task-detail-file-icon .el-icon { font-size: 24px; }
.task-detail-identity { min-width: 0; }
.task-detail-identity p { margin: 0 0 3px; color: var(--zh-text-theme); font-size: 11px; font-weight: 600; letter-spacing: var(--zh-tracking-wide); }
.task-detail-identity h2 { overflow: hidden; margin: 0; color: var(--zh-text-primary); font-size: 19px; font-weight: 600; letter-spacing: var(--zh-tracking-tight); line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.task-detail-meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; color: var(--zh-text-caption); font-size: 12px; }
.task-detail-meta i { width: 3px; height: 3px; border-radius: 50%; background: currentColor; }
.task-detail-hero :deep(.el-tag) { display: inline-flex; align-items: center; gap: 5px; border-radius: var(--zh-radius8); font-weight: 600; }
.task-detail-metrics { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 24px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-light); }
.task-detail-metrics > div { display: flex; min-width: 0; flex-direction: column; gap: 6px; padding: 16px 18px; }
.task-detail-metrics > div + div { border-left: 1px solid var(--zh-line-border); }
.task-detail-metrics span { color: var(--zh-text-caption); font-size: 11px; }
.task-detail-metrics strong { overflow: hidden; color: var(--zh-text-primary); font-size: 15px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.task-detail-metrics strong.number { font-family: var(--zh-font-number); font-variant-numeric: tabular-nums; }
.task-detail-info { margin-top: 22px; }
.task-detail-info > header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.task-detail-info > header span { color: var(--zh-text-primary); font-size: 13px; font-weight: 600; }
.task-detail-info > header small { color: var(--zh-text-caption); font-size: 11px; }
.task-detail-info dl { display: grid; grid-template-columns: 1fr 1fr; margin: 0; border-top: 1px solid var(--zh-line-parting); }
.task-detail-info dl > div { display: grid; grid-template-columns: 82px minmax(0, 1fr); gap: 10px; padding: 14px 0; border-bottom: 1px solid var(--zh-line-parting); }
.task-detail-info dl > div:nth-child(2n) { padding-left: 20px; }
.task-detail-info dt { color: var(--zh-text-caption); font-size: 12px; }
.task-detail-info dd { overflow: hidden; margin: 0; color: var(--zh-text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; text-overflow: ellipsis; white-space: nowrap; }
.task-detail-capabilities { display: flex; align-items: flex-start; gap: 18px; margin-top: 20px; padding: 14px 16px; border-radius: var(--zh-radius10); background: var(--zh-background-weaken); }
.task-detail-capabilities > span { flex: 0 0 auto; padding-top: 2px; color: var(--zh-text-theme); font-size: 12px; font-weight: 600; }
.task-detail-capabilities > div { display: flex; flex-wrap: wrap; gap: 8px 16px; }
.task-detail-capabilities > div span { display: inline-flex; align-items: center; gap: 5px; color: var(--zh-text-secondary); font-size: 12px; }
.task-detail-capabilities .el-icon { color: var(--zh-green); }
.task-detail-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.task-detail-actions > div { display: flex; gap: 10px; }
.task-detail-actions :deep(.el-button) { margin-left: 0; transition: transform 150ms ease, background 200ms ease, border-color 200ms ease; }
.task-detail-actions :deep(.el-button:active) { transform: scale(.98); }

:deep(.quality-report-dialog) { overflow: hidden; border-radius: var(--zh-radius16); box-shadow: var(--zh-shadow3); }
:deep(.quality-report-dialog .el-dialog__header) { margin: 0; padding: 22px 26px 18px; border-bottom: 1px solid var(--zh-line-parting); }
:deep(.quality-report-dialog .el-dialog__headerbtn) { top: 15px; right: 18px; width: 40px; height: 40px; border-radius: var(--zh-radius8); transition: background 200ms ease, transform 150ms ease; }
:deep(.quality-report-dialog .el-dialog__headerbtn:hover) { background: var(--zh-background-weaken); }
:deep(.quality-report-dialog .el-dialog__headerbtn:active) { transform: scale(.96); }
:deep(.quality-report-dialog .el-dialog__body) { padding: 0; }
:deep(.quality-report-dialog .el-dialog__footer) { padding: 16px 26px 20px; border-top: 1px solid var(--zh-line-parting); }
.quality-report-card { padding: 24px 26px 26px; background: var(--zh-background-pop); }
.quality-report-summary { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 16px; }
.quality-report-emblem { display: grid; place-items: center; width: 52px; height: 58px; border: 1px solid rgb(31 153 63 / 14%); border-radius: var(--zh-radius10); color: var(--zh-green); background: rgb(31 153 63 / 8%); }
.quality-report-emblem .el-icon { font-size: 25px; }
.quality-report-identity { min-width: 0; }
.quality-report-identity p { margin: 0 0 3px; color: var(--zh-green); font-size: 11px; font-weight: 600; letter-spacing: var(--zh-tracking-wide); }
.quality-report-identity h2 { overflow: hidden; margin: 0; color: var(--zh-text-primary); font-size: 19px; font-weight: 600; letter-spacing: var(--zh-tracking-tight); line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.quality-report-identity span { display: block; margin-top: 5px; color: var(--zh-text-caption); font-size: 12px; }
.quality-score { padding-left: 20px; border-left: 1px solid var(--zh-line-parting); }
.quality-score :deep(.el-progress__text) { display: flex; flex-direction: column; line-height: 1; }
.quality-score :deep(.el-progress__text strong) { color: var(--zh-text-primary); font: 600 24px var(--zh-font-number); font-variant-numeric: tabular-nums; letter-spacing: var(--zh-tracking-tight); }
.quality-score :deep(.el-progress__text small) { margin-top: 5px; color: var(--zh-text-caption); font-size: 10px; }
.quality-checks { margin-top: 24px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); overflow: hidden; }
.quality-checks > header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 16px; border-bottom: 1px solid var(--zh-line-parting); background: var(--zh-background-light); }
.quality-checks > header > div { display: flex; align-items: baseline; gap: 8px; }
.quality-checks > header span { color: var(--zh-text-primary); font-size: 13px; font-weight: 600; }
.quality-checks > header small { color: var(--zh-text-caption); font-size: 11px; }
.quality-checks ul { display: grid; margin: 0; padding: 0; list-style: none; }
.quality-checks li { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 12px; min-height: 58px; padding: 10px 16px; transition: background 200ms ease; }
.quality-checks li + li { border-top: 1px solid var(--zh-line-parting); }
.quality-checks li:hover { background: var(--zh-background-option); }
.quality-check-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: var(--zh-radius8); color: var(--zh-green); background: rgb(31 153 63 / 8%); }
.quality-checks li.warning .quality-check-icon { color: var(--zh-orange); background: rgb(255 107 63 / 8%); }
.quality-checks li > div { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.quality-checks li strong { overflow: hidden; color: var(--zh-text-primary); font-size: 13px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.quality-checks li small { overflow: hidden; color: var(--zh-text-caption); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.quality-checks li :deep(.el-tag) { border-radius: var(--zh-radius6, 6px); }

@media (max-width: 620px) {
  :deep(.task-detail-dialog .el-dialog__header) { padding-inline: 20px; }
  :deep(.task-detail-dialog .el-dialog__footer) { padding-inline: 20px; }
  .task-detail-card { padding: 20px; }
  .task-detail-hero { grid-template-columns: auto minmax(0, 1fr); }
  .task-detail-hero :deep(.el-tag) { grid-column: 1 / -1; justify-self: start; }
  .task-detail-metrics { grid-template-columns: 1fr; }
  .task-detail-metrics > div + div { border-top: 1px solid var(--zh-line-border); border-left: 0; }
  .task-detail-info dl { grid-template-columns: 1fr; }
  .task-detail-info dl > div:nth-child(2n) { padding-left: 0; }
  .task-detail-actions { align-items: stretch; flex-direction: column-reverse; }
  .task-detail-actions > div { display: grid; grid-template-columns: 1fr 1fr; }
  .task-detail-actions > div .el-button:last-child { grid-column: 1 / -1; }
  :deep(.quality-report-dialog .el-dialog__header), :deep(.quality-report-dialog .el-dialog__footer) { padding-inline: 20px; }
  .quality-report-card { padding: 20px; }
  .quality-report-summary { grid-template-columns: auto minmax(0, 1fr); }
  .quality-score { grid-column: 1 / -1; justify-self: stretch; margin-top: 2px; padding: 16px 0 0; border-top: 1px solid var(--zh-line-parting); border-left: 0; }
  .quality-score :deep(.el-progress) { margin: 0 auto; }
}
</style>
