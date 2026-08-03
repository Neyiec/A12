/**
 * [数据交互说明]
 * - 导出: 模拟项目数据、页面数据、版本数据
 * - 依赖: `./common.ts` 的 `now`、`timeOffset`、`generateId`
 * - 输入: 被 project.ts handler 引用
 * - 输出: ProjectVO、PageVO、VersionVO 列表
 */

import { now, timeOffset, generateId } from './common'

export interface MockProject {
  id: number
  user_id: number
  project_name: string
  project_type: 'ppt' | 'word' | 'h5' | 'mixed'
  status: 'draft' | 'editing' | 'confirmed' | 'exported' | 'archived'
  current_version: number
  snapshots: string
  edit_history: string
  permissions: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface MockPage {
  id: number
  project_id: number
  page_order: number
  page_type: 'cover' | 'toc' | 'content' | 'summary'
  page_title: string
  page_content: string
  components: string
  created_at: string
  updated_at: string
}

export interface MockVersion {
  version_id: number
  project_id: number
  version_number: number
  description: string
  snapshot_data: string
  created_by: number
  created_at: string
}

/** 模拟项目 */
export const mockProjects: MockProject[] = [
  {
    id: 1, user_id: 10001, project_name: '光合作用课件', project_type: 'ppt',
    status: 'editing', current_version: 3, snapshots: '[]', edit_history: '[]',
    permissions: JSON.stringify([10002]), created_at: timeOffset(-30), updated_at: timeOffset(-2), deleted_at: null,
  },
  {
    id: 2, user_id: 10001, project_name: '三角函数教案', project_type: 'word',
    status: 'confirmed', current_version: 5, snapshots: '[]', edit_history: '[]',
    permissions: '[]', created_at: timeOffset(-60), updated_at: timeOffset(-7), deleted_at: null,
  },
  {
    id: 3, user_id: 10002, project_name: '英语时态复习H5', project_type: 'h5',
    status: 'draft', current_version: 1, snapshots: '[]', edit_history: '[]',
    permissions: '[]', created_at: timeOffset(-10), updated_at: timeOffset(-5), deleted_at: null,
  },
  {
    id: 4, user_id: 10001, project_name: '初中化学元素周期表', project_type: 'ppt',
    status: 'exported', current_version: 4, snapshots: '[]', edit_history: '[]',
    permissions: '[]', created_at: timeOffset(-90), updated_at: timeOffset(-14), deleted_at: null,
  },
  {
    id: 5, user_id: 10002, project_name: '语文古诗词鉴赏', project_type: 'mixed',
    status: 'archived', current_version: 2, snapshots: '[]', edit_history: '[]',
    permissions: JSON.stringify([10001]), created_at: timeOffset(-120), updated_at: timeOffset(-60), deleted_at: null,
  },
]

/** 模拟页面 */
export const mockPages: MockPage[] = [
  { id: 1, project_id: 1, page_order: 1, page_type: 'cover', page_title: '封面', page_content: '{}', components: '[]', created_at: timeOffset(-30), updated_at: timeOffset(-2) },
  { id: 2, project_id: 1, page_order: 2, page_type: 'toc', page_title: '目录', page_content: '{}', components: '[]', created_at: timeOffset(-30), updated_at: timeOffset(-2) },
  { id: 3, project_id: 1, page_order: 3, page_type: 'content', page_title: '光合作用原理', page_content: '{}', components: '[]', created_at: timeOffset(-30), updated_at: timeOffset(-2) },
]

/** 模拟版本 */
export const mockVersions: MockVersion[] = [
  { version_id: 1, project_id: 1, version_number: 1, description: '初始版本', snapshot_data: '{}', created_by: 10001, created_at: timeOffset(-30) },
  { version_id: 2, project_id: 1, version_number: 2, description: '添加课堂互动页', snapshot_data: '{}', created_by: 10001, created_at: timeOffset(-15) },
  { version_id: 3, project_id: 1, version_number: 3, description: '修改配色方案', snapshot_data: '{}', created_by: 10001, created_at: timeOffset(-2) },
]

/** 自增 ID 计数器 */
let nextProjectId = mockProjects.length + 1
let nextPageId = mockPages.length + 1
let nextVersionId = mockVersions.length + 1

export function getNextProjectId(): number { return nextProjectId++ }
export function getNextPageId(): number { return nextPageId++ }
export function getNextVersionId(): number { return nextVersionId++ }
