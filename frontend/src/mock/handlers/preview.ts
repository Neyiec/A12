import { http, HttpResponse } from 'msw'
import { emptyQuestion } from '../../utils/questionBank'
import { error, getPagination, success } from '../data/common'

const questions = [
  {
    ...emptyQuestion(), stem: '直角三角形的两条直角边长分别为 3 和 4，斜边长是多少？',
    options: ['5', '6', '7', '8'], answer: 'A',
    analysis: '根据勾股定理，斜边长为 √(3² + 4²) = 5。', knowledge_points: '勾股定理',
    formula: 'a^2 + b^2 = c^2',
  },
  {
    ...emptyQuestion(), subject: '化学', grade: '初三',
    stem: '写出氢气在氧气中燃烧的化学方程式。', question_type: 'short',
    options: [], answer: '2H₂ + O₂ → 2H₂O',
    analysis: '反应前后各元素的原子数保持不变。', chemical: '2H2 + O2 -> 2H2O',
    knowledge_points: '化学方程式、质量守恒',
  },
  {
    ...emptyQuestion(), stem: '一根长 10 米的梯子靠墙放置，梯脚离墙 6 米。梯顶距离地面多高？',
    question_type: 'calculation', options: [], answer: '8 米',
    analysis: '设梯顶高度为 h，则 h² = 10² − 6² = 64，所以 h = 8。', knowledge_points: '勾股定理的应用',
  },
].map((content, index) => ({
  id: index + 1, revision: 1, status: 'approved', owner_id: 10001,
  subject: content.subject, grade: content.grade, difficulty: content.difficulty,
  question_type: content.question_type, knowledge_points: content.knowledge_points,
  content, reviews: [],
}))

const paper = {
  id: 1, revision: 1, title: '【演示】勾股定理课堂练习',
  subject: '数学', duration_minutes: 30, total_score: 15,
  content: {
    items: [questions[0], questions[2]].map((question, index) => ({
      question_id: question.id, question: question.content, score: index ? 10 : 5, source_revision: 1,
    })),
  },
}

const course = {
  course_id: 'preview-course', title: '【演示】勾股定理与实际测量',
  subject: '数学', grade: '初二', version: 1,
  nodes: [
    { id: 'k1', kind: 'concept', label: '直角三角形', description: '认识直角边与斜边。' },
    { id: 'k2', kind: 'concept', label: '面积关系', description: '借助正方形面积理解数量关系。' },
    { id: 'k3', kind: 'concept', label: '勾股定理', description: '建立三边长度的平方关系。' },
    { id: 'k4', kind: 'concept', label: '实际应用', description: '将测量问题转化为数学问题。' },
    { id: 's1', kind: 'skill', label: '识别图形', description: '从情境中识别直角三角形。' },
    { id: 's2', kind: 'skill', label: '整理数据', description: '记录测量数据并判断合理性。' },
    { id: 's3', kind: 'skill', label: '建立模型', description: '利用勾股定理求未知长度。' },
    { id: 's4', kind: 'skill', label: '说明结论', description: '用图形与算式解释结果。' },
  ],
  edges: [
    { source: 'k1', target: 'k2', relation: 'prerequisite' },
    { source: 'k2', target: 'k3', relation: 'prerequisite' },
    { source: 'k3', target: 'k4', relation: 'prerequisite' },
    { source: 'k1', target: 's1', relation: 'supports' },
    { source: 'k2', target: 's2', relation: 'supports' },
    { source: 'k3', target: 's3', relation: 'supports' },
    { source: 'k4', target: 's4', relation: 'supports' },
  ],
}

const plan = {
  id: 'preview-plan', revision: 1, status: 'draft', basis: 'suggested',
  title: '【演示】八年级数学单元备课', subject: '数学', grade: '初二',
  textbook_version: '人教版', reasoning_effort: 'low', needs_input: false,
  items: [
    { id: 'chapter-1', title: '从测量到证明：认识勾股定理', hours: '1 课时', objectives: '理解勾股定理并用图形解释。', min_pages: 6, max_pages: 8 },
    { id: 'chapter-2', title: '把数学带入校园：利用勾股定理解决测量问题', hours: '1 课时', objectives: '建立模型，解释计算结果。', min_pages: 6, max_pages: 8 },
  ],
}

const batch = {
  id: 'preview-batch', title: '【演示】从概念理解到生活应用的数学课程',
  status: 'partial_failed', progress: 50, theme: '素白风', zip_status: 'none',
  items: [
    { id: 'preview-item-1', item_order: 1, title: '认识三角形与课件结构', status: 'completed', stage: '已保存到个人项目', project_id: 1 },
    { id: 'preview-item-2', item_order: 2, title: '借助校园测量活动理解勾股定理的实际应用', status: 'failed', stage: '等待重试', attempts: 1, error: '这是用于查看错误详情样式的演示信息。实际生成任务需要启动后端并配置模型。' },
  ],
}

const videos = [
  { job_id: 'preview-video-1', title: '【演示】勾股定理知识回顾', status: 'ready', progress: 100, attempts: 1 },
  { job_id: 'preview-video-2', title: '【演示】校园测量活动讲解', status: 'failed', progress: 30, attempts: 1, error: '这是演示错误信息，可展开检查手机上的显示效果。' },
]

/** Only the explicit mock mode uses these read-only demonstration endpoints. */
export const previewHandlers = [
  http.get('/api/v1/questions', ({ request }) => {
    const params = new URL(request.url).searchParams
    const { page, size } = getPagination(params)
    const keyword = (params.get('keyword') || '').trim()
    const filtered = questions.filter(question =>
      ['subject', 'grade', 'difficulty', 'question_type'].every(key =>
        !params.get(key) || params.get(key) === question[key as keyof typeof question]) &&
      (!keyword || question.content.stem.includes(keyword) || question.knowledge_points.includes(keyword)))
    return HttpResponse.json(success({ items: filtered.slice((page - 1) * size, page * size), total: filtered.length }))
  }),
  http.get('/api/v1/questions/:id', ({ params }) => {
    const question = questions.find(item => item.id === Number(params.id))
    return question ? HttpResponse.json(success(question)) : HttpResponse.json(error(404, '题目不存在'), { status: 404 })
  }),
  http.get('/api/v1/papers', () => HttpResponse.json(success([paper]))),
  http.get('/api/v1/papers/:id', ({ params }) => Number(params.id) === paper.id
    ? HttpResponse.json(success(paper))
    : HttpResponse.json(error(404, '试卷不存在'), { status: 404 })),
  http.get('/api/v1/python/courses', () => HttpResponse.json(success([course]))),
  http.get('/api/v1/python/courses/:id/graph', () => HttpResponse.json(success(course))),
  http.get('/api/v1/python/courses/:id/versions', () => HttpResponse.json(success([{ version: 1, title: course.title }]))),
  http.get('/api/v1/python/batch-presentations/plans', () => HttpResponse.json(success([plan]))),
  http.get('/api/v1/python/batch-presentations/plans/:id', () => HttpResponse.json(success(plan))),
  http.get('/api/v1/python/batch-presentations/batches', () => HttpResponse.json(success([batch]))),
  http.get('/api/v1/python/batch-presentations/batches/:id', () => HttpResponse.json(success(batch))),
  http.post('/api/v1/python/batch-presentations/sync-ready', () => HttpResponse.json(success({ saved: 0 }))),
  http.get('/api/v1/python/learning-videos', () => HttpResponse.json(success(videos))),
  http.get('/api/v1/python/teacher-style/preferences', () => HttpResponse.json(success({}))),
  http.get('/api/v1/python/teacher-style/strategy-effects', () => HttpResponse.json(success({ strategies: [] }))),
]
