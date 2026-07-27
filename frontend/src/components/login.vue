<!--
  [数据交互说明]
  - 导入:
    - `login`, `register`: 来自 `../apis/login.js` 的 API 方法
    - `LOGIN_TEXT`, `VALIDATION_RULES`: 来自 `../config/login.config.js` 的配置常量
    - `User`, `Lock`: ElementPlus Icons 图标组件
  - 输出:
    - 登录成功后将 token 存入 localStorage，跳转至 `/main`
    - 注册成功后将自动切换到登录模式
  - 路由: 由 `/login` 路由匹配，见 `src/router/index.js`
-->
<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login, register } from '../apis/login.js'
import { LOGIN_TEXT, VALIDATION_RULES } from '../config/login.config.js'
import { startPageTransition } from '../utils/pageTransition.js'

const router = useRouter()

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
})

// ========== 表单校验规则 ==========

/** 确认密码校验器 — 检查是否与密码字段一致 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error(LOGIN_TEXT.message.passwordMismatch))
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
  // 清空注册表单
  registerForm.username = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerFormRef.value?.resetFields()
}

// ========== 提交处理 ==========

/**
 * 处理登录提交
 * 校验表单 → 调用登录 API → 存储 token 并跳转
 */
const handleLogin = async (event) => {
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
    // 存储认证信息
    localStorage.setItem('token', res.data.token)
    ElMessage.success(LOGIN_TEXT.message.loginSuccess)
    await startPageTransition({
      sourceEvent: event,
      onCovered: () => router.push('/main'),
    })
  } catch (err) {
    // 根据错误类型给出对应提示
    const status = err?.response?.status
    if (status === 401 || status === 403) {
      ElMessage.error(LOGIN_TEXT.message.loginFailed)
    } else if (status) {
      ElMessage.error(err.response?.data?.message || LOGIN_TEXT.message.loginFailed)
    } else {
      ElMessage.error(LOGIN_TEXT.message.networkError)
    }
    loginForm.password = ''
  } finally {
    loginLoading.value = false
  }
}

/**
 * 处理注册提交
 * 校验表单 → 调用注册 API → 提示成功并切换到登录模式
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
    await register({
      username: registerForm.username,
      password: registerForm.password,
    })
    ElMessage.success(LOGIN_TEXT.message.registerSuccess)
    // 注册成功后切换到登录模式
    toggleMode()
  } catch (err) {
    const status = err?.response?.status
    if (status) {
      ElMessage.error(err.response?.data?.message || LOGIN_TEXT.message.registerFailed)
    } else {
      ElMessage.error(LOGIN_TEXT.message.networkError)
    }
  } finally {
    registerLoading.value = false
  }
}
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
                  @click="handleLogin($event)"
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

          <!-- ===== 注册表单 ===== -->
          <div v-else key="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              label-position="top"
              @keyup.enter="handleRegister"
            >
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

              <!-- 注册按钮 -->
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  round
                  class="w-full !h-[48px] !text-base !font-semibold"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  {{ registerLoading ? LOGIN_TEXT.button.registerLoading : LOGIN_TEXT.button.register }}
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 切换到登录 -->
            <p class="text-center text-sm text-(--zh-text-caption)">
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
</style>
