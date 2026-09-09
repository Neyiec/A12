// srcdoc 中的 H5 默认是不受信任内容。该策略只允许内联教学交互和 data/blob 素材，
// 阻断联网、外部脚本、表单提交与对象嵌入；服务端校验会给出更明确的拒绝原因。
export const SANDBOX_CONTENT_SECURITY_POLICY = "default-src 'none'; base-uri 'none'; object-src 'none'; frame-src about: data: blob:; form-action 'none'; connect-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; media-src data: blob:; font-src data:"

const cspMeta = () => `<meta http-equiv="Content-Security-Policy" content="${SANDBOX_CONTENT_SECURITY_POLICY}">`

export const secureHtmlForSandbox = (source) => {
  const html = String(source || '').trim()
  if (!html) return ''
  const withoutExistingPolicy = html.replace(
    /<meta\b[^>]*http-equiv\s*=\s*(['"]?)content-security-policy\1[^>]*>/gi,
    ''
  )
  if (/<head\b[^>]*>/i.test(withoutExistingPolicy)) {
    return withoutExistingPolicy.replace(/(<head\b[^>]*>)/i, `$1${cspMeta()}`)
  }
  if (/<html\b[^>]*>/i.test(withoutExistingPolicy)) {
    return withoutExistingPolicy.replace(/(<html\b[^>]*>)/i, `$1<head>${cspMeta()}</head>`)
  }
  return `<!doctype html><html><head>${cspMeta()}</head><body>${withoutExistingPolicy}</body></html>`
}
