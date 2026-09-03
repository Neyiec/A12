/**
 * [数据交互说明]
 * - 导出: 聊天界面全部静态文案与配置常量、跨组件通信信号
 * - 依赖: Vue `ref`（共享响应式信号）
 * - 输出: 被 `ChatView.vue`、`TeacherHome.vue`、`TeacherLayout.vue` 使用
 */

import { ref } from 'vue'

/**
 * 跨组件通信信号：TeacherLayout 侧栏"新建对话"按钮点击时设为 true，
 * TeacherHome 监听到后调用 closeChatView() 并复位为 false。
 */
export const requestNewChat = ref(false)

/**
 * 跨组件通信信号：TeacherLayout 侧栏"历史对话"条目点击时写入 { id, title }，
 * TeacherHome 监听到后打开对应会话的聊天视图，并由 ChatView 依据 sessionId 拉取消息恢复历史。
 */
export const openChatSession = ref(null)

/**
 * 跨组件通信信号：ChatView 挂载时写入最新会话 { id, title, updated_at }，
 * TeacherLayout 监听到后在页面未刷新时将条目插入历史列表顶部（暂时性显示）。
 */
export const latestSessionPush = ref(null)

/** SSE 事件类型常量 */
export const SSE_EVENT = {
  SESSION: 'session',
  STAGE: 'stage',
  QUESTION: 'question',
  TOOL_RESULT: 'tool_result',
  PROMPT: 'prompt',
  PROGRESS: 'progress',
  OUTLINE_DELTA: 'outline_delta',
  DESIGN_TEXT_DELTA: 'design_text_delta',
  FINAL: 'final',
  ERROR: 'error',
  DONE: 'done',
}

/** SSE 阶段中文映射 */
export const STAGE_LABELS = {
  parse_input: '正在分析需求…',
  tools: '正在检索相关资料…',
  build_prompt: '正在构建教学方案…',
  generate_design: '正在生成教学设计方案…',
  generate_outline: '正在生成教学设计大纲…',
  generate_resource: '正在生成教学资源…',
}

/** 大纲操作按钮文案 */
export const OUTLINE_ACTIONS = {
  confirm: '确认大纲',
  modify: '修改要求',
  regenerate: '重新生成',
}

/** 大纲操作栏文案（Markdown 消息下方的操作按钮） */
export const DESIGN_ACTION_BAR = {
  modify: '修改',
  confirm: '✓ 确认大纲',
  confirmed: '✓ 已确认',
  processing: '生成中…',
}

/** 创作类型选项 */
export const GEN_TYPE_OPTIONS = [
  { value: 'ppt', label: 'PPT 课件', icon: 'Document' },
  { value: 'activity', label: '课堂活动', icon: 'DataBoard' },
]

/** 创作参数默认值 */
export const GEN_FORM_DEFAULTS = {
  slideCount: 8,
  theme: '素白风',
  activityType: '小组探究',
  duration: 15,
  notes: '',
}

/** PPT 模板风格选项 */
export const PPT_THEME_OPTIONS = [
  '素白风', '经典蓝', '科技风', '清新风', '中国风',
  '商务', '赛博朋克风', '吉卜力风', '莫奈风', '森林绿',
]

/** 课堂活动类型选项 */
export const ACTIVITY_TYPE_OPTIONS = [
  '小组探究', '角色扮演', '实验操作', '课堂讨论',
  '知识竞赛', '动手实践', '案例分析', '情景模拟',
]

/** 资源卡片文案 */
export const RESOURCE_CARD_LABELS = {
  open: '打开',
  slideCount: '页',
  duration: '分钟',
  pptDesc: '{count}页课件 · {theme}风格',
  activityDesc: '{type} · {duration}分钟',
}

/** 聊天输入区文案 */
export const CHAT_COMPOSER = {
  placeholder: '输入补充要求或修改建议…',
  generalPlaceholder: '输入你的问题，或描述想要完成的教学任务…',
  clarificationPlaceholder: '请回复以上问题，以帮助生成更贴合的教学大纲…',
  hint: '智核可能会出错，重要教学内容请核查。',
  attach: '添加资料',
  knowledge: '引用知识库',
  send: '发送',
}

/** 仅识别明确的教学设计动作，避免“PPT是什么”“教学怎么理解”等普通问题误入备课流程。 */
export const isPlanningPrompt = (text) => {
  const value = String(text || '').trim()
  if (!value) return false
  const hasQuestionMarker = /(?:是什么|什么是|什么意思|怎么理解|指什么)/.test(value)
  const hasExplicitAction = /(?:生成|制作|设计|编写|创建|准备|整理|开始|进行|安排|制定|帮我做|我要做|我想做)/.test(value)
  if (hasQuestionMarker && !hasExplicitAction) return false
  // 仅把“开始备课/帮我备课”识别为动作；“备课是什么”仍属于普通问答。
  if (/^(?:备课|开始备课)$/.test(value)) return true
  if (/(?:我要|我想|需要|帮我|请|开始|进行|准备|安排|制定|生成|设计|做).{0,10}备课/.test(value)) return true
  if (/备课.{0,8}(?:方案|计划|教案|课件|流程|内容)/.test(value)) return true
  const targets = '(?:课件|ppt|教案|教学设计|教学大纲|课堂活动|课程设计|问题链|学案|讲义|练习题|试卷|课程)'
  const creation = new RegExp(`(?:生成|制作|设计|编写|创建|准备|整理|做(?:一份|一个|个)?).{0,20}${targets}`, 'i')
  const targetQuestion = new RegExp(`${targets}.{0,12}(?:怎么做|如何做|帮我生成|帮我制作|帮我设计|帮我编写)`, 'i')
  return creation.test(value) || targetQuestion.test(value)
}

/** 备课征询可选项：与工作台/后端使用的上下文字段保持一致。 */
export const STAGE_OPTIONS = ['小学', '初中', '高中', '大学']
export const SUBJECT_OPTIONS = [
  '语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理',
  '道德与法治', '政治', '科学', '信息技术', '音乐', '美术', '体育',
]
export const GRADE_OPTIONS = [
  '一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
  '七年级', '八年级', '九年级', '高一', '高二', '高三',
]

/**
 * 从教师首句中提取已经明确的备课上下文。
 * 这是前端路由层的轻量解析，不替代后端 Agent；它的作用是避免模型用一段
 * 自由文本追问时，前端仍停留在普通聊天气泡里。
 */
export const extractPlanningContext = (text) => {
  const value = String(text || '').trim()
  const context = {
    stage: '',
    subject: '',
    grade: '',
    textbook: '',
    courseName: '',
  }
  if (!value) return context

  context.subject = SUBJECT_OPTIONS
    .slice()
    .sort((left, right) => right.length - left.length)
    .find((subject) => value.includes(subject)) || ''

  const gradeMatchers = [
    ['一年级', /(?:小学)?一(?:年级|年)/],
    ['二年级', /(?:小学)?二(?:年级|年)/],
    ['三年级', /(?:小学)?三(?:年级|年)/],
    ['四年级', /(?:小学)?四(?:年级|年)/],
    ['五年级', /(?:小学)?五(?:年级|年)/],
    ['六年级', /(?:小学)?六(?:年级|年)/],
    ['七年级', /(?:七年级|初一)/],
    ['八年级', /(?:八年级|初二)/],
    ['九年级', /(?:九年级|初三)/],
    ['高一', /(?:高一|高中一年级)/],
    ['高二', /(?:高二|高中二年级)/],
    ['高三', /(?:高三|高中三年级)/],
  ]
  context.grade = gradeMatchers.find(([, matcher]) => matcher.test(value))?.[0] || ''

  if (/(?:小学|小一|小二|小三|小四|小五|小六)/.test(value) || /^[一二三四五六]年级/.test(context.grade)) {
    context.stage = '小学'
  } else if (/(?:初中|初一|初二|初三|七年级|八年级|九年级)/.test(value)) {
    context.stage = '初中'
  } else if (/(?:高中|高一|高二|高三)/.test(value)) {
    context.stage = '高中'
  } else if (/大学|大一|大二|大三|大四/.test(value)) {
    context.stage = '大学'
  }

  const quotedTitle = value.match(/《([^》]{2,40})》/)
  const labeledTitle = value.match(/(?:课题|主题|课程名称)\s*(?:是|为|：|:)?\s*[“"「]?([^，。！？；;\n”"」]{2,40})/)
  context.courseName = String(quotedTitle?.[1] || labeledTitle?.[1] || '').trim()

  return context
}

/** 澄清问题相关文案 */
export const CLARIFICATION_LABELS = {
  title: '需要补充确认',
  hint: '为生成更贴合你意图的大纲，请补充回答以下问题后再继续。',
}

/** 聊天头部文案 */
export const CHAT_HEADER = {
  back: '返回',
  newChat: '新建对话',
}

/** 系统消息模板 */
export const SYSTEM_MESSAGES = {
  connectionError: '连接失败，请检查网络后重试。',
  streamInterrupted: '连接中断，请点击重试按钮重新生成。',
  timeout: '生成超时，请点击重试按钮重新尝试。',
  outlineConfirmed: '教学设计大纲已确认，请选择要生成的资源类型。',
  generatingResource: '正在根据教学设计生成资源…',
}

/** 历史会话恢复文案 */
export const CHAT_RESUME = {
  loading: '恢复历史对话…',
}

/** 创作类型模态框文案 */
export const GEN_DIALOG = {
  title: '选择创作类型',
  typeLabel: '创作类型',
  pptSettings: 'PPT 设置',
  activitySettings: '活动设置',
  slideCount: '期望页数',
  theme: '模板风格',
  activityType: '活动类型',
  duration: '预计时长',
  durationUnit: '分钟',
  notes: '补充说明',
  notesPlaceholder: '希望加入更多互动环节…',
  cancel: '取消',
  confirm: '开始生成',
}

/** 默认期望页数选项 */
export const SLIDE_COUNT_OPTIONS = [6, 8, 10, 12, 15, 20]

/** 预计时长选项 */
export const DURATION_OPTIONS = [5, 10, 15, 20, 30, 45]

/** 班级学情选项 */
export const CLASS_LEVEL_OPTIONS = ['优秀', '良好', '一般', '较弱']

/** 教材版本选项 */
export const TEXTBOOK_OPTIONS = [
  '人教版', '部编版', '北师大版', '苏教版', '外研社版', '湘教版', '校本教材',
]

/** 补充信息卡片表单默认值 */
export const INFO_FORM_DEFAULTS = {
  stage: '初中',
  subject: '语文',
  grade: '八年级',
  textbook: '人教版',
  classLevel: '良好',
  courseName: '',
  requirements: '符合新课标教学要求；课件风格为自动匹配',
}

/** 资源生成卡片默认值 */
export const GEN_RESOURCE_DEFAULTS = {
  name: '',
  description: '',
  slideCount: 8,
  theme: '自动匹配',
}
