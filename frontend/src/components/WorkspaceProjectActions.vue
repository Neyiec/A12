<script setup>
defineProps({
  status: { type: String, default: '' },
  savingVersion: Boolean,
  canUndo: Boolean,
})
defineEmits(['undo', 'quality', 'save-version', 'versions', 'permissions'])
</script>

<template>
  <nav class="project-utilities" aria-label="项目操作">
    <span role="status">{{ status }}</span>
    <el-button v-if="canUndo" text size="small" type="warning" @click="$emit('undo')">撤销本次 AI 修改</el-button>
    <el-button text size="small" @click="$emit('quality')">质量建议</el-button>
    <el-button text size="small" :loading="savingVersion" @click="$emit('save-version')">保存快照</el-button>
    <el-button text size="small" :disabled="savingVersion" @click="$emit('versions')">快照与恢复</el-button>
    <el-button text size="small" @click="$emit('permissions')">协作授权</el-button>
  </nav>
</template>

<style scoped>
.project-utilities{position:absolute;z-index:5;bottom:52px;left:50%;display:flex;align-items:center;gap:4px;width:max-content;max-width:calc(100% - 32px);overflow-x:auto;padding:5px 8px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);color:var(--zh-text-caption);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1);font-size:11px;transform:translateX(-50%)}
.project-utilities span{margin:0 4px;white-space:nowrap}
.project-utilities .el-button{flex-shrink:0}
</style>
