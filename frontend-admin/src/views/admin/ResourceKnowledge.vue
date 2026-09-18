<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDrawer, ElDialog, ElSkeleton, ElEmpty, ElMessageBox, ElMessage, ElTooltip,
      ElRadioGroup, ElRadioButton, ElProgress, ElUpload
    - ElementPlus Icons: Search, Refresh, Delete, Upload, Document, VideoCamera, PictureFilled,
      Headset, FolderOpened, Files, Download, View, Edit, CircleCheckFilled,
      WarningFilled, Clock, Loading, ArrowDown, ArrowUp, Top
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount` from Vue
  - 依赖:
    - `@/apis/resource`: 导入 `getPublicResources`（API-83，分页查询公共资源）与 ai-index 系列（overview/tasks/search/reparse，透传 Python 索引查询）
  - 输入: 无 props；资源列表来自 API-83（服务端分页），知识库数据来自 PostgreSQL a12_resource_index（服务端筛选/分页）
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
  WarningFilled,
  Clock,
  Loading,
  ArrowDown,
  ArrowUp,
  Top,
  Film,
  Grid,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPublicResources,
  createUploadSession,
  completeUpload,
  updateResource,
  deleteResource,
  reparseResource,
  getDownloadUrl,
  getProcessingStatus,
  bootstrapAiIndex,
  getAiIndexOverview,
  getAiIndexTasks,
  getAiIndexResource,
  searchAiIndex,
  reparseAiIndex,
} from '@/apis/resource'
import FileDropUpload from '@/components/admin/FileDropUpload.vue'
import { apiRequest } from '@/utils/api'
import { buildFileKey, formatFileSize, getFileExtension } from '@/utils/file'

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

/** 资源类型 → 缩略图图标映射（Element Plus 图标组件，用于无缩略图时的占位） */
const RESOURCE_TYPE_ICON_MAP = {
  pdf: Document,
  docx: Document,
  pptx: Film,
  xlsx: Grid,
  mp4: VideoCamera,
  avi: VideoCamera,
  mov: VideoCamera,
  jpg: PictureFilled,
  png: PictureFilled,
  gif: PictureFilled,
  mp3: Headset,
  wav: Headset,
  other: Document,
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

/** 学科筛选项（用于上传分类设置） */
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

/** 资源启用状态筛选项（对应 ResourceVO.status：1=启用 0=停用） */
const RESOURCE_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '已启用', value: 1 },
  { label: '已停用', value: 0 },
]

/** 资源解析状态（对应 ResourceVO.ai_index_status）→ 显示标签映射 */
const RESOURCE_STATUS_LABEL_MAP = {
  completed: '已就绪',
  indexing: '解析中',
  failed: '解析失败',
  pending: '待处理',
  disabled: '已停用',
}

/** 资源解析状态 → Tag 类型映射 */
const RESOURCE_STATUS_TAG_MAP = {
  completed: 'success',
  indexing: '',
  failed: 'danger',
  pending: 'info',
  disabled: 'info',
}

/** 资源解析状态 → 圆点颜色映射 */
const RESOURCE_STATUS_DOT_COLOR_MAP = {
  completed: 'var(--zh-green)',
  indexing: 'var(--zh-theme-primary)',
  failed: 'var(--zh-red)',
  pending: 'var(--zh-text-disabled)',
  disabled: 'var(--zh-text-disabled)',
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
// 配置常量 — Tab 2：知识库维护（真实数据：PG a12_resource_index）
// ===================================================================

/**
 * 索引状态筛选项（服务端过滤 parse_status）
 * 注：PG 行仅在终态落库（completed/failed），「索引中」由 MySQL ai_index_status 合成，无法作为服务端筛选值
 */
const VECTOR_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

/** 索引状态 → 显示标签映射（indexing 为 MySQL 合成状态，pending 为兜底显示） */
const VECTOR_STATUS_LABEL_MAP = {
  completed: '已完成',
  indexing: '索引中',
  failed: '失败',
  pending: '待解析',
}

/** 索引状态 → Tag 类型映射 */
const VECTOR_STATUS_TAG_MAP = {
  completed: 'success',
  indexing: '',
  failed: 'danger',
  pending: 'info',
}

/** 索引状态 → 圆点颜色映射 */
const VECTOR_STATUS_DOT_COLOR_MAP = {
  completed: 'var(--zh-green)',
  indexing: 'var(--zh-theme-primary)',
  failed: 'var(--zh-red)',
  pending: 'var(--zh-text-disabled)',
}

/** 知识索引来源域筛选项（对应 a12_resource_index.source_type） */
const KNOWLEDGE_SOURCE_OPTIONS = [
  { label: '全部来源', value: '' },
  { label: '公共资源', value: 'public' },
  { label: '个人素材', value: 'personal' },
]

/** 来源域 → 显示标签映射 */
const KNOWLEDGE_SOURCE_LABEL_MAP = {
  public: '公共资源',
  personal: '个人素材',
}

/** 来源域 → Tag 类型映射 */
const KNOWLEDGE_SOURCE_TAG_MAP = {
  public: 'primary',
  personal: 'warning',
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
const activeTab = ref('resources')

/** 资源列表数据 */
const resourceList = ref([])

/** 向量化任务列表数据 */
const vectorTaskList = ref([])

/** Tab 1 筛选条件（类型/状态均为 API-83 支持的服务端筛选，状态：1=启用 0=停用） */
const resourceFilters = reactive({
  type: '',
  status: '',
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

/** 上传队列中的重命名状态 */
const renamingUploadUid = ref(null)
const uploadRenameDraft = ref('')

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

/** 知识条目检索来源域（'' = 全部 / public / personal） */
const knowledgeSearchScope = ref('')

/** 知识条目搜索结果 */
const knowledgeSearchResults = ref([])

/** 知识条目检索元信息（search_mode / latency_ms，来自真实检索响应） */
const knowledgeSearchMeta = ref(null)

/** 知识条目搜索中 */
const isKnowledgeSearching = ref(false)

/** 知识索引总览统计（GET ai-index/overview，KPI 数据源） */
const indexOverview = ref(null)

/** 分块明细抽屉可见性 */
const chunkDrawerVisible = ref(false)

/** 分块明细抽屉加载中 */
const chunkDrawerLoading = ref(false)

/** 当前查看分块明细的任务行 */
const currentChunkRow = ref(null)

/** 分块明细列表（真实 chunks） */
const chunkList = ref([])

/** 操作执行中状态 */
const isActionLoading = ref(false)

/** 上传限制 */
const MAX_UPLOAD_FILES = 20
const MAX_UPLOAD_FILE_SIZE = 500 * 1024 * 1024
const SUPPORTED_UPLOAD_EXTENSIONS = new Set([
  'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt',
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp3', 'wav', 'm4a',
  'mp4', 'avi', 'mov', 'mkv',
])
/** 资源扩展名白名单数组（供 FileDropUpload 的 acceptExts 使用） */
const SUPPORTED_UPLOAD_EXT_LIST = Array.from(SUPPORTED_UPLOAD_EXTENSIONS)
/** 资源 MIME 前缀白名单（与扩展名白名单按 OR 命中） */
const SUPPORTED_UPLOAD_MIME_PREFIXES = ['image/', 'audio/', 'video/']
/** 文件选择器 accept 属性串（扩展名 + MIME 通配，与白名单保持一致） */
const UPLOAD_INPUT_ACCEPT = '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.mp4,.avi,.mov,.mkv,image/*,audio/*,video/*'

/** 上传队列中尚未完成的文件 */
const pendingUploadFiles = computed(() => {
  return uploadFileList.value.filter((file) => file.status !== 'success')
})

/** 已完成上传的文件数量 */
const completedUploadCount = computed(() => {
  return uploadFileList.value.filter((file) => file.status === 'success').length
})

/** 上传整体进度 */
const uploadOverallProgress = computed(() => {
  if (uploadFileList.value.length === 0) return 0
  const total = uploadFileList.value.reduce((sum, file) => sum + (Number(file.progress) || 0), 0)
  return Math.round(total / uploadFileList.value.length)
})

/** 队列中的文件是否全部完成 */
const uploadAllComplete = computed(() => {
  return uploadFileList.value.length > 0 && uploadFileList.value.every((file) => file.status === 'success')
})

// ===================================================================
// 数据映射工具 — Tab 1：资源数据（API-83 ResourceVO → 前端行对象）
// ===================================================================

/**
 * 格式化日期时间（后端 LocalDateTime 序列化值）
 * @param {string} value - 形如 2026-09-07T21:30:00 的时间字符串
 * @returns {string} 形如 2026-09-07 21:30:00 的显示字符串
 */
const formatDateTime = (value) => {
  if (!value) return '—'
  return String(value).replace('T', ' ').slice(0, 19)
}

/**
 * 从资源文件 URL 中提取文件扩展名
 * @param {string} fileUrl - 资源文件 URL
 * @returns {string} 小写扩展名，无法识别时返回 other
 */
const extractFileExtension = (fileUrl) => {
  const cleanPath = String(fileUrl || '').split('?')[0]
  const dotIndex = cleanPath.lastIndexOf('.')
  if (dotIndex === -1 || dotIndex === cleanPath.length - 1) return 'other'
  const ext = cleanPath.slice(dotIndex + 1).toLowerCase()
  return /^[a-z0-9]+$/.test(ext) ? ext : 'other'
}

/**
 * 将后端 ResourceVO（API-83）映射为前端资源行对象
 * @param {Object} vo - 后端 ResourceVO
 * @returns {Object} 前端资源行对象
 */
const mapResourceRow = (vo) => {
  const aiStatus = vo.ai_index_status || 'pending'
  return {
    id: vo.id,
    name: vo.title,
    format: extractFileExtension(vo.file_url),
    type: vo.resource_type,
    subject: vo.subject,
    grade: vo.grade,
    size: vo.file_size != null ? formatFileSize(Number(vo.file_size)) : '—',
    status: aiStatus,
    description: vo.description || '',
    updatedAt: formatDateTime(vo.updated_at),
    uploader: vo.uploaded_by != null ? `用户#${vo.uploaded_by}` : '—',
    tags: [SUBJECT_LABEL_MAP[vo.subject], GRADE_LABEL_MAP[vo.grade]].filter(Boolean),
    vectorProgress: aiStatus === 'completed' ? 100 : 0,
    failReason: vo.ai_index_error || '',
  }
}

// ===================================================================
// 数据映射 — Tab 2：知识索引任务行（Python list_resources item → 前端行对象）
// ===================================================================

/** 短文件类型 → 图标映射（Element Plus 图标组件，metadata.file_type 存 short 标识） */
const KNOWLEDGE_FILE_TYPE_ICON_MAP = {
  word: Document,
  pdf: Document,
  ppt: Film,
  txt: Document,
  image: PictureFilled,
  audio: Headset,
  video: VideoCamera,
  other: Document,
}

/**
 * 获取知识索引任务行的文件图标（兼容 short 类型标识与扩展名）
 * @param {string} fileType - 文件类型（word/pdf/ppt 或 docx/mp4 等扩展名）
 * @returns {Component} Element Plus 图标组件
 */
const getKnowledgeFileIcon = (fileType) => {
  return KNOWLEDGE_FILE_TYPE_ICON_MAP[fileType] || RESOURCE_TYPE_ICON_MAP[fileType] || RESOURCE_TYPE_ICON_MAP.other
}

/**
 * 将后端索引任务行映射为前端行对象
 * @param {Object} item - Python list_resources 返回的条目（resource_key/source_type/parse_status/chunk_count...）
 * @returns {Object} 前端任务行对象
 */
const mapVectorTaskRow = (item) => {
  const meta = item.metadata || {}
  return {
    resourceKey: item.resource_key,
    sourceType: item.source_type,
    resourceId: item.resource_id,
    resourceName: item.title || meta.title || meta.file_name || `资源#${item.resource_id}`,
    resourceFormat: String(meta.file_type || '').toLowerCase(),
    entryCount: item.chunk_count || 0,
    textLength: item.text_length || 0,
    status: item.effective_status || item.parse_status || '',
    failReason: item.error_message || '',
    available: item.available,
    allowAi: item.allow_ai,
    indexedAt: formatDateTime(item.indexed_at),
    updatedAt: formatDateTime(item.updated_at),
  }
}

// ===================================================================
// 计算属性：知识库概览统计（GET ai-index/overview 真实数据驱动）
// ===================================================================

/** 知识条目总数（a12_resource_index 全部行） */
const totalKnowledgeEntries = computed(() => indexOverview.value?.resource_count || 0)

/** 已完成向量化条目数（parse_status=completed 的资源数） */
const completedVectorEntries = computed(() => {
  const groups = indexOverview.value?.groups || []
  return groups
    .filter((g) => g.parse_status === 'completed')
    .reduce((sum, g) => sum + g.resource_count, 0)
})

/** 待处理资源数（解析失败，可重试） */
const pendingVectorCount = computed(() => {
  const groups = indexOverview.value?.groups || []
  return groups
    .filter((g) => g.parse_status === 'failed')
    .reduce((sum, g) => sum + g.resource_count, 0)
})

/** 向量化覆盖率（已向量化 / 总数） */
const vectorCoverage = computed(() => {
  if (totalKnowledgeEntries.value === 0) return '0%'
  return ((completedVectorEntries.value / totalKnowledgeEntries.value) * 100).toFixed(1) + '%'
})

/** 索引分块总数（真实分块行数） */
const totalChunkCount = computed(() => indexOverview.value?.chunk_count || 0)

/** 累计检索次数（a12_retrieval_log 行数） */
const retrievalLogCount = computed(() => indexOverview.value?.retrieval_log_count || 0)

/** 向量维度（真实 embedding 配置） */
const embeddingDimensions = computed(() => indexOverview.value?.embedding_dimensions || '—')

/** PostgreSQL 可用性（真实状态） */
const postgresAvailable = computed(() => indexOverview.value?.postgres_available !== false)

// ===================================================================
// 数据筛选与获取方法
// ===================================================================

/**
 * 获取资源列表数据（API-83 GET /api/v1/admin/public-resources）
 * 服务端分页，支持按资源类型与启用状态筛选
 */
const fetchResources = async () => {
  isTableLoading.value = true
  try {
    const statusValue = resourceFilters.status
    const res = await getPublicResources({
      resource_type: resourceFilters.type || undefined,
      status: statusValue === '' || statusValue == null ? undefined : Number(statusValue),
      page: resourcePagination.currentPage,
      size: resourcePagination.pageSize,
    })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '资源加载失败')
      resourceList.value = []
      resourcePagination.total = 0
      return
    }
    const data = res?.data || {}
    resourceList.value = (data.records || []).map(mapResourceRow)
    resourcePagination.total = data.total || 0
  } catch {
    ElMessage.error('资源加载失败，请稍后重试')
    resourceList.value = []
    resourcePagination.total = 0
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 获取知识索引总览统计（GET ai-index/overview → Python overview → PG 真实统计）
 * KPI 四卡数据源；失败时置空（KPI 显示 0，不打断任务列表）
 */
const fetchIndexOverview = async () => {
  try {
    indexOverview.value = unwrapResult(await getAiIndexOverview(), '知识库概览加载失败')
  } catch (error) {
    ElMessage.error(error?.message || '知识库概览加载失败')
    indexOverview.value = null
  }
}

/**
 * 获取向量化任务列表（GET ai-index/tasks → Python list_resources，服务端筛选 + 分页）
 * 行状态由后端合成：PG parse_status（终态）+ MySQL ai_index_status（indexing 进行中）
 */
const fetchVectorTasks = async () => {
  isTableLoading.value = true
  try {
    const payload = unwrapResult(await getAiIndexTasks({
      source_type: knowledgeFilters.type || undefined,
      parse_status: knowledgeFilters.status || undefined,
      keyword: knowledgeFilters.keyword.trim() || undefined,
      page: knowledgePagination.currentPage,
      size: knowledgePagination.pageSize,
    }), '任务列表加载失败')
    vectorTaskList.value = (payload?.items || []).map(mapVectorTaskRow)
    knowledgePagination.total = payload?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '任务列表加载失败，请稍后重试')
    vectorTaskList.value = []
    knowledgePagination.total = 0
  } finally {
    isTableLoading.value = false
  }
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
    fetchIndexOverview()
  }
}

/**
 * 页面首次数据加载 — 拉取当前 Tab 对应数据
 */
const loadData = () => {
  isLoading.value = true
  if (activeTab.value === 'resources') {
    fetchResources().finally(() => {
      isLoading.value = false
    })
  } else {
    fetchVectorTasks()
    fetchIndexOverview()
    isLoading.value = false
  }
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
  resourceFilters.status = ''
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
 * 获取文件格式对应的缩略图图标（Element Plus 图标组件）
 * @param {string} format - 文件扩展名
 * @returns {Component} Element Plus 图标组件
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
  const latest = resourceList.value.find((r) => r.id === row.id) || row
  currentResource.value = reactive({ ...latest })
  drawerVisible.value = true
}

/** 重命名已入库资源（API-87 PATCH），成功后同步本地行与知识库任务来源名称 */
const handleRenameResource = (row) => {
  ElMessageBox.prompt('请输入新的资源名称', '重命名资源', {
    confirmButtonText: '保存名称',
    cancelButtonText: '取消',
    inputValue: row.name,
    inputPlaceholder: '例如：2026版数学教材（必修三）.pdf',
    inputValidator: (value) => value?.trim() ? true : '资源名称不能为空',
  })
    .then(async ({ value }) => {
      const nextName = value.trim()
      const res = await updateResource(row.id, { title: nextName })
      const vo = unwrapResult(res, '重命名失败')
      row.name = vo.title || nextName
      row.updatedAt = new Date().toISOString().replace('T', ' ').slice(0, 16)
      if (currentResource.value?.id === row.id) {
        currentResource.value.name = row.name
        currentResource.value.updatedAt = row.updatedAt
      }
      ElMessage.success(`已将资源重命名为「${row.name}」`)
    })
    .catch((error) => {
      if (error !== 'cancel' && error !== 'close' && error?.message) ElMessage.error(error.message)
    })
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
  renamingUploadUid.value = null
  uploadRenameDraft.value = ''
  uploadDialogVisible.value = true
}

/** 现有队列的去重键集合（供 FileDropUpload 过滤重复文件与计算数量余量） */
const uploadExistingKeys = computed(() => {
  return uploadFileList.value.map((file) => buildFileKey(file))
})

/**
 * 接收 FileDropUpload 通过通用校验（去重/大小/类型/数量上限）的文件，生成上传队列项
 * @param {Array<File>} files - 通过通用校验的文件集合
 */
const onUploadFilesAccepted = (files) => {
  files.forEach((file, index) => {
    uploadFileList.value.push({
      uid: `${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
      raw: file,
      mimeType: file.type || '',
      name: file.name,
      size: file.size,
      lastModified: file.lastModified,
      status: 'ready',
      progress: 0,
      format: getFileExtension(file.name),
      error: '',
    })
  })
}

/** 开始编辑上传队列中的文件名 */
const beginUploadRename = (file) => {
  if (isUploading.value) return
  renamingUploadUid.value = file.uid
  uploadRenameDraft.value = file.name
}

/** 取消上传队列中的文件重命名 */
const cancelUploadRename = () => {
  renamingUploadUid.value = null
  uploadRenameDraft.value = ''
}

/** 保存上传队列中的文件名 */
const commitUploadRename = (file) => {
  if (renamingUploadUid.value !== file.uid) return
  const nextName = uploadRenameDraft.value.trim()
  if (!nextName) {
    ElMessage.warning('文件名不能为空')
    return
  }
  file.name = nextName
  file.format = getFileExtension(nextName)
  cancelUploadRename()
}

/**
 * 移除已选上传文件
 * @param {number} uid - 文件唯一标识
 */
const removeUploadFile = (uid) => {
  if (isUploading.value) return
  uploadFileList.value = uploadFileList.value.filter((f) => f.uid !== uid)
  if (renamingUploadUid.value === uid) cancelUploadRename()
}

/**
 * 统一解包 Result 响应：非成功码（0/200）抛出业务错误信息
 * @param {{code: number, message?: string, data?: any}} res - 后端统一响应
 * @param {string} fallbackMessage - 响应缺失时的兜底错误文案
 * @returns {any} 响应 data 字段
 */
const unwrapResult = (res, fallbackMessage) => {
  if (!res || (res.code !== 0 && res.code !== 200)) {
    throw new Error(res?.message || fallbackMessage)
  }
  return res.data
}

/**
 * OSS 预签名 PUT 直传（axios onUploadProgress 汇报 0-100 上传进度）
 * 注意：Content-Type 必须与创建会话时的 file_type 一致，否则预签名校验失败
 * @param {Object} queueFile - 上传队列项（含 raw 原始 File 与 mimeType）
 * @param {string} uploadUrl - 后端签发的预签名 PUT URL
 * @param {Function} onProgress - 进度回调（百分比数字）
 * @returns {Promise<void>}
 */
const uploadToOss = (queueFile, uploadUrl, onProgress) => apiRequest({
  url: uploadUrl,
  method: 'put',
  data: queueFile.raw,
  headers: { 'Content-Type': queueFile.mimeType || 'application/octet-stream' },
  timeout: 600000,
  onUploadProgress: (event) => {
    if (event.total) onProgress((event.loaded / event.total) * 100)
  },
})

/**
 * 上传单个文件：创建会话 → OSS 直传 → 确认完成（后端异步触发索引解析）
 * @param {Object} queueFile - 上传队列项
 * @returns {Promise<number|null>} 成功返回资源 ID（upload_id），失败返回 null
 */
const uploadSingleFile = async (queueFile) => {
  queueFile.status = 'uploading'
  queueFile.progress = 0
  try {
    const sessionRes = await createUploadSession({
      resource_type: uploadCategory.type || 'document',
      title: queueFile.name,
      subject: uploadCategory.subject || '',
      grade: uploadCategory.grade || '',
      file_name: queueFile.name,
      file_type: queueFile.mimeType || 'application/octet-stream',
      file_size: queueFile.size || 0,
    })
    const payload = unwrapResult(sessionRes, '创建上传会话失败')
    await uploadToOss(queueFile, payload.upload_url, (percent) => {
      queueFile.progress = Math.min(99, Math.round(percent))
    })
    queueFile.progress = 99
    await unwrapResult(await completeUpload(payload.upload_id), '确认上传失败')
    queueFile.progress = 100
    queueFile.status = 'success'
    return payload.upload_id
  } catch (error) {
    queueFile.status = 'error'
    queueFile.error = error?.message || '上传失败'
    return null
  }
}

/**
 * 执行上传：顺序走三段式（会话 → OSS 直传 → complete），全部结束后刷新列表并对新资源启动索引状态轮询
 */
const handleUpload = () => {
  const filesToUpload = uploadFileList.value.filter((file) => file.status === 'ready' || file.status === 'error')
  if (filesToUpload.length === 0) {
    if (uploadAllComplete.value) uploadDialogVisible.value = false
    else ElMessage.warning('请先选择要上传的文件')
    return
  }
  isUploading.value = true
  void runUploadQueue(filesToUpload)
}

/**
 * 顺序执行上传队列；结束后回到第 1 页拉取服务端真数据，并对新上传的资源逐个启动索引状态轮询
 * @param {Array<Object>} filesToUpload - 待上传队列项
 */
const runUploadQueue = async (filesToUpload) => {
  const uploadedIds = []
  for (const queueFile of filesToUpload) {
    const uploadId = await uploadSingleFile(queueFile)
    if (uploadId) uploadedIds.push(uploadId)
  }
  isUploading.value = false
  if (uploadedIds.length === 0) {
    ElMessage.error('上传失败，请检查网络或稍后重试')
    return
  }
  ElMessage.success(`成功上传 ${uploadedIds.length} 个资源，AI 索引解析已在后台进行`)
  resourcePagination.currentPage = 1
  await fetchResources()
  uploadedIds.forEach((id) => {
    const row = resourceList.value.find((r) => r.id === id)
    if (row) pollAiIndexStatus(row)
  })
}

/**
 * 删除资源 — 二次确认后调 DELETE 接口（同步清理 PG 向量索引与 OSS 对象）
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
    .then(async () => {
      await unwrapResult(await deleteResource(row.id), '删除失败')
      resourceList.value = resourceList.value.filter((r) => r.id !== row.id)
      ElMessage.success(`已删除资源「${row.name}」`)
      if (resourceList.value.length === 0 && resourcePagination.currentPage > 1) {
        resourcePagination.currentPage--
      }
    })
    .catch((error) => {
      if (error !== 'cancel' && error !== 'close' && error?.message) ElMessage.error(error.message)
    })
}

/**
 * 重新解析单个公共资源（Tab 1：POST /{id}/reparse，后端异步执行）——触发后轮询 processing-status 至出结果
 * @param {Object} row - 当前行资源数据
 */
const handleReparse = async (row) => {
  const resourceId = row.resourceId || row.id
  const name = row.resourceName || row.name
  try {
    await unwrapResult(await reparseResource(resourceId), '重新解析失败')
    const resource = resourceList.value.find((r) => r.id === resourceId)
    if (resource) {
      resource.status = 'indexing'
      resource.vectorProgress = 0
    }
    ElMessage.success(`已发起「${name}」的重新解析`)
    pollAiIndexStatus(resource || row)
  } catch (error) {
    ElMessage.error(error?.message || '重新解析失败')
  }
}

/**
 * 重新解析知识索引任务行（Tab 2：POST /ai-index/{sourceType}/{resourceId}/reparse，双域统一入口）
 * 后端仅标记 indexing 后立即返回（public 走公共同步服务、personal 走个人素材同步服务），前端轮询任务行状态
 * @param {Object} row - 当前任务行（需含 sourceType/resourceId/resourceName）
 */
const handleKnowledgeReparse = async (row) => {
  try {
    await unwrapResult(await reparseAiIndex(row.sourceType, row.resourceId), '重新解析失败')
    row.status = 'indexing'
    ElMessage.success(`已发起「${row.resourceName}」的重新解析`)
    pollKnowledgeTaskStatus(row)
  } catch (error) {
    ElMessage.error(error?.message || '重新解析失败')
  }
}

/**
 * 下载资源 — 获取 60 分钟预签名 GET URL 后触发浏览器下载
 * @param {Object} row - 当前行资源数据
 */
const handleDownloadResource = async (row) => {
  try {
    const res = await getDownloadUrl(row.id)
    const payload = unwrapResult(res, '获取下载地址失败')
    if (!payload?.download_url) throw new Error('下载地址为空')
    window.open(payload.download_url, '_blank')
  } catch (error) {
    ElMessage.error(error?.message || '下载失败')
  }
}

/** AI 索引状态轮询间隔与上限（4s × 150 ≈ 10 分钟） */
const AI_POLL_INTERVAL = 4000
const AI_POLL_MAX_ROUNDS = 150

/** 进行中的索引状态轮询定时器（按资源 ID 索引，防止重复轮询） */
const aiPollTimers = new Map()

/**
 * 轮询单资源的 AI 索引状态（GET processing-status），直至 completed/failed 或超时上限
 * @param {Object} row - 资源行（需含 id/name）
 */
const pollAiIndexStatus = (row) => {
  if (!row?.id || aiPollTimers.has(row.id)) return
  let rounds = 0
  const timer = setInterval(async () => {
    rounds += 1
    if (rounds > AI_POLL_MAX_ROUNDS) {
      clearInterval(timer)
      aiPollTimers.delete(row.id)
      ElMessage.warning(`「${row.name}」索引解析超过 10 分钟仍未完成，请稍后手动刷新查看`)
      return
    }
    try {
      const res = await getProcessingStatus(row.id)
      const payload = unwrapResult(res, '查询索引状态失败')
      const status = payload.index_status
      if (status !== 'completed' && status !== 'failed') return
      clearInterval(timer)
      aiPollTimers.delete(row.id)
      row.status = status
      row.vectorProgress = status === 'completed' ? 100 : 0
      row.failReason = payload.error_msg || ''
      if (status === 'completed') ElMessage.success(`「${row.name}」AI 索引解析完成`)
      else ElMessage.error(`「${row.name}」解析失败：${row.failReason || '未知原因'}`)
    } catch {
      // 单次查询失败（网络抖动）忽略，等待下一轮重试
    }
  }, AI_POLL_INTERVAL)
  aiPollTimers.set(row.id, timer)
}

/** Tab 2 任务状态轮询定时器（按 sourceType:resourceId 索引，防止重复轮询） */
const knowledgePollTimers = new Map()

/**
 * 轮询知识索引任务行状态（GET ai-index/resources/{st}/{id}，读 PG parse_status），直至终态或超时
 * 注：仅当 PG 行已存在时轮询有效——从未索引过的资源完成解析后才会出现在任务列表
 * @param {Object} row - 任务行（需含 sourceType/resourceId/resourceName）
 */
const pollKnowledgeTaskStatus = (row) => {
  const key = `${row.sourceType}:${row.resourceId}`
  if (!row?.resourceId || knowledgePollTimers.has(key)) return
  let rounds = 0
  const timer = setInterval(async () => {
    rounds += 1
    if (rounds > AI_POLL_MAX_ROUNDS) {
      clearInterval(timer)
      knowledgePollTimers.delete(key)
      ElMessage.warning(`「${row.resourceName}」索引解析超过 10 分钟仍未完成，请稍后手动刷新查看`)
      return
    }
    try {
      const payload = unwrapResult(await getAiIndexResource(row.sourceType, row.resourceId, 1), '查询索引状态失败')
      const status = payload?.parse_status
      if (status !== 'completed' && status !== 'failed') return
      clearInterval(timer)
      knowledgePollTimers.delete(key)
      row.status = status
      row.entryCount = payload?.chunk_count || row.entryCount
      row.failReason = payload?.error_message || ''
      fetchIndexOverview()
      if (status === 'completed') ElMessage.success(`「${row.resourceName}」AI 索引解析完成`)
      else ElMessage.error(`「${row.resourceName}」解析失败：${row.failReason || '未知原因'}`)
    } catch {
      // 单次查询失败（网络抖动）忽略，等待下一轮重试
    }
  }, AI_POLL_INTERVAL)
  knowledgePollTimers.set(key, timer)
}

/**
 * 打开分块明细抽屉（GET ai-index/resources/{st}/{id}，展示真实分块内容）
 * @param {Object} row - 当前任务行
 */
const openChunkDrawer = async (row) => {
  currentChunkRow.value = row
  chunkDrawerVisible.value = true
  chunkDrawerLoading.value = true
  chunkList.value = []
  try {
    const payload = unwrapResult(await getAiIndexResource(row.sourceType, row.resourceId, 50), '索引明细加载失败')
    chunkList.value = payload?.chunks || []
  } catch (error) {
    ElMessage.error(error?.message || '索引明细加载失败')
  } finally {
    chunkDrawerLoading.value = false
  }
}

/**
 * 批量重建全部知识索引 — 二次确认后调 bootstrap（public + personal 双域，force_reparse=true）
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
    .then(async () => {
      isTableLoading.value = true
      try {
        const res = await bootstrapAiIndex(true)
        const payload = unwrapResult(res, '重建索引失败')
        const handled = payload?.results?.length || 0
        ElMessage.success(`全量索引重建完成，共处理 ${handled} 条资源`)
        await fetchResources()
        await fetchVectorTasks()
        fetchIndexOverview()
      } catch (error) {
        ElMessage.error(error?.message || '重建索引失败，请稍后重试')
      } finally {
        isTableLoading.value = false
      }
    })
    .catch(() => {})
}

// ===================================================================
// 知识条目检索方法
// ===================================================================

/**
 * 执行知识条目检索（POST ai-index/search → Python pgvector 混合重排检索，真实向量）
 */
const handleKnowledgeSearch = async () => {
  const kw = knowledgeSearchKeyword.value.trim()
  if (!kw) {
    knowledgeSearchResults.value = []
    knowledgeSearchMeta.value = null
    return
  }
  isKnowledgeSearching.value = true
  try {
    const payload = unwrapResult(await searchAiIndex({
      query: kw,
      source_type: knowledgeSearchScope.value || undefined,
      top_k: 10,
    }), '知识检索失败')
    const matches = payload?.matches || []
    knowledgeSearchResults.value = matches.map((m) => ({
      id: m.chunk_id,
      content: m.content,
      // 分块 metadata 携带索引时的 title；老数据缺失时回退 resource_key
      source: m.metadata?.title || m.resource_id,
      matchRate: Math.round((m.score || 0) * 100),
      rank: m.rank,
      matchType: m.match_type || '',
    }))
    knowledgeSearchMeta.value = {
      mode: payload?.search_mode || '',
      latency: payload?.latency_ms ?? null,
    }
  } catch (error) {
    ElMessage.error(error?.message || '知识检索失败')
  } finally {
    isKnowledgeSearching.value = false
  }
}

/**
 * 切换知识条目检索面板展开/折叠
 */
const toggleKnowledgeSearch = () => {
  knowledgeSearchExpanded.value = !knowledgeSearchExpanded.value
  if (!knowledgeSearchExpanded.value) {
    knowledgeSearchResults.value = []
    knowledgeSearchKeyword.value = ''
    knowledgeSearchMeta.value = null
    knowledgeSearchScope.value = ''
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
  if (knowledgeSearchTimer) clearTimeout(knowledgeSearchTimer)
  aiPollTimers.forEach((timer) => clearInterval(timer))
  aiPollTimers.clear()
  knowledgePollTimers.forEach((timer) => clearInterval(timer))
  knowledgePollTimers.clear()
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
                  <!-- 缩略图占位：主题色底 + 白色描线 -->
                  <div
                    class="w-10 h-10 rounded-md flex items-center justify-center shrink-0"
                    :style="{ background: 'var(--zh-gradient-blue)' }"
                  >
                    <el-icon style="color: #ffffff; font-size: 20px;">
                      <component :is="getFileIcon(row.format)" />
                    </el-icon>
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
                      :class="{ 'animate-pulse': row.status === 'indexing' }"
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
            <el-table-column label="操作" width="240" align="center" fixed="right">
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
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="handleRenameResource(row)"
                  >
                    <el-icon class="mr-0.5"><Edit /></el-icon>
                    重命名
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
                <template v-if="resourceFilters.type || resourceFilters.status !== ''">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    没有符合条件的资源，请调整筛选条件
                  </span>
                  <el-button
                    type="primary" link size="small" class="mt-2"
                    @click="resourceFilters.type = ''; resourceFilters.status = ''; handleResourceFilterChange();"
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
      <!-- 4.1 知识库概览统计卡片（数据源：GET ai-index/overview，PG 真实统计） -->
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
        <el-card
          shadow="never"
          class="kpi-card"
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
              <el-icon :size="24" :style="{ color: 'var(--zh-text-caption)' }"><FolderOpened /></el-icon>
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ totalKnowledgeEntries.toLocaleString() }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: postgresAvailable ? 'var(--zh-text-disabled)' : 'var(--zh-red)' }">
              向量维度 {{ embeddingDimensions }} · {{ postgresAvailable ? 'PostgreSQL 已连接' : 'PostgreSQL 不可用（降级索引）' }}
            </span>
          </template>
        </el-card>

        <el-card
          shadow="never"
          class="kpi-card"
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
              <el-icon :size="24" :style="{ color: 'var(--zh-green)' }"><CircleCheckFilled /></el-icon>
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
          class="kpi-card"
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
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">解析失败</span>
              <el-icon :size="24" :style="{ color: pendingVectorCount > 0 ? 'var(--zh-orange)' : 'var(--zh-text-caption)' }"><WarningFilled /></el-icon>
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: pendingVectorCount > 0 ? 'var(--zh-orange)' : 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ pendingVectorCount }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)' }">
              {{ pendingVectorCount > 0 ? '存在解析失败的资源，可在列表中重试' : '无失败资源' }}
            </span>
          </template>
        </el-card>

        <el-card
          shadow="never"
          class="kpi-card"
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
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">索引分块总数</span>
              <el-icon :size="24" :style="{ color: 'var(--zh-text-caption)' }"><Files /></el-icon>
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size30)', fontWeight: 700, color: 'var(--zh-text-primary)', lineHeight: 1.2 }">
                {{ totalChunkCount.toLocaleString() }}
              </span>
            </div>
            <span :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)' }">
              累计知识检索 {{ retrievalLogCount.toLocaleString() }} 次
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
          placeholder="全部来源"
          clearable
          size="default"
          style="width: 130px;"
          @change="handleKnowledgeFilterChange"
        >
          <el-option
            v-for="opt in KNOWLEDGE_SOURCE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-input
          v-model="knowledgeFilters.keyword"
          placeholder="搜索资源名称 / ID..."
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
                    class="w-10 h-10 rounded-md flex items-center justify-center shrink-0"
                    :style="{ background: 'var(--zh-gradient-blue)' }"
                  >
                    <el-icon style="color: #ffffff; font-size: 20px;">
                      <component :is="getKnowledgeFileIcon(row.resourceFormat)" />
                    </el-icon>
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

            <!-- 列：来源域（public=公共资源 adm_resource / personal=个人素材 res_material） -->
            <el-table-column prop="sourceType" label="来源" width="100" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="KNOWLEDGE_SOURCE_TAG_MAP[row.sourceType] || 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ KNOWLEDGE_SOURCE_LABEL_MAP[row.sourceType] || row.sourceType }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：分块数（真实 chunk 行数） -->
            <el-table-column prop="entryCount" label="分块数" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
                  {{ row.entryCount.toLocaleString() }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：状态（indexing 为 MySQL 合成状态；失败时 tooltip 展示真实 error_message） -->
            <el-table-column prop="status" label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tooltip
                  :content="row.failReason"
                  placement="top"
                  effect="dark"
                  :disabled="!row.failReason"
                >
                  <el-tag
                    :type="getVectorStatusTagType(row.status)"
                    size="small"
                    effect="plain"
                  >
                    <span class="flex items-center gap-1.5">
                      <span
                        class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                        :class="{ 'animate-pulse': row.status === 'indexing' }"
                        :style="{ background: getVectorStatusDotColor(row.status) }"
                      ></span>
                      {{ VECTOR_STATUS_LABEL_MAP[row.status] || row.status }}
                    </span>
                  </el-tag>
                </el-tooltip>
              </template>
            </el-table-column>

            <!-- 列：索引时间（真实 indexed_at） -->
            <el-table-column prop="indexedAt" label="索引时间" width="160" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', fontFamily: 'var(--zh-font-number)' }">
                  {{ row.indexedAt }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：更新时间（真实 updated_at，元数据变更/重建均会刷新） -->
            <el-table-column prop="updatedAt" label="更新时间" width="160" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', fontFamily: 'var(--zh-font-number)' }">
                  {{ row.updatedAt }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：操作（completed→重解析 failed→重试 全状态→分块明细 public→详情） -->
            <el-table-column label="操作" width="180" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <!-- 已完成：重新解析 -->
                  <template v-if="row.status === 'completed'">
                    <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleKnowledgeReparse(row)">
                      <el-icon class="mr-0.5"><Refresh /></el-icon>
                      重解析
                    </el-button>
                  </template>
                  <!-- 失败：重试 -->
                  <template v-if="row.status === 'failed'">
                    <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleKnowledgeReparse(row)">
                      <el-icon class="mr-0.5"><Refresh /></el-icon>
                      重试
                    </el-button>
                  </template>
                  <!-- 分块明细（全状态可用，展示 PG 真实分块） -->
                  <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="openChunkDrawer(row)">
                    分块
                  </el-button>
                  <!-- 公共资源可跳 Tab 1 资源详情抽屉 -->
                  <el-button
                    v-if="row.sourceType === 'public'"
                    type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openDetailDrawer({ id: row.resourceId, name: row.resourceName, type: row.resourceFormat })"
                  >
                    详情
                  </el-button>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据占位 -->
            <template #empty>
              <el-empty description="暂无知识索引记录" :image-size="80">
                <template v-if="knowledgeFilters.status || knowledgeFilters.type || knowledgeFilters.keyword">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                    没有符合条件的记录，请调整筛选条件
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
                    知识索引将在资源解析完成后生成；已启用但尚未索引的资源可通过「全部重新索引」纳入
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
              <el-select
                v-model="knowledgeSearchScope"
                placeholder="全部来源"
                clearable
                size="default"
                style="width: 130px;"
              >
                <el-option
                  v-for="opt in KNOWLEDGE_SOURCE_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <el-input
                v-model="knowledgeSearchKeyword"
                placeholder="输入关键词进行向量语义检索..."
                clearable
                size="default"
                :prefix-icon="Search"
                style="flex: 1; max-width: 480px;"
                @keyup.enter="handleKnowledgeSearch"
                @clear="knowledgeSearchResults = []; knowledgeSearchMeta = null"
              />
              <el-button type="primary" :loading="isKnowledgeSearching" @click="handleKnowledgeSearch">
                搜索
              </el-button>
            </div>

            <!-- 搜索结果（真实 pgvector 混合重排检索，score → 匹配度） -->
            <template v-if="knowledgeSearchResults.length > 0">
              <div
                class="rounded-lg p-4"
                :style="{ border: '1px solid ' + 'var(--zh-line-border)', background: 'var(--zh-background-light-gray)' }"
              >
                <p :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)', marginBottom: '12px' }">
                  检索结果（{{ knowledgeSearchResults.length }} 条）
                  <template v-if="knowledgeSearchMeta">
                    · 模式 {{ knowledgeSearchMeta.mode }} · 耗时 {{ knowledgeSearchMeta.latency }}ms
                  </template>
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
                    来源：{{ item.source }} · 匹配度 {{ item.matchRate }}% · 第 {{ item.rank }} 位
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

      <!-- 4.5 分块明细抽屉（真实 PG chunks） -->
      <el-drawer
        v-model="chunkDrawerVisible"
        title="索引分块明细"
        size="560px"
        :style="{ '--el-drawer-bg-color': 'var(--zh-background-pop)' }"
      >
        <div v-if="currentChunkRow" class="flex flex-col gap-2 mb-4 pb-4 border-b" :style="{ borderColor: 'var(--zh-line-parting)' }">
          <div class="flex items-center gap-2">
            <span
              class="block truncate flex-1"
              :style="{ fontSize: 'var(--zh-font-size15)', fontWeight: 600, color: 'var(--zh-text-primary)' }"
            >
              {{ currentChunkRow.resourceName }}
            </span>
            <el-tag :type="KNOWLEDGE_SOURCE_TAG_MAP[currentChunkRow.sourceType] || 'info'" size="small" effect="plain">
              {{ KNOWLEDGE_SOURCE_LABEL_MAP[currentChunkRow.sourceType] || currentChunkRow.sourceType }}
            </el-tag>
          </div>
          <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', fontFamily: 'var(--zh-font-number)' }">
            resource_key：{{ currentChunkRow.resourceKey }} · 共 {{ currentChunkRow.entryCount.toLocaleString() }} 个分块
            <template v-if="chunkList.length">（展示前 {{ chunkList.length }} 块）</template>
          </span>
        </div>

        <div v-loading="chunkDrawerLoading" element-loading-text="加载分块中...">
          <div v-if="!chunkDrawerLoading && chunkList.length === 0">
            <el-empty description="该资源暂无分块数据（解析未完成或未生成向量）" :image-size="80" />
          </div>
          <div
            v-for="chunk in chunkList"
            :key="chunk.chunk_id"
            class="rounded-lg p-3 mb-3"
            :style="{ border: '1px solid var(--zh-line-border)', background: 'var(--zh-background-light-gray)' }"
          >
            <div class="flex items-center gap-2 mb-2">
              <span
                class="inline-flex items-center justify-center rounded px-1.5 py-0.5"
                :style="{ background: 'var(--zh-background-option)', fontSize: 'var(--zh-font-size11)', fontFamily: 'var(--zh-font-number)', color: 'var(--zh-text-secondary)' }"
              >
                #{{ chunk.chunk_index }}
              </span>
              <span
                class="truncate"
                :style="{ fontSize: 'var(--zh-font-size11)', color: 'var(--zh-text-disabled)', fontFamily: 'var(--zh-font-number)' }"
              >
                {{ chunk.chunk_id }}
              </span>
            </div>
            <p
              class="whitespace-pre-wrap break-words"
              :style="{ fontSize: 'var(--zh-font-size13)', lineHeight: 1.7, color: 'var(--zh-text-secondary)', margin: 0 }"
            >
              {{ chunk.content }}
            </p>
          </div>
        </div>
      </el-drawer>
    </template>

    <!-- ===================================================================
         5. 批量上传对话框
         =================================================================== -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传公共资源"
      width="640px"
      destroy-on-close
      :close-on-click-modal="!isUploading"
      :close-on-press-escape="!isUploading"
      :show-close="!isUploading"
      :style="{
        '--el-dialog-bg-color': 'var(--zh-background-pop)',
        '--el-dialog-border-radius': 'var(--zh-radius16)',
      }"
    >
      <!-- 拖拽上传区（复用 FileDropUpload：多文件 / ≤500MB / 单次 20 个） -->
      <FileDropUpload
        multiple
        :accept="UPLOAD_INPUT_ACCEPT"
        :accept-exts="SUPPORTED_UPLOAD_EXT_LIST"
        :mime-prefixes="SUPPORTED_UPLOAD_MIME_PREFIXES"
        :max-size-bytes="MAX_UPLOAD_FILE_SIZE"
        :max-count="MAX_UPLOAD_FILES"
        :existing-keys="uploadExistingKeys"
        :disabled="isUploading"
        @accept="onUploadFilesAccepted"
      >
        <template #default="{ dragOver }">
          <div
            class="upload-dropzone flex flex-col items-center justify-center gap-3 transition-all duration-200"
            :class="{ 'is-dragover': dragOver, 'is-uploading': isUploading }"
            :style="{
              border: '2px dashed var(--zh-line-heavier)',
              borderRadius: 'var(--zh-radius12)',
              background: 'var(--zh-background-light-gray)',
              minHeight: '160px',
            }"
          >
            <el-icon :size="48" :style="{ color: 'var(--zh-text-caption)' }">
              <Loading v-if="isUploading" class="is-loading" />
              <Upload v-else />
            </el-icon>
            <p :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-caption)' }">
              {{ isUploading ? '文件正在上传，请稍候...' : '将文件拖拽到此处，或' }}
              <span
                v-if="!isUploading"
                :style="{ color: 'var(--zh-text-link)', textDecoration: 'underline' }"
              >点击上传</span>
            </p>
            <p :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
              支持 PDF / Word / PPT / 图片 / 音视频，单文件最大 500MB，单次最多 20 个文件
            </p>
          </div>
        </template>
      </FileDropUpload>

      <!-- 整体上传进度 -->
      <div v-if="uploadFileList.length > 0" class="upload-overall-progress mt-4">
        <div class="flex items-center justify-between mb-1.5">
          <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
            上传进度 · {{ completedUploadCount }}/{{ uploadFileList.length }} 个文件
          </span>
          <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-theme)', fontFamily: 'var(--zh-font-number)' }">
            {{ uploadOverallProgress }}%
          </span>
        </div>
        <el-progress
          :percentage="uploadOverallProgress"
          :stroke-width="6"
          :show-text="false"
          :status="uploadAllComplete ? 'success' : undefined"
        />
      </div>

      <!-- 已选文件列表 -->
      <div v-if="uploadFileList.length > 0" class="mt-4">
        <p :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 500, color: 'var(--zh-text-primary)', marginBottom: '8px' }">
          文件队列（{{ uploadFileList.length }} 个）：
        </p>
        <div
          class="rounded-lg overflow-hidden"
          :style="{ border: '1px solid var(--zh-line-border)' }"
        >
          <div
            v-for="file in uploadFileList"
            :key="file.uid"
            class="upload-file-row flex items-center gap-3 px-4 py-2.5 border-b last:border-0"
            :style="{ borderColor: 'var(--zh-line-parting)' }"
          >
            <el-icon style="font-size: 18px; color: var(--zh-text-theme);"><component :is="getFileIcon(file.format)" /></el-icon>
            <div class="upload-file-main min-w-0 flex-1">
              <div class="flex items-center gap-1.5 min-w-0">
                <template v-if="renamingUploadUid === file.uid">
                  <el-input
                    v-model="uploadRenameDraft"
                    size="small"
                    maxlength="160"
                    show-word-limit
                    autofocus
                    @keyup.enter="commitUploadRename(file)"
                    @keyup.esc="cancelUploadRename"
                    @blur="commitUploadRename(file)"
                  />
                </template>
                <template v-else>
                  <span
                    class="truncate"
                    :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)' }"
                    :title="file.name"
                  >
                    {{ file.name }}
                  </span>
                  <el-button
                    text
                    size="small"
                    :icon="Edit"
                    :disabled="isUploading"
                    aria-label="重命名文件"
                    @click.stop="beginUploadRename(file)"
                  />
                </template>
              </div>
              <el-progress
                v-if="file.status === 'uploading' || file.status === 'success'"
                class="upload-file-progress"
                :percentage="file.progress"
                :stroke-width="4"
                :show-text="false"
                :status="file.status === 'success' ? 'success' : undefined"
              />
            </div>
            <span class="upload-file-size" :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }">
              {{ formatFileSize(file.size || 0) }}
            </span>
            <span
              class="upload-file-status"
              :class="{
                'is-success': file.status === 'success',
                'is-uploading': file.status === 'uploading',
              }"
            >
              {{ file.status === 'success' ? '已上传' : file.status === 'uploading' ? `${file.progress}%` : '待上传' }}
            </span>
            <el-button
              :icon="Delete"
              circle
              size="small"
              :disabled="isUploading"
              :style="{ color: 'var(--zh-text-caption)' }"
              aria-label="移除文件"
              @click="removeUploadFile(file.uid)"
            />
          </div>
        </div>
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
          <el-button :disabled="isUploading" @click="uploadDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="isUploading"
            :disabled="uploadFileList.length === 0"
            @click="handleUpload"
          >
            {{
              isUploading
                ? '上传中...'
                : uploadAllComplete
                  ? '完成'
                  : `开始上传 (${pendingUploadFiles.length})`
            }}
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
            <el-icon style="font-size: 48px; color: var(--zh-text-theme);"><component :is="getFileIcon(currentResource.format)" /></el-icon>
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

            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">描述</span>
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
              {{ currentResource.description || '—' }}
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
              :class="{ 'animate-pulse': currentResource.status === 'indexing' }"
              :style="{ background: getResourceStatusDotColor(currentResource.status) }"
            ></span>
            <span :style="{ fontSize: 'var(--zh-font-size14)', fontWeight: 500, color: 'var(--zh-text-primary)' }">
              {{ RESOURCE_STATUS_LABEL_MAP[currentResource.status] || currentResource.status }}
            </span>
          </div>
          <el-progress
            :percentage="currentResource.vectorProgress || 0"
            :status="getProgressStatus(currentResource.status)"
            :stroke-width="8"
            :striped="currentResource.status === 'indexing'"
            :striped-flow="currentResource.status === 'indexing'"
          />
          <!-- 失败原因提示 -->
          <div
            v-if="currentResource.status === 'failed' && currentResource.failReason"
            class="flex items-start gap-2 mt-2 p-2 rounded"
            :style="{ background: 'var(--zh-yellow-light)', borderLeft: '3px solid var(--zh-orange)' }"
          >
            <el-icon :size="14" :style="{ color: 'var(--zh-orange)', marginTop: '1px', flexShrink: 0 }"><WarningFilled /></el-icon>
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
              @click="handleRenameResource(currentResource)"
            >
              重命名
            </el-button>
            <el-button
              :icon="Download"
              :style="{ borderRadius: 'var(--zh-radius8)' }"
              @click="handleDownloadResource(currentResource)"
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
.upload-dropzone {
  cursor: pointer;
}
.upload-dropzone.is-dragover {
  border-color: var(--zh-text-theme) !important;
  background: var(--zh-background-option-on) !important;
  box-shadow: inset 0 0 0 1px var(--zh-text-theme);
}
.upload-dropzone.is-uploading {
  cursor: wait;
  opacity: 0.82;
}
.upload-overall-progress :deep(.el-progress-bar__outer),
.upload-file-progress :deep(.el-progress-bar__outer) {
  background: var(--zh-background-option);
}
.upload-file-row {
  min-height: 58px;
}
.upload-file-main {
  min-width: 0;
}
.upload-file-main :deep(.el-input) {
  min-width: 0;
}
.upload-file-progress {
  margin-top: 5px;
}
.upload-file-size {
  flex: 0 0 62px;
  text-align: right;
}
.upload-file-status {
  flex: 0 0 48px;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
  text-align: right;
}
.upload-file-status.is-uploading {
  color: var(--zh-text-theme);
  font-family: var(--zh-font-number);
}
.upload-file-status.is-success {
  color: var(--zh-green);
}
.upload-dropzone :deep(.is-loading) {
  animation: rotating 1.6s linear infinite;
}

@keyframes rotating {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
