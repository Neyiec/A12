/**
 * 判断token是否过期
 * @param {*} token 传入token 
 * @returns {boolean} true:过期  false:未过期
 */
export function isTokenExpired(token) {
    // 解析token
    // 获取payload(基于base64编码)
    const raw_payload = token.split('.')[1];
    // 解码payload为json字符串
    const json_PayLoad = window.atob(raw_payload);
    // 解析json字符串为对象
    const payload = JSON.parse(json_PayLoad);
    // 将exp这个秒级时间戳和Date.now()的毫秒级时间戳对比
    if(payload.exp * 1000 < Date.now()){
        return true;
    }else{
        return false;
    }
}