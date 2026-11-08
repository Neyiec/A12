<script setup>
import { watch } from 'vue'
const model = defineModel({ type: Object, required: true })
defineProps({ disabled: Boolean })
watch(() => model.value.source_type, type => {
  model.value.authority_level = ['official', 'publisher'].includes(type) ? type : 'general'
})
</script>

<template>
  <div class="source-fields">
    <p class="source-hint">来源与版本登记为发布必填信息。批量上传前请确认所选文件共用同一来源；不同来源请分批上传。</p>
    <el-form label-position="top" :disabled="disabled">
      <div class="source-grid">
        <el-form-item label="资料时效类型 *"><el-select v-model="model.source_kind">
          <el-option v-for="[value, label] in [['curriculum','课程标准'],['textbook','教材'],['current_affairs','时政资料'],['courseware','课件'],['other','其他教学资料']]" :key="value" :value="value" :label="label" />
        </el-select></el-form-item>
        <el-form-item label="来源类型 *"><el-select v-model="model.source_type">
          <el-option v-for="[value, label] in [['official','官方机构'],['publisher','出版社'],['teacher','教师原创'],['other','其他来源']]" :key="value" :value="value" :label="label" />
        </el-select></el-form-item>
        <el-form-item label="版本年份 *"><el-input v-model="model.version_year" placeholder="如 2022" maxlength="4" /></el-form-item>
        <el-form-item label="版本 / 教材版次 *"><el-input v-model="model.version_label" placeholder="如 2022年版 / 第2版 / v1" maxlength="100" /></el-form-item>
        <el-form-item label="可信等级"><el-input :model-value="({official:'官方 · gov.cn',publisher:'出版社 · pep.com.cn / hep.com.cn',general:'一般登记来源'})[model.authority_level] || '按来源类型联动'" disabled /></el-form-item>
        <el-form-item :label="model.source_kind === 'current_affairs' ? '有效期至 *' : '有效期至（可选）'"><el-date-picker v-model="model.valid_until" type="date" value-format="YYYY-MM-DD" placeholder="时政资料必填" /></el-form-item>
      </div>
      <el-form-item label="来源链接（官方 / 出版社必填）"><el-input v-model="model.source_url" placeholder="HTTPS 原始出处；域名由服务端核验" maxlength="1800" /></el-form-item>
      <el-form-item label="来源说明（无链接时必填）"><el-input v-model="model.source_note" type="textarea" :rows="2" placeholder="如作者、出版信息、原创说明及授权依据" maxlength="500" /></el-form-item>
    </el-form>
    <small>课标按版本、教材按版次核对，不以入库日期宣称最新；时政到期停止引用；课件同时记录入库时间。Word 无固定页码时只标注分块，不虚构页号。</small>
  </div>
</template>

<style scoped>
.source-fields { padding: 16px; margin: 12px 0; border: 1px solid #dce7ff; border-radius: 12px; background: #fff; color: #243754; }
.source-hint { color: #275ac9; line-height: 1.6; }
.source-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 0 16px; }
.source-fields :deep(.el-select), .source-fields :deep(.el-date-editor) { width:100%; }
small { color: #62728a; line-height: 1.6; }
@media(max-width:640px) { .source-grid { grid-template-columns:1fr; } }
</style>
