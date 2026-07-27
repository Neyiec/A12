<!--
  [数据交互说明]
  - 导入: 资源库演示数据、Element Plus 组件与图标
  - 输出: 教师个人资源库页面
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Folder, Lock, MoreFilled, Search, Upload } from '@element-plus/icons-vue'
import { RESOURCE_PAGE } from '../config/teacherPages.config.js'
import { completeResourceUpload, createResourceUpload, deleteResource, downloadResource, listResources } from '../apis/teacher'

const keyword = ref('')
const activeFolder = ref('全部素材')
const selectedRows = ref([])
const resources = ref(RESOURCE_PAGE.files)
const fileInput = ref(null)
const loading = ref(false)
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
    if (records.length) resources.value = records.map(normalizeResource)
  } catch { /* 开发环境保留示例数据，接口上线后自动替换。 */ } finally { loading.value = false }
}

const startUpload = () => fileInput.value?.click()
const handleUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    // 后端采用“创建上传会话 → 直传签名地址 → 确认上传”的三段式流程。
    const sessionResult = await createResourceUpload({
      file_name: file.name,
      file_type: file.name.split('.').pop()?.toLowerCase() || file.type || 'unknown',
      file_size: file.size,
    })
    const session = sessionResult?.data || sessionResult || {}
    const uploadId = session.upload_id || session.id
    if (!uploadId) throw new Error('上传会话创建失败')
    if (session.upload_url) {
      const response = await fetch(session.upload_url, { method: 'PUT', body: file, headers: file.type ? { 'Content-Type': file.type } : undefined })
      if (!response.ok) throw new Error('文件上传失败')
    }
    await completeResourceUpload(uploadId)
    ElMessage.success('素材已上传，正在解析')
    await loadResources()
  } catch { ElMessage.error('上传失败，请检查服务连接后重试') }
  event.target.value = ''
}
const handleAction = async (row, command) => {
  if (!row.id) return ElMessage.info('示例素材暂不支持此操作')
  try {
    if (command === 'download') {
      const result = await downloadResource(row.id)
      const url = result?.data?.download_url || result?.download_url
      if (url) window.open(url, '_blank', 'noopener')
    }
    if (command === 'delete') { await deleteResource(row.id); resources.value = resources.value.filter((item) => item.id !== row.id) }
  } catch { ElMessage.error('操作未成功，请稍后重试') }
}

onMounted(loadResources)
</script>

<template>
  <div class="page-wrap">
    <header class="page-heading">
      <div><p class="page-kicker">个人教学资产</p><h1>个人资源库</h1><p>统一管理私有素材，并决定哪些内容可供智能体引用。</p></div>
      <el-button type="primary" :icon="Upload" @click="startUpload">上传素材</el-button><input ref="fileInput" class="visually-hidden" type="file" accept=".doc,.docx,.pdf,.ppt,.pptx,.txt,image/*,audio/*,video/*" @change="handleUpload">
    </header>

    <section class="stat-strip" aria-label="资源库概览">
      <article v-for="stat in RESOURCE_PAGE.stats" :key="stat.label">
        <span>{{ stat.label }}</span><strong>{{ stat.value }}</strong><small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="resource-layout">
      <aside class="folder-panel">
        <div class="panel-title"><span>分类目录</span><el-button text circle aria-label="新建分类">+</el-button></div>
        <button v-for="folder in RESOURCE_PAGE.folders" :key="folder" :class="{ active: activeFolder === folder }" @click="activeFolder = folder">
          <el-icon><Folder /></el-icon><span>{{ folder }}</span>
        </button>
        <div class="privacy-note"><el-icon><Lock /></el-icon><p><strong>默认私有</strong><br>仅你和授权的智能体可以访问。</p></div>
      </aside>

      <div class="resource-content">
        <div class="resource-toolbar">
          <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索文件名、课程或标签" clearable />
          <el-select model-value="全部类型" aria-label="资源类型"><el-option label="全部类型" value="全部类型" /><el-option label="课件" value="课件" /><el-option label="文档" value="文档" /></el-select>
          <el-button :icon="Delete" :disabled="selectedRows.length === 0">批量管理</el-button>
        </div>
        <el-table v-loading="loading" :data="filteredFiles" @selection-change="selectedRows = $event">
          <el-table-column type="selection" width="42" />
          <el-table-column label="素材" min-width="260">
            <template #default="{ row }"><div class="file-cell"><span class="file-mark">{{ row.type.slice(0, 1) }}</span><div><strong>{{ row.name }}</strong><small>{{ row.course }} · {{ row.size }}</small></div></div></template>
          </el-table-column>
          <el-table-column prop="date" label="更新时间" min-width="120" />
          <el-table-column label="解析状态" width="110"><template #default="{ row }"><el-tag :type="row.status === '已解析' ? 'success' : row.status === '解析中' ? 'warning' : 'info'" effect="light">{{ row.status }}</el-tag></template></el-table-column>
          <el-table-column label="权限" width="92"><template #default><span class="private-label"><el-icon><Lock /></el-icon> 私有</span></template></el-table-column>
          <el-table-column width="54"><template #default="{ row }"><el-dropdown trigger="click" @command="handleAction(row, $event)"><el-button text circle aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="download">下载</el-dropdown-item><el-dropdown-item command="delete" divided>删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-wrap { width: min(1220px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 56px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; }
.page-kicker { margin: 0 0 6px !important; color: var(--zh-text-theme) !important; font-size: 13px !important; font-weight: 600; }
.page-heading h1 { margin: 0; font-size: 30px; letter-spacing: var(--zh-tracking-tight); }
.page-heading p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 14px; }
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
:deep(.el-table) { --el-table-border-color: var(--zh-line-parting); --el-table-header-bg-color: var(--zh-background-light); border-radius: var(--zh-radius12); }
@media (max-width: 820px) { .resource-layout { grid-template-columns: 1fr; }.folder-panel { display: none; }.stat-strip { grid-template-columns: 1fr; }.stat-strip article { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr; } }
</style>
