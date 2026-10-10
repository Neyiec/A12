// OSS 错误是 XML，不能当成普通 JSON 接口错误处理。
export function resourceUploadError(error) {
  const body = typeof error?.response?.data === 'string' ? error.response.data : ''
  const code = body.match(/<Code>\s*([^<]+)\s*<\/Code>/)?.[1]?.trim()
  const messages = {
    NoSuchBucket: '上传存储桶不存在，请管理员检查 OSS 的 bucket-name 与 endpoint 地域配置',
    AccessDenied: '上传被存储服务拒绝，请管理员检查 OSS 上传权限',
    InvalidAccessKeyId: '上传服务凭证无效，请管理员检查 OSS AccessKey 配置',
    SignatureDoesNotMatch: '上传签名校验失败，请管理员检查 OSS 签名配置与文件类型',
    RequestTimeTooSkewed: '上传签名时间异常，请校准服务器时间后重试',
  }
  if (messages[code]) return messages[code]
  if (!error?.response) return '无法连接上传服务，请检查网络及 OSS 跨域配置后重试'
  return `文件传输失败（HTTP ${error.response.status || '未知'}），请重试或联系管理员`
}
