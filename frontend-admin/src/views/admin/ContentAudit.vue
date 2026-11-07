<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDrawer, ElSkeleton, ElEmpty, ElMessageBox, ElMessage, ElTooltip, ElRadioGroup, ElRadioButton
    - ElementPlus Icons: Refresh, View, Select, Close
    - `ref`, `reactive`, `onMounted`, `onBeforeUnmount` from Vue
  - 依赖:
    - `@/apis/moderation`: 导入 `getModerationTasks`（API-90，分页查询审核任务）、
      `createModerationDecision`（API-91，提交审核决定）、`getReports`（API-95，分页查询举报）、
      `resolveReport`（API-96，处理举报）
  - 输入: 无 props；审核任务数据来自 API-90/91，举报数据来自 API-95/96
  - 输出: 渲染内容审核与社区治理视图（Tab 切换 + 工具栏 + 数据表格 + 分页器 + 详情抽屉）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
-->

<script setup>
import { computed, ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import {
  Refresh,
  View,
  Select,
  Close,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getModerationTasks,
  getModerationMetrics,
  getModerationContent,
  createModerationDecision,
  getReports,
  resolveReport,
} from '@/apis/moderation'
import CommunityContentPreview from '../../../../frontend/src/components/CommunityContentPreview.vue'

// ===================================================================
// 配置常量
// ===================================================================

/** 页面 Tab 定义 */
const PAGE_TABS = [
  { key: 'audit', label: '内容审核' },
  { key: 'report', label: '举报管理' },
]

/** 内容类型筛选项 */
const CONTENT_TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: 'PPT 课件', value: 'ppt' },
  { label: 'Skill', value: 'skill' },
  { label: '案例', value: 'lesson_case' },
]

/** 内容类型 → 显示标签映射（后端实际值域 skill/lesson_case，兼容历史 case 值） */
const CONTENT_TYPE_LABEL_MAP = { ppt: 'PPT 课件', skill: 'Skill', lesson_case: '教学案例', case: '教学案例' }

/** 内容类型 → Tag 类型映射 */
const CONTENT_TYPE_TAG_TYPE_MAP = { ppt: 'primary', skill: 'info', case: '' }
const AI_VERDICT_LABEL_MAP = { pass: 'AI 通过', review: '待人工复核', fail: 'AI 未通过', error: 'AI 异常' }
const AI_DOMAIN_LABEL_MAP = { arts: '文科 Agent', science: '理科 Agent', engineering: '工科 Agent', unknown: '人工分流' }
const AI_CHECK_LABEL_MAP = { pass: '通过', review: '需核验', fail: '未通过' }

/** 内容审核状态筛选项（对应 AuditVO.status：pending 待审核 / processed 已处理） */
const AUDIT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待审核', value: 'pending' },
  { label: '已处理', value: 'processed' },
]

/** 审核状态 → 显示标签映射 */
const AUDIT_STATUS_LABEL_MAP = {
  pending: '待审核',
  processed: '已处理',
}

/** 审核状态 → Tag 类型映射 */
const AUDIT_STATUS_TAG_TYPE_MAP = {
  pending: 'warning',
  processed: 'success',
}

/** 审核状态 → 圆点颜色映射 */
const AUDIT_STATUS_DOT_COLOR_MAP = {
  pending: 'var(--zh-orange)',
  processed: 'var(--zh-green)',
}

/** 审核动作 → 显示标签映射（对应 AuditVO.action） */
const AUDIT_ACTION_LABEL_MAP = {
  approve: '通过',
  ai_approve: 'AI 自动通过',
  ai_reject: '低于 60 分自动驳回',
  reject: '驳回',
  rework: '退回修改',
}

/** 举报状态筛选项（对应 AuditVO.status：pending 待处理 / processed 已处理） */
const REPORT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'processed' },
]

/** 举报状态 → 显示标签映射 */
const REPORT_STATUS_LABEL_MAP = {
  pending: '待处理',
  processed: '已处理',
}

/** 举报状态 → Tag 类型映射 */
const REPORT_STATUS_TAG_TYPE_MAP = {
  pending: 'warning',
  processed: 'success',
}

/** 举报状态 → 圆点颜色映射 */
const REPORT_STATUS_DOT_COLOR_MAP = {
  pending: 'var(--zh-orange)',
  processed: 'var(--zh-green)',
}

/** 举报处理动作 → 显示标签映射（对应 AuditVO.action） */
const REPORT_ACTION_LABEL_MAP = {
  approve: '确认违规',
  offline: '内容下架',
  ignore: '忽略举报',
  reject: '驳回举报',
  restore: '恢复上架',
}

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// ===================================================================
// 响应式状态
// ===================================================================

/** 数据加载状态 */
const isLoading = ref(true)

/** 表格数据加载中 */
const isTableLoading = ref(false)

/** 当前激活的 Tab */
const activeTab = ref('audit')

/** 审核内容列表 */
const contentList = ref([])

/** 举报内容列表 */
const reportList = ref([])

/** 筛选条件 */
const filters = reactive({
  type: '',
  status: '',
  aiVerdict: '',
  aiDomain: '',
})
const parsedAiReport = (row) => {
  try { return typeof row?.ai_report === 'string' ? JSON.parse(row.ai_report) : (row?.ai_report || {}) } catch { return {} }
}
const canHumanReview = (row) => row?.status === 'pending' || (row?.status === 'processed' && ['ai_approve', 'ai_reject'].includes(row?.action))
const auditQueueOptions = [
  { value: '', label: '全部投稿' },
  { value: 'spot_check', label: '待抽检' },
  { value: 'needs_review', label: '待人工复核' },
  { value: 'auto_approved', label: 'AI 已发布' },
  { value: 'auto_rejected', label: 'AI 自动驳回' },
]
const moderationMetrics = ref(null)
let metricsRequestId = 0
async function loadModerationMetrics() {
  const requestId = ++metricsRequestId
  try {
    const response = await getModerationMetrics()
    if (requestId !== metricsRequestId) return
    moderationMetrics.value = [0, 200].includes(response?.code) ? response.data : null
  } catch {
    if (requestId === metricsRequestId) moderationMetrics.value = null
  }
}

/** 分页参数 */
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** 详情抽屉可见性 */
const drawerVisible = ref(false)

/** 详情抽屉展示模式：audit 审核任务详情 / report 举报详情 */
const drawerMode = ref('audit')

/** 当前查看的数据（AuditVO 审核任务或举报记录） */
const currentContent = ref(null)


/** 管理员预览的实际投稿内容（与教师端共用同一只读预览组件） */
const contentPreviewLoading = ref(false)
const contentPreview = ref(null)
const contentPreviewError = ref('')
/** 投稿预览的内容视图与 PPT 当前页 */
const contentPreviewView = ref('ppt')
const contentPreviewSlideIndex = ref(0)
const previewVersionMatches = computed(() => {
  if (!contentPreview.value) return false
  const version = parsedAiReport(currentContent.value).content_version
  return version == null || Number(version) === Number(contentPreview.value.version)
})
/** 操作执行中 */
const isActionLoading = ref(false)
let listRequestId = 0

// ===================================================================
// 数据获取
// ===================================================================

/**
 * 拉取当前 Tab 数据 — 审核 Tab 走 API-90，举报 Tab 走 API-95，均为服务端分页
 */
const fetchData = () => {
  return activeTab.value === 'audit' ? fetchAuditTasks() : fetchReports()
}

/**
 * 拉取审核任务列表（API-90）
 * 状态与目标类型筛选由后端处理，空值不传避免空字符串匹配不到数据
 */
const fetchAuditTasks = async () => {
  void loadModerationMetrics()
  const requestId = ++listRequestId
  isTableLoading.value = true
  try {
    const res = await getModerationTasks({
      status: filters.status || undefined,
      target_type: filters.type || undefined,
      ai_verdict: filters.aiVerdict || undefined,
      ai_domain: filters.aiDomain || undefined,
      page: pagination.currentPage,
      size: pagination.pageSize,
    })
    if (requestId !== listRequestId) return
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '审核任务加载失败')
      contentList.value = []
      pagination.total = 0
      return
    }
    contentList.value = res?.data?.records || []
    pagination.total = res?.data?.total || 0
  } catch {
    if (requestId !== listRequestId) return
    ElMessage.error('审核任务加载失败，请稍后重试')
    contentList.value = []
    pagination.total = 0
  } finally {
    if (requestId === listRequestId) isTableLoading.value = false
  }
}

/**
 * 拉取举报列表（API-95）
 * 状态筛选由后端处理，空值不传避免空字符串匹配不到数据
 */
const fetchReports = async () => {
  const requestId = ++listRequestId
  isTableLoading.value = true
  try {
    const res = await getReports({
      status: filters.status || undefined,
      page: pagination.currentPage,
      size: pagination.pageSize,
    })
    if (requestId !== listRequestId) return
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '举报数据加载失败')
      reportList.value = []
      pagination.total = 0
      return
    }
    reportList.value = res?.data?.records || []
    pagination.total = res?.data?.total || 0
  } catch {
    if (requestId !== listRequestId) return
    ElMessage.error('举报数据加载失败，请稍后重试')
    reportList.value = []
    pagination.total = 0
  } finally {
    if (requestId === listRequestId) isTableLoading.value = false
  }
}

/**
 * 页面首次数据加载
 */
const loadData = async () => {
  isLoading.value = true
  await fetchData()
  isLoading.value = false
}

/**
 * Tab 切换处理
 * 重置筛选条件和分页
 * @param {string} tab - 目标 Tab key
 */
const handleTabChange = (tab) => {
  filters.type = ''
  filters.status = ''
  filters.aiVerdict = ''
  filters.aiDomain = ''
  pagination.currentPage = 1
  activeTab.value = tab
  fetchData()
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发
 */
const handleRefresh = () => {
  loadData()
}

/**
 * 筛选条件变更处理
 */
const handleFilterChange = () => {
  pagination.currentPage = 1
  fetchData()
}

const selectAuditQueue = (queue) => {
  filters.aiVerdict = queue
  filters.status = ''
  handleFilterChange()
}

/**
 * 分页页码变更
 */
const handlePageChange = (page) => {
  pagination.currentPage = page
  fetchData()
}

/**
 * 分页每页条数变更
 */
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchData()
}

/**
 * 获取内容类型 Tag 类型
 */
const getContentTagType = (type) => CONTENT_TYPE_TAG_TYPE_MAP[type] || 'info'

/**
 * 获取审核状态 Tag 类型
 */
const getStatusTagType = (status) => AUDIT_STATUS_TAG_TYPE_MAP[status] || 'info'

/**
 * 获取审核状态显示标签
 */
const getStatusLabel = (status) => AUDIT_STATUS_LABEL_MAP[status] || status

/**
 * 获取审核状态圆点颜色
 */
const getStatusDotColor = (status) => AUDIT_STATUS_DOT_COLOR_MAP[status] || 'var(--zh-text-disabled)'

/**
 * 格式化后端时间为 "YYYY-MM-DD HH:mm:ss"
 * LocalDateTime 经 Jackson 序列化为 ISO 字符串（2026-07-27T09:30:00）
 * @param {string} value - 后端时间字符串
 */
const formatDateTime = (value) => {
  if (!value) return '—'
  return String(value).replace('T', ' ').slice(0, 19)
}

/**
 * 获取举报状态 Tag 类型
 */
const getReportStatusTagType = (status) => REPORT_STATUS_TAG_TYPE_MAP[status] || 'info'

/**
 * 获取举报状态显示标签
 */
const getReportStatusLabel = (status) => REPORT_STATUS_LABEL_MAP[status] || status

/**
 * 获取举报状态圆点颜色
 */
const getReportStatusDotColor = (status) => REPORT_STATUS_DOT_COLOR_MAP[status] || 'var(--zh-text-disabled)'

/**
 * 打开详情抽屉
 * @param {Object} row - 当前行数据（AuditVO 审核任务或举报记录）
 * @param {'audit'|'report'} [mode='audit'] - 抽屉展示模式
 */
const openDetailDrawer = (row, mode = 'audit') => {
  drawerMode.value = mode
  currentContent.value = { ...row }
  contentPreviewView.value = 'ppt'
  contentPreviewSlideIndex.value = 0
  drawerVisible.value = true
  void loadContentPreview(currentContent.value)
}

/**
 * 加载审核目标的只读预览；待审内容走管理员受控接口，不走公开社区接口。
 * 在抽屉打开时直接加载，管理员无需再跳到一个独立弹窗才能判断稿件内容。
 */
const loadContentPreview = async (row = currentContent.value) => {
  const targetId = Number(row?.target_id)
  if (!Number.isInteger(targetId) || targetId <= 0) {
    contentPreviewLoading.value = false
    contentPreview.value = null
    contentPreviewError.value = '未找到可预览的投稿内容'
    return
  }
  contentPreviewLoading.value = true
  contentPreview.value = null
  contentPreviewError.value = ''
  try {
    const res = await getModerationContent(targetId)
    if (res?.code !== 0 && res?.code !== 200) throw new Error(res?.message || '内容预览加载失败')
    if (currentContent.value === row) {
      contentPreview.value = { ...res.data, id: res.data?.id ?? targetId }
    }
  } catch (error) {
    if (currentContent.value === row) {
      contentPreviewError.value = error?.message || '内容预览加载失败，请稍后重试'
    }
  } finally {
    if (currentContent.value === row) {
      contentPreviewLoading.value = false
    }
  }
}
/**
 * 抽屉状态显示辅助 — 按抽屉模式选择审核/举报语义
 */
const drawerStatusLabel = (status) =>
  drawerMode.value === 'audit' ? getStatusLabel(status) : getReportStatusLabel(status)

const drawerStatusTagType = (status) =>
  drawerMode.value === 'audit' ? getStatusTagType(status) : getReportStatusTagType(status)

const drawerStatusDotColor = (status) =>
  drawerMode.value === 'audit' ? getStatusDotColor(status) : getReportStatusDotColor(status)

/**
 * 审核通过操作（API-91：approve → 关联内容公开）
 * @param {Object} row - 当前行审核任务数据
 */
const handleApprove = (row) => {
  ElMessageBox.confirm(
    `确认通过审核任务 #${row.id}？关联内容将立即在社区中公开可见。`,
    '确认审核通过',
    {
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
      type: 'success',
      confirmButtonClass: 'el-button--success',
    },
  )
    .then(() => {
      submitDecision(row.id, 'approve', '')
    })
    .catch(() => {})
}

/**
 * 驳回操作 — 需要填写处理意见（API-91：reject → 关联内容下架）
 * @param {Object} row - 当前行审核任务数据
 */
const handleReject = (row, action = 'reject') => {
  const label = action === 'rework' ? '退回修改' : '驳回'
  ElMessageBox.prompt('请填写原因，投稿教师可在我的投稿中查看。', label, {
    confirmButtonText: `确认${label}`,
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
    inputType: 'textarea',
    inputPlaceholder: '请输入驳回理由...',
    inputValidator: (val) => {
      if (!val || !val.trim()) return '请填写审核意见'
      if (val.trim().length > 500) return '审核意见最多 500 字'
      return true
    },
  })
    .then(({ value }) => {
      submitDecision(row.id, action, value.trim())
    })
    .catch(() => {})
}

/**
 * 提交审核决定（API-91）— 成功后刷新列表
 * @param {number} taskId - 审核任务 ID
 * @param {'approve'|'reject'|'rework'} action - 审核动作
 * @param {string} comment - 处理意见
 */
const submitDecision = async (taskId, action, comment) => {
  if (isActionLoading.value) return
  isActionLoading.value = true
  try {
    const res = await createModerationDecision(taskId, { action, comment })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '审核操作失败')
      return
    }
    ElMessage.success({ approve: '审核通过，内容已公开', reject: '已驳回，内容已下架', rework: '已退回，教师可以修改后重新投稿' }[action])
    if (drawerVisible.value && Number(currentContent.value?.id) === Number(taskId)) drawerVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('审核操作失败，请稍后重试')
  } finally {
    isActionLoading.value = false
  }
}

/**
 * 举报管理 — 确认违规（API-96：offline → 关联内容下架）
 * @param {Object} row - 当前行举报数据
 */
const handleConfirmViolation = (row) => {
  ElMessageBox.confirm(
    `确认举报任务 #${row.id} 对应的内容违规？确认后将自动下架该内容并通知作者。`,
    '确认违规',
    {
      confirmButtonText: '确认违规',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    },
  )
    .then(() => {
      submitReportResolution(row.id, 'offline', '已确认违规，内容已下架')
    })
    .catch(() => {})
}

/**
 * 举报管理 — 驳回举报（API-96：ignore → 内容不受影响）
 * @param {Object} row - 当前行举报数据
 */
const handleDismissReport = (row) => {
  ElMessageBox.confirm(
    `确认驳回举报任务 #${row.id}？内容不受影响，举报将标记为已处理。`,
    '确认驳回举报',
    {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      type: 'info',
    },
  )
    .then(() => {
      submitReportResolution(row.id, 'ignore', '已驳回举报，内容不受影响')
    })
    .catch(() => {})
}

/**
 * 提交举报处理结果（API-96）— 成功后刷新列表
 * @param {number} reportId - 举报 ID
 * @param {'offline'|'ignore'} action - 处理动作
 * @param {string} successMsg - 成功提示文案
 */
const submitReportResolution = async (reportId, action, successMsg) => {
  isActionLoading.value = true
  try {
    const res = await resolveReport(reportId, { action, comment: '' })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '举报处理失败')
      return
    }
    ElMessage.success(successMsg)
    if (drawerVisible.value && Number(currentContent.value?.id) === Number(reportId)) drawerVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('举报处理失败，请稍后重试')
  } finally {
    isActionLoading.value = false
  }
}

// ===================================================================
// 生命周期
// ===================================================================

onMounted(() => {
  loadData()
  window.addEventListener('admin-refresh', handleRefresh)
})

onBeforeUnmount(() => {
  listRequestId++
  metricsRequestId++
  window.removeEventListener('admin-refresh', handleRefresh)
})
</script>

<template>
  <main class="moderation-page">
    <!-- ===================================================================
         1. 标题区 + Tab 分段
         =================================================================== -->
    <header class="moderation-page-header">
      <div>
        <p class="moderation-kicker">COMMUNITY GOVERNANCE</p>
        <h1>内容审核与社区治理</h1>
        <p class="moderation-page-intro">集中处理社区投稿与举报，所有决定均会同步给投稿教师。</p>
      </div>
      <el-tooltip content="刷新列表" placement="bottom" effect="dark">
        <el-button class="moderation-refresh" :icon="Refresh" aria-label="刷新列表" @click="handleRefresh">刷新</el-button>
      </el-tooltip>
    </header>

    <!-- ===================================================================
         2. 工作区导航与筛选器
         =================================================================== -->
    <section class="moderation-toolbar" aria-label="审核筛选">
      <el-radio-group
        :model-value="activeTab"
        size="default"
        class="audit-tab-group"
        @change="handleTabChange"
      >
        <el-radio-button
          v-for="tab in PAGE_TABS"
          :key="tab.key"
          :value="tab.key"
        >
          {{ tab.label }}
        </el-radio-button>
      </el-radio-group>

      <div class="moderation-filters">
        <el-select
          v-if="activeTab === 'audit'"
          v-model="filters.type"
          placeholder="全部类型"
          clearable
          size="default"
          @change="handleFilterChange"
        >
          <el-option
            v-for="opt in CONTENT_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-select
          v-model="filters.status"
          placeholder="全部状态"
          clearable
          size="default"
          @change="handleFilterChange"
        >
          <el-option
            v-for="opt in (activeTab === 'audit' ? AUDIT_STATUS_OPTIONS : REPORT_STATUS_OPTIONS)"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select v-if="activeTab === 'audit'" v-model="filters.aiVerdict" placeholder="AI 初审结果" clearable @change="handleFilterChange">
          <el-option label="全部 AI 结果" value="" />
          <el-option label="待抽检" value="spot_check" />
          <el-option label="待人工复核" value="needs_review" />
          <el-option label="AI 已发布" value="auto_approved" />
          <el-option label="AI 自动驳回" value="auto_rejected" />
          <el-option label="AI 通过（可抽查）" value="pass" />
          <el-option label="AI 未通过（需复核）" value="fail" />
          <el-option label="AI 待复核" value="review" />
          <el-option label="AI 异常" value="error" />
        </el-select>
        <el-select v-if="activeTab === 'audit'" v-model="filters.aiDomain" placeholder="学科 Agent" clearable @change="handleFilterChange">
          <el-option label="全部 Agent" value="" />
          <el-option label="文科 Agent" value="arts" />
          <el-option label="理科 Agent" value="science" />
          <el-option label="工科 Agent" value="engineering" />
        </el-select>
      </div>
    </section>

    <section v-if="activeTab === 'audit'" class="audit-policy">
      <p>有效机审低于 60 分自动驳回。达到 60 分且 AI 通过的投稿随机抽检 10%，抽中后经人工复审再发布。</p>
      <p>AI 待复核、报告异常或检查不完整的稿件保留人工处理。</p>
      <p v-if="moderationMetrics">
        待抽检 {{ moderationMetrics.pending_samples }} · 待复核 {{ moderationMetrics.pending_reviews }} ·
        自动驳回 {{ moderationMetrics.auto_rejected }} ·
        AI 与人工判定一致率
        {{ moderationMetrics.agreement_rate == null ? '暂无可比较样本' : (moderationMetrics.agreement_rate * 100).toFixed(1) + '%' }}
        （一致 {{ moderationMetrics.agreements }} / 可比较 {{ moderationMetrics.comparable }}，全量记录）
      </p>
      <small>一致率只统计 AI pass/fail 与人工通过/驳回，退回修改和 AI 待复核不计入。</small>
    </section>
    <nav v-if="activeTab === 'audit'" class="audit-queues" aria-label="审核队列">
      <el-button v-for="queue in auditQueueOptions" :key="queue.value"
        :type="filters.aiVerdict === queue.value ? 'primary' : 'default'"
        :aria-pressed="filters.aiVerdict === queue.value"
        @click="selectAuditQueue(queue.value)">{{ queue.label }}</el-button>
    </nav>

    <!-- ===================================================================
         3. 数据表格区
         =================================================================== -->
    <el-card
      class="moderation-table-card"
      shadow="never"
      :style="{
        background: 'var(--zh-background-capsule)',
        borderRadius: 'var(--zh-radius12)',
        borderColor: 'var(--zh-line-border)',
      }"
    >
      <!-- 全页骨架屏 -->
      <template v-if="isLoading">
        <div
          v-for="n in 8"
          :key="'skeleton-' + n"
          class="flex items-center gap-4 py-3 border-b last:border-0"
          style="border-color: var(--zh-line-parting);"
        >
          <div class="skeleton-loader w-14 h-4 rounded"></div>
          <div class="skeleton-loader flex-1 h-4 rounded"></div>
          <div class="skeleton-loader w-16 h-6 rounded-full"></div>
          <div class="skeleton-loader w-16 h-4 rounded"></div>
          <div class="skeleton-loader w-32 h-4 rounded"></div>
          <div class="skeleton-loader w-20 h-6 rounded-full"></div>
          <div class="skeleton-loader w-40 h-4 rounded"></div>
        </div>
      </template>

      <template v-else>
        <!-- ===== 内容审核 Tab 表格 ===== -->
        <template v-if="activeTab === 'audit'">
          <el-table
            :data="contentList"
            stripe
            border
            v-loading="isTableLoading"
            element-loading-text="加载中..."
            :row-class-name="(r) => r.row.status === 'pending' ? 'audit-table-row pending-row' : 'audit-table-row'"
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：任务 ID -->
            <el-table-column prop="id" label="任务 ID" width="100" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：目标类型 -->
            <el-table-column prop="target_type" label="目标类型" width="110" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getContentTagType(row.target_type)"
                  size="small"
                  effect="plain"
                >
                  {{ CONTENT_TYPE_LABEL_MAP[row.target_type] || row.target_type }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：目标内容 -->
            <el-table-column prop="target_id" label="目标内容" width="110" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  #{{ row.target_id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：审核理由 -->
            <el-table-column prop="reason" label="审核理由" min-width="200">
              <template #default="{ row }">
                <el-tooltip
                  :content="row.reason || '—'"
                  placement="top"
                  effect="dark"
                  :disabled="!row.reason || row.reason.length <= 18"
                >
                  <span class="inline-block max-w-45 truncate" style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                    {{ row.reason || '—' }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <!-- 列：提交时间 -->
            <el-table-column prop="created_at" label="提交时间" width="170" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ formatDateTime(row.created_at) }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：审核状态 -->
            <el-table-column label="AI 初审" min-width="165">
              <template #default="{ row }">
                <div v-if="row.ai_verdict" class="ai-review-cell">
                  <el-tag :type="row.ai_verdict === 'pass' ? 'success' : row.ai_verdict === 'fail' ? 'danger' : 'warning'" size="small" effect="plain">{{ AI_VERDICT_LABEL_MAP[row.ai_verdict] || row.ai_verdict }}</el-tag>
                  <small>{{ AI_DOMAIN_LABEL_MAP[row.ai_domain] || '人工分流' }} · {{ row.ai_score ?? '—' }} 分</small>
                </div>
                <span v-else class="ai-review-pending">{{ row.status === 'pending' ? '可人工审核' : '人工审核' }}</span>
              </template>
            </el-table-column>

            <!-- 列：审核状态 -->
            <el-table-column prop="status" label="审核状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getStatusTagType(row.status)"
                  size="small"
                  effect="plain"
                >
                  <span class="flex items-center gap-1.5">
                    <span
                      class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                      :style="{ background: getStatusDotColor(row.status) }"
                    ></span>
                    {{ getStatusLabel(row.status) }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：处理结果 -->
            <el-table-column prop="action" label="处理结果" width="130" align="center">
              <template #default="{ row }">
                <el-tag
                  v-if="row.status === 'processed'"
                  :type="row.action === 'approve' ? 'success' : row.action === 'reject' ? 'danger' : 'warning'"
                  size="small"
                  effect="plain"
                >
                  {{ AUDIT_ACTION_LABEL_MAP[row.action] || row.action }}
                </el-tag>
                <span v-else style="font-size: var(--zh-font-size13); color: var(--zh-text-disabled);">—</span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="190" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    type="primary"
                    link
                    size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer(row, 'audit')"
                  >
                    <el-icon class="mr-0.5"><View /></el-icon>
                    {{ row.action === 'ai_approve' ? '人工抽查' : canHumanReview(row) ? '查看并审核' : '详情' }}
                  </el-button>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无审核任务" :image-size="80">
                <template v-if="filters.type || filters.status || filters.aiVerdict || filters.aiDomain">
                  <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                    没有符合条件的审核任务，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="filters.type = ''; filters.status = ''; filters.aiVerdict = ''; filters.aiDomain = ''; handleFilterChange();"
                  >
                    清除筛选
                  </el-button>
                </template>
              </el-empty>
            </template>
          </el-table>
        </template>

        <!-- ===== 举报管理 Tab 表格 ===== -->
        <template v-if="activeTab === 'report'">
          <el-table
            :data="reportList"
            stripe
            border
            v-loading="isTableLoading"
            row-class-name="audit-table-row"
            element-loading-text="加载中..."
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：举报 ID -->
            <el-table-column prop="id" label="举报 ID" width="100" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：目标类型 -->
            <el-table-column prop="target_type" label="目标类型" width="110" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getContentTagType(row.target_type)"
                  size="small"
                  effect="plain"
                >
                  {{ CONTENT_TYPE_LABEL_MAP[row.target_type] || row.target_type }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：目标内容 -->
            <el-table-column prop="target_id" label="目标内容" width="110" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  #{{ row.target_id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：举报原因 -->
            <el-table-column prop="reason" label="举报原因" min-width="200">
              <template #default="{ row }">
                <el-tooltip
                  :content="row.reason || '—'"
                  placement="top"
                  effect="dark"
                  :disabled="!row.reason || row.reason.length <= 18"
                >
                  <span class="inline-block max-w-45 truncate" style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                    {{ row.reason || '—' }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <!-- 列：举报人 -->
            <el-table-column prop="reporter_id" label="举报人" width="110" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  {{ row.reporter_id ? '#' + row.reporter_id : '—' }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：举报时间 -->
            <el-table-column prop="created_at" label="举报时间" width="170" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ formatDateTime(row.created_at) }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：处理状态 -->
            <el-table-column prop="status" label="处理状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="getReportStatusTagType(row.status)" size="small" effect="plain">
                  <span class="flex items-center gap-1.5">
                    <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0" :style="{ background: getReportStatusDotColor(row.status) }"></span>
                    {{ getReportStatusLabel(row.status) }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：处理结果 -->
            <el-table-column prop="action" label="处理结果" width="130" align="center">
              <template #default="{ row }">
                <el-tag
                  v-if="row.status === 'processed'"
                  :type="row.action === 'offline' || row.action === 'approve' ? 'danger' : 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ REPORT_ACTION_LABEL_MAP[row.action] || row.action }}
                </el-tag>
                <span v-else style="font-size: var(--zh-font-size13); color: var(--zh-text-disabled);">—</span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="190" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer(row, 'report')"
                  >
                    <el-icon class="mr-0.5"><View /></el-icon>
                    详情
                  </el-button>
                  <template v-if="row.status === 'pending'">
                    <el-button
                      type="danger" link size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleConfirmViolation(row)"
                    >
                      <el-icon class="mr-0.5"><Select /></el-icon>
                      违规
                    </el-button>
                    <el-button
                      link size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }"
                      @click="handleDismissReport(row)"
                    >
                      <el-icon class="mr-0.5"><Close /></el-icon>
                      驳回
                    </el-button>
                  </template>
                </div>
              </template>
            </el-table-column>

            <template #empty>
              <el-empty description="暂无举报记录" :image-size="80">
                <template v-if="filters.status">
                  <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                    没有符合条件的举报，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="filters.status = ''; handleFilterChange();"
                  >
                    清除筛选
                  </el-button>
                </template>
              </el-empty>
            </template>
          </el-table>
        </template>

        <!-- ===== 分页器 ===== -->
        <div
          v-if="pagination.total > 0"
          class="flex justify-end pt-4 mt-4 border-t"
          :style="{ borderColor: 'var(--zh-line-parting)' }"
        >
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="PAGE_SIZE_OPTIONS"
            :background="true"
            layout="total, sizes, prev, pager, next, jumper"
            :style="{
              '--el-pagination-bg-color': 'var(--zh-background-capsule)',
              '--el-pagination-button-bg-color': 'var(--zh-background-option)',
              '--el-pagination-hover-color': 'var(--zh-text-theme)',
            }"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </template>
    </el-card>

    <!-- ===================================================================
         4. 内容审核详情：任务信息与原稿预览同时呈现
         =================================================================== -->
    <el-drawer
      v-model="drawerVisible"
      class="moderation-detail-drawer"
      direction="rtl"
      size="min(960px, 94vw)"
      destroy-on-close
      :style="{
        '--el-drawer-bg-color': 'var(--zh-background-primary)',
        '--el-drawer-padding-primary': '0',
      }"
    >
      <template #header>
        <header v-if="currentContent" class="moderation-drawer-header">
          <div>
            <p>{{ drawerMode === 'audit' ? 'CONTENT MODERATION' : 'COMMUNITY REPORT' }}</p>
            <h2>{{ drawerMode === 'audit' ? '审核任务' : '举报任务' }} <span>· #{{ currentContent.id }}</span></h2>
          </div>
          <el-tag :type="drawerStatusTagType(currentContent.status)" effect="plain" class="drawer-status-tag">
            <i :style="{ background: drawerStatusDotColor(currentContent.status) }"></i>
            {{ drawerStatusLabel(currentContent.status) }}
          </el-tag>
        </header>
      </template>

      <div v-if="currentContent" class="moderation-detail-layout">
        <aside class="moderation-task-panel" aria-label="审核任务信息">
          <section class="task-target-summary">
            <div class="task-target-mark" aria-hidden="true">{{ drawerMode === 'audit' ? '审' : '报' }}</div>
            <div>
              <span>{{ CONTENT_TYPE_LABEL_MAP[currentContent.target_type] || currentContent.target_type || '社区内容' }}</span>
              <strong>{{ contentPreview?.title || currentContent.content_title || `投稿 #${currentContent.target_id}` }}</strong>
              <small>投稿编号 #{{ currentContent.target_id }}</small>
            </div>
          </section>

          <section class="task-info-section">
            <div class="task-section-heading">
              <span>任务信息</span>
              <el-tag :type="getContentTagType(currentContent.target_type)" size="small" effect="plain">
                {{ CONTENT_TYPE_LABEL_MAP[currentContent.target_type] || currentContent.target_type }}
              </el-tag>
            </div>
            <dl class="task-meta-list">
              <div>
                <dt>提交时间</dt>
                <dd>{{ formatDateTime(currentContent.created_at) }}</dd>
              </div>
              <div>
                <dt>处理时间</dt>
                <dd>{{ formatDateTime(currentContent.processed_at) }}</dd>
              </div>
              <div>
                <dt>处理人</dt>
                <dd>{{ currentContent.handler_id ? `管理员 #${currentContent.handler_id}` : '待分配' }}</dd>
              </div>
              <div>
                <dt>处理结果</dt>
                <dd>{{ currentContent.status === 'processed'
                  ? (drawerMode === 'audit'
                    ? (AUDIT_ACTION_LABEL_MAP[currentContent.action] || currentContent.action)
                    : (REPORT_ACTION_LABEL_MAP[currentContent.action] || currentContent.action))
                  : '尚未处理' }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="currentContent.reason" class="task-note task-note-warning">
            <span>{{ drawerMode === 'audit' ? '送审说明' : '举报原因' }}</span>
            <p>{{ currentContent.reason }}</p>
          </section>

          <section v-if="currentContent.comment" class="task-note">
            <span>处理意见</span>
            <p>{{ currentContent.comment }}</p>
          </section>

          <section v-if="drawerMode === 'audit' && currentContent.ai_verdict" class="task-note ai-review-report">
            <span>AI 初审 · {{ AI_DOMAIN_LABEL_MAP[currentContent.ai_domain] || '人工分流' }}</span>
            <p><strong>{{ AI_VERDICT_LABEL_MAP[currentContent.ai_verdict] || currentContent.ai_verdict }}</strong> · {{ currentContent.ai_score ?? '—' }} 分 · {{ currentContent.ai_model || '模型未记录' }}</p>
            <p>{{ parsedAiReport(currentContent).summary || '未提供审核摘要' }}</p>
            <p v-if="parsedAiReport(currentContent).auto_reject">该稿件的机审评分低于 60 分，曾自动驳回，人工复核结果以处理意见为准。</p>
            <p v-if="parsedAiReport(currentContent).human_review?.agrees_with_ai !== undefined">
              人工与 AI 判定{{ parsedAiReport(currentContent).human_review.agrees_with_ai ? '一致' : '不一致' }}
            </p>
            <p v-if="parsedAiReport(currentContent).spot_check">{{ currentContent.status === 'pending' ? '已抽中，人工确认通过后发布。' : '该稿件已完成人工抽检。' }}</p>
            <ul v-if="parsedAiReport(currentContent).checks?.length">
              <li v-for="(check, index) in parsedAiReport(currentContent).checks" :key="index"><strong>{{ check.name }}：</strong>{{ AI_CHECK_LABEL_MAP[check.status] || '需核验' }} · {{ check.evidence }}</li>
            </ul>
            <ul v-if="parsedAiReport(currentContent).findings?.length">
              <li v-for="(finding, index) in parsedAiReport(currentContent).findings" :key="`finding-${index}`"><strong>风险：</strong>{{ finding.evidence }}{{ finding.suggestion ? `；建议：${finding.suggestion}` : '' }}</li>
            </ul>
            <small>AI 结果仅作辅助；审核员可推翻结论。{{ formatDateTime(currentContent.ai_reviewed_at) }}</small>
          </section>

          <section v-if="drawerMode === 'report' ? currentContent.status === 'pending' : canHumanReview(currentContent)" class="task-action-panel">
            <div>
              <strong>{{ drawerMode === 'audit' ? '做出审核决定' : '处理本条举报' }}</strong>
              <p>{{ drawerMode === 'audit' ? '决定会即时更新投稿的社区状态。' : '确认违规会下架对应的社区内容。' }}</p>
              <p v-if="drawerMode === 'audit' && contentPreview && !previewVersionMatches">稿件版本已变化，此审核单仅供查阅。</p>
            </div>
            <div class="task-action-buttons">
              <template v-if="drawerMode === 'audit'">
                <el-button type="primary" :disabled="!previewVersionMatches" :loading="isActionLoading" @click="handleApprove(currentContent)">
                  <el-icon><Select /></el-icon>
                  {{ currentContent.action === 'ai_approve' ? '抽查确认' : '审核通过' }}
                </el-button>
                <el-button :disabled="!previewVersionMatches" :loading="isActionLoading" @click="handleReject(currentContent, 'rework')">退回修改</el-button>
                <el-button type="danger" plain :disabled="!previewVersionMatches" :loading="isActionLoading" @click="handleReject(currentContent)">
                  <el-icon><Close /></el-icon>
                  驳回
                </el-button>
              </template>
              <template v-else>
                <el-button type="danger" :loading="isActionLoading" @click="handleConfirmViolation(currentContent)">
                  <el-icon><Select /></el-icon>
                  确认违规
                </el-button>
                <el-button :loading="isActionLoading" @click="handleDismissReport(currentContent)">
                  <el-icon><Close /></el-icon>
                  驳回举报
                </el-button>
              </template>
            </div>
          </section>
        </aside>

        <section class="moderation-preview-panel" aria-label="提交内容预览">
          <header class="preview-panel-header">
            <div>
              <p>SUBMISSION PREVIEW</p>
              <h3>提交内容</h3>
              <span>以下内容与教师端社区详情使用同一只读预览组件。</span>
            </div>
            <el-button link type="primary" :loading="contentPreviewLoading" @click="loadContentPreview(currentContent)">重新加载</el-button>
          </header>

          <div v-loading="contentPreviewLoading" class="submission-preview-viewport">
            <el-alert
              v-if="contentPreviewError"
              :title="contentPreviewError"
              type="error"
              :closable="false"
              show-icon
            />

            <template v-else-if="contentPreview">
              <header class="submission-preview-header">
                <div>
                  <el-tag :type="getContentTagType(contentPreview.content_type)" effect="plain">
                    {{ CONTENT_TYPE_LABEL_MAP[contentPreview.content_type] || contentPreview.content_type }}
                  </el-tag>
                  <h4>{{ contentPreview.title || `投稿 #${currentContent.target_id}` }}</h4>
                  <p v-if="contentPreview.description">{{ contentPreview.description }}</p>
                </div>
                <span>v{{ contentPreview.version || 1 }}</span>
              </header>

              <dl class="submission-attribute-list">
                <div><dt>学科</dt><dd>{{ contentPreview.subject || '未标注' }}</dd></div>
                <div><dt>学段</dt><dd>{{ contentPreview.grade || '未标注' }}</dd></div>
                <div><dt>课型</dt><dd>{{ contentPreview.lesson_type || '未标注' }}</dd></div>
                <div><dt>授权</dt><dd>{{ contentPreview.license || '未说明' }}</dd></div>
              </dl>

              <div class="submission-content">
                <div class="submission-content-heading">
                  <span>CONTENT</span>
                  <strong>正文与教学结构</strong>
                </div>
                <CommunityContentPreview
                  :item="contentPreview"
                  :active-view="contentPreviewView"
                  :active-slide-index="contentPreviewSlideIndex"
                  @update:active-view="contentPreviewView = $event"
                  @update:active-slide-index="contentPreviewSlideIndex = $event"
                />
              </div>
            </template>

            <el-empty v-else description="正在准备投稿内容" :image-size="72" />
          </div>
        </section>
      </div>
    </el-drawer>
  </main>
</template>

<style scoped>
.moderation-page {
  width: min(1440px, 100%);
  margin: 0 auto;
  padding: 8px 4px 28px;
  /* 审核操作保留状态语义，但将高饱和按钮收敛到灰白审核工作台的色阶。 */
  --audit-control-primary: color-mix(in srgb, var(--zh-text-theme) 68%, var(--zh-text-primary) 32%);
  --audit-control-primary-hover: color-mix(in srgb, var(--zh-text-theme) 78%, var(--zh-text-primary) 22%);
  --audit-control-primary-soft: color-mix(in srgb, var(--zh-text-theme) 8%, var(--zh-background-primary));
  --audit-control-primary-border: color-mix(in srgb, var(--zh-text-theme) 25%, var(--zh-line-border));
  --audit-control-danger: color-mix(in srgb, var(--zh-red) 64%, var(--zh-text-primary) 36%);
  --audit-control-danger-hover: color-mix(in srgb, var(--zh-red) 74%, var(--zh-text-primary) 26%);
  --audit-control-danger-soft: color-mix(in srgb, var(--zh-red) 7%, var(--zh-background-primary));
  --audit-control-danger-border: color-mix(in srgb, var(--zh-red) 24%, var(--zh-line-border));
  --audit-control-warning: color-mix(in srgb, var(--zh-orange) 64%, var(--zh-text-primary) 36%);
  --audit-control-warning-soft: color-mix(in srgb, var(--zh-orange) 8%, var(--zh-background-primary));
  --audit-control-warning-border: color-mix(in srgb, var(--zh-orange) 24%, var(--zh-line-border));
  --audit-control-success: color-mix(in srgb, var(--zh-green) 68%, var(--zh-text-primary) 32%);
  --audit-control-success-hover: color-mix(in srgb, var(--zh-green) 78%, var(--zh-text-primary) 22%);
}

.moderation-page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 0 24px;
}

.moderation-kicker,
.moderation-drawer-header p,
.preview-panel-header p,
.submission-content-heading > span {
  margin: 0;
  color: var(--zh-text-theme);
  font-family: var(--zh-font-number);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: var(--zh-tracking-wider);
}

.moderation-page-header h1 {
  margin: 7px 0 0;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size30);
  font-weight: 600;
  letter-spacing: var(--zh-tracking-tight);
  line-height: 1.2;
  text-wrap: balance;
}

.moderation-page-intro {
  max-width: 580px;
  margin: 9px 0 0;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
}

.moderation-refresh {
  flex: none;
  margin: 0;
  border-color: var(--zh-line-border);
  color: var(--zh-text-secondary);
  transition: color 200ms ease, background-color 200ms ease, transform 200ms ease;
}

.moderation-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
}

.moderation-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.moderation-filters :deep(.el-select) {
  width: 128px;
}

.moderation-table-card {
  overflow: hidden;
}

.moderation-table-card :deep(.el-card__body) {
  padding: 0 20px 20px;
}
/* ===== Tab 分段控件样式覆盖 ===== */
:deep(.audit-tab-group) {
  background: var(--zh-background-option);
  border-radius: var(--zh-radius8);
  padding: 2px;
}
:deep(.audit-tab-group .el-radio-button__inner) {
  border: none !important;
  box-shadow: none !important;
  background: transparent;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size14);
  font-weight: 400;
  padding: 7px 20px;
  border-radius: calc(var(--zh-radius8) - 2px);
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
:deep(.audit-tab-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--zh-background-capsule);
  color: var(--zh-text-theme);
  font-weight: 600;
  box-shadow: var(--zh-shadow1) !important;
}

:deep(.moderation-detail-drawer) {
  max-width: 94vw;
  --audit-control-primary: color-mix(in srgb, var(--zh-text-theme) 68%, var(--zh-text-primary) 32%);
  --audit-control-primary-hover: color-mix(in srgb, var(--zh-text-theme) 78%, var(--zh-text-primary) 22%);
  --audit-control-primary-soft: color-mix(in srgb, var(--zh-text-theme) 8%, var(--zh-background-primary));
  --audit-control-primary-border: color-mix(in srgb, var(--zh-text-theme) 25%, var(--zh-line-border));
  --audit-control-danger: color-mix(in srgb, var(--zh-red) 64%, var(--zh-text-primary) 36%);
  --audit-control-danger-hover: color-mix(in srgb, var(--zh-red) 74%, var(--zh-text-primary) 26%);
  --audit-control-danger-soft: color-mix(in srgb, var(--zh-red) 7%, var(--zh-background-primary));
  --audit-control-danger-border: color-mix(in srgb, var(--zh-red) 24%, var(--zh-line-border));
  --audit-control-warning: color-mix(in srgb, var(--zh-orange) 64%, var(--zh-text-primary) 36%);
  --audit-control-warning-soft: color-mix(in srgb, var(--zh-orange) 8%, var(--zh-background-primary));
  --audit-control-warning-border: color-mix(in srgb, var(--zh-orange) 24%, var(--zh-line-border));
  --audit-control-success: color-mix(in srgb, var(--zh-green) 68%, var(--zh-text-primary) 32%);
  --audit-control-success-hover: color-mix(in srgb, var(--zh-green) 78%, var(--zh-text-primary) 22%);
}

:deep(.moderation-detail-drawer .el-drawer__header) {
  align-items: center;
  min-height: 96px;
  margin: 0;
  padding: 0 30px;
  border-bottom: 1px solid var(--zh-line-border);
}

:deep(.moderation-detail-drawer .el-drawer__body) {
  min-height: 0;
  padding: 0;
  overflow: hidden;
}

:deep(.moderation-detail-drawer .el-drawer__close-btn) {
  width: 34px;
  height: 34px;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-secondary);
  transition: color 200ms ease, background-color 200ms ease;
}

:deep(.moderation-detail-drawer .el-drawer__close-btn:hover) {
  color: var(--zh-text-primary);
  background: var(--zh-background-option);
}

.moderation-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 28px;
}

.moderation-drawer-header h2 {
  margin: 7px 0 0;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size24);
  font-weight: 600;
  letter-spacing: var(--zh-tracking-tight);
  line-height: 1.25;
}

.moderation-drawer-header h2 span {
  color: var(--zh-text-caption);
  font-family: var(--zh-font-number);
  font-weight: 500;
}

.drawer-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  font-weight: 500;
}

.drawer-status-tag i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--warning) {
  --el-tag-text-color: var(--audit-control-warning);
  --el-tag-border-color: var(--audit-control-warning-border);
  --el-tag-bg-color: var(--audit-control-warning-soft);
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--warning i) {
  background: var(--audit-control-warning) !important;
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--danger) {
  --el-tag-text-color: var(--audit-control-danger);
  --el-tag-border-color: var(--audit-control-danger-border);
  --el-tag-bg-color: var(--audit-control-danger-soft);
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--danger i) {
  background: var(--audit-control-danger) !important;
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--success) {
  --el-tag-text-color: var(--audit-control-success);
  --el-tag-border-color: color-mix(in srgb, var(--zh-green) 24%, var(--zh-line-border));
  --el-tag-bg-color: color-mix(in srgb, var(--zh-green) 7%, var(--zh-background-primary));
}

:deep(.moderation-detail-drawer .drawer-status-tag.el-tag--success i) {
  background: var(--audit-control-success) !important;
}

.moderation-detail-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.8fr) minmax(0, 1.4fr);
  height: calc(100dvh - 96px);
  min-height: 0;
}

.moderation-task-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  padding: 24px;
  overflow: auto;
  background: var(--zh-background-primary);
}

.task-target-summary {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--zh-line-theme20);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-weaken);
}

.task-target-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--zh-radius10);
  color: var(--zh-text-white);
  background: var(--zh-gradient-blue);
  font-size: var(--zh-font-size16);
  font-weight: 600;
}

.task-target-summary > div:last-child {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.task-target-summary span,
.task-target-summary small {
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-target-summary strong {
  overflow: hidden;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  font-weight: 600;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-section-heading,
.submission-content-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-section-heading > span {
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  font-weight: 600;
}

.task-meta-list {
  display: grid;
  gap: 0;
  margin: 10px 0 0;
}

.task-meta-list > div {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--zh-line-parting);
}

.task-meta-list dt,
.submission-attribute-list dt {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
}

.task-meta-list dd,
.submission-attribute-list dd {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--zh-text-secondary);
  font-family: var(--zh-font-number);
  font-size: var(--zh-font-size12);
  line-height: 1.5;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-note {
  padding: 14px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: var(--zh-background-light);
}

.task-note-warning {
  border-color: color-mix(in srgb, var(--zh-orange) 26%, var(--zh-line-border));
  background: color-mix(in srgb, var(--zh-orange) 7%, var(--zh-background-primary));
}

.task-note > span {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
  font-weight: 500;
}

.task-note p {
  margin: 7px 0 0;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size13);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.task-action-panel {
  display: grid;
  gap: 14px;
  margin-top: auto;
  padding: 16px;
  border: 1px solid var(--zh-line-theme20);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-weaken);
}

.task-action-panel strong {
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  font-weight: 600;
}

.task-action-panel p {
  margin: 5px 0 0;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size12);
  line-height: 1.6;
}

.task-action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.task-action-buttons :deep(.el-button) {
  min-width: 108px;
  margin: 0;
  font-weight: 600;
}

/* 表格与抽屉里的操作按钮共用一套低饱和审核色。 */
:deep(.moderation-table-card .el-button.is-link.el-button--primary),
:deep(.moderation-detail-drawer .el-button.is-link.el-button--primary) {
  --el-button-text-color: var(--audit-control-primary);
  --el-button-hover-link-text-color: var(--audit-control-primary-hover);
  --el-button-hover-text-color: var(--audit-control-primary-hover);
  --el-button-active-color: var(--audit-control-primary-hover);
  --el-button-active-text-color: var(--audit-control-primary-hover);
}

:deep(.moderation-table-card .el-button.is-link.el-button--success) {
  --el-button-text-color: var(--audit-control-success);
  --el-button-hover-link-text-color: var(--audit-control-success-hover);
  --el-button-hover-text-color: var(--audit-control-success-hover);
  --el-button-active-color: var(--audit-control-success-hover);
  --el-button-active-text-color: var(--audit-control-success-hover);
}

:deep(.moderation-table-card .el-button.is-link.el-button--danger) {
  --el-button-text-color: var(--audit-control-danger);
  --el-button-hover-link-text-color: var(--audit-control-danger-hover);
  --el-button-hover-text-color: var(--audit-control-danger-hover);
  --el-button-active-color: var(--audit-control-danger-hover);
  --el-button-active-text-color: var(--audit-control-danger-hover);
}

:deep(.moderation-detail-drawer .task-action-buttons .el-button--primary) {
  --el-button-text-color: var(--zh-text-white);
  --el-button-bg-color: var(--audit-control-primary);
  --el-button-border-color: var(--audit-control-primary);
  --el-button-hover-text-color: var(--zh-text-white);
  --el-button-hover-bg-color: var(--audit-control-primary-hover);
  --el-button-hover-border-color: var(--audit-control-primary-hover);
  --el-button-active-color: var(--zh-text-white);
  --el-button-active-text-color: var(--zh-text-white);
  --el-button-active-bg-color: var(--audit-control-primary-hover);
  --el-button-active-border-color: var(--audit-control-primary-hover);
}

:deep(.moderation-detail-drawer .task-action-buttons .el-button--danger:not(.is-plain)) {
  --el-button-text-color: var(--zh-text-white);
  --el-button-bg-color: var(--audit-control-danger);
  --el-button-border-color: var(--audit-control-danger);
  --el-button-hover-text-color: var(--zh-text-white);
  --el-button-hover-bg-color: var(--audit-control-danger-hover);
  --el-button-hover-border-color: var(--audit-control-danger-hover);
  --el-button-active-color: var(--zh-text-white);
  --el-button-active-text-color: var(--zh-text-white);
  --el-button-active-bg-color: var(--audit-control-danger-hover);
  --el-button-active-border-color: var(--audit-control-danger-hover);
}

:deep(.moderation-detail-drawer .task-action-buttons .el-button--danger.is-plain) {
  --el-button-text-color: var(--audit-control-danger);
  --el-button-bg-color: var(--audit-control-danger-soft);
  --el-button-border-color: var(--audit-control-danger-border);
  --el-button-hover-text-color: var(--audit-control-danger-hover);
  --el-button-hover-link-text-color: var(--audit-control-danger-hover);
  --el-button-hover-bg-color: color-mix(in srgb, var(--zh-red) 12%, var(--zh-background-primary));
  --el-button-hover-border-color: var(--audit-control-danger-hover);
  --el-button-active-color: var(--audit-control-danger-hover);
  --el-button-active-text-color: var(--audit-control-danger-hover);
  --el-button-active-bg-color: color-mix(in srgb, var(--zh-red) 12%, var(--zh-background-primary));
  --el-button-active-border-color: var(--audit-control-danger-hover);
}

.task-action-buttons :deep(.el-button:active),
.moderation-refresh:active {
  transform: scale(.98);
}

.moderation-preview-panel {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  border-left: 1px solid var(--zh-line-border);
  background: var(--zh-background-light);
}

.preview-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px 20px;
  border-bottom: 1px solid var(--zh-line-border);
  background: var(--zh-background-primary);
}

.preview-panel-header h3 {
  margin: 5px 0 0;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size20);
  font-weight: 600;
}

.preview-panel-header span {
  display: block;
  margin-top: 6px;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
  line-height: 1.5;
}

.submission-preview-viewport {
  flex: 1;
  min-height: 0;
  padding: 24px 28px 32px;
  overflow: auto;
}

.submission-preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 18px;
}

.submission-preview-header h4 {
  margin: 10px 0 0;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size20);
  font-weight: 600;
  letter-spacing: var(--zh-tracking-tight);
  line-height: 1.4;
}

.submission-preview-header p {
  max-width: 620px;
  margin: 8px 0 0;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
  line-height: 1.7;
  white-space: pre-wrap;
}

.submission-preview-header > span {
  flex: none;
  padding: 6px 8px;
  border-radius: var(--zh-radius6);
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font: 600 var(--zh-font-size12) var(--zh-font-number);
}

.submission-attribute-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 20px;
}

.submission-attribute-list > div {
  min-width: 0;
  padding: 10px 11px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius8);
  background: var(--zh-background-primary);
}

.submission-attribute-list dd {
  margin-top: 5px;
  color: var(--zh-text-primary);
  font-family: var(--zh-font-text);
  text-align: left;
}

.submission-content {
  padding: 18px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-primary);
}

.submission-content-heading {
  margin-bottom: 14px;
}

.submission-content-heading strong {
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  font-weight: 600;
}

/* ===== 表格行悬浮过渡 ===== */
:deep(.audit-table-row) {
  transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 待审核行 — 左侧橙色强调条 ===== */
:deep(.pending-row td:first-child) {
  position: relative;
}
:deep(.pending-row td:first-child::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--zh-orange);
}

/* ===== 表格加载遮罩样式 ===== */
:deep(.el-loading-mask) {
  background: var(--zh-background-mask10);
}

/* ===== 骨架屏 ===== */
.skeleton-loader {
  background: linear-gradient(
    90deg,
    var(--zh-background-light-gray) 25%,
    var(--zh-background-light-grey) 50%,
    var(--zh-background-light-gray) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--zh-radius4);
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@media (max-width: 760px) {
  .moderation-page-header,
  .moderation-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .moderation-page-header {
    gap: 16px;
  }

  .moderation-page-header h1 {
    font-size: var(--zh-font-size24);
  }

  .moderation-refresh {
    align-self: flex-start;
  }

  .moderation-filters {
    width: 100%;
  }

  .moderation-filters :deep(.el-select) {
    flex: 1;
    width: auto;
  }

  :deep(.moderation-detail-drawer .el-drawer__header) {
    min-height: 82px;
    padding: 0 20px;
  }

  .moderation-drawer-header {
    padding-right: 20px;
  }

  .moderation-drawer-header h2 {
    font-size: var(--zh-font-size20);
  }

  .moderation-detail-layout {
    display: block;
    height: auto;
  }

  .moderation-task-panel,
  .submission-preview-viewport {
    overflow: visible;
  }

  .moderation-preview-panel {
    border-top: 1px solid var(--zh-line-border);
    border-left: 0;
  }

  .submission-attribute-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ai-review-cell { display: grid; justify-items: start; gap: 3px; }
.audit-queues { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; }
.audit-policy { margin: 0 0 16px; padding: 12px 16px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; color: #1e3a8a; line-height: 1.7; }
.audit-policy p { margin: 4px 0; }
.audit-queues :deep(.el-button) { margin-left: 0; }
.ai-review-cell small,.ai-review-pending { color: var(--zh-text-caption); font-size: 11px; }
.ai-review-report ul { margin: 8px 0; padding-left: 18px; }
.ai-review-report li { margin: 5px 0; line-height: 1.5; overflow-wrap: anywhere; }
.ai-review-report small { display: block; margin-top: 10px; color: var(--zh-text-caption); }
</style>
