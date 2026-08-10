<script setup>
import { computed, reactive, watch } from 'vue'
import { CircleCheckFilled, QuestionFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  question: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const selectedAnswers = reactive({})
const customAnswers = reactive({})

const normalizeOption = (option, index) => {
  if (typeof option === 'string') return { value: option, label: option, description: '' }
  if (!option || typeof option !== 'object') return null
  const value = String(option.value ?? option.id ?? option.key ?? option.label ?? `option-${index + 1}`)
  return {
    value,
    label: String(option.label ?? option.title ?? option.name ?? value),
    description: String(option.description ?? option.detail ?? ''),
  }
}

const optionList = (item) => (Array.isArray(item?.options) ? item.options : []).map(normalizeOption).filter(Boolean)

const questionItems = computed(() => {
  const source = Array.isArray(props.question?.questions) && props.question.questions.length
    ? props.question.questions
    : [props.question || {}]

  return source.map((item, index) => ({
    ...item,
    field: String(item.field || item.intent_field || `clarification_${index + 1}`),
    label: String(item.label || item.title || `需要确认的信息 ${index + 1}`),
    text: String(item.text || item.question || ''),
    options: optionList(item),
    allowCustom: item.allowCustom !== false && item.allow_custom !== false && props.question?.allowCustom !== false,
    required: item.required !== false,
  }))
})

const keyFor = (item, index) => `${item.field}-${index}`
const selectedOption = (item, index) => selectedAnswers[keyFor(item, index)] || null
const customValue = (item, index) => customAnswers[keyFor(item, index)] || ''
const hasAnswer = (item, index) => Boolean(selectedOption(item, index)?.value || customValue(item, index).trim())

const canSubmit = computed(() => questionItems.value.length > 0 && questionItems.value.every((item, index) => !item.required || hasAnswer(item, index)))
const submitLabel = computed(() => questionItems.value.length > 1 ? '提交并生成大纲' : '继续生成')
const questionSignature = computed(() => JSON.stringify(questionItems.value.map((item) => ({
  field: item.field,
  label: item.label,
  text: item.text,
  options: item.options.map((option) => option.value),
}))))

const resetSelection = () => {
  Object.keys(selectedAnswers).forEach((key) => delete selectedAnswers[key])
  Object.keys(customAnswers).forEach((key) => delete customAnswers[key])
}

watch([() => props.modelValue, questionSignature], ([visible, signature], [wasVisible, previousSignature]) => {
  if (visible && (!wasVisible || signature !== previousSignature)) resetSelection()
})

const chooseOption = (item, index, option) => {
  const key = keyFor(item, index)
  selectedAnswers[key] = option
  customAnswers[key] = ''
}

const clearOptionForCustomAnswer = (item, index) => {
  delete selectedAnswers[keyFor(item, index)]
}

const submit = () => {
  if (!canSubmit.value) return

  const answers = questionItems.value
    .map((item, index) => {
      const option = selectedOption(item, index)
      const custom = customValue(item, index).trim()
      if (!option && !custom) return null
      const answer = custom || option.label
      return {
        field: item.field,
        value: custom || option.value,
        label: custom || option.label,
        answer,
      }
    })
    .filter(Boolean)

  const knownContext = answers.reduce((context, item) => {
    if (item.field) context[item.field] = item.value
    return context
  }, {})

  emit('submit', {
    answers,
    knownContext,
    value: answers[0]?.value || '',
    label: answers[0]?.label || '',
    answer: answers.map((item) => `${item.field}: ${item.answer}`).join('；'),
  })
}

const close = () => emit('update:modelValue', false)
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    class="intent-clarification-dialog"
    width="min(600px, calc(100vw - 32px))"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @closed="resetSelection"
  >
    <template #header>
      <div class="clarification-header">
        <span class="clarification-mark" aria-hidden="true"><el-icon><QuestionFilled /></el-icon></span>
        <div>
          <strong>帮我确认一下方向</strong>
          <span>AI 对你的意图还不够确定</span>
        </div>
      </div>
    </template>

    <div class="clarification-content">
      <div class="clarification-kicker">
        <span>意图澄清</span>
        <span v-if="questionItems.length > 1" class="clarification-count">需要确认 {{ questionItems.length }} 项</span>
      </div>
      <p class="clarification-question">{{ question?.text || question?.title || '为了更准确地完成创作，请补充以下信息。' }}</p>

      <div class="clarification-items">
        <section v-for="(item, index) in questionItems" :key="keyFor(item, index)" class="clarification-item">
          <div class="item-heading">
            <span><b>{{ index + 1 }}</b>{{ item.label }}</span>
            <small v-if="item.required">必填</small>
            <small v-else>可选</small>
          </div>
          <p v-if="item.text && item.text !== question?.text" class="item-question">{{ item.text }}</p>

          <div v-if="item.options.length" class="clarification-options" role="radiogroup" :aria-label="item.label">
            <button
              v-for="option in item.options"
              :key="option.value"
              type="button"
              class="clarification-option"
              :class="{ selected: selectedOption(item, index)?.value === option.value }"
              role="radio"
              :aria-checked="selectedOption(item, index)?.value === option.value"
              @click="chooseOption(item, index, option)"
            >
              <span class="option-index">{{ String(item.options.indexOf(option) + 1).padStart(2, '0') }}</span>
              <span class="option-copy">
                <strong>{{ option.label }}</strong>
                <small v-if="option.description">{{ option.description }}</small>
              </span>
              <el-icon v-if="selectedOption(item, index)?.value === option.value" class="option-check"><CircleCheckFilled /></el-icon>
            </button>
          </div>

          <div v-if="item.allowCustom" class="custom-answer">
            <div class="custom-answer-label"><span>{{ item.options.length ? '如果都不合适' : '请补充说明' }}</span><small>{{ item.required ? '可自定义填写' : '可选' }}</small></div>
            <el-input
              :model-value="customValue(item, index)"
              type="textarea"
              :rows="item.options.length ? 2 : 3"
              resize="none"
              maxlength="120"
              show-word-limit
              :placeholder="item.placeholder || `补充${item.label}`"
              @update:model-value="customAnswers[keyFor(item, index)] = $event; clearOptionForCustomAnswer(item, index)"
            />
          </div>
        </section>
      </div>

      <div class="clarification-note">
        <el-icon><QuestionFilled /></el-icon>
        <span>补充的信息会合并到当前备课上下文，AI 将据此继续生成教学大纲。</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">稍后补充</el-button>
      <el-button type="primary" :loading="loading" :disabled="!canSubmit" @click="submit">{{ submitLabel }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.intent-clarification-dialog :deep(.el-dialog) {
  overflow: hidden;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius16);
  background: var(--zh-background-pop);
  box-shadow: var(--zh-shadow3);
}

.intent-clarification-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--zh-line-parting);
}

.intent-clarification-dialog :deep(.el-dialog__body) {
  max-height: min(68vh, 640px);
  overflow: auto;
  padding: 20px 24px 8px;
}

.intent-clarification-dialog :deep(.el-dialog__footer) {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--zh-line-parting);
}

.clarification-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.clarification-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: var(--zh-radius10);
  color: var(--zh-text-white);
  background: var(--zh-gradient-blue);
  box-shadow: 0 8px 18px rgb(37 99 235 / 18%);
}

.clarification-mark .el-icon {
  font-size: 19px;
}

.clarification-header div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.clarification-header strong {
  color: var(--zh-text-primary);
  font-size: 16px;
  line-height: 1.3;
}

.clarification-header span {
  color: var(--zh-text-caption);
  font-size: 12px;
  font-weight: 400;
}

.clarification-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 7px;
  color: var(--zh-text-theme);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
}

.clarification-count {
  color: var(--zh-text-caption);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0;
}

.clarification-question {
  margin: 0 0 18px;
  color: var(--zh-text-primary);
  font-size: 15px;
  line-height: 1.7;
}

.clarification-items {
  display: grid;
  gap: 16px;
}

.clarification-item {
  padding: 14px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  background: var(--zh-background-light);
}

.item-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 9px;
  color: var(--zh-text-primary);
  font-size: 13px;
}

.item-heading > span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-heading b {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  color: var(--zh-text-theme);
  background: var(--zh-background-primary);
  font: 700 10px var(--zh-font-number);
}

.item-heading small {
  color: var(--zh-text-caption);
  font-size: 10px;
  font-weight: 400;
}

.item-question {
  margin: -2px 0 10px;
  color: var(--zh-text-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.clarification-options {
  display: grid;
  gap: 8px;
}

.clarification-option {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--zh-line-border);
  border-radius: var(--zh-radius10);
  color: var(--zh-text-secondary);
  background: var(--zh-background-primary);
  text-align: left;
  cursor: pointer;
  transition: border-color 180ms ease, background-color 180ms ease, transform 180ms ease, box-shadow 180ms ease;
}

.clarification-option:hover,
.clarification-option:focus-visible {
  border-color: var(--zh-line-theme50);
  background: var(--zh-background-weaken);
  transform: translateY(-1px);
}

.clarification-option.selected {
  border-color: var(--zh-line-theme);
  color: var(--zh-text-primary);
  background: var(--zh-background-option-on);
  box-shadow: 0 0 0 3px var(--zh-line-theme20);
}

.clarification-option:active {
  transform: scale(.99);
}

.option-index {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  color: var(--zh-text-theme);
  background: var(--zh-background-light);
  font: 700 10px var(--zh-font-number);
}

.option-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.option-copy strong {
  overflow: hidden;
  color: inherit;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.option-copy small {
  overflow: hidden;
  color: var(--zh-text-caption);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.option-check {
  color: var(--zh-text-theme);
  font-size: 18px;
}

.custom-answer {
  margin-top: 12px;
}

.custom-answer-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 7px;
  color: var(--zh-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.custom-answer-label small {
  color: var(--zh-text-caption);
  font-size: 10px;
  font-weight: 400;
}

.custom-answer :deep(.el-textarea__inner) {
  border-color: var(--zh-line-border);
  background: var(--zh-background-primary);
  box-shadow: none;
}

.custom-answer :deep(.el-textarea__inner:focus) {
  border-color: var(--zh-line-theme);
}

.clarification-note {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 16px;
  color: var(--zh-text-caption);
  font-size: 11px;
  line-height: 1.6;
}

.clarification-note .el-icon {
  margin-top: 2px;
  color: var(--zh-text-theme);
}

@media (max-width: 520px) {
  .intent-clarification-dialog :deep(.el-dialog__header),
  .intent-clarification-dialog :deep(.el-dialog__body),
  .intent-clarification-dialog :deep(.el-dialog__footer) {
    padding-right: 16px;
    padding-left: 16px;
  }

  .clarification-option {
    grid-template-columns: 26px minmax(0, 1fr) auto;
  }
}
</style>
