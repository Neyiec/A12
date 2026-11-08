<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'
import { useUserStore } from '../../storage/user'
import { hasPermission } from '../../utils/adminAccess'
import QuestionEditor from '../../../../frontend/src/components/QuestionEditor.vue'
import QuestionContent from '../../../../frontend/src/components/QuestionContent.vue'
import { emptyQuestion, subjects, questionTypes, questionStatuses } from '../../../../frontend/src/utils/questionBank'
const filters=reactive({status:'pending',subject:'',keyword:'',page:1,size:12})
const user=useUserStore()
const canView=computed(()=>hasPermission(user.userInfo?.permissions,'audit:view'))
const canCreate=computed(()=>hasPermission(user.userInfo?.permissions,'resources:edit'))
const canReview=computed(()=>hasPermission(user.userInfo?.permissions,'audit:audit'))
const rows=ref([]),total=ref(0),loading=ref(false),busy=ref(false),editor=ref(false),question=ref(emptyQuestion()),selected=ref(null),note=ref(''),error=ref('')
async function api(url,method='get',data){const res=await request({url,method,...(method==='get'?{params:data}:{data})});if(![0,200].includes(res.code))throw new Error(res.message||'操作失败');return res.data}
let requestSeq=0, disposed=false
async function load(){
  if(disposed)return
  if(!canView.value){rows.value=[];total.value=0;return}
  const sequence=++requestSeq
  loading.value=true;error.value=''
  try{
    const res=await api('/api/v1/admin/questions','get',{...filters})
    if(disposed||sequence!==requestSeq)return
    rows.value=res.items;total.value=res.total
  }catch(e){if(!disposed&&sequence===requestSeq)error.value=e.message}
  finally{if(!disposed&&sequence===requestSeq)loading.value=false}
}
function search(){filters.page=1;load()}
async function view(row){try{selected.value=await api(`/api/v1/admin/questions/${row.id}`);note.value=''}catch(e){ElMessage.error(e.message)}}
async function review(decision){if(busy.value||!selected.value||!canReview.value)return;if(decision!=='approved'&&!note.value.trim())return ElMessage.warning('请填写退回或下架的具体原因');busy.value=true;try{await api(`/api/v1/admin/questions/${selected.value.id}/review`,'post',{decision,note:note.value,revision:selected.value.revision});selected.value=null;await load();ElMessage.success('审核结果已保存')}catch(e){ElMessage.error(e.message)}finally{busy.value=false}}
async function publish(){if(busy.value||!canCreate.value)return;busy.value=true;try{await api('/api/v1/admin/questions','post',{...question.value,action:'publish'});editor.value=false;ElMessage.success('题目已加入公共题库');await load()}catch(e){ElMessage.error(e.message)}finally{busy.value=false}}
onMounted(load)
const refreshFromHeader=()=>{if(!loading.value&&!busy.value)void load()}
onMounted(()=>window.addEventListener('admin-refresh',refreshFromHeader))
onBeforeUnmount(()=>{disposed=true;requestSeq++;window.removeEventListener('admin-refresh',refreshFromHeader)})
</script>
<template>
  <main class="question-admin"><header><div><h1>题库录入与审核</h1><p>检查题目准确性、学科年级匹配、答案解析与表述规范。通过后进入教师公共题库。</p></div><el-button v-if="canCreate" type="primary" @click="question=emptyQuestion();editor=true">＋ 后台录入题目</el-button></header>
    <el-alert v-if="!canView" title="你拥有题目录入权限，但没有审核队列查看权限。可直接录入题目；如需处理投稿，请申请审核权限。" type="info" :closable="false"/>
    <el-alert v-else-if="!canReview" title="当前为只读浏览，尚未拥有审核或下架权限。" type="info" :closable="false"/>
    <section class="filters"><el-select v-model="filters.status"><el-option label="待审核" value="pending"/><el-option label="已公开" value="approved"/><el-option label="已退回 / 下架" value="rejected"/></el-select><el-select v-model="filters.subject" clearable placeholder="全部学科"><el-option v-for="s in subjects" :key="s" :value="s"/></el-select><el-input v-model="filters.keyword" maxlength="120" placeholder="搜索题干或知识点" @keyup.enter="search"/><el-button type="primary" @click="search">查询</el-button></section>
    <el-alert v-if="error" type="error" :title="error" :closable="false"/>
    <el-table :data="rows" v-loading="loading" empty-text="当前没有此状态的题目"><el-table-column prop="id" label="编号" width="70"/><el-table-column prop="subject" label="学科" width="100"/><el-table-column prop="grade" label="年级" width="100"/><el-table-column label="题型" width="100"><template #default="{row}">{{ questionTypes[row.question_type] }}</template></el-table-column><el-table-column prop="stem" label="题干" show-overflow-tooltip/><el-table-column prop="owner_id" label="投稿人ID" width="110"/><el-table-column label="状态" width="100"><template #default="{row}">{{ questionStatuses[row.status] }}</template></el-table-column><el-table-column label="操作" width="140"><template #default="{row}"><el-button type="primary" plain @click="view(row)">{{ row.status==='pending'?'查看并审核':'查看详情' }}</el-button></template></el-table-column></el-table>
    <el-pagination v-model:current-page="filters.page" :page-size="filters.size" :total="total" layout="prev,pager,next,total" @current-change="load"/>
    <el-dialog v-model="editor" class="question-edit-dialog" title="后台录入 · 直接发布到公共题库" width="min(860px,96vw)" :close-on-click-modal="false"><QuestionEditor v-model="question"/><template #footer><el-button @click="editor=false">取消</el-button><el-button :loading="busy" type="primary" @click="publish">确认无误，加入公共题库</el-button></template></el-dialog>
    <el-dialog :model-value="!!selected" title="题目审核" width="min(820px,96vw)" :close-on-click-modal="false" @close="selected=null"><template v-if="selected"><el-alert title="审核要点：无事实错误；答案唯一或评分依据明确；难度与学段相符；无侵权、隐私和不适宜内容。" type="info" :closable="false"/><QuestionContent :question="selected.content" answers/><el-divider/><p>历史审核记录</p><p v-if="!selected.reviews?.length">暂无审核记录</p><p v-for="(r,i) in selected.reviews||[]" :key="i">{{ r.created_at }} · {{ r.decision }} · {{ r.note }}</p><el-input v-if="canReview&&['pending','approved'].includes(selected.status)" v-model="note" type="textarea" maxlength="1000" show-word-limit :rows="3" placeholder="审核意见（退回或下架时必填，请给出可改进建议）"/></template><template #footer><el-button @click="selected=null">关闭</el-button><template v-if="canReview&&selected?.status==='pending'"><el-button type="danger" :loading="busy" @click="review('rejected')">退回修改</el-button><el-button type="primary" :loading="busy" @click="review('approved')">审核通过并公开</el-button></template><el-button v-if="canReview&&selected?.status==='approved'" type="danger" :loading="busy" @click="review('withdrawn')">下架题目</el-button></template></el-dialog>
  </main>
</template>
<style scoped>.question-admin{background:#fff;color:#20334d;padding:24px;border-radius:16px}.question-admin header{display:flex;justify-content:space-between;gap:20px;align-items:center}.question-admin header p{color:#6b7e96;line-height:1.7}.filters{display:flex;gap:14px;margin:24px 0}.filters .el-select{min-width:140px}.el-pagination{margin-top:24px}@media(max-width:800px){.filters{flex-wrap:wrap}.question-admin header{flex-direction:column;align-items:flex-start}}</style>
