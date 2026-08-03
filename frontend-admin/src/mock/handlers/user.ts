/**
 * [数据交互说明]
 * - 导出: MSW 用户模块请求处理器（API-09 ~ API-11）
 * - 依赖:
 *   - `msw`: http, HttpResponse
 *   - `../data/users`: allMockUsers, mockSessions
 *   - `../data/common`: success, error, extractToken
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/users/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { allMockUsers, mockSessions } from '../data/users'
import { success, error, extractToken } from '../data/common'

export const userHandlers = [
  // ========== API-09 获取当前用户信息 ==========
  http.get('/api/v1/users/me', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) {
      return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    }
    return HttpResponse.json(success({
      id: user.id,
      username: user.username,
      real_name: user.real_name,
      phone: user.phone,
      email: user.email,
      avatar: user.avatar,
      user_type: user.user_type,
      roles: user.roles,
      permissions: user.permissions,
      is_active: user.is_active,
      email_verified: user.email_verified,
      phone_verified: user.phone_verified,
      last_login_at: user.last_login_at,
      last_login_ip: user.last_login_ip,
      password_changed_at: user.password_changed_at,
      deleted_at: user.deleted_at,
      created_at: user.created_at,
      updated_at: user.updated_at,
    }))
  }),

  // ========== API-10 根据用户名查询 ==========
  http.get('/api/v1/users/by-username', async ({ request }) => {
    const url = new URL(request.url)
    const username = url.searchParams.get('username')
    if (!username) {
      return HttpResponse.json(error(400, '缺少 username 参数'), { status: 400 })
    }

    const user = allMockUsers.find((u) => u.username === username)
    if (!user) {
      return HttpResponse.json(error(404, '用户不存在'), { status: 404 })
    }

    return HttpResponse.json(success({
      id: user.id,
      username: user.username,
      real_name: user.real_name,
      email: user.email,
    }))
  }),

  // ========== API-11 根据邮箱查询 ==========
  http.get('/api/v1/users/by-email', async ({ request }) => {
    const url = new URL(request.url)
    const email = url.searchParams.get('email')
    if (!email) {
      return HttpResponse.json(error(400, '缺少 email 参数'), { status: 400 })
    }

    const user = allMockUsers.find((u) => u.email === email)
    if (!user) {
      return HttpResponse.json(error(404, '用户不存在'), { status: 404 })
    }

    return HttpResponse.json(success({
      id: user.id,
      username: user.username,
      real_name: user.real_name,
      email: user.email,
    }))
  }),
]
