<script setup>
import { useRoute, useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
const route = useRoute()
const router = useRouter()
const backHome = () => router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
</script>

<template>
  <main class="question-bank-pending">
    <el-icon aria-hidden="true"><Document /></el-icon>
    <h1>题库与组卷</h1>
    <p>题库页面尚未接入，暂时无法浏览题目或组卷。</p>
    <el-button type="primary" @click="backHome">返回主页</el-button>
  </main>
</template>

<style scoped>
.question-bank-pending{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60dvh;gap:16px;padding:40px 24px;text-align:center;color:var(--zh-text-primary)}
.question-bank-pending>.el-icon{font-size:56px;color:var(--zh-text-theme)}.question-bank-pending h1{margin:0;font-size:26px;font-weight:650}.question-bank-pending p{max-width:28ch;margin:0 0 8px;font-size:16px;line-height:1.8;color:var(--zh-text-secondary)}
</style>
