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
        <el-avatar :size="38" shape="square" :src="avatarUrl">{{ avatarText }}</el-avatar>
        <div class="profile-copy"><strong>{{ userStore.userInfo?.real_name || TEACHER_HOME.teacher.name }}</strong><span>{{ userStore.userInfo?.user_type === 'admin' ? '管理员' : TEACHER_HOME.teacher.role }}</span></div>
        <el-button text circle aria-label="设置" @click="router.push('/main/settings')"><el-icon><Setting /></el-icon></el-button>
      </footer>
    </aside>

    <main id="main-content" class="teacher-main">
      <header v-if="!isWorkspace" class="teacher-topbar">
        <div>
          <span class="workspace-label">{{ route.meta.title || '个人工作空间' }}</span>
          <span class="status-dot"><i></i> 智能体在线</span>
        </div>
        <div class="topbar-actions">
          <el-button text circle aria-label="切换主题" @click="toggleTheme"><el-icon><component :is="isDark ? Sunny : Moon" /></el-icon></el-button>
          <el-button text circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <el-avatar :size="34" class="cursor-pointer" :src="avatarUrl" @click="router.push('/main/settings')">{{ avatarText }}</el-avatar>
        </div>
      </header>
      <router-view />
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
.new-chat-button { width: 100%; height: 42px; margin-bottom: 14px; border-radius: var(--zh-radius8); font-weight: 600; }
.primary-nav :deep(.el-menu) { border-right: 0; background: transparent; }
.primary-nav :deep(.el-menu-item) { height: 44px; margin: 3px 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); }
.primary-nav :deep(.el-menu-item:hover) { background: var(--zh-background-option); color: var(--zh-text-primary); }
.primary-nav :deep(.el-menu-item.is-active) { color: var(--zh-text-theme); background: var(--zh-background-option-on); font-weight: 600; }
.history { min-height: 0; margin-top: 20px; overflow-y: auto; }
.section-label-row { display: flex; align-items: center; justify-content: space-between; padding: 0 8px 5px; color: var(--zh-text-caption); font-size: 12px; }
.history-item { width: 100%; display: flex; flex-direction: column; gap: 3px; padding: 10px 8px; border: 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: transparent; text-align: left; cursor: pointer; transition: 200ms ease; }
.history-item:hover { color: var(--zh-text-primary); background: var(--zh-background-option); }
.history-item span { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.history-item small { color: var(--zh-text-caption); font-size: 11px; }
.teacher-profile { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; margin-top: auto; padding: 13px 8px 0; border-top: 1px solid var(--zh-line-border); }
.teacher-profile :deep(.el-avatar), .teacher-topbar :deep(.el-avatar) { color: white; background: var(--zh-theme-primary); }
.profile-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.teacher-main { min-width: 0; min-height: 100dvh; background: radial-gradient(circle at 50% 18%, rgb(37 99 235 / 5%), transparent 32%), var(--zh-background-primary); }
.teacher-topbar { position: sticky; z-index: 100; top: 0; height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; border-bottom: 1px solid var(--zh-line-parting); background: color-mix(in srgb, var(--zh-background-primary) 88%, transparent); backdrop-filter: blur(12px); }
.workspace-label { color: var(--zh-text-secondary); font-size: 13px; font-weight: 500; }
.status-dot { margin-left: 16px; color: var(--zh-text-caption); font-size: 12px; }
.status-dot i { width: 7px; height: 7px; display: inline-block; margin-right: 5px; border-radius: 50%; background: var(--zh-green); }
.topbar-actions { display: flex; align-items: center; gap: 4px; }
.topbar-actions :deep(.el-button .el-icon), .teacher-profile :deep(.el-button .el-icon) { font-size: 18px; }

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
</style>
