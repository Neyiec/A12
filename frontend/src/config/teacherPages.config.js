/**
 * [数据交互说明]
 * - 导出: 资源库、社区、导出中心与工作台的演示数据
 * - 依赖: 无
 * - 输出: 被教师端四个页面读取
 */
export const RESOURCE_PAGE = {
  stats: [
    { label: '全部素材', value: '128', detail: '本月新增 14 项' },
    { label: '已解析', value: '113', detail: '可被智能体引用' },
    { label: '占用空间', value: '3.7 GB', detail: '共 10 GB' },
  ],
  folders: ['全部素材', '我的课件', '教学教案', '课堂素材', '实验与活动'],
  files: [
    { name: '《背影》公开课教学设计.docx', type: 'Word', course: '高中语文', size: '2.4 MB', date: '今天 09:32', status: '已解析', private: true },
    { name: '勾股定理互动课件.pptx', type: 'PPT', course: '八年级数学', size: '18.7 MB', date: '昨天 16:18', status: '已解析', private: true },
    { name: '光合作用实验记录.mp4', type: '视频', course: '七年级生物', size: '428 MB', date: '7 月 23 日', status: '解析中', private: true },
    { name: '分数的初步认识课堂图片.zip', type: '压缩包', course: '三年级数学', size: '63.5 MB', date: '7 月 19 日', status: '待解析', private: true },
  ],
}

/**
 * 教师端可重复运行的全流程测试案例。
 * 路径：社区复用 → 创作工作台 → 导出预检 → 生成进度 → 下载成果。
 */
export const END_TO_END_TEST_CASE = {
  id: 'pythagorean-lab',
  title: '勾股定理：从测量到证明',
  projectName: '勾股定理互动教学课件',
  subject: '八年级数学',
  lessonType: '探究课',
  description: '可编辑的课堂案例，覆盖情境导入、观察猜想、公式推导与互动练习。',
  // 成果包会连同互动内容一起交付，符合导出中心对互动内容的处理要求。
  exportType: 'package',
  snapshotVersion: 1,
  steps: ['从社区复用案例', '在创作工作台调整内容', '完成导出预检并生成', '下载并预览成果'],
}

export const COMMUNITY_PAGE = {
  featured: {
    testCaseId: END_TO_END_TEST_CASE.id, type: '测试案例', title: END_TO_END_TEST_CASE.title, description: END_TO_END_TEST_CASE.description,
    author: '系统测试案例', meta: `${END_TO_END_TEST_CASE.subject} · ${END_TO_END_TEST_CASE.lessonType}`, uses: '可直接进入工作台', stage: '初中', subject: '数学', updatedAt: '2026-07-29',
  },
  cards: [
    { testCaseId: 'concept-question-chain', type: 'Skill', title: '概念课问题链生成器', subject: '通用', stage: '通用', author: '系统测试案例', uses: 0, tag: '问题链', updatedAt: '2026-07-29' },
    { testCaseId: 'circuit-interaction', type: '案例', title: '串联与并联电路互动实验', subject: '物理', stage: '初中', author: '系统测试案例', uses: 0, tag: '互动实验', updatedAt: '2026-07-29' },
    { testCaseId: 'classical-chinese-intro', type: 'Skill', title: '文言文情境导入设计', subject: '语文', stage: '高中', author: '系统测试案例', uses: 0, tag: '情境导入', updatedAt: '2026-07-29' },
    { testCaseId: 'photosynthesis-evidence', type: '案例', title: '光合作用证据推理课堂', subject: '生物', stage: '初中', author: '系统测试案例', uses: 0, tag: '证据推理', updatedAt: '2026-07-29' },
  ],
}

export const EXPORT_PAGE = {
  testCase: END_TO_END_TEST_CASE,
}

export const WORKSPACE_PAGE = {
  slides: ['课程封面', '情境导入', '观察与猜想', '公式推导', '互动练习', '课堂小结'],
  messages: [
    { role: 'user', text: '帮我设计一份八年级数学勾股定理互动课件。' },
    { role: 'assistant', text: '已按“情境测量—观察猜想—动手验证—公式应用”组织为 6 页。当前选中第 3 页，可以继续告诉我如何修改。' },
  ],
}
