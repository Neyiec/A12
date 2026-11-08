import { get, post, put } from '../utils/api'
const unwrap = async (promise) => {
  try {
    const result = await promise
    if (![0, 200].includes(result?.code)) throw new Error(result?.message || '操作失败')
    return result.data
  } catch (error) {
    if ([502, 503, 504].includes(error.response?.status)) throw new Error('题库服务暂不可用，请检查后端服务后重试')
    if (error.response?.status === 404) throw new Error('当前后端尚未加载题库接口，请更新并重启 Java 服务')
    throw error
  }
}
export const listQuestions = (params) => unwrap(get('/api/v1/questions', params))
export const getQuestion = (id) => unwrap(get(`/api/v1/questions/${id}`))
export const saveQuestion = (question, action) => unwrap(question.id ? put(`/api/v1/questions/${question.id}`, { ...question, action }) : post('/api/v1/questions', { ...question, action }))
export const listPapers = () => unwrap(get('/api/v1/papers'))
export const getPaper = (id) => unwrap(get(`/api/v1/papers/${id}`))
export const savePaper = (paper) => unwrap(paper.id ? put(`/api/v1/papers/${paper.id}`, paper) : post('/api/v1/papers', paper))
