/**
 * [数据交互说明]
 * - 导出: 模拟社区内容数据、投稿数据
 * - 依赖: `./common.ts` 的时间函数
 * - 输入: 被 community.ts handler 引用
 * - 输出: ContentVO 列表
 */

import { timeOffset } from './common'

export interface MockContent {
  id: number
  content_type: 'skill' | 'lesson_case'
  author_id: number
  title: string
  description: string
  subject: string
  grade: string
  lesson_type: string
  content_data: string
  input_variables: string
  example_effect: string
  version: number
  version_history: string
  license: string
  status: 'draft' | 'pending' | 'published' | 'unpublished' | 'disabled' | 'rejected'
  is_top: number
  view_count: number
  use_count: number
  created_at: string
  updated_at: string
}

export const mockContents: MockContent[] = [
  {
    id: 1, content_type: 'skill', author_id: 10001,
    title: '光合作用互动教学模板', description: '适用于初中生物光合作用章节的互动教学模板，包含课堂问答与动画演示',
    subject: '生物', grade: '七年级', lesson_type: '新授课',
    content_data: JSON.stringify({ template: 'interactive', slides: 8 }),
    input_variables: JSON.stringify(['student_count', 'duration_minutes']),
    example_effect: '可自动生成包含课堂互动环节的完整课件', version: 2,
    version_history: JSON.stringify([{ version: 1, note: '初始版本' }, { version: 2, note: '增加课堂互动' }]),
    license: 'CC BY-SA 4.0', status: 'published', is_top: 1,
    view_count: 1520, use_count: 386,
    created_at: timeOffset(-90), updated_at: timeOffset(-30),
  },
  {
    id: 2, content_type: 'lesson_case', author_id: 10002,
    title: '三角函数生活应用案例', description: '将三角函数知识与生活中的测量问题结合，激发学习兴趣',
    subject: '数学', grade: '高一', lesson_type: '复习课',
    content_data: JSON.stringify({ cases: 5, includes_quiz: true }),
    input_variables: JSON.stringify(['class_size']),
    example_effect: '生成贴近生活的三角函数教学案例集', version: 1,
    version_history: JSON.stringify([{ version: 1, note: '初始版本' }]),
    license: 'CC BY 4.0', status: 'published', is_top: 0,
    view_count: 890, use_count: 156,
    created_at: timeOffset(-60), updated_at: timeOffset(-60),
  },
  {
    id: 3, content_type: 'skill', author_id: 10001,
    title: '英语阅读理解策略工具', description: '帮助学生系统训练英语阅读策略，含速读、精读、猜词等模块',
    subject: '英语', grade: '八年级', lesson_type: '新授课',
    content_data: JSON.stringify({ strategies: ['skimming', 'scanning', 'inference'] }),
    input_variables: JSON.stringify(['text_difficulty', 'time_limit']),
    example_effect: '', version: 1, version_history: JSON.stringify([{ version: 1, note: '初始版本' }]),
    license: 'CC BY-SA 4.0', status: 'published', is_top: 0,
    view_count: 420, use_count: 89,
    created_at: timeOffset(-45), updated_at: timeOffset(-45),
  },
]

/** 用户收藏 */
export const mockFavorites: { user_id: number; content_id: number; created_at: string }[] = [
  { user_id: 10001, content_id: 2, created_at: timeOffset(-30) },
]

/** 最近浏览 */
export const mockRecentViews: { user_id: number; content_id: number; viewed_at: string }[] = [
  { user_id: 10001, content_id: 1, viewed_at: timeOffset(-1) },
  { user_id: 10001, content_id: 3, viewed_at: timeOffset(-5) },
  { user_id: 10002, content_id: 1, viewed_at: timeOffset(-2) },
]

let nextContentId = mockContents.length + 1
export function getNextContentId(): number { return nextContentId++ }
