<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Bell, Download, Files, Grid, Monitor, Moon, Setting, Sunny, User } from '@element-plus/icons-vue'
import { useUserStore } from '../storage/user'
import { useTeacherTheme } from '../composables/useTeacherTheme'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isDark, toggleTheme } = useTeacherTheme()
const notificationsVisible = ref(false)
const user = computed(() => userStore.userInfo || {})
const displayName = computed(() => user.value.real_name || user.value.username || '我的账号')
const avatarText = computed(() => Array.from(displayName.value)[0])
const role = computed(() => user.value.user_type === 'admin' ? '管理员' : '教师')
const tools = [
  { label: '课件', icon: Monitor, path: '/main/workspace' },
  { label: '导出', icon: Download, path: '/main/exports' },
  { label: '资源', icon: Files, path: '/main/resources' },
]
const navigate = path => router.push({ path, query: route.query.preview ? { preview: '1' } : {} })
</script>

<template>
  <main class="my-profile-page">
    <header class="my-profile-toolbar">
      <h1>我的</h1>
      <div class="profile-toolbar-actions"><button class="profile-settings-button" type="button" aria-label="通知" @click="notificationsVisible = true"><el-icon><Bell /></el-icon></button><button class="profile-settings-button" type="button" aria-label="账号设置" @click="navigate('/main/settings')"><el-icon><Setting /></el-icon></button></div>
    </header>

    <section class="profile-overview" aria-label="个人信息">
      <button class="profile-summary" type="button" aria-label="查看和编辑个人资料" @click="navigate('/main/settings')">
        <el-avatar :size="72" :src="user.avatar || undefined">{{ avatarText }}</el-avatar>
        <span class="profile-identity">
          <strong>{{ displayName }}</strong>
          <span class="profile-role">{{ role }}</span>
          <span v-if="user.username" class="profile-username">@{{ user.username }}</span>
        </span>
        <el-icon class="profile-chevron"><ArrowRight /></el-icon>
      </button>
    </section>

    <section class="personal-tools" aria-labelledby="personal-tools-title">
      <h2 id="personal-tools-title">我的教学</h2>
      <div class="personal-tool-grid">
        <button v-for="tool in tools" :key="tool.path" type="button" class="personal-tool" :aria-label="`打开${tool.label}`" @click="navigate(tool.path)">
          <span class="personal-tool-icon"><el-icon><component :is="tool.icon" /></el-icon></span>
          <span>{{ tool.label }}</span>
        </button>
      </div>
    </section>

    <section class="personal-account" aria-label="更多功能">
      <button type="button" class="personal-account-link" @click="navigate('/main/courses')"><span class="account-link-icon"><el-icon><Grid /></el-icon></span><span>课程图谱</span><el-icon class="profile-chevron"><ArrowRight /></el-icon></button>
      <button type="button" class="personal-account-link" @click="navigate('/main/settings')">
        <span class="account-link-icon"><el-icon><User /></el-icon></span>
        <span>账号与安全</span>
        <el-icon class="profile-chevron"><ArrowRight /></el-icon>
      </button>
      <button type="button" class="personal-account-link" :aria-pressed="isDark" @click="toggleTheme">
        <span class="account-link-icon"><el-icon><Moon v-if="isDark" /><Sunny v-else /></el-icon></span>
        <span>深色模式</span>
        <small class="theme-status">{{ isDark ? '已开启' : '已关闭' }}</small>
      </button>
    </section>
    <el-dialog v-model="notificationsVisible" title="通知" width="min(460px, 92vw)"><el-empty description="通知功能尚未接入" :image-size="72" /><template #footer><el-button @click="notificationsVisible = false">关闭</el-button></template></el-dialog>
  </main>
</template>

<style scoped>
.theme-status { flex: none; color: var(--zh-text-secondary); font-size: 14px; }
.my-profile-page{width:min(100%,780px);min-height:calc(100dvh - 68px);margin:0 auto;padding:24px 24px 40px;background:var(--zh-background-light);color:var(--zh-text-primary)}
.my-profile-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:28px}.my-profile-toolbar h1{margin:0;font-size:24px;font-weight:650;letter-spacing:-.025em}
.profile-settings-button{display:grid;place-items:center;flex:none;width:44px;height:44px;border:0;border-radius:12px;background:transparent;color:var(--zh-text-primary);font-size:26px;cursor:pointer}
.profile-toolbar-actions{display:flex;align-items:center;gap:8px}
.profile-overview{padding:8px 0 32px}.profile-summary{display:flex;align-items:center;gap:18px;width:100%;padding:0;border:0;background:transparent;color:inherit;text-align:left;font:inherit;cursor:pointer}
.profile-summary :deep(.el-avatar){flex:none;background:var(--zh-theme-primary);color:#fff;font-size:30px;font-weight:600}
.profile-identity{display:flex;flex:1;min-width:0;flex-direction:column;align-items:flex-start;gap:7px}.profile-identity>strong{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:24px;font-weight:650;line-height:1.4}.profile-role{display:inline-flex;padding:2px 9px;border-radius:6px;background:var(--zh-background-weaken);color:var(--zh-text-theme);font-size:13px;font-weight:600}.profile-username{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--zh-text-secondary);font-size:15px}.profile-chevron{flex:none;color:var(--zh-text-caption);font-size:19px}
.personal-tools,.personal-account{border-radius:20px;background:var(--zh-background-primary)}.personal-tools{padding:20px 16px 16px}.personal-tools h2{margin:0 4px 16px;font-size:19px;font-weight:650}.personal-tool-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.personal-tool{display:flex;min-width:0;min-height:108px;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:12px 4px;border:0;border-radius:14px;background:transparent;color:inherit;font:inherit;font-size:16px;font-weight:500;cursor:pointer}.personal-tool-icon{display:grid;width:52px;height:52px;place-items:center;border-radius:16px;background:var(--zh-background-weaken);color:var(--zh-text-theme);font-size:30px}
.personal-account{margin-top:18px;padding:4px 16px}.personal-account-link{display:flex;align-items:center;gap:14px;width:100%;min-height:68px;padding:8px 0;border:0;color:inherit;background:transparent;text-align:left;font:inherit;font-size:16px;cursor:pointer}.account-link-icon{display:grid;width:36px;height:36px;place-items:center;color:var(--zh-text-secondary);font-size:24px}.personal-account-link>span:nth-child(2){flex:1}
.personal-account-link+.personal-account-link{border-top:1px solid var(--zh-line-parting)}
.profile-settings-button:active,.personal-tool:active,.personal-account-link:active{background:var(--zh-background-option)}.profile-summary:active{opacity:.75}
@media(max-width:767.98px) and (hover:none) and (pointer:coarse){.my-profile-page{min-height:calc(100dvh - var(--zh-tabbar-h) - var(--zh-safe-bottom));padding:calc(12px + var(--zh-safe-top)) calc(20px + var(--zh-safe-right)) 32px calc(20px + var(--zh-safe-left))}.my-profile-toolbar{margin-bottom:24px}.profile-overview{padding-bottom:32px}.profile-summary{gap:16px}}
@media(max-width:359.98px){.profile-summary :deep(.el-avatar){width:64px;height:64px;font-size:27px}.profile-summary{gap:12px}.profile-identity>strong{font-size:22px}.personal-tools{padding-inline:12px}.personal-tool-grid{gap:0}}
</style>
