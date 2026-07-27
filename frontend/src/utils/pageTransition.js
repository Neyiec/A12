/**
 * 登录成功后的原点扩散转场。
 * 由点击位置扩散覆盖，在路由更新完成后向上收回。
 */
const EXPAND_DURATION = 400
const RETRACT_DURATION = 450

const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export async function startPageTransition({ sourceEvent, onCovered }) {
  if (prefersReducedMotion()) {
    await onCovered?.()
    return
  }

  const overlay = document.getElementById('pageTransitionOverlay')
  if (!overlay) {
    await onCovered?.()
    return
  }

  const x = Number.isFinite(sourceEvent?.clientX) && sourceEvent.clientX > 0 ? sourceEvent.clientX : window.innerWidth / 2
  const y = Number.isFinite(sourceEvent?.clientY) && sourceEvent.clientY > 0 ? sourceEvent.clientY : window.innerHeight / 2
  const color = getComputedStyle(document.documentElement).getPropertyValue('--zh-background-button').trim() || '#2563eb'

  overlay.style.setProperty('--click-x', `${x}px`)
  overlay.style.setProperty('--click-y', `${y}px`)
  overlay.style.setProperty('--transition-color', color)
  overlay.className = 'ui-page-transition'
  void overlay.offsetWidth
  overlay.classList.add('is-expanding')

  await new Promise((resolve) => window.setTimeout(resolve, EXPAND_DURATION))
  await onCovered?.()
  overlay.classList.remove('is-expanding')
  overlay.classList.add('is-retracting-slide-up')

  await new Promise((resolve) => window.setTimeout(resolve, RETRACT_DURATION))
  overlay.className = 'ui-page-transition'
  overlay.style.removeProperty('--click-x')
  overlay.style.removeProperty('--click-y')
  overlay.style.removeProperty('--transition-color')
}
