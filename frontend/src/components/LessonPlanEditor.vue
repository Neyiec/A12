<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus, Refresh } from '@element-plus/icons-vue'
import { exportLessonPlanDocx, generateLessonPlan } from '../apis/teacher'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'A12 教学教案' },
  subject: { type: String, default: '' },
  grade: { type: String, default: '' },
  outline: { type: Object, default: () => ({}) },
  slides: { type: Array, default: () => [] },
  initialPlan: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'save'])

const loading = ref(false)
const exporting = ref(false)
const errorMessage = ref('')
const requirements = ref('')
const referenceText = ref('')
const lessonPlan = ref(null)

const deepClone = (value, fallback = {}) => {
  try { return JSON.parse(JSON.stringify(value ?? fallback)) } catch { return fallback }
}
const toText = (value) => Array.isArray(value) ? value.filter(Boolean).join('\n') : String(value ?? '')
const toList = (value) => {
  if (Array.isArray(value)) return value.map((item) => typeof item === 'object' ? String(item?.content || item?.text || item?.name || '') : String(item ?? '')).map((item) => item.trim()).filter(Boolean)
  return String(value ?? '').split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
}
const normalizePlan = (raw = {}) => {
  const source = deepClone(raw, {})
  const process = Array.isArray(source.lesson_process) ? source.lesson_process : []
  const activities = Array.isArray(source.classroom_activities) ? source.classroom_activities : []
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
    lesson_process: process.map((item) => ({
      stage: String(item?.stage || item?.name || '教学环节'),
      duration: Number(item?.duration || item?.duration_minutes || 5),
      content: String(item?.content || item?.description || ''),
    })),
    classroom_activities: activities.map((item) => ({
      name: String(item?.name || item?.title || '课堂活动'),
      duration: Number(item?.duration || item?.duration_minutes || 10),
      description: String(item?.description || item?.content || ''),
    })),
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

const close = () => emit('update:modelValue', false)
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
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await generateLessonPlan({
      title: String(lessonPlan.value?.title || props.title || 'A12 教学教案'),
      subject: String(lessonPlan.value?.subject || props.subject || ''),
      grade: String(lessonPlan.value?.grade || props.grade || ''),
      duration_minutes: Number(lessonPlan.value?.duration_minutes || 45),
      teaching_goals: String(lessonPlan.value?.teaching_goals || ''),
      outline: deepClone(props.outline, {}),
      slides: slidePayload.value,
      requirements: requirements.value.trim(),
      reference_text: referenceText.value.trim(),
      language: 'zh-CN',
    })
    lessonPlan.value = normalizeGeneratedPlan(response)
    ElMessage.success('教案已生成，可以直接在线修改')
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error?.message || '教案生成失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
const saveDraft = () => {
  if (!lessonPlan.value) return ElMessage.warning('请先生成教案')
  emit('save', deepClone(lessonPlan.value))
}
const addProcessStep = () => {
  if (!lessonPlan.value) return
  lessonPlan.value.lesson_process.push({ stage: '新教学环节', duration: 5, content: '' })
}
const removeProcessStep = (index) => lessonPlan.value?.lesson_process.splice(index, 1)
const addActivity = () => {
  if (!lessonPlan.value) return
  lessonPlan.value.classroom_activities.push({ name: '新课堂活动', duration: 10, description: '' })
}
const removeActivity = (index) => lessonPlan.value?.classroom_activities.splice(index, 1)
const safeFilename = (value) => String(value || 'A12教学教案').replace(/[\\/:*?"<>|]/g, '').trim().slice(0, 80) || 'A12教学教案'
const exportDocx = async () => {
  if (!lessonPlan.value) return ElMessage.warning('请先生成教案')
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
  if (value && typeof value === 'object') lessonPlan.value = normalizePlan(value)
}, { deep: true, immediate: true })
watch(() => props.modelValue, (visible) => {
  if (visible) {
    errorMessage.value = ''
    if (props.initialPlan) lessonPlan.value = normalizePlan(props.initialPlan)
    else if (!lessonPlan.value) lessonPlan.value = normalizePlan({ title: props.title, subject: props.subject, grade: props.grade })
  }
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="在线教案编辑"
    width="min(960px, 94vw)"
    class="lesson-plan-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="lesson-plan-editor">
      <div class="lesson-plan-intro">
        <div>
          <span class="lesson-plan-kicker">API-142 · API-143</span>
          <h3>从当前课件生成配套教案</h3>
          <p>教案会结合大纲、页面标题、讲稿和资源上下文生成，生成后可在这里直接修改并导出 Word。</p>
        </div>
        <span class="lesson-plan-page-count">{{ slides.length }} 页课件</span>
      </div>

      <section class="lesson-plan-request">
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

      <el-empty v-if="!lessonPlan" description="还没有教案内容，点击下方“生成教案”开始" :image-size="72" />
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
            <article v-for="(step, index) in lessonPlan.lesson_process" :key="`step-${index}`" class="lesson-plan-process-row">
              <span class="lesson-plan-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <el-input v-model="step.stage" placeholder="环节名称" />
              <el-input-number v-model="step.duration" :min="1" :max="120" controls-position="right" />
              <el-input v-model="step.content" placeholder="教学活动、教师行为与学生任务" />
              <el-button text type="danger" :icon="Delete" aria-label="删除教学环节" @click="removeProcessStep(index)" />
            </article>
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
    </div>
    <template #footer>
      <el-button @click="close">关闭</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="generate">{{ lessonPlan ? '重新生成' : '生成教案' }}</el-button>
      <el-button v-if="lessonPlan" @click="saveDraft">保存到项目</el-button>
      <el-button v-if="lessonPlan" type="primary" :loading="exporting" @click="exportDocx">导出 Word</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.lesson-plan-editor { display: grid; gap: 14px; max-height: min(70vh, 760px); overflow: auto; padding: 2px 4px 4px 0; }
.lesson-plan-intro { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding: 18px; border: 1px solid var(--zh-line-theme20); border-radius: 12px; background: var(--zh-background-weaken); }
.lesson-plan-kicker { color: var(--zh-text-theme); font: 700 10px var(--zh-font-number); letter-spacing: .1em; }
.lesson-plan-intro h3 { margin: 7px 0 5px; color: var(--zh-text-primary); font-size: 18px; }
.lesson-plan-intro p { margin: 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.6; }
.lesson-plan-page-count { flex: none; padding: 6px 10px; border-radius: 999px; color: var(--zh-text-theme); background: var(--zh-background-primary); font: 700 11px var(--zh-font-number); }
.lesson-plan-request, .lesson-plan-section { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--zh-line-border); border-radius: 10px; background: var(--zh-background-primary); }
.lesson-plan-field-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 120px; gap: 10px; }
.lesson-plan-editor label { display: grid; gap: 6px; color: var(--zh-text-secondary); font-size: 11px; font-weight: 600; }
.lesson-plan-editor :deep(.el-input-number) { width: 100%; }
.lesson-plan-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--zh-text-primary); font-size: 12px; }
.lesson-plan-section-heading :deep(.el-button) { margin: -5px -7px -5px 0; }
.lesson-plan-two-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.lesson-plan-two-columns .lesson-plan-section { min-width: 0; }
.lesson-plan-process-list, .lesson-plan-activity-list { display: grid; gap: 8px; }
.lesson-plan-process-row { display: grid; grid-template-columns: 28px 150px 92px minmax(0, 1fr) 28px; align-items: center; gap: 7px; }
.lesson-plan-index { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font: 700 10px var(--zh-font-number); }
.lesson-plan-process-row :deep(.el-button), .lesson-plan-inline-fields :deep(.el-button) { width: 28px; margin: 0; }
.lesson-plan-activity-list article { display: grid; gap: 7px; padding: 10px; border-radius: 8px; background: var(--zh-background-light); }
.lesson-plan-inline-fields { display: grid; grid-template-columns: minmax(0, 1fr) 92px 28px; align-items: center; gap: 7px; }
@media (max-width: 760px) { .lesson-plan-field-grid, .lesson-plan-two-columns { grid-template-columns: 1fr 1fr; } .lesson-plan-process-row { grid-template-columns: 28px 1fr 82px 28px; } .lesson-plan-process-row :deep(.el-input:last-of-type) { grid-column: 2 / -1; } }
</style>
