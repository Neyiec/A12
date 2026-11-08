<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { get, post } from '@/utils/api'

const data = ref(null)
const error = ref('')
const busy = ref(false)
const selectedVersion = ref(null)
const rollbackVersion = ref(null)
const hasMockData = computed(() => (data.value?.versions || []).some(version => String(version.name || '').includes('[MOCK]')))
const percent = ref(10)
const base = '/api/v1/python/agent-evolution'
const candidates = computed(() => (data.value?.versions || []).filter(v => v.id !== data.value?.release.active_version))
const rollbackVersions = computed(() => {
  const ids = new Set()
  for (const item of data.value?.history || []) {
    ids.add(item.before_state.active_version)
    ids.add(item.after_state.active_version)
  }
  return (data.value?.versions || []).filter(item => ids.has(item.id) && item.id !== data.value?.release.active_version)
})
const ratio = (number, denominator) => denominator ? (Number(number) / Number(denominator) * 100).toFixed(1) + '%' : '—'
async function load() {
  error.value = ''
  try {
    const response = await get(base)
    data.value = response.data
  } catch (cause) {
    error.value = cause?.response?.data?.detail || cause?.message || '读取策略版本失败'
  }
}
async function perform(path, payload) {
  if (busy.value) return
  busy.value = true
  try {
    await post(base + path, payload || {})
    ElMessage.success('操作已保存')
    await load()
  } catch (cause) {
    ElMessage.error(cause?.response?.data?.detail || cause?.message || '操作失败')
  } finally { busy.value = false }
}
async function approve(version) {
  try {
    await ElMessageBox.confirm('确认已核对候选中的教学要求与布局规则？确认后仍需单独开启灰度。', '人工确认候选')
  } catch { return }
  await perform('/versions/' + version.id + '/approve')
}
async function release(action) {
  let reason
  try {
    const result = await ElMessageBox.prompt('填写本次操作依据，系统会保存版本与操作者。', '确认发布操作', {
      inputValidator: value => Boolean(value?.trim()) || '请填写依据',
    })
    reason = result.value.trim()
  } catch { return }
  await perform('/release', { action, reason, expected_revision: data.value.release.revision,
    version_id: action === 'rollback' ? rollbackVersion.value : selectedVersion.value, percent: percent.value })
}
onMounted(load)
</script>

<template>
  <el-card class="mb-4" shadow="never">
    <template #header>Agent 持续优化 · 候选与灰度</template>
    <p>知识资料更新、教学策略发布和教师偏好积累分别记录。候选来自重复反馈，经过人工确认后进入教师灰度。</p>
    <div class="evolution-actions">
      <el-button :disabled="busy" @click="load">刷新</el-button>
      <el-button :loading="busy" @click="perform('/candidates')">从反馈整理候选</el-button>
      <el-button :loading="busy" @click="perform('/candidates', { template_update: true })">从当前模板创建候选</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template v-if="data">
      <el-alert v-if="hasMockData" title="当前包含 Mock 联调样例，模拟指标仅用于流程验证，不代表真实教学成效。" type="warning" :closable="false" />
      <p>正式版本 v{{ data.release.active_version }} · 发布记录 #{{ data.release.revision }} ·
        灰度 {{ data.release.canary_version ? 'v' + data.release.canary_version + ' / ' + data.release.canary_percent + '%' : '未开启' }}</p>
      <el-table :data="data.versions" size="small" max-height="360">
        <el-table-column prop="id" label="版本" width="70" />
        <el-table-column prop="name" label="名称" width="130" />
        <el-table-column prop="template_count" label="模板快照项" width="110" />
        <el-table-column label="候选内容" min-width="240">
          <template #default="{ row }">
            <p class="evolution-rule">{{ row.instruction || '使用内置生成提示' }}</p>
            <small>{{ row.layout_rule }}</small>
          </template>
        </el-table-column>
        <el-table-column label="反馈证据" min-width="120">
          <template #default="{ row }">
            <div v-for="(value, key) in row.evidence" :key="key">{{ key }} · {{ value.teachers }} 位教师 / {{ value.units }} 个作品</div>
          </template>
        </el-table-column>
        <el-table-column label="人工确认" width="120">
          <template #default="{ row }">
            <el-button v-if="!row.approved_by" :disabled="busy" size="small" @click="approve(row)">确认候选</el-button>
            <span v-else>已确认</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="evolution-actions">
        <el-select v-model="selectedVersion" aria-label="灰度候选版本" placeholder="已确认候选" style="width:170px">
          <el-option v-for="item in candidates.filter(v => v.approved_by)" :key="item.id" :label="'v' + item.id + ' ' + item.name" :value="item.id" />
        </el-select>
        <el-select v-model="percent" aria-label="灰度比例" style="width:100px">
          <el-option v-for="value in [5, 10, 20]" :key="value" :value="value" :label="value + '%'" />
        </el-select>
        <el-button :disabled="busy || !selectedVersion || Boolean(data.release.canary_version)" @click="release('canary')">开启灰度</el-button>
        <el-button type="primary" :disabled="busy || !data.release.canary_version" @click="release('promote')">评估并正式发布</el-button>
        <el-button :disabled="busy || !data.release.canary_version" @click="release('stop')">结束灰度</el-button>
      </div>
      <p>当前轮次近 90 天统计。采纳率为已采纳或已成功导出的课件占生成成功课件的比例；一次通过率为未修改、首次导出即成功的课件占已导出课件的比例；平均修改轮次按生成成功课件计算。</p>
      <el-table :data="data.effects" size="small">
        <el-table-column prop="version_id" label="版本" />
        <el-table-column label="组别"><template #default="{ row }">{{ row.cohort === 'canary' ? '灰度组' : '对照组' }}</template></el-table-column>
        <el-table-column prop="generated" label="生成成功" />
        <el-table-column label="采纳率"><template #default="{ row }">{{ ratio(row.adopted, row.generated) }}</template></el-table-column>
        <el-table-column label="一次通过率"><template #default="{ row }">{{ ratio(row.first_pass, row.exported_runs) }}</template></el-table-column>
        <el-table-column label="平均修改轮次"><template #default="{ row }">{{ row.generated ? (row.revision_rounds / row.generated).toFixed(2) : '—' }}</template></el-table-column>
        <el-table-column label="PPTX 导出通过率"><template #default="{ row }">{{ ratio(row.exports_ok, row.exports) }}</template></el-table-column>
      </el-table>
      <p>正式发布要求两组各至少 5 份已导出的课件，导出通过率与平均修改轮次均不劣于基线，且至少一项改善。数据不足时保留灰度。</p>
      <div class="evolution-actions">
        <el-select v-model="rollbackVersion" aria-label="回滚目标版本" placeholder="历史正式版本" style="width:200px">
          <el-option v-for="item in rollbackVersions" :key="item.id" :label="'v' + item.id + ' ' + item.name" :value="item.id" />
        </el-select>
        <el-button :disabled="busy || !rollbackVersion" @click="release('rollback')">回滚正式版本</el-button>
      </div>
      <details>
        <summary>发布与回滚记录</summary>
        <p v-for="item in data.history" :key="item.id">#{{ item.id }} · {{ item.action }} · 操作者 {{ item.actor }} · {{ item.reason }}</p>
      </details>
    </template>
  </el-card>
</template>

<style scoped>
.evolution-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.evolution-actions :deep(.el-button) { margin-left: 0; }
.evolution-rule { white-space: pre-wrap; }
p { line-height: 1.6; }
</style>
