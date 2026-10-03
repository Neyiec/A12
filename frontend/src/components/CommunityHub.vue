<!--
  [数据交互说明]
  - 导入: 社区接口数据、开发预览兜底数据、Vue Router、Element Plus 组件、全局用户头像状态
  - 输出: Skill 与教学案例社区页面
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CollectionTag, Search, Star, Trophy, User } from '@element-plus/icons-vue'
import { COMMUNITY_PAGE } from '../config/teacherPages.config.js'
import { createCommunityReport, createCommunitySubmission, favoriteCommunityItem, getCommunityItem, getCommunityReport, getCommunitySubmission, likeCommunityItem, listCommunityFavorites, listCommunityItems, listCommunityRankings, listCommunityRecentViews, listCommunityReports, listCommunitySubmissions, listResources, patchProject, recordCommunityView, removeCommunityRecentView, reuseCommunityItem, saveCommunitySubmissionVersion, submitCommunitySubmission, unlikeCommunityItem, unfavoriteCommunityItem, updateCommunitySubmission } from '../apis/teacher'
import { useUserStore } from '../storage/user.js'
import CommunityContentPreview from './CommunityContentPreview.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const keyword = ref('')
const searchQuery = ref('')
const activeTab = ref('精选')
const selectedStage = ref('全部学段')
const selectedSubject = ref('全部学科')
const tabs = ['精选', 'PPT 课件', '最新', 'Skill', '教学案例']
const showMobileFilters = ref(false)
const communityCards = ref([])
const communityTotal = ref(0)
const communityPage = ref(1)
const communityPageSize = ref(12)
const communityError = ref('')
const usingDemoCards = ref(false)
const favoriteIds = ref(new Set())
// 功能11：列表排序维度（sort_by × period）与点赞态
const sortBy = ref('')
const sortPeriod = ref('all')
const sortOptions = [
  { value: 'like', label: '点赞最多' },
  { value: 'favorite', label: '收藏最多' },
  { value: 'use', label: '复用最多' },
]
const likedIds = ref(new Set())
// 功能11：热门榜单（类型 × 时间段，Top10）
const rankType = ref('skill')
const rankPeriod = ref('week')
const rankItems = ref([])
const rankLoading = ref(false)
const rankError = ref('')
const rankTypeTabs = [
  { value: 'skill', label: 'Skill' },
  { value: 'lesson_case', label: '教学案例' },
]
const rankPeriodTabs = [
  { value: 'day', label: '日' },
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
]
const rankTitle = computed(() => ({ day: '今日热门', week: '本周热门', month: '本月热门' }[rankPeriod.value] || '热门榜单'))
const loading = ref(false)
const detailVisible = ref(false), submissionVisible = ref(false), collectionVisible = ref(false), reportVisible = ref(false)
const detail = ref(null), favorites = ref([]), recentViews = ref([]), submissions = ref([]), reports = ref([])
const detailLoading = ref(false)
const detailSlideFrameObservers = new Set()
const detailError = ref('')
const activeDetailSlideIndex = ref(0)
const detailContentView = ref('lesson_plan')
const currentUser = computed(() => userStore.userInfo || {})
const currentAvatarText = computed(() => (currentUser.value.real_name || currentUser.value.username || '用').slice(0, 1))
const currentAvatarUrl = computed(() => currentUser.value.avatar || undefined)
const detailAuthorName = computed(() => {
  const source = detail.value || {}
  return source.author_name || source.author || (source.author_id ? `用户 #${source.author_id}` : '社区教师')
})
/** API-58 只保证返回 author_id；若后端补充作者头像则优先使用，否则跟随账号设置页。 */
const detailAuthorAvatarUrl = computed(() => {
  const source = detail.value || {}
  return source.author_avatar || source.authorAvatar || currentAvatarUrl.value
})
const detailAuthorAvatarText = computed(() => {
  const source = detail.value || {}
  const hasAuthorAvatar = source.author_avatar || source.authorAvatar
  return hasAuthorAvatar ? String(detailAuthorName.value || '教').slice(0, 2) : currentAvatarText.value
})
const collectionsLoading = ref(false)
const collectionError = ref('')
const reportsLoading = ref(false)
const reportDetailVisible = ref(false)
const reportDetailLoading = ref(false)
const reportDetail = ref(null)
const submissionSaving = ref(false)
const submissionLoading = ref(false)
const submissionError = ref('')
const emptySubmission = () => ({ id: null, content_type: 'lesson_case', title: '', description: '', subject: '', grade: '', lesson_type: '', keywords: '', content_data: '', input_variables: '', example_effect: '', license: 'CC BY-NC 4.0' })
const submission = ref(emptySubmission())
const submissionReadOnly = computed(() => Boolean(submission.value.id && submission.value.status && String(submission.value.status).toLowerCase() !== 'draft'))
const submissionContentEditor = ref({ objective: '', objectiveKey: 'objective', stepKey: 'steps', steps: [] })
const submissionVariableEditor = ref([])
const submissionVariablesShape = ref('array')
const reportForm = ref({ target_type: 'lesson_case', target_id: null, reason: '', comment: '' })
const reuseVisible = ref(false)
const reuseLoading = ref(false)
const reuseResourcesLoading = ref(false)
const reuseTarget = ref(null)
const reuseDetail = ref(null)
const reuseProjectName = ref('')
const reuseVersion = ref(1)
const reuseVariables = ref([])
const reuseVariableValues = ref({})
const reuseResources = ref([])
const reuseSelectedResourceIds = ref([])

const parseJsonValue = (value, fallback = null) => {
  if (value === undefined || value === null || value === '') return fallback
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return fallback }
}
const normalizeCommunityContentType = (item = {}) => {
  const type = String(item.content_type || item.contentType || '').trim().toLowerCase()
  if (type === 'skill' || String(item.type || '').trim().toLowerCase() === 'skill') return 'skill'
  if (type === 'ppt' || ['ppt', 'ppt 课件'].includes(String(item.type || '').trim().toLowerCase())) return 'ppt'
  return 'lesson_case'
}
const normalizeCommunityType = (item = {}) => {
  const type = String(item.type || '').trim().toLowerCase()
  if (type === 'skill') return 'Skill'
  if (type === 'ppt' || type === 'ppt 课件') return 'PPT'
  if (['case', 'lesson_case', 'lesson-case', '教学案例', '案例'].includes(type)) return '案例'
  return item.type || (normalizeCommunityContentType(item) === 'skill' ? 'Skill' : normalizeCommunityContentType(item) === 'ppt' ? 'PPT' : '案例')
}
const statusLabel = (status) => ({ draft: '草稿', reviewing: '审核中', pending: '待处理', approved: '已通过', rejected: '已退回', resolved: '已处理' }[String(status || '').toLowerCase()] || status || '草稿')
const isDevelopmentPreview = computed(() => import.meta.env.DEV && route.query.preview === '1')
const extractRecords = (value) => {
  const data = unwrap(value)
  if (Array.isArray(data)) return data
  const candidates = data?.records || data?.list || data?.items || data?.resources || []
  return Array.isArray(candidates) ? candidates : []
}
const extractTotal = (value, fallback = 0) => {
  const data = unwrap(value)
  const total = data?.total ?? data?.total_count ?? data?.totalCount
  return Number.isFinite(Number(total)) ? Number(total) : fallback
}
const toJsonEditorValue = (value) => {
  if (value === undefined || value === null || value === '') return ''
  if (typeof value === 'string') {
    const parsed = parseJsonValue(value, undefined)
    return parsed === undefined ? value : JSON.stringify(parsed)
  }
  return JSON.stringify(value)
}
const formatJsonForDisplay = (value) => {
  if (value === undefined || value === null || value === '') return '暂无正文内容'
  if (typeof value === 'string') {
    const parsed = parseJsonValue(value, undefined)
    return parsed === undefined ? value : JSON.stringify(parsed, null, 2)
  }
  return JSON.stringify(value, null, 2)
}
const parseSubmissionJson = (value, label, allowArray = false) => {
  const source = String(value ?? '').trim()
  if (!source) return ''
  let parsed
  try { parsed = JSON.parse(source) } catch { throw new Error(`${label}必须是合法 JSON`) }
  const isObject = parsed && typeof parsed === 'object' && !Array.isArray(parsed)
  if (!isObject && !(allowArray && Array.isArray(parsed))) {
    throw new Error(allowArray ? `${label}必须是 JSON 对象或数组` : `${label}必须是 JSON 对象，不能是数组或普通文本`)
  }
  return JSON.stringify(parsed)
}
const normalizeSubmissionPayload = () => {
  syncSubmissionContentEditor()
  syncSubmissionVariableEditor()
  const title = String(submission.value.title || '').trim()
  if (!title) throw new Error('请输入投稿标题')
  const contentType = normalizeCommunityContentType(submission.value)
  const license = String(submission.value.license || '').trim()
  if (!license) throw new Error('请填写授权许可')
  return {
    content_type: contentType,
    title,
    description: String(submission.value.description || '').trim(),
    subject: String(submission.value.subject || '').trim(),
    grade: String(submission.value.grade || '').trim(),
    lesson_type: String(submission.value.lesson_type || '').trim(),
    keywords: String(submission.value.keywords || '').trim(),
    content_data: parseSubmissionJson(submission.value.content_data, '正文'),
    input_variables: parseSubmissionJson(submission.value.input_variables, '输入变量', true),
    example_effect: String(submission.value.example_effect || '').trim(),
    license,
  }
}
const selectSubmissionDraft = async (item) => {
  if (!item?.id) return
  submissionLoading.value = true
  submissionError.value = ''
  try {
    const detailItem = unwrap(assertApiSuccess(await getCommunitySubmission(item.id)))
    submission.value = {
      ...emptySubmission(),
      ...detailItem,
      content_data: toJsonEditorValue(detailItem?.content_data),
      input_variables: toJsonEditorValue(detailItem?.input_variables),
    }
    hydrateSubmissionEditors()
  } catch (error) {
    submissionError.value = error?.message || '投稿详情加载失败，请稍后重试'
    ElMessage.error(submissionError.value)
  } finally { submissionLoading.value = false }
}
const recentViewItem = (row) => row?.item || row || {}
const recentViewId = (row) => recentViewItem(row)?.id ?? row?.item_id ?? row?.itemId ?? row?.id ?? null
const recentViewTitle = (row) => {
  const item = recentViewItem(row)
  return item.title || row?.item_title || row?.itemTitle || (recentViewId(row) ? `内容 #${recentViewId(row)}` : '未命名内容')
}
const normalizeReuseResource = (resource = {}) => {
  const id = resource.id ?? resource.resource_id ?? resource.resourceId
  return id === undefined || id === null ? null : {
    id: String(id),
    name: String(resource.name || resource.file_name || resource.filename || resource.title || `资源 ${id}`),
    fileType: String(resource.file_type || resource.fileType || resource.mime_type || resource.mimeType || ''),
  }
}
const normalizeInputVariables = (value) => {
  const parsed = parseJsonValue(value, [])
  if (Array.isArray(parsed)) return parsed.map((item, index) => {
    const variable = item && typeof item === 'object' ? item : { default: item }
    const key = String(variable.key || variable.name || variable.id || `variable_${index + 1}`)
    return { ...variable, key, label: String(variable.label || variable.title || variable.name || key), type: String(variable.type || variable.input_type || 'text'), required: variable.required !== false, description: String(variable.description || variable.help || '') }
  })
  if (parsed && typeof parsed === 'object') return Object.entries(parsed).map(([key, value]) => {
    const variable = value && typeof value === 'object' && !Array.isArray(value) ? value : { default: value }
    return { ...variable, key, label: String(variable.label || variable.title || key), type: String(variable.type || variable.input_type || 'text'), required: variable.required !== false, description: String(variable.description || variable.help || '') }
  })
  return []
}
const hasOwn = (value, key) => Object.prototype.hasOwnProperty.call(value || {}, key)
const briefText = (value, maxLength = 84) => String(value || '')
  .replace(/<[^>]*>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .slice(0, maxLength)
const submissionContentObject = computed(() => {
  const parsed = parseJsonValue(submission.value.content_data, null)
  return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
})
const submissionStepKey = (content = {}) => ['steps', 'activities', 'stages'].find((key) => Array.isArray(content?.[key])) || 'steps'
const submissionObjectiveKey = (content = {}) => ['objective', 'goal', 'summary', 'description'].find((key) => hasOwn(content, key)) || 'objective'
const submissionStepText = (step) => {
  if (step && typeof step === 'object' && !Array.isArray(step)) {
    const key = ['title', 'name', 'label', 'description', 'text', 'content'].find((field) => hasOwn(step, field))
    return String(key ? step[key] : '').trim()
  }
  return String(step ?? '').trim()
}
const submissionStepTextKey = (step = {}) => ['title', 'name', 'label', 'description', 'text', 'content'].find((key) => hasOwn(step, key)) || 'title'
const submissionSlidePreviews = computed(() => {
  const content = submissionContentObject.value || {}
  const slides = Array.isArray(content.slides) ? content.slides : Array.isArray(content.pages) ? content.pages : []
  return slides.map((slide, index) => {
    const item = slide && typeof slide === 'object' ? slide : {}
    return {
      number: index + 1,
      title: String(item.title || item.name || item.page_title || `第 ${index + 1} 页`).trim(),
      note: briefText(item.notes || item.description || item.summary || item.content || ''),
      layout: String(item.layout || item.type || '').trim(),
    }
  })
})
const submissionSlidePreviewList = computed(() => submissionSlidePreviews.value.slice(0, 6))
const submissionHiddenSlideCount = computed(() => Math.max(0, submissionSlidePreviews.value.length - submissionSlidePreviewList.value.length))
const submissionVariableCount = computed(() => submissionVariableEditor.value.length)
const submissionContentMetrics = computed(() => [
  { label: '课件页', value: submissionSlidePreviews.value.length || '—' },
  { label: '教学环节', value: submissionContentEditor.value.steps.length || '—' },
  { label: '复用输入', value: submissionVariableCount.value || '—' },
])
const submissionHasContent = computed(() => Boolean(
  submissionSlidePreviews.value.length
  || submissionContentEditor.value.objective
  || submissionContentEditor.value.steps.length
  || Object.keys(submissionContentObject.value || {}).length,
))
const hydrateSubmissionEditors = () => {
  const content = submissionContentObject.value || {}
  const objectiveKey = submissionObjectiveKey(content)
  const stepKey = submissionStepKey(content)
  const steps = Array.isArray(content[stepKey]) ? content[stepKey] : []
  submissionContentEditor.value = {
    objective: String(content[objectiveKey] || '').trim(),
    objectiveKey,
    stepKey,
    steps: steps.map((step) => ({
      raw: step && typeof step === 'object' && !Array.isArray(step) ? { ...step } : null,
      text: submissionStepText(step),
    })),
  }
  const variables = parseJsonValue(submission.value.input_variables, [])
  submissionVariablesShape.value = variables && typeof variables === 'object' && !Array.isArray(variables) ? 'object' : 'array'
  submissionVariableEditor.value = normalizeInputVariables(submission.value.input_variables).map((variable, index) => ({
    ...variable,
    key: String(variable.key || `variable_${index + 1}`),
    label: String(variable.label || variable.key || `输入项 ${index + 1}`),
    type: String(variable.type || 'text'),
    required: variable.required !== false,
    description: String(variable.description || ''),
  }))
}
const syncSubmissionContentEditor = () => {
  const original = submissionContentObject.value
  if (String(submission.value.content_data || '').trim() && !original) return
  const content = { ...(original || {}) }
  const editor = submissionContentEditor.value
  const objective = String(editor.objective || '').trim()
  if (objective) content[editor.objectiveKey || 'objective'] = objective
  else delete content[editor.objectiveKey || 'objective']
  const steps = editor.steps
    .map((step) => {
      const text = String(step.text || '').trim()
      if (!text) return null
      if (step.raw && typeof step.raw === 'object' && !Array.isArray(step.raw)) {
        return { ...step.raw, [submissionStepTextKey(step.raw)]: text }
      }
      return text
    })
    .filter(Boolean)
  if (steps.length) content[editor.stepKey || 'steps'] = steps
  else delete content[editor.stepKey || 'steps']
  submission.value.content_data = Object.keys(content).length ? JSON.stringify(content) : ''
}
const syncSubmissionVariableEditor = () => {
  const keys = new Set()
  const variables = submissionVariableEditor.value.map((variable, index) => {
    const baseKey = String(variable.key || `variable_${index + 1}`).trim().replace(/\s+/g, '_') || `variable_${index + 1}`
    let key = baseKey
    let suffix = 2
    while (keys.has(key)) key = `${baseKey}_${suffix++}`
    keys.add(key)
    return { ...variable, key, label: String(variable.label || key).trim() || key, type: String(variable.type || 'text'), required: variable.required !== false, description: String(variable.description || '').trim() }
  })
  if (!variables.length) {
    submission.value.input_variables = ''
    return
  }
  if (submissionVariablesShape.value === 'object') {
    submission.value.input_variables = JSON.stringify(Object.fromEntries(variables.map(({ key, ...value }) => [key, value])))
    return
  }
  submission.value.input_variables = JSON.stringify(variables)
}
const addSubmissionStep = () => submissionContentEditor.value.steps.push({ raw: null, text: '' })
const removeSubmissionStep = (index) => submissionContentEditor.value.steps.splice(index, 1)
const addSubmissionVariable = () => submissionVariableEditor.value.push({ key: `variable_${submissionVariableEditor.value.length + 1}`, label: '新输入项', type: 'text', required: false, description: '' })
const removeSubmissionVariable = (index) => submissionVariableEditor.value.splice(index, 1)
const detailContentObject = computed(() => {
  const parsed = parseJsonValue(detail.value?.content_data, null)
  if (Array.isArray(parsed)) return { slides: parsed }
  return parsed && typeof parsed === 'object' ? parsed : null
})
const detailSteps = computed(() => {
  const steps = detailContentObject.value?.steps ?? detailContentObject.value?.activities ?? detailContentObject.value?.stages
  if (!Array.isArray(steps)) return []
  return steps.map((step) => {
    if (step && typeof step === 'object') return String(step.title || step.name || step.label || step.description || '').trim()
    return String(step ?? '').trim()
  }).filter(Boolean)
})
const detailObjective = computed(() => String(detailContentObject.value?.objective || detailContentObject.value?.goal || '').trim())
const detailInputVariables = computed(() => normalizeInputVariables(detail.value?.input_variables))
const detailLessonPlan = computed(() => {
  const content = detailContentObject.value || {}
  const candidates = [
    content.lesson_plan,
    content.lessonPlan,
    content.teaching_plan,
    content.teachingPlan,
    content.workspace_context?.lesson_plan,
    content.workspace_context?.lessonPlan,
  ]
  for (const candidate of candidates) {
    const plan = parseJsonValue(candidate, candidate)
    if (!plan || typeof plan !== 'object' || Array.isArray(plan)) continue
    const nestedPlan = parseJsonValue(plan.lesson_plan, plan.lesson_plan)
    return nestedPlan && typeof nestedPlan === 'object' && !Array.isArray(nestedPlan) ? nestedPlan : plan
  }
  const planKeys = ['teaching_goals', 'goals', 'objectives', 'key_points', 'difficult_points', 'lesson_process', 'teaching_process', 'process', 'classroom_activities']
  if (planKeys.some((key) => Object.prototype.hasOwnProperty.call(content, key))) return content
  return null
})
const detailSlides = computed(() => {
  const content = detailContentObject.value || {}
  const pages = Array.isArray(content.slides)
    ? content.slides
    : Array.isArray(content.pages)
      ? content.pages
      : Array.isArray(content.presentation?.slides)
        ? content.presentation.slides
        : content.html || content.content_html || content.srcdoc
          ? [content]
          : []
  return pages.map((page, index) => {
    const item = page && typeof page === 'object' ? page : {}
    const html = String(item.html || item.content_html || item.srcdoc || '')
    const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)
    const title = String(item.title || item.name || item.page_title || (titleMatch ? briefText(titleMatch[1], 56) : '') || `第 ${index + 1} 页`).trim()
    return { index, html, title }
  }).filter((page) => Boolean(page.html))
})
const activeDetailSlide = computed(() => detailSlides.value[activeDetailSlideIndex.value] || detailSlides.value[0] || null)
const selectDetailSlide = (index) => { if (detailSlides.value[index]) activeDetailSlideIndex.value = index }
const fitDetailSlideFrame = (event) => {
  const iframe = event?.currentTarget
  const container = iframe?.parentElement
  if (!iframe || !container) return

  const previous = [...detailSlideFrameObservers].find((item) => item.iframe === iframe)
  previous?.observer?.disconnect()
  if (previous) detailSlideFrameObservers.delete(previous)

  const resize = () => {
    const { clientWidth: width, clientHeight: height } = container
    if (!width || !height) return
    iframe.style.transform = `scale(${Math.min(width / 1280, height / 720)})`
  }

  resize()
  if (typeof ResizeObserver === 'undefined') {
    detailSlideFrameObservers.add({ iframe, observer: null })
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  detailSlideFrameObservers.add({ iframe, observer })
}
onBeforeUnmount(() => {
  detailSlideFrameObservers.forEach(({ observer }) => observer?.disconnect())
  detailSlideFrameObservers.clear()
})
const normalizedVariableValue = (variable) => variable.default ?? variable.default_value ?? variable.example ?? ''
const reuseVersionOptions = computed(() => {
  const current = Number(reuseDetail.value?.version || 1)
  const history = parseJsonValue(reuseDetail.value?.version_history, [])
  const versions = [current, ...(Array.isArray(history) ? history.map((item) => {
    const stored = Number(item?.version_number || item?.version)
    return item?.snapshot_semantics === 'prior' ? stored : stored - 1
  }).filter((value) => Number.isInteger(value) && value > 0) : [])]
  return [...new Set(versions)].sort((a, b) => b - a)
})
const reuseContext = computed(() => {
  const source = reuseDetail.value || reuseTarget.value || {}
  const inputVariables = parseJsonValue(source.input_variables, [])
  const inputValues = { ...reuseVariableValues.value }
  const resourceIds = [...reuseSelectedResourceIds.value].map((id) => String(id))
  return {
    id: source.id || reuseTarget.value?.testCaseId || null,
    type: normalizeCommunityType(source),
    title: source.title || '',
    description: source.description || '',
    subject: source.subject || '',
    stage: source.stage || source.grade || '',
    grade: source.grade || source.stage || '',
    lesson_type: source.lesson_type || source.lessonType || '',
    version: Number(source.version || 1),
    version_history: parseJsonValue(source.version_history, []),
    license: source.license || '未说明',
    example_effect: source.example_effect || source.exampleEffect || '',
    input_variables: reuseVariables.value.length ? reuseVariables.value : inputVariables,
    input_values: inputValues,
    content_data: parseJsonValue(source.content_data, source.content_data || ''),
    resource_ids: resourceIds,
    resourceIds,
    bound_materials: resourceIds,
    bind_materials: resourceIds,
  }
})

const normalizeCard = (item = {}) => {
  const contentType = normalizeCommunityContentType(item)
  return {
    id: item.id ?? item.item_id ?? null,
    testCaseId: item.testCaseId,
    contentType,
    type: normalizeCommunityType(item),
    title: item.title || '未命名内容',
    description: item.description || item.summary || '',
    subject: item.subject || '通用',
    stage: item.grade || item.stage || '通用',
    author: item.author_name || item.author || item.creator_name || (item.author_id ? `用户 #${item.author_id}` : '社区教师'),
    uses: Number(item.use_count ?? item.useCount ?? 0),
    likes: Number(item.like_count ?? item.likeCount ?? 0),
    favorites: Number(item.favorite_count ?? item.favoriteCount ?? 0),
    liked: Boolean(item.liked),
    keywords: item.keywords || '',
    tag: item.lesson_type || item.lessonType || (contentType === 'skill' ? '智能 Skill' : contentType === 'ppt' ? '可复用课件' : '教学设计'),
    updatedAt: String(item.updated_at || item.updatedAt || item.created_at || ''),
    raw: item,
  }
}

let communityRequestSeq = 0
const loadCommunity = async () => {
  const requestSeq = ++communityRequestSeq
  loading.value = true
  communityError.value = ''
  const contentType = activeTab.value === 'Skill' ? 'skill' : activeTab.value === '教学案例' ? 'lesson_case' : activeTab.value === 'PPT 课件' ? 'ppt' : undefined
  try {
    const result = assertApiSuccess(await listCommunityItems({
      content_type: contentType,
      subject: selectedSubject.value === '全部学科' ? undefined : selectedSubject.value,
      grade: selectedStage.value === '全部学段' ? undefined : selectedStage.value,
      keyword: searchQuery.value || undefined,
      sort_by: sortBy.value || undefined,
      period: sortBy.value ? sortPeriod.value : undefined,
      page: communityPage.value,
      size: communityPageSize.value,
    }))
    if (requestSeq !== communityRequestSeq) return
    const nextRecords = extractRecords(result)
    communityCards.value = nextRecords.map(normalizeCard)
    communityTotal.value = extractTotal(result, nextRecords.length)
    syncLikeState(nextRecords)
    usingDemoCards.value = false
  } catch (error) {
    if (requestSeq !== communityRequestSeq) return
    communityTotal.value = 0
    communityError.value = error?.message || '社区内容加载失败，请重试'
    if (isDevelopmentPreview.value) {
      usingDemoCards.value = true
      communityCards.value = COMMUNITY_PAGE.cards.map(normalizeCard)
    } else {
      usingDemoCards.value = false
      communityCards.value = []
    }
  } finally {
    if (requestSeq === communityRequestSeq) loading.value = false
  }
}

/** 提交关键词，避免输入过程中频繁改变社区结果。 */
const submitSearch = () => {
  searchQuery.value = keyword.value.trim().toLowerCase()
  communityPage.value = 1
  loadCommunity()
}

const changeCommunityPage = (page) => {
  communityPage.value = page
  loadCommunity()
}

/** 判断内容是否符合关键词、学段和学科条件。 */
const matchesFilters = (item) => {
  const searchableText = [item.title, item.subject, item.tag, item.author, item.type, item.keywords].join(' ').toLowerCase()
  const matchesSearch = !searchQuery.value || searchableText.includes(searchQuery.value)
  const matchesStage = selectedStage.value === '全部学段' || item.stage === selectedStage.value || item.stage === '通用'
  const matchesSubject = selectedSubject.value === '全部学科' || item.subject === selectedSubject.value || item.subject === '通用'
  return matchesSearch && matchesStage && matchesSubject
}

/** 根据当前页签和筛选条件生成社区卡片；选择了排序维度时交由后端排序，「最新」仅在前端按更新时间排序。 */
const filteredCards = computed(() => {
  if (!usingDemoCards.value) return communityCards.value
  const filtered = communityCards.value.filter((card) => {
    const matchesTab = activeTab.value === '精选'
      || activeTab.value === 'Skill' && card.type === 'Skill'
      || activeTab.value === '教学案例' && card.type === '案例'
      || activeTab.value === 'PPT 课件' && card.type === 'PPT'
      || activeTab.value === '最新'
    return matchesTab && matchesFilters(card)
  })
  return activeTab.value === '最新' && !sortBy.value ? [...filtered].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)) : filtered
})

/** 判断精选案例是否仍应展示。 */
const showFeatured = computed(() => usingDemoCards.value && activeTab.value === '精选' && matchesFilters(COMMUNITY_PAGE.featured))

/** 打开复用配置：先展示版本、授权、输入变量和个人资源绑定，再创建派生项目。 */
const openReuse = async (item) => {
  if (!item?.id && !item?.testCaseId) {
    ElMessage.info('该内容暂时无法创建派生项目')
    return
  }
  reuseTarget.value = item
  reuseDetail.value = item.testCaseId ? item : null
  reuseProjectName.value = `${item.title || '未命名内容'}（副本）`
  reuseSelectedResourceIds.value = []
  reuseResources.value = []
  reuseVisible.value = true
  reuseLoading.value = Boolean(item.id)
  try {
    if (item.id) reuseDetail.value = unwrap(assertApiSuccess(await getCommunityItem(item.id)))
    const source = reuseDetail.value || item
    reuseVariables.value = normalizeInputVariables(source.input_variables)
    reuseVariableValues.value = Object.fromEntries(reuseVariables.value.map((variable) => [variable.key, normalizedVariableValue(variable)]))
    reuseVersion.value = Number(source.version || 1)
    reuseResourcesLoading.value = true
    try {
      const response = unwrap(assertApiSuccess(await listResources({ page: 1, size: 100 })))
      const candidates = Array.isArray(response) ? response : response?.records || response?.items || response?.list || response?.resources || []
      const records = Array.isArray(candidates) ? candidates : []
      reuseResources.value = records.map(normalizeReuseResource).filter(Boolean)
    } catch (error) {
      reuseResources.value = []
      ElMessage.warning(error?.message || '个人资源加载失败，仍可不绑定素材继续复用')
    } finally {
      reuseResourcesLoading.value = false
    }
  } catch (error) {
    reuseVisible.value = false
    ElMessage.error(error?.message || '社区内容详情加载失败')
  } finally {
    reuseLoading.value = false
  }
}

/** 复制社区内容并进入个人创作工作台。 */
const reuse = async (item) => openReuse(item)

const removeReuseResource = (id) => {
  reuseSelectedResourceIds.value = reuseSelectedResourceIds.value.filter((item) => String(item) !== String(id))
}

const finishReuse = async () => {
  const item = reuseTarget.value
  const source = reuseDetail.value || item
  if (!source) return
  reuseLoading.value = true
  const context = reuseContext.value
  try {
    if (item?.testCaseId) {
      reuseVisible.value = false
      ElMessage.success('测试案例已载入创作工作台')
      await router.push({
        path: '/main/workspace',
        query: {
          testCase: item.testCaseId,
          templateTitle: source.title,
          communityType: context.type,
          communityId: context.id || item.testCaseId,
          resourceIds: JSON.stringify(context.resource_ids),
          workspaceContext: JSON.stringify({ community: context, resource_ids: context.resource_ids, resourceIds: context.resource_ids }),
        },
      })
      return
    }
    const result = await reuseCommunityItem(source.id, {
      target_version: Number(reuseVersion.value) || Number(source.version) || 1,
      bind_materials: JSON.stringify(context.resource_ids),
    })
    const project = unwrap(assertApiSuccess(result))
    const projectId = project?.id || project?.project_id
    const savedContext = parseJsonValue(project?.edit_history, {})?.workspace_context || {}
    const selectedContext = {
      ...context,
      community: savedContext.community
        ? { ...context, ...savedContext.community, resource_ids: context.resource_ids, resourceIds: context.resource_ids }
        : context,
    }
    if (projectId) {
      try {
        await assertApiSuccess(await patchProject(projectId, {
          project_name: reuseProjectName.value.trim() || `${source.title || '未命名内容'}（副本）`,
          edit_history: JSON.stringify({ workspace_context: selectedContext }),
          current_version: Number(project?.current_version || 1),
        }))
      } catch (error) {
        ElMessage.warning(error?.message || '派生项目已创建，但复用上下文暂未同步；进入工作台后仍可重新保存')
      }
    }
    reuseVisible.value = false
    ElMessage.success('已按所选版本和素材绑定复制到个人空间')
    await router.push({
      path: '/main/workspace',
      query: {
        ...(projectId ? { projectId } : {}),
        communityType: context.type,
        communityId: source.id,
        resourceIds: JSON.stringify(context.resource_ids),
        workspaceContext: JSON.stringify(selectedContext),
      },
    })
  } catch (error) {
    ElMessage.error(error?.message || '无法创建派生项目，请稍后重试')
  } finally {
    reuseLoading.value = false
  }
}
const unwrap = (value) => value?.data || value
const assertApiSuccess = (value) => {
  const code = Number(value?.code)
  if (Number.isFinite(code) && code !== 0 && code !== 200) throw new Error(value?.message || `接口请求失败（${code}）`)
  return value
}
const favoriteItem = (row) => row?.item || row || {}
const favoriteItemId = (row) => favoriteItem(row)?.id ?? favoriteItem(row)?.item_id ?? row?.itemId ?? null
const setFavoriteState = (rows) => {
  favorites.value = rows
  favoriteIds.value = new Set(rows.map(favoriteItemId).filter((id) => id !== null && id !== undefined).map((id) => String(id)))
}
const loadFavoriteState = async () => {
  try { setFavoriteState(extractRecords(assertApiSuccess(await listCommunityFavorites({ page: 1, size: 100 })))) } catch { /* 未登录时由列表页错误态提示，避免首屏重复弹窗。 */ }
}
const updateVisibleMetric = (id, field, delta, liked) => {
  communityCards.value = communityCards.value.map((card) => String(card.id) === String(id)
    ? { ...card, [field]: Math.max(0, card[field] + delta), ...(liked === undefined ? {} : { liked }) }
    : card)
  if (detail.value && String(detail.value.id) === String(id)) {
    const key = field === 'likes' ? 'like_count' : 'favorite_count'
    detail.value = { ...detail.value, [key]: Math.max(0, Number(detail.value[key] || 0) + delta), ...(liked === undefined ? {} : { liked }) }
  }
}
const toggleFavorite = async (item) => {
  const rawId = item?.id ?? item?.item_id ?? item?.testCaseId
  if (rawId === null || rawId === undefined || rawId === '') return ElMessage.info('该内容暂不支持收藏')
  const favoriteKey = String(rawId)
  const next = !favoriteIds.value.has(favoriteKey)
  const previousIds = new Set(favoriteIds.value)
  const previousFavorites = [...favorites.value]
  const updated = new Set(previousIds)
  next ? updated.add(favoriteKey) : updated.delete(favoriteKey)
  favoriteIds.value = updated
  if (item.testCaseId && !item.id) {
    ElMessage.success(next ? '已收藏测试案例' : '已取消收藏')
    return
  }
  try {
    if (next) await assertApiSuccess(await favoriteCommunityItem(rawId)); else await assertApiSuccess(await unfavoriteCommunityItem(rawId))
    if (next) {
      const existing = favorites.value.some((row) => String(favoriteItemId(row)) === favoriteKey)
      if (!existing) favorites.value = [{ ...(item.raw || item), id: rawId }, ...favorites.value]
    } else {
      favorites.value = favorites.value.filter((row) => String(favoriteItemId(row)) !== favoriteKey)
    }
    updateVisibleMetric(rawId, 'favorites', next ? 1 : -1)
    if (sortBy.value === 'favorite') loadCommunity()
    ElMessage.success(next ? '已收藏' : '已取消收藏')
  } catch (error) {
    favoriteIds.value = previousIds
    favorites.value = previousFavorites
    ElMessage.error(error?.message || '收藏状态未能更新')
  }
}

// ------------------ 功能11：点赞与热门榜单 ------------------
/** 点赞图标路径（Element Plus 图标库无 thumbs-up，Material thumb_up 单处维护） */
const LIKE_ICON_PATH = 'M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z'
/** 进行中的点赞请求集合：防连点产生交错请求 */
const likePendingIds = ref(new Set())

/** 将后端返回的 liked 字段同步进点赞态集合（分页/刷新后保持一致）。 */
const syncLikeState = (records) => {
  const next = new Set(likedIds.value)
  records.forEach((item) => {
    if (item?.id === null || item?.id === undefined) return
    const key = String(item.id)
    item.liked ? next.add(key) : next.delete(key)
  })
  likedIds.value = next
}

/** 本地点赞计数即时反馈：列表卡片、详情弹窗与榜单行同步增减，接口失败时由调用方回滚。 */
const adjustLocalLikeCount = (rawId, liked) => {
  communityCards.value = communityCards.value.map((card) => (
    String(card.id) === String(rawId) ? { ...card, likes: Math.max(0, card.likes + (liked ? 1 : -1)), liked } : card
  ))
  rankItems.value = rankItems.value.map((row) => (
    String(row.id) === String(rawId) ? { ...row, likes: Math.max(0, row.likes + (liked ? 1 : -1)) } : row
  ))
  if (detail.value && String(detail.value.id) === String(rawId)) {
    detail.value = {
      ...detail.value,
      liked,
      like_count: Math.max(0, Number(detail.value.like_count ?? 0) + (liked ? 1 : -1)),
    }
  }
}

/** 点赞/取消点赞（乐观更新；后端唯一索引幂等；同内容请求进行中时忽略重复点击）。 */
const toggleLike = async (item) => {
  const rawId = item?.id ?? item?.item_id
  if (rawId === null || rawId === undefined || rawId === '') return ElMessage.info('该内容暂不支持点赞')
  if (item.testCaseId && !item.id) return ElMessage.info('演示内容暂不支持点赞')
  const key = String(rawId)
  if (likePendingIds.value.has(key)) return
  const next = !likedIds.value.has(key)
  const previousIds = likedIds.value
  const pending = new Set(likePendingIds.value)
  pending.add(key)
  likePendingIds.value = pending
  likedIds.value = next ? new Set([...previousIds, key]) : new Set([...previousIds].filter((id) => id !== key))
  adjustLocalLikeCount(rawId, next)
  try {
    if (next) await assertApiSuccess(await likeCommunityItem(rawId)); else await assertApiSuccess(await unlikeCommunityItem(rawId))
    ElMessage.success(next ? '已点赞' : '已取消点赞')
  } catch (error) {
    likedIds.value = previousIds
    adjustLocalLikeCount(rawId, !next)
    ElMessage.error(error?.message || '点赞状态未能更新')
  } finally {
    const rest = new Set(likePendingIds.value)
    rest.delete(key)
    likePendingIds.value = rest
  }
}

let rankRequestSeq = 0
/** 榜单行归一：RankItemVO{rank, hot_score, content} → 展示字段。 */
const normalizeRankRow = (row = {}) => {
  const content = row.content || row.item || {}
  return {
    rank: Number(row.rank ?? 0),
    score: Number(row.hot_score ?? row.hotScore ?? 0),
    id: content.id ?? content.item_id,
    title: content.title || '未命名内容',
    author: content.author_name || content.author || (content.author_id ? `用户 #${content.author_id}` : '社区教师'),
    likes: Number(content.like_count ?? content.likeCount ?? 0),
    uses: Number(content.use_count ?? content.useCount ?? 0),
  }
}

/** 加载热门榜单：内容类型 × 时间段，Top10；ZSET 缺失时后端自动降级 DB 聚合。 */
const loadRankings = async () => {
  const requestSeq = ++rankRequestSeq
  rankLoading.value = true
  rankError.value = ''
  try {
    const result = assertApiSuccess(await listCommunityRankings({
      content_type: rankType.value,
      period: rankPeriod.value,
      limit: 10,
    }))
    if (requestSeq !== rankRequestSeq) return
    rankItems.value = extractRecords(result).map(normalizeRankRow)
  } catch (error) {
    if (requestSeq !== rankRequestSeq) return
    rankItems.value = []
    rankError.value = error?.message || '热门榜单加载失败'
  } finally {
    if (requestSeq === rankRequestSeq) rankLoading.value = false
  }
}

const openDetail = async (item) => {
  const rawId = item?.id ?? item?.item_id ?? item?.testCaseId
  if (rawId === null || rawId === undefined || rawId === '') return ElMessage.info('该内容暂时没有可查看的详情')
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = ''
  try {
    const source = item?.testCaseId && !item?.id
      ? (item.raw || item)
      : unwrap(assertApiSuccess(await getCommunityItem(rawId)))
    if (!source) throw new Error('未找到社区内容')
    detail.value = { ...source, id: source.id ?? rawId, content_type: normalizeCommunityContentType(source) }
    detailContentView.value = detailLessonPlan.value ? 'lesson_plan' : detailSlides.value.length ? 'ppt' : 'overview'
    try { await assertApiSuccess(await recordCommunityView(rawId)) } catch { /* 浏览事件失败不阻塞详情查看。 */ }
    activeDetailSlideIndex.value = 0
  } catch (error) {
    detail.value = null
    detailError.value = error?.message || '内容详情加载失败，请稍后重试'
  } finally {
    detailLoading.value = false
  }
}

const loadCollections = async () => {
  collectionsLoading.value = true
  collectionError.value = ''
  const [favoriteResult, recentResult] = await Promise.allSettled([
    listCommunityFavorites({ page: 1, size: 30 }),
    listCommunityRecentViews({ page: 1, size: 30 }),
  ])
  let favoriteError = favoriteResult.status === 'rejected' ? favoriteResult.reason : null
  let recentError = recentResult.status === 'rejected' ? recentResult.reason : null
  if (favoriteResult.status === 'fulfilled') {
    try { setFavoriteState(extractRecords(assertApiSuccess(favoriteResult.value))) } catch (error) { favoriteError = error; setFavoriteState([]) }
  }
  if (recentResult.status === 'fulfilled') {
    try { recentViews.value = extractRecords(assertApiSuccess(recentResult.value)) } catch (error) { recentError = error; recentViews.value = [] }
  }
  if (favoriteError || recentError) {
    collectionError.value = favoriteError?.message || recentError?.message || '收藏或浏览记录加载失败，请重试'
  }
  collectionsLoading.value = false
}
const openCollections = async () => {
  collectionVisible.value = true
  await loadCollections()
}
const removeView = async (row) => {
  const id = recentViewId(row)
  if (id === null || id === undefined || id === '') return ElMessage.info('该浏览记录缺少内容 ID')
  try {
    await assertApiSuccess(await removeCommunityRecentView(id))
    recentViews.value = recentViews.value.filter((item) => String(recentViewId(item)) !== String(id))
    ElMessage.success('已删除浏览记录')
  } catch (error) { ElMessage.error(error?.message || '浏览记录删除失败') }
}

const openSubmission = async () => {
  submission.value = emptySubmission()
  hydrateSubmissionEditors()
  submissionError.value = ''
  submissionVisible.value = true
  try { submissions.value = extractRecords(assertApiSuccess(await listCommunitySubmissions({ page: 1, size: 20 }))) } catch (error) {
    submissions.value = []
    submissionError.value = error?.message || '投稿草稿加载失败，请稍后重试'
  }
}
const saveSubmission = async (submit = false) => {
  submissionError.value = ''
  let payload
  try { payload = normalizeSubmissionPayload() } catch (error) {
    submissionError.value = error?.message || '请检查投稿内容'
    return ElMessage.warning(submissionError.value)
  }
  submissionSaving.value = true
  try {
    const saved = submission.value.id
      ? unwrap(assertApiSuccess(await updateCommunitySubmission(submission.value.id, payload)))
      : unwrap(assertApiSuccess(await createCommunitySubmission(payload)))
    const savedId = saved?.id ?? submission.value.id
    if (savedId === null || savedId === undefined) throw new Error('投稿保存成功，但未返回投稿 ID')
    submission.value = { ...submission.value, ...saved, ...payload, id: savedId }
    const versionResult = assertApiSuccess(await saveCommunitySubmissionVersion(savedId, { description: submit ? '教师提交前保存投稿版本' : '教师保存投稿草稿' }))
    const versionData = unwrap(versionResult)
    if (versionData?.version_number) submission.value.version = versionData.version_number
    if (submit) {
      await assertApiSuccess(await submitCommunitySubmission(savedId, { source_declaration: '本人原创或已获得授权', notes: '' }))
      submission.value.status = 'reviewing'
    }
    submissions.value = submissions.value.some((item) => String(item.id) === String(savedId))
      ? submissions.value.map((item) => String(item.id) === String(savedId) ? { ...item, ...submission.value } : item)
      : [submission.value, ...submissions.value]
    ElMessage.success(submit ? '投稿已提交审核' : '投稿草稿已保存')
  } catch (error) {
    submissionError.value = error?.message || '投稿保存失败，请稍后重试'
    ElMessage.error(submissionError.value)
  } finally { submissionSaving.value = false }
}

const loadReports = async () => {
  reportsLoading.value = true
  try { reports.value = extractRecords(assertApiSuccess(await listCommunityReports({ page: 1, size: 30 }))) } catch (error) {
    reports.value = []
    ElMessage.error(error?.message || '举报记录加载失败，请稍后重试')
  } finally { reportsLoading.value = false }
}
const openReports = async () => {
  reportVisible.value = true
  await loadReports()
}
const openReportDetail = async (report) => {
  if (!report?.id) return
  reportDetail.value = null
  reportDetailVisible.value = true
  reportDetailLoading.value = true
  try { reportDetail.value = unwrap(assertApiSuccess(await getCommunityReport(report.id))) } catch (error) {
    reportDetail.value = { ...report, detail_error: error?.message || '举报详情加载失败' }
  } finally { reportDetailLoading.value = false }
}
const openReportForDetail = () => {
  if (!detail.value?.id || !Number.isInteger(Number(detail.value.id))) return ElMessage.info('演示内容没有可用的举报 ID')
  reportForm.value = { target_type: normalizeCommunityContentType(detail.value), target_id: detail.value.id, reason: '', comment: '' }
  detailVisible.value = false
  reportVisible.value = true
}
const reportItem = async () => {
  const targetId = Number(reportForm.value.target_id)
  if (!Number.isInteger(targetId) || targetId <= 0) return ElMessage.warning('请输入有效的内容 ID')
  if (!['skill', 'lesson_case'].includes(reportForm.value.target_type)) return ElMessage.warning('请选择有效的内容类型')
  if (!String(reportForm.value.reason || '').trim()) return ElMessage.warning('请填写举报原因')
  try {
    await assertApiSuccess(await createCommunityReport({
      audit_type: 'report',
      target_type: reportForm.value.target_type,
      target_id: targetId,
      reason: String(reportForm.value.reason).trim(),
      comment: String(reportForm.value.comment || '').trim(),
    }))
    ElMessage.success('举报已提交')
    reportForm.value = { target_type: 'lesson_case', target_id: null, reason: '', comment: '' }
    await loadReports()
  } catch (error) { ElMessage.error(error?.message || '举报提交失败') }
}

watch([activeTab, selectedStage, selectedSubject], () => {
  communityPage.value = 1
  loadCommunity()
})
// 功能11：排序维度/时间段变化即时重查；榜单类型/时间段变化即时重查
watch([sortBy, sortPeriod], () => {
  communityPage.value = 1
  loadCommunity()
})
watch([rankType, rankPeriod], loadRankings)
onMounted(() => {
  loadCommunity()
  loadFavoriteState()
  loadRankings()
})
</script>

<template>
  <div class="community-page">
    <header class="community-hero">
      <p>教师共创社区 / Community</p>
      <h1><span>把好课的经验，</span><span>变成下一堂课的起点</span></h1>
      <span>按主题寻找可复用的 PPT 课件、Skill 与教学案例；复用后生成独立草稿，不会修改社区原件。</span>
      <div class="community-search-row">
        <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索 PPT 主题、知识点、学科或课型" clearable size="large" @keyup.enter="submitSearch">
          <template #append><el-button type="primary" class="community-search-button" @click="submitSearch">搜索</el-button></template>
        </el-input>
        <el-button type="primary" class="submission-button" @click="openSubmission">我要投稿</el-button>
      </div>
    </header>

    <div class="community-toolbar">
      <div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ tab }}</button></div>
      <div class="toolbar-controls">
        <button type="button" class="mobile-filter-toggle" :aria-expanded="showMobileFilters" aria-controls="community-filters" @click="showMobileFilters = !showMobileFilters">筛选与排序 <span aria-hidden="true">{{ showMobileFilters ? '−' : '＋' }}</span></button>
        <el-button text @click="openCollections">收藏与浏览</el-button>
        <el-button text @click="openReports">举报进度</el-button>
        <div id="community-filters" class="filters" :class="{ 'mobile-open': showMobileFilters }">
          <el-select v-model="selectedStage" aria-label="筛选学段"><el-option label="全部学段" value="全部学段" /><el-option label="初中" value="初中" /><el-option label="高中" value="高中" /></el-select>
          <el-select v-model="selectedSubject" aria-label="筛选学科"><el-option label="全部学科" value="全部学科" /><el-option label="数学" value="数学" /><el-option label="物理" value="物理" /><el-option label="语文" value="语文" /><el-option label="生物" value="生物" /></el-select>
          <el-select v-model="sortBy" aria-label="排序方式" placeholder="默认排序">
            <el-option label="默认排序" value="" />
            <el-option v-for="option in sortOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
          <el-select v-model="sortPeriod" aria-label="时间范围" :disabled="!sortBy">
            <el-option label="全部时间" value="all" />
            <el-option label="近 1 天" value="day" />
            <el-option label="近 7 天" value="week" />
            <el-option label="近 30 天" value="month" />
          </el-select>
        </div>
      </div>
    </div>

    <div class="community-status-row" aria-live="polite">
      <span v-if="usingDemoCards">演示内容</span>
      <span v-else>{{ communityTotal }} 项公开内容</span>
      <el-tag v-if="usingDemoCards" size="small" effect="plain">预览数据</el-tag>
      <span v-if="loading" class="status-muted">正在同步社区目录…</span>
    </div>
    <div v-if="communityError" class="community-error" role="alert">
      <span>{{ communityError }}</span>
      <el-button text type="primary" @click="loadCommunity">重试</el-button>
    </div>

    <section class="rank-section" aria-label="热门榜单">
      <header class="rank-header">
        <div class="rank-title"><el-icon><Trophy /></el-icon><h2>{{ rankTitle }}</h2></div>
        <div class="rank-controls">
          <el-segmented v-model="rankPeriod" :options="rankPeriodTabs" size="small" aria-label="榜单时间段" />
          <el-segmented v-model="rankType" :options="rankTypeTabs" size="small" aria-label="榜单内容类型" />
        </div>
      </header>
      <div v-loading="rankLoading" class="rank-list">
        <article v-for="row in rankItems" :key="row.id" class="rank-row" role="button" tabindex="0" :aria-label="`第 ${row.rank} 名 ${row.title}`" @click="openDetail({ id: row.id })" @keydown.enter.prevent="openDetail({ id: row.id })" @keydown.space.prevent="openDetail({ id: row.id })">
          <span class="rank-badge" :class="{ top: row.rank <= 3 }">{{ row.rank }}</span>
          <div class="rank-info"><strong>{{ row.title }}</strong><span>{{ row.author }} · {{ row.likes }} 赞 · {{ row.uses }} 次使用</span></div>
          <span class="rank-score" :title="`热度 ${row.score.toFixed(1)}`">{{ row.score.toFixed(1) }}</span>
        </article>
        <el-empty v-if="!rankLoading && !rankError && rankItems.length === 0" class="rank-empty" description="近期互动还未达标，暂无上榜内容" />
        <div v-if="rankError" class="rank-error" role="alert">
          <span>{{ rankError }}</span>
          <el-button text type="primary" @click="loadRankings">重试</el-button>
        </div>
      </div>
    </section>

    <section v-if="showFeatured" class="featured-case">
      <div class="feature-visual">
        <span>3² + 4² = 5²</span>
        <i></i><i></i><i></i>
      </div>
      <div class="feature-copy">
        <el-tag effect="plain">{{ COMMUNITY_PAGE.featured.type }}</el-tag>
        <h2>{{ COMMUNITY_PAGE.featured.title }}</h2>
        <p>{{ COMMUNITY_PAGE.featured.description }}</p>
        <dl><div><dt>适用范围</dt><dd>{{ COMMUNITY_PAGE.featured.meta }}</dd></div><div><dt>作者</dt><dd>{{ COMMUNITY_PAGE.featured.author }}</dd></div></dl>
        <footer><span>{{ COMMUNITY_PAGE.featured.uses }}</span><el-button type="primary" @click="reuse(COMMUNITY_PAGE.featured)">基于此创作</el-button></footer>
      </div>
    </section>

    <section v-loading="loading" class="community-grid" aria-label="社区内容">
      <article v-for="card in filteredCards" :key="card.id || card.testCaseId || card.title" class="community-card" data-hover-lift role="button" tabindex="0" @click="openDetail(card)" @keydown.enter.prevent="openDetail(card)" @keydown.space.prevent="openDetail(card)">
        <div class="card-top"><span>{{ card.type }}</span><div class="card-top-actions"><button class="card-like" :class="{ active: likedIds.has(String(card.id)) }" :aria-pressed="likedIds.has(String(card.id))" aria-label="点赞" @click.stop="toggleLike(card)"><svg viewBox="0 0 24 24" aria-hidden="true"><path :d="LIKE_ICON_PATH" /></svg><span>{{ card.likes }}</span></button><el-button text circle :type="favoriteIds.has(String(card.id ?? card.testCaseId)) ? 'warning' : undefined" aria-label="收藏" @click.stop="toggleFavorite(card)"><el-icon><Star /></el-icon></el-button></div></div>
        <div class="card-icon"><el-icon><CollectionTag /></el-icon></div>
        <h3>{{ card.title }}</h3>
        <p>{{ card.subject }} · {{ card.tag }}</p>
        <p v-if="card.description" class="card-description">{{ card.description }}</p>
        <div class="card-metrics"><span>收藏 {{ card.favorites }}</span><span>复用 {{ card.uses }}</span></div>
        <footer><span><el-icon><User /></el-icon>{{ card.author }}</span><div class="card-actions"><button class="card-detail" @click.stop="openDetail(card)">查看详情</button><button @click.stop="reuse(card)">{{ card.testCaseId ? '进入工作台 →' : `${card.uses} 次使用 →` }}</button></div></footer>
      </article>
      <el-empty v-if="filteredCards.length === 0" class="community-empty" description="没有符合当前筛选条件的课件或教学内容" />
    </section>
    <el-pagination v-if="communityTotal > communityPageSize" class="community-pagination" :current-page="communityPage" :page-size="communityPageSize" :total="communityTotal" layout="prev, pager, next" background @current-change="changeCommunityPage" />
    <p class="source-note">所有内容均标记来源、版本与授权信息；个人私有素材不会写回社区或进入公共索引。</p>
  </div>
    <el-dialog v-model="submissionVisible" class="community-submission-dialog" modal-class="community-submission-backdrop" width="min(1080px, calc(100vw - 32px))" :show-close="false" :close-on-click-modal="false">
      <div v-loading="submissionSaving || submissionLoading" class="submission-dialog">
        <header class="submission-header">
          <div class="submission-heading">
            <div class="submission-kicker"><span class="submission-kicker-mark" aria-hidden="true"></span><span>投稿工作台</span><span v-if="submission.id" class="submission-version">v{{ submission.version || 1 }}</span></div>
            <h2>{{ submissionReadOnly ? '投稿详情' : '整理后提交给教师社区' }}</h2>
            <p>{{ submissionReadOnly ? '内容已进入审核流程，以下为提交时的结构化摘要。' : '先整理课堂信息与可复用内容，再提交给教师社区审核。' }}</p>
          </div>
          <button class="submission-close-button" aria-label="关闭投稿窗口" @click="submissionVisible = false"><span aria-hidden="true">×</span></button>
        </header>

        <div class="submission-layout">
          <main class="submission-main">
            <el-alert v-if="submissionError" class="submission-inline-alert" :title="submissionError" type="error" show-icon :closable="false" />
            <div v-if="submissionReadOnly" class="submission-readonly-notice"><span>审核状态</span><strong>{{ statusLabel(submission.status) }}</strong><p>审核期间保留当前版本，仅支持查看。</p></div>

            <el-form label-position="top" :disabled="submissionReadOnly" class="submission-form">
              <section class="submission-section">
                <header class="submission-section-heading"><div><span>基本信息</span><h3>这份内容适合什么课堂</h3></div><small>带 * 的内容为必填项</small></header>
                <div class="submission-meta-grid">
                  <el-form-item class="submission-title-field" label="标题" required><el-input v-model="submission.title" maxlength="120" show-word-limit placeholder="用一句话说明案例主题" /></el-form-item>
                  <el-form-item label="内容类型" required><el-select v-model="submission.content_type"><el-option label="教学案例" value="lesson_case" /><el-option label="Skill" value="skill" /><el-option label="PPT 课件（请从课件工作台发布）" value="ppt" disabled /></el-select></el-form-item>
                  <el-form-item label="学科"><el-input v-model="submission.subject" placeholder="例如 数学" /></el-form-item>
                  <el-form-item label="学段"><el-input v-model="submission.grade" placeholder="例如 初中" /></el-form-item>
                  <el-form-item label="课型"><el-input v-model="submission.lesson_type" placeholder="例如 探究课" /></el-form-item>
                  <el-form-item label="检索关键词"><el-input v-model="submission.keywords" placeholder="例如 分数、探究课、三年级" /></el-form-item>
                  <el-form-item label="授权许可" required><el-input v-model="submission.license" placeholder="例如 CC BY-NC 4.0" /></el-form-item>
                  <el-form-item class="submission-effect-field" label="示例效果"><el-input v-model="submission.example_effect" placeholder="简述预期教学效果" /></el-form-item>
                </div>
                <el-form-item class="submission-summary-field" label="简介"><el-input v-model="submission.description" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="说明案例的使用场景、教学重点或适用人群" /></el-form-item>
              </section>

              <section class="submission-section submission-content-section">
                <header class="submission-section-heading submission-content-heading"><div><span>内容概览</span></div></header>
                <div class="submission-metric-grid"><div v-for="metric in submissionContentMetrics" :key="metric.label"><strong>{{ metric.value }}</strong><span>{{ metric.label }}</span></div></div>
                <el-form-item label="教学目标 / 内容说明"><el-input v-model="submissionContentEditor.objective" type="textarea" :rows="3" maxlength="400" show-word-limit placeholder="例如：引导学生用实验现象解释光的折射规律" /></el-form-item>

                <section v-if="submissionSlidePreviewList.length" class="submission-slides">
                  <header><strong>课件章节</strong><span>{{ submissionSlidePreviews.length }} 页内容已载入</span></header>
                  <div class="submission-slide-list"><article v-for="slide in submissionSlidePreviewList" :key="slide.number" class="submission-slide-card"><span>{{ String(slide.number).padStart(2, '0') }}</span><div><strong>{{ slide.title }}</strong><p>{{ slide.note || slide.layout || '已关联课件页面' }}</p></div></article></div>
                  <p v-if="submissionHiddenSlideCount" class="submission-more-slides">还有 {{ submissionHiddenSlideCount }} 页内容已保留在投稿数据中。</p>
                </section>

                <section class="submission-flow-editor">
                  <header><div><strong>教学环节</strong><span>用清晰的步骤帮助其他教师快速判断是否适用</span></div><button v-if="!submissionReadOnly" type="button" class="submission-text-action" @click="addSubmissionStep">添加环节</button></header>
                  <ol v-if="submissionContentEditor.steps.length" class="submission-flow-list"><li v-for="(step, index) in submissionContentEditor.steps" :key="`${index}-${step.raw?.id || step.text}`"><span>{{ index + 1 }}</span><el-input v-model="step.text" placeholder="例如：情境导入" /><button v-if="!submissionReadOnly" type="button" aria-label="删除教学环节" @click="removeSubmissionStep(index)">×</button></li></ol>
                  <div v-else class="submission-empty-flow"><strong>{{ submissionHasContent ? '尚未提炼教学环节' : '从一句教学目标开始' }}</strong><span>{{ submissionReadOnly ? '该投稿未提供可单列的教学环节。' : '添加 3–5 个环节，能让社区教师更快理解你的课堂设计。' }}</span></div>
                </section>
              </section>

              <section class="submission-section submission-variable-section">
                <header class="submission-section-heading"><div><span>复用设置</span><h3>其他教师复用前需要补充什么</h3></div><button v-if="!submissionReadOnly" type="button" class="submission-text-action" @click="addSubmissionVariable">添加输入项</button></header>
                <p class="submission-section-intro">输入项会在他人配置复用时生成表单；不需要额外信息时可留空。</p>
                <div v-if="submissionVariableEditor.length" class="submission-variable-list"><article v-for="(variable, index) in submissionVariableEditor" :key="`${variable.key}-${index}`" class="submission-variable-row"><span class="submission-variable-index">{{ index + 1 }}</span><div class="submission-variable-fields"><el-input v-model="variable.label" placeholder="输入项名称" /><el-input v-model="variable.key" placeholder="字段标识" /><el-select v-model="variable.type"><el-option label="单行文本" value="text" /><el-option label="多行文本" value="textarea" /><el-option label="数字" value="number" /></el-select><el-switch v-model="variable.required" inline-prompt active-text="必填" inactive-text="可选" /></div><el-input v-model="variable.description" class="submission-variable-description" placeholder="给复用者的填写说明（可选）" /><button v-if="!submissionReadOnly" type="button" class="submission-variable-delete" aria-label="删除输入项" @click="removeSubmissionVariable(index)">×</button></article></div>
                <div v-else class="submission-variable-empty"><strong>无需额外输入</strong><span>复用时将直接复制当前案例结构。</span></div>
              </section>
            </el-form>
          </main>

          <aside class="submission-aside">
            <section class="submission-aside-card submission-status-card"><span>投稿状态</span><strong>{{ submission.id ? statusLabel(submission.status) : '待保存' }}</strong><p>{{ submissionReadOnly ? '等待审核结果后将同步到社区。' : '保存草稿后可继续补充，提交后进入审核。' }}</p></section>
            <section class="submission-aside-card submission-attribute-card"><span>投稿信息</span><dl><div><dt>当前版本</dt><dd>v{{ submission.version || 1 }}</dd></div><div><dt>内容类型</dt><dd>{{ normalizeCommunityType(submission) }}</dd></div><div><dt>授权许可</dt><dd>{{ submission.license || '未填写' }}</dd></div></dl></section>
            <section class="submission-aside-card submission-drafts-card"><header><span>我的投稿</span><small>{{ submissions.length }} 条</small></header><div v-if="submissions.length" class="submission-draft-list"><button v-for="item in submissions" :key="item.id" type="button" :class="{ active: String(item.id) === String(submission.id) }" @click="selectSubmissionDraft(item)"><strong>{{ item.title || `投稿 #${item.id}` }}</strong><span>{{ statusLabel(item.status) }} · v{{ item.version || 1 }}</span></button></div><div v-else class="submission-draft-empty">保存草稿后会显示在这里。</div></section>
            <p class="submission-aside-note">提交审核后内容会锁定，审核通过后才会出现在教师社区。</p>
          </aside>
        </div>
      </div>
      <template #footer><el-button :disabled="submissionSaving || submissionLoading" @click="submissionVisible = false">{{ submissionReadOnly ? '关闭' : '稍后继续' }}</el-button><el-button v-if="!submissionReadOnly" :loading="submissionSaving" :disabled="submissionLoading" @click="saveSubmission(false)">保存草稿</el-button><el-button v-if="!submissionReadOnly" type="primary" :loading="submissionSaving" :disabled="submissionLoading" @click="saveSubmission(true)">提交审核</el-button></template>
    </el-dialog>
    <el-dialog v-model="collectionVisible" class="community-collection-dialog" title="我的收藏与最近浏览" width="min(680px, 92vw)">
      <div v-loading="collectionsLoading">
        <el-alert v-if="collectionError" :title="collectionError" type="error" show-icon :closable="false"><template #default><el-button text type="primary" @click="loadCollections">重试</el-button></template></el-alert>
        <section class="collection-section">
          <h3>我的收藏</h3>
          <div v-for="row in favorites" :key="favoriteItemId(row)" class="collection-row">
            <button class="collection-item-link" @click="openDetail(favoriteItem(row))">{{ favoriteItem(row).title || `内容 #${favoriteItemId(row)}` }}</button>
            <el-button text size="small" @click="toggleFavorite(favoriteItem(row))">取消收藏</el-button>
          </div>
          <el-empty v-if="!favorites.length" description="暂无收藏" />
        </section>
        <section class="collection-section">
          <h3>最近浏览</h3>
          <div v-for="row in recentViews" :key="recentViewId(row)" class="collection-row">
            <button class="collection-item-link" @click="openDetail(recentViewItem(row))">{{ recentViewTitle(row) }}</button>
            <div><el-button text size="small" @click="openDetail(recentViewItem(row))">查看</el-button><el-button text size="small" type="danger" @click="removeView(row)">删除</el-button></div>
          </div>
          <el-empty v-if="!recentViews.length" description="暂无浏览记录" />
        </section>
      </div>
    </el-dialog>
    <el-dialog v-model="reportVisible" class="community-report-dialog" title="举报与处理进度" width="min(640px, 92vw)">
      <div v-loading="reportsLoading" class="report-dialog">
        <el-form label-position="top" class="report-form-grid">
          <el-form-item label="内容类型" required><el-select v-model="reportForm.target_type"><el-option label="教学案例" value="lesson_case" /><el-option label="Skill" value="skill" /><el-option label="PPT 课件" value="ppt" /></el-select></el-form-item>
          <el-form-item label="内容 ID" required><el-input v-model="reportForm.target_id" inputmode="numeric" placeholder="请输入社区内容 ID" /></el-form-item>
          <el-form-item label="举报原因" required><el-input v-model="reportForm.reason" maxlength="120" show-word-limit placeholder="例如：内容疑似侵权" /></el-form-item>
          <el-form-item label="补充说明"><el-input v-model="reportForm.comment" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        </el-form>
        <el-button type="primary" @click="reportItem">提交举报</el-button>
        <div class="report-list"><h3>我的举报记录</h3><div v-for="report in reports" :key="report.id" class="report-row"><span>#{{ report.id }} · {{ statusLabel(report.status) }} · {{ report.reason || report.comment || '未填写原因' }}</span><el-button text size="small" @click="openReportDetail(report)">查看详情</el-button></div><el-empty v-if="!reports.length" description="暂无举报记录" /></div>
      </div>
    </el-dialog>
    <el-dialog v-model="reportDetailVisible" class="community-report-detail-dialog" title="举报详情" width="min(560px, 92vw)">
      <div v-loading="reportDetailLoading" class="report-detail">
        <el-alert v-if="reportDetail?.detail_error" :title="reportDetail.detail_error" type="error" show-icon :closable="false" />
        <dl v-if="reportDetail">
          <div><dt>举报编号</dt><dd>#{{ reportDetail.id }}</dd></div>
          <div><dt>处理状态</dt><dd>{{ statusLabel(reportDetail.status) }}</dd></div>
          <div><dt>内容类型</dt><dd>{{ reportDetail.target_type || reportDetail.targetType || '未说明' }}</dd></div>
          <div><dt>内容 ID</dt><dd>{{ reportDetail.target_id || reportDetail.targetId || '未说明' }}</dd></div>
          <div><dt>内容标题</dt><dd>{{ reportDetail.content_title || '未获取到标题' }}</dd></div>
          <div><dt>举报原因</dt><dd>{{ reportDetail.reason || '未填写' }}</dd></div>
          <div><dt>补充说明</dt><dd>{{ reportDetail.comment || reportDetail.description || '无' }}</dd></div>
          <div><dt>处理动作</dt><dd>{{ reportDetail.action || '待处理' }}</dd></div>
          <div><dt>提交时间</dt><dd>{{ reportDetail.created_at || '未说明' }}</dd></div>
          <div><dt>处理时间</dt><dd>{{ reportDetail.processed_at || '尚未处理' }}</dd></div>
        </dl>
      </div>
    </el-dialog>
    <el-dialog v-model="detailVisible" class="community-detail-dialog" modal-class="community-detail-backdrop" :title="detail?.title || '社区内容详情'" width="min(1080px, calc(100vw - 32px))" :show-close="false">
      <div v-loading="detailLoading" class="detail-dialog">
        <el-alert v-if="detailError" :title="detailError" type="error" show-icon :closable="false" />
        <button v-if="!detail" class="detail-fallback-close" aria-label="关闭详情" @click="detailVisible = false">×</button>
        <template v-if="detail">
          <div class="detail-shell">
            <header class="detail-header">
              <div class="detail-heading">
                <div class="detail-kicker"><span class="detail-kicker-mark" aria-hidden="true"></span><span>{{ normalizeCommunityType(detail) }}</span><span class="detail-version">v{{ detail.version || 1 }}</span></div>
                <h2>{{ detail.title || '未命名社区内容' }}</h2>
                <p>{{ detail.description || '这份内容由社区教师整理，适合直接了解结构，再按自己的课堂进行调整。' }}</p>
                <div class="detail-tags" aria-label="内容标签">
                  <span>{{ detail.subject || '通用学科' }}</span><i aria-hidden="true">·</i><span>{{ detail.grade || detail.stage || '通用学段' }}</span><i aria-hidden="true">·</i><span>{{ detail.lesson_type || '未标注课型' }}</span>
                </div>
              </div>
              <div class="detail-header-actions">
                <button class="detail-favorite-button" :class="{ active: favoriteIds.has(String(detail.id)) }" :aria-pressed="favoriteIds.has(String(detail.id))" @click="toggleFavorite(detail)"><el-icon><Star /></el-icon><span>{{ favoriteIds.has(String(detail.id)) ? '已收藏' : '收藏内容' }}</span></button>
                <button class="detail-favorite-button detail-like-button" :class="{ active: Boolean(detail.liked) }" :aria-pressed="Boolean(detail.liked)" @click="toggleLike(detail)"><svg class="like-icon" viewBox="0 0 24 24" aria-hidden="true"><path :d="LIKE_ICON_PATH" /></svg><span>{{ detail.liked ? '已点赞' : '点赞案例' }}</span></button>
                <button class="detail-close-button" aria-label="关闭详情" @click="detailVisible = false"><span aria-hidden="true">×</span></button>
              </div>
            </header>

            <div class="detail-layout">
              <main class="detail-main">
                <section v-if="detail.example_effect" class="detail-highlight">
                  <div class="detail-section-eyebrow">预期效果</div>
                  <p>{{ detail.example_effect }}</p>
                </section>
                <section class="detail-content-section">
                  <div class="detail-section-heading"><div><span class="detail-section-eyebrow">CONTENT</span><h3>内容预览</h3></div><span class="detail-section-note">结构化内容预览</span></div>
                  <CommunityContentPreview
                    :item="detail"
                    :slides="detailSlides"
                    :lesson-plan="detailLessonPlan"
                    :active-view="detailContentView"
                    :active-slide-index="activeDetailSlideIndex"
                    @update:active-view="detailContentView = $event"
                    @update:active-slide-index="selectDetailSlide($event)"
                  />
                </section>
              </main>

              <aside class="detail-aside">
                <section class="detail-aside-card detail-author-card">
                  <div class="detail-aside-label">发布者</div>
                  <div class="detail-author"><el-avatar class="detail-author-avatar" :size="38" :src="detailAuthorAvatarUrl">{{ detailAuthorAvatarText }}</el-avatar><div><strong>{{ detailAuthorName }}</strong><span>教师共创社区</span></div></div>
                </section>

                <section class="detail-aside-card">
                  <div class="detail-aside-label">使用数据</div>
                  <div class="detail-stat-list"><div><span>使用次数</span><strong>{{ detail.use_count ?? detail.useCount ?? 0 }}</strong></div><div><span>浏览次数</span><strong>{{ detail.view_count ?? detail.viewCount ?? 0 }}</strong></div><div><span>点赞</span><strong>{{ detail.like_count ?? 0 }}</strong></div><div><span>收藏</span><strong>{{ detail.favorite_count ?? 0 }}</strong></div></div>
                </section>

                <section class="detail-aside-card detail-attribute-card">
                  <div class="detail-aside-label">案例属性</div>
                  <dl><div><dt>授权许可</dt><dd>{{ detail.license || '未说明' }}</dd></div><div><dt>内容版本</dt><dd>v{{ detail.version || 1 }}</dd></div><div v-if="detail.created_at"><dt>发布时间</dt><dd>{{ detail.created_at }}</dd></div></dl>
                </section>

                <section v-if="detailInputVariables.length" class="detail-aside-card detail-variable-card">
                  <div class="detail-aside-label">复用前填写</div>
                  <p>配置复用时将生成以下输入项</p>
                  <div class="detail-variable-list"><span v-for="variable in detailInputVariables" :key="variable.key">{{ variable.label }}</span></div>
                </section>

                <div class="detail-aside-actions"><button class="detail-primary-action" :disabled="detailLoading || !detail" @click="reuse(detail)">配置复用 <span aria-hidden="true">↗</span></button><button class="detail-report-action" :disabled="detailLoading || !detail" @click="openReportForDetail">举报内容</button><span>复用会创建你的独立草稿，不会改动社区原件</span></div>
              </aside>
            </div>
            <div class="detail-mobile-footer">
              <button class="detail-primary-action" :disabled="detailLoading || !detail" @click="reuse(detail)">配置复用 <span aria-hidden="true">↗</span></button>
              <button class="detail-report-action" :disabled="detailLoading || !detail" @click="openReportForDetail">举报内容</button>
            </div>
          </div>
        </template>
      </div>
    </el-dialog>
    <el-dialog v-model="reuseVisible" class="community-reuse-dialog" :title="`配置复用 · ${reuseDetail?.title || reuseTarget?.title || '社区内容'}`" width="min(760px, 94vw)" :close-on-click-modal="false">
      <div v-loading="reuseLoading" class="reuse-dialog">
        <p class="reuse-intro">复用会创建个人派生项目，不会修改社区原件。请先确认来源版本、授权条件，并选择要绑定给 AI 的个人资料。</p>
        <el-form label-position="top">
          <el-form-item label="派生项目名称"><el-input v-model="reuseProjectName" maxlength="80" show-word-limit /></el-form-item>
          <div class="reuse-meta-grid"><el-form-item label="来源版本"><el-select v-model="reuseVersion" class="full-width"><el-option v-for="version in reuseVersionOptions" :key="version" :label="`v${version}`" :value="version" /></el-select></el-form-item><div class="reuse-meta-card"><small>授权说明</small><strong>{{ reuseDetail?.license || '未说明' }}</strong></div><div class="reuse-meta-card"><small>示例效果</small><strong>{{ reuseDetail?.example_effect || '未提供' }}</strong></div></div>
          <section v-if="reuseVariables.length" class="reuse-section"><header><strong>输入变量</strong><span>复用前填写，随项目上下文保存</span></header><div class="reuse-variable-grid"><el-form-item v-for="variable in reuseVariables" :key="variable.key" :label="variable.label" :required="variable.required"><el-input v-model="reuseVariableValues[variable.key]" :type="variable.type === 'textarea' ? 'textarea' : 'text'" :placeholder="variable.description || `请输入${variable.label}`" /><small v-if="variable.description">{{ variable.description }}</small></el-form-item></div></section>
          <section class="reuse-section"><header><strong>绑定个人资料</strong><span>已选择 {{ reuseSelectedResourceIds.length }} 项，AI 仅在本项目中使用</span></header><el-checkbox-group v-model="reuseSelectedResourceIds" v-loading="reuseResourcesLoading" class="reuse-resource-picker"><el-checkbox v-for="resource in reuseResources" :key="resource.id" :value="resource.id">{{ resource.name }}<small>{{ resource.fileType || '资料' }}</small></el-checkbox><el-empty v-if="!reuseResourcesLoading && !reuseResources.length" description="暂无个人资料，可稍后在工作台补充绑定" /></el-checkbox-group><div v-if="reuseSelectedResourceIds.length" class="reuse-selected-resources"><el-tag v-for="id in reuseSelectedResourceIds" :key="id" closable @close="removeReuseResource(id)">{{ reuseResources.find((resource) => resource.id === String(id))?.name || `资源 ${id}` }}</el-tag></div></section>
        </el-form>
      </div>
      <template #footer><el-button @click="reuseVisible = false">取消</el-button><el-button type="primary" :loading="reuseLoading" @click="finishReuse">确认复用并进入工作台</el-button></template>
    </el-dialog>
</template>

<style scoped>
.community-page { width: min(1180px, calc(100% - 48px)); margin: 0 auto; padding: 40px 0 60px; }
.community-hero { width: 100%; padding: 26px 0 20px; }.community-hero > p { margin: 0 0 10px; color: var(--zh-text-theme); font-size: 12px; font-weight: 600; letter-spacing: .08em; }
.community-hero h1 { max-width: 680px; margin: 0; font-size: clamp(32px, 4vw, 48px); line-height: 1.18; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.community-hero h1 span { display: inline; }
.community-hero > span { display: block; max-width: 650px; margin-top: 16px; color: var(--zh-text-secondary); line-height: 1.7; }
.community-search-row { width: 100%; display: flex; align-items: center; gap: 12px; margin-top: 28px; }.community-search-row :deep(.el-input) { width: min(650px, calc(100% - 140px)); flex: 0 1 650px; }.community-search-row>.submission-button { min-width: 112px; margin: 0 0 0 auto; color: var(--zh-text-white); font-weight: 600; }.community-hero :deep(.el-input__wrapper) { padding-left: 16px; }.community-hero :deep(.el-input-group__append) { padding: 0; background: var(--zh-background-button); box-shadow: none; }.community-hero :deep(.community-search-button) { width: 76px; min-width: 76px; height: 40px; margin: 0; border: 0; border-radius: 0 var(--zh-radius8) var(--zh-radius8) 0; color: var(--zh-text-white) !important; font-weight: 600; letter-spacing: var(--zh-tracking-normal); white-space: nowrap; transition: background 200ms cubic-bezier(.4, 0, .2, 1), transform 200ms cubic-bezier(.4, 0, .2, 1); }.community-hero :deep(.community-search-button:hover), .community-hero :deep(.community-search-button:focus-visible) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); }.community-hero :deep(.community-search-button:active) { color: var(--zh-text-white) !important; background: var(--zh-background-button-hover); transform: scale(.98); }
.community-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 24px; border-bottom: 1px solid var(--zh-line-border); }
.toolbar-controls { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }.filters { display: flex; gap: 8px; margin-left: 8px; }.submission-button { min-width: 104px; color: var(--zh-text-white); font-weight: 600; }.submission-button:hover, .submission-button:focus-visible { color: var(--zh-text-white); background: var(--zh-background-button-hover); border-color: var(--zh-background-button-hover); }
.tab-list { display: flex; gap: 20px; }.tab-list button { padding: 14px 2px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; cursor: pointer; }.tab-list button.active { color: var(--zh-text-theme); border-color: var(--zh-line-theme); font-weight: 600; }
.filters { display: flex; gap: 8px; }.filters :deep(.el-select) { width: 120px; }
.featured-case { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr); margin-top: 28px; overflow: hidden; border-radius: var(--zh-radius16); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }
.feature-visual { position: relative; min-height: 330px; display: grid; place-items: center; overflow: hidden; color: white; background: #173d78; }
.feature-visual::before { content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 68% 30%, rgb(96 165 250 / 55%), transparent 28%), linear-gradient(145deg, transparent 45%, rgb(255 255 255 / 8%) 45% 46%, transparent 46%); }
.feature-visual span { position: relative; z-index: 1; font: 600 clamp(30px, 4vw, 52px) var(--zh-font-number); letter-spacing: .03em; }
.feature-visual i { position: absolute; width: 80px; height: 80px; border: 1px solid rgb(255 255 255 / 22%); transform: rotate(45deg); }.feature-visual i:nth-of-type(1) { left: 8%; top: 16%; }.feature-visual i:nth-of-type(2) { right: 9%; bottom: 12%; width: 120px; height: 120px; }.feature-visual i:nth-of-type(3) { left: 36%; bottom: -38px; }
.feature-copy { display: flex; flex-direction: column; padding: 32px; }.feature-copy h2 { margin: 18px 0 10px; font-size: 26px; }.feature-copy > p { margin: 0; color: var(--zh-text-secondary); line-height: 1.75; }
.feature-copy dl { margin: 24px 0; }.feature-copy dl div { display: grid; grid-template-columns: 76px 1fr; padding: 8px 0; border-bottom: 1px solid var(--zh-line-parting); }.feature-copy dt { color: var(--zh-text-caption); font-size: 12px; }.feature-copy dd { margin: 0; font-size: 13px; }
.feature-copy footer { display: flex; align-items: center; justify-content: space-between; margin-top: auto; color: var(--zh-text-caption); font-size: 12px; }
.community-status-row { display: flex; align-items: center; gap: 9px; margin-top: 16px; color: var(--zh-text-caption); font-size: 12px; }.status-muted { color: var(--zh-text-caption); font-size: 11px; }.community-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; padding: 9px 12px; border: 1px solid color-mix(in srgb, var(--zh-red) 30%, var(--zh-line-border)); border-radius: var(--zh-radius8); color: var(--zh-red); background: var(--zh-danger-background); font-size: 12px; }.community-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin-top: 18px; }.community-card { padding: 18px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-capsule); cursor: pointer; transition: transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease; }.community-card:hover, .community-card:focus-visible { transform: translateY(-3px); border-color: var(--zh-line-theme20); box-shadow: var(--zh-shadow2); outline: none; }
.community-empty { grid-column: 1 / -1; padding: 40px 0; border: 1px dashed var(--zh-line-heavier); border-radius: var(--zh-radius12); }
.card-top, .community-card footer { display: flex; align-items: center; justify-content: space-between; }.card-top > span { color: var(--zh-text-caption); font-size: 11px; }.card-icon { width: 38px; height: 38px; display: grid; place-items: center; margin-top: 18px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
/* 功能11：卡片点赞按钮（图标 + 计数，激活态主题色） */
.card-top-actions { display: flex; align-items: center; gap: 2px; }.card-like { display: inline-flex; align-items: center; justify-content: center; gap: 4px; min-width: 44px; height: 34px; padding: 0 9px; border: 0; border-radius: 9999px; color: var(--zh-text-caption); background: transparent; cursor: pointer; font-size: 11px; transition: color 200ms ease, background 200ms ease, transform 200ms ease; }.card-like svg { width: 13px; height: 13px; fill: currentColor; }.card-like:hover { color: var(--zh-text-theme); background: var(--zh-background-weaken); }.card-like:active { transform: scale(.94); }.card-like.active { color: var(--zh-text-theme); }
.community-card h3 { min-height: 44px; margin: 18px 0 8px; font-size: 15px; line-height: 1.5; }.community-card > p { margin: 0 0 28px; color: var(--zh-text-caption); font-size: 12px; }.community-card > p.card-description { display: -webkit-box; min-height: 36px; margin: -16px 0 20px; overflow: hidden; color: var(--zh-text-secondary); line-height: 1.5; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }.community-card footer { gap: 8px; border-top: 1px solid var(--zh-line-parting); padding-top: 12px; font-size: 11px; }.community-card footer span { min-width: 0; display: flex; align-items: center; gap: 4px; overflow: hidden; color: var(--zh-text-caption); text-overflow: ellipsis; white-space: nowrap; }.community-card footer button { flex: none; border: 0; color: var(--zh-text-link); background: transparent; cursor: pointer; font-size: 11px; }.card-actions { display: flex; align-items: center; gap: 8px; }.card-detail { color: var(--zh-text-caption) !important; }.community-pagination { justify-content: center; margin: 24px 0 0; }
.card-metrics { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin: -9px 0 15px; color: var(--zh-text-caption); font-size: 11px; }.card-metrics button { padding: 0; border: 0; color: inherit; background: transparent; cursor: pointer; font: inherit; }.card-metrics button:hover,.card-metrics button[aria-pressed="true"] { color: var(--zh-text-theme); }
.source-note { margin: 20px 0 0; color: var(--zh-text-caption); font-size: 11px; text-align: center; }
/* 功能11：热门榜单区（白卡 + el-segmented 类型/时间段切换 + Top10 双列列表） */
.rank-section { margin-top: 20px; padding: 18px 20px 20px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-pop); box-shadow: var(--zh-shadow1); }.rank-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }.rank-title { display: flex; align-items: center; gap: 8px; color: var(--zh-text-theme); }.rank-title .el-icon { font-size: 18px; }.rank-title h2 { margin: 0; color: var(--zh-text-primary); font-size: 16px; font-weight: 600; letter-spacing: var(--zh-tracking-tight); }.rank-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rank-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; min-height: 56px; margin-top: 14px; }.rank-row { display: flex; align-items: center; gap: 10px; min-width: 0; padding: 9px 10px; border: 1px solid var(--zh-line-parting); border-radius: var(--zh-radius8); background: var(--zh-background-capsule); cursor: pointer; transition: border-color .15s ease, transform .15s ease, box-shadow .15s ease; }.rank-row:hover, .rank-row:focus-visible { border-color: var(--zh-line-theme20); transform: translateY(-1px); box-shadow: var(--zh-shadow1); }.rank-badge { display: grid; width: 24px; height: 24px; flex: none; place-items: center; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); font: 600 11px/1 var(--zh-font-number); }.rank-badge.top { color: var(--zh-text-white); background: var(--zh-gradient-blue); }.rank-info { min-width: 0; display: grid; gap: 2px; }.rank-info strong { overflow: hidden; color: var(--zh-text-primary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.rank-info span { overflow: hidden; color: var(--zh-text-caption); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }.rank-score { flex: none; margin-left: auto; color: var(--zh-text-theme); font: 600 13px/1 var(--zh-font-number); }.rank-empty { grid-column: 1 / -1; padding: 14px 0; border: 1px dashed var(--zh-line-heavier); border-radius: var(--zh-radius8); }.rank-error { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 12px; border: 1px solid color-mix(in srgb, var(--zh-red) 30%, var(--zh-line-border)); border-radius: var(--zh-radius8); color: var(--zh-red); background: var(--zh-danger-background); font-size: 12px; }
@media (max-width: 980px) { .community-grid { grid-template-columns: repeat(2, 1fr); }.featured-case { grid-template-columns: 1fr; }.feature-visual { min-height: 240px; } }
@media (max-width: 600px) { .community-search-row { align-items: stretch; flex-direction: column; }.community-search-row :deep(.el-input) { width: 100%; flex-basis: auto; }.community-search-row>.submission-button { width: 100%; margin-left: 0; }.community-toolbar { align-items: stretch; flex-direction: column; }.filters { padding-bottom: 12px; }.community-grid { grid-template-columns: 1fr; } }
.community-actions{display:flex;justify-content:center;gap:8px;margin-top:24px}.submission-dialog{display:grid;gap:12px}.submission-state{display:flex;align-items:center;gap:14px;padding:9px 11px;border-radius:var(--zh-radius8);color:var(--zh-text-caption);background:var(--zh-background-light);font-size:12px}.submission-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px}.submission-grid-secondary{grid-template-columns:1fr 1fr 2fr}.submission-grid :deep(.el-form-item){margin-bottom:0}.json-editor-hint{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-top:5px;color:var(--zh-text-caption);font-size:11px;line-height:1.45}.json-editor-hint .el-button{flex:none;padding:0;font-size:11px}.draft-list{display:flex;align-items:center;gap:4px;overflow:auto;padding:10px;border-radius:var(--zh-radius8);background:var(--zh-background-light);font-size:12px}.draft-list span{flex:none;color:var(--zh-text-caption)}.collection-section{margin-bottom:20px}.collection-section h3,.report-list h3{margin:0 0 8px;font-size:14px}.collection-row,.report-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:1px solid var(--zh-line-parting);color:var(--zh-text-secondary);font-size:13px}.collection-item-link{min-width:0;overflow:hidden;padding:0;border:0;color:var(--zh-text-link);background:transparent;cursor:pointer;font:inherit;text-align:left;text-overflow:ellipsis;white-space:nowrap}.collection-item-link:hover,.collection-item-link:focus-visible{color:var(--zh-text-theme);text-decoration:underline;outline:none}.report-dialog{display:grid;gap:10px}.report-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}.report-form-grid :deep(.el-form-item:nth-child(3)),.report-form-grid :deep(.el-form-item:nth-child(4)){grid-column:1 / -1}.report-list{margin-top:16px;padding-top:12px;border-top:1px solid var(--zh-line-border)}.report-row span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.report-detail dl{display:grid;gap:0;margin:0}.report-detail dl div{display:grid;grid-template-columns:90px minmax(0,1fr);gap:12px;padding:10px 0;border-bottom:1px solid var(--zh-line-parting)}.report-detail dt{color:var(--zh-text-caption);font-size:12px}.report-detail dd{margin:0;color:var(--zh-text-secondary);font-size:13px;word-break:break-word}.detail-meta{color:var(--zh-text-caption);font-size:12px}.detail-section-title{margin:18px 0 8px;font-size:14px}.detail-content{max-height:360px;overflow:auto;padding:14px;border-radius:var(--zh-radius8);background:var(--zh-background-light);font:12px/1.65 var(--zh-font-code);white-space:pre-wrap}@media(max-width:600px){.submission-grid,.submission-grid-secondary,.report-form-grid{grid-template-columns:1fr}.report-form-grid :deep(.el-form-item:nth-child(3)),.report-form-grid :deep(.el-form-item:nth-child(4)){grid-column:auto}.community-actions{flex-wrap:wrap}}
.detail-context-grid,.reuse-meta-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:14px 0}.detail-context-grid>span,.reuse-meta-card{display:grid;gap:4px;min-width:0;padding:10px 12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.detail-context-grid small,.reuse-meta-card small{color:var(--zh-text-caption);font-size:10px}.detail-context-grid strong,.reuse-meta-card strong{overflow:hidden;color:var(--zh-text-secondary);font-size:12px;line-height:1.45;text-overflow:ellipsis}.detail-variable-preview{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin:12px 0;color:var(--zh-text-caption);font-size:11px}.detail-variable-preview strong{flex:none;color:var(--zh-text-secondary)}.detail-variable-preview span{padding:4px 8px;border-radius:999px;color:var(--zh-text-theme);background:var(--zh-background-weaken)}.reuse-dialog{display:grid;gap:4px}.reuse-intro{margin:0 0 12px;color:var(--zh-text-secondary);font-size:13px;line-height:1.65}.reuse-meta-grid{align-items:stretch}.reuse-meta-grid :deep(.el-form-item){margin:0}.full-width{width:100%}.reuse-section{margin-top:8px;padding:14px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-primary)}.reuse-section>header{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:10px}.reuse-section>header strong{font-size:13px}.reuse-section>header span{color:var(--zh-text-caption);font-size:11px}.reuse-variable-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.reuse-variable-grid :deep(.el-form-item){margin-bottom:0}.reuse-variable-grid small{display:block;margin-top:4px;color:var(--zh-text-caption);font-size:10px;line-height:1.4}.reuse-resource-picker{display:grid;gap:6px;max-height:210px;overflow:auto;padding:10px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.reuse-resource-picker :deep(.el-checkbox){display:flex;align-items:flex-start;margin:0}.reuse-resource-picker :deep(.el-checkbox__label){display:flex;align-items:baseline;gap:8px;min-width:0;color:var(--zh-text-secondary);font-size:12px}.reuse-resource-picker small{color:var(--zh-text-caption);font-size:10px}.reuse-selected-resources{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}@media(max-width:600px){.detail-context-grid,.reuse-meta-grid,.reuse-variable-grid{grid-template-columns:1fr}}
/* 社区详情：采用 design.md 的高层 Modal 规范，内容与操作分层呈现。 */
/* 遮罩保持纯色，避免 backdrop-filter 在弹窗滚动时触发整页重绘。 */
:global(.community-detail-backdrop) { background: rgb(17 24 39 / 48%); }
:global(.community-detail-dialog.el-dialog) { width: min(1080px, calc(100vw - 32px)); max-width: 1080px; margin: 4vh auto !important; padding: 0; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius16); background: var(--zh-background-pop); box-shadow: var(--zh-shadow3); }
:global(.community-detail-dialog.el-dialog .el-dialog__header) { display: none; }
:global(.community-detail-dialog.el-dialog .el-dialog__body) { padding: 0; }
:global(.community-detail-dialog.el-dialog .el-dialog__footer) { display: none; }
.community-detail-dialog .detail-dialog { min-height: 260px; }
.community-detail-dialog .detail-dialog > .el-alert { margin: 24px; }
.detail-dialog { position: relative; }
.detail-fallback-close { position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--zh-text-caption); background: transparent; cursor: pointer; font-size: 24px; font-weight: 300; line-height: 1; }.detail-fallback-close:hover,.detail-fallback-close:focus-visible { color: var(--zh-text-primary); background: var(--zh-background-light); outline: none; }
.detail-shell { color: var(--zh-text-primary); }
.detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 32px; padding: 32px 36px 28px; border-bottom: 1px solid var(--zh-line-parting); background: var(--zh-background-pop); }
.detail-heading { min-width: 0; max-width: 760px; }
.detail-kicker { display: flex; align-items: center; gap: 8px; color: var(--zh-text-theme); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.detail-kicker-mark { width: 8px; height: 8px; border-radius: 50%; background: var(--zh-theme-primary); box-shadow: 0 0 0 4px var(--zh-background-weaken); }
.detail-version { padding-left: 8px; border-left: 1px solid var(--zh-line-border); color: var(--zh-text-caption); font-size: 11px; font-weight: 500; letter-spacing: 0; text-transform: none; }
.detail-heading h2 { margin: 12px 0 10px; color: var(--zh-text-primary); font-size: clamp(24px, 3vw, 34px); font-weight: 700; line-height: 1.25; letter-spacing: var(--zh-tracking-tight); text-wrap: balance; }
.detail-heading > p { max-width: 700px; margin: 0; color: var(--zh-text-secondary); font-size: 14px; line-height: 1.7; }
.detail-tags { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 18px; color: var(--zh-text-caption); font-size: 12px; }
.detail-tags i { color: var(--zh-line-heavier); font-style: normal; }
.detail-header-actions { display: flex; flex: none; align-items: center; gap: 10px; }
.detail-favorite-button,.detail-close-button { display: inline-flex; align-items: center; justify-content: center; border: 1px solid var(--zh-line-border); color: var(--zh-text-secondary); background: var(--zh-background-capsule); cursor: pointer; transition: border-color 180ms ease, color 180ms ease, background 180ms ease, transform 180ms ease; }
.detail-favorite-button { gap: 7px; min-height: 36px; padding: 0 13px; border-radius: var(--zh-radius8); font: inherit; font-size: 12px; }
.detail-favorite-button:hover,.detail-favorite-button:focus-visible { border-color: var(--zh-line-theme20); color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.detail-favorite-button:active { transform: scale(.98); }
.detail-favorite-button.active { border-color: var(--zh-line-theme20); color: var(--zh-text-theme); background: var(--zh-background-option-on); }
@media (max-width: 560px) { .detail-like-button { width: auto !important; padding: 0 8px !important; }.detail-like-button span { display: inline !important; white-space: nowrap; } }
.detail-close-button { width: 36px; height: 36px; padding: 0; border-color: transparent; border-radius: 50%; font-size: 25px; font-weight: 300; line-height: 1; }
.detail-close-button:hover,.detail-close-button:focus-visible { border-color: var(--zh-line-border); color: var(--zh-text-primary); background: var(--zh-background-light); outline: none; }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) 292px; gap: 28px; padding: 28px 36px 34px; background: var(--zh-background-light); overscroll-behavior: contain; }
.detail-main { min-width: 0; display: grid; align-content: start; gap: 20px; }
.detail-highlight,.detail-content-section,.detail-aside-card { border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius12); background: var(--zh-background-pop); box-shadow: var(--zh-shadow1); }
.detail-highlight { padding: 20px 22px; border-color: var(--zh-line-theme20); background: var(--zh-background-weaken); }
.detail-section-eyebrow { color: var(--zh-text-theme); font-size: 11px; font-weight: 700; letter-spacing: .1em; }
.detail-highlight p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 14px; line-height: 1.7; }
.detail-content-section { padding: 22px; }
.detail-section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.detail-section-heading h3 { margin: 4px 0 0; font-size: 20px; line-height: 1.35; }
.detail-section-note { padding-top: 3px; color: var(--zh-text-caption); font-size: 11px; }
.detail-content-switch { display: inline-flex; flex: none; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }.detail-content-switch button { min-width: 66px; padding: 6px 10px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; cursor: pointer; font: 600 11px/1.2 var(--zh-font-family); transition: color .16s ease, background .16s ease, box-shadow .16s ease; }.detail-content-switch button:hover { color: var(--zh-text-theme); }.detail-content-switch button.active { color: var(--zh-text-theme); background: var(--zh-background-pop); box-shadow: var(--zh-shadow1); }.detail-content-switch button:focus-visible { outline: 2px solid var(--zh-border-focus); outline-offset: 2px; }
.detail-slides-preview { display: grid; gap: 10px; margin-top: 14px; padding: 14px; border: 1px solid var(--zh-line-parting); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.detail-lesson-plan { margin-top: 14px; }
.detail-slides-preview-header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }.detail-slides-preview-header div { display: grid; gap: 3px; }.detail-slides-preview-header strong { color: var(--zh-text-primary); font-size: 13px; }.detail-slides-preview-header span,.detail-slides-preview-header small { color: var(--zh-text-caption); font-size: 11px; }.detail-slides-preview-header span { overflow: hidden; max-width: 440px; text-overflow: ellipsis; white-space: nowrap; }
.detail-slide-stage { position: relative; aspect-ratio: 16 / 9; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: 7px; background: #fff; box-shadow: inset 0 0 0 1px rgb(15 23 42 / 3%); }.detail-slide-frame { position: absolute; top: 0; left: 0; display: block; width: 1280px; height: 720px; border: 0; background: #fff; transform-origin: top left; }
.detail-slide-picker { display: flex; gap: 7px; overflow-x: auto; padding: 1px; scrollbar-width: thin; }.detail-slide-picker button { display: grid; grid-template-columns: 24px minmax(0, 1fr); flex: 0 0 min(180px, 42%); align-items: center; gap: 7px; min-width: 120px; padding: 8px; border: 1px solid var(--zh-line-parting); border-radius: 7px; color: var(--zh-text-secondary); background: var(--zh-background-pop); cursor: pointer; text-align: left; transition: border-color .16s ease, background .16s ease, transform .16s ease; }.detail-slide-picker button:hover { border-color: var(--zh-border-focus); transform: translateY(-1px); }.detail-slide-picker button.active { border-color: var(--zh-theme-primary); background: var(--zh-background-weaken); }.detail-slide-picker button > span { display: grid; width: 24px; height: 24px; place-items: center; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-background-option-on); font: 600 10px/1 var(--zh-font-number); }.detail-slide-picker button > strong { overflow: hidden; color: inherit; font-size: 11px; font-weight: 580; text-overflow: ellipsis; white-space: nowrap; }
.detail-content-frame { position: relative; overflow: hidden; border: 1px solid var(--zh-line-parting); border-radius: var(--zh-radius8); background: #f3f6fb; }
.detail-content { max-height: 320px; margin: 0; overflow: auto; padding: 24px 22px; color: #334155; background: transparent; contain: content; font: 12px/1.75 var(--zh-font-code, ui-monospace, SFMono-Regular, Consolas, monospace); white-space: pre-wrap; word-break: break-word; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
.detail-content::-webkit-scrollbar { width: 8px; height: 8px; }.detail-content::-webkit-scrollbar-thumb { border: 2px solid transparent; border-radius: 999px; background: #cbd5e1; background-clip: padding-box; }
.detail-flow { padding: 16px; border: 1px solid var(--zh-line-parting); border-radius: var(--zh-radius8); background: var(--zh-background-light); }.detail-flow-header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }.detail-flow-header strong { font-size: 13px; }.detail-flow-header span { color: var(--zh-text-caption); font-size: 11px; }.detail-flow-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 0; padding: 0; list-style: none; }.detail-flow-list li { display: flex; align-items: center; gap: 10px; min-width: 0; padding: 10px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-pop); }.detail-flow-list li > span { display: grid; width: 24px; height: 24px; flex: none; place-items: center; border-radius: 7px; color: var(--zh-text-theme); background: var(--zh-background-option-on); font: 600 11px/1 var(--zh-font-number); }.detail-flow-list li > strong { min-width: 0; overflow: hidden; color: var(--zh-text-secondary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.detail-objective { margin-top: 14px; padding: 14px 16px; border-left: 3px solid var(--zh-theme-primary); background: var(--zh-background-weaken); }.detail-objective > span { color: var(--zh-text-caption); font-size: 11px; font-weight: 700; }.detail-objective p { margin: 5px 0 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.6; }.detail-raw-content { margin-top: 16px; }.detail-raw-content summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 0; border-top: 1px solid var(--zh-line-parting); color: var(--zh-text-caption); cursor: pointer; font-size: 11px; list-style: none; }.detail-raw-content summary::-webkit-details-marker { display: none; }.detail-raw-content summary::after { content: "＋"; color: var(--zh-text-theme); font-size: 16px; font-weight: 300; line-height: 1; }.detail-raw-content[open] summary::after { content: "−"; }.detail-raw-content summary span:last-child { margin-left: auto; color: var(--zh-text-theme); font: 600 10px/1 var(--zh-font-number); letter-spacing: .12em; }.detail-raw-content .detail-content-frame { margin-top: 4px; }
.detail-aside { min-width: 0; display: grid; align-content: start; gap: 12px; }
.detail-aside-card { padding: 18px; box-shadow: none; }
.detail-aside-label { margin-bottom: 14px; color: var(--zh-text-caption); font-size: 11px; font-weight: 700; letter-spacing: .08em; }
.detail-author { display: flex; align-items: center; gap: 11px; }
.detail-author-avatar { flex: none; color: var(--zh-text-white); background: var(--zh-theme-primary); font-size: 15px; font-weight: 500; }
.detail-author strong,.detail-author span { display: block; }.detail-author strong { color: var(--zh-text-primary); font-size: 13px; }.detail-author span { margin-top: 4px; color: var(--zh-text-caption); font-size: 11px; }
.detail-stat-list { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 0; }.detail-stat-list div { min-width: 0; padding-right: 10px; border-right: 1px solid var(--zh-line-parting); }.detail-stat-list div:nth-child(2n), .detail-stat-list div:last-child { padding-right: 0; border-right: 0; }.detail-stat-list span,.detail-stat-list strong { display: block; }.detail-stat-list span { color: var(--zh-text-caption); font-size: 11px; }.detail-stat-list strong { margin-top: 5px; color: var(--zh-text-primary); font: 600 24px/1.1 var(--zh-font-number); }
.detail-like-button .like-icon { width: 13px; height: 13px; fill: currentColor; }.detail-like-button:focus-visible { outline: 2px solid var(--zh-border-focus); outline-offset: 2px; }
.detail-attribute-card dl { display: grid; gap: 0; margin: 0; }.detail-attribute-card dl div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--zh-line-parting); }.detail-attribute-card dl div:first-child { padding-top: 0; }.detail-attribute-card dl div:last-child { padding-bottom: 0; border-bottom: 0; }.detail-attribute-card dt { color: var(--zh-text-caption); font-size: 11px; }.detail-attribute-card dd { max-width: 170px; margin: 0; color: var(--zh-text-secondary); font-size: 12px; text-align: right; word-break: break-word; }
.detail-variable-card p { margin: -5px 0 12px; color: var(--zh-text-caption); font-size: 11px; line-height: 1.5; }.detail-variable-list { display: flex; flex-wrap: wrap; gap: 6px; }.detail-variable-list span { padding: 5px 8px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); font-size: 11px; }
.detail-aside-actions { display: grid; gap: 8px; padding-top: 4px; }.detail-primary-action,.detail-report-action { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 42px; padding: 0 15px; border-radius: var(--zh-radius8); cursor: pointer; font: inherit; font-size: 13px; transition: background 180ms ease, border-color 180ms ease, color 180ms ease, transform 180ms ease; }.detail-primary-action { border: 1px solid var(--zh-theme-primary); color: var(--zh-text-white); background: var(--zh-background-button); font-weight: 600; }.detail-primary-action:hover,.detail-primary-action:focus-visible { border-color: var(--zh-background-button-hover); background: var(--zh-background-button-hover); outline: none; }.detail-primary-action:active { transform: translateY(1px); }.detail-report-action { justify-content: center; border: 1px solid transparent; color: var(--zh-text-caption); background: transparent; }.detail-report-action:hover,.detail-report-action:focus-visible { border-color: var(--zh-line-border); color: var(--zh-text-danger, var(--zh-red)); background: var(--zh-background-pop); outline: none; }.detail-primary-action:disabled,.detail-report-action:disabled { cursor: not-allowed; opacity: .55; }.detail-aside-actions > span { color: var(--zh-text-caption); font-size: 10px; line-height: 1.45; text-align: center; }
@media (max-width: 800px) { .detail-header { gap: 18px; padding: 24px 22px; }.detail-layout { grid-template-columns: 1fr; gap: 18px; padding: 22px; }.detail-aside { grid-template-columns: repeat(2, minmax(0, 1fr)); }.detail-aside-actions { grid-column: 1 / -1; }.detail-author-card { grid-column: 1 / -1; } }
@media (max-width: 560px) { :global(.community-detail-dialog.el-dialog) { width: calc(100vw - 20px); margin: 10px auto !important; }.detail-header { padding: 20px 18px; }.detail-header-actions { gap: 6px; }.detail-favorite-button { width: 36px; padding: 0; }.detail-favorite-button span { display: none; }.detail-layout { padding: 18px; }.detail-content-section { padding: 18px; }.detail-flow-list { grid-template-columns: 1fr; }.detail-aside { grid-template-columns: 1fr; }.detail-author-card { grid-column: auto; }.detail-aside-actions { grid-column: auto; }.detail-heading h2 { font-size: 24px; } }

:global(.community-submission-backdrop){background:rgb(15 23 42 / 50%)}
:global(.community-submission-dialog.el-dialog){margin:3vh auto;overflow:hidden;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius16);background:var(--zh-background-pop);box-shadow:var(--zh-shadow3)}
:global(.community-submission-dialog .el-dialog__header){display:none}
:global(.community-submission-dialog .el-dialog__body){padding:0;background:var(--zh-background-pop)}
:global(.community-submission-dialog .el-dialog__footer){padding:16px 36px 22px;border-top:1px solid var(--zh-line-parting);background:var(--zh-background-pop)}
.submission-dialog{display:block;color:var(--zh-text-primary)}
.submission-header{display:flex;justify-content:space-between;gap:24px;padding:30px 36px 25px;border-bottom:1px solid var(--zh-line-parting);background:var(--zh-background-pop)}
.submission-heading{min-width:0}.submission-kicker{display:flex;align-items:center;gap:7px;margin-bottom:8px;color:var(--zh-text-theme);font-size:12px;font-weight:650;letter-spacing:.06em}.submission-kicker-mark{width:7px;height:7px;border-radius:50%;background:var(--zh-text-theme)}.submission-version{padding:2px 6px;border-radius:999px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:11px;letter-spacing:0}.submission-heading h2{margin:0;color:var(--zh-text-primary);font-size:clamp(24px,2.2vw,32px);font-weight:650;letter-spacing:-.035em;line-height:1.18}.submission-heading p{margin:8px 0 0;color:var(--zh-text-secondary);font-size:14px;line-height:1.65}.submission-close-button{display:grid;flex:none;width:34px;height:34px;place-items:center;border:0;border-radius:var(--zh-radius8);color:var(--zh-text-caption);background:transparent;cursor:pointer;font-size:30px;font-weight:300;line-height:1;transition:color .16s ease,background .16s ease,transform .16s ease}.submission-close-button:hover{color:var(--zh-text-theme);background:var(--zh-background-light);transform:scale(1.04)}.submission-close-button:focus-visible{outline:2px solid var(--zh-border-focus);outline-offset:2px}
.submission-layout{display:grid;grid-template-columns:minmax(0,1fr) 252px;gap:24px;max-height:min(68vh,740px);overflow:auto;padding:25px 36px 30px;background:var(--zh-background-light);scrollbar-gutter:stable;overscroll-behavior:contain}.submission-main{min-width:0;display:grid;align-content:start;gap:16px}.submission-aside{display:grid;align-content:start;gap:12px;min-width:0}.submission-inline-alert{margin:0}.submission-readonly-notice{display:grid;grid-template-columns:auto auto 1fr;align-items:center;gap:9px;padding:11px 14px;border:1px solid #bae6fd;border-radius:var(--zh-radius8);color:#075985;background:#f0f9ff;font-size:12px}.submission-readonly-notice strong{font-size:13px}.submission-readonly-notice p{margin:0;color:#0c4a6e;text-align:right;line-height:1.5}
.submission-form{display:grid;gap:16px}.submission-section{padding:20px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius12);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1)}.submission-section-heading{display:flex;justify-content:space-between;gap:16px;margin-bottom:16px}.submission-section-heading>div>span{display:block;margin-bottom:4px;color:var(--zh-text-theme);font-size:11px;font-weight:650;letter-spacing:.08em}.submission-section-heading h3{margin:0;color:var(--zh-text-primary);font-size:18px;font-weight:620;letter-spacing:-.02em;line-height:1.3}.submission-section-heading small{padding-top:5px;color:var(--zh-text-caption);font-size:11px;white-space:nowrap}.submission-section-intro{margin:-6px 0 14px;color:var(--zh-text-secondary);font-size:12px;line-height:1.6}.submission-meta-grid{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:0 12px}.submission-meta-grid :deep(.el-form-item){margin-bottom:12px}.submission-meta-grid :deep(.submission-title-field){grid-column:span 2}.submission-meta-grid :deep(.submission-effect-field){grid-column:span 2}.submission-summary-field{margin:0}.submission-form :deep(.el-form-item__label){height:auto;padding:0 0 6px;color:var(--zh-text-secondary);font-size:12px;font-weight:580;line-height:1.25}.submission-form :deep(.el-input__wrapper),.submission-form :deep(.el-textarea__inner),.submission-form :deep(.el-select__wrapper){border-radius:var(--zh-radius8);box-shadow:0 0 0 1px var(--zh-line-border) inset;transition:box-shadow .16s ease,background .16s ease}.submission-form :deep(.el-input__wrapper:hover),.submission-form :deep(.el-select__wrapper:hover),.submission-form :deep(.el-textarea__inner:hover){box-shadow:0 0 0 1px var(--zh-border-focus) inset}.submission-form :deep(.el-input__wrapper.is-focus),.submission-form :deep(.el-select__wrapper.is-focused),.submission-form :deep(.el-textarea__inner:focus){box-shadow:0 0 0 1px var(--zh-border-focus) inset}.submission-form :deep(.el-input.is-disabled .el-input__wrapper),.submission-form :deep(.el-textarea.is-disabled .el-textarea__inner),.submission-form :deep(.el-select .el-select__wrapper.is-disabled){color:var(--zh-text-secondary);background:var(--zh-background-light);box-shadow:0 0 0 1px var(--zh-line-parting) inset}.submission-form :deep(.el-input.is-disabled input),.submission-form :deep(.el-textarea.is-disabled textarea){-webkit-text-fill-color:var(--zh-text-secondary)}
.submission-metric-grid{display:grid;grid-template-columns:repeat(3,1fr);margin:0 0 16px;border:1px solid var(--zh-line-parting);border-radius:var(--zh-radius8);overflow:hidden;background:var(--zh-background-light)}.submission-metric-grid div{display:grid;gap:2px;padding:11px 13px;border-right:1px solid var(--zh-line-parting)}.submission-metric-grid div:last-child{border-right:0}.submission-metric-grid strong{color:var(--zh-text-primary);font-size:18px;line-height:1.2}.submission-metric-grid span{color:var(--zh-text-caption);font-size:11px}.submission-slides{margin:2px 0 16px;padding:14px;border:1px solid var(--zh-line-parting);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.submission-slides>header,.submission-flow-editor>header,.submission-aside-card>header{display:flex;align-items:center;justify-content:space-between;gap:12px}.submission-slides>header{margin-bottom:10px}.submission-slides>header strong,.submission-flow-editor strong{color:var(--zh-text-primary);font-size:13px}.submission-slides>header span{color:var(--zh-text-caption);font-size:11px}.submission-slide-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.submission-slide-card{display:flex;gap:9px;min-width:0;padding:10px;border:1px solid var(--zh-line-parting);border-radius:var(--zh-radius8);background:var(--zh-background-pop)}.submission-slide-card>span{display:grid;flex:none;width:26px;height:26px;place-items:center;border-radius:6px;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:10px;font-weight:650}.submission-slide-card div{min-width:0}.submission-slide-card strong{display:block;overflow:hidden;color:var(--zh-text-primary);font-size:12px;line-height:1.35;text-overflow:ellipsis;white-space:nowrap}.submission-slide-card p{display:-webkit-box;overflow:hidden;margin:3px 0 0;color:var(--zh-text-caption);font-size:11px;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:2}.submission-more-slides{margin:10px 0 0;color:var(--zh-text-caption);font-size:11px}
.submission-flow-editor{margin-top:2px}.submission-flow-editor>header{margin-bottom:10px}.submission-flow-editor>header>div{display:grid;gap:3px}.submission-flow-editor>header div span{color:var(--zh-text-caption);font-size:11px;line-height:1.45}.submission-text-action{padding:0;border:0;color:var(--zh-text-link);background:transparent;cursor:pointer;font:600 12px var(--zh-font-family);white-space:nowrap;transition:color .16s ease,transform .16s ease}.submission-text-action:hover{color:var(--zh-text-theme);transform:translateY(-1px)}.submission-text-action:focus-visible{outline:2px solid var(--zh-border-focus);outline-offset:3px}.submission-flow-list{display:grid;gap:8px;margin:0;padding:0;list-style:none}.submission-flow-list li{display:grid;grid-template-columns:26px minmax(0,1fr) 22px;align-items:center;gap:8px}.submission-flow-list li>span{display:grid;width:24px;height:24px;place-items:center;border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:11px;font-weight:650}.submission-flow-list li>button,.submission-variable-delete{display:grid;width:22px;height:22px;place-items:center;padding:0;border:0;border-radius:5px;color:var(--zh-text-caption);background:transparent;cursor:pointer;font-size:18px;line-height:1;transition:color .16s ease,background .16s ease}.submission-flow-list li>button:hover,.submission-variable-delete:hover{color:var(--zh-color-error);background:#fef2f2}.submission-empty-flow,.submission-variable-empty{display:grid;gap:4px;padding:14px;border:1px dashed var(--zh-line-border);border-radius:var(--zh-radius8);color:var(--zh-text-caption);background:var(--zh-background-light);font-size:12px;line-height:1.55}.submission-empty-flow strong,.submission-variable-empty strong{color:var(--zh-text-secondary);font-size:12px}
.submission-variable-list{display:grid;gap:8px}.submission-variable-row{position:relative;display:grid;grid-template-columns:26px minmax(0,1fr) 22px;gap:8px;align-items:start;padding:10px;border:1px solid var(--zh-line-parting);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.submission-variable-index{display:grid;width:24px;height:24px;place-items:center;border-radius:50%;color:var(--zh-text-theme);background:var(--zh-background-weaken);font-size:11px;font-weight:650}.submission-variable-fields{display:grid;grid-template-columns:1.1fr 1fr .8fr auto;gap:7px;align-items:center;min-width:0}.submission-variable-fields :deep(.el-switch){justify-self:start}.submission-variable-description{grid-column:2 / 3;margin-top:1px}.submission-variable-delete{margin-top:2px}.submission-aside-card{padding:15px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius12);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1)}.submission-status-card>span,.submission-attribute-card>span,.submission-drafts-card header>span{display:block;color:var(--zh-text-caption);font-size:11px;font-weight:600;letter-spacing:.06em}.submission-status-card strong{display:block;margin-top:6px;color:var(--zh-text-primary);font-size:20px;letter-spacing:-.025em}.submission-status-card p{margin:7px 0 0;color:var(--zh-text-secondary);font-size:12px;line-height:1.6}.submission-attribute-card dl{display:grid;gap:0;margin:9px 0 0}.submission-attribute-card dl div{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid var(--zh-line-parting);font-size:12px}.submission-attribute-card dl div:last-child{padding-bottom:0;border-bottom:0}.submission-attribute-card dt{color:var(--zh-text-caption)}.submission-attribute-card dd{max-width:135px;margin:0;overflow:hidden;color:var(--zh-text-secondary);font-weight:560;text-align:right;text-overflow:ellipsis;white-space:nowrap}.submission-drafts-card header small{color:var(--zh-text-caption);font-size:11px}.submission-draft-list{display:grid;gap:4px;margin-top:9px;max-height:215px;overflow:auto}.submission-draft-list button{display:grid;gap:3px;width:100%;padding:9px;border:1px solid transparent;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:transparent;cursor:pointer;text-align:left;transition:background .16s ease,border-color .16s ease}.submission-draft-list button:hover,.submission-draft-list button.active{border-color:var(--zh-line-parting);background:var(--zh-background-light)}.submission-draft-list button.active{border-color:#bfdbfe;background:#eff6ff}.submission-draft-list strong{overflow:hidden;color:var(--zh-text-secondary);font-size:12px;font-weight:580;text-overflow:ellipsis;white-space:nowrap}.submission-draft-list span{color:var(--zh-text-caption);font-size:11px}.submission-draft-empty,.submission-aside-note{margin:10px 0 0;color:var(--zh-text-caption);font-size:11px;line-height:1.6}.submission-aside-note{margin:0;padding:0 4px}
@media(max-width:960px){:global(.community-submission-dialog .el-dialog__footer){padding-right:24px;padding-left:24px}.submission-header{padding-right:24px;padding-left:24px}.submission-layout{grid-template-columns:1fr;padding-right:24px;padding-left:24px}.submission-aside{grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch}.submission-drafts-card{grid-column:1 / -1}.submission-draft-list{grid-template-columns:repeat(3,minmax(0,1fr));max-height:none}.submission-aside-note{grid-column:1 / -1}.submission-draft-list strong{font-size:11px}}
@media(max-width:700px){:global(.community-submission-dialog.el-dialog){margin:0;width:100%!important;min-height:100dvh;border:0;border-radius:0}:global(.community-submission-dialog .el-dialog__footer){position:sticky;bottom:0;padding:14px 18px;background:var(--zh-background-pop)}.submission-header{padding:24px 18px 20px}.submission-heading h2{font-size:25px}.submission-heading p{font-size:13px}.submission-layout{max-height:none;padding:18px;gap:16px}.submission-section{padding:16px}.submission-meta-grid{grid-template-columns:1fr 1fr}.submission-meta-grid :deep(.submission-title-field),.submission-meta-grid :deep(.submission-effect-field){grid-column:1 / -1}.submission-slide-list{grid-template-columns:1fr}.submission-variable-fields{grid-template-columns:1fr 1fr}.submission-variable-fields :deep(.el-select){grid-column:1 / 2}.submission-variable-description{grid-column:2 / 3}.submission-aside{grid-template-columns:1fr}.submission-drafts-card,.submission-aside-note{grid-column:auto}.submission-draft-list{grid-template-columns:1fr}.submission-readonly-notice{grid-template-columns:auto 1fr}.submission-readonly-notice p{grid-column:1 / -1;text-align:left}}
@media(max-width:430px){:global(.community-submission-dialog .el-dialog__footer){display:grid;grid-template-columns:1fr 1fr;gap:8px}:global(.community-submission-dialog .el-dialog__footer .el-button){margin:0}:global(.community-submission-dialog .el-dialog__footer .el-button:last-child){grid-column:1 / -1}.submission-section-heading{display:grid;gap:5px}.submission-section-heading small{padding:0;white-space:normal}.submission-meta-grid{grid-template-columns:1fr}.submission-meta-grid :deep(.submission-title-field),.submission-meta-grid :deep(.submission-effect-field){grid-column:auto}.submission-metric-grid div{padding:10px}.submission-flow-list li{grid-template-columns:24px minmax(0,1fr) 20px}.submission-variable-row{grid-template-columns:24px minmax(0,1fr) 20px}.submission-variable-fields{grid-template-columns:1fr}.submission-variable-fields :deep(.el-select),.submission-variable-description{grid-column:auto}.submission-variable-description{margin-top:0}}
.submission-content-heading{margin-bottom:14px}.submission-content-heading>div>span{margin:0;color:var(--zh-text-theme);font-size:17px;font-weight:630;letter-spacing:-.01em}

@media (max-width: 1023.98px) { .community-grid { grid-template-columns: repeat(2, 1fr); }.featured-case { grid-template-columns: 1fr; }.feature-visual { min-height: 240px; }.community-toolbar { flex-wrap: wrap; row-gap: 4px; }.toolbar-controls { flex-wrap: wrap; row-gap: 4px; } }
@media (max-width: 767.98px) { .community-search-row { align-items: stretch; flex-direction: column; }.community-search-row :deep(.el-input) { width: 100%; flex-basis: auto; }.community-search-row>.submission-button { width: 100%; margin-left: 0; }.community-toolbar { align-items: stretch; flex-direction: column; }.tab-list { overflow-x: auto; -webkit-overflow-scrolling: touch; }.filters { padding-bottom: 12px; flex-wrap: wrap; }.community-grid { grid-template-columns: 1fr; }.community-card footer button { min-height: 44px; }.card-like { min-height: 40px; }.rank-list { grid-template-columns: 1fr; }.rank-section { padding: 16px; } }
.mobile-filter-toggle,.detail-mobile-footer{display:none}
@media (max-width: 767.98px) {
  .community-page{display:flex;flex-direction:column;width:calc(100% - 32px);padding:12px 0 24px;}
  .community-hero{order:1;padding:8px 0 12px;}
  .community-hero>p{margin-bottom:7px;font-size:11px;}
  .community-hero h1{max-width:24rem;font-size:clamp(24px,6.3vw,29px);line-height:1.24;letter-spacing:-.035em;}
  .community-hero>span{margin-top:8px;font-size:12px;line-height:1.55;}
  .community-search-row{display:grid;grid-template-columns:minmax(0,1fr) 88px;align-items:stretch;gap:8px;margin-top:15px;}
  .community-search-row :deep(.el-input){width:100%;min-width:0;flex-basis:auto;}
  .community-search-row>.submission-button{width:88px;min-width:0;min-height:42px;margin:0;padding:0 6px;font-size:13px;}
  .community-hero :deep(.el-input__wrapper){min-width:0;padding-left:10px;}
  .community-hero :deep(.el-input__inner){font-size:13px;}
  .community-hero :deep(.community-search-button){width:52px;min-width:52px;height:42px;}
  .community-toolbar{order:2;gap:0;margin-top:0;}
  .tab-list{width:100%;gap:16px;scrollbar-width:none;}
  .tab-list::-webkit-scrollbar{display:none;}
  .tab-list button{flex:none;min-height:42px;padding:10px 2px;font-size:13px;white-space:nowrap;}
  .toolbar-controls{width:100%;justify-content:space-between;gap:4px;padding:3px 0 8px;}
  .toolbar-controls :deep(.el-button){min-height:34px;margin:0;padding:0 5px;font-size:12px;}
  .mobile-filter-toggle{display:inline-flex;align-items:center;gap:5px;min-height:34px;padding:0 5px;border:0;border-radius:var(--zh-radius8);color:var(--zh-text-theme);background:transparent;cursor:pointer;font:600 12px var(--zh-font-family);white-space:nowrap;}
  .mobile-filter-toggle span{font-size:17px;font-weight:400;line-height:1;}
  .mobile-filter-toggle:focus-visible{outline:2px solid var(--zh-border-focus);outline-offset:2px;}
  .filters{display:none;flex-basis:100%;width:100%;margin:4px 0 0;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);background:var(--zh-background-light);}
  .filters.mobile-open{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
  .filters :deep(.el-select){width:100%;min-width:0;}
  .community-status-row{order:3;margin-top:10px;}
  .community-error{order:4;}
  .community-grid{order:5;grid-template-columns:1fr;gap:10px;margin-top:12px;}
  .community-pagination{order:6;}
  .rank-section{order:7;margin-top:24px;padding:15px;box-shadow:none;}
  .featured-case{order:8;margin-top:20px;}
  .source-note{order:9;text-align:left;line-height:1.5;}
  .community-card{display:grid;grid-template-columns:38px minmax(0,1fr);column-gap:12px;padding:14px 15px;box-shadow:none;}
  .card-top{grid-column:1/-1;}
  .card-icon{grid-column:1;grid-row:2 / span 2;margin-top:12px;}
  .community-card h3{grid-column:2;min-height:0;margin:11px 0 3px;font-size:15px;line-height:1.35;}
  .community-card>p{grid-column:2;margin:0 0 11px;}
  .community-card>p.card-description{grid-column:1/-1;min-height:0;margin:0 0 12px;}
  .community-card footer{grid-column:1/-1;flex-wrap:wrap;min-width:0;padding-top:8px;}
  .community-card footer button{min-height:36px;}
  .card-actions{margin-left:auto;}
  .rank-header{align-items:flex-start;}
  .rank-controls{width:100%;justify-content:space-between;gap:6px;}
  .rank-controls :deep(.el-segmented){max-width:100%;}
  .rank-row{min-height:46px;}
  .feature-visual{min-height:130px;}
  .feature-copy{padding:18px;}
  .feature-copy h2{margin:12px 0 7px;font-size:20px;}
  .feature-copy dl{margin:14px 0;}
}
@media (max-width: 600px) {
  :global(.community-collection-dialog.el-dialog),:global(.community-report-dialog.el-dialog),:global(.community-report-detail-dialog.el-dialog),:global(.community-reuse-dialog.el-dialog){box-sizing:border-box;display:flex;flex-direction:column;width:100vw!important;height:100dvh;max-height:100dvh;margin:0!important;overflow:hidden;padding:env(safe-area-inset-top, 0px) 0 0;border-radius:0;}
  :global(.community-collection-dialog .el-dialog__header),:global(.community-report-dialog .el-dialog__header),:global(.community-report-detail-dialog .el-dialog__header),:global(.community-reuse-dialog .el-dialog__header){flex:none;margin:0;padding:17px 18px 13px;border-bottom:1px solid var(--zh-line-parting);}
  :global(.community-collection-dialog .el-dialog__headerbtn),:global(.community-report-dialog .el-dialog__headerbtn),:global(.community-report-detail-dialog .el-dialog__headerbtn),:global(.community-reuse-dialog .el-dialog__headerbtn){top:calc(env(safe-area-inset-top, 0px) + 2px);right:6px;width:44px;height:44px;}
  :global(.community-collection-dialog .el-dialog__title),:global(.community-report-dialog .el-dialog__title),:global(.community-report-detail-dialog .el-dialog__title),:global(.community-reuse-dialog .el-dialog__title){display:block;max-width:calc(100% - 36px);overflow:hidden;font-size:17px;font-weight:650;text-overflow:ellipsis;white-space:nowrap;}
  :global(.community-collection-dialog .el-dialog__body),:global(.community-report-dialog .el-dialog__body),:global(.community-report-detail-dialog .el-dialog__body),:global(.community-reuse-dialog .el-dialog__body){flex:1;min-height:0;overflow-y:auto;padding:18px;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
  :global(.community-collection-dialog .el-dialog__body),:global(.community-report-dialog .el-dialog__body),:global(.community-report-detail-dialog .el-dialog__body){padding-bottom:calc(18px + env(safe-area-inset-bottom, 0px));}
  :global(.community-reuse-dialog .el-dialog__footer){display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px;flex:none;padding:10px 18px calc(10px + env(safe-area-inset-bottom));border-top:1px solid var(--zh-line-parting);}
  :global(.community-reuse-dialog .el-dialog__footer .el-button){margin:0;min-height:44px;}
  .collection-row,.report-row{align-items:flex-start;min-height:52px;}
  .collection-item-link{padding:8px 0;white-space:normal;overflow-wrap:anywhere;}
  .collection-row>.el-button,.collection-row>div,.report-row>.el-button{flex:none;}
  .report-row span{padding:8px 0;white-space:normal;overflow-wrap:anywhere;}
  .report-form-grid{grid-template-columns:1fr;}
  .report-form-grid :deep(.el-form-item:nth-child(3)),.report-form-grid :deep(.el-form-item:nth-child(4)){grid-column:auto;}
  .report-dialog>.el-button{width:100%;min-height:44px;}
  .report-detail dl div{grid-template-columns:78px minmax(0,1fr);gap:10px;}
  .reuse-section>header{align-items:flex-start;flex-direction:column;gap:4px;}
  .reuse-resource-picker :deep(.el-checkbox__label){align-items:flex-start;flex-wrap:wrap;white-space:normal;overflow-wrap:anywhere;}
  .reuse-meta-card strong{white-space:normal;overflow-wrap:anywhere;}
}
@media (max-width: 560px) {
  :global(.community-detail-dialog.el-dialog){box-sizing:border-box;display:flex;flex-direction:column;width:100vw!important;height:100dvh;max-height:100dvh;margin:0!important;padding:env(safe-area-inset-top, 0px) 0 0;border:0;border-radius:0;}
  :global(.community-detail-dialog.el-dialog .el-dialog__body){flex:1;min-height:0;overflow:hidden;}
  .detail-dialog{height:100%;min-height:0;overflow:hidden;}
  .detail-shell{display:flex;flex-direction:column;height:100%;min-height:0;}
  .detail-header{position:relative;display:block;flex:none;padding:17px 18px 13px;}
  .detail-heading{padding-right:30px;}
  .detail-heading h2{display:-webkit-box;max-height:3.75em;margin:8px 0 6px;overflow:hidden;font-size:23px;line-height:1.25;-webkit-box-orient:vertical;-webkit-line-clamp:3;}
  .detail-heading>p{display:-webkit-box;overflow:hidden;font-size:12px;line-height:1.5;-webkit-box-orient:vertical;-webkit-line-clamp:2;}
  .detail-tags{gap:5px;margin-top:9px;font-size:11px;}
  .detail-header-actions{gap:8px;margin-top:12px;}
  .detail-favorite-button{width:auto;min-height:36px;padding:0 11px;}
  .detail-favorite-button span{display:inline;}
  .detail-close-button{position:absolute;top:13px;right:13px;width:38px;height:38px;}
  .detail-layout{display:block;flex:1;min-height:0;overflow-y:auto;padding:14px 16px 22px;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
  .detail-main{gap:12px;}
  .detail-content-section{padding:15px;}
  .detail-section-heading{margin-bottom:12px;}
  .detail-section-heading h3{font-size:17px;}
  .detail-section-note{display:none;}
  .detail-highlight{padding:15px;}
  .detail-aside{gap:9px;margin-top:12px;}
  .detail-aside-card{padding:15px;}
  .detail-aside-actions{display:none;}
  .detail-mobile-footer{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;flex:none;padding:10px 16px calc(10px + env(safe-area-inset-bottom));border-top:1px solid var(--zh-line-parting);background:var(--zh-background-pop);box-shadow:0 -8px 20px rgb(24 49 85 / 6%);}
  .detail-mobile-footer .detail-primary-action,.detail-mobile-footer .detail-report-action{min-height:44px;}
  .detail-mobile-footer .detail-report-action{width:auto;padding:0 8px;}
}
@media (max-width: 700px) {
  :global(.community-submission-dialog.el-dialog){box-sizing:border-box;display:flex;flex-direction:column;height:100dvh;max-height:100dvh;padding:env(safe-area-inset-top, 0px) 0 0;}
  :global(.community-submission-dialog .el-dialog__body){flex:1;min-height:0;overflow:hidden;}
  :global(.community-submission-dialog .el-dialog__footer){flex:none;padding-bottom:calc(12px + env(safe-area-inset-bottom));}
  .submission-dialog{display:flex;flex-direction:column;height:100%;min-height:0;}
  .submission-header{flex:none;padding:16px 18px 13px;}
  .submission-heading h2{font-size:22px;}
  .submission-heading p{font-size:12px;line-height:1.45;}
  .submission-layout{flex:1;min-height:0;max-height:none;overflow-y:auto;padding:14px 16px 22px;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
  .submission-section{padding:15px;}
  .submission-aside-card{padding:14px;}
}
</style>
