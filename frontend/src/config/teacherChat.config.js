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

/** 教学设计方案 Markdown 流式生成 SSE 端点 */
export const DESIGN_STREAM_URL = '/api/v1/python/designs/stream'

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
  hint: '智核可能会出错，重要教学内容请核查。',
  attach: '添加资料',
  knowledge: '引用知识库',
  send: '发送',
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
