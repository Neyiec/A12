import { login } from '../apis/login.js'
import { useUserStore } from '../storage/user.js'

/**
 * 开发预览使用真实 mock 登录接口建立会话。
 * 这样预览链路中的项目、页面和导出请求都会经过与生产相同的鉴权边界，
 * 不会因为浏览器刷新后 mockSessions 被清空而退化成纯前端演示数据。
 */
export async function ensureDevelopmentPreviewSession(force = false) {
  const isPreviewOrAutoExport = window.location.hash.includes('preview=1') || window.location.hash.includes('autoExport=1')
  if (!import.meta.env.DEV || (!force && !isPreviewOrAutoExport)) return null

  const result = await login({ username: 'teacher_zhang', password: '123456' })
  const loginVO = result?.data
  if (!loginVO?.token) throw new Error('开发预览账号登录失败')

  const userStore = useUserStore()
  userStore.setToken(loginVO.token)
  userStore.setUserInfo(loginVO)
  return loginVO
}
