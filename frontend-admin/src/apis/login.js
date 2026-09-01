/**
 * [数据交互说明]
 * - 导出:
 *   - `login`: 用户登录接口
 *   - `register`: 用户注册接口
 *   - `sendVerificationCode`: 发送邮箱验证码接口
 *   - `getRouters`: 获取动态路由菜单
 * - 依赖:
 *   - `../utils/api`: 导入 `post`、`get` HTTP 工具方法
 * - 输入: 接收来自 `login.vue` 的用户凭证对象 / 验证码请求对象
 * - 输出: 返回 Promise，resolve 时为后端响应数据
 */
import {post, get} from '../utils/api'

/**
 * 用户登录
 * @param {{ username: string, password: string }} user - 登录凭证
 * @returns {Promise} 后端返回 { token: string, menus: Array } 等认证信息
 */
export function login(user) {
  return post('/api/v1/auth/login', user)
}

/**
 * 用户注册
 * @param {{ username: string, password: string, real_name: string,
 *           phone: string, email: string, code: string }} user - 注册信息
 * @returns {Promise<Result<UserVO>>} 后端返回注册用户信息
 */
export function register(user) {
  return post('/api/v1/auth/register', user)
}

/**
 * 发送邮箱验证码
 * 注册场景下 username 字段传邮箱地址
 * @param {{ username: string, scene: string, channel: string }} params - 验证码请求参数
 * @returns {Promise<Result<Void>>} 后端返回发送结果
 */
export function sendVerificationCode(params) {
  return post('/api/v1/auth/verification-codes', params)
}

/** 获取动态路由菜单
 * 根据当前登录用户的角色/权限返回可访问的菜单树
 * @returns {Promise} 后端返回 { menus: Array } 菜单树数据
 */
export function getRouters() {
  return get('/api/v1/menu/routers')
}

/**
 * 通过邮箱验证码重置密码
 * @param {{ username: string, code: string, new_password: string }} data - 重置资料
 * @returns {Promise<Result<Void>>} 后端返回重置结果
 */
export function resetPassword(data) {
  return post('/api/v1/auth/password-reset', data)
}
