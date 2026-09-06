/**
 * [数据交互说明]
 * - 导出: MSW 项目模块请求处理器（API-20 ~ API-35）
 * - 依赖: msw, ../data/users, ../data/projects, ../data/common
 * - 输入: 被 handlers/index.ts 聚合导出
 * - 输出: 拦截 /api/v1/projects/* 请求并返回模拟响应
 */

import { http, HttpResponse } from 'msw'
import { mockSessions } from '../data/users'
import { mockProjects, mockPages, mockVersions, getNextProjectId, getNextPageId, getNextVersionId } from '../data/projects'
import { success, error, extractToken, now, getPagination, pageResult } from '../data/common'

export const projectHandlers = [
  // ========== API-20 创建项目 ==========
  http.post('/api/v1/projects', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const body = (await request.json()) as Record<string, unknown>
    const newProject = {
      id: getNextProjectId(),
      user_id: user.id,
      project_name: body.project_name as string,
      project_type: (body.project_type as 'ppt' | 'word' | 'h5' | 'mixed') || 'ppt',
      status: (body.status as string) || 'draft',
      current_version: 1,
      snapshots: body.snapshots as string || '[]',
      edit_history: body.edit_history as string || '[]',
      permissions: body.permissions as string || '[]',
      created_at: now(),
      updated_at: now(),
      deleted_at: null,
    }
    mockProjects.push(newProject)
    return HttpResponse.json(success(newProject))
  }),

  // ========== API-21 分页查询项目 ==========
  http.get('/api/v1/projects', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)
    const keyword = url.searchParams.get('keyword') || ''
    const projectType = url.searchParams.get('project_type')
    const status = url.searchParams.get('status')

    // 筛选当前用户有权限的项目（拥有者或被授权者）
    let filtered = mockProjects.filter((p) => {
      if (p.deleted_at) return false
      if (p.user_id !== user.id) {
        const permissions = JSON.parse(p.permissions || '[]') as number[]
        if (!permissions.includes(user.id)) return false
      }
      if (keyword && !p.project_name.includes(keyword)) return false
      if (projectType && p.project_type !== projectType) return false
      if (status && p.status !== status) return false
      return true
    })

    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-22 获取项目详情 ==========
  http.get('/api/v1/projects/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })

    // 权限校验
    const perms = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !perms.includes(user.id)) {
      return HttpResponse.json(error(403, '无权访问该项目'), { status: 403 })
    }

    const pages = mockPages.filter((pg) => pg.project_id === projectId)
    return HttpResponse.json(success({ ...project, pages }))
  }),

  // ========== 页面级 API：API-19A ~ API-19F ==========
  http.get('/api/v1/projects/:id/pages', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) return HttpResponse.json(error(403, '无权访问该项目'), { status: 403 })
    return HttpResponse.json(success(mockPages.filter((page) => page.project_id === projectId).sort((a, b) => a.page_order - b.page_order)))
  }),

  http.get('/api/v1/projects/:id/pages/:pageId', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) return HttpResponse.json(error(403, '无权访问该项目'), { status: 403 })
    const page = mockPages.find((item) => item.project_id === projectId && item.id === parseInt(params.pageId as string, 10))
    if (!page) return HttpResponse.json(error(404, '页面不存在'), { status: 404 })
    return HttpResponse.json(success(page))
  }),

  http.post('/api/v1/projects/:id/pages', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) return HttpResponse.json(error(403, '无权修改该项目'), { status: 403 })
    const body = (await request.json()) as Record<string, unknown>
    const page = {
      id: getNextPageId(), project_id: projectId,
      page_order: Number(body.page_order || mockPages.filter((item) => item.project_id === projectId).length + 1),
      page_type: (body.page_type as string) || 'content', page_title: (body.page_title as string) || '',
      page_content: (body.page_content as string) || '{}', components: (body.components as string) || '[]',
      page_version: 1, client_version: body.client_version as string | undefined,
      autosave: Boolean(body.autosave), dirty: Boolean(body.dirty), last_saved_at: now(),
      created_at: now(), updated_at: now(),
    }
    mockPages.push(page)
    project.current_version += 1
    project.updated_at = now()
    return HttpResponse.json(success(page))
  }),

  http.put('/api/v1/projects/:id/pages/:pageId', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) return HttpResponse.json(error(403, '无权修改该项目'), { status: 403 })
    const page = mockPages.find((item) => item.project_id === projectId && item.id === parseInt(params.pageId as string, 10))
    if (!page) return HttpResponse.json(error(404, '页面不存在'), { status: 404 })
    const body = (await request.json()) as Record<string, unknown>
    const expectedVersion = Number(body.expected_page_version)
    if (!expectedVersion || expectedVersion !== (page.page_version || 1)) return HttpResponse.json(error(400, 'Version conflict, please refresh and retry'))
    if (body.page_order !== undefined) page.page_order = Number(body.page_order)
    if (body.page_type) page.page_type = body.page_type as string
    if (body.page_title !== undefined) page.page_title = body.page_title as string
    if (body.page_content !== undefined) page.page_content = body.page_content as string
    if (body.components !== undefined) page.components = body.components as string
    page.page_version = (page.page_version || 1) + 1
    page.client_version = body.client_version as string | undefined
    page.autosave = Boolean(body.autosave)
    page.dirty = Boolean(body.dirty)
    page.last_saved_at = now()
    page.updated_at = now()
    project.current_version += 1
    project.updated_at = now()
    return HttpResponse.json(success(page))
  }),

  http.post('/api/v1/projects/:id/pages/batch-save', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) return HttpResponse.json(error(403, '无权修改该项目'), { status: 403 })
    const body = (await request.json()) as { pages?: Array<Record<string, unknown>>, client_version?: string, autosave?: boolean }
    if (!Array.isArray(body.pages) || !body.pages.length) return HttpResponse.json(error(400, 'pages cannot be empty'))
    const saved = []
    for (const pageBody of body.pages) {
      const pageId = Number(pageBody.page_id)
      const page = pageId ? mockPages.find((item) => item.project_id === projectId && item.id === pageId) : null
      if (page) {
        const expectedVersion = Number(pageBody.expected_page_version)
        if (!expectedVersion || expectedVersion !== (page.page_version || 1)) return HttpResponse.json(error(400, 'Version conflict, please refresh and retry'))
        page.page_order = Number(pageBody.page_order || page.page_order)
        page.page_type = (pageBody.page_type as string) || page.page_type
        page.page_title = (pageBody.page_title as string) ?? page.page_title
        page.page_content = (pageBody.page_content as string) ?? page.page_content
        page.components = (pageBody.components as string) ?? page.components
        page.page_version = (page.page_version || 1) + 1
        page.client_version = (pageBody.client_version as string) || body.client_version
        page.autosave = Boolean(pageBody.autosave ?? body.autosave)
        page.dirty = Boolean(pageBody.dirty)
        page.last_saved_at = now()
        page.updated_at = now()
        saved.push(page)
        continue
      }
      const created = {
        id: getNextPageId(), project_id: projectId,
        page_order: Number(pageBody.page_order || mockPages.filter((item) => item.project_id === projectId).length + 1),
        page_type: (pageBody.page_type as string) || 'content', page_title: (pageBody.page_title as string) || '',
        page_content: (pageBody.page_content as string) || '{}', components: (pageBody.components as string) || '[]',
        page_version: 1, client_version: (pageBody.client_version as string) || body.client_version,
        autosave: Boolean(pageBody.autosave ?? body.autosave), dirty: Boolean(pageBody.dirty), last_saved_at: now(),
        created_at: now(), updated_at: now(),
      }
      mockPages.push(created)
      saved.push(created)
    }
    project.current_version += saved.length
    project.updated_at = now()
    return HttpResponse.json(success(saved))
  }),

  http.delete('/api/v1/projects/:id/pages/:pageId', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((item) => item.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    if (project.user_id !== user.id) return HttpResponse.json(error(403, '无权修改该项目'), { status: 403 })
    const index = mockPages.findIndex((item) => item.project_id === projectId && item.id === parseInt(params.pageId as string, 10))
    if (index < 0) return HttpResponse.json(error(404, '页面不存在'), { status: 404 })
    mockPages.splice(index, 1)
    project.current_version += 1
    project.updated_at = now()
    return HttpResponse.json(success(null, '页面已删除'))
  }),

  http.post('/api/v1/projects/tools/validate-component', async ({ request }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })
    const body = (await request.json()) as Record<string, unknown>
    const type = String(body.type || '')
    const data = (body.data || {}) as Record<string, unknown>
    const errors: string[] = []
    if (type === 'math_formula' && !String(data.latex || '').trim()) errors.push('latex 不能为空')
    if (type === 'chart' && !data.option) errors.push('data.option 不能为空')
    if (type === 'table' && data.rows === undefined && data.columns === undefined) errors.push('需要 rows 或 columns')
    return HttpResponse.json(success({ valid: errors.length === 0, normalized: body, render_hint: {}, errors, warnings: [] }))
  }),

  // ========== API-23 修改项目 ==========
  http.patch('/api/v1/projects/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })

    if (project.user_id !== user.id) {
      const perms = JSON.parse(project.permissions || '[]') as number[]
      if (!perms.includes(user.id)) return HttpResponse.json(error(403, '无权修改该项目'), { status: 403 })
    }

    const body = (await request.json()) as Record<string, unknown>
    // 乐观锁校验
    if (body.current_version !== undefined && (body.current_version as number) !== project.current_version) {
      return HttpResponse.json(error(409, '版本冲突，项目已被他人修改'), { status: 409 })
    }

    if (body.project_name) project.project_name = body.project_name as string
    if (body.project_type) project.project_type = body.project_type as 'ppt' | 'word' | 'h5' | 'mixed'
    if (body.status) project.status = body.status as string
    if (body.permissions) project.permissions = body.permissions as string
    if (body.edit_history !== undefined) project.edit_history = body.edit_history as string
    if (body.snapshots !== undefined) project.snapshots = body.snapshots as string
    project.current_version += 1
    project.updated_at = now()

    return HttpResponse.json(success(project))
  }),

  // ========== API-24 复制项目 ==========
  http.post('/api/v1/projects/:id/copies', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const source = mockProjects.find((p) => p.id === projectId)
    if (!source) return HttpResponse.json(error(404, '源项目不存在'), { status: 404 })

    const body = (await request.json()) as { new_name?: string }
    const copy = {
      id: getNextProjectId(),
      user_id: user.id,
      project_name: body.new_name || `${source.project_name} - 副本`,
      project_type: source.project_type,
      status: 'draft' as const,
      current_version: 1,
      snapshots: '[]',
      edit_history: '[]',
      permissions: '[]',
      created_at: now(),
      updated_at: now(),
      deleted_at: null,
    }
    mockProjects.push(copy)
    return HttpResponse.json(success(copy))
  }),

  // ========== API-25 归档项目 ==========
  http.post('/api/v1/projects/:id/archive', async ({ params }) => {
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    project.status = 'archived'
    project.updated_at = now()
    return HttpResponse.json(success(project))
  }),

  // ========== API-26 恢复项目 ==========
  http.post('/api/v1/projects/:id/restore', async ({ params }) => {
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    project.status = 'draft'
    project.updated_at = now()
    return HttpResponse.json(success(project))
  }),

  // ========== API-27 软删除项目 ==========
  http.delete('/api/v1/projects/:id', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    if (project.user_id !== user.id) return HttpResponse.json(error(403, '无权删除该项目'), { status: 403 })

    project.deleted_at = now()
    project.updated_at = now()
    return HttpResponse.json(success(null, '项目已删除'))
  }),

  // ========== API-28 AI 修改页面/组件 ==========
  http.post('/api/v1/projects/:id/ai-revisions', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const context = (() => {
      try {
        return typeof body.context === 'string' ? JSON.parse(body.context) : body.context
      } catch {
        return {}
      }
    })() as Record<string, unknown>
    const contextObject = context && typeof context === 'object' ? context : {}
    const sourcePage = (contextObject.page && typeof contextObject.page === 'object' ? contextObject.page : contextObject) as Record<string, unknown>
    const instruction = String(body.instruction || '').trim()
    const sourceElements = sourcePage.elements ?? sourcePage.components ?? []
    const elements = typeof sourceElements === 'string'
      ? (() => { try { return JSON.parse(sourceElements) } catch { return [] } })()
      : sourceElements
    const nextPage = {
      ...sourcePage,
      description: instruction ? `已根据“${instruction}”生成可编辑页面内容。` : sourcePage.description,
      elements: Array.isArray(elements) ? elements : [],
    }
    return HttpResponse.json(success({
      id: Number(body.target_id) || sourcePage.componentId || sourcePage.id || 1,
      page_id: Number(body.target_id) || sourcePage.componentId || sourcePage.id || 1,
      page_title: nextPage.title || 'AI 修改页面',
      page_content: JSON.stringify(nextPage),
      components: JSON.stringify(nextPage.elements),
    }))
  }),

  // ========== API-29 插入组件/页面 ==========
  http.post('/api/v1/projects/:id/components', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const newPage = {
      id: getNextPageId(),
      project_id: parseInt((body as Record<string, string>).project_id || '0', 10),
      page_order: body.page_order as number,
      page_type: body.page_type as string,
      page_title: (body.page_title as string) || '',
      page_content: (body.page_content as string) || '{}',
      components: (body.components as string) || '[]',
      created_at: now(),
      updated_at: now(),
    }
    mockPages.push(newPage)
    return HttpResponse.json(success(newPage))
  }),

  // ========== API-30 修改组件 ==========
  http.patch('/api/v1/projects/:id/components/:componentId', async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>
    const projectId = parseInt(params.id as string, 10)
    const componentId = String(params.componentId || '')
    const numericPageId = Number(componentId)
    let page = Number.isInteger(numericPageId)
      ? mockPages.find((p) => p.project_id === projectId && p.id === numericPageId)
      : undefined
    if (!page) {
      page = mockPages.find((candidate) => {
        if (candidate.project_id !== projectId) return false
        try {
          const content = JSON.parse(candidate.page_content || '{}') as Record<string, unknown>
          const elements = content.elements ?? content.components
          return Array.isArray(elements) && elements.some((element) => String((element as Record<string, unknown>)?.id || (element as Record<string, unknown>)?.component_id || '') === componentId)
        } catch {
          return false
        }
      })
    }
    if (!page) return HttpResponse.json(error(404, '页面不存在'), { status: 404 })

    if (body.page_order !== undefined) page.page_order = body.page_order as number
    if (body.page_type) page.page_type = body.page_type as string
    if (body.page_title) page.page_title = body.page_title as string
    if (body.page_content) page.page_content = body.page_content as string
    if (body.components) page.components = body.components as string
    page.updated_at = now()

    return HttpResponse.json(success(page))
  }),

  // ========== API-31 保存版本 ==========
  http.post('/api/v1/projects/:id/versions', async ({ request, params }) => {
    const body = (await request.json()) as { description?: string }
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })
    const permissions = JSON.parse(project.permissions || '[]') as number[]
    if (project.user_id !== user.id && !permissions.includes(user.id)) {
      return HttpResponse.json(error(403, '无权为该项目创建快照'), { status: 403 })
    }

    project.current_version += 1
    project.updated_at = now()
    // 版本内容必须和后续编辑隔离；导出服务只读取这个不可变副本。
    const snapshot = {
      project: JSON.parse(JSON.stringify(project)),
      pages: mockPages
        .filter((page) => page.project_id === projectId)
        .sort((a, b) => a.page_order - b.page_order)
        .map((page) => JSON.parse(JSON.stringify(page))),
    }
    const newVersion = {
      version_id: getNextVersionId(),
      project_id: projectId,
      version_number: project.current_version,
      description: body.description || '',
      snapshot_data: JSON.stringify(snapshot),
      created_by: project.user_id,
      created_at: now(),
    }
    mockVersions.push(newVersion)

    return HttpResponse.json(success({
      version_id: newVersion.version_id,
      version_number: newVersion.version_number,
    }))
  }),

  // ========== API-32 查询版本列表 ==========
  http.get('/api/v1/projects/:id/versions', async ({ request, params }) => {
    const projectId = parseInt(params.id as string, 10)
    const url = new URL(request.url)
    const { page, size } = getPagination(url.searchParams)

    const filtered = mockVersions.filter((v) => v.project_id === projectId)
    const total = filtered.length
    const start = (page - 1) * size
    const records = filtered.slice(start, start + size)

    return HttpResponse.json(success(pageResult(records, total, page, size)))
  }),

  // ========== API-33 版本差异比较 ==========
  http.get('/api/v1/projects/:id/versions/:versionId/diff', async () => {
    return HttpResponse.json(success({
      differences: [
        { path: '/project_name', type: 'modified', old: '光合作用课件', new: '光合作用课件-v2' },
        { path: '/pages/0/title', type: 'modified', old: '旧标题', new: '新标题' },
      ],
      summary: '共 2 处变更：1 处属性修改，1 处页面修改',
    }))
  }),

  // ========== API-34 恢复版本 ==========
  http.post('/api/v1/projects/:id/versions/:versionId/restore', async ({ params }) => {
    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })

    project.current_version += 1
    project.updated_at = now()
    return HttpResponse.json(success(project))
  }),

  // ========== API-35 添加项目授权用户 ==========
  http.post('/api/v1/projects/:id/permissions', async ({ request, params }) => {
    const token = extractToken(request.headers.get('Authorization'))
    const user = mockSessions.get(token || '')
    if (!user) return HttpResponse.json(error(401, '请先登录'), { status: 401 })

    const projectId = parseInt(params.id as string, 10)
    const project = mockProjects.find((p) => p.id === projectId)
    if (!project) return HttpResponse.json(error(404, '项目不存在'), { status: 404 })

    if (project.user_id !== user.id) {
      return HttpResponse.json(error(403, '仅项目创建者可以授权'), { status: 403 })
    }

    const body = (await request.json()) as { user_id: number }
    const perms = JSON.parse(project.permissions || '[]') as number[]
    if (!perms.includes(body.user_id)) {
      perms.push(body.user_id)
      project.permissions = JSON.stringify(perms)
    }
    project.updated_at = now()

    return HttpResponse.json(success(project))
  }),
]
