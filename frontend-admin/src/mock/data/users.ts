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
  user_type: 'teacher' | 'admin' | 'super_admin' | 'content_auditor' | 'knowledge_curator'
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

/** 后台账号池：覆盖 super_admin / content_auditor / knowledge_curator / teacher 四种角色及正常/封禁两种状态 */
export const mockStaffUsers: MockUser[] = [
  // 超级管理员
  { id: 90002, username: 'root_admin', real_name: '根管理员', phone: '13900139002', email: 'root@a12.edu.cn', avatar: '', user_type: 'super_admin', roles: JSON.stringify(['super_admin']), permissions: JSON.stringify(['*']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(0), last_login_ip: '192.168.1.201', password_changed_at: timeOffset(-20), deleted_at: null, created_at: timeOffset(-400), updated_at: timeOffset(0), _password: 'admin123' },
  { id: 90003, username: 'sec_admin', real_name: '安全管理员', phone: '13900139003', email: 'sec@a12.edu.cn', avatar: '', user_type: 'super_admin', roles: JSON.stringify(['super_admin']), permissions: JSON.stringify(['*']), is_active: 1, email_verified: 1, phone_verified: 0, last_login_at: timeOffset(-2), last_login_ip: '192.168.1.202', password_changed_at: timeOffset(-15), deleted_at: null, created_at: timeOffset(-300), updated_at: timeOffset(-2), _password: 'admin123' },

  // 内容审核员
  { id: 90004, username: 'auditor_chen', real_name: '陈审核员', phone: '13900139004', email: 'chen@a12.edu.cn', avatar: '', user_type: 'content_auditor', roles: JSON.stringify(['content_auditor']), permissions: JSON.stringify(['content:review', 'content:publish', 'report:handle']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-1), last_login_ip: '192.168.1.203', password_changed_at: timeOffset(-25), deleted_at: null, created_at: timeOffset(-200), updated_at: timeOffset(-1), _password: '123456' },
  { id: 90005, username: 'auditor_zhao', real_name: '赵审核员', phone: '13900139005', email: 'zhao@a12.edu.cn', avatar: '', user_type: 'content_auditor', roles: JSON.stringify(['content_auditor']), permissions: JSON.stringify(['content:review', 'content:publish']), is_active: 1, email_verified: 1, phone_verified: 0, last_login_at: timeOffset(-5), last_login_ip: '192.168.1.204', password_changed_at: timeOffset(-40), deleted_at: null, created_at: timeOffset(-180), updated_at: timeOffset(-5), _password: '123456' },
  { id: 90006, username: 'auditor_liu', real_name: '刘审核员', phone: '13900139006', email: 'liu@a12.edu.cn', avatar: '', user_type: 'content_auditor', roles: JSON.stringify(['content_auditor']), permissions: JSON.stringify(['content:review']), is_active: 0, email_verified: 0, phone_verified: 0, last_login_at: '', last_login_ip: '', password_changed_at: timeOffset(-50), deleted_at: null, created_at: timeOffset(-120), updated_at: timeOffset(-50), _password: '123456' },

  // 知识库维护员
  { id: 90007, username: 'curator_sun', real_name: '孙维护员', phone: '13900139007', email: 'sun@a12.edu.cn', avatar: '', user_type: 'knowledge_curator', roles: JSON.stringify(['knowledge_curator']), permissions: JSON.stringify(['resource:manage', 'kb:edit']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-1), last_login_ip: '192.168.1.205', password_changed_at: timeOffset(-10), deleted_at: null, created_at: timeOffset(-90), updated_at: timeOffset(-1), _password: '123456' },
  { id: 90008, username: 'curator_zhou', real_name: '周维护员', phone: '13900139008', email: 'zhou@a12.edu.cn', avatar: '', user_type: 'knowledge_curator', roles: JSON.stringify(['knowledge_curator']), permissions: JSON.stringify(['resource:manage']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-6), last_login_ip: '192.168.1.206', password_changed_at: timeOffset(-35), deleted_at: null, created_at: timeOffset(-70), updated_at: timeOffset(-6), _password: '123456' },
  { id: 90009, username: 'curator_wu', real_name: '吴维护员', phone: '13900139009', email: 'wu@a12.edu.cn', avatar: '', user_type: 'knowledge_curator', roles: JSON.stringify(['knowledge_curator']), permissions: JSON.stringify(['kb:edit']), is_active: 0, email_verified: 0, phone_verified: 0, last_login_at: '', last_login_ip: '', password_changed_at: timeOffset(-45), deleted_at: null, created_at: timeOffset(-60), updated_at: timeOffset(-45), _password: '123456' },

  // 普通教师
  { id: 10003, username: 'teacher_wang', real_name: '王老师', phone: '13800138003', email: 'wang@school.edu.cn', avatar: '', user_type: 'teacher', roles: JSON.stringify(['teacher']), permissions: JSON.stringify(['project:create', 'project:edit', 'resource:upload', 'ai:use']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-2), last_login_ip: '192.168.1.210', password_changed_at: timeOffset(-20), deleted_at: null, created_at: timeOffset(-140), updated_at: timeOffset(-2), _password: '123456' },
  { id: 10004, username: 'teacher_chen', real_name: '陈老师', phone: '13800138004', email: 'chen@school.edu.cn', avatar: '', user_type: 'teacher', roles: JSON.stringify(['teacher']), permissions: JSON.stringify(['project:create', 'resource:upload']), is_active: 1, email_verified: 1, phone_verified: 0, last_login_at: timeOffset(-8), last_login_ip: '192.168.1.211', password_changed_at: timeOffset(-70), deleted_at: null, created_at: timeOffset(-100), updated_at: timeOffset(-8), _password: '123456' },
  { id: 10005, username: 'teacher_zhao', real_name: '赵老师', phone: '13800138005', email: 'zhao@school.edu.cn', avatar: '', user_type: 'teacher', roles: JSON.stringify(['teacher']), permissions: JSON.stringify(['ai:use']), is_active: 0, email_verified: 1, phone_verified: 0, last_login_at: '', last_login_ip: '', password_changed_at: timeOffset(-55), deleted_at: null, created_at: timeOffset(-50), updated_at: timeOffset(-55), _password: '123456' },
  { id: 10006, username: 'teacher_huang', real_name: '黄老师', phone: '13800138006', email: 'huang@school.edu.cn', avatar: '', user_type: 'teacher', roles: JSON.stringify(['teacher']), permissions: JSON.stringify(['project:create', 'ai:use']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-12), last_login_ip: '192.168.1.212', password_changed_at: timeOffset(-15), deleted_at: null, created_at: timeOffset(-30), updated_at: timeOffset(-12), _password: '123456' },
  { id: 10007, username: 'teacher_lin', real_name: '林老师', phone: '13800138007', email: 'lin@school.edu.cn', avatar: '', user_type: 'teacher', roles: JSON.stringify(['teacher']), permissions: JSON.stringify(['resource:upload', 'ai:use']), is_active: 1, email_verified: 1, phone_verified: 1, last_login_at: timeOffset(-1), last_login_ip: '192.168.1.213', password_changed_at: timeOffset(-22), deleted_at: null, created_at: timeOffset(-25), updated_at: timeOffset(-1), _password: '123456' },
]

/** 所有模拟用户 */
export const allMockUsers: MockUser[] = [...mockTeachers, ...mockAdmins, ...mockStaffUsers]

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
