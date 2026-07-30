<!--
  [数据交互说明]
  - 导入: 首页配置、Element Plus 图标
  - 输出: 教师端默认首页内容，由 `TeacherLayout.vue` 承载全局导航
-->
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Document,
  MagicStick,
  Microphone,
  Monitor,
  Paperclip,
  Promotion,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'
import { archiveProject, copyProject, createAiSession, createProject, deleteProject, listProjects, listResources, restoreProject, uploadResource } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const canSend = computed(() => prompt.value.trim().length > 0)
const composerInput = ref(null)
const activeSuggestionId = ref(null)
const iconMap = { Presentation: Monitor, Document, MagicStick }
const projects = ref([])
const projectsLoading = ref(true)
const sessionDialogVisible = ref(false)
const sessionCreating = ref(false)
const resourcesLoading = ref(false)
const availableResources = ref([])
const selectedResourceIds = ref([])
const uploadDialogVisible = ref(false)
const knowledgeDialogVisible = ref(false)
const resourceSearch = ref('')
const resourceUploading = ref(false)
const resourceUploadProgress = ref(0)
const resourceFileInput = ref(null)
const uploadedResourceNames = ref([])
const uploadDragging = ref(false)
const voiceDialogVisible = ref(false)
const voiceLanguage = ref('zh-CN')
const sessionForm = reactive({ title: '', subject: '', grade: '' })
const archivedVisible = ref(false)
const archivedProjects = ref([])
const archivedLoading = ref(false)
const projectManagerVisible = ref(false)
const managedProjects = ref([])
const projectManagerLoading = ref(false)
const filteredAvailableResources = computed(() => {
  const query = resourceSearch.value.trim().toLowerCase()
  return query ? availableResources.value.filter((item) => (item.file_name || '').toLowerCase().includes(query)) : availableResources.value
})

const openProject = (project) => router.push({
  path: '/main/workspace',
  query: { ...(route.query.preview ? { preview: '1' } : {}), projectId: project.id },
})

const loadProjects = async () => {
  projectsLoading.value = true
  try {
    const result = await listProjects({ page: 1, size: 4, status: 'draft' })
    projects.value = result?.data?.records || result?.data?.list || result?.data?.items || []
  } catch {
    projects.value = []
  } finally {
    projectsLoading.value = false
  }
}

/** 将推荐任务写入输入框。 */
const applySuggestion = (suggestion) => {
  prompt.value = suggestion.prompt
  activeSuggestionId.value = suggestion.id
  requestAnimationFrame(() => composerInput.value?.focus())
}

/** 创建演示任务并进入创作工作台。 */
const sendPrompt = () => {
  if (!canSend.value) return
  ElMessage.success('教学思路已梳理，正在展开创作工作台')
  router.push({ path: '/main/workspace', query: route.query.preview ? { preview: '1' } : {} })
}

const createProjectFromPrompt = async () => {
  if (!canSend.value) return
  try {
    const result = await createProject({
      project_name: prompt.value.trim().slice(0, 40),
      project_type: 'courseware',
      status: 'draft',
    })
    const project = result?.data || result
    if (!project?.id) throw new Error(result?.message || '创建项目失败')
    ElMessage.success('已创建教学项目')
    openProject(project)
  } catch (error) {
    ElMessage.error(error?.message || '创建项目失败，请登录后重试')
  }
}

const loadAvailableResources = async () => {
  resourcesLoading.value = true
  try {
    const result = await listResources({ page: 1, size: 30 })
    availableResources.value = result?.data?.records || result?.data?.list || result?.data?.items || []
  } catch { availableResources.value = [] } finally { resourcesLoading.value = false }
}
const openUploadDialog = () => {
  uploadedResourceNames.value = []
  resourceUploadProgress.value = 0
  uploadDialogVisible.value = true
}
const openKnowledgeDialog = async () => {
  resourceSearch.value = ''
  knowledgeDialogVisible.value = true
  await loadAvailableResources()
}
const triggerResourceUpload = () => resourceFileInput.value?.click()
const uploadLocalFiles = async (rawFiles) => {
  const supportedExtensions = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'md']
  const files = Array.from(rawFiles || []).filter((file) => supportedExtensions.includes(file.name.split('.').pop()?.toLowerCase()))
  if (!files.length) return
  resourceUploading.value = true; resourceUploadProgress.value = 0
  try {
    for (let index = 0; index < files.length; index += 1) {
      const file = files[index]
      const resource = await uploadResource(file, (progress) => { resourceUploadProgress.value = Math.round(((index + progress / 100) / files.length) * 100) })
      const resourceId = resource?.id || resource?.resource_id
      if (resourceId && !selectedResourceIds.value.includes(resourceId)) selectedResourceIds.value.push(resourceId)
      uploadedResourceNames.value.push(file.name)
    }
    ElMessage.success(`${files.length} 份资料已上传并引用`)
  } catch (error) { ElMessage.error(error?.message || '资料上传失败') }
  finally { resourceUploading.value = false }
}
const uploadPickedResource = async (event) => {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  await uploadLocalFiles(files)
}
const dropResourceFiles = async (event) => {
  uploadDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  if (!files.length) return
  const supported = files.filter((file) => /\.(pdf|docx?|pptx?|txt|md)$/i.test(file.name))
  if (supported.length !== files.length) ElMessage.warning('已忽略不支持的文件格式')
  await uploadLocalFiles(supported)
}
const openSessionDialog = async () => {
  if (!canSend.value) return
  sessionForm.title = prompt.value.trim().slice(0, 40)
  sessionForm.subject = ''
  sessionForm.grade = ''
  sessionDialogVisible.value = true
  await loadAvailableResources()
}

const createSessionFromPrompt = async () => {
  if (!sessionForm.title.trim() || !sessionForm.subject.trim() || !sessionForm.grade.trim()) return ElMessage.warning('请完整填写备课信息')
  sessionCreating.value = true
  try {
    const result = await createAiSession({
      title: sessionForm.title.trim(), subject: sessionForm.subject.trim(), grade: sessionForm.grade.trim(), status: 'active',
      messages: JSON.stringify([{ role: 'user', content: prompt.value.trim() }]), uploaded_refs: JSON.stringify(selectedResourceIds.value),
    })
    const task = result?.data || result
    const sessionId = task?.conversation_id || task?.id
    if (!sessionId) throw new Error(result?.message || '创建备课会话失败')
    sessionDialogVisible.value = false
    ElMessage.success('备课会话已创建，正在生成教学大纲')
    router.push({ path: '/main/workspace', query: { ...(route.query.preview ? { preview: '1' } : {}), sessionId, taskId: task.id } })
  } catch (error) { ElMessage.error(error?.message || '创建备课会话失败，请稍后重试') } finally { sessionCreating.value = false }
}

const openArchivedProjects = async () => {
  archivedVisible.value = true; archivedLoading.value = true
  try { const result = await listProjects({ page: 1, size: 30, status: 'archived' }); archivedProjects.value = result?.data?.records || result?.data?.list || result?.data?.items || [] }
  catch (error) { ElMessage.error(error?.message || '归档项目加载失败') } finally { archivedLoading.value = false }
}
const restoreArchivedProject = async (project) => {
  try { await restoreProject(project.id); archivedProjects.value = archivedProjects.value.filter((item) => item.id !== project.id); await loadProjects(); ElMessage.success('项目已恢复到草稿') }
  catch (error) { ElMessage.error(error?.message || '项目恢复失败') }
}
const openProjectManager = async () => {
  projectManagerVisible.value = true; projectManagerLoading.value = true
  try { const result = await listProjects({ page: 1, size: 50 }); managedProjects.value = result?.data?.records || result?.data?.list || result?.data?.items || [] }
  catch (error) { ElMessage.error(error?.message || '项目列表加载失败') } finally { projectManagerLoading.value = false }
}
const copyManagedProject = async (project) => {
  try { await copyProject(project.id, { new_name: `${project.project_name} 副本` }); ElMessage.success('项目已复制'); await openProjectManager(); await loadProjects() }
  catch (error) { ElMessage.error(error?.message || '项目复制失败') }
}
const archiveManagedProject = async (project) => {
  try { await archiveProject(project.id); ElMessage.success('项目已归档'); await openProjectManager(); await loadProjects() }
  catch (error) { ElMessage.error(error?.message || '项目归档失败') }
}
const deleteManagedProject = async (project) => {
  try { await ElMessageBox.confirm(`确定删除“${project.project_name}”吗？此操作不可恢复。`, '删除项目', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }); await deleteProject(project.id); ElMessage.success('项目已删除'); await openProjectManager(); await loadProjects() }
  catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error?.message || '项目删除失败') }
}

onMounted(loadProjects)
</script>

<template>
  <section class="home-welcome">
    <div class="welcome-copy motion-stage motion-stage-1">
      <p class="eyebrow">{{ TEACHER_HOME.greeting.eyebrow }}</p>
      <h1>{{ TEACHER_HOME.greeting.title }}</h1>
      <p class="intro">{{ TEACHER_HOME.greeting.description }}</p>
    </div>

    <section
      v-if="projectsLoading || projects.length"
      class="recent-projects motion-stage motion-stage-2"
      aria-label="最近项目"
      :aria-busy="projectsLoading"
    >
      <div class="recent-projects-heading"><h2>最近项目</h2><span><el-button text size="small" @click="openProjectManager">管理项目</el-button></span></div>
      <div v-if="projectsLoading" class="project-grid" aria-hidden="true">
        <el-skeleton v-for="index in 4" :key="index" animated class="project-skeleton">
          <template #template>
            <el-skeleton-item variant="text" class="project-skeleton-title" />
            <el-skeleton-item variant="text" class="project-skeleton-meta" />
          </template>
        </el-skeleton>
      </div>
      <div v-else class="project-grid">
        <button v-for="project in projects" :key="project.id" type="button" class="project-card" @click="openProject(project)">
          <strong>{{ project.project_name }}</strong>
          <span>{{ project.project_type || '教学项目' }} · v{{ project.current_version || 1 }}</span>
        </button>
      </div>
    </section>

    <div class="suggestion-grid motion-stage motion-stage-3">
      <el-card
        v-for="suggestion in TEACHER_HOME.suggestions"
        :key="suggestion.id"
        shadow="never"
        class="suggestion-card"
        :class="{ 'is-selected': activeSuggestionId === suggestion.id }"
        tabindex="0"
        @click="applySuggestion(suggestion)"
        @keyup.enter="applySuggestion(suggestion)"
      >
        <div class="suggestion-icon">
          <el-icon><component :is="iconMap[suggestion.icon]" /></el-icon>
        </div>
        <h2>{{ suggestion.title }}</h2>
        <p>{{ suggestion.description }}</p>
        <el-icon class="card-arrow"><Promotion /></el-icon>
      </el-card>
    </div>

    <section class="composer motion-stage motion-stage-4" aria-label="AI 教学任务输入">
      <el-input
        ref="composerInput"
        v-model="prompt"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 7 }"
        resize="none"
        :placeholder="TEACHER_HOME.composer.placeholder"
        @keydown.ctrl.enter="openSessionDialog"
      />
      <div class="composer-toolbar">
        <div class="composer-tools">
          <el-tooltip content="从电脑上传本次备课要使用的资料"><span><el-button text :icon="Paperclip" @click="openUploadDialog">{{ TEACHER_HOME.composer.attach }}</el-button></span></el-tooltip>
          <el-tooltip content="从个人知识库中检索并引用已有资料"><span><el-button text :icon="Collection" @click="openKnowledgeDialog">{{ TEACHER_HOME.composer.knowledge }}</el-button></span></el-tooltip>
          <el-tooltip content="打开语音输入"><span><el-button text circle aria-label="语音输入" @click="voiceDialogVisible = true"><el-icon><Microphone /></el-icon></el-button></span></el-tooltip>
        </div>
        <el-button
          type="primary"
          circle
          :icon="Promotion"
          :class="{ 'is-ready': canSend }"
          :disabled="!canSend"
          :aria-label="TEACHER_HOME.composer.send"
          @click="openSessionDialog"
        />
      </div>
    </section>
    <p class="composer-hint motion-stage motion-stage-4">{{ TEACHER_HOME.composer.hint }}</p>
    <el-dialog v-model="uploadDialogVisible" title="添加资料" width="min(560px, 92vw)">
      <input ref="resourceFileInput" class="resource-file-input" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md" @change="uploadPickedResource" />
      <button
        type="button"
        :class="['upload-dropzone', { 'is-dragging': uploadDragging }]"
        :disabled="resourceUploading"
        @click="triggerResourceUpload"
        @dragenter.prevent="uploadDragging = true"
        @dragover.prevent="uploadDragging = true"
        @dragleave.prevent="uploadDragging = false"
        @drop.prevent="dropResourceFiles"
      >
        <el-icon><Paperclip /></el-icon>
        <strong>{{ uploadDragging ? '松开即可添加资料' : '点击选择或拖入本地资料' }}</strong>
        <span>支持 PDF、Word、PowerPoint、TXT 和 Markdown，可多选</span>
      </button>
      <el-progress v-if="resourceUploading" :percentage="resourceUploadProgress" :show-text="true" />
      <div v-if="uploadedResourceNames.length" class="uploaded-resource-list"><span>已自动引用</span><p v-for="name in uploadedResourceNames" :key="name">{{ name }}</p></div>
      <template #footer><el-button @click="uploadDialogVisible = false">完成</el-button></template>
    </el-dialog>
    <el-dialog v-model="knowledgeDialogVisible" title="引用知识库" width="min(640px, 92vw)">
      <div class="knowledge-picker-header"><p>从已经上传并入库的资料中选择，AI 将结合这些内容生成大纲。</p><el-input v-model="resourceSearch" placeholder="搜索知识库资料" clearable /></div>
      <el-checkbox-group v-model="selectedResourceIds" v-loading="resourcesLoading" class="resource-picker resource-picker-dialog"><el-checkbox v-for="item in filteredAvailableResources" :key="item.id" :value="item.id">{{ item.file_name }}</el-checkbox><el-empty v-if="!resourcesLoading && !filteredAvailableResources.length" description="没有找到可引用的知识资料" /></el-checkbox-group>
      <template #footer><span class="selected-resource-count">已选择 {{ selectedResourceIds.length }} 项</span><el-button type="primary" @click="knowledgeDialogVisible = false">完成引用</el-button></template>
    </el-dialog>
    <el-dialog v-model="voiceDialogVisible" title="语音输入" width="min(480px, 92vw)">
      <div class="voice-panel">
        <div class="voice-orb" aria-hidden="true"><el-icon><Microphone /></el-icon></div>
        <strong>说出你的备课需求</strong>
        <p>例如：“帮我设计一节八年级物理光的折射互动课”。</p>
        <div class="voice-wave" aria-hidden="true"><i v-for="index in 9" :key="index"></i></div>
        <div class="voice-status"><span class="voice-status-dot"></span><span>语音识别能力暂未接入</span><time>00:00</time></div>
        <el-form label-position="top" class="voice-settings">
          <el-form-item label="识别语言">
            <el-select v-model="voiceLanguage">
              <el-option label="普通话" value="zh-CN" />
              <el-option label="英语" value="en-US" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer><el-button @click="voiceDialogVisible = false">取消</el-button><el-tooltip content="等待语音识别服务接入"><span><el-button type="primary" disabled>开始录音</el-button></span></el-tooltip></template>
    </el-dialog>
    <el-dialog v-model="sessionDialogVisible" title="创建 AI 备课会话" width="min(600px, 92vw)" destroy-on-close>
      <el-form label-position="top" class="session-form">
        <div class="session-fields"><el-form-item label="备课主题" required><el-input v-model="sessionForm.title" maxlength="40" show-word-limit /></el-form-item><el-form-item label="学科" required><el-input v-model="sessionForm.subject" placeholder="例如：数学" /></el-form-item><el-form-item label="年级" required><el-input v-model="sessionForm.grade" placeholder="例如：八年级" /></el-form-item></div>
        <el-form-item label="本次需求"><div class="prompt-preview">{{ prompt }}</div></el-form-item>
        <el-form-item label="引用个人资源（可选）"><el-checkbox-group v-model="selectedResourceIds" v-loading="resourcesLoading" class="resource-picker"><el-checkbox v-for="item in availableResources" :key="item.id" :value="item.id">{{ item.file_name }}</el-checkbox><span v-if="!resourcesLoading && !availableResources.length" class="empty-resources">暂无可选资源</span></el-checkbox-group></el-form-item>
      </el-form>
      <template #footer><el-button @click="sessionDialogVisible = false">取消</el-button><el-button type="primary" :loading="sessionCreating" @click="createSessionFromPrompt">开始生成大纲</el-button></template>
    </el-dialog>
  </section>
    <div class="archive-entry"><el-button text size="small" @click="openArchivedProjects">归档项目管理</el-button></div>
    <el-dialog v-model="projectManagerVisible" title="项目管理" width="min(720px, 92vw)">
      <div v-loading="projectManagerLoading" class="managed-project-list">
        <article v-for="project in managedProjects" :key="project.id"><div><strong>{{ project.project_name }}</strong><span>{{ project.project_type || '教学项目' }} · {{ project.status }}</span></div><div class="managed-project-actions"><el-button text size="small" @click="openProject(project)">打开</el-button><el-button text size="small" @click="copyManagedProject(project)">复制</el-button><el-button v-if="project.status !== 'archived'" text size="small" @click="archiveManagedProject(project)">归档</el-button><el-button type="danger" text size="small" @click="deleteManagedProject(project)">删除</el-button></div></article><el-empty v-if="!projectManagerLoading && !managedProjects.length" description="暂无项目" />
      </div>
    </el-dialog>
    <el-dialog v-model="archivedVisible" title="归档项目" width="min(620px, 92vw)"><div v-loading="archivedLoading" class="archived-list"><article v-for="project in archivedProjects" :key="project.id"><div><strong>{{ project.project_name }}</strong><span>{{ project.project_type || '教学项目' }}</span></div><el-button type="primary" plain size="small" @click="restoreArchivedProject(project)">恢复</el-button></article><el-empty v-if="!archivedLoading && !archivedProjects.length" description="暂无归档项目" /></div><template #footer><el-button @click="archivedVisible = false">关闭</el-button></template></el-dialog>
</template>

<style scoped>
.home-welcome {
  width: min(880px, calc(100% - 48px));
  margin: 0 auto;
  padding: clamp(70px, 10vh, 124px) 0 42px;
}

.welcome-copy { max-width: 720px; }
.motion-stage { animation: fadeIn 300ms cubic-bezier(0, 0, 0.2, 1) both; }
.motion-stage-1 { animation-delay: 0ms; }
.motion-stage-2 { animation-delay: 50ms; }
.motion-stage-3 { animation-delay: 100ms; }
.motion-stage-4 { animation-delay: 200ms; }
.eyebrow { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 14px; font-weight: 600; }
h1 { margin: 0; font-size: clamp(36px, 4vw, 48px); line-height: 1.15; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.intro { max-width: 660px; margin: 18px 0 0; color: var(--zh-text-secondary); font-size: 16px; line-height: 1.75; text-wrap: pretty; }
.suggestion-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 38px; }
.suggestion-card { position: relative; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), background-color 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover, .suggestion-card:focus-visible { transform: translateY(-3px); border-color: var(--zh-line-theme20); box-shadow: var(--zh-shadow2); }
.suggestion-card:focus-visible { outline: 3px solid var(--zh-line-theme20); outline-offset: 2px; }
.suggestion-card:active { transform: translateY(-1px) scale(.99); }
.suggestion-card.is-selected { border-color: var(--zh-line-theme50); background: var(--zh-background-weaken); animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card :deep(.el-card__body) { min-height: 150px; padding: 18px; }
.suggestion-icon { width: 36px; height: 36px; display: grid; place-items: center; margin-bottom: 24px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover .suggestion-icon, .suggestion-card:focus-visible .suggestion-icon { transform: scale(1.04); }
.suggestion-card h2 { margin: 0; font-size: 15px; font-weight: 600; }
.suggestion-card p { margin: 7px 24px 0 0; color: var(--zh-text-caption); font-size: 12px; line-height: 1.6; }
.card-arrow { position: absolute; right: 16px; bottom: 18px; color: var(--zh-text-disabled); transform: rotate(-45deg); transition: color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.suggestion-card:hover .card-arrow, .suggestion-card:focus-visible .card-arrow { color: var(--zh-text-theme); transform: rotate(-45deg) translateX(3px); }
.recent-projects { margin-top: 30px; }.recent-projects-heading { display: flex; align-items: baseline; justify-content: space-between; }.recent-projects-heading h2 { margin: 0; font-size: 16px; }.recent-projects-heading span { color: var(--zh-text-caption); font-size: 12px; }.project-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }.project-card { display: flex; min-width: 0; flex-direction: column; gap: 5px; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); color: var(--zh-text-primary); background: var(--zh-background-primary); text-align: left; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1); }.project-card:hover, .project-card:focus-visible { transform: translateY(-2px); border-color: var(--zh-line-theme50); background: var(--zh-background-weaken); box-shadow: var(--zh-shadow1); }.project-card:active { transform: translateY(-1px) scale(.99); transition-duration: 150ms; }.project-card strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.project-card span { color: var(--zh-text-caption); font-size: 11px; }
.project-skeleton { min-width: 0; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }.project-skeleton-title { width: 76%; }.project-skeleton-meta { width: 52%; margin-top: 8px; }
.composer { margin-top: 24px; padding: 9px 10px 10px; border: 1px solid var(--zh-line-heavier); border-radius: var(--zh-radius16); background: var(--zh-background-input); box-shadow: var(--zh-shadow1); transition: border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer:focus-within { border-color: var(--zh-line-theme50); box-shadow: 0 0 0 3px var(--zh-line-theme20), var(--zh-shadow2); }
.composer :deep(.el-textarea__inner) { min-height: 78px !important; padding: 10px 12px 6px; border: 0; background: transparent; box-shadow: none; color: var(--zh-text-primary); font-size: 15px; line-height: 1.65; }
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 2px 2px 0; }
.composer-tools { display: flex; align-items: center; }
.composer-tools :deep(.el-button) { color: var(--zh-text-secondary); }
.composer-toolbar :deep(.el-button.is-ready) { animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.composer-hint { margin: 10px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }
.session-fields { display:grid; grid-template-columns: 1.5fr 1fr 1fr; gap:12px; }.session-fields :deep(.el-form-item){margin-bottom:0}.prompt-preview{width:100%;padding:10px 12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);line-height:1.65;white-space:pre-wrap}.resource-picker{display:grid;gap:8px;max-height:160px;overflow:auto;padding:10px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.empty-resources{color:var(--zh-text-caption);font-size:12px}
.resource-file-input{display:none}.resource-picker-dialog{max-height:280px;margin-top:12px}.upload-dropzone{width:100%;min-height:180px;display:grid;place-items:center;align-content:center;gap:9px;padding:24px;border:1px dashed var(--zh-line-theme50);border-radius:var(--zh-radius12);color:var(--zh-text-theme);background:var(--zh-background-weaken);cursor:pointer;transition:border-color 200ms cubic-bezier(.4,0,.2,1),background-color 200ms cubic-bezier(.4,0,.2,1),transform 200ms cubic-bezier(.4,0,.2,1),box-shadow 200ms cubic-bezier(.4,0,.2,1)}.upload-dropzone:hover,.upload-dropzone:focus-visible{border-color:var(--zh-line-theme);background:var(--zh-background-option-on);transform:translateY(-1px)}.upload-dropzone.is-dragging{border-color:var(--zh-line-theme);background:var(--zh-background-option-on);box-shadow:0 0 0 4px var(--zh-line-theme20);transform:scale(1.01)}.upload-dropzone:disabled{cursor:wait;opacity:.65}.upload-dropzone .el-icon{font-size:28px}.upload-dropzone strong{color:var(--zh-text-primary);font-size:16px}.upload-dropzone span{color:var(--zh-text-caption);font-size:12px}.uploaded-resource-list{display:grid;gap:6px;margin-top:14px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-light)}.uploaded-resource-list>span{color:var(--zh-text-caption);font-size:12px}.uploaded-resource-list p{margin:0;color:var(--zh-text-secondary);font-size:13px}.knowledge-picker-header{display:grid;grid-template-columns:minmax(0,1fr) 240px;align-items:center;gap:16px}.knowledge-picker-header p{margin:0;color:var(--zh-text-secondary);font-size:13px;line-height:1.6}.selected-resource-count{display:inline-block;margin-right:16px;color:var(--zh-text-caption);font-size:12px}
.voice-panel{display:grid;justify-items:center;padding:8px 8px 0;text-align:center}.voice-orb{width:78px;height:78px;display:grid;place-items:center;margin:4px 0 18px;border:1px solid var(--zh-line-theme20);border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);box-shadow:0 0 0 10px var(--zh-background-weaken)}.voice-orb .el-icon{font-size:30px}.voice-panel>strong{font-size:18px}.voice-panel>p{max-width:350px;margin:8px 0 20px;color:var(--zh-text-secondary);font-size:13px;line-height:1.65}.voice-wave{height:42px;display:flex;align-items:center;gap:5px}.voice-wave i{width:3px;height:10px;border-radius:999px;background:var(--zh-line-theme50)}.voice-wave i:nth-child(2),.voice-wave i:nth-child(8){height:16px}.voice-wave i:nth-child(3),.voice-wave i:nth-child(7){height:24px}.voice-wave i:nth-child(4),.voice-wave i:nth-child(6){height:32px}.voice-wave i:nth-child(5){height:40px}.voice-status{width:100%;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;margin-top:16px;padding:12px 14px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-light);font-size:12px;text-align:left}.voice-status-dot{width:7px;height:7px;border-radius:50%;background:var(--zh-text-disabled)}.voice-status time{color:var(--zh-text-caption);font-family:var(--zh-font-number)}.voice-settings{width:100%;margin-top:18px;text-align:left}.voice-settings :deep(.el-select){width:100%}

@media (max-width: 680px) {
  .home-welcome { width: min(100% - 28px, 540px); padding-top: 54px; }
  .suggestion-grid, .project-grid { grid-template-columns: 1fr; }
  .suggestion-card :deep(.el-card__body) { min-height: 118px; }
  .suggestion-icon { margin-bottom: 16px; }
  .session-fields { grid-template-columns:1fr; }
  .knowledge-picker-header { grid-template-columns:1fr; }
}
.archive-entry{display:flex;justify-content:center;margin-top:10px}.archived-list{display:grid;gap:10px}.archived-list article{display:flex;align-items:center;justify-content:space-between;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.archived-list article div{display:flex;flex-direction:column;gap:4px}.archived-list strong{font-size:13px}.archived-list span{color:var(--zh-text-caption);font-size:11px}
.managed-project-list{display:grid;gap:10px}.managed-project-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.managed-project-list article>div:first-child{display:grid;gap:4px;min-width:0}.managed-project-list strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.managed-project-list span{color:var(--zh-text-caption);font-size:12px}.managed-project-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:2px}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}
</style>
