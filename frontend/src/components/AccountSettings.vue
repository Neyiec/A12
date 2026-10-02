<script setup>
/**
 * [数据交互说明]
 * - 导出: AccountSettings 账号设置页面组件
 * - 依赖:
 *   - ../apis/login.js: 导入 changePassword, getCurrentUser, logout
 *   - ../apis/teacher.js: 导入 getTeacherPreferences, saveTeacherPreferences
 *   - ../storage/user.js: 导入 useUserStore
 *   - ../config/preferences.config.js: 导入 TEACHING_STYLES, TEMPLATES, INTERACTION_FORMS, PREFERENCES_DEFAULTS
 *   - @element-plus/icons-vue: 导入图标组件
 * - 输入: 接收来自路由的用户导航行为
 * - 输出: 通过 API 更新用户密码、偏好设置；通过 userStore 更新本地用户状态
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Lock, User, CircleCheck, Setting, Key, Phone,
  MagicStick, Document, Share, FolderOpened, Refresh,
  Grid, Collection, Star, Monitor,
  ChatDotRound, EditPen, Promotion, Message, Microphone,
} from '@element-plus/icons-vue'
import { changeContact, changePassword, getCurrentUser, logout, sendVerificationCode } from '../apis/login.js'
import { getTeacherPreferences, saveTeacherPreferences } from '../apis/teacher.js'
import { useUserStore } from '../storage/user.js'
import { TEACHING_STYLES, TEMPLATES, INTERACTION_FORMS, PREFERENCES_DEFAULTS } from '../config/preferences.config.js'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const saving = ref(false)
const passwordDialogVisible = ref(false)
const form = reactive({ current_password: '', new_password: '', confirmPassword: '' })
const user = computed(() => userStore.userInfo || {})
const avatarText = computed(() => (user.value.real_name || user.value.username || '用').slice(0, 1))
const avatarUrl = computed(() => user.value.avatar || undefined)
const maskContact = (value) => {
  if (!value) return '未绑定'
  if (value.length <= 5) return `${value.slice(0, 1)}***${value.slice(-1)}`
  return `${value.slice(0, 3)}****${value.slice(-2)}`
}
const maskEmail = (value) => {
  if (!value || !value.includes('@')) return '未绑定'
  const [local, ...domainParts] = value.split('@')
  const domain = domainParts.join('@')
  const visible = local.slice(0, 3)
  return `${visible}${local.length > 3 ? '****' : ''}@${domain}`
}
const maskedEmail = computed(() => maskEmail(user.value.email))
const maskedPhone = computed(() => maskContact(user.value.phone))
const rules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
  confirmPassword: [{ validator: (_, value, callback) => value === form.new_password ? callback() : callback(new Error('两次输入的密码不一致')), trigger: 'blur' }],
}
const isSuccess = res => res?.code === 0 || res?.code === 200

const contactDialogVisible = ref(false)
const contactFormRef = ref()
const contactSaving = ref(false)
const contactCodeLoading = ref(false)
const contactCountdown = ref(0)
let contactTimer
const contactForm = reactive({ real_name: '', email: '', phone: '', code: '' })
const contactRules = {
  real_name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '真实姓名长度需要在 2 到 50 个字符之间', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^1\d{10}$/, message: '请输入正确的 11 位手机号', trigger: 'blur' }],
  code: [{ required: true, len: 6, message: '请输入 6 位验证码', trigger: 'blur' }],
}

const openPasswordDialog = () => {
  Object.assign(form, { current_password: '', new_password: '', confirmPassword: '' })
  passwordDialogVisible.value = true
}

const openContactDialog = () => {
  Object.assign(contactForm, { real_name: user.value.real_name || '', email: '', phone: '', code: '' })
  contactDialogVisible.value = true
}

const startContactCountdown = () => {
  contactCountdown.value = 60
  clearInterval(contactTimer)
  contactTimer = setInterval(() => {
    contactCountdown.value -= 1
    if (contactCountdown.value <= 0) clearInterval(contactTimer)
  }, 1000)
}

const sendContactCode = async () => {
  if (!user.value.email) return ElMessage.warning('当前账号未绑定邮箱，请联系管理员处理')
  contactCodeLoading.value = true
  try {
    const res = await sendVerificationCode({
      username: user.value.username,
      scene: 'profile_update',
      channel: 'email',
    })
    if (!isSuccess(res)) return ElMessage.error(res.message || '验证码发送失败')
    startContactCountdown()
    ElMessage.success(`验证码已发送至原邮箱 ${maskedEmail.value}`)
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '验证码发送失败，请稍后重试')
  } finally {
    contactCodeLoading.value = false
  }
}

const submitContact = async () => {
  const realNameChanged = contactForm.real_name.trim() !== String(user.value.real_name || '').trim()
  if (!realNameChanged && !contactForm.email.trim() && !contactForm.phone.trim()) {
    return ElMessage.warning('请修改真实姓名，或填写新的邮箱、手机号')
  }
  await contactFormRef.value?.validate()
  contactSaving.value = true
  try {
    const res = await changeContact({
      real_name: contactForm.real_name.trim(),
      email: contactForm.email.trim(),
      phone: contactForm.phone.trim(),
      code: contactForm.code.trim(),
    })
    if (!isSuccess(res)) return ElMessage.error(res.message || '个人信息修改失败')
    userStore.setUserInfo(res.data)
    contactDialogVisible.value = false
    ElMessage.success('个人信息已更新')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '个人信息修改失败，请稍后重试')
  } finally {
    contactSaving.value = false
  }
}

// ========== 偏好设置 ==========

/** 图标字符串 → 组件映射（与 preferences.config.js 中的 icon 字段对应） */
const iconMap = {
  MagicStick, Document, Share, FolderOpened, Refresh,
  Grid, Collection, Star, Monitor,
  User, ChatDotRound, EditPen, Promotion, Message, Microphone,
  Setting, CircleCheck,
}

/** 当前编辑中的偏好设置 */
const preferences = reactive({
  teachingStyle: PREFERENCES_DEFAULTS.teachingStyle,
  templateStyle: PREFERENCES_DEFAULTS.templateStyle,
  interactionForms: [...PREFERENCES_DEFAULTS.interactionForms],
})

/** 偏好保存按钮 loading 态 */
const savingPrefs = ref(false)

/** 偏好初始加载 loading 态 */
const loadingPrefs = ref(false)

/**
 * 加载教师已保存的偏好设置
 * 接口成功且有数据则回填，否则使用系统默认值
 */
async function loadPreferences() {
  loadingPrefs.value = true
  try {
    const res = await getTeacherPreferences()
    if (isSuccess(res) && res.data) {
      preferences.teachingStyle = res.data.teaching_style ?? PREFERENCES_DEFAULTS.teachingStyle
      preferences.templateStyle = res.data.template_style ?? PREFERENCES_DEFAULTS.templateStyle
      preferences.interactionForms = res.data.interaction_forms?.length
        ? res.data.interaction_forms
        : [...PREFERENCES_DEFAULTS.interactionForms]
    }
  } catch {
    // 接口异常时继续使用默认值，不打扰用户
  } finally {
    loadingPrefs.value = false
  }
}

/**
 * 切换互动形式多选状态：已选中则移除，未选中则添加
 * @param {string} value - 要切换的互动形式值
 */
function toggleInteraction(value) {
  const idx = preferences.interactionForms.indexOf(value)
  if (idx >= 0) {
    preferences.interactionForms.splice(idx, 1)
  } else {
    preferences.interactionForms.push(value)
  }
}

/**
 * 保存偏好设置到服务端
 * 成功显示绿色提示，失败显示错误消息并允许重试
 */
async function savePreferences() {
  savingPrefs.value = true
  try {
    const res = await saveTeacherPreferences({
      teaching_style: preferences.teachingStyle,
      template_style: preferences.templateStyle,
      interaction_forms: preferences.interactionForms,
    })
    if (!isSuccess(res)) return ElMessage.error(res.message || '偏好保存失败')
    ElMessage.success('偏好设置已保存')
  } catch (error) {
    const message = error?.response?.data?.message
      || (error?.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '')
      || error?.message
      || '偏好保存失败，请稍后重试'
    ElMessage.error(message)
  } finally {
    savingPrefs.value = false
  }
}

/**
 * 恢复默认偏好设置
 * 弹出确认框，用户确认后重置所有选项为系统默认值
 */
async function resetPreferences() {
  try {
    await ElMessageBox.confirm(
      '恢复默认设置将清除您的个人偏好配置，是否继续？',
      '确认恢复',
      { type: 'warning' },
    )
  } catch {
    return // 用户取消
  }
  preferences.teachingStyle = PREFERENCES_DEFAULTS.teachingStyle
  preferences.templateStyle = PREFERENCES_DEFAULTS.templateStyle
  preferences.interactionForms = [...PREFERENCES_DEFAULTS.interactionForms]
  ElMessage.success('已恢复默认设置')
}

// ========== 已有账号方法 ==========

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
    passwordDialogVisible.value = false
    ElMessage.success('密码已修改，请妥善保管新密码')
  } catch (error) {
    const message = error?.response?.data?.message
      || (error?.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '')
      || error?.message
      || '密码修改失败，请稍后重试'
    ElMessage.error(message)
  } finally { saving.value = false }
}
const signOut = async () => {
  try {
    await ElMessageBox.confirm('退出后需要重新登录，是否继续？', '确认退出', { type: 'warning' })
    await logout()
  } catch (error) { if (error === 'cancel' || error === 'close') return }
  userStore.clearUser()
  router.replace('/login')
}
onMounted(() => {
  refreshUser().catch(() => ElMessage.error('个人资料加载失败，请检查后端服务后重试'))
  loadPreferences()
})
onBeforeUnmount(() => clearInterval(contactTimer))
</script>

<template>
  <section class="settings-page">
    <div class="settings-heading"><span class="eyebrow">ACCOUNT CENTER</span><h1>账号与安全</h1><p>管理个人资料、登录密码和当前会话。</p></div>
    <div class="settings-grid">
      <el-card class="settings-card profile-card" shadow="never">
        <div class="card-title card-title-with-action">
          <el-icon><User /></el-icon>
          <div><h2>个人资料</h2><p>信息由账号中心统一维护</p></div>
          <el-button class="card-action" type="primary" plain @click="openContactDialog">修改个人信息</el-button>
        </div>
        <div class="profile-summary"><el-avatar :size="64" :src="avatarUrl">{{ avatarText }}</el-avatar><div><strong>{{ user.real_name || user.username }}</strong><span>{{ user.user_type === 'admin' ? '管理员' : '教师' }}</span></div></div>
        <dl><div><dt>登录账号</dt><dd>{{ user.username || '—' }}</dd></div><div><dt>真实姓名</dt><dd>{{ user.real_name || '未填写' }}</dd></div><div><dt>邮箱</dt><dd>{{ maskedEmail }}</dd></div><div><dt>手机号码</dt><dd>{{ maskedPhone }}</dd></div></dl>
      </el-card>
      <el-card class="settings-card password-card" shadow="never">
        <div class="card-title"><el-icon><CircleCheck /></el-icon><div><h2>登录密码</h2><p>定期更新密码可以提高账号安全性</p></div></div>
        <div class="security-action-row">
          <div><strong>当前密码</strong><span>已设置，可用于账号密码登录</span></div>
          <el-button type="primary" @click="openPasswordDialog">修改密码</el-button>
        </div>
      </el-card>
    </div>

    <!-- 个人偏好设置 -->
    <el-card class="settings-card preferences-card" shadow="never">
      <div class="card-title">
        <el-icon><component :is="iconMap.Setting" /></el-icon>
        <div>
          <h2>个人偏好设置</h2>
          <p>配置您的教学风格与默认偏好，AI 将据此生成更贴合您个人特色的教学内容。</p>
        </div>
      </div>

      <div v-loading="loadingPrefs" class="preferences-body">
        <!-- 区块1：默认教学风格（单选） -->
        <fieldset class="pref-section">
          <legend class="pref-section-title">默认教学风格</legend>
          <div class="pref-option-grid pref-option-grid--5">
            <button
              v-for="style in TEACHING_STYLES"
              :key="style.value"
              type="button"
              class="pref-card"
              data-hover-lift
              :aria-pressed="preferences.teachingStyle === style.value"
              :class="{ selected: preferences.teachingStyle === style.value }"
              @click="preferences.teachingStyle = style.value"
            >
              <span class="pref-card-icon">
                <el-icon><component :is="iconMap[style.icon]" /></el-icon>
              </span>
              <span class="pref-card-copy">
                <strong>{{ style.label }}</strong>
                <small>{{ style.desc }}</small>
              </span>
              <el-icon v-if="preferences.teachingStyle === style.value" class="pref-card-check"><CircleCheck /></el-icon>
            </button>
          </div>
        </fieldset>

        <!-- 区块2：默认课件模板（单选，带缩略图占位） -->
        <fieldset class="pref-section">
          <legend class="pref-section-title">默认课件模板</legend>
          <div class="pref-option-grid pref-option-grid--4">
            <button
              v-for="tpl in TEMPLATES"
              :key="tpl.value"
              type="button"
              class="pref-card pref-card--template"
              data-hover-lift
              :aria-pressed="preferences.templateStyle === tpl.value"
              :class="{ selected: preferences.templateStyle === tpl.value }"
              @click="preferences.templateStyle = tpl.value"
            >
              <span class="pref-thumb">
                <el-icon><component :is="iconMap[tpl.icon]" /></el-icon>
              </span>
              <span class="pref-card-copy">
                <strong>{{ tpl.label }}</strong>
                <small>{{ tpl.desc }}</small>
              </span>
              <el-icon v-if="preferences.templateStyle === tpl.value" class="pref-card-check"><CircleCheck /></el-icon>
            </button>
          </div>
        </fieldset>

        <!-- 区块3：默认互动形式（多选） -->
        <fieldset class="pref-section">
          <legend class="pref-section-title">
            默认互动形式
            <small v-if="preferences.interactionForms.length" class="pref-chip-count">已选 {{ preferences.interactionForms.length }} 项</small>
          </legend>
          <div class="pref-chip-grid">
            <button
              v-for="form in INTERACTION_FORMS"
              :key="form.value"
              type="button"
              class="pref-chip"
              :aria-pressed="preferences.interactionForms.includes(form.value)"
              :class="{ on: preferences.interactionForms.includes(form.value) }"
              @click="toggleInteraction(form.value)"
            >
              <el-icon><component :is="iconMap[form.icon]" /></el-icon>
              <span>{{ form.label }}</span>
            </button>
          </div>
        </fieldset>

        <!-- 操作区 -->
        <div class="pref-footer">
          <el-button type="primary" :loading="savingPrefs" @click="savePreferences">保存偏好设置</el-button>
          <el-button type="primary" link @click="resetPreferences">恢复默认</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="settings-card danger-zone" shadow="never"><div><h2>退出登录</h2><p>立即结束本浏览器中的服务端会话。</p></div><el-button plain type="danger" @click="signOut">退出当前账号</el-button></el-card>

    <el-dialog v-model="passwordDialogVisible" title="修改登录密码" width="min(460px, calc(100vw - 24px))" align-center :close-on-click-modal="false" class="account-dialog">
      <p class="dialog-tip">修改成功后，请使用新密码完成后续登录。</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="当前密码" prop="current_password"><el-input v-model="form.current_password" :prefix-icon="Lock" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-form-item label="新密码" prop="new_password"><el-input v-model="form.new_password" :prefix-icon="Lock" type="password" show-password autocomplete="new-password" /></el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword"><el-input v-model="form.confirmPassword" :prefix-icon="Lock" type="password" show-password autocomplete="new-password" @keyup.enter="submit" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="passwordDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submit">确认修改</el-button></template>
    </el-dialog>

    <el-dialog v-model="contactDialogVisible" title="修改个人信息" width="min(500px, calc(100vw - 24px))" align-center :close-on-click-modal="false" class="account-dialog">
      <div class="verification-notice">
        <el-icon><Message /></el-icon>
        <div><strong>验证原邮箱</strong><p>为保护账号安全，验证码将发送至 {{ maskedEmail }}。</p></div>
      </div>
      <el-form ref="contactFormRef" :model="contactForm" :rules="contactRules" label-position="top" @submit.prevent="submitContact">
        <el-form-item label="真实姓名" prop="real_name"><el-input v-model="contactForm.real_name" :prefix-icon="User" maxlength="50" show-word-limit placeholder="请输入真实姓名" /></el-form-item>
        <el-form-item label="新邮箱（选填）" prop="email"><el-input v-model="contactForm.email" :prefix-icon="Message" placeholder="不修改邮箱请留空" /></el-form-item>
        <el-form-item label="新手机号（选填）" prop="phone"><el-input v-model="contactForm.phone" :prefix-icon="Phone" maxlength="11" placeholder="不修改手机号请留空" /></el-form-item>
        <el-form-item label="原邮箱验证码" prop="code">
          <div class="verification-code-row">
            <el-input v-model="contactForm.code" :prefix-icon="Key" maxlength="6" placeholder="请输入 6 位验证码" @keyup.enter="submitContact" />
            <el-button :loading="contactCodeLoading" :disabled="contactCountdown > 0 || !user.email" @click="sendContactCode">
              {{ contactCountdown > 0 ? `${contactCountdown} 秒后重发` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="contactDialogVisible = false">取消</el-button><el-button type="primary" :loading="contactSaving" @click="submitContact">确认修改</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.settings-page { max-width: 1080px; margin: 0 auto; padding: 48px 32px 60px; }.settings-heading { margin-bottom: 28px; }.eyebrow { color: var(--zh-text-theme); font-size: var(--zh-font-size11); font-weight: 700; letter-spacing: .14em; }.settings-heading h1 { margin: 6px 0; font-size: 30px; }.settings-heading p,.card-title p,.danger-zone p { margin: 0; color: var(--zh-text-caption); }.settings-grid { display:grid; grid-template-columns: minmax(260px,.9fr) minmax(360px,1.1fr); gap: 18px; }.settings-card { border-color: var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }.settings-card :deep(.el-card__body) { padding: 26px; }.card-title { display:flex; gap:12px; align-items:flex-start; margin-bottom: 24px; }.card-title>.el-icon { margin-top:3px; color:var(--zh-theme-primary); font-size:22px; }.card-title h2,.danger-zone h2 { margin:0 0 4px; font-size:17px; }.profile-summary { display:flex; align-items:center; gap:14px; padding-bottom:22px; border-bottom:1px solid var(--zh-line-parting); }.profile-summary :deep(.el-avatar) { display:flex; align-items:center; justify-content:center; color:#fff; background:var(--zh-theme-primary); font-size:28px; font-weight:500; line-height:1; }.profile-summary strong,.profile-summary span { display:block; }.profile-summary span { margin-top:4px; color:var(--zh-text-caption); font-size:13px; }dl { margin: 6px 0 0; }dl>div { display:flex; justify-content:space-between; gap:12px; padding:14px 0 0; }dt { color:var(--zh-text-caption); }dd { margin:0; text-align:right; word-break:break-all; }.danger-zone { margin-top:18px; }.danger-zone :deep(.el-card__body) { display:flex; align-items:center; justify-content:space-between; gap:20px; }.password-card :deep(.el-form-item) { margin-bottom:18px; }
.card-title-with-action > div { min-width: 0; flex: 1; }
.card-action { flex: 0 0 auto; margin-left: auto; }
.security-action-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 92px; padding: 20px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-area); }
.security-action-row div { display: grid; gap: 6px; }
.security-action-row strong { color: var(--zh-text-primary); font-size: 15px; }
.security-action-row span { color: var(--zh-text-caption); font-size: 13px; }
.dialog-tip { margin: -4px 0 20px; color: var(--zh-text-caption); font-size: 13px; line-height: 1.6; }
.verification-notice { display: flex; align-items: flex-start; gap: 12px; margin: -4px 0 22px; padding: 14px 16px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius10); color: var(--zh-text-theme); background: var(--zh-background-option-on); }
.verification-notice > .el-icon { flex: 0 0 auto; margin-top: 3px; font-size: 19px; }
.verification-notice strong { color: var(--zh-text-primary); font-size: 14px; }
.verification-notice p { margin: 4px 0 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.55; }
.verification-code-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; width: 100%; }
.verification-code-row .el-button { min-width: 116px; }

/* ===== 个人偏好设置 ===== */
.preferences-card { margin-top: 18px; }
.preferences-body { display: grid; gap: 24px; }

/* 区块容器 */
.pref-section { margin: 0; padding: 0; border: none; min-width: 0; }
.pref-section-title {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px; padding: 0;
  color: var(--zh-text-primary);
  font-size: 15px; font-weight: 600;
  float: none; width: auto;
}
.pref-section-title::before {
  content: '';
  display: inline-block;
  width: 3px; height: 16px;
  border-radius: 2px;
  background: var(--zh-theme-primary);
  flex-shrink: 0;
}
.pref-section-title small {
  color: var(--zh-text-caption);
  font-size: 12px; font-weight: 400;
}

/* 选项网格 */
.pref-option-grid { display: grid; gap: 10px; }
.pref-option-grid--5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.pref-option-grid--4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }

/* 可选中卡片 */
.pref-card {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center; gap: 10px;
  width: 100%; padding: 12px 14px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  color: var(--zh-text-secondary);
  background: var(--zh-background-capsule);
  text-align: left; cursor: pointer;
  font-family: inherit;
  transition: border-color .2s ease, background-color .2s ease, transform .2s ease, box-shadow .2s ease;
}
.pref-card:hover,
.pref-card:focus-visible {
  border-color: var(--zh-line-heavier);
  background: var(--zh-background-option);
  transform: translateY(-1px);
  box-shadow: var(--zh-shadow1);
}
.pref-card.selected {
  border-color: var(--zh-line-theme);
  color: var(--zh-text-primary);
  background: var(--zh-background-option-on);
  box-shadow: 0 0 0 3px var(--zh-line-theme20);
}
.pref-card.selected:hover { border-color: var(--zh-line-theme); background: var(--zh-background-option-on); }

.pref-card-icon {
  display: grid; place-items: center;
  width: 32px; height: 32px;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-theme);
  background: var(--zh-background-area);
  font-size: 16px; flex-shrink: 0;
}
.pref-card-copy { display: grid; gap: 3px; min-width: 0; }
.pref-card-copy strong {
  overflow: hidden; color: inherit;
  font-size: 13px; text-overflow: ellipsis; white-space: nowrap;
}
.pref-card-copy small {
  overflow: hidden; color: var(--zh-text-caption);
  font-size: 11px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap;
}
.pref-card-check { color: var(--zh-text-theme); font-size: 18px; flex-shrink: 0; }

/* 模板卡片 — 缩略图占位 */
.pref-card--template {
  position: relative;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto;
  gap: 8px; padding: 0;
}
.pref-card--template .pref-card-copy { padding: 0 14px 12px; }
.pref-card--template .pref-card-check {
  position: absolute; top: 8px; right: 8px;
}

.pref-thumb {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px;
  width: 100%; height: 100px;
  border-radius: var(--zh-radius8) var(--zh-radius8) 0 0;
  color: var(--zh-text-caption);
  background: var(--zh-background-light);
  font-size: 24px;
}
/* 互动形式 芯片网格 */
.pref-chip-grid {
  display: flex; flex-wrap: wrap; gap: 10px;
}
.pref-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 16px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius20);
  color: var(--zh-text-secondary);
  background: var(--zh-background-capsule);
  font-size: 13px; cursor: pointer;
  font-family: inherit;
  transition: border-color .2s ease, background-color .2s ease, color .2s ease;
}
.pref-chip:hover {
  border-color: var(--zh-line-heavier);
  background: var(--zh-background-option);
}
.pref-chip.on {
  border-color: var(--zh-line-theme);
  color: var(--zh-text-theme);
  background: var(--zh-background-option-on);
  font-weight: 500;
}
.pref-chip .el-icon { font-size: 14px; }
.pref-chip:focus-visible, .pref-card:focus-visible { outline: 2px solid var(--zh-line-theme); outline-offset: 2px; }
.pref-chip:active, .pref-card:active { transform: scale(.98); }

/* 操作区 */
.pref-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding-top: 8px;
}

/* 响应式（断点已按 design.md §9.3 收敛：平板 1023.98 / 手机 767.98） */
@media(max-width:1023.98px){
  .settings-page { padding: 28px 16px; }
  .settings-grid { grid-template-columns: 1fr; }
  .danger-zone :deep(.el-card__body) { align-items: flex-start; flex-direction: column; }
  .pref-option-grid--5{grid-template-columns:repeat(3,minmax(0,1fr))}
  .pref-option-grid--4{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:767.98px){
  .settings-page { max-width: none; padding: 20px 14px calc(100px + env(safe-area-inset-bottom)); }
  .settings-heading { margin-bottom: 20px; }
  .settings-heading h1 { margin: 5px 0 7px; font-size: 26px; letter-spacing: var(--zh-tracking-tight); }
  .settings-heading p { font-size: 13px; line-height: 1.5; }
  .settings-grid { gap: 12px; }
  .settings-card :deep(.el-card__body) { padding: 18px; }
  .card-title { gap: 10px; margin-bottom: 17px; }
  .card-title h2, .danger-zone h2 { font-size: 16px; }
  .card-title p, .danger-zone p { font-size: 12px; line-height: 1.5; }
  .profile-summary { padding-bottom: 17px; }
  .profile-summary :deep(.el-avatar) { width: 52px; height: 52px; font-size: 22px; }
  dl > div { align-items: flex-start; padding-top: 12px; font-size: 13px; }
  dd { max-width: 62%; }
  .card-title-with-action { flex-wrap: wrap; }
  .card-action { width: 100%; min-height: 44px; margin: 4px 0 0; }
  .security-action-row { align-items: stretch; flex-direction: column; gap: 14px; min-height: 0; padding: 15px; }
  .security-action-row .el-button { width: 100%; min-height: 44px; margin: 0; }
  .preferences-card, .danger-zone { margin-top: 12px; }
  .preferences-body { gap: 22px; }
  .pref-option-grid--5 { grid-template-columns: 1fr; gap: 8px; }
  .pref-option-grid--4 { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .pref-card { min-height: 60px; padding: 10px 12px; }
  .pref-card-copy strong { font-size: 13px; }
  .pref-card-copy small { overflow: visible; text-overflow: clip; white-space: normal; }
  .pref-card--template { min-height: 0; padding: 0; }
  .pref-card--template .pref-card-copy { padding: 0 10px 11px; }
  .pref-thumb { height: 68px; font-size: 22px; }
  .pref-chip-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .pref-chip { justify-content: center; min-height: 44px; padding: 8px 10px; }
  .pref-footer { flex-direction: column; align-items: stretch; gap: 4px; padding-top: 2px; }
  .pref-footer .el-button { width: 100%; min-height: 44px; margin: 0; }
  .danger-zone :deep(.el-card__body) { gap: 14px; }
  .danger-zone .el-button { width: 100%; min-height: 44px; margin: 0; }
  .verification-code-row { grid-template-columns: 1fr; }
  .verification-code-row .el-button { width: 100%; min-height: 44px; margin: 0; }
  :global(.account-dialog.el-dialog) { display: flex; flex-direction: column; width: calc(100vw - 20px) !important; max-height: calc(100dvh - 20px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); margin: calc(10px + env(safe-area-inset-top)) auto calc(10px + env(safe-area-inset-bottom)) !important; border-radius: 16px; }
  :global(.account-dialog .el-dialog__header) { flex: none; padding: 17px 16px 12px; }
  :global(.account-dialog .el-dialog__body) { min-height: 0; overflow-y: auto; padding: 12px 16px; overscroll-behavior: contain; }
  :global(.account-dialog .el-dialog__footer) { display: grid; flex: none; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding: 12px 16px calc(14px + env(safe-area-inset-bottom)); border-top: 1px solid var(--zh-line-parting); }
  :global(.account-dialog .el-dialog__footer .el-button) { width: 100%; min-height: 44px; margin: 0; }
  :global(.account-dialog .el-input__inner) { font-size: 16px; }
}

</style>
