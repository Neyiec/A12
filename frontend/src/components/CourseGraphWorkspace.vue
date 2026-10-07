<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../storage/user'
import LearningGraphPanel from './LearningGraphPanel.vue'
import { listCourseGraphs, getCourseGraph, saveCourseGraph, draftCourseGraph, listCourseGraphVersions,
  restoreCourseGraph, planCourseLearningPath, pruneCourseGraph, generatePathOutline,
  generatePresentationStream, exportPresentationPptx, createLearningVideo, uploadTempResource,
  createProject, batchSaveProjectPages, cleanupTempResources, listResources } from '../apis/teacher'

const router = useRouter(), user = useUserStore()
const courses = ref([]), courseId = ref(''), title = ref(''), version = ref(0), versions = ref([])
const subject = ref(''), grade = ref(''), sourceText = ref(''), resourceIds = ref([])
const nodes = ref([]), edges = ref([]), targetIds = ref([]), masteredIds = ref([]), startId = ref('')
const path = ref(null), metrics = ref(null), outline = ref(null), slides = ref([]), page = ref(0)
const busy = ref(''), error = ref(''), dirty = ref(false)
const savedProjectId = ref('')
const generatedPagesSaved = ref(false)
const relation = ref({ source: '', target: '', relation: 'prerequisite' })
const fileInput = ref(null)
const personalResources = ref([])
const bloomOptions = { remember: '记忆', understand: '理解', apply: '应用', analyze: '分析', evaluate: '评价', create: '创造' }
const relationLabels = { prerequisite: '先修', contains: '包含', related: '相关', supports: '支持技能', applies: '应用技能', assesses: '评价技能' }
const graphView = computed(() => ({ status: version.value && !dirty.value ? 'approved_course' : 'ai_proposal',
  knowledge: { nodes: nodes.value.filter(n => n.kind === 'concept'), edges: edges.value },
  skill: { nodes: nodes.value.filter(n => n.kind === 'skill'), edges: edges.value } }))
const userId = () => String(user.userInfo?.user_id || user.userInfo?.id || '')
const unwrap = response => response?.data || response
const request = () => ({ target_ids: targetIds.value, mastered_ids: masteredIds.value, start_id: startId.value || null,
  subject: subject.value, grade: grade.value })
let abort = null, disposed = false
onBeforeUnmount(() => { disposed = true; abort?.abort(); if (resourceIds.value.length) cleanupTempResources([...resourceIds.value]).catch(() => {}) })
const run = async (label, fn) => {
  if (busy.value) return
  busy.value = label; error.value = ''
  try { await fn() } catch (e) { error.value = e?.response?.data?.detail || e?.message || '操作失败'; ElMessage.error(error.value) }
  finally { busy.value = '' }
}
const refresh = async () => {
  courses.value = unwrap(await listCourseGraphs()) || []
  try { const result = unwrap(await listResources({ page: 1, size: 100 })); personalResources.value = Array.isArray(result) ? result : result.records || result.list || result.items || [] }
  catch { /* Java素材服务暂不可用时，图谱编辑仍可继续。 */ }
}
onMounted(() => run('加载课程', refresh))
function clearLearningResults() {
  path.value = null; metrics.value = null; outline.value = null; slides.value = []; page.value = 0
  savedProjectId.value = ''; generatedPagesSaved.value = false
}
function invalidate() { dirty.value = true; clearLearningResults() }
watch([targetIds, masteredIds, startId, subject, grade], () => {
  if (!busy.value) clearLearningResults()
}, { deep: true, flush: 'sync' })
function newCourse() {
  if (busy.value) return
  if (resourceIds.value.length) cleanupTempResources([...resourceIds.value]).catch(() => {})
  courseId.value = ''; title.value = ''; version.value = 0; nodes.value = []; edges.value = []
  versions.value = []; targetIds.value = []; masteredIds.value = []; startId.value = ''; resourceIds.value = []; invalidate()
}
const load = () => run('加载图谱', async () => {
  const graph = unwrap(await getCourseGraph(courseId.value, userId()))
  title.value = graph.title; version.value = graph.version; nodes.value = graph.nodes; edges.value = graph.edges
  targetIds.value = []; masteredIds.value = []; startId.value = ''; path.value = null; outline.value = null; slides.value = []; dirty.value = false
  versions.value = unwrap(await listCourseGraphVersions(courseId.value))
})
function addNode(kind) { nodes.value.push({ id: `${kind === 'concept' ? 'k' : 's'}_${crypto.randomUUID().slice(0, 8)}`,
  label: '', kind, description: '', bloom: 'understand', difficulty: 0.5, exam_frequency: 0, mastery_standard: '', resource_ids: [] }); invalidate() }
function removeNode(id) { nodes.value = nodes.value.filter(n => n.id !== id); edges.value = edges.value.filter(e => e.source !== id && e.target !== id); targetIds.value = targetIds.value.filter(i => i !== id); masteredIds.value = masteredIds.value.filter(i => i !== id); if (startId.value === id) startId.value = ''; invalidate() }
function addEdge() {
  if (!relation.value.source || !relation.value.target || relation.value.source === relation.value.target) return ElMessage.warning('请选择不同的起点与终点')
  if (edges.value.some(e => JSON.stringify(e) === JSON.stringify(relation.value))) return ElMessage.warning('关系已存在')
  edges.value.push({ ...relation.value }); invalidate()
}
const save = () => run('确认保存', async () => {
  if (!courseId.value || !title.value) throw new Error('请填写课程标识和名称')
  const graph = unwrap(await saveCourseGraph({ user_id: userId(), course_id: courseId.value, title: title.value,
    nodes: nodes.value, edges: edges.value, expected_version: version.value }))
  version.value = graph.version; nodes.value = graph.nodes; edges.value = graph.edges; dirty.value = false
  path.value = null; outline.value = null; slides.value = []
  versions.value = unwrap(await listCourseGraphVersions(courseId.value)); await refresh(); ElMessage.success('已确认并保存课程图谱')
})
const extract = () => run('抽取候选图谱', async () => {
  if (!title.value) throw new Error('请先填写课程名称')
  const draft = unwrap(await draftCourseGraph({ title: title.value, subject: subject.value, source_text: sourceText.value, resource_ids: resourceIds.value }))
  nodes.value = draft.nodes; edges.value = draft.edges; targetIds.value = []; masteredIds.value = []; invalidate()
  ElMessage.success('已生成候选图谱，请核对节点及先修关系后确认保存')
})
const upload = event => {
  const file = event.target.files?.[0]; event.target.value = ''
  if (file) run('解析参考资料', async () => { const data = new FormData(); data.append('file', file); const result = unwrap(await uploadTempResource(data)); if (!result?.resource_id) throw new Error('资料上传未返回资源ID'); resourceIds.value.push(result.resource_id); ElMessage.success('资料已加入本次图谱抽取') })
}
const restore = row => run('恢复版本', async () => {
  const graph = unwrap(await restoreCourseGraph(courseId.value, { version: row.version, expected_version: version.value }))
  nodes.value = graph.nodes; edges.value = graph.edges; title.value = graph.title; version.value = graph.version
  targetIds.value = []; masteredIds.value = []; invalidate(); dirty.value = false
  versions.value = unwrap(await listCourseGraphVersions(courseId.value)); await refresh()
})
const plan = () => run('规划学习路径', async () => {
  if (dirty.value || !version.value) throw new Error('请先确认保存图谱再规划路径')
  path.value = unwrap(await planCourseLearningPath(courseId.value, request()))
  const pruned = unwrap(await pruneCourseGraph(courseId.value, { seed_ids: targetIds.value, hops: 2, max_nodes: 24, token_budget: 4000 }))
  metrics.value = pruned.pruning_metrics; outline.value = null; slides.value = []
})
function move(index, delta) { if (busy.value || !path.value) return; const next = index + delta; if (next < 0 || next >= path.value.nodes.length) return; const nodes = [...path.value.nodes]; [nodes[index], nodes[next]] = [nodes[next], nodes[index]]; path.value = { ...path.value, nodes }; outline.value = null; slides.value = []; savedProjectId.value = ''; generatedPagesSaved.value = false }
const createOutline = () => run('校验路径并生成大纲', async () => {
  const result = unwrap(await generatePathOutline(courseId.value, { ...request(), ordered_ids: path.value.nodes.map(n => n.id) }))
  outline.value = result.outline; slides.value = []
})
const generate = () => run('按学习路径生成课件', async () => {
  slides.value = []; savedProjectId.value = ''; generatedPagesSaved.value = false; abort = new AbortController()
  const result = await generatePresentationStream({ title: title.value, outline: outline.value, model_profile: 'fast', reasoning_effort: 'low',
    resource_ids: [...new Set([...resourceIds.value, ...nodes.value.flatMap(n => n.resource_ids || [])])] },
    { signal: abort.signal, onSlide: event => { if (disposed || abort.signal.aborted) return; const slide = event.slide || event; if (slide.html) { slides.value.push(slide); slides.value.sort((a, b) => a.slide_no - b.slide_no) } } })
  if (disposed || abort.signal.aborted) return
  const deck = unwrap(result); if (deck.slides) slides.value = deck.slides
  page.value = 0
})
function download(blob, filename) { const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob])); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
const pptx = () => run('导出可编辑PPTX', async () => {
  const result = await exportPresentationPptx({ title: title.value, slides: slides.value, fidelity: 'dom_editable' })
  download(result?.data || result, `${title.value}.pptx`)
})
const saveGenerated = () => run('保存到创作工作台', async () => {
  if (!savedProjectId.value) {
    const project = unwrap(await createProject({ project_name: title.value, project_type: 'ppt', status: 'editing',
      edit_history: JSON.stringify({ course_id: courseId.value, course_version: version.value, learning_path: path.value,
        workspace_context: { mode: 'presentation', outline: outline.value } }) }))
    savedProjectId.value = String(project.id || project.project_id || '')
    if (!savedProjectId.value) throw new Error('项目创建未返回ID')
  }
  if (!generatedPagesSaved.value) {
    await batchSaveProjectPages(savedProjectId.value, { pages: slides.value.map((slide, index) => ({
      page_order: index + 1, page_type: index === 0 ? 'cover' : 'content', page_title: slide.title || `第${index+1}页`,
      page_content: JSON.stringify(slide), components: '[]', autosave: false, dirty: false,
    })) })
    generatedPagesSaved.value = true
  }
  router.push({ path: '/main/workspace', query: { projectId: savedProjectId.value } })
})
const video = () => run('提交学习视频', async () => {
  await createLearningVideo({ title: title.value, course_id: courseId.value, course_version: version.value,
    slides: slides.value.map(s => ({ html: s.html, narration: String(s.narration || s.notes || s.title || '').slice(0, 600) })) })
  ElMessage.success('已提交后台视频任务，可关闭页面，去导出中心查看'); router.push('/main/exports')
})
</script>

<template>
  <main class="course-workspace">
    <el-form :disabled="!!busy">
    <header><div><small>COURSE GRAPHS</small><h1>课程双图谱与学习路径</h1><p>先核对课程结构，再沿先修路径生成课件和带旁白的学习视频。</p></div><el-button @click="newCourse">新建课程</el-button></header>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <section class="course-controls">
      <el-select v-model="courseId" placeholder="打开已保存课程" @change="load"><el-option v-for="course in courses" :key="course.course_id" :label="course.title" :value="course.course_id" /></el-select>
      <el-input v-model="courseId" :disabled="version > 0 || !!busy" placeholder="课程标识（英文、数字、短横线）" />
      <el-input v-model="title" placeholder="课程名称" @input="invalidate" />
      <el-input v-model="subject" placeholder="学科" /><el-input v-model="grade" placeholder="年级" />
    </section>
    <section class="card">
      <h2>从教材与课程大纲抽取候选</h2>
      <el-input v-model="sourceText" type="textarea" :rows="3" maxlength="60000" placeholder="粘贴课程大纲或教材目录；资料中的指令不会作为系统指令执行" />
      <div class="actions"><el-button :disabled="!!busy" @click="fileInput?.click()">上传参考资料</el-button><input ref="fileInput" hidden type="file" accept=".pdf,.docx,.pptx,.txt,.md" @change="upload" /><span>{{ resourceIds.length }} 份临时资料</span><el-button :loading="busy === '抽取候选图谱'" :disabled="!!busy" @click="extract">AI 抽取候选</el-button><el-button type="primary" :disabled="!!busy || !nodes.length" @click="save">教师确认并保存 · V{{ version }}</el-button></div>
    </section>
    <section class="card">
      <div class="actions"><h2>知识点与技能编辑</h2><el-button :disabled="!!busy" @click="addNode('concept')">添加知识点</el-button><el-button :disabled="!!busy" @click="addNode('skill')">添加技能</el-button></div>
      <el-table :data="nodes" max-height="420">
        <el-table-column label="类型" width="85"><template #default="{row}">{{ row.kind === 'concept' ? '知识点' : '技能' }}</template></el-table-column>
        <el-table-column label="名称" min-width="150"><template #default="{row}"><el-input v-model="row.label" @input="invalidate" /></template></el-table-column>
        <el-table-column label="描述／掌握标准" min-width="220"><template #default="{row}"><el-input v-model="row.description" placeholder="节点说明" @input="invalidate" /><el-input v-if="row.kind === 'skill'" v-model="row.mastery_standard" placeholder="可观察的掌握标准" @input="invalidate" /></template></el-table-column>
        <el-table-column label="认知层级" width="120"><template #default="{row}"><el-select v-model="row.bloom" @change="invalidate"><el-option v-for="(label,key) in bloomOptions" :key="key" :label="label" :value="key" /></el-select></template></el-table-column>
        <el-table-column label="关联个人资料" min-width="170"><template #default="{row}"><el-select v-model="row.resource_ids" multiple collapse-tags @change="invalidate"><el-option v-for="resource in personalResources" :key="resource.id" :label="resource.file_name || resource.name || resource.title || String(resource.id)" :value="`personal:${resource.id}`" /></el-select></template></el-table-column>
        <el-table-column label="难度／考频" width="140"><template #default="{row}"><el-input-number v-model="row.difficulty" :min="0" :max="1" :step="0.1" controls-position="right" @change="invalidate" /><el-input-number v-model="row.exam_frequency" :min="0" :max="1" :step="0.1" controls-position="right" @change="invalidate" /></template></el-table-column>
        <el-table-column width="70"><template #default="{row}"><el-button text type="danger" :disabled="!!busy" @click="removeNode(row.id)">删除</el-button></template></el-table-column>
      </el-table>
      <div class="actions"><el-select v-model="relation.source" placeholder="起点"><el-option v-for="node in nodes" :key="node.id" :label="node.label || node.id" :value="node.id" /></el-select><el-select v-model="relation.relation"><el-option v-for="(label,key) in relationLabels" :key="key" :label="label" :value="key" /></el-select><el-select v-model="relation.target" placeholder="终点"><el-option v-for="node in nodes" :key="node.id" :label="node.label || node.id" :value="node.id" /></el-select><el-button @click="addEdge">添加关系</el-button></div>
      <div class="edges"><el-tag v-for="(edge,index) in edges" :key="`${edge.source}-${edge.target}-${edge.relation}`" :closable="!busy" @close="edges.splice(index,1); invalidate()">{{ nodes.find(n => n.id === edge.source)?.label }} → {{ nodes.find(n => n.id === edge.target)?.label }} · {{ relationLabels[edge.relation] }}</el-tag></div>
      <LearningGraphPanel v-if="nodes.length" :graphs="graphView" :max-nodes="300" :editable="!busy" @node-move="({id,position}) => { const node = nodes.find(n => n.id === id); if(node) node.position = position; invalidate() }" />
      <details v-if="versions.length"><summary>历史版本与恢复</summary><div v-for="row in versions" :key="row.version" class="actions">V{{ row.version }} · {{ row.title }}<el-button size="small" :disabled="row.version === version || !!busy" @click="restore(row)">恢复为新版本</el-button></div></details>
    </section>
    <section class="card">
      <h2>学习路径与生成范围</h2>
      <div class="actions"><el-select v-model="targetIds" multiple placeholder="目标知识点"><el-option v-for="node in nodes.filter(n => n.kind === 'concept')" :key="node.id" :label="node.label" :value="node.id" /></el-select><el-select v-model="startId" clearable placeholder="可选起点"><el-option v-for="node in nodes" :key="node.id" :label="node.label" :value="node.id" /></el-select><el-select v-model="masteredIds" multiple placeholder="已掌握节点（跳过）"><el-option v-for="node in nodes" :key="node.id" :label="node.label" :value="node.id" /></el-select><el-button :disabled="!targetIds.length || !!busy" @click="plan">规划路径与剪枝</el-button></div>
      <div v-if="metrics" class="metrics">节点 {{ metrics.nodes_before }} → {{ metrics.nodes_after }} · 估算 Token {{ metrics.estimated_tokens_before }} → {{ metrics.estimated_tokens_after }} · 主题节点保留率 {{ metrics.seed_coverage * 100 }}%（估算，不是实际模型账单）</div>
      <ol v-if="path"><li v-for="(node,index) in path.nodes" :key="node.id">{{ node.label }}<el-button text @click="move(index,-1)">上移</el-button><el-button text @click="move(index,1)">下移</el-button></li></ol>
      <div class="actions"><el-button v-if="path" :disabled="!!busy" @click="createOutline">校验顺序并生成路径大纲</el-button><el-button v-if="outline" type="primary" :disabled="!!busy" @click="generate">按路径生成 PPT</el-button><el-button v-if="slides.length" :disabled="!!busy" @click="saveGenerated">保存并进入编辑工作台</el-button><el-button v-if="slides.length" :disabled="!!busy" @click="pptx">下载可编辑 PPTX</el-button><el-button v-if="slides.length && !busy" @click="video">生成学习视频</el-button><span v-if="busy">{{ busy }}…</span></div>
      <ol v-if="outline"><li v-for="(slide,index) in outline.slides" :key="index">{{ slide.title }} · {{ slide.graph_node_ids?.join('、') || '课程导入' }}</li></ol>
      <div v-if="slides.length" class="preview"><el-select v-model="page"><el-option v-for="(slide,index) in slides" :key="index" :label="slide.title || `第${index+1}页`" :value="index" /></el-select><iframe sandbox="" :srcdoc="slides[page]?.html" title="学习路径课件预览" /><el-input v-model="slides[page].notes" type="textarea" :rows="3" maxlength="600" show-word-limit placeholder="请核对并编辑本页视频旁白，最多600字" /><p>学习视频使用静态页面与旁白；外部网络资源不会在后台截图时加载，请使用内嵌图片和样式。</p></div>
    </section>
    </el-form>
    <el-button v-if="busy === '按学习路径生成课件'" @click="abort?.abort()">停止生成</el-button>
  </main>
</template>

<style scoped>
.course-workspace{max-width:1240px;margin:auto;padding:28px 24px 60px;color:var(--zh-text-primary,#172554)}header,.actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}header{justify-content:space-between;margin-bottom:24px}h1{font-size:28px;margin:8px 0}h2{font-size:18px;margin:0 0 16px}p,small{color:#64748b}.card{padding:22px;border:1px solid #e2e8f0;border-radius:18px;background:var(--zh-surface,#fff);margin:18px 0}.course-controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.actions{margin:14px 0}.actions .el-select{width:220px}.edges{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.metrics{padding:14px;background:#eff6ff;border-radius:12px}li{padding:5px 0}.preview iframe{display:block;width:100%;aspect-ratio:16/9;border:1px solid #e2e8f0;margin-top:12px}.card :deep(.el-input-number){width:120px}.card :deep(.el-table .el-input){margin:3px 0}@media(max-width:767px){.course-workspace{padding:18px 12px}.course-controls{grid-template-columns:1fr}.card{padding:14px}.actions .el-select{width:100%}}
</style>
