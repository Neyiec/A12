<script setup>
import { computed, onBeforeUnmount } from 'vue'
import LessonPlanPreview from './LessonPlanPreview.vue'
import { secureHtmlForSandbox } from '../utils/htmlSecurity'

const props = defineProps({
  item: {
    type: Object,
    default: () => ({}),
  },
  slides: {
    type: Array,
    default: () => [],
  },
  lessonPlan: {
    type: Object,
    default: null,
  },
  activeView: {
    type: String,
    default: '',
  },
  activeSlideIndex: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['update:activeView', 'update:activeSlideIndex'])

const FIELD_LABELS = {
  template: '内容模板',
  strategies: '训练策略',
  cases: '案例数量',
  includes_quiz: '课堂练习',
  slides: '课件页数',
  duration: '建议用时',
  duration_minutes: '建议用时',
  objective: '教学目标',
  objectives: '教学目标',
  goal: '教学目标',
  summary: '内容摘要',
  description: '内容说明',
  steps: '教学步骤',
  activities: '课堂活动',
  stages: '教学环节',
  materials: '教学材料',
  assessment: '评价方式',
  homework: '课后作业',
}

const HIDDEN_KEYS = new Set([
  'source',
  'project_id',
  'presentation_id',
  'workspace_mode',
  'workspace_context',
  'metadata',
  'elements',
  'html',
  'srcdoc',
  'content_html',
  'slides',
  'pages',
  'lesson_plan',
  'lessonPlan',
  'teaching_plan',
  'teachingPlan',
])

const parseValue = (value, fallback = null) => {
  if (value === undefined || value === null || value === '') return fallback
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

const sourceData = computed(() => props.item?.content_data
  ?? props.item?.contentData
  ?? props.item?.content
  ?? props.item?.body
  ?? '')

const parsedData = computed(() => parseValue(sourceData.value, null))

const toText = (value, fallback = '') => {
  if (value === null || value === undefined) return fallback
  if (Array.isArray(value)) return value.map((item) => toText(item)).filter(Boolean).join('、')
  if (typeof value === 'object') {
    const candidate = ['title', 'name', 'label', 'description', 'content', 'text', 'activity', 'value']
      .map((key) => value[key])
      .find((item) => item !== undefined && item !== null && item !== '')
    return candidate === undefined ? fallback : toText(candidate, fallback)
  }
  if (typeof value === 'boolean') return value ? '已包含' : '未包含'
  return String(value).trim() || fallback
}

const labelForKey = (key) => FIELD_LABELS[key] || String(key)

const toLines = (value) => {
  if (Array.isArray(value)) return value.map((item) => toText(item)).filter(Boolean)
  if (value && typeof value === 'object') return Object.entries(value).map(([key, item]) => `${labelForKey(key)}：${toText(item)}`).filter(Boolean)
  return String(value ?? '').split(/\r?\n|[；;]/).map((item) => item.trim()).filter(Boolean)
}

const rawSlideSource = computed(() => {
  const data = parsedData.value
  if (Array.isArray(data)) return data
  if (!data || typeof data !== 'object') return []
  const candidates = [
    data.slides,
    data.pages,
    data.presentation?.slides,
    data.presentation?.pages,
    data.ppt?.slides,
  ]
  const collection = candidates.find((value) => Array.isArray(value))
  if (collection) return collection
  if (data.html || data.content_html || data.srcdoc) return [data]
  return []
})

const normalizeSlide = (slide, index) => {
  const item = slide && typeof slide === 'object' ? slide : { html: slide }
  const html = String(item.html || item.content_html || item.srcdoc || '').trim()
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)
  const title = toText(item.title || item.name || item.page_title, '')
    || (titleMatch ? toText(titleMatch[1], '') : '')
    || `第 ${index + 1} 页`
  return {
    ...item,
    index,
    html,
    title,
    notes: toText(item.notes || item.speaker_notes || item.description || item.summary, ''),
  }
}

const normalizedSlides = computed(() => {
  const input = props.slides.length ? props.slides : rawSlideSource.value
  return input.map(normalizeSlide).filter((slide) => slide.html)
})

const hasPpt = computed(() => normalizedSlides.value.length > 0)

const unwrapPlan = (value) => {
  const parsed = parseValue(value, value)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
  const nested = parseValue(parsed.lesson_plan ?? parsed.lessonPlan, null)
  if (nested && typeof nested === 'object' && !Array.isArray(nested)) return nested
  return parsed
}

const planLooksUseful = (value) => {
  const plan = unwrapPlan(value)
  if (!plan) return false
  return Object.keys(plan).some((key) => !['source', 'metadata', 'workspace_context'].includes(key))
}

const explicitLessonPlan = computed(() => {
  const data = parsedData.value && typeof parsedData.value === 'object' && !Array.isArray(parsedData.value)
    ? parsedData.value
    : {}
  const candidates = [
    props.lessonPlan,
    data.lesson_plan,
    data.lessonPlan,
    data.teaching_plan,
    data.teachingPlan,
  ]
  const found = candidates.find(planLooksUseful)
  if (found) return unwrapPlan(found)

  const planKeys = ['teaching_goals', 'goals', 'objectives', 'key_points', 'difficult_points', 'lesson_process', 'teaching_process', 'process', 'classroom_activities']
  if (!Array.isArray(parsedData.value) && planKeys.some((key) => Object.prototype.hasOwnProperty.call(data, key))) return data
  return null
})

const derivedLessonPlan = computed(() => {
  if (explicitLessonPlan.value) return explicitLessonPlan.value
  if (!hasPpt.value) return null

  return {
    title: props.item?.title || '社区教学案例',
    subject: props.item?.subject || '',
    grade: props.item?.grade || props.item?.stage || '',
    duration_minutes: Math.max(40, normalizedSlides.value.length * 6),
    teaching_goals: props.item?.description || '借助课件页面组织课堂讲解、观察与练习，帮助学生形成完整理解。',
    lesson_process: normalizedSlides.value.map((slide, index) => ({
      stage: slide.title || `教学环节 ${index + 1}`,
      duration_minutes: Math.max(3, Math.round(40 / normalizedSlides.value.length)),
      teacher_activity: slide.notes || `结合第 ${index + 1} 页内容进行讲解与提问，引导学生关注本页的关键信息。`,
      student_activity: '观察页面信息，完成思考、表达或课堂练习。',
      design_intent: props.item?.description || '让课件内容与课堂活动保持连贯。',
      ppt_reference: `第 ${index + 1} 页`,
    })),
  }
})

const hasLessonPlan = computed(() => planLooksUseful(derivedLessonPlan.value))

const genericObject = computed(() => {
  const data = parsedData.value
  if (data && typeof data === 'object' && !Array.isArray(data)) return data
  return {}
})

const genericEntries = computed(() => Object.entries(genericObject.value)
  .filter(([key, value]) => !HIDDEN_KEYS.has(key) && value !== undefined && value !== null && value !== '')
  .map(([key, value]) => ({
    key,
    label: labelForKey(key),
    value,
    lines: toLines(value),
    kind: Array.isArray(value) ? 'list' : value && typeof value === 'object' ? 'facts' : 'text',
  })))

const genericArray = computed(() => Array.isArray(parsedData.value)
  ? parsedData.value.map((item) => toText(item)).filter(Boolean)
  : [])

const overviewMetrics = computed(() => {
  const data = genericObject.value
  const metrics = []
  if (hasPpt.value) metrics.push({ label: 'PPT 页面', value: normalizedSlides.value.length })
  if (Array.isArray(data.strategies)) metrics.push({ label: '训练策略', value: data.strategies.length })
  if (Number.isFinite(Number(data.cases))) metrics.push({ label: '案例数量', value: Number(data.cases) })
  if (data.includes_quiz !== undefined) metrics.push({ label: '课堂练习', value: data.includes_quiz ? '已包含' : '未包含' })
  return metrics.slice(0, 4)
})

const viewOptions = computed(() => [
  ...(hasPpt.value ? [{ key: 'ppt', label: 'PPT', description: '创作工作台画布' }] : []),
  ...(hasLessonPlan.value ? [{ key: 'lesson_plan', label: '教案', description: '结构化教学案' }] : []),
])

const effectiveView = computed(() => {
  if (viewOptions.value.some((option) => option.key === props.activeView)) return props.activeView
  return viewOptions.value[0]?.key || 'overview'
})

const hasOverview = computed(() => Boolean(
  genericEntries.value.length
  || genericArray.value.length
  || props.item?.description
  || props.item?.title,
))

const activeSlide = computed(() => normalizedSlides.value[props.activeSlideIndex] || normalizedSlides.value[0] || null)

const selectView = (view) => emit('update:activeView', view)
const selectSlide = (index) => emit('update:activeSlideIndex', index)

const safeCssUrl = (value) => String(value || '').replace(/["'()\\]/g, '')
const withSlideBackground = (source, slide) => {
  const html = String(source || '').trim()
  const color = String(slide?.backgroundColor || slide?.background_color || slide?.background?.color || '').trim()
  const image = String(slide?.backgroundImage || slide?.background_image || slide?.background?.src || '').trim()
  if (!html || (!color && !image)) return html
  const safeColor = /^(#[0-9a-f]{3,8}|rgba?\([^)]{1,80}\)|hsla?\([^)]{1,100}\)|transparent|white|black)$/i.test(color) ? color : ''
  const background = `${safeColor ? `background-color:${safeColor} !important;` : ''}${image ? `background-image:url("${safeCssUrl(image)}") !important;background-size:cover !important;background-position:center !important;` : ''}`
  const style = `<style data-a12-community-page-background>html,body,.slide,.slide.dark{${background}}html,body{background-repeat:no-repeat !important;}</style>`
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, `${style}</head>`)
  return `${style}${html}`
}

const frameObservers = new Set()
const fitPptFrame = (event) => {
  const iframe = event?.currentTarget
  const container = iframe?.parentElement
  if (!iframe || !container) return

  const previous = [...frameObservers].find((entry) => entry.iframe === iframe)
  previous?.observer?.disconnect()
  if (previous) frameObservers.delete(previous)

  const resize = () => {
    const width = container.clientWidth
    const height = container.clientHeight
    if (!width || !height) return
    iframe.style.transform = `scale(${Math.min(width / 1280, height / 720)})`
  }

  resize()
  if (typeof ResizeObserver === 'undefined') {
    frameObservers.add({ iframe, observer: null })
    return
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  frameObservers.add({ iframe, observer })
}

onBeforeUnmount(() => {
  frameObservers.forEach(({ observer }) => observer?.disconnect())
  frameObservers.clear()
})
</script>

<template>
  <section class="community-content-preview" aria-label="社区内容可视化预览">
    <div v-if="viewOptions.length > 1" class="content-preview-toolbar">
      <div class="content-view-switch" role="tablist" aria-label="内容预览方式">
        <button
          v-for="option in viewOptions"
          :key="option.key"
          type="button"
          role="tab"
          :aria-selected="effectiveView === option.key"
          :class="{ active: effectiveView === option.key }"
          @click="selectView(option.key)"
        >
          {{ option.label }}
        </button>
      </div>
      <span>{{ viewOptions.find((option) => option.key === effectiveView)?.description }}</span>
    </div>

    <div v-if="effectiveView === 'ppt' && activeSlide" class="ppt-preview" aria-label="PPT 预览">
      <div class="ppt-preview-heading">
        <div>
          <span class="preview-eyebrow">PPT PREVIEW</span>
          <strong>创作工作台画布</strong>
        </div>
        <span>{{ normalizedSlides.length }} 页 · 16:9 等比例缩放</span>
      </div>

      <div class="ppt-preview-stage">
        <iframe
          :srcdoc="secureHtmlForSandbox(withSlideBackground(activeSlide.html, activeSlide))"
          sandbox="allow-scripts"
          :title="`${activeSlide.title} PPT 预览`"
          class="ppt-preview-frame"
          @load="fitPptFrame"
        ></iframe>
      </div>

      <div v-if="normalizedSlides.length > 1" class="ppt-slide-picker" aria-label="PPT 页面导航">
        <button
          v-for="(slide, index) in normalizedSlides"
          :key="`${slide.title}-${index}`"
          type="button"
          :class="{ active: (props.activeSlideIndex || 0) === index }"
          :aria-label="`查看第 ${index + 1} 页：${slide.title}`"
          @click="selectSlide(index)"
        >
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <strong>{{ slide.title }}</strong>
        </button>
      </div>
    </div>

    <div v-else-if="effectiveView === 'lesson_plan' && hasLessonPlan" class="lesson-plan-preview-shell">
      <LessonPlanPreview
        :plan="derivedLessonPlan"
        :title="item?.title || '社区教学教案'"
        :subject="item?.subject || ''"
        :grade="item?.grade || item?.stage || ''"
        embedded
      />
    </div>

    <div v-else-if="hasOverview" class="community-overview">
      <div class="overview-intro">
        <span class="preview-eyebrow">STRUCTURED CONTENT</span>
        <h4>{{ item?.title || '社区内容' }}</h4>
        <p>{{ item?.description || '这份社区内容已整理为可阅读的结构化摘要。' }}</p>
      </div>

      <div v-if="overviewMetrics.length" class="overview-metrics">
        <div v-for="metric in overviewMetrics" :key="metric.label" class="overview-metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </div>

      <div v-if="genericEntries.length" class="overview-entry-grid">
        <article v-for="entry in genericEntries" :key="entry.key" class="overview-entry">
          <header><span>{{ entry.label }}</span><i aria-hidden="true">·</i></header>
          <ul v-if="entry.kind === 'list'" class="overview-list">
            <li v-for="line in entry.lines" :key="line">{{ line }}</li>
          </ul>
          <dl v-else-if="entry.kind === 'facts'" class="overview-facts">
            <div v-for="(value, key) in entry.value" :key="key"><dt>{{ labelForKey(key) }}</dt><dd>{{ toText(value, '—') }}</dd></div>
          </dl>
          <p v-else>{{ toText(entry.value, '—') }}</p>
        </article>
      </div>

      <div v-if="genericArray.length" class="overview-array">
        <div v-for="(line, index) in genericArray" :key="`${line}-${index}`" class="overview-array-item"><span>{{ String(index + 1).padStart(2, '0') }}</span><p>{{ line }}</p></div>
      </div>
    </div>

    <el-empty v-else description="投稿未填写可预览的内容" :image-size="64" />
  </section>
</template>

<style scoped>
.community-content-preview { min-width: 0; }
.content-preview-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.content-preview-toolbar > span { color: var(--zh-text-caption); font-size: 11px; }
.content-view-switch { display: inline-flex; flex: none; gap: 3px; padding: 3px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.content-view-switch button { min-width: 58px; padding: 7px 12px; border: 0; border-radius: 6px; color: var(--zh-text-caption); background: transparent; cursor: pointer; font: 600 11px/1.2 var(--zh-font-text, inherit); transition: color .16s ease, background .16s ease, box-shadow .16s ease, transform .16s ease; }
.content-view-switch button:hover { color: var(--zh-text-theme); }
.content-view-switch button:active { transform: scale(.98); }
.content-view-switch button.active { color: var(--zh-text-theme); background: var(--zh-background-pop); box-shadow: var(--zh-shadow1); }
.content-view-switch button:focus-visible { outline: 2px solid var(--zh-border-focus); outline-offset: 2px; }
.preview-eyebrow { color: var(--zh-text-theme); font: 700 10px/1 var(--zh-font-number, inherit); letter-spacing: .12em; }
.ppt-preview { display: grid; gap: 12px; }
.ppt-preview-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.ppt-preview-heading > div { display: grid; gap: 5px; }
.ppt-preview-heading strong { color: var(--zh-text-primary); font-size: 13px; }
.ppt-preview-heading > span { color: var(--zh-text-caption); font-size: 11px; white-space: nowrap; }
.ppt-preview-stage { position: relative; width: 100%; aspect-ratio: 16 / 9; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background-color: #eef0f4; background-image: radial-gradient(#c9ced7 1px, transparent 1px); background-size: 18px 18px; box-shadow: 0 14px 30px rgb(40 57 82 / 10%); }
.ppt-preview-frame { position: absolute; top: 0; left: 0; display: block; width: 1280px; height: 720px; border: 0; background: #fff; transform-origin: top left; }
.ppt-slide-picker { display: flex; gap: 7px; overflow-x: auto; padding: 1px; scrollbar-width: thin; }
.ppt-slide-picker button { display: grid; grid-template-columns: 26px minmax(0, 1fr); flex: 0 0 min(190px, 44%); align-items: center; gap: 8px; min-width: 126px; padding: 8px; border: 1px solid var(--zh-line-parting); border-radius: 7px; color: var(--zh-text-secondary); background: var(--zh-background-pop); cursor: pointer; text-align: left; transition: border-color .16s ease, background .16s ease, transform .16s ease; }
.ppt-slide-picker button:hover { border-color: var(--zh-border-focus); transform: translateY(-1px); }
.ppt-slide-picker button.active { border-color: var(--zh-theme-primary); background: var(--zh-background-weaken); }
.ppt-slide-picker button > span { display: grid; width: 26px; height: 26px; place-items: center; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-background-option-on); font: 600 10px/1 var(--zh-font-number, inherit); }
.ppt-slide-picker button > strong { overflow: hidden; color: inherit; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.lesson-plan-preview-shell { min-width: 0; }
.community-overview { display: grid; gap: 14px; }
.overview-intro { padding: 18px 20px; border: 1px solid var(--zh-line-theme20); border-radius: var(--zh-radius12); background: var(--zh-background-weaken); }
.overview-intro h4 { margin: 8px 0 6px; color: var(--zh-text-primary); font-size: 18px; line-height: 1.35; }
.overview-intro p { max-width: 68ch; margin: 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.7; }
.overview-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden; border: 1px solid var(--zh-line-parting); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.overview-metric { display: grid; gap: 5px; padding: 12px 14px; border-right: 1px solid var(--zh-line-parting); }
.overview-metric:last-child { border-right: 0; }
.overview-metric span { color: var(--zh-text-caption); font-size: 10px; }
.overview-metric strong { color: var(--zh-text-primary); font: 700 20px/1.1 var(--zh-font-number, inherit); }
.overview-entry-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.overview-entry { min-width: 0; padding: 14px 16px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius10); background: var(--zh-background-primary); }
.overview-entry header { display: flex; align-items: center; gap: 6px; margin-bottom: 9px; color: var(--zh-text-primary); font-size: 13px; font-weight: 650; }
.overview-entry header i { color: var(--zh-text-theme); font-style: normal; }
.overview-entry p { margin: 0; color: var(--zh-text-secondary); font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.overview-list { display: grid; gap: 7px; margin: 0; padding: 0; list-style: none; }
.overview-list li { position: relative; padding-left: 14px; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.6; word-break: break-word; }
.overview-list li::before { position: absolute; top: .7em; left: 0; width: 5px; height: 5px; border-radius: 50%; background: var(--zh-text-theme); content: ''; }
.overview-facts { display: grid; gap: 7px; margin: 0; }
.overview-facts div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding-bottom: 7px; border-bottom: 1px solid var(--zh-line-parting); }
.overview-facts div:last-child { padding-bottom: 0; border-bottom: 0; }
.overview-facts dt { flex: none; color: var(--zh-text-caption); font-size: 11px; }
.overview-facts dd { min-width: 0; margin: 0; color: var(--zh-text-secondary); font-size: 12px; text-align: right; word-break: break-word; }
.overview-array { display: grid; gap: 8px; }
.overview-array-item { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; align-items: start; padding: 11px 12px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.overview-array-item > span { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 7px; color: var(--zh-text-theme); background: var(--zh-background-option-on); font: 700 10px/1 var(--zh-font-number, inherit); }
.overview-array-item p { margin: 2px 0 0; color: var(--zh-text-secondary); font-size: 12px; line-height: 1.6; }
@media (max-width: 767.98px) and (hover: none) and (pointer: coarse) {
  .content-preview-toolbar { align-items: flex-start; flex-direction: column; gap: 7px; margin-bottom: 12px; }
  .content-view-switch { display: flex; width: 100%; }
  .content-view-switch button { flex: 1; min-height: 40px; font-size: 13px; }
  .content-preview-toolbar > span { padding-left: 2px; font-size: 11px; }
  .overview-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .overview-metric:nth-child(2) { border-right: 0; }
  .overview-metric:nth-child(-n + 2) { border-bottom: 1px solid var(--zh-line-parting); }
  .overview-entry-grid { grid-template-columns: 1fr; }
  .ppt-preview-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
  .ppt-preview-stage { box-shadow: none; }
  .ppt-slide-picker { gap: 8px; padding: 2px 0 4px; scroll-snap-type: x proximity; -webkit-overflow-scrolling: touch; }
  .ppt-slide-picker button { flex-basis: min(64%, 220px); min-height: 44px; scroll-snap-align: start; }
  .overview-intro { padding: 15px; }
  .overview-intro h4 { font-size: 16px; }
  .overview-intro p { font-size: 12px; }
  .overview-metric { padding: 10px 12px; }
  .overview-metric strong { font-size: 18px; }
  .overview-entry { padding: 13px 14px; }
  .overview-facts div { align-items: flex-start; }
}
</style>
