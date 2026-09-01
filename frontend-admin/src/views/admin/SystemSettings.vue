<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDialog, ElEmpty, ElMessageBox, ElMessage, ElTooltip, ElRadioGroup, ElRadioButton,
      ElSlider, ElInputNumber, ElSwitch, ElDatePicker, ElAlert, ElUpload
    - ElementPlus Icons: Search, Refresh, Setting, Download, Upload, Delete, View,
      MagicStick, Cpu, Edit, ArrowDown, Top, CopyDocument, InfoFilled
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount`, `watch` from Vue
  - 依赖:
    - `../apis/export`: 导入 `getExportTemplates`（API-98，分页查询导出模板）
  - 输入: 无 props，导出模板数据来自 API-98，系统日志数据为组件内部 mock
  - 输出: 渲染系统配置视图（Tab 切换 + AI参数表单 + 导出模板表格 + 系统日志表格 + 上传对话框 + 日志详情对话框）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
  - 对应需求文档: §4.7.3.3 — 系统配置与数据看板
-->

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import {
  Search,
  Refresh,
  Setting,
  Download,
  Upload,
  Delete,
  View,
  MagicStick,
  Cpu,
  Edit,
  ArrowDown,
  Top,
  CopyDocument,
  InfoFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getExportTemplates } from '@/apis/export'

// ===================================================================
// 配置常量 — Tab 定义
// ===================================================================

/** 页面 Tab 定义 */
const PAGE_TABS = [
  { key: 'ai', label: 'AI 参数配置' },
  { key: 'templates', label: '导出模板管理' },
  { key: 'logs', label: '系统日志' },
]

// ===================================================================
// 配置常量 — Tab 1：AI 参数配置
// ===================================================================

/** 默认模型选项 */
const MODEL_OPTIONS = [
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'Claude 5 Sonnet', value: 'claude-sonnet-5' },
  { label: 'DeepSeek-V3', value: 'deepseek-v3' },
  { label: 'Qwen-Max', value: 'qwen-max' },
]

/** AI 参数默认值 — 用于单字段恢复和整体重置 */
const AI_DEFAULTS = {
  defaultModel: 'gpt-4o',
  temperature: 0.7,
  topP: 0.9,
  maxTokens: 4096,
  frequencyPenalty: 0.0,
  presencePenalty: 0.0,
  repetitionPenalty: 1.0,
  maxWords: 2000,
  systemPrompt:
    '你是一个专业的教育AI助手，名为"智核"。你的任务是帮助一线教师完成备课、课件制作、教案编写和教学反思。请始终以教育专业视角回应，引用权威教材和课程标准，确保内容准确、科学、适合目标学段。在不确定时，应主动标注"此内容需教师进一步核实"。',
}

// ===================================================================
// 配置常量 — Tab 2：导出模板管理
// ===================================================================

/** 模板类型筛选项 */
const TEMPLATE_TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: 'PPTX 课件', value: 'pptx' },
  { label: 'Word 教案', value: 'docx' },
]

/** 模板类型 → 显示标签映射 */
const TEMPLATE_TYPE_LABEL_MAP = { pptx: 'PPTX 课件', docx: 'Word 教案' }

/** 模板类型 → Tag 颜色映射 */
const TEMPLATE_TYPE_TAG_MAP = { pptx: '', docx: 'info' }

/** 模板状态筛选项 */
const TEMPLATE_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '启用', value: 'enabled' },
  { label: '禁用', value: 'disabled' },
]

// ===================================================================
// 配置常量 — Tab 3：系统日志
// ===================================================================

/** 日志级别筛选项 */
const LOG_LEVEL_OPTIONS = [
  { label: '全部级别', value: '' },
  { label: 'ERROR', value: 'error' },
  { label: 'WARN', value: 'warn' },
  { label: 'INFO', value: 'info' },
  { label: 'DEBUG', value: 'debug' },
]

/** 日志级别 → 显示标签映射 */
const LOG_LEVEL_LABEL_MAP = {
  error: 'ERROR', warn: 'WARN', info: 'INFO', debug: 'DEBUG',
}

/** 日志级别 → Tag 类型映射 */
const LOG_LEVEL_TAG_TYPE_MAP = {
  error: 'danger', warn: 'warning', info: '', debug: 'info',
}

/** 日志级别 → 圆点颜色映射 */
const LOG_LEVEL_DOT_COLOR_MAP = {
  error: 'var(--zh-red)',
  warn: 'var(--zh-orange)',
  info: 'var(--zh-cyan)',
  debug: 'var(--zh-text-disabled)',
}

/** 日志模块筛选项 */
const LOG_MODULE_OPTIONS = [
  { label: '全部模块', value: '' },
  { label: 'AI 引擎', value: 'ai-engine' },
  { label: '知识库', value: 'knowledge-base' },
  { label: '导出服务', value: 'export-service' },
  { label: '存储服务', value: 'storage' },
  { label: '用户系统', value: 'user-system' },
  { label: '社区模块', value: 'community' },
  { label: '系统', value: 'system' },
]

/** 日志模块 → 显示标签映射 */
const LOG_MODULE_LABEL_MAP = {
  'ai-engine': 'AI 引擎',
  'knowledge-base': '知识库',
  'export-service': '导出服务',
  storage: '存储服务',
  'user-system': '用户系统',
  community: '社区模块',
  system: '系统',
}

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

/** 日志自动刷新间隔（毫秒） */
const LOG_AUTO_REFRESH_INTERVAL = 10000

// ===================================================================
// 响应式状态 — 通用
// ===================================================================

/** 数据加载状态 */
const isLoading = ref(true)

/** 表格数据加载中 */
const isTableLoading = ref(false)

/** 当前激活的 Tab */
const activeTab = ref('ai')

// ===================================================================
// 响应式状态 — Tab 1：AI 参数配置
// ===================================================================

/** AI 参数表单数据 */
const aiConfig = reactive({ ...AI_DEFAULTS })

/** 参数是否有未保存的修改 */
const isAiDirty = ref(false)

/** AI 配置保存中 */
const isAiSaving = ref(false)

// ===================================================================
// 响应式状态 — Tab 2：导出模板管理
// ===================================================================

/** 模板列表数据 */
const templateList = ref([])

/** 模板筛选条件 */
const templateFilters = reactive({ type: '', status: '', keyword: '' })

/** 模板分页参数 */
const templatePagination = reactive({ currentPage: 1, pageSize: 20, total: 0 })

/** 上传模板对话框可见性 */
const templateUploadVisible = ref(false)

/** 上传模板表单 */
const templateUploadForm = reactive({ name: '', type: 'pptx', version: '', description: '' })

/** 上传中 */
const isTemplateUploading = ref(false)

/** 当前上传模式：create | replace */
const uploadMode = ref('create')

/** 替换目标模板 ID */
const replaceTargetId = ref(null)

// ===================================================================
// 响应式状态 — Tab 3：系统日志
// ===================================================================

/** 日志列表数据 */
const logList = ref([])

/** 日志筛选条件 */
const logFilters = reactive({ timeRange: null, level: '', module: '', keyword: '' })

/** 日志分页参数 */
const logPagination = reactive({ currentPage: 1, pageSize: 20, total: 0 })

/** 自动刷新开关 */
const autoRefreshEnabled = ref(false)

/** 自动刷新定时器 ID */
let autoRefreshTimer = null

/** 日志详情对话框可见性 */
const logDetailVisible = ref(false)

/** 当前查看的日志条目 */
const currentLog = ref(null)

/** 日志详情中堆栈跟踪展开状态 */
const stackTraceExpanded = ref(false)

/** 日志详情中上下文数据展开状态 */
const contextDataExpanded = ref(false)

// ===================================================================
// 监测 AI 参数变更 — 标记 dirty 状态
// ===================================================================

watch(
  () => ({ ...aiConfig }),
  () => { isAiDirty.value = true },
  { deep: true },
)

// ===================================================================
// Mock 数据生成 — Tab 3：系统日志
// ===================================================================

/**
 * 生成模拟系统日志数据
 * @returns {Array} 日志对象数组
 */
const generateMockLogs = () => {
  const levels = ['error', 'warn', 'info', 'debug']
  const modules = ['ai-engine', 'knowledge-base', 'export-service', 'storage', 'user-system', 'community', 'system']
  const operators = ['admin', 'system', 'scheduler', 'admin', 'scanner']

  const errorMsgs = [
    '上传失败：Connection timeout after 30000ms to bucket "zh-templates"',
    '向量化引擎异常：第128页编码无法识别，请检查文件完整性',
    'AI 模型调用超时：GPT-4o API 响应超过 60s，已自动降级',
    '存储空间不足：磁盘使用率 92%，无法写入新文件',
    '数据库连接池耗尽：Active=50, Idle=0, Waiting=12',
  ]
  const warnMsgs = [
    '导出任务队列积压：当前排队 47 项，最长等待 28 分钟',
    'Token 用量接近限制：本月已用 85%（425万/500万）',
    '知识库索引重建耗时过长：预计剩余 15 分钟',
    'API 响应延迟升高：P99 = 8.2s（正常 < 3s）',
    '用户并发数超过阈值：当前 1280 人（阈值 1000）',
  ]
  const infoMsgs = [
    '模板生成成功：用户 admin 导出了「勾股定理」课件',
    '知识库向量化完成：「2026 版数学教材」入库 2.3 万条',
    '新模板上传成功：「互动课件模板 - 科技感」v1.0',
    '用户登录成功：张老师 (T0042) 来自 192.168.1.100',
    'AI 参数配置已更新：temperature 0.7 → 0.8',
    '社区内容审核通过：「勾股定理互动教学案例」(R0001)',
    '系统定时任务完成：日志清理 1,280 条过期记录',
    '资源解析完成：「细胞分裂动画.mp4」生成 1,200 条知识条目',
  ]
  const debugMsgs = [
    'RAG 检索请求：query="勾股定理证明方法", topK=10',
    '向量匹配耗时：12ms, 候选集=1,280',
    '知识条目写入：batch=500, latency=45ms',
    '缓存命中率：92.3% (12,400/13,430)',
    'WebSocket 心跳检测：所有连接正常',
  ]

  const logs = []
  for (let i = 0; i < 50; i++) {
    const level = levels[i % 4]
    const module = modules[i % 7]
    let message = ''
    if (level === 'error') message = errorMsgs[i % errorMsgs.length]
    else if (level === 'warn') message = warnMsgs[i % warnMsgs.length]
    else if (level === 'info') message = infoMsgs[i % infoMsgs.length]
    else message = debugMsgs[i % debugMsgs.length]

    const minutesAgo = i * 7 + Math.floor(Math.random() * 5)
    const logDate = new Date(Date.now() - minutesAgo * 60000)
    const ts = logDate.toISOString().replace('T', ' ').slice(0, 19) + '.' + String(Math.floor(Math.random() * 1000)).padStart(3, '0')

    logs.push({
      id: `LOG${String(i + 1).padStart(5, '0')}`,
      timestamp: ts,
      level,
      module,
      moduleLabel: LOG_MODULE_LABEL_MAP[module] || module,
      message,
      operator: operators[i % 5],
      requestId: `req_${Math.random().toString(36).slice(2, 10)}`,
      ip: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
      stackTrace:
        level === 'error'
          ? `at ObjectStorageService.upload (src/services/storage.ts:142:15)
at TemplateController.handleUpload (src/controllers/template.ts:88:22)
at async middleware (src/middleware/auth.ts:34:5)`
          : '',
      contextData:
        level === 'error'
          ? JSON.stringify({ bucket: 'zh-templates', fileName: '2026版数学教材（必修三）.pdf', fileSize: '128MB', retryCount: 3, timeoutMs: 30000 }, null, 2)
          : '',
    })
  }
  return logs
}

/** 全部日志数据（模拟数据库） */
let allLogs = []

// ===================================================================
// 数据适配
// ===================================================================

/**
 * 将 ISO 时间字符串格式化为 "YYYY-MM-DD HH:mm"
 * @param {string|undefined} value - 后端返回的时间（ISO 格式）
 * @returns {string} 格式化后的时间文本
 */
const formatTemplateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/**
 * 将后端模板 VO 归一化为表格所需结构
 * 兼容 export_type/type、published/unpublished ↔ enabled/disabled 等字段差异
 * @param {Object} t - 后端返回的模板对象
 * @returns {Object} 归一化后的模板对象
 */
const normalizeTemplate = (t) => ({
  id: t.id,
  name: t.name,
  type: t.export_type === 'word' ? 'docx' : t.export_type,
  version: `v${t.version}`,
  size: t.size || '—',
  isDefault: !!t.is_default,
  status: t.status === 'published' ? 'enabled' : 'disabled',
  updatedAt: formatTemplateTime(t.updated_at),
  uploader: t.uploader || '管理员',
  downloadCount: t.download_count || 0,
})

// ===================================================================
// 数据筛选与获取方法
// ===================================================================

/**
 * 获取模板列表数据（API-98）
 * 将前端筛选条件映射为后端查询参数，请求成功后归一化列表并记录总数
 */
const fetchTemplates = async () => {
  isTableLoading.value = true
  try {
    // 组装查询参数：只传有效的筛选条件
    const params = { page: templatePagination.currentPage, size: templatePagination.pageSize }
    if (templateFilters.type) params.export_type = templateFilters.type === 'docx' ? 'word' : templateFilters.type
    if (templateFilters.status) params.status = templateFilters.status === 'enabled' ? 'published' : 'unpublished'
    if (templateFilters.keyword.trim()) params.keyword = templateFilters.keyword.trim()

    const res = await getExportTemplates(params)
    const data = res?.data
    const rows = data?.records || data?.list || data?.items || []
    templateList.value = rows.map(normalizeTemplate)
    templatePagination.total = Number(data?.total ?? rows.length)
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 获取日志列表数据（模拟异步请求）
 */
const fetchLogs = () => {
  isTableLoading.value = true
  setTimeout(() => {
    let filtered = [...allLogs]
    if (logFilters.level) filtered = filtered.filter((l) => l.level === logFilters.level)
    if (logFilters.module) filtered = filtered.filter((l) => l.module === logFilters.module)
    if (logFilters.keyword.trim()) {
      const kw = logFilters.keyword.trim().toLowerCase()
      filtered = filtered.filter((l) => l.message.toLowerCase().includes(kw))
    }
    filtered.sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    logPagination.total = filtered.length
    const start = (logPagination.currentPage - 1) * logPagination.pageSize
    logList.value = filtered.slice(start, start + logPagination.pageSize)
    isTableLoading.value = false
  }, 300)
}

/**
 * 获取当前 Tab 对应的数据
 */
const fetchData = () => {
  if (activeTab.value === 'templates') fetchTemplates()
  else if (activeTab.value === 'logs') fetchLogs()
}

/**
 * 页面首次数据加载
 */
const loadData = () => {
  isLoading.value = true
  setTimeout(() => {
    allLogs = generateMockLogs()
    isLoading.value = false
    fetchData()
  }, 600)
}

// ===================================================================
// 交互事件处理方法 — 通用
// ===================================================================

/**
 * Tab 切换处理 — 重置筛选条件和分页，离开日志 Tab 时关闭自动刷新
 * @param {string} tab - 目标 Tab key
 */
const handleTabChange = (tab) => {
  templateFilters.type = ''
  templateFilters.status = ''
  templateFilters.keyword = ''
  logFilters.level = ''
  logFilters.module = ''
  logFilters.keyword = ''
  templatePagination.currentPage = 1
  logPagination.currentPage = 1
  if (activeTab.value === 'logs' && tab !== 'logs') stopAutoRefresh()
  activeTab.value = tab
  fetchData()
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发
 */
const handleRefresh = () => {
  loadData()
}

// ===================================================================
// 交互事件处理方法 — Tab 1：AI 参数配置
// ===================================================================

/**
 * 保存 AI 参数配置 — 二次确认后模拟保存
 */
const handleAiSave = () => {
  ElMessageBox.confirm(
    '确认保存当前 AI 参数配置？修改将立即生效，影响所有教师的 AI 生成结果。',
    '保存配置',
    { confirmButtonText: '确认保存', cancelButtonText: '取消', type: 'info' },
  )
    .then(() => {
      isAiSaving.value = true
      setTimeout(() => {
        isAiSaving.value = false
        isAiDirty.value = false
        ElMessage.success('AI 参数配置已保存并生效')
      }, 800)
    })
    .catch(() => {})
}

/**
 * 恢复全部 AI 参数为默认值 — 二次确认后重置
 */
const handleAiReset = () => {
  ElMessageBox.confirm(
    '恢复默认设置将覆盖当前所有配置，是否继续？',
    '恢复默认',
    { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'warning' },
  )
    .then(() => {
      Object.assign(aiConfig, AI_DEFAULTS)
      isAiDirty.value = false
      ElMessage.success('已恢复为默认设置并自动保存')
    })
    .catch(() => {})
}

/**
 * 单个字段恢复默认值
 * @param {string} field - 字段名
 */
const resetSingleField = (field) => {
  if (AI_DEFAULTS[field] !== undefined) {
    aiConfig[field] = AI_DEFAULTS[field]
    ElMessage.success(`已恢复为默认值`)
  }
}

// ===================================================================
// 交互事件处理方法 — Tab 2：导出模板管理
// ===================================================================

/**
 * 模板筛选条件变更 — 重置分页并重新获取数据
 */
const handleTemplateFilterChange = () => {
  templatePagination.currentPage = 1
  fetchTemplates()
}

/** 模板搜索防抖定时器 */
let templateSearchTimer = null

/**
 * 模板搜索输入防抖处理
 */
const handleTemplateSearchInput = () => {
  clearTimeout(templateSearchTimer)
  templateSearchTimer = setTimeout(() => handleTemplateFilterChange(), 300)
}

/**
 * 模板搜索回车处理
 */
const handleTemplateSearchEnter = () => {
  clearTimeout(templateSearchTimer)
  handleTemplateFilterChange()
}

/**
 * 模板分页页码变更
 * @param {number} page - 目标页码
 */
const handleTemplatePageChange = (page) => {
  templatePagination.currentPage = page
  fetchTemplates()
}

/**
 * 模板分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleTemplateSizeChange = (size) => {
  templatePagination.pageSize = size
  templatePagination.currentPage = 1
  fetchTemplates()
}

/**
 * 模板启用/禁用切换
 * @param {Object} row - 模板行数据
 */
const handleTemplateStatusToggle = (row) => {
  if (row.isDefault) {
    ElMessage.warning('默认模板不可禁用，请先设置其他模板为默认')
    return
  }
  const newStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  ElMessage.success(`模板「${row.name}」已${newStatus === 'enabled' ? '启用' : '禁用'}`)
  fetchTemplates()
}

/**
 * 设为默认模板 — 同类型旧默认模板自动取消
 * @param {Object} row - 模板行数据
 */
const handleSetDefault = (row) => {
  if (row.isDefault) return
  ElMessageBox.confirm(
    `将「${row.name}」设为默认${TEMPLATE_TYPE_LABEL_MAP[row.type]}？原默认模板将被替换。`,
    '设为默认',
    { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' },
  )
    .then(() => {
      ElMessage.success(`已将「${row.name}」设为默认模板`)
      fetchTemplates()
    })
    .catch(() => {})
}

/**
 * 下载模板
 * @param {Object} row - 模板行数据
 */
const handleDownloadTemplate = (row) => {
  ElMessage.success(`开始下载「${row.name}」`)
}

/**
 * 打开替换模板对话框 — 预填当前模板信息
 * @param {Object} row - 模板行数据
 */
const openReplaceDialog = (row) => {
  uploadMode.value = 'replace'
  replaceTargetId.value = row.id
  templateUploadForm.name = row.name
  templateUploadForm.type = row.type
  templateUploadForm.version = ''
  templateUploadForm.description = ''
  templateUploadVisible.value = true
}

/**
 * 删除模板 — 二次确认
 * @param {Object} row - 模板行数据
 */
const handleDeleteTemplate = (row) => {
  if (row.isDefault) {
    ElMessage.warning('默认模板不可删除，请先设置其他模板为默认')
    return
  }
  ElMessageBox.confirm(
    `确认删除「${row.name}」？此操作不可撤销。`,
    '确认删除',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning', confirmButtonClass: 'el-button--danger' },
  )
    .then(() => {
      ElMessage.success(`已删除模板「${row.name}」`)
      if (templateList.value.length === 1 && templatePagination.currentPage > 1) templatePagination.currentPage--
      fetchTemplates()
    })
    .catch(() => {})
}

/**
 * 打开上传模板对话框（新建模式）
 */
const openUploadDialog = () => {
  uploadMode.value = 'create'
  replaceTargetId.value = null
  templateUploadForm.name = ''
  templateUploadForm.type = 'pptx'
  templateUploadForm.version = ''
  templateUploadForm.description = ''
  templateUploadVisible.value = true
}

/**
 * 模拟文件选择 — 自动填入模板名称
 * @param {Object} file - 文件对象，含 name 和 size
 */
const handleTemplateFileSelect = (file) => {
  if (!templateUploadForm.name) {
    templateUploadForm.name = file.name.replace(/\.(pptx|docx)$/i, '')
  }
}

/**
 * 执行模板上传/替换 — 含基础校验
 */
const handleTemplateUpload = () => {
  if (!templateUploadForm.name.trim()) { ElMessage.warning('请输入模板名称'); return }
  if (!templateUploadForm.version.trim()) { ElMessage.warning('请输入版本号'); return }

  isTemplateUploading.value = true
  setTimeout(() => {
    if (uploadMode.value === 'create') {
      ElMessage.success(`模板「${templateUploadForm.name}」上传成功`)
    } else {
      ElMessage.success(`模板「${templateUploadForm.name}」已替换为 ${templateUploadForm.version}`)
    }
    isTemplateUploading.value = false
    templateUploadVisible.value = false
    fetchTemplates()
  }, 1500)
}

/**
 * 获取模板类型 emoji 图标
 * @param {string} type - 模板类型
 * @returns {string} emoji 图标字符
 */
const getTemplateIcon = (type) => (type === 'pptx' ? '📙' : '📘')

/**
 * 获取模板类型 Tag 类型
 * @param {string} type - 模板类型
 * @returns {string} ElementPlus Tag type
 */
const getTemplateTagType = (type) => TEMPLATE_TYPE_TAG_MAP[type] || 'primary'

// ===================================================================
// 交互事件处理方法 — Tab 3：系统日志
// ===================================================================

/**
 * 日志筛选条件变更 — 重置分页并重新获取数据
 */
const handleLogFilterChange = () => {
  logPagination.currentPage = 1
  fetchLogs()
}

/** 日志搜索防抖定时器 */
let logSearchTimer = null

/**
 * 日志搜索输入防抖处理
 */
const handleLogSearchInput = () => {
  clearTimeout(logSearchTimer)
  logSearchTimer = setTimeout(() => handleLogFilterChange(), 300)
}

/**
 * 日志搜索回车处理
 */
const handleLogSearchEnter = () => {
  clearTimeout(logSearchTimer)
  handleLogFilterChange()
}

/**
 * 日志分页页码变更
 * @param {number} page - 目标页码
 */
const handleLogPageChange = (page) => {
  logPagination.currentPage = page
  fetchLogs()
}

/**
 * 日志分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleLogSizeChange = (size) => {
  logPagination.pageSize = size
  logPagination.currentPage = 1
  fetchLogs()
}

/**
 * 清除日志筛选条件
 */
const handleClearLogFilters = () => {
  logFilters.level = ''
  logFilters.module = ''
  logFilters.keyword = ''
  logFilters.timeRange = null
  handleLogFilterChange()
}

/**
 * 打开日志详情对话框 — 重置折叠状态
 * @param {Object} row - 日志行数据
 */
const openLogDetail = (row) => {
  currentLog.value = row
  stackTraceExpanded.value = false
  contextDataExpanded.value = false
  logDetailVisible.value = true
}

/**
 * 复制日志全部内容到剪贴板
 */
const handleCopyLog = () => {
  if (!currentLog.value) return
  const text = JSON.stringify(currentLog.value, null, 2)
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('日志详情已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

/**
 * 启动自动刷新定时器
 */
const startAutoRefresh = () => {
  if (autoRefreshTimer) return
  autoRefreshTimer = setInterval(() => fetchLogs(), LOG_AUTO_REFRESH_INTERVAL)
}

/**
 * 停止自动刷新定时器
 */
const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

/**
 * 自动刷新开关切换
 * @param {boolean} val - 开关状态
 */
const handleAutoRefreshToggle = (val) => {
  if (val) startAutoRefresh()
  else stopAutoRefresh()
}

/**
 * 导出日志（模拟）
 */
const handleExportLogs = () => {
  isTableLoading.value = true
  setTimeout(() => {
    isTableLoading.value = false
    ElMessage.success(`已导出 ${logPagination.total} 条日志记录`)
  }, 800)
}

/**
 * 获取日志级别圆点颜色
 * @param {string} level - 日志级别
 * @returns {string} CSS 颜色值
 */
const getLogLevelDotColor = (level) => LOG_LEVEL_DOT_COLOR_MAP[level] || 'var(--zh-text-disabled)'

/**
 * 获取日志级别 Tag 类型
 * @param {string} level - 日志级别
 * @returns {string} ElementPlus Tag type
 */
const getLogLevelTagType = (level) => LOG_LEVEL_TAG_TYPE_MAP[level] || 'info'

// ===================================================================
// 生命周期
// ===================================================================

onMounted(() => {
  loadData()
  window.addEventListener('admin-refresh', handleRefresh)
})

onBeforeUnmount(() => {
  window.removeEventListener('admin-refresh', handleRefresh)
  stopAutoRefresh()
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
        系统配置
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
         3. 全页骨架屏
         =================================================================== -->
    <template v-if="isLoading">
      <div class="space-y-4">
        <div
          v-for="n in 3"
          :key="'skeleton-card-' + n"
          class="rounded-xl p-5"
          :style="{ background: 'var(--zh-background-capsule)', border: '1px solid var(--zh-line-border)' }"
        >
          <div class="skeleton-loader h-5 w-32 mb-4"></div>
          <div class="grid grid-cols-2 gap-x-8 gap-y-3">
            <div v-for="m in 4" :key="'sf-' + n + '-' + m" class="flex items-center gap-3">
              <div class="skeleton-loader h-4 w-16"></div>
              <div class="skeleton-loader h-8 flex-1"></div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- ===================================================================
           4. Tab 1：AI 参数配置
           =================================================================== -->
      <template v-if="activeTab === 'ai'">
        <!-- 未保存提示条 -->
        <el-alert
          v-if="isAiDirty"
          type="warning"
          :closable="false"
          show-icon
          class="mb-4"
          :style="{ borderRadius: 'var(--zh-radius8)' }"
        >
          <template #title>
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)' }">
              当前配置尚未保存，切换页面或刷新将丢失修改
            </span>
          </template>
        </el-alert>

        <!-- 4.1 模型基础参数卡片 -->
        <el-card
          shadow="never"
          class="settings-card mb-4"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Cpu :size="18" :style="{ color: 'var(--zh-text-theme)' }" />
                <span :style="{ fontSize: 'var(--zh-font-size15)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  模型基础参数
                </span>
              </div>
              <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('defaultModel'); resetSingleField('temperature'); resetSingleField('topP'); resetSingleField('maxTokens')">
                恢复本组默认
              </el-button>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
            <!-- 默认模型 -->
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">默认模型</span>
              <el-select v-model="aiConfig.defaultModel" size="default" style="width: 100%;">
                <el-option v-for="opt in MODEL_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>

            <!-- Temperature -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">Temperature</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  {{ aiConfig.temperature.toFixed(1) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <el-slider v-model="aiConfig.temperature" :min="0" :max="2" :step="0.1" :show-tooltip="false" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('temperature')">↺</el-button>
              </div>
            </div>

            <!-- Top-P -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">Top-P</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  {{ aiConfig.topP.toFixed(2) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <el-slider v-model="aiConfig.topP" :min="0" :max="1" :step="0.05" :show-tooltip="false" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('topP')">↺</el-button>
              </div>
            </div>

            <!-- 最大输出 Token -->
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">最大输出 Token</span>
              <div class="flex items-center gap-3">
                <el-input-number v-model="aiConfig.maxTokens" :min="256" :max="32768" :step="256" size="default" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('maxTokens')">↺</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 4.2 生成策略参数卡片 -->
        <el-card
          shadow="never"
          class="settings-card mb-4"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <MagicStick :size="18" :style="{ color: 'var(--zh-text-theme)' }" />
                <span :style="{ fontSize: 'var(--zh-font-size15)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  生成策略参数
                </span>
              </div>
              <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('frequencyPenalty'); resetSingleField('presencePenalty'); resetSingleField('repetitionPenalty'); resetSingleField('maxWords')">
                恢复本组默认
              </el-button>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
            <!-- 频率惩罚 -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">频率惩罚 (Frequency Penalty)</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  {{ aiConfig.frequencyPenalty.toFixed(1) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <el-slider v-model="aiConfig.frequencyPenalty" :min="-2" :max="2" :step="0.1" :show-tooltip="false" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('frequencyPenalty')">↺</el-button>
              </div>
            </div>

            <!-- 存在惩罚 -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">存在惩罚 (Presence Penalty)</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  {{ aiConfig.presencePenalty.toFixed(1) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <el-slider v-model="aiConfig.presencePenalty" :min="-2" :max="2" :step="0.1" :show-tooltip="false" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('presencePenalty')">↺</el-button>
              </div>
            </div>

            <!-- 重复惩罚 -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">重复惩罚</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size14)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  {{ aiConfig.repetitionPenalty.toFixed(2) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <el-slider v-model="aiConfig.repetitionPenalty" :min="1" :max="2" :step="0.05" :show-tooltip="false" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('repetitionPenalty')">↺</el-button>
              </div>
            </div>

            <!-- 单次最大字数 -->
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">单次最大中文字数</span>
              <div class="flex items-center gap-3">
                <el-input-number v-model="aiConfig.maxWords" :min="100" :max="10000" :step="100" size="default" style="flex: 1;" />
                <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('maxWords')">↺</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 4.3 系统提示词模板卡片 -->
        <el-card
          shadow="never"
          class="settings-card mb-5"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Edit :size="18" :style="{ color: 'var(--zh-text-theme)' }" />
                <span :style="{ fontSize: 'var(--zh-font-size15)', fontWeight: 600, color: 'var(--zh-text-primary)' }">
                  系统提示词模板
                </span>
              </div>
              <el-button link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="resetSingleField('systemPrompt')">恢复默认</el-button>
            </div>
          </template>
          <el-input
            v-model="aiConfig.systemPrompt"
            type="textarea"
            :rows="5"
            placeholder="请输入全局系统提示词模板..."
            :style="{ fontSize: 'var(--zh-font-size14)' }"
          />
          <p :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', marginTop: '8px' }">
            系统提示词将作为所有 AI 对话的上下文前缀。建议包含角色定位、输出规范、学科要求等核心约束。
          </p>
        </el-card>

        <!-- 操作按钮区 -->
        <div class="flex items-center justify-end gap-3">
          <el-button @click="handleAiReset" :disabled="!isAiDirty">恢复默认设置</el-button>
          <el-button type="primary" :loading="isAiSaving" :disabled="!isAiDirty" @click="handleAiSave">
            {{ isAiSaving ? '保存中...' : '保存配置' }}
          </el-button>
        </div>
      </template>

      <!-- ===================================================================
           5. Tab 2：导出模板管理
           =================================================================== -->
      <template v-if="activeTab === 'templates'">
        <!-- 筛选器行 -->
        <div class="flex items-center flex-wrap gap-3 mb-4">
          <el-select
            v-model="templateFilters.type"
            placeholder="全部类型"
            clearable
            size="default"
            style="width: 140px;"
            @change="handleTemplateFilterChange"
          >
            <el-option v-for="opt in TEMPLATE_TYPE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>

          <el-select
            v-model="templateFilters.status"
            placeholder="全部状态"
            clearable
            size="default"
            style="width: 120px;"
            @change="handleTemplateFilterChange"
          >
            <el-option v-for="opt in TEMPLATE_STATUS_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>

          <el-input
            v-model="templateFilters.keyword"
            placeholder="搜索模板名称..."
            clearable
            size="default"
            :prefix-icon="Search"
            style="width: 220px;"
            @input="handleTemplateSearchInput"
            @keyup.enter="handleTemplateSearchEnter"
            @clear="handleTemplateFilterChange"
          />

          <div class="flex items-center gap-2 ml-auto">
            <el-button type="primary" :icon="Upload" @click="openUploadDialog">上传模板</el-button>
            <el-button :icon="Download" disabled>批量导出</el-button>
          </div>
        </div>

        <!-- 模板数据表格 -->
        <el-card
          shadow="never"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <el-table
            :data="templateList"
            stripe
            border
            v-loading="isTableLoading"
            element-loading-text="加载中..."
            row-class-name="settings-table-row"
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：模板名称 -->
            <el-table-column prop="name" label="模板名称" min-width="200">
              <template #default="{ row }">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-md flex items-center justify-center shrink-0 text-lg" :style="{ background: 'var(--zh-background-light-gray)' }">
                    {{ getTemplateIcon(row.type) }}
                  </div>
                  <div class="min-w-0">
                    <el-tooltip :content="row.name" placement="top" effect="dark" :disabled="row.name.length <= 18">
                      <span class="block truncate max-w-50" :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-primary)', fontWeight: 500 }">
                        {{ row.name }}
                      </span>
                    </el-tooltip>
                    <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
                      {{ row.isDefault ? '默认模板' : '' }}
                    </span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 列：类型 -->
            <el-table-column prop="type" label="类型" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="getTemplateTagType(row.type)" size="small" effect="plain">
                  {{ TEMPLATE_TYPE_LABEL_MAP[row.type] || row.type }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：版本 -->
            <el-table-column prop="version" label="版本" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
                  {{ row.version }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：大小 -->
            <el-table-column prop="size" label="大小" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">{{ row.size }}</span>
              </template>
            </el-table-column>

            <!-- 列：状态 -->
            <el-table-column prop="status" label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.status === 'enabled'"
                  size="small"
                  @change="handleTemplateStatusToggle(row)"
                />
              </template>
            </el-table-column>

            <!-- 列：是否默认 -->
            <el-table-column prop="isDefault" label="默认" width="70" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.isDefault ? 'var(--zh-yellow)' : 'var(--zh-text-disabled)', fontSize: 'var(--zh-font-size16)' }">
                  {{ row.isDefault ? '★' : '☆' }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：更新时间 -->
            <el-table-column prop="updatedAt" label="更新时间" width="160" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">{{ row.updatedAt }}</span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="240" align="center" fixed="right">
              <template #default="{ row }">
                <div class="flex items-center justify-center gap-1">
                  <el-button
                    v-if="!row.isDefault"
                    type="primary" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="handleSetDefault(row)"
                  >
                    <el-icon class="mr-0.5"><Top /></el-icon>
                    设为默认
                  </el-button>
                  <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="handleDownloadTemplate(row)">
                    <el-icon class="mr-0.5"><Download /></el-icon>
                    下载
                  </el-button>
                  <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="openReplaceDialog(row)">
                    <el-icon class="mr-0.5"><Edit /></el-icon>
                    替换
                  </el-button>
                  <el-button
                    type="danger" link size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    :disabled="row.isDefault"
                    @click="handleDeleteTemplate(row)"
                  >
                    <el-icon class="mr-0.5"><Delete /></el-icon>
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>

            <!-- 空数据 -->
            <template #empty>
              <el-empty description="暂无导出模板" :image-size="80">
                <template v-if="templateFilters.type || templateFilters.status || templateFilters.keyword">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">没有符合条件的模板，请调整筛选条件</span>
                  <el-button type="primary" link size="small" class="mt-2" @click="templateFilters.type = ''; templateFilters.status = ''; templateFilters.keyword = ''; handleTemplateFilterChange();">
                    清除筛选
                  </el-button>
                </template>
                <template v-else>
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">点击「上传模板」添加第一个导出模板</span>
                  <el-button type="primary" size="small" class="mt-3" :icon="Upload" @click="openUploadDialog">
                    上传模板
                  </el-button>
                </template>
              </el-empty>
            </template>
          </el-table>

          <!-- 分页器 -->
          <div v-if="templatePagination.total > 0" class="flex justify-end pt-4 mt-4 border-t" :style="{ borderColor: 'var(--zh-line-parting)' }">
            <el-pagination
              v-model:current-page="templatePagination.currentPage"
              v-model:page-size="templatePagination.pageSize"
              :total="templatePagination.total"
              :page-sizes="PAGE_SIZE_OPTIONS"
              :background="true"
              layout="total, sizes, prev, pager, next, jumper"
              :style="{ '--el-pagination-bg-color': 'var(--zh-background-capsule)', '--el-pagination-button-bg-color': 'var(--zh-background-option)', '--el-pagination-hover-color': 'var(--zh-text-theme)' }"
              @current-change="handleTemplatePageChange"
              @size-change="handleTemplateSizeChange"
            />
          </div>
        </el-card>

        <!-- 上传/替换模板对话框 -->
        <el-dialog
          v-model="templateUploadVisible"
          :title="uploadMode === 'create' ? '上传导出模板' : '替换模板'"
          width="520px"
          destroy-on-close
          :style="{ '--el-dialog-bg-color': 'var(--zh-background-pop)', '--el-dialog-border-radius': 'var(--zh-radius16)' }"
        >
          <!-- 拖拽上传区（仅新建模式） -->
          <div
            v-if="uploadMode === 'create'"
            class="upload-dropzone flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-200 mb-5"
            :style="{ border: '2px dashed var(--zh-line-heavier)', borderRadius: 'var(--zh-radius12)', background: 'var(--zh-background-light-gray)', minHeight: '140px' }"
          >
            <el-icon :size="48" :style="{ color: 'var(--zh-text-caption)' }"><Upload /></el-icon>
            <p :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-caption)' }">
              将文件拖拽到此处，或<span :style="{ color: 'var(--zh-text-link)', textDecoration: 'underline' }">点击上传</span>
            </p>
            <p :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
              支持 .pptx / .docx，最大 20MB
            </p>
            <!-- 演示用示例文件按钮 -->
            <el-button size="small" @click="handleTemplateFileSelect({ name: '标准课件模板.pptx', size: 4.2 * 1024 * 1024 })">
              + 添加示例文件 (PPTX)
            </el-button>
          </div>

          <!-- 替换模式提示 -->
          <div
            v-if="uploadMode === 'replace'"
            class="flex items-center gap-3 p-4 rounded-lg mb-5"
            :style="{ background: 'var(--zh-background-light-gray)', border: '1px solid var(--zh-line-border)' }"
          >
            <InfoFilled :size="20" :style="{ color: 'var(--zh-cyan)' }" />
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
              将替换模板「{{ templateUploadForm.name }}」，新版本号将覆盖旧版本
            </span>
          </div>

          <!-- 表单区 -->
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">模板名称</span>
              <el-input v-model="templateUploadForm.name" placeholder="请输入模板名称" size="default" :disabled="uploadMode === 'replace'" />
            </div>
            <div class="flex items-center gap-4">
              <div class="flex flex-col gap-1.5 flex-1">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">模板类型</span>
                <el-select v-model="templateUploadForm.type" size="default" style="width: 100%;" :disabled="uploadMode === 'replace'">
                  <el-option v-for="opt in TEMPLATE_TYPE_OPTIONS.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
                </el-select>
              </div>
              <div class="flex flex-col gap-1.5 flex-1">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">版本号</span>
                <el-input v-model="templateUploadForm.version" placeholder="如 v2.0" size="default" />
              </div>
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end gap-3">
              <el-button @click="templateUploadVisible = false">取消</el-button>
              <el-button type="primary" :loading="isTemplateUploading" @click="handleTemplateUpload">
                {{ isTemplateUploading ? '上传中...' : (uploadMode === 'create' ? '确认上传' : '确认替换') }}
              </el-button>
            </div>
          </template>
        </el-dialog>
      </template>

      <!-- ===================================================================
           6. Tab 3：系统日志
           =================================================================== -->
      <template v-if="activeTab === 'logs'">
        <!-- 筛选器行 -->
        <div class="flex items-center flex-wrap gap-3 mb-4">
          <el-date-picker
            v-model="logFilters.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            size="default"
            style="width: 370px;"
            @change="handleLogFilterChange"
          />

          <el-select
            v-model="logFilters.level"
            placeholder="全部级别"
            clearable
            size="default"
            style="width: 120px;"
            @change="handleLogFilterChange"
          >
            <el-option v-for="opt in LOG_LEVEL_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>

          <el-select
            v-model="logFilters.module"
            placeholder="全部模块"
            clearable
            size="default"
            style="width: 130px;"
            @change="handleLogFilterChange"
          >
            <el-option v-for="opt in LOG_MODULE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>

          <el-input
            v-model="logFilters.keyword"
            placeholder="搜索日志内容..."
            clearable
            size="default"
            :prefix-icon="Search"
            style="width: 200px;"
            @input="handleLogSearchInput"
            @keyup.enter="handleLogSearchEnter"
            @clear="handleLogFilterChange"
          />

          <div class="flex items-center gap-3 ml-auto">
            <div class="flex items-center gap-2">
              <el-switch
                :model-value="autoRefreshEnabled"
                size="small"
                @change="handleAutoRefreshToggle"
              />
              <span :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)', whiteSpace: 'nowrap' }">
                自动刷新{{ autoRefreshEnabled ? ' (10s)' : '' }}
              </span>
            </div>
            <el-button size="default" :icon="Download" @click="handleExportLogs">导出日志</el-button>
          </div>
        </div>

        <!-- 日志数据表格 -->
        <el-card
          shadow="never"
          :style="{ background: 'var(--zh-background-capsule)', borderRadius: 'var(--zh-radius12)', borderColor: 'var(--zh-line-border)' }"
        >
          <el-table
            :data="logList"
            stripe
            border
            v-loading="isTableLoading"
            element-loading-text="加载中..."
            row-class-name="settings-table-row"
            :style="{
              '--el-table-border-color': 'var(--zh-line-border)',
              '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
              '--el-table-header-text-color': 'var(--zh-text-caption)',
              '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
              '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
              '--el-table-stripe-bg-color': 'var(--zh-background-option)',
            }"
          >
            <!-- 列：时间戳 -->
            <el-table-column prop="timestamp" label="时间戳" width="170">
              <template #default="{ row }">
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">
                  {{ row.timestamp }}
                </span>
              </template>
            </el-table-column>

            <!-- 列：级别 -->
            <el-table-column prop="level" label="级别" width="85" align="center">
              <template #default="{ row }">
                <el-tag :type="getLogLevelTagType(row.level)" size="small" effect="plain">
                  <span class="flex items-center gap-1.5">
                    <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0" :style="{ background: getLogLevelDotColor(row.level) }"></span>
                    {{ LOG_LEVEL_LABEL_MAP[row.level] || row.level }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>

            <!-- 列：模块 -->
            <el-table-column prop="moduleLabel" label="模块" width="100" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">{{ row.moduleLabel }}</span>
              </template>
            </el-table-column>

            <!-- 列：消息摘要 -->
            <el-table-column prop="message" label="消息摘要" min-width="300">
              <template #default="{ row }">
                <el-tooltip :content="row.message" placement="top" effect="dark" :disabled="row.message.length <= 40">
                  <span
                    class="cursor-pointer hover:underline block truncate max-w-90"
                    :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)' }"
                    @click="openLogDetail(row)"
                  >
                    {{ row.message }}
                  </span>
                </el-tooltip>
              </template>
            </el-table-column>

            <!-- 列：操作人 -->
            <el-table-column prop="operator" label="操作人" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">{{ row.operator }}</span>
              </template>
            </el-table-column>

            <!-- 列：操作 -->
            <el-table-column label="操作" width="90" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" :style="{ fontSize: 'var(--zh-font-size12)' }" @click="openLogDetail(row)">
                  <el-icon class="mr-0.5"><View /></el-icon>
                  详情
                </el-button>
              </template>
            </el-table-column>

            <!-- 空数据 -->
            <template #empty>
              <el-empty description="暂无匹配的日志记录" :image-size="80">
                <template v-if="logFilters.level || logFilters.module || logFilters.keyword">
                  <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">当前筛选条件下没有日志，请调整筛选条件</span>
                  <el-button type="primary" link size="small" class="mt-2" @click="handleClearLogFilters">清除筛选</el-button>
                </template>
              </el-empty>
            </template>
          </el-table>

          <!-- 分页器 -->
          <div v-if="logPagination.total > 0" class="flex justify-end pt-4 mt-4 border-t" :style="{ borderColor: 'var(--zh-line-parting)' }">
            <el-pagination
              v-model:current-page="logPagination.currentPage"
              v-model:page-size="logPagination.pageSize"
              :total="logPagination.total"
              :page-sizes="PAGE_SIZE_OPTIONS"
              :background="true"
              layout="total, sizes, prev, pager, next, jumper"
              :style="{ '--el-pagination-bg-color': 'var(--zh-background-capsule)', '--el-pagination-button-bg-color': 'var(--zh-background-option)', '--el-pagination-hover-color': 'var(--zh-text-theme)' }"
              @current-change="handleLogPageChange"
              @size-change="handleLogSizeChange"
            />
          </div>
        </el-card>

        <!-- 日志详情对话框 -->
        <el-dialog
          v-model="logDetailVisible"
          title="日志详情"
          width="640px"
          destroy-on-close
          :style="{ '--el-dialog-bg-color': 'var(--zh-background-pop)', '--el-dialog-border-radius': 'var(--zh-radius16)' }"
        >
          <template v-if="currentLog">
            <!-- 基本信息 Grid -->
            <div class="rounded-lg p-4 mb-4" :style="{ border: '1px solid var(--zh-line-border)' }">
              <div class="grid gap-y-3 gap-x-2" style="grid-template-columns: 90px 1fr;">
                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">时间戳</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)' }">{{ currentLog.timestamp }}</span>

                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">级别</span>
                <span>
                  <el-tag :type="getLogLevelTagType(currentLog.level)" size="small" effect="plain">
                    <span class="flex items-center gap-1.5">
                      <span class="inline-block w-1.5 h-1.5 rounded-full" :style="{ background: getLogLevelDotColor(currentLog.level) }"></span>
                      {{ LOG_LEVEL_LABEL_MAP[currentLog.level] || currentLog.level }}
                    </span>
                  </el-tag>
                </span>

                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">模块</span>
                <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">{{ currentLog.moduleLabel }}</span>

                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">操作人</span>
                <span :style="{ fontSize: 'var(--zh-font-size14)', color: 'var(--zh-text-secondary)' }">{{ currentLog.operator }}</span>

                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">请求 ID</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">{{ currentLog.requestId }}</span>

                <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">IP</span>
                <span :style="{ fontFamily: 'var(--zh-font-number)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">{{ currentLog.ip }}</span>
              </div>
            </div>

            <!-- 消息内容 -->
            <div class="mb-4">
              <span :style="{ fontSize: 'var(--zh-font-size13)', fontWeight: 600, color: 'var(--zh-text-primary)', display: 'block', marginBottom: '8px' }">消息内容</span>
              <div class="rounded-lg p-4 overflow-auto" :style="{ background: 'var(--zh-background-light-gray)', border: '1px solid var(--zh-line-border)', maxHeight: '150px' }">
                <pre :style="{ fontFamily: 'var(--zh-font-code)', fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-primary)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }">{{ currentLog.message }}</pre>
              </div>
            </div>

            <!-- 堆栈跟踪（仅 ERROR 级别） -->
            <div v-if="currentLog.level === 'error' && currentLog.stackTrace" class="mb-4">
              <div
                class="flex items-center gap-2 cursor-pointer select-none py-1"
                @click="stackTraceExpanded = !stackTraceExpanded"
              >
                <el-icon :class="{ 'rotate-180': stackTraceExpanded }" class="transition-transform duration-300" :style="{ color: 'var(--zh-text-caption)' }">
                  <ArrowDown />
                </el-icon>
                <span :style="{ fontSize: 'var(--zh-font-size13)', fontWeight: 600, color: 'var(--zh-text-primary)' }">堆栈跟踪</span>
              </div>
              <div v-show="stackTraceExpanded" class="rounded-lg p-4 overflow-auto mt-2" :style="{ background: 'var(--zh-background-light-gray)', border: '1px solid var(--zh-line-border)', maxHeight: '200px' }">
                <pre :style="{ fontFamily: 'var(--zh-font-code)', fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-secondary)', margin: 0, whiteSpace: 'pre-wrap' }">{{ currentLog.stackTrace }}</pre>
              </div>
            </div>

            <!-- 上下文数据 -->
            <div v-if="currentLog.contextData" class="mb-4">
              <div
                class="flex items-center gap-2 cursor-pointer select-none py-1"
                @click="contextDataExpanded = !contextDataExpanded"
              >
                <el-icon :class="{ 'rotate-180': contextDataExpanded }" class="transition-transform duration-300" :style="{ color: 'var(--zh-text-caption)' }">
                  <ArrowDown />
                </el-icon>
                <span :style="{ fontSize: 'var(--zh-font-size13)', fontWeight: 600, color: 'var(--zh-text-primary)' }">上下文数据 (JSON)</span>
              </div>
              <div v-show="contextDataExpanded" class="rounded-lg p-4 overflow-auto mt-2" :style="{ background: 'var(--zh-background-light-gray)', border: '1px solid var(--zh-line-border)', maxHeight: '200px' }">
                <pre :style="{ fontFamily: 'var(--zh-font-code)', fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-secondary)', margin: 0, whiteSpace: 'pre-wrap' }">{{ currentLog.contextData }}</pre>
              </div>
            </div>
          </template>

          <template #footer>
            <div class="flex justify-end gap-3">
              <el-button :icon="CopyDocument" @click="handleCopyLog">复制全部</el-button>
              <el-button type="primary" @click="logDetailVisible = false">关闭</el-button>
            </div>
          </template>
        </el-dialog>
      </template>
    </template>
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
:deep(.settings-table-row) {
  transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 表格加载遮罩 ===== */
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

/* ===== 配置卡片悬浮态 ===== */
.settings-card {
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1),
              border-color 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.settings-card:hover {
  box-shadow: var(--zh-shadow1) !important;
  border-color: var(--zh-line-heavier) !important;
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
</style>
