<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDrawer, ElSkeleton, ElEmpty, ElMessageBox, ElMessage, ElTooltip, ElRadioGroup, ElRadioButton
    - ElementPlus Icons: Search, Refresh, View, Select, Close, Download, Delete, WarningFilled, Star
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount` from Vue
  - 依赖:
    - 无外部 API 调用，当前使用静态示例数据（后续替换为后端 API）
  - 输入: 无 props，数据在组件内部 mock
  - 输出: 渲染内容审核与社区治理视图（Tab 切换 + 工具栏 + 数据表格 + 分页器 + 审核详情抽屉）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
-->

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  Search,
  Refresh,
  View,
  Select,
  Close,
  Download,
  Delete,
  WarningFilled,
  Star,
  Top,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

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

/** 内容审核状态筛选项 */
const AUDIT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
  { label: '已下架', value: 'removed' },
]

/** 审核状态 → 显示标签映射 */
const AUDIT_STATUS_LABEL_MAP = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  removed: '已下架',
}

/** 审核状态 → Tag 类型映射 */
const AUDIT_STATUS_TAG_TYPE_MAP = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  removed: 'info',
}

/** 审核状态 → 圆点颜色映射 */
const AUDIT_STATUS_DOT_COLOR_MAP = {
  pending: 'var(--zh-orange)',
  approved: 'var(--zh-green)',
  rejected: 'var(--zh-red)',
  removed: 'var(--zh-text-disabled)',
}

/** 举报状态筛选项 */
const REPORT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'resolved' },
  { label: '已驳回举报', value: 'dismissed' },
]

/** 举报状态 → 显示标签映射 */
const REPORT_STATUS_LABEL_MAP = {
  pending: '待处理',
  resolved: '已处理',
  dismissed: '已驳回举报',
}

/** 举报状态 → Tag 类型映射 */
const REPORT_STATUS_TAG_TYPE_MAP = {
  pending: 'warning',
  resolved: 'success',
  dismissed: 'info',
}

/** 举报状态 → 圆点颜色映射 */
const REPORT_STATUS_DOT_COLOR_MAP = {
  pending: 'var(--zh-orange)',
  resolved: 'var(--zh-green)',
  dismissed: 'var(--zh-text-disabled)',
}

/** 敏感词严重程度配置 */
const SENSITIVITY_LEVEL_MAP = {
  high: { label: '高', color: 'var(--zh-red)', tagType: 'danger' },
  medium: { label: '中', color: 'var(--zh-orange)', tagType: 'warning' },
  low: { label: '低', color: 'var(--zh-cyan)', tagType: 'info' },
}

/** 敏感词类别列表 */
const SENSITIVITY_CATEGORIES = ['政治敏感', '色情低俗', '暴力恐怖', '违法犯罪', '侵权内容']

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
  keyword: '',
})

/** 分页参数 */
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** 详情抽屉可见性 */
const drawerVisible = ref(false)

/** 当前查看的内容数据 */
const currentContent = ref(null)

/** 驳回理由输入 */
const rejectReason = ref('')

/** 操作执行中 */
const isActionLoading = ref(false)

// ===================================================================
// Mock 数据生成
// ===================================================================

/**
 * 生成模拟审核内容数据
 * @returns {Array} 内容对象数组
 */
const generateMockContents = () => {
  const authors = [
    { name: '张老师', id: 'T0042' },
    { name: '李老师', id: 'T0015' },
    { name: '王老师', id: 'T0028' },
    { name: '赵老师', id: 'T0007' },
    { name: '陈老师', id: 'T0053' },
    { name: '刘老师', id: 'T0031' },
    { name: '周老师', id: 'T0019' },
    { name: '吴老师', id: 'T0046' },
  ]
  const types = ['skill', 'case']
  const grades = ['小学', '初中', '高中', '大学']
  const subjects = ['数学', '语文', '英语', '物理', '化学', '历史']
  const lessonTypes = ['新授课', '复习课', '习题课', '实验课']
  const statuses = ['pending', 'approved', 'rejected', 'removed']

  // 预定义 20 条真实感内容
  const templates = [
    { title: '勾股定理互动教学案例', type: 'case', grade: '初中', subject: '数学', lessonType: '新授课' },
    { title: '串联电路Skill模板', type: 'skill', grade: '初中', subject: '物理', lessonType: '实验课' },
    { title: '背影课文精读案例', type: 'case', grade: '初中', subject: '语文', lessonType: '复习课' },
    { title: '化学方程式配平Skill', type: 'skill', grade: '高中', subject: '化学', lessonType: '习题课' },
    { title: '三角函数图像变换案例', type: 'case', grade: '高中', subject: '数学', lessonType: '新授课' },
    { title: '英语虚拟语气讲解Skill', type: 'skill', grade: '高中', subject: '英语', lessonType: '复习课' },
    { title: '辛亥革命历史重现案例', type: 'case', grade: '初中', subject: '历史', lessonType: '新授课' },
    { title: '牛顿第二定律实验Skill', type: 'skill', grade: '高中', subject: '物理', lessonType: '实验课' },
    { title: '分数加减法互动课件案例', type: 'case', grade: '小学', subject: '数学', lessonType: '新授课' },
    { title: '光合作用探究Skill', type: 'skill', grade: '高中', subject: '化学', lessonType: '实验课' },
    { title: '定语从句精讲案例', type: 'case', grade: '高中', subject: '英语', lessonType: '新授课' },
    { title: '一次函数图像绘制Skill', type: 'skill', grade: '初中', subject: '数学', lessonType: '习题课' },
    { title: '古诗词鉴赏万能Skill模板', type: 'skill', grade: '高中', subject: '语文', lessonType: '复习课' },
    { title: '电路故障诊断案例集', type: 'case', grade: '初中', subject: '物理', lessonType: '习题课' },
    { title: '有机化学官能团识别Skill', type: 'skill', grade: '高中', subject: '化学', lessonType: '新授课' },
    { title: '地球公转自转演示案例', type: 'case', grade: '小学', subject: '语文', lessonType: '新授课' },
    { title: '概率统计趣味教学案例', type: 'case', grade: '高中', subject: '数学', lessonType: '新授课' },
    { title: '英语写作框架Skill', type: 'skill', grade: '初中', subject: '英语', lessonType: '复习课' },
    { title: '文言文翻译五步法Skill', type: 'skill', grade: '高中', subject: '语文', lessonType: '新授课' },
    { title: '电磁感应现象演示案例', type: 'case', grade: '高中', subject: '物理', lessonType: '实验课' },
  ]

  const contents = templates.map((tpl, i) => {
    const id = `C${String(i + 1).padStart(4, '0')}`
    const author = authors[i % authors.length]
    const status = statuses[i % statuses.length]
    // 前 8 条中的部分设为待审核以丰富数据
    const actualStatus = i < 8 ? statuses[i % 4] : statuses[i % statuses.length]
    // 部分待审核项包含敏感词
    const hasSensitive = actualStatus === 'pending' && i % 3 === 0
    const day = 27 - i
    const hour = 9 + (i % 12)
    const min = (i * 7) % 60

    return {
      id,
      title: tpl.title,
      type: tpl.type,
      author: author.name,
      authorId: author.id,
      grade: tpl.grade,
      subject: tpl.subject,
      lessonType: tpl.lessonType,
      status: actualStatus,
      submittedAt: `2026-07-${String(day).padStart(2, '0')} ${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`,
      description: `这是「${tpl.title}」的完整内容描述。适用于${tpl.grade}${tpl.subject}${tpl.lessonType}场景。\n\n教师可以通过此${
        tpl.type === 'skill' ? 'Skill模板快速生成符合教学要求的课件，支持自定义参数配置。' : '案例了解完整的教学流程设计，包含导入、讲解、互动、总结等环节。'
      }\n\n使用方法：选择目标课程后，在创作工作台中基于此${
        tpl.type === 'skill' ? '模板' : '案例'
      }进行二次创作，可绑定个人资源库中的素材。`,
      hasSensitive,
      sensitiveHits: hasSensitive
        ? [
            {
              position: '第2段',
              keyword: '不当言论示例A',
              category: SENSITIVITY_CATEGORIES[0],
              level: 'medium',
            },
            {
              position: '第5段',
              keyword: '违规内容示例B',
              category: SENSITIVITY_CATEGORIES[1],
              level: 'low',
            },
            {
              position: '第8段',
              keyword: '敏感词示例C',
              category: SENSITIVITY_CATEGORIES[2],
              level: 'high',
            },
          ]
        : [],
      isRecommended: actualStatus === 'approved' && i % 5 === 0,
      version: `v${Math.floor(i / 5) + 1}.${i % 5}`,
      auditHistory: [
        {
          time: `2026-07-${String(day).padStart(2, '0')} ${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`,
          action: '提交',
          operator: author.name,
          reason: '',
        },
      ],
    }
  })

  return contents
}

/**
 * 生成模拟举报数据
 * @param {Array} contents - 审核内容列表（用于关联）
 * @returns {Array} 举报对象数组
 */
const generateMockReports = (contents) => {
  const reporters = ['孙老师', '钱老师', '杨老师', '黄老师', '马老师', '胡老师']
  const reasons = [
    '内容涉及敏感政治言论，建议立即审查',
    '课件包含不实信息，误导学生',
    '涉嫌抄袭他人作品，侵犯版权',
    '包含商业广告推广内容',
    '内容质量低劣，存在明显知识性错误',
    '使用了未经授权的教材图片',
    '标题与实际内容严重不符，存在欺骗行为',
    '包含不当言论和歧视性表述',
  ]
  const reportStatuses = ['pending', 'resolved', 'dismissed']

  // 选取部分已通过的内容作为被举报目标
  const targetContents = contents.filter((c) => c.status === 'approved').slice(0, 10)

  return targetContents.map((content, i) => {
    const id = `R${String(i + 1).padStart(4, '0')}`
    const reporter = reporters[i % reporters.length]
    const day = 27 - i
    const hour = 14 + (i % 8)
    const min = (i * 13) % 60

    return {
      id,
      contentId: content.id,
      contentTitle: content.title,
      contentAuthor: content.author,
      reporter,
      reporterId: `T${String(i * 7 + 10).padStart(4, '0')}`,
      reason: reasons[i % reasons.length],
      reportedAt: `2026-07-${String(day).padStart(2, '0')} ${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`,
      status: reportStatuses[i % reportStatuses.length],
      // 关联到源内容
      contentRef: content,
    }
  })
}

/** 全部审核内容（模拟数据库） */
let allContents = []

/** 全部举报数据（模拟数据库） */
let allReports = []

// ===================================================================
// 当前 Tab 对应的数据源与筛选配置
// ===================================================================

/** 当前 Tab 的数据总数 */
const currentTotal = computed(() => pagination.total)

/** 当前数据列表（根据 Tab 切换） */
const currentList = computed(() => {
  return activeTab.value === 'audit' ? contentList.value : reportList.value
})

/**
 * 发送筛选请求（模拟）
 * 根据当前 Tab 和筛选条件过滤 mock 数据
 */
const fetchData = () => {
  isTableLoading.value = true

  setTimeout(() => {
    if (activeTab.value === 'audit') {
      let filtered = [...allContents]
      if (filters.type) {
        filtered = filtered.filter((c) => c.type === filters.type)
      }
      if (filters.status) {
        filtered = filtered.filter((c) => c.status === filters.status)
      }
      if (filters.keyword.trim()) {
        const kw = filters.keyword.trim().toLowerCase()
        filtered = filtered.filter(
          (c) =>
            c.title.toLowerCase().includes(kw) ||
            c.author.toLowerCase().includes(kw),
        )
      }
      // 默认排序：待审核排最前 → 按提交时间降序
      const statusPriority = { pending: 0, rejected: 1, approved: 2, removed: 3 }
      filtered.sort((a, b) => {
        const sp = statusPriority[a.status] - statusPriority[b.status]
        if (sp !== 0) return sp
        return b.submittedAt.localeCompare(a.submittedAt)
      })
      pagination.total = filtered.length
      const start = (pagination.currentPage - 1) * pagination.pageSize
      contentList.value = filtered.slice(start, start + pagination.pageSize)
    } else {
      let filtered = [...allReports]
      if (filters.status) {
        filtered = filtered.filter((r) => r.status === filters.status)
      }
      if (filters.keyword.trim()) {
        const kw = filters.keyword.trim().toLowerCase()
        filtered = filtered.filter(
          (r) =>
            r.contentTitle.toLowerCase().includes(kw) ||
            r.reporter.toLowerCase().includes(kw) ||
            r.contentAuthor.toLowerCase().includes(kw),
        )
      }
      // 默认排序：待处理排最前
      const statusPriority = { pending: 0, resolved: 1, dismissed: 2 }
      filtered.sort((a, b) => {
        const sp = statusPriority[a.status] - statusPriority[b.status]
        if (sp !== 0) return sp
        return b.reportedAt.localeCompare(a.reportedAt)
      })
      pagination.total = filtered.length
      const start = (pagination.currentPage - 1) * pagination.pageSize
      reportList.value = filtered.slice(start, start + pagination.pageSize)
    }

    isTableLoading.value = false
  }, 300)
}

/**
 * 页面首次数据加载
 */
const loadData = () => {
  isLoading.value = true
  setTimeout(() => {
    allContents = generateMockContents()
    allReports = generateMockReports(allContents)
    isLoading.value = false
    fetchData()
  }, 600)
}

/**
 * Tab 切换处理
 * 重置筛选条件和分页
 * @param {string} tab - 目标 Tab key
 */
const handleTabChange = (tab) => {
  filters.type = ''
  filters.status = ''
  filters.keyword = ''
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
 * 搜索框输入防抖处理
 */
let searchTimer = null
const handleSearchInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    handleFilterChange()
  }, 300)
}

/**
 * 搜索框回车处理
 */
const handleSearchEnter = () => {
  clearTimeout(searchTimer)
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
 * 打开内容详情抽屉
 * @param {Object} row - 当前行内容数据
 */
const openDetailDrawer = (row) => {
  // 查找最新的源数据（可能在 allContents 中被更新过）
  const latest = allContents.find((c) => c.id === row.id) || row
  currentContent.value = reactive({ ...latest })
  rejectReason.value = ''
  drawerVisible.value = true
}

/**
 * 审核通过操作
 * @param {Object} row - 当前行内容数据
 */
const handleApprove = (row) => {
  ElMessageBox.confirm(
    `确认通过「${row.title}」的审核？内容将立即在社区中公开可见。`,
    '确认审核通过',
    {
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
      type: 'success',
      confirmButtonClass: 'el-button--success',
    },
  )
    .then(() => {
      applyAuditAction(row.id, 'approved', '审核通过')
    })
    .catch(() => {})
}

/**
 * 驳回操作 — 需要填写驳回理由
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
      applyAuditAction(row.id, 'rejected', value.trim())
    })
    .catch(() => {})
}

/**
 * 下架操作
 */
const handleRemove = (row) => {
  ElMessageBox.confirm(
    `确认下架「${row.title}」？内容将从社区广场中移除，作者可修改后重新提交。`,
    '确认下架',
    {
      confirmButtonText: '确认下架',
      cancelButtonText: '取消',
      type: 'warning',
    },
  )
    .then(() => {
      applyAuditAction(row.id, 'removed', '内容下架')
    })
    .catch(() => {})
}

/**
 * 重新上架操作
 */
const handleRelist = (row) => {
  ElMessageBox.confirm(
    `确认重新上架「${row.title}」？内容将恢复在社区中的公开展示。`,
    '确认重新上架',
    {
      confirmButtonText: '确认上架',
      cancelButtonText: '取消',
      type: 'info',
    },
  )
    .then(() => {
      applyAuditAction(row.id, 'approved', '重新上架')
    })
    .catch(() => {})
}

/**
 * 重新审核操作（用于已驳回内容）
 */
const handleReaudit = (row) => {
  ElMessageBox.confirm(
    `确认将「${row.title}」重新纳入审核队列？`,
    '确认重新审核',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'info',
    },
  )
    .then(() => {
      applyAuditAction(row.id, 'pending', '重新审核')
    })
    .catch(() => {})
}

/**
 * 执行审核动作的底层逻辑
 * @param {string} contentId - 内容 ID
 * @param {string} newStatus - 新状态
 * @param {string} reason - 操作原因/备注
 */
const applyAuditAction = (contentId, newStatus, reason) => {
  isActionLoading.value = true

  setTimeout(() => {
    const idx = allContents.findIndex((c) => c.id === contentId)
    if (idx !== -1) {
      allContents[idx].status = newStatus
      allContents[idx].auditHistory.unshift({
        time: new Date().toISOString().replace('T', ' ').slice(0, 16),
        action: AUDIT_STATUS_LABEL_MAP[newStatus] || reason,
        operator: '管理员',
        reason,
      })
    }
    // 更新抽屉中的当前查看项
    if (currentContent.value && currentContent.value.id === contentId) {
      const src = allContents.find((c) => c.id === contentId)
      if (src) {
        currentContent.value.status = src.status
        currentContent.value.auditHistory = [...src.auditHistory]
      }
    }

    const statusLabel = AUDIT_STATUS_LABEL_MAP[newStatus] || newStatus
    const content = allContents.find((c) => c.id === contentId)
    ElMessage.success(`「${content?.title || contentId}」已${statusLabel}`)

    isActionLoading.value = false
    fetchData()
  }, 400)
}

/**
 * 推荐/取消推荐切换
 */
const handleToggleRecommend = (row) => {
  const idx = allContents.findIndex((c) => c.id === row.id)
  if (idx === -1) return
  const newVal = !allContents[idx].isRecommended
  allContents[idx].isRecommended = newVal
  if (currentContent.value && currentContent.value.id === row.id) {
    currentContent.value.isRecommended = newVal
  }
  ElMessage.success(newVal ? `「${row.title}」已设为推荐` : `「${row.title}」已取消推荐`)
  fetchData()
}

/**
 * 删除内容
 */
const handleDeleteContent = (row) => {
  ElMessageBox.confirm(
    `确认永久删除「${row.title}」？此操作不可撤销，所有关联数据将被一并移除。`,
    '确认删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    },
  )
    .then(() => {
      allContents = allContents.filter((c) => c.id !== row.id)
      ElMessage.success(`已删除内容「${row.title}」`)
      if (contentList.value.length === 1 && pagination.currentPage > 1) {
        pagination.currentPage--
      }
      fetchData()
    })
    .catch(() => {})
}

/**
 * 举报管理 — 确认违规
 */
const handleConfirmViolation = (row) => {
  ElMessageBox.confirm(
    `确认被举报内容「${row.contentTitle}」违规？确认后将自动下架该内容并通知作者。`,
    '确认违规',
    {
      confirmButtonText: '确认违规',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    },
  )
    .then(() => {
      // 更新举报状态
      const rIdx = allReports.findIndex((r) => r.id === row.id)
      if (rIdx !== -1) allReports[rIdx].status = 'resolved'
      // 下架关联内容
      const cIdx = allContents.findIndex((c) => c.id === row.contentId)
      if (cIdx !== -1) {
        allContents[cIdx].status = 'removed'
        allContents[cIdx].auditHistory.unshift({
          time: new Date().toISOString().replace('T', ' ').slice(0, 16),
          action: '确认违规',
          operator: '管理员',
          reason: `举报处理：${row.reason}`,
        })
      }
      ElMessage.success(`已确认违规并下架内容「${row.contentTitle}」`)
      fetchData()
    })
    .catch(() => {})
}

/**
 * 举报管理 — 驳回举报
 */
const handleDismissReport = (row) => {
  ElMessageBox.confirm(
    `确认驳回对「${row.contentTitle}」的举报？内容不受影响，举报状态将标记为已驳回。`,
    '确认驳回举报',
    {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      type: 'info',
    },
  )
    .then(() => {
      const idx = allReports.findIndex((r) => r.id === row.id)
      if (idx !== -1) allReports[idx].status = 'dismissed'
      ElMessage.success(`已驳回对「${row.contentTitle}」的举报`)
      fetchData()
    })
    .catch(() => {})
}

/**
 * 获取敏感词等级配置
 */
const getSensitivityLevel = (level) => SENSITIVITY_LEVEL_MAP[level] || SENSITIVITY_LEVEL_MAP.low

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
        :placeholder="activeTab === 'audit' ? '全部状态' : '全部状态'"
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

      <!-- 搜索框 -->
      <el-input
        v-model="filters.keyword"
        :placeholder="activeTab === 'audit' ? '搜索标题 / 作者...' : '搜索标题 / 举报人...'"
        clearable
        size="default"
        :prefix-icon="Search"
        style="width: 240px;"
        @input="handleSearchInput"
        @keyup.enter="handleSearchEnter"
        @clear="handleFilterChange"
      />
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
            row-class-name="audit-table-row"
            element-loading-text="加载中..."
            :row-class-name="(r) => r.row.status === 'pending' ? 'audit-table-row pending-row' : r.row.hasSensitive ? 'audit-table-row sensitive-row' : 'audit-table-row'"
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：ID -->
            <el-table-column prop="id" label="ID" width="110" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：内容标题 -->
            <el-table-column prop="title" label="内容标题" min-width="220">
              <template #default="{ row }">
                <el-tooltip
                  :content="row.title"
                  placement="top"
                  effect="dark"
                  :disabled="row.title.length <= 25"
                >
                  <span
                    class="cursor-pointer hover:underline inline-block max-w-65 truncate"
                    style="font-size: var(--zh-font-size14); color: var(--zh-text-primary);"
                    @click="openDetailDrawer(row)"
                  >
                    {{ row.title }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <!-- 列：内容类型 -->
            <el-table-column prop="type" label="类型" width="110" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getContentTagType(row.type)"
                  size="small"
                  effect="plain"
                >
                  {{ getContentIcon(row.type) }} {{ CONTENT_TYPE_LABEL_MAP[row.type] }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：作者 -->
            <el-table-column prop="author" label="作者" width="120" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  {{ row.author }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：提交时间 -->
            <el-table-column prop="submittedAt" label="提交时间" width="170" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.submittedAt }}
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

            <!-- 列：操作 -->
            <el-table-column label="操作" width="250" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    type="primary"
                    link
                    size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer(row)"
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

                  <!-- 已通过：推荐 + 下架 + 删除 -->
                  <template v-if="row.status === 'approved'">
                    <el-button
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)', color: row.isRecommended ? 'var(--zh-yellow)' : 'var(--zh-text-caption)' }"
                      @click="handleToggleRecommend(row)"
                    >
                      <el-icon class="mr-0.5"><Star /></el-icon>
                      {{ row.isRecommended ? '已推荐' : '推荐' }}
                    </el-button>
                    <el-button
                      type="warning"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleRemove(row)"
                    >
                      <el-icon class="mr-0.5"><Download /></el-icon>
                      下架
                    </el-button>
                    <el-button
                      type="danger"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleDeleteContent(row)"
                    >
                      <el-icon class="mr-0.5"><Delete /></el-icon>
                      删除
                    </el-button>
                  </template>

                  <!-- 已驳回：重新审核 + 删除 -->
                  <template v-if="row.status === 'rejected'">
                    <el-button
                      type="primary"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleReaudit(row)"
                    >
                      <el-icon class="mr-0.5"><Refresh /></el-icon>
                      重审
                    </el-button>
                    <el-button
                      type="danger"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleDeleteContent(row)"
                    >
                      <el-icon class="mr-0.5"><Delete /></el-icon>
                      删除
                    </el-button>
                  </template>

                  <!-- 已下架：重新上架 + 删除 -->
                  <template v-if="row.status === 'removed'">
                    <el-button
                      type="success"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleRelist(row)"
                    >
                      <el-icon class="mr-0.5"><Top /></el-icon>
                      上架
                    </el-button>
                    <el-button
                      type="danger"
                      link
                      size="small"
                      :style="{ fontSize: 'var(--zh-font-size12)' }"
                      @click="handleDeleteContent(row)"
                    >
                      <el-icon class="mr-0.5"><Delete /></el-icon>
                      删除
                    </el-button>
                  </template>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无审核内容" :image-size="80">
                <template v-if="filters.type || filters.status || filters.keyword">
                  <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                    没有符合条件的内容，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="filters.type = ''; filters.status = ''; filters.keyword = ''; handleFilterChange();"
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
            <el-table-column prop="id" label="ID" width="110" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--zh-font-number); font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.id }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="contentTitle" label="被举报内容" min-width="180">
              <template #default="{ row }">
                <el-tooltip :content="row.contentTitle" placement="top" effect="dark" :disabled="row.contentTitle.length <= 20">
                  <span class="inline-block max-w-45 truncate" style="font-size: var(--zh-font-size14); color: var(--zh-text-primary);">
                    {{ row.contentTitle }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <el-table-column prop="contentAuthor" label="被举报者" width="110" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  {{ row.contentAuthor }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="reporter" label="举报人" width="110" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                  {{ row.reporter }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="reason" label="举报原因" min-width="160">
              <template #default="{ row }">
                <el-tooltip :content="row.reason" placement="top" effect="dark" :disabled="row.reason.length <= 18">
                  <span class="inline-block max-w-40 truncate" style="font-size: var(--zh-font-size13); color: var(--zh-text-secondary);">
                    {{ row.reason }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <el-table-column prop="reportedAt" label="举报时间" width="170" align="center">
              <template #default="{ row }">
                <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                  {{ row.reportedAt }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="status" label="处理状态" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="getReportStatusTagType(row.status)" size="small" effect="plain">
                  <span class="flex items-center gap-1.5">
                    <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0" :style="{ background: getReportStatusDotColor(row.status) }"></span>
                    {{ getReportStatusLabel(row.status) }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="190" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer(row.contentRef)"
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
              <el-empty description="暂无举报数据" :image-size="80">
                <template v-if="filters.status || filters.keyword">
                  <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
                    没有符合条件的举报，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="filters.status = ''; filters.keyword = ''; handleFilterChange();"
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
          内容详情 — {{ currentContent?.id || '' }}
        </span>
      </template>

      <template v-if="currentContent">
        <!-- 基本信息区 -->
        <div
          class="rounded-lg p-4 mb-4"
          style="border: 1px solid var(--zh-line-border);"
        >
          <div class="grid grid-cols-[80px_1fr] gap-y-3 gap-x-2">
            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">标题</span>
            <span style="font-size: var(--zh-font-size14); color: var(--zh-text-primary); font-weight: 500;">
              {{ currentContent.title }}
              <Star v-if="currentContent.isRecommended" :size="14" style="color: var(--zh-yellow); margin-left: 4px;" />
            </span>

            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">类型</span>
            <span>
              <el-tag :type="getContentTagType(currentContent.type)" size="small" effect="plain">
                {{ getContentIcon(currentContent.type) }} {{ CONTENT_TYPE_LABEL_MAP[currentContent.type] }}
              </el-tag>
            </span>

            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">作者</span>
            <span style="font-size: var(--zh-font-size14); color: var(--zh-text-secondary);">
              {{ currentContent.author }}（{{ currentContent.authorId }}）
            </span>

            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">提交时间</span>
            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
              {{ currentContent.submittedAt }}
            </span>

            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">适用学段</span>
            <span style="font-size: var(--zh-font-size14); color: var(--zh-text-secondary);">
              {{ currentContent.grade }} / {{ currentContent.subject }} / {{ currentContent.lessonType }}
            </span>

            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">版本</span>
            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);">
              {{ currentContent.version }}
            </span>
          </div>
        </div>

        <!-- 内容预览区 -->
        <div
          class="rounded-lg p-4 mb-4 overflow-y-auto"
          style="border: 1px solid var(--zh-line-border); background: var(--zh-background-light-gray); max-height: 240px;"
        >
          <span style="font-size: var(--zh-font-size12); color: var(--zh-text-caption); display: block; margin-bottom: 8px;">内容预览</span>
          <p style="font-size: var(--zh-font-size14); color: var(--zh-text-primary); line-height: 1.7; white-space: pre-wrap; margin: 0;">
            {{ currentContent.description }}
            [此处需填写：内容截图/文本预览]
          </p>
        </div>

        <!-- 敏感词检测区 -->
        <div
          v-if="currentContent.hasSensitive && currentContent.sensitiveHits.length > 0"
          class="rounded-lg p-4 mb-4"
          style="
            border-left: 3px solid var(--zh-orange);
            background: var(--zh-yellow-light);
          "
        >
          <div class="flex items-center gap-2 mb-2">
            <WarningFilled :size="16" style="color: var(--zh-orange);" />
            <span style="font-size: var(--zh-font-size14); font-weight: 600; color: var(--zh-text-primary);">
              检测到 {{ currentContent.sensitiveHits.length }} 处疑似敏感内容
            </span>
          </div>
          <div
            v-for="(hit, idx) in currentContent.sensitiveHits"
            :key="idx"
            class="flex items-center gap-2 py-1.5"
            style="font-size: var(--zh-font-size12); color: var(--zh-text-secondary);"
          >
            <span style="color: var(--zh-text-caption);">{{ hit.position }}：</span>
            <span style="color: var(--zh-red); font-weight: 500;">"{{ hit.keyword }}"</span>
            <span>— {{ hit.category }}</span>
            <el-tag
              :type="getSensitivityLevel(hit.level).tagType"
              size="small"
              effect="plain"
              class="ml-1"
            >
              {{ getSensitivityLevel(hit.level).label }}
            </el-tag>
          </div>
        </div>

        <!-- 审核历史 -->
        <div
          class="rounded-lg p-4 mb-4"
          style="border: 1px solid var(--zh-line-border);"
        >
          <span style="font-size: var(--zh-font-size13); color: var(--zh-text-caption); display: block; margin-bottom: 8px;">审核历史</span>
          <template v-if="currentContent.auditHistory && currentContent.auditHistory.length > 0">
            <div
              v-for="(entry, idx) in currentContent.auditHistory"
              :key="idx"
              class="flex items-center gap-2 py-1.5"
              :class="idx > 0 ? 'border-t' : ''"
              :style="{ borderColor: 'var(--zh-line-parting)' }"
            >
              <span style="font-size: var(--zh-font-size12); color: var(--zh-text-caption); min-width: 140px;">
                {{ entry.time }}
              </span>
              <span style="font-size: var(--zh-font-size13); color: var(--zh-text-primary); min-width: 80px;">
                {{ entry.action }}
              </span>
              <span style="font-size: var(--zh-font-size12); color: var(--zh-text-secondary);">
                {{ entry.operator }}
              </span>
              <span
                v-if="entry.reason"
                style="font-size: var(--zh-font-size12); color: var(--zh-text-caption); margin-left: 4px;"
              >
                — {{ entry.reason }}
              </span>
            </div>
          </template>
          <template v-else>
            <span style="font-size: var(--zh-font-size13); color: var(--zh-text-disabled);">
              暂无审核记录
            </span>
          </template>
        </div>

        <!-- 审核操作区 -->
        <div
          class="rounded-lg p-4"
          style="border: 1px solid var(--zh-line-border); background: var(--zh-background-light-gray);"
        >
          <span style="font-size: var(--zh-font-size14); font-weight: 600; color: var(--zh-text-primary); display: block; margin-bottom: 12px;">
            审核操作
          </span>

          <div class="flex flex-wrap gap-2">
            <el-button
              v-if="currentContent.status === 'pending'"
              type="success"
              :loading="isActionLoading"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleApprove(currentContent); drawerVisible = false;"
            >
              <el-icon class="mr-1"><Select /></el-icon>
              审核通过
            </el-button>
            <el-button
              v-if="currentContent.status === 'pending'"
              type="danger"
              :loading="isActionLoading"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleReject(currentContent); drawerVisible = false;"
            >
              <el-icon class="mr-1"><Close /></el-icon>
              驳回
            </el-button>
            <el-button
              v-if="currentContent.status === 'approved'"
              @click="handleToggleRecommend(currentContent)"
            >
              <el-icon class="mr-1"><Star /></el-icon>
              {{ currentContent.isRecommended ? '取消推荐' : '设为推荐' }}
            </el-button>
            <el-button
              v-if="currentContent.status === 'approved'"
              type="warning"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleRemove(currentContent); drawerVisible = false;"
            >
              <el-icon class="mr-1"><Download /></el-icon>
              下架
            </el-button>
            <el-button
              v-if="currentContent.status === 'rejected'"
              type="primary"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleReaudit(currentContent); drawerVisible = false;"
            >
              <el-icon class="mr-1"><Refresh /></el-icon>
              重新审核
            </el-button>
            <el-button
              v-if="currentContent.status === 'removed'"
              type="success"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleRelist(currentContent); drawerVisible = false;"
            >
              <el-icon class="mr-1"><Top /></el-icon>
              重新上架
            </el-button>
          </div>
        </div>
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
