<!--
  [数据交互说明]
  - 功能: 公共资源与知识库维护占位页面
  - 对应需求文档: §4.7.3.2 — 批量上传官方教材/题库/多媒体素材，系统自动解析向量化
  - 待实现: 资源上传、分类管理、向量化状态监控、知识库检索
-->
<script setup>
import { FolderOpened } from '@element-plus/icons-vue'
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20">
    <el-icon :size="64" style="color: var(--zh-text-disabled);">
      <FolderOpened />
    </el-icon>
    <h2
      class="mt-6 text-xl font-semibold"
      style="color: var(--zh-text-primary);"
    >
      公共资源与知识库维护
    </h2>
    <p
      class="mt-2 text-sm"
      style="color: var(--zh-text-caption);"
    >
      教材上传 · 题库管理 · 多媒体素材 · 向量化处理
    </p>
    <p
      class="mt-4 text-xs"
      style="color: var(--zh-text-disabled);"
    >
      此页面正在开发中，敬请期待...
    </p>
  </div>
</template>
