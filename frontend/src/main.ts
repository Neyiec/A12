/**
 * [数据交互说明]
 * - 依赖:
 *   - `./router`: Vue Router 路由实例
 *   - `./App.vue`: 根组件
 *   - `element-plus`: UI 组件库
 *   - `pinia`: 全局状态管理
 *   - `pinia-plugin-persistedstate`: Pinia 持久化插件（localStorage）
 *   - `../mock/browser`: MSW Mock Service Worker（本地演示模式可显式启用）
 * - 输出: 挂载整个 Vue 应用到 `#app`
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'markstream-vue/index.css'
import './style.css'
import './mobile-ui.css'
import './mobile-system.css'
import { createPinia } from 'pinia'
// Pinia 持久化插件 — 自动将 store 状态同步到 localStorage
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

/**
 * 启动 Vue 应用
 * 在显式启用本地演示模式时先启动 MSW mock worker，再挂载应用
 */
async function bootstrap() {
  // 本地演示模式用 MSW 返回模拟 API 数据，不连接 Java/Python 后端。
  const mockApiEnabled = import.meta.env.VITE_ENABLE_MOCK_API === 'true'
  if (mockApiEnabled) {
    const { startMockWorker } = await import('./mock/browser.ts')
    await startMockWorker()
  }

  const app = createApp(App)
  const pinia = createPinia()

  // 注册持久化插件，使 defineStore 中的 persist 选项生效
  pinia.use(piniaPluginPersistedstate)

  app.use(pinia)

  // 预览页需要先在 MSW 中建立 mock 会话，再挂载路由和发起页面请求。
  if (mockApiEnabled && (import.meta.env.MODE === 'mock' || window.location.hash.includes('preview=1'))) {
    const { ensureDevelopmentPreviewSession } = await import('./utils/previewSession.js')
    await ensureDevelopmentPreviewSession()
  }

  app.use(router)
  app.use(ElementPlus, { locale: zhCn })

  app.mount('#app')
}

bootstrap()
