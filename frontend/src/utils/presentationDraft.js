const DRAFT_KEY_PREFIX = 'a12:presentation-draft:'
const OUTLINE_DRAFT_KEY_PREFIX = 'a12:outline-draft:'

const getDraftKey = (sessionId) => `${DRAFT_KEY_PREFIX}${encodeURIComponent(String(sessionId || ''))}`
const getOutlineDraftKey = (sessionId) => `${OUTLINE_DRAFT_KEY_PREFIX}${encodeURIComponent(String(sessionId || ''))}`

export const readPresentationDraft = (sessionId) => {
  if (!sessionId || typeof window === 'undefined' || !window.sessionStorage) return null

  try {
    const raw = window.sessionStorage.getItem(getDraftKey(sessionId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const savePresentationDraft = (sessionId, payload) => {
  if (!sessionId || typeof window === 'undefined' || !window.sessionStorage) return false

  try {
    window.sessionStorage.setItem(getDraftKey(sessionId), JSON.stringify(payload))
    return true
  } catch {
    return false
  }
}

/**
 * 备课大纲的本地快照。
 * 真实大纲流使用 Python 会话存储，而当前开发环境的 Java 会话仍是 mock，
 * 因此在同一浏览器会话中保留一份快照，供工作台读取并继续生成 HTML PPT。
 */
export const readOutlineDraft = (sessionId) => {
  if (!sessionId || typeof window === 'undefined' || !window.sessionStorage) return null

  try {
    const raw = window.sessionStorage.getItem(getOutlineDraftKey(sessionId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const saveOutlineDraft = (sessionId, payload) => {
  if (!sessionId || typeof window === 'undefined' || !window.sessionStorage) return false

  try {
    window.sessionStorage.setItem(getOutlineDraftKey(sessionId), JSON.stringify(payload))
    return true
  } catch {
    return false
  }
}
