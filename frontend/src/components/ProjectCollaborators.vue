<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addProjectPermission, findUserByEmail, findUserByUsername, getProject, patchProject } from '../apis/teacher'
import { parsePresentationValue } from '../utils/mobilePresentation'
import { unwrapWorkspaceResult } from '../utils/workspaceEntry'

const visible = ref(false)
const busy = ref(false)
const projectId = ref(null)
const project = ref(null)
const searchType = ref('username')
const query = ref('')
const teacher = ref(null)
const error = ref('')
const permissionIds = value => {
  const ids = parsePresentationValue(value, [])
  return Array.isArray(ids) ? ids.map(Number).filter(id => Number.isInteger(id) && id > 0) : []
}
const collaborators = computed(() => permissionIds(project.value?.permissions))

const perform = async (operation, fallback) => {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try { await operation() }
  catch (failure) { error.value = failure?.message || fallback }
  finally { busy.value = false }
}

const refresh = async () => {
  project.value = unwrapWorkspaceResult(await getProject(projectId.value))
}
const open = id => {
  if (busy.value) return
  projectId.value = id
  project.value = null
  query.value = ''
  teacher.value = null
  searchType.value = 'username'
  visible.value = true
  return perform(refresh, '协作者列表加载失败')
}
defineExpose({ open })

const search = () => {
  const text = query.value.trim()
  if (!text) return ElMessage.warning('请输入教师账号')
  return perform(async () => {
    teacher.value = null
    const lookup = searchType.value === 'email' ? findUserByEmail : findUserByUsername
    const result = unwrapWorkspaceResult(await lookup(text))
    if (!result?.id) throw new Error('未找到对应教师账号')
    teacher.value = result
  }, '教师账号查询失败')
}

const add = () => perform(async () => {
  const id = Number(teacher.value?.id)
  if (!Number.isInteger(id) || id <= 0 || collaborators.value.includes(id)) return
  const updated = unwrapWorkspaceResult(await addProjectPermission(projectId.value, { user_id: id }))
  project.value = { ...project.value, ...updated }
  ElMessage.success('协作者已添加')
}, '授权失败')

const remove = id => perform(async () => {
  try {
    await ElMessageBox.confirm(`移除用户 #${id} 的项目权限？`, '移除协作者', {
      type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消',
    })
  } catch { return }
  await refresh()
  if (!collaborators.value.includes(id)) return
  const updated = unwrapWorkspaceResult(await patchProject(projectId.value, {
    current_version: project.value.current_version,
    permissions: JSON.stringify(collaborators.value.filter(userId => userId !== id)),
  }))
  project.value = { ...project.value, ...updated }
  ElMessage.success('协作者已移除')
}, '移除协作者失败')
</script>

<template>
  <el-dialog v-model="visible" title="协作授权" width="min(480px, 92vw)" :close-on-click-modal="false" :show-close="!busy" :close-on-press-escape="!busy">
    <div v-loading="busy" class="collaborators">
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <template v-if="project">
        <el-radio-group v-model="searchType" aria-label="教师账号类型" :disabled="busy" @change="teacher = null">
          <el-radio-button value="username">用户名</el-radio-button>
          <el-radio-button value="email">邮箱</el-radio-button>
        </el-radio-group>
        <form class="collaborator-search" @submit.prevent="search">
          <el-input v-model="query" :disabled="busy" :placeholder="searchType === 'email' ? '输入教师邮箱' : '输入教师用户名'" @input="teacher = null" />
          <el-button native-type="submit" type="primary" :disabled="busy">查找</el-button>
        </form>
        <div v-if="teacher" class="collaborator-row">
          <span>{{ teacher.real_name || teacher.username || `用户 #${teacher.id}` }}</span>
          <el-button :disabled="busy || collaborators.includes(Number(teacher.id)) || Number(teacher.id) === Number(project.user_id)" @click="add">
            {{ Number(teacher.id) === Number(project.user_id) ? '项目所有者' : collaborators.includes(Number(teacher.id)) ? '已授权' : '授权编辑' }}
          </el-button>
        </div>
        <h3>已授权用户</h3>
        <div v-for="id in collaborators" :key="id" class="collaborator-row">
          <span>用户 #{{ id }}</span>
          <el-button type="danger" plain :disabled="busy" @click="remove(id)">移除</el-button>
        </div>
        <p v-if="!collaborators.length" class="collaborator-empty">暂无协作者</p>
      </template>
      <el-button v-else-if="!busy" @click="perform(refresh, '协作者列表加载失败')">重新加载</el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
.collaborators { display: grid; gap: 12px; min-height: 80px; }
.collaborators h3 { margin: 8px 0 0; font-size: 17px; }
.collaborator-search, .collaborator-row { display: flex; align-items: center; gap: 10px; }
.collaborator-search .el-input { min-width: 0; }
.collaborator-row { justify-content: space-between; padding: 4px 0; font-size: 16px; overflow-wrap: anywhere; }
.collaborator-row .el-button, .collaborator-search .el-button { min-height: 44px; }
.collaborator-empty { margin: 0; color: var(--zh-text-secondary); }
</style>
