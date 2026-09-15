/**
 * 管理端通用上传组件（FileDropUpload）的提示文案配置 — 落实"禁止硬编码"约定
 * [数据交互说明]
 * - 被引用: components/admin/FileDropUpload.vue
 */

export const ADMIN_UPLOAD_MESSAGES = {
  /** 单文件模式下选择了多个文件 */
  singleOnly: '一次只能上传一个文件，已选取第一个文件',
  /** 文件超过大小限制（count: 数量, sizeText: 已格式化的大小文本） */
  oversized: (count, sizeText) => `${count} 个文件超过 ${sizeText} 限制，已跳过`,
  /** 文件类型不在白名单 */
  unsupported: (count) => `${count} 个文件格式不受支持，已跳过`,
  /** 与已有队列重复 */
  duplicate: (count) => `${count} 个重复文件已跳过`,
  /** 超出单次数量上限（max: 上限值） */
  overflow: (max) => `单次最多上传 ${max} 个文件，已忽略多余文件`,
}
