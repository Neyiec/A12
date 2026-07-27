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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login, register, sendRegisterVerificationCode } from '../apis/login.js'
import { LOGIN_TEXT, VALIDATION_RULES } from '../config/login.config.js'
import { startPageTransition } from '../utils/pageTransition.js'

const router = useRouter()
const route = useRoute()

/** 本地界面预览开关：仅 Vite 开发环境且 URL 带 ?preview=1 时有效。 */
const isDevelopmentPreview = computed(() => (
  import.meta.env.DEV && route.query.preview === '1'
))

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
const verificationCodeLoading = ref(false)
/** 验证码重发倒计时（秒） */
const verificationCodeCountdown = ref(0)
let verificationCodeTimer = null
const backgroundCanvas = ref(null)
let backgroundAnimation = null
let removeCanvasResizeListener = null
let removeCanvasPointerListeners = null

/** 登录表单数据 */
const loginForm = reactive({
  username: '',
  password: '',
  agreeToPrivacy: false,
})

/** 注册表单数据 */
const registerForm = reactive({
  username: '',
  email: '',
  code: '',
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
  email: [{
    required: VALIDATION_RULES.email.required,
    type: VALIDATION_RULES.email.type,
    message: VALIDATION_RULES.email.message,
    trigger: VALIDATION_RULES.email.trigger,
  }],
  code: [{
    required: VALIDATION_RULES.verificationCode.required,
    pattern: VALIDATION_RULES.verificationCode.pattern,
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
  // 清空注册表单
  registerForm.username = ''
  registerForm.email = ''
  registerForm.code = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerFormRef.value?.resetFields()

  if (verificationCodeTimer) {
    window.clearInterval(verificationCodeTimer)
    verificationCodeTimer = null
  }
  verificationCodeCountdown.value = 0
}

/** 发送注册邮箱验证码，并启动与服务端一致的 60 秒重发倒计时。 */
const handleSendVerificationCode = async () => {
  if (!registerFormRef.value || verificationCodeCountdown.value > 0) return

  try {
    await registerFormRef.value.validateField('email')
  } catch {
    return
  }

  verificationCodeLoading.value = true
  try {
    const res = await sendRegisterVerificationCode(registerForm.email)
    if (res?.code !== 200) {
      ElMessage.error(res?.message || LOGIN_TEXT.message.verificationCodeFailed)
      return
    }

    ElMessage.success(LOGIN_TEXT.message.verificationCodeSent)
    verificationCodeCountdown.value = 60
    verificationCodeTimer = window.setInterval(() => {
      verificationCodeCountdown.value -= 1
      if (verificationCodeCountdown.value <= 0) {
        window.clearInterval(verificationCodeTimer)
        verificationCodeTimer = null
      }
    }, 1000)
  } catch {
    ElMessage.error(LOGIN_TEXT.message.networkError)
  } finally {
    verificationCodeLoading.value = false
  }
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
    // 本地预览无需启动后端，仍复用真实的页面转场和主界面路由。
    if (isDevelopmentPreview.value) {
      ElMessage.success(LOGIN_TEXT.message.loginSuccess)
      await startPageTransition({
        sourceEvent: event,
        onCovered: () => router.push({ path: '/main', query: { preview: '1' } }),
      })
      return
    }

    const res = await login({
      username: loginForm.username,
      password: loginForm.password,
    })

    // 后端使用 Result<LoginVO> 包装响应：认证失败时仍会返回 HTTP 200，
    // 因此前端必须先判断业务状态，不能直接读取 token。
    if (res?.code !== 200 || !res?.data?.token) {
      ElMessage.error(res?.message || LOGIN_TEXT.message.loginFailed)
      loginForm.password = ''
      return
    }

    // /main 是教师端入口，统一登录接口返回的管理员/审核员账号不可进入此处。
    if (res.data.user_type !== 'teacher') {
      ElMessage.error('当前账号没有教师端访问权限')
      loginForm.password = ''
      return
    }

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
    const res = await register({
      username: registerForm.username,
      password: registerForm.password,
      email: registerForm.email,
      code: registerForm.code,
    })
    if (res?.code !== 200) {
      ElMessage.error(res?.message || LOGIN_TEXT.message.registerFailed)
      return
    }
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

/** 低对比字符场：以缓慢呼吸和鼠标涟漪回应用户，不依赖第三方动画素材。 */
const startFluidBackground = () => {
  const canvas = backgroundCanvas.value
  const context = canvas?.getContext('2d')
  if (!canvas || !context) return

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const pointer = {
    x: window.innerWidth * .72,
    y: window.innerHeight * .5,
    targetX: window.innerWidth * .72,
    targetY: window.innerHeight * .5,
    velocity: 0,
    active: false,
  }
  const glyphs = '·:｡･+×○01'
  let viewportWidth = window.innerWidth
  let viewportHeight = window.innerHeight
  let previousPointerX = pointer.x
  let previousPointerY = pointer.y

  const glyphAt = (column, row, phase) => {
    // 变化沿斜向波带传播，避免整屏字符在同一帧机械切换。
    const cycle = Math.floor(phase * 1.3 + row * .14 - column * .07)
    return glyphs[(column * 7 + row * 11 + cycle) % glyphs.length]
  }

  const resize = () => {
    const scale = Math.min(window.devicePixelRatio || 1, 2)
    viewportWidth = window.innerWidth
    viewportHeight = window.innerHeight
    canvas.width = viewportWidth * scale
    canvas.height = viewportHeight * scale
    canvas.style.width = `${viewportWidth}px`
    canvas.style.height = `${viewportHeight}px`
    context.setTransform(scale, 0, 0, scale, 0, 0)
  }

  const paint = (time = 0) => {
    const width = viewportWidth
    const height = viewportHeight
    const phase = time / 1000
    context.clearRect(0, 0, width, height)

    pointer.x += (pointer.targetX - pointer.x) * .12
    pointer.y += (pointer.targetY - pointer.y) * .12
    pointer.velocity *= .9

    const ambientX = pointer.active
      ? pointer.x
      : width * (.72 + Math.sin(phase * .24) * .09)
    const ambientY = pointer.active
      ? pointer.y
      : height * (.5 + Math.cos(phase * .19) * .12)
    const ambient = context.createRadialGradient(
      ambientX,
      ambientY,
      0,
      ambientX,
      ambientY,
      Math.max(width, height) * .38,
    )
    ambient.addColorStop(0, `rgba(96, 165, 250, ${pointer.active ? .045 : .085})`)
    ambient.addColorStop(.52, 'rgba(37, 99, 235, .02)')
    ambient.addColorStop(1, 'rgba(247, 248, 252, 0)')
    context.fillStyle = ambient
    context.fillRect(0, 0, width, height)

    const cellWidth = width < 640 ? 22 : 20
    const cellHeight = width < 640 ? 25 : 23
    const interactionRadius = Math.min(150, Math.max(105, width * .11))
    const wake = Math.min(pointer.velocity / 26, 1)
    context.font = `${width < 640 ? 11 : 12}px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
    context.textBaseline = 'middle'
    context.textAlign = 'center'

    for (let row = 0, y = cellHeight / 2; y < height + cellHeight; row += 1, y += cellHeight) {
      for (let column = 0, x = cellWidth / 2; x < width + cellWidth; column += 1, x += cellWidth) {
        const dx = x - pointer.x
        const dy = y - pointer.y
        const distance = Math.sqrt(dx * dx + dy * dy) || 1
        const proximity = pointer.active
          ? Math.max(0, 1 - distance / interactionRadius)
          : 0
        const easedProximity = proximity * proximity * (3 - 2 * proximity)
        const directionX = dx / distance
        const directionY = dy / distance
        const idleWave = prefersReducedMotion
          ? 0
          : (Math.sin(phase * 1.28 - row * .2 + column * .09) + 1) / 2
        const crossWave = prefersReducedMotion
          ? 0
          : Math.sin(phase * .9 + row * .11 + column * .17)
        const signalBand = prefersReducedMotion
          ? 0
          : Math.max(0, Math.sin(phase * 1.02 - row * .15 + column * .045) - .68) / .32
        const shimmerSeed = (column * 13 + row * 17) % 37
        const shimmer = prefersReducedMotion
          ? 0
          : Math.max(0, Math.sin(phase * 1.34 + shimmerSeed) - .88) / .12
        const wave = prefersReducedMotion
          ? 0
          : Math.sin(distance * .052 - phase * 3.1) * easedProximity
        const displacement = easedProximity * (4 + wake * 5) + wave * 1.2
        const offsetX = directionX * displacement + crossWave * .65
        const offsetY = directionY * displacement + (idleWave - .5) * 3.4
        const baseAlpha = .08 + idleWave * .1 + signalBand * .13 + shimmer * .09
        const blueMix = easedProximity * (.07 + wake * .03)
          + signalBand * .14
        const finalAlpha = Math.min(baseAlpha + blueMix, .58)

        context.fillStyle = blueMix > .06
          ? `rgba(37, 99, 235, ${finalAlpha})`
          : `rgba(102, 102, 102, ${baseAlpha})`
        context.fillText(glyphAt(column, row, phase), x + offsetX, y + offsetY)
      }
    }

    if (!prefersReducedMotion) backgroundAnimation = window.requestAnimationFrame(paint)
  }

  resize()
  paint()
  window.addEventListener('resize', resize)
  const updatePointer = (event) => {
    const deltaX = event.clientX - previousPointerX
    const deltaY = event.clientY - previousPointerY
    pointer.targetX = event.clientX
    pointer.targetY = event.clientY
    pointer.velocity = Math.max(pointer.velocity, Math.sqrt(deltaX * deltaX + deltaY * deltaY))
    pointer.active = true
    previousPointerX = event.clientX
    previousPointerY = event.clientY
  }
  const clearPointer = () => {
    pointer.active = false
  }
  window.addEventListener('pointermove', updatePointer, { passive: true })
  document.documentElement.addEventListener('pointerleave', clearPointer)
  window.addEventListener('blur', clearPointer)
  removeCanvasResizeListener = () => window.removeEventListener('resize', resize)
  removeCanvasPointerListeners = () => {
    window.removeEventListener('pointermove', updatePointer)
    document.documentElement.removeEventListener('pointerleave', clearPointer)
    window.removeEventListener('blur', clearPointer)
  }
}

onMounted(startFluidBackground)

onUnmounted(() => {
  if (verificationCodeTimer) {
    window.clearInterval(verificationCodeTimer)
  }
  if (backgroundAnimation) window.cancelAnimationFrame(backgroundAnimation)
  removeCanvasResizeListener?.()
  removeCanvasPointerListeners?.()
})
</script>

<template>
  <!-- 全屏容器：左右分栏 -->
  <div class="login-shell flex min-h-[100dvh] overflow-hidden bg-(--zh-background-primary)">
    <!-- 参考 Essential 的克制字符场：Canvas 负责缓慢呼吸和鼠标涟漪。 -->
    <div class="login-tech-background" aria-hidden="true">
      <canvas ref="backgroundCanvas" class="login-fluid-canvas"></canvas>
      <div class="login-background-wash"></div>
      <span class="login-calibration-mark login-calibration-mark--top"></span>
      <span class="login-calibration-mark login-calibration-mark--bottom"></span>
    </div>

    <!-- ========== 左侧：品牌展示区 (lg:w-5/12) ========== -->
    <aside class="login-brand-panel hidden lg:flex lg:w-5/12 relative overflow-hidden">
      <!--
        [此处需填写：AI生成的品牌插图]
        提示词: A futuristic digital classroom scene with a glowing holographic brain at the center
        radiating streams of golden-blue light, connecting to floating books, mathematical formulas,
        molecular structures, and abstract geometric shapes. Background transitions from deep navy
        blue (#1D4ED8) to lighter blue (#60A5FA). Modern minimalist illustration style.
        建议尺寸: 1920×1280px, WebP 或 SVG 格式
      -->
      <img
        class="login-brand-image absolute inset-0 w-full h-full object-cover"
        src="/image_384866672794550.png"
        alt="智核品牌插图"
      />
      <!-- 底部渐变遮罩，确保文字可读性 -->
      <div class="login-brand-scrim absolute inset-0"></div>
      <!-- 品牌文字叠加层 -->
      <div class="login-brand-copy relative z-10 flex flex-col justify-end h-full p-12">
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
    <main class="login-main relative z-10 flex-1 flex items-center justify-center px-6 py-10 sm:px-10 lg:px-16">
      <div class="login-form-panel w-full max-w-[440px]">

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

              <!-- 注册邮箱及验证码 -->
              <el-form-item :label="LOGIN_TEXT.label.email" prop="email">
                <div class="flex w-full gap-3">
                  <el-input
                    v-model="registerForm.email"
                    type="email"
                    :placeholder="LOGIN_TEXT.placeholder.email"
                    size="large"
                    clearable
                  />
                  <el-button
                    size="large"
                    :loading="verificationCodeLoading"
                    :disabled="verificationCodeCountdown > 0"
                    @click="handleSendVerificationCode"
                  >
                    {{ verificationCodeCountdown > 0
                      ? `${verificationCodeCountdown}${LOGIN_TEXT.button.resendVerificationCode}`
                      : LOGIN_TEXT.button.sendVerificationCode }}
                  </el-button>
                </div>
              </el-form-item>

              <el-form-item :label="LOGIN_TEXT.label.verificationCode" prop="code">
                <el-input
                  v-model="registerForm.code"
                  inputmode="numeric"
                  maxlength="6"
                  :placeholder="LOGIN_TEXT.placeholder.verificationCode"
                  size="large"
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
.login-shell {
  position: relative;
  isolation: isolate;
  background: var(--zh-background-light);
}

.login-tech-background {
  position: absolute;
  z-index: -1;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.login-fluid-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.login-background-wash {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, transparent 0 42%, rgb(247 248 252 / 12%) 48%, rgb(247 248 252 / 70%) 100%),
    radial-gradient(circle at 74% 48%, transparent 0 28%, rgb(247 248 252 / 22%) 66%, rgb(247 248 252 / 58%) 100%);
}

.login-calibration-mark {
  position: absolute;
  right: 32px;
  width: 16px;
  height: 16px;
  opacity: .46;
}

.login-calibration-mark::before,
.login-calibration-mark::after {
  position: absolute;
  content: '';
  background: var(--zh-line-theme50);
}

.login-calibration-mark::before {
  top: 50%;
  left: 0;
  width: 100%;
  height: 1px;
}

.login-calibration-mark::after {
  top: 0;
  left: 50%;
  width: 1px;
  height: 100%;
}

.login-calibration-mark--top { top: 32px; }
.login-calibration-mark--bottom { bottom: 32px; }

.login-brand-panel { border-right: 1px solid rgb(255 255 255 / 16%); }

.login-brand-panel::after {
  position: absolute;
  z-index: 1;
  inset: 0;
  content: '';
  pointer-events: none;
  opacity: .32;
  background-image:
    radial-gradient(circle, rgb(191 219 254 / 42%) 1px, transparent 1.5px);
  background-size: 20px 23px;
  mask-image: linear-gradient(135deg, black, transparent 82%);
}

.login-brand-image {
  filter: saturate(.82) contrast(1.04);
  transform: scale(1.02);
}

.login-brand-scrim {
  background:
    linear-gradient(90deg, rgb(8 27 67 / 52%), rgb(8 27 67 / 7%)),
    linear-gradient(0deg, rgb(7 20 50 / 78%), rgb(7 20 50 / 5%) 60%, rgb(7 20 50 / 20%));
}

.login-brand-copy { text-shadow: 0 2px 20px rgb(5 17 45 / 38%); }

.login-form-panel {
  padding: 36px;
  border: 1px solid rgb(37 99 235 / 12%);
  border-radius: var(--zh-radius16);
  background: rgb(255 255 255 / 76%);
  box-shadow: 0 24px 70px -36px rgb(30 64 175 / 30%), 0 1px 0 rgb(255 255 255 / 88%) inset;
  backdrop-filter: blur(20px) saturate(1.1);
  -webkit-backdrop-filter: blur(20px) saturate(1.1);
}

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
  border: 1px solid var(--zh-line-border);
  background: rgb(255 255 255 / 78%);
  box-shadow: none;
  transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
}

:deep(.el-input--large .el-input__wrapper.is-focus) {
  border-color: var(--zh-line-theme);
  background: #fff;
  box-shadow: 0 0 0 3px var(--zh-line-theme20);
}

:deep(.el-button--primary) {
  border: 0;
  border-radius: var(--zh-radius8);
  background: var(--zh-gradient-dblue);
  box-shadow: 0 10px 20px -12px rgb(29 78 216 / 68%);
  transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
}

:deep(.el-button--primary:hover) {
  filter: brightness(1.04);
  box-shadow: 0 14px 26px -14px rgb(29 78 216 / 78%);
  transform: translateY(-1px);
}

:deep(.el-button--primary:active) { transform: translateY(0) scale(.98); }

@media (max-width: 1023px) {
  .login-form-panel {
    max-width: 440px;
    padding: 28px;
  }
}

@media (max-width: 639px) {
  .login-main { align-items: flex-start; padding-top: 72px; }
  .login-form-panel { padding: 0; border: 0; background: transparent; box-shadow: none; backdrop-filter: none; }
  .login-calibration-mark { right: 20px; }
  .login-calibration-mark--top { top: 20px; }
  .login-calibration-mark--bottom { bottom: 20px; }
}

@media (prefers-reduced-motion: reduce) {
  .login-fluid-canvas { opacity: .72; }
}
</style>
