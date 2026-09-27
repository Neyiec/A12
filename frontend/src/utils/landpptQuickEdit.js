/**
 * Adapted from LandPPT's quick-edit implementation (Apache-2.0).
 * Upstream: https://github.com/sligter/LandPPT
 * Source modules: projectSlidesEditor.quickEdit.js / quickEditActions.js
 *
 * The upstream editor is coupled to Jinja pages and global variables. This
 * module keeps the reusable DOM rules while leaving persistence to A12's Vue
 * state and Java page APIs.
 */

const DIRECT_TEXT_TAGS = new Set([
  'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
  'P', 'SPAN', 'DIV', 'LI', 'TD', 'TH',
  'A', 'SMALL', 'STRONG', 'EM', 'B', 'I', 'U', 'S', 'MARK', 'BLOCKQUOTE',
])

const INLINE_CHILD_TAGS = new Set([
  'BR', 'SPAN', 'A', 'SMALL', 'STRONG', 'EM', 'B', 'I', 'U', 'S', 'MARK', 'SUB', 'SUP', 'CODE',
])

const STRUCTURAL_SELECTOR = [
  'img', 'svg', 'canvas', 'table', 'thead', 'tbody', 'tfoot', 'tr',
  'ul', 'ol', 'video', 'audio', 'iframe', 'form', 'button', 'input', 'textarea', 'select',
  'mjx-container', '.MathJax', '.MathJax_Display', '.katex', '.katex-display',
  'math', '[data-latex]', '[data-tex]', '[data-formula]', '[data-equation]', '[data-math]',
].join(',')

export const canLandPptDirectEdit = (element) => {
  if (!element?.tagName || !String(element.textContent || '').trim()) return false
  if (!DIRECT_TEXT_TAGS.has(element.tagName.toUpperCase())) return false
  if (element.matches?.(STRUCTURAL_SELECTOR) || element.querySelector?.(STRUCTURAL_SELECTOR)) return false

  const children = [...(element.children || [])].filter((child) => !child.hasAttribute('data-a12-editor-artifact'))
  return children.every((child) => {
    const tag = child.tagName?.toUpperCase()
    if (!INLINE_CHILD_TAGS.has(tag) || child.matches?.(STRUCTURAL_SELECTOR)) return false
    if (tag === 'BR') return true
    const display = String(child.ownerDocument?.defaultView?.getComputedStyle(child)?.display || '').toLowerCase()
    return display.includes('inline') || display === 'contents'
  })
}

export const shouldCommitLandPptInlineEdit = (editingElement, eventTarget) => Boolean(
  editingElement
  && eventTarget
  && eventTarget !== editingElement
  && !editingElement.contains(eventTarget),
)

export const placeLandPptCaret = (element, event) => {
  const document = element?.ownerDocument
  const selection = document?.getSelection?.()
  if (!document || !selection) return
  try {
    const pointRange = event && document.caretRangeFromPoint?.(event.clientX, event.clientY)
    const range = pointRange && element.contains(pointRange.startContainer)
      ? pointRange
      : document.createRange()
    if (range !== pointRange) {
      range.selectNodeContents(element)
      range.collapse(false)
    }
    selection.removeAllRanges()
    selection.addRange(range)
  } catch {
    element.focus?.()
  }
}

export const serializeLandPptEditableDocument = (document) => {
  const root = document?.documentElement?.cloneNode(true)
  if (!root) return ''

  root.querySelectorAll([
    '#a12-html-drag-style',
    '.a12-html-editor-overlay',
    '.a12-html-element-proxy',
    '[data-a12-editor-artifact]',
  ].join(',')).forEach((element) => element.remove())

  root.querySelectorAll('[data-a12-drag-selected]').forEach((element) => {
    element.removeAttribute('data-a12-drag-selected')
  })
  root.querySelectorAll('[data-a12-html-editing],[contenteditable="true"]').forEach((element) => {
    element.removeAttribute('data-a12-html-editing')
    element.removeAttribute('contenteditable')
    element.removeAttribute('spellcheck')
  })
  return `<!DOCTYPE html>\n${root.outerHTML}`
}
