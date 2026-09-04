<script setup>
import { computed, ref, watch } from 'vue'
import { ChatDotRound, Close, CopyDocument, Delete, Plus, RefreshLeft, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  slide: { type: Object, required: true },
  elements: { type: Array, default: () => [] },
  selectedElement: { type: Object, default: null },
  selectedElementId: { type: [String, Number], default: null },
  activePanel: { type: String, default: 'style' },
  themes: { type: Array, default: () => [] },
  layouts: { type: Array, default: () => [] },
  pageNumber: { type: Number, default: 1 },
})

const emit = defineEmits([
  'update:activePanel',
  'update-element-style',
  'update-element-position',
  'update-element-content',
  'update-element-field',
  'update-element-data',
  'update-slide-field',
  'select-element',
  'clear-element',
  'copy-element',
  'delete-element',
  'copy-slide',
  'remove-slide',
])

const elementTypeLabels = {
  text: '文本元素',
  formula: '公式元素',
  image: '图片元素',
  shape: '形状元素',
  chart: '图表元素',
  audio: '音频元素',
  video: '视频元素',
  table: '表格元素',
  h5: 'H5组件',
  subject: '学科工具',
}

const hasSelectedElement = computed(() => Boolean(props.selectedElement))
const selectedElementType = computed(() => elementTypeLabels[props.selectedElement?.type] || '页面元素')
const pageLabel = computed(() => `页面 ${String(props.pageNumber).padStart(2, '0')}`)
const elementList = computed(() => props.elements)
const styleValue = (key, fallback = '') => props.selectedElement?.style?.[key] ?? fallback
const positionValue = (key, fallback = 0) => props.selectedElement?.position?.[key] ?? fallback
const positionLimits = computed(() => {
  const width = Math.min(100, Math.max(4, Number(positionValue('width', 30)) || 4))
  const height = Math.min(100, Math.max(4, Number(positionValue('height', 20)) || 4))
  const x = Math.min(100 - width, Math.max(0, Number(positionValue('x')) || 0))
  const y = Math.min(100 - height, Math.max(0, Number(positionValue('y')) || 0))
  return { x: 100 - width, y: 100 - height, width: 100 - x, height: 100 - y }
})
const contentValue = computed(() => props.selectedElement?.content || '')
const currentImageSource = computed(() => props.selectedElement?.type === 'image' ? (props.selectedElement.src || '') : '')
const chartData = computed(() => Array.isArray(props.selectedElement?.data) ? props.selectedElement.data : [])
const imageSourceDraft = ref('')
const imageSourceError = ref('')
const imageFileInput = ref(null)
const elementEditorSection = ref('style')
const chartImportDraft = ref('')
const chartImportError = ref('')
const elementEditorSections = [
  { id: 'content', label: '内容' },
  { id: 'style', label: '样式' },
  { id: 'position', label: '布局' },
]
const updateStyle = (key, value) => emit('update-element-style', { key, value })
const updatePosition = (key, value) => emit('update-element-position', { key, value })
const updateContent = (value) => emit('update-element-content', value)
const updateField = (key, value) => emit('update-element-field', { key, value })
const updateData = (value) => emit('update-element-data', value)
const updateSlideField = (key, value) => emit('update-slide-field', { key, value })
const setActivePanel = (panel) => emit('update:activePanel', panel)
const selectElement = (id) => emit('select-element', id)
const clearElement = () => emit('clear-element')
const copyElement = () => { if (props.selectedElement) emit('copy-element', props.selectedElement.id) }
const deleteElement = () => { if (props.selectedElement) emit('delete-element', props.selectedElement.id) }

watch([() => props.selectedElement?.id, () => props.selectedElement?.src], () => {
  const source = props.selectedElement?.src || ''
  imageSourceDraft.value = /^data:image\//i.test(source) ? '' : source
  imageSourceError.value = ''
}, { immediate: true })

watch(() => props.selectedElement?.id, () => {
  const type = props.selectedElement?.type
  elementEditorSection.value = ['image', 'chart'].includes(type) ? 'content' : 'style'
  chartImportDraft.value = ''
  chartImportError.value = ''
}, { immediate: true })

const applyImageSource = () => {
  const source = imageSourceDraft.value.trim()
  if (!/^(https?:\/\/|data:image\/|blob:|\/|\.\/|\.\.\/)/i.test(source)) {
    imageSourceError.value = '请输入 http(s) 图片地址或项目内相对路径'
    return
  }
  imageSourceError.value = ''
  updateField('src', source)
}
const resetImageSource = () => {
  imageSourceDraft.value = ''
  imageSourceError.value = ''
  updateField('src', '')
}
const openImageFilePicker = () => imageFileInput.value?.click()
const handleImageFile = (event) => {
  const file = event.target?.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    imageSourceError.value = '请选择图片文件'
    event.target.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    imageSourceError.value = '图片不能超过 5MB'
    event.target.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    imageSourceDraft.value = ''
    imageSourceError.value = ''
    updateField('src', String(reader.result || ''))
  }
  reader.onerror = () => { imageSourceError.value = '读取图片失败，请重新选择' }
  reader.readAsDataURL(file)
  event.target.value = ''
}
const updateChartItem = (index, key, value) => {
  updateData(chartData.value.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: key === 'value' ? Number(value) : value } : { ...item }))
}
const addChartItem = () => {
  if (chartData.value.length >= 8) return
  updateData([...chartData.value.map((item) => ({ ...item })), { label: `数据${chartData.value.length + 1}`, value: 50 }])
}
const removeChartItem = (index) => {
  if (chartData.value.length <= 1) return
  updateData(chartData.value.filter((_, itemIndex) => itemIndex !== index).map((item) => ({ ...item })))
}
const importChartData = () => {
  const rows = chartImportDraft.value
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean)
    .map((row) => {
      const [label = '', rawValue = ''] = row.split(/[,，\t]/, 2)
      return { label: label.trim().slice(0, 10), value: Number(rawValue.trim()) }
    })
    .filter((item) => item.label && Number.isFinite(item.value))

  if (!rows.length) {
    chartImportError.value = '请按“名称,数值”格式输入至少一行有效数据'
    return
  }

  updateData(rows.slice(0, 8).map((item) => ({ ...item, value: Math.max(0, Math.min(100, item.value)) })))
  chartImportError.value = rows.length > 8 ? '已导入前 8 项数据' : ''
}

const resetSelectedStyle = () => {
  if (!props.selectedElement) return
  const defaults = {
    text: { color: '#102d54', fontSize: 20, fontWeight: 500, textAlign: 'left', lineHeight: 1.5, opacity: 100 },
    formula: { color: '#2563eb', fontSize: 32, fontWeight: 700, textAlign: 'center', lineHeight: 1.2, opacity: 100 },
    shape: {
      fillColor: '#dbeafe', borderColor: '#2563eb', borderWidth: 2,
      borderRadius: props.selectedElement.shapeKind === 'rounded' ? 14 : 0, opacity: 100,
    },
    image: { tintColor: '#2563eb', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, objectFit: 'cover', showCaption: true, opacity: 100 },
    chart: { color: '#2563eb', backgroundColor: '#eff6ff', borderColor: '#bfdbfe', borderWidth: 1, borderRadius: 14, opacity: 100 },
  }
  const fallback = { color: '#2563eb', backgroundColor: '#eff6ff', borderRadius: 12, opacity: 100 }
  Object.entries(defaults[props.selectedElement.type] || fallback).forEach(([key, value]) => updateStyle(key, value))
}

const typeInitials = {
  text: 'T',
  formula: 'F',
  image: 'I',
  shape: 'S',
  chart: 'C',
  audio: 'A',
  video: 'V',
  table: '▦',
  h5: 'H5',
  subject: '学',
}
</script>

<template>
  <aside class="properties" :class="{ 'has-selected-element': hasSelectedElement, 'is-content-focused': ['image', 'chart'].includes(selectedElement?.type) }" aria-label="页面属性设置">
    <header class="properties-header">
      <div>
        <span class="properties-kicker">{{ hasSelectedElement ? '元素属性' : '页面属性' }}</span>
        <strong>{{ hasSelectedElement ? selectedElement.name : '页面属性' }}</strong>
      </div>
      <el-button v-if="hasSelectedElement" text size="small" :icon="Close" @click="clearElement">返回页面</el-button>
      <span v-else>{{ pageLabel }}</span>
    </header>

    <section class="element-list-section">
      <div class="panel-section-heading">
        <strong>页面元素</strong>
        <span>{{ elementList.length }} 个 · 点击选择</span>
      </div>
      <el-select
        v-if="hasSelectedElement && elementList.length"
        class="selected-element-switcher"
        :model-value="selectedElementId"
        filterable
        aria-label="切换当前元素"
        @update:model-value="selectElement"
      >
        <el-option
          v-for="element in elementList"
          :key="element.id"
          :value="element.id"
          :label="`${element.name} · ${elementTypeLabels[element.type] || '页面元素'}`"
        />
      </el-select>
      <div v-else-if="elementList.length" class="element-list">
        <button
          v-for="element in elementList"
          :key="element.id"
          type="button"
          class="element-list-item"
          :class="{ selected: selectedElementId === element.id }"
          @click="selectElement(element.id)"
        >
          <span class="element-type-icon">{{ typeInitials[element.type] || '?' }}</span>
          <span class="element-list-copy">
            <strong>{{ element.name }}</strong>
            <small>{{ elementTypeLabels[element.type] || '页面元素' }}</small>
          </span>
          <span class="element-list-index">z{{ element.position?.zIndex ?? 1 }}</span>
        </button>
      </div>
      <el-empty v-else :image-size="48" description="页面暂无元素" />
    </section>

    <template v-if="hasSelectedElement">
      <section class="selected-element-summary">
        <div>
          <span class="element-type-badge">{{ selectedElementType }}</span>
          <strong>{{ selectedElement.name }}</strong>
        </div>
        <span class="element-id">#{{ selectedElement.id }}</span>
      </section>

      <section class="element-actions">
        <el-button :icon="CopyDocument" @click="copyElement">复制元素</el-button>
        <el-button type="danger" plain :icon="Delete" @click="deleteElement">删除元素</el-button>
      </section>

      <div class="element-editor-tabs" role="tablist" aria-label="元素属性分组">
        <button
          v-for="section in elementEditorSections"
          :key="section.id"
          type="button"
          role="tab"
          :aria-selected="elementEditorSection === section.id"
          :class="{ active: elementEditorSection === section.id }"
          @click="elementEditorSection = section.id"
        >{{ section.label }}</button>
      </div>

      <section v-show="elementEditorSection === 'content'" class="element-content-section">
        <div class="panel-section-heading">
          <strong>内容设置</strong>
          <span>同步更新画布</span>
        </div>
        <template v-if="selectedElement.type === 'image'">
          <div class="image-content-preview" :class="{ empty: !currentImageSource }">
            <img v-if="currentImageSource" :src="currentImageSource" :alt="contentValue || '当前图片预览'" />
            <span v-else>暂无图片</span>
          </div>
          <label>图片标题</label>
          <el-input :model-value="contentValue" maxlength="60" show-word-limit placeholder="显示在图片下方的说明" @update:model-value="updateContent" />
          <label>替代文本</label>
          <el-input :model-value="selectedElement.alt || contentValue" maxlength="80" show-word-limit placeholder="为无法查看图片的用户描述内容" @update:model-value="updateField('alt', $event)" />
          <label>图片地址</label>
          <el-input v-model="imageSourceDraft" clearable placeholder="https://… 或 /assets/…" @keyup.enter="applyImageSource">
            <template #append><el-button aria-label="应用图片地址" @click="applyImageSource">应用</el-button></template>
          </el-input>
          <p v-if="imageSourceError" class="content-error" role="alert">{{ imageSourceError }}</p>
          <div class="image-source-actions">
            <el-button :icon="Upload" @click="openImageFilePicker">选择本地图片</el-button>
            <el-button text @click="resetImageSource">恢复示例图</el-button>
          </div>
          <input ref="imageFileInput" hidden type="file" accept="image/*" @change="handleImageFile" />
          <p class="content-help">支持 JPG、PNG、WebP、SVG，文件不超过 5MB；图片仅保存在当前课件数据中。</p>
        </template>

        <template v-else-if="selectedElement.type === 'chart'">
          <label>图表标题</label>
          <el-input :model-value="contentValue" maxlength="40" show-word-limit placeholder="输入图表标题" @update:model-value="updateContent" />
          <div class="chart-data-heading">
            <label>图表数据</label>
            <span>数值范围 0–100</span>
          </div>
          <div class="chart-data-editor">
            <div v-for="(item, index) in chartData" :key="index" class="chart-data-row">
              <el-input :model-value="item.label" :maxlength="10" :aria-label="`第 ${index + 1} 项名称`" placeholder="名称" @update:model-value="updateChartItem(index, 'label', $event)" />
              <el-input-number :model-value="Number(item.value)" :min="0" :max="100" :aria-label="`第 ${index + 1} 项数值`" controls-position="right" @update:model-value="updateChartItem(index, 'value', $event)" />
              <el-button text circle :icon="Close" :disabled="chartData.length <= 1" :aria-label="`删除第 ${index + 1} 项`" @click="removeChartItem(index)" />
            </div>
          </div>
          <el-button class="add-chart-item" :icon="Plus" :disabled="chartData.length >= 8" @click="addChartItem">添加数据项</el-button>
          <label>批量导入数据</label>
          <el-input v-model="chartImportDraft" type="textarea" :rows="3" maxlength="240" show-word-limit placeholder="例如：A组,68&#10;B组,82&#10;C组,56" />
          <el-button class="import-chart-data" @click="importChartData">导入并覆盖当前数据</el-button>
          <p v-if="chartImportError" class="content-error" role="alert">{{ chartImportError }}</p>
          <p class="content-help">每行一项，支持英文逗号、中文逗号或 Tab 分隔；数值范围为 0–100。</p>
        </template>

        <template v-else>
          <label>{{ ['text', 'formula'].includes(selectedElement.type) ? (selectedElement.type === 'formula' ? '公式内容' : '文本内容') : '元素说明' }}</label>
          <el-input
            v-if="['text', 'formula'].includes(selectedElement.type)"
            :model-value="contentValue"
            type="textarea"
            :rows="4"
            maxlength="160"
            show-word-limit
            @update:model-value="updateContent"
          />
          <el-input v-else :model-value="contentValue" maxlength="40" show-word-limit @update:model-value="updateContent" />
        </template>
      </section>

      <section v-show="elementEditorSection === 'position'" class="element-position-section">
        <div class="panel-section-heading">
          <strong>位置与尺寸</strong>
          <span>百分比坐标 · 可拖拽</span>
        </div>
        <div class="field-grid">
          <div><label>X 位置</label><el-input-number :model-value="Number(positionValue('x'))" :min="0" :max="positionLimits.x" :step="1" controls-position="right" @update:model-value="updatePosition('x', $event)" /></div>
          <div><label>Y 位置</label><el-input-number :model-value="Number(positionValue('y'))" :min="0" :max="positionLimits.y" :step="1" controls-position="right" @update:model-value="updatePosition('y', $event)" /></div>
          <div><label>宽度</label><el-input-number :model-value="Number(positionValue('width', 30))" :min="4" :max="positionLimits.width" :step="1" controls-position="right" @update:model-value="updatePosition('width', $event)" /></div>
          <div><label>高度</label><el-input-number :model-value="Number(positionValue('height', 20))" :min="4" :max="positionLimits.height" :step="1" controls-position="right" @update:model-value="updatePosition('height', $event)" /></div>
          <div><label>旋转角度</label><el-input-number :model-value="Number(positionValue('rotation'))" :min="-180" :max="180" :step="1" controls-position="right" @update:model-value="updatePosition('rotation', $event)" /></div>
          <div><label>层级</label><el-input-number :model-value="Number(positionValue('zIndex', 1))" :min="0" :max="99" :step="1" controls-position="right" @update:model-value="updatePosition('zIndex', $event)" /></div>
        </div>
      </section>

      <section v-show="elementEditorSection === 'style'" class="element-style-section">
        <div class="panel-section-heading">
          <strong>样式设置</strong>
          <el-button text size="small" :icon="RefreshLeft" class="reset-style-button" @click="resetSelectedStyle">重置样式</el-button>
        </div>

        <template v-if="['text', 'formula'].includes(selectedElement.type)">
          <label>{{ selectedElement.type === 'formula' ? '公式颜色' : '文字颜色' }}</label>
          <div class="color-field">
            <el-color-picker :model-value="styleValue('color', '#102d54')" @update:model-value="updateStyle('color', $event)" />
            <span>{{ styleValue('color', '#102d54') }}</span>
          </div>
          <label>字号</label>
          <el-input-number :model-value="Number(styleValue('fontSize', 16))" :min="10" :max="96" controls-position="right" @update:model-value="updateStyle('fontSize', $event)" />
          <label>字重</label>
          <el-select :model-value="String(styleValue('fontWeight', 400))" @update:model-value="updateStyle('fontWeight', Number($event))">
            <el-option label="常规" value="400" />
            <el-option label="中等" value="500" />
            <el-option label="加粗" value="700" />
          </el-select>
          <label>对齐方式</label>
          <el-radio-group :model-value="styleValue('textAlign', 'left')" @update:model-value="updateStyle('textAlign', $event)">
            <el-radio-button label="left">左对齐</el-radio-button>
            <el-radio-button label="center">居中</el-radio-button>
            <el-radio-button label="right">右对齐</el-radio-button>
          </el-radio-group>
          <label>行高</label>
          <el-input-number :model-value="Number(styleValue('lineHeight', 1.5))" :min="1" :max="3" :step="0.1" :precision="1" controls-position="right" @update:model-value="updateStyle('lineHeight', $event)" />
        </template>

        <template v-else-if="selectedElement.type === 'shape'">
          <label>填充颜色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('fillColor', '#2563eb')" @update:model-value="updateStyle('fillColor', $event)" /><span>{{ styleValue('fillColor', '#2563eb') }}</span></div>
          <label>边框颜色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('borderColor', '#2563eb')" @update:model-value="updateStyle('borderColor', $event)" /><span>{{ styleValue('borderColor', '#2563eb') }}</span></div>
          <label>边框宽度</label>
          <el-input-number :model-value="Number(styleValue('borderWidth', 2))" :min="0" :max="12" controls-position="right" @update:model-value="updateStyle('borderWidth', $event)" />
          <template v-if="selectedElement.shapeKind === 'rounded'">
            <label>圆角</label>
            <el-input-number aria-label="形状圆角" :model-value="Number(styleValue('borderRadius', 14))" :min="0" :max="40" controls-position="right" @update:model-value="updateStyle('borderRadius', $event)" />
          </template>
        </template>

        <template v-else-if="selectedElement.type === 'image'">
          <label>图片色调</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('tintColor', '#2563eb')" @update:model-value="updateStyle('tintColor', $event)" /><span>{{ styleValue('tintColor', '#2563eb') }}</span></div>
          <label>边框颜色</label>
          <div class="color-field"><el-color-picker aria-label="图片边框颜色" :model-value="styleValue('borderColor', '#bfdbfe')" @update:model-value="updateStyle('borderColor', $event)" /><span>{{ styleValue('borderColor', '#bfdbfe') }}</span></div>
          <label>图片适配</label>
          <el-select :model-value="styleValue('objectFit', 'cover')" @update:model-value="updateStyle('objectFit', $event)"><el-option label="裁切填充" value="cover" /><el-option label="完整显示" value="contain" /></el-select>
          <label class="switch-field"><span>显示图片标题</span><el-switch :model-value="styleValue('showCaption', true)" @update:model-value="updateStyle('showCaption', $event)" /></label>
          <label>圆角</label>
          <el-input-number :model-value="Number(styleValue('borderRadius', 12))" :min="0" :max="40" controls-position="right" @update:model-value="updateStyle('borderRadius', $event)" />
          <label>边框宽度</label>
          <el-input-number :model-value="Number(styleValue('borderWidth', 1))" :min="0" :max="8" controls-position="right" @update:model-value="updateStyle('borderWidth', $event)" />
        </template>

        <template v-else-if="selectedElement.type === 'chart'">
          <label>图表主色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('color', '#2563eb')" @update:model-value="updateStyle('color', $event)" /><span>{{ styleValue('color', '#2563eb') }}</span></div>
          <label>图表底色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('backgroundColor', '#eff6ff')" @update:model-value="updateStyle('backgroundColor', $event)" /><span>{{ styleValue('backgroundColor', '#eff6ff') }}</span></div>
          <label>边框颜色</label>
          <div class="color-field"><el-color-picker aria-label="图表边框颜色" :model-value="styleValue('borderColor', '#bfdbfe')" @update:model-value="updateStyle('borderColor', $event)" /><span>{{ styleValue('borderColor', '#bfdbfe') }}</span></div>
          <label>边框宽度</label>
          <el-input-number aria-label="图表边框宽度" :model-value="Number(styleValue('borderWidth', 1))" :min="0" :max="8" controls-position="right" @update:model-value="updateStyle('borderWidth', $event)" />
          <label>圆角</label>
          <el-input-number :model-value="Number(styleValue('borderRadius', 12))" :min="0" :max="40" controls-position="right" @update:model-value="updateStyle('borderRadius', $event)" />
        </template>

        <template v-else>
          <label>组件主色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('color', '#2563eb')" @update:model-value="updateStyle('color', $event)" /><span>{{ styleValue('color', '#2563eb') }}</span></div>
          <label>组件底色</label>
          <div class="color-field"><el-color-picker :model-value="styleValue('backgroundColor', '#eff6ff')" @update:model-value="updateStyle('backgroundColor', $event)" /><span>{{ styleValue('backgroundColor', '#eff6ff') }}</span></div>
          <label>圆角</label>
          <el-input-number :model-value="Number(styleValue('borderRadius', 12))" :min="0" :max="40" controls-position="right" @update:model-value="updateStyle('borderRadius', $event)" />
        </template>

        <label>透明度</label>
        <el-slider :model-value="Number(styleValue('opacity', 100))" :min="0" :max="100" :show-tooltip="false" @update:model-value="updateStyle('opacity', $event)" />
        <div class="slider-value"><span>透明</span><strong>{{ styleValue('opacity', 100) }}%</strong><span>不透明</span></div>
      </section>

      <section class="element-hint">
        <el-icon><ChatDotRound /></el-icon>
        <p>可以从工具栏新增元素，也可以从元素列表查询并选中元素。位置、尺寸和样式修改会自动保存。</p>
      </section>
    </template>

    <template v-else>
      <div class="tabs">
        <button :class="{ active: activePanel === 'content' }" @click="setActivePanel('content')">内容</button>
        <button :class="{ active: activePanel === 'style' }" @click="setActivePanel('style')">样式</button>
        <button :class="{ active: activePanel === 'layout' }" @click="setActivePanel('layout')">布局</button>
      </div>

      <section v-if="activePanel === 'content'">
        <label>页面标题</label>
        <el-input :model-value="slide.title" maxlength="20" show-word-limit @update:model-value="updateSlideField('title', $event)" />
        <label>引导文案</label>
        <el-input :model-value="slide.description" type="textarea" :rows="4" maxlength="70" show-word-limit @update:model-value="updateSlideField('description', $event)" />
      </section>

      <section v-else-if="activePanel === 'style'">
        <label>主题色</label>
        <div class="theme-picker"><button v-for="item in themes" :key="item.id" :class="{ selected: slide.theme === item.id }" :style="{ background: item.color }" :title="item.name" @click="updateSlideField('theme', item.id)"></button></div>
      </section>

      <section v-else-if="activePanel === 'layout'">
        <label>页面布局</label>
        <div class="layout-picker"><button v-for="item in layouts" :key="item" :class="{ active: slide.layout === item }" @click="updateSlideField('layout', item)"><i></i><i></i><span>{{ item }}</span></button></div>
      </section>

      <section class="page-actions">
        <label>页面操作</label>
        <el-button :icon="CopyDocument" @click="emit('copy-slide')">复制页面</el-button>
        <el-button :icon="Delete" @click="emit('remove-slide')">删除页面</el-button>
      </section>

      <div class="assistant-tip"><el-icon><ChatDotRound /></el-icon><p>点击画布中的元素，或从上方元素列表选择元素，即可打开对应的属性设置。</p></div>
    </template>
  </aside>
</template>

<style scoped>
.properties { min-height: 0; overflow: auto; border-left: 1px solid var(--zh-line-border); background: var(--zh-background-primary); }
.properties-header { position: sticky; top: 0; z-index: 4; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px; border-bottom: 1px solid var(--zh-line-parting); background: var(--zh-background-primary); }
.properties-header > div { display: grid; min-width: 0; gap: 4px; }
.properties-header strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.properties-header > span, .properties-kicker { color: var(--zh-text-caption); font-size: 10px; }
.properties-kicker { color: var(--zh-text-theme); font-weight: 700; letter-spacing: .08em; }
.element-list-section, .selected-element-summary, .element-actions, .element-content-section, .element-position-section, .element-style-section, .properties > section { padding: 16px; border-bottom: 1px solid var(--zh-line-parting); }
.panel-section-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.panel-section-heading strong { font-size: 13px; }
.panel-section-heading span { color: var(--zh-text-caption); font-size: 10px; }
.element-list { display: grid; gap: 6px; }
.selected-element-switcher { width: 100%; }
.element-list-item { display: flex; align-items: center; gap: 9px; width: 100%; min-width: 0; padding: 8px; border: 1px solid transparent; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-light); text-align: left; cursor: pointer; }
.element-list-item:hover, .element-list-item.selected { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.element-type-icon { display: grid; place-items: center; flex: none; width: 24px; height: 24px; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-line-theme20); font: 700 11px var(--zh-font-number); }
.element-list-copy { display: grid; min-width: 0; gap: 2px; }
.element-list-copy strong, .element-list-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.element-list-copy strong { font-size: 11px; }
.element-list-copy small { color: var(--zh-text-caption); font-size: 9px; }
.element-list-index { margin-left: auto; color: var(--zh-text-caption); font: 10px var(--zh-font-number); }
.selected-element-summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 0; padding-top: 12px; padding-bottom: 12px; border-bottom: 0; background: var(--zh-background-weaken); }
.selected-element-summary > div { display: grid; min-width: 0; gap: 5px; }
.selected-element-summary strong { overflow: hidden; color: var(--zh-text-primary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.element-type-badge { color: var(--zh-text-theme); font-size: 10px; font-weight: 700; }
.element-id { color: var(--zh-text-caption); font: 10px var(--zh-font-number); }
.element-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.element-actions :deep(.el-button) { width: 100%; margin: 0; }
.element-content-section, .element-position-section, .element-style-section { padding-top: 14px; }
.properties.has-selected-element { display: flex; flex-direction: column; }
.properties.has-selected-element > * { flex: none; }
.properties.has-selected-element > .properties-header { order: 0; }
.properties.has-selected-element > .element-list-section { order: 1; padding-top: 12px; padding-bottom: 12px; }
.properties.has-selected-element > .selected-element-summary { order: 2; }
.properties.has-selected-element > .element-actions { order: 3; }
.element-editor-tabs { display: grid; grid-template-columns: repeat(3, 1fr); order: 4; padding: 10px 16px 0; border-bottom: 1px solid var(--zh-line-parting); background: var(--zh-background-primary); }
.element-editor-tabs button { padding: 8px 4px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; font-size: 11px; cursor: pointer; }
.element-editor-tabs button:hover, .element-editor-tabs button:focus-visible { color: var(--zh-text-theme); background: var(--zh-background-weaken); outline: none; }
.element-editor-tabs button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); font-weight: 700; }
.properties.has-selected-element > .element-style-section, .properties.has-selected-element > .element-content-section, .properties.has-selected-element > .element-position-section { order: 5; }
.properties.has-selected-element > .element-hint { order: 6; }
.reset-style-button { margin: -6px -8px -6px 0; color: var(--zh-text-caption); font-size: 10px; }
.reset-style-button:hover, .reset-style-button:focus-visible { color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.image-content-preview { position: relative; display: grid; place-items: center; aspect-ratio: 16 / 9; margin-bottom: 14px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); color: var(--zh-text-caption); background: var(--zh-background-light); font-size: 10px; }
.image-content-preview img { display: block; width: 100%; height: 100%; object-fit: cover; }
.image-content-preview::after { position: absolute; inset: 0; border: 1px solid rgb(255 255 255 / 55%); border-radius: inherit; content: ''; pointer-events: none; }
.image-source-actions { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 6px; margin-top: 10px; }
.image-source-actions :deep(.el-button) { margin: 0; }
.properties label.switch-field { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.switch-field > span { color: var(--zh-text-secondary); font-size: 11px; font-weight: 600; }
.content-help, .content-error { margin: 8px 0 0; font-size: 10px; line-height: 1.55; }
.content-help { color: var(--zh-text-caption); }
.content-error { color: var(--el-color-danger); }
.visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.chart-data-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-top: 16px; }
.chart-data-heading label { margin: 0; }
.chart-data-heading span { color: var(--zh-text-caption); font-size: 9px; }
.chart-data-editor { display: grid; gap: 7px; margin-top: 8px; }
.chart-data-row { display: grid; grid-template-columns: minmax(0, 1fr) 92px 28px; align-items: center; gap: 5px; }
.chart-data-row :deep(.el-button) { width: 28px; height: 28px; margin: 0; color: var(--zh-text-caption); }
.chart-data-row :deep(.el-button:hover:not(:disabled)) { color: var(--el-color-danger); background: var(--el-color-danger-light-9); }
.chart-data-row :deep(.el-input-number .el-input__wrapper) { padding-right: 28px; padding-left: 7px; }
.add-chart-item { width: 100%; margin-top: 10px; margin-left: 0; border-style: dashed; }
.import-chart-data { width: 100%; margin-top: 8px; margin-left: 0; }
.properties label { display: block; margin: 0 0 9px; color: var(--zh-text-secondary); font-size: 11px; font-weight: 600; }
.properties label:not(:first-child) { margin-top: 16px; }
.properties :deep(.el-input), .properties :deep(.el-input-number), .properties :deep(.el-select) { width: 100%; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 8px; }
.field-grid label { margin: 0 0 6px; font-size: 10px; }
.color-field { display: flex; align-items: center; gap: 9px; }
.color-field span { color: var(--zh-text-caption); font: 11px var(--zh-font-number); text-transform: uppercase; }
.properties :deep(.el-radio-group) { display: flex; align-items: stretch; width: 100%; }
.properties :deep(.el-radio-button) { display: flex; flex: 1 1 0; min-width: 0; margin: 0; }
.properties :deep(.el-radio-button:not(:first-child)) { margin-top: 0; }
.properties :deep(.el-radio-button__inner) { display: flex; align-items: center; justify-content: center; box-sizing: border-box; width: 100%; height: 38px; padding: 8px 4px; font-size: 10px; line-height: 1.2; }
.slider-value { display: flex; justify-content: space-between; color: var(--zh-text-caption); font-size: 10px; }
.slider-value strong { color: var(--zh-text-theme); font: 700 11px var(--zh-font-number); }
.element-hint, .assistant-tip { display: flex; gap: 8px; margin: 16px; padding: 12px; border-radius: var(--zh-radius8); background: var(--zh-background-weaken); }
.element-hint .el-icon, .assistant-tip .el-icon { flex: none; color: var(--zh-text-theme); }
.element-hint p, .assistant-tip p, .hint { margin: 0; color: var(--zh-text-secondary); font-size: 10px; line-height: 1.6; }
.tabs { display: grid; grid-template-columns: repeat(3, 1fr); padding: 10px 14px 0; border-bottom: 1px solid var(--zh-line-parting); }
.tabs button { padding: 8px; border: 0; border-bottom: 2px solid transparent; color: var(--zh-text-caption); background: transparent; cursor: pointer; }
.tabs button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); }
.theme-picker { display: flex; gap: 12px; }
.theme-picker button { width: 24px; height: 24px; border: 2px solid var(--zh-background-primary); border-radius: 50%; box-shadow: 0 0 0 1px var(--zh-line-border); cursor: pointer; }
.theme-picker button.selected { outline: 2px solid var(--zh-text-theme); outline-offset: 2px; }
.layout-picker { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.layout-picker button { display: grid; grid-template-rows: 26px auto; gap: 4px; min-height: 66px; padding: 7px 4px; border: 1px solid var(--zh-line-border); border-radius: 6px; color: var(--zh-text-caption); background: var(--zh-background-light); font-size: 9px; cursor: pointer; }
.layout-picker button.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.layout-picker i { display: block; width: 70%; height: 4px; margin: auto; background: var(--zh-line-theme50); }
.layout-picker i:nth-child(2) { width: 48%; }
.page-actions { display: grid; gap: 8px; }
.page-actions :deep(.el-button) { justify-content: flex-start; margin: 0; }
</style>
