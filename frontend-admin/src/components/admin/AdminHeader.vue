<!--
  [数据交互说明]
  - 导入:
    - `useRoute`: 获取当前路由信息生成面包屑导航
    - ElementPlus Icons: Search、Bell、Refresh、Fold、Expand 图标
    - `ElMessage`: 操作反馈提示
  - Props:
    - `sidebarCollapsed`: Boolean — 由父组件 main.vue 传入，用于切换折叠按钮图标
  - Emits:
    - `toggle-sidebar`: 通知父组件切换侧边栏折叠状态
  - 输出:
    - 渲染顶部通栏：折叠按钮 + 面包屑导航 + 全局搜索框 + 通知铃铛 + 刷新按钮
-->
<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Bell, Refresh, Fold, Expand } from '@element-plus/icons-vue'

const props = defineProps({
  /** 侧边栏折叠状态，由父组件传入，用于切换折叠按钮图标 */
  sidebarCollapsed: {
    type: Boolean,
    default: false,
  },
})

/** 通知父组件切换侧边栏折叠/展开 */
const emit = defineEmits(['toggle-sidebar'])

const route = useRoute()

/** 搜索关键词 */
const searchKeyword = ref('')
/** 未读通知数 */
const unreadCount = ref(0)
/** 刷新按钮加载态 */
const isRefreshing = ref(false)

/**
 * 面包屑导航映射 — 根据路由名称动态生成层级
 * 返回 [{ label, path? }] 数组，最后一项为当前页（无链接）
 */
const breadcrumbMap = {
  AdminAccess: { parent: '账号与权限', current: '权限与访问说明' },
  QuestionManagement: { parent: '教学评价', current: '题库录入与审核' },
  Dashboard: { parent: '数据看板', current: 'Dashboard Overview' },
  Settings: { parent: '系统配置', current: 'System Settings' },
  Users: { parent: '用户管理', current: 'Users & Permissions' },
  Roles: { parent: '角色管理', current: 'Roles & Permissions' },
  Audit: { parent: '内容审核与社区治理', current: 'Content Audit & Governance' },
  Resources: { parent: '公共资源与知识库维护', current: 'Resources & Knowledge Base' },
}

const breadcrumbs = computed(() => {
  const name = route.name
  const entry = breadcrumbMap[name]
  if (!entry) {
    return [
      { label: '管理工作台' },
      { label: route.meta?.title || '当前页面' },
    ]
  }
  return [
    { label: entry.parent, path: route.path },
    { label: entry.current },
  ]
})

/**
 * 点击折叠/展开按钮 — 向上 emit 切换事件
 */
const handleToggleClick = () => {
  emit('toggle-sidebar')
}

/**
 * 折叠按钮 Tooltip 文案 — 根据当前状态动态返回
 */
const toggleTooltip = computed(() => {
  return props.sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'
})

/**
 * 触发全局搜索 — 聚焦搜索框后按 Enter 触发
 * 将来可扩展为调用后端搜索 API 或弹出全局搜索面板
 */
const handleSearch = () => {
  if (!searchKeyword.value.trim()) return
  ElMessage.info('请使用当前页面内的关键词筛选；跨模块搜索暂未接入')
}

/**
 * 点击通知铃铛 — 展开通知下拉面板
 * 将来可替换为 el-popover 通知列表面板
 */
const handleNotificationClick = () => {
  // TODO: 展开通知下拉面板
  ElMessage.info('暂无已接入的通知数据，请在看板查看待处理事项')
}

/**
 * 点击刷新按钮 — 重新加载当前页面数据
 * 显示旋转加载态 500ms 后恢复
 */
const handleRefresh = () => {
  isRefreshing.value = true
  // 触发自定义事件通知父组件刷新数据
  window.dispatchEvent(new CustomEvent('admin-refresh'))
  setTimeout(() => {
    isRefreshing.value = false
  }, 500)
}
</script>

<template>
  <!-- 顶部通栏容器：固定高度 56px，sticky 定位 -->
  <header
    class="flex items-center justify-between h-[56px] px-6 flex-shrink-0 sticky top-0 z-[100] border-b"
    style="
      background: var(--zh-background-primary);
      border-color: var(--zh-line-border);
    "
  >
    <!-- ===== 左侧：折叠按钮 + 面包屑导航 ===== -->
    <div class="flex items-center gap-2">
      <!-- 侧边栏折叠/展开切换按钮 -->
      <el-tooltip
        :content="toggleTooltip"
        placement="bottom"
        effect="dark"
      >
        <el-button
          :icon="sidebarCollapsed ? Expand : Fold"
          circle
          size="small"
          class="!text-lg"
          @click="handleToggleClick"
        />
      </el-tooltip>

      <el-breadcrumb separator="/">
        <el-breadcrumb-item
          v-for="(crumb, index) in breadcrumbs"
          :key="index"
          :to="crumb.path ? { path: crumb.path } : undefined"
        >
          <span
            :style="{
              fontSize: 'var(--zh-font-size14)',
              color: index === breadcrumbs.length - 1
                ? 'var(--zh-text-primary)'
                : 'var(--zh-text-caption)',
              fontWeight: index === breadcrumbs.length - 1 ? 600 : 400,
            }"
          >
            {{ crumb.label }}
          </span>
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- ===== 右侧：操作工具栏 ===== -->
    <div class="flex items-center gap-3">
      <!-- 全局搜索框 -->
      <el-input
        v-model="searchKeyword"
        placeholder="搜索账号、内容、日志..."
        aria-label="管理端搜索提示：请使用各页面内的筛选"
        :prefix-icon="Search"
        size="small"
        clearable
        class="!w-[240px]"
        :style="{
          '--el-border-radius-base': 'var(--zh-radius8)',
        }"
        @keyup.enter="handleSearch"
      />

      <!-- 通知铃铛（带红点徽标） -->
      <el-badge :value="unreadCount" :hidden="unreadCount === 0">
        <el-button
          :icon="Bell"
          circle
          size="small"
          class="!text-lg"
          @click="handleNotificationClick"
          aria-label="通知"
        />
      </el-badge>

      <!-- 刷新按钮 -->
      <el-button
        :icon="Refresh"
        circle
        size="small"
        class="!text-lg"
        :class="{ 'animate-spin': isRefreshing }"
        @click="handleRefresh"
        :disabled="isRefreshing"
        aria-label="刷新当前管理页面"
      />
    </div>
  </header>
</template>

<style scoped>
/** 刷新按钮旋转动画 */
.animate-spin :deep(svg) {
  animation: loadingSpin 0.5s ease-in-out;
}

@keyframes loadingSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
