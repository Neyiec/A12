<!--
  [数据交互说明]
  - 导入: SSE composable、聊天配置、Element Plus 图标
  - Props: sessionId (Java会话ID), initialPrompt (首条用户消息), resourceIds (引用资源)
  - Emits: @back (返回欢迎页), @open-workspace (跳转工作台), @session-created (Python会话ID)
  - 输入: 接收来自 TeacherHome 的会话初始参数
  - 输出: 聊天界面完整交互，流程：用户输入 → 补充信息卡片 → 教案大纲生成 → 资源生成卡片 → 跳转工作台
-->
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Document, Promotion } from '@element-plus/icons-vue'
import { useUserStore } from '../storage/user.js'
import { confirmAiPlan, getAiPlan } from '../apis/teacher.js'
import { useSSEChat } from '../composables/useSSEChat.js'
import {
  CHAT_COMPOSER, CHAT_HEADER, CLASS_LEVEL_OPTIONS, GEN_RESOURCE_DEFAULTS,
  INFO_FORM_DEFAULTS, RESOURCE_CARD_LABELS, STAGE_LABELS, SYSTEM_MESSAGES,
} from '../config/teacherChat.config.js'

const props = defineProps({
  sessionId: { type: String, required: true },
  initialPrompt: { type: String, required: true },
  resourceIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['back', 'open-workspace', 'session-created'])

const userStore = useUserStore()
const { connectStream, abort, isConnecting } = useSSEChat()

// ========== 对话阶段控制 ==========
/**
 * 阶段状态机：
 *   'info'     → 显示补充信息卡片，等待教师填写
 *   'generating_outline' → 正在通过 SSE 生成教学设计大纲
 *   'outline_ready'      → 大纲已展示，等待确认
 *   'resource_ready'     → 资源生成卡片展示，等待点击生成
 *   'generating_resource' → 正在生成资源
 */
const phase = ref('info')

// ========== 消息列表 ==========
/** 每条消息: { id, role: 'user'|'assistant'|'system', type: 'text'|'outline'|'info_form', content, data? } */
const messages = reactive([])
let messageSeq = 0
const messageListRef = ref(null)

// ========== SSE 流式状态 ==========
const currentStage = ref('')
const outlineSlides = ref([])
const outlineData = ref(null)

// ========== 补充信息表单 ==========
/** 使用配置模块的默认值初始化补充信息表单 */
const infoForm = reactive({ ...INFO_FORM_DEFAULTS })

// ========== 资源生成卡片数据 ==========
/** 使用配置模块的默认值初始化资源生成卡片 */
const genResource = reactive({ ...GEN_RESOURCE_DEFAULTS })

// ========== 重新生成标记 ==========
/** 标记当前是否正在重新生成大纲（修改要求触发），用于 handleFinal 判断是覆盖还是新增 */
const isRegenerating = ref(false)

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

// ========== SSE 事件处理 ==========

/** 处理 stage 事件：仅更新阶段状态驱动三点动画，不展示文字 */
function handleStage(data) {
  const stageKey = data.stage || ''
  currentStage.value = STAGE_LABELS[stageKey] || data.message || stageKey
}

/** 处理 outline_delta 事件：逐页累积大纲 */
function handleOutlineDelta(data) {
  if (data.slide) outlineSlides.value.push(data.slide)
}

/** 处理 final 事件：保存完整大纲并渲染大纲卡片（重新生成时覆盖原卡片） */
function handleFinal(data) {
  outlineData.value = data.outline || data
  const slideList = data.slides || outlineSlides.value
  const title = data.title || outlineData.value?.title || '教学设计'
  const slideCount = data.slide_count || slideList.length || 0
  const newData = {
    outline: outlineData.value,
    slides: slideList,
    slideCount,
    outlineId: data.outline_id,
  }
  // 重新生成时：找到原大纲消息直接覆盖，不追加新消息
  if (isRegenerating.value) {
    const idx = [...messages].reverse().findIndex(m => m.type === 'outline')
    if (idx !== -1) {
      const realIdx = messages.length - 1 - idx
      messages[realIdx].content = title
      messages[realIdx].data = newData
    }
    isRegenerating.value = false
  } else {
    addMessage('assistant', 'outline', title, newData)
  }
  outlineSlides.value = []
  currentStage.value = ''
  phase.value = 'outline_ready'
}

/** 处理 error 事件：通过 ElMessage 弹窗告知用户错误 */
function handleSSEError(data) {
  const msg = data?.message || data?.error || SYSTEM_MESSAGES.connectionError
  ElMessage.error(msg)
  currentStage.value = ''
  isRegenerating.value = false
  phase.value = 'info'
}

/** 构建 SSE 回调映射 */
function buildSSECallbacks() {
  return {
    onSession: (data) => {
      if (data.session_id) emit('session-created', data.session_id)
    },
    onStage: handleStage,
    onQuestion: () => { /* 不再使用 question 事件 */ },
    onToolResult: () => { /* 不再在聊天中展示检索结果 */ },
    onPrompt: () => {},
    onProgress: () => {},
    onOutlineDelta: handleOutlineDelta,
    onFinal: handleFinal,
    onError: handleSSEError,
    onDone: () => { currentStage.value = '' },
  }
}

// ========== 补充信息确认 ==========

/** 确认补充信息，构建上下文消息，发起 SSE 大纲生成 */
async function confirmInfo() {
  // 校验课程名称必填
  if (!infoForm.courseName.trim()) {
    ElMessage.warning('请输入课程名称')
    return
  }

  phase.value = 'generating_outline'

  // 构建包含补充信息的上下文消息
  const contextMsg = [
    `${infoForm.stage}${infoForm.subject}${infoForm.grade}${infoForm.textbook}`,
    `课程名称：《${infoForm.courseName.trim()}》`,
    `班级学情：${infoForm.classLevel}`,
    `个性化需求：${infoForm.requirements}`,
  ].join('，')

  await connectStream('/api/v1/python/outlines/chat/stream', {
    user_id: String(userStore.userInfo?.user_id || ''),
    session_id: props.sessionId,
    message: contextMsg,
    history: [],
    resource_ids: props.resourceIds,
    enable_rag: props.resourceIds.length > 0,
    enable_web: false,
  }, buildSSECallbacks())
}

// ========== 大纲操作 ==========

/** 确认教学设计大纲，切换到资源生成卡片阶段 */
function confirmOutline() {
  // 从大纲数据中提取资源卡片信息
  const outline = outlineData.value
  const slides = outline?.slides || []
  genResource.name = (infoForm.courseName.trim() || outline?.title || '教学设计') + ' 课件'
  genResource.slideCount = slides.length || GEN_RESOURCE_DEFAULTS.slideCount
  genResource.theme = GEN_RESOURCE_DEFAULTS.theme
  genResource.description = RESOURCE_CARD_LABELS.pptDesc
    .replace('{count}', genResource.slideCount)
    .replace('{theme}', genResource.theme)
  phase.value = 'resource_ready'
}

/** 打开大纲修改模态框 */
async function modifyOutline() {
  outlineDialogVisible.value = true
  // 若尚未加载大纲数据，从后端拉取
  if (!planTask.value) {
    planLoading.value = true
    try {
      planTask.value = (await getAiPlan(props.sessionId))?.data || (await getAiPlan(props.sessionId))
    } catch {
      ElMessage.error('教学大纲加载失败')
      outlineDialogVisible.value = false
    } finally {
      planLoading.value = false
    }
  }
}

/** 修改要求：必须填写说明 → 通知后端 → 重新通过 SSE 生成大纲 */
async function submitModifyRequirement() {
  if (!planComment.value.trim()) {
    ElMessage.warning('请填写修改要求')
    return
  }
  planSubmitting.value = true
  try {
    // 通知后端补充要求
    await confirmAiPlan(props.sessionId, {
      action: 'supplement',
      comment: planComment.value.trim(),
      plan_version: Number(planTask.value?.plan_version) || 1,
    })
  } catch {
    // 即使通知失败也继续尝试重新生成
  }
  // 在清空前保存修改要求文本
  const requirement = planComment.value.trim()
  // 标记为重新生成模式，关闭对话框并重置状态，重新发起 SSE 大纲生成
  isRegenerating.value = true
  outlineDialogVisible.value = false
  planComment.value = ''
  planSubmitting.value = false
  outlineSlides.value = []
  phase.value = 'generating_outline'
  // 构建包含修改要求的上下文消息
  const contextMsg = [
    `${infoForm.stage}${infoForm.subject}${infoForm.grade}${infoForm.textbook}`,
    `课程名称：《${infoForm.courseName.trim()}》`,
    `班级学情：${infoForm.classLevel}`,
    `${requirement}`,
  ].join('，')
  await connectStream('/api/v1/python/outlines/chat/stream', {
    user_id: String(userStore.userInfo?.user_id || ''),
    session_id: props.sessionId,
    message: contextMsg,
    history: [],
    resource_ids: props.resourceIds,
    enable_rag: props.resourceIds.length > 0,
    enable_web: false,
  }, buildSSECallbacks())
}

/** 从模态框确认大纲，功能等同大纲卡片上的"确认大纲"按钮 */
function confirmOutlineFromDialog() {
  outlineDialogVisible.value = false
  confirmOutline()
}

// ========== 资源生成 ==========

/** 点击"生成"按钮：跳转到创作工作台 */
function startGenerateResource() {
  phase.value = 'generating_resource'
  // 跳转到创作工作台，由工作台侧完成 PPT 生成
  emit('open-workspace', null)
}

// ========== 生命周期 ==========
onMounted(async () => {
  // 首条用户消息气泡
  addMessage('user', 'text', props.initialPrompt)
  // 显示补充信息卡片
  addMessage('assistant', 'info_form', '补充信息')
})

onBeforeUnmount(() => {
  abort()
})
</script>

<template>
  <div class="chat-container">
    <!-- 顶部导航栏 -->
    <header class="chat-header">
      <el-button text size="small" @click="$emit('back')">{{ CHAT_HEADER.back }}</el-button>
      <el-button text size="small" type="primary" @click="$emit('back')">{{ CHAT_HEADER.newChat }}</el-button>
    </header>

    <!-- 消息列表 -->
    <div ref="messageListRef" class="chat-messages">
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
                  :loading="isConnecting"
                  :disabled="phase !== 'info'"
                  @click="confirmInfo"
                >
                  确认
                </el-button>
              </div>
            </div>

            <!-- 教学设计大纲卡片 -->
            <div v-else-if="msg.type === 'outline'" class="outline-card">
              <div class="outline-header">
                <strong>教学设计大纲</strong>
                <el-tag v-if="msg.data?.slideCount" size="small" round>共 {{ msg.data.slideCount }} 页</el-tag>
              </div>

              <!-- 大纲每页列表 -->
              <ul v-if="msg.data?.slides?.length" class="outline-slides">
                <li v-for="(slide, i) in msg.data.slides" :key="i">
                  <span class="slide-no">{{ String(slide.slide_no || i + 1).padStart(2, '0') }}</span>
                  <div class="slide-info">
                    <strong>{{ slide.title }}</strong>
                    <span v-if="slide.teaching_intent">{{ slide.teaching_intent }}</span>
                  </div>
                </li>
              </ul>

              <!-- 大纲操作按钮 -->
              <div class="outline-actions">
                <el-button
                  v-if="phase === 'outline_ready'"
                  size="small"
                  @click="modifyOutline"
                >
                  修改
                </el-button>
                <el-button
                  v-if="phase === 'outline_ready'"
                  type="primary"
                  size="small"
                  @click="confirmOutline"
                >
                  ✓ 确认大纲
                </el-button>
                <span v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="confirmed-badge">✓ 已确认</span>
              </div>
            </div>

            <!-- 普通 AI 文本消息 -->
            <div v-else class="ai-bubble">
              <span class="ai-avatar"><el-icon><ChatDotRound /></el-icon></span>
              <p>{{ msg.content }}</p>
            </div>
          </template>
        </article>
      </TransitionGroup>

      <!-- 流式加载指示器：三个依次闪烁的点 -->
      <div v-if="isConnecting" class="streaming-indicator">
        <span class="dot-pulse"><i></i><i></i><i></i></span>
      </div>

      <!-- 资源生成卡片：大纲确认后展示，左侧图标 + 右侧生成按钮 -->
      <div v-if="phase === 'resource_ready' || phase === 'generating_resource'" class="resource-cards-area">
        <div class="resource-card">
          <el-icon class="resource-icon" :size="28">
            <Document />
          </el-icon>
          <div class="resource-info">
            <strong>{{ genResource.name }}</strong>
            <span>{{ genResource.description }}</span>
          </div>
          <el-button
            type="primary"
            size="small"
            :loading="phase === 'generating_resource'"
            @click="startGenerateResource"
          >
            生成
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部输入区（flex 布局固定在页面底部，不随消息滚动） -->
    <footer class="chat-composer">
      <div class="composer-input-row">
        <el-input
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          resize="none"
          :placeholder="CHAT_COMPOSER.placeholder"
          readonly
        />
        <el-button
          type="primary"
          circle
          :icon="Promotion"
          disabled
          :aria-label="CHAT_COMPOSER.send"
        />
      </div>
      <p class="composer-hint">{{ CHAT_COMPOSER.hint }}</p>
    </footer>
  </div>

  <!-- 教学大纲确认/修改模态框（由大纲卡片"修改"按钮触发） -->
  <el-dialog v-model="outlineDialogVisible" title="教学设计大纲" width="min(700px, 92vw)" destroy-on-close>
    <div v-loading="planLoading" class="plan-dialog-content">
      <p class="plan-status">请确认以下教学设计大纲，或填写修改要求后重新生成。</p>

      <!-- 可读大纲：复用卡片样式展示每页信息 -->
      <ul v-if="outlineData?.slides?.length" class="plan-outline-list">
        <li v-for="(slide, i) in outlineData.slides" :key="i">
          <span class="plan-slide-no">{{ String(slide.slide_no || i + 1).padStart(2, '0') }}</span>
          <div class="plan-slide-info">
            <strong>{{ slide.title }}</strong>
            <span v-if="slide.teaching_intent">{{ slide.teaching_intent }}</span>
            <span v-if="slide.content_points" class="plan-content">{{ slide.content_points }}</span>
          </div>
        </li>
      </ul>
      <!-- 回退：大纲数据暂不可用时显示提示 -->
      <p v-else class="plan-fallback">大纲数据暂未就绪，请关闭后重试。</p>

      <el-input v-model="planComment" type="textarea" :rows="3" placeholder="请描述您希望调整的内容，例如：增加互动环节、调整难度、精简内容…" />
    </div>
    <template #footer>
      <el-button :loading="planSubmitting" :disabled="!planComment.trim()" @click="submitModifyRequirement">修改要求</el-button>
      <el-button type="primary" @click="confirmOutlineFromDialog">确认大纲</el-button>
    </template>
  </el-dialog>
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

/* ===== AI 气泡 ===== */
.ai-bubble {
  display: flex;
  gap: 10px;
  max-width: 75%;
  margin: 20px 0;
}
.ai-avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--zh-radius8);
  color: var(--zh-text-white);
  background: var(--zh-gradient-blue);
  font-size: var(--zh-font-size14);
  font-weight: 700;
}
.ai-bubble p {
  margin: 0;
  padding: 12px 18px;
  border-radius: var(--zh-radius18) var(--zh-radius18) var(--zh-radius18) var(--zh-radius8);
  background: var(--zh-background-answer-card);
  color: var(--zh-text-primary);
  font-size: var(--zh-font-size14);
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== 补充信息卡片 ===== */
.info-card {
  max-width: 92%;
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

/* ===== 教学设计大纲卡片 ===== */
.outline-card {
  max-width: 85%;
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--zh-line-heavier);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
  box-shadow: var(--zh-shadow1);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.outline-card:hover {
  box-shadow: var(--zh-shadow2);
  transform: translateY(-1px);
}
.outline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.outline-icon {
  font-size: var(--zh-font-size18);
}
.outline-header strong {
  font-size: var(--zh-font-size15);
  color: var(--zh-text-primary);
}
.outline-slides {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: grid;
  gap: 8px;
}
.outline-slides li {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
  transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.outline-slides li:hover {
  background: var(--zh-background-option);
}
.slide-no {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: var(--zh-radius6);
  background: var(--zh-background-option-on);
  color: var(--zh-text-theme);
  font-size: var(--zh-font-size12);
  font-weight: 600;
}
.slide-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.slide-info strong {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
}
.slide-info span {
  font-size: var(--zh-font-size11);
  color: var(--zh-text-caption);
  line-height: 1.4;
}
.outline-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid var(--zh-line-parting);
}
.confirmed-badge {
  color: var(--zh-green);
  font-size: var(--zh-font-size13);
  font-weight: 600;
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
.outline-card:focus-visible,
.resource-card:focus-visible {
  outline: 2px solid var(--zh-line-theme);
  outline-offset: 2px;
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
  .user-bubble,
  .ai-bubble,
  .info-card,
  .outline-card {
    max-width: 92%;
  }
  .info-label,
  .info-desc {
    display: none;
  }
}

/* ===== 大纲确认模态框内容 ===== */
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
/* 可读大纲列表 */
.plan-outline-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: grid;
  gap: 6px;
  max-height: 360px;
  overflow: auto;
}
.plan-outline-list li {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}
.plan-slide-no {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: var(--zh-radius6);
  background: var(--zh-background-option-on);
  color: var(--zh-text-theme);
  font-size: var(--zh-font-size12);
  font-weight: 600;
}
.plan-slide-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.plan-slide-info strong {
  font-size: var(--zh-font-size13);
  color: var(--zh-text-primary);
}
.plan-slide-info span {
  font-size: var(--zh-font-size11);
  color: var(--zh-text-caption);
  line-height: 1.4;
}
.plan-content {
  color: var(--zh-text-secondary) !important;
  font-size: var(--zh-font-size12) !important;
}
</style>
