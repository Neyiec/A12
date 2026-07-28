<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock, User, CircleCheck } from '@element-plus/icons-vue'
import { changePassword, getCurrentUser, logout } from '../apis/login.js'
import { useUserStore } from '../storage/user.js'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const saving = ref(false)
const form = reactive({ current_password: '', new_password: '', confirmPassword: '' })
const user = computed(() => userStore.userInfo || {})
const avatarText = computed(() => (user.value.real_name || user.value.username || '用').slice(0, 1))
const avatarUrl = computed(() => user.value.avatar || undefined)
const rules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
  confirmPassword: [{ validator: (_, value, callback) => value === form.new_password ? callback() : callback(new Error('两次输入的密码不一致')), trigger: 'blur' }],
}
const isSuccess = res => res?.code === 0 || res?.code === 200

const refreshUser = async () => {
  const res = await getCurrentUser()
  if (isSuccess(res)) userStore.setUserInfo(res.data)
}
const submit = async () => {
  await formRef.value?.validate()
  saving.value = true
  try {
    const res = await changePassword({ current_password: form.current_password, new_password: form.new_password })
    if (!isSuccess(res)) return ElMessage.error(res.message || '密码修改失败')
    Object.assign(form, { current_password: '', new_password: '', confirmPassword: '' })
    ElMessage.success('密码已修改，请妥善保管新密码')
  } catch { /* 由请求层处理网络错误 */ } finally { saving.value = false }
}
const signOut = async () => {
  try {
    await ElMessageBox.confirm('退出后需要重新登录，是否继续？', '确认退出', { type: 'warning' })
    await logout()
  } catch (error) { if (error === 'cancel' || error === 'close') return }
  userStore.clearUser()
  router.replace('/login')
}
onMounted(() => refreshUser().catch(() => {}))
</script>

<template>
  <section class="settings-page">
    <div class="settings-heading"><span class="eyebrow">ACCOUNT CENTER</span><h1>账号与安全</h1><p>管理个人资料、登录密码和当前会话。</p></div>
    <div class="settings-grid">
      <el-card class="settings-card profile-card" shadow="never">
        <div class="card-title"><el-icon><User /></el-icon><div><h2>个人资料</h2><p>信息由账号中心统一维护</p></div></div>
        <div class="profile-summary"><el-avatar :size="64" :src="avatarUrl">{{ avatarText }}</el-avatar><div><strong>{{ user.real_name || user.username }}</strong><span>{{ user.user_type === 'admin' ? '管理员' : '教师' }}</span></div></div>
        <dl><div><dt>登录账号</dt><dd>{{ user.username || '—' }}</dd></div><div><dt>邮箱</dt><dd>{{ user.email || '—' }}</dd></div><div><dt>手机号码</dt><dd>{{ user.phone || '—' }}</dd></div></dl>
      </el-card>
      <el-card class="settings-card password-card" shadow="never">
        <div class="card-title"><el-icon><CircleCheck /></el-icon><div><h2>修改密码</h2><p>修改后建议在其他设备重新登录</p></div></div>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="当前密码" prop="current_password"><el-input v-model="form.current_password" :prefix-icon="Lock" type="password" show-password /></el-form-item>
          <el-form-item label="新密码" prop="new_password"><el-input v-model="form.new_password" :prefix-icon="Lock" type="password" show-password /></el-form-item>
          <el-form-item label="确认新密码" prop="confirmPassword"><el-input v-model="form.confirmPassword" :prefix-icon="Lock" type="password" show-password @keyup.enter="submit" /></el-form-item>
          <el-button type="primary" :loading="saving" @click="submit">保存新密码</el-button>
        </el-form>
      </el-card>
    </div>
    <el-card class="settings-card danger-zone" shadow="never"><div><h2>退出登录</h2><p>立即结束本浏览器中的服务端会话。</p></div><el-button plain type="danger" @click="signOut">退出当前账号</el-button></el-card>
  </section>
</template>

<style scoped>
.settings-page { max-width: 1080px; margin: 0 auto; padding: 48px 32px 60px; }.settings-heading { margin-bottom: 28px; }.eyebrow { color: var(--zh-text-theme); font-size: var(--zh-font-size11); font-weight: 700; letter-spacing: .14em; }.settings-heading h1 { margin: 6px 0; font-size: 30px; }.settings-heading p,.card-title p,.danger-zone p { margin: 0; color: var(--zh-text-caption); }.settings-grid { display:grid; grid-template-columns: minmax(260px,.9fr) minmax(360px,1.1fr); gap: 18px; }.settings-card { border-color: var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }.settings-card :deep(.el-card__body) { padding: 26px; }.card-title { display:flex; gap:12px; align-items:flex-start; margin-bottom: 24px; }.card-title>.el-icon { margin-top:3px; color:var(--zh-theme-primary); font-size:22px; }.card-title h2,.danger-zone h2 { margin:0 0 4px; font-size:17px; }.profile-summary { display:flex; align-items:center; gap:14px; padding-bottom:22px; border-bottom:1px solid var(--zh-line-parting); }.profile-summary :deep(.el-avatar) { display:flex; align-items:center; justify-content:center; color:#fff; background:var(--zh-theme-primary); font-size:28px; font-weight:500; line-height:1; }.profile-summary strong,.profile-summary span { display:block; }.profile-summary span { margin-top:4px; color:var(--zh-text-caption); font-size:13px; }dl { margin: 6px 0 0; }dl>div { display:flex; justify-content:space-between; gap:12px; padding:14px 0 0; }dt { color:var(--zh-text-caption); }dd { margin:0; text-align:right; word-break:break-all; }.danger-zone { margin-top:18px; }.danger-zone :deep(.el-card__body) { display:flex; align-items:center; justify-content:space-between; gap:20px; }.password-card :deep(.el-form-item) { margin-bottom:18px; }@media(max-width:760px){.settings-page{padding:28px 16px}.settings-grid{grid-template-columns:1fr}.danger-zone :deep(.el-card__body){align-items:flex-start;flex-direction:column}}
</style>
