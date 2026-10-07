import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createServer } from 'vite'

test('学科组件离线渲染：公式、化学式、流程图和完整函数坐标图', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { subjectToolMarkup } = await server.ssrLoadModule('/src/utils/subjectTool.js')
    const formula = subjectToolMarkup({ subjectType: 'math_formula', data: { latex: 'y=x^2', display_mode: true } })
    assert.match(formula, /katex/)
    assert.doesNotMatch(formula, /<script|<iframe/)
    assert.match(subjectToolMarkup({ subjectType: 'chemical_formula', data: { formula: 'H2O' } }), /<sub/)
    assert.match(subjectToolMarkup({ subjectType: 'mermaid_diagram', data: { mermaid: 'flowchart LR\nA[输入] --> B[输出]' } }), /<svg/)
    const xs = Array.from({ length: 41 }, (_, i) => (i - 20) / 4)
    const graph = subjectToolMarkup({ subjectType: 'chart', data: { option: {
      a12_function_graph: true, xAxis: { name: 'x', data: xs }, yAxis: { name: 'y' },
      series: [{ type: 'line', data: xs.map(x => x * x) }],
    } } })
    assert.match(graph, /函数坐标图/)
    assert.equal((graph.match(/<circle/g) || []).length, 41)
    assert.match(graph, />5<\/text>/)
    assert.match(graph, />0<\/text>/)
  } finally {
    await server.close()
  }
})
