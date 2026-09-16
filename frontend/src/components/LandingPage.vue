<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, ChatDotRound, Check, Download, EditPen, Files, MagicStick, Menu } from '@element-plus/icons-vue'
import { getCurrentUser } from '../apis/login.js'
import { useUserStore } from '../storage/user.js'
import { isSessionExpired } from '../utils/JWTParser.js'

const router = useRouter()
const userStore = useUserStore()
const entering = ref(false)

/** 移动端锚点菜单：平滑滚动到对应区块 */
const scrollToSection = (command) => {
  const target = document.querySelector(command)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}


/** 先确认 12 小时本地会话，再由后端确认令牌没有被异地登录替换。 */
const enterProgram = async () => {
  if (entering.value) return

  if (!userStore.token || isSessionExpired(userStore.token, userStore.loginAt)) {
    userStore.clearUser()
    await router.push('/login')
    return
  }

  entering.value = true
  try {
    const result = await getCurrentUser()
    if (result?.code !== 0 && result?.code !== 200) {
      ElMessage.error(result?.message || '登录状态验证失败，请稍后重试')
      return
    }
    await router.push('/main')
  } catch (error) {
    // 401 会由请求拦截器清理令牌并跳转登录；网络异常则留在官网页，方便重试。
    if (userStore.token) ElMessage.error('暂时无法验证登录状态，请检查后端服务或网络连接')
  } finally {
    entering.value = false
  }
}
</script>

<template>
  <div class="landing-page">
    <header class="site-header">
      <a class="brand" href="#top" aria-label="智核首页">
        <span class="brand-logo-frame" aria-hidden="true">
          <img class="brand-logo-image" src="/branding/logo-intro.png" alt="" />
        </span>
        <span>智核</span>
      </a>

      <nav class="site-nav" aria-label="官网导航">
        <a href="#features">核心能力</a>
        <a href="#workflow">使用流程</a>
        <a href="#results">教学成果</a>
      </nav>

      <!-- 移动端/平板锚点导航（<1024px 显示，替代被隐藏的 site-nav） -->
      <el-dropdown
        class="site-nav-mobile"
        trigger="click"
        @command="scrollToSection"
      >
        <button class="header-action site-nav-mobile-trigger" type="button" aria-label="打开导航菜单">
          <el-icon><Menu /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="#features">核心能力</el-dropdown-item>
            <el-dropdown-item command="#workflow">使用流程</el-dropdown-item>
            <el-dropdown-item command="#results">教学成果</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <button class="header-action" type="button" :disabled="entering" @click="enterProgram">
        {{ entering ? '正在进入' : '进入程序' }}
        <el-icon><ArrowRight /></el-icon>
      </button>
    </header>

    <main id="top">
      <section class="hero-section" aria-labelledby="hero-title">
        <div class="hero-copy">
          <div class="eyebrow">
            <el-icon><MagicStick /></el-icon>
            面向教师的 AI 创作工作台
          </div>
          <h1 id="hero-title">把每一个教学想法，<br /><span>变成精彩课堂。</span></h1>
          <p class="hero-description">
            从一句主题到完整课件、教案与互动活动。智核把备课所需的资料、灵感和制作流程放进一个工作空间。
          </p>
          <div class="hero-actions">
            <button class="primary-action" type="button" :disabled="entering" @click="enterProgram">
              {{ entering ? '正在进入' : '开始使用' }}
              <el-icon><ArrowRight /></el-icon>
            </button>
            <a class="secondary-action" href="#features">了解核心能力</a>
          </div>
          <ul class="hero-proof" aria-label="产品特点">
            <li><el-icon><Check /></el-icon>多模态资料理解</li>
            <li><el-icon><Check /></el-icon>课件与教案协同生成</li>
            <li><el-icon><Check /></el-icon>成果随时编辑导出</li>
          </ul>
        </div>

        <div class="hero-visual" aria-label="智核 AI 教学创作场景">
          <div class="visual-halo"></div>
          <div class="visual-card">
            <img src="/智核品牌插图.png" alt="AI 连接知识与课堂的教学创作场景" />
            <div class="visual-overlay">
              <div>
                <span>正在创作</span>
                <strong>勾股定理 · 探究式课堂</strong>
              </div>
              <span class="progress-pill">8 页课件</span>
            </div>
          </div>
          <div class="floating-note note-top">
            <span class="note-icon">✦</span>
            <div><small>AI 教学设计</small><strong>大纲已生成</strong></div>
          </div>
          <div class="floating-note note-bottom">
            <span class="note-icon note-icon-gold">✓</span>
            <div><small>课堂成果</small><strong>可编辑 · 可导出</strong></div>
          </div>
        </div>
      </section>

      <section id="features" class="content-section features-section" aria-labelledby="features-title">
        <div class="section-heading">
          <span>一个工作空间，完成整套备课</span>
          <h2 id="features-title">让 AI 真正进入教学流程</h2>
          <p>不是生成一段文字就结束，而是把资料理解、教学设计、内容制作和成果交付连成一条清晰路径。</p>
        </div>

        <div class="feature-grid">
          <article class="feature-card feature-card-wide">
            <div class="feature-icon"><el-icon><ChatDotRound /></el-icon></div>
            <div class="feature-copy">
              <span>对话式教学设计</span>
              <h3>像与教研伙伴交流一样梳理课堂</h3>
              <p>补充学科、年级和教学目标，智核会主动澄清关键信息，再形成结构完整的课程大纲。</p>
            </div>
            <div class="chat-preview" aria-hidden="true">
              <div class="chat-bubble chat-user">为七年级设计一节光合作用探究课</div>
              <div class="chat-bubble chat-ai"><span>智</span>建议从叶片实验导入，并加入一个预测—观察—解释活动。</div>
            </div>
          </article>

          <article class="feature-card">
            <div class="feature-icon"><el-icon><Files /></el-icon></div>
            <span>多模态资料理解</span>
            <h3>已有资料也能成为创作起点</h3>
            <p>上传 PDF、Word 和文本资料，从你的教学内容中提取重点，减少重复整理。</p>
            <div class="file-stack" aria-hidden="true">
              <div><b>PDF</b><span>课程标准.pdf</span><em>已解析</em></div>
              <div><b>DOC</b><span>单元教案.docx</span><em>已关联</em></div>
            </div>
          </article>

          <article class="feature-card feature-card-blue">
            <div class="feature-icon feature-icon-light"><el-icon><EditPen /></el-icon></div>
            <span>可编辑的生成结果</span>
            <h3>课件、教案与互动活动一起完成</h3>
            <p>每一页都能继续修改，既保留生成效率，也让最终成果符合你的课堂习惯。</p>
            <div class="slide-miniature" aria-hidden="true">
              <small>03 / 08</small>
              <strong>探索勾股定理</strong>
              <div><i></i><i></i><i></i></div>
            </div>
          </article>
        </div>
      </section>

      <section id="workflow" class="workflow-section" aria-labelledby="workflow-title">
        <div class="workflow-inner">
          <div class="workflow-copy">
            <span class="section-kicker">从想法到成果</span>
            <h2 id="workflow-title">三步进入你的创作节奏</h2>
            <ol class="workflow-list">
              <li>
                <span>01</span>
                <div><h3>告诉智核你要教什么</h3><p>输入主题、对象和目标，也可以加入已有资料。</p></div>
              </li>
              <li>
                <span>02</span>
                <div><h3>确认结构并继续完善</h3><p>通过对话调整课程大纲、内容重点和互动方式。</p></div>
              </li>
              <li>
                <span>03</span>
                <div><h3>编辑并交付课堂成果</h3><p>统一管理课件、教案和资源，完成后直接导出。</p></div>
              </li>
            </ol>
          </div>

          <div class="workflow-canvas" aria-label="智核创作工作台示意">
            <div class="canvas-topbar"><span></span><span></span><span></span><b>AI 课程创作</b></div>
            <div class="canvas-body">
              <div class="canvas-sidebar">
                <span class="active"></span><span></span><span></span><span></span>
              </div>
              <div class="canvas-content">
                <small>课程主题</small>
                <h3>勾股定理：从测量到证明</h3>
                <div class="outline-row"><b>01</b><span><strong>情境导入</strong><i></i></span></div>
                <div class="outline-row"><b>02</b><span><strong>动手测量</strong><i></i></span></div>
                <div class="outline-row"><b>03</b><span><strong>归纳与证明</strong><i></i></span></div>
                <div class="canvas-prompt">加入一个适合小组合作的课堂活动 <em>↑</em></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="results" class="content-section results-section" aria-labelledby="results-title">
        <div class="results-panel">
          <div>
            <span class="section-kicker">成果不止停留在页面里</span>
            <h2 id="results-title">备课完成，马上带进课堂</h2>
            <p>统一导出 PPTX、Word 和成果包，保留项目版本，方便继续调整与复用。</p>
          </div>
          <div class="result-types" aria-label="支持导出格式">
            <span><el-icon><Download /></el-icon>PPTX</span>
            <span><el-icon><Download /></el-icon>Word</span>
            <span><el-icon><Download /></el-icon>成果包</span>
          </div>
        </div>
      </section>

      <section class="final-cta" aria-labelledby="cta-title">
        <span>现在，开始准备下一堂课</span>
        <h2 id="cta-title">把时间留给教学，把繁琐交给智核。</h2>
        <button class="primary-action cta-action" type="button" :disabled="entering" @click="enterProgram">
          {{ entering ? '正在进入' : '开始使用' }}
          <el-icon><ArrowRight /></el-icon>
        </button>
      </section>
    </main>

    <footer class="site-footer">
      <a class="brand footer-brand" href="#top">
        <span class="brand-logo-frame" aria-hidden="true">
          <img class="brand-logo-image" src="/branding/logo-intro.png" alt="" />
        </span>
        <span>智核</span>
      </a>
      <p>多模态 AI 互动式教学智能体</p>
      <span>让每一次备课都有清晰的开始</span>
    </footer>
  </div>
</template>

<style scoped>
.landing-page {
  min-height: 100%;
  overflow-x: hidden;
  color: #172033;
  background:
    radial-gradient(circle at 82% 12%, rgb(219 234 254 / 72%), transparent 30rem),
    linear-gradient(180deg, #fbfdff 0%, #fff 72%);
}

.site-header {
  position: relative;
  z-index: 20;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  width: min(1180px, calc(100% - 48px));
  min-height: 82px;
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: 10px;
  color: #172033;
  font-size: 21px;
  font-weight: 750;
  letter-spacing: -.03em;
  text-decoration: none;
}

.brand-logo-frame {
  position: relative;
  display: block;
  flex: 0 0 auto;
  overflow: hidden;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 8px 20px rgb(37 99 235 / 24%);
}

.brand-logo-image {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 68px;
  height: 68px;
  max-width: none;
  object-fit: cover;
  transform: translate(-50%, -50%);
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 34px;
}

.site-nav a {
  color: #596579;
  font-size: 15px;
  font-weight: 550;
  text-decoration: none;
  transition: color 160ms ease;
}

.site-nav a:hover { color: #1d4ed8; }

.header-action,
.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 999px;
  color: white;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
  background: #172033;
  box-shadow: 0 10px 24px rgb(15 23 42 / 14%);
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.header-action:disabled,
.primary-action:disabled {
  cursor: wait;
  opacity: .72;
}

.header-action {
  justify-self: end;
  min-height: 44px;
  padding: 0 20px;
  font-size: 14px;
}

.header-action:hover,
.primary-action:hover {
  background: #2563eb;
  box-shadow: 0 14px 28px rgb(37 99 235 / 22%);
  transform: translateY(-2px);
}

.hero-section {
  display: grid;
  grid-template-columns: minmax(0, .86fr) minmax(480px, 1.14fr);
  align-items: center;
  gap: clamp(44px, 6vw, 90px);
  width: min(1180px, calc(100% - 48px));
  min-height: calc(100vh - 82px);
  margin: 0 auto;
  padding: 54px 0 92px;
}

.hero-copy { position: relative; z-index: 2; }

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding: 8px 13px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 650;
  background: rgb(239 246 255 / 75%);
}

h1 {
  margin: 0;
  color: #121a2b;
  font-size: clamp(48px, 5vw, 74px);
  font-weight: 760;
  letter-spacing: -.065em;
  line-height: 1.08;
}

h1 span {
  color: transparent;
  background: linear-gradient(100deg, #1d4ed8 4%, #3b82f6 52%, #0ea5e9 100%);
  background-clip: text;
  -webkit-background-clip: text;
}

.hero-description {
  max-width: 600px;
  margin: 26px 0 0;
  color: #647087;
  font-size: 18px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 34px;
}

.primary-action {
  min-height: 54px;
  padding: 0 27px;
  font-size: 16px;
  background: #2563eb;
}

.secondary-action {
  display: inline-flex;
  min-height: 54px;
  align-items: center;
  padding: 0 24px;
  border: 1px solid #dce3ee;
  border-radius: 999px;
  color: #344056;
  font-size: 15px;
  font-weight: 620;
  text-decoration: none;
  background: rgb(255 255 255 / 70%);
  transition: border-color 160ms ease, background 160ms ease;
}

.secondary-action:hover { border-color: #93c5fd; background: white; }

.hero-proof {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 22px;
  margin: 30px 0 0;
  padding: 0;
  color: #657087;
  font-size: 13px;
  list-style: none;
}

.hero-proof li { display: inline-flex; align-items: center; gap: 5px; }
.hero-proof .el-icon { color: #2563eb; }

.hero-visual { position: relative; min-width: 0; padding: 38px 0; }
.visual-halo {
  position: absolute;
  inset: 8% 4%;
  border-radius: 50%;
  background: #60a5fa;
  filter: blur(80px);
  opacity: .22;
}

.visual-card {
  position: relative;
  overflow: hidden;
  aspect-ratio: 1.27;
  border: 8px solid rgb(255 255 255 / 82%);
  border-radius: 32px;
  background: #0c2c76;
  box-shadow: 0 38px 90px rgb(30 64 175 / 24%), 0 8px 28px rgb(15 23 42 / 12%);
  transform: perspective(1100px) rotateY(-4deg) rotateX(1deg);
}

.visual-card img { width: 100%; height: 100%; object-fit: cover; }
.visual-card::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(180deg, transparent 52%, rgb(4 18 57 / 88%) 100%);
}

.visual-overlay {
  position: absolute;
  z-index: 2;
  right: 24px;
  bottom: 22px;
  left: 24px;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  color: white;
}

.visual-overlay div { display: grid; gap: 3px; }
.visual-overlay span { color: rgb(255 255 255 / 66%); font-size: 12px; }
.visual-overlay strong { font-size: 16px; font-weight: 650; }
.progress-pill { padding: 7px 11px; border: 1px solid rgb(255 255 255 / 22%); border-radius: 999px; background: rgb(255 255 255 / 12%); backdrop-filter: blur(8px); }

.floating-note {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 176px;
  padding: 13px 15px;
  border: 1px solid rgb(255 255 255 / 80%);
  border-radius: 17px;
  background: rgb(255 255 255 / 88%);
  box-shadow: 0 18px 45px rgb(30 64 175 / 16%);
  backdrop-filter: blur(16px);
}

.floating-note div { display: grid; gap: 2px; }
.floating-note small { color: #8390a5; font-size: 11px; }
.floating-note strong { color: #233047; font-size: 13px; }
.note-icon { display: grid; width: 33px; height: 33px; place-items: center; border-radius: 10px; color: white; background: #2563eb; }
.note-icon-gold { background: #f59e0b; }
.note-top { top: 2px; right: -24px; }
.note-bottom { bottom: 0; left: -34px; }

.content-section {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 108px 0;
}

.section-heading { max-width: 720px; margin-bottom: 48px; }
.section-heading > span,
.section-kicker {
  color: #2563eb;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .08em;
}

.section-heading h2,
.workflow-copy h2,
.results-panel h2,
.final-cta h2 {
  margin: 12px 0 0;
  color: #152036;
  font-size: clamp(36px, 4vw, 54px);
  line-height: 1.18;
  letter-spacing: -.045em;
}

.section-heading p,
.results-panel p {
  margin: 18px 0 0;
  color: #6b768a;
  font-size: 17px;
  line-height: 1.8;
}

.feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.feature-card {
  position: relative;
  overflow: hidden;
  min-height: 430px;
  padding: 34px;
  border: 1px solid #e5eaf1;
  border-radius: 28px;
  background: #f8fafc;
}

.feature-card-wide {
  display: grid;
  grid-template-columns: .8fr 1.2fr;
  grid-column: 1 / -1;
  align-items: center;
  gap: 44px;
  min-height: 390px;
  background: linear-gradient(135deg, #f5f9ff, #eef5ff);
}

.feature-copy { max-width: 460px; }
.feature-icon {
  display: grid;
  width: 46px;
  height: 46px;
  margin-bottom: 66px;
  place-items: center;
  border-radius: 14px;
  color: #2563eb;
  font-size: 22px;
  background: #e4efff;
}

.feature-card-wide .feature-icon { position: absolute; top: 34px; left: 34px; margin: 0; }
.feature-card > span,
.feature-copy > span { color: #2563eb; font-size: 13px; font-weight: 700; }
.feature-card h3,
.feature-copy h3 {
  max-width: 500px;
  margin: 10px 0 0;
  color: #18233a;
  font-size: clamp(25px, 2.4vw, 35px);
  line-height: 1.28;
  letter-spacing: -.035em;
}

.feature-card p,
.feature-copy p { margin: 14px 0 0; color: #6b768a; font-size: 15px; line-height: 1.75; }
.chat-preview { display: grid; gap: 14px; padding: 28px; border: 1px solid #dbe7fa; border-radius: 22px; background: rgb(255 255 255 / 80%); box-shadow: 0 20px 55px rgb(37 99 235 / 10%); }
.chat-bubble { max-width: 88%; padding: 14px 16px; border-radius: 16px; color: #40506a; font-size: 14px; line-height: 1.6; }
.chat-user { justify-self: end; color: white; background: #2563eb; border-bottom-right-radius: 5px; }
.chat-ai { display: flex; gap: 10px; background: #eef2f8; border-bottom-left-radius: 5px; }
.chat-ai span { display: grid; flex: 0 0 auto; width: 25px; height: 25px; place-items: center; border-radius: 8px; color: white; font-size: 11px; background: #172033; }
.file-stack { position: absolute; right: 34px; bottom: 34px; left: 34px; display: grid; gap: 10px; }
.file-stack div { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; padding: 15px; border: 1px solid #e4e9f0; border-radius: 14px; background: white; box-shadow: 0 10px 24px rgb(15 23 42 / 5%); }
.file-stack b { color: #2563eb; font-size: 11px; }
.file-stack span { color: #344056; font-size: 14px; }
.file-stack em { color: #789083; font-size: 12px; font-style: normal; }
.feature-card-blue { color: white; border-color: transparent; background: linear-gradient(145deg, #1e40af, #2563eb 60%, #3b82f6); }
.feature-card-blue > span, .feature-card-blue h3 { color: white; }
.feature-card-blue p { color: rgb(255 255 255 / 72%); }
.feature-icon-light { color: white; background: rgb(255 255 255 / 14%); }
.slide-miniature { position: absolute; right: 34px; bottom: 0; left: 34px; min-height: 150px; padding: 24px; border: 1px solid rgb(255 255 255 / 26%); border-bottom: 0; border-radius: 18px 18px 0 0; background: rgb(255 255 255 / 14%); box-shadow: 0 -12px 40px rgb(11 31 93 / 20%); backdrop-filter: blur(10px); }
.slide-miniature small { color: rgb(255 255 255 / 60%); }
.slide-miniature strong { display: block; margin-top: 15px; font-size: 20px; }
.slide-miniature div { display: flex; gap: 8px; margin-top: 22px; }
.slide-miniature i { display: block; width: 24%; height: 6px; border-radius: 8px; background: rgb(255 255 255 / 28%); }
.slide-miniature i:first-child { width: 44%; background: #fbbf24; }

.workflow-section { padding: 34px 24px; background: #111a2d; }
.workflow-inner { display: grid; grid-template-columns: .76fr 1.24fr; align-items: center; gap: 80px; width: min(1180px, 100%); min-height: 700px; margin: 0 auto; }
.workflow-copy h2 { color: white; }
.workflow-list { display: grid; gap: 0; margin: 40px 0 0; padding: 0; list-style: none; }
.workflow-list li { display: grid; grid-template-columns: 48px 1fr; gap: 17px; padding: 20px 0; border-top: 1px solid rgb(255 255 255 / 10%); }
.workflow-list li > span { color: #60a5fa; font-size: 13px; font-weight: 700; }
.workflow-list h3 { margin: 0; color: white; font-size: 17px; }
.workflow-list p { margin: 6px 0 0; color: rgb(255 255 255 / 55%); font-size: 14px; line-height: 1.6; }
.workflow-canvas { overflow: hidden; border: 1px solid rgb(255 255 255 / 13%); border-radius: 25px; background: #f8fafc; box-shadow: 0 30px 80px rgb(0 0 0 / 34%); transform: rotate(1.5deg); }
.canvas-topbar { display: flex; align-items: center; gap: 7px; height: 48px; padding: 0 18px; border-bottom: 1px solid #e8ecf2; background: white; }
.canvas-topbar span { width: 8px; height: 8px; border-radius: 50%; background: #dce3ec; }
.canvas-topbar b { margin-left: 8px; color: #7b8798; font-size: 11px; font-weight: 600; }
.canvas-body { display: grid; grid-template-columns: 56px 1fr; min-height: 480px; }
.canvas-sidebar { display: flex; flex-direction: column; align-items: center; gap: 18px; padding-top: 28px; border-right: 1px solid #e8ecf2; background: #f0f4f9; }
.canvas-sidebar span { width: 23px; height: 23px; border-radius: 7px; background: #dce4ef; }
.canvas-sidebar span.active { background: #2563eb; box-shadow: 0 7px 16px rgb(37 99 235 / 26%); }
.canvas-content { padding: 38px 42px; }
.canvas-content > small { color: #8591a4; font-size: 12px; }
.canvas-content > h3 { margin: 7px 0 30px; color: #19253b; font-size: 25px; }
.outline-row { display: grid; grid-template-columns: 34px 1fr; gap: 14px; margin-top: 12px; padding: 16px; border: 1px solid #e6ebf2; border-radius: 13px; background: white; }
.outline-row b { color: #2563eb; font-size: 12px; }
.outline-row span { display: grid; gap: 8px; }
.outline-row strong { color: #3d4960; font-size: 13px; }
.outline-row i { display: block; width: 72%; height: 5px; border-radius: 8px; background: #edf0f5; }
.canvas-prompt { display: flex; align-items: center; justify-content: space-between; margin-top: 24px; padding: 14px 16px; border: 1px solid #bfdbfe; border-radius: 13px; color: #60708a; font-size: 13px; background: #eff6ff; }
.canvas-prompt em { display: grid; width: 27px; height: 27px; place-items: center; border-radius: 8px; color: white; font-style: normal; background: #2563eb; }

.results-section { padding-bottom: 50px; }
.results-panel { display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 40px; padding: 55px; border: 1px solid #e4eaf2; border-radius: 30px; background: linear-gradient(135deg, #f8fbff, #f2f7ff); }
.results-panel h2 { max-width: 680px; font-size: clamp(34px, 3.5vw, 48px); }
.results-panel p { max-width: 650px; font-size: 16px; }
.result-types { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 9px; }
.result-types span { display: inline-flex; align-items: center; gap: 7px; padding: 11px 14px; border: 1px solid #dae3ef; border-radius: 999px; color: #40506a; font-size: 13px; font-weight: 650; background: white; }
.result-types .el-icon { color: #2563eb; }

.final-cta { display: flex; flex-direction: column; align-items: center; width: min(920px, calc(100% - 48px)); margin: 70px auto 120px; text-align: center; }
.final-cta > span { color: #2563eb; font-size: 14px; font-weight: 700; }
.final-cta h2 { max-width: 820px; }
.cta-action { margin-top: 32px; }
.site-footer { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 24px; width: min(1180px, calc(100% - 48px)); min-height: 118px; margin: 0 auto; border-top: 1px solid #e8ecf2; color: #8a95a7; font-size: 13px; }
.footer-brand .brand-logo-frame { width: 32px; height: 32px; border-radius: 10px; }
.footer-brand .brand-logo-image { width: 57px; height: 57px; }
.site-footer p { margin: 0; }
.site-footer > span { justify-self: end; }

/* 移动端锚点菜单触发按钮：默认隐藏，<1024px 显示 */
.site-nav-mobile { display: none; }

@media (max-width: 1023.98px) {
  .site-header { grid-template-columns: 1fr auto; }
  .site-nav { display: none; }
  .site-nav-mobile {
    display: inline-flex;
    justify-self: end;
    margin-right: 10px;
  }
  .site-nav-mobile-trigger {
    min-width: 44px;
    min-height: 44px;
    padding: 0;
    justify-content: center;
  }
  .hero-section { grid-template-columns: 1fr; padding-top: 72px; }
  .hero-copy { max-width: 720px; text-align: center; margin: 0 auto; }
  .hero-description { margin-right: auto; margin-left: auto; }
  .hero-actions, .hero-proof { justify-content: center; }
  .hero-visual { width: min(720px, 100%); margin: 0 auto; }
  .feature-card-wide { grid-template-columns: 1fr; padding-top: 108px; }
  .workflow-inner { grid-template-columns: 1fr; gap: 45px; padding: 80px 0; }
  .results-panel { grid-template-columns: 1fr; align-items: start; }
  .result-types { justify-content: flex-start; }
}

@media (max-width: 767.98px) {
  .site-header, .hero-section { width: min(100% - 32px, 1180px); }
  .site-header { min-height: 70px; }
  .header-action { min-height: 40px; padding: 0 15px; }
  .hero-section { min-height: auto; padding: 55px 0 72px; }
  h1 { font-size: clamp(40px, 12vw, 58px); }
  .hero-description { font-size: 16px; }
  .hero-actions { flex-direction: column; align-items: stretch; }
  .primary-action, .secondary-action { width: 100%; }
  .hero-proof { display: grid; justify-content: start; width: max-content; max-width: 100%; margin-right: auto; margin-left: auto; text-align: left; }
  .hero-visual { padding: 26px 0; }
  .visual-card { border-width: 5px; border-radius: 22px; transform: none; }
  .visual-overlay { right: 14px; bottom: 14px; left: 14px; }
  .visual-overlay strong { font-size: 13px; }
  .floating-note { display: none; }
  .content-section { width: min(100% - 32px, 1180px); padding: 76px 0; }
  .feature-grid { grid-template-columns: 1fr; }
  .feature-card-wide { grid-column: auto; }
  .feature-card { min-height: 410px; padding: 26px; border-radius: 22px; }
  .feature-card-wide .feature-icon { top: 26px; left: 26px; }
  .chat-preview { padding: 18px; }
  .workflow-section { padding: 0 16px; }
  .workflow-canvas { transform: none; }
  .canvas-content { padding: 28px 20px; }
  .canvas-body { grid-template-columns: 42px 1fr; min-height: 430px; }
  .results-panel { padding: 30px 24px; border-radius: 22px; }
  .final-cta { width: min(100% - 32px, 920px); margin-bottom: 80px; }
  .site-footer { grid-template-columns: 1fr; justify-items: start; width: min(100% - 32px, 1180px); padding: 30px 0; }
  .site-footer > span { justify-self: start; }
}
</style>
