export const isAndroidApp = () => window.Capacitor?.getPlatform?.() === 'android'

export function resolveDownloadUrl(value) {
  const apiBase = new URL(import.meta.env.VITE_API_BASE_URL || '/', window.location.origin)
  const url = new URL(value, apiBase)
  // Locally signed resource links can advertise the backend's loopback address.
  if (url.pathname.startsWith('/api/v1/storage/local-object') &&
      ['localhost', '127.0.0.1'].includes(url.hostname) &&
      isAndroidApp() && import.meta.env.VITE_API_BASE_URL) {
    return new URL(url.pathname + url.search, apiBase)
  }
  return url
}

export function isBackendDownload(url) {
  const apiBase = new URL(import.meta.env.VITE_API_BASE_URL || '/', window.location.origin)
  return url.origin === apiBase.origin && url.pathname.startsWith('/api/v1/')
}

export async function saveAndroidDownload(url, filename, authorization) {
  const plugin = window.Capacitor?.Plugins?.A12FileDownload
  if (!plugin) throw new Error('请更新 App 后再保存文件')
  try {
    await plugin.save({ url: String(url), filename, authorization })
    return true
  } catch (error) {
    if (error?.code === 'CANCELLED') return false
    throw error
  }
}
