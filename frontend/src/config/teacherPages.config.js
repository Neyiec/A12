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

export const COMMUNITY_PAGE = {
  featured: {
    type: '精选案例', title: '勾股定理：从测量到证明', description: '用校园测量任务引出直角三角形关系，包含动态演示、分组实验与分层练习。',
    author: '周明远 · 杭州第二中学', meta: '八年级数学 · 探究课', uses: '1,286 次复用', stage: '初中', subject: '数学', updatedAt: '2026-07-25',
  },
  cards: [
    { type: 'Skill', title: '概念课问题链生成器', subject: '通用', stage: '通用', author: '智核教研组', uses: '842', tag: '问题链', updatedAt: '2026-07-24' },
    { type: '案例', title: '串联与并联电路互动实验', subject: '物理', stage: '初中', author: '陈思远', uses: '637', tag: '互动实验', updatedAt: '2026-07-26' },
    { type: 'Skill', title: '文言文情境导入设计', subject: '语文', stage: '高中', author: '许清禾', uses: '491', tag: '情境导入', updatedAt: '2026-07-22' },
    { type: '案例', title: '光合作用证据推理课堂', subject: '生物', stage: '初中', author: '林若岚', uses: '368', tag: '证据推理', updatedAt: '2026-07-23' },
  ],
}

export const EXPORT_PAGE = {
  stats: [
    { label: '本月导出', value: '23', detail: '较上月 +4' },
    { label: '可下载成果', value: '17', detail: '6 个文件将在 7 天内过期' },
    { label: '平均生成时间', value: '1m 46s', detail: '最近 30 次任务' },
  ],
  tasks: [
    { project: '《背影》公开课', format: 'PPTX + Word', version: 'v1.4', time: '今天 10:08', status: '成功', quality: '校验通过', size: '24.8 MB' },
    { project: '勾股定理互动教学', format: '成果包', version: 'v2.1', time: '昨天 17:42', status: '部分成功', quality: '1 项提示', size: '38.2 MB' },
    { project: '光合作用实验活动', format: 'PPTX', version: 'v1.0', time: '7 月 23 日', status: '已过期', quality: '校验通过', size: '16.5 MB' },
  ],
}

export const WORKSPACE_PAGE = {
  slides: ['课程封面', '情境导入', '观察与猜想', '公式推导', '互动练习', '课堂小结'],
  messages: [
    { role: 'user', text: '帮我设计一份八年级数学勾股定理互动课件。' },
    { role: 'assistant', text: '已按“情境测量—观察猜想—动手验证—公式应用”组织为 6 页。当前选中第 3 页，可以继续告诉我如何修改。' },
  ],
}
