import axios from 'axios'
import router from '../router/index'
// 全局用户 store — 统一管理 token，替代直接操作 localStorage
import { useUserStore } from '../storage/user.js'

// 从环境变量获取基础 URL
const baseURL = import.meta.env.VITE_API_BASE_URL || ''

// 创建 axios 实例
const service = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// 开发预览页使用组件内置的演示数据，不应因 mock 接口未登录而离开预览流程。
const isDevelopmentPreview = () => import.meta.env.DEV && router.currentRoute.value?.query?.preview === '1'

// 请求拦截器
service.interceptors.request.use(
  config => {
    // AI 引擎接口由浏览器直接调用 FastAPI；账号/业务接口仍由 Java 提供。
    if (config.url?.startsWith('/api/v1/python/')) {
      config.baseURL = import.meta.env.VITE_PYTHON_API_BASE_URL || ''
    }
    // 从 Pinia store 获取 token（由 pinia-plugin-persistedstate 自动从 localStorage 恢复）
    const userStore = useUserStore()
    const token = userStore.token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // FormData 请求必须交给浏览器生成带 boundary 的 multipart Content-Type。
    // 实例默认的 application/json 会触发 axios 的 formDataToJSON，把 File 序列化成 {}（语音上传 415 的根因）。
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      config.headers.delete?.('Content-Type')
      delete config.headers['Content-Type']
    }
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 根据后端返回的数据结构处理
    const res = response.data
    const code = response.data.code

    // 401 未授权 — 清除用户状态并跳转登录页，提前返回阻止业务层误处理
    if (code == 401 && !isDevelopmentPreview()) {
      const userStore = useUserStore()
      userStore.clearUser()
      router.replace('/login')
      return Promise.reject(new Error('未授权'))
    }

    // 如果返回的是二进制数据（如下载文件），直接返回
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response
    }

    return res
  },
  error => {
    console.error('响应错误:', error)

    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 400:
          console.error('请求参数错误')
          break
        case 401: {
          console.error('未授权，请重新登录')
          if (!isDevelopmentPreview()) {
            // 清除用户状态并使用 SPA 路由跳转，避免整页刷新
            const userStore = useUserStore()
            userStore.clearUser()
            router.replace('/login')
          }
          break
        }
        case 403:
          console.error('拒绝访问')
          break
        case 404:
          console.error('请求的资源不存在')
          break
        case 500:
          console.error('服务器内部错误')
          break
        default:
          console.error(data?.message || '请求失败')
      }
    } else if (error.request) {
      console.error('网络错误，请检查网络连接')
    } else {
      console.error('请求配置错误:', error.message)
    }

    return Promise.reject(error)
  }
)

export default service
