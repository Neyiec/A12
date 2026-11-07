<script setup>
import { computed, defineAsyncComponent, onErrorCaptured, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createProject, createProjectPage, listProjects, saveProjectVersion } from '../apis/teacher'
import { hasWorkspaceTarget, unwrapWorkspaceResult } from '../utils/workspaceEntry'
import '../workspace-theme.css'
import WorkspaceEditorState from './WorkspaceEditorState.vue'
import { createGenerationTiming } from '../utils/generationTiming.js'

const editorFailure = ref(null)
const Editor = defineAsyncComponent({
  loader: () => createGenerationTiming().measure('workspace.editor_import', () => import('./CreationWorkspace.vue')),
  loadingComponent: WorkspaceEditorState,
  errorComponent: WorkspaceEditorState,
  delay: 0,
  timeout: 30000,
})
onErrorCaptured((failure) => {
  console.error('[workspace] 编辑器加载或初始化失败', failure)
  editorFailure.value = failure
  return false
})
const route = useRoute()
const router = useRouter()
const hasTarget = computed(() => hasWorkspaceTarget(route.query))
const projects = ref([])
const loading = ref(false)
const error = ref('')
const total = ref(0)
const filters = reactive({ keyword: '', page: 1, size: 12 })
const createVisible = ref(false)
const creating = ref(false)
const name = ref('')
const pendingProjectId = ref(null)
const pendingPageSaved = ref(false)
let requestSequence = 0
const loadProjects = async () => {
  const sequence = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const result = unwrapWorkspaceResult(await listProjects({ ...filters, keyword: filters.keyword.trim() || undefined }))
    if (sequence !== requestSequence) return
    projects.value = result?.records || []
    total.value = Number(result?.total || 0)
  } catch (failure) {
    if (sequence !== requestSequence) return
    error.value = failure?.message || '项目列表加载失败'
    projects.value = []
  } finally { if (sequence === requestSequence) loading.value = false }
}
const search = () => { filters.page = 1; return loadProjects() }
const openProject = project => router.push({ path: '/main/workspace', query: { projectId: String(project.id) } })
const beginCreate = () => {
  if (!pendingProjectId.value) name.value = ''
  createVisible.value = true
}
const createNewProject = async () => {
  const title = name.value.trim()
  if (!title) return ElMessage.warning('请输入项目名称')
  if (creating.value) return
  creating.value = true
  try {
    // Only explicit confirmation writes data. A retry reuses the partially created project.
    if (!pendingProjectId.value) {
      const project = unwrapWorkspaceResult(await createProject({ project_name: title, project_type: 'ppt', status: 'editing' }))
      pendingProjectId.value = project?.id || project?.project_id
      if (!pendingProjectId.value) throw new Error('创建项目未返回项目 ID')
    }
    if (!pendingPageSaved.value) {
      const slide = { title, pageType: 'cover', elements: [], html: '<html><body style="margin:0"><section style="position:relative;width:1280px;height:720px;background:white"></section></body></html>' }
      unwrapWorkspaceResult(await createProjectPage(pendingProjectId.value, { page_order: 1, page_type: 'cover', page_title: title, page_content: JSON.stringify(slide), components: '[]' }))
      pendingPageSaved.value = true
    }
    unwrapWorkspaceResult(await saveProjectVersion(pendingProjectId.value, { description: '教师主动新建项目的初始快照' }))
    await openProject({ id: pendingProjectId.value })
    createVisible.value = false
    ElMessage.success('新项目已创建')
  } catch (failure) {
    ElMessage.error(failure?.message || '项目创建失败，请重试')
  } finally { creating.value = false }
}
watch(hasTarget, target => {
  if (!target) void loadProjects()
  else {
    createVisible.value = false
    pendingProjectId.value = null
    pendingPageSaved.value = false
  }
}, { immediate: true })
</script>

<template>
  <div class="workspace-blue-white">
  <WorkspaceEditorState v-if="hasTarget && editorFailure" :error="editorFailure" />
  <Editor v-else-if="hasTarget" />
  <main v-else class="workspace-entry">
    <header><div><small>个人工作台</small><h1>选择项目，开始备课</h1><p>打开已有项目，或主动创建一份空白课件。不选择不会创建项目。</p></div><el-button type="primary" @click="beginCreate">＋ 新建项目</el-button></header>
    <div class="entry-search"><el-input v-model="filters.keyword" clearable placeholder="搜索项目名称" @keyup.enter="search" @clear="search" /><el-button :loading="loading" @click="search">搜索</el-button><el-button @click="router.push('/main')">返回教学助手</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon><el-button text @click="loadProjects">重新加载</el-button></el-alert>
    <section v-loading="loading" class="entry-projects">
      <article v-for="project in projects" :key="project.id"><h2>{{ project.project_name }}</h2><p>{{ project.status === 'archived' ? '已归档' : '可继续编辑' }} · 项目 {{ project.id }}</p><el-button type="primary" plain :disabled="project.status === 'archived'" @click="openProject(project)">打开项目</el-button></article>
    </section>
    <el-empty v-if="!loading && !error && !projects.length" description="暂无项目，请点击“新建项目”开始" />
    <el-pagination v-if="total > filters.size" v-model:current-page="filters.page" :total="total" :page-size="filters.size" layout="prev, pager, next, total" @current-change="loadProjects" />
    <el-dialog v-model="createVisible" title="新建项目" width="min(480px, 92vw)" :close-on-click-modal="!creating" :close-on-press-escape="!creating" :show-close="!creating">
      <p>创建一份空白 PPT 课件，并保存初始快照。</p><el-input v-model="name" :disabled="Boolean(pendingProjectId)" maxlength="80" show-word-limit placeholder="例如：八年级数学·勾股定理" @keyup.enter="createNewProject" />
      <p v-if="pendingProjectId">项目已建立，重试将继续完成初始化，不会重复创建。</p>
      <template #footer><el-button :disabled="creating" @click="createVisible = false">取消</el-button><el-button type="primary" :loading="creating" @click="createNewProject">{{ pendingProjectId ? '继续创建' : '创建项目' }}</el-button></template>
    </el-dialog>
  </main>
  </div>
</template>

<style scoped>
.workspace-blue-white{min-height:100dvh;background:#f4f8ff}
.workspace-entry{max-width:1100px;margin:auto;padding:48px 24px;min-height:100dvh;background:#f4f8ff;color:#172b4d}
header{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:28px}h1{font-size:28px;margin:10px 0}small{color:var(--el-color-primary)}p{color:var(--zh-text-caption);line-height:1.7}.entry-search{display:flex;gap:12px;margin-bottom:24px}.entry-search .el-input{max-width:420px}.entry-projects{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;min-height:100px;margin:24px 0}.entry-projects article{border:1px solid var(--zh-line-border);border-radius:16px;padding:22px}.entry-projects h2{font-size:17px;overflow-wrap:anywhere;margin:0 0 16px}@media(max-width:600px){.workspace-entry{padding:24px 16px}header{align-items:flex-start;flex-direction:column}.entry-search{flex-wrap:wrap}h1{font-size:24px}}
</style>
