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

type MockTaxonomy = { id: number; name: string; color: string | null; sort_order: number; deleted?: boolean }

const mockTaxonomies: Record<'category' | 'tag', MockTaxonomy[]> = {
  category: [
    { id: 101, name: '生物', color: '#2f6feb', sort_order: 10 },
    { id: 102, name: '七年级', color: '#35a06f', sort_order: 20 },
    { id: 103, name: '初中', color: '#9b6cf0', sort_order: 30 },
  ],
  tag: [
    { id: 201, name: '教材', color: '#2f6feb', sort_order: 10 },
    { id: 202, name: '光合作用', color: '#35a06f', sort_order: 20 },
    { id: 203, name: '教学设计', color: '#9b6cf0', sort_order: 30 },
  ],
}

let nextTaxonomyId = 301

function parseTaxonomyValues(value: string): string[] {
  try {
    const parsed = JSON.parse(value || '[]')
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch { return [] }
}

function getTaxonomyItems(kind: 'category' | 'tag', userId: number) {
  const field = kind === 'category' ? 'categories' : 'tags'
  const ownResources = mockMaterials.filter((item) => item.user_id === userId)
  const counts = new Map<string, number>()
  ownResources.forEach((item) => parseTaxonomyValues(item[field]).forEach((name) => counts.set(name, (counts.get(name) || 0) + 1)))
  const managedNames = new Set<string>()
  const managed = mockTaxonomies[kind].filter((item) => !item.deleted).map((item) => {
    managedNames.add(item.name)
    return { ...item, type: kind, count: counts.get(item.name) || 0, managed: true }
  })
  const unmanaged = [...counts.entries()]
    .filter(([name]) => !managedNames.has(name))
    .map(([name, count]) => ({ id: null, name, type: kind, count, color: null, sort_order: 1000, managed: false }))
  return [...managed, ...unmanaged].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name, 'zh-CN'))
}

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
      // 开发环境使用同源 mock 地址，避免浏览器因示例 OSS 域名跨域导致上传弹窗直接失败。
      upload_url: `/api/v1/resources/upload-objects?object_key=${encodeURIComponent(objectKey)}&signature=mock_sig_${Date.now()}`,
      expires_at: expiresAt,
    }))
  }),

  // ========== Mock OSS 文件直传 ==========
  http.put('/api/v1/resources/upload-objects', async ({ request }) => {
    await request.arrayBuffer()
    // 留出可观察的传输时间，便于开发环境验证上传进度反馈。
    await new Promise((resolve) => setTimeout(resolve, 600))
    return new HttpResponse(null, { status: 200 })
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

  // ========== API-38A/B 资源分类与标签词典 ==========
  http.get('/api/v1/resources/tags', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    return HttpResponse.json(success(getTaxonomyItems('tag', user.id)))
  }),

  http.get('/api/v1/resources/categories', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    return HttpResponse.json(success(getTaxonomyItems('category', user.id)))
  }),

  // ========== API-38C/D/F/G 管理资源分类与标签词典 ==========
  http.post('/api/v1/resources/tags', async ({ request }) => {
    const body = (await request.json()) as { name?: string; color?: string; sort_order?: number }
    const name = body.name?.trim()
    if (!name) return HttpResponse.json(error(400, '词条名称不能为空'), { status: 400 })
    const existing = mockTaxonomies.tag.find((item) => item.name === name)
    if (existing) { existing.deleted = false; existing.color = body.color || existing.color; return HttpResponse.json(success(getTaxonomyItems('tag', 10001).find((item) => item.id === existing.id))) }
    const item = { id: nextTaxonomyId++, name, color: body.color || null, sort_order: Number(body.sort_order) || 1000 }
    mockTaxonomies.tag.push(item)
    return HttpResponse.json(success(getTaxonomyItems('tag', 10001).find((entry) => entry.id === item.id)))
  }),

  http.post('/api/v1/resources/categories', async ({ request }) => {
    const body = (await request.json()) as { name?: string; color?: string; sort_order?: number }
    const name = body.name?.trim()
    if (!name) return HttpResponse.json(error(400, '词条名称不能为空'), { status: 400 })
    const existing = mockTaxonomies.category.find((item) => item.name === name)
    if (existing) { existing.deleted = false; existing.color = body.color || existing.color; return HttpResponse.json(success(getTaxonomyItems('category', 10001).find((item) => item.id === existing.id))) }
    const item = { id: nextTaxonomyId++, name, color: body.color || null, sort_order: Number(body.sort_order) || 1000 }
    mockTaxonomies.category.push(item)
    return HttpResponse.json(success(getTaxonomyItems('category', 10001).find((entry) => entry.id === item.id)))
  }),

  http.patch('/api/v1/resources/tags/:dictId', async ({ request, params }) => {
    const item = mockTaxonomies.tag.find((entry) => entry.id === Number(params.dictId) && !entry.deleted)
    if (!item) return HttpResponse.json(error(404, '标签不存在'), { status: 404 })
    const body = (await request.json()) as { name?: string; color?: string; sort_order?: number }
    if (body.name?.trim()) item.name = body.name.trim()
    if (body.color !== undefined) item.color = body.color || null
    if (body.sort_order !== undefined) item.sort_order = Number(body.sort_order) || 0
    return HttpResponse.json(success(getTaxonomyItems('tag', 10001).find((entry) => entry.id === item.id)))
  }),

  http.patch('/api/v1/resources/categories/:dictId', async ({ request, params }) => {
    const item = mockTaxonomies.category.find((entry) => entry.id === Number(params.dictId) && !entry.deleted)
    if (!item) return HttpResponse.json(error(404, '分类不存在'), { status: 404 })
    const body = (await request.json()) as { name?: string; color?: string; sort_order?: number }
    if (body.name?.trim()) item.name = body.name.trim()
    if (body.color !== undefined) item.color = body.color || null
    if (body.sort_order !== undefined) item.sort_order = Number(body.sort_order) || 0
    return HttpResponse.json(success(getTaxonomyItems('category', 10001).find((entry) => entry.id === item.id)))
  }),

  http.delete('/api/v1/resources/tags/:dictId', async ({ params }) => {
    const item = mockTaxonomies.tag.find((entry) => entry.id === Number(params.dictId))
    if (!item) return HttpResponse.json(error(404, '标签不存在'), { status: 404 })
    item.deleted = true
    return HttpResponse.json(success(null, '标签已删除'))
  }),

  http.delete('/api/v1/resources/categories/:dictId', async ({ params }) => {
    const item = mockTaxonomies.category.find((entry) => entry.id === Number(params.dictId))
    if (!item) return HttpResponse.json(error(404, '分类不存在'), { status: 404 })
    item.deleted = true
    return HttpResponse.json(success(null, '分类已删除'))
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
