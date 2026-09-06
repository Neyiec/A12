<script setup>
import { computed, ref } from 'vue'
import { Aim, ArrowDown, ArrowLeft, Check, CircleCheck, DataAnalysis, Download, EditPen, FolderOpened, Grid, Headset, Histogram, MagicStick, Picture, SetUp, VideoCamera } from '@element-plus/icons-vue'
import WorkspaceToolButton from './WorkspaceToolButton.vue'

const props = defineProps({
  title: { type: String, default: '未命名课件' },
  autosaveState: { type: String, default: '已保存' },
  projectId: { type: [String, Number], default: '' },
  modelValue: { type: String, default: '' },
  htmlMode: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'tool-select', 'back', 'export', 'generate-interactive', 'lesson-plan', 'project-manage'])

const tools = [
  { id: 'text', label: '文本', icon: EditPen },
  { id: 'image', label: '图片', icon: Picture },
  { id: 'shape', label: '形状', icon: Grid },
  { id: 'chart', label: '图表', icon: Histogram },
  { id: 'interactive', label: '互动', icon: MagicStick },
  { id: 'audio', label: '音频', icon: Headset },
  { id: 'video', label: '视频', icon: VideoCamera },
  { id: 'table', label: '表格', icon: DataAnalysis },
  { id: 'h5', label: 'H5', icon: MagicStick },
  { id: 'subject', label: '学科', icon: Aim || SetUp },
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
const selectedShape = computed(() => shapeOptions.find((item) => item.shapeKind === selectedShapeKind.value) || shapeOptions[0])
const projectLabel = computed(() => props.projectId || '演示')
const activeToolLabel = computed(() => {
  if (props.modelValue === 'shape') return selectedShape.value.label
  return tools.find((item) => item.id === props.modelValue)?.label || ''
})
const toolStatus = computed(() => props.htmlMode ? '点击工具直接插入 HTML 元素' : '选择元素后在画布中放置')

const selectTool = (tool) => {
  if (tool.id === 'interactive') {
    emit('generate-interactive')
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

const goBack = () => emit('back')
const exportProject = () => emit('export')
const openLessonPlan = () => emit('lesson-plan')
const manageProject = () => emit('project-manage')
</script>

<template>
  <header class="toolbar">
    <div class="project-title">
      <el-button text circle aria-label="返回教学助手" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <div>
        <strong>{{ title }}教学设计</strong>
        <span>
          <el-icon><CircleCheck /></el-icon>
          {{ autosaveState }} · 项目 {{ projectLabel }}
        </span>
      </div>
    </div>

    <div class="editing-tool-area">
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
          <WorkspaceToolButton v-else :icon="tool.icon" :label="tool.label" :active="modelValue === tool.id" @click="selectTool(tool)" />
        </template>
      </nav>
      <span class="tool-placement-status" aria-live="polite">{{ activeToolLabel ? (htmlMode ? `正在插入${activeToolLabel}` : `正在放置${activeToolLabel}`) : toolStatus }}</span>
    </div>

    <div class="toolbar-actions">
      <el-button :icon="FolderOpened" @click="manageProject">项目</el-button>
      <el-button :icon="SetUp" @click="openLessonPlan">教案</el-button>
      <el-button type="primary" :icon="Download" @click="exportProject">导出</el-button>
    </div>
  </header>
</template>

<style scoped>
.toolbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--zh-line-border);
  background: var(--zh-background-primary);
}

.project-title {
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

.project-title span .el-icon {
  flex: none;
  color: var(--zh-green);
}

.editing-tools {
  display: flex;
  padding: 3px;
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}

.editing-tool-area {
  display: grid;
  justify-items: center;
  gap: 2px;
}

.tool-placement-status {
  max-width: 100%;
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: 10px;
  line-height: 1.1;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-actions {
  display: flex;
  justify-self: end;
  gap: 8px;
}

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

@media (max-width: 820px) {
  .toolbar {
    grid-template-columns: 1fr auto;
  }

  .editing-tool-area {
    display: none;
  }
}

</style>
