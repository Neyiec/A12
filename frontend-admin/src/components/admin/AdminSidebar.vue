<!--
  [数据交互说明]
  - 导入:
    - `useRouter` / `useRoute`: Vue Router 实例，用于路由跳转和当前路径检测
    - `useUserStore`: Pinia 用户状态 store，获取当前登录管理员信息
    - ElementPlus Icons: 菜单图标组件
  - Props:
    - `collapsed`: Boolean — 由父组件 main.vue 传入，控制侧边栏折叠/展开状态
  - 输出:
    - 渲染侧边栏功能树导航（el-menu），点击叶子节点触发路由跳转
    - 高亮当前激活的路由对应菜单项
    - 折叠态下 hover 父节点弹出子菜单浮层（ElMenu 原生行为）
    - 底部展示当前登录管理员头像和名称
  - 菜单结构:
    - 数据看板 → /main/dashboard (el-menu-item)
    - 系统管理 (el-sub-menu)
      ├─ 用户管理 → /main/users
      ├─ 角色管理 → /main/roles
      └─ 系统配置 → /main/settings
    - 内容审核与社区治理 → /main/audit (el-menu-item)
    - 公共资源与知识库维护 → /main/resources (el-menu-item)
-->
<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../storage/user'
import {
  Setting,
  UserFilled,
  Checked,
  FolderOpened,
  Monitor,
  Avatar,
} from '@element-plus/icons-vue'

/** Props: 侧边栏折叠状态，由父组件 main.vue 控制 */
const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false,
  },
})

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

/**
 * 侧边栏功能树配置
 * - type: 'item' → 叶子节点，渲染为 <el-menu-item>
 * - type: 'sub'  → 父节点，渲染为 <el-sub-menu>，children 为子节点
 */
const menuConfig = [
  {
    type: 'item',
    key: 'dashboard',
    path: '/main/dashboard',
    icon: Monitor,
    label: '数据看板',
    subLabel: 'Dashboard',
  },
  {
    type: 'sub',
    key: 'sub-system-mgmt',
    icon: Setting,
    label: '系统管理',
    subLabel: 'System Management',
    children: [
      {
        type: 'item',
        key: 'users',
        path: '/main/users',
        icon: UserFilled,
        label: '用户管理',
        subLabel: 'User Management',
      },
      {
        type: 'item',
        key: 'roles',
        path: '/main/roles',
        icon: Avatar,
        label: '角色管理',
        subLabel: 'Role Management',
      },
      {
        type: 'item',
        key: 'settings',
        path: '/main/settings',
        icon: Setting,
        label: '系统配置',
        subLabel: 'System Settings',
      },
    ],
  },
  {
    type: 'item',
    key: 'audit',
    path: '/main/audit',
    icon: Checked,
    label: '内容审核与社区治理',
    subLabel: 'Content Audit & Governance',
  },
  {
    type: 'item',
    key: 'resources',
    path: '/main/resources',
    icon: FolderOpened,
    label: '公共资源与知识库维护',
    subLabel: 'Resources & Knowledge Base',
  },
]

/**
 * 收集所有叶子节点路径，用于路由匹配判断
 * 遍历 menuConfig，提取 type === 'item' 的 path 字段
 */
const allLeafPaths = []
const collectLeafPaths = (items) => {
  for (const item of items) {
    if (item.type === 'item') {
      allLeafPaths.push(item.path)
    } else if (item.type === 'sub' && item.children) {
      collectLeafPaths(item.children)
    }
  }
}
collectLeafPaths(menuConfig)

/** 当前激活的菜单路径 — 传递给 el-menu 的 default-active */
const activePath = computed(() => {
  // 先精确匹配
  if (allLeafPaths.includes(route.path)) {
    return route.path
  }
  // 再前缀匹配（处理如 /main/dashboard/xxx 的子路由）
  for (const p of allLeafPaths) {
    if (route.path.startsWith(p)) {
      return p
    }
  }
  return '/main/dashboard'
})

/**
 * 根据当前路由自动展开对应的父级子菜单
 * 当路由命中「系统管理」子节点时，自动展开 sub-system-mgmt
 */
const openedMenus = ref([])

watch(
  () => route.path,
  (path) => {
    const systemChildren = ['/main/users', '/main/roles', '/main/settings']
    if (systemChildren.some((r) => path.startsWith(r))) {
      openedMenus.value = ['sub-system-mgmt']
    }
  },
  { immediate: true },
)

/** 当前登录管理员显示名称 */
const adminName = computed(() => {
  const info = userStore.userInfo
  if (info && info.real_name) {
    return info.real_name
  }
  return '管理员'
})

/** 当前登录管理员角色标签 */
const adminRole = computed(() => {
  const info = userStore.userInfo
  if (info && info.user_type === 'admin') {
    return '超级管理员'
  }
  return '管理员'
})
</script>

<template>
  <!--
    侧边栏容器：宽度通过 sidebar-transition 动画在 240px / 64px 之间切换
    overflow-hidden 防止折叠时文字溢出
  -->
  <aside
    class="flex flex-col h-full border-r overflow-hidden flex-shrink-0 sidebar-transition"
    :class="collapsed ? 'sidebar-collapsed' : 'sidebar-expanded'"
    style="
      background: var(--zh-background-pc-sidebar);
      border-color: var(--zh-line-parting);
    "
  >
    <!-- ===== 顶部：Logo 区域（保持不变） ===== -->
    <div
      class="flex items-center h-[56px] flex-shrink-0 border-b sidebar-logo-area"
      :class="collapsed ? 'justify-center px-0 gap-0' : 'gap-2 px-3'"
      style="border-color: var(--zh-line-parting);"
    >
      <!-- Logo 图标（始终显示） -->
      <div
        class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style="background: var(--zh-gradient-blue);"
      >
        <span class="text-white font-bold text-sm">智</span>
      </div>
      <!-- Logo 文字（仅展开态显示） -->
      <span
        class="font-semibold text-base whitespace-nowrap sidebar-text-fade"
        :class="{ 'sidebar-text-hidden': collapsed }"
        style="color: var(--zh-text-primary);"
      >
        智核 Admin
      </span>
    </div>

    <!-- ===== 中部：ElementPlus 功能树菜单 ===== -->
    <el-menu
      :collapse="collapsed"
      :default-active="activePath"
      :default-openeds="openedMenus"
      router
      class="flex-1 overflow-y-auto overflow-x-hidden sidebar-menu"
      style="border-right: none;"
    >
      <!-- 遍历菜单配置：区分叶子节点 (el-menu-item) 与父节点 (el-sub-menu) -->
      <template v-for="item in menuConfig" :key="item.key">
        <!-- 叶子节点：直接可点击导航 -->
        <el-menu-item v-if="item.type === 'item'" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>
            <div class="flex flex-col min-w-0">
              <span class="menu-item-label">{{ item.label }}</span>
              <span class="menu-item-sublabel">{{ item.subLabel }}</span>
            </div>
          </template>
        </el-menu-item>

        <!-- 父节点：可展开的子菜单 -->
        <el-sub-menu v-else-if="item.type === 'sub'" :index="item.key">
          <template #title>
            <el-icon><component :is="item.icon" /></el-icon>
            <div class="flex flex-col min-w-0">
              <span class="menu-item-label">{{ item.label }}</span>
              <span class="menu-item-sublabel">{{ item.subLabel }}</span>
            </div>
          </template>
          <!-- 子菜单项 -->
          <el-menu-item
            v-for="child in item.children"
            :key="child.key"
            :index="child.path"
          >
            <el-icon><component :is="child.icon" /></el-icon>
            <template #title>
              <div class="flex flex-col min-w-0">
                <span class="menu-item-label">{{ child.label }}</span>
                <span class="menu-item-sublabel">{{ child.subLabel }}</span>
              </div>
            </template>
          </el-menu-item>
        </el-sub-menu>
      </template>
    </el-menu>

    <!-- ===== 底部：管理员信息区（保持不变） ===== -->
    <div class="flex-shrink-0 border-t px-3 py-4" :class="collapsed ? 'px-0' : ''" style="border-color: var(--zh-line-parting);">
      <!-- 折叠态下 el-tooltip 显示管理员名称 + 角色 -->
      <el-tooltip
        :content="`${adminName} · ${adminRole}`"
        placement="right"
        :disabled="!collapsed"
        :show-after="300"
        effect="dark"
      >
        <div class="flex items-center" :class="collapsed ? 'justify-center gap-0' : 'gap-3'">
          <!-- 管理员头像 -->
          <el-avatar
            :size="36"
            :src="userStore.userInfo?.avatar || undefined"
            :style="{ background: 'var(--zh-gradient-blue)' }"
          >
            {{ adminName.charAt(0) }}
          </el-avatar>

          <!-- 名称与角色（仅展开态显示） -->
          <div class="flex flex-col min-w-0 sidebar-text-fade" :class="{ 'sidebar-text-hidden': collapsed }">
            <span
              class="text-[13px] leading-5 truncate"
              style="color: var(--zh-text-primary); font-weight: 500;"
            >
              {{ adminName }}
            </span>
            <span
              class="text-[11px] leading-4"
              style="color: var(--zh-text-caption);"
            >
              {{ adminRole }}
            </span>
          </div>
        </div>
      </el-tooltip>
    </div>
  </aside>
</template>

<style scoped>
/*
 * 侧边栏容器宽度过渡动画
 * 与 ElementPlus 默认折叠动画保持一致的缓动曲线
 */
.sidebar-transition {
  transition: width 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-expanded {
  width: 240px;
}

.sidebar-collapsed {
  width: 64px;
}

/*
 * 文字区域淡入淡出
 * opacity + max-width + visibility 组合确保平滑过渡
 */
.sidebar-text-fade {
  transition:
    opacity 200ms cubic-bezier(0.4, 0, 0.2, 1),
    visibility 200ms cubic-bezier(0.4, 0, 0.2, 1),
    max-width 200ms cubic-bezier(0.4, 0, 0.2, 1);
  max-width: 160px;
}

.sidebar-text-hidden {
  opacity: 0;
  visibility: hidden;
  max-width: 0;
  transition:
    opacity 150ms cubic-bezier(0.4, 0, 0.2, 1),
    visibility 0ms 150ms,
    max-width 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Logo 区域伸缩适配 */
.sidebar-logo-area {
  transition: padding 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== ElMenu 内部样式覆盖 ===== */

/** 菜单项内的中文标签文字 */
.menu-item-label {
  font-size: var(--zh-font-size14);
  line-height: 1.25;
  color: inherit;
}

/** 菜单项内的英文副标签 */
.menu-item-sublabel {
  font-size: 11px;
  line-height: 1.25;
  color: var(--zh-text-disabled);
}

/**
 * ElMenu item 激活态样式
 * 移除默认右侧边框指示器，改用背景色高亮
 */
.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--zh-background-option-on) !important;
  color: var(--zh-text-theme) !important;
  border-right: none !important;
}

/** ElMenu item 悬浮态 */
.sidebar-menu :deep(.el-menu-item:not(.is-active):hover) {
  background: var(--zh-background-option) !important;
  color: var(--zh-text-primary) !important;
}

/** ElMenu 移除内边距，让子项左对齐 */
.sidebar-menu :deep(.el-menu) {
  padding-left: 0;
}

/** 折叠态下隐藏菜单项内的中文标签和英文副标签 */
.el-menu--collapse .menu-item-label,
.el-menu--collapse .menu-item-sublabel {
  display: none;
}

/**
 * 折叠态弹出子菜单面板 (el-popper) 样式
 * ElMenu collapse 模式下 hover 父节点时自动弹出
 */
.sidebar-menu :deep(.el-menu--popup) {
  background: var(--zh-background-pop) !important;
  border-radius: var(--zh-radius8) !important;
  box-shadow: var(--zh-shadow2) !important;
  border: 1px solid var(--zh-line-border) !important;
  padding: 4px 0 !important;
  min-width: 160px !important;
}

/** 弹出面板中的菜单项 */
.sidebar-menu :deep(.el-menu--popup .el-menu-item) {
  height: 40px;
  line-height: 40px;
  font-size: var(--zh-font-size13);
  color: var(--zh-text-secondary);
}

.sidebar-menu :deep(.el-menu--popup .el-menu-item:hover) {
  background: var(--zh-background-option);
  color: var(--zh-text-primary);
}

.sidebar-menu :deep(.el-menu--popup .el-menu-item.is-active) {
  background: var(--zh-background-option-on);
  color: var(--zh-text-theme);
}
</style>
