/**
 * [数据交互说明]
 * - 导出:
 *   - `TEACHING_STYLES`: 教学风格选项列表（含 label/desc/icon 标识）
 *   - `TEMPLATES`: 课件模板选项列表（含 label/desc/icon 标识）
 *   - `INTERACTION_FORMS`: 互动形式选项列表（含 label/icon 标识）
 *   - `PREFERENCES_DEFAULTS`: 偏好设置系统默认值
 * - 依赖: 无外部依赖（纯配置模块）
 * - 输入: 无
 * - 输出: 为 AccountSettings.vue 提供偏好选项数据与默认值
 *
 * 注意: 此文件中的 icon 字段为字符串标识，由调用方通过 iconMap 解析为实际图标组件。
 */

/** 教学风格选项 — 用于单选用例 */
export const TEACHING_STYLES = [
  { value: 'heuristic', label: '启发式探究', desc: '引导发现，自主建构知识', icon: 'MagicStick' },
  { value: 'lecture', label: '讲授式教学', desc: '系统讲解，高效传递信息', icon: 'Document' },
  { value: 'cooperative', label: '合作学习', desc: '小组协作，互助共进', icon: 'Share' },
  { value: 'project_based', label: '项目式学习', desc: '实践驱动，任务导向', icon: 'FolderOpened' },
  { value: 'blended', label: '混合式教学', desc: '线上线下多法融合', icon: 'Refresh' },
]

/** 课件模板选项 — 用于单选用例（带缩略图占位） */
export const TEMPLATES = [
  { value: 'business', label: '简约商务', desc: '白色底+蓝色几何色块，极简线条', icon: 'Grid' },
  { value: 'academic', label: '学术严谨', desc: '浅灰底+深蓝标题栏，传统学术', icon: 'Collection' },
  { value: 'lively', label: '活泼趣味', desc: '暖色渐变+圆角卡片，卡通点缀', icon: 'Star' },
  { value: 'tech', label: '科技现代', desc: '深色底+霓虹蓝光效，数据可视化', icon: 'Monitor' },
]

/** 互动形式选项 — 用于多选用例 */
export const INTERACTION_FORMS = [
  { value: 'random_call', label: '随机点名', icon: 'User' },
  { value: 'group_discussion', label: '小组讨论', icon: 'ChatDotRound' },
  { value: 'quiz', label: '随堂测验', icon: 'EditPen' },
  { value: 'poll', label: '投票问卷', icon: 'Promotion' },
  { value: 'bullet_chat', label: '弹幕互动', icon: 'Message' },
  { value: 'raise_hand', label: '举手发言', icon: 'Microphone' },
]

/** 系统默认偏好值 — 新用户或无历史数据时的初始值 */
export const PREFERENCES_DEFAULTS = {
  teachingStyle: '',
  templateStyle: '',
  interactionForms: ['group_discussion', 'quiz'],
}
