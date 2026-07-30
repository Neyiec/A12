<!--
  [数据交互说明]
  - 导入: 教师端导航配置、Vue Router、Element Plus 图标
  - 输出: 教师端所有独立页面共用的侧栏与顶栏布局
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell, ChatDotRound, Download, FolderOpened, Grid,
  Moon, MoreFilled, Plus, Setting, Sunny,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'
import { getCurrentUser } from '../apis/login.js'
import { useUserStore } from '../storage/user.js'

const route = useRoute()
const router = useRouter()
const isDark = ref(document.documentElement.dataset.theme === 'dark')
const settingsReturnTarget = ref('/main')
const userStore = useUserStore()
const iconMap = { ChatDotRound, FolderOpened, Grid, Download }
const routeMap = {
  home: '/main',
  resources: '/main/resources',
  community: '/main/community',
  exports: '/main/exports',
}
const activeMenu = computed(() => route.meta.menu || 'home')
const isWorkspace = computed(() => route.path === '/main/workspace')
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
})
</script>

<template>
  <div :class="['teacher-shell', { 'workspace-mode': isWorkspace }]">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <aside v-if="!isWorkspace" class="teacher-sidebar" aria-label="教师端主导航">
      <header class="brand">
        <div class="brand-mark" aria-hidden="true">智</div>
        <div class="brand-copy">
          <strong>{{ TEACHER_HOME.brand.name }}</strong>
          <span>{{ TEACHER_HOME.brand.subtitle }}</span>
        </div>
      </header>
      <el-button type="primary" class="new-chat-button" :icon="Plus" @click="router.push('/main')">
        {{ TEACHER_HOME.actions.newChat }}
      </el-button>
      <nav class="primary-nav">
        <el-menu :key="activeMenu" :default-active="activeMenu" @select="handleMenuSelect">
          <el-menu-item v-for="item in TEACHER_HOME.navigation" :key="item.index" :index="item.index">
            <el-icon><component :is="iconMap[item.icon]" /></el-icon>
            <span>{{ item.label }}</span>
          </el-menu-item>
        </el-menu>
      </nav>
      <section class="history" aria-labelledby="history-title">
        <div class="section-label-row">
          <span id="history-title">{{ TEACHER_HOME.historyTitle }}</span>
          <el-button text circle aria-label="更多历史记录"><el-icon><MoreFilled /></el-icon></el-button>
        </div>
        <button v-for="item in TEACHER_HOME.history" :key="item.id" class="history-item" type="button">
          <span>{{ item.title }}</span><small>{{ item.time }}</small>
        </button>
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
      <header v-if="!isWorkspace" class="teacher-topbar">
        <div>
          <span class="workspace-label">{{ route.meta.title || '个人工作空间' }}</span>
          <span class="status-dot"><i></i> 智能体在线</span>
        </div>
        <div class="topbar-actions">
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
.teacher-shell { min-height: 100dvh; display: grid; grid-template-columns: 260px minmax(0, 1fr); background: var(--zh-background-primary); color: var(--zh-text-primary); }
.teacher-shell.workspace-mode { display: block; }
.teacher-sidebar { position: sticky; top: 0; height: 100dvh; display: flex; flex-direction: column; padding: 20px 14px 14px; background: var(--zh-background-pc-sidebar); border-right: 1px solid var(--zh-line-parting); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 8px 22px; }
.brand-mark { width: 38px; height: 38px; display: grid; place-items: center; border-radius: var(--zh-radius10); color: white; background: var(--zh-gradient-blue); box-shadow: 0 8px 18px -8px rgb(37 99 235 / 55%); font-size: 18px; font-weight: 700; }
.brand-copy, .profile-copy { min-width: 0; display: flex; flex-direction: column; }
.brand-copy strong { font-size: 18px; letter-spacing: var(--zh-tracking-wide); }
.brand-copy span, .profile-copy span { margin-top: 2px; color: var(--zh-text-caption); font-size: 12px; }
.new-chat-button { width: 100%; height: 42px; margin-bottom: 14px; border-color: var(--zh-background-button); border-radius: var(--zh-radius8); color: var(--zh-text-white); background: var(--zh-background-button); font-weight: 600; transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.new-chat-button:hover, .new-chat-button:focus-visible { border-color: var(--zh-background-button-hover); color: var(--zh-text-white); background: var(--zh-background-button-hover); }
.new-chat-button:active { transform: translateY(1px); }
.new-chat-button :deep(.el-icon) { transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.new-chat-button:hover :deep(.el-icon) { transform: rotate(90deg); }
.new-chat-button:active :deep(.el-icon) { transform: rotate(90deg) scale(.92); transition-duration: 150ms; }
.primary-nav :deep(.el-menu) { border-right: 0; background: transparent; }
.primary-nav :deep(.el-menu-item) { height: 44px; margin: 3px 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); }
.primary-nav :deep(.el-menu-item .el-icon) { transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.primary-nav :deep(.el-menu-item:hover) { background: var(--zh-background-option); color: var(--zh-text-primary); }
.primary-nav :deep(.el-menu-item:hover .el-icon) { transform: translateX(2px) scale(1.04); }
.primary-nav :deep(.el-menu-item.is-active) { color: var(--zh-text-theme); background: var(--zh-background-option-on); font-weight: 600; }
.history { min-height: 0; margin-top: 20px; overflow-y: auto; }
.section-label-row { display: flex; align-items: center; justify-content: space-between; padding: 0 8px 5px; color: var(--zh-text-caption); font-size: 12px; }
.history-item { width: 100%; display: flex; flex-direction: column; gap: 3px; padding: 10px 8px; border: 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: transparent; text-align: left; cursor: pointer; transition: color 200ms cubic-bezier(0.4, 0, 0.2, 1), background-color 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.history-item:hover { color: var(--zh-text-primary); background: var(--zh-background-option); }
.history-item span { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.history-item small { color: var(--zh-text-caption); font-size: 11px; }
.teacher-profile { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; margin-top: auto; padding: 13px 8px 0; border-top: 1px solid var(--zh-line-border); }
.teacher-profile :deep(.el-avatar), .teacher-topbar :deep(.el-avatar) { color: white; background: var(--zh-theme-primary); }
.avatar-button { display: grid; place-items: center; padding: 0; border: 0; border-radius: var(--zh-radius8); background: transparent; cursor: pointer; transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.avatar-button:hover, .avatar-button:focus-visible { transform: translateY(-1px) scale(1.04); }
.avatar-button:active { transform: scale(.96); transition-duration: 150ms; }
.profile-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.teacher-main { min-width: 0; min-height: 100dvh; background: radial-gradient(circle at 50% 18%, rgb(37 99 235 / 5%), transparent 32%), var(--zh-background-primary); }
.teacher-topbar { position: sticky; z-index: 100; top: 0; height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; border-bottom: 1px solid var(--zh-line-parting); background: color-mix(in srgb, var(--zh-background-primary) 88%, transparent); backdrop-filter: blur(12px); }
.workspace-label { color: var(--zh-text-secondary); font-size: 13px; font-weight: 500; }
.status-dot { margin-left: 16px; color: var(--zh-text-caption); font-size: 12px; }
.status-dot i { width: 7px; height: 7px; display: inline-block; margin-right: 5px; border-radius: 50%; background: var(--zh-green); animation: pulse 200ms cubic-bezier(0.4, 0, 0.2, 1) both; }
.topbar-actions { display: flex; align-items: center; gap: 8px; }
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
  .teacher-shell { grid-template-columns: 76px minmax(0, 1fr); }
  .teacher-sidebar { padding-inline: 10px; }
  .brand { justify-content: center; padding-inline: 0; }
  .brand-copy, .history, .profile-copy, .primary-nav :deep(.el-menu-item span), .new-chat-button :deep(span) { display: none; }
  .new-chat-button { width: 44px; margin-inline: auto; padding: 0; }
  .primary-nav :deep(.el-menu-item) { justify-content: center; padding: 0 !important; }
  .teacher-profile { display: flex; justify-content: center; padding-inline: 0; }
  .teacher-profile > :last-child { display: none; }
}
@media (max-width: 680px) {
  .teacher-shell { display: block; }
  .teacher-sidebar { display: none; }
  .teacher-topbar { height: 60px; padding-inline: 16px; }
  .status-dot { display: none; }
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
