<script setup>
import { computed, defineAsyncComponent, onErrorCaptured, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { archiveProject, copyProject, createProject, createProjectPage, deleteProject, getProject, listProjects, patchProject, restoreProject, saveProjectVersion } from '../apis/teacher'
import { hasWorkspaceTarget, unwrapWorkspaceResult } from '../utils/workspaceEntry'
import '../workspace-theme.css'
import WorkspaceEditorState from './WorkspaceEditorState.vue'
import { createGenerationTiming } from '../utils/generationTiming.js'
import { ArrowRight, MoreFilled } from '@element-plus/icons-vue'
import { useMobileViewport } from '../composables/useMobileViewport'
import ProjectCollaborators from './ProjectCollaborators.vue'

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
const MobilePreview = defineAsyncComponent(() => import('./MobileWorkspacePreview.vue'))
const isMobile = useMobileViewport()
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
const projectActionPending = ref(false)
const collaborators = ref(null)
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
const openProject = project => router.push({ path: '/main/workspace', query: { projectId: String(project.id), ...(route.query.preview ? { preview: '1' } : {}) } })
const handleProjectAction = async (action, project) => {
  if (projectActionPending.value) return
  const query = route.query.preview ? { preview: '1' } : {}
  if (action === 'publish') return router.push({ path: '/main/community', query: { ...query, publishProject: project.id } })
  if (action === 'history') return router.push({ path: '/main/workspace', query: { ...query, projectId: project.id, history: '1' } })
  if (action === 'collaborators') return collaborators.value.open(project.id)

  const operations = {
    rename: async () => {
      let name
      try {
        const result = await ElMessageBox.prompt('输入新的课件名称', '重命名课件', {
          inputValue: project.project_name,
          inputValidator: value => Boolean(value?.trim() && value.trim().length <= 80) || '名称需为 1–80 字',
          confirmButtonText: '保存', cancelButtonText: '取消',
        })
        name = result.value.trim()
      } catch { return false }
      if (name === project.project_name) return false
      const current = unwrapWorkspaceResult(await getProject(project.id))
      return patchProject(project.id, { project_name: name, current_version: current.current_version })
    },
    copy: () => copyProject(project.id, { new_name: `${project.project_name} 副本` }),
    archive: () => archiveProject(project.id),
    restore: () => restoreProject(project.id),
    delete: () => deleteProject(project.id),
  }
  const labels = { rename: '重命名', copy: '复制', archive: '归档', restore: '恢复', delete: '删除' }
  if (!operations[action]) return
  projectActionPending.value = true
  try {
    if (action === 'delete') {
      try {
        await ElMessageBox.confirm(`确定删除“${project.project_name}”吗？`, '删除课件', {
          type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
        })
      } catch { return }
    }
    const result = await operations[action]()
    if (result === false) return
    unwrapWorkspaceResult(result)
    if (action === 'delete' && projects.value.length === 1 && filters.page > 1) filters.page--
    if (action === 'copy') filters.page = 1
    ElMessage.success(`课件已${labels[action]}`)
    await loadProjects()
  } catch (failure) {
    ElMessage.error(failure?.message || `${labels[action]}课件失败`)
  } finally {
    projectActionPending.value = false
  }
}
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
  <div :class="isMobile ? 'workspace-mobile-shell' : 'workspace-blue-white'">
  <MobilePreview v-if="hasTarget && isMobile" />
  <WorkspaceEditorState v-else-if="hasTarget && editorFailure" :error="editorFailure" />
  <Editor v-else-if="hasTarget" />
  <main v-else class="workspace-entry">
    <header v-if="!isMobile"><div><small>个人工作台</small><h1>选择项目，开始备课</h1><p>打开已有项目，或主动创建一份空白课件。不选择不会创建项目。</p></div><el-button type="primary" @click="beginCreate">＋ 新建项目</el-button></header>
    <div class="entry-search"><el-input v-model="filters.keyword" clearable :placeholder="isMobile ? '搜索课件' : '搜索项目名称'" @keyup.enter="search" @clear="search" /><el-button :loading="loading" @click="search">搜索</el-button><el-button v-if="!isMobile" @click="router.push('/main')">返回教学助手</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon><el-button text @click="loadProjects">重新加载</el-button></el-alert>
    <section v-loading="loading" class="entry-projects">
      <template v-if="isMobile">
        <div v-for="project in projects" :key="project.id" class="mobile-project-row">
          <button type="button" class="mobile-project-item" @click="openProject(project)">
            <span><strong>{{ project.project_name }}</strong><small>{{ project.project_type === 'word' ? '教学教案' : 'PPT 课件' }}<template v-if="project.status === 'archived'"> · 已归档</template></small></span>
            <el-icon><ArrowRight /></el-icon>
          </button>
          <el-dropdown trigger="click" :disabled="projectActionPending" @command="handleProjectAction($event, project)">
            <button type="button" class="mobile-project-more" :aria-label="`${project.project_name}的更多操作`"><el-icon><MoreFilled /></el-icon></button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="history">历史版本</el-dropdown-item>
                <el-dropdown-item v-if="project.status !== 'archived'" command="publish">发布社区</el-dropdown-item>
                <el-dropdown-item v-if="project.status !== 'archived'" command="collaborators">协作授权</el-dropdown-item>
                <el-dropdown-item command="copy" divided>复制课件</el-dropdown-item>
                <el-dropdown-item v-if="project.status !== 'archived'" command="rename">重命名</el-dropdown-item>
                <el-dropdown-item v-if="project.status === 'archived'" command="restore">恢复归档</el-dropdown-item>
                <el-dropdown-item v-else command="archive">归档课件</el-dropdown-item>
                <el-dropdown-item command="delete">删除课件</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
      <template v-else>
      <article v-for="(project, index) in projects" :key="project.id"><div v-if="isMobile" class="project-cover" aria-hidden="true"><span>{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ project.project_type === 'word' ? '教案' : 'PPT' }}</strong></div><div class="project-copy"><h2>{{ project.project_name }}</h2><p>{{ isMobile ? (project.project_type === 'word' ? '教学教案' : '演示课件') : `${project.status === 'archived' ? '已归档' : '可继续编辑'} · 项目 ${project.id}` }}</p><el-button type="primary" plain :disabled="!isMobile && project.status === 'archived'" @click="openProject(project)">{{ isMobile ? '预览课件' : '打开项目' }}</el-button></div></article>
      </template>
    </section>
    <el-empty v-if="!loading && !error && !projects.length" :description="isMobile ? (filters.keyword ? '没有找到相关课件' : '暂无课件，请先在电脑端完成制作') : '暂无项目，请点击“新建项目”开始'" />
    <el-pagination v-if="total > filters.size" v-model:current-page="filters.page" :total="total" :page-size="filters.size" layout="prev, pager, next, total" @current-change="loadProjects" />
    <ProjectCollaborators v-if="isMobile" ref="collaborators" />
    <el-dialog v-model="createVisible" title="新建项目" width="min(480px, 92vw)" :close-on-click-modal="!creating" :close-on-press-escape="!creating" :show-close="!creating">
      <p>创建一份空白 PPT 课件，并保存初始快照。</p><el-input v-model="name" :disabled="Boolean(pendingProjectId)" maxlength="80" show-word-limit placeholder="例如：八年级数学·勾股定理" @keyup.enter="createNewProject" />
      <p v-if="pendingProjectId">项目已建立，重试将继续完成初始化，不会重复创建。</p>
      <template #footer><el-button :disabled="creating" @click="createVisible = false">取消</el-button><el-button type="primary" :loading="creating" @click="createNewProject">{{ pendingProjectId ? '继续创建' : '创建项目' }}</el-button></template>
    </el-dialog>
  </main>
  </div>
</template>

<style scoped>
.workspace-mobile-shell .workspace-entry {
  background: var(--zh-background-light);
  color: var(--zh-text-primary);
}
.mobile-project-row {
  display: flex;
  align-items: center;
  padding-right: 8px;
  border-radius: 14px;
  background: var(--zh-background-primary);
}
.mobile-project-row .mobile-project-item { flex: 1; min-width: 0; }
.mobile-project-more {
  display: grid;
  place-items: center;
  width: 44px;
  height: 48px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--zh-text-secondary);
  font-size: 22px;
  cursor: pointer;
}
.mobile-project-more:active { background: var(--zh-background-option); }
.workspace-blue-white{min-height:100dvh;background:#f4f8ff}
.workspace-entry{max-width:1100px;margin:auto;padding:48px 24px;min-height:100dvh;background:#f4f8ff;color:#172b4d}
header{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:28px}h1{font-size:28px;margin:10px 0}small{color:var(--el-color-primary)}p{color:var(--zh-text-caption);line-height:1.7}.entry-search{display:flex;gap:12px;margin-bottom:24px}.entry-search .el-input{max-width:420px}.entry-projects{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;min-height:100px;margin:24px 0}.entry-projects article{border:1px solid var(--zh-line-border);border-radius:16px;padding:22px}.entry-projects h2{font-size:17px;overflow-wrap:anywhere;margin:0 0 16px}@media(max-width:600px){.workspace-entry{padding:24px 16px}header{align-items:flex-start;flex-direction:column}.entry-search{flex-wrap:wrap}h1{font-size:24px}}
</style>

<style scoped>
@media (max-width:767.98px) and (hover:none) and (pointer:coarse){
  .workspace-entry{padding:calc(24px + var(--zh-safe-top)) 20px calc(96px + var(--zh-safe-bottom));background:#f4f6fa}
  header{flex-direction:row;align-items:center;gap:8px;margin-bottom:24px}header h1{margin:0;font-size:28px;letter-spacing:-.04em}.mobile-preview-hint{margin:6px 0 0;font-size:15px;color:#64748b}
  .entry-search{flex-wrap:nowrap;gap:8px}.entry-search .el-input{flex:1;min-width:0}
  .entry-projects{grid-template-columns:1fr;gap:16px}.entry-projects article{display:flex;gap:16px;padding:18px;border:0;border-radius:18px;box-shadow:0 3px 15px #172b4d06}
  .project-cover{display:flex;flex:none;flex-direction:column;justify-content:space-between;width:82px;min-height:116px;padding:12px;border-radius:10px;background:#e8efff;color:#2563eb}.project-cover span{font-size:28px;font-weight:650;font-variant-numeric:tabular-nums}.project-cover strong{font-size:14px;letter-spacing:.06em}
  .entry-projects article:nth-child(3n + 2) .project-cover{background:#e8f2ef;color:#337461}.entry-projects article:nth-child(3n) .project-cover{background:#f5ede3;color:#916431}
  .project-copy{flex:1;min-width:0}.entry-projects h2{margin:0;font-size:18px;line-height:1.5}.entry-projects p{margin:6px 0 10px;font-size:14px}.project-copy .el-button{min-height:44px;font-size:15px}
}
</style>
