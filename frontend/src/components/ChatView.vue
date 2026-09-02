<!--
  [数据交互说明]
  - 导入: 聊天配置、Element Plus 图标、`sendAiSessionMessage`（API-13）、`getAiPlan`（API-14）、`confirmAiPlan`（API-15）
  - Props: sessionId (Java会话ID), initialPrompt (首条用户消息), resourceIds (引用资源)
  - Emits: @back (返回欢迎页), @open-workspace (跳转工作台), @session-created (Python会话ID)
  - 输入: 接收来自 TeacherHome 的会话初始参数
  - 输出: 聊天界面完整交互，流程：用户输入 → 补充信息卡片 → API-13 发消息生成大纲 → API-14 拉取并展示 → 确认/修改(API-15 确认) → 资源生成卡片 → 跳转工作台
  - 流程说明: 大纲生成走 Java 网关，非流式。若 API-13 返回 last_question，转入澄清阶段等待教师补充回复后继续。修改要求通过再次发送 API-13 消息实现重生成。
-->
<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Brush, Document, Promotion } from '@element-plus/icons-vue'
import MarkdownRender from 'markstream-vue'
import { useUserStore } from '../storage/user.js'
import { confirmAiPlan, getAiPlan, getAiSession, listPptTemplates, sendAiSessionMessage } from '../apis/teacher.js'
import {
  CHAT_COMPOSER, CLASS_LEVEL_OPTIONS, CLARIFICATION_LABELS,
  CHAT_RESUME, DESIGN_ACTION_BAR, GEN_RESOURCE_DEFAULTS, INFO_FORM_DEFAULTS,
  latestSessionPush, RESOURCE_CARD_LABELS, SYSTEM_MESSAGES,
} from '../config/teacherChat.config.js'
import PptTemplatePicker from './PptTemplatePicker.vue'

const props = defineProps({
  sessionId: { type: String, required: true },
  initialPrompt: { type: String, default: '' },
  resourceIds: { type: Array, default: () => [] },
  /** 是否为恢复历史会话（来自侧栏历史对话），开启时挂载后拉取消息回显 */
  resume: { type: Boolean, default: false },
})

const emit = defineEmits(['back', 'open-workspace', 'session-created'])

const userStore = useUserStore()

// ========== 对话阶段控制 ==========
/**
 * 阶段状态机：
 *   'info'      → 显示补充信息卡片，等待教师填写
 *   'generating_outline' → 正在通过 API-13 + API-14 获取教学设计大纲
 *   'clarifying'         → 后端返回澄清问题，等待教师补充回复
 *   'outline_ready'      → 大纲已展示，等待确认
 *   'resource_ready'     → 资源生成卡片展示，等待点击生成
 *   'generating_resource' → 正在生成资源
 */
const phase = ref('info')

/** 正在请求提纲/大纲的加载态（用于按钮 loading 与流式指示器） */
const isRequesterLoading = ref(false)
/** 恢复历史会话的加载态（进入已有对话时短暂展示"恢复历史对话…"） */
const resumeLoading = ref(false)

// ========== 消息列表 ==========
/** 每条消息: { id, role: 'user'|'assistant'|'system', type: 'text'|'outline'|'info_form'|'clarification', content, data? } */
const messages = reactive([])
let messageSeq = 0
const messageListRef = ref(null)

// ========== 教学设计方案数据 ==========
/** 完整大纲数据（Markdown + 元数据），由 API-14 拉取的 plan_json 填充 */
const outlineData = ref(null)
/** 最新一次用于展示的大纲版本号（提交确认/修改时携带，防并发冲突） */
const planVersion = ref(1)

// ========== 补充信息表单 ==========
/** 使用配置模块的默认值初始化补充信息表单 */
const infoForm = reactive({ ...INFO_FORM_DEFAULTS })

// ========== 澄清交互 ==========
/** 当前待补充的澄清问题文本 */
const lastClarification = ref('')
/** 澄清/修改输入框内容 */
const composerInput = ref('')

// ========== 资源生成卡片数据 ==========
/** 使用配置模块的默认值初始化资源生成卡片 */
const genResource = reactive({ ...GEN_RESOURCE_DEFAULTS })
/** 生成 PPT 前选择的后端模板；工作台只负责编辑生成结果，不在此阶段换肤。 */
const pptTemplateDialogVisible = ref(false)
const pptTemplateLoading = ref(false)
const pptTemplateLoadError = ref('')
const pptTemplates = ref([])
const selectedPptTemplateTheme = ref('')
const pptTemplateDraftTheme = ref('')
let pptTemplateRequest = null

// ========== 大纲对话框 ==========
/** 教学大纲确认/修改模态框 */
const outlineDialogVisible = ref(false)
/** 大纲数据（从后端加载） */
const planTask = ref(null)
/** 对话框加载中 */
const planLoading = ref(false)
/** 对话框提交中 */
const planSubmitting = ref(false)
/** 补充/退回说明 */
const planComment = ref('')

// ========== 辅助函数 ==========

const normalizePptTemplate = (template) => {
  const theme = String(template?.theme || '').trim()
  if (!theme) return null
  return {
    theme,
    name: String(template?.template_name || theme).trim() || theme,
    description: String(template?.description || '适用于课堂课件生成的 PPT 模板。').trim(),
    aliases: Array.isArray(template?.aliases)
      ? template.aliases.map((item) => String(item).trim()).filter(Boolean).slice(0, 4)
      : [],
    isDefault: Boolean(template?.is_default),
    filename: String(template?.filename || '').trim(),
  }
}

const selectedPptTemplate = computed(() => pptTemplates.value.find((item) => item.theme === selectedPptTemplateTheme.value) || null)
const pptTemplateName = computed(() => selectedPptTemplate.value?.name || selectedPptTemplateTheme.value || '')
const pptTemplateStorageKey = () => `a12:ppt-template:session:${props.sessionId}`
const readStoredPptTemplateTheme = () => {
  try { return window.localStorage.getItem(pptTemplateStorageKey()) || '' } catch { return '' }
}
const persistPptTemplateTheme = () => {
  if (!selectedPptTemplateTheme.value) return
  try { window.localStorage.setItem(pptTemplateStorageKey(), selectedPptTemplateTheme.value) } catch { /* 浏览器禁用本地存储时仍保留本次选择 */ }
}

const loadPptTemplates = async (force = false) => {
  if (pptTemplateRequest) return pptTemplateRequest
  if (pptTemplates.value.length && !force) return pptTemplates.value
  pptTemplateLoading.value = true
  pptTemplateLoadError.value = ''
  pptTemplateRequest = (async () => {
    try {
      const response = await listPptTemplates()
      const data = isOk(response) ? response.data : response
      const source = Array.isArray(data) ? data : data?.templates
      const templates = (Array.isArray(source) ? source : []).map(normalizePptTemplate).filter(Boolean)
      if (!templates.length) throw new Error('后端暂未提供可用的 PPT 模板')
      pptTemplates.value = templates
      const availableThemes = new Set(templates.map((item) => item.theme))
      const preferredThemes = [
        readStoredPptTemplateTheme(),
        String(data?.default_theme || '').trim(),
        templates.find((item) => item.isDefault)?.theme || '',
        templates[0].theme,
      ]
      selectedPptTemplateTheme.value = preferredThemes.find((theme) => availableThemes.has(theme)) || templates[0].theme
      persistPptTemplateTheme()
      if (outlineData.value) fillGenResource(outlineData.value)
      return templates
    } catch (error) {
      pptTemplateLoadError.value = error?.response?.data?.message || error?.message || 'PPT 模板加载失败'
      return []
    } finally {
      pptTemplateLoading.value = false
    }
  })()
  try {
    return await pptTemplateRequest
  } finally {
    pptTemplateRequest = null
  }
}

const openPptTemplateDialog = async () => {
  pptTemplateDialogVisible.value = true
  pptTemplateDraftTheme.value = selectedPptTemplateTheme.value
  await loadPptTemplates()
  pptTemplateDraftTheme.value = selectedPptTemplateTheme.value
}

const confirmPptTemplate = (template) => {
  const theme = template?.theme || pptTemplateDraftTheme.value
  const selected = pptTemplates.value.find((item) => item.theme === theme)
  if (!selected) return ElMessage.warning('请先选择一个 PPT 模板')
  selectedPptTemplateTheme.value = selected.theme
  pptTemplateDraftTheme.value = selected.theme
  persistPptTemplateTheme()
  pptTemplateDialogVisible.value = false
  fillGenResource(outlineData.value)
  ElMessage.success(`已选择“${selected.name}”，生成 PPT 时将采用此模板`)
}

/** 添加消息到列表并自动滚动 */
function addMessage(role, type, content, data) {
  messageSeq += 1
  messages.push({ id: messageSeq, role, type, content, data })
  scrollToBottom()
}

/** 滚动消息列表到底部 */
async function scrollToBottom() {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/** 判断响应是否成功（兼容 code 0 / 200） */
function isOk(res) {
  return res && (res.code === 0 || res.code === 200)
}

/**
 * 将后端 plan_json 结构化大纲转换为 Markdown 文本，供 MarkdownRender 展示。
 * @param {Object} planJson - 来自 API-14 的 plan_json
 * @returns {string} Markdown 大纲文本
 */
function planJsonToMarkdown(planJson) {
  if (!planJson) return ''
  const lines = []
  if (planJson.title) lines.push(`# ${planJson.title}`)
  if (planJson.summary) {
    lines.push('', '> 摘要：' + planJson.summary)
  }
  const slides = Array.isArray(planJson.slides) ? planJson.slides : []
  for (const slide of slides) {
    lines.push('', `## ${slide.slide_no ?? ''} ${slide.title || ''}`.trim(), '')
    const points = Array.isArray(slide.content_points) ? slide.content_points : []
    points.forEach((point) => lines.push(`- ${point}`))
    if (slide.teaching_intent) lines.push('', `**教学意图**：${slide.teaching_intent}`)
    if (slide.visual_suggestion) lines.push(`**视觉建议**：${slide.visual_suggestion}`)
  }
  return lines.join('\n')
}

// ========== 大纲请求与结果落库 ==========

/**
 * 组合补充信息为 API-13 的 message 输入。
 * @param {string} extra - 追加的澄清回复或修改要求
 * @returns {string} 拼装后的自然语言输入
 */
function buildContextMessage(extra = '') {
  const parts = [
    `${infoForm.stage}${infoForm.subject}${infoForm.grade}${infoForm.textbook}`,
    `课程名称：《${infoForm.courseName.trim()}》`,
    `班级学情：${infoForm.classLevel}`,
    `个性化需求：${infoForm.requirements}`,
  ]
  if (extra) parts.push(`补充要求：${extra}`)
  return parts.join('，')
}

/**
 * 调用 API-13 发送消息，驱动 Java 转发 Python 生成大纲。
 * 返回解析后的 ConversationVO；若后端需要澄清，则转入 clarifying 阶段等待教师回复。
 * @param {string} message - 本轮自然语言输入
 */
async function sendMessageToBackend(message) {
  phase.value = 'generating_outline'
  isRequesterLoading.value = true
  try {
    const res = await sendAiSessionMessage(props.sessionId, {
      message,
      resource_ids: JSON.stringify(props.resourceIds || []),
      enable_rag: props.resourceIds.length > 0,
      enable_web: false,
      known_context: {
        title: infoForm.courseName.trim(),
        subject: infoForm.subject,
        grade: infoForm.grade,
      },
    })
    if (!isOk(res)) {
      ElMessage.error(res?.message || SYSTEM_MESSAGES.connectionError)
      phase.value = 'info'
      return
    }
    const data = res.data
    // 归一化澄清问题：真实后端 last_question 为字符串，mock 可能为对象
    const question = (typeof data?.last_question === 'string' && data.last_question.trim())
      ? data.last_question
      : (typeof data?.last_question === 'object' && data.last_question?.text) || ''
    if (question) {
      // 需要澄清：记录问题并等待教师回复
      lastClarification.value = question
      phase.value = 'clarifying'
      addMessage('assistant', 'clarification', question)
      return
    }
    // 无需澄清：拉取最新大纲
    await loadPlan()
  } catch {
    ElMessage.error(SYSTEM_MESSAGES.connectionError)
    phase.value = 'info'
  } finally {
    isRequesterLoading.value = false
  }
}

/**
 * 调用 API-14 拉取大纲 plan_json，转换为 Markdown 后展示。
 */
async function loadPlan() {
  const res = await getAiPlan(props.sessionId)
  const data = isOk(res) ? res.data : null
  const planJson = data?.plan_json
  if (!planJson || typeof planJson !== 'object') {
    ElMessage.info('大纲尚未生成，请稍后重试或补充信息后继续。')
    phase.value = 'info'
    return
  }
  planTask.value = data
  planVersion.value = Number(data?.plan_version) || Number(planJson.version) || 1
  outlineData.value = {
    markdown: planJsonToMarkdown(planJson),
    title: planJson.title || '教学设计方案',
    slideCount: Number(planJson.slide_count) || 0,
    planJson,
    outlineId: data?.python_outline_id || planJson.outline_id,
  }
  phase.value = 'outline_ready'
  addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
  addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
  await scrollToBottom()
}

// ========== 补充信息确认 ==========

/** 确认补充信息，发起教学大纲生成（API-13 → API-14） */
async function confirmInfo() {
  // 校验课程名称必填
  if (!infoForm.courseName.trim()) {
    ElMessage.warning('请输入课程名称')
    return
  }
  addMessage('user', 'text', infoForm.courseName.trim())
  await sendMessageToBackend(buildContextMessage())
}

/** 澄清回复：把教师针对问题的回复作为下一轮输入继续生成 */
async function handleClarificationReply() {
  const text = composerInput.value.trim()
  if (!text) {
    ElMessage.warning('请输入澄清回复')
    return
  }
  addMessage('user', 'text', text)
  composerInput.value = ''
  await sendMessageToBackend(text)
}

// ========== 大纲操作 ==========

/** 依据已确认大纲的大纲数据填充资源生成卡片信息（确认与历史恢复共用）。 */
function fillGenResource(data) {
  if (!data) return
  const slideCount = data?.slideCount || 0
  genResource.name = (infoForm.courseName.trim() || data?.title || '教学设计') + ' 课件'
  genResource.slideCount = slideCount || GEN_RESOURCE_DEFAULTS.slideCount
  genResource.theme = pptTemplateName.value || GEN_RESOURCE_DEFAULTS.theme
  genResource.description = RESOURCE_CARD_LABELS.pptDesc
    .replace('{count}', genResource.slideCount)
    .replace('{theme}', genResource.theme)
}

/** 确认教学设计方案：提交确认动作并切换到资源生成卡片阶段 */
async function confirmOutline() {
  const data = outlineData.value
  if (!data) return
  phase.value = 'resource_ready'
  // 提交确认（非阻塞；失败不阻断进入资源生成，仅提示）
  try {
    await confirmAiPlan(props.sessionId, { action: 'confirm', plan_version: planVersion.value })
  } catch {
    ElMessage.warning('大纲确认状态同步失败，但可继续生成资源。')
  }
  await loadPptTemplates()
  fillGenResource(data)
}

/** 打开教学设计方案修改模态框 */
async function modifyOutline() {
  outlineDialogVisible.value = true
  // 若尚未加载大纲数据，从后端拉取
  if (!planTask.value && !outlineData.value?.markdown) {
    planLoading.value = true
    try {
      const res = await getAiPlan(props.sessionId)
      planTask.value = isOk(res) ? res.data : null
      if (!planTask.value) ElMessage.error('教学方案加载失败')
    } catch {
      ElMessage.error('教学方案加载失败')
      outlineDialogVisible.value = false
    } finally {
      planLoading.value = false
    }
  }
}

/** 修改要求：必须填写说明 → 作为新消息重新生成大纲（API-13 → API-14） */
async function submitModifyRequirement() {
  if (!planComment.value.trim()) {
    ElMessage.warning('请填写修改要求')
    return
  }
  planSubmitting.value = true
  outlineDialogVisible.value = false
  const requirement = planComment.value.trim()
  planComment.value = ''
  planSubmitting.value = false
  await sendMessageToBackend(buildContextMessage(requirement))
}

/** 从模态框确认大纲，功能等同大纲卡片上的"确认大纲"按钮 */
function confirmOutlineFromDialog() {
  outlineDialogVisible.value = false
  confirmOutline()
}

// ========== 资源生成 ==========

/** 点击"生成"按钮：确认模板后跳转到创作工作台编辑生成结果。 */
function startGenerateResource() {
  if (!selectedPptTemplateTheme.value) {
    ElMessage.warning('请先选择 PPT 生成模板')
    void openPptTemplateDialog()
    return
  }
  phase.value = 'generating_resource'
  // 模板选择发生在生成前；进入工作台后继续编辑 AI 生成的页面内容。
  emit('open-workspace', { pptTheme: selectedPptTemplateTheme.value, generationKey: String(Date.now()) })
}

// ========== 生命周期 ==========
onMounted(async () => {
  // 恢复历史会话：拉取会话详情与大纲重建消息与阶段，不透传首条消息
  if (props.resume) {
    await restoreSession()
    return
  }
  // 新会话：首条用户消息气泡 + 补充信息卡片
  addMessage('user', 'text', props.initialPrompt)
  // 显示补充信息卡片
  addMessage('assistant', 'info_form', '补充信息')
  void loadPptTemplates()
  // 将最新会话推送到 TeacherLayout 历史列表（页面未刷新时的暂时性显示）
  latestSessionPush.value = {
    id: props.sessionId,
    title: props.initialPrompt.trim().slice(0, 40) || '未命名对话',
    updated_at: new Date().toISOString(),
  }
})

/** 将后端 messages JSON 字符串解析为消息数组，非法或为空时返回空数组。 */
function parseStoredMessages(raw) {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/** 解析 plan_json（后端可能是 JSON 字符串，也可能已是对象），非法或为空时返回 null。 */
function parsePlanJson(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return parsed && typeof parsed === 'object' ? parsed : null
    } catch {
      return null
    }
  }
  return null
}

/**
 * 恢复已有会话：按"固定三条"还原对话——先渲染前两条用户消息（初始输入、补充信息），再渲染最新大纲。
 * 阶段判定只看 getPlan 返回的 plan_confirm_status：已确认进资源生成；未确认待确认；无大纲则按澄清/补充信息回落。
 */
async function restoreSession() {
  resumeLoading.value = true
  try {
    const [sessionRes, planRes] = await Promise.all([
      getAiSession(props.sessionId),
      getAiPlan(props.sessionId).catch(() => null),
    ])
    const session = isOk(sessionRes) ? sessionRes.data : null
    const task = isOk(planRes) ? planRes.data : null

    // 前两条用户消息作为"初始输入 + 补充信息"气泡渲染（后续各轮 user 皆修改要求，不再重复展示）
    const userMessages = parseStoredMessages(session?.messages)
      .filter((msg) => msg.role === 'user' && msg.content)
      .slice(0, 2)
    userMessages.forEach((msg) => addMessage('user', 'text', msg.content))

    // 有最新大纲：渲染大纲 + 操作栏，并按确认状态进入资源生成或待确认
    const planJson = parsePlanJson(task?.plan_json)
    if (planJson) {
      outlineData.value = {
        markdown: planJsonToMarkdown(planJson),
        title: planJson.title || '教学设计方案',
        slideCount: Number(planJson.slide_count) || 0,
        planJson,
        outlineId: task?.python_outline_id || planJson.outline_id,
      }
      planTask.value = task
      planVersion.value = Number(task?.plan_version) || Number(planJson.version) || 1
      addMessage('assistant', 'markdown', outlineData.value.markdown, { data: outlineData.value })
      addMessage('assistant', 'outline_actions', '', { outlineId: outlineData.value.outlineId })
      if (task?.plan_confirm_status === 'confirmed') {
        await loadPptTemplates()
        fillGenResource(outlineData.value)
        phase.value = 'resource_ready'
      } else {
        phase.value = 'outline_ready'
      }
      await scrollToBottom()
      return
    }

    // 尚未生成大纲：有待答澄清 → 澄清；否则回落到补充信息卡继续发起
    if (session?.last_question) {
      const question = (typeof session.last_question === 'string' && session.last_question.trim())
        ? session.last_question
        : (typeof session.last_question === 'object' && session.last_question?.text) || ''
      lastClarification.value = question
      phase.value = 'clarifying'
      addMessage('assistant', 'clarification', question)
    } else {
      phase.value = 'info'
      addMessage('assistant', 'info_form', '补充信息')
    }
    await scrollToBottom()
  } catch { /* 请求层会统一处理失效会话 */ } finally {
    resumeLoading.value = false
  }
}
</script>

<template>
  <div class="chat-container">
    <!-- 消息列表 -->
    <div ref="messageListRef" class="chat-messages">
      <div v-if="resumeLoading" class="resume-loading">{{ CHAT_RESUME.loading }}</div>
      <TransitionGroup name="msg-enter">
        <article
          v-for="msg in messages"
          :key="msg.id"
          :class="['chat-message', `msg-${msg.role}`, `msg-type-${msg.type}`]"
        >
          <!-- 用户消息：右对齐气泡 -->
          <div v-if="msg.role === 'user'" class="user-bubble">
            {{ msg.content }}
          </div>

          <!-- AI 消息：根据 type 不同渲染 -->
          <template v-else-if="msg.role === 'assistant'">
            <!-- 补充信息卡片（表格样式表单） -->
            <div v-if="msg.type === 'info_form'" class="info-card">
              <div class="info-card-header">
                <strong>补充信息</strong>
              </div>

              <div class="info-table">
                <!-- 基础信息行 -->
                <div class="info-row">
                  <span class="info-label">基础信息</span>
                  <span class="info-desc">学段/学科/年级/教材</span>
                  <span class="info-value-cell">
                    <span class="info-readonly">{{ infoForm.stage }} / {{ infoForm.subject }}</span>
                  </span>
                </div>
                <!-- 班级学情行 -->
                <div class="info-row">
                  <span class="info-label">班级学情</span>
                  <span class="info-desc">学生整体基础水平</span>
                  <span class="info-value-cell">
                    <el-select
                      v-model="infoForm.classLevel"
                      size="small"
                      :disabled="phase !== 'info'"
                    >
                      <el-option
                        v-for="level in CLASS_LEVEL_OPTIONS"
                        :key="level"
                        :label="level"
                        :value="level"
                      />
                    </el-select>
                  </span>
                </div>
                <!-- 课程名称行 -->
                <div class="info-row">
                  <span class="info-label">课程名称</span>
                  <span class="info-desc">教学内容主题</span>
                  <span class="info-value-cell">
                    <el-input
                      v-model="infoForm.courseName"
                      size="small"
                      placeholder="请输入课程名称"
                      :disabled="phase !== 'info'"
                    />
                  </span>
                </div>
                <!-- 个性化需求行 -->
                <div class="info-row">
                  <span class="info-label">个性化需求</span>
                  <span class="info-desc">教学侧重点与风格偏好</span>
                  <span class="info-value-cell">
                    <el-input
                      v-model="infoForm.requirements"
                      type="textarea"
                      :autosize="{ minRows: 2, maxRows: 4 }"
                      size="small"
                      :disabled="phase !== 'info'"
                    />
                  </span>
                </div>
              </div>

              <!-- 确认按钮 -->
              <div class="info-actions">
                <el-button
                  type="primary"
                  :loading="isRequesterLoading"
                  :disabled="phase !== 'info'"
                  @click="confirmInfo"
                >
                  确认
                </el-button>
              </div>
            </div>

            <!-- 澄清问题消息（后端需要补充信息时展示） -->
            <div v-else-if="msg.type === 'clarification'" class="clarification-card">
              <div class="clarification-card-header">
                <strong>{{ CLARIFICATION_LABELS.title }}</strong>
              </div>
              <p class="clarification-question">{{ msg.content }}</p>
              <p class="clarification-hint">{{ CLARIFICATION_LABELS.hint }}</p>
            </div>

            <!-- AI Markdown 大纲消息：使用 markstream-vue 渲染，占满全宽 -->
            <div v-else-if="msg.type === 'markdown'" class="ai-bubble">
              <div class="ai-markdown-body">
                <MarkdownRender
                  mode="chat"
                  :content="msg.content"
                  :final="true"
                  :fade="false"
                  max-live-nodes="0"
                />
              </div>
            </div>

            <!-- 大纲操作栏（独立消息类型，在 Markdown 方案下方） -->
            <div v-else-if="msg.type === 'outline_actions'" class="outline-actions-bar">
              <el-button
                v-if="phase === 'outline_ready'"
                size="small"
                @click="modifyOutline"
              >
                {{ DESIGN_ACTION_BAR.modify }}
              </el-button>
              <el-button
                v-if="phase === 'outline_ready'"
                type="primary"
                size="small"
                :loading="isRequesterLoading"
                @click="confirmOutline"
              >
                {{ DESIGN_ACTION_BAR.confirm }}
              </el-button>
              <span v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="confirmed-badge">{{ DESIGN_ACTION_BAR.confirmed }}</span>
            </div>

            <!-- 普通 AI 文本消息（同样使用 MarkdownRender 渲染以支持 MD 格式，占满全宽） -->
            <div v-else class="ai-bubble">
              <div class="ai-markdown-body">
                <MarkdownRender
                  mode="chat"
                  :content="msg.content"
                  :final="true"
                  :fade="false"
                  max-live-nodes="0"
                />
              </div>
            </div>
          </template>
        </article>
      </TransitionGroup>

      <!-- 加载指示器：正在请求大纲时显示三个依次闪烁的点 -->
      <div v-if="isRequesterLoading" class="streaming-indicator">
        <span class="dot-pulse"><i></i><i></i><i></i></span>
      </div>

      <!-- 资源生成卡片：大纲确认后先选生成模板，再进入工作台编辑结果 -->
      <div v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="resource-cards-area">
        <div class="resource-card">
          <el-icon class="resource-icon" :size="28">
            <Document />
          </el-icon>
          <div class="resource-info">
            <strong>{{ genResource.name }}</strong>
            <span>{{ genResource.description }}</span>
            <div class="resource-template-choice">
              <span>生成模板：{{ pptTemplateName || '加载中…' }}</span>
              <el-button
                class="resource-template-change"
                type="primary"
                plain
                round
                size="small"
                :icon="Brush"
                :disabled="phase === 'generating_resource'"
                @click="openPptTemplateDialog"
              >
                {{ pptTemplateName ? '更换模板' : '选择模板' }}
              </el-button>
            </div>
          </div>
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedPptTemplateTheme"
            :loading="phase === 'generating_resource'"
            @click="startGenerateResource"
          >
            生成 PPT
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部输入区（flex 布局固定在页面底部，不随消息滚动）
         澄清阶段启用输入框，供教师补充回复后端提出的澄清问题 -->
    <footer class="chat-composer">
      <div class="composer-input-row" :class="{ 'is-editable': phase === 'clarifying' }">
        <el-input
          v-model="composerInput"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          resize="none"
          :placeholder="phase === 'clarifying' ? CHAT_COMPOSER.clarificationPlaceholder : CHAT_COMPOSER.placeholder"
          :readonly="phase !== 'clarifying'"
          @keydown.enter.exact.prevent="handleClarificationReply"
        />
        <el-button
          type="primary"
          circle
          :icon="Promotion"
          :disabled="phase !== 'clarifying'"
          :loading="isRequesterLoading"
          :aria-label="CHAT_COMPOSER.send"
          @click="handleClarificationReply"
        />
      </div>
      <p class="composer-hint">{{ CHAT_COMPOSER.hint }}</p>
    </footer>
  </div>

  <!-- 教学设计方案确认/修改模态框（由操作栏"修改"按钮触发） -->
  <el-dialog v-model="outlineDialogVisible" title="教学设计方案" width="min(700px, 92vw)" destroy-on-close>
    <div v-loading="planLoading" class="plan-dialog-content">
      <p class="plan-status">请确认以下教学设计方案，或填写修改要求后重新生成。</p>

      <!-- Markdown 方案内容 -->
      <div v-if="outlineData?.markdown" class="plan-markdown-body">
        <MarkdownRender
          mode="chat"
          :content="outlineData.markdown"
          :final="true"
          :fade="false"
          max-live-nodes="0"
        />
      </div>
      <!-- 回退：方案数据暂不可用时显示提示 -->
      <p v-else class="plan-fallback">方案数据暂未就绪，请关闭后重试。</p>

      <el-input v-model="planComment" type="textarea" :rows="3" placeholder="请描述您希望调整的内容，例如：增加互动环节、调整难度、精简内容…" />
    </div>
    <template #footer>
      <el-button :loading="planSubmitting" :disabled="!planComment.trim()" @click="submitModifyRequirement">修改要求</el-button>
      <el-button type="primary" @click="confirmOutlineFromDialog">确认大纲</el-button>
    </template>
  </el-dialog>

  <PptTemplatePicker
    v-model="pptTemplateDialogVisible"
    :selected-theme="pptTemplateDraftTheme"
    :templates="pptTemplates"
    :loading="pptTemplateLoading"
    :error="pptTemplateLoadError"
    @update:selected-theme="pptTemplateDraftTheme = $event"
    @retry="loadPptTemplates(true)"
    @confirm="confirmPptTemplate"
  />
</template>

<style scoped>
/* ===== 容器 ===== */
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 68px); /* 减去 topbar 高度 */
  max-width: 880px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ===== 顶部导航栏 ===== */
.chat-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--zh-line-parting);
}

/* ===== 消息滚动区 ===== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
  scroll-behavior: smooth;
}
/* 自定义滚动条（遵循设计规范：宽 4px，色 --zh-line-border） */
.chat-messages::-webkit-scrollbar {
  width: 4px;
}
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}
.chat-messages::-webkit-scrollbar-thumb {
  border-radius: var(--zh-radius4);
  background: var(--zh-line-border);
}
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--zh-line-heavier);
}

/* ===== 用户气泡 ===== */
.user-bubble {
  max-width: 75%;
  margin: 20px 0 20px auto;
  padding: 12px 18px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius8) var(--zh-radius18);
  background: var(--zh-background-user-query);
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== AI 气泡（全宽，无头像） ===== */
.ai-bubble {
  width: 100%;
  margin: 20px 0;
}
/* Markdown 渲染内容容器：全宽展示 */
.ai-markdown-body {
  width: 100%;
  padding: 12px 18px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius18) var(--zh-radius8);
  background: var(--zh-background-answer-card);
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
}

/* ===== 补充信息卡片 ===== */
.info-card {
  width: 100%;
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--zh-line-heavier);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
  box-shadow: var(--zh-shadow1);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.info-card:hover {
  box-shadow: var(--zh-shadow2);
  transform: translateY(-1px);
}
.info-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.info-icon {
  font-size: var(--zh-font-size18);
}
.info-card-header strong {
  font-size: var(--zh-font-size15);
  color: var(--zh-text-primary);
}

/* CSS Table 布局 */
.info-table {
  display: table;
  width: 100%;
  border-collapse: collapse;
}
.info-row {
  display: table-row;
}
.info-label,
.info-desc,
.info-value-cell {
  display: table-cell;
  padding: 10px 12px;
  vertical-align: middle;
  border-bottom: 1px solid var(--zh-line-parting);
}
.info-row:last-child .info-label,
.info-row:last-child .info-desc,
.info-row:last-child .info-value-cell {
  border-bottom: none;
}
.info-label {
  font-weight: 600;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size13);
  white-space: nowrap;
  width: 1%;
}
.info-desc {
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
  width: 1%;
  white-space: nowrap;
}
.info-value-cell {
  width: auto;
}
.info-readonly {
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
}
.info-value-cell :deep(.el-select) {
  width: 140px;
}
.info-value-cell :deep(.el-input) {
  width: 100%;
}
.info-value-cell :deep(.el-textarea__inner) {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
}

/* 补充信息确认按钮 */
.info-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--zh-line-parting);
}

/* ===== 澄清问题卡片（后端需要补充信息时展示） ===== */
.clarification-card {
  width: 100%;
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--zh-line-heavier);
  border-left: 3px solid var(--zh-text-theme);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
}
.clarification-card-header strong {
  font-size: var(--zh-font-size15);
  color: var(--zh-text-primary);
}
.clarification-question {
  margin: 12px 0 4px;
  font-size: var(--zh-font-size14);
  line-height: 1.65;
  color: var(--zh-text-primary);
}
.clarification-hint {
  margin: 0;
  font-size: var(--zh-font-size12);
  color: var(--zh-text-caption);
}

/* ===== 大纲操作栏（Markdown 方案下方独立消息条） ===== */
.outline-actions-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  margin: 4px 0 20px 0;
}

/* ===== 流式加载指示器 ===== */
.streaming-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
}
.dot-pulse {
  display: flex;
  gap: 4px;
}
.dot-pulse i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--zh-text-theme);
  animation: dotPulse 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
.dot-pulse i:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse i:nth-child(3) { animation-delay: 0.4s; }

/* ===== 资源卡片 ===== */
.resource-cards-area {
  padding: 0 0 16px;
  display: grid;
  gap: 8px;
}
.resource-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: var(--zh-background-light);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.resource-card:hover {
  box-shadow: var(--zh-shadow1);
  transform: translateY(-1px);
}
.resource-icon {
  flex-shrink: 0;
  color: var(--zh-text-theme);
}
.resource-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.resource-info strong {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.resource-info span {
  font-size: var(--zh-font-size11);
  color: var(--zh-text-caption);
}
.resource-template-choice {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-top: 2px;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size11);
}
.resource-template-change {
  height: 24px;
  padding: 0 9px;
  border-radius: var(--zh-radius20);
  font-size: var(--zh-font-size11);
  font-weight: 600;
}

/* ===== 底部输入区（flex 布局固定在页面底部，不随消息滚动） ===== */
.chat-composer {
  flex-shrink: 0;
  padding: 12px 0 16px;
  border-top: 1px solid var(--zh-line-parting);
  background: var(--zh-background-primary);
}
.composer-input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 9px 10px 10px;
  border: 1px solid var(--zh-line-parting);
  border-radius: var(--zh-radius16);
  background: var(--zh-background-light-gray);
  box-shadow: none;
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}
/* 澄清阶段启用输入框 */
.composer-input-row.is-editable {
  opacity: 1;
  cursor: text;
  pointer-events: auto;
  border-color: var(--zh-line-heavier);
  background: var(--zh-background-light);
}
.composer-input-row :deep(.el-textarea__inner) {
  min-height: 52px !important;
  padding: 6px 8px;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.6;
}
.composer-hint {
  margin: 8px 0 0;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size11);
  text-align: center;
}

/* ===== 无障碍：键盘焦点可见指示器 ===== */
.info-card:focus-visible,
.resource-card:focus-visible {
  outline: 2px solid var(--zh-line-theme);
  outline-offset: 2px;
}

/* ===== 历史会话恢复加载提示 ===== */
.resume-loading {
  padding: 48px 0;
  text-align: center;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
}

/* ===== 动画 ===== */
.msg-enter-enter-active {
  transition: opacity 300ms cubic-bezier(0, 0, 0.2, 1), transform 300ms cubic-bezier(0, 0, 0.2, 1);
}
.msg-enter-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

@keyframes dotPulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .chat-container {
    padding: 0 12px;
  }
  .user-bubble {
    max-width: 92%;
  }
  .info-label,
  .info-desc {
    display: none;
  }
  .resource-card {
    align-items: flex-start;
  }
  .resource-card > .el-button {
    flex-shrink: 0;
  }
}

/* ===== 方案确认模态框内容 ===== */
.plan-dialog-content .plan-status {
  margin: 0 0 14px;
  color: var(--zh-text-secondary);
  font-size: var(--zh-font-size13);
}
.plan-fallback {
  margin: 0 0 16px;
  padding: 24px;
  text-align: center;
  color: var(--zh-text-caption);
  font-size: var(--zh-font-size13);
  background: var(--zh-background-light);
  border-radius: var(--zh-radius8);
}
/* 模态框内 Markdown 方案内容：限高滚动 */
.plan-markdown-body {
  max-height: 360px;
  overflow: auto;
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--zh-line-parting);
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}
</style>
