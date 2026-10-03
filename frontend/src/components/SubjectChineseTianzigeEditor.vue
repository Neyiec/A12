<script setup>
// 数据交互：接收语文田字格的 entries 与 show_pinyin，向属性面板提交完整数据；预览复用学科画布渲染。
import { computed, ref } from 'vue'
import SubjectToolRuntime from './SubjectToolRuntime.vue'

const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue'])
const MAX_CELLS = 40
const MAX_PINYIN = 32
const inputError = ref('')
const composing = ref(false)
const toneVowels = {
  a: 'āáǎà', e: 'ēéěè', i: 'īíǐì', o: 'ōóǒò', u: 'ūúǔù', ü: 'ǖǘǚǜ',
}
const entries = computed(() => Array.isArray(props.modelValue?.entries) ? props.modelValue.entries : [])
const sourceText = computed(() => entries.value.map((entry) => entry.character || '').join(''))
const showPinyin = computed(() => props.modelValue?.show_pinyin !== false)
const previewElement = computed(() => ({
  type: 'subject', subjectType: 'chinese_tianzige', name: '语文田字格',
  data: { entries: entries.value, show_pinyin: showPinyin.value },
}))

/** 将输入文字映射到格子，保留未改动文字的拼音。 */
const matchEntries = (nextChars) => {
  const old = entries.value
  let prefix = 0
  while (prefix < old.length && prefix < nextChars.length && old[prefix].character === nextChars[prefix]) prefix += 1
  let suffix = 0
  while (suffix < old.length - prefix && suffix < nextChars.length - prefix
    && old[old.length - 1 - suffix].character === nextChars[nextChars.length - 1 - suffix]) suffix += 1
  return nextChars.map((character, index) => {
    const oldIndex = index < prefix ? index : index >= nextChars.length - suffix ? old.length - (nextChars.length - index) : -1
    return { character, pinyin: oldIndex >= 0 ? String(old[oldIndex].pinyin || '') : '' }
  })
}

/** 更新汉字输入，空白不占田字格。 */
const updateText = (value) => {
  const chars = Array.from(String(value || '').replace(/\s/g, ''))
  if (chars.length > MAX_CELLS) {
    inputError.value = `最多输入 ${MAX_CELLS} 个字。`
    return
  }
  inputError.value = ''
  emit('update:modelValue', { ...props.modelValue, entries: matchEntries(chars), show_pinyin: showPinyin.value })
}

/** 在中文输入法组合期间保留原生输入，结束后再同步到格子。 */
const handleTextInput = (event) => {
  if (composing.value) return
  const input = event.target
  const raw = input.value
  const caret = raw.slice(0, input.selectionStart).replace(/\s/g, '').length
  const normalized = raw.replace(/\s/g, '')
  updateText(normalized)
  if (normalized !== raw) {
    input.value = normalized
    input.setSelectionRange(caret, caret)
  }
}

/** 完成输入法候选字选择后提交文字。 */
const finishComposition = (event) => {
  composing.value = false
  handleTextInput(event)
}

/** 更新某一个格子的拼音。 */
const updatePinyin = (index, value) => {
  const next = entries.value.map((entry, entryIndex) => entryIndex === index
    ? { ...entry, pinyin: String(value || '').slice(0, MAX_PINYIN) } : entry)
  emit('update:modelValue', { ...props.modelValue, entries: next, show_pinyin: showPinyin.value })
}

/** 根据汉语拼音规则定位需要标声调的元音。 */
const toneVowelIndex = (syllable) => {
  const lower = syllable.toLowerCase()
  if (lower.includes('a')) return lower.indexOf('a')
  if (lower.includes('e')) return lower.indexOf('e')
  if (lower.includes('ou')) return lower.indexOf('o')
  return [...lower].reduce((last, letter, index) => toneVowels[letter] ? index : last, -1)
}

/** 将 ni3 一类键盘写法转换为带声调的拼音。 */
const markPinyinTone = (syllable, tone) => {
  const normalized = syllable.replace(/u:/gi, (value) => value[0] === 'U' ? 'Ü' : 'ü')
    .replace(/v/gi, (value) => value === 'V' ? 'Ü' : 'ü')
  if (tone === '5') return normalized
  const index = toneVowelIndex(normalized)
  if (index < 0) return normalized + tone
  const vowel = normalized[index]
  const marked = toneVowels[vowel.toLowerCase()][Number(tone) - 1]
  return normalized.slice(0, index) + (vowel === vowel.toUpperCase() ? marked.toUpperCase() : marked) + normalized.slice(index + 1)
}

/** 离开拼音框时转换数字声调，仍允许直接输入带调字符。 */
const finishPinyinInput = (index, value) => {
  const converted = String(value || '').replace(/([a-zA-ZüÜvV:]+)([1-5])/g, (_, syllable, tone) => markPinyinTone(syllable, tone))
  if (converted !== value) updatePinyin(index, converted)
}

/** 切换拼音显示，同时保留已输入的拼音数据。 */
const updateShowPinyin = (value) => {
  emit('update:modelValue', { ...props.modelValue, entries: entries.value, show_pinyin: value })
}
</script>

<template>
  <div class="chinese-tianzige-editor">
    <div class="tianzige-input-panel">
      <label for="tianzige-text-input">汉字内容</label>
      <textarea id="tianzige-text-input" :value="sourceText" rows="2" :maxlength="MAX_CELLS"
        aria-label="田字格文字" placeholder="输入要展示的汉字"
        @input="handleTextInput" @compositionstart="composing = true" @compositionend="finishComposition"
      ></textarea>
      <div class="tianzige-input-footer"><span>每字一格</span><span>{{ entries.length }} / {{ MAX_CELLS }}</span></div>
    </div>

    <label class="tianzige-pinyin-toggle"><span>显示拼音</span><el-switch :model-value="showPinyin" @update:model-value="updateShowPinyin" /></label>
    <div v-if="showPinyin && entries.length" class="tianzige-pinyin-panel">
      <span class="tianzige-field-label">逐字填写拼音</span>
      <div class="tianzige-pinyin-fields">
        <label v-for="(entry, index) in entries" :key="index" class="tianzige-pinyin-field">
          <span>{{ entry.character }}</span>
          <input :value="entry.pinyin" :maxlength="MAX_PINYIN" type="text"
            :aria-label="`${entry.character}的拼音`" placeholder="拼音" @input="updatePinyin(index, $event.target.value)"
            @blur="finishPinyinInput(index, $event.target.value)"
          />
        </label>
      </div>
      <span class="tianzige-pinyin-help">可输入 ni3，离开输入框后显示为 nǐ。</span>
    </div>

    <div class="tianzige-preview" aria-label="语文田字格实时预览" role="status">
      <span class="tianzige-preview-label">预览</span>
      <SubjectToolRuntime :element="previewElement" compact />
    </div>
    <p v-if="inputError" class="tianzige-error" role="alert">{{ inputError }}</p>
  </div>
</template>

<style scoped>
.chinese-tianzige-editor { display: grid; gap: 9px; min-width: 0; }
.tianzige-input-panel, .tianzige-pinyin-panel { display: grid; gap: 6px; min-width: 0; padding: 10px 11px 8px; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.tianzige-input-panel:focus-within, .tianzige-pinyin-panel:focus-within { border-color: var(--zh-line-theme); }
.tianzige-input-panel > label, .tianzige-field-label { color: var(--zh-text-secondary); font-size: 10px; font-weight: 600; }
.tianzige-input-panel textarea { width: 100%; min-height: 48px; padding: 7px 8px; border: 1px solid var(--zh-line-border); border-radius: 5px; outline: none; resize: vertical; color: var(--zh-text-primary); background: var(--zh-background-primary); font: 16px/1.5 'Microsoft YaHei', sans-serif; }
.tianzige-input-panel textarea:focus, .tianzige-pinyin-field input:focus { border-color: var(--zh-line-theme); }
.tianzige-input-footer { display: flex; justify-content: space-between; color: var(--zh-text-caption); font-size: 10px; }
.tianzige-pinyin-toggle { display: flex; align-items: center; justify-content: space-between; color: var(--zh-text-secondary); font-size: 11px; }
.tianzige-pinyin-fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 6px; max-height: 220px; overflow-y: auto; }
.tianzige-pinyin-field { display: grid; justify-items: center; gap: 3px; min-width: 0; padding: 5px 3px; border: 1px solid var(--zh-line-border); border-radius: 5px; color: var(--zh-text-primary); background: var(--zh-background-light); font-size: 16px; }
.tianzige-pinyin-field input { width: 100%; min-width: 0; padding: 4px 2px; border: 1px solid var(--zh-line-border); border-radius: 4px; outline: none; background: var(--zh-background-primary); font-size: 11px; text-align: center; }
.tianzige-pinyin-help { color: var(--zh-text-caption); font-size: 10px; }
.tianzige-preview { display: grid; gap: 6px; min-width: 0; min-height: 160px; padding: 9px; overflow: hidden; border: 1px solid var(--zh-line-border); border-radius: 8px; background: var(--zh-background-primary); }
.tianzige-preview-label { color: var(--zh-text-caption); font-size: 10px; }
.tianzige-preview :deep(.subject-runtime) { min-height: 124px; }
.tianzige-preview :deep(.a12-subject-tool) { cursor: default; }
.tianzige-error { margin: 0; color: var(--el-color-danger); font-size: 10px; line-height: 1.5; }
</style>
