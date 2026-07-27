<!--
  [数据交互说明]
  - 功能: 系统配置占位页面
  - 对应需求文档: 系统参数配置、平台设置、管理员管理
  - 待实现: 系统参数配置、管理员账号管理、平台公告管理、数据统计与报表导出
-->
<script setup>
import { Setting } from '@element-plus/icons-vue'
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20">
    <el-icon :size="64" style="color: var(--zh-text-disabled);">
      <Setting />
    </el-icon>
    <h2
      class="mt-6 text-xl font-semibold"
      style="color: var(--zh-text-primary);"
    >
      系统配置
    </h2>
    <p
      class="mt-2 text-sm"
      style="color: var(--zh-text-caption);"
    >
      系统参数配置 · 管理员管理 · 平台公告 · 数据报表
    </p>
    <p
      class="mt-4 text-xs"
      style="color: var(--zh-text-disabled);"
    >
      此页面正在开发中，敬请期待...
    </p>
  </div>
</template>
