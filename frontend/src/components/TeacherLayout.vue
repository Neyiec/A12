<!--
  [数据交互说明]
  - 导入: 教师端导航配置、Vue Router、Element Plus 图标、`listAiSessions`（GET /api/v1/ai/sessions）会话历史、`latestSessionPush`（ChatView 推送的最新会话）
  - 输出: 教师端所有独立页面共用的顶部导航；教学助手独享会话侧栏
-->
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Bell, ChatDotRound, Delete, Download, EditPen, FolderOpened, Grid,
  Moon, MoreFilled, Plus, Setting, Sunny,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'
import { requestNewChat, latestSessionPush, openChatSession } from '../config/teacherChat.config.js'
import { getCurrentUser } from '../apis/login.js'
import { deleteAiSession, listAiSessions, updateAiSession } from '../apis/teacher.js'
import { useUserStore } from '../storage/user.js'

const route = useRoute()
const router = useRouter()
const isDark = ref(document.documentElement.dataset.theme === 'dark')
const settingsReturnTarget = ref('/main')
const userStore = useUserStore()
/** 侧栏最近对话历史，数据来自 GET /api/v1/ai/sessions */
const history = ref([])
/** 当前打开的历史会话 id（用于侧栏高亮） */
const activeHistoryId = ref(null)
const iconMap = { ChatDotRound, FolderOpened, Grid, Download }
const routeMap = {
  home: '/main',
  resources: '/main/resources',
  community: '/main/community',
  exports: '/main/exports',
}
const activeMenu = computed(() => route.meta.menu || 'home')
const isWorkspace = computed(() => route.path === '/main/workspace')
const isTeachingAssistant = computed(() => route.path === '/main')
const avatarText = computed(() => (userStore.userInfo?.real_name || userStore.userInfo?.username || TEACHER_HOME.teacher.name).slice(0, 1))
const avatarUrl = computed(() => userStore.userInfo?.avatar || undefined)
const isSettings = computed(() => route.path === '/main/settings')
const settingsActionLabel = computed(() => isSettings.value ? '返回之前页面' : '打开账号设置')
const viewTransitionName = computed(() => route.path === '/main' ? 'teacher-home-view' : 'teacher-view')

/** 跳转到教师端目标功能模块。 */
const handleMenuSelect = (index) => {
  const target = routeMap[index]
  if (target) router.push({ path: target, query: route.query.preview ? { preview: '1' } : {} })
}

/** 点击"新建对话"：无论当前在哪个页面，都跳回教师端首页的初始（欢迎）视图。 */
const handleNewChat = () => {
  // 不在首页时先导航到首页，TeacherHome 以欢迎视图重新挂载即可
  if (route.path !== '/main') {
    router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
    return
  }
  // 已在首页时通知 TeacherHome 关闭聊天视图，回到欢迎页
  requestNewChat.value = true
}

/** 移动端没有常驻侧栏，通过顶部菜单访问新建对话和最近会话。 */
const handleMobileHistoryCommand = (command) => {
  if (command === 'new') {
    handleNewChat()
    return
  }
  const item = history.value.find((entry) => String(entry.id) === String(command))
  if (item) openHistorySession(item)
}

/** 切换全局亮暗主题。 */
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light'
}

/** 设置与头像共用入口：首次进入设置，再次点击返回来源页面。 */
const toggleSettings = () => {
  if (isSettings.value) {
    const target = settingsReturnTarget.value === '/main' && route.query.preview
      ? '/main?preview=1'
      : settingsReturnTarget.value
    settingsReturnTarget.value = '/main'
    router.push(target)
    return
  }

  settingsReturnTarget.value = route.fullPath
  router.push({
    path: '/main/settings',
    query: route.query.preview ? { preview: '1' } : {},
  })
}

onMounted(async () => {
  if (!userStore.token) return
  try {
    const res = await getCurrentUser()
    if (res.code === 0 || res.code === 200) userStore.setUserInfo(res.data)
  } catch { /* 请求层会统一处理失效会话 */ }
  loadHistory()
})

/** 拉取会话历史并映射为侧栏最近对话的展示数据。 */
const loadHistory = async () => {
  try {
    const res = await listAiSessions()
    const sessions = (res.code === 0 || res.code === 200) ? res.data : []
    // 侧栏仅保留展示所需的最小字段，完整消息在点击时通过 GET 获取
    history.value = (Array.isArray(sessions) ? sessions : []).map((item) => ({
      id: item.id,
      title: item.title,
      time: formatRelativeTime(item.updated_at),
    }))
  } catch { /* 请求层会统一处理失效会话 */ }
}

/** 点击历史对话：跳回首页并通知首页打开对应会话，由 ChatView 依据 sessionId 拉取消息恢复历史。 */
const openHistorySession = (item) => {
  activeHistoryId.value = String(item.id)
  if (route.path !== '/main') {
    router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
  }
  openChatSession.value = { id: item.id, title: item.title }
}

/** 处理历史记录行的操作菜单命令：删除弹出危险确认框，重命名弹出输入框。 */
const handleHistoryCommand = (command, item) => {
  if (command === 'delete') confirmDeleteHistory(item)
  if (command === 'rename') renameHistory(item)
}

/** 弹出危险确认框，确认后调用删除接口并从侧栏移除对应会话。 */
const confirmDeleteHistory = (item) => {
  ElMessageBox.confirm('删除后不可恢复，确定要删除该历史会话吗？', '删除历史记录', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'is-danger',
  }).then(async () => {
    await deleteAiSession(item.id)
    history.value = history.value.filter((h) => String(h.id) !== String(item.id))
    // 若删除的是当前高亮会话，同步清除高亮
    if (activeHistoryId.value === String(item.id)) activeHistoryId.value = null
  }).catch(() => {})
}

/** 弹出输入框，确认后调用重命名接口并同步侧栏标题（含当前打开会话标题）。 */
const renameHistory = (item) => {
  ElMessageBox.prompt('请输入新的会话名称', '重命名历史记录', {
    inputValue: item.title,
    confirmButtonText: '保存',
    cancelButtonText: '取消',
  }).then(async ({ value }) => {
    const newTitle = (value || '').trim()
    if (!newTitle) return
    await updateAiSession(item.id, { title: newTitle })
    item.title = newTitle
    if (String(openChatSession.value?.id) === String(item.id)) {
      openChatSession.value = { ...openChatSession.value, title: newTitle }
    }
  }).catch(() => {})
}

/** 将 ISO 时间格式化为"今天/昨天/M 月 D 日"。 */
const formatRelativeTime = (iso) => {
  if (!iso) return ''
  const date = new Date(iso)
  const startOfToday = (new Date()).setHours(0, 0, 0, 0)
  const diffDays = Math.round((startOfToday - new Date(date).setHours(0, 0, 0, 0)) / 86400000)
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`
}

/** 监听 ChatView 推送的最新会话，去重后插入历史列表顶部（页面未刷新时的暂时性显示）。 */
watch(latestSessionPush, (session) => {
  if (!session || !session.id) return
  const index = history.value.findIndex((item) => String(item.id) === String(session.id))
  if (index >= 0) history.value.splice(index, 1)
  history.value.unshift({
    id: session.id,
    title: session.title,
    time: formatRelativeTime(session.updated_at),
  })
})
</script>

<template>
  <div :class="['teacher-shell', { 'workspace-mode': isWorkspace, 'assistant-mode': isTeachingAssistant }]">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <header v-if="!isWorkspace" class="teacher-topbar">
      <button type="button" class="brand" aria-label="返回教学助手" @click="handleMenuSelect('home')">
        <span class="app-brand-icon" aria-hidden="true">
          <img src="/branding/logo-intro.png" alt="" />
        </span>
        <strong class="app-brand-name">智核</strong>
      </button>

      <nav class="top-navigation" aria-label="教师端主导航">
        <button
          v-for="item in TEACHER_HOME.navigation"
          :key="item.index"
          type="button"
          :class="['top-nav-item', { 'is-active': activeMenu === item.index }]"
          :aria-current="activeMenu === item.index ? 'page' : undefined"
          @click="handleMenuSelect(item.index)"
        >
          <el-icon><component :is="iconMap[item.icon]" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="topbar-actions">
        <span v-if="isTeachingAssistant" class="status-dot"><i></i> 智能体在线</span>
        <el-dropdown
          v-if="isTeachingAssistant"
          class="mobile-history-menu"
          trigger="click"
          placement="bottom-end"
          @command="handleMobileHistoryCommand"
        >
          <el-button text circle class="icon-action" aria-label="打开最近对话"><el-icon><ChatDotRound /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="new"><el-icon><Plus /></el-icon>新建对话</el-dropdown-item>
              <el-dropdown-item
                v-for="item in history.slice(0, 10)"
                :key="item.id"
                :command="String(item.id)"
                divided
              >
                {{ item.title }} · {{ item.time }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button
          text
          circle
          class="icon-action theme-toggle"
          aria-label="切换主题"
          :aria-pressed="isDark"
          @click="toggleTheme"
        >
          <span :class="['theme-orbit', { 'is-dark': isDark }]" aria-hidden="true">
            <span class="theme-orbit-track">
              <el-icon class="theme-orbit-moon"><Moon /></el-icon>
              <el-icon class="theme-orbit-sun"><Sunny /></el-icon>
            </span>
          </span>
        </el-button>
        <el-button text circle class="icon-action notification-button" aria-label="通知"><el-icon><Bell /></el-icon></el-button>
        <button type="button" class="avatar-button" :aria-label="settingsActionLabel" @click="toggleSettings">
          <el-avatar :size="34" :src="avatarUrl">{{ avatarText }}</el-avatar>
        </button>
      </div>
    </header>

    <aside v-if="isTeachingAssistant && !isWorkspace" class="teacher-sidebar" aria-label="教学助手对话记录">

      <el-button type="primary" class="new-chat-button" :icon="Plus" @click="handleNewChat">
        {{ TEACHER_HOME.actions.newChat }}
      </el-button>

      <section class="history" aria-labelledby="history-title">
        <!-- 标题行固定在顶部，不随历史条目滚动；仅下方条目区域可滚动 -->
        <div class="section-label-row">
          <span id="history-title">{{ TEACHER_HOME.historyTitle }}</span>
        </div>
        <div class="history-scroll">
          <div
            v-for="item in history"
            :key="item.id"
            class="history-item"
            :class="{ 'is-active': activeHistoryId === String(item.id) }"
          >
            <button type="button" class="history-item-main" @click="openHistorySession(item)">
              <span>{{ item.title }}</span><small>{{ item.time }}</small>
            </button>
            <el-dropdown
              class="history-item-actions"
              trigger="click"
              placement="bottom-end"
              @command="(command) => handleHistoryCommand(command, item)"
            >
              <el-button text circle size="small" aria-label="历史会话更多操作">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">
                    <el-icon><EditPen /></el-icon>重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided style="color: var(--zh-red)">
                    <el-icon><Delete /></el-icon>删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </section>
      
      <footer class="teacher-profile">
        <button type="button" class="avatar-button" :aria-label="settingsActionLabel" @click="toggleSettings">
          <el-avatar :size="38" shape="square" :src="avatarUrl">{{ avatarText }}</el-avatar>
        </button>
        <div class="profile-copy"><strong>{{ userStore.userInfo?.real_name || TEACHER_HOME.teacher.name }}</strong><span>{{ userStore.userInfo?.user_type === 'admin' ? '管理员' : TEACHER_HOME.teacher.role }}</span></div>
        <el-button text circle class="icon-action settings-button" :aria-label="settingsActionLabel" @click="toggleSettings"><el-icon><Setting /></el-icon></el-button>
      </footer>
    </aside>

    <main id="main-content" class="teacher-main">
      <router-view v-slot="{ Component, route: viewRoute }">
        <Transition :name="viewTransitionName" mode="out-in" appear>
          <div
            :key="viewRoute.path"
            :class="['teacher-view-frame', { 'workspace-view-frame': viewRoute.path === '/main/workspace' }]"
          >
            <component :is="Component" />
          </div>
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.teacher-shell { min-height: 100dvh; display: grid; grid-template-rows: 68px minmax(0, 1fr); grid-template-areas: "topbar" "main"; background: var(--zh-background-primary); color: var(--zh-text-primary); }
.teacher-shell.assistant-mode { grid-template-columns: 260px minmax(0, 1fr); grid-template-areas: "topbar topbar" "sidebar main"; }
.teacher-shell.workspace-mode { display: block; }
.teacher-sidebar { grid-area: sidebar; position: sticky; top: 68px; height: calc(100dvh - 68px); display: flex; flex-direction: column; padding: 18px 14px 14px; background: var(--zh-background-pc-sidebar); border-right: 1px solid var(--zh-line-parting); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0; border: 0; color: var(--zh-text-primary); background: transparent; font: inherit; text-align: left; cursor: pointer; }
.app-brand-icon { position: relative; width: 40px; height: 40px; display: block; flex: 0 0 auto; overflow: hidden; border-radius: var(--zh-radius10); background: white; box-shadow: 0 8px 18px -8px rgb(37 99 235 / 40%); }
.app-brand-icon img { position: absolute; top: 50%; left: 50%; width: 71px; height: 71px; max-width: none; object-fit: cover; transform: translate(-50%, -50%); }
.app-brand-name { color: var(--zh-text-primary); font-size: 18px; font-weight: 750; letter-spacing: var(--zh-tracking-wide); white-space: nowrap; }
.brand-copy, .profile-copy { min-width: 0; display: flex; flex-direction: column; }
.brand-copy strong { font-size: 18px; letter-spacing: var(--zh-tracking-wide); }
.brand-copy span, .profile-copy span { margin-top: 2px; color: var(--zh-text-caption); font-size: 12px; }
.new-chat-button { width: 100%; height: 42px; margin-bottom: 14px; border-color: var(--zh-background-button); border-radius: var(--zh-radius8); color: var(--zh-text-white); background: var(--zh-background-button); font-weight: 600; transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.new-chat-button:hover, .new-chat-button:focus-visible { border-color: var(--zh-background-button-hover); color: var(--zh-text-white); background: var(--zh-background-button-hover); }
.new-chat-button:active { transform: translateY(1px); }
.new-chat-button :deep(.el-icon) { transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.new-chat-button:hover :deep(.el-icon) { transform: rotate(90deg); }
.new-chat-button:active :deep(.el-icon) { transform: rotate(90deg) scale(.92); transition-duration: 150ms; }
.history { min-height: 0; margin-top: 18px; display: flex; flex: 1; flex-direction: column; }
.history-scroll { min-height: 0; flex: 1; overflow-y: auto; }
.section-label-row { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; padding: 0 8px 5px; color: var(--zh-text-caption); font-size: 12px; }
.history-item { width: 100%; display: flex; align-items: center; gap: 4px; padding: 4px 6px 4px 8px; border-radius: var(--zh-radius8); transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.history-item:hover, .history-item:focus-within { background: var(--zh-background-option); }
.history-item.is-active { background: var(--zh-background-option-on); }
.history-item-main { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; padding: 6px 2px; border: 0; background: transparent; color: var(--zh-text-secondary); text-align: left; cursor: pointer; transition: color 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.history-item:hover .history-item-main { color: var(--zh-text-primary); }
.history-item.is-active .history-item-main { color: var(--zh-text-theme); font-weight: 600; }
.history-item-main span { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.history-item-main small { color: var(--zh-text-caption); font-size: 11px; }
.history-item-actions { flex: 0 0 auto; opacity: 0; pointer-events: none; transition: opacity 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.history-item:hover .history-item-actions, .history-item:focus-within .history-item-actions { opacity: 1; pointer-events: auto; }
.history-item-actions :deep(.el-button) { color: var(--zh-text-caption); }
.history-item-actions :deep(.el-button .el-icon) { font-size: 16px; }
.teacher-profile { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; margin-top: auto; padding: 13px 8px 0; border-top: 1px solid var(--zh-line-border); }
.teacher-profile :deep(.el-avatar), .teacher-topbar :deep(.el-avatar) { color: white; background: var(--zh-theme-primary); }
.avatar-button { display: grid; place-items: center; padding: 0; border: 0; border-radius: var(--zh-radius8); background: transparent; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.avatar-button:hover, .avatar-button:focus-visible { transform: translateY(-1px) scale(1.04); }
.avatar-button:active { transform: scale(.96); transition-duration: 150ms; }
.profile-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.teacher-main { grid-area: main; min-width: 0; min-height: calc(100dvh - 68px); background: radial-gradient(circle at 50% 18%, rgb(37 99 235 / 5%), transparent 32%), var(--zh-background-primary); }
.teacher-topbar { grid-area: topbar; position: sticky; z-index: 100; top: 0; height: 68px; display: grid; grid-template-columns: minmax(160px, 1fr) auto minmax(160px, 1fr); align-items: center; gap: 24px; padding: 0 24px; border-bottom: 1px solid var(--zh-line-parting); background: color-mix(in srgb, var(--zh-background-primary) 90%, transparent); backdrop-filter: blur(14px); }
.top-navigation { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 4px; border: 1px solid var(--zh-line-parting); border-radius: 14px; background: var(--zh-background-light); }
.top-nav-item { min-height: 40px; display: inline-flex; align-items: center; gap: 7px; padding: 0 16px; border: 0; border-radius: 10px; color: var(--zh-text-secondary); background: transparent; font: inherit; font-size: 14px; white-space: nowrap; cursor: pointer; transition: color 180ms ease, background-color 180ms ease, box-shadow 180ms ease, transform 180ms ease; }
.top-nav-item:hover, .top-nav-item:focus-visible { color: var(--zh-text-primary); background: var(--zh-background-primary); transform: translateY(-1px); }
.top-nav-item.is-active { color: var(--zh-text-theme); background: var(--zh-background-primary); box-shadow: var(--zh-shadow1); font-weight: 650; }
.top-nav-item .el-icon { font-size: 16px; }
.status-dot { margin-right: 4px; color: var(--zh-text-caption); font-size: 12px; white-space: nowrap; }
.status-dot i { width: 7px; height: 7px; display: inline-block; margin-right: 5px; border-radius: 50%; background: var(--zh-green); animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1) both; }
.topbar-actions { display: flex; align-items: center; justify-self: end; gap: 8px; }
.mobile-history-menu { display: none; }
.topbar-actions .icon-action, .topbar-actions > .avatar-button { width: 36px; height: 36px; flex: 0 0 36px; margin: 0; }
.topbar-actions :deep(.el-button .el-icon), .teacher-profile :deep(.el-button .el-icon) { font-size: 18px; }
.icon-action { transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.icon-action:hover, .icon-action:focus-visible { transform: translateY(-1px); }
.icon-action:active { transform: scale(.96); }
.settings-button :deep(.el-icon) { transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1); }
.settings-button:hover :deep(.el-icon), .settings-button:focus-visible :deep(.el-icon) { transform: rotate(60deg) scale(1.06); }
.settings-button:active :deep(.el-icon) { transform: rotate(60deg) scale(.94); transition-duration: 150ms; }
.notification-button:hover :deep(.el-icon), .notification-button:focus-visible :deep(.el-icon) { animation: bellRing 300ms cubic-bezier(0.4, 0, 0.2, 1); }
.theme-orbit { position: relative; width: 20px; height: 20px; display: block; overflow: hidden; border-radius: 50%; }
.theme-orbit-track { position: absolute; top: 0; left: 0; width: 20px; height: 46px; transform: rotate(0); transform-origin: 10px 23px; transition: transform 500ms cubic-bezier(0.4, 0, 0.2, 1); }
.theme-orbit.is-dark .theme-orbit-track { transform: rotate(180deg); }
.theme-toggle:hover .theme-orbit-track, .theme-toggle:focus-visible .theme-orbit-track { transform: rotate(12deg) scale(1.04); }
.theme-toggle:hover .theme-orbit.is-dark .theme-orbit-track, .theme-toggle:focus-visible .theme-orbit.is-dark .theme-orbit-track { transform: rotate(192deg) scale(1.04); }
.theme-orbit :deep(.el-icon) { position: absolute; left: 1px; width: 18px; height: 18px; }
.theme-orbit-moon { top: 1px; color: var(--zh-text-secondary); }
.theme-orbit-sun { bottom: 1px; color: var(--zh-text-theme); }
.teacher-view-frame { min-width: 0; }
.workspace-view-frame { min-height: 100dvh; }
.teacher-view-enter-active { transition: opacity 300ms cubic-bezier(0, 0, 0.2, 1), transform 300ms cubic-bezier(0, 0, 0.2, 1); }
.teacher-view-enter-from { opacity: 0; transform: translateY(8px); }
.teacher-view-enter-to { opacity: 1; transform: translateY(0); }

@media (max-width: 900px) {
  .teacher-shell.assistant-mode { grid-template-columns: 76px minmax(0, 1fr); }
  .teacher-sidebar { padding-inline: 10px; }
  .teacher-topbar { grid-template-columns: auto 1fr auto; gap: 12px; padding-inline: 16px; }
  .brand-copy span, .history, .profile-copy, .new-chat-button :deep(span), .status-dot { display: none; }
  .app-brand-icon { width: 38px; height: 38px; }
  .app-brand-icon img { width: 68px; height: 68px; }
  .new-chat-button { width: 44px; margin-inline: auto; padding: 0; }
  .top-navigation { justify-self: center; }
  .top-nav-item { padding: 0 11px; }
  .top-nav-item span { display: none; }
  .teacher-profile { display: flex; justify-content: center; padding-inline: 0; }
  .teacher-profile > :last-child { display: none; }
}
@media (max-width: 680px) {
  .teacher-shell, .teacher-shell.assistant-mode { display: grid; grid-template-columns: 1fr; grid-template-rows: 56px minmax(0, 1fr); grid-template-areas: "topbar" "main"; }
  .teacher-sidebar { display: none; }
  .teacher-topbar { height: 56px; min-height: 56px; grid-template-columns: 1fr auto; gap: 10px; padding: 4px 12px; }
  .app-brand-icon { width: 34px; height: 34px; }
  .app-brand-icon img { width: 61px; height: 61px; }
  .app-brand-name { font-size: 16px; }
  .brand-copy strong { font-size: 16px; }
  .top-navigation { position: fixed; z-index: 120; right: 8px; bottom: max(8px, env(safe-area-inset-bottom)); left: 8px; width: auto; min-height: 56px; justify-content: stretch; overflow-x: visible; border-radius: 16px; box-shadow: 0 12px 32px rgb(15 23 42 / 18%); }
  .top-nav-item { min-width: 0; flex: 1; flex-direction: column; gap: 2px; padding: 5px 3px; justify-content: center; font-size: 10px; line-height: 1.1; }
  .top-nav-item span { display: inline; }
  .top-nav-item .el-icon { font-size: 18px; }
  .topbar-actions { grid-column: 2; }
  .mobile-history-menu { display: inline-flex; }
  .notification-button { display: none; }
  .teacher-main { min-height: calc(100dvh - 56px); padding-bottom: calc(76px + env(safe-area-inset-bottom)); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .72; transform: scale(1.35); }
}

@keyframes bellRing {
  0%, 100% { transform: rotate(0); }
  30% { transform: rotate(10deg); }
  60% { transform: rotate(-8deg); }
}
</style>
