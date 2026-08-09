<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Brush, ChatDotRound, CircleCheck, CopyDocument, DataBoard, Delete, Download, EditPen, FullScreen, Monitor, Picture, Plus, Promotion, VideoPlay } from '@element-plus/icons-vue'
import { addProjectComponent, addProjectPermission, createAiRun, getAiPlan, getAiRun, getProject, getProjectVersionDiff, listProjectVersions, restoreProjectVersion, reviseProjectWithAi, saveProjectVersion, sendAiSessionMessage, updateProjectComponent } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const prompt = ref('')
const selectedSlide = ref(0)
const activePanel = ref('style')
const previewVisible = ref(false)
const planLoading = ref(false)
const planTask = ref(null)
const runStatus = ref('idle')
const runProgress = ref(0)
const runStage = ref('')
const versionDialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const versionLoading = ref(false)
const savingComponent = ref(false)
const versions = ref([])
const versionDiff = ref(null)
const permissionUserId = ref('')
const autosaveState = ref('已保存')
let eventSource = null
let runPollTimer = null
let autosaveTimer = null
const themes = [
  { id: 'blue', name: '经典蓝', color: '#2563eb' },
  { id: 'navy', name: '沉静蓝', color: '#173d78' },
  { id: 'green', name: '自然绿', color: '#1f993f' },
  { id: 'orange', name: '活力橙', color: '#ff6b3f' },
]
const layouts = ['重点陈述', '图文并置', '双栏探究']
const messages = reactive([
  { role: 'assistant', text: '我已根据教学目标整理出一份 6 页课件。你可以直接描述想调整的内容，或在右侧细化当前页面。' },
  { role: 'user', text: '让情境导入更贴近校园生活。' },
  { role: 'assistant', text: '已将导入场景调整为校园旗杆测量任务，并保留小组讨论环节。' },
])
const slides = reactive([
  { title: '勾股定理', eyebrow: '八年级数学 · 第 1 课时', description: '从实际测量出发，发现直角三角形三边之间恒定而优雅的关系。', layout: '重点陈述', theme: 'blue' },
  { title: '情境导入', eyebrow: '01 / 生活中的直角', description: '校园里有哪些直角三角形？用旗杆与影子的测量任务开启今天的探索。', layout: '图文并置', theme: 'blue' },
  { title: '观察与猜想', eyebrow: '02 / 发现关系', description: '拖动顶点，观察两条直角边所对应正方形面积与斜边面积的变化。', layout: '图文并置', theme: 'navy' },
  { title: '公式推导', eyebrow: '03 / 建立模型', description: '将三边长度转化为面积，归纳勾股定理的表达式。', layout: '双栏探究', theme: 'green' },
  { title: '互动练习', eyebrow: '04 / 动手验证', description: '完成三组测量与计算，检验你的发现是否始终成立。', layout: '双栏探究', theme: 'orange' },
])
const current = computed(() => slides[selectedSlide.value])
const theme = computed(() => themes.find((item) => item.id === current.value.theme) || themes[0])
const unwrapResponse = (response) => response?.data || response
const sessionId = computed(() => route.query.sessionId)
const projectId = computed(() => route.query.projectId)
const project = ref(null)
const defaultSlide = (index = 1) => ({ title: `新建页面 ${index}`, eyebrow: '教学内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue' })
const parseJson = (value, fallback = {}) => { try { return typeof value === 'string' ? JSON.parse(value) : (value || fallback) } catch { return fallback } }
const pageToSlide = (page, index) => {
  const content = parseJson(page.page_content)
  return { ...defaultSlide(index + 1), ...content, componentId: page.id || page.component_id, title: content.title || page.page_title || `第 ${index + 1} 页` }
}
const loadProject = async () => {
  if (!projectId.value) return
  try {
    project.value = unwrapResponse(await getProject(projectId.value))
    const pages = Array.isArray(project.value?.pages) ? project.value.pages : []
    slides.splice(0, slides.length, ...(pages.length ? pages.map(pageToSlide) : [defaultSlide()]))
    selectedSlide.value = 0
  } catch (error) { ElMessage.error(error?.message || '项目内容加载失败') }
}
const loadTestCase = () => {
  if (!route.query.testCase) return
  const title = String(route.query.templateTitle || '临时测试案例')
  const presets = {
    'pythagorean-lab': { subject: '八年级数学', activity: '校园测量与直角三角形验证', theme: 'blue' },
    'concept-question-chain': { subject: '通用概念课', activity: '从已有认知到核心概念的问题链', theme: 'navy' },
    'circuit-interaction': { subject: '初中物理', activity: '串并联电路连接、观察与归纳', theme: 'orange' },
    'classical-chinese-intro': { subject: '高中语文', activity: '历史语境、人物关系与文本初读', theme: 'navy' },
    'photosynthesis-evidence': { subject: '初中生物', activity: '基于实验现象建立证据链', theme: 'green' },
  }
  const preset = presets[route.query.testCase] || presets['concept-question-chain']
  const visualType = route.query.testCase === 'pythagorean-lab' ? 'formula' : 'generic'
  slides.splice(0, slides.length,
    { title, eyebrow: `${preset.subject} · 测试案例`, description: `这是可编辑的临时测试案例，可继续调整内容、布局与视觉风格。`, footer: `围绕“${title}”展开完整教学活动。`, layout: '重点陈述', theme: preset.theme, visualType },
    { title: '学习目标', eyebrow: '01 / 明确方向', description: `围绕“${title}”建立知识理解、实践应用与课堂表达目标。`, footer: '明确本节课需要理解、应用和表达的核心内容。', layout: '图文并置', theme: preset.theme, visualType },
    { title: '探究活动', eyebrow: '02 / 课堂任务', description: preset.activity, footer: '在观察、讨论和实践中形成对核心问题的理解。', layout: '双栏探究', theme: preset.theme, visualType },
    { title: '交流与总结', eyebrow: '03 / 形成理解', description: '组织学生展示过程、比较证据并用自己的语言归纳本课核心结论。', footer: '用证据说明结论，并反思本节课的学习过程。', layout: '图文并置', theme: preset.theme, visualType },
  )
  messages.splice(0, messages.length, { role: 'assistant', text: `已载入“${title}”测试案例。你可以编辑页面内容，或继续描述希望调整的方向。` })
  selectedSlide.value = 0
}

/** 静默加载大纲数据（模态框已移至 ChatView 的"修改"按钮触发） */
const loadPlan = async () => {
  if (!sessionId.value) return
  planLoading.value = true
  try { planTask.value = unwrapResponse(await getAiPlan(sessionId.value)) }
  catch (error) { ElMessage.error(error?.message || '教学大纲加载失败') }
  finally { planLoading.value = false }
}
const connectRunEvents = (runId) => {
  eventSource?.close(); eventSource = new EventSource(`/api/v1/ai/runs/${runId}/events`)
  eventSource.onmessage = (event) => {
    try { const payload = JSON.parse(event.data); runStage.value = payload.stage || payload.message || '正在生成教学内容'; runProgress.value = Math.max(0, Math.min(100, Number(payload.progress) || runProgress.value)); if (payload.status) runStatus.value = payload.status; if (payload.preview?.slides && Array.isArray(payload.preview.slides)) slides.splice(0, slides.length, ...payload.preview.slides); if (['completed', 'failed'].includes(payload.status)) eventSource?.close() }
    catch { runStage.value = event.data || runStage.value }
  }
  eventSource.onerror = () => eventSource?.close()
  clearInterval(runPollTimer)
  runPollTimer = setInterval(async () => {
    try {
      const latest = unwrapResponse(await getAiRun(runId))
      runStatus.value = latest?.status || runStatus.value
      runProgress.value = Number(latest?.progress) || runProgress.value
      runStage.value = latest?.stage || latest?.status_message || runStage.value
      if (['completed', 'failed'].includes(runStatus.value)) clearInterval(runPollTimer)
    } catch { /* SSE remains the primary status channel */ }
  }, 3000)
}
const startRun = async () => {
  if (!sessionId.value) return
  try { const run = unwrapResponse(await createAiRun(sessionId.value)); const runId = run?.id || run?.run_id; if (!runId) throw new Error('未获取到生成任务'); runStatus.value = 'running'; runProgress.value = 0; runStage.value = '正在创建生成任务'; connectRunEvents(runId); const latest = unwrapResponse(await getAiRun(runId)); runStatus.value = latest?.status || runStatus.value }
  catch (error) { runStatus.value = 'failed'; ElMessage.error(error?.message || '生成任务创建失败') }
}
const submitRevision = async () => {
  const instruction = prompt.value.trim(); if (!instruction) return
  messages.push({ role: 'user', text: instruction }); prompt.value = ''
  try {
    if (projectId.value) {
      const page = unwrapResponse(await reviseProjectWithAi(projectId.value, { target_type: 'slide', target_id: String(current.value.componentId || selectedSlide.value + 1), instruction, context: JSON.stringify(current.value) }))
      if (page?.id || page?.component_id) slides.splice(selectedSlide.value, 1, pageToSlide(page, selectedSlide.value))
    }
    else if (sessionId.value) await sendAiSessionMessage(sessionId.value, { messages: JSON.stringify([{ role: 'user', content: instruction }]) })
    messages.push({ role: 'assistant', text: '已收到修改要求，正在结合当前页面内容进行调整。' }); ElMessage.success('修改要求已提交')
  } catch (error) { messages.push({ role: 'assistant', text: '修改请求暂未提交成功，请稍后重试。' }); ElMessage.error(error?.message || '修改请求失败') }
}
onMounted(() => { loadTestCase(); loadPlan(); loadProject() })
onBeforeUnmount(() => { eventSource?.close(); clearInterval(runPollTimer) })
const currentPagePayload = () => ({ page_order: selectedSlide.value + 1, page_type: selectedSlide.value === 0 ? 'cover' : 'content', page_title: current.value.title, page_content: JSON.stringify(current.value), components: JSON.stringify([current.value]) })
const persistCurrentSlide = async () => {
  if (!projectId.value || savingComponent.value) return
  savingComponent.value = true; autosaveState.value = '保存中…'
  try {
    const payload = currentPagePayload()
    const response = current.value.componentId ? await updateProjectComponent(projectId.value, current.value.componentId, payload) : await addProjectComponent(projectId.value, payload)
    const saved = unwrapResponse(response)
    current.value.componentId ||= saved?.id || saved?.component_id
    autosaveState.value = '已保存'
  } catch (error) { autosaveState.value = '保存失败'; ElMessage.error(error?.message || '页面保存失败') } finally { savingComponent.value = false }
}
const loadVersions = async () => {
  if (!projectId.value) return ElMessage.warning('演示项目不支持版本管理')
  versionLoading.value = true; versionDialogVisible.value = true
  try { const result = unwrapResponse(await listProjectVersions(projectId.value, { page: 1, size: 30 })); versions.value = result?.records || result?.list || result?.items || [] }
  catch (error) { ElMessage.error(error?.message || '版本历史加载失败') } finally { versionLoading.value = false }
}
const createVersion = async () => { if (!projectId.value) return; try { await saveProjectVersion(projectId.value, { description: `保存第 ${selectedSlide.value + 1} 页调整` }); autosaveState.value = '已创建版本'; await loadVersions(); ElMessage.success('项目版本已保存') } catch (error) { ElMessage.error(error?.message || '版本保存失败') } }
const showVersionDiff = async (version) => { try { versionDiff.value = unwrapResponse(await getProjectVersionDiff(projectId.value, version.id || version.version_id)) } catch (error) { ElMessage.error(error?.message || '差异加载失败') } }
const restoreVersion = async (version) => { try { await restoreProjectVersion(projectId.value, version.id || version.version_id); ElMessage.success('已恢复历史版本'); await loadVersions() } catch (error) { ElMessage.error(error?.message || '版本恢复失败') } }
const grantPermission = async () => { const userId = Number(permissionUserId.value); if (!Number.isInteger(userId) || userId <= 0) return ElMessage.warning('请输入有效用户 ID'); try { await addProjectPermission(projectId.value, { user_id: userId }); permissionUserId.value = ''; permissionDialogVisible.value = false; ElMessage.success('协作者已添加') } catch (error) { ElMessage.error(error?.message || '授权失败') } }
watch(slides, () => { if (!projectId.value) return; autosaveState.value = '待保存'; clearTimeout(autosaveTimer); autosaveTimer = setTimeout(persistCurrentSlide, 700) }, { deep: true })
onBeforeUnmount(() => clearTimeout(autosaveTimer))
const goHome = () => router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })
const exportProject = () => router.push({ path: '/main/exports', query: route.query.preview ? { preview: '1' } : {} })
const addSlide = () => { slides.push({ title: `新建页面 ${slides.length + 1}`, eyebrow: '新建内容', description: '在右侧完善页面文案与布局，或通过 AI 对话继续创作。', layout: '图文并置', theme: 'blue' }); selectedSlide.value = slides.length - 1 }
const copySlide = () => { slides.splice(selectedSlide.value + 1, 0, { ...current.value, title: `${current.value.title} 副本` }); selectedSlide.value++ }
const removeSlide = () => { if (slides.length === 1) return ElMessage.warning('课件至少保留一页'); slides.splice(selectedSlide.value, 1); selectedSlide.value = Math.max(0, selectedSlide.value - 1) }
const sendRevision = () => submitRevision()
</script>

<template>
  <div class="workspace">
    <header class="toolbar">
      <div class="project-title"><el-button text circle aria-label="返回教学助手" @click="goHome"><el-icon><ArrowLeft /></el-icon></el-button><div><strong>{{ current.title }}教学设计</strong><span><el-icon><CircleCheck /></el-icon> 已保存 · 项目 {{ route.query.projectId || '演示' }}</span></div></div>
      <div class="editing-tools"><el-button text :icon="EditPen">文本</el-button><el-button text :icon="Picture">图片</el-button><el-button text :icon="DataBoard">互动组件</el-button><el-button text :icon="Brush">背景</el-button></div>
      <div class="toolbar-actions"><el-button :icon="Monitor" @click="previewVisible = true">预览</el-button><el-button type="primary" :icon="Download" @click="exportProject">导出</el-button></div>
    </header>

    <div class="workspace-grid">
      <aside class="assistant-panel" aria-label="AI 教学助手">
        <header><div class="assistant-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div></header>
        <section class="conversation"><article v-for="(message, index) in messages" :key="index" :class="['message', message.role]"><span v-if="message.role === 'assistant'">智</span><p>{{ message.text }}</p></article></section>
        <footer class="composer"><el-input v-model="prompt" type="textarea" :rows="3" resize="none" placeholder="例如：把提问改得更有启发性" @keydown.ctrl.enter="sendRevision" /><div><span>Ctrl + Enter 发送</span><el-button type="primary" circle :icon="Promotion" :disabled="!prompt.trim()" aria-label="发送修改" @click="sendRevision" /></div></footer>
      </aside>

      <section class="editor-stage">
        <aside class="slide-rail" aria-label="课件页面列表"><button v-for="(slide, index) in slides" :key="`${slide.title}-${index}`" :class="{ active: selectedSlide === index }" @click="selectedSlide = index"><span>{{ String(index + 1).padStart(2, '0') }}</span><div class="thumbnail" :style="{ '--thumb': themes.find((item) => item.id === slide.theme)?.color }"><i></i><b>{{ slide.title }}</b></div></button><el-button text :icon="Plus" @click="addSlide">添加页面</el-button></aside>
        <main class="canvas-area"><div class="canvas-meta"><span>第 {{ selectedSlide + 1 }} 页，共 {{ slides.length }} 页</span><span>16:9 · 自适应窗口</span></div><article class="slide-canvas" :class="`layout-${current.layout}`" :style="{ '--accent': theme.color }"><span class="slide-eyebrow">{{ current.eyebrow }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p><div v-if="current.layout !== '重点陈述'" class="theorem"><template v-if="current.visualType !== 'generic'"><div class="triangle"><i>a</i><i>b</i><i>c</i></div><div class="formula"><span>a² + b²</span><em>=</em><strong>c²</strong><small>拖动顶点，观察面积变化</small></div></template><div v-else class="generic-visual"><span>观察</span><em>→</em><span>探究</span><em>→</em><span>表达</span></div></div><footer><span>{{ current.layout === '重点陈述' ? '本课目标' : '小组任务' }}</span><p>{{ current.footer || '在测量、猜想与验证中理解勾股定理，并用它解决简单的实际问题。' }}</p></footer></article><div class="canvas-controls"><button aria-label="缩小">−</button><span>86%</span><button aria-label="放大">+</button><button aria-label="全屏预览" @click="previewVisible = true"><el-icon><FullScreen /></el-icon></button></div></main>
      </section>

      <aside class="properties" aria-label="页面属性设置"><header><strong>页面属性</strong><span>页面 {{ String(selectedSlide + 1).padStart(2, '0') }}</span></header><div class="tabs"><button :class="{ active: activePanel === 'style' }" @click="activePanel = 'style'">样式</button><button :class="{ active: activePanel === 'layout' }" @click="activePanel = 'layout'">布局</button><button :class="{ active: activePanel === 'animation' }" @click="activePanel = 'animation'">动画</button></div><section v-if="activePanel === 'style'"><label>页面标题</label><el-input v-model="current.title" maxlength="20" show-word-limit /><label>引导文案</label><el-input v-model="current.description" type="textarea" :rows="4" maxlength="70" show-word-limit /><label>主题色</label><div class="theme-picker"><button v-for="item in themes" :key="item.id" :class="{ selected: current.theme === item.id }" :style="{ background: item.color }" :title="item.name" @click="current.theme = item.id"></button></div></section><section v-else-if="activePanel === 'layout'"><label>页面布局</label><div class="layout-picker"><button v-for="item in layouts" :key="item" :class="{ active: current.layout === item }" @click="current.layout = item"><i></i><i></i><span>{{ item }}</span></button></div></section><section v-else><label>页面进入动画</label><el-select model-value="fade"><el-option label="淡入出现" value="fade" /><el-option label="向上浮现" value="rise" /><el-option label="无动画" value="none" /></el-select><label>讲解节奏</label><el-slider :model-value="60" :show-tooltip="false" /><p class="hint">建议保留简洁动画，避免影响学生对知识点的注意力。</p></section><section class="page-actions"><label>页面操作</label><el-button :icon="CopyDocument" @click="copySlide">复制页面</el-button><el-button :icon="Delete" @click="removeSlide">删除页面</el-button></section><div class="assistant-tip"><el-icon><ChatDotRound /></el-icon><p>也可以在左侧直接描述希望调整的内容、语气或活动设计。</p></div></aside>
    </div>

    <el-dialog v-model="previewVisible" class="preview-dialog" width="min(960px, 92vw)" title="课件预览"><div class="preview"><article class="slide-canvas preview-slide" :style="{ '--accent': theme.color }"><span class="slide-eyebrow">{{ current.eyebrow }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p><div class="formula preview-formula"><span>a² + b²</span><em>=</em><strong>c²</strong></div></article></div><template #footer><el-button @click="previewVisible = false">继续编辑</el-button><el-button type="primary" :icon="VideoPlay" @click="previewVisible = false">播放预览</el-button></template></el-dialog>
  </div>
    <div v-if="runStatus === 'running'" class="run-progress"><span>{{ runStage || 'AI 正在生成课件' }}</span><el-progress :percentage="runProgress" :show-text="false" :stroke-width="4" /></div>
    <div v-if="projectId" class="project-utilities"><span>{{ autosaveState }}</span><el-button text size="small" @click="createVersion">保存版本</el-button><el-button text size="small" @click="loadVersions">版本历史</el-button><el-button text size="small" @click="permissionDialogVisible = true">协作授权</el-button></div>
    <el-dialog v-model="versionDialogVisible" title="项目版本历史" width="min(680px, 92vw)"><div v-loading="versionLoading" class="version-list"><article v-for="version in versions" :key="version.id || version.version_id"><div><strong>版本 {{ version.version_number || version.id }}</strong><p>{{ version.description || '未填写说明' }}</p></div><div><el-button text size="small" @click="showVersionDiff(version)">查看差异</el-button><el-button text size="small" type="primary" @click="restoreVersion(version)">恢复此版本</el-button></div></article><p v-if="versionDiff" class="version-diff">{{ versionDiff.summary || JSON.stringify(versionDiff.differences || versionDiff) }}</p><el-empty v-if="!versionLoading && !versions.length" description="暂无历史版本" /></div><template #footer><el-button @click="versionDialogVisible = false">关闭</el-button></template></el-dialog>
    <el-dialog v-model="permissionDialogVisible" title="添加协作者" width="420px"><p class="dialog-hint">协作者将获得项目编辑权限。</p><el-input v-model="permissionUserId" inputmode="numeric" placeholder="输入用户 ID" /><template #footer><el-button @click="permissionDialogVisible = false">取消</el-button><el-button type="primary" @click="grantPermission">确认授权</el-button></template></el-dialog>
</template>

<style scoped>
.workspace{height:100dvh;display:grid;grid-template-rows:60px minmax(0,1fr);overflow:hidden;background:var(--zh-background-light)}.toolbar{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 16px;border-bottom:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.project-title{display:flex;align-items:center;gap:8px}.project-title div{display:flex;flex-direction:column}.project-title strong{font-size:13px}.project-title span{display:flex;align-items:center;gap:4px;margin-top:3px;color:var(--zh-text-caption);font-size:10px}.project-title span .el-icon{color:var(--zh-green)}.editing-tools{display:flex;padding:3px;border-radius:var(--zh-radius8);background:var(--zh-background-light)}.toolbar-actions{justify-self:end;display:flex;gap:8px}.workspace-grid{min-height:0;display:grid;grid-template-columns:286px minmax(500px,1fr) 270px}.assistant-panel,.properties{min-height:0;background:var(--zh-background-primary)}.assistant-panel{display:flex;flex-direction:column;border-right:1px solid var(--zh-line-border)}.assistant-panel>header{display:flex;align-items:center;gap:9px;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.assistant-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:var(--zh-radius8);color:#fff;background:var(--zh-gradient-blue);font-weight:700}.assistant-panel header div:last-child{display:flex;flex-direction:column}.assistant-panel header strong{font-size:13px}.assistant-panel header span{margin-top:2px;color:var(--zh-text-caption);font-size:10px}.conversation{flex:1;padding:16px;overflow:auto}.message{display:flex;align-items:flex-start;gap:8px;margin-bottom:16px}.message>span{display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:6px;color:#fff;background:var(--zh-theme-primary);font-size:10px}.message p{margin:0;padding:10px 12px;border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-answer-card);font-size:12px;line-height:1.65}.message.user{justify-content:flex-end}.message.user p{color:var(--zh-text-primary);background:var(--zh-background-user-query)}.composer{padding:12px;border-top:1px solid var(--zh-line-border)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:8px}.composer span{color:var(--zh-text-caption);font-size:10px}.composer :deep(.el-textarea__inner){background:var(--zh-background-light);box-shadow:none}.editor-stage{display:grid;grid-template-columns:116px minmax(0,1fr);min-width:0}.slide-rail{padding:12px 9px;overflow:auto;border-right:1px solid var(--zh-line-border);background:var(--zh-background-primary)}.slide-rail>button{display:grid;grid-template-columns:18px 1fr;gap:4px;width:100%;margin-bottom:10px;padding:3px;border:1px solid transparent;border-radius:6px;color:var(--zh-text-caption);background:transparent;text-align:left;cursor:pointer}.slide-rail>button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.thumbnail{display:flex;flex-direction:column;justify-content:center;gap:5px;height:54px;padding:8px;border-radius:4px;background:var(--zh-background-light)}.thumbnail i{width:65%;height:3px;background:var(--thumb)}.thumbnail b{overflow:hidden;color:var(--zh-text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}.slide-rail :deep(.el-button){width:100%;justify-content:flex-start}.canvas-area{position:relative;display:grid;place-items:center;min-width:0;padding:44px 34px;overflow:auto;background-color:#eef0f4;background-image:radial-gradient(#c9ced7 1px,transparent 1px);background-size:18px 18px}.canvas-meta{position:absolute;top:12px;inset-inline:20px;display:flex;justify-content:space-between;color:#7c8491;font-size:10px}.slide-canvas{position:relative;width:min(780px,100%);aspect-ratio:16/9;overflow:hidden;padding:clamp(28px,4vw,52px);color:#102d54;background:#f9fbff;box-shadow:0 18px 45px rgb(40 57 82 / 18%)}.slide-canvas:after{content:'';position:absolute;top:-18%;right:-8%;width:42%;aspect-ratio:1;border-radius:50%;background:color-mix(in srgb,var(--accent) 16%,white)}.slide-eyebrow,.slide-canvas h1,.slide-canvas>p,.theorem{position:relative;z-index:1}.slide-eyebrow{color:var(--accent);font:600 10px var(--zh-font-number);letter-spacing:.12em}.slide-canvas h1{max-width:76%;margin:18px 0 0;font-size:clamp(26px,3vw,40px);line-height:1.2;letter-spacing:-.04em}.slide-canvas>p{max-width:64%;margin:12px 0;color:#607491;font-size:clamp(11px,1.2vw,15px);line-height:1.65}.theorem{display:grid;grid-template-columns:.8fr 1.2fr;align-items:center;gap:28px;width:76%;margin:28px auto}.triangle{position:relative;width:104px;height:104px;border-right:5px solid var(--accent);border-bottom:5px solid var(--accent);transform:skewY(-35deg) rotate(-10deg)}.triangle i{position:absolute;color:var(--accent);font-style:normal;font-weight:700;transform:skewY(35deg) rotate(10deg)}.triangle i:nth-child(1){bottom:-22px;left:36px}.triangle i:nth-child(2){top:40px;right:-18px}.triangle i:nth-child(3){top:-22px;left:8px}.formula{display:grid;grid-template-columns:auto 24px auto;align-items:center;font-family:var(--zh-font-number)}.formula span,.formula strong{font-size:clamp(22px,3vw,36px)}.formula em{color:#7c8da4;font-style:normal}.formula strong{color:var(--accent)}.formula small{grid-column:1/-1;margin-top:8px;color:#7c8da4;font-size:10px}.slide-canvas footer{position:absolute;z-index:1;right:0;bottom:0;left:0;display:grid;grid-template-columns:110px 1fr;padding:14px 28px;color:#fff;background:color-mix(in srgb,var(--accent) 82%,#102d54)}.slide-canvas footer p{margin:0;font-size:10px;line-height:1.5}.layout-重点陈述 h1{margin-top:54px;font-size:clamp(34px,4.4vw,52px)}.canvas-controls{position:absolute;right:18px;bottom:14px;display:flex;overflow:hidden;border-radius:var(--zh-radius8);background:var(--zh-background-capsule);box-shadow:var(--zh-shadow1)}.canvas-controls button,.canvas-controls span{padding:6px 9px;border:0;color:var(--zh-text-secondary);background:transparent;font-size:11px}.canvas-controls button{cursor:pointer}.properties{overflow:auto;border-left:1px solid var(--zh-line-border)}.properties>header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties header strong{font-size:13px}.properties header span{color:var(--zh-text-caption);font-size:10px}.tabs{display:grid;grid-template-columns:repeat(3,1fr);padding:10px 14px 0;border-bottom:1px solid var(--zh-line-parting)}.tabs button{padding:8px;border:0;border-bottom:2px solid transparent;color:var(--zh-text-caption);background:transparent;cursor:pointer}.tabs button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme)}.properties section{padding:16px;border-bottom:1px solid var(--zh-line-parting)}.properties label{display:block;margin:0 0 10px;color:var(--zh-text-secondary);font-size:11px;font-weight:600}.properties label:not(:first-child){margin-top:18px}.theme-picker{display:flex;gap:12px}.theme-picker button{width:24px;height:24px;border:2px solid var(--zh-background-primary);border-radius:50%;box-shadow:0 0 0 1px var(--zh-line-border);cursor:pointer}.theme-picker button.selected{outline:2px solid var(--zh-text-theme);outline-offset:2px}.layout-picker{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.layout-picker button{display:grid;grid-template-rows:26px auto;gap:4px;min-height:66px;padding:7px 4px;border:1px solid var(--zh-line-border);border-radius:6px;color:var(--zh-text-caption);background:var(--zh-background-light);font-size:9px;cursor:pointer}.layout-picker button.active{border-color:var(--zh-line-theme);color:var(--zh-text-theme);background:var(--zh-background-weaken)}.layout-picker i{display:block;width:70%;height:4px;margin:auto;background:var(--zh-line-theme50)}.layout-picker i:nth-child(2){width:48%}.page-actions{display:grid;gap:8px}.page-actions :deep(.el-button){justify-content:flex-start;margin:0}.assistant-tip{display:flex;gap:8px;margin:16px;padding:12px;border-radius:var(--zh-radius8);background:var(--zh-background-weaken)}.assistant-tip p,.hint{margin:0;color:var(--zh-text-secondary);font-size:10px;line-height:1.6}.preview{display:grid;place-items:center;padding:18px;background:#eef0f4}.preview-slide{width:min(780px,100%)}.preview-formula{width:max-content;margin:50px auto}.preview-dialog :deep(.el-dialog__body){padding:0}@media(max-width:1120px){.workspace-grid{grid-template-columns:250px minmax(460px,1fr)}.properties{display:none}}@media(max-width:820px){.toolbar{grid-template-columns:1fr auto}.editing-tools{display:none}.workspace-grid{grid-template-columns:1fr}.assistant-panel{display:none}.editor-stage{grid-template-columns:88px minmax(0,1fr)}}
.run-progress{position:fixed;z-index:100;right:24px;bottom:24px;width:min(320px,calc(100vw - 48px));padding:12px 14px;border:1px solid var(--zh-line-theme20);border-radius:var(--zh-radius12);color:var(--zh-text-secondary);background:var(--zh-background-pop);box-shadow:var(--zh-shadow2);font-size:12px}.run-progress :deep(.el-progress){margin-top:9px}
.project-utilities{position:fixed;z-index:100;right:24px;top:72px;display:flex;align-items:center;gap:4px;padding:5px 8px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius10);color:var(--zh-text-caption);background:var(--zh-background-pop);box-shadow:var(--zh-shadow1);font-size:11px}.project-utilities span{margin:0 4px}.version-list{display:grid;gap:10px}.version-list article{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px;border:1px solid var(--zh-line-border);border-radius:var(--zh-radius8);background:var(--zh-background-light)}.version-list strong{font-size:13px}.version-list p{margin:4px 0 0;color:var(--zh-text-caption);font-size:12px}.version-diff{margin:0;padding:12px;border-radius:var(--zh-radius8);color:var(--zh-text-secondary);background:var(--zh-background-weaken);font-size:12px;line-height:1.6;white-space:pre-wrap}.dialog-hint{margin:0 0 12px;color:var(--zh-text-secondary);font-size:13px}
.generic-visual{grid-column:1/-1;display:flex;align-items:center;justify-content:center;gap:14px;padding:24px;border:1px solid color-mix(in srgb,var(--accent) 24%,transparent);border-radius:var(--zh-radius12);background:color-mix(in srgb,var(--accent) 8%,white)}.generic-visual span{color:var(--accent);font-size:clamp(15px,2vw,22px);font-weight:600}.generic-visual em{color:#8a98aa;font-style:normal}

/* PPT 缩略图：阻止长标题撑开网格，并在固定画布内最多展示两行。 */
.slide-rail > button {
  grid-template-columns: 18px minmax(0, 1fr);
  min-width: 0;
  overflow: hidden;
}
.thumbnail {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
.thumbnail i {
  flex: none;
}
.thumbnail b {
  display: -webkit-box;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  line-height: 1.35;
  overflow-wrap: anywhere;
  white-space: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
