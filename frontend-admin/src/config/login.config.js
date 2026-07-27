/**
 * [数据交互说明]
 * - 导出:
 *   - `LOGIN_TEXT`: 登录/注册页面所有文本标签的常量集合
 *   - `VALIDATION_RULES`: 表单校验规则常量
 * - 依赖: 无外部依赖
 * - 输出: 被 `src/components/login.vue` 引用
 */

/** 登录页面文本常量 — 禁止在组件中硬编码文本 */
export const LOGIN_TEXT = {
  // ========== 品牌信息 ==========
  brand: {
    name: '智核',
    /** 左侧面板主标语 */
    slogan: 'AI赋能教育\n让每一节课都精彩',
    /** 左侧面板副标语 */
    subtitle: '多模态AI互动式教学智能体',
  },

  // ========== 表单标题 ==========
  form: {
    loginTitle: '欢迎回来',
    registerTitle: '创建您的账号',
    loginSubtitle: '登录您的智核账号以继续使用AI教学助手',
    registerSubtitle: '创建账号以开启您的AI教学之旅',
  },

  // ========== 输入框标签 ==========
  label: {
    username: '用户名',
    password: '密码',
    confirmPassword: '确认密码',
  },

  // ========== placeholder ==========
  placeholder: {
    username: '请输入用户名',
    password: '请输入密码',
    registerPassword: '请输入密码（至少6位）',
    confirmPassword: '请再次输入密码',
  },

  // ========== 按钮 ==========
  button: {
    login: '登录',
    register: '注册',
    loginLoading: '登录中...',
    registerLoading: '注册中...',
  },

  // ========== 隐私协议 ==========
  privacy: {
    prefix: '我已阅读并同意',
    serviceAgreement: '《用户服务协议》',
    privacyPolicy: '《隐私政策》',
    and: '和',
  },

  // ========== 切换链接 ==========
  switch: {
    toRegister: '还没有账号？立即注册',
    toLogin: '已有账号？立即登录',
  },

  // ========== 提示信息 ==========
  message: {
    loginSuccess: '登录成功',
    registerSuccess: '注册成功，请登录',
    loginFailed: '用户名或密码错误',
    networkError: '网络连接失败，请检查网络后重试',
    registerFailed: '注册失败，请稍后重试',
    passwordMismatch: '两次输入的密码不一致',
  },
}

/** 表单校验规则 */
export const VALIDATION_RULES = {
  username: {
    required: true,
    min: 2,
    message: '用户名至少需要2个字符',
    trigger: ['blur', 'change'],
  },
  password: {
    required: true,
    min: 6,
    message: '密码至少需要6位',
    trigger: ['blur', 'change'],
  },
  confirmPassword: {
    required: true,
    min: 6,
    message: '请再次输入密码',
    trigger: ['blur', 'change'],
  },
  privacy: {
    required: true,
    message: '请先阅读并同意用户服务协议和隐私政策',
    trigger: ['change'],
  },
}
