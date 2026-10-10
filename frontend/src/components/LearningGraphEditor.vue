<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
const props = defineProps({ graphs: { type: Object, required: true }, kind: { type: String, required: true }, save: { type: Function, required: true }, aiEdit: { type: Function, required: true }, startWithAi: Boolean })
const emit = defineEmits(['close'])
const snapshot = ref(JSON.parse(JSON.stringify(props.graphs)))
const draft = computed(() => snapshot.value[props.kind])
const isSkill = props.kind === 'skill'
const name = isSkill ? '技能图谱' : '知识图谱'
const instruction = ref('')
const aiMode = ref(props.startWithAi)
const previewReady = ref(false)
const saving = ref(false)
function addNode() {
  draft.value.nodes.push({ id: `${props.kind}_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`, label: '', level: isSkill ? '应用' : '', category: isSkill ? '' : '概念', description: '', task: '', assessment: '' })
}
function removeNode(id) {
  draft.value.nodes = draft.value.nodes.filter(node => node.id !== id)
  draft.value.edges = draft.value.edges.filter(edge => edge.source !== id && edge.target !== id)
  snapshot.value.skill.knowledge_links = (snapshot.value.skill.knowledge_links || []).filter(link => isSkill ? link.skill_id !== id : link.knowledge_id !== id)
}
function supports(id) {
  return (snapshot.value.skill.knowledge_links || []).filter(link => isSkill ? link.skill_id === id : link.knowledge_id === id).map(link => isSkill ? link.knowledge_id : link.skill_id)
}
function setSupports(id, values) {
  snapshot.value.skill.knowledge_links = [...(snapshot.value.skill.knowledge_links || []).filter(link => isSkill ? link.skill_id !== id : link.knowledge_id !== id),
    ...values.map(value => ({ knowledge_id: isSkill ? value : id, skill_id: isSkill ? id : value, relation: '支撑' }))]
}
async function requestAI() {
  if (!instruction.value.trim()) return ElMessage.warning('请填写修改要求')
  saving.value = true
  try {
    const proposal = await props.aiEdit(JSON.parse(JSON.stringify(snapshot.value)), props.kind, instruction.value)
    snapshot.value = { ...snapshot.value, ...proposal }
    previewReady.value = true
    ElMessage.success('AI 修改结果已载入下方编辑表单，请核对后保存')
  } catch (error) { ElMessage.error(error?.response?.data?.detail || error?.message || 'AI 修改失败，原图谱未改变') }
  finally { saving.value = false }
}
async function submit() {
  saving.value = true
  try {
    await props.save(JSON.parse(JSON.stringify(snapshot.value)))
    emit('close')
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '保存失败，请重试')
  } finally { saving.value = false }
}
</script>
<template>
  <el-dialog :model-value="true" :title="`修改${name}`" width="min(760px, 94vw)" append-to-body
    :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" @close="emit('close')">
    <p class="editor-hint">两张图谱分别保留 4–12 个节点。技能需填写课堂任务、达标依据及支撑知识；删除知识点后请重新关联受影响的技能。</p>
    <el-button text :disabled="saving" @click="aiMode = !aiMode">{{ aiMode ? '收起 AI 修改' : '让 AI 修改' }}</el-button>
    <div v-if="aiMode" class="ai-edit">
      <el-input v-model="instruction" type="textarea" :rows="3" maxlength="2000" :disabled="saving" :placeholder="isSkill ? '例如：增加实验探究能力，细化课堂任务与达标依据' : '例如：细分折射规律、补充先修概念和生活应用'" />
      <el-button :loading="saving" @click="requestAI">生成修改预览</el-button>
      <p v-if="previewReady">AI 建议已载入下方，尚未保存；您可继续编辑或取消。</p>
    </div>
    <div class="editor-body">
      <section v-for="(node, index) in draft.nodes" :key="node.id" class="skill-edit-node">
        <header><strong>{{ isSkill ? '能力' : '知识点' }} {{ index + 1 }}</strong><el-button type="danger" text :disabled="saving || draft.nodes.length <= 4" @click="removeNode(node.id)">删除</el-button></header>
        <el-form label-position="top" :disabled="saving">
          <el-form-item :label="isSkill ? '能力名称' : '知识名称'"><el-input v-model="node.label" maxlength="48" /></el-form-item>
          <el-form-item v-if="isSkill" label="能力层级"><el-input v-model="node.level" maxlength="30" /></el-form-item>
          <el-form-item v-else label="知识类别"><el-input v-model="node.category" maxlength="30" placeholder="概念、原理、现象、应用" /></el-form-item>
          <el-form-item label="节点说明"><el-input v-model="node.description" type="textarea" maxlength="180" /></el-form-item>
          <el-form-item v-if="isSkill" label="课堂任务"><el-input v-model="node.task" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" maxlength="240" show-word-limit /></el-form-item>
          <el-form-item v-if="isSkill" label="达标依据"><el-input v-model="node.assessment" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" maxlength="240" show-word-limit /></el-form-item>
          <el-form-item :label="isSkill ? '支撑知识点' : '支撑的技能'"><el-select :model-value="supports(node.id)" multiple style="width:100%" @update:model-value="setSupports(node.id, $event)"><el-option v-for="other in snapshot[isSkill ? 'knowledge' : 'skill'].nodes" :key="other.id" :label="other.label" :value="other.id" /></el-select></el-form-item>
        </el-form>
      </section>
      <el-button :disabled="saving || draft.nodes.length >= 12" @click="addNode">添加{{ isSkill ? '能力' : '知识' }}节点</el-button>
      <h4>节点关系</h4>
      <div v-for="(edge, index) in draft.edges" :key="index" class="edge-row">
        <el-select v-model="edge.source" aria-label="起始能力" :disabled="saving"><el-option v-for="node in draft.nodes" :key="node.id" :value="node.id" :label="node.label || '未命名能力'" /></el-select>
        <el-input v-model="edge.relation" aria-label="关系类型" maxlength="16" :disabled="saving" placeholder="先修 / 递进 / 应用" />
        <el-select v-model="edge.target" aria-label="目标能力" :disabled="saving"><el-option v-for="node in draft.nodes" :key="node.id" :value="node.id" :label="node.label || '未命名能力'" /></el-select>
        <el-button type="danger" text :disabled="saving" @click="draft.edges.splice(index, 1)">删除</el-button>
      </div>
      <el-button :disabled="saving || draft.edges.length >= 24" @click="draft.edges.push({ source: '', target: '', relation: isSkill ? '递进' : '先修' })">添加关系</el-button>
    </div>
    <template #footer><el-button :disabled="saving" @click="emit('close')">取消</el-button><el-button type="primary" :loading="saving" @click="submit">保存{{ name }}</el-button></template>
  </el-dialog>
</template>
<style scoped>
.editor-hint { color: #67758b; line-height: 1.7; margin-top: 0; }
.ai-edit { display: grid; gap: 10px; margin-bottom: 16px; }
.ai-edit p { color: #287859; }
.editor-body { max-height: 60vh; overflow-y: auto; padding: 0 8px 8px 0; }
.skill-edit-node { padding: 14px; border: 1px solid #e3e9ef; border-radius: 12px; margin-bottom: 14px; }
.skill-edit-node header { display: flex; justify-content: space-between; align-items: center; }
.edge-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .7fr) minmax(0, 1fr) auto; gap: 8px; margin-bottom: 12px; }
@media (max-width: 600px) { .edge-row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); } }
</style>
