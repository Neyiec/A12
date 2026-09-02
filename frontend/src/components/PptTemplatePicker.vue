<script setup>
import { computed } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  selectedTheme: { type: String, default: '' },
  templates: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'update:selectedTheme', 'retry', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const selectedTemplate = computed(() => props.templates.find((item) => item.theme === props.selectedTheme) || null)

const templateAccent = (template) => {
  const name = String(template?.theme || '')
  if (/科技|赛博|终端/.test(name)) return '#2563eb'
  if (/中国|中式|宣纸|竹简|饺子/.test(name)) return '#b37536'
  if (/森林|清新|莫奈/.test(name)) return '#1f993f'
  if (/星月|黑|日落|红|速度/.test(name)) return '#ff6b3f'
  return '#64748b'
}

const chooseTemplate = (template) => {
  if (template?.theme) emit('update:selectedTheme', template.theme)
}
</script>

<template>
  <el-dialog v-model="visible" title="选择 PPT 生成模板" width="min(960px, 94vw)" class="ppt-template-dialog" destroy-on-close>
    <div class="ppt-template-intro">
      <div>
        <p>模板在生成 PPT 前生效，用来决定新课件的页面风格。</p>
        <small>进入创作工作台后，您仍可继续编辑 AI 生成的页面内容；这里不会改变已有页面的编辑结构。</small>
      </div>
      <el-tag v-if="selectedTemplate" effect="plain">当前：{{ selectedTemplate.name }}</el-tag>
    </div>

    <div v-loading="loading" class="ppt-template-grid">
      <el-skeleton v-if="loading && !templates.length" :rows="6" animated />
      <el-empty v-else-if="error" :description="error">
        <el-button :icon="Refresh" @click="emit('retry')">重新加载</el-button>
      </el-empty>
      <el-empty v-else-if="!templates.length" description="暂无可用的 PPT 模板" />
      <template v-if="!loading && !error && templates.length">
        <el-card
          v-for="template in templates"
          :key="template.theme"
          shadow="never"
          class="ppt-template-card"
          :class="{ 'is-selected': selectedTheme === template.theme }"
          @click="chooseTemplate(template)"
        >
          <div class="ppt-template-preview" :style="{ '--template-accent': templateAccent(template) }" aria-hidden="true">
            <i></i><i></i><i></i><b></b>
          </div>
          <div class="ppt-template-card-body">
            <div class="ppt-template-card-heading">
              <strong>{{ template.name }}</strong>
              <el-tag v-if="template.isDefault" size="small" type="success" effect="plain">默认</el-tag>
            </div>
            <p>{{ template.description }}</p>
            <div v-if="template.aliases.length" class="ppt-template-aliases">
              <span v-for="alias in template.aliases" :key="alias">{{ alias }}</span>
            </div>
            <el-button
              class="ppt-template-select-button"
              :type="selectedTheme === template.theme ? 'primary' : 'default'"
              :plain="selectedTheme !== template.theme"
              size="small"
              @click.stop="chooseTemplate(template)"
            >
              {{ selectedTheme === template.theme ? '已选择' : '选择模板' }}
            </el-button>
          </div>
        </el-card>
      </template>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!selectedTemplate" @click="emit('confirm', selectedTemplate)">使用当前模板</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.ppt-template-dialog :deep(.el-dialog__body) {
  padding-top: 10px;
}

.ppt-template-intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 13px 15px;
  border: 1px solid var(--zh-line-theme20);
  border-radius: var(--zh-radius10);
  background: var(--zh-background-weaken);
}

.ppt-template-intro p,
.ppt-template-intro small {
  display: block;
  margin: 0;
  color: var(--zh-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.ppt-template-intro small {
  margin-top: 3px;
  color: var(--zh-text-caption);
  font-size: 11px;
}

.ppt-template-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  min-height: 160px;
  max-height: min(60vh, 560px);
  overflow-y: auto;
  padding: 2px 4px 4px 2px;
}

.ppt-template-grid > .el-skeleton,
.ppt-template-grid > .el-empty {
  grid-column: 1 / -1;
}

.ppt-template-card {
  min-width: 0;
  cursor: pointer;
  border-color: var(--zh-line-border);
  border-radius: var(--zh-radius12);
  background: var(--zh-background-capsule);
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}

.ppt-template-card:hover {
  border-color: var(--zh-line-theme50);
  box-shadow: var(--zh-shadow1);
  transform: translateY(-1px);
}

.ppt-template-card.is-selected {
  border-color: var(--zh-line-theme);
  box-shadow: 0 0 0 2px var(--zh-line-theme20), var(--zh-shadow1);
}

.ppt-template-card :deep(.el-card__body) {
  display: grid;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.ppt-template-preview {
  position: relative;
  display: grid;
  align-content: center;
  gap: 7px;
  height: 74px;
  overflow: hidden;
  padding: 14px 16px;
  border-radius: var(--zh-radius8);
  background: var(--zh-background-light);
}

.ppt-template-preview::before {
  position: absolute;
  top: -26px;
  right: -18px;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--template-accent) 16%, transparent);
  content: '';
}

.ppt-template-preview i,
.ppt-template-preview b {
  position: relative;
  display: block;
  width: 64%;
  height: 5px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--template-accent) 82%, white);
}

.ppt-template-preview i:nth-child(2) {
  width: 42%;
  background: color-mix(in srgb, var(--template-accent) 34%, white);
}

.ppt-template-preview i:nth-child(3) {
  width: 52%;
  background: color-mix(in srgb, var(--template-accent) 22%, white);
}

.ppt-template-preview b {
  position: absolute;
  right: 16px;
  bottom: 14px;
  width: 28px;
  height: 28px;
  border: 3px solid var(--template-accent);
  border-radius: 50%;
  background: transparent;
}

.ppt-template-card-body {
  display: grid;
  grid-template-rows: auto minmax(34px, auto) minmax(20px, auto) auto;
  gap: 7px;
  min-width: 0;
  flex: 1;
}

.ppt-template-card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ppt-template-card-heading strong {
  overflow: hidden;
  color: var(--zh-text-primary);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ppt-template-card-body > p {
  display: -webkit-box;
  min-height: 34px;
  margin: 0;
  overflow: hidden;
  color: var(--zh-text-secondary);
  font-size: 11px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.ppt-template-aliases {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-height: 20px;
}

.ppt-template-aliases span {
  padding: 3px 7px;
  border: 1px solid var(--zh-line-tag);
  border-radius: 999px;
  color: var(--zh-text-caption);
  background: var(--zh-background-tag);
  font-size: 10px;
}

.ppt-template-select-button {
  width: 100%;
  margin-top: 2px;
}

@media (max-width: 640px) {
  .ppt-template-intro {
    flex-direction: column;
    gap: 8px;
  }

  .ppt-template-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
