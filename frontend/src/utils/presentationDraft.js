const DRAFT_KEY_PREFIX = 'a12:presentation-draft:'

const getDraftKey = (sessionId) => `${DRAFT_KEY_PREFIX}${encodeURIComponent(String(sessionId || ''))}`

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
