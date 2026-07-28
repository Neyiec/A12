<!--
  [数据交互说明]
  - 功能: 内容审核与社区治理占位页面
  - 对应需求文档: §4.7.3.1 — 对教师上传的 Skill、案例进行合规性/版权/质量审核；处理用户举报
  - 待实现: 审核队列、敏感词过滤、内容上下架、举报处理
-->
<script setup>
import { Checked } from '@element-plus/icons-vue'
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20">
    <el-icon :size="64" style="color: var(--zh-text-disabled);">
      <Checked />
    </el-icon>
    <h2
      class="mt-6 text-xl font-semibold"
      style="color: var(--zh-text-primary);"
    >
      内容审核与社区治理
    </h2>
    <p
      class="mt-2 text-sm"
      style="color: var(--zh-text-caption);"
    >
      内容审核队列 · 敏感词管理 · 举报处理 · 优质内容推荐
    </p>
    <p
      class="mt-4 text-xs"
      style="color: var(--zh-text-disabled);"
    >
      此页面正在开发中，敬请期待...
    </p>
  </div>
</template>
