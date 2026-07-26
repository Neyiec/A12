<!--
  [数据交互说明]
  - 导入: `TEACHER_HOME` 首页配置、Element Plus 图标组件
  - 输出: 教师端 `/main` 默认首页
  - 输入: 当前为前端演示数据；后续可接入用户信息、对话历史与智能体会话接口
-->
<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Bell,
  ChatDotRound,
  Collection,
  Document,
  Download,
  FolderOpened,
  Grid,
  MagicStick,
  Microphone,
  Monitor,
  Moon,
  MoreFilled,
  Paperclip,
  Plus,
  Promotion,
  Setting,
  Sunny,
} from '@element-plus/icons-vue'
import { TEACHER_HOME } from '../config/teacherHome.config.js'

const prompt = ref('')
const activeMenu = ref('home')
const isDark = ref(false)

const iconMap = {
  ChatDotRound,
  Collection,
  Document,
  Download,
  FolderOpened,
  Grid,
  MagicStick,
  Presentation: Monitor,
}

const canSend = computed(() => prompt.value.trim().length > 0)

/** 将推荐任务填入输入框，便于教师继续补充要求。 */
const applySuggestion = (suggestion) => {
  prompt.value = suggestion.prompt
}

/** 切换亮暗主题，并同步设计系统根节点属性。 */
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light'
}

/** 提交教师指令；当前保留前端反馈，等待接入会话接口。 */
const sendPrompt = () => {
  if (!canSend.value) return
  ElMessage.success('任务已创建，正在梳理教学思路')
  prompt.value = ''
}

/** 处理尚未接入独立页面的导航项。 */
const handleMenuSelect = (index) => {
  activeMenu.value = index
  if (index !== 'home') {
    ElMessage.info('该模块正在接入中')
  }
}
</script>

<template>
  <div class="teacher-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <aside class="sidebar" aria-label="教师端主导航">
      <header class="brand">
        <div class="brand-mark" aria-hidden="true">智</div>
        <div class="brand-copy">
          <strong>{{ TEACHER_HOME.brand.name }}</strong>
          <span>{{ TEACHER_HOME.brand.subtitle }}</span>
        </div>
      </header>

      <el-button type="primary" class="new-chat-button" :icon="Plus">
        {{ TEACHER_HOME.actions.newChat }}
      </el-button>

      <nav class="primary-nav">
        <el-menu :default-active="activeMenu" @select="handleMenuSelect">
          <el-menu-item
            v-for="item in TEACHER_HOME.navigation"
            :key="item.index"
            :index="item.index"
          >
            <el-icon><component :is="iconMap[item.icon]" /></el-icon>
            <span>{{ item.label }}</span>
          </el-menu-item>
        </el-menu>
      </nav>

      <section class="history" aria-labelledby="history-title">
        <div class="section-label-row">
          <span id="history-title">{{ TEACHER_HOME.historyTitle }}</span>
          <el-button text circle aria-label="更多历史记录">
            <el-icon><MoreFilled /></el-icon>
          </el-button>
        </div>
        <button
          v-for="item in TEACHER_HOME.history"
          :key="item.id"
          class="history-item"
          type="button"
        >
          <span>{{ item.title }}</span>
          <small>{{ item.time }}</small>
        </button>
      </section>

      <footer class="teacher-profile">
        <el-avatar :size="38" shape="square">{{ TEACHER_HOME.teacher.initials }}</el-avatar>
        <div class="profile-copy">
          <strong>{{ TEACHER_HOME.teacher.name }}</strong>
          <span>{{ TEACHER_HOME.teacher.role }}</span>
        </div>
        <el-button text circle :aria-label="TEACHER_HOME.actions.settings">
          <el-icon><Setting /></el-icon>
        </el-button>
      </footer>
    </aside>

    <main id="main-content" class="main-content">
      <header class="topbar">
        <div>
          <span class="workspace-label">个人工作空间</span>
          <span class="status-dot"><i></i> 智能体在线</span>
        </div>
        <div class="topbar-actions">
          <el-button text circle :aria-label="TEACHER_HOME.actions.theme" @click="toggleTheme">
            <el-icon><component :is="isDark ? Sunny : Moon" /></el-icon>
          </el-button>
          <el-button text circle :aria-label="TEACHER_HOME.actions.notifications">
            <el-icon><Bell /></el-icon>
          </el-button>
          <el-avatar :size="34">{{ TEACHER_HOME.teacher.initials }}</el-avatar>
        </div>
      </header>

      <section class="welcome">
        <div class="welcome-copy">
          <p class="eyebrow">{{ TEACHER_HOME.greeting.eyebrow }}</p>
          <h1>{{ TEACHER_HOME.greeting.title }}</h1>
          <p class="intro">{{ TEACHER_HOME.greeting.description }}</p>
        </div>

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
            <div>
              <h2>{{ suggestion.title }}</h2>
              <p>{{ suggestion.description }}</p>
            </div>
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
            @keydown.ctrl.enter="sendPrompt"
          />
          <div class="composer-toolbar">
            <div class="composer-tools">
              <el-button text :icon="Paperclip">{{ TEACHER_HOME.composer.attach }}</el-button>
              <el-button text :icon="Collection">{{ TEACHER_HOME.composer.knowledge }}</el-button>
              <el-button text circle aria-label="语音输入">
                <el-icon><Microphone /></el-icon>
              </el-button>
            </div>
            <el-button
              type="primary"
              circle
              :icon="Promotion"
              :disabled="!canSend"
              :aria-label="TEACHER_HOME.composer.send"
              @click="sendPrompt"
            />
          </div>
        </section>
        <p class="composer-hint">{{ TEACHER_HOME.composer.hint }}</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.teacher-shell {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background: var(--zh-background-primary);
  color: var(--zh-text-primary);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  padding: 20px 14px 14px;
  background: var(--zh-background-pc-sidebar);
  border-right: 1px solid var(--zh-line-parting);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px 22px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: var(--zh-radius10);
  color: var(--zh-text-white);
  background: var(--zh-gradient-blue);
  box-shadow: 0 8px 18px -8px rgb(37 99 235 / 55%);
  font-size: var(--zh-font-size18);
  font-weight: 700;
}

.brand-copy,
.profile-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.brand-copy strong {
  font-size: var(--zh-font-size18);
  letter-spacing: var(--zh-tracking-wide);
}

.brand-copy span,
.profile-copy span {
  margin-top: 2px;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
}

.new-chat-button {
  width: 100%;
  height: 42px;
  margin-bottom: 14px;
  border-radius: var(--zh-radius8);
  font-weight: 600;
}

.primary-nav :deep(.el-menu) {
  border-right: 0;
  background: transparent;
}

.primary-nav :deep(.el-menu-item) {
  height: 44px;
  margin: 3px 0;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-secondary);
}

.primary-nav :deep(.el-menu-item:hover) {
  background: var(--zh-background-option);
  color: var(--zh-text-primary);
}

.primary-nav :deep(.el-menu-item.is-active) {
  color: var(--zh-text-theme);
  background: var(--zh-background-option-on);
  font-weight: 600;
}

.history {
  min-height: 0;
  margin-top: 20px;
  overflow-y: auto;
}

.section-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 5px;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
}

.history-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 8px;
  border: 0;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-secondary);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 200ms ease, color 200ms ease;
}

.history-item:hover {
  color: var(--zh-text-primary);
  background: var(--zh-background-option);
}

.history-item span {
  overflow: hidden;
  font-size: var(--zh-font-size13);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item small {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
}

.teacher-profile {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding: 13px 8px 0;
  border-top: 1px solid var(--zh-line-border);
}

.teacher-profile :deep(.el-avatar),
.topbar :deep(.el-avatar) {
  color: var(--zh-text-white);
  background: var(--zh-theme-primary);
}

.profile-copy strong {
  overflow: hidden;
  font-size: var(--zh-font-size13);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-content {
  min-width: 0;
  min-height: 100dvh;
  background:
    radial-gradient(circle at 50% 18%, rgb(37 99 235 / 6%), transparent 34%),
    var(--zh-background-primary);
}

.topbar {
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  border-bottom: 1px solid var(--zh-line-parting);
}

.workspace-label {
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
  font-weight: 500;
}

.status-dot {
  margin-left: 16px;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
}

.status-dot i {
  width: 7px;
  height: 7px;
  display: inline-block;
  margin-right: 5px;
  border-radius: 50%;
  background: var(--zh-green);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.welcome {
  width: min(880px, calc(100% - 48px));
  margin: 0 auto;
  padding: clamp(70px, 11vh, 132px) 0 42px;
}

.welcome-copy {
  max-width: 720px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--zh-text-theme);
  font-size: var(--zh-font-size14);
  font-weight: 600;
}

.welcome h1 {
  margin: 0;
  font-size: clamp(36px, 4vw, 48px);
  line-height: 1.15;
  letter-spacing: var(--zh-tracking-tight);
  text-wrap: balance;
}

.intro {
  max-width: 660px;
  margin: 18px 0 0;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size16);
  line-height: 1.75;
  text-wrap: pretty;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 38px;
}

.suggestion-card {
  position: relative;
  cursor: pointer;
  transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease;
}

.suggestion-card:hover,
.suggestion-card:focus-visible {
  transform: translateY(-3px);
  border-color: var(--zh-line-theme20);
  box-shadow: var(--zh-shadow2);
  outline: none;
}

.suggestion-card:active {
  transform: translateY(-1px) scale(0.99);
}

.suggestion-card :deep(.el-card__body) {
  min-height: 150px;
  padding: 18px;
}

.suggestion-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  margin-bottom: 24px;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
}

.suggestion-card h2 {
  margin: 0;
  font-size: var(--zh-font-size15);
  font-weight: 600;
}

.suggestion-card p {
  margin: 7px 24px 0 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size12);
  line-height: 1.6;
}

.card-arrow {
  position: absolute;
  right: 16px;
  bottom: 18px;
  color: var(--zh-text-disabled);
  transform: rotate(-45deg);
}

.composer {
  margin-top: 24px;
  padding: 9px 10px 10px;
  border: 1px solid var(--zh-line-heavier);
  border-radius: var(--zh-radius16);
  background: var(--zh-background-input);
  box-shadow: var(--zh-shadow1);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.composer:focus-within {
  border-color: var(--zh-line-theme50);
  box-shadow: 0 0 0 3px var(--zh-line-theme20), var(--zh-shadow2);
}

.composer :deep(.el-textarea__inner) {
  min-height: 78px !important;
  padding: 10px 12px 6px;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size15);
  line-height: 1.65;
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 2px 0;
}

.composer-tools {
  display: flex;
  align-items: center;
}

.composer-tools :deep(.el-button) {
  color: var(--zh-text-secondary);
}

.composer-hint {
  margin: 10px 0 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
  text-align: center;
}

@media (max-width: 900px) {
  .teacher-shell {
    grid-template-columns: 76px minmax(0, 1fr);
  }

  .sidebar {
    padding-inline: 10px;
  }

  .brand {
    justify-content: center;
    padding-inline: 0;
  }

  .brand-copy,
  .history,
  .profile-copy,
  .primary-nav :deep(.el-menu-item span),
  .new-chat-button :deep(span) {
    display: none;
  }

  .new-chat-button {
    width: 44px;
    margin-inline: auto;
    padding: 0;
  }

  .primary-nav :deep(.el-menu-item) {
    justify-content: center;
    padding: 0 !important;
  }

  .teacher-profile {
    display: flex;
    justify-content: center;
    padding-inline: 0;
  }

  .teacher-profile > :last-child {
    display: none;
  }
}

@media (max-width: 680px) {
  .teacher-shell {
    display: block;
  }

  .sidebar {
    display: none;
  }

  .topbar {
    height: 60px;
    padding-inline: 16px;
  }

  .status-dot {
    display: none;
  }

  .welcome {
    width: min(100% - 28px, 540px);
    padding-top: 54px;
  }

  .suggestion-grid {
    grid-template-columns: 1fr;
  }

  .suggestion-card :deep(.el-card__body) {
    min-height: 118px;
  }

  .suggestion-icon {
    margin-bottom: 16px;
  }
}
</style>
