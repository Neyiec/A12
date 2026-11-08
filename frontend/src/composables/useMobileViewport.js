import { onBeforeUnmount, ref } from 'vue'

// Retain the mobile layout in landscape without treating a narrow desktop window as a phone.
const mobileViewportQuery = '(max-width: 767.98px) and (hover: none) and (pointer: coarse), (max-width: 1023.98px) and (max-height: 600px) and (hover: none) and (pointer: coarse)'

export function isMobileViewport() {
  return window.matchMedia(mobileViewportQuery).matches
}

export function useMobileViewport() {
  const media = window.matchMedia(mobileViewportQuery)
  const isMobile = ref(media.matches)
  const update = event => { isMobile.value = event.matches }
  media.addEventListener('change', update)
  onBeforeUnmount(() => media.removeEventListener('change', update))
  return isMobile
}
