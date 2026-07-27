/**
 * 判断token是否过期
 * @param {*} token 传入token 
 * @returns {boolean} true:过期  false:未过期
 */
export function isTokenExpired(token) {
    if (!token || typeof token !== 'string') {
        return true;
    }
    const parts = token.split('.');
    if (parts.length !== 3) {
        return true;
    }
    try {
        // 获取payload(基于base64编码)，并将 Base64URL 字符替换为标准 Base64 字符
        const raw_payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        // 解码payload为json字符串
        const json_PayLoad = window.atob(raw_payload);
        // 解析json字符串为对象
        const payload = JSON.parse(json_PayLoad);
        if (!payload || !payload.exp) {
            return false;
        }
        // 将exp这个秒级时间戳和Date.now()的毫秒级时间戳对比
        return payload.exp * 1000 < Date.now();
    } catch (e) {
        console.warn('JWT解析异常:', e);
        return true;
    }
}