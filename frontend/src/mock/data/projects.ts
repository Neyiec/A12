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

/** 可直接在创作工作台中选中的演示元素及其初始样式。 */
const createMockImageSrc = (label = '课堂观察') => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect width="640" height="360" rx="28" fill="#eff6ff"/><circle cx="150" cy="148" r="62" fill="#93c5fd"/><path d="M85 275c42-86 91-98 142-40 33-31 75-35 120 40" fill="none" stroke="#2563eb" stroke-width="18" stroke-linecap="round"/><rect x="350" y="88" width="188" height="24" rx="12" fill="#93c5fd"/><rect x="350" y="132" width="144" height="18" rx="9" fill="#bfdbfe"/><text x="350" y="222" fill="#173d78" font-family="Arial, sans-serif" font-size="26" font-weight="700">${label}</text><text x="350" y="258" fill="#607491" font-family="Arial, sans-serif" font-size="18">MOCK IMAGE</text></svg>`
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}
const createMockSlideContent = (title: string, description: string, layout = '图文并置', theme = 'blue') => {
  const themeColor = { blue: '#2563eb', navy: '#173d78', green: '#1f993f', orange: '#ff6b3f' }[theme] || '#2563eb'
  const elements = [
    { id: 'title', type: 'text', name: '页面标题', target: 'title', content: title, position: { x: 8, y: 13, width: 62, height: 15, rotation: 0, zIndex: 4 }, style: { color: '#102d54', fontSize: 40, fontWeight: 700, opacity: 100, textAlign: 'left', lineHeight: 1.2 } },
    { id: 'description', type: 'text', name: '引导文案', target: 'description', content: description, position: { x: 8, y: 30, width: 57, height: 14, rotation: 0, zIndex: 4 }, style: { color: '#607491', fontSize: 15, fontWeight: 400, opacity: 100, textAlign: 'left', lineHeight: 1.65 } },
    { id: 'visual', type: 'formula', name: '公式', target: 'formula', content: 'a² + b² = c²', position: { x: 8, y: 47, width: 48, height: 28, rotation: 0, zIndex: 3 }, style: { color: themeColor, fontSize: 32, fontWeight: 700, opacity: 100, textAlign: 'center', lineHeight: 1.2 } },
    { id: 'shape', type: 'shape', name: '几何形状', target: 'shape', shapeKind: 'circle', content: '', position: { x: 57, y: 54, width: 7, height: 11, rotation: 0, zIndex: 3 }, style: { fillColor: '#dbeafe', borderColor: themeColor, borderWidth: 2, borderRadius: 50, opacity: 100 } },
    { id: 'image', type: 'image', name: '课堂图片', target: 'image', content: '校园测量示意图', src: createMockImageSrc(), position: { x: 66, y: 46, width: 25, height: 29, rotation: 0, zIndex: 3 }, style: { tintColor: themeColor, borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, opacity: 100, objectFit: 'cover' } },
    { id: 'chart', type: 'chart', name: '测量图表', target: 'chart', content: '三组测量数据', data: [{ label: 'A组', value: 68 }, { label: 'B组', value: 82 }, { label: 'C组', value: 56 }, { label: 'D组', value: 91 }], position: { x: 64, y: 13, width: 27, height: 27, rotation: 0, zIndex: 3 }, style: { color: themeColor, backgroundColor: '#eff6ff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, opacity: 100 } },
    { id: 'footer', type: 'text', name: '页脚说明', target: 'footer', content: '在观察、猜想与验证中理解核心概念，并用它解决简单的实际问题。', position: { x: 0, y: 86, width: 100, height: 14, rotation: 0, zIndex: 5 }, style: { color: '#ffffff', fontSize: 10, fontWeight: 400, opacity: 100, textAlign: 'left', lineHeight: 1.5 } },
  ]
  return { title, description, layout, theme, elements }
}

const mockPageContents = [
  createMockSlideContent('勾股定理', '从测量与观察出发，发现直角三角形三边之间的恒定关系。', '图文并置', 'blue'),
  createMockSlideContent('情境导入', '用校园旗杆与影子的测量任务开启今天的探索。', '图文并置', 'blue'),
  createMockSlideContent('公式推导', '将三边长度转化为面积，归纳勾股定理的表达式。', '双栏探究', 'green'),
]

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
  { id: 1, project_id: 1, page_order: 1, page_type: 'cover', page_title: mockPageContents[0].title, page_content: JSON.stringify(mockPageContents[0]), components: JSON.stringify(mockPageContents[0].elements), created_at: timeOffset(-30), updated_at: timeOffset(-2) },
  { id: 2, project_id: 1, page_order: 2, page_type: 'toc', page_title: mockPageContents[1].title, page_content: JSON.stringify(mockPageContents[1]), components: JSON.stringify(mockPageContents[1].elements), created_at: timeOffset(-30), updated_at: timeOffset(-2) },
  { id: 3, project_id: 1, page_order: 3, page_type: 'content', page_title: mockPageContents[2].title, page_content: JSON.stringify(mockPageContents[2]), components: JSON.stringify(mockPageContents[2].elements), created_at: timeOffset(-30), updated_at: timeOffset(-2) },
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
