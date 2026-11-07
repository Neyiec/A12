<!--
  [数据交互说明]
  - 导入: Vue Router 当前路由（useRoute/useRouter）
  - 输出: 教师端手机档底部固定导航，4 个一级入口；课件预览中隐藏
  - 说明: 候选组件规范见 doc/pending-specs/BottomTabBar.md
-->
<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChatDotRound, House, Document, User } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { path: '/main', label: '主页', icon: House },
  { path: '/main/community', label: '社区', icon: ChatDotRound },
  { path: '/main/questions', label: '题库', icon: Document },
  { path: '/main/me', label: '我的', icon: User },
]

/** Personal tools and settings belong to 我的 even while viewing their own routes. */
const personalMenus = new Set(['me', 'workspace', 'resources', 'exports', 'settings', 'courses'])
const activePath = computed(() => personalMenus.has(route.meta.menu) ? '/main/me' : route.path)

/** 切换页面；点击当前页不重复跳转，保留开发预览 query 与桌面导航行为一致。 */
const handleSelect = (tab) => {
  if (route.path === tab.path) return
  router.push({ path: tab.path, query: route.query.preview ? { preview: '1' } : {} })
}
</script>

<template>
  <nav class="bottom-tabbar" aria-label="底部主导航">
    <button
      v-for="tab in tabs"
      :key="tab.path"
      type="button"
      :class="['tab-item', { 'is-active': activePath === tab.path }]"
      :aria-label="tab.label"
      :aria-current="activePath === tab.path ? 'page' : undefined"
      @click="handleSelect(tab)"
    >
      <el-icon class="tab-icon"><component :is="tab.icon" /></el-icon>
      <span class="tab-label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.bottom-tabbar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 100;
  display: flex;
  align-items: stretch;
  height: calc(var(--zh-tabbar-h) + var(--zh-safe-bottom));
  padding-bottom: var(--zh-safe-bottom);
  border-top: 1px solid var(--zh-line-parting);
  box-shadow: 0 -3px 16px rgb(23 43 77 / 4%);
  background: var(--zh-background-primary);
}
.tab-item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 4px;
  border: 0;
  border-radius: 0;
  color: var(--zh-text-caption);
  background: transparent;
  font: inherit;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease, transform 150ms ease;
}
.tab-icon { display: grid; place-items: center; width: 48px; height: 32px; border-radius: 12px; font-size: 26px; }
.tab-label { font-size: 14px; line-height: 1.3; font-weight: 500; }
.tab-item.is-active { color: var(--zh-text-theme); }
.tab-item.is-active .tab-icon { background: var(--zh-background-weaken); }
.tab-item.is-active .tab-label { font-weight: 650; }
.tab-item:active { color: var(--zh-text-theme); background: var(--zh-background-option); transform: scale(0.92); }
/* 横屏矮屏：隐藏文字仅留图标，高度降为 48px */
@media (orientation: landscape) and (max-height: 480px) {
  .bottom-tabbar { height: calc(48px + var(--zh-safe-bottom)); }
  .tab-label { display: none; }
}
</style>
