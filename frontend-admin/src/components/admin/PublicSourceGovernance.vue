<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest } from '@/utils/api'
const emit = defineEmits(['register'])
const data = ref(null), busy = ref(false), error = ref('')
const base = '/api/v1/python/resources/index/governance'
let active = true
onBeforeUnmount(() => { active = false })
async function load() {
  try {
    const response = await apiRequest({ url: base })
    if (active) { data.value = response.data; error.value = '' }
  } catch (cause) { if (active) error.value = cause.message || '来源检查读取失败' }
}
async function patrol() {
  if (busy.value) return
  busy.value = true
  try {
    const result = await apiRequest({ url: base + '/patrol', method: 'post', timeout: 120000 })
    if (!active) return
    ElMessage.success(`已巡检 ${result.data.checked} 项，其中 ${result.data.warnings} 项需关注`)
    await load()
  } catch (cause) { if (active) error.value = cause.message || '巡检失败' }
  finally { busy.value = false }
}
defineExpose({ load })
onMounted(load)
</script>

<template>
  <el-card shadow="never" class="source-governance">
    <template #header><div class="source-actions"><strong>公共知识来源与时效</strong><el-button :disabled="busy" @click="load">刷新</el-button><el-button type="primary" :loading="busy" @click="patrol">巡检来源</el-button></div></template>
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
    <template v-if="data">
      <p>共 {{ data.total }} 项已入索引公共资料，{{ data.blocked }} 项暂不可引用，{{ data.warnings }} 项需关注。每次巡检最久未检查的 20 项；后台每 6 小时自动执行。</p>
      <p>超时或访问受限会提醒人工核对；明确 404 / 410 的来源、过期资料与登记不完整资料停止公共 RAG 引用，补齐登记或复核后可恢复。</p>
      <el-table :data="data.items.slice(0, 15)" size="small" max-height="380">
        <el-table-column prop="title" label="资料" min-width="160" />
        <el-table-column label="来源版本" min-width="170"><template #default="{row}">{{ row.assessment.version_label || '待登记' }} · {{ row.assessment.version_year || '—' }}</template></el-table-column>
        <el-table-column label="核查结果" min-width="240"><template #default="{row}">{{ row.assessment.reasons.join('；') || row.source_check.warning || '登记有效' }}<br><small>{{ row.source_check.checked_at || '尚未巡检' }}</small></template></el-table-column>
        <el-table-column label="操作" width="100"><template #default="{row}"><el-button link type="primary" @click="emit('register', row.resource_id)">来源登记</el-button></template></el-table-column>
      </el-table>
      <details><summary>最近巡检记录</summary><p v-for="item in data.history" :key="item.id">{{ item.created_at }} · {{ item.actor }} · 检查 {{ item.checked_count }} 项 / 提醒 {{ item.warning_count }} 项</p></details>
    </template>
  </el-card>
</template>

<style scoped>
.source-governance { margin: 16px 0; color: #243754; border-color:#dce7ff; }
.source-actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.source-actions strong { margin-right:auto; }
p { line-height:1.7; color:#526580; font-size:13px; }
</style>
