/**
 * [数据交互说明]
 * - 导出: 模拟个人资源数据
 * - 依赖: `./common.ts` 的时间函数
 * - 输入: 被 resource.ts handler 引用
 * - 输出: MaterialVO 列表
 */

import { timeOffset } from './common'

export interface MockMaterial {
  id: number
  user_id: number
  file_name: string
  file_type: string
  file_size: number
  object_key: string
  file_url: string
  description: string
  categories: string
  tags: string
  access_type: 'private' | 'shared' | 'authorized'
  authorized_users: string
  allow_ai: number
  ai_index_status: string
  ai_indexed_at: string | null
  ai_index_error: string | null
  status: number
  created_at: string
  updated_at: string
}

export const mockMaterials: MockMaterial[] = [
  {
    id: 1, user_id: 10001, file_name: '光合作用教材.pdf', file_type: 'pdf',
    file_size: 2048000, object_key: 'resources/10001/uuid_001.pdf',
    file_url: 'https://oss.example.com/resources/10001/uuid_001.pdf',
    description: '人教版七年级生物教材相关章节', categories: JSON.stringify(['生物', '七年级']),
    tags: JSON.stringify(['教材', '光合作用']), access_type: 'private', authorized_users: '[]',
    allow_ai: 1, ai_index_status: 'completed', ai_indexed_at: timeOffset(-20), ai_index_error: null,
    status: 1, created_at: timeOffset(-30), updated_at: timeOffset(-20),
  },
  {
    id: 2, user_id: 10001, file_name: '课堂互动设计.docx', file_type: 'word',
    file_size: 512000, object_key: 'resources/10001/uuid_002.docx',
    file_url: 'https://oss.example.com/resources/10001/uuid_002.docx',
    description: '生物课堂互动环节设计方案', categories: JSON.stringify(['生物']),
    tags: JSON.stringify(['课堂互动', '教学设计']), access_type: 'shared', authorized_users: JSON.stringify([10002]),
    allow_ai: 0, ai_index_status: 'disabled', ai_indexed_at: null, ai_index_error: null,
    status: 1, created_at: timeOffset(-50), updated_at: timeOffset(-45),
  },
  {
    id: 3, user_id: 10002, file_name: '英语时态总结.pptx', file_type: 'ppt',
    file_size: 3072000, object_key: 'resources/10002/uuid_003.pptx',
    file_url: 'https://oss.example.com/resources/10002/uuid_003.pptx',
    description: '初中英语八大时态总结', categories: JSON.stringify(['英语', '初中']),
    tags: JSON.stringify(['语法', '时态']), access_type: 'private', authorized_users: '[]',
    allow_ai: 0, ai_index_status: 'pending', ai_indexed_at: null, ai_index_error: null,
    status: 1, created_at: timeOffset(-10), updated_at: timeOffset(-10),
  },
]

export const mockAuditLogs = [
  { id: 1, resource_id: 1, user_id: 10001, action: 'upload', detail: '上传文件', created_at: timeOffset(-30) },
  { id: 2, resource_id: 1, user_id: 10001, action: 'allow_ai', detail: '开启AI访问', created_at: timeOffset(-20) },
  { id: 3, resource_id: 2, user_id: 10001, action: 'share', detail: '分享给用户10002', created_at: timeOffset(-45) },
]

let nextMaterialId = mockMaterials.length + 1
export function getNextMaterialId(): number { return nextMaterialId++ }
