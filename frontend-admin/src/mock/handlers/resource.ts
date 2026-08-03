/**
 * [数据交互说明]
 * - 导出: MSW 个人资源库请求处理器（API-36 ~ API-46）
 * - 依赖: msw, ../data/users, ../data/resources, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/resources/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { mockMaterials, mockAuditLogs, getNextMaterialId } from '../data/resources'
import { success, error, extractToken, now, getPagination, pageResult, generateId } from '../data/common'

export const resourceHandlers = [
  // ========== API-36 获取 OSS 上传 Token ==========
  http.post('/api/v1/resources/upload-tokens', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, string>
    const objectKey = `resources/${user.id}/${generateId()}_${body.file_name}`
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString()

    return HttpResponse.json(success({
      object_key: objectKey,
      upload_url: `https://oss.example.com/put/${encodeURIComponent(objectKey)}?signature=mock_sig_${Date.now()}`,
      expires_at: expiresAt,
    }))
  }),

  // ========== API-37 确认文件上传 ==========
  http.post('/api/v1/resources/uploaded-files', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const material = {
      id: getNextMaterialId(),
      user_id: user.id,
      file_name: body.file_name as string,
      file_type: (body.file_type as string) || 'other',
      file_size: body.file_size as number,
      object_key: body.object_key as string,
      file_url: `https://oss.example.com/${body.object_key}`,
      description: (body.description as string) || '',
      categories: '[]',
      tags: '[]',
      access_type: 'private' as const,
      authorized_users: '[]',
      allow_ai: 0,
      ai_index_status: 'pending',
      ai_indexed_at: null,
      ai_index_error: null,
      status: 1,
      created_at: now(),
      updated_at: now(),
    }
    mockMaterials.push(material)
    return HttpResponse.json(success(material))
  }),

  // ========== API-38 分页查询资源 ==========
  http.get('/api/v1/resources', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const keyword = url.searchParams.get('keyword') || ''
    const fileType = url.searchParams.get('file_type')

    let filtered = mockMaterials.filter((m) => m.user_id === user.id)
    if (keyword) filtered = filtered.filter((m) => m.file_name.includes(keyword))
    if (fileType) filtered = filtered.filter((m) => m.file_type === fileType)

    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-39 获取资源详情 ==========
  http.get('/api/v1/resources/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const material = mockMaterials.find((m) => m.id === id)
    if (!material) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    return HttpResponse.json(success(material))
  }),

  // ========== API-40 编辑资源元数据 ==========
  http.patch('/api/v1/resources/:id', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const material = mockMaterials.find((m) => m.id === id)
    if (!material) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })

    const body = (await request.json()) as Record<string, unknown>
    if (body.file_name) material.file_name = body.file_name as string
    if (body.description) material.description = body.description as string
    if (body.categories) material.categories = body.categories as string
    if (body.tags) material.tags = body.tags as string
    material.updated_at = now()

    return HttpResponse.json(success(material))
  }),

  // ========== API-41 删除资源 ==========
  http.delete('/api/v1/resources/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const idx = mockMaterials.findIndex((m) => m.id === id)
    if (idx === -1) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    mockMaterials.splice(idx, 1)
    return HttpResponse.json(success(null, '资源已删除'))
  }),

  // ========== API-42 批量操作 ==========
  http.post('/api/v1/resources/batch-actions', async ({ request }) => {
    const body = (await request.json()) as { action: string; resource_ids: number[]; idempotent_key: string; target?: string }
    const results = body.resource_ids.map((rid) => {
      const material = mockMaterials.find((m) => m.id === rid)
      if (!material) return { id: rid, success: false, error: '资源不存在' }
      if (body.action === 'allow_ai') material.allow_ai = 1
      if (body.action === 'deny_ai') material.allow_ai = 0
      return { id: rid, success: true, error: null }
    })
    return HttpResponse.json(success({ results }))
  }),

  // ========== API-43 获取资源权限 ==========
  http.get('/api/v1/resources/:id/permission', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const material = mockMaterials.find((m) => m.id === id)
    if (!material) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })
    return HttpResponse.json(success({
      access_type: material.access_type,
      authorized_users: material.authorized_users,
      allow_ai: material.allow_ai,
    }))
  }),

  // ========== API-44 设置资源权限 ==========
  http.put('/api/v1/resources/:id/permission', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const material = mockMaterials.find((m) => m.id === id)
    if (!material) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })

    const body = (await request.json()) as Record<string, unknown>
    if (body.access_type) material.access_type = body.access_type as 'private' | 'shared' | 'authorized'
    if (body.authorized_users) material.authorized_users = body.authorized_users as string
    if (body.allow_ai !== undefined) material.allow_ai = body.allow_ai as number
    material.updated_at = now()

    return HttpResponse.json(success(material))
  }),

  // ========== API-45 审计日志 ==========
  http.get('/api/v1/resources/:id/audit-logs', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)

    const filtered = mockAuditLogs.filter((log) => log.resource_id === id)
    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-46 生成下载链接 ==========
  http.post('/api/v1/resources/:id/download-url', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const material = mockMaterials.find((m) => m.id === id)
    if (!material) return HttpResponse.json(error(404, '资源不存在'), { status: 404 })

    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString()
    return HttpResponse.json(success({
      download_url: `${material.file_url}?download_token=mock_${Date.now()}`,
      expires_at: expiresAt,
    }))
  }),
]
