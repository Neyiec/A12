/**
 * [数据交互说明]
 * - 导出: MSW 成果导出中心请求处理器（API-47 ~ API-56）
 * - 依赖: msw, ../data/users, ../data/projects, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 与前端页面一致的项目预检、任务状态、质量报告、预览和下载链路
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { mockProjects, mockVersions } from '../data/projects'
import { success, error, extractToken, now, getPagination, pageResult } from '../data/common'

interface ExportTask {
  id: number
  user_id: number
  project_id: number
  project_name: string
  subject?: string
  page_count?: number
  snapshot_version: number
  export_type: string
  test_case_id?: string
  status: 'queued' | 'generating' | 'checking' | 'success' | 'partial' | 'failed' | 'cancelled'
  config: string
  file_name: string | null
  file_url: string | null
  file_size: number | null
  download_url: string | null
  preview_url: string | null
  url_expire_at: string | null
  file_status: string | null
  quality_report: string | null
  error_msg: string | null
  progress: number
  retry_count: number
  worker_id: string | null
  started_at: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface ExportSnapshot {
  project: { id: number; project_name: string; current_version: number }
  pages: Array<{ page_order: number; page_title: string }>
}

/** 导出任务内存存储，浏览器刷新后会随 mock worker 一起重新开始。 */
const exportTasks: ExportTask[] = []

const getUser = (request: Request) => {
  const token = extractToken(request.headers.get('Authorization'))
  return mockSessions.get(token || '')
}

const getProject = (projectId: unknown) => mockProjects.find((item) => item.id === Number(projectId))
const supportedExportTypes = ['pptx', 'word', 'package']
const isTestTask = (task: Partial<ExportTask> | Record<string, unknown>) => task.test_case_id === 'pythagorean-lab'

const parseConfig = (value: unknown) => {
  try {
    return typeof value === 'string' ? JSON.parse(value) : value || {}
  } catch {
    return {}
  }
}

const getSnapshot = (projectId: number, version: number): ExportSnapshot | null => {
  const record = mockVersions.find((item) => item.project_id === projectId && item.version_number === version)
  if (!record) return null
  try {
    const parsed = JSON.parse(record.snapshot_data) as ExportSnapshot
    return parsed?.project && Array.isArray(parsed.pages) ? parsed : null
  } catch {
    return null
  }
}

const precheckKeys = new Map<string, { requiresConfirmation: boolean }>()
const precheckKey = (userId: number, projectId: number, snapshotVersion: number, exportType: string) => `${userId}:${projectId}:${snapshotVersion}:${exportType}`

const escapeHtml = (value: unknown) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character] || character))
const buildArtifactContent = (task: ExportTask) => {
  const snapshot = getSnapshot(task.project_id, task.snapshot_version)
  const pages = snapshot?.pages || []
  const pageSections = pages.length
    ? pages.map((page, index) => `<section class="lesson-section"><span>${String(index + 1).padStart(2, '0')}</span><h2>${escapeHtml(page.page_title)}</h2><p>页面内容来自项目组件接口，导出服务已完成结构化转换。</p></section>`).join('')
    : '<section class="lesson-section"><span>01</span><h2>暂无页面</h2><p>项目尚未保存页面内容。</p></section>'
  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(task.project_name)}</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f8fc;color:#172033;font-family:"Microsoft YaHei","Segoe UI",sans-serif}.deck{width:min(960px,calc(100% - 40px));margin:40px auto 72px}.cover,.lesson-section{padding:42px;border:1px solid #dbe6f4;border-radius:18px;background:#fff;box-shadow:0 12px 30px rgba(40,75,120,.08)}.cover{color:#fff;background:#2563eb}.cover small{opacity:.78;letter-spacing:.08em}.cover h1{margin:14px 0 8px;font-size:40px;line-height:1.2}.cover p{margin:0;opacity:.82}.lesson-section{margin-top:16px}.lesson-section span{color:#2563eb;font-weight:700;letter-spacing:.08em}.lesson-section h2{margin:12px 0 8px;font-size:24px}.lesson-section p{margin:0;color:#63748c;line-height:1.8}</style></head><body><main class="deck"><section class="cover"><small>${escapeHtml(task.subject || '教学成果')} · 快照 v${task.snapshot_version}</small><h1>${escapeHtml(task.project_name)}</h1><p>本地 mock 依据不可变项目快照生成的预览内容</p></section>${pageSections}</main></body></html>`
}

const buildArtifact = (task: ExportTask) => {
  const content = buildArtifactContent(task)
  const dataUrl = `data:text/html;charset=utf-8,${encodeURIComponent(content)}`
  const extension = ({ pptx: 'pptx', word: 'docx', package: 'zip' } as Record<string, string>)[task.export_type] || 'zip'
  const fileName = `export_${task.id}.${extension}`
  return { content, dataUrl, fileName, fileSize: content.length }
}

const qualityReport = (task: ExportTask) => JSON.stringify({
  overall: 'good',
  ...(isTestTask(task) ? {
    测试标识: '社区全流程测试案例',
    校验结论: '通过',
    总分: 96,
    检查项: [
      { 名称: '不可变项目快照已绑定', 结果: '通过', 说明: `使用快照 v${task.snapshot_version}，后续编辑不会覆盖本次成果。` },
      { 名称: '项目页面结构完整', 结果: '通过' },
      { 名称: '素材授权有效', 结果: '通过' },
      { 名称: '互动组件可兼容', 结果: '通过' },
      { 名称: '导出文件可读取', 结果: '通过' },
    ],
  } : {
    warnings: [{ type: 'resolution', detail: '第3页图片分辨率低于720p' }],
    degraded: [],
  }),
})

const completeTask = (task: ExportTask) => {
  if (task.status === 'cancelled') return
  const artifact = buildArtifact(task)
  task.status = 'success'
  task.progress = 100
  task.file_name = artifact.fileName
  task.file_url = artifact.dataUrl
  task.file_size = artifact.fileSize
  task.download_url = artifact.dataUrl
  task.preview_url = artifact.dataUrl
  task.url_expire_at = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
  task.file_status = 'available'
  task.quality_report = qualityReport(task)
  task.completed_at = new Date().toISOString()
  task.updated_at = now()
}

/** 模拟生成服务的阶段推进，前端必须轮询任务详情才能看到这些状态。 */
const scheduleTaskLifecycle = (task: ExportTask) => {
  const phases: Array<[number, ExportTask['status'], number]> = [
    [280, 'generating', 24],
    [760, 'generating', 56],
    [1240, 'checking', 82],
    [1850, 'success', 100],
  ]
  phases.forEach(([delay, status, progress]) => {
    setTimeout(() => {
      if (task.status === 'cancelled' || task.status === 'failed') return
      task.status = status
      task.progress = progress
      task.started_at ||= new Date().toISOString()
      task.updated_at = now()
      if (status === 'success') completeTask(task)
    }, delay)
  })
}

export const exportHandlers = [
  // ========== API-47 导出预检 ==========
  http.post('/api/v1/projects/:id/export-prechecks', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const project = getProject(params.id)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })

    const body = (await request.json()) as Record<string, unknown>
    const snapshotVersion = Number(body.snapshot_version)
    const exportType = String(body.export_type || '')
    const snapshot = getSnapshot(project.id, snapshotVersion)
    const config = parseConfig(body.config) as Record<string, unknown>
    const errors = [
      ...(supportedExportTypes.includes(exportType) ? [] : [{ type: 'error', message: '导出类型仅支持 PPTX、Word 或成果包' }]),
      ...(snapshot ? [] : [{ type: 'error', message: `未找到项目快照 v${snapshotVersion}，请先保存不可变版本后再导出` }]),
      ...(body.force_fail === true ? [{ type: 'error', message: '导出预检被测试参数阻断' }] : []),
    ]
    const warnings = snapshot && config.interaction_mode === 'static'
      ? [{ type: 'warning', message: '互动内容将以静态截图方式导出，交互能力会降级。' }]
      : []
    const passed = errors.length === 0
    if (passed) precheckKeys.set(precheckKey(user.id, project.id, snapshotVersion, exportType), { requiresConfirmation: warnings.length > 0 })
    return HttpResponse.json(success({
      passed,
      warnings,
      errors,
      requires_confirmation: warnings.length > 0,
      snapshot_version: snapshotVersion,
      export_type: exportType,
      project_id: project.id,
      checked_at: now(),
    }))
  }),

  // ========== API-48 创建导出任务 ==========
  http.post('/api/v1/export-tasks', async ({ request }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const project = getProject(body.project_id)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    if (project.user_id !== user.id) return HttpResponse.json(error(403, '无权导出该项目'), { status: 403 })
    const snapshotVersion = Number(body.snapshot_version)
    const exportType = String(body.export_type || '')
    const snapshot = getSnapshot(project.id, snapshotVersion)
    if (!supportedExportTypes.includes(exportType)) return HttpResponse.json(error(422, '导出类型仅支持 PPTX、Word 或成果包'), { status: 422 })
    if (!snapshot) return HttpResponse.json(error(422, '必须绑定已保存的不可变项目快照'), { status: 422 })
    const result = precheckKeys.get(precheckKey(user.id, project.id, snapshotVersion, exportType))
    if (!result) return HttpResponse.json(error(422, '请先完成导出预检'), { status: 422 })
    if (result.requiresConfirmation && body.precheck_confirmed !== true) return HttpResponse.json(error(422, '预检存在警告，请经教师确认后继续'), { status: 422 })

    const task: ExportTask = {
      id: exportTasks.length + 1,
      user_id: user.id,
      project_id: project.id,
      project_name: snapshot.project.project_name,
      subject: body.subject as string | undefined,
      page_count: snapshot.pages.length,
      snapshot_version: snapshotVersion,
      export_type: exportType,
      test_case_id: body.test_case_id as string | undefined,
      status: 'queued',
      config: typeof body.config === 'string' ? body.config : JSON.stringify(body.config || {}),
      file_name: null,
      file_url: null,
      file_size: null,
      download_url: null,
      preview_url: null,
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
    scheduleTaskLifecycle(task)
    return HttpResponse.json(success(task))
  }),

  // ========== API-49 分页查询导出任务 ==========
  http.get('/api/v1/export-tasks', async ({ request }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const statusFilter = url.searchParams.get('status')
    const exportType = url.searchParams.get('export_type')
    let filtered = exportTasks.filter((task) => task.user_id === user.id)
    if (statusFilter) filtered = filtered.filter((task) => task.status === statusFilter)
    if (exportType) filtered = filtered.filter((task) => task.export_type === exportType)
    const total = filtered.length
    const start = (page - 1) * size
    return HttpResponse.json(success(pageResult(filtered.slice(start, start + size), total, page, size)))
  }),

  // ========== API-50 查看导出任务 ==========
  http.get('/api/v1/export-tasks/:id', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    return HttpResponse.json(success(task))
  }),

  // ========== API-51 取消导出任务 ==========
  http.post('/api/v1/export-tasks/:id/cancel', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    if (!['queued', 'generating', 'checking'].includes(task.status)) return HttpResponse.json(error(422, '当前状态不允许取消'), { status: 422 })
    task.status = 'cancelled'
    task.updated_at = now()
    return HttpResponse.json(success(task))
  }),

  // ========== API-52 重试导出 ==========
  http.post('/api/v1/export-tasks/:id/retry', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    task.status = 'queued'
    task.progress = 0
    task.error_msg = null
    task.completed_at = null
    task.retry_count += 1
    task.updated_at = now()
    scheduleTaskLifecycle(task)
    return HttpResponse.json(success(task))
  }),

  // ========== API-53 导出质量报告 ==========
  http.get('/api/v1/export-tasks/:id/quality-report', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '导出任务不存在'), { status: 404 })
    return HttpResponse.json(success({ quality_report: task.quality_report || qualityReport(task) }))
  }),

  // ========== API-54 成果文件元数据 ==========
  http.get('/api/v1/export-artifacts/:id', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '成果文件不存在'), { status: 404 })
    return HttpResponse.json(success({ ...task, thumbnails: [], preview_type: 'html', is_mock: true, export_format: task.export_type }))
  }),

  // ========== API-55 成果预览链接 ==========
  http.post('/api/v1/export-artifacts/:id/preview-url', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '成果文件不存在'), { status: 404 })
    if (!task.preview_url) return HttpResponse.json(error(422, '成果尚未生成完成'), { status: 422 })
    return HttpResponse.json(success({ preview_url: task.preview_url, expires_at: task.url_expire_at }))
  }),

  // ========== API-56 成果下载链接 ==========
  http.post('/api/v1/export-artifacts/:id/download-url', async ({ request, params }) => {
    const user = getUser(request)
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const id = parseInt(params.id as string, 10)
    const task = exportTasks.find((item) => item.id === id && item.user_id === user.id)
    if (!task) return HttpResponse.json(error(404, '成果文件不存在'), { status: 404 })
    if (!task.download_url) return HttpResponse.json(error(422, '成果尚未生成完成'), { status: 422 })
    return HttpResponse.json(success({ download_url: task.download_url, expires_at: task.url_expire_at }))
  }),
]
