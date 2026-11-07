/**
 * [数据交互说明]
 * - 导出: MSW 社区模块请求处理器（API-57 ~ API-74）
 * - 依赖: msw, ../data/users, ../data/community, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/community/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { mockContents, mockFavorites, mockRecentViews, getNextContentId } from '../data/community'
import { success, error, extractToken, now, getPagination, pageResult } from '../data/common'

/** 投稿存储 */
const submissions: Record<string, unknown>[] = [...mockContents]
/** 举报存储 */
const reports: Record<string, unknown>[] = []

export const communityHandlers = [
  // ========== API-73 热门榜单（本地演示） ==========
  http.get('/api/v1/community/rankings', async ({ request }) => {
    const url = new URL(request.url)
    const contentType = url.searchParams.get('content_type')
    const limit = Math.min(50, Math.max(1, Number(url.searchParams.get('limit')) || 10))
    const records = mockContents
      .filter((content) => content.status === 'published' && (!contentType || content.content_type === contentType))
      .map((content) => ({
        content,
        hot_score: content.view_count * 0.2
          + content.use_count * 4
          + mockFavorites.filter((favorite) => favorite.content_id === content.id).length * 2,
      }))
      .sort((a, b) => b.hot_score - a.hot_score)
      .slice(0, limit)
      .map((entry, index) => ({ rank: index + 1, hot_score: entry.hot_score, content: entry.content }))

    return HttpResponse.json(success(records))
  }),

  // ========== API-57 检索社区内容 ==========
  http.get('/api/v1/community/items', async ({ request }) => {
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const contentType = url.searchParams.get('content_type')
    const subject = url.searchParams.get('subject')
    const grade = url.searchParams.get('grade')
    const keyword = url.searchParams.get('keyword') || ''

    let filtered = mockContents.filter((c) => c.status === 'published')
    if (contentType) filtered = filtered.filter((c) => c.content_type === contentType)
    if (subject) filtered = filtered.filter((c) => c.subject === subject)
    if (grade) filtered = filtered.filter((c) => c.grade === grade)
    if (keyword) filtered = filtered.filter((c) => c.title.includes(keyword) || c.description.includes(keyword))

    // 按置顶和时间排序
    filtered.sort((a, b) => b.is_top - a.is_top || new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())

    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-58 获取社区内容详情 ==========
  http.get('/api/v1/community/items/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const content = mockContents.find((c) => c.id === id)
    if (!content) return HttpResponse.json(error(404, '内容不存在'), { status: 404 })
    return HttpResponse.json(success(content))
  }),

  // ========== API-59 收藏 ==========
  http.put('/api/v1/community/items/:id/favorite', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const contentId = parseInt(params.id as string, 10)
    if (!mockFavorites.find((f) => f.user_id === user.id && f.content_id === contentId)) {
      mockFavorites.push({ user_id: user.id, content_id: contentId, created_at: now() })
    }
    return HttpResponse.json(success(null, '收藏成功'))
  }),

  // ========== API-60 取消收藏 ==========
  http.delete('/api/v1/community/items/:id/favorite', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const contentId = parseInt(params.id as string, 10)
    const idx = mockFavorites.findIndex((f) => f.user_id === user.id && f.content_id === contentId)
    if (idx !== -1) mockFavorites.splice(idx, 1)
    return HttpResponse.json(success(null, '已取消收藏'))
  }),

  // ========== API-61 记录浏览事件 ==========
  http.post('/api/v1/community/items/:id/view-events', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const contentId = parseInt(params.id as string, 10)
    const content = mockContents.find((c) => c.id === contentId)
    if (content) content.view_count += 1

    const existing = mockRecentViews.find((v) => v.user_id === user.id && v.content_id === contentId)
    if (existing) {
      existing.viewed_at = now()
    } else {
      mockRecentViews.push({ user_id: user.id, content_id: contentId, viewed_at: now() })
    }
    return HttpResponse.json(success(null))
  }),

  // ========== API-62 收藏列表 ==========
  http.get('/api/v1/community/favorites', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)

    const userFavorites = mockFavorites.filter((f) => f.user_id === user.id)
    const contentIds = userFavorites.map((f) => f.content_id)
    const records = mockContents.filter((c) => contentIds.includes(c.id))

    const total = records.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(records.slice(start, start + size), total, page, size)))
  }),

  // ========== API-63 最近浏览 ==========
  http.get('/api/v1/community/recent-views', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)

    const views = mockRecentViews
      .filter((v) => v.user_id === user.id)
      .sort((a, b) => new Date(b.viewed_at).getTime() - new Date(a.viewed_at).getTime())
    const records = views.map((v) => ({
      item: mockContents.find((c) => c.id === v.content_id),
      viewed_at: v.viewed_at,
    }))

    const total = records.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(records.slice(start, start + size), total, page, size)))
  }),

  // ========== API-64 移除最近浏览 ==========
  http.delete('/api/v1/community/recent-views/:itemId', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const contentId = parseInt(params.itemId as string, 10)
    const idx = mockRecentViews.findIndex((v) => v.user_id === user.id && v.content_id === contentId)
    if (idx !== -1) mockRecentViews.splice(idx, 1)
    return HttpResponse.json(success(null))
  }),

  // ========== API-65 复用内容 ==========
  http.post('/api/v1/community/items/:id/reuse', async ({ request, params }) => {
    const body = (await request.json()) as { new_project_name?: string }
    const contentId = parseInt(params.id as string, 10)
    const content = mockContents.find((c) => c.id === contentId)
    if (!content) return HttpResponse.json(error(404, '内容不存在'), { status: 404 })

    // 增加使用计数
    content.use_count += 1

    return HttpResponse.json(success({
      id: Math.floor(Math.random() * 1000) + 100,
      project_name: body.new_project_name || `派生-${content.title}`,
      project_type: 'ppt',
      status: 'draft',
      source_content_id: contentId,
      created_at: now(),
    }))
  }),

  // ========== API-66 创建投稿 ==========
  http.post('/api/v1/community/submissions', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const submission = {
      id: getNextContentId(),
      content_type: body.content_type,
      author_id: user.id,
      title: body.title,
      description: body.description || '',
      subject: body.subject || '',
      grade: body.grade || '',
      lesson_type: body.lesson_type || '',
      content_data: body.content_data || '{}',
      input_variables: body.input_variables || '[]',
      example_effect: body.example_effect || '',
      version: 1,
      version_history: '[]',
      license: body.license,
      status: 'draft',
      is_top: 0,
      view_count: 0,
      use_count: 0,
      created_at: now(),
      updated_at: now(),
    }
    submissions.push(submission)
    return HttpResponse.json(success(submission))
  }),

  // ========== API-67 查询投稿列表 ==========
  http.get('/api/v1/community/submissions', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const statusFilter = url.searchParams.get('status')

    let filtered = submissions.filter((s) => s.author_id === user.id)
    if (statusFilter) filtered = filtered.filter((s) => s.status === statusFilter)

    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  // ========== API-68 投稿详情 ==========
  http.get('/api/v1/community/submissions/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const submission = submissions.find((s) => s.id === id)
    if (!submission) return HttpResponse.json(error(404, '投稿不存在'), { status: 404 })
    return HttpResponse.json(success(submission))
  }),

  // ========== API-69 修改投稿 ==========
  http.patch('/api/v1/community/submissions/:id', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const submission = submissions.find((s) => s.id === id)
    if (!submission) return HttpResponse.json(error(404, '投稿不存在'), { status: 404 })

    const body = (await request.json()) as Record<string, unknown>
    Object.keys(body).forEach((key) => {
      if (body[key] !== undefined && key !== 'id') (submission as Record<string, unknown>)[key] = body[key]
    })
    submission.updated_at = now()
    return HttpResponse.json(success(submission))
  }),

  // ========== API-70 保存投稿版本 ==========
  http.post('/api/v1/community/submissions/:id/versions', async ({ request, params }) => {
    const body = (await request.json()) as { description?: string }
    const id = parseInt(params.id as string, 10)
    const submission = submissions.find((s) => s.id === id)
    if (!submission) return HttpResponse.json(error(404, '投稿不存在'), { status: 404 })

    const ver = ((submission.version as number) || 0) + 1
    submission.version = ver
    return HttpResponse.json(success({ version_id: ver * 100 + id, version_number: ver }))
  }),

  // ========== API-71 提交审核 ==========
  http.post('/api/v1/community/submissions/:id/submit', async ({ request, params }) => {
    const id = parseInt(params.id as string, 10)
    const submission = submissions.find((s) => s.id === id)
    if (!submission) return HttpResponse.json(error(404, '投稿不存在'), { status: 404 })
    if (submission.status !== 'draft') {
      return HttpResponse.json(error(422, '只有草稿状态可以提交'), { status: 422 })
    }

    submission.status = 'pending'
    submission.updated_at = now()
    return HttpResponse.json(success(null, '已提交审核'))
  }),

  // ========== API-72 创建举报 ==========
  http.post('/api/v1/community/reports', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const reportId = reports.length + 1
    reports.push({
      id: reportId,
      reporter_id: user.id,
      target_type: body.target_type,
      target_id: body.target_id,
      reason: body.reason,
      description: body.description || '',
      status: 'pending',
      handler_id: null,
      result: null,
      created_at: now(),
      updated_at: now(),
    })
    return HttpResponse.json(success({ report_id: reportId }))
  }),

  // ========== API-73 举报列表 ==========
  http.get('/api/v1/community/reports', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)

    const filtered = reports.filter((r) => r.reporter_id === user.id)
    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  // ========== API-74 举报详情 ==========
  http.get('/api/v1/community/reports/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const report = reports.find((r) => r.id === id)
    if (!report) return HttpResponse.json(error(404, '举报不存在'), { status: 404 })
    return HttpResponse.json(success(report))
  }),
]
