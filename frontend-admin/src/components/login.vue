<!--
  [数据交互说明]
  - 导入:
    - `login`, `register`, `sendVerificationCode`: 来自 `../apis/login.js` 的 API 方法
    - `LOGIN_TEXT`, `VALIDATION_RULES`: 来自 `../config/login.config.js` 的配置常量
    - `User`, `Lock`, `Message`, `Phone`, `Key`: ElementPlus Icons 图标组件
    - `useUserStore`: 全局用户状态 Pinia store（持久化）
  - 输出:
    - 登录成功后将 token + 用户信息写入 Pinia store（自动持久化至 localStorage），跳转至 `/main`
    - 注册成功后将自动切换到登录模式
  - 路由: 由 `/login` 路由匹配，见 `src/router/index.js`
-->
<script setup>
import { ref, reactive, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Phone, Key } from '@element-plus/icons-vue'
import { login, register, sendVerificationCode } from '../apis/login.js'
import { LOGIN_TEXT, VALIDATION_RULES } from '../config/login.config.js'
import { useUserStore } from '../storage/user.js'

const router = useRouter()
/** 用户状态 store — 登录成功后写入 token 与用户信息 */
const userStore = useUserStore()

// ========== 响应式状态 ==========

/** 当前是否为登录模式（true=登录, false=注册） */
const isLoginMode = ref(true)

/** 登录表单组件引用 */
const loginFormRef = ref(null)
/** 注册表单组件引用 */
const registerFormRef = ref(null)

/** 登录按钮加载态 */
const loginLoading = ref(false)
/** 注册按钮加载态 */
const registerLoading = ref(false)
/** 发送验证码按钮加载态 */
const sendCodeLoading = ref(false)
/** 发送验证码后倒计时秒数（0=可再次发送） */
const sendCodeCooldown = ref(0)
/** 倒计时定时器引用 — 用于组件卸载时清理 */
let cooldownTimer = null

/** 登录表单数据 */
const loginForm = reactive({
  username: '',
  password: '',
  agreeToPrivacy: false,
})

/** 注册表单数据 */
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  phone: '',
  email: '',
  verificationCode: '',
})

/** 当前注册步骤索引（0=基本信息, 1=邮箱验证, 2=设置密码） */
const currentStep = ref(0)
/** 每个步骤对应的表单字段名 — handleNext 只校验当前步字段 */
const stepFields = [
  ['username', 'real_name', 'phone'],
  ['email', 'verificationCode'],
  ['password', 'confirmPassword'],
]

// ========== 表单校验规则 ==========

/** 确认密码校验器 — 检查是否与密码字段一致 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error(LOGIN_TEXT.message.passwordMismatch))
  } else {
    callback()
  }
}

/** 手机号校验器 — 中国手机号正则匹配 */
const validatePhone = (rule, value, callback) => {
  if (!VALIDATION_RULES.phone.pattern.test(value)) {
    callback(new Error(LOGIN_TEXT.message.phoneInvalid))
  } else {
    callback()
  }
}

/** 邮箱格式校验器 */
const validateEmail = (rule, value, callback) => {
  // 基础邮箱正则校验
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailPattern.test(value)) {
    callback(new Error(LOGIN_TEXT.message.emailInvalid))
  } else {
    callback()
  }
}

/** 登录表单校验规则 */
const loginRules = computed(() => ({
  username: [{
    required: VALIDATION_RULES.username.required,
    min: VALIDATION_RULES.username.min,
    message: VALIDATION_RULES.username.message,
    trigger: VALIDATION_RULES.username.trigger,
  }],
  password: [{
    required: VALIDATION_RULES.password.required,
    min: VALIDATION_RULES.password.min,
    message: VALIDATION_RULES.password.message,
    trigger: VALIDATION_RULES.password.trigger,
  }],
  agreeToPrivacy: [{
    validator: (rule, value, callback) => {
      if (!value) {
        callback(new Error(VALIDATION_RULES.privacy.message))
      } else {
        callback()
      }
    },
    trigger: VALIDATION_RULES.privacy.trigger,
  }],
}))

/** 注册表单校验规则 */
const registerRules = computed(() => ({
  username: [{
    required: VALIDATION_RULES.username.required,
    min: VALIDATION_RULES.username.min,
    message: VALIDATION_RULES.username.message,
    trigger: VALIDATION_RULES.username.trigger,
  }],
  real_name: [{
    required: VALIDATION_RULES.realName.required,
    min: VALIDATION_RULES.realName.min,
    message: VALIDATION_RULES.realName.message,
    trigger: VALIDATION_RULES.realName.trigger,
  }],
  phone: [
    {
      required: VALIDATION_RULES.phone.required,
      message: VALIDATION_RULES.phone.message,
      trigger: VALIDATION_RULES.phone.trigger,
    },
    { validator: validatePhone, trigger: ['blur', 'change'] },
  ],
  email: [
    {
      required: VALIDATION_RULES.email.required,
      message: VALIDATION_RULES.email.message,
      trigger: VALIDATION_RULES.email.trigger,
    },
    { validator: validateEmail, trigger: ['blur', 'change'] },
  ],
  verificationCode: [{
    required: VALIDATION_RULES.verificationCode.required,
    len: VALIDATION_RULES.verificationCode.len,
    message: VALIDATION_RULES.verificationCode.message,
    trigger: VALIDATION_RULES.verificationCode.trigger,
  }],
  password: [{
    required: VALIDATION_RULES.password.required,
    min: VALIDATION_RULES.password.min,
    message: VALIDATION_RULES.password.message,
    trigger: VALIDATION_RULES.password.trigger,
  }],
  confirmPassword: [
    {
      required: VALIDATION_RULES.confirmPassword.required,
      min: VALIDATION_RULES.confirmPassword.min,
      message: VALIDATION_RULES.confirmPassword.message,
      trigger: VALIDATION_RULES.confirmPassword.trigger,
    },
    { validator: validateConfirmPassword, trigger: ['blur', 'change'] },
  ],
}))

// ========== 模式切换 ==========

/**
 * 切换登录/注册模式
 * 切换前清空所有表单字段和校验状态
 */
const toggleMode = () => {
  isLoginMode.value = !isLoginMode.value
  // 清空登录表单
  loginForm.username = ''
  loginForm.password = ''
  loginForm.agreeToPrivacy = false
  loginFormRef.value?.resetFields()
  // 清空注册表单（含新增字段）
  registerForm.username = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerForm.real_name = ''
  registerForm.phone = ''
  registerForm.email = ''
  registerForm.verificationCode = ''
  registerFormRef.value?.resetFields()
  // 重置注册步骤
  currentStep.value = 0
  // 重置验证码倒计时
  sendCodeCooldown.value = 0
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}

// ========== 步骤导航 ==========

/**
 * 下一步：仅校验当前步骤字段 → 通过后推进步骤
 */
const handleNext = async () => {
  if (!registerFormRef.value) return
  const fields = stepFields[currentStep.value]
  try {
    // 逐一校验当前步的每个字段
    await registerFormRef.value.validateField(fields)
  } catch {
    return // 校验不通过，停留在当前步骤
  }
  currentStep.value++
}

/**
 * 上一步：无需校验，直接回退
 */
const handlePrev = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

/**
 * 点击步骤指示器跳转到已完成步骤
 * @param {number} n - 目标步骤索引
 */
const goToStep = (n) => {
  // 仅允许跳转到已完成步骤（< currentStep）
  if (n < currentStep.value) {
    currentStep.value = n
  }
}

// ========== 提交处理 ==========

/**
 * 发送邮箱验证码
 * 先单独校验邮箱字段 → 调用 API-02 → 成功后启动 60 秒倒计时
 * 注意：request.js 响应拦截器已返回 response.data（{ code, data, message }），
 * 业务错误也会 resolve，需自行判断 res.code；只有网络/HTTP 错误才会进 catch
 */
const handleSendCode = async () => {
  // 单独校验邮箱字段
  if (!registerFormRef.value) return
  try {
    await registerFormRef.value.validateField('email')
  } catch {
    return // 邮箱格式校验不通过
  }

  sendCodeLoading.value = true
  try {
    const res = await sendVerificationCode({
      username: registerForm.email,
      scene: 'register',
      channel: 'email',
    })
    // 检查业务状态码（200 或 0 视为成功）
    if (res.code !== 200 && res.code !== 0) {
      ElMessage.error(res.message || LOGIN_TEXT.message.sendCodeFailed)
      return
    }
    ElMessage.success(LOGIN_TEXT.message.sendCodeSuccess)
    // 启动 60 秒倒计时
    sendCodeCooldown.value = 60
    cooldownTimer = setInterval(() => {
      sendCodeCooldown.value--
      if (sendCodeCooldown.value <= 0) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  } catch {
    // HTTP/网络错误已被 request.js 拦截器记录日志，此处仅做用户提示
    ElMessage.error(LOGIN_TEXT.message.networkError)
  } finally {
    sendCodeLoading.value = false
  }
}

/**
 * 处理登录提交
 * 校验表单 → 调用登录 API → 将 LoginVO 完整存入 Pinia store 并跳转
 * 注意：request.js 响应拦截器已返回 response.data（{ code, data, message }），
 * 业务错误也会 resolve，需自行判断 res.code；只有网络/HTTP 错误才会进 catch
 */
const handleLogin = async () => {
  // 表单校验
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
  } catch {
    return // 校验不通过，终止提交
  }

  loginLoading.value = true
  try {
    const res = await login({
      username: loginForm.username,
      password: loginForm.password,
    })

    // res 为 { code, data, message }，其中 data 是 LoginVO
    // 检查业务状态码（200 或 0 视为成功）
    if (res.code !== 200 && res.code !== 0) {
      ElMessage.error(res.message || LOGIN_TEXT.message.loginFailed)
      loginForm.password = ''
      return
    }
    // 将登录返回的 LoginVO 完整写入 Pinia store（自动持久化到 localStorage）
    const loginVO = res.data
    userStore.setToken(loginVO.token)
    userStore.setUserInfo(loginVO)
    ElMessage.success(LOGIN_TEXT.message.loginSuccess)
    // 短暂延迟后跳转，让用户看到成功提示
    setTimeout(() => {
      router.push('/main')
    }, 200)
  } catch {
    // HTTP/网络错误已被 request.js 拦截器记录日志，此处仅做用户提示
    ElMessage.error(LOGIN_TEXT.message.networkError)
    loginForm.password = ''
  } finally {
    loginLoading.value = false
  }
}

/**
 * 处理注册提交
 * 校验表单 → 调用注册 API（含验证码）→ 提示成功并切换到登录模式
 * 注意：request.js 响应拦截器已返回 response.data（{ code, data, message }），
 * 业务错误也会 resolve，需自行判断 res.code；只有网络/HTTP 错误才会进 catch
 */
const handleRegister = async () => {
  // 表单校验
  if (!registerFormRef.value) return
  try {
    await registerFormRef.value.validate()
  } catch {
    return // 校验不通过，终止提交
  }

  registerLoading.value = true
  try {
    const res = await register({
      username: registerForm.username,
      password: registerForm.password,
      real_name: registerForm.real_name,
      phone: registerForm.phone,
      email: registerForm.email,
      code: registerForm.verificationCode,
    })
    // 检查业务状态码（200 或 0 视为成功）
    if (res.code !== 200 && res.code !== 0) {
      ElMessage.error(res.message || LOGIN_TEXT.message.registerFailed)
      return
    }
    ElMessage.success(LOGIN_TEXT.message.registerSuccess)
    // 注册成功后切换到登录模式
    toggleMode()
  } catch {
    // HTTP/网络错误已被 request.js 拦截器记录日志，此处仅做用户提示
    ElMessage.error(LOGIN_TEXT.message.networkError)
  } finally {
    registerLoading.value = false
  }
}

// ========== 生命周期 ==========

/** 组件卸载前清理倒计时定时器，防止内存泄漏 */
onBeforeUnmount(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
})
</script>

<template>
  <!-- 全屏容器：左右分栏 -->
  <div class="flex h-screen overflow-hidden bg-(--zh-background-primary)">

    <!-- ========== 左侧：品牌展示区 (lg:w-5/12) ========== -->
    <aside class="hidden lg:flex lg:w-5/12 relative overflow-hidden">
      <!--
        [此处需填写：AI生成的品牌插图]
        提示词: A futuristic digital classroom scene with a glowing holographic brain at the center
        radiating streams of golden-blue light, connecting to floating books, mathematical formulas,
        molecular structures, and abstract geometric shapes. Background transitions from deep navy
        blue (#1D4ED8) to lighter blue (#60A5FA). Modern minimalist illustration style.
        建议尺寸: 1920×1280px, WebP 或 SVG 格式
      -->
      <img
        class="absolute inset-0 w-full h-full object-cover"
        src="/image_384866672794550.png"
        alt="智核品牌插图"
      />
      <!-- 底部渐变遮罩，确保文字可读性 -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/40 via-black/10 to-transparent"></div>
      <!-- 品牌文字叠加层 -->
      <div class="relative z-10 flex flex-col justify-end h-full p-12">
        <!-- 品牌名 -->
        <h1 class="text-white text-[32px] font-bold mb-3 tracking-wide">
          {{ LOGIN_TEXT.brand.name }}
        </h1>
        <!-- 主标语 -->
        <p class="text-white text-[30px] font-semibold leading-relaxed whitespace-pre-line">
          {{ LOGIN_TEXT.brand.slogan }}
        </p>
        <!-- 副标语 -->
        <p class="text-white/70 text-base mt-4">
          {{ LOGIN_TEXT.brand.subtitle }}
        </p>
      </div>
    </aside>

    <!-- ========== 右侧：登录/注册表单区 (lg:w-7/12) ========== -->
    <main class="flex-1 flex items-center justify-center px-6 sm:px-10 lg:px-16">
      <div class="w-full max-w-[440px]">

        <!-- 移动端可见的品牌 Logo + 名称 -->
        <div class="flex flex-col items-center mb-10 lg:hidden">
          <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-[#2563EB] to-[#60A5FA] flex items-center justify-center mb-3 shadow-lg">
            <span class="text-white font-bold text-xl">智</span>
          </div>
          <span class="text-lg font-semibold text-(--zh-text-primary)">
            {{ LOGIN_TEXT.brand.name }}
          </span>
        </div>

        <!-- 表单标题区域 -->
        <div class="mb-8">
          <h2 class="text-2xl font-bold text-(--zh-text-primary) mb-2">
            {{ isLoginMode ? LOGIN_TEXT.form.loginTitle : LOGIN_TEXT.form.registerTitle }}
          </h2>
          <p class="text-sm text-(--zh-text-secondary)">
            {{ isLoginMode ? LOGIN_TEXT.form.loginSubtitle : LOGIN_TEXT.form.registerSubtitle }}
          </p>
        </div>

        <!-- 表单区域：带切换动画 -->
        <Transition name="form" mode="out-in">

          <!-- ===== 登录表单 ===== -->
          <div v-if="isLoginMode" key="login">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              label-position="top"
              @submit.prevent
              @keyup.enter="handleLogin"
            >
              <!-- 用户名 -->
              <el-form-item :label="LOGIN_TEXT.label.username" prop="username">
                <el-input
                  v-model="loginForm.username"
                  :placeholder="LOGIN_TEXT.placeholder.username"
                  :prefix-icon="User"
                  size="large"
                  clearable
                />
              </el-form-item>

              <!-- 密码 -->
              <el-form-item :label="LOGIN_TEXT.label.password" prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  :placeholder="LOGIN_TEXT.placeholder.password"
                  :prefix-icon="Lock"
                  size="large"
                  show-password
                />
              </el-form-item>

              <!-- 隐私协议勾选 -->
              <el-form-item prop="agreeToPrivacy">
                <el-checkbox v-model="loginForm.agreeToPrivacy">
                  <span class="text-xs text-(--zh-text-caption)">
                    {{ LOGIN_TEXT.privacy.prefix }}
                    <a href="#" class="text-(--zh-text-link) hover:underline">
                      {{ LOGIN_TEXT.privacy.serviceAgreement }}
                    </a>
                    {{ LOGIN_TEXT.privacy.and }}
                    <a href="#" class="text-(--zh-text-link) hover:underline">
                      {{ LOGIN_TEXT.privacy.privacyPolicy }}
                    </a>
                  </span>
                </el-checkbox>
              </el-form-item>

              <!-- 登录按钮 -->
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  round
                  class="w-full !h-[48px] !text-base !font-semibold"
                  :loading="loginLoading"
                  @click="handleLogin"
                >
                  {{ loginLoading ? LOGIN_TEXT.button.loginLoading : LOGIN_TEXT.button.login }}
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 切换到注册 -->
            <p class="text-center text-sm text-(--zh-text-caption)">
              <a
                href="javascript:void(0)"
                class="text-(--zh-text-link) hover:underline cursor-pointer"
                @click="toggleMode"
              >
                {{ LOGIN_TEXT.switch.toRegister }}
              </a>
            </p>
          </div>

          <!-- ===== 注册表单（分步） ===== -->
          <div v-else key="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              label-position="top"
              @submit.prevent
              @keyup.enter="currentStep < 2 ? handleNext() : handleRegister()"
            >
              <!-- 步骤指示器 — 已完成步骤可点击回退 -->
              <el-steps :active="currentStep" align-center class="mb-8">
                <el-step
                  v-for="(title, i) in LOGIN_TEXT.steps.titles"
                  :key="i"
                  :title="title"
                  :class="{ 'cursor-pointer': i < currentStep }"
                  @click="goToStep(i)"
                />
              </el-steps>

              <!-- ===== 第 1 步：基本信息 ===== -->
              <Transition name="step" mode="out-in">
                <div v-if="currentStep === 0" key="step1">
                  <!-- 用户名 -->
                  <el-form-item :label="LOGIN_TEXT.label.username" prop="username">
                    <el-input
                      v-model="registerForm.username"
                      :placeholder="LOGIN_TEXT.placeholder.username"
                      :prefix-icon="User"
                      size="large"
                      clearable
                    />
                  </el-form-item>

                  <!-- 真实姓名 -->
                  <el-form-item :label="LOGIN_TEXT.label.realName" prop="real_name">
                    <el-input
                      v-model="registerForm.real_name"
                      :placeholder="LOGIN_TEXT.placeholder.realName"
                      :prefix-icon="User"
                      size="large"
                      clearable
                    />
                  </el-form-item>

                  <!-- 手机号 -->
                  <el-form-item :label="LOGIN_TEXT.label.phone" prop="phone">
                    <el-input
                      v-model="registerForm.phone"
                      :placeholder="LOGIN_TEXT.placeholder.phone"
                      :prefix-icon="Phone"
                      size="large"
                      clearable
                    />
                  </el-form-item>
                </div>

                <!-- ===== 第 2 步：邮箱验证 ===== -->
                <div v-else-if="currentStep === 1" key="step2">
                  <!-- 邮箱 + 发送验证码按钮（同一行） -->
                  <el-form-item :label="LOGIN_TEXT.label.email" prop="email">
                    <div class="flex gap-2">
                      <el-input
                        v-model="registerForm.email"
                        :placeholder="LOGIN_TEXT.placeholder.email"
                        :prefix-icon="Message"
                        size="large"
                        clearable
                        class="flex-1"
                      />
                      <el-button
                        size="large"
                        class="min-w-[128px] send-code-btn"
                        :disabled="sendCodeCooldown > 0"
                        :loading="sendCodeLoading"
                        @click="handleSendCode"
                      >
                        {{
                          sendCodeLoading
                            ? LOGIN_TEXT.button.sendingCode
                            : sendCodeCooldown > 0
                              ? LOGIN_TEXT.button.codeSent.replace('{n}', sendCodeCooldown)
                              : LOGIN_TEXT.button.sendCode
                        }}
                      </el-button>
                    </div>
                  </el-form-item>

                  <!-- 验证码 — 紧接邮箱下方 -->
                  <el-form-item :label="LOGIN_TEXT.label.verificationCode" prop="verificationCode">
                    <el-input
                      v-model="registerForm.verificationCode"
                      :placeholder="LOGIN_TEXT.placeholder.verificationCode"
                      :prefix-icon="Key"
                      size="large"
                      clearable
                      maxlength="6"
                    />
                  </el-form-item>
                </div>

                <!-- ===== 第 3 步：设置密码 ===== -->
                <div v-else key="step3">
                  <!-- 密码 -->
                  <el-form-item :label="LOGIN_TEXT.label.password" prop="password">
                    <el-input
                      v-model="registerForm.password"
                      type="password"
                      :placeholder="LOGIN_TEXT.placeholder.registerPassword"
                      :prefix-icon="Lock"
                      size="large"
                      show-password
                    />
                  </el-form-item>

                  <!-- 确认密码 -->
                  <el-form-item :label="LOGIN_TEXT.label.confirmPassword" prop="confirmPassword">
                    <el-input
                      v-model="registerForm.confirmPassword"
                      type="password"
                      :placeholder="LOGIN_TEXT.placeholder.confirmPassword"
                      :prefix-icon="Lock"
                      size="large"
                      show-password
                    />
                  </el-form-item>
                </div>
              </Transition>

              <!-- 步骤导航按钮 -->
              <div class="flex justify-between mt-4">
                <el-button
                  v-if="currentStep > 0"
                  size="large"
                  round
                  class="w-[120px]"
                  @click="handlePrev"
                >
                  {{ LOGIN_TEXT.steps.prev }}
                </el-button>
                <span v-else></span>

                <el-button
                  v-if="currentStep < 2"
                  type="primary"
                  size="large"
                  round
                  class="w-[120px]"
                  @click="handleNext"
                >
                  {{ LOGIN_TEXT.steps.next }}
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  size="large"
                  round
                  class="w-[120px]"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  {{ registerLoading ? LOGIN_TEXT.button.registerLoading : LOGIN_TEXT.button.register }}
                </el-button>
              </div>
            </el-form>

            <!-- 切换到登录 -->
            <p class="text-center text-sm text-(--zh-text-caption) mt-4">
              <a
                href="javascript:void(0)"
                class="text-(--zh-text-link) hover:underline cursor-pointer"
                @click="toggleMode"
              >
                {{ LOGIN_TEXT.switch.toLogin }}
              </a>
            </p>
          </div>

        </Transition>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ===== 表单切换动画 ===== */

/** 新内容从右侧滑入 */
.form-enter-active {
  animation: slideInFromRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/** 旧内容向左侧滑出 */
.form-leave-active {
  animation: slideOutToLeft 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideInFromRight {
  from {
    transform: translateX(30px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOutToLeft {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(-30px);
    opacity: 0;
  }
}

/* ===== 步骤切换动画 ===== */

/** 步骤前进：新内容从右侧滑入 */
.step-enter-active {
  animation: stepSlideIn 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/** 步骤回退：旧内容向右侧滑出后，新内容从左侧滑入 */
.step-leave-active {
  animation: stepSlideOut 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes stepSlideIn {
  from {
    transform: translateX(40px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes stepSlideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(-40px);
    opacity: 0;
  }
}

/* ===== ElementPlus 组件微调 ===== */

/** 调整 el-form-item 之间的间距，使其更紧凑 */
:deep(.el-form-item) {
  margin-bottom: 20px;
}

/** 表单项标签加粗 */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--zh-text-primary);
}

/** 大号输入框高度微调 */
:deep(.el-input--large .el-input__wrapper) {
  padding: 12px 16px;
}

/** 发送验证码按钮：取消 ElementPlus 固定高度，与同行输入框自然对齐 */
:deep(.send-code-btn) {
  height: auto;
}
</style>
