export function communityLoadError(error) {
  const status = error?.response?.status
  if (error?.request && !error.response || [502, 503, 504].includes(status)
    || status === 500 && !error?.response?.data?.message) {
    return '社区服务暂时不可用，请确认 Java 后端已启动（默认端口 8088），再点击重试'
  }
  return error?.response?.data?.message || error?.message || '社区内容加载失败，请重试'
}
