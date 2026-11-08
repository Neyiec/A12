<script setup>
import { computed } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { chemicalFormulaMarkup } from '../utils/subjectTool'
const props = defineProps({ question: { type: Object, required: true }, answers: Boolean })
const render = (value, chemical = false) => {
  if (!value) return ''
  try { return katex.renderToString(chemical ? `\\mathrm{${value}}` : value, { throwOnError: false, trust: false, strict: 'ignore', maxExpand: 300, maxSize: 10 }) } catch { return '' }
}
const formula = computed(() => render(props.question.formula))
const chemical = computed(() => props.question.chemical ? chemicalFormulaMarkup(props.question.chemical) : '')
</script>
<template>
  <div class="question-content">
    <p class="stem">{{ question.stem }}</p>
    <div v-if="formula" class="formula" v-html="formula"></div>
    <div v-if="chemical" class="formula" v-html="chemical"></div>
    <p v-for="(option, index) in question.options || []" :key="index" class="option">{{ String.fromCharCode(65 + index) }}. {{ option }}</p>
    <div v-if="answers" class="answer"><p><strong>参考答案：</strong>{{ question.answer }}</p><p><strong>解析：</strong>{{ question.analysis }}</p></div>
  </div>
</template>
<style scoped>
.stem,.option,.answer p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;margin:8px 0}.formula{overflow:auto;padding:10px 0}.answer{background:#edf5ff;border-radius:10px;padding:12px;color:#294a78;margin-top:16px}.stem{font-weight:500;color:#172d4a}
</style>
