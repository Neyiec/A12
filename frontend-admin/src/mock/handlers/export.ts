/**
 * [数据交互说明]
 * - 导出: MSW 成果导出中心请求处理器（API-47 ~ API-56）
 * - 依赖: msw, ../data/users, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/export-* 和 /api/v1/projects/:id/export-* 请求
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { success, error, extractToken, now, getPagination, pageResult, generateId } from '../data/common'

/** 导出任务内存存储 */
const exportTasks: Record<string, unknown>[] = []

export const exportHandlers = [
  // ========== API-47 导出预检 ==========
  http.post('/api/v1/projects/:id/export-prechecks', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    // 模拟预检通过
    const passed = Math.random() > 0.1
    return HttpResponse.json(success({
      passed,
      warnings: passed ? [{ type: 'notice', message: '部分图片分辨率较低，建议替换' }] : [],
      errors: passed ? [] : [{ type: 'error', message: '项目快照版本不匹配' }],
      snapshot_version: body.snapshot_version,
      export_type: body.export_type,
    }))
  }),

  // ========== API-48 创建导出任务 ==========
  http.post('/api/v1/export-tasks', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const task = {
      id: exportTasks.length + 1,
      user_id: user.id,
      project_id: body.project_id,
      snapshot_version: body.snapshot_version,
      export_type: body.export_type,
      status: 'queued',
      config: body.config || '{}',
      file_name: null,
      file_url: null,
      file_size: null,
      download_url: null,
      url_expire_at: null,
      file_status: null,
      quality_report: null,
      error_msg: null,
      progress: 0,
      retry_count: 0,
      worker_id: null,
      started_at: null,
      created_at: now(),
      updated_at: now(),
      completed_at: null,
    }
    exportTasks.push(task)

    // 模拟异步导出：2秒后自动完成
    setTimeout(() => {
      task.status = 'success'
      task.progress = 100
      task.file_name = `export_${task.id}.${body.export_type === 'pptx' ? 'pptx' : body.export_type === 'word' ? 'docx' : 'zip'}`
      task.file_url = `https://oss.example.com/exports/${task.file_name}`
      task.file_size = 1024000
      task.download_url = `${task.file_url}?token=mock_${Date.now()}`
      task.url_expire_at = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      task.file_status = 'available'
      task.completed_at = new Date().toISOString()
      task.updated_at = new Date().toISOString()
    }, 2000)

    return HttpResponse.json(success(task))
  }),

  // ========== API-49 分页查询导出任务 ==========
  http.get('/api/v1/export-tasks', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const statusFilter = url.searchParams.get('status')
    const exportType = url.searchParams.get('export_type')

    let filtered = exportTasks.filter((t) => t.user_id === user.id)
    if (statusFilter) filtered = filtered.filter((t) => t.status === statusFilter)
    if (exportType) filtered = filtered.filter((t) => t.export_type === exportType)

    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-50 查看导出任务 ==========
  http.get('/api/v1/export-tasks/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    return HttpResponse.json(success(task))
  }),

  // ========== API-51 取消导出任务 ==========
  http.post('/api/v1/export-tasks/:id/cancel', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    if (task.status !== 'queued' && task.status !== 'generating') {
      return HttpResponse.json(error(422, '当前状态不允许取消'), { status: 422 })
    }
    task.status = 'cancelled'
    task.updated_at = now()
    return HttpResponse.json(success(task))
  }),

  // ========== API-52 重试导出 ==========
  http.post('/api/v1/export-tasks/:id/retry', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })

    task.status = 'queued'
    task.progress = 0
    task.retry_count = ((task.retry_count as number) || 0) + 1
    task.updated_at = now()

    // 模拟异步重试
    setTimeout(() => {
      task.status = 'success'
      task.progress = 100
      task.completed_at = new Date().toISOString()
    }, 2000)

    return HttpResponse.json(success(task))
  }),

  // ========== API-53 导出质量报告 ==========
  http.get('/api/v1/export-tasks/:id/quality-report', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })

    return HttpResponse.json(success({
      quality_report: JSON.stringify({
        overall: 'good',
        warnings: [{ type: 'resolution', detail: '第3页图片分辨率低于720p' }],
        degraded: [],
      }),
    }))
  }),

  // ========== API-54 成果文件元数据 ==========
  http.get('/api/v1/export-artifacts/:id', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '成果文件不存在'), { status: 404 })
    return HttpResponse.json(success({ ...task, thumbnails: [], preview_type: 'pptx' }))
  }),

  // ========== API-55 成果预览链接 ==========
  http.post('/api/v1/export-artifacts/:id/preview-url', async () => {
    const expiresAt = new Date(Date.now() + 30 * 60 * 1000).toISOString()
    return HttpResponse.json(success({
      preview_url: `https://oss.example.com/preview/${generateId()}?token=mock_${Date.now()}`,
      expires_at: expiresAt,
    }))
  }),

  // ========== API-56 成果下载链接 ==========
  http.post('/api/v1/export-artifacts/:id/download-url', async ({ params }) => {
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((t) => t.id === id)
    if (!task) return HttpResponse.json(error(404, '成果文件不存在'), { status: 404 })

    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString()
    return HttpResponse.json(success({
      download_url: `${task.file_url || 'https://oss.example.com/exports/unknown'}?token=mock_${Date.now()}`,
      expires_at: expiresAt,
    }))
  }),
]
