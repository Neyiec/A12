<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'A12 教学教案' },
  subject: { type: String, default: '' },
  grade: { type: String, default: '' },
  plan: { type: Object, default: null },
  embedded: { type: Boolean, default: false },
  emptyDescription: { type: String, default: '暂无可预览的教案内容' },
})

const emit = defineEmits(['update:modelValue'])

const toText = (value) => {
  if (Array.isArray(value)) return value.map(toText).filter(Boolean).join('\n')
  if (value && typeof value === 'object') return toText(value.content ?? value.text ?? value.description ?? value.name ?? '')
  return String(value ?? '').trim()
}
const toLines = (value) => toText(value).split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
const firstText = (source, keys) => {
  for (const key of keys) {
    const value = toText(source?.[key])
    if (value) return value
  }
  return ''
}
const previewPlan = computed(() => {
  const raw = props.plan && typeof props.plan === 'object' && !Array.isArray(props.plan) ? props.plan : {}
  return raw.lesson_plan && typeof raw.lesson_plan === 'object' && !Array.isArray(raw.lesson_plan) ? raw.lesson_plan : raw
})
const hasPlan = computed(() => Object.keys(previewPlan.value).length > 0)
const planTitle = computed(() => firstText(previewPlan.value, ['title']) || props.title || 'A12 教学教案')
const planSubject = computed(() => firstText(previewPlan.value, ['subject']) || props.subject || '未设置学科')
const planGrade = computed(() => firstText(previewPlan.value, ['grade']) || props.grade || '')
const planDuration = computed(() => Math.max(0, Number(previewPlan.value.duration_minutes || previewPlan.value.duration || 45) || 45))
const teachingGoals = computed(() => firstText(previewPlan.value, ['teaching_goals', 'goals', 'objectives']))
const keyPoints = computed(() => toLines(previewPlan.value.key_points || previewPlan.value.keypoint || previewPlan.value.keyPoints))
const difficultPoints = computed(() => toLines(previewPlan.value.difficult_points || previewPlan.value.difficulties || previewPlan.value.difficultPoints))
const teachingMethods = computed(() => toLines(previewPlan.value.teaching_methods || previewPlan.value.methods || previewPlan.value.teachingMethods))
const teachingResources = computed(() => toLines(previewPlan.value.teaching_resources || previewPlan.value.resources || previewPlan.value.teachingResources))
const processSteps = computed(() => {
  const source = previewPlan.value.lesson_process || previewPlan.value.teaching_process || previewPlan.value.process || []
  const items = Array.isArray(source) ? source : []
  return items.map((item, index) => {
    const raw = item && typeof item === 'object' ? item : { teacher_activity: item }
    const description = firstText(raw, ['description', 'content', 'activity'])
    return {
      title: firstText(raw, ['stage', 'name', 'title', 'activity_name']) || `教学环节 ${index + 1}`,
      duration: Math.max(0, Number(raw.duration_minutes ?? raw.duration ?? raw.minutes) || 0),
      teacherActivity: firstText(raw, ['teacher_activity', 'teacherActivity', 'teacher_actions', 'teacher_behavior', '教师活动']) || description,
      studentActivity: firstText(raw, ['student_activity', 'studentActivity', 'student_actions', 'student_task', '学生活动']),
      designIntent: firstText(raw, ['design_intent', 'designIntent', 'teaching_intent', '设计意图']),
      pptReference: firstText(raw, ['ppt_reference', 'pptReference', 'slide_reference', 'PPT对应']),
    }
  })
})
const classroomActivities = computed(() => {
  const source = previewPlan.value.classroom_activities || previewPlan.value.activities || []
  const items = Array.isArray(source) ? source : []
  return items.map((item, index) => {
    const raw = item && typeof item === 'object' ? item : { description: item }
    const detail = firstText(raw, ['description', 'content', 'activity', 'activity_description', 'steps', 'procedure'])
      || [
        ['教师活动', firstText(raw, ['teacher_activity', 'teacherActivity'])],
        ['学生活动', firstText(raw, ['student_activity', 'studentActivity'])],
        ['分组方式', firstText(raw, ['grouping', 'grouping_method', 'groupingMethod'])],
        ['预期产出', firstText(raw, ['expected_output', 'expectedOutput', 'output'])],
      ].filter(([, value]) => value).map(([label, value]) => `${label}：${value}`).join('\n')
    return {
      name: firstText(raw, ['name', 'title', 'activity_name', 'activityName', 'stage']) || `课堂活动 ${index + 1}`,
      duration: Math.max(0, Number(raw.duration ?? raw.duration_minutes ?? raw.minutes) || 0),
      description: detail,
    }
  })
})
const homework = computed(() => {
  const source = previewPlan.value.homework || []
  const items = Array.isArray(source) ? source : toLines(source)
  return items.map((item) => {
    if (item && typeof item === 'object') {
      const content = firstText(item, ['content', 'text', 'description'])
      const type = firstText(item, ['type', 'category'])
      return type && content ? `${type}：${content}` : content
    }
    return toText(item)
  }).filter(Boolean)
})
const assessment = computed(() => {
  const raw = previewPlan.value.assessment
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    return {
      formative: firstText(raw, ['formative', 'process', '过程性']),
      summative: firstText(raw, ['summative', 'result', '总结性']),
    }
  }
  return { formative: toText(raw), summative: '' }
})
const blackboardDesign = computed(() => firstText(previewPlan.value, ['blackboard_design', 'blackboard']))
const reflection = computed(() => firstText(previewPlan.value, ['reflection', 'teaching_reflection']))
const previewWrapperComponent = computed(() => props.embedded ? 'section' : 'el-dialog')
const previewWrapperProps = computed(() => props.embedded
  ? { class: 'lesson-plan-preview-embedded' }
  : {
      modelValue: props.modelValue,
      title: '教学案预览',
      width: 'min(1060px, 94vw)',
      alignCenter: true,
      class: 'lesson-plan-preview-dialog',
    })
</script>

<template>
  <component
    :is="previewWrapperComponent"
    v-bind="previewWrapperProps"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <article v-if="hasPlan" class="lesson-plan-preview" aria-label="教学案预览内容">
      <header class="lesson-plan-preview-header">
        <span>教学案文档</span>
        <h1>{{ planTitle }}</h1>
        <p>{{ planSubject }}<template v-if="planGrade"> · {{ planGrade }}</template> · {{ planDuration }} 分钟</p>
      </header>

      <details v-if="teachingGoals" class="lesson-plan-preview-section lesson-plan-preview-fold">
        <summary><h2>教学目标</h2></summary>
        <p>{{ teachingGoals }}</p>
      </details>

      <section v-if="keyPoints.length || difficultPoints.length || teachingMethods.length || teachingResources.length" class="lesson-plan-preview-grid">
        <details v-if="keyPoints.length" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>教学重点</h2></summary><ul><li v-for="item in keyPoints" :key="item">{{ item }}</li></ul></details>
        <details v-if="difficultPoints.length" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>教学难点</h2></summary><ul><li v-for="item in difficultPoints" :key="item">{{ item }}</li></ul></details>
        <details v-if="teachingMethods.length" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>教学方法</h2></summary><ul><li v-for="item in teachingMethods" :key="item">{{ item }}</li></ul></details>
        <details v-if="teachingResources.length" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>教学资源</h2></summary><ul><li v-for="item in teachingResources" :key="item">{{ item }}</li></ul></details>
      </section>

      <details v-if="processSteps.length" class="lesson-plan-preview-section lesson-plan-preview-process lesson-plan-preview-fold">
        <summary><h2>教学过程</h2></summary>
        <ol>
          <li v-for="(step, index) in processSteps" :key="`${step.title}-${index}`">
            <div class="lesson-plan-preview-step-number">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="lesson-plan-preview-step-content">
              <header><h3>{{ step.title }}</h3><span v-if="step.duration">{{ step.duration }} 分钟</span></header>
              <dl>
                <template v-if="step.teacherActivity"><dt>教师活动</dt><dd>{{ step.teacherActivity }}</dd></template>
                <template v-if="step.studentActivity"><dt>学生活动</dt><dd>{{ step.studentActivity }}</dd></template>
                <template v-if="step.designIntent"><dt>设计意图</dt><dd>{{ step.designIntent }}</dd></template>
                <template v-if="step.pptReference"><dt>PPT 对应</dt><dd>{{ step.pptReference }}</dd></template>
              </dl>
            </div>
          </li>
        </ol>
      </details>

      <details v-if="classroomActivities.length" class="lesson-plan-preview-section lesson-plan-preview-activities lesson-plan-preview-fold">
        <summary><h2>课堂活动</h2></summary>
        <article v-for="(activity, index) in classroomActivities" :key="`${activity.name}-${index}`">
          <header><h3>{{ activity.name }}</h3><span v-if="activity.duration">{{ activity.duration }} 分钟</span></header>
          <p v-if="activity.description">{{ activity.description }}</p>
        </article>
      </details>

      <section v-if="blackboardDesign || homework.length || assessment.formative || assessment.summative || reflection" class="lesson-plan-preview-grid">
        <details v-if="blackboardDesign" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>板书设计</h2></summary><p>{{ blackboardDesign }}</p></details>
        <details v-if="homework.length" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>课后作业</h2></summary><ul><li v-for="item in homework" :key="item">{{ item }}</li></ul></details>
        <details v-if="assessment.formative" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>形成性评价</h2></summary><p>{{ assessment.formative }}</p></details>
        <details v-if="assessment.summative" class="lesson-plan-preview-section lesson-plan-preview-fold"><summary><h2>总结性评价</h2></summary><p>{{ assessment.summative }}</p></details>
        <details v-if="reflection" class="lesson-plan-preview-section lesson-plan-preview-wide lesson-plan-preview-fold"><summary><h2>课后反思</h2></summary><p>{{ reflection }}</p></details>
      </section>
    </article>
    <el-empty v-else :description="emptyDescription" :image-size="72" />
    <template v-if="!embedded" #footer><el-button @click="emit('update:modelValue', false)">返回编辑</el-button></template>
  </component>
</template>

<style scoped>
.lesson-plan-preview-embedded .lesson-plan-preview { max-height: none; overflow: visible; padding: 0; }
.lesson-plan-preview { display: grid; gap: 16px; max-height: min(76vh, 820px); overflow: auto; padding: 2px 4px 8px 0; color: var(--zh-text-secondary); }
.lesson-plan-preview-header { padding: 22px 24px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius12); background: var(--zh-background-weaken); }
.lesson-plan-preview-header > span { color: var(--zh-text-theme); font: 700 10px var(--zh-font-number); letter-spacing: .12em; }
.lesson-plan-preview-header h1 { margin: 8px 0 5px; color: var(--zh-text-primary); font-size: 25px; line-height: 1.35; letter-spacing: -.02em; text-wrap: balance; }
.lesson-plan-preview-header p { margin: 0; color: var(--zh-text-caption); font-size: 12px; }
.lesson-plan-preview-section { min-width: 0; padding: 18px 20px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }
.lesson-plan-preview-section h2 { margin: 0 0 10px; color: var(--zh-text-primary); font-size: 14px; }
.lesson-plan-preview-fold { padding: 0; overflow: hidden; }.lesson-plan-preview-fold > summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; color: var(--zh-text-primary); cursor: pointer; list-style: none; }.lesson-plan-preview-fold > summary::-webkit-details-marker { display: none; }.lesson-plan-preview-fold > summary h2 { margin: 0; }.lesson-plan-preview-fold > summary::after { flex: none; color: var(--zh-text-link); content: '展开'; font-size: 11px; font-weight: 600; }.lesson-plan-preview-fold[open] > summary { border-bottom: 1px solid var(--zh-line-parting); background: var(--zh-background-light); }.lesson-plan-preview-fold[open] > summary::after { content: '收起'; }.lesson-plan-preview-fold > p,.lesson-plan-preview-fold > ul { margin: 0 20px 18px; }.lesson-plan-preview-fold.lesson-plan-preview-process > ol { margin: 0 20px 18px; }.lesson-plan-preview-fold.lesson-plan-preview-activities { display: block; }.lesson-plan-preview-fold.lesson-plan-preview-activities > article { margin: 0 20px 12px; }.lesson-plan-preview-fold.lesson-plan-preview-activities > article:last-child { margin-bottom: 18px; }
.lesson-plan-preview-section p { margin: 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.8; white-space: pre-wrap; }
.lesson-plan-preview-section ul { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.lesson-plan-preview-section li { position: relative; padding-left: 13px; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.65; white-space: pre-wrap; }
.lesson-plan-preview-section ul li::before { position: absolute; top: .68em; left: 0; width: 4px; height: 4px; border-radius: 50%; background: var(--zh-text-theme); content: ''; }
.lesson-plan-preview-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.lesson-plan-preview-wide { grid-column: 1 / -1; }
.lesson-plan-preview-process > ol { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.lesson-plan-preview-process > ol > li { display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 12px; padding: 15px 0; border-top: 1px solid var(--zh-line-parting); }
.lesson-plan-preview-process > ol > li:first-child { padding-top: 0; border-top: 0; }
.lesson-plan-preview-process > ol > li:last-child { padding-bottom: 0; }
.lesson-plan-preview-step-number { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font: 700 10px var(--zh-font-number); }
.lesson-plan-preview-step-content header, .lesson-plan-preview-activities article header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.lesson-plan-preview-step-content h3, .lesson-plan-preview-activities h3 { margin: 0; color: var(--zh-text-primary); font-size: 13px; }
.lesson-plan-preview-step-content header span, .lesson-plan-preview-activities header span { flex: none; color: var(--zh-text-caption); font: 700 11px var(--zh-font-number); }
.lesson-plan-preview-step-content dl { display: grid; grid-template-columns: 74px minmax(0, 1fr); gap: 7px 12px; margin: 10px 0 0; }
.lesson-plan-preview-step-content dt { color: var(--zh-text-caption); font-size: 11px; font-weight: 600; }
.lesson-plan-preview-step-content dd { margin: 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.7; white-space: pre-wrap; }
.lesson-plan-preview-activities { display: grid; gap: 12px; }
.lesson-plan-preview-activities > h2 { margin-bottom: 0; }
.lesson-plan-preview-activities article { display: grid; gap: 7px; padding: 12px; border-radius: 8px; background: var(--zh-background-light); }
.lesson-plan-preview-activities p { font-size: 12px; }
@media (max-width: 767.98px) { .lesson-plan-preview { max-height: 72vh; } .lesson-plan-preview-header, .lesson-plan-preview-section { padding: 16px; } .lesson-plan-preview-grid { grid-template-columns: 1fr; } .lesson-plan-preview-wide { grid-column: auto; } .lesson-plan-preview-step-content dl { grid-template-columns: 1fr; gap: 3px; } .lesson-plan-preview-step-content dd { margin-bottom: 6px; } }
</style>
