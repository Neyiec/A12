import request from './request'

/**
 * 通用 API 调用方法
 * @param {Object} options - 请求配置
 * @param {string} options.url - 请求地址
 * @param {string} [options.method='get'] - 请求方法
 * @param {Object} [options.params] - URL 参数（GET 请求）
 * @param {Object} [options.data] - 请求体数据（POST/PUT 请求）
 * @param {Object} [options.headers] - 自定义请求头
 * @param {number} [options.timeout] - 请求超时时间（毫秒）
 * @returns {Promise}
 */
export function apiRequest(options) {
  return request({
    url: options.url,
    method: options.method || 'get',
    params: options.params,
    data: options.data,
    headers: options.headers,
    responseType: options.responseType,
    timeout: options.timeout
  })
}

/**
 * GET 请求
 * @param {string} url - 请求地址
 * @param {Object} params - URL 参数
 */
export function get(url, params) {
  return request.get(url, { params })
}

/**
 * POST 请求
 * @param {string} url - 请求地址
 * @param {Object} data - 请求体数据
 */
export function post(url, data) {
  return request.post(url, data)
}

/**
 * PUT 请求
 * @param {string} url - 请求地址
 * @param {Object} data - 请求体数据
 */
export function put(url, data) {
  return request.put(url, data)
}

/**
 * DELETE 请求
 * @param {string} url - 请求地址
 */
export function del(url) {
  return request.delete(url)
}

/**
 * 文件下载
 * @param {string} url - 下载地址
 * @param {string} filename - 保存的文件名
 */
export async function downloadFile(url, filename) {
  const response = await request.get(url, {
    responseType: 'blob'
  })
  
  const blob = new Blob([response.data])
  const link = document.createElement('a')
  link.href = window.URL.createObjectURL(blob)
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(link.href)
}

/**
 * 文件上传
 * @param {string} url - 上传地址
 * @param {FormData} formData - 表单数据
 * @param {Function} onProgress - 进度回调函数
 */
export function uploadFile(url, formData, onProgress) {
  return request.post(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        onProgress(percentCompleted)
      }
    }
  })
}
