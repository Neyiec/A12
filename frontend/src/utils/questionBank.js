export const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '道德与法治', '政治', '信息技术', '计算机', '其他']
export const grades = ['小学一年级', '小学二年级', '小学三年级', '小学四年级', '小学五年级', '小学六年级', '初一', '初二', '初三', '高一', '高二', '高三', '大学', '职业教育']
export const questionTypes = { single: '单选题', multiple: '多选题', judgment: '判断题', blank: '填空题', short: '简答题', calculation: '计算 / 综合题' }
export const difficulties = { easy: '基础', medium: '进阶', hard: '挑战' }
export const questionStatuses = { draft: '草稿', pending: '待审核', approved: '已公开', rejected: '已退回' }
export const emptyQuestion = () => ({ subject: '数学', grade: '初二', question_type: 'single', difficulty: 'medium', stem: '', options: ['', '', '', ''], answer: '', analysis: '', knowledge_points: '', formula: '', chemical: '' })
export function paperItems(paper) {
  return (paper.content?.items || []).map(item => ({ ...item.question, id: item.question_id, score: Number(item.score), source_revision: item.source_revision }))
}
export function totalScore(items) { return Math.round(items.reduce((sum, item) => sum + Number(item.score || 0), 0) * 100) / 100 }
export function addToBasket(items, question) {
  if (items.some(item => item.id === question.id)) return items
  if (items.length >= 100) throw new Error('一份试卷最多100题')
  if (items.length && items[0].subject !== question.subject) throw new Error('同一份试卷请选择同一学科；请先保存或清空当前题篮')
  return [...items, { ...question, score: question.question_type === 'single' ? 3 : 5 }]
}
