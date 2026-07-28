<!--
  [数据交互说明]
  - 导入:
    - `AdminSidebar`: 左侧导航栏组件
    - `AdminHeader`: 顶部通栏组件
  - 依赖:
    - Vue Router: 通过 `<router-view>` 嵌套渲染子路由页面
    - Pinia: 子组件通过 `useUserStore` 获取当前用户信息
  - 输入: 无直接 props，子路由路径由 Vue Router 匹配
  - 输出: 渲染完整的后台管理布局框架（侧边栏 + 头部 + 内容区）
  - 布局模式: 左侧可收缩导航（240px ⇄ 64px）+ 右侧自适应内容区（最大 1440px 居中）
  - 状态管理: `isSidebarCollapsed` 控制侧边栏折叠/展开，持久化到 localStorage
-->
<script setup>
import { ref } from 'vue'
import AdminSidebar from './admin/AdminSidebar.vue'
import AdminHeader from './admin/AdminHeader.vue'

/** 侧边栏折叠状态 — 从 localStorage 读取初始值，首次访问默认展开 */
const SIDEBAR_STORAGE_KEY = 'zhihu-sidebar-collapsed'
const isSidebarCollapsed = ref(
  localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true'
)

/**
 * 切换侧边栏折叠状态，并持久化到 localStorage
 * 由 AdminHeader 的折叠按钮触发
 */
const handleToggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isSidebarCollapsed.value))
}
</script>

<template>
  <!-- 整体容器：全屏高度，水平弹性布局 -->
  <div class="flex h-screen overflow-hidden" style="background: var(--zh-background-light);">

    <!-- ===== 左侧导航栏：可收缩宽度 ===== -->
    <AdminSidebar :collapsed="isSidebarCollapsed" />

    <!-- ===== 右侧主内容区：弹性填充，侧边栏收缩时自动扩展 ===== -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden">

      <!-- 顶部通栏 — 包含折叠切换按钮 -->
      <AdminHeader
        :sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="handleToggleSidebar"
      />

      <!-- 内容区：可滚动，最大宽度 1440px 居中 -->
      <main class="flex-1 overflow-y-auto">
        <div class="max-w-[1440px] mx-auto p-6">
          <router-view />
        </div>
      </main>

    </div>
  </div>
</template>
