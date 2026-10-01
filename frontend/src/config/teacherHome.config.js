/**
 * [数据交互说明]
 * - 导出: 教师端首页全部静态文案、导航与示例数据
 * - 依赖: 无
 * - 输出: 被 `TeacherHome.vue` 使用，避免界面文案硬编码
 */

export const TEACHER_HOME = {
  brand: {
    name: '智核',
    subtitle: 'AI 教学智能体',
  },
  teacher: {
    name: '林知夏',
    role: '高中语文教师',
    initials: '林',
  },
  navigation: [
    { index: 'home', label: 'AI 教学助手', icon: 'ChatDotRound' },
    { index: 'resources', label: '个人资源库', icon: 'FolderOpened' },
    { index: 'community', label: '技能与案例', icon: 'Grid' },
    { index: 'exports', label: '成果导出中心', icon: 'Download' },
  ],
  historyTitle: '最近对话',
  greeting: {
    eyebrow: '上午好，林老师',
    title: '今天准备一堂什么课？',
    description: '描述你的教学目标，或上传教材与参考资料。我会先梳理教学思路，再和你一起完成课件、教案与互动活动。',
  },
  suggestions: [
    {
      id: 'courseware',
      icon: 'Presentation',
      title: '生成互动课件',
      description: '根据学科、年级与课时目标生成可编辑课件',
      prompt: '帮我为八年级物理“光的折射”设计一份互动课件',
    },
    {
      id: 'lesson',
      icon: 'Document',
      title: '设计完整教案',
      description: '从教学目标到课堂活动，形成结构化教案',
      prompt: '为《背影》设计一节 45 分钟的公开课教案',
    },
    {
      id: 'activity',
      icon: 'MagicStick',
      title: '创建课堂活动',
      description: '把知识点转化为讨论、实验或互动小游戏',
      prompt: '围绕勾股定理设计一个小组探究活动',
    },
  ],
  composer: {
    placeholder: '描述你的教学需求…',
    attach: '添加资料',
    knowledge: '引用知识库',
    send: '发送',
    hint: '智核可能会出错，重要教学内容请核查。',
  },
  actions: {
    newChat: '新建对话',
    notifications: '通知',
    theme: '切换主题',
    settings: '设置',
    collapse: '收起侧栏',
    expand: '展开侧栏',
  },
  /** 折叠栏式侧栏：折叠状态持久化与响应式默认值 */
  sidebar: {
    collapsedStorageKey: 'a12_sidebar_collapsed',
    /** 小于该视口宽度（平板中间态）默认收起侧栏 */
    desktopMinWidth: 1024,
  },
}
