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
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import {
  Refresh,
  View,
  Select,
  Close,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getModerationTasks,
  createModerationDecision,
  getReports,
  resolveReport,
} from '@/apis/moderation'

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
  { label: 'Skill', value: 'skill' },
  { label: '案例', value: 'case' },
]

/** 内容类型 → 显示标签映射 */
const CONTENT_TYPE_LABEL_MAP = { skill: 'Skill', case: '案例' }

/** 内容类型 → Tag 类型映射 */
const CONTENT_TYPE_TAG_TYPE_MAP = { skill: 'info', case: '' }

/** 内容类型 → 图标映射 */
const CONTENT_TYPE_ICON_MAP = { skill: '⚡', case: '📋' }

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
})

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

/** 操作执行中 */
const isActionLoading = ref(false)

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
  isTableLoading.value = true
  try {
    const res = await getModerationTasks({
      status: filters.status || undefined,
      target_type: filters.type || undefined,
      page: pagination.currentPage,
      size: pagination.pageSize,
    })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '审核任务加载失败')
      contentList.value = []
      pagination.total = 0
      return
    }
    contentList.value = res?.data?.records || []
    pagination.total = res?.data?.total || 0
  } catch {
    ElMessage.error('审核任务加载失败，请稍后重试')
    contentList.value = []
    pagination.total = 0
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 拉取举报列表（API-95）
 * 状态筛选由后端处理，空值不传避免空字符串匹配不到数据
 */
const fetchReports = async () => {
  isTableLoading.value = true
  try {
    const res = await getReports({
      status: filters.status || undefined,
      page: pagination.currentPage,
      size: pagination.pageSize,
    })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '举报数据加载失败')
      reportList.value = []
      pagination.total = 0
      return
    }
    reportList.value = res?.data?.records || []
    pagination.total = res?.data?.total || 0
  } catch {
    ElMessage.error('举报数据加载失败，请稍后重试')
    reportList.value = []
    pagination.total = 0
  } finally {
    isTableLoading.value = false
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
 * 获取内容类型图标
 */
const getContentIcon = (type) => CONTENT_TYPE_ICON_MAP[type] || ''

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
  drawerVisible.value = true
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
const handleReject = (row) => {
  ElMessageBox.prompt('请输入驳回理由（将通过通知发送给作者）', '驳回内容', {
    confirmButtonText: '确认驳回',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
    inputType: 'textarea',
    inputPlaceholder: '请输入驳回理由...',
    inputValidator: (val) => {
      if (!val || !val.trim()) return '请填写驳回理由'
      return true
    },
  })
    .then(({ value }) => {
      submitDecision(row.id, 'reject', value.trim())
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
  isActionLoading.value = true
  try {
    const res = await createModerationDecision(taskId, { action, comment })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '审核操作失败')
      return
    }
    ElMessage.success(action === 'approve' ? '审核通过，内容已公开' : '已驳回，内容已下架')
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
  window.removeEventListener('admin-refresh', handleRefresh)
})
</script>

<template>
  <div>
    <!-- ===================================================================
         1. 标题区 + Tab 分段
         =================================================================== -->
    <div class="flex items-center justify-between flex-wrap gap-3 mb-4">
      <!-- 左侧：标题 -->
      <h1
        class="text-lg font-semibold shrink-0"
        style="
          font-size: var(--zh-font-size18);
          color: var(--zh-text-primary);
        "
      >
        内容审核与治理
      </h1>

      <!-- 右侧：刷新按钮 -->
      <el-tooltip content="刷新列表" placement="bottom" effect="dark">
        <el-button
          :icon="Refresh"
          circle
          size="default"
          @click="handleRefresh"
        />
      </el-tooltip>
    </div>

    <!-- Tab 分段控件 -->
    <div class="mb-4">
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
    </div>

    <!-- ===================================================================
         2. 筛选器组（根据 Tab 动态调整）
         =================================================================== -->
    <div class="flex items-center flex-wrap gap-3 mb-4">
      <!-- 内容类型筛选（仅审核 Tab） -->
      <el-select
        v-if="activeTab === 'audit'"
        v-model="filters.type"
        placeholder="全部类型"
        clearable
        size="default"
        style="width: 120px;"
        @change="handleFilterChange"
      >
        <el-option
          v-for="opt in CONTENT_TYPE_OPTIONS"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>

      <!-- 状态筛选 -->
      <el-select
        v-model="filters.status"
        placeholder="全部状态"
        clearable
        size="default"
        style="width: 130px;"
        @change="handleFilterChange"
      >
        <el-option
          v-for="opt in (activeTab === 'audit' ? AUDIT_STATUS_OPTIONS : REPORT_STATUS_OPTIONS)"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>

    <!-- ===================================================================
         3. 数据表格区
         =================================================================== -->
    <el-card
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
                  {{ getContentIcon(row.target_type) }} {{ CONTENT_TYPE_LABEL_MAP[row.target_type] || row.target_type }}
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
                    详情
                  </el-button>

                  <!-- 待审核：通过 + 驳回 -->
                  <template v-if="row.status === 'pending'">
                    <el-button
                      type="success"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleApprove(row)"
                    >
                      <el-icon class="mr-0.5"><Select /></el-icon>
                      通过
                    </el-button>
                    <el-button
                      type="danger"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleReject(row)"
                    >
                      <el-icon class="mr-0.5"><Close /></el-icon>
                      驳回
                    </el-button>
                  </template>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无审核任务" :image-size="80">
                <template v-if="filters.type || filters.status">
                  <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                    没有符合条件的审核任务，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="filters.type = ''; filters.status = ''; handleFilterChange();"
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
                  {{ getContentIcon(row.target_type) }} {{ CONTENT_TYPE_LABEL_MAP[row.target_type] || row.target_type }}
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
         4. 内容审核详情抽屉
         =================================================================== -->
    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="560px"
      destroy-on-close
      :style="{
        '--el-drawer-bg-color': 'var(--zh-background-primary)',
        '--el-drawer-padding-primary': '24px',
      }"
    >
      <template #header>
        <span style="font-size: var(--zh-font-size16); font-weight: 600; color: var(--zh-text-primary);">
          {{ (drawerMode === 'audit' ? '审核任务详情 — ' : '举报详情 — ') + (currentContent?.id || '') }}
        </span>
      </template>

      <template v-if="currentContent">
        <!-- ===== 审核任务/举报详情（共享 AuditVO 结构） ===== -->
        <template v-if="drawerMode !== 'content'">
          <!-- 任务信息区 -->
          <div
            class="rounded-lg p-4 mb-4"
            style="border: 1px solid var(--zh-line-border);"
          >
            <div class="grid grid-cols-[80px_1fr] gap-y-3 gap-x-2">
              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">目标类型</span>
              <span>
                <el-tag :type="getContentTagType(currentContent.target_type)" size="small" effect="plain">
                  {{ getContentIcon(currentContent.target_type) }} {{ CONTENT_TYPE_LABEL_MAP[currentContent.target_type] || currentContent.target_type }}
                </el-tag>
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">目标内容</span>
              <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size14); color: var(--zh-text-secondary);">
                #{{ currentContent.target_id }}
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">提交时间</span>
              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                {{ formatDateTime(currentContent.created_at) }}
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">处理时间</span>
              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                {{ formatDateTime(currentContent.processed_at) }}
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">处理人</span>
              <span style="font-size: var(--zh-font-size14); color: var(--zh-text-secondary);">
                {{ currentContent.handler_id ? '管理员 #' + currentContent.handler_id : '—' }}
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">审核状态</span>
              <span>
                <el-tag :type="getStatusTagType(currentContent.status)" size="small" effect="plain">
                  <span class="flex items-center gap-1.5">
                    <span
                      class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                      :style="{ background: getStatusDotColor(currentContent.status) }"
                    ></span>
                    {{ getStatusLabel(currentContent.status) }}
                  </span>
                </el-tag>
              </span>

              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">处理结果</span>
              <span style="font-size: var(--zh-font-size14); color: var(--zh-text-secondary);">
                {{ currentContent.status === 'processed' ? (AUDIT_ACTION_LABEL_MAP[currentContent.action] || currentContent.action) : '—' }}
              </span>
            </div>
          </div>

          <!-- 审核理由区 -->
          <div
            v-if="currentContent.reason"
            class="rounded-lg p-4 mb-4"
            style="border: 1px solid var(--zh-line-border); background: var(--zh-background-light-gray);"
          >
            <span style="font-size: var(--zh-font-size12); color: var(--zh-text-caption); display: block; margin-bottom: 8px;">审核理由</span>
            <p style="font-size: var(--zh-font-size14); color: var(--zh-text-primary); line-height: 1.7; white-space: pre-wrap; margin: 0;">
              {{ currentContent.reason }}
            </p>
          </div>

          <!-- 处理意见区 -->
          <div
            v-if="currentContent.comment"
            class="rounded-lg p-4 mb-4"
            style="border: 1px solid var(--zh-line-border); background: var(--zh-background-light-gray);"
          >
            <span style="font-size: var(--zh-font-size12); color: var(--zh-text-caption); display: block; margin-bottom: 8px;">处理意见</span>
            <p style="font-size: var(--zh-font-size14); color: var(--zh-text-primary); line-height: 1.7; white-space: pre-wrap; margin: 0;">
              {{ currentContent.comment }}
            </p>
          </div>

          <!-- 操作区（仅待处理） -->
          <div
            v-if="currentContent.status === 'pending'"
            class="rounded-lg p-4"
            style="border: 1px solid var(--zh-line-border); background: var(--zh-background-light-gray);"
          >
            <span style="font-size: var(--zh-font-size14); font-weight: 600; color: var(--zh-text-primary); display: block; margin-bottom: 12px;">
              {{ drawerMode === 'audit' ? '审核操作' : '举报处理' }}
            </span>

            <div class="flex flex-wrap gap-2">
              <!-- 审核 Tab：通过 / 驳回（API-91） -->
              <template v-if="drawerMode === 'audit'">
                <el-button
                  type="success"
                  :loading="isActionLoading"
                  :style="{ borderRadius: 'var(--zh-radius8)' }"
                  @click="handleApprove(currentContent); drawerVisible = false;"
                >
                  <el-icon class="mr-1"><Select /></el-icon>
                  审核通过
                </el-button>
                <el-button
                  type="danger"
                  :loading="isActionLoading"
                  :style="{ borderRadius: 'var(--zh-radius8)' }"
                  @click="handleReject(currentContent); drawerVisible = false;"
                >
                  <el-icon class="mr-1"><Close /></el-icon>
                  驳回
                </el-button>
              </template>

              <!-- 举报 Tab：确认违规 / 驳回举报（API-96） -->
              <template v-else>
                <el-button
                  type="danger"
                  :loading="isActionLoading"
                  :style="{ borderRadius: 'var(--zh-radius8)' }"
                  @click="handleConfirmViolation(currentContent); drawerVisible = false;"
                >
                  <el-icon class="mr-1"><Select /></el-icon>
                  确认违规
                </el-button>
                <el-button
                  :loading="isActionLoading"
                  :style="{ borderRadius: 'var(--zh-radius8)' }"
                  @click="handleDismissReport(currentContent); drawerVisible = false;"
                >
                  <el-icon class="mr-1"><Close /></el-icon>
                  驳回举报
                </el-button>
              </template>
            </div>
          </div>
        </template>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
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

/* ===== 脉冲动画（敏感词预警图标） ===== */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
