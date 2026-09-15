<template>
  <div
    class="file-drop-upload"
    @click="openPicker"
    @dragenter.prevent="setDragOver(true)"
    @dragover.prevent="setDragOver(true)"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 拖拽区视觉由父级插槽提供；dragOver / disabled 状态经插槽 prop 暴露 -->
    <slot :drag-over="isDragOver" :disabled="disabled" />
    <input
      ref="inputRef"
      class="file-drop-upload__input"
      type="file"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @change="onInputChange"
    >
  </div>
</template>

<script setup>
/**
 * 通用文件拖拽/选择上传区（管理端复用组件）
 * [数据交互说明]
 * - 被引用: views/admin/SystemSettings.vue（导出模板上传：.json 单文件 20MB）、
 *   views/admin/ResourceKnowledge.vue（公共资源上传：多文件 500MB / 单次 20 个）
 * - 职责: 隐藏文件选择器 + 拖拽事件 + 入队前通用校验（单文件截断 / 去重 / 大小 / 类型白名单 / 数量上限），
 *   通过校验的原生 File 经 `accept` 事件交给父级入队；视觉与队列渲染由父级插槽与队列自行处理
 * - 依赖: config/adminUpload.config.js（提示文案）、utils/file.js（buildFileKey / formatFileSize / getFileExtension）
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ADMIN_UPLOAD_MESSAGES } from '@/config/adminUpload.config'
import { buildFileKey, formatFileSize, getFileExtension } from '@/utils/file'

const props = defineProps({
  /** 文件选择器 accept 属性（如 ".json" 或 ".pdf,image/*"，空串不限） */
  accept: { type: String, default: '' },
  /** 是否允许多选 */
  multiple: { type: Boolean, default: true },
  /** 允许的文件扩展名白名单（小写不含点；null 表示不按扩展名过滤） */
  acceptExts: { type: Array, default: null },
  /** 允许的 MIME 前缀（如 ['image/']；null 表示不按 MIME 过滤） */
  mimePrefixes: { type: Array, default: null },
  /** 单文件大小上限（字节；0 表示不限） */
  maxSizeBytes: { type: Number, default: 0 },
  /** 队列数量上限（含父级已有文件；0 表示不限） */
  maxCount: { type: Number, default: 0 },
  /** 父级现有队列的去重键集合（utils/file.buildFileKey 生成） */
  existingKeys: { type: Array, default: () => [] },
  /** 禁用交互（上传中） */
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['accept'])

/** 隐藏文件选择 input 引用 */
const inputRef = ref(null)

/** 拖拽区高亮状态 */
const isDragOver = ref(false)

/** 打开系统文件选择器（禁用时忽略），供容器点击与父级调用 */
const openPicker = () => {
  if (!props.disabled) inputRef.value?.click()
}

/** 拖拽悬停状态置位（禁用时忽略） */
const setDragOver = (value) => {
  if (!props.disabled) isDragOver.value = value
}

/** 拖拽离开：仅当真正离开容器（而非进入子元素）时取消高亮 */
const onDragLeave = (event) => {
  if (event.currentTarget === event.target || !event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

/** 放置文件 → 走统一入队校验 */
const onDrop = (event) => {
  isDragOver.value = false
  addFiles(event.dataTransfer?.files)
}

/** 文件选择器变更 — 取文件后清空 input 允许重复选择同一文件 */
const onInputChange = (event) => {
  addFiles(event.target?.files)
  if (event.target) event.target.value = ''
}

/**
 * 判断文件类型是否命中扩展名 / MIME 前缀白名单（两者按 OR 命中；均未配置视为不限）
 * @param {File} file - 待校验文件
 * @returns {boolean} 是否允许
 */
const isFileTypeAllowed = (file) => {
  const checks = []
  if (props.acceptExts) checks.push(props.acceptExts.includes(getFileExtension(file.name)))
  if (props.mimePrefixes) checks.push(props.mimePrefixes.some((prefix) => String(file.type || '').startsWith(prefix)))
  return checks.length === 0 || checks.some(Boolean)
}

/**
 * 逐文件校验并收集通过项：去重 → 大小 → 类型 → 数量上限，结果写入 counters
 * @param {Array<File>} candidates - 待校验文件集合
 * @param {Set<string>} existing - 现有去重键集合（命中后加入新键）
 * @param {{oversized: number, unsupported: number, duplicate: number, overflow: number}} counters - 拒绝计数器
 * @returns {Array<File>} 通过校验的文件集合
 */
const collectAccepted = (candidates, existing, counters) => {
  const accepted = []
  for (const file of candidates) {
    const key = buildFileKey(file)
    if (existing.has(key)) {
      counters.duplicate += 1
      continue
    }
    if (props.maxSizeBytes > 0 && (file.size || 0) > props.maxSizeBytes) {
      counters.oversized += 1
      continue
    }
    if (!isFileTypeAllowed(file)) {
      counters.unsupported += 1
      continue
    }
    if (props.maxCount > 0 && existing.size >= props.maxCount) {
      counters.overflow += 1
      continue
    }
    existing.add(key)
    accepted.push(file)
  }
  return accepted
}

/**
 * 统一入队入口：单文件截断 → 通用校验 → 汇总提示 → 向父级交付通过文件
 * @param {FileList|Array<File>} fileList - 文件选择器或拖拽得到的文件集合
 */
const addFiles = (fileList) => {
  if (props.disabled) return
  let candidates = Array.from(fileList || [])
  if (!candidates.length) return
  if (!props.multiple && candidates.length > 1) {
    candidates = candidates.slice(0, 1)
    ElMessage.info(ADMIN_UPLOAD_MESSAGES.singleOnly)
  }
  const counters = { oversized: 0, unsupported: 0, duplicate: 0, overflow: 0 }
  const accepted = collectAccepted(candidates, new Set(props.existingKeys), counters)
  if (counters.oversized) ElMessage.warning(ADMIN_UPLOAD_MESSAGES.oversized(counters.oversized, formatFileSize(props.maxSizeBytes)))
  if (counters.unsupported) ElMessage.warning(ADMIN_UPLOAD_MESSAGES.unsupported(counters.unsupported))
  if (counters.duplicate) ElMessage.info(ADMIN_UPLOAD_MESSAGES.duplicate(counters.duplicate))
  if (counters.overflow) ElMessage.warning(ADMIN_UPLOAD_MESSAGES.overflow(props.maxCount))
  if (accepted.length) emit('accept', accepted)
}

defineExpose({ openPicker })
</script>

<style scoped>
/* 组件容器：块级占位，视觉完全由插槽内容决定 */
.file-drop-upload {
  display: block;
}

/* 隐藏原生文件选择器（保留可访问性，由容器点击触发） */
.file-drop-upload__input {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
