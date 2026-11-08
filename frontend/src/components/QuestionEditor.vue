<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { subjects, grades, questionTypes, difficulties } from '../utils/questionBank'
import QuestionContent from './QuestionContent.vue'
const SubjectFormulaEditor = defineAsyncComponent(() => import('./SubjectFormulaEditor.vue'))
const SubjectChemicalFormulaEditor = defineAsyncComponent(() => import('./SubjectChemicalFormulaEditor.vue'))
const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])
const value = computed(() => props.modelValue)
const set = (key, data) => emit('update:modelValue', { ...value.value, [key]: data })
const choices = computed(() => ['single', 'multiple'].includes(value.value.question_type))
function changeType(type) { emit('update:modelValue', { ...value.value, question_type: type, answer: '', options: ['single', 'multiple'].includes(type) ? ['', '', '', ''] : [] }) }
</script>
<template>
  <el-form label-position="top" class="question-editor">
    <p class="editor-hint">草稿可以先保存未完成的题目；提交审核前请补齐题干、选项、答案与解析。</p>
    <div class="fields">
      <el-form-item label="学科 *"><el-select :model-value="value.subject" filterable allow-create @update:model-value="set('subject',$event)"><el-option v-for="item in subjects" :key="item" :value="item" /></el-select></el-form-item>
      <el-form-item label="年级 / 学段 *"><el-select :model-value="value.grade" filterable allow-create @update:model-value="set('grade',$event)"><el-option v-for="item in grades" :key="item" :value="item" /></el-select></el-form-item>
      <el-form-item label="题型 *"><el-select :model-value="value.question_type" @update:model-value="changeType"><el-option v-for="(label,key) in questionTypes" :key="key" :label="label" :value="key" /></el-select></el-form-item>
      <el-form-item label="难度 *"><el-select :model-value="value.difficulty" @update:model-value="set('difficulty',$event)"><el-option v-for="(label,key) in difficulties" :key="key" :label="label" :value="key" /></el-select></el-form-item>
    </div>
    <el-form-item label="知识点（用逗号分隔，便于教师搜索）"><el-input :model-value="value.knowledge_points" maxlength="500" placeholder="例如：勾股定理、直角三角形" @update:model-value="set('knowledge_points',$event)" /></el-form-item>
    <el-form-item label="题干 *"><el-input type="textarea" :rows="4" :model-value="value.stem" maxlength="10000" show-word-limit placeholder="完整描述题目与作答要求" @update:model-value="set('stem',$event)" /></el-form-item>
    <template v-if="choices">
      <el-form-item v-for="(option,index) in value.options" :key="index" :label="`选项 ${String.fromCharCode(65+index)} *`"><el-input :model-value="option" maxlength="2000" @update:model-value="set('options',value.options.map((s,i)=>i===index?$event:s))" /></el-form-item>
      <el-button :disabled="value.options.length>=8" @click="set('options',[...value.options,''])">添加选项</el-button>
      <el-button :disabled="value.options.length<=2" @click="set('options',value.options.slice(0,-1))">移除末项</el-button>
    </template>
    <el-form-item label="参考答案 *" style="margin-top:20px">
      <el-select v-if="value.question_type==='judgment'" :model-value="value.answer" @update:model-value="set('answer',$event)"><el-option value="正确" /><el-option value="错误" /></el-select>
      <el-input v-else :model-value="value.answer" type="textarea" :rows="2" maxlength="5000" :placeholder="choices?'单选填 A；多选填 A,C（用英文逗号分隔）':'填写参考答案或评分要点'" @update:model-value="set('answer',$event)" />
    </el-form-item>
    <el-form-item label="答案解析 / 评分依据 *"><el-input :model-value="value.analysis" type="textarea" :rows="3" maxlength="10000" placeholder="说明思路、关键步骤以及评分依据，审核通过后供教师参考" @update:model-value="set('analysis',$event)" /></el-form-item>
    <el-collapse>
      <el-collapse-item title="学科组件 · 插入数学 / 物理公式" name="math"><SubjectFormulaEditor :model-value="value.formula" @update:model-value="set('formula',$event)" /></el-collapse-item>
      <el-collapse-item title="学科组件 · 插入化学式 / 反应式" name="chem"><SubjectChemicalFormulaEditor :model-value="value.chemical" @update:model-value="set('chemical',$event)" /></el-collapse-item>
      <el-collapse-item title="查看题目预览（含答案）" name="preview"><QuestionContent :question="value" answers /></el-collapse-item>
    </el-collapse>
  </el-form>
</template>
<style scoped>.editor-hint{color:#617895;line-height:1.6}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 20px}.question-editor :deep(.el-select){width:100%}@media(max-width:600px){.fields{grid-template-columns:1fr}}</style>
<style>.question-edit-dialog{margin-top:5dvh!important}.question-edit-dialog .el-dialog__body{max-height:calc(90dvh - 140px);overflow-y:auto;padding-right:12px}.question-edit-dialog .el-dialog__footer{border-top:1px solid #edf2fa;padding-top:16px}</style>
