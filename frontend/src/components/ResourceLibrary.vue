<!--
  [数据交互说明]
  - 导入: 资源库演示数据、Element Plus 组件与图标
  - 输出: 教师个人资源库页面
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Edit, Folder, Loading, Lock, MoreFilled, Plus, Refresh, Search, Setting, Upload } from '@element-plus/icons-vue'
import {
  batchResourceAction,
  bootstrapResourceIndex,
  createResourceCategory,
  createResourceTag,
  deleteResource,
  deleteResourceCategory,
  deleteResourceIndex,
  deleteResourceTag,
  downloadResource,
  getResourceIndexOverview,
  getResourcePermission,
  listResourceCategories,
  listResourceIndexLogs,
  listResourceIndexResources,
  listResourceTags,
  listResources,
  searchResourceIndex,
  setResourcePermission,
  syncResourceIndex,
  updateResource,
  updateResourceCategory,
  updateResourceTag,
  uploadResource,
} from '../apis/teacher'

const keyword = ref('')
const activeFolder = ref('全部素材')
const selectedRows = ref([])
const resources = ref([])
const resourceTotal = ref(0)
const uploadInput = ref(null)
const loading = ref(false)
const uploading = ref(false)
const uploadDialogVisible = ref(false)
const uploadQueue = ref([])
const isDragOver = ref(false)
const typeFilter = ref('')
const editDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const batchDialogVisible = ref(false)
const taxonomyDialogVisible = ref(false)
const taxonomyTab = ref('category')
const taxonomyLoading = ref(false)
const taxonomySaving = ref(false)
const taxonomyEditing = ref(null)
const taxonomyForm = ref({ name: '', color: '', sort_order: 1000 })
const categories = ref([])
const tags = ref([])
const indexDialogVisible = ref(false)
const indexTab = ref('overview')
const indexLoading = ref(false)
const indexActionLoading = ref(false)
const indexOverview = ref({})
const indexResources = ref([])
const indexResourceTotal = ref(0)
const indexLogs = ref([])
const indexLogTotal = ref(0)
const indexAvailable = ref('')
const indexSearchQuery = ref('')
const indexSearchResults = ref([])
const indexSearchLoading = ref(false)
const saving = ref(false)
const editingRow = ref(null)
const editForm = ref({ file_name: '', description: '', categories: [], tags: [] })
const permissionForm = ref({ access_type: 'private', authorized_users: '', allow_ai: false })
const batchForm = ref({ action: 'delete', target: '' })

// 移动端判定（<768px）：表格切换为卡片列表、分类入口移到顶部下拉
const isMobile = ref(false)
let mobileMediaQuery = null
const handleMobileMediaChange = (event) => {
  isMobile.value = event.matches
  // 表格与卡片的选择状态不互通，断点切换时清空，避免批量管理作用于不可见选择
  selectedRows.value = []
}

const MAX_UPLOAD_FILES = 20
const MAX_UPLOAD_FILE_SIZE = 500 * 1024 * 1024
const SUPPORTED_UPLOAD_EXTENSIONS = new Set([
  'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip',
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp3', 'wav', 'm4a',
  'mp4', 'avi', 'mov', 'mkv',
])

const completedUploadCount = computed(() => uploadQueue.value.filter((file) => file.status === 'success').length)
const uploadOverallProgress = computed(() => {
  if (!uploadQueue.value.length) return 0
  const total = uploadQueue.value.reduce((sum, file) => sum + (Number(file.progress) || 0), 0)
  return Math.round(total / uploadQueue.value.length)
})
/** 上传队列全部成功（进度条 success 态，修复模板引用未定义变量的存量问题） */
const uploadAllComplete = computed(() => uploadQueue.value.length > 0 && completedUploadCount.value === uploadQueue.value.length)
const uploadProgressTimers = new Map()

const formatFileSize = (bytes) => {
  const size = Number(bytes) || 0
  if (size < 1024) return `${size} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  const unitIndex = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length)
  return `${Number((size / (1024 ** unitIndex)).toFixed(2))} ${units[unitIndex - 1]}`
}

const formatUpdatedAt = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date)
}

const parseList = (value) => {
  if (Array.isArray(value)) return value
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch { return String(value).split(/[,，、]/).map((item) => item.trim()).filter(Boolean) }
}

const normalizeRealResource = (item) => ({
  id: item.id,
  name: item.file_name || item.name || '未命名资源',
  type: (item.file_type || 'file').toUpperCase(),
  course: parseList(item.categories).join(' · ') || '未分类',
  size: formatFileSize(item.file_size),
  fileSize: Number(item.file_size) || 0,
  date: formatUpdatedAt(item.updated_at || item.created_at),
  // AI 索引状态：异步同步期间展示「索引中」过程态，完成后按 allow_ai 显示启用态
  status: item.ai_index_status === 'indexing' ? '索引中' : (item.allow_ai === 1 ? '已启用' : '未启用'),
  private: item.access_type !== 'shared',
  description: item.description || '',
  raw: item,
})

const resourceStats = computed(() => {
  const totalSize = resources.value.reduce((sum, item) => sum + item.fileSize, 0)
  const aiAvailable = resources.value.filter((item) => item.status === '已启用').length
  return [
    { label: '全部素材', value: String(resourceTotal.value), detail: `当前已加载 ${resources.value.length} 项` },
    { label: '可供 AI 引用', value: String(aiAvailable), detail: '依据资源授权状态统计' },
    { label: '已加载空间', value: formatFileSize(totalSize), detail: '当前列表资源总大小' },
  ]
})

const resourceFolders = computed(() => [
  '全部素材',
  ...new Set([
    ...categories.value.map((item) => item.name),
    ...resources.value.flatMap((item) => item.course === '未分类' ? [] : item.course.split(' · ')),
  ]),
])

const taxonomyItems = computed(() => taxonomyTab.value === 'category' ? categories.value : tags.value)
const taxonomyTitle = computed(() => taxonomyTab.value === 'category' ? '分类词典' : '标签词典')
const taxonomyTypeLabel = computed(() => taxonomyTab.value === 'category' ? '分类' : '标签')
const indexGroups = computed(() => Array.isArray(indexOverview.value.groups) ? indexOverview.value.groups : [])

const visibleFiles = computed(() => resources.value.filter((file) => (
  (activeFolder.value === '全部素材' || file.course.split(' · ').includes(activeFolder.value)) &&
  (!typeFilter.value || file.type.toLowerCase() === typeFilter.value) &&
  file.name.toLowerCase().includes(keyword.value.toLowerCase())
)))
const filteredFiles = computed(() => resources.value.filter((file) => (
  (activeFolder.value === '全部素材' || activeFolder.value === '我的课件' && file.type === 'PPT') &&
  file.name.toLowerCase().includes(keyword.value.toLowerCase())
)))

const normalizeResource = (item) => ({
  id: item.id, name: item.file_name || item.name, type: item.file_type?.toUpperCase() || item.type || '文件',
  course: item.course || item.categories?.join(' · ') || '未分类', size: item.file_size_text || item.size || '—',
  date: item.updated_at || item.date || '刚刚', status: item.parse_status || item.status || '待解析',
  private: item.access_type !== 'shared',
})

const loadResources = async () => {
  loading.value = true
  try {
    const result = await listResources({ keyword: keyword.value || undefined, page: 1, size: 50 })
    const records = result?.data?.records || result?.data?.list || result?.data?.items || result?.records || []
    resources.value = records.map(normalizeRealResource)
    resourceTotal.value = Number(result?.data?.total ?? result?.total ?? resources.value.length)
  } catch { /* 开发环境保留示例数据，接口上线后自动替换。 */ } finally { loading.value = false }
}

const clearUploadProgressTimers = () => {
  uploadProgressTimers.forEach((timer) => clearInterval(timer))
  uploadProgressTimers.clear()
}

const resetUploadQueue = () => {
  clearUploadProgressTimers()
  uploadQueue.value = []
  isDragOver.value = false
  uploading.value = false
}

const startUpload = () => {
  resetUploadQueue()
  uploadDialogVisible.value = true
}

const openFilePicker = () => {
  if (!uploading.value) uploadInput.value?.click()
}

const getFileExtension = (name) => {
  const parts = String(name || '').toLowerCase().split('.')
  return parts.length > 1 ? parts.pop() : ''
}

const isSupportedUploadFile = (file) => {
  const extension = getFileExtension(file.name)
  return SUPPORTED_UPLOAD_EXTENSIONS.has(extension)
    || String(file.type || '').startsWith('image/')
    || String(file.type || '').startsWith('audio/')
    || String(file.type || '').startsWith('video/')
}

const addUploadFiles = (files) => {
  if (uploading.value) return
  const incomingFiles = Array.from(files || [])
  if (!incomingFiles.length) return

  const availableSlots = MAX_UPLOAD_FILES - uploadQueue.value.length
  if (availableSlots <= 0) {
    ElMessage.warning(`单次最多上传 ${MAX_UPLOAD_FILES} 个文件`)
    return
  }

  const existingKeys = new Set(uploadQueue.value.map((item) => `${item.name}:${item.size}:${item.lastModified || 0}`))
  const acceptedFiles = []
  let oversizedCount = 0
  let unsupportedCount = 0
  let duplicateCount = 0

  for (const file of incomingFiles) {
    const key = `${file.name}:${file.size}:${file.lastModified || 0}`
    if (existingKeys.has(key)) {
      duplicateCount += 1
      continue
    }
    if (file.size > MAX_UPLOAD_FILE_SIZE) {
      oversizedCount += 1
      continue
    }
    if (!isSupportedUploadFile(file)) {
      unsupportedCount += 1
      continue
    }
    existingKeys.add(key)
    acceptedFiles.push(file)
  }

  acceptedFiles.slice(0, availableSlots).forEach((file, index) => {
    uploadQueue.value.push({
      uid: `${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
      file,
      name: file.name,
      size: file.size,
      lastModified: file.lastModified,
      format: getFileExtension(file.name) || 'file',
      status: 'ready',
      progress: 0,
      error: '',
    })
  })

  const overflowCount = Math.max(acceptedFiles.length - availableSlots, 0)
  if (oversizedCount) ElMessage.warning(`${oversizedCount} 个文件超过 500MB，已跳过`)
  if (unsupportedCount) ElMessage.warning(`${unsupportedCount} 个文件格式不受支持，已跳过`)
  if (duplicateCount) ElMessage.info(`${duplicateCount} 个重复文件已跳过`)
  if (overflowCount) ElMessage.warning(`单次最多上传 ${MAX_UPLOAD_FILES} 个文件，已忽略多余文件`)

  // 文件一旦进入队列就立即开始传输，不再等待底部按钮触发。
  void handleUpload()
}

const handleUploadInputChange = (event) => {
  addUploadFiles(event.target?.files)
  if (event.target) event.target.value = ''
}

const handleUploadDragOver = (event) => {
  event.preventDefault()
  if (!uploading.value) isDragOver.value = true
}

const handleUploadDragLeave = (event) => {
  event.preventDefault()
  if (event.currentTarget === event.target || !event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

const handleUploadDrop = (event) => {
  event.preventDefault()
  isDragOver.value = false
  if (!uploading.value) addUploadFiles(event.dataTransfer?.files)
}

const removeUploadFile = (uid) => {
  if (uploading.value) return
  uploadQueue.value = uploadQueue.value.filter((file) => file.uid !== uid)
}

const renameUploadFile = (file) => {
  if (uploading.value) return
  const nextName = window.prompt('请输入新的文件名', file.name)?.trim()
  if (!nextName) return
  file.name = nextName
  file.format = getFileExtension(nextName) || 'file'
}

const createUploadFile = (item) => {
  if (item.file.name === item.name) return item.file
  return new File([item.file], item.name, {
    type: item.file.type,
    lastModified: item.file.lastModified,
  })
}

const startProgressFallback = (item) => {
  const timer = setInterval(() => {
    if (item.status === 'uploading' && item.progress < 90) {
      item.progress = Math.min(90, item.progress + 4)
    }
  }, 180)
  uploadProgressTimers.set(item.uid, timer)
}

const stopProgressFallback = (item) => {
  const timer = uploadProgressTimers.get(item.uid)
  if (timer) clearInterval(timer)
  uploadProgressTimers.delete(item.uid)
}

const handleUpload = async () => {
  if (uploading.value) return

  const pendingFiles = uploadQueue.value.filter((file) => file.status === 'ready')
  if (!pendingFiles.length) return ElMessage.warning('请先选择要上传的文件')

  uploading.value = true
  let successCount = 0
  let failureCount = 0

  for (const item of pendingFiles) {
    item.status = 'uploading'
    item.progress = 0
    item.error = ''
    startProgressFallback(item)

    try {
      const resource = await uploadResource(createUploadFile(item), (progress) => {
        item.progress = Math.max(item.progress, progress)
      })
      item.status = 'success'
      item.progress = 100
      successCount += 1
      if (resource?.id) {
        const normalized = normalizeRealResource(resource)
        resources.value = [normalized, ...resources.value.filter((row) => row.id !== normalized.id)]
      }
    } catch (error) {
      item.status = 'error'
      item.error = error?.message || '上传失败，请重试'
      failureCount += 1
    } finally {
      stopProgressFallback(item)
    }
  }

  uploading.value = false
  if (successCount) {
    await loadResources()
    ElMessage.success(`${successCount} 个素材上传成功，已加入个人资源库`)
  }
  if (failureCount) ElMessage.error(`${failureCount} 个文件上传失败，可确认后重新打开弹窗再试`)
}

const confirmUploadDialog = () => {
  if (uploading.value) return
  uploadDialogVisible.value = false
}

const toggleCardSelection = (row) => {
  const selected = selectedRows.value.some((item) => item.id === row.id)
  selectedRows.value = selected
    ? selectedRows.value.filter((item) => item.id !== row.id)
    : [...selectedRows.value, row]
}

const handleAction = async (row, command) => {
  if (!row.id) return ElMessage.info('示例素材暂不支持此操作')
  try {
    if (command === 'edit') return openEditDialog(row)
    if (command === 'permission') return openPermissionDialog(row)
    if (command === 'download') {
      const result = await downloadResource(row.id)
      const url = result?.data?.download_url || result?.download_url
      if (url) window.open(url, '_blank', 'noopener')
    }
    if (command === 'delete') { await deleteResource(row.id); resources.value = resources.value.filter((item) => item.id !== row.id); selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id) }
  } catch { ElMessage.error('操作未成功，请稍后重试') }
}

const unwrapResponse = (response) => response?.data ?? response
const parseEditableList = (value) => parseList(value).join(', ')
const normalizeEditableList = (value) => parseList(value)
const toJsonList = (value) => JSON.stringify(Array.isArray(value) ? value : normalizeEditableList(value))

const openEditDialog = (row) => {
  editingRow.value = row
  editForm.value = { file_name: row.name, description: row.description || '', categories: normalizeEditableList(row.raw?.categories), tags: normalizeEditableList(row.raw?.tags) }
  editDialogVisible.value = true
}

const submitEdit = async () => {
  if (!editForm.value.file_name.trim()) return ElMessage.warning('请输入资源名称')
  saving.value = true
  try {
    const updated = unwrapResponse(await updateResource(editingRow.value.id, {
      file_name: editForm.value.file_name.trim(), description: editForm.value.description.trim(),
      categories: toJsonList(editForm.value.categories), tags: toJsonList(editForm.value.tags),
    }))
    resources.value = resources.value.map((item) => item.id === editingRow.value.id ? normalizeRealResource(updated) : item)
    editDialogVisible.value = false
    ElMessage.success('资源信息已更新')
  } catch (error) { ElMessage.error(error?.message || '保存失败，请稍后重试') } finally { saving.value = false }
}

const openPermissionDialog = async (row) => {
  editingRow.value = row
  permissionDialogVisible.value = true
  saving.value = true
  try {
    const permission = unwrapResponse(await getResourcePermission(row.id))
    permissionForm.value = { access_type: permission.access_type || 'private', authorized_users: parseEditableList(permission.authorized_users), allow_ai: Number(permission.allow_ai) === 1 }
  } catch (error) {
    permissionDialogVisible.value = false
    ElMessage.error(error?.message || '无法读取资源权限')
  } finally { saving.value = false }
}

const submitPermission = async () => {
  saving.value = true
  try {
    const updated = unwrapResponse(await setResourcePermission(editingRow.value.id, {
      access_type: permissionForm.value.access_type, authorized_users: toJsonList(permissionForm.value.authorized_users), allow_ai: permissionForm.value.allow_ai ? 1 : 0,
    }))
    resources.value = resources.value.map((item) => item.id === editingRow.value.id ? normalizeRealResource(updated) : item)
    permissionDialogVisible.value = false
    ElMessage.success('资源权限已更新')
  } catch (error) { ElMessage.error(error?.message || '权限设置失败，请稍后重试') } finally { saving.value = false }
}

const openBatchDialog = () => {
  if (!selectedRows.value.length) return ElMessage.warning('请先选择资源')
  batchForm.value = { action: 'delete', target: '' }
  batchDialogVisible.value = true
}

const submitBatchAction = async () => {
  if (batchForm.value.action !== 'delete' && !batchForm.value.target.trim()) return ElMessage.warning('请输入目标分类或目录')
  saving.value = true
  try {
    // API-42 的 Java DTO 将 resource_ids 定义为 String，内容可传 JSON 数组字符串。
    // 保持数字 ID，避免把表格行对象或显示文本带入请求体。
    await batchResourceAction({ idempotent_key: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`, action: batchForm.value.action, resource_ids: JSON.stringify(selectedRows.value.map((row) => Number(row.id)).filter(Number.isFinite)), target: batchForm.value.target.trim() || undefined })
    batchDialogVisible.value = false
    selectedRows.value = []
    await loadResources()
    ElMessage.success('批量操作已提交')
  } catch (error) { ElMessage.error(error?.message || '批量操作失败，请稍后重试') } finally { saving.value = false }
}

const loadTaxonomy = async () => {
  taxonomyLoading.value = true
  try {
    const [categoryResult, tagResult] = await Promise.all([listResourceCategories(), listResourceTags()])
    categories.value = Array.isArray(unwrapResponse(categoryResult)) ? unwrapResponse(categoryResult) : []
    tags.value = Array.isArray(unwrapResponse(tagResult)) ? unwrapResponse(tagResult) : []
  } catch (error) {
    ElMessage.error(error?.message || '词典加载失败，请稍后重试')
  } finally { taxonomyLoading.value = false }
}

const resetTaxonomyForm = () => {
  taxonomyEditing.value = null
  taxonomyForm.value = { name: '', color: '', sort_order: 1000 }
}

const openTaxonomyDialog = (tab = 'category') => {
  taxonomyTab.value = tab
  taxonomyDialogVisible.value = true
  resetTaxonomyForm()
  void loadTaxonomy()
}

const editTaxonomy = (item) => {
  if (!item.managed || !item.id) return ElMessage.info('资源中已有的未管理词条只能直接使用，不能编辑')
  taxonomyEditing.value = item
  taxonomyForm.value = { name: item.name, color: item.color || '', sort_order: Number(item.sort_order) || 1000 }
}

const saveTaxonomy = async () => {
  const name = taxonomyForm.value.name.trim()
  if (!name) return ElMessage.warning(`请输入${taxonomyTypeLabel.value}名称`)
  taxonomySaving.value = true
  try {
    const payload = { name, color: taxonomyForm.value.color.trim() || undefined, sort_order: Number(taxonomyForm.value.sort_order) || 1000 }
    if (taxonomyEditing.value) {
      if (taxonomyTab.value === 'category') await updateResourceCategory(taxonomyEditing.value.id, payload)
      else await updateResourceTag(taxonomyEditing.value.id, payload)
      ElMessage.success(`${taxonomyTypeLabel.value}已更新`)
    } else {
      if (taxonomyTab.value === 'category') await createResourceCategory(payload)
      else await createResourceTag(payload)
      ElMessage.success(`${taxonomyTypeLabel.value}已创建`)
    }
    resetTaxonomyForm()
    await loadTaxonomy()
  } catch (error) { ElMessage.error(error?.message || `${taxonomyTypeLabel.value}保存失败，请稍后重试`) } finally { taxonomySaving.value = false }
}

const removeTaxonomy = async (item) => {
  if (!item.managed || !item.id) return ElMessage.info('未管理词条不能删除')
  if (!window.confirm(`确定删除${taxonomyTypeLabel.value}“${item.name}”吗？已有资源中的词条不会被清除。`)) return
  taxonomySaving.value = true
  try {
    if (taxonomyTab.value === 'category') await deleteResourceCategory(item.id)
    else await deleteResourceTag(item.id)
    if (taxonomyEditing.value?.id === item.id) resetTaxonomyForm()
    await loadTaxonomy()
    ElMessage.success(`${taxonomyTypeLabel.value}已删除`)
  } catch (error) { ElMessage.error(error?.message || `${taxonomyTypeLabel.value}删除失败，请稍后重试`) } finally { taxonomySaving.value = false }
}

const loadIndexOverview = async () => {
  indexOverview.value = unwrapResponse(await getResourceIndexOverview()) || {}
}

const loadIndexResources = async () => {
  const params = { limit: 100, offset: 0 }
  if (indexAvailable.value !== '') params.available = indexAvailable.value === 'true'
  const result = unwrapResponse(await listResourceIndexResources(params)) || {}
  indexResources.value = Array.isArray(result.items) ? result.items : []
  indexResourceTotal.value = Number(result.total) || indexResources.value.length
}

const loadIndexLogs = async () => {
  const result = unwrapResponse(await listResourceIndexLogs({ limit: 50, offset: 0 })) || {}
  indexLogs.value = Array.isArray(result.items) ? result.items : []
  indexLogTotal.value = Number(result.total) || indexLogs.value.length
}

const loadIndexPanel = async () => {
  indexLoading.value = true
  try {
    await Promise.all([loadIndexOverview(), loadIndexResources(), loadIndexLogs()])
  } catch (error) {
    ElMessage.error(error?.message || '知识库索引数据加载失败，请稍后重试')
  } finally { indexLoading.value = false }
}

const openIndexDialog = () => {
  indexDialogVisible.value = true
  indexTab.value = 'overview'
  void loadIndexPanel()
}

const resourceIndexPayload = (row) => {
  const raw = row?.raw || row || {}
  const resourceId = raw.id ?? row?.id
  const title = raw.file_name || row?.name
  if (!resourceId || !title || !raw.file_url) return null
  return {
    source_type: raw.source_type === 'public' ? 'public' : 'personal',
    resource_id: String(resourceId),
    title,
    file_url: raw.file_url,
    file_type: String(raw.file_type || '').toLowerCase() || undefined,
    file_size: Number(raw.file_size) || undefined,
    uploaded_by: raw.user_id ? String(raw.user_id) : undefined,
    owner_user_id: raw.user_id ? String(raw.user_id) : undefined,
    available: raw.status !== 0,
    allow_ai: Number(raw.allow_ai) === 1,
    metadata: {
      title,
      source: 'teacher_resource_library',
      source_type: raw.source_type === 'public' ? 'public' : 'personal',
      resource_id: String(resourceId),
      file_url: raw.file_url,
      file_type: raw.file_type || undefined,
      file_size: Number(raw.file_size) || undefined,
      categories: parseList(raw.categories),
      tags: parseList(raw.tags),
      access_type: raw.access_type || 'private',
    },
  }
}

const syncIndexResource = async (row, forceReparse = false) => {
  const payload = resourceIndexPayload(row)
  if (!payload) return ElMessage.warning('该资源缺少可供 Python 解析的文件地址，暂时无法同步')
  indexActionLoading.value = true
  try {
    await syncResourceIndex({ ...payload, force_reparse: forceReparse })
    ElMessage.success(forceReparse ? '资源索引已重建' : '资源索引已同步')
    await loadIndexPanel()
  } catch (error) { ElMessage.error(error?.message || '资源索引同步失败，请稍后重试') } finally { indexActionLoading.value = false }
}

const bootstrapIndex = async (forceReparse = false) => {
  const payloads = resources.value.map((row) => resourceIndexPayload(row)).filter(Boolean)
  if (!payloads.length) return ElMessage.warning('当前资源列表没有可同步的文件')
  indexActionLoading.value = true
  try {
    const result = unwrapResponse(await bootstrapResourceIndex({ resources: payloads, force_reparse: forceReparse })) || {}
    ElMessage.success(`${forceReparse ? '重建' : '同步'}完成：${result.indexed || 0} 个已处理，${result.skipped || 0} 个跳过，${result.failed || 0} 个失败`)
    await loadIndexPanel()
  } catch (error) { ElMessage.error(error?.message || '批量索引操作失败，请稍后重试') } finally { indexActionLoading.value = false }
}

const removeIndex = async (row) => {
  if (!row?.source_type || !row?.resource_id) return
  if (!window.confirm(`确定删除“${row.title || row.resource_key}”的知识库索引吗？`)) return
  indexActionLoading.value = true
  try {
    await deleteResourceIndex(row.source_type, row.resource_id)
    indexResources.value = indexResources.value.filter((item) => item.resource_key !== row.resource_key)
    indexResourceTotal.value = Math.max(0, indexResourceTotal.value - 1)
    await loadIndexOverview()
    ElMessage.success('索引已删除，原始资源不会受到影响')
  } catch (error) { ElMessage.error(error?.message || '索引删除失败，请稍后重试') } finally { indexActionLoading.value = false }
}

const runIndexSearch = async () => {
  const query = indexSearchQuery.value.trim()
  if (!query) return ElMessage.warning('请输入要检索的内容')
  indexSearchLoading.value = true
  try {
    const result = unwrapResponse(await searchResourceIndex({ query, resource_ids: [], limit: 12000, top_k: 8 })) || {}
    indexSearchResults.value = Array.isArray(result.matches) ? result.matches : []
  } catch (error) { ElMessage.error(error?.message || '索引检索失败，请稍后重试') } finally { indexSearchLoading.value = false }
}

onMounted(() => {
  void loadResources()
  void loadTaxonomy()
  mobileMediaQuery = window.matchMedia('(max-width: 767.98px)')
  isMobile.value = mobileMediaQuery.matches
  mobileMediaQuery.addEventListener('change', handleMobileMediaChange)
})
onBeforeUnmount(() => {
  mobileMediaQuery?.removeEventListener('change', handleMobileMediaChange)
  clearUploadProgressTimers()
})
</script>

<template>
  <div class="page-wrap">
    <header class="page-heading">
      <div><p class="page-kicker">个人教学资产</p><h1>个人资源库</h1><p>统一管理私有素材，并决定哪些内容可供智能体引用。</p></div>
      <div class="heading-actions">
        <el-button :icon="Setting" @click="openIndexDialog">知识库索引</el-button>
        <el-button type="primary" :icon="Upload" @click="startUpload">上传素材</el-button>
      </div>
    </header>

    <section class="stat-strip" aria-label="资源库概览">
      <article v-for="stat in resourceStats" :key="stat.label">
        <span>{{ stat.label }}</span><strong>{{ stat.value }}</strong><small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="resource-layout">
      <aside class="folder-panel">
        <div class="panel-title"><span>分类目录</span><el-button text circle :icon="Plus" aria-label="管理分类" @click="openTaxonomyDialog('category')" /></div>
        <button v-for="folder in resourceFolders" :key="folder" :class="{ active: activeFolder === folder }" @click="activeFolder = folder">
          <el-icon><Folder /></el-icon><span>{{ folder }}</span>
        </button>
        <div class="privacy-note"><el-icon><Lock /></el-icon><p><strong>默认私有</strong><br>仅你和授权的智能体可以访问。</p></div>
      </aside>

      <div class="resource-content">
        <el-select
          v-if="isMobile"
          v-model="activeFolder"
          class="mobile-folder-select"
          aria-label="选择分类目录"
        >
          <el-option v-for="folder in resourceFolders" :key="folder" :label="folder" :value="folder" />
        </el-select>
        <div class="resource-toolbar">
          <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索文件名、课程或标签" clearable />
          <el-select v-model="typeFilter" aria-label="资源类型" clearable placeholder="全部类型"><el-option label="全部类型" value="" /><el-option label="课件" value="ppt" /><el-option label="文档" value="word" /><el-option label="PDF" value="pdf" /><el-option label="图片" value="image" /><el-option label="音视频" value="audio" /></el-select>
          <div class="resource-toolbar-actions">
            <el-button :icon="Setting" @click="openTaxonomyDialog('category')">词典管理</el-button>
            <el-button :icon="Delete" :disabled="selectedRows.length === 0" @click="openBatchDialog">批量管理</el-button>
          </div>
        </div>
        <el-table v-if="!isMobile" v-loading="loading" :data="visibleFiles" @selection-change="selectedRows = $event">
          <el-table-column type="selection" width="42" />
          <el-table-column label="素材" min-width="260">
            <template #default="{ row }">
              <div class="file-cell">
                <span class="file-mark">{{ row.type.slice(0, 1) }}</span>
                <div>
                  <strong>{{ row.name }}</strong>
                  <small>{{ row.course }} · {{ row.size }}</small>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="date" label="更新时间" min-width="120" />
          <el-table-column label="解析状态" width="110"><template #default="{ row }"><el-tag :type="row.status === '已解析' ? 'success' : row.status === '解析中' ? 'warning' : 'info'" effect="light">{{ row.status }}</el-tag></template></el-table-column>
          <el-table-column label="权限" width="108"><template #default="{ row }"><span class="private-label"><el-icon><Lock /></el-icon> {{ row.private ? '私有' : '共享' }}</span></template></el-table-column>
          <el-table-column class-name="resource-action-column" width="54" align="center"><template #default="{ row }"><el-dropdown trigger="click" @command="handleAction(row, $event)"><el-button class="resource-more-button" text circle data-hover-reveal aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="edit"><el-icon><Edit /></el-icon>编辑信息</el-dropdown-item><el-dropdown-item command="permission">权限设置</el-dropdown-item><el-dropdown-item command="download">下载</el-dropdown-item><el-dropdown-item class="resource-danger-menu-item" command="delete" divided><el-icon><Delete /></el-icon>删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column>
        </el-table>
        <div v-if="isMobile" v-loading="loading" class="resource-card-list">
          <el-empty v-if="!visibleFiles.length" description="暂无素材" />
          <article v-for="row in visibleFiles" :key="row.id" class="resource-card">
            <div class="resource-card-main">
              <el-checkbox
                class="resource-card-check"
                :model-value="selectedRows.some((item) => item.id === row.id)"
                aria-label="选择该资源"
                @change="toggleCardSelection(row)"
              />
              <span class="file-mark">{{ row.type.slice(0, 1) }}</span>
              <div class="resource-card-info">
                <strong>{{ row.name }}</strong>
                <small>{{ row.course }} · {{ row.size }} · {{ row.date }}</small>
                <div class="resource-card-meta">
                  <el-tag size="small" :type="row.status === '已解析' ? 'success' : row.status === '解析中' ? 'warning' : 'info'" effect="light">{{ row.status }}</el-tag>
                  <span class="private-label"><el-icon><Lock /></el-icon>{{ row.private ? '私有' : '共享' }}</span>
                </div>
              </div>
            </div>
            <el-dropdown trigger="click" @command="handleAction(row, $event)">
              <el-button class="resource-more-button" text circle data-hover-reveal aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit"><el-icon><Edit /></el-icon>编辑信息</el-dropdown-item>
                  <el-dropdown-item command="permission">权限设置</el-dropdown-item>
                  <el-dropdown-item command="download">下载</el-dropdown-item>
                  <el-dropdown-item class="resource-danger-menu-item" command="delete" divided><el-icon><Delete /></el-icon>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </article>
        </div>
      </div>
    </section>

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传素材"
      width="min(680px, 92vw)"
      align-center
      destroy-on-close
      :close-on-click-modal="!uploading"
      :close-on-press-escape="!uploading"
      :show-close="!uploading"
    >
      <input
        ref="uploadInput"
        class="visually-hidden"
        type="file"
        multiple
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.mp4,.avi,.mov,.mkv,image/*,audio/*,video/*"
        @change="handleUploadInputChange"
      >

      <div
        class="upload-dropzone"
        :class="{ 'is-dragover': isDragOver, 'is-uploading': uploading }"
        @click="openFilePicker"
        @dragenter.prevent="handleUploadDragOver"
        @dragover.prevent="handleUploadDragOver"
        @dragleave.prevent="handleUploadDragLeave"
        @drop.prevent="handleUploadDrop"
      >
        <el-icon :size="42" class="upload-dropzone-icon">
          <Loading v-if="uploading" class="upload-loading-icon" />
          <Upload v-else />
        </el-icon>
        <strong>{{ uploading ? '正在上传文件，请稍候…' : '拖拽文件到这里，或点击选择文件' }}</strong>
        <span>支持 PDF、Word、PPT、TXT、图片、音频和视频，单文件最大 500MB，最多 20 个文件</span>
      </div>

      <section v-if="uploadQueue.length" class="upload-queue" aria-label="待上传文件列表">
        <div class="upload-summary">
          <span>上传进度 · {{ completedUploadCount }}/{{ uploadQueue.length }} 个文件</span>
          <strong>{{ uploadOverallProgress }}%</strong>
        </div>
        <el-progress
          :percentage="uploadOverallProgress"
          :stroke-width="6"
          :show-text="false"
          :status="uploadAllComplete ? 'success' : undefined"
        />

        <div class="upload-file-list">
          <div v-for="file in uploadQueue" :key="file.uid" class="upload-file-item">
            <span class="upload-file-mark">{{ file.format.slice(0, 3).toUpperCase() }}</span>
            <div class="upload-file-info">
              <div class="upload-file-title-row">
                <strong :title="file.name">{{ file.name }}</strong>
                <el-button
                  text
                  size="small"
                  :icon="Edit"
                  :disabled="uploading"
                  aria-label="重命名文件"
                  @click="renameUploadFile(file)"
                />
              </div>
              <el-progress
                v-if="file.status === 'uploading' || file.status === 'success'"
                :percentage="file.progress"
                :stroke-width="4"
                :show-text="false"
                :status="file.status === 'success' ? 'success' : undefined"
              />
              <small v-if="file.status === 'error'" class="upload-error">{{ file.error }}</small>
            </div>
            <span class="upload-file-size">{{ formatFileSize(file.size) }}</span>
            <span
              class="upload-file-status"
              :class="{ 'is-success': file.status === 'success', 'is-error': file.status === 'error' }"
            >
              {{ file.status === 'success' ? '已完成' : file.status === 'uploading' ? `${file.progress}%` : file.status === 'error' ? '失败' : '待上传' }}
            </span>
            <el-button
              text
              circle
              :icon="Delete"
              :disabled="uploading"
              aria-label="移除文件"
              @click="removeUploadFile(file.uid)"
            />
          </div>
        </div>
      </section>

      <template #footer>
        <div class="upload-dialog-footer">
          <el-button :disabled="uploading" @click="uploadDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :disabled="uploading"
            @click="confirmUploadDialog"
          >
            确认
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑资源信息" width="min(520px, 92vw)" align-center destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="资源名称"><el-input v-model="editForm.file_name" maxlength="100" show-word-limit /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        <el-form-item label="分类"><el-select v-model="editForm.categories" multiple filterable allow-create default-first-option placeholder="选择或新增分类" style="width: 100%"><el-option v-for="item in categories" :key="item.id || item.name" :label="item.name" :value="item.name" /></el-select></el-form-item>
        <el-form-item label="标签"><el-select v-model="editForm.tags" multiple filterable allow-create default-first-option placeholder="选择或新增标签" style="width: 100%"><el-option v-for="item in tags" :key="item.id || item.name" :label="item.name" :value="item.name" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="editDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="taxonomyDialogVisible" :title="`${taxonomyTitle}管理`" width="min(720px, 92vw)" align-center destroy-on-close>
      <el-tabs v-model="taxonomyTab" @tab-change="resetTaxonomyForm">
        <el-tab-pane label="分类词典" name="category" />
        <el-tab-pane label="标签词典" name="tag" />
      </el-tabs>
      <div class="taxonomy-editor">
        <el-input v-model="taxonomyForm.name" :placeholder="`输入${taxonomyTypeLabel}名称`" maxlength="80" @keyup.enter="saveTaxonomy" />
        <el-input v-model="taxonomyForm.color" placeholder="颜色（可选，如 #2f6feb）" />
        <el-input-number v-model="taxonomyForm.sort_order" :min="0" :max="99999" controls-position="right" />
        <el-button type="primary" :loading="taxonomySaving" @click="saveTaxonomy">{{ taxonomyEditing ? '保存修改' : `新增${taxonomyTypeLabel}` }}</el-button>
        <el-button v-if="taxonomyEditing" @click="resetTaxonomyForm">取消编辑</el-button>
      </div>
      <el-table v-loading="taxonomyLoading" :data="taxonomyItems" size="small" row-key="name">
        <el-table-column prop="name" :label="taxonomyTypeLabel" min-width="220" />
        <el-table-column prop="count" label="使用资源数" width="110" />
        <el-table-column label="来源" width="100"><template #default="{ row }"><el-tag size="small" :type="row.managed ? 'success' : 'info'">{{ row.managed ? '词典' : '历史值' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" align="right"><template #default="{ row }"><el-button v-if="row.managed" link type="primary" @click="editTaxonomy(row)">编辑</el-button><el-button v-if="row.managed" link type="danger" @click="removeTaxonomy(row)">删除</el-button></template></el-table-column>
      </el-table>
      <p class="dialog-hint">删除词典项不会清除已有资源中的分类或标签；编辑资源时仍可选择历史值或新增词条。</p>
    </el-dialog>

    <el-dialog v-model="indexDialogVisible" title="知识库索引管理" width="min(1000px, 94vw)" align-center destroy-on-close>
      <el-tabs v-model="indexTab">
        <el-tab-pane label="索引概览" name="overview">
          <div v-loading="indexLoading" class="index-panel">
            <div class="index-overview-grid">
              <article><span>索引资源</span><strong>{{ indexOverview.resource_count ?? 0 }}</strong></article>
              <article><span>文本分块</span><strong>{{ indexOverview.chunk_count ?? 0 }}</strong></article>
              <article><span>检索日志</span><strong>{{ indexOverview.retrieval_log_count ?? 0 }}</strong></article>
              <article><span>存储状态</span><strong>{{ indexOverview.postgres_available ? 'PostgreSQL' : '本地回退' }}</strong></article>
            </div>
            <div class="index-panel-heading"><div><strong>索引分组</strong><span>按来源、解析状态和可用状态统计</span></div><el-button :icon="Refresh" :loading="indexLoading" @click="loadIndexPanel">刷新</el-button></div>
            <el-table :data="indexGroups" size="small"><el-table-column prop="source_type" label="来源" width="100" /><el-table-column prop="parse_status" label="解析状态" width="120" /><el-table-column label="可检索" width="100"><template #default="{ row }">{{ row.available ? '是' : '否' }}</template></el-table-column><el-table-column label="允许 AI" width="100"><template #default="{ row }">{{ row.allow_ai ? '是' : '否' }}</template></el-table-column><el-table-column prop="resource_count" label="资源数" width="100" /><el-table-column prop="chunk_count" label="分块数" width="100" /></el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="索引资源" name="resources">
          <div class="index-panel">
            <div class="index-panel-heading"><div><strong>已进入 RAG 的资源</strong><span>共 {{ indexResourceTotal }} 项；删除索引不会删除原始素材</span></div><div class="index-actions"><el-select v-model="indexAvailable" size="small" style="width: 120px" @change="loadIndexResources"><el-option label="全部状态" value="" /><el-option label="可检索" value="true" /><el-option label="不可检索" value="false" /></el-select><el-button size="small" :icon="Refresh" :loading="indexLoading" @click="loadIndexPanel">刷新</el-button><el-button size="small" :loading="indexActionLoading" @click="bootstrapIndex(false)">同步当前资源</el-button><el-button size="small" type="warning" plain :loading="indexActionLoading" @click="bootstrapIndex(true)">重建索引</el-button></div></div>
            <el-table v-loading="indexLoading" :data="indexResources" size="small" max-height="460">
              <el-table-column prop="title" label="资源" min-width="220" show-overflow-tooltip />
              <el-table-column prop="resource_key" label="索引键" width="150" />
              <el-table-column prop="parse_status" label="解析状态" width="110" />
              <el-table-column prop="chunk_count" label="分块" width="70" />
              <el-table-column label="AI" width="70"><template #default="{ row }"><el-tag size="small" :type="row.allow_ai ? 'success' : 'info'">{{ row.allow_ai ? '允许' : '关闭' }}</el-tag></template></el-table-column>
              <el-table-column label="操作" width="170" align="right"><template #default="{ row }"><el-button link type="primary" :loading="indexActionLoading" @click="syncIndexResource({ raw: { id: row.resource_id, file_name: row.title, file_url: row.metadata?.file_url, file_type: row.metadata?.file_type, file_size: row.metadata?.file_size, allow_ai: row.allow_ai, status: row.available ? 1 : 0, user_id: row.metadata?.owner_user_id, categories: row.metadata?.categories, tags: row.metadata?.tags, access_type: row.metadata?.access_type }, id: row.resource_id })">同步</el-button><el-button link type="danger" :loading="indexActionLoading" @click="removeIndex(row)">删除</el-button></template></el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="检索测试" name="search">
          <div class="index-panel">
            <div class="index-search-bar"><el-input v-model="indexSearchQuery" clearable placeholder="输入关键词测试知识库检索，例如：光合作用实验设计" @keyup.enter="runIndexSearch" /><el-button type="primary" :loading="indexSearchLoading" @click="runIndexSearch">开始检索</el-button></div>
            <el-empty v-if="!indexSearchResults.length && !indexSearchLoading" description="输入关键词后查看检索结果" />
            <div v-else class="index-result-list"><article v-for="(item, index) in indexSearchResults" :key="item.chunk_id || `${item.resource_id}-${index}`"><div><strong>#{{ item.rank || index + 1 }} · {{ item.resource_id }}</strong><span>得分 {{ Number(item.score || item.rerank_score || 0).toFixed(3) }} · {{ item.match_type || 'hybrid' }}</span></div><p>{{ item.content }}</p></article></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="检索日志" name="logs">
          <div class="index-panel">
            <div class="index-panel-heading"><div><strong>Python RAG 检索日志</strong><span>共 {{ indexLogTotal }} 条</span></div><el-button :icon="Refresh" :loading="indexLoading" @click="loadIndexLogs">刷新</el-button></div>
            <el-table v-loading="indexLoading" :data="indexLogs" size="small" max-height="460"><el-table-column prop="query" label="查询内容" min-width="260" show-overflow-tooltip /><el-table-column prop="match_count" label="命中" width="70" /><el-table-column prop="top_score" label="最高分" width="90" /><el-table-column prop="search_mode" label="模式" width="140" /><el-table-column prop="latency_ms" label="耗时（ms）" width="100" /><el-table-column label="时间" width="155"><template #default="{ row }">{{ formatUpdatedAt(row.created_at) }}</template></el-table-column></el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="permissionDialogVisible" title="资源权限设置" width="min(480px, 92vw)" align-center destroy-on-close>
      <el-form label-position="top" v-loading="saving">
        <el-form-item label="访问范围"><el-radio-group v-model="permissionForm.access_type"><el-radio value="private">仅自己</el-radio><el-radio value="shared">所有成员</el-radio><el-radio value="authorized">指定成员</el-radio></el-radio-group></el-form-item>
        <el-form-item v-if="permissionForm.access_type === 'authorized'" label="授权用户 ID"><el-input v-model="permissionForm.authorized_users" placeholder="多个用户 ID 请用逗号分隔" /></el-form-item>
        <el-form-item label="允许 AI 引用"><el-switch v-model="permissionForm.allow_ai" active-text="允许" inactive-text="不允许" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitPermission">保存权限</el-button></template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量管理资源" width="min(480px, 92vw)" align-center destroy-on-close>
      <p class="batch-summary">已选择 {{ selectedRows.length }} 个资源</p>
      <el-form label-position="top"><el-form-item label="操作"><el-radio-group v-model="batchForm.action"><el-radio value="delete">批量删除</el-radio><el-radio value="move">移动目录</el-radio><el-radio value="categorize">修改分类</el-radio></el-radio-group></el-form-item><el-form-item v-if="batchForm.action !== 'delete'" :label="batchForm.action === 'move' ? '目标目录' : '目标分类'"><el-input v-model="batchForm.target" /></el-form-item></el-form>
      <template #footer><el-button @click="batchDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitBatchAction">确认操作</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-wrap { width: min(1220px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 56px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; }
.page-kicker { margin: 0 0 6px !important; color: var(--zh-text-theme) !important; font-size: 13px !important; font-weight: 600; }
.page-heading h1 { margin: 0; font-size: 30px; letter-spacing: var(--zh-tracking-tight); }
.page-heading p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 14px; }
.upload-dropzone {
  min-height: 178px;
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
.upload-dropzone:hover, .upload-dropzone.is-dragover {
  border-color: var(--zh-text-theme);
  background: var(--zh-background-option-on);
  box-shadow: inset 0 0 0 1px var(--zh-text-theme);
}
.upload-dropzone.is-uploading { cursor: wait; opacity: .82; }
.upload-dropzone strong { color: var(--zh-text-primary); font-size: 14px; font-weight: 600; }
.upload-dropzone span { color: var(--zh-text-caption); font-size: 12px; text-align: center; }
.upload-dropzone-icon { color: var(--zh-text-theme); }
.upload-loading-icon { animation: resource-upload-spin 1.4s linear infinite; }
.upload-queue { margin-top: 20px; }
.upload-summary { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; color: var(--zh-text-secondary); font-size: 13px; }
.upload-summary strong { color: var(--zh-text-theme); font-family: var(--zh-font-number); font-weight: 600; }
.upload-queue :deep(.el-progress-bar__outer) { background: var(--zh-background-option); }
.upload-file-list { max-height: 250px; margin-top: 12px; overflow: auto; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); }
.upload-file-item { display: flex; align-items: center; gap: 10px; min-height: 66px; padding: 10px 12px; border-bottom: 1px solid var(--zh-line-parting); }
.upload-file-item:last-child { border-bottom: 0; }
.upload-file-mark { width: 38px; height: 38px; display: grid; place-items: center; flex: 0 0 38px; border-radius: 7px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font-size: 10px; font-weight: 700; }
.upload-file-info { min-width: 0; flex: 1; }
.upload-file-title-row { display: flex; align-items: center; gap: 4px; min-width: 0; }
.upload-file-title-row strong { min-width: 0; overflow: hidden; color: var(--zh-text-primary); font-size: 13px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.upload-file-title-row :deep(.el-button) { flex: 0 0 auto; color: var(--zh-text-caption); }
.upload-file-info :deep(.el-progress) { margin-top: 5px; }
.upload-file-size { flex: 0 0 62px; color: var(--zh-text-caption); font-size: 12px; text-align: right; }
.upload-file-status { flex: 0 0 48px; color: var(--zh-text-caption); font-size: 12px; text-align: right; }
.upload-file-status.is-success { color: var(--zh-green); }
.upload-file-status.is-error, .upload-error { color: var(--zh-red); }
.upload-error { display: block; margin-top: 4px; overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.upload-dialog-footer { display: flex; justify-content: flex-end; gap: 10px; }
@keyframes resource-upload-spin { to { transform: rotate(360deg); } }
.stat-strip { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 32px; border-block: 1px solid var(--zh-line-border); }
.stat-strip article { display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; padding: 22px 28px; border-right: 1px solid var(--zh-line-border); }
.stat-strip article:last-child { border: 0; }
.stat-strip span, .stat-strip small { color: var(--zh-text-caption); font-size: 12px; }
.stat-strip strong { grid-row: 1 / 3; grid-column: 2; align-self: center; font: 600 26px var(--zh-font-number); }
.resource-layout { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 24px; margin-top: 28px; }
.folder-panel { padding: 14px; border-radius: var(--zh-radius12); background: var(--zh-background-pc-sidebar); }
.panel-title { display: flex; align-items: center; justify-content: space-between; padding: 0 8px 8px; color: var(--zh-text-caption); font-size: 12px; }
.folder-panel > button { width: 100%; display: flex; align-items: center; gap: 9px; padding: 10px; border: 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: transparent; cursor: pointer; text-align: left; }
.folder-panel > button:hover, .folder-panel > button.active { color: var(--zh-text-theme); background: var(--zh-background-option-on); }
.privacy-note { display: flex; gap: 8px; margin-top: 20px; padding: 12px; border-top: 1px solid var(--zh-line-border); color: var(--zh-text-caption); font-size: 11px; }
.privacy-note p { margin: 0; line-height: 1.6; }.privacy-note strong { color: var(--zh-text-secondary); }
.resource-content { min-width: 0; }.resource-toolbar { display: grid; grid-template-columns: minmax(240px, 1fr) 140px auto; gap: 10px; margin-bottom: 16px; }
.heading-actions, .resource-toolbar-actions, .index-actions { display: flex; align-items: center; gap: 8px; }
.resource-toolbar-actions { justify-content: flex-end; }
.file-cell { display: flex; align-items: center; gap: 12px; }.file-cell > div { min-width: 0; display: flex; flex-direction: column; }
.file-cell strong { overflow: hidden; color: var(--zh-text-primary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.file-cell small { margin-top: 3px; color: var(--zh-text-caption); }
.file-mark { width: 34px; height: 38px; display: grid; place-items: center; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font-weight: 700; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.private-label { display: inline-flex; align-items: center; gap: 4px; color: var(--zh-text-secondary); font-size: 12px; }
.batch-summary { margin: 0 0 18px; color: var(--zh-text-secondary); }
:deep(.resource-action-column .cell) { overflow: hidden; padding: 0 4px; text-align: center; }
:deep(.resource-action-column .el-dropdown), :deep(.resource-more-button) { display: inline-flex; max-width: 100%; }
:deep(.resource-more-button) { width: 32px; height: 32px; padding: 0; }
:global(.resource-danger-menu-item) { color: var(--zh-red) !important; }
:global(.resource-danger-menu-item:hover), :global(.resource-danger-menu-item:focus) { color: var(--zh-danger-clicked) !important; background: var(--zh-danger-background) !important; }
:deep(.el-table) { --el-table-border-color: var(--zh-line-parting); --el-table-header-bg-color: var(--zh-background-light); border-radius: var(--zh-radius12); }
.taxonomy-editor { display: grid; grid-template-columns: minmax(160px, 1fr) minmax(180px, 1fr) 130px auto auto; align-items: center; gap: 8px; margin: 6px 0 18px; }
.dialog-hint { margin: 14px 0 0; color: var(--zh-text-caption); font-size: 12px; }
.index-panel { min-height: 180px; }
.index-overview-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 22px; }
.index-overview-grid article { display: grid; gap: 7px; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.index-overview-grid span, .index-panel-heading span { color: var(--zh-text-caption); font-size: 12px; }
.index-overview-grid strong { color: var(--zh-text-primary); font: 600 21px var(--zh-font-number); }
.index-panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 4px 0 12px; }
.index-panel-heading > div:first-child { display: grid; gap: 4px; min-width: 0; }
.index-panel-heading strong { color: var(--zh-text-primary); font-size: 14px; }
.index-actions { flex-wrap: wrap; justify-content: flex-end; }
.index-search-bar { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; margin: 8px 0 18px; }
.index-result-list { display: grid; gap: 10px; max-height: 460px; overflow: auto; }
.index-result-list article { padding: 12px 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.index-result-list article > div { display: flex; justify-content: space-between; gap: 12px; }
.index-result-list strong { color: var(--zh-text-primary); font-size: 13px; }
.index-result-list span { color: var(--zh-text-caption); font-size: 11px; }
.index-result-list p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.65; white-space: pre-wrap; }
/* 平板（768–1023.98）与手机（<768）共用：布局收单列、知识库 header 转单列 */
@media (max-width: 1023.98px) { .page-heading { align-items: flex-start; flex-direction: column; }.resource-layout { grid-template-columns: 1fr; }.stat-strip { grid-template-columns: repeat(2, 1fr); }.stat-strip article:nth-child(2n) { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr 1fr; }.resource-toolbar > .el-input { grid-column: 1 / -1; }.resource-toolbar-actions { justify-content: flex-start; flex-wrap: wrap; }.taxonomy-editor { grid-template-columns: 1fr 1fr; }.taxonomy-editor .el-button:last-child { grid-column: 2; }.index-overview-grid { grid-template-columns: repeat(2, 1fr); }.index-panel-heading { align-items: flex-start; flex-direction: column; }.index-actions { justify-content: flex-start; } }
/* 平板档：分类面板收为 76px 图标态（点击仍可切换分类，入口不丢） */
@media (min-width: 768px) and (max-width: 1023.98px) { .folder-panel { width: 76px; padding: 12px 6px; }.panel-title { justify-content: center; padding: 0 0 8px; }.panel-title > span { display: none; }.folder-panel > button { flex-direction: column; gap: 4px; padding: 8px 2px; }.folder-panel > button .el-icon { display: none; }.folder-panel > button > span { display: block; max-width: 100%; overflow: hidden; font-size: 11px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }.privacy-note { display: none; } }
/* 手机档：分类面板隐藏（顶部 el-select 承载入口）、主表格切换为卡片列表 */
@media (max-width: 767.98px) { .folder-panel { display: none; }.stat-strip { grid-template-columns: 1fr; }.stat-strip article { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr; }.resource-toolbar > .el-input { grid-column: auto; }.mobile-folder-select { width: 100%; margin-bottom: 12px; }.resource-card-list { display: grid; gap: 10px; min-height: 120px; }.resource-card { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-light); }.resource-card-main { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }.resource-card-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }.resource-card-info strong { overflow: hidden; color: var(--zh-text-primary); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }.resource-card-info small { color: var(--zh-text-caption); font-size: 12px; }.resource-card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }.resource-card :deep(.resource-more-button) { width: 40px; height: 40px; flex: 0 0 auto; }.taxonomy-editor { grid-template-columns: 1fr; }.taxonomy-editor .el-button:last-child { grid-column: auto; }.index-overview-grid { grid-template-columns: 1fr; }.index-search-bar { grid-template-columns: 1fr; }.index-result-list article > div { align-items: flex-start; flex-direction: column; gap: 4px; } }
</style>
