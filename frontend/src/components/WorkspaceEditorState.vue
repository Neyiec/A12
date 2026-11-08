<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
const props = defineProps({ error: { type: [Object, String], default: null } })
const router = useRouter()
const failed = computed(() => Boolean(props.error))
const reload = () => window.location.reload()
</script>

<template>
  <main class="workspace-editor-state" :role="failed ? 'alert' : 'status'" aria-live="polite">
    <section>
      <span class="workspace-state-label">个人工作台</span>
      <h1>{{ failed ? '工作台暂时未能打开' : '正在打开个人工作台…' }}</h1>
      <p>{{ failed ? '编辑器依赖加载或初始化失败。刷新后可按当前会话重新进入，页面地址和已有大纲会保留。' : '正在加载编辑器，请稍候；打开后将按已确认的大纲生成 PPT。' }}</p>
      <div v-if="failed" class="workspace-state-actions">
        <el-button type="primary" @click="reload">刷新并重试</el-button>
        <el-button @click="router.push('/main')">返回教学助手</el-button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.workspace-editor-state{min-height:100dvh;display:grid;place-items:center;padding:24px;box-sizing:border-box;background:#f4f8ff;color:#172b4d}
section{width:min(560px,100%);padding:32px;box-sizing:border-box;background:white;border:1px solid #dbe7ff;border-radius:20px}
.workspace-state-label{color:#2563eb;font-size:14px;font-weight:600}h1{font-size:24px;line-height:1.4;margin:16px 0}p{color:#526581;line-height:1.8;margin:0}
.workspace-state-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}.workspace-state-actions .el-button{margin-left:0}
</style>
