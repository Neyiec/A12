import axios from 'axios'
import router from '../router/index'

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

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 添加 token
    const token = localStorage.getItem('token')
    if (token != null) {
      config.headers['token'] = token;
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

    // TODO 可以搞个弹窗
    if(code == 401){
      localStorage.removeItem('token')
      router.replace('/login');
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
        case 401:
          console.error('未授权，请重新登录')
          // 清除 token 并跳转到登录页
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
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