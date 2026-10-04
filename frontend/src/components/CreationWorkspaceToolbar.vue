<script setup>
import { computed, ref } from 'vue'
import { Aim, ArrowDown, ArrowLeft, Check, ChatDotRound, CircleCheck, DataAnalysis, DataBoard, Download, EditPen, FolderOpened, Grid, Headset, Histogram, MagicStick, Picture, SetUp, Share, VideoCamera, View } from '@element-plus/icons-vue'
import WorkspaceToolButton from './WorkspaceToolButton.vue'
import { subjectToolMenuGroups } from '../utils/subjectTool'

const props = defineProps({
  title: { type: String, default: '未命名课件' },
  autosaveState: { type: String, default: '已保存' },
  projectId: { type: [String, Number], default: '' },
  workspaceMode: { type: String, default: 'ppt' },
  mobileView: { type: String, default: 'chat' },
  isLocalDraft: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  onlinePreviewLoading: { type: Boolean, default: false },
  quickExportLoading: { type: String, default: '' },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits([
  'save',
  'update:modelValue',
  'tool-select',
  'back',
  'export',
  'export-quick',
  'publish-community',

  'online-preview',
  'generate-h5',
  'lesson-plan',
  'return-ppt',
  'project-manage',
  'save-as-project',
  'toggle-assistant',
  'toggle-properties',
  'versions',
  'permissions',
])

const tools = [
  { id: 'text', label: '文本', icon: EditPen },
  { id: 'image', label: '图片', icon: Picture },
  { id: 'shape', label: '形状', icon: Grid },
  { id: 'chart', label: '图表', icon: Histogram },
  { id: 'audio', label: '音频', icon: Headset },
  { id: 'video', label: '视频', icon: VideoCamera },
  { id: 'table', label: '表格', icon: DataAnalysis },
  { id: 'h5', label: 'H5 组件', icon: MagicStick },
  { id: 'subject', label: '学科组件', icon: Aim || SetUp },
]
const shapeOptions = [
  { shapeKind: 'rectangle', label: '矩形' },
  { shapeKind: 'rounded', label: '圆角矩形' },
  { shapeKind: 'circle', label: '圆形' },
  { shapeKind: 'diamond', label: '菱形' },
  { shapeKind: 'triangle', label: '三角形' },
]
const selectedShapeKind = ref('rectangle')
const shapeMenuOpen = ref(false)
const selectedSubjectType = ref('geometry')
const subjectMenuOpen = ref(false)
const compactToolsOpen = ref(false)
const selectedShape = computed(() => shapeOptions.find((item) => item.shapeKind === selectedShapeKind.value) || shapeOptions[0])
const subjectMarks = {
  math_formula: 'ƒx',
  chinese_tianzige: '田',
  english_four_line: 'Aa',
  chemical_formula: 'CH',
  mermaid_diagram: '→',
  geometry: '△',
  coordinate_system: '⊞',
  solid_geometry: '⬡',
}
const subjectGroups = subjectToolMenuGroups.map((group) => ({
  ...group,
  options: group.options.map((item) => ({ ...item, mark: subjectMarks[item.value] || '·' })),
}))
const subjects = subjectGroups.flatMap((group) => group.options)
const workspaceModes = [
  { value: 'ppt', label: 'PPT 课件' },
  { value: 'document', label: '教学案' },
]
const workspaceModeLabel = computed(() => workspaceModes.find((item) => item.value === props.workspaceMode)?.label || 'PPT 课件')
const projectLabel = computed(() => props.projectId || '本地草稿')
const compactAutosaveState = computed(() => props.autosaveState.split(' · ')[0])
const selectTool = (tool) => {
  if (tool.id === 'h5') {
    emit('update:modelValue', '')
    emit('generate-h5')
    return
  }
  if (tool.id === 'chart' || tool.id === 'table') {
    emit('update:modelValue', tool.id)
    emit('tool-select', { ...tools.find((item) => item.id === 'subject'), label: tool.label, subjectType: tool.id })
    return
  }
  emit('update:modelValue', tool.id)
  emit('tool-select', tool)
}
const selectShape = (shapeKind) => {
  const shape = shapeOptions.find((item) => item.shapeKind === shapeKind)
  if (shape) {
    selectedShapeKind.value = shapeKind
    selectTool({ ...tools.find((item) => item.id === 'shape'), ...shape })
  }
}
const selectSubject = (subjectType) => {
  const subject = subjects.find((item) => item.value === subjectType)
  if (!subject) return
  selectedSubjectType.value = subjectType
  selectTool({ ...tools.find((item) => item.id === 'subject'), ...subject, subjectType })
}

const goBack = () => emit('back')
const openOnlinePreview = () => emit('online-preview')
const exportProject = () => emit('export')
const handleExportCommand = (command) => emit('export-quick', command)
const publishCommunity = () => emit('publish-community')
const openLessonPlan = () => emit('lesson-plan')
const returnToPpt = () => emit('return-ppt')
const manageProject = () => emit('project-manage')
const saveAsProject = () => emit('save-as-project')
const toggleCompactTools = () => { compactToolsOpen.value = !compactToolsOpen.value }
</script>

<template>
  <header class="toolbar">
    <div class="project-title">
      <el-button text circle aria-label="返回教学助手" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <div>
        <strong>{{ title }}<small class="toolbar-mode-suffix"> · {{ workspaceModeLabel }}</small></strong>
        <span>
          <el-icon v-if="!autosaveState.includes('失败') && !autosaveState.includes('待保存') && !saving"><CircleCheck /></el-icon>
          <b class="toolbar-status-full">{{ autosaveState }}</b><b class="toolbar-status-short">{{ compactAutosaveState }}</b><small class="toolbar-project-suffix"> · {{ isLocalDraft ? '未保存为项目' : `项目 ${projectLabel}` }}</small>
        </span>
      </div>
    </div>

    <div class="editing-tool-area" :class="{ 'is-mobile-open': compactToolsOpen }">
      <nav class="editing-tools" aria-label="页面编辑工具">
        <template v-for="tool in tools" :key="tool.id">
          <el-dropdown v-if="tool.id === 'shape'" trigger="click" @command="selectShape" @visible-change="shapeMenuOpen = $event">
            <WorkspaceToolButton
              :icon="tool.icon"
              :label="selectedShape.label"
              :active="modelValue === tool.id"
              :trailing-icon="ArrowDown"
              aria-haspopup="menu"
              :aria-expanded="shapeMenuOpen"
            />
            <template #dropdown>
              <el-dropdown-menu class="shape-picker-menu">
                <el-dropdown-item
                  v-for="shape in shapeOptions"
                  :key="shape.shapeKind"
                  :command="shape.shapeKind"
                  :class="{ 'is-shape-selected': selectedShapeKind === shape.shapeKind }"
                  :aria-current="selectedShapeKind === shape.shapeKind ? 'true' : undefined"
                >
                  <span class="shape-picker-option">
                    <svg v-if="shape.shapeKind === 'triangle'" class="shape-picker-preview shape-picker-triangle" viewBox="0 0 22 16" aria-hidden="true">
                      <polygon points="11,1 21,15 1,15" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
                    </svg>
                    <i v-else :class="['shape-picker-preview', `shape-picker-${shape.shapeKind}`]"></i>
                    <span>{{ shape.label }}</span>
                    <el-icon class="shape-picker-check"><Check v-if="selectedShapeKind === shape.shapeKind" /></el-icon>
                  </span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown v-else-if="tool.id === 'subject'" trigger="click" @command="selectSubject" @visible-change="subjectMenuOpen = $event">
            <WorkspaceToolButton
              :icon="tool.icon"
              :label="tool.label"
              :active="modelValue === tool.id"
              :trailing-icon="ArrowDown"
              aria-haspopup="menu"
              :aria-expanded="subjectMenuOpen"
            />
            <template #dropdown>
              <el-dropdown-menu class="subject-picker-menu">
                <template v-for="group in subjectGroups" :key="group.label">
                  <li class="subject-picker-group-heading" role="presentation">{{ group.label }}</li>
                  <el-dropdown-item
                    v-for="subject in group.options"
                    :key="subject.value"
                    :command="subject.value"
                    :class="{ 'is-subject-selected': selectedSubjectType === subject.value }"
                    :aria-current="selectedSubjectType === subject.value ? 'true' : undefined"
                  >
                    <span class="subject-picker-option">
                      <i aria-hidden="true">{{ subject.mark }}</i>
                      <span>{{ subject.label }}</span>
                    </span>
                  </el-dropdown-item>
                </template>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <WorkspaceToolButton v-else :icon="tool.icon" :label="tool.label" :active="modelValue === tool.id" @click="selectTool(tool)" />
        </template>
    </nav>
    </div>

    <div class="toolbar-actions">
      <el-button v-if="!isLocalDraft && autosaveState.includes('失败')" class="toolbar-priority mobile-save-retry" :loading="saving" type="danger" plain @click="emit('save')">重试</el-button>
      <el-button class="mobile-preview-action" type="primary" plain :icon="View" :loading="onlinePreviewLoading" :aria-label="mobileView === 'plan' ? '预览教案' : '预览课件'" @click="openOnlinePreview">预览</el-button>
      <el-button v-if="isLocalDraft" class="toolbar-priority" type="primary" plain @click="saveAsProject">保存为项目</el-button>
      <el-button class="toolbar-priority" :icon="FolderOpened" @click="manageProject">项目</el-button>
      <el-button class="toolbar-priority" :icon="Share" @click="publishCommunity">发布社区</el-button>
      <el-button v-if="workspaceMode === 'document'" class="toolbar-priority workspace-content-mode-button" :icon="DataBoard" aria-label="返回 PPT 课件" @click="returnToPpt">PPT</el-button>
      <el-button v-else class="toolbar-priority workspace-content-mode-button" :icon="SetUp" @click="openLessonPlan">教案</el-button>
      <el-button class="toolbar-priority" :icon="View" :loading="onlinePreviewLoading" @click="openOnlinePreview">在线预览</el-button>
      <el-dropdown class="toolbar-priority" trigger="click" :disabled="Boolean(quickExportLoading)" @command="handleExportCommand">
        <el-button type="primary" :icon="Download" :loading="Boolean(quickExportLoading)">导出<el-icon v-if="!quickExportLoading" class="toolbar-dropdown-arrow"><ArrowDown /></el-icon></el-button>
        <template #dropdown>
          <el-dropdown-menu>
                  <el-dropdown-item command="quick-pptx">快速下载 PPTX（学科组件为静态）</el-dropdown-item>
            <el-dropdown-item command="quick-word">快速下载 DOCX</el-dropdown-item>
            <el-dropdown-item command="precheck">导出预检</el-dropdown-item>
            <el-dropdown-item divided command="advanced">前往导出中心高级导出</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button class="mobile-panel-trigger" :icon="ChatDotRound" aria-label="打开 AI 助手" @click="emit('toggle-assistant')">AI</el-button>
      <el-button class="mobile-panel-trigger" :icon="SetUp" aria-label="打开属性面板" @click="emit('toggle-properties')">属性</el-button>
      <el-button class="mobile-panel-trigger" :icon="Grid" aria-label="打开编辑工具" @click="toggleCompactTools">工具</el-button>
      <el-dropdown class="workspace-more" trigger="click">
        <el-button aria-label="更多工作台操作">更多<el-icon><ArrowDown /></el-icon></el-button>
        <template #dropdown><el-dropdown-menu>
          <el-dropdown-item class="workspace-mobile-action" v-if="isLocalDraft" :disabled="saving" @click="saveAsProject">保存为项目</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" v-else-if="autosaveState.includes('失败')" :disabled="saving" @click="emit('save')">重试保存</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" @click="manageProject">项目管理</el-dropdown-item>


          <el-dropdown-item class="workspace-mobile-action" @click="workspaceMode === 'document' ? returnToPpt() : openLessonPlan()">{{ workspaceMode === 'document' ? '返回 PPT' : '打开教案' }}</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" @click="openOnlinePreview">在线预览</el-dropdown-item>
            <el-dropdown-item class="workspace-mobile-action" :disabled="Boolean(quickExportLoading)" @click="handleExportCommand('quick-pptx')">下载 PPTX（学科组件为静态）</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" :disabled="Boolean(quickExportLoading)" @click="handleExportCommand('quick-word')">下载 DOCX</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" @click="exportProject">导出中心</el-dropdown-item>
          <el-dropdown-item class="workspace-mobile-action" divided @click="publishCommunity">发布社区</el-dropdown-item>
        </el-dropdown-menu></template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-rows: 48px 52px;
  align-items: center;
  column-gap: 16px;
  row-gap: 0;
  min-width: 0;
  padding: 0 16px;
  border-bottom: 1px solid var(--zh-line-border);
  background: var(--zh-background-primary);
}

.project-title {
  grid-area: 1 / 1;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.project-title > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.project-title strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-title span {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-title > div > span .el-icon {
  flex: none;
  color: var(--zh-green);
}
.project-title > div > span b { font-weight: 400; }
.toolbar-status-short { display: none; }

.editing-tools {
  display: flex;
  padding: 3px;
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}

.editing-tool-area {
  grid-area: 2 / 1 / 3 / -1;
  justify-self: center;
  padding-bottom: 6px;
  display: grid;
  justify-items: center;
  gap: 2px;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.editing-tools {
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
  flex-wrap: nowrap;
}

.editing-tools::-webkit-scrollbar,
.toolbar-actions::-webkit-scrollbar { display: none; }

.toolbar-actions {
  grid-area: 1 / 2;
  align-items: center;
  display: flex;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  justify-self: end;
  gap: 8px;
  scrollbar-width: none;
}

.toolbar-dropdown-arrow { margin-left: 4px; }

.workspace-content-mode-button { flex: 0 0 5rem; inline-size: 5rem; justify-content: center; }
.mobile-panel-trigger { display: none; }
.mobile-preview-action { display: none; }

:global(.shape-picker-option) {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-width: 112px;
}

:global(.shape-picker-option > span) { flex: 1; }
:global(.shape-picker-check) { width: 14px; color: var(--zh-text-theme); }
:global(.el-dropdown-menu__item.is-shape-selected) {
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font-weight: 600;
}

:global(.subject-picker-option) {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-width: 150px;
}

:global(.subject-picker-group-heading) {
  margin: 6px 0 2px;
  padding: 5px 16px 3px;
  color: var(--zh-text-caption);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.3;
}

:global(.subject-picker-group-heading:not(:first-child)) {
  border-top: 1px solid var(--zh-line-border);
  padding-top: 9px;
}

:global(.subject-picker-option > i) {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 20px;
  border-radius: 5px;
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font: 700 11px/1 ui-monospace, Consolas, monospace;
  font-style: normal;
}

:global(.subject-picker-option > span) { flex: 1; }
:global(.el-dropdown-menu__item.is-subject-selected) {
  color: var(--zh-text-theme);
  background: var(--zh-background-weaken);
  font-weight: 600;
}

:global(.shape-picker-preview) {
  display: inline-block;
  width: 22px;
  height: 16px;
  border: 2px solid var(--zh-text-theme);
  border-radius: 2px;
  background: var(--zh-background-weaken);
}

:global(.shape-picker-rounded) { border-radius: 7px; }
:global(.shape-picker-circle) { border-radius: 50%; }
:global(.shape-picker-diamond) { width: 14px; height: 14px; margin: 1px 4px; transform: rotate(45deg); }
:global(.shape-picker-triangle) {
  display: block;
  width: 22px;
  height: 16px;
  flex: none;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--zh-text-theme);
  overflow: visible;
}

:global(.workspace-mobile-action) { display: none; }

@media (max-width: 767.98px) and (hover: none) and (pointer: coarse) {
  :global(.workspace-mobile-action) { display: flex; }
  .toolbar {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: 60px;
    gap: 8px;
  }

  .editing-tool-area {
    display: none;
  }

  .editing-tool-area.is-mobile-open {
    position: fixed;
    z-index: 80;
    top: 60px;
    right: 8px;
    left: 8px;
    display: block;
    max-height: min(45dvh, 310px);
    padding: 8px;
    overflow: auto;
    border: 1px solid var(--zh-line-border);
    border-radius: var(--zh-radius10);
    background: var(--zh-background-primary);
    box-shadow: var(--zh-shadow2);
  }

  .editing-tools {
    flex-wrap: wrap;
    justify-content: center;
  }

  .toolbar-actions { gap: 4px; }
  .toolbar-actions > :not(.mobile-panel-trigger):not(.workspace-more):not(.mobile-preview-action):not(.mobile-save-retry) { display: none; }
  .mobile-panel-trigger { display: inline-flex; }

  .project-title strong { max-width: 42vw; }
  .project-title span { max-width: 42vw; }
}

/* Compact project actions without shifting the centered editing row. */
@media (min-width: 768px) and (max-width: 1023.98px) {
  .toolbar-actions { gap: 4px; }
  .toolbar-actions :deep(.el-button) { padding-inline: 8px; }
  .project-title strong, .project-title span { max-width: 26vw; }
}
.workspace-more { display: none; flex: none; }

@media (max-width: 767.98px) and (hover: none) and (pointer: coarse) { .workspace-more { display: inline-flex; } }
.toolbar-actions > .el-button + .el-button { margin-left: 0; }
.toolbar-actions > .el-button, .toolbar-actions > .el-dropdown { flex-shrink: 0; }
.project-title strong { max-width: 40vw; }
@media (max-width: 767.98px) and (hover: none) and (pointer: coarse) {
  .toolbar { grid-template-rows: 56px; padding-inline: 12px; }
  .project-title { gap: 4px; }
  .project-title > .el-button { width: 44px; height: 44px; flex: none; margin: 0; font-size: 19px; }
  .project-title > .el-button :deep(.el-icon) { color: var(--zh-text-primary); }
  .project-title strong, .project-title > div > span { max-width: none; }
  .project-title strong { font-size: 15px; }
  .project-title > div > span { margin-top: 2px; font-size: 11px; }
  .toolbar-status-full { display: none; }
  .toolbar-status-short { display: inline; }
  .toolbar-mode-suffix, .toolbar-project-suffix { display: none; }
  .toolbar-actions { overflow: visible; gap: 6px; }
  .toolbar-actions > :not(.mobile-preview-action):not(.mobile-save-retry) { display: none; }
  .toolbar-actions > .mobile-preview-action { display: inline-flex; min-width: 76px; min-height: 44px; padding-inline: 10px; }
  .toolbar-actions > .mobile-save-retry { display: inline-flex; min-height: 44px; padding-inline: 10px; }
}

</style>
