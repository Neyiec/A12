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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Lock, User, CircleCheck, Setting,
  MagicStick, Document, Share, FolderOpened, Refresh,
  Grid, Collection, Star, Monitor,
  ChatDotRound, EditPen, Promotion, Message, Microphone,
} from '@element-plus/icons-vue'
import { changePassword, getCurrentUser, logout } from '../apis/login.js'
import { getTeacherPreferences, saveTeacherPreferences } from '../apis/teacher.js'
import { useUserStore } from '../storage/user.js'
import { TEACHING_STYLES, TEMPLATES, INTERACTION_FORMS, PREFERENCES_DEFAULTS } from '../config/preferences.config.js'

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
  refreshUser().catch(() => {})
  loadPreferences()
})
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
              :class="{ selected: preferences.templateStyle === tpl.value }"
              @click="preferences.templateStyle = tpl.value"
            >
              <span class="pref-thumb">
                <el-icon><component :is="iconMap[tpl.icon]" /></el-icon>
                <span class="pref-thumb-tag">[模板缩略图]</span>
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
  </section>
</template>

<style scoped>
.settings-page { max-width: 1080px; margin: 0 auto; padding: 48px 32px 60px; }.settings-heading { margin-bottom: 28px; }.eyebrow { color: var(--zh-text-theme); font-size: var(--zh-font-size11); font-weight: 700; letter-spacing: .14em; }.settings-heading h1 { margin: 6px 0; font-size: 30px; }.settings-heading p,.card-title p,.danger-zone p { margin: 0; color: var(--zh-text-caption); }.settings-grid { display:grid; grid-template-columns: minmax(260px,.9fr) minmax(360px,1.1fr); gap: 18px; }.settings-card { border-color: var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }.settings-card :deep(.el-card__body) { padding: 26px; }.card-title { display:flex; gap:12px; align-items:flex-start; margin-bottom: 24px; }.card-title>.el-icon { margin-top:3px; color:var(--zh-theme-primary); font-size:22px; }.card-title h2,.danger-zone h2 { margin:0 0 4px; font-size:17px; }.profile-summary { display:flex; align-items:center; gap:14px; padding-bottom:22px; border-bottom:1px solid var(--zh-line-parting); }.profile-summary :deep(.el-avatar) { display:flex; align-items:center; justify-content:center; color:#fff; background:var(--zh-theme-primary); font-size:28px; font-weight:500; line-height:1; }.profile-summary strong,.profile-summary span { display:block; }.profile-summary span { margin-top:4px; color:var(--zh-text-caption); font-size:13px; }dl { margin: 6px 0 0; }dl>div { display:flex; justify-content:space-between; gap:12px; padding:14px 0 0; }dt { color:var(--zh-text-caption); }dd { margin:0; text-align:right; word-break:break-all; }.danger-zone { margin-top:18px; }.danger-zone :deep(.el-card__body) { display:flex; align-items:center; justify-content:space-between; gap:20px; }.password-card :deep(.el-form-item) { margin-bottom:18px; }

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
.pref-thumb-tag {
  font-size: 11px; color: var(--zh-text-disabled);
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

/* 操作区 */
.pref-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding-top: 8px;
}

/* 响应式 */
@media(max-width:860px){
  .pref-option-grid--5{grid-template-columns:repeat(3,minmax(0,1fr))}
  .pref-option-grid--4{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:580px){
  .pref-option-grid--5{grid-template-columns:repeat(2,minmax(0,1fr))}
  .pref-option-grid--4{grid-template-columns:1fr}
  .pref-card{padding:10px 12px}
}

@media(max-width:760px){.settings-page{padding:28px 16px}.settings-grid{grid-template-columns:1fr}.danger-zone :deep(.el-card__body){align-items:flex-start;flex-direction:column}}
</style>
