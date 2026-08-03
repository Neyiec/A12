/**
 * [数据交互说明]
 * - 导出: MSW 认证模块请求处理器（API-01 ~ API-08）
 * - 依赖:
 *   - `msw`: http, HttpResponse
 *   - `../data/users`: MockUser, generateMockToken, verificationCodes, mockSessions, allMockUsers
 *   - `../data/common`: success, error, simulateDelay, extractToken
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/auth/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { allMockUsers, generateMockToken, mockSessions, verificationCodes } from '../data/users'
import { success, error, simulateDelay, extractToken } from '../data/common'

export const authHandlers = [
  // ========== API-01 注册 ==========
  http.post('/api/v1/auth/register', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as Record<string, string>

    // 校验必填字段
    if (!body.username || !body.password || !body.real_name || !body.email || !body.code) {
      return HttpResponse.json(error(400, '缺少必填字段'), { status: 400 })
    }

    // 检查用户名是否已存在
    if (allMockUsers.find((u) => u.username === body.username)) {
      return HttpResponse.json(error(422, '用户名已被注册'), { status: 422 })
    }

    // 校验验证码
    const stored = verificationCodes.get(body.username)
    if (!stored || stored.code !== body.code || stored.expiresAt < Date.now()) {
      return HttpResponse.json(error(422, '验证码错误或已过期'), { status: 422 })
    }
    verificationCodes.delete(body.username)

    // 创建新用户
    const now = new Date().toISOString()
    const newUser = {
      id: allMockUsers.length + 10010,
      username: body.username,
      real_name: body.real_name,
      phone: body.phone || '',
      email: body.email,
      avatar: body.avatar || '',
      user_type: 'teacher' as const,
      roles: JSON.stringify(['teacher']),
      permissions: JSON.stringify(['project:create', 'project:edit', 'resource:upload', 'ai:use']),
      is_active: 1,
      email_verified: 0,
      phone_verified: 0,
      last_login_at: now,
      last_login_ip: '127.0.0.1',
      password_changed_at: now,
      deleted_at: null,
      created_at: now,
      updated_at: now,
      _password: body.password,
    }
    allMockUsers.push(newUser)

    return HttpResponse.json(success({
      id: newUser.id,
      username: newUser.username,
      real_name: newUser.real_name,
      phone: newUser.phone,
      email: newUser.email,
      avatar: newUser.avatar,
      user_type: newUser.user_type,
      roles: newUser.roles,
      permissions: newUser.permissions,
      is_active: newUser.is_active,
      email_verified: newUser.email_verified,
      phone_verified: newUser.phone_verified,
      created_at: newUser.created_at,
    }))
  }),

  // ========== API-02 发送验证码 ==========
  http.post('/api/v1/auth/verification-codes', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as Record<string, string>

    if (!body.username || !body.scene || !body.channel) {
      return HttpResponse.json(error(400, '缺少必填字段'), { status: 400 })
    }
    if (body.channel !== 'email') {
      return HttpResponse.json(error(400, '仅支持 email 渠道'), { status: 400 })
    }

    // 生成6位验证码，5分钟有效
    const code = String(Math.floor(100000 + Math.random() * 900000))
    verificationCodes.set(body.username, { code, expiresAt: Date.now() + 5 * 60 * 1000 })
    console.log(`[Mock] 验证码已发送到 ${body.username}: ${code}`)
    return HttpResponse.json(success(null, '验证码已发送'))
  }),

  // ========== API-03 校验验证码 ==========
  http.post('/api/v1/auth/verify', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as Record<string, string>

    const stored = verificationCodes.get(body.username)
    if (!stored || stored.code !== body.code || stored.expiresAt < Date.now()) {
      return HttpResponse.json(error(422, '验证码错误或已过期'), { status: 422 })
    }
    return HttpResponse.json(success(null, '验证码正确'))
  }),

  // ========== API-04 登录 ==========
  http.post('/api/v1/auth/login', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as { username: string; password: string }

    if (!body.username || !body.password) {
      return HttpResponse.json(error(400, '请输入用户名和密码'), { status: 400 })
    }

    const user = allMockUsers.find((u) => u.username === body.username && u.is_active === 1)
    if (!user || user._password !== body.password) {
      return HttpResponse.json(error(401, '用户名或密码错误'), { status: 401 })
    }

    // 生成 token 并记录会话
    const token = generateMockToken(user)
    mockSessions.set(token, user)

    // 更新最后登录时间
    user.last_login_at = new Date().toISOString()

    return HttpResponse.json(success({
      token,
      user_id: user.id,
      username: user.username,
      real_name: user.real_name,
      avatar: user.avatar,
      user_type: user.user_type,
      roles: user.roles,
      permissions: user.permissions,
      last_login_at: user.last_login_at,
      created_at: user.created_at,
    }))
  }),

  // ========== API-05 首次改密 ==========
  http.post('/api/v1/auth/initial-password-change', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as { username: string; initial_password: string; new_password: string }

    const user = allMockUsers.find((u) => u.username === body.username)
    if (!user || user._password !== body.initial_password) {
      return HttpResponse.json(error(401, '初始密码错误'), { status: 401 })
    }

    user._password = body.new_password
    user.password_changed_at = new Date().toISOString()
    const token = generateMockToken(user)
    mockSessions.set(token, user)

    return HttpResponse.json(success({
      token,
      user_id: user.id,
      username: user.username,
      real_name: user.real_name,
      avatar: user.avatar,
      user_type: user.user_type,
      roles: user.roles,
      permissions: user.permissions,
    }))
  }),

  // ========== API-06 密码重置 ==========
  http.post('/api/v1/auth/password-reset', async ({ request }) => {
    await simulateDelay()
    const body = (await request.json()) as { username: string; code: string; new_password: string }

    const stored = verificationCodes.get(body.username)
    if (!stored || stored.code !== body.code || stored.expiresAt < Date.now()) {
      return HttpResponse.json(error(422, '验证码错误或已过期'), { status: 422 })
    }
    verificationCodes.delete(body.username)

    const user = allMockUsers.find((u) => u.username === body.username)
    if (!user) {
      return HttpResponse.json(error(404, '用户不存在'), { status: 404 })
    }

    user._password = body.new_password
    // 撤销所有已有会话
    mockSessions.forEach((u, t) => { if (u.id === user.id) mockSessions.delete(t) })

    return HttpResponse.json(success(null, '密码重置成功，请重新登录'))
  }),

  // ========== API-07 已登录用户改密 ==========
  http.post('/api/v1/users/me/password-change', async ({ request }) => {
    await simulateDelay()
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) {
      return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    }

    const body = (await request.json()) as { current_password: string; new_password: string }
    if (user._password !== body.current_password) {
      return HttpResponse.json(error(422, '当前密码错误'), { status: 422 })
    }

    user._password = body.new_password
    user.password_changed_at = new Date().toISOString()
    // 撤销其他会话
    mockSessions.forEach((u, t) => { if (u.id === user.id && t !== token) mockSessions.delete(t) })

    return HttpResponse.json(success(null, '密码修改成功'))
  }),

  // ========== API-08 退出登录 ==========
  http.post('/api/v1/auth/logout', async ({ request }) => {
    await simulateDelay()
    const token = extractToken(request.headers.get('Authorization'))
    if (token) mockSessions.delete(token)
    return HttpResponse.json(success(null, '已退出登录'))
  }),
]
