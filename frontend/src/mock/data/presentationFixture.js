/**
 * 固定的 HTML PPT 测试样例。
 *
 * 该文件只用于开发环境的工作台联调：加载它不会请求大模型，也不会消耗
 * DeepSeek API。页面保留多个可选中、可拖拽和可缩放的 HTML 元素，便于
 * 反复验证工作台编辑能力。
 */

const commonStyles = `
  :root{--ink:#17233b;--muted:#65748d;--accent:#4d64d8;--line:#dfe5ef;--soft:#f4f7fb;--paper:#ffffff}
  *{box-sizing:border-box}
  html,body{width:1280px;height:720px;margin:0;overflow:hidden}
  body{font-family:"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif;color:var(--ink);background:var(--paper)}
  .slide{position:relative;width:1280px;height:720px;padding:58px 68px;overflow:hidden;background:var(--paper)}
  .slide.dark{--ink:#f5f7ff;--muted:#b9c6e5;--line:rgba(255,255,255,.18);--soft:rgba(255,255,255,.08);--paper:#101936;color:var(--ink);background:#101936}
  .eyebrow{position:relative;z-index:1;margin:0 0 24px;color:var(--accent);font-size:16px;font-weight:700;letter-spacing:.12em}
  h1,h2,h3,p{position:relative;z-index:1}
  h1{margin:0;font-size:46px;line-height:1.18;letter-spacing:-.04em}
  h2{margin:0;font-size:34px;line-height:1.2;letter-spacing:-.03em}
  h3{margin:0;font-size:23px;line-height:1.35}
  p{margin:0;font-size:19px;line-height:1.7}
  .lead{max-width:650px;margin-top:18px;color:var(--muted);font-size:22px;line-height:1.65}
  .footer{position:absolute;right:68px;bottom:30px;left:68px;z-index:2;display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:14px}
  .footer strong{color:var(--accent);font-size:15px}
  .rule{position:relative;z-index:1;width:76px;height:5px;margin:26px 0;background:var(--accent)}
  .stack{position:relative;z-index:1;display:grid;gap:14px}
  .card{position:relative;z-index:1;border:1px solid var(--line);border-radius:18px;background:var(--soft)}
  .card p{color:var(--muted);font-size:17px;line-height:1.55}
  .split{position:relative;z-index:1;display:grid;grid-template-columns:1fr 1fr;gap:46px;align-items:center;margin-top:38px}
  .number{display:inline-grid;place-items:center;width:38px;height:38px;margin-right:12px;border-radius:12px;color:#fff;background:var(--accent);font-size:16px;font-weight:700}
  .tag{display:inline-flex;align-items:center;padding:8px 14px;border-radius:999px;color:var(--accent);background:color-mix(in srgb,var(--accent) 12%,transparent);font-size:15px;font-weight:700}
  .cover-title{max-width:700px;margin-top:52px;font-size:68px}
  .cover-subtitle{max-width:620px;margin-top:22px;color:var(--muted);font-size:24px}
  .cover-meta{position:absolute;right:68px;bottom:82px;display:grid;gap:12px;min-width:250px;padding:20px 22px;border-left:4px solid var(--accent);background:rgba(255,255,255,.07);font-size:17px}
  .cover-meta span{color:var(--muted)}
  .agenda-list{display:grid;gap:14px;margin-top:42px}
  .agenda-item{display:grid;grid-template-columns:82px 1fr;align-items:center;gap:18px;padding:17px 22px;border-bottom:1px solid var(--line)}
  .agenda-item b{color:var(--accent);font:700 22px/1 var(--zh-font-number,"Segoe UI",sans-serif)}
  .agenda-item span{font-size:22px}
  .knowledge-list{display:grid;gap:18px}
  .knowledge-item{display:grid;grid-template-columns:58px 1fr;gap:16px;align-items:start;padding:18px 20px;border-left:4px solid var(--accent);background:var(--soft)}
  .knowledge-item strong{display:block;margin-bottom:6px;font-size:22px}
  .knowledge-item p{font-size:17px}
  .callout{padding:28px 30px;border-radius:20px;background:#eef2ff}
  .callout strong{display:block;margin-bottom:16px;color:var(--accent);font-size:23px}
  .callout p{color:#52637f;font-size:18px}
  .experiment{display:grid;place-items:center;min-height:330px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(145deg,#f5f8ff,#edf2ff)}
  .experiment svg{width:390px;height:260px}
  .experiment-label{margin-top:14px;color:var(--muted);font-size:16px;text-align:center}
  .evidence-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:36px;align-items:stretch;margin-top:38px}
  .bars{display:flex;align-items:end;justify-content:space-around;height:300px;padding:26px 26px 22px;border-bottom:2px solid var(--line);background:var(--soft)}
  .bar{display:flex;flex-direction:column;align-items:center;justify-content:end;width:74px;height:100%;gap:10px}
  .bar i{display:block;width:42px;min-height:32px;border-radius:12px 12px 0 0;background:linear-gradient(180deg,var(--accent),#9ca9ef);font-style:normal}
  .bar b{font-size:17px}
  .evidence-note{display:flex;flex-direction:column;justify-content:center;padding:30px;border-left:4px solid var(--accent);background:var(--soft)}
  .evidence-note strong{margin-bottom:16px;color:var(--accent);font-size:24px}
  .evidence-note p{color:var(--muted);font-size:18px}
  .interaction-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:44px}
  .interaction-card{min-height:210px;padding:24px;border-radius:20px;background:var(--soft)}
  .interaction-card .tag{margin-bottom:24px}
  .interaction-card p{margin-top:12px;color:var(--muted);font-size:17px}
  .summary{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:48px}
  .summary .card{min-height:190px;padding:26px}
  .summary .card b{display:block;margin-bottom:16px;color:var(--accent);font:700 34px/1 var(--zh-font-number,"Segoe UI",sans-serif)}
  .summary .card strong{display:block;margin-bottom:10px;font-size:21px}
  .summary .card p{font-size:16px}
  .task-list{display:grid;gap:16px;margin-top:44px;max-width:740px}
  .task{display:grid;grid-template-columns:34px 1fr;gap:15px;align-items:center;padding:18px 20px;border:1px solid var(--line);border-radius:16px;background:var(--soft)}
  .task i{width:24px;height:24px;border:2px solid var(--accent);border-radius:7px}
  .task span{font-size:20px}
  .closing-mark{position:absolute;right:68px;bottom:106px;display:grid;place-items:center;width:220px;height:220px;border:1px solid rgba(255,255,255,.22);border-radius:50%;color:var(--accent);font-size:72px;font-weight:700;transform:rotate(-8deg)}
`

const wrapSlide = (content, { page, title, dark = false, accent = '#4d64d8', notes = '' } = {}) => ({
  slide_no: page,
  title,
  html: `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=1280,height=720"><style>${commonStyles}</style></head><body><main class="slide${dark ? ' dark' : ''}" style="--accent:${accent}">${content}<footer class="footer"><strong>A12 智能备课</strong><span>素白风 · ${String(page).padStart(2, '0')} / 08</span></footer></main></body></html>`,
  notes,
  metadata: { theme: '素白风', source: 'frontend-test-fixture', fixture: true },
})
const fixtureSlides = [
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-cover-eyebrow">八年级生物 · 探究课</p>
    <h1 class="cover-title" data-ppt-element="fixture-cover-title">光合作用</h1>
    <p class="cover-subtitle" data-ppt-element="fixture-cover-subtitle">从一个问题出发，观察植物如何把光能转化为生命所需的能量。</p>
    <div class="rule" data-ppt-element="fixture-cover-rule"></div>
    <div class="cover-meta" data-ppt-element="fixture-cover-meta"><span>核心问题</span><strong>绿叶为什么需要阳光？</strong><span>课堂任务 · 观察 · 解释 · 迁移</span></div>
  `, { page: 1, title: '光合作用', dark: true, accent: '#7c8cf2', notes: '固定测试样例封面：用于验证 HTML 页面选中、拖拽和缩放。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-agenda-eyebrow">01 / 先提出问题</p>
    <h1 data-ppt-element="fixture-agenda-title">我们要用证据回答三个问题</h1>
    <div class="agenda-list">
      <div class="agenda-item" data-ppt-element="fixture-agenda-item-1"><b>01</b><span>植物制造的有机物从哪里来？</span></div>
      <div class="agenda-item" data-ppt-element="fixture-agenda-item-2"><b>02</b><span>光照和叶片在过程中分别起什么作用？</span></div>
      <div class="agenda-item" data-ppt-element="fixture-agenda-item-3"><b>03</b><span>如何把实验现象组织成一个可靠结论？</span></div>
    </div>
  `, { page: 2, title: '问题链', accent: '#5368d8', notes: '固定测试样例目录页。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-knowledge-eyebrow">02 / 知识讲解</p>
    <h1 data-ppt-element="fixture-knowledge-title">光合作用是一场能量转换</h1>
    <div class="split">
      <div class="knowledge-list" data-ppt-element="fixture-knowledge-list">
        <div class="knowledge-item" data-ppt-element="fixture-knowledge-item-1"><span class="number">1</span><div><strong>吸收光能</strong><p>叶绿体中的色素捕获光能，为后续反应提供动力。</p></div></div>
        <div class="knowledge-item" data-ppt-element="fixture-knowledge-item-2"><span class="number">2</span><div><strong>合成有机物</strong><p>二氧化碳和水在光照条件下参与物质合成。</p></div></div>
        <div class="knowledge-item" data-ppt-element="fixture-knowledge-item-3"><span class="number">3</span><div><strong>释放氧气</strong><p>反应过程中会产生氧气，成为可观察的线索。</p></div></div>
      </div>
      <div class="callout" data-ppt-element="fixture-knowledge-callout"><strong>一句话抓住核心</strong><p>绿色植物利用光能，把二氧化碳和水转化成储存能量的有机物，并释放氧气。</p><div class="rule"></div><p>光能 → 化学能</p></div>
    </div>
  `, { page: 3, title: '知识讲解', accent: '#4d64d8', notes: '固定测试样例知识讲解页。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-experiment-eyebrow">03 / 实验观察</p>
    <h1 data-ppt-element="fixture-experiment-title">先看现象，再解释现象</h1>
    <div class="split">
      <div class="experiment" data-ppt-element="fixture-experiment-visual">
        <div>
          <svg viewBox="0 0 390 260" role="img" aria-label="叶片与光照示意图" data-ppt-element="fixture-experiment-svg"><circle cx="210" cy="125" r="67" fill="#cdebdc" stroke="#4d9a71" stroke-width="4"/><path d="M210 184C176 156 165 119 181 87c36 4 62 25 67 59-8 17-21 30-38 38Z" fill="#77bf8e"/><path d="M210 184V82" stroke="#fff" stroke-width="4" stroke-linecap="round"/><path d="M64 60h82M82 95h56M70 130h64" stroke="#e0ad44" stroke-width="9" stroke-linecap="round"/><path d="M142 60l-22-15M142 60l-13 20M138 95l-20-15M138 95l-11 18" stroke="#e0ad44" stroke-width="4" stroke-linecap="round"/></svg>
          <div class="experiment-label" data-ppt-element="fixture-experiment-label">光照、叶片与淀粉检验</div>
        </div>
      </div>
      <div class="stack" data-ppt-element="fixture-experiment-observations">
        <div class="card" style="padding:24px" data-ppt-element="fixture-experiment-card-1"><h3>观察</h3><p>见光部分出现蓝色，遮光部分没有明显变化。</p></div>
        <div class="card" style="padding:24px" data-ppt-element="fixture-experiment-card-2"><h3>推断</h3><p>光照可能影响有机物的形成，需要排除其他变量。</p></div>
        <div class="card" style="padding:24px" data-ppt-element="fixture-experiment-card-3"><h3>下一步</h3><p>把“现象—证据—结论”写成完整的实验解释。</p></div>
      </div>
    </div>
  `, { page: 4, title: '实验观察', accent: '#3d9b71', notes: '固定测试样例实验页，包含 SVG 与卡片元素。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-evidence-eyebrow">04 / 证据整理</p>
    <h1 data-ppt-element="fixture-evidence-title">证据越清楚，结论越可靠</h1>
    <div class="evidence-grid">
      <div class="bars" data-ppt-element="fixture-evidence-chart"><div class="bar"><i style="height:42%"></i><b>遮光</b></div><div class="bar"><i style="height:74%"></i><b>见光</b></div><div class="bar"><i style="height:90%"></i><b>充分光照</b></div><div class="bar"><i style="height:58%"></i><b>弱光</b></div></div>
      <div class="evidence-note" data-ppt-element="fixture-evidence-note"><strong>把数据转成语言</strong><p>见光组的淀粉检验反应更明显，说明光照是光合作用的重要条件之一。</p><div class="rule"></div><p>不要只说“有变化”，要说明变化意味着什么。</p></div>
    </div>
  `, { page: 5, title: '证据整理', accent: '#d28a3f', notes: '固定测试样例数据页。图表数据仅用于前端编辑测试。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-interaction-eyebrow">05 / 课堂互动</p>
    <h1 data-ppt-element="fixture-interaction-title">用三分钟完成一轮小组推理</h1>
    <div class="interaction-grid">
      <div class="interaction-card" data-ppt-element="fixture-interaction-card-1"><span class="tag">观察者</span><h3>你看到了什么？</h3><p>只描述可见现象，不急着解释原因。</p></div>
      <div class="interaction-card" data-ppt-element="fixture-interaction-card-2"><span class="tag">证据员</span><h3>什么支持你的判断？</h3><p>指出实验对照和最关键的变化。</p></div>
      <div class="interaction-card" data-ppt-element="fixture-interaction-card-3"><span class="tag">表达者</span><h3>结论怎样说更准确？</h3><p>用“条件—过程—结果”组织一句话。</p></div>
    </div>
    <p style="margin-top:34px;color:var(--muted);font-size:18px" data-ppt-element="fixture-interaction-tip">提示：先独立写下判断，再与同伴交换证据。</p>
  `, { page: 6, title: '课堂互动', accent: '#886bd5', notes: '固定测试样例互动页。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-summary-eyebrow">06 / 形成理解</p>
    <h1 data-ppt-element="fixture-summary-title">一页记住光合作用的逻辑</h1>
    <div class="summary">
      <div class="card" data-ppt-element="fixture-summary-card-1"><b>01</b><strong>输入</strong><p>二氧化碳 + 水 + 光能</p></div>
      <div class="card" data-ppt-element="fixture-summary-card-2"><b>02</b><strong>过程</strong><p>叶绿体完成能量转换与物质合成</p></div>
      <div class="card" data-ppt-element="fixture-summary-card-3"><b>03</b><strong>输出</strong><p>有机物 + 氧气</p></div>
    </div>
    <div class="callout" style="margin-top:26px;padding:19px 24px" data-ppt-element="fixture-summary-callout"><p>真正的理解，不是背下定义，而是能用证据解释现象。</p></div>
  `, { page: 7, title: '课堂小结', accent: '#4d64d8', notes: '固定测试样例总结页。' }),
  wrapSlide(`
    <p class="eyebrow" data-ppt-element="fixture-task-eyebrow">07 / 课后迁移</p>
    <h1 data-ppt-element="fixture-task-title">把今天的推理带回生活</h1>
    <p class="lead" data-ppt-element="fixture-task-lead">选择一片常见植物，设计一个小观察，记录你想验证的条件与证据。</p>
    <div class="task-list" data-ppt-element="fixture-task-list">
      <div class="task" data-ppt-element="fixture-task-1"><i></i><span>写出一个可检验的问题</span></div>
      <div class="task" data-ppt-element="fixture-task-2"><i></i><span>说明你准备观察的变量</span></div>
      <div class="task" data-ppt-element="fixture-task-3"><i></i><span>用三句话写下证据与结论</span></div>
    </div>
    <div class="closing-mark" data-ppt-element="fixture-task-mark">光</div>
  `, { page: 8, title: '课后任务', dark: true, accent: '#7c8cf2', notes: '固定测试样例收束页。' }),
]

export const createPresentationFixture = () => ({
  presentation_id: 'ppt_fixture_photosynthesis_20260902',
  title: '光合作用：从现象到证据',
  slide_count: fixtureSlides.length,
  slides: fixtureSlides.map((slide) => ({ ...slide })),
  html: fixtureSlides.map((slide) => slide.html).join('\n'),
  metadata: {
    theme: '素白风',
    source: 'frontend-test-fixture',
    fixture: true,
    label: '固定测试样例',
    model: 'not-generated',
  },
})
