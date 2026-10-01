<!--
  [数据交互说明]
  - 导入: Vue Router 当前路由（useRoute/useRouter）
  - 输出: 教师端手机档（<768px）底部固定导航，5 个一级入口；是否渲染/显示由 TeacherLayout 控制（workspace-mode 或桌面档隐藏）
  - 说明: 候选组件规范见 doc/pending-specs/BottomTabBar.md
-->
<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChatDotRound, Download, Edit, Files, House } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

/** 底部 5 个一级入口；工作台居中央主操作位，用品牌实色按钮突出。 */
const tabs = [
  { path: '/main', label: '主页', icon: House },
  { path: '/main/resources', label: '资源', icon: Files },
  { path: '/main/workspace', label: '工作台', icon: Edit, emphasized: true },
  { path: '/main/exports', label: '导出', icon: Download },
  { path: '/main/community', label: '社区', icon: ChatDotRound },
]

/** 当前激活 Tab：与路由 path 精确匹配（query 不参与判断）。 */
const activePath = computed(() => route.path)

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
      :class="['tab-item', { 'is-active': activePath === tab.path, 'is-emphasized': tab.emphasized }]"
      :aria-label="tab.label"
      :aria-current="activePath === tab.path ? 'page' : undefined"
      @click="handleSelect(tab)"
    >
      <el-icon class="tab-icon"><component :is="tab.icon" /></el-icon>
      <span v-if="!tab.emphasized" class="tab-label">{{ tab.label }}</span>
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
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.08);
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
.tab-icon { font-size: 24px; }
.tab-label { font-size: var(--zh-font-size10); line-height: 1; }
.tab-item.is-active { color: var(--zh-text-theme); }
/* 中央主操作位：以更大的品牌实色图标突出，文字由 aria-label 提供。 */
.tab-item.is-emphasized { gap: 0; padding: 4px; }
.tab-item.is-emphasized .tab-icon {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: var(--zh-radius16);
  color: var(--zh-background-primary);
  background: var(--zh-theme-primary);
  font-size: 26px;
}
.tab-item.is-emphasized.is-active .tab-icon { background: var(--zh-background-button-hover); }
.tab-item:active { color: var(--zh-text-theme); background: var(--zh-background-option); transform: scale(0.92); }
/* 横屏矮屏：隐藏文字仅留图标，高度降为 48px */
@media (orientation: landscape) and (max-height: 480px) {
  .bottom-tabbar { height: calc(48px + var(--zh-safe-bottom)); }
  .tab-label { display: none; }
}
</style>
