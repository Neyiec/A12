const textContent = (value) => {
  if (typeof value === 'string') return value
  if (!Array.isArray(value)) return ''
  return value.map((part) => typeof part === 'string' ? part : String(part?.text || '')).join('')
}

/** 读取 Java 网关转发的 OpenAI 兼容 SSE，并保留上游 error 事件。 */
export async function readOpenAiTextStream(response, onDelta, onEvent, options = {}) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('模型没有返回可读取的数据流')

  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = 'message'
  let dataLines = []
  let content = ''

  const dispatch = () => {
    const data = dataLines.join('\n').trim()
    const type = eventName
    eventName = 'message'
    dataLines = []
    if (!data || data === '[DONE]') return

    let payload
    try {
      payload = JSON.parse(data)
    } catch {
      if (type === 'error') throw new Error(data)
      return
    }
    if (type === 'error' || payload?.error) {
      throw new Error(payload?.message || payload?.error?.message || '对话模型调用失败，请稍后重试')
    }
    if (type !== 'message') {
      onEvent?.(type, payload)
      return
    }
    const delta = textContent(payload?.choices?.[0]?.delta?.content ?? payload?.choices?.[0]?.message?.content)
    if (delta) {
      content += delta
      onDelta?.(delta, content)
    }
  }

  const consumeLine = (line) => {
    if (!line) return dispatch()
    if (line.startsWith('event:')) eventName = line.slice(6).trim() || 'message'
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    let newlineIndex
    while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newlineIndex).replace(/\r$/, '')
      buffer = buffer.slice(newlineIndex + 1)
      consumeLine(line)
    }
    if (done) break
  }
  if (buffer) consumeLine(buffer.replace(/\r$/, ''))
  dispatch()
  if (!content.trim() && !options.allowEmpty) throw new Error('模型未返回有效内容')
  return content
}
