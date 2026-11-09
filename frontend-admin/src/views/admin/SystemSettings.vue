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
    - `../apis/export`: 导入 `getExportTemplates`（API-134，查询 Python 全部导出模板）、
      `createExportTemplate`（创建导出模板）、`replaceExportTemplate`（替换模板）
    - `../apis/config`: 导入 `getSystemLogs`（API-106，分页查询系统日志）
  - 输入: 无 props，导出模板数据来自 API-98，系统日志数据来自 API-106
  - 输出: 渲染系统配置视图（Tab 切换 + AI参数表单 + 导出模板表格 + 系统日志表格 + 上传对话框 + 日志详情对话框）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
  - 对应需求文档: §4.7.3.3 — 系统配置与数据看板
-->

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
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
  Loading,
  Film,
  Notebook,
  StarFilled,
  Star,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getExportTemplates, createExportTemplate, replaceExportTemplate, deleteExportTemplate, downloadExportTemplate } from '@/apis/export'
import { getAiConfigs, createAiConfig, publishAiConfig, getSystemLogs } from '@/apis/config'
import FileDropUpload from '@/components/admin/FileDropUpload.vue'
import AgentEvolution from './AgentEvolution.vue'
import { formatFileSize } from '@/utils/file'

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

/** AI 参数配置分组（对应 sys_config.config_group，API-102/103 固定取值） */
const AI_CONFIG_GROUP = 'ai_model'

/**
 * AI 表单字段 → 后端配置项映射
 * numeric 为 true 时回填时执行数值解析，保存时转为字符串存入 config_value
 */
const AI_FIELD_DEFS = [
  { field: 'defaultModel', configKey: 'default_model', description: '默认模型', numeric: false },
  { field: 'temperature', configKey: 'temperature', description: '生成随机性（Temperature）', numeric: true },
  { field: 'topP', configKey: 'top_p', description: '核采样概率（Top-P）', numeric: true },
  { field: 'maxTokens', configKey: 'max_tokens', description: '最大生成 Token 数', numeric: true },
  { field: 'frequencyPenalty', configKey: 'frequency_penalty', description: '频率惩罚', numeric: true },
  { field: 'presencePenalty', configKey: 'presence_penalty', description: '存在惩罚', numeric: true },
  { field: 'repetitionPenalty', configKey: 'repetition_penalty', description: '重复惩罚', numeric: true },
  { field: 'maxWords', configKey: 'max_words', description: '最大生成长度（字）', numeric: true },
  { field: 'systemPrompt', configKey: 'system_prompt', description: '系统提示词', numeric: false },
]

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

/** 日志类型筛选项（对应后端 sys_log.log_type 取值） */
const LOG_LEVEL_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: '操作', value: 'operation' },
  { label: '审核', value: 'audit' },
  { label: '下载', value: 'download' },
  { label: '浏览', value: 'browse' },
]

/** 日志类型 → 显示标签映射 */
const LOG_LEVEL_LABEL_MAP = {
  operation: '操作', audit: '审核', download: '下载', browse: '浏览',
}

/** 日志类型 → Tag 类型映射 */
const LOG_LEVEL_TAG_TYPE_MAP = {
  operation: '', audit: 'warning', download: 'success', browse: 'info',
}

/** 日志类型 → 圆点颜色映射 */
const LOG_LEVEL_DOT_COLOR_MAP = {
  operation: 'var(--zh-cyan)',
  audit: 'var(--zh-orange)',
  download: 'var(--zh-green)',
  browse: 'var(--zh-text-disabled)',
}

/** 日志模块筛选项（对应后端 sys_log.module 取值） */
const LOG_MODULE_OPTIONS = [
  { label: '全部模块', value: '' },
  { label: '项目', value: 'project' },
  { label: '认证', value: 'auth' },
  { label: '用户', value: 'user' },
  { label: '用户管理', value: 'admin_user' },
  { label: '角色管理', value: 'admin_role' },
  { label: '系统配置', value: 'admin_config' },
  { label: '内容审核', value: 'admin_moderation' },
  { label: '社区', value: 'community' },
  { label: '资源库', value: 'resource' },
  { label: '公共资源', value: 'admin_resource' },
  { label: 'AI 引擎', value: 'ai' },
  { label: '导出', value: 'export' },
  { label: '导出模板', value: 'admin_export_template' },
  { label: '告警', value: 'admin_alert' },
]

/** 日志模块 → 显示标签映射 */
const LOG_MODULE_LABEL_MAP = Object.fromEntries(
  LOG_MODULE_OPTIONS.filter((o) => o.value).map((o) => [o.value, o.label]),
)

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

/** AI 配置加载中（回填期间抑制 dirty 监听，避免误报未保存修改） */
const isAiLoading = ref(false)

/** AI 配置保存中 */
const isAiSaving = ref(false)

const teachingCategories = ['语言', '文科', '理科', '工科']
const selectedTeachingCategory = ref('文科')
const teachingPolicies = reactive(Object.fromEntries(teachingCategories.map((category) => [category, {
  subjects: '', method: '', activity: '', visual: '', page_structure: '', examples: '',
}])))
const imageMonthlyQuota = ref(100)
const imageGenerationModel = ref('wan2.2-t2i-flash')
const isTeachingSaving = ref(false)

const fetchTeachingConfigs = async () => {
  try {
    const [subjectRes, imageRes] = await Promise.all([
      getAiConfigs({ config_group: 'teaching_subject' }),
      getAiConfigs({ config_group: 'image_generation' }),
    ])
    for (const config of subjectRes?.data || []) {
      const category = config.config_key?.replace(/^subject_policy:/, '')
      if (!teachingCategories.includes(category)) continue
      try {
        const value = JSON.parse(config.config_value)
        if (Array.isArray(value.subjects)) {
          Object.assign(teachingPolicies[category], value, { subjects: value.subjects.join('、') })
        }
      } catch { /* 后台历史配置异常时保留表单初值 */ }
    }
    const quota = (imageRes?.data || []).find((item) => item.config_key === 'monthly_quota')
    if (quota && Number.isInteger(Number(quota.config_value))) imageMonthlyQuota.value = Number(quota.config_value)
    const model = (imageRes?.data || []).find((item) => item.config_key === 'model')
    if (model?.config_value) imageGenerationModel.value = model.config_value
  } catch { ElMessage.warning('学科策略配置暂时无法加载') }
}

const savePublishedConfig = async (data) => {
  const saved = await createAiConfig(data)
  if (![0, 200].includes(saved?.code) || !saved?.data?.id) throw new Error(saved?.message || '保存失败')
  const published = await publishAiConfig(saved.data.id)
  if (![0, 200].includes(published?.code)) throw new Error(published?.message || '发布失败')
}

const saveTeachingPolicy = async () => {
  const category = selectedTeachingCategory.value
  const value = teachingPolicies[category]
  const subjects = value.subjects.split(/[、,，]/).map((item) => item.trim()).filter(Boolean)
  if (!subjects.length || !value.method.trim() || !value.activity.trim() || !value.visual.trim()) {
    ElMessage.warning('请填写学科关键词、方法、活动和视觉建议')
    return
  }
  isTeachingSaving.value = true
  try {
    await savePublishedConfig({ config_group: 'teaching_subject', config_key: `subject_policy:${category}`,
      config_value: JSON.stringify({ subjects, method: value.method, activity: value.activity, visual: value.visual,
        page_structure: value.page_structure, examples: value.examples }),
      description: `${category}学科教学策略` })
    ElMessage.success('学科策略已发布，Python 服务将在约一分钟内读取')
  } catch (error) { ElMessage.error(error.message || '发布失败') }
  finally { isTeachingSaving.value = false }
}

const saveImageQuota = async () => {
  isTeachingSaving.value = true
  try {
    await savePublishedConfig({ config_group: 'image_generation', config_key: 'monthly_quota',
      config_value: String(imageMonthlyQuota.value), description: '每位教师每月 AI 配图调用额度，0 表示关闭' })
    ElMessage.success('配图额度已发布')
  } catch (error) { ElMessage.error(error.message || '发布失败') }
  finally { isTeachingSaving.value = false }
}

const saveImageModel = async () => {
  const model = imageGenerationModel.value.trim()
  if (!model || model.length > 100) { ElMessage.warning('请输入有效的文生图模型名称'); return }
  isTeachingSaving.value = true
  try {
    await savePublishedConfig({ config_group: 'image_generation', config_key: 'model',
      config_value: model, description: '百炼文生图模型名称' })
    ElMessage.success('配图模型已发布')
  } catch (error) { ElMessage.error(error.message || '发布失败') }
  finally { isTeachingSaving.value = false }
}

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

/** 上传模板表单数据（名称即 Python 侧 theme；模板文件存储于 Python 服务，版本固定 v1） */
const templateUploadForm = reactive({ name: '', type: 'pptx', description: '' })

/** 上传中 */
const isTemplateUploading = ref(false)

/** 当前上传模式：create | replace */
const uploadMode = ref('create')

/** 替换目标模板 ID（Python 侧 theme） */
const replaceTargetId = ref(null)

/** 已选模板文件（单文件队列：模板一次上传一个文件） */
const templateFile = ref(null)

/** 模板文件约束：仅接受 JSON 模板文件（含 html_template 字段，用于 PPT 生成） */
const TEMPLATE_FILE_ACCEPT = '.json'
const TEMPLATE_FILE_MAX_SIZE = 20 * 1024 * 1024

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
  () => {
    if (isAiLoading.value) return
    isAiDirty.value = true
  },
  { deep: true },
)

// ===================================================================
// 数据适配 — 后端 ConfigVO → AI 参数表单（Tab 1：AI 参数配置）
// ===================================================================

/**
 * 将后端配置项数组按 config_key 回填到 AI 参数表单
 * 后端 config_value 一律为字符串；数值字段解析失败或缺失时回落默认值
 * @param {Array<{config_key: string, config_value: string}>} configs - API-102 返回的配置项
 */
const applyAiConfigs = (configs) => {
  const valueMap = new Map((configs || []).map((c) => [c.config_key, c.config_value]))
  AI_FIELD_DEFS.forEach(({ field, configKey, numeric }) => {
    const raw = valueMap.get(configKey)
    if (raw === undefined || raw === null || raw === '') {
      aiConfig[field] = AI_DEFAULTS[field]
      return
    }
    if (!numeric) {
      aiConfig[field] = raw
      return
    }
    const num = Number(raw)
    aiConfig[field] = Number.isFinite(num) ? num : AI_DEFAULTS[field]
  })
}

/**
 * 批量保存 AI 参数（API-103）— 按字段映射逐项提交，任一失败时提示并返回 false
 * 后端按 config_key upsert：已存在则版本+1 并保存历史版本，否则新建
 * @param {Object} values - 表单字段值（field → value）
 * @returns {Promise<boolean>} 是否全部保存成功
 */
const saveAiConfigs = async (values) => {
  const results = await Promise.all(
    AI_FIELD_DEFS.map(({ field, configKey, description, numeric }) =>
      createAiConfig({
        config_group: AI_CONFIG_GROUP,
        config_key: configKey,
        config_value: numeric ? String(values[field]) : values[field],
        description,
      }),
    ),
  )
  const failed = results.find((res) => res?.code !== 0 && res?.code !== 200)
  if (failed) {
    ElMessage.error(failed?.message || 'AI 参数配置保存失败')
    return false
  }
  return true
}

/**
 * 获取 AI 参数配置（API-102，config_group 固定 ai_model）
 * 回填期间抑制 dirty 监听，避免误报"未保存修改"
 */
const fetchAiConfigs = async () => {
  isAiLoading.value = true
  try {
    const res = await getAiConfigs({ config_group: AI_CONFIG_GROUP })
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || 'AI 参数配置加载失败')
      return
    }
    applyAiConfigs(res?.data || [])
    // 等待排队的 dirty watcher 执行完毕（期间被 isAiLoading 抑制）
    await nextTick()
  } catch {
    ElMessage.error('AI 参数配置加载失败，请稍后重试')
  } finally {
    isAiLoading.value = false
    isAiDirty.value = false
  }
}

// ===================================================================
// 数据适配 — 后端 LogVO → 页面行数据（Tab 3：系统日志）
// ===================================================================

/**
 * 将时间格式化为 "YYYY-MM-DD HH:mm:ss"（日志精确到秒）
 * @param {string|Date|undefined} value - 后端返回的时间
 * @returns {string} 格式化后的时间文本
 */
const formatLogTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/**
 * 将时间选择器的值转换为后端可解析的 ISO 格式（yyyy-MM-ddTHH:mm:ss）
 * @param {Date|string} value - 时间选择器值
 * @returns {string|undefined} ISO 时间字符串，无法解析时返回 undefined
 */
const toIsoDateTime = (value) => {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return undefined
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/**
 * 将后端 LogVO 归一化为表格所需结构
 * level 字段承载后端 log_type；message 显示操作动作；detail JSON 放入 contextData 供详情查看
 * @param {Object} vo - 后端日志对象
 * @returns {Object} 归一化后的日志对象
 */
const normalizeLog = (vo) => ({
  id: vo.id,
  timestamp: formatLogTime(vo.created_at),
  level: vo.log_type || '',
  module: vo.module || '',
  moduleLabel: LOG_MODULE_LABEL_MAP[vo.module] || vo.module || '—',
  message: vo.action || '',
  operator: vo.user_id != null ? `#${vo.user_id}` : 'system',
  requestId: vo.request_id || '—',
  ip: vo.ip || '—',
  stackTrace: vo.error_message || '',
  contextData: vo.detail || '',
})

// ===================================================================
// 数据适配
// ===================================================================

/**
 * 将 Python 模板 VO（theme/template_name/aliases/is_default/size）归一化为表格所需结构
 * Python 侧不提供 export_type/version/status/时间字段：固定 pptx/v1/published
 * @param {Object} t - Python 返回的模板对象
 * @returns {Object} 归一化后的模板对象
 */
const normalizeTemplate = (t) => ({
  id: t.theme,
  name: t.template_name || t.theme,
  type: 'pptx',
  version: 'v1',
  size: t.size || '—',
  isDefault: !!t.is_default,
  status: 'enabled',
  updatedAt: '—',
  uploader: '管理员',
  downloadCount: 0,
})

// ===================================================================
// 数据筛选与获取方法
// ===================================================================

/**
 * 获取模板列表数据（API-134，Python 全量返回）
 * Python 不支持筛选/分页参数：前端按类型/状态/关键词过滤后分页切片
 */
const fetchTemplates = async () => {
  isTableLoading.value = true
  try {
    const res = await getExportTemplates()
    const data = res?.data
    const all = data?.templates || []
    const keyword = templateFilters.keyword.trim().toLowerCase()
    const filtered = all.filter((t) => {
      if (templateFilters.type && templateFilters.type !== 'pptx') return false
      if (templateFilters.status && templateFilters.status !== 'enabled') return false
      if (keyword && !`${t.template_name || ''}${t.theme || ''}`.toLowerCase().includes(keyword)) return false
      return true
    })
    templatePagination.total = filtered.length
    const start = (templatePagination.currentPage - 1) * templatePagination.pageSize
    templateList.value = filtered.slice(start, start + templatePagination.pageSize).map(normalizeTemplate)
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 获取日志列表数据（API-106）
 * 将前端筛选条件映射为后端查询参数，服务端过滤分页（结果按创建时间倒序）
 */
const fetchLogs = async () => {
  isTableLoading.value = true
  try {
    // 组装查询参数：只传有效的筛选条件
    const params = { page: logPagination.currentPage, size: logPagination.pageSize }
    if (logFilters.level) params.log_type = logFilters.level
    if (logFilters.module) params.module = logFilters.module
    if (logFilters.keyword.trim()) params.keyword = logFilters.keyword.trim()
    if (Array.isArray(logFilters.timeRange) && logFilters.timeRange.length === 2) {
      params.start_time = toIsoDateTime(logFilters.timeRange[0])
      params.end_time = toIsoDateTime(logFilters.timeRange[1])
    }

    const res = await getSystemLogs(params)
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '系统日志加载失败')
      logList.value = []
      logPagination.total = 0
      return
    }
    const data = res?.data
    const rows = data?.records || data?.list || data?.items || []
    logList.value = rows.map(normalizeLog)
    logPagination.total = Number(data?.total ?? rows.length)
  } catch {
    ElMessage.error('系统日志加载失败，请稍后重试')
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 获取当前 Tab 对应的数据
 */
const fetchData = async () => {
  if (activeTab.value === 'ai') await fetchAiConfigs()
  else if (activeTab.value === 'templates') await fetchTemplates()
  else if (activeTab.value === 'logs') await fetchLogs()
}

/**
 * 页面首次数据加载
 */
const loadData = async () => {
  isLoading.value = true
  try {
    await fetchData()
  } finally {
    isLoading.value = false
  }
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
 * 保存 AI 参数配置（API-103）— 二次确认后按字段逐项提交
 */
const handleAiSave = () => {
  ElMessageBox.confirm(
    '确认保存当前 AI 参数配置？修改将立即生效，影响所有教师的 AI 生成结果。',
    '保存配置',
    { confirmButtonText: '确认保存', cancelButtonText: '取消', type: 'info' },
  )
    .then(async () => {
      isAiSaving.value = true
      try {
        const ok = await saveAiConfigs({ ...aiConfig })
        if (!ok) return
        await fetchAiConfigs()
        ElMessage.success('AI 参数配置已保存并生效')
      } catch {
        ElMessage.error('AI 参数配置保存失败，请稍后重试')
      } finally {
        isAiSaving.value = false
      }
    })
    .catch(() => {})
}

/**
 * 恢复全部 AI 参数为默认值 — 二次确认后将默认值写回后端（API-103）
 */
const handleAiReset = () => {
  ElMessageBox.confirm(
    '恢复默认设置将覆盖当前所有配置，是否继续？',
    '恢复默认',
    { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'warning' },
  )
    .then(async () => {
      isAiSaving.value = true
      try {
        const ok = await saveAiConfigs(AI_DEFAULTS)
        if (!ok) return
        Object.assign(aiConfig, AI_DEFAULTS)
        await fetchAiConfigs()
        ElMessage.success('已恢复为默认设置并自动保存')
      } catch {
        ElMessage.error('恢复默认设置失败，请稍后重试')
      } finally {
        isAiSaving.value = false
      }
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
 * 打开替换模板对话框 — 预填当前模板信息，等待选择新文件（默认模板不可替换）
 * @param {Object} row - 模板行数据
 */
const openReplaceDialog = (row) => {
  if (row.isDefault) {
    ElMessage.warning('默认模板不可替换，请新建模板后使用')
    return
  }
  uploadMode.value = 'replace'
  replaceTargetId.value = row.id
  templateUploadForm.name = row.name
  templateUploadForm.type = row.type
  templateUploadForm.description = ''
  templateFile.value = null
  templateUploadVisible.value = true
}

/**
 * 删除模板 — 二次确认后调用 DELETE 接口（默认模板后端同样拒绝删除）
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
    .then(async () => {
      try {
        const res = await deleteExportTemplate(row.id)
        if (res?.code !== 0 && res?.code !== 200) {
          ElMessage.error(res?.message || `删除模板「${row.name}」失败`)
          return
        }
        ElMessage.success(`已删除模板「${row.name}」`)
        if (templateList.value.length === 1 && templatePagination.currentPage > 1) templatePagination.currentPage--
        fetchTemplates()
      } catch {
        ElMessage.error('删除模板失败，请稍后重试')
      }
    })
    .catch(() => {})
}

/**
 * 下载模板 JSON 文件 — 请求 blob 后经 objectURL 触发浏览器下载（文件名与 Python 侧一致：theme.json）
 * @param {Object} row - 模板行数据
 */
const handleDownloadTemplate = async (row) => {
  try {
    const response = await downloadExportTemplate(row.id)
    const blob = new Blob([response?.data], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${row.id}.json`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`已开始下载「${row.name}」模板文件`)
  } catch (error) {
    const message = error?.response?.data && typeof error.response.data === 'string'
      ? (() => { try { return JSON.parse(error.response.data)?.message } catch { return null } })()
      : null
    ElMessage.error(message || `下载模板「${row.name}」失败，请稍后重试`)
  }
}

/**
 * 打开上传模板对话框（新建模式）
 */
const openUploadDialog = () => {
  uploadMode.value = 'create'
  replaceTargetId.value = null
  templateUploadForm.name = ''
  templateUploadForm.type = 'pptx'
  templateUploadForm.description = ''
  templateFile.value = null
  templateUploadVisible.value = true
}

// ===================================================================
// 上传模板 — 拖拽/选择交互由 FileDropUpload 组件承担，此处仅做模板 JSON 结构校验
// ===================================================================

/**
 * 校验模板 JSON 结构：顶层对象且含 html_template 字段
 * （扩展名/大小/单文件限制已由 FileDropUpload 通用校验完成，此处只做模板结构校验）
 * @param {string} content - 模板文件文本
 * @returns {string} 校验失败原因，通过时返回空串
 */
const getTemplateJsonError = (content) => {
  let parsed
  try {
    parsed = JSON.parse(content)
  } catch (error) {
    return `模板文件不是有效的 JSON 格式：${error?.message || '解析失败'}`
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return '模板 JSON 顶层必须是对象（{...}）'
  }
  if (!String(parsed.html_template || '').trim()) {
    return '模板 JSON 缺少 html_template 字段，无法用于 PPT 生成'
  }
  return ''
}

/**
 * 处理 FileDropUpload 通过通用校验（.json 扩展名 / ≤20MB / 单文件）后的模板文件：
 * 读取文本内容存入单文件队列（重复选择直接覆盖），类型锁定 pptx，名称为空时自动回填
 * @param {Array<File>} files - 通过通用校验的文件集合（multiple=false 至多一个）
 */
const onTemplateFilesAccepted = async (files) => {
  const file = files?.[0]
  if (!file) return
  // 读取文本内容，确认上传时整体提交给 Python 侧
  let content
  try {
    content = await file.text()
  } catch {
    ElMessage.error('读取模板文件失败，请重试')
    return
  }
  const jsonError = getTemplateJsonError(content)
  if (jsonError) {
    ElMessage.warning(jsonError)
    return
  }
  templateFile.value = {
    uid: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    file,
    content,
    name: file.name,
    size: file.size,
    format: 'json',
    status: 'ready',
    progress: 0,
    error: '',
  }
  // 名称即 Python 侧 theme（模板文件名），名称为空时自动回填文件名去后缀
  templateUploadForm.type = 'pptx'
  if (!templateUploadForm.name.trim()) {
    templateUploadForm.name = file.name.replace(/\.json$/i, '')
  }
}

/** 移除已选文件（上传中禁止） */
const removeTemplateFile = () => {
  if (isTemplateUploading.value) return
  templateFile.value = null
}

/** 文件状态显示文本 */
const getTemplateFileStatusText = (status, progress) =>
  status === 'success' ? '已完成' : status === 'uploading' ? `${progress}%` : status === 'error' ? '失败' : '待上传'

/**
 * 执行模板上传/替换 — 调用 API-95 创建 / API-100 替换
 * template_data 提交所选 JSON 文件的文本内容，Python 侧落盘为 {theme}.json（theme 即表单名称）
 */
const handleTemplateUpload = async () => {
  if (!templateFile.value) { ElMessage.warning('请先选择模板文件'); return }
  if (!templateUploadForm.name.trim()) { ElMessage.warning('请输入模板名称'); return }

  const item = templateFile.value
  isTemplateUploading.value = true
  item.status = 'uploading'
  item.progress = 0
  item.error = ''
  // JSON 提交无字节级进度，用渐进模拟呈现（完成后跳 100%）
  const progressTimer = setInterval(() => {
    if (item.progress < 90) item.progress = Math.min(90, item.progress + 6)
  }, 150)

  try {
    const payload = {
      name: templateUploadForm.name.trim(),
      template_data: item.content,
      description: templateUploadForm.description || undefined,
    }
    const res = uploadMode.value === 'create'
      ? await createExportTemplate(payload)
      : await replaceExportTemplate(replaceTargetId.value, payload)
    if (res?.code !== 0 && res?.code !== 200) {
      item.status = 'error'
      item.error = res?.message || '上传失败'
      ElMessage.error(res?.message || `模板「${templateUploadForm.name}」上传失败`)
      return
    }
    item.status = 'success'
    item.progress = 100
    ElMessage.success(uploadMode.value === 'create'
      ? `模板「${templateUploadForm.name}」上传成功`
      : `模板「${templateUploadForm.name}」已替换`)
    templateUploadVisible.value = false
    fetchTemplates()
  } catch (error) {
    item.status = 'error'
    item.error = error?.message || '上传失败，请重试'
    ElMessage.error('上传模板失败，请稍后重试')
  } finally {
    clearInterval(progressTimer)
    isTemplateUploading.value = false
  }
}

/**
 * 获取模板类型图标（Element Plus 图标组件）
 * pptx 课件 → Film（放映胶片）；docx 教案 → Notebook（教案本）
 * @param {string} type - 模板类型
 * @returns {Component} Element Plus 图标组件
 */
const getTemplateIcon = (type) => (type === 'pptx' ? Film : Notebook)

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
  fetchTeachingConfigs()
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
                <el-icon :size="18" :style="{ color: 'var(--zh-text-theme)' }"><Cpu /></el-icon>
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
                <el-icon :size="18" :style="{ color: 'var(--zh-text-theme)' }"><MagicStick /></el-icon>
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
                <el-icon :size="18" :style="{ color: 'var(--zh-text-theme)' }"><Edit /></el-icon>
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

        <el-card shadow="never" class="settings-card mt-5 mb-4">
          <template #header>学科教学策略（保存并发布后供 Python 生成链路读取）</template>
          <el-select v-model="selectedTeachingCategory" class="mb-3" style="width: 180px">
            <el-option v-for="category in teachingCategories" :key="category" :label="category" :value="category" />
          </el-select>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <el-input v-model="teachingPolicies[selectedTeachingCategory].subjects" placeholder="适用学科，用顿号分隔，如语文、历史" />
            <el-input v-model="teachingPolicies[selectedTeachingCategory].method" placeholder="教学方法" />
            <el-input v-model="teachingPolicies[selectedTeachingCategory].activity" placeholder="学生参与活动" />
            <el-input v-model="teachingPolicies[selectedTeachingCategory].visual" placeholder="图文与组件建议" />
            <el-input v-model="teachingPolicies[selectedTeachingCategory].page_structure" placeholder="页面结构，如问题→实验→结论→练习" />
            <el-input v-model="teachingPolicies[selectedTeachingCategory].examples" placeholder="示例库提示，如史料比较、函数图像探究" />
          </div>
          <div class="mt-3 flex justify-end">
            <el-button type="primary" :loading="isTeachingSaving" @click="saveTeachingPolicy">发布本学科策略</el-button>
          </div>
        </el-card>
        <AgentEvolution />
        <el-card shadow="never" class="settings-card mb-4">
          <template #header>AI 配图额度</template>
          <div class="flex flex-wrap items-center gap-3">
            <span>每位教师每月调用次数</span>
            <el-input-number v-model="imageMonthlyQuota" :min="0" :max="100000" />
            <span class="text-sm">0 表示关闭；缓存命中不计入额度。</span>
            <el-button type="primary" :loading="isTeachingSaving" @click="saveImageQuota">发布额度</el-button>
          </div>
          <div class="flex flex-wrap items-center gap-3 mt-4">
            <span>百炼文生图模型</span>
            <el-input v-model="imageGenerationModel" style="width: 260px" placeholder="wan2.2-t2i-flash" />
            <el-button type="primary" :loading="isTeachingSaving" @click="saveImageModel">发布模型</el-button>
          </div>
        </el-card>
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
                  <!-- 模板类型图标：主题色底 + 白色描线（与角色管理图标规范一致） -->
                  <div class="w-10 h-10 rounded-md flex items-center justify-center shrink-0" :style="{ background: 'var(--zh-gradient-blue)' }">
                    <el-icon style="color: #ffffff; font-size: 20px;">
                      <component :is="getTemplateIcon(row.type)" />
                    </el-icon>
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
                <el-icon
                  :style="{ color: row.isDefault ? 'var(--zh-yellow)' : 'var(--zh-text-disabled)', fontSize: 'var(--zh-font-size16)' }"
                >
                  <component :is="row.isDefault ? StarFilled : Star" />
                </el-icon>
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

        <!-- 上传/替换模板对话框（结构参考用户端个人资源库上传素材） -->
        <el-dialog
          v-model="templateUploadVisible"
          :title="uploadMode === 'create' ? '上传导出模板' : '替换模板'"
          width="680px"
          destroy-on-close
          :close-on-click-modal="!isTemplateUploading"
          :close-on-press-escape="!isTemplateUploading"
          :show-close="!isTemplateUploading"
          :style="{ '--el-dialog-bg-color': 'var(--zh-background-pop)', '--el-dialog-border-radius': 'var(--zh-radius16)' }"
        >
          <!-- 拖拽上传区（复用 FileDropUpload：仅 .json / 单文件 / ≤20MB） -->
          <FileDropUpload
            :accept="TEMPLATE_FILE_ACCEPT"
            :multiple="false"
            :accept-exts="['json']"
            :max-size-bytes="TEMPLATE_FILE_MAX_SIZE"
            :disabled="isTemplateUploading"
            @accept="onTemplateFilesAccepted"
          >
            <template #default="{ dragOver }">
              <div
                class="upload-dropzone"
                :class="{ 'is-dragover': dragOver, 'is-uploading': isTemplateUploading }"
              >
                <el-icon :size="42" class="upload-dropzone-icon">
                  <Loading v-if="isTemplateUploading" class="upload-loading-icon" />
                  <Upload v-else />
                </el-icon>
                <strong>{{ isTemplateUploading ? '正在上传模板，请稍候…' : '拖拽文件到这里，或点击选择文件' }}</strong>
                <span>仅支持 .json 模板文件（需含 html_template 字段），单文件最大 20MB，一次上传一个文件</span>
              </div>
            </template>
          </FileDropUpload>

          <!-- 替换模式提示 -->
          <div
            v-if="uploadMode === 'replace'"
            class="flex items-center gap-3 p-4 rounded-lg mb-5"
            :style="{ background: 'var(--zh-background-light-gray)', border: '1px solid var(--zh-line-border)' }"
          >
            <el-icon :size="16" :style="{ color: 'var(--zh-cyan)' }"><InfoFilled /></el-icon>
            <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-secondary)' }">
              将替换模板「{{ templateUploadForm.name }}」的模板内容，替换后立即生效
            </span>
          </div>

          <!-- 已选文件队列（单文件） -->
          <section v-if="templateFile" class="upload-queue" aria-label="待上传模板文件">
            <div class="upload-file-list">
              <div class="upload-file-item">
                <span class="upload-file-mark">{{ templateFile.format }}</span>
                <div class="upload-file-info">
                  <div class="upload-file-title-row">
                    <strong :title="templateFile.name">{{ templateFile.name }}</strong>
                  </div>
                  <el-progress
                    v-if="templateFile.status === 'uploading' || templateFile.status === 'success'"
                    :percentage="templateFile.progress"
                    :stroke-width="4"
                    :show-text="false"
                    :status="templateFile.status === 'success' ? 'success' : undefined"
                  />
                  <small v-if="templateFile.status === 'error'" class="upload-error">{{ templateFile.error }}</small>
                </div>
                <span class="upload-file-size">{{ formatFileSize(templateFile.size) }}</span>
                <span
                  class="upload-file-status"
                  :class="{ 'is-success': templateFile.status === 'success', 'is-error': templateFile.status === 'error' }"
                >
                  {{ getTemplateFileStatusText(templateFile.status, templateFile.progress) }}
                </span>
                <el-button
                  text
                  circle
                  :icon="Delete"
                  :disabled="isTemplateUploading"
                  aria-label="移除文件"
                  @click="removeTemplateFile"
                />
              </div>
            </div>
          </section>

          <!-- 表单区：模板名称与类型 -->
          <div class="flex flex-col gap-4 mt-5">
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">模板名称</span>
              <el-input
                v-model="templateUploadForm.name"
                placeholder="请输入模板名称"
                size="default"
                maxlength="50"
                :disabled="uploadMode === 'replace' || isTemplateUploading"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <span :style="{ fontSize: 'var(--zh-font-size13)', color: 'var(--zh-text-caption)' }">模板类型</span>
              <el-select
                v-model="templateUploadForm.type"
                size="default"
                style="width: 100%;"
                :disabled="!!templateFile || uploadMode === 'replace' || isTemplateUploading"
              >
                <el-option label="PPTX 课件" value="pptx" />
              </el-select>
              <span v-if="templateFile" :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-disabled)' }">
                类型已锁定为 PPTX 课件，Word 教案模板暂未开放
              </span>
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end gap-3">
              <el-button :disabled="isTemplateUploading" @click="templateUploadVisible = false">取消</el-button>
              <el-button
                type="primary"
                :disabled="isTemplateUploading || !templateFile"
                @click="handleTemplateUpload"
              >
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
            placeholder="全部类型"
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
            <el-table-column prop="level" label="类型" width="85" align="center">
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
            <div v-if="currentLog.stackTrace" class="mb-4">
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

/* ===== 上传模板拖拽区与文件队列（样式参考用户端个人资源库上传素材） ===== */
.upload-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  border: 1.5px dashed var(--zh-line-heavier);
  border-radius: var(--zh-radius12);
  color: var(--zh-text-secondary);
  background: var(--zh-background-light-gray);
  cursor: pointer;
  transition: border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}
.upload-dropzone:hover,
.upload-dropzone.is-dragover {
  border-color: var(--zh-text-theme);
  background: var(--zh-background-option-on);
  box-shadow: inset 0 0 0 1px var(--zh-text-theme);
}
.upload-dropzone.is-uploading { cursor: wait; opacity: 0.82; }
.upload-dropzone strong { color: var(--zh-text-primary); font-size: 14px; font-weight: 600; }
.upload-dropzone span { color: var(--zh-text-caption); font-size: 12px; text-align: center; }
.upload-dropzone-icon { color: var(--zh-text-theme); }
.upload-loading-icon { animation: template-upload-spin 1.4s linear infinite; }

.upload-queue { margin-top: 20px; }
.upload-queue :deep(.el-progress-bar__outer) { background: var(--zh-background-option); }
.upload-file-list { border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); }
.upload-file-item { display: flex; align-items: center; gap: 10px; min-height: 66px; padding: 10px 12px; }
.upload-file-mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex: 0 0 38px;
  border-radius: 7px;
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.upload-file-info { min-width: 0; flex: 1; }
.upload-file-title-row { display: flex; align-items: center; gap: 4px; min-width: 0; }
.upload-file-title-row strong {
  min-width: 0;
  overflow: hidden;
  color: var(--zh-text-primary);
  font-size: 14px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-file-info :deep(.el-progress) { margin-top: 5px; }
.upload-file-size { flex: 0 0 62px; color: var(--zh-text-caption); font-size: 12px; text-align: right; font-family: var(--zh-font-number); }
.upload-file-status { flex: 0 0 48px; color: var(--zh-text-caption); font-size: 12px; text-align: right; }
.upload-file-status.is-success { color: var(--zh-green); }
.upload-file-status.is-error,
.upload-error { color: var(--zh-red); }
.upload-error { display: block; margin-top: 4px; overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@keyframes template-upload-spin { to { transform: rotate(360deg); } }

/* ===== 旋转动画（折叠箭头） ===== */
.rotate-180 {
  transform: rotate(180deg);
}
</style>
