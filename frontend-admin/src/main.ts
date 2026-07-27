/**
 * [数据交互说明]
 * - 依赖:
 *   - `./router`: Vue Router 路由实例
 *   - `./App.vue`: 根组件
 *   - `element-plus`: UI 组件库
 *   - `pinia`: 全局状态管理
 *   - `pinia-plugin-persistedstate`: Pinia 持久化插件（localStorage）
 * - 输出: 挂载整个 Vue 应用到 `#app`
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import { createPinia } from 'pinia'
// Pinia 持久化插件 — 自动将 store 状态同步到 localStorage
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

const app = createApp(App)
const pinia = createPinia()

// 注册持久化插件，使 defineStore 中的 persist 选项生效
pinia.use(piniaPluginPersistedstate)

app.use(router)
app.use(ElementPlus)
app.use(pinia)

app.mount('#app')
