/**
 * [数据交互说明]
 * - 导出: MSW 后台管理请求处理器（API-75 ~ API-132）
 *   涵盖: 用户权限、公共资源、内容审核、导出模板、AI配置、安全策略、日志与看板
 * - 依赖: msw, ../data/users, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/admin/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { allMockUsers, mockRoles, mockSessions } from '../data/users'
import { success, error, extractToken, now, getPagination, pageResult, timeOffset } from '../data/common'

/** 公共资源存储 */
const publicResources: Record<string, unknown>[] = [
  { id: 1, resource_type: 'template', title: '通用课件模板', subject: '通用', grade: '通用', file_url: 'https://oss.example.com/public/template_v1.pptx', template_data: '{}', thumbnail: '', description: '适用于各学科的标准课件模板', status: 1, uploaded_by: 90001, ai_index_status: 'completed', ai_indexed_at: timeOffset(-10), ai_index_error: null, created_at: timeOffset(-30), updated_at: timeOffset(-10) },
  { id: 2, resource_type: 'image', title: '数学几何图形集', subject: '数学', grade: '初中', file_url: 'https://oss.example.com/public/math_shapes.zip', template_data: null, thumbnail: '', description: '常用几何图形素材', status: 1, uploaded_by: 90001, ai_index_status: 'indexing', ai_indexed_at: null, ai_index_error: null, created_at: timeOffset(-5), updated_at: timeOffset(-5) },
]
const auditTasks: Record<string, unknown>[] = [
  { id: 1, audit_type: 'moderation', target_type: 'submission', target_id: 1, handler_id: null, status: 'pending', reason: '', action: null, comment: null, created_at: timeOffset(-15), updated_at: timeOffset(-15) },
]
const configs: Record<string, unknown>[] = [
  { id: 1, config_group: 'ai_model', config_key: 'default_model', config_value: 'gpt-4o', description: '默认大模型', updated_by: 90001, updated_at: timeOffset(-10) },
  { id: 2, config_group: 'platform', config_key: 'max_slide_count', config_value: '30', description: '单次生成最大页数', updated_by: 90001, updated_at: timeOffset(-30) },
  { id: 3, config_group: 'security', config_key: 'content_filter', config_value: 'enabled', description: '内容安全过滤开关', updated_by: 90001, updated_at: timeOffset(-60) },
]
const auditLogs: Record<string, unknown>[] = [
  { id: 1, user_id: 10001, log_type: 'operation', module: 'project', action: 'create', target_type: 'project', target_id: 1, detail: '{}', ip: '192.168.1.100', request_id: 'req_001', method: 'POST', path: '/api/v1/projects', user_agent: 'Mozilla/5.0', status: 'success', error_message: null, duration_ms: 120, created_at: timeOffset(-30) },
  { id: 2, user_id: 10001, log_type: 'download', module: 'resource', action: 'download', target_type: 'resource', target_id: 1, detail: '{}', ip: '192.168.1.100', request_id: 'req_002', method: 'POST', path: '/api/v1/resources/1/download-url', user_agent: 'Mozilla/5.0', status: 'success', error_message: null, duration_ms: 85, created_at: timeOffset(-15) },
]
const alerts: Record<string, unknown>[] = [
  { id: 1, level: 'warning', source: 'ai_service', title: 'AI 模型响应延迟升高', detail: '近5分钟平均延迟超过5秒', status: 'pending', acknowledged_by: null, resolved_by: null, created_at: timeOffset(-1), acknowledged_at: null, resolved_at: null },
  { id: 2, level: 'info', source: 'storage', title: 'OSS 存储空间使用率80%', detail: '当前使用800GB/1TB', status: 'acknowledged', acknowledged_by: 90001, resolved_by: null, created_at: timeOffset(-2), acknowledged_at: timeOffset(-1), resolved_at: null },
]

/** 导出模板内存存储（API-98~101） */
const exportTemplates = [
  { id: 1, name: '标准课件模板 - 简约蓝', export_type: 'pptx', version: 2, status: 'published', size: '4.2MB', is_default: true, uploader: '管理员', download_count: 328, created_at: timeOffset(-90), updated_at: timeOffset(-30) },
  { id: 2, name: '标准教案模板 - 学术风格', export_type: 'word', version: 3, status: 'published', size: '2.1MB', is_default: true, uploader: '管理员', download_count: 265, created_at: timeOffset(-60), updated_at: timeOffset(-7) },
  { id: 3, name: '实验报告模板', export_type: 'word', version: 5, status: 'published', size: '1.8MB', is_default: false, uploader: '教务处', download_count: 412, created_at: timeOffset(-75), updated_at: timeOffset(-3) },
  { id: 4, name: '互动课件模板 - 科技感', export_type: 'pptx', version: 1, status: 'unpublished', size: '5.6MB', is_default: false, uploader: '李老师', download_count: 0, created_at: timeOffset(-20), updated_at: timeOffset(-1) },
  { id: 5, name: '公开课教案模板', export_type: 'word', version: 4, status: 'published', size: '1.4MB', is_default: false, uploader: '教研组', download_count: 189, created_at: timeOffset(-55), updated_at: timeOffset(-12) },
  { id: 6, name: '习题课课件模板', export_type: 'pptx', version: 2, status: 'published', size: '3.7MB', is_default: false, uploader: '王老师', download_count: 143, created_at: timeOffset(-40), updated_at: timeOffset(-6) },
  { id: 7, name: '复习课教案模板', export_type: 'word', version: 1, status: 'published', size: '1.6MB', is_default: false, uploader: '教研组', download_count: 96, created_at: timeOffset(-32), updated_at: timeOffset(-14) },
  { id: 8, name: '教学反思报告模板', export_type: 'word', version: 3, status: 'unpublished', size: '0.9MB', is_default: false, uploader: '张老师', download_count: 0, created_at: timeOffset(-8), updated_at: timeOffset(-2) },
  { id: 9, name: '项目式学习课件模板', export_type: 'pptx', version: 1, status: 'published', size: '6.3MB', is_default: false, uploader: '赵老师', download_count: 57, created_at: timeOffset(-28), updated_at: timeOffset(-18) },
  { id: 10, name: '单元教学设计模板', export_type: 'word', version: 2, status: 'published', size: '2.8MB', is_default: false, uploader: '教务处', download_count: 231, created_at: timeOffset(-50), updated_at: timeOffset(-9) },
  { id: 11, name: '说课稿模板', export_type: 'word', version: 1, status: 'unpublished', size: '1.1MB', is_default: false, uploader: '孙老师', download_count: 0, created_at: timeOffset(-4), updated_at: timeOffset(-4) },
  { id: 12, name: '微课课件模板', export_type: 'pptx', version: 2, status: 'published', size: '4.8MB', is_default: false, uploader: '钱老师', download_count: 174, created_at: timeOffset(-45), updated_at: timeOffset(-5) },
]

export const adminHandlers = [
  // ==================== 八、用户权限模块（API-75 ~ API-82） ====================

  // ========== API-75 分页查询用户 ==========
  http.get('/api/v1/admin/users', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const keyword = url.searchParams.get('keyword') || ''
    const userType = url.searchParams.get('user_type')
    const isActive = url.searchParams.get('is_active')

    let filtered = [...allMockUsers]
    if (keyword) filtered = filtered.filter((u) => u.username.includes(keyword) || u.real_name.includes(keyword))
    if (userType) filtered = filtered.filter((u) => u.user_type === userType)
    if (isActive !== null) filtered = filtered.filter((u) => u.is_active === parseInt(isActive, 10))

    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  // ========== API-76 获取用户详情 ==========
  http.get('/api/v1/admin/users/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const user = allMockUsers.find((u) => u.id === id)
    if (!user) return HttpResponse.json(error(404, '用户不存在'), { status: 404 })
    return HttpResponse.json(success(user))
  }),

  // ========== API-77 启用/停用/锁定用户 ==========
  http.patch('/api/v1/admin/users/:id/status', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const user = allMockUsers.find((u) => u.id === id)
    if (!user) return HttpResponse.json(error(404, '用户不存在'), { status: 404 })

    const body = (await request.json()) as { is_active: number }
    user.is_active = body.is_active
    user.updated_at = now()
    return HttpResponse.json(success(user))
  }),

  // ========== API-78 创建后台账号 ==========
  http.post('/api/v1/admin/users', async ({ request }) => {
    const body = (await request.json()) as Record<string, string>
    const newUser = {
      id: allMockUsers.length + 90010,
      username: body.username,
      real_name: body.real_name,
      phone: body.phone || '',
      email: body.email || '',
      avatar: '',
      user_type: 'admin' as const,
      roles: body.roles,
      permissions: JSON.stringify([]),
      is_active: 1,
      email_verified: 0,
      phone_verified: 0,
      last_login_at: '',
      last_login_ip: '',
      password_changed_at: now(),
      deleted_at: null,
      created_at: now(),
      updated_at: now(),
      _password: body.password,
    }
    allMockUsers.push(newUser)
    return HttpResponse.json(success(newUser))
  }),

  // ========== API-79 批量创建账号 ==========
  http.post('/api/v1/admin/users/batch', async ({ request }) => {
    const body = (await request.json()) as { idempotent_key: string; users: Record<string, string>[] }
    const results = body.users.map((u) => {
      const newUser = {
        id: allMockUsers.length + 90020,
        username: u.username,
        real_name: u.real_name,
        phone: u.phone || '',
        email: u.email || '',
        avatar: '',
        user_type: 'admin' as const,
        roles: u.roles,
        permissions: JSON.stringify([]),
        is_active: 1,
        email_verified: 0,
        phone_verified: 0,
        last_login_at: '',
        last_login_ip: '',
        password_changed_at: now(),
        deleted_at: null,
        created_at: now(),
        updated_at: now(),
        _password: u.password,
      }
      allMockUsers.push(newUser)
      return { username: u.username, success: true, initial_credentials: { username: u.username, password: u.password }, error: null }
    })
    return HttpResponse.json(success({ results }))
  }),

  // ========== API-80 查询角色 ==========
  http.get('/api/v1/admin/roles', async () => {
    return HttpResponse.json(success(mockRoles))
  }),

  // ========== API-81 分配角色 ==========
  http.put('/api/v1/admin/users/:id/roles', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const user = allMockUsers.find((u) => u.id === id)
    if (!user) return HttpResponse.json(error(404, '用户不存在'), { status: 404 })
    const body = (await request.json()) as { roles: string }
    user.roles = body.roles
    user.updated_at = now()
    return HttpResponse.json(success(user))
  }),

  // ========== API-82 配置角色权限 ==========
  http.put('/api/v1/admin/roles/:id/permissions', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const role = mockRoles.find((r) => r.role_id === id)
    if (!role) return HttpResponse.json(error(404, '角色不存在'), { status: 404 })
    const body = (await request.json()) as { permissions: string }
    role.permissions = body.permissions
    return HttpResponse.json(success(null))
  }),

  // ==================== 九、公共资源模块（API-83 ~ API-89-1） ====================

  // ========== API-83 分页查询公共资源 ==========
  http.get('/api/v1/admin/public-resources', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const resourceType = url.searchParams.get('resource_type')
    const status = url.searchParams.get('status')

    let filtered = [...publicResources]
    if (resourceType) filtered = filtered.filter((r) => r.resource_type === resourceType)
    if (status !== null) filtered = filtered.filter((r) => r.status === parseInt(status, 10))

    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  // ========== API-84 创建公共资源上传会话 ==========
  http.post('/api/v1/admin/public-resources/uploads', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    const body = (await request.json()) as Record<string, unknown>
    const uploadId = publicResources.length + 100
    const expiresAt = new Date(Date.now() + 30 * 60 * 1000).toISOString()

    publicResources.push({
      id: uploadId, resource_type: body.resource_type, title: body.title, subject: '', grade: '',
      file_url: `https://oss.example.com/public/${body.file_name || 'unknown'}`,
      template_data: null, thumbnail: '', description: '', status: 0,
      uploaded_by: user?.id || 90001, ai_index_status: 'pending', ai_indexed_at: null, ai_index_error: null,
      created_at: now(), updated_at: now(),
    })

    return HttpResponse.json(success({ upload_id: uploadId, upload_url: `https://oss.example.com/put/public_${uploadId}?signature=mock`, expires_at: expiresAt }))
  }),

  // ========== API-85 完成上传 ==========
  http.post('/api/v1/admin/public-resources/uploads/:id/complete', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const resource = publicResources.find((r) => r.id === id)
    if (!resource) return HttpResponse.json(error(404, '上传会话不存在'), { status: 404 })
    resource.status = 1
    resource.ai_index_status = 'indexing'
    resource.updated_at = now()

    // 模拟异步索引完成
    setTimeout(() => { resource.ai_index_status = 'completed'; resource.ai_indexed_at = new Date().toISOString() }, 2000)

    return HttpResponse.json(success(resource))
  }),

  // ========== API-86 公共资源详情 ==========
  http.get('/api/v1/admin/public-resources/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const resource = publicResources.find((r) => r.id === id)
    if (!resource) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    return HttpResponse.json(success(resource))
  }),

  // ========== API-87 更新公共资源元数据 ==========
  http.patch('/api/v1/admin/public-resources/:id', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const resource = publicResources.find((r) => r.id === id)
    if (!resource) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    const body = (await request.json()) as Record<string, unknown>
    if (body.title) resource.title = body.title
    if (body.subject) resource.subject = body.subject
    if (body.grade) resource.grade = body.grade
    if (body.description) resource.description = body.description
    resource.updated_at = now()
    return HttpResponse.json(success(resource))
  }),

  // ========== API-88 启用/停用公共资源 ==========
  http.put('/api/v1/admin/public-resources/:id/status', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const resource = publicResources.find((r) => r.id === id)
    if (!resource) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    const body = (await request.json()) as { status: number }
    resource.status = body.status
    resource.updated_at = now()
    return HttpResponse.json(success(resource))
  }),

  // ========== API-89 处理状态 ==========
  http.get('/api/v1/admin/public-resources/:id/processing-status', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const resource = publicResources.find((r) => r.id === id)
    if (!resource) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    return HttpResponse.json(success({
      security_check: 'passed', parse_status: resource.ai_index_status, index_status: resource.ai_index_status, error_msg: resource.ai_index_error,
    }))
  }),

  // ========== API-89-1 初始化AI索引库 ==========
  http.post('/api/v1/admin/public-resources/ai-index/bootstrap', async ({ request }) => {
    const url = new URL(request.url)
    const force = url.searchParams.get('force_reparse') === 'true'
    return HttpResponse.json(success({ total: publicResources.length, indexed: force ? publicResources.length : 1, skipped: force ? 0 : publicResources.length - 1, failed: 0, results: [] }))
  }),

  // ==================== 十、内容审核与举报处理（API-90 ~ API-97） ====================

  // ========== API-90 审核任务列表 ==========
  http.get('/api/v1/admin/moderation/tasks', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const total = auditTasks.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(auditTasks.slice(start, start + size), total, page, size)))
  }),

  // ========== API-91 审核任务详情 ==========
  http.get('/api/v1/admin/moderation/tasks/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = auditTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '审核任务不存在'), { status: 404 })
    return HttpResponse.json(success(task))
  }),

  // ========== API-92 提交审核决定 ==========
  http.post('/api/v1/admin/moderation/tasks/:id/decisions', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const task = auditTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '审核任务不存在'), { status: 404 })
    const body = (await request.json()) as { action: string; comment?: string }
    task.action = body.action
    task.comment = body.comment || ''
    task.status = 'resolved'
    task.updated_at = now()
    return HttpResponse.json(success(null))
  }),

  // ========== API-93 上架/下架社区内容 ==========
  http.put('/api/v1/admin/community-items/:id/status', async ({ request, params }) => {
    const body = (await request.json()) as { status: string }
    return HttpResponse.json(success({ id: parseInt(params.id as string, 10), status: body.status, updated_at: now() }))
  }),

  // ========== API-94 设置推荐/置顶 ==========
  http.put('/api/v1/admin/community-items/:id/recommendation', async ({ request, params }) => {
    const body = (await request.json()) as { is_top: number; expires_at?: string }
    return HttpResponse.json(success({ id: parseInt(params.id as string, 10), is_top: body.is_top, expires_at: body.expires_at || null }))
  }),

  // ========== API-95 举报列表(管理端) ==========
  http.get('/api/v1/admin/reports', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    return HttpResponse.json(success(pageResult([], 0, page, size)))
  }),

  // ========== API-96 举报详情(管理端) ==========
  http.get('/api/v1/admin/reports/:id', async () => {
    return HttpResponse.json(error(404, '举报不存在'), { status: 404 })
  }),

  // ========== API-97 处理举报 ==========
  http.post('/api/v1/admin/reports/:id/resolution', async ({ request }) => {
    const body = (await request.json()) as { action: string; comment?: string }
    return HttpResponse.json(success(null, `处理结果: ${body.action}`))
  }),

  // ==================== 十一、导出模板模块（API-98 ~ API-101） ====================

  // ========== API-98 分页查询导出模板 ==========
  http.get('/api/v1/admin/export-templates', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const exportType = url.searchParams.get('export_type')
    const status = url.searchParams.get('status')
    const keyword = (url.searchParams.get('keyword') || '').trim()

    let filtered = [...exportTemplates]
    if (exportType) filtered = filtered.filter((t) => t.export_type === exportType)
    if (status) filtered = filtered.filter((t) => t.status === status)
    if (keyword) filtered = filtered.filter((t) => t.name.includes(keyword))

    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  http.post('/api/v1/admin/export-templates', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const tpl = { id: exportTemplates.length + 1, name: body.name, export_type: body.export_type, version: 1, status: 'unpublished', created_at: now(), updated_at: now() }
    exportTemplates.push(tpl)
    return HttpResponse.json(success({ id: tpl.id, version: 1 }))
  }),

  http.patch('/api/v1/admin/export-templates/:id', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const tpl = exportTemplates.find((t) => t.id === id)
    if (!tpl) return HttpResponse.json(error(404, '模板不存在'), { status: 404 })
    tpl.version += 1
    tpl.updated_at = now()
    return HttpResponse.json(success({ id, version: tpl.version }))
  }),

  http.put('/api/v1/admin/export-templates/:id/status', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const tpl = exportTemplates.find((t) => t.id === id)
    if (!tpl) return HttpResponse.json(error(404, '模板不存在'), { status: 404 })
    const body = (await request.json()) as { status: string }
    tpl.status = body.status
    return HttpResponse.json(success(null))
  }),

  // ==================== 十二、AI配置模块（API-102 ~ API-122） ====================

  http.get('/api/v1/admin/ai-configs', async ({ request }) => {
    const url = new URL(request.url)
    const group = url.searchParams.get('config_group')
    let filtered = configs
    if (group) filtered = configs.filter((c) => c.config_group === group)
    return HttpResponse.json(success(filtered))
  }),

  http.post('/api/v1/admin/ai-configs', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const cfg = { id: configs.length + 1, config_group: body.config_group, config_key: body.config_key, config_value: body.config_value, description: body.description || '', updated_by: 90001, updated_at: now() }
    configs.push(cfg)
    return HttpResponse.json(success(cfg))
  }),

  http.post('/api/v1/admin/ai-configs/:id/publish', async () => {
    return HttpResponse.json(success({ node_status: [{ node: 'node-1', status: 'ok' }] }))
  }),

  http.post('/api/v1/admin/ai-configs/:id/rollback', async ({ request }) => {
    const body = (await request.json()) as { target_version: number; reason: string }
    return HttpResponse.json(success({ ...configs[0], version: body.target_version }))
  }),

  // ==================== 十三、安全策略（API-123 ~ API-125） ====================

  http.get('/api/v1/admin/security-policies', async () => {
    return HttpResponse.json(success(configs.filter((c) => c.config_group === 'security')))
  }),

  http.put('/api/v1/admin/security-policies/:id', async ({ request }) => {
    const body = (await request.json()) as { config_value: string; version: number }
    return HttpResponse.json(success({ ...configs[2], config_value: body.config_value, updated_at: now() }))
  }),

  http.post('/api/v1/admin/security-policies/:id/publish', async () => {
    return HttpResponse.json(success({ published: true }))
  }),

  // ==================== 十四、日志与看板（API-126 ~ API-132） ====================

  http.get('/api/v1/admin/audit-logs', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const total = auditLogs.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(auditLogs.slice(start, start + size), total, page, size)))
  }),

  http.get('/api/v1/admin/system-logs', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    return HttpResponse.json(success(pageResult(auditLogs.filter((l) => l.log_type === 'system'), 0, page, size)))
  }),

  http.get('/api/v1/admin/dashboard', async () => {
    return HttpResponse.json(success({
      user_count: allMockUsers.length,
      resource_count: 128,
      ai_task_count: 456,
      export_task_count: 89,
      moderation_pending_count: 3,
    }))
  }),

  http.get('/api/v1/admin/alerts', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const level = url.searchParams.get('level')
    const status = url.searchParams.get('status')

    let filtered = [...alerts]
    if (level) filtered = filtered.filter((a) => a.level === level)
    if (status) filtered = filtered.filter((a) => a.status === status)

    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size).map((a) => ({ id: a.id, level: a.level, source: a.source, title: a.title, status: a.status, created_at: a.created_at, resolved_at: a.resolved_at })), total, page, size)))
  }),

  http.get('/api/v1/admin/alerts/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const alert = alerts.find((a) => a.id === id)
    if (!alert) return HttpResponse.json(error(404, '告警不存在'), { status: 404 })
    return HttpResponse.json(success(alert))
  }),

  http.post('/api/v1/admin/alerts/:id/acknowledge', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const alert = alerts.find((a) => a.id === id)
    if (!alert) return HttpResponse.json(error(404, '告警不存在'), { status: 404 })
    alert.status = 'acknowledged'
    alert.acknowledged_by = 90001
    alert.acknowledged_at = now()
    return HttpResponse.json(success(null))
  }),

  http.post('/api/v1/admin/alerts/:id/resolve', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const alert = alerts.find((a) => a.id === id)
    if (!alert) return HttpResponse.json(error(404, '告警不存在'), { status: 404 })
    const body = (await request.json()) as { resolution: string }
    alert.status = 'resolved'
    alert.resolved_by = 90001
    alert.resolved_at = now()
    return HttpResponse.json(success(null, `已解决: ${body.resolution}`))
  }),
]
