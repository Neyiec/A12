import rdkitWasmUrl from '@rdkit/rdkit/RDKit_minimal.wasm?url'

const renderCache = new Map()
let rdkitPromise

const sourceFor = (data = {}) => {
  const molfile = String(data?.molfile || '').trim()
  if (molfile) return { format: 'molfile', value: molfile }
  const smiles = String(data?.smiles || '').trim()
  if (smiles) return { format: 'smiles', value: smiles }
  return null
}

const normalizeFontSize = (value) => {
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? Math.max(10, Math.min(96, parsed)) : 24
}

const cacheKeyFor = (source, fontSize = 24) => source ? `${source.format}\u0000${source.value}\u0000${normalizeFontSize(fontSize)}` : ''

const moleculeRenderKey = (data = {}, fontSize = 24) => `${chemicalStructureKey(data)}:${normalizeFontSize(fontSize)}`

const styleableSvg = (source = '') => String(source || '')
  .replace(/^\s*<\?xml[^>]*\?>\s*/i, '')
  // RDKit includes an opaque white canvas even with clearBackground enabled.
  // Remove that canvas so the molecule shows the subject tool's own background.
  .replace(/<rect\b(?=[^>]*\bstyle=['"][^'"]*\bfill\s*:\s*#(?:fff|ffffff)\b[^'"]*\bstroke\s*:\s*none)[^>]*>[\s\S]*?<\/rect>/i, '')
  // Inherit the chemical formula's foreground color for atom labels and bonds.
  .replace(/(\b(?:fill|stroke)\s*:\s*)#[\da-f]{3,8}\b/gi, '$1currentColor')
  .replace(/(\b(?:fill|stroke)\s*=\s*['"])#[\da-f]{3,8}(['"])/gi, '$1currentColor$2')
  .replace(/<svg\b/, '<svg class="a12-subject-tool__molecule-svg"')
  .replace(/\bwidth=(['"])[^'"]*\1/i, 'width="100%"')
  .replace(/\bheight=(['"])[^'"]*\1/i, 'height="100%"')

export const chemicalStructureKey = (data = {}) => {
  const source = sourceFor(data)
  if (!source) return ''
  const value = cacheKeyFor(source)
  let first = 2166136261
  let second = 2246822519
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    first = Math.imul(first ^ code, 16777619)
    second = Math.imul(second ^ code, 3266489917)
  }
  return `${source.format}-${value.length}-${(first >>> 0).toString(36)}-${(second >>> 0).toString(36)}`
}

export const cachedChemicalStructure = (data = {}, options = {}) => {
  const source = sourceFor(data)
  return source ? renderCache.get(cacheKeyFor(source, options.fontSize)) || null : null
}

export const chemicalStructureDataUrl = (svg) => svg
  ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  : ''

const loadRdkit = () => {
  if (!rdkitPromise) {
    rdkitPromise = import('@rdkit/rdkit').then(({ default: initRDKitModule }) => initRDKitModule({
      locateFile: (path) => path.endsWith('.wasm') ? rdkitWasmUrl : path,
    }))
  }
  return rdkitPromise
}

export const prepareChemicalStructure = async (data = {}, options = {}) => {
  const source = sourceFor(data)
  if (!source) return null

  const fontSize = normalizeFontSize(options.fontSize)
  const key = cacheKeyFor(source, fontSize)
  const cached = renderCache.get(key)
  if (cached) return cached

  let molecule = null
  try {
    const rdkit = await loadRdkit()
    molecule = rdkit.get_mol(source.value)
    if (!molecule || !molecule.is_valid()) {
      throw new Error('invalid molecule')
    }
    const svg = molecule.get_svg_with_highlights(JSON.stringify({
      clearBackground: true,
      fontFile: 'BuiltinRobotoRegular',
      baseFontSize: 0.6 * (fontSize / 24),
    }))
    if (!svg || !svg.includes('<svg')) throw new Error('empty molecule drawing')
    const result = { svg: styleableSvg(svg), error: '' }
    renderCache.set(key, result)
    return result
  } catch {
    const error = source.format === 'molfile'
      ? 'Molfile 解析失败，请检查结构数据'
      : 'SMILES 解析失败，请检查结构编码'
    const result = { svg: '', error }
    renderCache.set(key, result)
    return result
  } finally {
    molecule?.delete?.()
  }
}

export const chemicalStructureImageUrl = (data = {}) => chemicalStructureDataUrl(cachedChemicalStructure(data)?.svg)

export const renderChemicalStructure = async (target, data = {}) => {
  const source = sourceFor(data)
  if (!target || !source) return

  const key = chemicalStructureKey(data)
  if (target.dataset.a12ChemicalKey !== key) return
  const chemical = target.closest?.('.a12-subject-tool__chemical') || target
  const view = target.ownerDocument?.defaultView
  const fontSize = normalizeFontSize(view?.getComputedStyle?.(chemical)?.fontSize)
  const renderKey = moleculeRenderKey(data, fontSize)
  if (target.dataset.a12ChemicalRenderedKey === renderKey) return
  if (target.dataset.a12ChemicalPendingKey === renderKey) return
  target.dataset.a12ChemicalPendingKey = renderKey

  try {
    const result = await prepareChemicalStructure(data, { fontSize })
    if (!target.isConnected || target.dataset.a12ChemicalKey !== key) return

    const doc = target.ownerDocument || document
    target.replaceChildren()
    if (result?.svg) {
      const Parser = doc.defaultView?.DOMParser || DOMParser
      const parsed = new Parser().parseFromString(result.svg, 'image/svg+xml')
      const drawing = parsed.documentElement
      drawing.setAttribute('role', 'img')
      drawing.setAttribute('aria-label', '分子结构')
      target.appendChild(doc.importNode(drawing, true))
    } else {
      const message = doc.createElement('span')
      message.className = 'a12-subject-tool__molecule-error'
      message.setAttribute('role', 'status')
      message.textContent = result?.error || '分子结构暂时无法显示'
      target.appendChild(message)
    }
    target.dataset.a12ChemicalRenderedKey = renderKey
  } finally {
    if (target.dataset.a12ChemicalPendingKey === renderKey) delete target.dataset.a12ChemicalPendingKey
  }
}
