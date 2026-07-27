<!--
  [数据交互说明]
  - 导入: 工作台演示数据、Element Plus 组件
  - 输出: 对话驱动的课件创作工作台
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Brush, ChatDotRound, CircleCheck, CopyDocument, DataBoard,
  Delete, Download, EditPen, Picture, Plus, Promotion, Refresh,
} from '@element-plus/icons-vue'
import { WORKSPACE_PAGE } from '../config/teacherPages.config.js'
import { getProject, reviseProject, sendAiMessage } from '../apis/teacher'

const router = useRouter()
const route = useRoute()
const selectedSlide = ref(2)
const prompt = ref('')
const activePanel = ref('样式')
const panels = ['样式', '布局', '动画']
const slideTitle = computed(() => WORKSPACE_PAGE.slides[selectedSlide.value])
const project = ref(null)
const messages = ref([...WORKSPACE_PAGE.messages])
const projectId = computed(() => route.query.projectId)
const projectName = computed(() => project.value?.project_name || '教学创作项目')

const loadProject = async () => {
  if (!projectId.value) return
  try {
    const result = await getProject(projectId.value)
    project.value = result?.data || result
  } catch { ElMessage.error('项目加载失败，请稍后重试') }
}

/** 模拟自然语言修改当前课件页。 */
const sendRevision = async () => {
  if (!prompt.value.trim()) return
  if (!projectId.value) return ElMessage.warning('请先从首页创建或打开一个项目')
  const instruction = prompt.value.trim()
  try {
    messages.value.push({ role: 'user', text: instruction })
    await reviseProject(projectId.value, { target_type: 'page', target_id: String(selectedSlide.value + 1), instruction, context: JSON.stringify({ page_title: slideTitle.value }) })
    if (route.query.sessionId) await sendAiMessage(route.query.sessionId, { messages: JSON.stringify([{ role: 'user', text: instruction }]) })
    messages.value.push({ role: 'assistant', text: `已提交对“${slideTitle.value}”的修改请求。` })
    ElMessage.success('修改请求已提交')
    prompt.value = ''
  } catch {
    messages.value.pop()
    ElMessage.error('修改未能保存，请稍后重试')
  }
}
onMounted(loadProject)
</script>

<template>
  <div class="workspace">
    <header class="workspace-toolbar">
      <div class="workspace-title"><el-button text circle aria-label="返回首页" @click="router.push({ path: '/main', query: route.query.preview ? { preview: '1' } : {} })"><el-icon><ArrowLeft /></el-icon></el-button><div><strong>{{ projectName }}</strong><span><el-icon><CircleCheck /></el-icon> {{ project ? `已保存 · v${project.current_version || 1}` : '正在加载项目' }}</span></div></div>
      <div class="tool-cluster" title="组件编辑能力将在项目接口接入后开放"><el-button text :icon="EditPen" disabled>文本</el-button><el-button text :icon="Picture" disabled>图片</el-button><el-button text :icon="DataBoard" disabled>互动组件</el-button><el-button text :icon="Brush" disabled>背景</el-button></div>
      <div><el-button :icon="Refresh" disabled title="项目预览暂未接入">预览</el-button><el-button type="primary" :icon="Download" :disabled="!projectId" @click="router.push({ path: '/main/exports', query: { ...(route.query.preview ? { preview: '1' } : {}), projectId } })">导出</el-button></div>
    </header>

    <div class="workspace-grid">
      <aside class="ai-panel">
        <header><div class="ai-mark">智</div><div><strong>AI 教学助手</strong><span>正在编辑第 {{ selectedSlide + 1 }} 页</span></div></header>
        <section class="messages">
          <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
            <span v-if="message.role === 'assistant'">智</span><p>{{ message.text }}</p>
          </article>
        </section>
        <footer class="ai-composer"><el-input v-model="prompt" type="textarea" :rows="3" resize="none" placeholder="描述你想修改的内容……" @keydown.ctrl.enter="sendRevision" /><div><span>选中：{{ slideTitle }}</span><el-button type="primary" circle :icon="Promotion" :disabled="!prompt.trim()" @click="sendRevision" /></div></footer>
      </aside>

      <section class="editor-stage">
        <aside class="slide-list">
          <button v-for="(slide, index) in WORKSPACE_PAGE.slides" :key="slide" :class="{ active: selectedSlide === index }" @click="selectedSlide = index">
            <span>{{ index + 1 }}</span><div class="mini-slide"><i></i><b>{{ slide }}</b></div>
          </button>
          <el-button text :icon="Plus" disabled title="页面编辑暂未接入">添加页面</el-button>
        </aside>

        <main class="canvas-area">
          <div class="canvas-meta"><span>{{ selectedSlide + 1 }} / {{ WORKSPACE_PAGE.slides.length }}</span><span>16:9 · 适应窗口</span></div>
          <article class="slide-canvas">
            <span class="slide-label">03 / 观察与猜想</span>
            <h1>直角三角形的三边，<br>藏着怎样的关系？</h1>
            <div class="theorem-visual">
              <div class="triangle"></div>
              <div class="formula"><span>a² + b²</span><i>=</i><strong>c²</strong><small>拖动顶点，观察面积变化</small></div>
            </div>
            <footer><span>小组任务</span><p>测量三组直角三角形边长，记录并比较两个较小正方形与最大正方形的面积。</p></footer>
          </article>
          <div class="zoom-control" title="缩放暂未接入"><button disabled>−</button><span>86%</span><button disabled>＋</button></div>
        </main>
      </section>

      <aside class="property-panel">
        <header><strong>属性设置</strong><span>页面 03</span></header>
        <div class="panel-tabs"><button v-for="panel in panels" :key="panel" :class="{ active: activePanel === panel }" @click="activePanel = panel">{{ panel }}</button></div>
        <section><label>页面布局</label><div class="layout-options"><button class="active" disabled><i></i><i></i></button><button disabled><i></i><i></i></button><button disabled><i></i></button></div></section>
        <section><label>主题色</label><div class="color-row"><button class="blue" disabled></button><button class="navy" disabled></button><button class="green" disabled></button><button class="orange" disabled></button><button class="custom" disabled>+</button></div></section>
        <section><label>背景</label><el-select model-value="浅色网格" disabled><el-option label="浅色网格" value="浅色网格" /></el-select><el-slider :model-value="18" disabled /></section>
        <section><label>页面操作</label><div class="action-list"><el-button :icon="CopyDocument" disabled>复制页面</el-button><el-button :icon="Delete" disabled>删除页面</el-button></div></section>
        <div class="property-tip"><el-icon><ChatDotRound /></el-icon><p>你也可以在左侧直接说：<br>“把背景换成更简洁的浅蓝色”</p></div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.workspace { height: 100dvh; display: grid; grid-template-rows: 58px minmax(0, 1fr); overflow: hidden; background: var(--zh-background-light); }
.workspace-toolbar { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; padding: 0 16px; border-bottom: 1px solid var(--zh-line-border); background: var(--zh-background-primary); }.workspace-toolbar > :last-child { justify-self: end; }
.workspace-title { display: flex; align-items: center; gap: 8px; }.workspace-title > div { display: flex; flex-direction: column; }.workspace-title strong { font-size: 13px; }.workspace-title span { display: flex; align-items: center; gap: 3px; margin-top: 2px; color: var(--zh-text-caption); font-size: 10px; }.workspace-title span .el-icon { color: var(--zh-green); }
.tool-cluster { display: flex; padding: 3px; border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.workspace-grid { min-height: 0; display: grid; grid-template-columns: 286px minmax(480px, 1fr) 250px; }
.ai-panel, .property-panel { min-height: 0; background: var(--zh-background-primary); }.ai-panel { display: flex; flex-direction: column; border-right: 1px solid var(--zh-line-border); }.ai-panel > header { display: flex; align-items: center; gap: 9px; padding: 16px; border-bottom: 1px solid var(--zh-line-parting); }.ai-mark { width: 32px; height: 32px; display: grid; place-items: center; border-radius: var(--zh-radius8); color: white; background: var(--zh-gradient-blue); font-weight: 700; }.ai-panel header > div:last-child { display: flex; flex-direction: column; }.ai-panel header strong { font-size: 13px; }.ai-panel header span { color: var(--zh-text-caption); font-size: 10px; }
.messages { flex: 1; padding: 16px; overflow-y: auto; }.message { display: flex; align-items: start; gap: 7px; margin-bottom: 18px; }.message > span { flex: none; width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px; color: white; background: var(--zh-theme-primary); font-size: 10px; }.message p { margin: 0; padding: 10px 12px; border-radius: var(--zh-radius8); background: var(--zh-background-answer-card); box-shadow: 0 1px 0 var(--zh-line-border); color: var(--zh-text-secondary); font-size: 12px; line-height: 1.65; }.message.user { justify-content: flex-end; }.message.user p { background: var(--zh-background-user-query); color: var(--zh-text-primary); }
.ai-composer { padding: 12px; border-top: 1px solid var(--zh-line-border); }.ai-composer :deep(.el-textarea__inner) { box-shadow: none; background: var(--zh-background-light); }.ai-composer > div { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }.ai-composer span { color: var(--zh-text-caption); font-size: 10px; }
.editor-stage { min-width: 0; display: grid; grid-template-columns: 116px minmax(0, 1fr); }.slide-list { padding: 12px 9px; border-right: 1px solid var(--zh-line-border); overflow-y: auto; background: var(--zh-background-primary); }.slide-list > button { width: 100%; display: grid; grid-template-columns: 16px 1fr; gap: 4px; margin-bottom: 10px; padding: 3px; border: 1px solid transparent; border-radius: 6px; color: var(--zh-text-caption); background: transparent; cursor: pointer; }.slide-list > button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); }.mini-slide { height: 54px; display: flex; flex-direction: column; justify-content: center; gap: 5px; padding: 8px; border-radius: 4px; background: var(--zh-background-light); }.mini-slide i { width: 65%; height: 3px; background: var(--zh-line-theme50); }.mini-slide b { overflow: hidden; color: var(--zh-text-secondary); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.canvas-area { min-width: 0; position: relative; display: grid; place-items: center; padding: 44px 34px; overflow: auto; background-color: #eef0f4; background-image: radial-gradient(#c9ced7 1px, transparent 1px); background-size: 18px 18px; }.canvas-meta { position: absolute; top: 12px; inset-inline: 20px; display: flex; justify-content: space-between; color: #7c8491; font-size: 10px; }
.slide-canvas { width: min(780px, 100%); aspect-ratio: 16 / 9; position: relative; overflow: hidden; padding: clamp(28px, 4vw, 52px); color: #102d54; background: #f9fbff; box-shadow: 0 18px 45px rgb(40 57 82 / 18%); }.slide-canvas::after { content: ""; position: absolute; right: -8%; top: -18%; width: 42%; aspect-ratio: 1; border-radius: 50%; background: #dbeafe; opacity: .7; }.slide-label { color: #3772ba; font: 600 10px var(--zh-font-number); letter-spacing: .12em; }.slide-canvas h1 { max-width: 72%; margin: 18px 0 0; font-size: clamp(22px, 3vw, 38px); line-height: 1.28; letter-spacing: -.04em; }
.theorem-visual { display: grid; grid-template-columns: .8fr 1.2fr; align-items: center; gap: 32px; width: 76%; margin: 34px auto 0; }.triangle { width: 0; height: 0; border-left: 80px solid #4a83c8; border-top: 55px solid transparent; border-bottom: 55px solid transparent; transform: rotate(45deg); filter: drop-shadow(8px 10px 0 #bfdbfe); }.formula { display: grid; grid-template-columns: auto 24px auto; align-items: center; font-family: var(--zh-font-number); }.formula span, .formula strong { font-size: clamp(22px, 3vw, 36px); }.formula i { color: #7c8da4; font-style: normal; }.formula strong { color: #2563eb; }.formula small { grid-column: 1 / -1; margin-top: 8px; color: #7c8da4; font-size: 10px; }
.slide-canvas footer { position: absolute; inset-inline: 0; bottom: 0; display: grid; grid-template-columns: 110px 1fr; padding: 14px 28px; color: white; background: #173d78; }.slide-canvas footer span { font-weight: 600; }.slide-canvas footer p { margin: 0; font-size: 10px; line-height: 1.5; }
.zoom-control { position: absolute; right: 18px; bottom: 14px; display: flex; align-items: center; overflow: hidden; border-radius: var(--zh-radius8); background: var(--zh-background-capsule); box-shadow: var(--zh-shadow1); }.zoom-control button, .zoom-control span { padding: 6px 9px; border: 0; color: var(--zh-text-secondary); background: var(--zh-background-capsule); font-size: 10px; }
.property-panel { border-left: 1px solid var(--zh-line-border); overflow-y: auto; }.property-panel > header { display: flex; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--zh-line-parting); }.property-panel header strong { font-size: 13px; }.property-panel header span { color: var(--zh-text-caption); font-size: 10px; }
.panel-tabs { display: grid; grid-template-columns: repeat(3, 1fr); padding: 10px 14px 0; border-bottom: 1px solid var(--zh-line-parting); }.panel-tabs button { padding: 8px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; cursor: pointer; }.panel-tabs button.active { color: var(--zh-text-theme); border-color: var(--zh-line-theme); }
.property-panel section { padding: 15px; border-bottom: 1px solid var(--zh-line-parting); }.property-panel label { display: block; margin-bottom: 10px; color: var(--zh-text-secondary); font-size: 11px; font-weight: 600; }.layout-options, .color-row, .action-list { display: flex; gap: 8px; }.layout-options button { width: 54px; height: 36px; display: grid; grid-template-columns: 1fr 1fr; gap: 3px; padding: 6px; border: 1px solid var(--zh-line-border); border-radius: 5px; background: var(--zh-background-light); }.layout-options button.active { border-color: var(--zh-line-theme); }.layout-options i { background: var(--zh-line-theme20); }.color-row button { width: 24px; height: 24px; border: 2px solid var(--zh-background-primary); border-radius: 50%; box-shadow: 0 0 0 1px var(--zh-line-border); }.blue { background: #2563eb; }.navy { background: #173d78; }.green { background: #1f993f; }.orange { background: #ff6b3f; }.custom { color: var(--zh-text-caption); background: var(--zh-background-light); }.property-panel :deep(.el-select) { width: 100%; }.action-list { flex-direction: column; }.action-list :deep(.el-button) { margin: 0; justify-content: start; }
.property-tip { display: flex; gap: 8px; margin: 16px; padding: 12px; border-radius: var(--zh-radius8); color: var(--zh-text-theme); background: var(--zh-background-weaken); }.property-tip p { margin: 0; color: var(--zh-text-secondary); font-size: 10px; line-height: 1.6; }
@media (max-width: 1120px) { .workspace-grid { grid-template-columns: 250px minmax(460px, 1fr); }.property-panel { display: none; } }
@media (max-width: 820px) { .workspace-toolbar { grid-template-columns: 1fr auto; }.tool-cluster { display: none; }.workspace-grid { grid-template-columns: 1fr; }.ai-panel { display: none; }.editor-stage { grid-template-columns: 88px minmax(0, 1fr); } }
</style>
