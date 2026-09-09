export const INTERACTIVE_MODULE_TYPES = [
  { value: 'animation', label: '知识动画', description: '用动画演示概念变化与过程' },
  { value: 'quiz_game', label: '问答游戏', description: '适合课堂练习与即时反馈' },
  { value: 'matching_game', label: '匹配游戏', description: '将概念、图示或答案进行配对' },
  { value: 'timeline_game', label: '时间线游戏', description: '按时间或步骤组织互动内容' },
  { value: 'simulation', label: '模拟实验', description: '模拟实验过程与参数变化' },
]

const INTERACTIVE_MODULE_TYPE_MAP = new Map(INTERACTIVE_MODULE_TYPES.map((item) => [item.value, item]))

export const normalizeInteractiveModuleType = (value) => {
  const normalized = String(value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
  return INTERACTIVE_MODULE_TYPE_MAP.has(normalized) ? normalized : 'unknown'
}

export const interactiveModuleTypeInfo = (value) => {
  const normalized = normalizeInteractiveModuleType(value)
  return INTERACTIVE_MODULE_TYPE_MAP.get(normalized) || {
    value: 'unknown',
    label: '未识别类型',
    description: '接口未返回可识别的 module_type，无法推断该组件的生成类型',
  }
}

export const interactiveModuleTypeLabel = (value) => interactiveModuleTypeInfo(value).label
