/**
 * [数据交互说明]
 * - 导出:
 *   - `useUserStore`: 全局用户状态 Pinia store（含持久化）
 * - 依赖:
 *   - `pinia`: 状态管理
 *   - `pinia-plugin-persistedstate`: 自动将 token/userInfo/menus 同步到 localStorage
 * - 输入: 接收来自 `login.vue` 的 LoginVO 响应数据
 * - 输出: 为 `router`、`request.js` 及全局组件提供用户认证信息与菜单数据
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

/** 登录接口 LoginVO 中的用户信息字段 */
export interface UserInfo {
  /** 用户ID */
  user_id: number
  /** 用户名（登录账号） */
  username: string
  /** 真实姓名 */
  real_name: string
  /** 头像URL */
  avatar: string
  /** 用户类型: teacher / admin */
  user_type: 'teacher' | 'admin'
  /** 角色列表（后端以 JSON 字符串返回，存储时解析为数组） */
  roles: string[]
  /** 权限列表（后端以 JSON 字符串返回，存储时解析为数组） */
  permissions: string[]
  /** 登录时间 */
  created_at: string
}

export const useUserStore = defineStore('user', () => {
  // ========== 状态 ==========

  /** 会话令牌（JWT） */
  const token = ref('')

  /** 本次登录建立会话的时间，用于兼容不含 exp 的旧令牌 */
  const loginAt = ref(0)

  /** 当前登录用户的基本信息 */
  const userInfo = ref<UserInfo | null>(null)

  /** 后端返回的动态路由菜单数据 */
  const menus = ref<any[]>([])

  // ========== 方法 ==========

  /**
   * 设置登录令牌
   * @param t - JWT token 字符串
   */
  const setToken = (t: string) => {
    token.value = t
    loginAt.value = t ? Date.now() : 0
  }

  /**
   * 设置用户信息（LoginVO 完整字段）
   * 后端返回的 roles/permissions 为 JSON 字符串，此处做解析兼容
   * @param info - 登录接口返回的原始数据对象
   */
  const setUserInfo = (info: Record<string, any>) => {
    // 安全解析 JSON 字符串字段
    let roles: string[] = []
    let permissions: string[] = []
    try {
      roles = typeof info.roles === 'string' ? JSON.parse(info.roles) : (info.roles || [])
    } catch { /* 解析失败则使用空数组 */ }
    try {
      permissions = typeof info.permissions === 'string' ? JSON.parse(info.permissions) : (info.permissions || [])
    } catch { /* 解析失败则使用空数组 */ }

    userInfo.value = {
      user_id: info.user_id,
      username: info.username,
      real_name: info.real_name || '',
      avatar: info.avatar || '',
      user_type: info.user_type || 'teacher',
      roles,
      permissions,
      created_at: info.created_at || '',
    }
  }

  /**
   * 设置动态路由菜单数据
   * @param data - 后端返回的菜单树数组
   */
  const setMenus = (data: any[]) => {
    menus.value = data
  }

  /**
   * 清除所有用户状态（登出时调用）
   * 重置 token、userInfo、menus 为初始值
   */
  const clearUser = () => {
    token.value = ''
    loginAt.value = 0
    userInfo.value = null
    menus.value = []
  }

  return { token, loginAt, userInfo, menus, setToken, setUserInfo, setMenus, clearUser }
}, {
  // 开启持久化 — 自动将指定字段同步到 localStorage
  persist: {
    key: 'zh-user-store',
    storage: localStorage,
    // 指定需要持久化的字段
    pick: ['token', 'loginAt', 'userInfo', 'menus'],
  },
})
