/**
 * [数据交互说明]
 * - 导出:
 *   - `login`: 用户登录接口
 *   - `register`: 用户注册接口
 *   - `getRouters`: 获取动态路由菜单
 * - 依赖:
 *   - `../utils/api`: 导入 `post`、`get` HTTP 工具方法
 * - 输入: 接收来自 `login.vue` 的用户凭证对象
 * - 输出: 返回 Promise，resolve 时为后端响应数据
 */
import {post, get} from '../utils/api'

/**
 * 用户登录
 * @param {{ username: string, password: string }} user - 登录凭证
 * @returns {Promise} 后端返回 { token: string, menus: Array } 等认证信息
 */
export function login(user) {
  return post('/api/user/login', user)
}

/**
 * 用户注册
 * @param {{ username: string, password: string }} user - 注册信息
 * @returns {Promise} 后端返回注册结果
 */
export function register(user) {
  return post('/api/user/register', user)
}

/**
 * 获取动态路由菜单
 * @returns {Promise} 后端返回 { menus: Array } 菜单树
 */
export function getRouters() {
  return get('/api/getRouters')
}