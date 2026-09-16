<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { exportLessonPlanDocx, generateLessonPlan } from '../apis/teacher'

const props = defineProps({
  title: { type: String, default: 'A12 教学教案' },
  subject: { type: String, default: '' },
  grade: { type: String, default: '' },
  outline: { type: Object, default: () => ({}) },
  slides: { type: Array, default: () => [] },
  initialPlan: { type: Object, default: null },
})

const emit = defineEmits(['save', 'autosave'])

// 手机档（<768px）切换教学过程行为卡片堆叠；与全局断点 767.98px 对齐。
const isMobile = ref(false)
let mobileMediaQuery = null
const handleMobileMediaChange = (event) => { isMobile.value = event.matches }

const loading = ref(false)
const exporting = ref(false)
const errorMessage = ref('')
const requirements = ref('')
const referenceText = ref('')
const lessonPlan = ref(null)
const hasGeneratedPlan = ref(false)
let autosaveTimer = null
let lastSyncedPlanSignature = ''

const deepClone = (value, fallback = {}) => {
  try { return JSON.parse(JSON.stringify(value ?? fallback)) } catch { return fallback }
}
const planSignature = (value) => {
  try { return JSON.stringify(value || {}) } catch { return '' }
}
const toText = (value) => Array.isArray(value) ? value.filter(Boolean).join('\n') : String(value ?? '')
const toList = (value) => {
  if (Array.isArray(value)) return value.map((item) => typeof item === 'object' ? String(item?.content || item?.text || item?.name || '') : String(item ?? '')).map((item) => item.trim()).filter(Boolean)
  return String(value ?? '').split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
}
const toDuration = (value, fallback = 5) => {
  const duration = Number(value)
  return Number.isFinite(duration) && duration > 0 ? duration : fallback
}
const toProcessText = (value) => {
  if (Array.isArray(value)) return value.map(toProcessText).filter(Boolean).join('；')
  if (value && typeof value === 'object') {
    return toProcessText(value.content ?? value.text ?? value.description ?? value.activity ?? value.name ?? value.title ?? '')
  }
  return String(value ?? '').trim()
}
const firstProcessText = (item, keys) => {
  for (const key of keys) {
    const value = toProcessText(item?.[key])
    if (value) return value
  }
  return ''
}
const normalizeProcessStep = (raw, index) => {
  const item = raw && typeof raw === 'object' && !Array.isArray(raw)
    ? raw
    : { teacher_activity: raw }
  const legacyContent = firstProcessText(item, ['content', 'description', 'activity', '教学活动'])
  return {
    ...item,
    stage: firstProcessText(item, ['stage', 'name', '环节']) || `教学环节 ${index + 1}`,
    duration_minutes: toDuration(item.duration_minutes ?? item.duration ?? item.minutes),
    // 真正的教案接口以这四个字段返回教学过程；保留 content 是为了兼容历史草稿。
    teacher_activity: firstProcessText(item, ['teacher_activity', 'teacherActivity', 'teacher_actions', 'teacher_behavior', '教师活动', '教师行为']) || legacyContent,
    student_activity: firstProcessText(item, ['student_activity', 'studentActivity', 'student_actions', 'student_task', '学生任务', '学生活动']),
    design_intent: firstProcessText(item, ['design_intent', 'designIntent', 'teaching_intent', '教学意图', '设计意图']),
    ppt_reference: firstProcessText(item, ['ppt_reference', 'pptReference', 'slide_reference', '课件关联', 'PPT对应']),
    content: legacyContent,
  }
}
const describeActivityDetails = (item) => {
  const directDescription = firstProcessText(item, [
    'description', 'content', 'activity', 'activity_description', 'activityDescription',
    'activity_content', 'activityContent', 'steps', 'procedure', 'process', 'task',
    'activity_steps', '活动描述', '活动步骤', '任务',
  ])
  if (directDescription) return directDescription

  return [
    ['教师活动', firstProcessText(item, ['teacher_activity', 'teacherActivity', 'teacher_actions', 'teacher_behavior', '教师活动', '教师行为'])],
    ['学生活动', firstProcessText(item, ['student_activity', 'studentActivity', 'student_actions', 'student_task', '学生任务', '学生活动'])],
    ['分组方式', firstProcessText(item, ['grouping', 'grouping_method', 'groupingMethod', '分组方式'])],
    ['预期产出', firstProcessText(item, ['expected_output', 'expectedOutput', 'output', '预期产出'])],
  ].filter(([, value]) => value).map(([label, value]) => `${label}：${value}`).join('\n')
}
const describeProcessActivity = (step) => {
  if (!step) return ''
  return [
    ['教师活动', toProcessText(step.teacher_activity)],
    ['学生活动', toProcessText(step.student_activity)],
    ['设计意图', toProcessText(step.design_intent)],
  ].filter(([, value]) => value).map(([label, value]) => `${label}：${value}`).join('\n')
}
const normalizeActivity = (raw, index, processSteps = []) => {
  const item = raw && typeof raw === 'object' && !Array.isArray(raw)
    ? raw
    : { description: raw }
  const stageName = firstProcessText(item, ['stage', 'stage_name', 'stageName', 'lesson_stage', 'lessonStage', '环节'])
  const matchedProcess = processSteps.find((step) => stageName && step.stage === stageName) || processSteps[index]
  const name = firstProcessText(item, [
    'name', 'title', 'activity_name', 'activityName', 'activity_title', 'activityTitle',
    'topic', '活动名称', '活动标题', '活动',
  ]) || stageName || matchedProcess?.stage || `课堂活动 ${index + 1}`
  const description = describeActivityDetails(item)
    || describeProcessActivity(matchedProcess)
    || ''
  return {
    ...item,
    name,
    duration: toDuration(item.duration ?? item.duration_minutes ?? item.minutes ?? item.time ?? item.时长 ?? item.时间 ?? matchedProcess?.duration_minutes, 10),
    description,
  }
}
const normalizePlan = (raw = {}) => {
  const source = deepClone(raw, {})
  const process = Array.isArray(source.lesson_process) ? source.lesson_process : []
  const activities = Array.isArray(source.classroom_activities) ? source.classroom_activities : []
  const normalizedProcess = process.map(normalizeProcessStep)
  const assessment = source.assessment && typeof source.assessment === 'object' && !Array.isArray(source.assessment)
    ? source.assessment
    : { formative: String(source.assessment || ''), summative: '' }
  return {
    ...source,
    title: String(source.title || props.title || 'A12 教学教案'),
    subject: String(source.subject || props.subject || ''),
    grade: String(source.grade || props.grade || ''),
    duration_minutes: Number(source.duration_minutes || 45),
    teaching_goals: toText(source.teaching_goals),
    key_points: toList(source.key_points),
    difficult_points: toList(source.difficult_points),
    teaching_methods: toList(source.teaching_methods),
    teaching_resources: toList(source.teaching_resources),
    lesson_process: normalizedProcess,
    // 真实模型偶尔只为课堂活动返回时长；此处优先使用其原始字段，缺失时关联同一份教案的教学过程补齐展示。
    classroom_activities: activities.map((activity, index) => normalizeActivity(activity, index, normalizedProcess)),
    blackboard_design: toText(source.blackboard_design),
    homework: Array.isArray(source.homework)
      ? source.homework.map((item) => typeof item === 'object' ? { type: String(item?.type || '课后作业'), content: String(item?.content || item?.text || '') } : { type: '课后作业', content: String(item) })
      : toList(source.homework).map((item) => ({ type: '课后作业', content: item })),
    assessment: {
      formative: String(assessment.formative || assessment.process || assessment.过程性 || ''),
      summative: String(assessment.summative || assessment.result || assessment.总结性 || ''),
    },
    reflection: toText(source.reflection),
  }
}
const unwrapResponse = (response) => {
  if (response && typeof response === 'object' && Object.prototype.hasOwnProperty.call(response, 'code')) {
    const code = Number(response.code)
    if (![0, 200].includes(code)) throw new Error(response.message || '请求失败')
    return Object.prototype.hasOwnProperty.call(response, 'data') ? response.data : response
  }
  return response
}
const normalizeGeneratedPlan = (response) => {
  const payload = unwrapResponse(response) || {}
  const nested = payload.lesson_plan && typeof payload.lesson_plan === 'object' && !Array.isArray(payload.lesson_plan)
    ? payload.lesson_plan
    : payload
  return normalizePlan({
    ...nested,
    lesson_plan_id: payload.lesson_plan_id || nested.lesson_plan_id,
    title: nested.title || payload.title,
    subject: nested.subject || payload.subject,
    grade: nested.grade || payload.grade,
  })
}
const ensureLessonPlan = () => {
  if (!lessonPlan.value) {
    lessonPlan.value = normalizePlan({
      title: props.title,
      subject: props.subject,
      grade: props.grade,
    })
  }
  return lessonPlan.value
}

const listText = (key) => computed({
  get: () => lessonPlan.value ? (lessonPlan.value[key] || []).join('\n') : '',
  set: (value) => { if (lessonPlan.value) lessonPlan.value[key] = toList(value) },
})
const keyPointsText = listText('key_points')
const difficultPointsText = listText('difficult_points')
const teachingMethodsText = listText('teaching_methods')
const teachingResourcesText = listText('teaching_resources')
const homeworkText = computed({
  get: () => (lessonPlan.value?.homework || []).map((item) => `${item.type ? `${item.type}：` : ''}${item.content || ''}`).join('\n'),
  set: (value) => { if (lessonPlan.value) lessonPlan.value.homework = toList(value).map((item) => ({ type: '课后作业', content: item.replace(/^课后作业：/, '') })) },
})

const slidePayload = computed(() => props.slides.map((slide, index) => ({
  slide_no: Number(slide?.slideNo || slide?.slide_no || index + 1),
  title: String(slide?.title || ''),
  description: String(slide?.description || ''),
  notes: String(slide?.notes || ''),
  content_points: Array.isArray(slide?.content_points) ? slide.content_points : [],
  teaching_intent: String(slide?.teaching_intent || ''),
  visual_suggestion: String(slide?.visual_suggestion || ''),
})))
const generate = async () => {
  if (!props.slides.length) {
    errorMessage.value = '当前还没有可用于生成教案的课件页面。请先创建或导入至少一页 PPT。'
    return
  }
  const draft = ensureLessonPlan()
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await generateLessonPlan({
      title: String(draft.title || props.title || 'A12 教学教案'),
      subject: String(draft.subject || props.subject || ''),
      grade: String(draft.grade || props.grade || ''),
      duration_minutes: Number(draft.duration_minutes || 45),
      teaching_goals: String(draft.teaching_goals || ''),
      outline: deepClone(props.outline, {}),
      slides: slidePayload.value,
      requirements: requirements.value.trim(),
      reference_text: referenceText.value.trim(),
      language: 'zh-CN',
    })
    lessonPlan.value = normalizeGeneratedPlan(response)
    hasGeneratedPlan.value = true
    lastSyncedPlanSignature = planSignature(lessonPlan.value)
    // 生成结果立刻同步给主工作区，顶部“在线预览”无需等待再次手动保存。
    emit('save', deepClone(lessonPlan.value))
    ElMessage.success('教案已生成，可以直接在线修改')
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error?.message || '教案生成失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
const saveDraft = () => {
  if (!hasGeneratedPlan.value || !lessonPlan.value) return ElMessage.warning('请先生成教案')
  lastSyncedPlanSignature = planSignature(lessonPlan.value)
  emit('save', deepClone(lessonPlan.value))
}
const addProcessStep = () => {
  if (!lessonPlan.value) return
  lessonPlan.value.lesson_process.push({
    stage: '新教学环节',
    duration_minutes: 5,
    teacher_activity: '',
    student_activity: '',
    design_intent: '',
    ppt_reference: '',
    content: '',
  })
}
// 手机档卡片默认收起详情，「编辑详情」展开；删除后同步平移已展开的步骤标记。
const expandedProcessSteps = ref([])
const isProcessStepExpanded = (index) => expandedProcessSteps.value.includes(index)
const toggleProcessStep = (index) => {
  const position = expandedProcessSteps.value.indexOf(index)
  if (position >= 0) expandedProcessSteps.value.splice(position, 1)
  else expandedProcessSteps.value.push(index)
}
const removeProcessStep = (index) => {
  lessonPlan.value?.lesson_process.splice(index, 1)
  expandedProcessSteps.value = expandedProcessSteps.value
    .filter((item) => item !== index)
    .map((item) => (item > index ? item - 1 : item))
}
const addActivity = () => {
  if (!lessonPlan.value) return
  lessonPlan.value.classroom_activities.push({ name: '新课堂活动', duration: 10, description: '' })
}
const removeActivity = (index) => lessonPlan.value?.classroom_activities.splice(index, 1)
const safeFilename = (value) => String(value || 'A12教学教案').replace(/[\\/:*?"<>|]/g, '').trim().slice(0, 80) || 'A12教学教案'
const exportDocx = async () => {
  if (!hasGeneratedPlan.value || !lessonPlan.value) return ElMessage.warning('请先生成教案')
  exporting.value = true
  errorMessage.value = ''
  try {
    const response = await exportLessonPlanDocx({
      title: lessonPlan.value.title,
      filename: `${safeFilename(lessonPlan.value.title)}.docx`,
      lesson_plan: deepClone(lessonPlan.value),
    })
    const blob = response?.data instanceof Blob ? response.data : response instanceof Blob ? response : null
    if (!blob) throw new Error('导出接口未返回 DOCX 文件')
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${safeFilename(lessonPlan.value.title)}.docx`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('教案 DOCX 已下载')
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error?.message || '教案导出失败，请稍后重试'
  } finally {
    exporting.value = false
  }
}

watch(() => props.initialPlan, (value) => {
  const currentSignature = planSignature(lessonPlan.value)
  const incomingPlan = value && typeof value === 'object'
    ? normalizePlan(value)
    : normalizePlan({ title: props.title, subject: props.subject, grade: props.grade })
  const incomingSignature = planSignature(incomingPlan)
  // 父组件会在自动保存开始时回写一份快照；如果教师此时已经继续输入，
  // 这份 prop 是旧快照，不能覆盖编辑器里的更新。
  const hasUnsavedLocalChanges = Boolean(hasGeneratedPlan.value && currentSignature && currentSignature !== lastSyncedPlanSignature)
  if (hasUnsavedLocalChanges && incomingSignature !== currentSignature) return
  if (value && typeof value === 'object') {
    lessonPlan.value = incomingPlan
    hasGeneratedPlan.value = true
    lastSyncedPlanSignature = incomingSignature
    return
  }
  hasGeneratedPlan.value = false
  lessonPlan.value = incomingPlan
  lastSyncedPlanSignature = incomingSignature
}, { deep: true, immediate: true })
watch(() => [props.title, props.subject, props.grade], ([title, subject, grade]) => {
  const draft = ensureLessonPlan()
  if (!hasGeneratedPlan.value) {
    if (!draft.title || draft.title === 'A12 教学教案') draft.title = String(title || 'A12 教学教案')
    if (!draft.subject) draft.subject = String(subject || '')
    if (!draft.grade) draft.grade = String(grade || '')
  }
}, { immediate: true })

// 编辑器内容与工作台共用自动保存链路。只有内容真正发生变化时才排队，
// 父组件回写 initialPlan 后会更新签名，不会因响应式同步形成保存循环。
watch(lessonPlan, (value) => {
  if (!hasGeneratedPlan.value || !value) return
  const signature = planSignature(value)
  if (!signature || signature === lastSyncedPlanSignature) return
  clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(() => {
    if (!lessonPlan.value) return
    const snapshot = deepClone(lessonPlan.value)
    lastSyncedPlanSignature = planSignature(snapshot)
    emit('autosave', snapshot)
  }, 800)
}, { deep: true })

onMounted(() => {
  mobileMediaQuery = window.matchMedia('(max-width: 767.98px)')
  isMobile.value = mobileMediaQuery.matches
  mobileMediaQuery.addEventListener('change', handleMobileMediaChange)
})
onBeforeUnmount(() => {
  mobileMediaQuery?.removeEventListener('change', handleMobileMediaChange)
  clearTimeout(autosaveTimer)
})

defineExpose({
  getLessonPlan: () => hasGeneratedPlan.value && lessonPlan.value ? deepClone(lessonPlan.value) : null,
  saveDraft,
})
</script>

<template>
  <section class="lesson-plan-editor" aria-label="教学案编辑器">
    <header class="lesson-plan-editor-toolbar">
      <div>
        <span class="lesson-plan-kicker">{{ hasGeneratedPlan ? '教学案编辑' : '生成设置' }}</span>
        <p>{{ hasGeneratedPlan ? '可直接修改各项内容；顶部“在线预览”会读取当前编辑中的教案。' : '填写必要信息后，结合当前课件内容生成完整教学案。' }}</p>
      </div>
      <div class="lesson-plan-editor-actions">
        <span class="lesson-plan-page-count">{{ slides.length }} 页课件</span>
        <el-button :icon="Refresh" :loading="loading" @click="generate">{{ hasGeneratedPlan ? '重新生成' : '生成教案' }}</el-button>
        <el-button v-if="hasGeneratedPlan" type="primary" :loading="exporting" @click="exportDocx">导出 Word</el-button>
      </div>
    </header>

    <section class="lesson-plan-request">
      <div class="lesson-plan-request-heading"><strong>生成设置</strong><span>模型会参考页面标题、讲稿、大纲和资源上下文。</span></div>
      <div class="lesson-plan-field-grid">
        <label>教案标题<el-input v-model="lessonPlan.title" maxlength="80" /></label>
        <label>学科<el-input v-model="lessonPlan.subject" placeholder="例如：初中生物" /></label>
        <label>年级<el-input v-model="lessonPlan.grade" placeholder="例如：八年级" /></label>
        <label>课时（分钟）<el-input-number v-model="lessonPlan.duration_minutes" :min="10" :max="240" controls-position="right" /></label>
      </div>
      <label>生成要求<el-input v-model="requirements" type="textarea" :rows="2" maxlength="600" show-word-limit placeholder="例如：增加分层作业，安排一次小组探究活动" /></label>
      <label>参考资料补充<el-input v-model="referenceText" type="textarea" :rows="2" maxlength="1200" show-word-limit placeholder="可补充教材版本、课堂约束或希望强调的内容" /></label>
    </section>

    <el-alert v-if="errorMessage" type="error" :closable="false" show-icon>{{ errorMessage }}</el-alert>

    <el-empty v-if="!hasGeneratedPlan" class="lesson-plan-empty" description="教案尚未生成。确认设置后即可生成并在本页继续编辑。" :image-size="72">
      <el-button type="primary" :loading="loading" @click="generate">生成教学案</el-button>
    </el-empty>
    <template v-else>
      <section class="lesson-plan-section">
        <div class="lesson-plan-section-heading"><strong>教学目标</strong><span>支持直接改写</span></div>
        <el-input v-model="lessonPlan.teaching_goals" type="textarea" :rows="3" maxlength="1200" show-word-limit placeholder="输入知识、能力与素养目标" />
      </section>

      <section class="lesson-plan-two-columns">
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>教学重点</strong></div><el-input v-model="keyPointsText" type="textarea" :rows="4" placeholder="一行一个重点" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>教学难点</strong></div><el-input v-model="difficultPointsText" type="textarea" :rows="4" placeholder="一行一个难点" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>教学方法</strong></div><el-input v-model="teachingMethodsText" type="textarea" :rows="4" placeholder="一行一种方法" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>教学资源</strong></div><el-input v-model="teachingResourcesText" type="textarea" :rows="4" placeholder="一行一种资源" /></div>
      </section>

      <section class="lesson-plan-section">
        <div class="lesson-plan-section-heading"><strong>教学过程</strong><el-button text size="small" :icon="Plus" @click="addProcessStep">添加环节</el-button></div>
        <div class="lesson-plan-process-list">
          <template v-for="(step, index) in lessonPlan.lesson_process" :key="`step-${index}`">
            <article v-if="!isMobile" class="lesson-plan-process-row">
              <span class="lesson-plan-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <el-input v-model="step.stage" placeholder="环节名称" />
              <el-input-number v-model="step.duration_minutes" :min="1" :max="120" controls-position="right" />
              <div class="lesson-plan-process-details">
                <label><span>教师活动</span><el-input v-model="step.teacher_activity" type="textarea" :rows="2" placeholder="教师讲解、提问、示范或组织方式" /></label>
                <label><span>学生活动</span><el-input v-model="step.student_activity" type="textarea" :rows="2" placeholder="学生观察、讨论、操作或产出" /></label>
                <label><span>设计意图</span><el-input v-model="step.design_intent" placeholder="本环节要达成的学习目标" /></label>
                <label><span>PPT 对应</span><el-input v-model="step.ppt_reference" placeholder="例如：第 2—3 页" /></label>
              </div>
              <el-button text type="danger" :icon="Delete" aria-label="删除教学环节" @click="removeProcessStep(index)" />
            </article>
            <article v-else class="lesson-plan-process-card">
              <header class="lesson-plan-process-card-head">
                <span class="lesson-plan-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <el-input v-model="step.stage" placeholder="环节名称" />
              </header>
              <label>时长（分钟）<el-input-number v-model="step.duration_minutes" :min="1" :max="120" controls-position="right" /></label>
              <div v-show="isProcessStepExpanded(index)" class="lesson-plan-process-details">
                <label><span>教师活动</span><el-input v-model="step.teacher_activity" type="textarea" :rows="2" placeholder="教师讲解、提问、示范或组织方式" /></label>
                <label><span>学生活动</span><el-input v-model="step.student_activity" type="textarea" :rows="2" placeholder="学生观察、讨论、操作或产出" /></label>
                <label><span>设计意图</span><el-input v-model="step.design_intent" placeholder="本环节要达成的学习目标" /></label>
                <label><span>PPT 对应</span><el-input v-model="step.ppt_reference" placeholder="例如：第 2—3 页" /></label>
              </div>
              <div class="lesson-plan-process-card-actions">
                <el-button text :icon="Edit" :aria-expanded="isProcessStepExpanded(index)" @click="toggleProcessStep(index)">{{ isProcessStepExpanded(index) ? '收起详情' : '编辑详情' }}</el-button>
                <el-button text type="danger" :icon="Delete" aria-label="删除教学环节" @click="removeProcessStep(index)">删除</el-button>
              </div>
            </article>
          </template>
        </div>
        <el-empty v-if="!lessonPlan.lesson_process.length" :image-size="40" description="暂无教学环节" />
      </section>

      <section class="lesson-plan-section">
        <div class="lesson-plan-section-heading"><strong>课堂活动</strong><el-button text size="small" :icon="Plus" @click="addActivity">添加活动</el-button></div>
        <div class="lesson-plan-activity-list">
          <article v-for="(activity, index) in lessonPlan.classroom_activities" :key="`activity-${index}`">
            <div class="lesson-plan-inline-fields"><el-input v-model="activity.name" placeholder="活动名称" /><el-input-number v-model="activity.duration" :min="1" :max="120" controls-position="right" /><el-button text type="danger" :icon="Delete" aria-label="删除课堂活动" @click="removeActivity(index)" /></div>
            <el-input v-model="activity.description" type="textarea" :rows="2" placeholder="描述活动步骤、分组方式和预期产出" />
          </article>
        </div>
        <el-empty v-if="!lessonPlan.classroom_activities.length" :image-size="40" description="暂无课堂活动" />
      </section>

      <section class="lesson-plan-two-columns">
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>板书设计</strong></div><el-input v-model="lessonPlan.blackboard_design" type="textarea" :rows="4" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>课后作业</strong></div><el-input v-model="homeworkText" type="textarea" :rows="4" placeholder="一行一项作业" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>形成性评价</strong></div><el-input v-model="lessonPlan.assessment.formative" type="textarea" :rows="3" /></div>
        <div class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>总结性评价</strong></div><el-input v-model="lessonPlan.assessment.summative" type="textarea" :rows="3" /></div>
      </section>

      <section class="lesson-plan-section"><div class="lesson-plan-section-heading"><strong>课后反思</strong></div><el-input v-model="lessonPlan.reflection" type="textarea" :rows="4" placeholder="记录本课实施后的观察与改进方向" /></section>
    </template>
  </section>
</template>

<style scoped>
.lesson-plan-editor { display: grid; gap: 16px; min-width: 0; padding: 0 0 36px; }
.lesson-plan-editor-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 15px 18px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius10); background: var(--zh-background-weaken); }
.lesson-plan-kicker { display: block; color: var(--zh-text-theme); font: 700 10px var(--zh-font-number); letter-spacing: .1em; }
.lesson-plan-editor-toolbar p { max-width: 47rem; margin: 5px 0 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.6; }
.lesson-plan-editor-actions { display: flex; align-items: center; flex: none; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.lesson-plan-page-count { flex: none; padding: 6px 9px; border-radius: 999px; color: var(--zh-text-theme); background: var(--zh-background-primary); font: 700 11px var(--zh-font-number); }
.lesson-plan-request, .lesson-plan-section { display: grid; gap: 10px; padding: 16px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }
.lesson-plan-request-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.lesson-plan-request-heading strong { color: var(--zh-text-primary); font-size: 13px; }
.lesson-plan-request-heading span { color: var(--zh-text-caption); font-size: 11px; }
.lesson-plan-field-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 120px; gap: 10px; }
.lesson-plan-editor label { display: grid; gap: 6px; color: var(--zh-text-secondary); font-size: 11px; font-weight: 600; }
.lesson-plan-editor :deep(.el-input-number) { width: 100%; }
.lesson-plan-empty { padding: 32px 18px; border: 1px dashed var(--zh-line-theme20); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }
.lesson-plan-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--zh-text-primary); font-size: 12px; }
.lesson-plan-section-heading > span { color: var(--zh-text-caption); font-size: 11px; font-weight: 400; }
.lesson-plan-section-heading :deep(.el-button) { margin: -5px -7px -5px 0; }
.lesson-plan-two-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.lesson-plan-two-columns .lesson-plan-section { min-width: 0; }
.lesson-plan-process-list, .lesson-plan-activity-list { display: grid; gap: 8px; }
.lesson-plan-process-row { display: grid; grid-template-columns: 28px 150px 92px minmax(0, 1fr) 28px; align-items: start; gap: 7px; }
.lesson-plan-index { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font: 700 10px var(--zh-font-number); }
.lesson-plan-process-row > :is(.lesson-plan-index, .el-input, .el-input-number, .el-button) { margin-top: 20px; }
.lesson-plan-process-details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; min-width: 0; }
.lesson-plan-process-details label { display: grid; gap: 4px; min-width: 0; color: var(--zh-text-caption); font-size: 10px; font-weight: 600; }
.lesson-plan-process-details :deep(.el-textarea__inner) { min-height: 52px !important; resize: vertical; }
.lesson-plan-process-row :deep(.el-button), .lesson-plan-inline-fields :deep(.el-button) { width: 28px; margin: 0; }
.lesson-plan-activity-list article { display: grid; gap: 7px; padding: 10px; border-radius: 8px; background: var(--zh-background-light); }
.lesson-plan-inline-fields { display: grid; grid-template-columns: minmax(0, 1fr) 92px 28px; align-items: center; gap: 7px; }
.lesson-plan-process-card { display: grid; gap: 8px; padding: 12px; border-radius: 8px; background: var(--zh-background-light); }
.lesson-plan-process-card-head { display: grid; grid-template-columns: 28px minmax(0, 1fr); align-items: center; gap: 8px; }
.lesson-plan-process-card-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 8px; border-top: 1px solid var(--zh-line-parting); }
.lesson-plan-process-card-actions :deep(.el-button) { min-width: 44px; min-height: 44px; margin: 0; }
@media (max-width: 1023.98px) { .lesson-plan-editor-toolbar { align-items: flex-start; flex-direction: column; } .lesson-plan-editor-actions { justify-content: flex-start; } .lesson-plan-field-grid, .lesson-plan-two-columns, .lesson-plan-process-details { grid-template-columns: 1fr 1fr; } .lesson-plan-process-row { grid-template-columns: 28px 1fr 82px 28px; } .lesson-plan-process-details { grid-column: 2 / -1; } .lesson-plan-process-row > :is(.lesson-plan-index, .el-input, .el-input-number, .el-button) { margin-top: 0; } }
@media (max-width: 767.98px) { .lesson-plan-editor-toolbar, .lesson-plan-request, .lesson-plan-section { padding: 14px; } .lesson-plan-editor-actions { width: 100%; } .lesson-plan-page-count { margin-right: auto; } .lesson-plan-request-heading { align-items: flex-start; flex-direction: column; gap: 4px; } .lesson-plan-field-grid, .lesson-plan-two-columns, .lesson-plan-process-details { grid-template-columns: 1fr; } .lesson-plan-process-details { grid-column: auto; } .lesson-plan-inline-fields { grid-template-columns: minmax(0, 1fr) 92px 44px; } .lesson-plan-inline-fields :deep(.el-button) { width: 44px; min-height: 44px; } }
</style>
