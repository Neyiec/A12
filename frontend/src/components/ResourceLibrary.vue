<!--
  [数据交互说明]
  - 导入: 资源库演示数据、Element Plus 组件与图标
  - 输出: 教师个人资源库页面
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Edit, Folder, Loading, Lock, MoreFilled, Search, Upload } from '@element-plus/icons-vue'
import { batchResourceAction, deleteResource, downloadResource, getResourcePermission, listResources, setResourcePermission, updateResource, uploadResource } from '../apis/teacher'

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
const saving = ref(false)
const editingRow = ref(null)
const editForm = ref({ file_name: '', description: '', categories: '', tags: '' })
const permissionForm = ref({ access_type: 'private', authorized_users: '', allow_ai: false })
const batchForm = ref({ action: 'delete', target: '' })

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
  try { return JSON.parse(value || '[]') } catch { return [] }
}

const normalizeRealResource = (item) => ({
  id: item.id,
  name: item.file_name,
  type: (item.file_type || 'file').toUpperCase(),
  course: parseList(item.categories).join(' · ') || '未分类',
  size: formatFileSize(item.file_size),
  fileSize: Number(item.file_size) || 0,
  date: formatUpdatedAt(item.updated_at || item.created_at),
  status: item.allow_ai === 1 ? '已启用' : '未启用',
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
  ...new Set(resources.value.flatMap((item) => item.course === '未分类' ? [] : item.course.split(' · '))),
])

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
    if (command === 'delete') { await deleteResource(row.id); resources.value = resources.value.filter((item) => item.id !== row.id) }
  } catch { ElMessage.error('操作未成功，请稍后重试') }
}

const unwrapResponse = (response) => response?.data || response
const parseEditableList = (value) => parseList(value).join(', ')
const toJsonList = (value) => JSON.stringify(value.split(/[,，]/).map((item) => item.trim()).filter(Boolean))

const openEditDialog = (row) => {
  editingRow.value = row
  editForm.value = { file_name: row.name, description: row.description || '', categories: parseEditableList(row.raw?.categories), tags: parseEditableList(row.raw?.tags) }
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
    await batchResourceAction({ idempotent_key: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`, action: batchForm.value.action, resource_ids: JSON.stringify(selectedRows.value.map((row) => row.id)), target: batchForm.value.target.trim() || undefined })
    batchDialogVisible.value = false
    selectedRows.value = []
    await loadResources()
    ElMessage.success('批量操作已提交')
  } catch (error) { ElMessage.error(error?.message || '批量操作失败，请稍后重试') } finally { saving.value = false }
}

onMounted(loadResources)
onBeforeUnmount(clearUploadProgressTimers)
</script>

<template>
  <div class="page-wrap">
    <header class="page-heading">
      <div><p class="page-kicker">个人教学资产</p><h1>个人资源库</h1><p>统一管理私有素材，并决定哪些内容可供智能体引用。</p></div>
      <el-button type="primary" :icon="Upload" @click="startUpload">上传素材</el-button>
    </header>

    <section class="stat-strip" aria-label="资源库概览">
      <article v-for="stat in resourceStats" :key="stat.label">
        <span>{{ stat.label }}</span><strong>{{ stat.value }}</strong><small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="resource-layout">
      <aside class="folder-panel">
        <div class="panel-title"><span>分类目录</span><el-button text circle aria-label="新建分类">+</el-button></div>
        <button v-for="folder in resourceFolders" :key="folder" :class="{ active: activeFolder === folder }" @click="activeFolder = folder">
          <el-icon><Folder /></el-icon><span>{{ folder }}</span>
        </button>
        <div class="privacy-note"><el-icon><Lock /></el-icon><p><strong>默认私有</strong><br>仅你和授权的智能体可以访问。</p></div>
      </aside>

      <div class="resource-content">
        <div class="resource-toolbar">
          <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索文件名、课程或标签" clearable />
          <el-select v-model="typeFilter" aria-label="资源类型" clearable placeholder="全部类型"><el-option label="全部类型" value="" /><el-option label="课件" value="ppt" /><el-option label="文档" value="word" /><el-option label="PDF" value="pdf" /><el-option label="图片" value="image" /><el-option label="音视频" value="audio" /></el-select>
          <el-button :icon="Delete" :disabled="selectedRows.length === 0" @click="openBatchDialog">批量管理</el-button>
        </div>
        <el-table v-loading="loading" :data="visibleFiles" @selection-change="selectedRows = $event">
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
          <el-table-column width="54"><template #default="{ row }"><el-dropdown trigger="click" @command="handleAction(row, $event)"><el-button text circle aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="edit"><el-icon><Edit /></el-icon>编辑信息</el-dropdown-item><el-dropdown-item command="permission">权限设置</el-dropdown-item><el-dropdown-item command="download">下载</el-dropdown-item><el-dropdown-item command="delete" divided>删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传素材"
      width="680px"
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

    <el-dialog v-model="editDialogVisible" title="编辑资源信息" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="资源名称"><el-input v-model="editForm.file_name" maxlength="100" show-word-limit /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        <el-form-item label="分类"><el-input v-model="editForm.categories" placeholder="多个分类请用逗号分隔" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="editForm.tags" placeholder="多个标签请用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="permissionDialogVisible" title="资源权限设置" width="480px" destroy-on-close>
      <el-form label-position="top" v-loading="saving">
        <el-form-item label="访问范围"><el-radio-group v-model="permissionForm.access_type"><el-radio value="private">仅自己</el-radio><el-radio value="shared">所有成员</el-radio><el-radio value="authorized">指定成员</el-radio></el-radio-group></el-form-item>
        <el-form-item v-if="permissionForm.access_type === 'authorized'" label="授权用户 ID"><el-input v-model="permissionForm.authorized_users" placeholder="多个用户 ID 请用逗号分隔" /></el-form-item>
        <el-form-item label="允许 AI 引用"><el-switch v-model="permissionForm.allow_ai" active-text="允许" inactive-text="不允许" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitPermission">保存权限</el-button></template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量管理资源" width="480px" destroy-on-close>
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
.file-cell { display: flex; align-items: center; gap: 12px; }.file-cell > div { min-width: 0; display: flex; flex-direction: column; }
.file-cell strong { overflow: hidden; color: var(--zh-text-primary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.file-cell small { margin-top: 3px; color: var(--zh-text-caption); }
.file-mark { width: 34px; height: 38px; display: grid; place-items: center; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font-weight: 700; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.private-label { display: inline-flex; align-items: center; gap: 4px; color: var(--zh-text-secondary); font-size: 12px; }
.batch-summary { margin: 0 0 18px; color: var(--zh-text-secondary); }
:deep(.el-table) { --el-table-border-color: var(--zh-line-parting); --el-table-header-bg-color: var(--zh-background-light); border-radius: var(--zh-radius12); }
@media (max-width: 820px) { .resource-layout { grid-template-columns: 1fr; }.folder-panel { display: none; }.stat-strip { grid-template-columns: 1fr; }.stat-strip article { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr; } }
</style>
