/** 仅重组本次请求已经收到的完整页面；缺页时明确失败，不能保存空白页。 */
export function restoreStreamedPresentation(final, received) {
  if (!final?.stream_compact) return final
  const slides = (final.slides || []).map(slide => {
    const streamed = received.get(Number(slide.slide_no))
    if (!streamed?.html) throw new Error(`第 ${slide.slide_no} 页生成结果缺失，请重试`)
    return { ...streamed, ...slide, html: streamed.html, metadata: { ...streamed.metadata, ...slide.metadata } }
  })
  if (!slides.length || slides.length !== Number(final.slide_count)) throw new Error('课件页面未接收完整，请重试')
  return { ...final, slides }
}

export async function isServerValidatedHtml(slide, digest = async text => {
  if (!globalThis.crypto?.subtle) return null
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('')
}) {
  const proof = slide?.metadata?.html_validation
  if (!proof?.valid || !/^[a-f0-9]{64}$/.test(proof.sha256 || '')) return false
  try { return (await digest(String(slide.html || ''))) === proof.sha256 }
  catch { return false } // 摘要不可用时走原来的服务端校验。
}

/** 维持原顺序的有界并发，用于校验/准备保存，不额外重试。 */
export async function mapLimited(items, limit, operation) {
  const result = new Array(items.length)
  let index = 0
  let failure
  await Promise.all(Array.from({ length: Math.min(Math.max(1, limit), items.length) }, async () => {
    while (index < items.length && !failure) {
      const current = index++
      try { result[current] = await operation(items[current], current) }
      catch (error) { failure ||= error }
    }
  }))
  if (failure) throw failure
  return result
}
