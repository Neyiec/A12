/**
 * 判断token是否过期
 * @param {*} token 传入token 
 * @returns {boolean} true:过期  false:未过期
 */
const SESSION_DURATION_MS = 12 * 60 * 60 * 1000

/** 安全解析 JWT payload，兼容 base64url 编码。 */
export function parseTokenPayload(token) {
    try {
        const rawPayload = String(token || '').split('.')[1]
        if (!rawPayload) return null
        const base64 = rawPayload.replace(/-/g, '+').replace(/_/g, '/')
        const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
        return JSON.parse(window.atob(padded))
    } catch {
        return null
    }
}

/** JWT 无效或已到 exp 时返回 true。旧令牌没有 exp 时交给会话时限判断。 */
export function isTokenExpired(token) {
    const payload = parseTokenPayload(token)
    if (!payload) return true
    return Number.isFinite(payload.exp) && payload.exp * 1000 <= Date.now()
}

/**
 * 判断本地登录会话是否已超过 12 小时。
 * 新会话优先采用服务端签发的 exp；旧令牌则使用本地登录时间或 JWT iat。
 */
export function isSessionExpired(token, loginAt = 0) {
    const payload = parseTokenPayload(token)
    if (!payload || isTokenExpired(token)) return true

    if (Number.isFinite(payload.exp)) return payload.exp * 1000 <= Date.now()

    const startedAt = Number(loginAt) || (Number(payload.iat) * 1000)
    return !Number.isFinite(startedAt) || startedAt <= 0 || Date.now() - startedAt >= SESSION_DURATION_MS
}
