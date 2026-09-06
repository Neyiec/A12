<script setup>
import { computed, ref, watch } from 'vue'
import { ChatDotRound, Close, CopyDocument, Delete, Plus, RefreshLeft, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  elements: { type: Array, default: () => [] },
  selectedElement: { type: Object, default: null },
  selectedElementId: { type: [String, Number], default: null },
  pageNumber: { type: Number, default: 1 },
  page: { type: Object, default: null },
  themes: { type: Array, default: () => [] },
  layouts: { type: Array, default: () => [] },
  resources: { type: Array, default: () => [] },
  resourcesLoading: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update-element-style',
  'update-element-position',
  'update-element-content',
  'update-element-field',
  'update-element-data',
  'select-element',
  'clear-element',
  'copy-element',
  'delete-element',
  'update-page-field',
  'update-page-theme',
  'update-page-layout',
  'update-page-background',
  'clear-page-background',
  'refresh-resources',
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
const pageBackground = computed(() => props.page?.background || {})
const pageBackgroundPreview = computed(() => props.page?.backgroundImage || props.page?.background_image || pageBackground.value.src || '')
const resourcePickerVisible = ref(false)
const resourceKeyword = ref('')
const isImageResource = (resource) => {
  const type = String(resource?.fileType || resource?.file_type || resource?.mimeType || resource?.mime_type || '').toLowerCase()
  const name = String(resource?.name || resource?.file_name || '')
  return type.startsWith('image/') || /\.(?:png|jpe?g|gif|webp|svg|bmp|avif)(?:$|\?)/i.test(name)
}
const imageResources = computed(() => props.resources.filter(isImageResource))
const filteredImageResources = computed(() => {
  const keyword = resourceKeyword.value.trim().toLowerCase()
  if (!keyword) return imageResources.value
  return imageResources.value.filter((resource) => String(resource?.name || '').toLowerCase().includes(keyword))
})
const updatePageField = (key, value) => emit('update-page-field', { key, value })
const updatePageTheme = (themeId) => emit('update-page-theme', themeId)
const updatePageLayout = (layout) => emit('update-page-layout', layout)
const openResourcePicker = () => {
  resourceKeyword.value = ''
  resourcePickerVisible.value = true
  if (!props.resources.length) emit('refresh-resources')
}
const selectBackgroundResource = (resource) => {
  emit('update-page-background', { resourceId: resource?.id, resource })
  resourcePickerVisible.value = false
}
const resourceName = (resource) => String(resource?.name || resource?.file_name || `图片素材 ${resource?.id || ''}`).trim()
const resourcePreview = (resource) => resource?.thumbnail || resource?.previewUrl || resource?.fileUrl || resource?.file_url || resource?.raw?.thumbnail || resource?.raw?.file_url || ''
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
const currentMediaSource = computed(() => ['audio', 'video'].includes(props.selectedElement?.type)
  ? (props.selectedElement?.url || props.selectedElement?.src || '')
  : '')
const currentH5Html = computed(() => props.selectedElement?.type === 'h5' ? (props.selectedElement?.html || '') : '')
const chartData = computed(() => Array.isArray(props.selectedElement?.data) ? props.selectedElement.data : [])
const tableData = computed(() => {
  if (!Array.isArray(props.selectedElement?.data)) return []
  return props.selectedElement.data.map((row) => Array.isArray(row) ? row.map((cell) => String(cell ?? '')) : [String(row ?? '')])
})
const tableColumnCount = computed(() => Math.max(1, ...tableData.value.map((row) => row.length)))
const subjectData = computed(() => props.selectedElement?.data && typeof props.selectedElement.data === 'object' && !Array.isArray(props.selectedElement.data) ? props.selectedElement.data : {})
const imageSourceDraft = ref('')
const imageSourceError = ref('')
const mediaSourceDraft = ref('')
const mediaSourceError = ref('')
const imageFileInput = ref(null)
const mediaFileInput = ref(null)
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
const selectElement = (id) => emit('select-element', id)
const clearElement = () => emit('clear-element')
const copyElement = () => { if (props.selectedElement) emit('copy-element', props.selectedElement.id) }
const deleteElement = () => { if (props.selectedElement) emit('delete-element', props.selectedElement.id) }

watch([() => props.selectedElement?.id, () => props.selectedElement?.src, () => props.selectedElement?.url], () => {
  const source = props.selectedElement?.src || ''
  imageSourceDraft.value = /^data:image\//i.test(source) ? '' : source
  imageSourceError.value = ''
  const mediaSource = props.selectedElement?.url || props.selectedElement?.src || ''
  mediaSourceDraft.value = /^data:(audio|video)\//i.test(mediaSource) ? '' : mediaSource
  mediaSourceError.value = ''
}, { immediate: true })

watch(() => props.selectedElement?.id, () => {
  const type = props.selectedElement?.type
  elementEditorSection.value = ['image', 'chart', 'audio', 'video', 'table', 'h5', 'subject'].includes(type) ? 'content' : 'style'
  chartImportDraft.value = ''
  chartImportError.value = ''
  mediaSourceError.value = ''
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
const openMediaFilePicker = () => mediaFileInput.value?.click()
const handleMediaFile = (event) => {
  const file = event.target?.files?.[0]
  if (!file) return

  const type = props.selectedElement?.type
  const isAudio = type === 'audio'
  const mediaKind = isAudio ? '音频' : '视频'
  const mimePrefix = isAudio ? 'audio/' : 'video/'
  const acceptedExtensions = isAudio
    ? ['aac', 'flac', 'm4a', 'mp3', 'ogg', 'wav', 'webm']
    : ['avi', 'm4v', 'mkv', 'mov', 'mp4', 'ogv', 'webm']
  const extension = file.name.split('.').pop()?.toLowerCase()
  const isAcceptedFile = file.type.startsWith(mimePrefix) || (!file.type && acceptedExtensions.includes(extension))

  if (!isAcceptedFile) {
    mediaSourceError.value = `请选择${mediaKind}文件`
    event.target.value = ''
    return
  }

  const maxSize = isAudio ? 20 * 1024 * 1024 : 50 * 1024 * 1024
  if (file.size > maxSize) {
    mediaSourceError.value = `${mediaKind}不能超过 ${isAudio ? '20' : '50'}MB`
    event.target.value = ''
    return
  }

  const reader = new FileReader()
  reader.onload = () => {
    mediaSourceDraft.value = ''
    mediaSourceError.value = ''
    updateField('url', String(reader.result || ''))
  }
  reader.onerror = () => { mediaSourceError.value = `读取${mediaKind}失败，请重新选择` }
  reader.readAsDataURL(file)
  event.target.value = ''
}
const applyMediaSource = () => {
  const source = mediaSourceDraft.value.trim()
  if (source && !/^(https?:\/\/|data:(audio|video)\/|blob:|\/|\.\/|\.\.\/)/i.test(source)) {
    mediaSourceError.value = '请输入 http(s) 地址或项目内相对路径'
    return
  }
  mediaSourceError.value = ''
  updateField('url', source)
}
const clearMediaSource = () => {
  mediaSourceDraft.value = ''
  mediaSourceError.value = ''
  updateField('url', '')
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
const updateTableCell = (rowIndex, columnIndex, value) => {
  const rows = tableData.value.map((row) => [...row])
  while (rows.length <= rowIndex) rows.push([])
  while (rows[rowIndex].length <= columnIndex) rows[rowIndex].push('')
  rows[rowIndex][columnIndex] = String(value ?? '')
  updateData(rows)
}
const addTableRow = () => {
  if (tableData.value.length >= 12) return
  updateData([...tableData.value.map((row) => [...row]), Array.from({ length: tableColumnCount.value }, (_, index) => `内容${index + 1}`)])
}
const removeTableRow = (index) => {
  if (tableData.value.length <= 1) return
  updateData(tableData.value.filter((_, rowIndex) => rowIndex !== index).map((row) => [...row]))
}
const addTableColumn = () => {
  if (tableColumnCount.value >= 8) return
  updateData(tableData.value.map((row) => [...row, '']))
}
const removeTableColumn = () => {
  if (tableColumnCount.value <= 1) return
  updateData(tableData.value.map((row) => row.slice(0, -1)))
}
const updateSubjectField = (key, value) => updateData({ ...subjectData.value, [key]: value })
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
  <aside class="properties" :class="{ 'has-selected-element': hasSelectedElement, 'is-content-focused': ['image', 'chart', 'audio', 'video', 'table', 'h5', 'subject'].includes(selectedElement?.type) }" aria-label="页面属性设置">
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

        <template v-else-if="['audio', 'video'].includes(selectedElement.type)">
          <div class="media-content-preview">
            <audio v-if="selectedElement.type === 'audio' && currentMediaSource" :src="currentMediaSource" controls :autoplay="Boolean(selectedElement.autoplay)" />
            <video v-else-if="selectedElement.type === 'video' && currentMediaSource" :src="currentMediaSource" controls :autoplay="Boolean(selectedElement.autoplay)" />
            <span v-else>{{ selectedElement.type === 'audio' ? '暂无音频地址' : '暂无视频地址' }}</span>
          </div>
          <label>{{ selectedElement.type === 'audio' ? '音频标题' : '视频标题' }}</label>
          <el-input :model-value="contentValue" maxlength="60" show-word-limit @update:model-value="updateContent" />
          <label>{{ selectedElement.type === 'audio' ? '音频地址' : '视频地址' }}</label>
          <el-input v-model="mediaSourceDraft" clearable placeholder="https://… 或 /assets/…" @keyup.enter="applyMediaSource">
            <template #append><el-button @click="applyMediaSource">应用</el-button></template>
          </el-input>
          <p v-if="mediaSourceError" class="content-error" role="alert">{{ mediaSourceError }}</p>
          <div class="media-source-actions">
            <el-button :icon="Upload" @click="openMediaFilePicker">选择本地{{ selectedElement.type === 'audio' ? '音频' : '视频' }}</el-button>
            <el-button text @click="clearMediaSource">清除地址</el-button>
          </div>
          <input
            ref="mediaFileInput"
            hidden
            type="file"
            :accept="selectedElement.type === 'audio' ? 'audio/*' : 'video/*'"
            @change="handleMediaFile"
          />
          <label class="switch-field"><span>自动播放</span><el-switch :model-value="Boolean(selectedElement.autoplay)" @update:model-value="updateField('autoplay', $event)" /></label>
          <label class="switch-field"><span>显示控制条</span><el-switch :model-value="selectedElement.controls !== false" @update:model-value="updateField('controls', $event)" /></label>
          <p class="content-help">支持选择本地{{ selectedElement.type === 'audio' ? '音频' : '视频' }}；{{ selectedElement.type === 'audio' ? '音频不超过 20MB' : '视频不超过 50MB' }}。文件会随当前课件数据保存。</p>
        </template>

        <template v-else-if="selectedElement.type === 'table'">
          <label>表格标题</label>
          <el-input :model-value="contentValue" maxlength="60" show-word-limit @update:model-value="updateContent" />
          <div class="table-editor-heading">
            <label>表格数据</label>
            <span>{{ tableData.length }} 行 × {{ tableColumnCount }} 列</span>
          </div>
          <div v-if="tableData.length" class="table-data-editor">
            <div v-for="(row, rowIndex) in tableData" :key="`table-row-${rowIndex}`" class="table-data-row">
              <el-input v-for="columnIndex in tableColumnCount" :key="`table-cell-${rowIndex}-${columnIndex}`" :model-value="row[columnIndex - 1] || ''" :aria-label="`第 ${rowIndex + 1} 行第 ${columnIndex} 列`" placeholder="单元格" @update:model-value="updateTableCell(rowIndex, columnIndex - 1, $event)" />
              <el-button text circle :icon="Close" :disabled="tableData.length <= 1" :aria-label="`删除第 ${rowIndex + 1} 行`" @click="removeTableRow(rowIndex)" />
            </div>
          </div>
          <el-empty v-else :image-size="40" description="暂无表格数据" />
          <div class="table-editor-actions">
            <el-button :icon="Plus" @click="addTableRow">添加行</el-button>
            <el-button @click="addTableColumn">添加列</el-button>
            <el-button text type="danger" :disabled="tableColumnCount <= 1" @click="removeTableColumn">删除末列</el-button>
          </div>
          <el-button class="initialize-table" @click="updateData([['列 1', '列 2'], ['内容 1', '内容 2']])">重置为两列表格</el-button>
          <p class="content-help">每一行对应一条记录，输入框会即时同步到页面数据。</p>
        </template>

        <template v-else-if="selectedElement.type === 'h5'">
          <label>H5 标题</label>
          <el-input :model-value="contentValue" maxlength="80" show-word-limit @update:model-value="updateContent" />
          <label>H5 HTML 内容</label>
          <el-input :model-value="currentH5Html" type="textarea" :rows="8" maxlength="12000" show-word-limit placeholder="粘贴或编辑可嵌入的 HTML5 内容" @update:model-value="updateField('html', $event)" />
          <label>模块 ID</label>
          <el-input :model-value="selectedElement.moduleId || selectedElement.module_id || ''" maxlength="80" placeholder="可选，用于关联互动模块" @update:model-value="updateField('moduleId', $event)" />
          <label>嵌入方式</label>
          <el-select :model-value="selectedElement.embedMode || selectedElement.embed_mode || 'standalone'" @update:model-value="updateField('embedMode', $event)"><el-option label="独立运行" value="standalone" /><el-option label="嵌入页面" value="slide_fragment" /></el-select>
          <p class="content-help">可编辑标题、HTML、模块关联和嵌入方式；已有互动模块仍可从画布按钮预览。</p>
        </template>

        <template v-else-if="selectedElement.type === 'subject'">
          <label>学科工具名称</label>
          <el-input :model-value="contentValue" maxlength="80" show-word-limit @update:model-value="updateContent" />
          <label>工具类型</label>
          <el-select :model-value="selectedElement.subjectType || selectedElement.subject_type || 'geometry'" @update:model-value="updateField('subjectType', $event)"><el-option label="几何绘图" value="geometry" /><el-option label="物理实验" value="physics" /><el-option label="化学结构" value="chemistry" /><el-option label="数据分析" value="data" /><el-option label="通用学科工具" value="general" /></el-select>
          <label>工具说明</label>
          <el-input :model-value="subjectData.description || subjectData.instruction || ''" type="textarea" :rows="4" maxlength="240" show-word-limit placeholder="描述工具要帮助学生观察或完成什么" @update:model-value="updateSubjectField('description', $event)" />
          <label>初始参数</label>
          <el-input :model-value="subjectData.parameters || subjectData.initial_state || ''" maxlength="240" placeholder="例如：a=3,b=4" @update:model-value="updateSubjectField('parameters', $event)" />
          <p class="content-help">学科工具的类型、说明和初始参数会保存到组件数据，便于后续重新生成或导出。</p>
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
      <section class="page-settings-section">
        <div class="panel-section-heading">
          <strong>页面信息</strong>
          <span>保存到当前页面</span>
        </div>
        <label>页面标题</label>
        <el-input
          :model-value="page?.title || ''"
          maxlength="80"
          show-word-limit
          placeholder="输入页面标题"
          @update:model-value="updatePageField('title', $event)"
        />
        <label>页面类型</label>
        <el-select :model-value="page?.pageType || page?.page_type || 'content'" @update:model-value="updatePageField('pageType', $event)">
          <el-option label="封面页" value="cover" />
          <el-option label="目录页" value="toc" />
          <el-option label="内容页" value="content" />
          <el-option label="总结页" value="summary" />
        </el-select>
        <label>讲稿与页面备注</label>
        <el-input
          :model-value="page?.notes || ''"
          type="textarea"
          :rows="4"
          maxlength="1200"
          show-word-limit
          placeholder="补充讲解提示、课堂活动或页面备注"
          @update:model-value="updatePageField('notes', $event)"
        />
      </section>

      <section class="page-settings-section">
        <div class="panel-section-heading">
          <strong>页面外观</strong>
          <span>即时预览</span>
        </div>
        <label>主题色</label>
        <div class="theme-picker" role="listbox" aria-label="选择页面主题">
          <button
            v-for="theme in themes"
            :key="theme.id"
            type="button"
            class="theme-picker-item"
            :class="{ active: (page?.theme || 'blue') === theme.id }"
            :aria-label="theme.name"
            :aria-selected="(page?.theme || 'blue') === theme.id"
            @click="updatePageTheme(theme.id)"
          >
            <span class="theme-picker-dot" :style="{ backgroundColor: theme.color }" />
            <span>{{ theme.name }}</span>
          </button>
        </div>
        <label>页面布局</label>
        <el-select :model-value="page?.layout || ''" placeholder="选择页面布局" clearable @update:model-value="updatePageLayout">
          <el-option v-for="layout in layouts" :key="layout" :label="layout" :value="layout" />
        </el-select>
        <label>背景色</label>
        <div class="color-field page-background-color-field">
          <el-color-picker :model-value="page?.backgroundColor || page?.background_color || '#f9fbff'" @update:model-value="updatePageField('backgroundColor', $event)" />
          <span>{{ page?.backgroundColor || page?.background_color || '#f9fbff' }}</span>
        </div>
        <label>背景图</label>
        <div v-if="pageBackgroundPreview" class="page-background-card">
          <img :src="pageBackgroundPreview" alt="当前页面背景图" />
          <div class="page-background-copy">
            <strong>{{ pageBackground.name || '已绑定个人资源' }}</strong>
            <small>来自个人资源库</small>
          </div>
          <el-button text type="danger" size="small" @click="emit('clear-page-background')">清除</el-button>
        </div>
        <el-button class="resource-picker-trigger" :loading="resourcesLoading" @click="openResourcePicker">
          {{ pageBackgroundPreview ? '更换资源库背景图' : '从个人资源库选择背景图' }}
        </el-button>
        <p class="content-help">背景资源会随页面绑定，后续重新生成或编辑时仍可作为上下文使用。</p>
      </section>

      <section class="selection-empty-state">
        <el-icon><ChatDotRound /></el-icon>
        <div>
          <strong>选择元素开始编辑</strong>
          <p>点击画布中的元素，或从上方列表选择元素，即可修改其内容、样式和布局。</p>
        </div>
      </section>
      <section class="page-actions">
        <label>页面操作</label>
        <el-button :icon="CopyDocument" @click="emit('copy-slide')">复制页面</el-button>
        <el-button :icon="Delete" @click="emit('remove-slide')">删除页面</el-button>
      </section>

      <el-dialog v-model="resourcePickerVisible" title="从个人资源库选择背景图" width="520px" append-to-body>
        <div class="resource-picker-toolbar">
          <el-input v-model="resourceKeyword" clearable placeholder="搜索图片名称" />
          <el-button text @click="emit('refresh-resources')">刷新</el-button>
        </div>
        <div v-if="resourcesLoading" class="resource-picker-loading">正在读取个人资源库…</div>
        <div v-else-if="filteredImageResources.length" class="resource-picker-list">
          <button
            v-for="resource in filteredImageResources"
            :key="resource.id"
            type="button"
            class="resource-picker-item"
            @click="selectBackgroundResource(resource)"
          >
            <span class="resource-picker-thumbnail">
              <img v-if="resourcePreview(resource)" :src="resourcePreview(resource)" :alt="resourceName(resource)" />
              <span v-else>IMG</span>
            </span>
            <span class="resource-picker-copy">
              <strong>{{ resourceName(resource) }}</strong>
              <small>{{ resource.fileType || resource.file_type || '图片资源' }}</small>
            </span>
            <span class="resource-picker-select">使用</span>
          </button>
        </div>
        <el-empty v-else :image-size="54" description="个人资源库中暂无图片，可先上传一张图片" />
      </el-dialog>
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
.media-content-preview { display: grid; place-items: center; min-height: 70px; margin-bottom: 14px; padding: 10px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.media-content-preview audio, .media-content-preview video { width: 100%; max-height: 150px; }
.media-content-preview span { color: var(--zh-text-caption); font-size: 11px; }
.media-source-actions { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 6px; margin-top: 10px; }
.media-source-actions :deep(.el-button) { margin: 0; }
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
.table-editor-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-top: 16px; }
.table-editor-heading label { margin: 0; }
.table-editor-heading span { color: var(--zh-text-caption); font-size: 9px; }
.table-data-editor { display: grid; gap: 7px; margin-top: 8px; overflow-x: auto; }
.table-data-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)) 28px; align-items: center; gap: 5px; min-width: 300px; }
.table-data-row :deep(.el-button) { width: 28px; height: 28px; margin: 0; color: var(--zh-text-caption); }
.table-editor-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.table-editor-actions :deep(.el-button), .initialize-table { margin: 0; }
.initialize-table { width: 100%; margin-top: 8px; border-style: dashed; }
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
.element-hint { display: flex; gap: 8px; margin: 16px; padding: 12px; border-radius: var(--zh-radius8); background: var(--zh-background-weaken); }
.element-hint .el-icon { flex: none; color: var(--zh-text-theme); }
.element-hint p, .hint { margin: 0; color: var(--zh-text-secondary); font-size: 10px; line-height: 1.6; }
.selection-empty-state { display: flex; gap: 10px; margin: 16px; padding: 14px; border: 1px dashed var(--zh-line-border); border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-light); }
.selection-empty-state .el-icon { flex: none; margin-top: 1px; color: var(--zh-text-theme); }
.selection-empty-state strong { display: block; margin-bottom: 4px; color: var(--zh-text-primary); font-size: 12px; }
.selection-empty-state p { margin: 0; font-size: 10px; line-height: 1.6; }
.page-settings-section { padding-top: 14px !important; }
.page-settings-section label:not(:first-child) { margin-top: 15px; }
.theme-picker { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.theme-picker-item { display: flex; align-items: center; gap: 7px; min-width: 0; padding: 8px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-light); font-size: 10px; cursor: pointer; }
.theme-picker-item:hover, .theme-picker-item.active { border-color: var(--zh-line-theme); color: var(--zh-text-theme); background: var(--zh-background-weaken); }
.theme-picker-dot { flex: none; width: 14px; height: 14px; border-radius: 50%; box-shadow: inset 0 0 0 2px rgb(255 255 255 / 70%); }
.page-background-card { display: grid; grid-template-columns: 54px minmax(0, 1fr) auto; align-items: center; gap: 8px; margin-bottom: 8px; padding: 6px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); background: var(--zh-background-light); }
.page-background-card img { display: block; width: 54px; height: 38px; border-radius: 5px; object-fit: cover; }
.page-background-copy { display: grid; min-width: 0; gap: 3px; }
.page-background-copy strong, .page-background-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.page-background-copy strong { color: var(--zh-text-primary); font-size: 10px; }
.page-background-copy small { color: var(--zh-text-caption); font-size: 9px; }
.resource-picker-trigger { width: 100%; margin: 0; border-style: dashed; }
.resource-picker-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px; margin-bottom: 12px; }
.resource-picker-list { display: grid; gap: 7px; max-height: 420px; overflow: auto; }
.resource-picker-item { display: grid; grid-template-columns: 48px minmax(0, 1fr) auto; align-items: center; gap: 9px; width: 100%; padding: 7px; border: 1px solid var(--zh-line-border); border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: var(--zh-background-light); text-align: left; cursor: pointer; }
.resource-picker-item:hover { border-color: var(--zh-line-theme); background: var(--zh-background-weaken); }
.resource-picker-thumbnail { display: grid; place-items: center; width: 48px; height: 36px; overflow: hidden; border-radius: 5px; color: var(--zh-text-theme); background: var(--zh-line-theme20); font: 700 9px var(--zh-font-number); }
.resource-picker-thumbnail img { display: block; width: 100%; height: 100%; object-fit: cover; }
.resource-picker-copy { display: grid; min-width: 0; gap: 3px; }
.resource-picker-copy strong, .resource-picker-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-picker-copy strong { color: var(--zh-text-primary); font-size: 11px; }
.resource-picker-copy small { color: var(--zh-text-caption); font-size: 9px; }
.resource-picker-select { color: var(--zh-text-theme); font-size: 10px; font-weight: 700; }
.resource-picker-loading { padding: 42px 0; color: var(--zh-text-caption); text-align: center; font-size: 11px; }
.page-actions { display: grid; gap: 8px; }
.page-actions :deep(.el-button) { justify-content: flex-start; margin: 0; }
</style>
