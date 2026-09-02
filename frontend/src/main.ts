/**
 * [数据交互说明]
 * - 依赖:
 *   - `./router`: Vue Router 路由实例
 *   - `./App.vue`: 根组件
 *   - `element-plus`: UI 组件库
 *   - `pinia`: 全局状态管理
 *   - `pinia-plugin-persistedstate`: Pinia 持久化插件（localStorage）
 *   - `../mock/browser`: MSW Mock Service Worker（仅 DEV 模式）
 * - 输出: 挂载整个 Vue 应用到 `#app`
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'markstream-vue/index.css'
import './style.css'
import { createPinia } from 'pinia'
// Pinia 持久化插件 — 自动将 store 状态同步到 localStorage
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

/**
 * 启动 Vue 应用
 * 在 DEV 模式下先启动 MSW mock worker，再挂载应用
 */
async function bootstrap() {
  // 开发模式下启动 MSW Mock Service Worker，拦截 API 请求
  // if (import.meta.env.DEV) {
  //   const { startMockWorker } = await import('./mock/browser.ts')
  //   await startMockWorker()
  // }

  const app = createApp(App)
  const pinia = createPinia()

  // 注册持久化插件，使 defineStore 中的 persist 选项生效
  pinia.use(piniaPluginPersistedstate)

  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)

  // 预览或工作台自动导出入口都先建立 mock 会话，避免跳转后因鉴权失败而静默没有任务。
  // if (import.meta.env.DEV && (window.location.hash.includes('preview=1') || window.location.hash.includes('autoExport=1'))) {
  //   try {
  //     const { ensureDevelopmentPreviewSession } = await import('./utils/previewSession.js')
  //     await ensureDevelopmentPreviewSession()
  //   } catch (error) {
  //     console.error('[preview] mock 登录失败:', error)
  //   }
  // }

  app.mount('#app')
}

bootstrap()
