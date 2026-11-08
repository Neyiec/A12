<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Back, FullScreen, Close, Tickets } from '@element-plus/icons-vue'
import { getCommunityItem, getProject, listProjectPages, listProjectVersions } from '../apis/teacher'
import { unwrapWorkspaceResult } from '../utils/workspaceEntry'
import { readPresentationDraft } from '../utils/presentationDraft'
import { normalizePreviewPages, parsePresentationValue } from '../utils/mobilePresentation'
import PresentationSlidePreview from './PresentationSlidePreview.vue'
import LessonPlanPreview from './LessonPlanPreview.vue'

const route = useRoute()
const router = useRouter()
const title = ref('课件预览')
const projectSlides = ref([])
const projectPlan = ref(null)
const view = ref('ppt')
const activeIndex = ref(0)
const loading = ref(false)
const error = ref('')
const immersive = ref(false)
const exiting = ref(false)
const player = ref(null)
const playerHeight = ref(0)
const enterButton = ref(null)
const exitButton = ref(null)
const nativePlayer = window.Capacitor?.Plugins?.A12Presentation
const showNotes = ref(false)
const thumbnails = ref(null)
const historyVisible = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const historyPage = ref(1)
const historyTotal = ref(0)
const historyPageSize = 6
const versions = ref([])
const selectedVersion = ref(null)
const versionSnapshot = computed(() => parsePresentationValue(selectedVersion.value?.snapshot_data, null))
const slides = computed(() => selectedVersion.value ? normalizePreviewPages(versionSnapshot.value?.pages) : projectSlides.value)
const plan = computed(() => {
  if (!selectedVersion.value) return projectPlan.value
  const history = parsePresentationValue(versionSnapshot.value?.project?.edit_history)
  return history?.lesson_plan || history?.lessonPlan || null
})
const current = computed(() => slides.value[activeIndex.value])
const viewingSlides = computed(() => Boolean(current.value && (view.value === 'ppt' || !plan.value)))
let epoch = 0
let historyEpoch = 0
const back = () => router.push({ path: '/main/workspace', query: route.query.preview ? { preview: '1' } : {} })
const loadHistory = async (page = 1) => {
  const id = route.query.projectId
  if (!id) return
  const request = ++historyEpoch
  historyVisible.value = true
  historyLoading.value = true
  historyPage.value = page
  historyError.value = ''
  versions.value = []
  try {
    const result = unwrapWorkspaceResult(await listProjectVersions(String(id), { page, size: historyPageSize }))
    if (request !== historyEpoch) return
    versions.value = result?.records || []
    historyTotal.value = Number(result?.total || 0)
  } catch (failure) {
    if (request === historyEpoch) historyError.value = failure?.message || '版本历史加载失败'
  } finally {
    if (request === historyEpoch) historyLoading.value = false
  }
}
const showVersion = version => {
  selectedVersion.value = version
  activeIndex.value = 0
  showNotes.value = false
  immersive.value = false
  view.value = 'ppt'
  historyVisible.value = false
}
const load = async () => {
  const request = ++epoch
  loading.value = true
  error.value = ''
  projectSlides.value = []
  projectPlan.value = null
  selectedVersion.value = null
  immersive.value = false
  view.value = 'ppt'
  activeIndex.value = 0
  showNotes.value = false
  try {
    if (route.query.projectId) {
      // Read APIs only: mobile must never initialize an editor or autosave a project.
      const [projectResponse, pagesResponse] = await Promise.all([
        getProject(String(route.query.projectId)), listProjectPages(String(route.query.projectId)),
      ])
      if (request !== epoch) return
      const project = unwrapWorkspaceResult(projectResponse)
      title.value = project?.project_name || '课件预览'
      const history = parsePresentationValue(project?.edit_history) || {}
      projectPlan.value = history.lesson_plan || history.lessonPlan || null
      projectSlides.value = normalizePreviewPages(unwrapWorkspaceResult(pagesResponse))
    } else if (route.query.communityId) {
      const item = unwrapWorkspaceResult(await getCommunityItem(String(route.query.communityId)))
      if (request !== epoch) return
      const data = parsePresentationValue(item?.content_data) || {}
      title.value = item?.title || '课件预览'
      projectSlides.value = normalizePreviewPages(data.slides || data.pages || [])
      projectPlan.value = data.lesson_plan || data.lessonPlan || null
    } else {
      const draft = readPresentationDraft(String(route.query.sessionId || route.query.localDraftId || ''))
      title.value = draft?.title || draft?.metadata?.title || '课件预览'
      projectPlan.value = draft?.lesson_plan || null
      projectSlides.value = normalizePreviewPages(draft?.slides || [])
    }
  } catch (failure) {
    if (request === epoch) error.value = failure?.message || '课件加载失败，请重试'
  } finally { if (request === epoch) loading.value = false }
}
const select = index => {
  if (!viewingSlides.value) return
  activeIndex.value = Math.max(0, Math.min(slides.value.length - 1, index))
}
watch([activeIndex, immersive], () => {
  if (immersive.value) return
  const strip = thumbnails.value
  const active = strip?.querySelector('[aria-current="true"]')
  if (!active) return
  const row = strip.getBoundingClientRect()
  const tile = active.getBoundingClientRect()
  if (tile.left < row.left || tile.right > row.right) {
    strip.scrollBy({ left: tile.left - row.left + (tile.width - row.width) / 2, behavior: 'smooth' })
  }
}, { flush: 'post' })
let originalOverflow = ''
let previousScroll
let removeNativeBackListener
let disposed = false
const enterFullscreen = () => {
  if (!player.value || immersive.value || exiting.value) return
  playerHeight.value = player.value.offsetHeight
  previousScroll = { page: window.scrollY, body: document.body.scrollTop }
  immersive.value = true
}

const waitForPortrait = () => {
  const portrait = window.matchMedia('(orientation: portrait)')
  if (portrait.matches) return Promise.resolve()
  return new Promise(resolve => {
    const finish = () => {
      window.clearTimeout(timeout)
      portrait.removeEventListener('change', finish)
      resolve()
    }
    const timeout = window.setTimeout(finish, 900)
    portrait.addEventListener('change', finish)
  })
}

const exitFullscreen = async () => {
  if (!immersive.value || exiting.value) return
  exiting.value = true
  try {
    if (nativePlayer) {
      try { await nativePlayer.exit() } catch { /* The overlay can still be closed. */ }
      await waitForPortrait()
    }
    if (disposed || !immersive.value) return
    immersive.value = false
    await nextTick()
    if (!disposed) {
      document.body.scrollTo({ top: previousScroll.body, behavior: 'instant' })
      window.scrollTo({ top: previousScroll.page, behavior: 'instant' })
    }
  } finally {
    exiting.value = false
  }
}

onMounted(async () => {
  if (!nativePlayer) return
  try {
    const listener = await nativePlayer.addListener('exitRequested', exitFullscreen)
    if (disposed) await listener.remove()
    else removeNativeBackListener = () => listener.remove()
  } catch { /* The visible exit button remains available. */ }
})
watch(immersive, value => {
  if (value) {
    originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    void nativePlayer?.enter().catch(() => {})
  } else {
    document.body.style.overflow = originalOverflow
    if (!exiting.value) void nativePlayer?.exit().catch(() => {})
  }
}, { flush: 'sync' })
watch(immersive, value => {
  (value ? exitButton : enterButton).value?.focus({ preventScroll: true })
}, { flush: 'post' })
onBeforeUnmount(() => {
  epoch++
  historyEpoch++
  disposed = true
  immersive.value = false
  void removeNativeBackListener?.().catch(() => {})
})
let touchStart = null
const startTouch = event => { touchStart = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null }
const endTouch = event => {
  if (!touchStart || !event.changedTouches.length) return
  const dx = event.changedTouches[0].clientX - touchStart.x
  const dy = event.changedTouches[0].clientY - touchStart.y
  // When the host keeps its portrait viewport, the player itself is rotated.
  const rotated = immersive.value && window.matchMedia('(orientation: portrait)').matches
  const along = rotated ? dy : dx
  const across = rotated ? dx : dy
  if (Math.abs(along) > 45 && Math.abs(along) > Math.abs(across) * 1.5) {
    select(activeIndex.value + (along < 0 ? 1 : -1))
  }
  touchStart = null
}
watch(() => [route.query.projectId, route.query.sessionId, route.query.localDraftId, route.query.communityId], load, { immediate: true })
watch([() => route.query.projectId, () => route.query.history], ([id, show]) => {
  historyEpoch++
  historyVisible.value = false
  if (id && show === '1') void loadHistory()
}, { immediate: true })
</script>

<template>
  <main class="mobile-presentation" :inert="immersive || undefined">
    <header class="preview-header">
      <button class="preview-icon" aria-label="返回我的课件" @click="back"><el-icon><Back /></el-icon></button>
      <div><h1>{{ title }}</h1><span>只读预览</span></div>
    </header>
    <div v-if="!loading && !error && (route.query.projectId || (slides.length && plan))" class="preview-options">
      <el-radio-group v-if="slides.length && plan" v-model="view" aria-label="预览内容">
        <el-radio-button value="ppt">PPT</el-radio-button>
        <el-radio-button value="plan">教案</el-radio-button>
      </el-radio-group>
      <el-button v-if="selectedVersion" @click="showVersion(null)">返回当前版本</el-button>
      <el-button v-else-if="route.query.projectId" text :icon="Tickets" @click="loadHistory()">历史版本</el-button>
    </div>
    <p v-if="selectedVersion" class="version-label">正在预览 v{{ selectedVersion.version_number }}</p>
    <div v-if="loading" class="preview-state" role="status"><el-skeleton animated :rows="4" /><p>正在加载课件…</p></div>
    <div v-else-if="error" class="preview-state" role="alert"><h2>暂时无法打开课件</h2><p>{{ error }}</p><el-button type="primary" @click="load">重新加载</el-button></div>
    <template v-else-if="viewingSlides">
      <div :style="immersive ? { height: `${playerHeight}px` } : undefined">
        <Teleport to="body" :disabled="!immersive">
          <div
            ref="player"
            class="preview-player"
            :class="{ 'is-immersive': immersive }"
            @keydown.esc="exitFullscreen"
            @keydown.left.prevent="select(activeIndex - 1)"
            @keydown.right.prevent="select(activeIndex + 1)"
          >
            <section class="preview-stage" :aria-label="`第 ${activeIndex + 1} 页：${current.title}`" @touchstart.passive="startTouch" @touchend.passive="endTouch" @touchcancel="touchStart = null">
              <div class="preview-slide"><PresentationSlidePreview :slide="current" /></div>
              <button v-if="!immersive" ref="enterButton" type="button" class="preview-icon fullscreen-enter" aria-label="横屏全屏播放" @click="enterFullscreen">
                <el-icon><FullScreen /></el-icon>
              </button>
            </section>
            <div class="preview-controls">
              <button class="preview-icon" aria-label="上一页" :disabled="activeIndex === 0" @click="select(activeIndex - 1)"><el-icon><ArrowLeft /></el-icon></button>
              <span class="preview-counter" aria-live="polite"><strong>{{ activeIndex + 1 }}</strong> / {{ slides.length }}</span>
              <button class="preview-icon" aria-label="下一页" :disabled="activeIndex === slides.length - 1" @click="select(activeIndex + 1)"><el-icon><ArrowRight /></el-icon></button>
              <button v-if="immersive" ref="exitButton" type="button" class="preview-icon fullscreen-exit" aria-label="退出全屏" @click="exitFullscreen">
                <el-icon><Close /></el-icon>
              </button>
            </div>
          </div>
        </Teleport>
      </div>
      <nav ref="thumbnails" class="preview-thumbnails" aria-label="课件页面">
        <button v-for="(slide, index) in slides" :key="index" :aria-label="`第 ${index + 1} 页：${slide.title}`" :aria-current="activeIndex === index ? 'true' : undefined" @click="select(index)">
          <PresentationSlidePreview :slide="slide" decorative /><span>{{ index + 1 }}</span>
        </button>
      </nav>
      <section class="preview-detail">
        <div class="preview-detail-heading"><h2>{{ current.title }}</h2><button class="notes-button" :aria-expanded="showNotes" @click="showNotes = !showNotes"><el-icon><Tickets /></el-icon>备注</button></div>
        <p v-if="showNotes" class="preview-notes">{{ current.notes || '本页暂无备注' }}</p>
      </section>
    </template>
    <section v-else-if="plan" class="preview-document"><LessonPlanPreview :plan="plan" :title="title" embedded /></section>
    <div v-else class="preview-state"><el-icon class="empty-icon"><Tickets /></el-icon><h2>{{ selectedVersion ? '此版本暂无可预览内容' : '课件尚未生成' }}</h2><el-button type="primary" @click="selectedVersion ? showVersion(null) : back()">{{ selectedVersion ? '返回当前版本' : '返回我的课件' }}</el-button></div>
    <el-dialog v-model="historyVisible" title="历史版本" width="min(480px, 92vw)">
      <div v-loading="historyLoading" class="version-list">
        <template v-if="historyError">
          <el-alert :title="historyError" type="error" :closable="false" show-icon />
          <el-button @click="loadHistory(historyPage)">重新加载</el-button>
        </template>
        <button v-for="version in versions" :key="version.version_id" type="button" class="version-item" @click="showVersion(version)">
          <strong>v{{ version.version_number }} · {{ version.description || '课件快照' }}</strong>
          <small v-if="version.created_at">{{ String(version.created_at).replace('T', ' ').slice(0, 16) }}</small>
        </button>
        <el-empty v-if="!historyLoading && !historyError && !versions.length" description="暂无历史版本" :image-size="64" />
        <el-pagination v-if="!historyLoading && !historyError && historyTotal > historyPageSize" :current-page="historyPage" :total="historyTotal" :page-size="historyPageSize" layout="prev, pager, next" @current-change="loadHistory" />
      </div>
    </el-dialog>
  </main>
</template>

<style scoped>
.preview-options { display: flex; justify-content: space-between; gap: 8px; padding: 10px 16px; }
.preview-options .el-button { min-height: 44px; margin-left: auto; }
.preview-options :deep(.el-radio-button__inner) { min-height: 44px; display: flex; align-items: center; }
.version-label { padding: 0 16px; color: var(--zh-text-secondary); }
.version-list { display: grid; gap: 10px; min-height: 80px; }
.version-item {
  display: grid;
  gap: 6px;
  min-height: 56px;
  padding: 12px;
  border: 1px solid var(--zh-line-border);
  border-radius: 10px;
  background: var(--zh-background-primary);
  color: var(--zh-text-primary);
  text-align: left;
  font: inherit;
  font-size: 16px;
  overflow-wrap: anywhere;
}
.version-item small { color: var(--zh-text-secondary); }
.mobile-presentation{min-height:100dvh;background:#f4f6fa;color:#172b4d;padding-bottom:calc(24px + var(--zh-safe-bottom));--preview-control-bg:#fff}
.preview-header{display:flex;align-items:center;gap:10px;padding:calc(10px + var(--zh-safe-top)) 12px 12px;background:#fff;border-bottom:1px solid #e4e9f1}
.preview-header>div{flex:1;min-width:0}.preview-header h1{margin:0;font-size:18px;font-weight:650;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.preview-header span{font-size:13px;color:#64748b}
.preview-icon{display:inline-grid;flex:none;width:48px;height:48px;place-items:center;border:0;border-radius:12px;background:var(--preview-control-bg);color:inherit;font-size:25px;cursor:pointer}.preview-icon:disabled{opacity:.3}.preview-icon:active:not(:disabled){background:#dbeafe}
.preview-stage{position:relative;display:flex;align-items:center;justify-content:center;min-height:36dvh;padding:24px 12px;background:#e8edf4;touch-action:pan-y}
.preview-stage .fullscreen-enter {
  position: absolute;
  inset: auto 16px 12px auto;
  background: rgb(15 23 42 / 85%);
  color: #fff;
}
.preview-stage .fullscreen-enter:active { background: #0f172a; }
.preview-slide{width:100%;max-width:1200px;border-radius:6px;box-shadow:0 8px 28px #142b4d18}
.preview-controls{display:flex;align-items:center;justify-content:center;gap:36px;padding:12px}.preview-counter{min-width:68px;text-align:center;color:#64748b;font-size:16px;font-variant-numeric:tabular-nums}.preview-counter strong{color:#172b4d;font-size:22px;font-weight:650}
.preview-thumbnails{display:flex;gap:12px;overflow-x:auto;padding:4px 16px 16px;scrollbar-width:none}.preview-thumbnails button{position:relative;flex:0 0 112px;min-width:112px;padding:3px 3px 24px;border:2px solid transparent;border-radius:8px;background:#fff;color:#64748b;font:inherit;font-size:13px}.preview-thumbnails button[aria-current="true"]{border-color:#2563eb;color:#1d4ed8;background:#eff6ff}.preview-thumbnails button>span{position:absolute;bottom:2px;left:0;width:100%;text-align:center}
.preview-detail{padding:16px 20px;border-top:1px solid #e4e9f1}.preview-detail-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.preview-detail h2{margin:0;font-size:18px;line-height:1.5;overflow-wrap:anywhere}.notes-button{display:flex;align-items:center;gap:6px;flex:none;min-height:44px;padding:0 12px;border:0;border-radius:10px;background:#e8effc;color:#1d4ed8;font:inherit;font-size:15px}.notes-button .el-icon{font-size:20px}.preview-notes{white-space:pre-wrap;font-size:16px;line-height:1.8;color:#40536c}
.preview-state{padding:56px 24px;text-align:center}.preview-state h2{font-size:22px}.preview-state p{font-size:16px;line-height:1.7;color:#64748b}.empty-icon{font-size:52px;color:#8ba9d5}.preview-document{padding:16px}
.is-immersive {
  position: fixed;
  inset: 0;
  z-index: 250;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100dvh;
  padding: var(--zh-safe-top) var(--zh-safe-right) var(--zh-safe-bottom) var(--zh-safe-left);
  overflow: hidden;
  background: #090e19;
  color: #fff;
  --preview-control-bg: #202a3a;
}
.is-immersive .preview-stage {
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: transparent;
  container-type: size;
  touch-action: none;
}
.is-immersive .preview-slide {
  width: min(100%, calc(100cqh * 16 / 9));
  max-width: none;
  border-radius: 0;
  box-shadow: none;
}
.is-immersive .preview-controls { position: relative; flex: none; gap: 20px; padding: 0 8px 4px; }
.is-immersive .preview-counter, .is-immersive .preview-counter strong { color: #fff; }
.is-immersive .preview-icon:active:not(:disabled) { background: #34445b; }
.is-immersive .fullscreen-exit { position: absolute; right: 8px; bottom: 4px; }
@media (orientation: portrait) {
  .is-immersive {
    inset: 50% auto auto 50%;
    width: 100dvh;
    height: 100dvw;
    padding: var(--zh-safe-right) var(--zh-safe-bottom) var(--zh-safe-left) var(--zh-safe-top);
    transform: translate(-50%, -50%) rotate(90deg);
  }
}
:global([data-theme="dark"]) .mobile-presentation {
  background: var(--zh-background-light);
  color: var(--zh-text-primary);
  --preview-control-bg: var(--zh-background-primary);
}
:global([data-theme="dark"]) .preview-header,
:global([data-theme="dark"]) .preview-thumbnails button {
  background: var(--zh-background-primary);
  border-color: var(--zh-line-border);
}
:global([data-theme="dark"]) .mobile-presentation .preview-stage,
:global([data-theme="dark"]) .notes-button {
  background: var(--zh-background-option);
}
:global([data-theme="dark"]) .mobile-presentation .preview-counter strong,
:global([data-theme="dark"]) .preview-thumbnails button[aria-current="true"],
:global([data-theme="dark"]) .notes-button {
  color: var(--zh-text-primary);
}
:global([data-theme="dark"]) .preview-header span,
:global([data-theme="dark"]) .mobile-presentation .preview-counter,
:global([data-theme="dark"]) .preview-notes,
:global([data-theme="dark"]) .preview-state p {
  color: var(--zh-text-secondary);
}
@media (orientation: landscape) and (max-height: 600px) {
  .preview-stage { min-height: 0; }
}
</style>
