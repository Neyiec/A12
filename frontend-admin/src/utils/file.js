/**
 * 文件公共工具
 * [数据交互说明]
 * - 被引用: views/admin/SystemSettings.vue（导出模板上传）、views/admin/ResourceKnowledge.vue（公共资源上传）、
 *   components/admin/FileDropUpload.vue（通用拖拽上传组件）
 * - 职责: 扩展名解析、文件大小格式化、上传去重键生成——原先在两个视图中重复实现，统一收敛于此
 */

/**
 * 获取文件扩展名（小写）
 * @param {string} name - 文件名
 * @param {string} [fallback=''] - 无扩展名时的返回值
 * @returns {string} 扩展名（不含点）
 */
export const getFileExtension = (name, fallback = '') => {
  const parts = String(name || '').toLowerCase().split('.')
  return parts.length > 1 ? parts.pop() : fallback
}

/**
 * 格式化文件大小为可读文本
 * @param {number} bytes - 字节数
 * @returns {string} 如 "4.2 MB"，非法输入返回 "—"
 */
export const formatFileSize = (bytes) => {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

/**
 * 生成文件去重键（同名同大小同修改时间视为同一文件）
 * @param {{name: string, size: number, lastModified?: number}} file - 原生 File 或上传队列项
 * @returns {string} 去重键
 */
export const buildFileKey = (file) => `${file?.name || ''}:${file?.size || 0}:${file?.lastModified || 0}`
