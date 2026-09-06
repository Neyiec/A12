<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  element: { type: Object, default: () => ({}) },
  compact: { type: Boolean, default: false },
})

const parseData = (value) => {
  if (value && typeof value === 'object') return value
  if (typeof value === 'string') {
    try { return JSON.parse(value) || {} } catch { return { description: value } }
  }
  return {}
}

const data = computed(() => parseData(props.element?.data))
const subjectType = computed(() => String(props.element?.subjectType || props.element?.subject_type || data.value.subjectType || data.value.subject_type || 'general').toLowerCase())
const subjectLabel = computed(() => ({
  geometry: '几何探究', math: '数学探究', math_formula: '数学公式', physics: '物理实验', chemistry: '化学结构', chemistry_formula: '化学式', data: '数据分析',
}[subjectType.value] || '学科工具'))

const geometryA = ref(Number(data.value.a || data.value.side_a || 3) || 3)
const geometryB = ref(Number(data.value.b || data.value.side_b || 4) || 4)
const geometryC = computed(() => Math.sqrt(geometryA.value ** 2 + geometryB.value ** 2).toFixed(2))
const geometryRatio = computed(() => Math.max(0.28, Math.min(1.7, geometryA.value / Math.max(1, geometryB.value))))

const physicsMass = ref(Number(data.value.mass || 2) || 2)
const physicsForce = ref(Number(data.value.force || 10) || 10)
const physicsAcceleration = computed(() => (physicsForce.value / Math.max(0.1, physicsMass.value)).toFixed(2))

const chemistryFormula = ref(String(data.value.formula || props.element?.content || 'H₂O'))
const chemistryAtoms = computed(() => {
  const matches = chemistryFormula.value.match(/[A-Z][a-z]?\d*/g) || []
  return matches.map((token) => {
    const match = token.match(/^([A-Z][a-z]?)(\d*)$/)
    return { symbol: match?.[1] || token, count: Number(match?.[2] || 1) }
  })
})
const chemistryAtomCount = computed(() => chemistryAtoms.value.reduce((total, atom) => total + atom.count, 0))

const dataA = ref(Number(data.value.first || data.value.a || 42) || 42)
const dataB = ref(Number(data.value.second || data.value.b || 58) || 58)
const dataTotal = computed(() => Math.max(1, dataA.value + dataB.value))
const dataRatio = computed(() => Math.round((dataA.value / dataTotal.value) * 100))
const checked = ref(false)
</script>

<template>
  <div class="subject-runtime" :class="[`subject-runtime-${subjectType}`, { 'is-compact': compact }]">
    <header class="subject-runtime-header">
      <span class="subject-runtime-kicker">{{ subjectLabel }}</span>
      <strong>{{ element?.name || element?.content || '学科探究工具' }}</strong>
    </header>

    <div v-if="['geometry', 'math', 'math_formula'].includes(subjectType)" class="subject-runtime-body geometry-runtime">
      <svg class="subject-runtime-geometry" viewBox="0 0 180 100" role="img" aria-label="可调参数的直角三角形">
        <path d="M 16 82 L 156 82 L 156 18 Z" />
        <text x="86" y="96">a={{ geometryA.toFixed(1) }}</text>
        <text x="166" y="53">b={{ geometryB.toFixed(1) }}</text>
        <text x="67" y="42">c={{ geometryC }}</text>
      </svg>
      <div class="subject-runtime-controls">
        <label>a <input v-model.number="geometryA" type="range" min="1" max="10" step="0.5" @pointerdown.stop><output>{{ geometryA.toFixed(1) }}</output></label>
        <label>b <input v-model.number="geometryB" type="range" min="1" max="10" step="0.5" @pointerdown.stop><output>{{ geometryB.toFixed(1) }}</output></label>
      </div>
      <p>勾股关系：a² + b² = c² · 斜边 c = {{ geometryC }}</p>
    </div>

    <div v-else-if="subjectType === 'physics'" class="subject-runtime-body physics-runtime">
      <div class="physics-equation"><b>F = ma</b><span>{{ physicsForce }} N ÷ {{ physicsMass }} kg = <strong>{{ physicsAcceleration }} m/s²</strong></span></div>
      <label>力 F <input v-model.number="physicsForce" type="range" min="1" max="30" step="1" @pointerdown.stop><output>{{ physicsForce }} N</output></label>
      <label>质量 m <input v-model.number="physicsMass" type="range" min="0.5" max="10" step="0.5" @pointerdown.stop><output>{{ physicsMass }} kg</output></label>
    </div>

    <div v-else-if="['chemistry', 'chemistry_formula'].includes(subjectType)" class="subject-runtime-body chemistry-runtime">
      <label>化学式 <input v-model="chemistryFormula" type="text" maxlength="24" @pointerdown.stop></label>
      <div class="atom-list"><span v-for="(atom, index) in chemistryAtoms" :key="`${atom.symbol}-${index}`"><b>{{ atom.symbol }}</b><small>×{{ atom.count }}</small></span></div>
      <p>当前结构包含 {{ chemistryAtomCount }} 个原子单位，可在右侧属性中保存公式。</p>
    </div>

    <div v-else-if="subjectType === 'data'" class="subject-runtime-body data-runtime">
      <div class="data-bars"><i :style="{ height: `${Math.max(12, dataRatio)}%` }"><span>A</span></i><i :style="{ height: `${Math.max(12, 100 - dataRatio)}%` }"><span>B</span></i></div>
      <label>A <input v-model.number="dataA" type="range" min="0" max="100" step="1" @pointerdown.stop><output>{{ dataA }}</output></label>
      <label>B <input v-model.number="dataB" type="range" min="0" max="100" step="1" @pointerdown.stop><output>{{ dataB }}</output></label>
      <p>A 占比 {{ dataRatio }}%</p>
    </div>

    <div v-else class="subject-runtime-body general-runtime">
      <p>{{ data.description || element?.content || '该学科工具已加载，可在右侧配置参数。' }}</p>
      <button type="button" :class="{ checked }" @pointerdown.stop @click="checked = !checked">{{ checked ? '已完成探究' : '标记为已探究' }}</button>
    </div>
  </div>
</template>

<style scoped>
.subject-runtime{display:grid;gap:7px;width:100%;height:100%;min-width:0;padding:10px 12px;overflow:hidden;border:1px solid rgb(37 99 235 / 18%);border-radius:10px;color:#27405f;background:linear-gradient(135deg,#f7fbff,#eef5ff);font-size:10px}.subject-runtime-header{display:grid;gap:2px;min-width:0}.subject-runtime-kicker{color:#4d79b5;font-size:9px;font-weight:700;letter-spacing:.08em}.subject-runtime-header strong{overflow:hidden;color:#24456f;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.subject-runtime-body{display:grid;gap:6px;min-height:0}.subject-runtime p{margin:0;color:#607491;font-size:9px;line-height:1.45}.subject-runtime-controls,.physics-runtime label,.chemistry-runtime label,.data-runtime label{display:grid;grid-template-columns:18px minmax(0,1fr) 38px;align-items:center;gap:5px;color:#607491;font-size:9px}.subject-runtime input[type=range]{width:100%;accent-color:#4f83d8}.subject-runtime output{color:#315f9f;font:600 9px var(--zh-font-number)}.subject-runtime-geometry .subject-runtime-geometry{width:100%;height:54px}.subject-runtime-geometry path{fill:none;stroke:#4d83d4;stroke-width:2}.subject-runtime-geometry text{fill:#315f9f;font-size:9px}.physics-equation{display:grid;gap:3px;color:#446482}.physics-equation b{font-size:17px;color:#2563a9}.physics-equation strong{color:#1f8a63}.chemistry-runtime>label{grid-template-columns:50px minmax(0,1fr)}.chemistry-runtime input[type=text]{min-width:0;padding:4px 6px;border:1px solid #c6d7ed;border-radius:5px;color:#27405f;background:#fff;font-size:10px}.atom-list{display:flex;flex-wrap:wrap;gap:5px}.atom-list span{display:inline-flex;align-items:baseline;gap:3px;padding:5px 7px;border-radius:6px;color:#2b5e9f;background:#dceaff}.atom-list b{font-size:12px}.atom-list small{font-size:8px}.data-bars{display:flex;align-items:flex-end;justify-content:center;gap:22px;height:56px;padding:4px 0;border-bottom:1px solid #b9cae0}.data-bars i{position:relative;width:25px;min-height:12px;border-radius:5px 5px 0 0;background:#5d8ed4;font-style:normal}.data-bars i:nth-child(2){background:#8fb0df}.data-bars i span{position:absolute;top:-15px;left:50%;transform:translateX(-50%);color:#315f9f;font-size:9px}.general-runtime{align-content:center}.general-runtime button{justify-self:start;padding:5px 8px;border:1px solid #a7c4e8;border-radius:6px;color:#315f9f;background:#fff;cursor:pointer;font-size:9px}.general-runtime button.checked{color:#fff;background:#4f83d8}
</style>
