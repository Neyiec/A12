/**
 * [数据交互说明]
 * - 导出: 模拟用户数据、角色数据、token 生成
 * - 依赖: `./common.ts` 的 `now`、`timeOffset`
 * - 输入: 被 auth.ts、user.ts、admin.ts handler 引用
 * - 输出: UserVO 列表、角色列表、登录态管理
 */

import { now, timeOffset } from './common'

/** 用户 VO（对应文档 UserVO） */
export interface MockUser {
  id: number
  username: string
  real_name: string
  phone: string
  email: string
  avatar: string
  user_type: 'teacher' | 'admin'
  roles: string
  permissions: string
  is_active: number
  email_verified: number
  phone_verified: number
  last_login_at: string
  last_login_ip: string
  password_changed_at: string
  deleted_at: string | null
  created_at: string
  updated_at: string
  /** 模拟明文密码，仅 mock 使用 */
  _password: string
}

/** 预置教师账号 */
export const mockTeachers: MockUser[] = [
  {
    id: 10001,
    username: 'teacher_zhang',
    real_name: '张老师',
    phone: '13800138001',
    email: 'zhang@school.edu.cn',
    avatar: '',
    user_type: 'teacher',
    roles: JSON.stringify(['teacher']),
    permissions: JSON.stringify(['project:create', 'project:edit', 'resource:upload', 'ai:use']),
    is_active: 1,
    email_verified: 1,
    phone_verified: 1,
    last_login_at: timeOffset(-1),
    last_login_ip: '192.168.1.100',
    password_changed_at: timeOffset(-30),
    deleted_at: null,
    created_at: timeOffset(-180),
    updated_at: timeOffset(-1),
    _password: '123456',
  },
  {
    id: 10002,
    username: 'teacher_li',
    real_name: '李老师',
    phone: '13800138002',
    email: 'li@school.edu.cn',
    avatar: '',
    user_type: 'teacher',
    roles: JSON.stringify(['teacher']),
    permissions: JSON.stringify(['project:create', 'project:edit', 'resource:upload']),
    is_active: 1,
    email_verified: 1,
    phone_verified: 0,
    last_login_at: timeOffset(-3),
    last_login_ip: '192.168.1.101',
    password_changed_at: timeOffset(-60),
    deleted_at: null,
    created_at: timeOffset(-150),
    updated_at: timeOffset(-3),
    _password: '123456',
  },
]

/** 预置管理员账号 */
export const mockAdmins: MockUser[] = [
  {
    id: 90001,
    username: 'admin_wang',
    real_name: '王管理员',
    phone: '13900139001',
    email: 'admin@a12.edu.cn',
    avatar: '',
    user_type: 'admin',
    roles: JSON.stringify(['super_admin']),
    permissions: JSON.stringify(['*']),
    is_active: 1,
    email_verified: 1,
    phone_verified: 1,
    last_login_at: timeOffset(0),
    last_login_ip: '192.168.1.200',
    password_changed_at: timeOffset(-90),
    deleted_at: null,
    created_at: timeOffset(-365),
    updated_at: timeOffset(0),
    _password: 'admin123',
  },
]

/** 所有模拟用户 */
export const allMockUsers: MockUser[] = [...mockTeachers, ...mockAdmins]

/** 基于 token 的简单会话表 */
export const mockSessions = new Map<string, MockUser>()

/**
 * 生成模拟 JWT 风格的 token
 */
export function generateMockToken(user: MockUser): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({ sub: user.id, username: user.username, user_type: user.user_type, iat: Math.floor(Date.now() / 1000) }))
  return `${header}.${payload}.mock_signature_${user.id}`
}

/** 预置角色 */
export const mockRoles = [
  { role_id: 1, role_name: 'super_admin', permissions: JSON.stringify(['*']), audit_scope: 'all' },
  { role_id: 2, role_name: 'content_admin', permissions: JSON.stringify(['content:review', 'content:publish', 'report:handle']), audit_scope: 'content' },
  { role_id: 3, role_name: 'teacher', permissions: JSON.stringify(['project:create', 'project:edit', 'resource:upload', 'ai:use']), audit_scope: 'self' },
]

/** 根据 token 查找当前用户 */
export function getUserByToken(authHeader: string | null): MockUser | null {
  if (!authHeader) return null
  const token = authHeader.replace(/^Bearer\s+/i, '')
  return mockSessions.get(token) || null
}

/** 验证码暂存（生产会存 Redis） */
export const verificationCodes = new Map<string, { code: string; expiresAt: number }>()
