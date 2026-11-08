<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { isNavigationFailure, useRouter } from 'vue-router'
import { cleanupTempResources, listResources, rememberTempResource, syncWordConversionSource, uploadWordConversionSource } from '../apis/teacher'

const visible = defineModel({ type: Boolean, required: true })
const router = useRouter()
const sourceMode = ref('local')
const splitMode = ref('chapters')
const file = ref(null)
const resource = ref(null)
const resources = ref([])
const keyword = ref('')
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const working = ref(false)
const error = ref('')
const listError = ref('')
const pageSize = 10
let requestId = 0
let disposed = false

const isDocx = (name) => /\.docx$/i.test(String(name || ''))
const canUse = (item) => isDocx(item.file_name) && Number(item.allow_ai) === 1

async function loadResources(nextPage = 1) {
  const sequence = ++requestId
  page.value = nextPage
  loading.value = true
  listError.value = ''
  try {
    const result = await listResources({ file_type: 'word', keyword: keyword.value.trim() || undefined, page: nextPage, size: pageSize })
    if (disposed || sequence !== requestId) return
    resources.value = result?.data?.records || []
    total.value = Number(result?.data?.total) || 0
  } catch (cause) {
    if (disposed || sequence !== requestId) return
    resources.value = []
    total.value = 0
    listError.value = cause?.message || '资源库读取失败，请重试。'
  } finally {
    if (!disposed && sequence === requestId) loading.value = false
  }
}

function chooseFile(event) {
  const picked = event.target.files?.[0]
  event.target.value = ''
  error.value = ''
  file.value = null
  if (!picked) return
  if (!isDocx(picked.name)) {
    error.value = '请选择 .docx 文件。旧版 .doc 可先在 Word 中另存为 .docx。'
  } else if (!picked.size || picked.size > 50 * 1024 * 1024) {
    error.value = '文件不能为空，大小不能超过 50 MB。'
  } else {
    file.value = picked
  }
}

async function startConversion() {
  if (working.value) return
  const local = sourceMode.value === 'local'
  if (local ? !file.value : !resource.value || !canUse(resource.value)) return
  working.value = true
  error.value = ''
  let temporaryId = ''
  let handedOff = false
  try {
    let source
    if (local) {
      const selected = file.value
      const form = new FormData()
      form.append('file', selected)
      const result = await uploadWordConversionSource(form)
      const data = result?.data || result
      temporaryId = String(data?.resource_id || '')
      if (!temporaryId || !(Number(data?.text_length) > 0)) {
        throw new Error('Word 未提取到可用文字，请检查文档是否只包含图片或已加密。')
      }
      source = { id: temporaryId, name: selected.name, temp: true }
    } else {
      const selected = resource.value
      const result = await syncWordConversionSource({
        source_type: 'personal', resource_id: String(selected.id), title: selected.file_name,
        file_type: 'docx', file_url: selected.file_url || '', allow_ai: true,
      })
      const data = result?.data
      if (!['indexed', 'skipped'].includes(data?.status) || !(Number(data?.chunk_count) > 0)) {
        throw new Error(data?.error_message || '该教案尚未解析出可用内容。')
      }
      source = { id: String(selected.id), name: selected.file_name, temp: false }
    }
    if (disposed) return
    const failure = await router.push({
      name: 'TeacherHome', query: { wordConversion: '1' }, state: { wordSource: { ...source, single: splitMode.value === 'single' } },
    })
    if (isNavigationFailure(failure)) throw new Error('无法打开备课页面，请重试。')
    handedOff = true
    if (temporaryId) rememberTempResource(temporaryId)
    visible.value = false
  } catch (cause) {
    const detail = cause?.response?.data?.detail
    if (!disposed) error.value = (typeof detail === 'string' ? detail : detail?.message) || cause?.message || '无法开始转换，请重试。'
  } finally {
    if (temporaryId && !handedOff) void cleanupTempResources([temporaryId]).catch(() => {})
    working.value = false
  }
}

onBeforeUnmount(() => { disposed = true })
</script>

<template>
  <el-dialog v-model="visible" title="格式转换" width="min(560px, 92vw)" align-center
    :close-on-click-modal="!working" :close-on-press-escape="!working" :show-close="!working">
    <p><strong>Word 教案 → 可编辑 PPTX</strong></p>
    <p class="conversion-hint">提取 Word 章节、表格与插图，先确认拆分计划，再生成可编辑课件。整套课程和单份讲义使用同一条流程。</p>
    <el-radio-group v-model="splitMode" :disabled="working"><el-radio value="chapters">按章节生成多份</el-radio><el-radio value="single">整份生成一个 PPT</el-radio></el-radio-group>
    <el-radio-group v-model="sourceMode" :disabled="working" @change="sourceMode === 'library' && loadResources()">
      <el-radio-button value="local">上传本地文件</el-radio-button>
      <el-radio-button value="library">从个人资源库选择</el-radio-button>
    </el-radio-group>
    <div v-if="sourceMode === 'local'" class="conversion-source">
      <label for="conversion-docx">Word 教案（.docx，最多 50 MB）</label>
      <input id="conversion-docx" type="file" accept=".docx" :disabled="working" @change="chooseFile" />
      <span v-if="file">{{ file.name }}</span>
    </div>
    <div v-else class="conversion-source" v-loading="loading">
      <form class="conversion-search" @submit.prevent="loadResources()">
        <el-input v-model="keyword" placeholder="搜索教案文件名" aria-label="搜索教案文件名" :disabled="working" />
        <el-button native-type="submit" :disabled="working">搜索</el-button>
      </form>
      <el-radio-group v-model="resource" class="conversion-resources" :disabled="working">
        <el-radio v-for="item in resources" :key="item.id" :value="item" :disabled="!canUse(item)">
          {{ item.file_name }}{{ !isDocx(item.file_name) ? '（仅支持 .docx）' : Number(item.allow_ai) !== 1 ? '（未授权 AI 使用）' : '' }}
        </el-radio>
      </el-radio-group>
      <p v-if="listError" role="alert">{{ listError }}</p>
      <p v-else-if="!loading && !resources.length">没有找到 Word 教案，可换个关键词或上传本地文件。</p>
      <el-pagination v-if="total > pageSize" small layout="prev, pager, next" :pager-count="5"
        :current-page="page" :page-size="pageSize" :total="total" :disabled="working" @current-change="loadResources" />
      <p v-if="resource" class="conversion-hint">已选择 {{ resource.file_name }}</p>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template #footer>
      <el-button :disabled="working" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="working" :disabled="sourceMode === 'local' ? !file : !resource"
        @click="startConversion">{{ working ? '正在解析教案…' : '查看生成计划' }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.conversion-hint { color: var(--el-text-color-secondary); line-height: 1.6; overflow-wrap: anywhere; }
.conversion-source { display: grid; gap: 8px; margin: 16px 0; min-width: 0; overflow-wrap: anywhere; }
.conversion-search { display: flex; gap: 8px; }
.conversion-resources { display: grid; gap: 4px; }
.conversion-resources :deep(.el-radio) { white-space: normal; height: auto; }
</style>
