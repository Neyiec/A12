export function parsePresentationValue(value, fallback = {}) {
  if (value == null || value === '') return fallback
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return fallback }
}

export function normalizePreviewPages(value) {
  const collection = Array.isArray(value) ? value : value?.records || value?.pages
  const pages = Array.isArray(collection) ? collection : []
  return pages.map((page, index) => {
    const source = typeof page === 'string' ? { html: page } : page || {}
    const parsed = parsePresentationValue(source.page_content ?? source.content ?? source.data, {})
    const content = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    return {
      ...source,
      ...content,
      title: content.title || source.page_title || source.title || `第 ${index + 1} 页`,
      html: content.html || content.content_html || source.html || source.srcdoc || '',
      elements: parsePresentationValue(content.elements ?? source.elements ?? source.components, []),
      notes: content.notes || source.notes || '',
      order: Number(source.page_order ?? content.pageOrder ?? index + 1),
    }
  }).sort((a, b) => a.order - b.order)
}
