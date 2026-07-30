<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDrawer, ElDialog, ElSkeleton, ElEmpty, ElMessageBox, ElMessage, ElTooltip,
      ElRadioGroup, ElRadioButton, ElProgress, ElUpload
    - ElementPlus Icons: Search, Refresh, Delete, Upload, Document, VideoCamera, PictureFilled,
      Headset, FolderOpened, Files, Download, View, Edit, CircleCheckFilled, CircleCloseFilled,
      WarningFilled, Clock, Loading, ArrowDown, ArrowUp, Top
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount` from Vue
  - 依赖:
    - 无外部 API 调用，当前使用静态示例数据（后续替换为后端 API）
  - 输入: 无 props，数据在组件内部 mock
  - 输出: 渲染公共资源管理与知识库维护视图（Tab 切换 + 筛选工具 + 数据表格 + 分页器 + 上传对话框 + 详情抽屉）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
  - 对应需求文档: §4.7.3.2 — 公共资源与知识库维护
-->

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  Search,
  Refresh,
  Delete,
  Upload,
  Document,
  VideoCamera,
  PictureFilled,
  Headset,
  FolderOpened,
  Files,
  Download,
  View,
  Edit,
  CircleCheckFilled,
  CircleCloseFilled,
  WarningFilled,
  Clock,
  Loading,
  ArrowDown,
  ArrowUp,
  Top,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// ===================================================================
// 配置常量 — Tab 1：公共资源管理
// ===================================================================

/** 页面 Tab 定义 */
const PAGE_TABS = [
  { key: 'resources', label: '公共资源管理' },
  { key: 'knowledge', label: '知识库维护' },
]

/** 资源类型筛选项 */
const RESOURCE_TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: '教材', value: 'textbook' },
  { label: '题库', value: 'exam' },
  { label: '多媒体素材', value: 'media' },
  { label: '教学文档', value: 'document' },
]

/** 资源类型 → 显示标签映射 */
const RESOURCE_TYPE_LABEL_MAP = {
  textbook: '教材',
  exam: '题库',
  media: '多媒体素材',
  document: '教学文档',
}

/** 资源类型 → Tag 类型映射 */
const RESOURCE_TYPE_TAG_MAP = {
  textbook: 'primary',
  exam: 'success',
  media: 'warning',
  document: 'info',
}

/** 资源类型 → 缩略图图标映射（用于无缩略图时的 emoji 占位） */
const RESOURCE_TYPE_ICON_MAP = {
  pdf: '📕',
  docx: '📘',
  pptx: '📙',
  xlsx: '📊',
  mp4: '🎬',
  avi: '🎬',
  mov: '🎬',
  jpg: '🖼',
  png: '🖼',
  gif: '🖼',
  mp3: '🎵',
  wav: '🎵',
  other: '📄',
}

/** 资源类型 → 副类型映射（用于显示中文标签） */
const RESOURCE_SUBTYPE_LABEL_MAP = {
  pdf: 'PDF 文档',
  docx: 'Word 文档',
  pptx: 'PPT 课件',
  xlsx: 'Excel 表格',
  mp4: '视频文件',
  avi: '视频文件',
  mov: '视频文件',
  jpg: '图片文件',
  png: '图片文件',
  gif: '图片文件',
  mp3: '音频文件',
  wav: '音频文件',
  other: '其他文件',
}

/** 学科筛选项 */
const SUBJECT_OPTIONS = [
  { label: '全部学科', value: '' },
  { label: '数学', value: 'math' },
  { label: '语文', value: 'chinese' },
  { label: '英语', value: 'english' },
  { label: '物理', value: 'physics' },
  { label: '化学', value: 'chemistry' },
  { label: '生物', value: 'biology' },
  { label: '历史', value: 'history' },
  { label: '地理', value: 'geography' },
  { label: '政治', value: 'politics' },
]

/** 学科 → 显示标签映射 */
const SUBJECT_LABEL_MAP = {
  math: '数学',
  chinese: '语文',
  english: '英语',
  physics: '物理',
  chemistry: '化学',
  biology: '生物',
  history: '历史',
  geography: '地理',
  politics: '政治',
}

/** 资源处理状态筛选项 */
const RESOURCE_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '已就绪', value: 'ready' },
  { label: '解析中', value: 'processing' },
  { label: '解析失败', value: 'failed' },
  { label: '待处理', value: 'pending' },
]

/** 资源状态 → 显示标签映射 */
const RESOURCE_STATUS_LABEL_MAP = {
  ready: '已就绪',
  processing: '解析中',
  failed: '解析失败',
  pending: '待处理',
}

/** 资源状态 → Tag 类型映射 */
const RESOURCE_STATUS_TAG_MAP = {
  ready: 'success',
  processing: '',
  failed: 'danger',
  pending: 'info',
}

/** 资源状态 → 圆点颜色映射 */
const RESOURCE_STATUS_DOT_COLOR_MAP = {
  ready: 'var(--zh-green)',
  processing: 'var(--zh-theme-primary)',
  failed: 'var(--zh-red)',
  pending: 'var(--zh-text-disabled)',
}

/** 学段筛选项 */
const GRADE_OPTIONS = [
  { label: '全部学段', value: '' },
  { label: '小学', value: 'primary' },
  { label: '初中', value: 'junior' },
  { label: '高中', value: 'senior' },
  { label: '大学', value: 'college' },
]

/** 学段 → 显示标签映射 */
const GRADE_LABEL_MAP = {
  primary: '小学',
  junior: '初中',
  senior: '高中',
  college: '大学',
}

// ===================================================================
// 配置常量 — Tab 2：知识库维护
// ===================================================================

/** 向量化任务状态筛选项 */
const VECTOR_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '已完成', value: 'completed' },
  { label: '解析中', value: 'processing' },
  { label: '失败', value: 'failed' },
  { label: '排队中', value: 'queued' },
  { label: '已取消', value: 'cancelled' },
]

/** 向量化状态 → 显示标签映射 */
const VECTOR_STATUS_LABEL_MAP = {
  completed: '已完成',
  processing: '解析中',
  failed: '失败',
  queued: '排队中',
  cancelled: '已取消',
}

/** 向量化状态 → Tag 类型映射 */
const VECTOR_STATUS_TAG_MAP = {
  completed: 'success',
  processing: '',
  failed: 'danger',
  queued: 'info',
  cancelled: 'info',
}

/** 向量化状态 → 圆点颜色映射 */
const VECTOR_STATUS_DOT_COLOR_MAP = {
  completed: 'var(--zh-green)',
  processing: 'var(--zh-theme-primary)',
  failed: 'var(--zh-red)',
  queued: 'var(--zh-text-disabled)',
  cancelled: 'var(--zh-text-disabled)',
}

/** 知识条目搜索类型 */
const KNOWLEDGE_SEARCH_TYPES = [
  { label: '全部来源', value: '' },
  { label: '教材', value: 'textbook' },
  { label: '题库', value: 'exam' },
  { label: '文档', value: 'document' },
]

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
const activeTab = ref('resources')

/** 资源列表数据 */
const resourceList = ref([])

/** 向量化任务列表数据 */
const vectorTaskList = ref([])

/** Tab 1 筛选条件 */
const resourceFilters = reactive({
  type: '',
  subject: '',
  status: '',
  keyword: '',
})

/** Tab 2 筛选条件 */
const knowledgeFilters = reactive({
  status: '',
  type: '',
  keyword: '',
})

/** Tab 1 分页参数 */
const resourcePagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** Tab 2 分页参数 */
const knowledgePagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** 详情抽屉可见性 */
const drawerVisible = ref(false)

/** 当前查看的资源数据 */
const currentResource = ref(null)

/** 上传对话框可见性 */
const uploadDialogVisible = ref(false)

/** 上传文件列表 */
const uploadFileList = ref([])

/** 上传中状态 */
const isUploading = ref(false)

/** 上传分类设置 */
const uploadCategory = reactive({
  subject: '',
  type: '',
  grade: '',
})

/** 知识条目检索面板折叠状态 */
const knowledgeSearchExpanded = ref(false)

/** 知识条目搜索关键词 */
const knowledgeSearchKeyword = ref('')

/** 知识条目搜索结果 */
const knowledgeSearchResults = ref([])

/** 知识条目搜索中 */
const isKnowledgeSearching = ref(false)

/** 操作执行中状态 */
const isActionLoading = ref(false)

// ===================================================================
// Mock 数据生成 — Tab 1：资源数据
// ===================================================================

/**
 * 随机格式化文件大小
 * @returns {string} 格式化的文件大小字符串
 */
const randomFileSize = () => {
  const sizes = ['12MB', '45MB', '128MB', '256MB', '320MB', '8MB', '64MB', '512MB', '1.2GB', '780MB']
  return sizes[Math.floor(Math.random() * sizes.length)]
}

/**
 * 生成模拟资源数据
 * @returns {Array} 资源对象数组
 */
const generateMockResources = () => {
  const templates = [
    { name: '2026版高中数学教材（必修一）', type: 'textbook', format: 'pdf', subject: 'math', grade: 'senior' },
    { name: '2026版高中数学教材（必修二）', type: 'textbook', format: 'pdf', subject: 'math', grade: 'senior' },
    { name: '勾股定理章节测试题库', type: 'exam', format: 'docx', subject: 'math', grade: 'junior' },
    { name: '一元二次方程综合练习', type: 'exam', format: 'docx', subject: 'math', grade: 'senior' },
    { name: '细胞分裂动画演示课件', type: 'media', format: 'mp4', subject: 'biology', grade: 'senior' },
    { name: '光合作用过程教学视频', type: 'media', format: 'mp4', subject: 'biology', grade: 'senior' },
    { name: '背影课文精读PPT课件', type: 'document', format: 'pptx', subject: 'chinese', grade: 'junior' },
    { name: '定语从句语法教学课件', type: 'document', format: 'pptx', subject: 'english', grade: 'senior' },
    { name: '串联电路实验指导书', type: 'document', format: 'docx', subject: 'physics', grade: 'junior' },
    { name: '牛顿第二定律实验报告模板', type: 'document', format: 'docx', subject: 'physics', grade: 'senior' },
    { name: '化学方程式配平练习题库', type: 'exam', format: 'xlsx', subject: 'chemistry', grade: 'senior' },
    { name: '有机化学官能团识别图谱', type: 'media', format: 'png', subject: 'chemistry', grade: 'senior' },
    { name: '辛亥革命历史课件', type: 'document', format: 'pptx', subject: 'history', grade: 'junior' },
    { name: '地球公转自转演示动画', type: 'media', format: 'avi', subject: 'geography', grade: 'junior' },
    { name: '英语听力训练音频集', type: 'media', format: 'mp3', subject: 'english', grade: 'junior' },
    { name: '分数加减法教学素材包', type: 'media', format: 'jpg', subject: 'math', grade: 'primary' },
    { name: '概率统计教学案例集', type: 'document', format: 'pdf', subject: 'math', grade: 'senior' },
    { name: '政治经济学基础知识题库', type: 'exam', format: 'docx', subject: 'politics', grade: 'senior' },
    { name: '中国地理知识点汇总', type: 'document', format: 'pdf', subject: 'geography', grade: 'junior' },
    { name: '古诗词鉴赏教学音频', type: 'media', format: 'mp3', subject: 'chinese', grade: 'senior' },
  ]

  const statuses = ['ready', 'ready', 'ready', 'processing', 'failed', 'pending']

  return templates.map((tpl, i) => {
    const id = `R${String(i + 1).padStart(4, '0')}`
    const day = 27 - Math.floor(i / 3)
    const hour = 9 + (i * 3) % 14
    const min = (i * 11) % 60
    const status = statuses[i % statuses.length]

    return {
      id,
      name: tpl.name,
      type: tpl.type,
      format: tpl.format,
      subject: tpl.subject,
      grade: tpl.grade,
      size: randomFileSize(),
      status,
      updatedAt: `2026-07-${String(day).padStart(2, '0')} ${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`,
      uploader: '管理员',
      version: `v${Math.floor(i / 5) + 1}.${i % 5}`,
      tags: [SUBJECT_LABEL_MAP[tpl.subject], GRADE_LABEL_MAP[tpl.grade]],
      vectorCount: status === 'ready' ? Math.floor(Math.random() * 15000) + 500 : (status === 'processing' ? Math.floor(Math.random() * 8000) : 0),
      vectorProgress: status === 'ready' ? 100 : (status === 'processing' ? Math.floor(Math.random() * 60) + 20 : (status === 'failed' ? Math.floor(Math.random() * 60) + 10 : 0)),
      failReason: status === 'failed' ? '文件格式解析异常：第128页包含无法识别的编码字符' : '',
    }
  })
}

// ===================================================================
// Mock 数据生成 — Tab 2：向量化任务数据
// ===================================================================

/**
 * 生成模拟向量化任务数据
 * @param {Array} resources - 资源列表（用于关联资源名称）
 * @returns {Array} 任务对象数组
 */
const generateMockVectorTasks = (resources) => {
  const taskStatuses = ['completed', 'completed', 'processing', 'completed', 'failed', 'queued', 'completed', 'processing', 'cancelled', 'completed']
  const durations = ['3m 28s', '1m 12s', null, '8m 05s', '0m 32s', null, '2m 15s', null, '1m 45s', '5m 10s']

  return resources.map((res, i) => {
    const taskStatus = taskStatuses[i % taskStatuses.length]
    const entryCount = taskStatus === 'completed' ? (Math.floor(Math.random() * 15000) + 500) : (taskStatus === 'processing' ? Math.floor(Math.random() * 8000) + 1000 : (res.vectorCount || Math.floor(Math.random() * 5000)))
    const progress = taskStatus === 'completed' ? 100 : (taskStatus === 'processing' ? Math.floor(Math.random() * 50) + 30 : (taskStatus === 'failed' ? Math.floor(Math.random() * 40) + 20 : 0))
    const errorMsg = taskStatus === 'failed' ? '向量化引擎异常：第' + (Math.floor(Math.random() * 200) + 1) + '页编码无法识别，请检查文件完整性' : ''

    return {
      id: `V${String(i + 1).padStart(4, '0')}`,
      resourceId: res.id,
      resourceName: res.name,
      resourceType: res.type,
      resourceFormat: res.format,
      entryCount,
      progress,
      status: taskStatus,
      duration: taskStatus === 'completed' || taskStatus === 'failed' ? (durations[i] || '0m 45s') : null,
      elapsedTime: taskStatus === 'processing' ? (Math.floor(Math.random() * 120) + 10) + 's' : null,
      failReason: errorMsg,
      startedAt: res.updatedAt,
    }
  })
}

/** 全部资源数据（模拟数据库） */
let allResources = []

/** 全部向量化任务数据（模拟数据库） */
let allVectorTasks = []

// ===================================================================
// 计算属性：知识库概览统计数据
// ===================================================================

/** 知识条目总数 */
const totalKnowledgeEntries = computed(() => {
  return allVectorTasks
    .filter((t) => t.status === 'completed' || t.status === 'processing')
    .reduce((sum, t) => sum + t.entryCount, 0)
})

/** 已完成向量化条目数 */
const completedVectorEntries = computed(() => {
  return allVectorTasks
    .filter((t) => t.status === 'completed')
    .reduce((sum, t) => sum + t.entryCount, 0)
})

/** 待处理资源数 */
const pendingVectorCount = computed(() => {
  return allVectorTasks.filter((t) => t.status === 'failed' || t.status === 'queued').length
})

/** 向量化覆盖率 */
const vectorCoverage = computed(() => {
  if (totalKnowledgeEntries.value === 0) return '0%'
  return ((completedVectorEntries.value / totalKnowledgeEntries.value) * 100).toFixed(1) + '%'
})

// ===================================================================
// 数据筛选与获取方法
// ===================================================================

/**
 * 获取资源列表数据（模拟异步请求）
 * 根据当前 Tab 1 的筛选条件 + 分页参数过滤 mock 数据
 */
const fetchResources = () => {
  isTableLoading.value = true

  setTimeout(() => {
    let filtered = [...allResources]
    if (resourceFilters.type) {
      filtered = filtered.filter((r) => r.type === resourceFilters.type)
    }
    if (resourceFilters.subject) {
      filtered = filtered.filter((r) => r.subject === resourceFilters.subject)
    }
    if (resourceFilters.status) {
      filtered = filtered.filter((r) => r.status === resourceFilters.status)
    }
    if (resourceFilters.keyword.trim()) {
      const kw = resourceFilters.keyword.trim().toLowerCase()
      filtered = filtered.filter((r) => r.name.toLowerCase().includes(kw))
    }
    // 排序：待处理/解析中 > 失败 > 已就绪
    const statusPriority = { pending: 0, processing: 1, failed: 2, ready: 3 }
    filtered.sort((a, b) => {
      const sp = statusPriority[a.status] - statusPriority[b.status]
      if (sp !== 0) return sp
      return b.updatedAt.localeCompare(a.updatedAt)
    })
    resourcePagination.total = filtered.length
    const start = (resourcePagination.currentPage - 1) * resourcePagination.pageSize
    resourceList.value = filtered.slice(start, start + resourcePagination.pageSize)
    isTableLoading.value = false
  }, 300)
}

/**
 * 获取向量化任务列表数据（模拟异步请求）
 * 根据当前 Tab 2 的筛选条件 + 分页参数过滤 mock 数据
 */
const fetchVectorTasks = () => {
  isTableLoading.value = true

  setTimeout(() => {
    let filtered = [...allVectorTasks]
    if (knowledgeFilters.status) {
      filtered = filtered.filter((t) => t.status === knowledgeFilters.status)
    }
    if (knowledgeFilters.type) {
      filtered = filtered.filter((t) => t.resourceType === knowledgeFilters.type)
    }
    if (knowledgeFilters.keyword.trim()) {
      const kw = knowledgeFilters.keyword.trim().toLowerCase()
      filtered = filtered.filter((t) => t.resourceName.toLowerCase().includes(kw))
    }
    // 排序：解析中 > 排队中 > 失败 > 已完成 > 已取消
    const taskPriority = { processing: 0, queued: 1, failed: 2, completed: 3, cancelled: 4 }
    filtered.sort((a, b) => {
      const tp = taskPriority[a.status] - taskPriority[b.status]
      if (tp !== 0) return tp
      return b.startedAt.localeCompare(a.startedAt)
    })
    knowledgePagination.total = filtered.length
    const start = (knowledgePagination.currentPage - 1) * knowledgePagination.pageSize
    vectorTaskList.value = filtered.slice(start, start + knowledgePagination.pageSize)
    isTableLoading.value = false
  }, 300)
}

/**
 * 获取当前 Tab 对应的数据
 * 根据 activeTab 的值调用 fetchResources 或 fetchVectorTasks
 */
const fetchData = () => {
  if (activeTab.value === 'resources') {
    fetchResources()
  } else {
    fetchVectorTasks()
  }
}

/**
 * 页面首次数据加载 — 初始化 mock 数据并触发首次渲染
 */
const loadData = () => {
  isLoading.value = true
  setTimeout(() => {
    allResources = generateMockResources()
    allVectorTasks = generateMockVectorTasks(allResources)
    isLoading.value = false
    fetchData()
  }, 600)
}

// ===================================================================
// 交互事件处理方法
// ===================================================================

/**
 * Tab 切换处理 — 重置筛选条件和分页
 * @param {string} tab - 目标 Tab key
 */
const handleTabChange = (tab) => {
  resourceFilters.type = ''
  resourceFilters.subject = ''
  resourceFilters.status = ''
  resourceFilters.keyword = ''
  knowledgeFilters.status = ''
  knowledgeFilters.type = ''
  knowledgeFilters.keyword = ''
  resourcePagination.currentPage = 1
  knowledgePagination.currentPage = 1
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
 * Tab 1 筛选条件变更处理
 */
const handleResourceFilterChange = () => {
  resourcePagination.currentPage = 1
  fetchResources()
}

/**
 * Tab 2 筛选条件变更处理
 */
const handleKnowledgeFilterChange = () => {
  knowledgePagination.currentPage = 1
  fetchVectorTasks()
}

/**
 * Tab 1 搜索框输入防抖处理
 */
let resourceSearchTimer = null
const handleResourceSearchInput = () => {
  clearTimeout(resourceSearchTimer)
  resourceSearchTimer = setTimeout(() => {
    handleResourceFilterChange()
  }, 300)
}

/**
 * Tab 1 搜索框回车处理
 */
const handleResourceSearchEnter = () => {
  clearTimeout(resourceSearchTimer)
  handleResourceFilterChange()
}

/**
 * Tab 2 搜索框输入防抖处理
 */
let knowledgeSearchTimer = null
const handleKnowledgeSearchInput = () => {
  clearTimeout(knowledgeSearchTimer)
  knowledgeSearchTimer = setTimeout(() => {
    handleKnowledgeFilterChange()
  }, 300)
}

/**
 * Tab 2 搜索框回车处理
 */
const handleKnowledgeSearchEnter = () => {
  clearTimeout(knowledgeSearchTimer)
  handleKnowledgeFilterChange()
}

/**
 * Tab 1 分页页码变更
 * @param {number} page - 目标页码
 */
const handleResourcePageChange = (page) => {
  resourcePagination.currentPage = page
  fetchResources()
}

/**
 * Tab 1 分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleResourceSizeChange = (size) => {
  resourcePagination.pageSize = size
  resourcePagination.currentPage = 1
  fetchResources()
}

/**
 * Tab 2 分页页码变更
 * @param {number} page - 目标页码
 */
const handleKnowledgePageChange = (page) => {
  knowledgePagination.currentPage = page
  fetchVectorTasks()
}

/**
 * Tab 2 分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleKnowledgeSizeChange = (size) => {
  knowledgePagination.pageSize = size
  knowledgePagination.currentPage = 1
  fetchVectorTasks()
}

// ===================================================================
// 资源操作：文件类型缩略图
// ===================================================================

/**
 * 获取文件格式对应的缩略图图标字符
 * @param {string} format - 文件扩展名
 * @returns {string} emoji 占位字符
 */
const getFileIcon = (format) => {
  return RESOURCE_TYPE_ICON_MAP[format] || RESOURCE_TYPE_ICON_MAP.other
}

/**
 * 获取文件格式对应的中文标签
 * @param {string} format - 文件扩展名
 * @returns {string} 中文标签
 */
const getFileFormatLabel = (format) => {
  return RESOURCE_SUBTYPE_LABEL_MAP[format] || '未知格式'
}

/**
 * 获取资源状态圆点颜色
 * @param {string} status - 状态标识
 * @returns {string} CSS 颜色值
 */
const getResourceStatusDotColor = (status) => {
  return RESOURCE_STATUS_DOT_COLOR_MAP[status] || 'var(--zh-text-disabled)'
}

/**
 * 获取资源状态 Tag 类型
 * @param {string} status - 状态标识
 * @returns {string} ElementPlus Tag type
 */
const getResourceStatusTagType = (status) => {
  return RESOURCE_STATUS_TAG_MAP[status] || 'info'
}

/**
 * 获取向量化状态圆点颜色
 * @param {string} status - 状态标识
 * @returns {string} CSS 颜色值
 */
const getVectorStatusDotColor = (status) => {
  return VECTOR_STATUS_DOT_COLOR_MAP[status] || 'var(--zh-text-disabled)'
}

/**
 * 获取向量化状态 Tag 类型
 * @param {string} status - 状态标识
 * @returns {string} ElementPlus Tag type
 */
const getVectorStatusTagType = (status) => {
  return VECTOR_STATUS_TAG_MAP[status] || 'info'
}

/**
 * 获取进度条状态类型
 * @param {string} status - 任务状态
 * @returns {string} ElementPlus Progress status
 */
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
}

// ===================================================================
// 资源 CRUD 操作方法
// ===================================================================

/**
 * 打开资源详情抽屉
 * @param {Object} row - 当前行资源数据
 */
const openDetailDrawer = (row) => {
  const latest = allResources.find((r) => r.id === row.id) || row
  currentResource.value = reactive({ ...latest })
  drawerVisible.value = true
}

/**
 * 打开上传对话框 — 重置上传状态
 */
const openUploadDialog = () => {
  uploadFileList.value = []
  uploadCategory.subject = ''
  uploadCategory.type = ''
  uploadCategory.grade = ''
  isUploading.value = false
  uploadDialogVisible.value = true
}

/**
 * 模拟上传文件选择（演示用，实际使用 el-upload 的 on-change 回调）
 * @param {File} file - 选择的文件对象
 */
const handleFileSelected = (file) => {
  const newFile = {
    uid: Date.now() + Math.random(),
    name: file.name,
    size: file.size,
    status: 'ready',
    format: file.name.split('.').pop().toLowerCase(),
  }
  uploadFileList.value.push(newFile)
}

/**
 * 移除已选上传文件
 * @param {number} uid - 文件唯一标识
 */
const removeUploadFile = (uid) => {
  uploadFileList.value = uploadFileList.value.filter((f) => f.uid !== uid)
}

/**
 * 格式化文件大小显示
 * @param {number} bytes - 字节数
 * @returns {string} 格式化字符串
 */
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

/**
 * 判断上传文件是否超过 500MB 限制
 * @param {number} bytes - 文件字节数
 * @returns {boolean} 是否超限
 */
const isFileOversized = (bytes) => {
  return bytes > 500 * 1024 * 1024
}

/**
 * 执行上传操作（模拟异步上传）
 */
const handleUpload = () => {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  // 检查文件大小
  const oversized = uploadFileList.value.filter((f) => isFileOversized(f.size || 0))
  if (oversized.length > 0) {
    ElMessage.warning(`${oversized.length} 个文件超过 500MB 限制，请移除后重试`)
    return
  }

  isUploading.value = true
  setTimeout(() => {
    const count = uploadFileList.value.length
    uploadFileList.value.forEach((file, idx) => {
      const newId = `R${String(allResources.length + idx + 1).padStart(4, '0')}`
      allResources.unshift({
        id: newId,
        name: file.name,
        type: uploadCategory.type || 'document',
        format: file.format,
        subject: uploadCategory.subject || 'math',
        grade: uploadCategory.grade || 'senior',
        size: formatFileSize(file.size || 0),
        status: 'pending',
        updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 16),
        uploader: '管理员',
        version: 'v1.0',
        tags: [
          SUBJECT_LABEL_MAP[uploadCategory.subject] || '未分类',
          GRADE_LABEL_MAP[uploadCategory.grade] || '未分类',
        ],
        vectorCount: 0,
        vectorProgress: 0,
        failReason: '',
      })
    })
    isUploading.value = false
    uploadDialogVisible.value = false
    ElMessage.success(`成功上传 ${count} 个资源，系统正在自动解析...`)
    // 更新向量化任务列表
    allVectorTasks = generateMockVectorTasks(allResources)
    fetchResources()
  }, 2000)
}

/**
 * 删除资源 — 二次确认后删除
 * @param {Object} row - 当前行资源数据
 */
const handleDeleteResource = (row) => {
  ElMessageBox.confirm(
    `确认删除「${row.name}」？关联的知识条目将一并移除，此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    },
  )
    .then(() => {
      allResources = allResources.filter((r) => r.id !== row.id)
      allVectorTasks = allVectorTasks.filter((t) => t.resourceId !== row.id)
      ElMessage.success(`已删除资源「${row.name}」`)
      if (resourceList.value.length === 1 && resourcePagination.currentPage > 1) {
        resourcePagination.currentPage--
      }
      fetchResources()
    })
    .catch(() => {})
}

/**
 * 重新解析单个资源
 * @param {Object} row - 当前行任务或资源数据
 */
const handleReparse = (row) => {
  const resourceId = row.resourceId || row.id
  const name = row.resourceName || row.name

  // 更新资源状态为 processing
  const resIdx = allResources.findIndex((r) => r.id === resourceId)
  if (resIdx !== -1) {
    allResources[resIdx].status = 'processing'
    allResources[resIdx].vectorProgress = 0
  }
  // 更新或创建向量化任务
  const taskIdx = allVectorTasks.findIndex((t) => t.resourceId === resourceId)
  if (taskIdx !== -1) {
    allVectorTasks[taskIdx].status = 'processing'
    allVectorTasks[taskIdx].progress = 0
    allVectorTasks[taskIdx].duration = null
    allVectorTasks[taskIdx].failReason = ''
  }
  ElMessage.success(`已重新发起「${name}」的解析任务`)
  fetchData()
}

/**
 * 取消解析任务
 * @param {Object} row - 当前行任务数据
 */
const handleCancelTask = (row) => {
  ElMessageBox.confirm(
    `确认取消「${row.resourceName}」的解析任务？已完成的部分将保留。`,
    '确认取消',
    { confirmButtonText: '确认取消', cancelButtonText: '返回', type: 'warning' },
  )
    .then(() => {
      const taskIdx = allVectorTasks.findIndex((t) => t.id === row.id)
      if (taskIdx !== -1) allVectorTasks[taskIdx].status = 'cancelled'
      const resIdx = allResources.findIndex((r) => r.id === row.resourceId)
      if (resIdx !== -1) allResources[resIdx].status = 'pending'
      ElMessage.success(`已取消「${row.resourceName}」的解析任务`)
      fetchData()
    })
    .catch(() => {})
}

/**
 * 批量重建全部知识索引 — 二次确认
 */
const handleRebuildAllIndex = () => {
  ElMessageBox.confirm(
    '确认重建全部知识向量索引？此操作将清除现有索引并重新解析所有资源，耗时较长（预计 30-60 分钟），期间 RAG 检索将暂时不可用。',
    '确认重建索引',
    {
      confirmButtonText: '确认重建',
      cancelButtonText: '取消',
      type: 'warning',
    },
  )
    .then(() => {
      isTableLoading.value = true
      setTimeout(() => {
        allResources.forEach((r) => {
          r.status = 'processing'
          r.vectorProgress = 0
        })
        allVectorTasks.forEach((t) => { t.status = 'processing'; t.progress = 0; t.duration = null; t.failReason = '' })
        ElMessage.success('已发起全量索引重建任务')
        isTableLoading.value = false
        fetchData()
      }, 500)
    })
    .catch(() => {})
}

// ===================================================================
// 知识条目检索方法
// ===================================================================

/**
 * 执行知识条目检索（模拟异步搜索）
 */
const handleKnowledgeSearch = () => {
  const kw = knowledgeSearchKeyword.value.trim()
  if (!kw) {
    knowledgeSearchResults.value = []
    return
  }
  isKnowledgeSearching.value = true
  setTimeout(() => {
    const results = []
    const completedTasks = allVectorTasks.filter((t) => t.status === 'completed')
    completedTasks.forEach((task) => {
      const matchCount = Math.floor(Math.random() * 5)
      for (let i = 0; i < matchCount; i++) {
        results.push({
          id: `KE${task.id}_${i}`,
          content: `与"${kw}"相关的知识条目 #${i + 1} — 来自「${task.resourceName}」`,
          source: task.resourceName,
          matchRate: Math.floor(Math.random() * 30) + 70,
          entryCount: task.entryCount,
        })
      }
    })
    knowledgeSearchResults.value = results.slice(0, 20)
    isKnowledgeSearching.value = false
  }, 500)
}

/**
 * 切换知识条目检索面板展开/折叠
 */
const toggleKnowledgeSearch = () => {
  knowledgeSearchExpanded.value = !knowledgeSearchExpanded.value
  if (!knowledgeSearchExpanded.value) {
    knowledgeSearchResults.value = []
    knowledgeSearchKeyword.value = ''
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
         1. 页面标题区 + 刷新按钮
         =================================================================== -->
    <div class="flex items-center justify-between flex-wrap gap-3 mb-4">
      <h1
        class="text-lg font-semibold shrink-0"
        :style="{ fontSize: 'var(--zh-font-size18)', color: 'var(--zh-text-primary)' }"
      >
        公共资源与知识库维护
      </h1>
      <el-tooltip content="刷新列表" placement="bottom" effect="dark">
        <el-button :icon="Refresh" circle size="default" @click="handleRefresh" />
      </el-tooltip>
    </div>

    <!-- ===================================================================
         2. Tab 分段控件
         =================================================================== -->
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
         3. Tab 1：公共资源管理
         =================================================================== -->
    <template v-if="activeTab === 'resources'">
      <!-- 3.1 筛选器行 -->
      <div class="flex items-center flex-wrap gap-3 mb-4">
        <el-select
          v-model="resourceFilters.type"
          placeholder="全部类型"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleResourceFilterChange"
        >
          <el-option
            v-for="opt in RESOURCE_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-select
          v-model="resourceFilters.subject"
          placeholder="全部学科"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleResourceFilterChange"
        >
          <el-option
            v-for="opt in SUBJECT_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-select
          v-model="resourceFilters.status"
          placeholder="全部状态"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleResourceFilterChange"
        >
          <el-option
            v-for="opt in RESOURCE_STATUS_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-input
          v-model="resourceFilters.keyword"
          placeholder="搜索资源名称 / 文件名..."
          clearable
          size="default"
          :prefix-icon="Search"
          style="width: 260px;"
          @input="handleResourceSearchInput"
          @keyup.enter="handleResourceSearchEnter"
          @clear="handleResourceFilterChange"
        />

        <div class="flex items-center gap-2 ml-auto">
          <el-button type="primary" :icon="Upload" @click="openUploadDialog">
            批量上传
          </el-button>
          <el-button :icon="Download" disabled>
            导出
          </el-button>
        </div>
      </div>

      <!-- 3.2 资源数据表格 -->
      <el-card
        shadow="never"
        :style="{
          background: 'var(--zh-background-capsule)',
          borderRadius: 'var(--zh-radius12)',
          borderColor: 'var(--zh-line-border)',
        }"
      >
        <!-- 骨架屏 -->
        <template v-if="isLoading">
          <div
            v-for="n in 8"
            :key="'skeleton-' + n"
            class="flex items-center gap-4 py-3 border-b last:border-0"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <div class="skeleton-loader w-14 h-4 rounded"></div>
            <div class="skeleton-loader w-10 h-10 rounded-md shrink-0"></div>
            <div class="skeleton-loader flex-1 h-4 rounded"></div>
            <div class="skeleton-loader w-16 h-6 rounded-full"></div>
            <div class="skeleton-loader w-12 h-4 rounded"></div>
            <div class="skeleton-loader w-14 h-4 rounded"></div>
            <div class="skeleton-loader w-20 h-6 rounded-full"></div>
            <div class="skeleton-loader w-32 h-4 rounded"></div>
            <div class="skeleton-loader w-28 h-4 rounded"></div>
          </div>
        </template>

        <template v-else>
          <el-table
            :data="resourceList"
            stripe
            border
            v-loading="isTableLoading"
            element-loading-text="加载中..."
            :row-class-name="(r) => r.row.status === 'pending' ? 'resource-table-row pending-resource-row' : r.row.status === 'failed' ? 'resource-table-row failed-resource-row' : 'resource-table-row'"
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
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                  {{ row.id }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：资源名称（含缩略图） -->
            <el-table-column prop="name" label="资源名称" min-width="240">
              <template #default="{ row }">
                <div class="flex items-center gap-3">
                  <!-- 缩略图占位 -->
                  <div
                    class="w-10 h-10 rounded-md flex items-center justify-center shrink-0 text-lg"
                    :style="{ background: 'var(--zh-background-light-gray)' }"
                  >
                    {{ getFileIcon(row.format) }}
                  </div>
                  <div class="min-w-0">
                    <el-tooltip
                      :content="row.name"
                      placement="top"
                      effect="dark"
                      :disabled="row.name.length <= 20"
                    >
                      <span
                        class="cursor-pointer hover:underline block truncate max-w-55"
                        :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-primary)' }"
                        @click="openDetailDrawer(row)"
                      >
                        {{ row.name }}
                      </span>
                    </el-tooltip>
                    <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
                      {{ getFileFormatLabel(row.format) }}
                    </span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 列：资源类型 -->
            <el-table-column prop="type" label="类型" width="120" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="RESOURCE_TYPE_TAG_MAP[row.type] || 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ RESOURCE_TYPE_LABEL_MAP[row.type] || row.type }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：学科 -->
            <el-table-column prop="subject" label="学科" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
                  {{ SUBJECT_LABEL_MAP[row.subject] || row.subject }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：大小 -->
            <el-table-column prop="size" label="大小" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
                  {{ row.size }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：状态 -->
            <el-table-column prop="status" label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getResourceStatusTagType(row.status)"
                  size="small"
                  effect="plain"
                >
                  <span class="flex items-center gap-1.5">
                    <span
                      class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                      :class="{ 'animate-pulse': row.status === 'processing' }"
                      :style="{ background: getResourceStatusDotColor(row.status) }"
                    ></span>
                    {{ RESOURCE_STATUS_LABEL_MAP[row.status] || row.status }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：更新时间 -->
            <el-table-column prop="updatedAt" label="更新时间" width="160" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                  {{ row.updatedAt }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="180" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer(row)"
                  >
                    <el-icon class="mr-0.5"><View /></el-icon>
                    详情
                  </el-button>
                  <el-button
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="handleReparse(row)"
                  >
                    <el-icon class="mr-0.5"><Refresh /></el-icon>
                    重解析
                  </el-button>
                  <el-button
                    type="danger" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="handleDeleteResource(row)"
                  >
                    <el-icon class="mr-0.5"><Delete /></el-icon>
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无资源数据" :image-size="80">
                <template v-if="resourceFilters.type || resourceFilters.subject || resourceFilters.status || resourceFilters.keyword">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    没有符合条件的资源，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="resourceFilters.type = ''; resourceFilters.subject = ''; resourceFilters.status = ''; resourceFilters.keyword = ''; handleResourceFilterChange();"
                  >
                    清除筛选
                  </el-button>
                </template>
                <template v-else>
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    点击"批量上传"按钮添加公共教学资源
                  </span>
                  <el-button type="primary" size="small" class="mt-3" :icon="Upload" @click="openUploadDialog">
                    批量上传
                  </el-button>
                </template>
              </el-empty>
            </template>
          </el-table>

          <!-- 分页器 -->
          <div
            v-if="resourcePagination.total > 0"
            class="flex justify-end pt-4 mt-4 border-t"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <el-pagination
              v-model:current-page="resourcePagination.currentPage"
              v-model:page-size="resourcePagination.pageSize"
              :total="resourcePagination.total"
              :page-sizes="PAGE_SIZE_OPTIONS"
              :background="true"
              layout="total, sizes, prev, pager, next, jumper"
              :style="{
                '--el-pagination-bg-color': 'var(--zh-background-capsule)',
                '--el-pagination-button-bg-color': 'var(--zh-background-option)',
                '--el-pagination-hover-color': 'var(--zh-text-theme)',
              }"
              @current-change="handleResourcePageChange"
              @size-change="handleResourceSizeChange"
            />
          </div>
        </template>
      </el-card>
    </template>

    <!-- ===================================================================
         4. Tab 2：知识库维护
         =================================================================== -->
    <template v-if="activeTab === 'knowledge'">
      <!-- 4.1 知识库概览统计卡片 -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        <el-card
          shadow="never"
          class="kpi-card cursor-pointer"
          :class="{ 'skeleton-pulse kpi-card-skeleton': isLoading }"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template v-if="isLoading">
            <div class="flex flex-col gap-3">
              <div class="skeleton-loader h-4 w-2/3"></div>
              <div class="skeleton-loader h-8 w-1/2"></div>
              <div class="skeleton-loader h-3 w-3/4"></div>
            </div>
          </template>
          <template v-else>
            <div class="flex items-center justify-between mb-3">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">知识条目总数</span>
              <FolderOpened class="w-6 h-6" :style="{ color: 'var(--zh-text-caption)' }" />
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ totalKnowledgeEntries.toLocaleString() }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)' }">
              覆盖 10+ 学科
            </span>
          </template>
        </el-card>

        <el-card
          shadow="never"
          class="kpi-card cursor-pointer"
          :class="{ 'skeleton-pulse kpi-card-skeleton': isLoading }"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template v-if="isLoading">
            <div class="flex flex-col gap-3">
              <div class="skeleton-loader h-4 w-2/3"></div>
              <div class="skeleton-loader h-8 w-1/2"></div>
              <div class="skeleton-loader h-3 w-3/4"></div>
            </div>
          </template>
          <template v-else>
            <div class="flex items-center justify-between mb-3">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">已向量化</span>
              <CircleCheckFilled class="w-6 h-6" :style="{ color: 'var(--zh-green)' }" />
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ completedVectorEntries.toLocaleString() }}
              </span>
              <span :style="{ fontSize: 'var(--zh-font-size12)', fontWeight: 500, color: 'var(--zh-green)' }">
                {{ vectorCoverage }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)' }">
              覆盖率 {{ vectorCoverage }}
            </span>
          </template>
        </el-card>

        <el-card
          shadow="never"
          class="kpi-card cursor-pointer"
          :class="{ 'skeleton-pulse kpi-card-skeleton': isLoading }"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template v-if="isLoading">
            <div class="flex flex-col gap-3">
              <div class="skeleton-loader h-4 w-2/3"></div>
              <div class="skeleton-loader h-8 w-1/2"></div>
              <div class="skeleton-loader h-3 w-3/4"></div>
            </div>
          </template>
          <template v-else>
            <div class="flex items-center justify-between mb-3">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">待处理</span>
              <WarningFilled class="w-6 h-6" :style="{ color: pendingVectorCount > 0 ? 'var(--zh-orange)' : 'var(--zh-text-caption)' }" />
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: pendingVectorCount > 0 ? 'var(--zh-orange)' : 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ pendingVectorCount }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)' }">
              涉及 {{ pendingVectorCount }} 个资源
            </span>
          </template>
        </el-card>
      </div>

      <!-- 4.2 筛选器行 -->
      <div class="flex items-center flex-wrap gap-3 mb-4">
        <el-select
          v-model="knowledgeFilters.status"
          placeholder="全部状态"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleKnowledgeFilterChange"
        >
          <el-option
            v-for="opt in VECTOR_STATUS_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-select
          v-model="knowledgeFilters.type"
          placeholder="全部类型"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleKnowledgeFilterChange"
        >
          <el-option
            v-for="opt in RESOURCE_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-input
          v-model="knowledgeFilters.keyword"
          placeholder="搜索资源名称..."
          clearable
          size="default"
          :prefix-icon="Search"
          style="width: 240px;"
          @input="handleKnowledgeSearchInput"
          @keyup.enter="handleKnowledgeSearchEnter"
          @clear="handleKnowledgeFilterChange"
        />

        <div class="flex items-center gap-2 ml-auto">
          <el-button type="danger" plain size="default" :icon="Refresh" @click="handleRebuildAllIndex">
            全部重新索引
          </el-button>
        </div>
      </div>

      <!-- 4.3 向量化任务表格 -->
      <el-card
        shadow="never"
        :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
      >
        <template v-if="isLoading">
          <div
            v-for="n in 8"
            :key="'skeleton-' + n"
            class="flex items-center gap-4 py-3 border-b last:border-0"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <div class="skeleton-loader w-10 h-10 rounded-md shrink-0"></div>
            <div class="skeleton-loader flex-1 h-4 rounded"></div>
            <div class="skeleton-loader w-16 h-6 rounded-full"></div>
            <div class="skeleton-loader w-16 h-4 rounded"></div>
            <div class="skeleton-loader w-32 h-4 rounded"></div>
            <div class="skeleton-loader w-20 h-6 rounded-full"></div>
            <div class="skeleton-loader w-16 h-4 rounded"></div>
            <div class="skeleton-loader w-28 h-4 rounded"></div>
          </div>
        </template>

        <template v-else>
          <el-table
            :data="vectorTaskList"
            stripe
            border
            v-loading="isTableLoading"
            element-loading-text="加载中..."
            row-class-name="vector-table-row"
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：资源名称 -->
            <el-table-column prop="resourceName" label="资源名称" min-width="220">
              <template #default="{ row }">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-md flex items-center justify-center shrink-0 text-lg"
                    :style="{ background: 'var(--zh-background-light-gray)' }"
                  >
                    {{ getFileIcon(row.resourceFormat) }}
                  </div>
                  <el-tooltip
                    :content="row.resourceName"
                    placement="top"
                    effect="dark"
                    :disabled="row.resourceName.length <= 20"
                  >
                    <span
                      class="block truncate max-w-55"
                      :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-primary)' }"
                    >
                      {{ row.resourceName }}
                    </span>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>

            <!-- 列：类型 -->
            <el-table-column prop="resourceType" label="类型" width="120" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="RESOURCE_TYPE_TAG_MAP[row.resourceType] || 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ RESOURCE_TYPE_LABEL_MAP[row.resourceType] || row.resourceType }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：条目数 -->
            <el-table-column prop="entryCount" label="条目数" width="100" align="center">
              <template #default="{ row }">
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
                  {{ row.entryCount.toLocaleString() }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：进度 -->
            <el-table-column prop="progress" label="进度" width="180">
              <template #default="{ row }">
                <div class="flex items-center gap-2">
                  <el-progress
                    :percentage="row.progress"
                    :status="getProgressStatus(row.status)"
                    :stroke-width="6"
                    :striped="row.status === 'processing'"
                    :striped-flow="row.status === 'processing'"
                    :show-text="false"
                    style="flex: 1;"
                  />
                  <span
                    :style="{
                      fontSize: 'var(--zh-font-size12)',
                      fontFamily: 'var(--zh-font-number)',
                      color: row.status === 'failed' ? 'var(--zh-red)' : 'var(--zh-text-caption)',
                      minWidth: '36px',
                    }"
                  >
                    {{ row.progress }}%
                  </span>
                </div>
              </template>
            </el-table-column>

            <!-- 列：状态 -->
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="getVectorStatusTagType(row.status)"
                  size="small"
                  effect="plain"
                >
                  <span class="flex items-center gap-1.5">
                    <span
                      class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                      :class="{ 'animate-pulse': row.status === 'processing' }"
                      :style="{ background: getVectorStatusDotColor(row.status) }"
                    ></span>
                    {{ VECTOR_STATUS_LABEL_MAP[row.status] || row.status }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：耗时 -->
            <el-table-column prop="duration" label="耗时" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                  {{ row.status === 'processing' ? row.elapsedTime : (row.duration || '—') }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="160" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <!-- 已完成：重新解析 -->
                  <template v-if="row.status === 'completed'">
                    <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleReparse(row)">
                      <el-icon class="mr-0.5"><Refresh /></el-icon>
                      重解析
                    </el-button>
                  </template>
                  <!-- 解析中：取消 -->
                  <template v-if="row.status === 'processing'">
                    <el-button type="warning" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleCancelTask(row)">
                      <el-icon class="mr-0.5"><CircleCloseFilled /></el-icon>
                      取消
                    </el-button>
                  </template>
                  <!-- 失败：重新解析 -->
                  <template v-if="row.status === 'failed'">
                    <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleReparse(row)">
                      <el-icon class="mr-0.5"><Refresh /></el-icon>
                      重试
                    </el-button>
                  </template>
                  <!-- 排队中：取消 -->
                  <template v-if="row.status === 'queued'">
                    <el-button type="warning" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleCancelTask(row)">
                      <el-icon class="mr-0.5"><CircleCloseFilled /></el-icon>
                      取消
                    </el-button>
                  </template>
                  <!-- 查看详情按钮（所有状态通用） -->
                  <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="openDetailDrawer({ id: row.resourceId, name: row.resourceName, type: row.resourceType, format: row.resourceFormat })">
                    详情
                  </el-button>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无向量化任务记录" :image-size="80">
                <template v-if="knowledgeFilters.status || knowledgeFilters.type || knowledgeFilters.keyword">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    没有符合条件的任务，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="knowledgeFilters.status = ''; knowledgeFilters.type = ''; knowledgeFilters.keyword = ''; handleKnowledgeFilterChange();"
                  >
                    清除筛选
                  </el-button>
                </template>
                <template v-else>
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    知识条目将在资源上传并解析后自动生成
                  </span>
                  <el-button type="primary" size="small" class="mt-3" @click="activeTab = 'resources'; openUploadDialog();">
                    前往上传资源 →
                  </el-button>
                </template>
              </el-empty>
            </template>
          </el-table>

          <!-- 分页器 -->
          <div
            v-if="knowledgePagination.total > 0"
            class="flex justify-end pt-4 mt-4 border-t"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <el-pagination
              v-model:current-page="knowledgePagination.currentPage"
              v-model:page-size="knowledgePagination.pageSize"
              :total="knowledgePagination.total"
              :page-sizes="PAGE_SIZE_OPTIONS"
              :background="true"
              layout="total, sizes, prev, pager, next, jumper"
              :style="{
                '--el-pagination-bg-color': 'var(--zh-background-capsule)',
                '--el-pagination-button-bg-color': 'var(--zh-background-option)',
                '--el-pagination-hover-color': 'var(--zh-text-theme)',
              }"
              @current-change="handleKnowledgePageChange"
              @size-change="handleKnowledgeSizeChange"
            />
          </div>
        </template>
      </el-card>

      <!-- 4.4 知识条目检索面板（可折叠） -->
      <div class="mt-5">
        <el-card
          shadow="never"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <!-- 面板标题行（可点击折叠） -->
          <div
            class="flex items-center justify-between cursor-pointer select-none"
            @click="toggleKnowledgeSearch"
          >
            <div class="flex items-center gap-2">
              <span :style="{ fontSize: 'var(--zh-font-size15)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                知识条目检索
              </span>
              <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }">
                （基于向量语义匹配搜索知识库条目）
              </span>
            </div>
            <el-icon
              class="transition-transform duration-300"
              :class="{ 'rotate-180': knowledgeSearchExpanded }"
              :style="{ color: 'var(--zh-text-caption)' }"
            >
              <ArrowDown />
            </el-icon>
          </div>

          <!-- 展开内容区 -->
          <div
            v-show="knowledgeSearchExpanded"
            class="mt-4"
          >
            <div class="flex items-center gap-3 mb-4">
              <el-input
                v-model="knowledgeSearchKeyword"
                placeholder="输入关键词检索知识条目..."
                clearable
                size="default"
                :prefix-icon="Search"
                style="flex: 1; max-width: 480px;"
                @keyup.enter="handleKnowledgeSearch"
                @clear="knowledgeSearchResults = []"
              />
              <el-button type="primary" :loading="isKnowledgeSearching" @click="handleKnowledgeSearch">
                搜索
              </el-button>
            </div>

            <!-- 搜索结果 -->
            <template v-if="knowledgeSearchResults.length > 0">
              <div
                class="rounded-lg p-4"
                :style="{ border: '1px solid ' + 'var(--zh-line-border)', background: 'var(--zh-background-light-gray)' }"
              >
                <p :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)', marginBottom: '12px' }">
                  检索结果（{{ knowledgeSearchResults.length }} 条）：
                </p>
                <div
                  v-for="(item, idx) in knowledgeSearchResults"
                  :key="item.id"
                  class="py-2.5"
                  :class="{ 'border-t': idx > 0 }"
                  :style="{ borderColor: 'var(--zh-line-parting)' }"
                >
                  <p :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-primary)', marginBottom: '4px' }">
                    {{ idx + 1 }}. {{ item.content }}
                  </p>
                  <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }">
                    来源：{{ item.source }} · 匹配度 {{ item.matchRate }}%
                  </span>
                </div>
              </div>
            </template>
            <template v-else-if="knowledgeSearchKeyword && !isKnowledgeSearching">
              <div :style="{ padding: '24px 0', textAlign: 'center' }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-disabled)' }">
                  未找到与「{{ knowledgeSearchKeyword }}」相关的知识条目
                </span>
              </div>
            </template>
          </div>
        </el-card>
      </div>
    </template>

    <!-- ===================================================================
         5. 批量上传对话框
         =================================================================== -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传公共资源"
      width="640px"
      destroy-on-close
      :style="{
        '--el-dialog-bg-color': 'var(--zh-background-pop)',
        '--el-dialog-border-radius': 'var(--zh-radius16)',
      }"
    >
      <!-- 拖拽上传区 -->
      <div
        class="upload-dropzone flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-200"
        :style="{
          border: '2px dashed var(--zh-line-heavier)',
          borderRadius: 'var(--zh-radius12)',
          background: 'var(--zh-background-light-gray)',
          minHeight: '160px',
        }"
        @click="() => { /* el-upload 会自动处理点击 */ }"
      >
        <el-icon :size="48" :style="{ color: 'var(--zh-text-caption)' }">
          <Upload />
        </el-icon>
        <p :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-caption)' }">
          将文件拖拽到此处，或<span :style="{ color: 'var(--zh-text-link)', textDecoration: 'underline' }">点击上传</span>
        </p>
        <p :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
          支持 PDF / Word / PPT / 图片 / 音视频，单文件最大 500MB，单次最多 20 个文件
        </p>
      </div>

      <!-- 已选文件列表（演示用静态数据） -->
      <div v-if="uploadFileList.length > 0" class="mt-4">
        <p :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 500, color: 'var(--zh-text-primary)', marginBottom: '8px' }">
          已选文件（{{ uploadFileList.length }} 个）：
        </p>
        <div
          class="rounded-lg overflow-hidden"
          :style="{ border: '1px solid var(--zh-line-border)' }"
        >
          <div
            v-for="file in uploadFileList"
            :key="file.uid"
            class="flex items-center gap-3 px-4 py-2.5 border-b last:border-0"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <span class="text-lg">{{ getFileIcon(file.format) }}</span>
            <span class="flex-1 truncate" :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)' }">
              {{ file.name }}
            </span>
            <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }">
              {{ formatFileSize(file.size || 0) }}
            </span>
            <span
              v-if="isFileOversized(file.size || 0)"
              :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-red)' }"
            >
              ⚠ 超限
            </span>
            <span v-else :style="{ color: 'var(--zh-green)' }">✅</span>
            <el-button
              :icon="Delete"
              circle
              size="small"
              :style="{ color: 'var(--zh-text-caption)' }"
              @click="removeUploadFile(file.uid)"
            />
          </div>
        </div>
      </div>

      <!-- 空状态下演示添加文件的按钮 -->
      <div v-else class="mt-4 flex justify-center">
        <el-button size="small" @click="handleFileSelected({ name: '2026版数学教材（必修三）.pdf', size: 128 * 1024 * 1024, format: 'pdf' })">
          + 添加示例文件（PDF）
        </el-button>
        <el-button size="small" class="ml-2" @click="handleFileSelected({ name: '细胞分裂动画.mp4', size: 320 * 1024 * 1024, format: 'mp4' })">
          + 添加示例文件（MP4）
        </el-button>
      </div>

      <!-- 资源分类设置 -->
      <div class="mt-5">
        <p :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 500, color: 'var(--zh-text-primary)', marginBottom: '8px' }">
          资源分类设置（批量应用）
        </p>
        <div class="flex items-center gap-3">
          <el-select v-model="uploadCategory.subject" placeholder="选择学科" clearable size="default" style="width: 140px;">
            <el-option v-for="opt in SUBJECT_OPTIONS.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="uploadCategory.type" placeholder="资源类型" clearable size="default" style="width: 140px;">
            <el-option v-for="opt in RESOURCE_TYPE_OPTIONS.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="uploadCategory.grade" placeholder="适用学段" clearable size="default" style="width: 140px;">
            <el-option v-for="opt in GRADE_OPTIONS.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </div>
      </div>

      <!-- 底部按钮 -->
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="isUploading" :disabled="uploadFileList.length === 0" @click="handleUpload">
            {{ isUploading ? '上传中...' : `开始上传 (${uploadFileList.length})` }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ===================================================================
         6. 资源详情抽屉
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
        <span :style="{ fontSize: 'var(--zh-font-size16)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
          资源详情 — {{ currentResource?.id || '' }}
        </span>
      </template>

      <template v-if="currentResource">
        <!-- 预览区 -->
        <div
          class="rounded-lg flex items-center justify-center mb-4 overflow-hidden"
          :style="{
            background: 'var(--zh-background-light-gray)',
            border: '1px solid var(--zh-line-border)',
            height: '200px',
          }"
        >
          <div class="text-center">
            <span class="text-5xl">{{ getFileIcon(currentResource.format) }}</span>
            <p :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)', marginTop: '8px' }">
              [此处需填写：文件预览/封面缩略图 — 建议尺寸 480×270px]
            </p>
          </div>
        </div>

        <!-- 基本信息区 -->
        <div
          class="rounded-lg p-4 mb-4"
          :style="{ border: '1px solid var(--zh-line-border)' }"
        >
          <div class="grid gap-y-3 gap-x-2" style="grid-template-columns: 90px 1fr;">
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">资源名称</span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-primary)', fontWeight: 500 }">
              {{ currentResource.name }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">文件类型</span>
            <span>
              <el-tag :type="RESOURCE_TYPE_TAG_MAP[currentResource.type] || 'info'" size="small" effect="plain">
                {{ RESOURCE_TYPE_LABEL_MAP[currentResource.type] || currentResource.type }}
              </el-tag>
              <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', marginLeft: '6px' }">
                · {{ getFileFormatLabel(currentResource.format) }}
              </span>
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">文件大小</span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">
              {{ currentResource.size }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">所属学科</span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">
              {{ SUBJECT_LABEL_MAP[currentResource.subject] || currentResource.subject }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">适用学段</span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">
              {{ GRADE_LABEL_MAP[currentResource.grade] || currentResource.grade }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">上传时间</span>
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
              {{ currentResource.updatedAt }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">上传者</span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">
              {{ currentResource.uploader || '管理员' }}
            </span>

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">版本</span>
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
              {{ currentResource.version }}
            </span>
          </div>
        </div>

        <!-- 分类标签区 -->
        <div
          class="rounded-lg p-4 mb-4"
          :style="{ border: '1px solid var(--zh-line-border)' }"
        >
          <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)', display: 'block', marginBottom: '8px' }">
            分类标签
          </span>
          <div class="flex flex-wrap gap-1.5">
            <el-tag
              v-for="tag in (currentResource.tags || [])"
              :key="tag"
              size="small"
              :style="{ background: 'var(--zh-background-tag)', borderColor: 'var(--zh-line-tag)', borderRadius: 'var(--zh-radius4)' }"
            >
              {{ tag }}
            </el-tag>
            <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }">
              + 添加标签
            </el-button>
          </div>
        </div>

        <!-- 向量化状态区 -->
        <div
          class="rounded-lg p-4 mb-4"
          :style="{ border: '1px solid var(--zh-line-border)' }"
        >
          <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)', display: 'block', marginBottom: '8px' }">
            向量化状态
          </span>
          <div class="flex items-center gap-2 mb-2">
            <span
              class="inline-block w-2 h-2 rounded-full"
              :class="{ 'animate-pulse': currentResource.status === 'processing' }"
              :style="{ background: getResourceStatusDotColor(currentResource.status) }"
            ></span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 500, color: 'var(--zh-text-primary)' }">
              {{ RESOURCE_STATUS_LABEL_MAP[currentResource.status] || currentResource.status }}
            </span>
            <span
              v-if="currentResource.status === 'ready'"
              :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }"
            >
              · {{ (currentResource.vectorCount || 0).toLocaleString() }} 条知识条目
            </span>
          </div>
          <el-progress
            :percentage="currentResource.vectorProgress || 0"
            :status="getProgressStatus(currentResource.status)"
            :stroke-width="8"
            :striped="currentResource.status === 'processing'"
            :striped-flow="currentResource.status === 'processing'"
          />
          <!-- 失败原因提示 -->
          <div
            v-if="currentResource.status === 'failed' && currentResource.failReason"
            class="flex items-start gap-2 mt-2 p-2 rounded"
            :style="{ background: 'var(--zh-yellow-light)', borderLeft: '3px solid var(--zh-orange)' }"
          >
            <WarningFilled :size="14" :style="{ color: 'var(--zh-orange)', marginTop: '1px', flexShrink: 0 }" />
            <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-secondary)' }">
              {{ currentResource.failReason }}
            </span>
          </div>
        </div>

        <!-- 操作区 -->
        <div
          class="rounded-lg p-4"
          :style="{ border: '1px solid var(--zh-line-border)', background: 'var(--zh-background-light-gray)' }"
        >
          <span :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)', display: 'block', marginBottom: '12px' }">
            操作
          </span>
          <div class="flex flex-wrap gap-2">
            <el-button
              type="primary"
              :icon="Refresh"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleReparse(currentResource); drawerVisible = false;"
            >
              重新解析
            </el-button>
            <el-button
              :icon="Edit"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
            >
              编辑分类
            </el-button>
            <el-button
              :icon="Download"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
            >
              下载
            </el-button>
            <el-button
              type="danger"
              :icon="Delete"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleDeleteResource(currentResource); drawerVisible = false;"
            >
              删除
            </el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
/* ===== Tab 分段控件样式覆盖（复用 ContentAudit 样式） ===== */
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
:deep(.resource-table-row),
:deep(.vector-table-row) {
  transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 待处理行 — 左侧橙色强调条 ===== */
:deep(.pending-resource-row td:first-child) {
  position: relative;
}
:deep(.pending-resource-row td:first-child::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--zh-orange);
}

/* ===== 失败行 — 左侧红色强调条 ===== */
:deep(.failed-resource-row td:first-child) {
  position: relative;
}
:deep(.failed-resource-row td:first-child::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--zh-red);
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

/* ===== 上传拖拽区悬浮态 ===== */
.upload-dropzone:hover {
  border-color: var(--zh-text-theme) !important;
  background: var(--zh-background-weaken) !important;
}

/* ===== 旋转动画（折叠箭头） ===== */
.rotate-180 {
  transform: rotate(180deg);
}

/* ===== KPI 卡片悬浮态（复用 Dashboard 样式） ===== */
.kpi-card {
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1),
              transform 200ms cubic-bezier(0.4, 0, 0.2, 1),
              border-color 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.kpi-card:hover {
  box-shadow: var(--zh-shadow2) !important;
  transform: translateY(-2px);
  border-color: var(--zh-line-heavier) !important;
}

/* ===== 骨架屏脉冲态 ===== */
.kpi-card-skeleton :deep(.skeleton-loader),
.skeleton-pulse .skeleton-loader {
  animation: shimmer 1.5s infinite;
}

/* ===== 脉冲动画（状态指示灯） ===== */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
