<!--
  [数据交互说明]
  - 导入: 首页配置、Element Plus 图标
  - 输出: 教师端默认首页内容，由 `TeacherLayout.vue` 承载全局导航
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
import { createProject, listProjects } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const canSend = computed(() => prompt.value.trim().length > 0)
const iconMap = { Presentation: Monitor, Document, MagicStick }
const projects = ref([])

const openProject = (project) => router.push({
  path: '/main/workspace',
  query: { ...(route.query.preview ? { preview: '1' } : {}), projectId: project.id },
})

const loadProjects = async () => {
  try {
    const result = await listProjects({ page: 1, size: 4, status: 'draft' })
    projects.value = result?.data?.records || result?.data?.list || result?.data?.items || []
  } catch {
    projects.value = []
  }
}

/** 将推荐任务写入输入框。 */
const applySuggestion = (suggestion) => {
  prompt.value = suggestion.prompt
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

onMounted(loadProjects)
</script>

<template>
  <section class="home-welcome">
    <div class="welcome-copy">
      <p class="eyebrow">{{ TEACHER_HOME.greeting.eyebrow }}</p>
      <h1>{{ TEACHER_HOME.greeting.title }}</h1>
      <p class="intro">{{ TEACHER_HOME.greeting.description }}</p>
    </div>

    <section v-if="projects.length" class="recent-projects" aria-label="最近项目">
      <div class="recent-projects-heading"><h2>最近项目</h2><span>从项目继续创作</span></div>
      <div class="project-grid">
        <button v-for="project in projects" :key="project.id" type="button" class="project-card" @click="openProject(project)">
          <strong>{{ project.project_name }}</strong>
          <span>{{ project.project_type || '教学项目' }} · v{{ project.current_version || 1 }}</span>
        </button>
      </div>
    </section>

    <div class="suggestion-grid">
      <el-card
        v-for="suggestion in TEACHER_HOME.suggestions"
        :key="suggestion.id"
        shadow="never"
        class="suggestion-card"
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

    <section class="composer" aria-label="AI 教学任务输入">
      <el-input
        v-model="prompt"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 7 }"
        resize="none"
        :placeholder="TEACHER_HOME.composer.placeholder"
        @keydown.ctrl.enter="createProjectFromPrompt"
      />
      <div class="composer-toolbar">
        <div class="composer-tools">
          <el-tooltip content="资料上传将在会话接口接入后开放"><span><el-button text :icon="Paperclip" disabled>{{ TEACHER_HOME.composer.attach }}</el-button></span></el-tooltip>
          <el-tooltip content="知识库选择将在会话接口接入后开放"><span><el-button text :icon="Collection" disabled>{{ TEACHER_HOME.composer.knowledge }}</el-button></span></el-tooltip>
          <el-tooltip content="语音输入暂未接入"><span><el-button text circle aria-label="语音输入" disabled><el-icon><Microphone /></el-icon></el-button></span></el-tooltip>
        </div>
        <el-button
          type="primary"
          circle
          :icon="Promotion"
          :disabled="!canSend"
          :aria-label="TEACHER_HOME.composer.send"
          @click="createProjectFromPrompt"
        />
      </div>
    </section>
    <p class="composer-hint">{{ TEACHER_HOME.composer.hint }}</p>
  </section>
</template>

<style scoped>
.home-welcome {
  width: min(880px, calc(100% - 48px));
  margin: 0 auto;
  padding: clamp(70px, 10vh, 124px) 0 42px;
}

.welcome-copy { max-width: 720px; }
.eyebrow { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 14px; font-weight: 600; }
h1 { margin: 0; font-size: clamp(36px, 4vw, 48px); line-height: 1.15; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.intro { max-width: 660px; margin: 18px 0 0; color: var(--zh-text-secondary); font-size: 16px; line-height: 1.75; text-wrap: pretty; }
.suggestion-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 38px; }
.suggestion-card { position: relative; cursor: pointer; transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease; }
.suggestion-card:hover, .suggestion-card:focus-visible { transform: translateY(-3px); border-color: var(--zh-line-theme20); box-shadow: var(--zh-shadow2); outline: none; }
.suggestion-card:active { transform: translateY(-1px) scale(.99); }
.suggestion-card :deep(.el-card__body) { min-height: 150px; padding: 18px; }
.suggestion-icon { width: 36px; height: 36px; display: grid; place-items: center; margin-bottom: 24px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.suggestion-card h2 { margin: 0; font-size: 15px; font-weight: 600; }
.suggestion-card p { margin: 7px 24px 0 0; color: var(--zh-text-caption); font-size: 12px; line-height: 1.6; }
.card-arrow { position: absolute; right: 16px; bottom: 18px; color: var(--zh-text-disabled); transform: rotate(-45deg); }
.recent-projects { margin-top: 30px; }.recent-projects-heading { display: flex; align-items: baseline; justify-content: space-between; }.recent-projects-heading h2 { margin: 0; font-size: 16px; }.recent-projects-heading span { color: var(--zh-text-caption); font-size: 12px; }.project-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }.project-card { display: flex; min-width: 0; flex-direction: column; gap: 5px; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); color: var(--zh-text-primary); background: var(--zh-background-primary); text-align: left; cursor: pointer; }.project-card:hover { border-color: var(--zh-line-theme50); background: var(--zh-background-weaken); }.project-card strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.project-card span { color: var(--zh-text-caption); font-size: 11px; }
.composer { margin-top: 24px; padding: 9px 10px 10px; border: 1px solid var(--zh-line-heavier); border-radius: var(--zh-radius16); background: var(--zh-background-input); box-shadow: var(--zh-shadow1); transition: border-color 200ms ease, box-shadow 200ms ease; }
.composer:focus-within { border-color: var(--zh-line-theme50); box-shadow: 0 0 0 3px var(--zh-line-theme20), var(--zh-shadow2); }
.composer :deep(.el-textarea__inner) { min-height: 78px !important; padding: 10px 12px 6px; border: 0; background: transparent; box-shadow: none; color: var(--zh-text-primary); font-size: 15px; line-height: 1.65; }
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 2px 2px 0; }
.composer-tools { display: flex; align-items: center; }
.composer-tools :deep(.el-button) { color: var(--zh-text-secondary); }
.composer-hint { margin: 10px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }

@media (max-width: 680px) {
  .home-welcome { width: min(100% - 28px, 540px); padding-top: 54px; }
  .suggestion-grid, .project-grid { grid-template-columns: 1fr; }
  .suggestion-card :deep(.el-card__body) { min-height: 118px; }
  .suggestion-icon { margin-bottom: 16px; }
}
</style>
