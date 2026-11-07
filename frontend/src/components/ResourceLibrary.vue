<!--
  [数据交互说明]
  - 导入: 资源库演示数据、Element Plus 组件与图标
  - 输出: 教师个人资源库页面
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Edit, Filter, Folder, Loading, Lock, MoreFilled, Plus, Refresh, Search, Setting, Upload } from '@element-plus/icons-vue'
import { downloadFile } from '../utils/api'
import { useUserStore } from '../storage/user'
import { isAndroidApp, isBackendDownload, resolveDownloadUrl, saveAndroidDownload } from '../utils/fileDownload'
import { resourceIndexStatus, indexSyncResult } from '../utils/resourceIndexStatus'
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
const resourcesError = ref('')
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
const mobileFiltersOpen = ref(false)
const mobileBatchMode = ref(false)
const mobileOverviewOpen = ref(false)
const mobileResource = ref(null)
const mobileResourceOpen = ref(false)
const handleMobileResourceMenu = command => {
  if (command === 'overview') mobileOverviewOpen.value = true
  if (command === 'index') openIndexDialog()
  if (command === 'taxonomy') openTaxonomyDialog('category')
  if (command === 'batch') { mobileBatchMode.value = !mobileBatchMode.value; selectedRows.value = [] }
}
let mobileMediaQuery = null
const handleMobileMediaChange = (event) => {
  isMobile.value = event.matches
  // 表格与卡片的选择状态不互通，断点切换时清空，避免批量管理作用于不可见选择
  selectedRows.value = []
}

const MAX_UPLOAD_FILES = 20
const MAX_UPLOAD_FILE_SIZE = 500 * 1024 * 1024
const SUPPORTED_UPLOAD_EXTENSIONS = new Set([
  'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'md', 'csv', 'srt', 'vtt', 'ass', 'zip',
  'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp3', 'wav', 'm4a', 'aac', 'ogg',
  'mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv', 'flv',
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
  status: resourceIndexStatus(item).label,
  statusType: resourceIndexStatus(item).type,
  indexError: resourceIndexStatus(item).error,
  aiUsable: resourceIndexStatus(item).usable,
  private: item.access_type !== 'shared',
  description: item.description || '',
  raw: item,
})

const resourceStats = computed(() => {
  const totalSize = resources.value.reduce((sum, item) => sum + item.fileSize, 0)
  const aiAvailable = resources.value.filter((item) => item.aiUsable).length
  return [
    { label: '全部素材', value: resourcesError.value ? '—' : String(resourceTotal.value), detail: `当前已加载 ${resources.value.length} 项` },
    { label: '可供 AI 引用', value: resourcesError.value ? '—' : String(aiAvailable), detail: '当前已加载素材中，已解析且允许 AI 使用的数量' },
    { label: '已加载空间', value: resourcesError.value ? '—' : formatFileSize(totalSize), detail: '当前列表资源总大小' },
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

const resourceTypeGroups = {
  ppt: ['PPT', 'PPTX'],
  word: ['DOC', 'DOCX', 'TXT', 'MD', 'XLS', 'XLSX', 'CSV'],
  pdf: ['PDF'],
  image: ['JPG', 'JPEG', 'PNG', 'GIF', 'BMP', 'WEBP'],
  audio: ['MP3', 'WAV', 'M4A', 'AAC', 'OGG', 'MP4', 'AVI', 'MOV', 'MKV', 'WEBM', 'WMV', 'FLV', 'SRT', 'VTT', 'ASS'],
}
const matchesResourceType = (file, filter) => !filter || (resourceTypeGroups[filter] || [filter.toUpperCase()]).includes(file.type)

const visibleFiles = computed(() => resources.value.filter((file) => (
  (activeFolder.value === '全部素材' || file.course.split(' · ').includes(activeFolder.value)) &&
  matchesResourceType(file, typeFilter.value) &&
  file.name.toLowerCase().includes(keyword.value.toLowerCase())
)))
watch([keyword, activeFolder, typeFilter], () => { selectedRows.value = [] })
const clearResourceFilters = () => {
  keyword.value = ''
  activeFolder.value = '全部素材'
  typeFilter.value = ''
}
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

let resourceRequestSeq = 0
let resourceDisposed = false
const loadResources = async () => {
  if (resourceDisposed) return
  const sequence = ++resourceRequestSeq
  loading.value = true
  resourcesError.value = ''
  selectedRows.value = []
  try {
    const result = await listResources({ keyword: keyword.value || undefined, page: 1, size: 50 })
    if (resourceDisposed || sequence !== resourceRequestSeq) return
    const records = result?.data?.records || result?.data?.list || result?.data?.items || result?.records || []
    resources.value = records.map(normalizeRealResource)
    resourceTotal.value = Number(result?.data?.total ?? result?.total ?? resources.value.length)
  } catch {
    if (resourceDisposed || sequence !== resourceRequestSeq) return
    resourcesError.value = '素材加载失败，请检查登录状态或网络连接后重试。'
  } finally { if (!resourceDisposed && sequence === resourceRequestSeq) loading.value = false }
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

  const pendingFiles = uploadQueue.value.filter((file) => file.status === 'ready' || file.status === 'error')
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
  if (failureCount) ElMessage.error(`${failureCount} 个文件上传失败，请点击“重试失败文件”`)
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
      if (isAndroidApp()) {
        if (!url) return ElMessage.warning('服务端暂未返回下载链接')
        const downloadUrl = resolveDownloadUrl(url)
        const token = useUserStore().token
        const authorization = isBackendDownload(downloadUrl) && downloadUrl.pathname.startsWith('/api/v1/resources/') && token
          ? `Bearer ${token}` : undefined
        if (await saveAndroidDownload(downloadUrl, row.file_name || '教学资源', authorization)) ElMessage.success('资源已保存')
      } else if (url?.startsWith('/api/v1/resources/')) await downloadFile(url, row.file_name)
      else if (url) window.open(url, '_blank', 'noopener')
    }
    if (command === 'delete') { await deleteResource(row.id); resources.value = resources.value.filter((item) => item.id !== row.id); selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id) }
  } catch (error) {
    const message = isAndroidApp() && command === 'download' ? error?.message : undefined
    ElMessage.error(message || '操作未成功，请稍后重试')
  }
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
    const { complete } = indexSyncResult(await syncResourceIndex({ ...payload, force_reparse: forceReparse }))
    if (complete) ElMessage.success(forceReparse ? '资源索引已重建' : '资源索引已同步')
    else ElMessage.info('同步请求已提交，请刷新查看实际解析状态')
    await loadIndexPanel()
  } catch (error) { ElMessage.error(error?.message || '资源索引同步失败，请稍后重试') } finally { indexActionLoading.value = false }
}

const syncIndexedResource = (row) => syncIndexResource({
  id: row.resource_id,
  raw: {
    id: row.resource_id,
    source_type: row.source_type ?? row.metadata?.source_type,
    file_name: row.title,
    file_url: row.metadata?.file_url,
    file_type: row.metadata?.file_type,
    file_size: row.metadata?.file_size,
    allow_ai: row.allow_ai,
    status: row.available ? 1 : 0,
    user_id: row.metadata?.owner_user_id,
    categories: row.metadata?.categories,
    tags: row.metadata?.tags,
    access_type: row.metadata?.access_type,
  },
})

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

const indexResultTimeRange = (item) => {
  const start = item?.start_timestamp || item?.metadata?.start_timestamp
  const end = item?.end_timestamp || item?.metadata?.end_timestamp
  return start ? `${start}${end ? `–${end}` : ''}` : ''
}

onMounted(() => {
  void loadResources()
  void loadTaxonomy()
  mobileMediaQuery = window.matchMedia('(max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse)')
  isMobile.value = mobileMediaQuery.matches
  mobileMediaQuery.addEventListener('change', handleMobileMediaChange)
})
onBeforeUnmount(() => {
  resourceDisposed = true
  resourceRequestSeq += 1
  mobileMediaQuery?.removeEventListener('change', handleMobileMediaChange)
  clearUploadProgressTimers()
})
</script>

<template>
  <div class="page-wrap" :class="{ 'mobile-resource-page': isMobile }">
    <header class="page-heading">
      <div v-if="!isMobile"><p class="page-kicker">个人教学资产</p><h1>个人资源库</h1><p>统一管理私有素材，并决定哪些内容可供智能体引用。</p></div>
      <div class="heading-actions">
        <el-button v-if="!isMobile" :icon="Setting" @click="openIndexDialog">知识库索引</el-button>
        <el-button type="primary" :icon="Upload" @click="startUpload">上传素材</el-button>
        <el-dropdown v-if="isMobile" trigger="click" @command="handleMobileResourceMenu"><el-button class="mobile-icon-button" aria-label="资源更多功能" :icon="MoreFilled" /><template #dropdown><el-dropdown-menu><el-dropdown-item command="overview">资源概览</el-dropdown-item><el-dropdown-item command="index">知识库索引</el-dropdown-item><el-dropdown-item command="taxonomy">分类与标签</el-dropdown-item><el-dropdown-item command="batch">{{ mobileBatchMode ? '退出批量选择' : '批量选择' }}</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
      </div>
    </header>

    <section v-if="!isMobile" class="stat-strip" aria-label="资源库概览">
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
        <div class="resource-toolbar">
          <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索素材" clearable aria-label="搜索素材名称"><template v-if="isMobile" #append><el-button class="mobile-search-action" @click="keyword = keyword.trim()">搜索</el-button></template></el-input>
          <el-button v-if="isMobile" class="mobile-icon-button" :type="mobileFiltersOpen ? 'primary' : undefined" :plain="mobileFiltersOpen" :icon="Filter" aria-label="筛选资源" :aria-expanded="mobileFiltersOpen" @click="mobileFiltersOpen = !mobileFiltersOpen" />
          <el-select
            v-if="isMobile && mobileFiltersOpen"
            v-model="activeFolder"
            class="mobile-folder-select"
            aria-label="选择分类目录"
          >
            <el-option v-for="folder in resourceFolders" :key="folder" :label="folder" :value="folder" />
          </el-select>
          <el-select v-if="!isMobile || mobileFiltersOpen" v-model="typeFilter" aria-label="资源类型" clearable placeholder="全部类型"><el-option label="全部类型" value="" /><el-option label="课件" value="ppt" /><el-option label="文档" value="word" /><el-option label="PDF" value="pdf" /><el-option label="图片" value="image" /><el-option label="音视频" value="audio" /></el-select>
          <div class="resource-toolbar-actions">
            <el-button v-if="!isMobile" :icon="Setting" @click="openTaxonomyDialog('category')">词典管理</el-button>
            <el-button v-if="isMobile && mobileFiltersOpen" text @click="clearResourceFilters">重置筛选</el-button>
            <el-button v-if="isMobile && mobileBatchMode" text @click="mobileBatchMode = false; selectedRows = []">退出多选</el-button>
            <el-button v-if="!isMobile || selectedRows.length" :icon="Delete" :disabled="selectedRows.length === 0" @click="openBatchDialog">批量管理{{ isMobile ? `（${selectedRows.length}）` : '' }}</el-button>
          </div>
        </div>
        <div v-if="isMobile" class="mobile-list-heading">
          <strong>{{ mobileBatchMode ? '选择素材' : '我的素材' }}</strong>
          <span>{{ resourcesError ? '加载失败' : `当前显示 ${visibleFiles.length} 项${selectedRows.length ? ` · 已选 ${selectedRows.length} 项` : ''}` }}</span>
        </div>
        <div v-if="resourcesError && !isMobile" class="resource-load-error" role="alert"><span>{{ resourcesError }}</span><el-button type="primary" plain @click="loadResources">重试</el-button></div>
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
          <el-table-column label="解析状态" min-width="120"><template #default="{ row }"><el-tooltip :content="row.indexError || row.status" placement="top"><el-tag :type="row.statusType" effect="light">{{ row.status }}</el-tag></el-tooltip></template></el-table-column>
          <el-table-column label="权限" width="108"><template #default="{ row }"><span class="private-label"><el-icon><Lock /></el-icon> {{ row.private ? '私有' : '共享' }}</span></template></el-table-column>
          <el-table-column class-name="resource-action-column" width="54" align="center"><template #default="{ row }"><el-dropdown trigger="click" @command="handleAction(row, $event)"><el-button class="resource-more-button" text circle data-hover-reveal aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="edit"><el-icon><Edit /></el-icon>编辑信息</el-dropdown-item><el-dropdown-item command="permission">权限设置</el-dropdown-item><el-dropdown-item command="download">下载</el-dropdown-item><el-dropdown-item class="resource-danger-menu-item" command="delete" divided><el-icon><Delete /></el-icon>删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column>
        </el-table>
        <div v-if="isMobile" class="resource-card-list" aria-live="polite">
          <template v-if="loading">
            <div v-for="index in 3" :key="index" class="resource-card resource-card-skeleton" aria-hidden="true"><span class="skeleton-mark" /><span class="skeleton-lines"><i /><i /></span></div>
          </template>
          <div v-else-if="resourcesError" class="resource-load-error" role="alert"><span>{{ resourcesError }}</span><el-button type="primary" plain @click="loadResources">重试加载</el-button></div>
          <div v-else-if="!visibleFiles.length" class="resource-empty-state">
            <el-empty :description="resources.length ? '没有匹配的素材' : '还没有上传素材'" />
            <el-button v-if="resources.length" type="primary" plain @click="clearResourceFilters">清除筛选</el-button>
            <el-button v-else type="primary" :icon="Upload" @click="startUpload">上传第一份素材</el-button>
          </div>
          <template v-else><article v-for="row in visibleFiles" :key="row.id" class="resource-card">
            <div class="resource-card-main">
              <el-checkbox
                v-if="mobileBatchMode"
                class="resource-card-check"
                :model-value="selectedRows.some((item) => item.id === row.id)"
                :aria-label="`选择${row.name}`"
                @change="toggleCardSelection(row)"
              />
              <button class="resource-card-open" type="button" :aria-label="`查看${row.name}`" @click="mobileResource = row; mobileResourceOpen = true"><div class="resource-card-info">
                <strong :title="row.name">{{ row.name }}</strong>
                <small>{{ row.course }} · {{ row.size }}</small>
                <div v-if="row.indexError" class="resource-card-meta">
                  <el-tooltip :content="row.indexError || row.status" placement="top"><el-tag size="small" :type="row.statusType" effect="light">{{ row.status }}</el-tag></el-tooltip>
                </div>
              </div></button>
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
          </template>
        </div>
      </div>
    </section>

    <el-dialog v-model="mobileOverviewOpen" title="资源概览" class="resource-dialog"><dl class="mobile-info-list"><div v-for="stat in resourceStats" :key="stat.label"><dt>{{ stat.label }}</dt><dd>{{ stat.value }}</dd></div></dl></el-dialog>
    <el-dialog v-model="mobileResourceOpen" title="素材详情" class="resource-dialog"><template v-if="mobileResource"><h2 class="mobile-detail-title">{{ mobileResource.name }}</h2><dl class="mobile-info-list"><div><dt>课程</dt><dd>{{ mobileResource.course }}</dd></div><div><dt>大小</dt><dd>{{ mobileResource.size }}</dd></div><div><dt>更新</dt><dd>{{ mobileResource.date }}</dd></div><div><dt>权限</dt><dd>{{ mobileResource.private ? '私有' : '共享' }}</dd></div><div><dt>索引状态</dt><dd>{{ mobileResource.status }}</dd></div></dl><p v-if="mobileResource.indexError" class="mobile-inline-error" role="status">{{ mobileResource.indexError }}</p></template><template #footer><el-button @click="mobileResourceOpen = false">关闭</el-button><el-button type="primary" @click="handleAction(mobileResource, 'download')">下载素材</el-button></template></el-dialog>

    <el-dialog
      v-model="uploadDialogVisible"
      class="resource-dialog"
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
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.csv,.srt,.vtt,.ass,.zip,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp3,.wav,.m4a,.aac,.ogg,.mp4,.avi,.mov,.mkv,.webm,.wmv,.flv,image/*,audio/*,video/*"
        @change="handleUploadInputChange"
      >

      <button
        type="button"
        :disabled="uploading"
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
        <strong>{{ uploading ? '正在上传文件，请稍候…' : isMobile ? '点击选择文件' : '拖拽文件到这里，或点击选择文件' }}</strong>
        <span>支持文档、图片、音视频与字幕文件，单文件最大 500MB，最多 20 个文件</span>
      </button>

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
          <el-button
            v-if="uploadQueue.some((file) => file.status === 'error')"
            :disabled="uploading"
            @click="handleUpload"
          >重试失败文件</el-button>
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

    <el-dialog v-model="editDialogVisible" class="resource-dialog" title="编辑资源信息" width="min(520px, 92vw)" align-center destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="资源名称"><el-input v-model="editForm.file_name" maxlength="100" show-word-limit /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        <el-form-item label="分类"><el-select v-model="editForm.categories" multiple filterable allow-create default-first-option placeholder="选择或新增分类" style="width: 100%"><el-option v-for="item in categories" :key="item.id || item.name" :label="item.name" :value="item.name" /></el-select></el-form-item>
        <el-form-item label="标签"><el-select v-model="editForm.tags" multiple filterable allow-create default-first-option placeholder="选择或新增标签" style="width: 100%"><el-option v-for="item in tags" :key="item.id || item.name" :label="item.name" :value="item.name" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="editDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="taxonomyDialogVisible" class="resource-dialog" :title="`${taxonomyTitle}管理`" width="min(720px, 92vw)" align-center destroy-on-close>
      <el-tabs v-model="taxonomyTab" @tab-change="resetTaxonomyForm">
        <el-tab-pane label="分类词典" name="category" />
        <el-tab-pane label="标签词典" name="tag" />
      </el-tabs>
      <div class="taxonomy-editor">
        <label class="taxonomy-field taxonomy-name"><span>{{ taxonomyTypeLabel }}名称</span><el-input v-model="taxonomyForm.name" :placeholder="`输入${taxonomyTypeLabel}名称`" maxlength="80" @keyup.enter="saveTaxonomy" /></label>
        <label class="taxonomy-field taxonomy-color"><span>标识颜色</span><el-input v-model="taxonomyForm.color" placeholder="可选，如 #2f6feb" /></label>
        <label class="taxonomy-field taxonomy-order"><span>排序值</span><el-input-number v-model="taxonomyForm.sort_order" :min="0" :max="99999" controls-position="right" /></label>
        <div class="taxonomy-actions"><el-button type="primary" :loading="taxonomySaving" @click="saveTaxonomy">{{ taxonomyEditing ? '保存修改' : `新增${taxonomyTypeLabel}` }}</el-button><el-button v-if="taxonomyEditing" @click="resetTaxonomyForm">取消编辑</el-button></div>
      </div>
      <div v-if="!isMobile" class="taxonomy-table-shell"><el-table v-loading="taxonomyLoading" :data="taxonomyItems" size="small" row-key="name">
          <el-table-column prop="name" :label="taxonomyTypeLabel" min-width="220" />
          <el-table-column prop="count" label="使用资源数" width="110" />
          <el-table-column label="来源" width="100"><template #default="{ row }"><el-tag size="small" :type="row.managed ? 'success' : 'info'">{{ row.managed ? '词典' : '历史值' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="150" align="right"><template #default="{ row }"><el-button v-if="row.managed" link type="primary" @click="editTaxonomy(row)">编辑</el-button><el-button v-if="row.managed" link type="danger" @click="removeTaxonomy(row)">删除</el-button></template></el-table-column>
        </el-table></div>
      <div v-else v-loading="taxonomyLoading" class="taxonomy-mobile-list">
        <el-empty v-if="!taxonomyLoading && !taxonomyItems.length" :description="`暂无${taxonomyTypeLabel}`" />
        <article v-for="item in taxonomyItems" :key="item.id || item.name" class="taxonomy-mobile-item">
          <div class="taxonomy-mobile-summary"><strong>{{ item.name }}</strong><el-tag size="small" :type="item.managed ? 'success' : 'info'">{{ item.managed ? '词典' : '历史值' }}</el-tag></div>
          <div class="taxonomy-mobile-bottom"><span>使用资源 {{ item.count ?? 0 }}</span><div v-if="item.managed" class="taxonomy-mobile-actions"><el-button text type="primary" @click="editTaxonomy(item)">编辑</el-button><el-button text type="danger" @click="removeTaxonomy(item)">删除</el-button></div></div>
        </article>
      </div>
      <p class="dialog-hint">删除词典项不会清除已有资源中的分类或标签；编辑资源时仍可选择历史值或新增词条。</p>
    </el-dialog>

    <el-dialog v-model="indexDialogVisible" class="resource-dialog resource-index-dialog" title="知识库索引管理" width="min(1000px, 94vw)" align-center destroy-on-close>
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
            <el-table v-if="!isMobile" :data="indexGroups" size="small"><el-table-column prop="source_type" label="来源" width="100" /><el-table-column prop="parse_status" label="解析状态" width="120" /><el-table-column label="可检索" width="100"><template #default="{ row }">{{ row.available ? '是' : '否' }}</template></el-table-column><el-table-column label="允许 AI" width="100"><template #default="{ row }">{{ row.allow_ai ? '是' : '否' }}</template></el-table-column><el-table-column prop="resource_count" label="资源数" width="100" /><el-table-column prop="chunk_count" label="分块数" width="100" /></el-table>
            <div v-else class="index-mobile-list"><el-empty v-if="!indexLoading && !indexGroups.length" description="暂无索引分组" /><article v-for="(row, index) in indexGroups" :key="`${row.source_type}-${row.parse_status}-${index}`" class="index-mobile-item"><div class="index-mobile-top"><strong>{{ row.source_type || '未知来源' }}</strong><el-tag size="small" :type="row.available ? 'success' : 'info'">{{ row.available ? '可检索' : '不可检索' }}</el-tag></div><p>解析状态：{{ row.parse_status || '未知' }}</p><div class="index-mobile-meta"><span>资源 {{ row.resource_count ?? 0 }}</span><span>分块 {{ row.chunk_count ?? 0 }}</span><span>{{ row.allow_ai ? '允许 AI' : '未允许 AI' }}</span></div></article></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="索引资源" name="resources">
          <div class="index-panel">
            <div class="index-panel-heading"><div><strong>已进入 RAG 的资源</strong><span>共 {{ indexResourceTotal }} 项；删除索引不会删除原始素材</span></div><div class="index-actions"><el-select v-model="indexAvailable" size="small" style="width: 120px" @change="loadIndexResources"><el-option label="全部状态" value="" /><el-option label="可检索" value="true" /><el-option label="不可检索" value="false" /></el-select><el-button size="small" :icon="Refresh" :loading="indexLoading" @click="loadIndexPanel">刷新</el-button><el-button size="small" :loading="indexActionLoading" @click="bootstrapIndex(false)">同步当前资源</el-button><el-button size="small" type="warning" plain :loading="indexActionLoading" @click="bootstrapIndex(true)">重建索引</el-button></div></div>
            <el-table v-if="!isMobile" v-loading="indexLoading" :data="indexResources" size="small" max-height="460">
              <el-table-column prop="title" label="资源" min-width="220" show-overflow-tooltip />
              <el-table-column prop="resource_key" label="索引键" width="150" />
              <el-table-column label="解析状态" width="110"><template #default="{ row }"><el-tag :type="row.parse_status === 'failed' ? 'danger' : row.parse_status === 'completed' ? 'success' : 'info'">{{ ({ completed: '已解析', failed: '失败', pending: '待解析', processing: '解析中' })[row.parse_status] || row.parse_status }}</el-tag></template></el-table-column>
              <el-table-column prop="error_message" label="失败原因" min-width="230" show-overflow-tooltip />
              <el-table-column prop="chunk_count" label="分块" width="70" />
              <el-table-column label="AI" width="70"><template #default="{ row }"><el-tag size="small" :type="row.allow_ai ? 'success' : 'info'">{{ row.allow_ai ? '允许' : '关闭' }}</el-tag></template></el-table-column>
              <el-table-column label="操作" width="170" align="right"><template #default="{ row }"><el-button link type="primary" :loading="indexActionLoading" @click="syncIndexedResource(row)">同步</el-button><el-button link type="danger" :loading="indexActionLoading" @click="removeIndex(row)">删除</el-button></template></el-table-column>
            </el-table>
            <div v-else v-loading="indexLoading" class="index-mobile-list"><el-empty v-if="!indexLoading && !indexResources.length" description="暂无索引资源" /><article v-for="row in indexResources" :key="row.resource_key" class="index-mobile-item"><div class="index-mobile-top"><strong>{{ row.title || '未命名资源' }}</strong><el-tag size="small" :type="row.allow_ai ? 'success' : 'info'">{{ row.allow_ai ? '允许 AI' : 'AI 关闭' }}</el-tag></div><p class="index-resource-key">{{ row.resource_key }}</p><div class="index-mobile-meta"><span>{{ row.parse_status || '未解析' }}</span><span>分块 {{ row.chunk_count ?? 0 }}</span></div><div class="index-mobile-actions"><el-button text type="primary" :loading="indexActionLoading" @click="syncIndexedResource(row)">同步</el-button><el-button text type="danger" :loading="indexActionLoading" @click="removeIndex(row)">删除索引</el-button></div></article></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="检索测试" name="search">
          <div class="index-panel">
            <div class="index-search-bar"><el-input v-model="indexSearchQuery" clearable placeholder="输入关键词测试知识库检索，例如：光合作用实验设计" @keyup.enter="runIndexSearch" /><el-button type="primary" :loading="indexSearchLoading" @click="runIndexSearch">开始检索</el-button></div>
            <el-empty v-if="!indexSearchResults.length && !indexSearchLoading" description="输入关键词后查看检索结果" />
            <div v-else class="index-result-list"><article v-for="(item, index) in indexSearchResults" :key="item.chunk_id || `${item.resource_id}-${index}`"><div><strong>#{{ item.rank || index + 1 }} · {{ item.resource_id }} <em v-if="indexResultTimeRange(item)">{{ indexResultTimeRange(item) }}</em></strong><span>得分 {{ Number(item.score || item.rerank_score || 0).toFixed(3) }} · {{ item.match_type || 'hybrid' }}</span></div><p>{{ item.content }}</p></article></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="检索日志" name="logs">
          <div class="index-panel">
            <div class="index-panel-heading"><div><strong>Python RAG 检索日志</strong><span>共 {{ indexLogTotal }} 条</span></div><el-button :icon="Refresh" :loading="indexLoading" @click="loadIndexLogs">刷新</el-button></div>
            <el-table v-if="!isMobile" v-loading="indexLoading" :data="indexLogs" size="small" max-height="460"><el-table-column prop="query" label="查询内容" min-width="260" show-overflow-tooltip /><el-table-column prop="match_count" label="命中" width="70" /><el-table-column prop="top_score" label="最高分" width="90" /><el-table-column prop="search_mode" label="模式" width="140" /><el-table-column prop="latency_ms" label="耗时（ms）" width="100" /><el-table-column label="时间" width="155"><template #default="{ row }">{{ formatUpdatedAt(row.created_at) }}</template></el-table-column></el-table>
            <div v-else v-loading="indexLoading" class="index-mobile-list"><el-empty v-if="!indexLoading && !indexLogs.length" description="暂无检索日志" /><article v-for="(row, index) in indexLogs" :key="row.id || index" class="index-mobile-item"><div class="index-mobile-top"><strong>{{ row.query || '空查询' }}</strong><time>{{ formatUpdatedAt(row.created_at) }}</time></div><div class="index-mobile-meta"><span>命中 {{ row.match_count ?? 0 }}</span><span>最高分 {{ row.top_score ?? '—' }}</span><span>{{ row.search_mode || '—' }}</span><span>{{ row.latency_ms ?? '—' }} ms</span></div></article></div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="permissionDialogVisible" class="resource-dialog" title="资源权限设置" width="min(480px, 92vw)" align-center destroy-on-close>
      <el-form label-position="top" v-loading="saving">
        <el-form-item label="访问范围"><el-radio-group v-model="permissionForm.access_type"><el-radio value="private">仅自己</el-radio><el-radio value="shared">所有成员</el-radio><el-radio value="authorized">指定成员</el-radio></el-radio-group></el-form-item>
        <el-form-item v-if="permissionForm.access_type === 'authorized'" label="授权用户 ID"><el-input v-model="permissionForm.authorized_users" placeholder="多个用户 ID 请用逗号分隔" /></el-form-item>
        <el-form-item label="允许 AI 引用"><el-switch v-model="permissionForm.allow_ai" active-text="允许" inactive-text="不允许" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitPermission">保存权限</el-button></template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" class="resource-dialog" title="批量管理资源" width="min(480px, 92vw)" align-center destroy-on-close>
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
.taxonomy-editor { display: grid; grid-template-columns: minmax(160px, 1fr) minmax(170px, .9fr) 118px auto; align-items: end; gap: 10px; margin: 8px 0 20px; }
.taxonomy-field { min-width: 0; display: grid; gap: 6px; color: var(--zh-text-caption); font-size: 11px; }
.taxonomy-field :deep(.el-input-number) { width: 100%; }
.taxonomy-actions { display: flex; align-items: center; gap: 8px; }
.taxonomy-actions :deep(.el-button) { margin: 0; white-space: nowrap; }
.taxonomy-table-shell { width: 100%; overflow-x: auto; border-radius: var(--zh-radius8); }
.taxonomy-table-shell :deep(.el-table) { min-width: 620px; }
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
.index-result-list strong em { display: inline-flex; margin-left: 6px; padding: 1px 7px; border-radius: 999px; background: var(--zh-primary-soft); color: var(--zh-primary); font-size: 11px; font-style: normal; font-weight: 600; }
.index-result-list span { color: var(--zh-text-caption); font-size: 11px; }
.index-result-list p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.65; white-space: pre-wrap; }
.resource-load-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px; border: 1px solid #fecaca; border-radius: var(--zh-radius12); color: #b91c1c; background: #fff7f7; font-size: 13px; line-height: 1.6; }
/* 平板（768–1023.98）与手机（<768）共用：布局收单列、知识库 header 转单列 */
@media (max-width: 1023.98px) { .page-heading { align-items: flex-start; flex-direction: column; }.resource-layout { grid-template-columns: 1fr; }.stat-strip { grid-template-columns: repeat(2, 1fr); }.stat-strip article:nth-child(2n) { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr 1fr; }.resource-toolbar > .el-input { grid-column: 1 / -1; }.resource-toolbar-actions { justify-content: flex-start; flex-wrap: wrap; }.taxonomy-editor { grid-template-columns: 1fr 1fr; }.taxonomy-editor .el-button:last-child { grid-column: 2; }.index-overview-grid { grid-template-columns: repeat(2, 1fr); }.index-panel-heading { align-items: flex-start; flex-direction: column; }.index-actions { justify-content: flex-start; } }
/* 平板档：分类面板收为 76px 图标态（点击仍可切换分类，入口不丢） */
@media (min-width: 768px) and (max-width: 1023.98px) { .folder-panel { width: 76px; padding: 12px 6px; }.panel-title { justify-content: center; padding: 0 0 8px; }.panel-title > span { display: none; }.folder-panel > button { flex-direction: column; gap: 4px; padding: 8px 2px; }.folder-panel > button .el-icon { display: none; }.folder-panel > button > span { display: block; max-width: 100%; overflow: hidden; font-size: 11px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }.privacy-note { display: none; } }
/* 手机档：分类面板隐藏（顶部 el-select 承载入口）、主表格切换为卡片列表 */
/* 手机资源页：概览压缩为一行，搜索和素材列表进入首屏。 */
@media (max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse) {
  .folder-panel { display: none; }
  .resource-card-list { display: grid; }
  .resource-card { display: flex; justify-content: space-between; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); }
  .resource-card-main { display: flex; min-width: 0; flex: 1; }
  .resource-card-info { display: flex; flex: 1; flex-direction: column; min-width: 0; }
  .resource-card-info small { color: var(--zh-text-caption); font-size: 12px; }
  .resource-card-meta { display: flex; align-items: center; flex-wrap: wrap; }
  .taxonomy-editor { grid-template-columns: 1fr; }
  .index-search-bar { grid-template-columns: 1fr; }
  .index-result-list article > div { align-items: flex-start; flex-direction: column; gap: 4px; }
  .page-wrap { width: calc(100% - 32px); padding: 24px 0 calc(96px + var(--zh-safe-bottom, 0px)); }
  .page-heading { gap: 16px; }
  .page-kicker { margin-bottom: 4px !important; font-size: 11px !important; }
  .page-heading h1 { font-size: 24px; line-height: 1.25; }
  .page-heading p { max-width: 36ch; margin-top: 6px; font-size: 12px; line-height: 1.55; }
  .heading-actions { display: grid; grid-template-columns: 1fr 1fr; width: 100%; gap: 8px; }
  .heading-actions :deep(.el-button) { min-width: 0; min-height: 42px; margin: 0; }
  .stat-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 20px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-light); }
  .stat-strip article { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 5px; padding: 12px 9px; border-right: 1px solid var(--zh-line-border) !important; }
  .stat-strip article:last-child { border-right: 0 !important; }
  .stat-strip span { color: var(--zh-text-secondary); font-size: 10px; line-height: 1.3; white-space: nowrap; }
  .stat-strip strong { grid-row: auto; grid-column: auto; max-width: 100%; overflow: hidden; color: var(--zh-text-primary); font-size: 17px; line-height: 1.1; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .stat-strip small { display: none; }
  .resource-layout { margin-top: 19px; }
  .resource-toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; margin-bottom: 10px; }
  .resource-toolbar > .el-input { grid-column: 1 / -1; }
  .resource-toolbar :deep(.el-input__wrapper), .resource-toolbar :deep(.el-select__wrapper) { min-height: 42px; }
  .mobile-folder-select { width: 100%; min-width: 0; margin-bottom: 0; }
  .resource-toolbar > .el-select { min-width: 0; }
  .resource-toolbar-actions { grid-column: 1 / -1; min-height: 36px; justify-content: flex-start; gap: 8px; }
  .resource-toolbar-actions :deep(.el-button) { min-height: 36px; margin: 0; padding-inline: 9px; }
  .mobile-list-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 0 2px 10px; }
  .mobile-list-heading strong { color: var(--zh-text-primary); font-size: 15px; font-weight: 600; }
  .mobile-list-heading span { color: var(--zh-text-caption); font-size: 12px; font-variant-numeric: tabular-nums; }
  .resource-card-list { gap: 9px; min-height: 0; }
  .resource-load-error { align-items: stretch; flex-direction: column; }
  .resource-load-error :deep(.el-button) { min-height: 44px; margin: 0; }
  .resource-card { align-items: flex-start; gap: 7px; padding: 12px 9px; background: var(--zh-background-primary); }
  .resource-card-main { align-items: flex-start; gap: 7px; }
  .resource-card-check { min-width: 28px; min-height: 44px; margin: 0; padding-top: 4px; }
  .resource-card-check :deep(.el-checkbox__inner) { width: 18px; height: 18px; }
  .resource-card .file-mark { width: 31px; height: 35px; flex: 0 0 31px; font-size: 11px; }
  .resource-card-info { gap: 5px; }
  .resource-card-info strong { display: -webkit-box; overflow: hidden; color: var(--zh-text-primary); font-size: 13px; line-height: 1.4; text-overflow: initial; white-space: normal; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .resource-card-info small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .resource-card-meta { gap: 6px; }
  .resource-card :deep(.el-dropdown) { flex: 0 0 auto; }
  .resource-card :deep(.resource-more-button) { width: 44px; height: 44px; margin-top: -5px; }
  .resource-card-skeleton { align-items: center; min-height: 77px; }
  .skeleton-mark { width: 34px; height: 38px; flex: 0 0 34px; border-radius: 7px; background: var(--zh-background-weaken); }
  .skeleton-lines { display: grid; flex: 1; gap: 9px; }
  .skeleton-lines i { width: 78%; height: 10px; border-radius: 5px; background: var(--zh-background-option); }
  .skeleton-lines i:last-child { width: 48%; }
  .resource-empty-state { padding: 6px 12px 24px; border: 1px dashed var(--zh-line-heavier); border-radius: var(--zh-radius12); background: var(--zh-background-light); text-align: center; }
  .resource-empty-state :deep(.el-empty) { padding-bottom: 8px; }
  .resource-empty-state :deep(.el-button) { min-height: 42px; }

  .upload-dropzone { width: 100%; min-height: 142px; padding: 18px 14px; font: inherit; text-align: center; }
  .upload-dropzone:focus-visible { outline: 2px solid var(--zh-border-focus); outline-offset: 2px; }
  .upload-dropzone-icon { font-size: 34px !important; }
  .upload-file-item { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto; gap: 3px 8px; min-height: 76px; padding: 9px; }
  .upload-file-mark { grid-row: 1 / 3; grid-column: 1; align-self: start; width: 34px; height: 34px; flex: none; }
  .upload-file-info { grid-row: 1; grid-column: 2; }
  .upload-file-size { grid-row: 2; grid-column: 2; flex: none; text-align: left; }
  .upload-file-status { grid-row: 1; grid-column: 3; flex: none; }
  .upload-file-item > .el-button { grid-row: 2; grid-column: 3; justify-self: end; min-width: 36px; min-height: 36px; }
  .upload-dialog-footer { display: grid; grid-template-columns: 1fr 1fr; }
  .upload-dialog-footer :deep(.el-button) { width: 100%; margin: 0; }

  .taxonomy-editor { gap: 12px; }
  .taxonomy-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .taxonomy-actions :deep(.el-button) { width: 100%; min-height: 42px; }
  .taxonomy-actions :deep(.el-button:only-child) { grid-column: 1 / -1; }
  .taxonomy-mobile-list, .index-mobile-list { display: grid; gap: 9px; min-height: 72px; }
  .taxonomy-mobile-item, .index-mobile-item { min-width: 0; padding: 12px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
  .taxonomy-mobile-summary, .taxonomy-mobile-bottom, .index-mobile-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .taxonomy-mobile-summary strong, .index-mobile-top strong { min-width: 0; overflow-wrap: anywhere; color: var(--zh-text-primary); font-size: 13px; line-height: 1.5; }
  .taxonomy-mobile-bottom { align-items: center; margin-top: 8px; }
  .taxonomy-mobile-bottom > span, .index-mobile-meta, .index-mobile-top time { color: var(--zh-text-caption); font-size: 11px; }
  .taxonomy-mobile-actions, .index-mobile-actions { display: flex; align-items: center; gap: 4px; }
  .taxonomy-mobile-actions :deep(.el-button), .index-mobile-actions :deep(.el-button) { min-height: 36px; margin: 0; padding-inline: 9px; }
  .index-overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 18px; }
  .index-overview-grid article { min-width: 0; padding: 11px; }
  .index-overview-grid strong { font-size: 17px; overflow-wrap: anywhere; }
  .index-panel-heading { gap: 10px; }
  .index-panel-heading > .el-button { min-height: 40px; }
  .index-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; gap: 8px; }
  .index-actions :deep(.el-select) { grid-column: 1 / -1; width: 100% !important; }
  .index-actions :deep(.el-button) { min-width: 0; min-height: 40px; margin: 0; padding-inline: 5px; }
  .index-search-bar :deep(.el-button) { min-height: 42px; }
  .index-mobile-top time { flex: 0 0 auto; white-space: nowrap; }
  .index-mobile-item p { margin: 7px 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.5; }
  .index-mobile-item .index-resource-key { overflow-wrap: anywhere; color: var(--zh-text-caption); font-size: 11px; }
  .index-mobile-meta { display: flex; flex-wrap: wrap; gap: 5px 12px; font-variant-numeric: tabular-nums; }
  .index-mobile-actions { justify-content: flex-end; margin-top: 6px; }
  .index-result-list { max-height: none; overflow: visible; }
  .index-result-list article { overflow-wrap: anywhere; }
  :global(.resource-dialog) { display: flex; flex-direction: column; width: calc(100vw - 24px) !important; max-height: calc(100dvh - max(12px, var(--zh-safe-top)) - max(12px, var(--zh-safe-bottom))); margin: max(12px, var(--zh-safe-top)) auto !important; overflow: hidden; border-radius: var(--zh-radius16); }
  :global(.resource-dialog .el-dialog__header) { flex: 0 0 auto; padding: 18px 18px 12px; }
  :global(.resource-dialog .el-dialog__body) { flex: 1 1 auto; min-height: 0; padding: 8px 16px 18px; overflow-y: auto; overscroll-behavior: contain; }
  :global(.resource-dialog .el-dialog__footer) { flex: 0 0 auto; padding: 12px 16px calc(12px + var(--zh-safe-bottom, 0px)); border-top: 1px solid var(--zh-line-border); }
  :global(.resource-dialog .el-form-item__label) { font-size: 13px; }
  :global(.resource-dialog .el-input__wrapper), :global(.resource-dialog .el-select__wrapper) { min-height: 42px; }
  :global(.resource-dialog .el-radio-group) { display: grid; align-items: start; gap: 5px; }
  :global(.resource-dialog .el-radio) { min-height: 36px; margin-right: 0; }
  :global(.resource-index-dialog .el-tabs__item) { padding-inline: 12px; font-size: 12px; }
}
</style>
