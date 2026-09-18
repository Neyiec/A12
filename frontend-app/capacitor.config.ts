import type { CapacitorConfig } from '@capacitor/cli'

/**
 * A12 教师端 App 原生壳配置
 * [数据交互说明]
 * - 依赖:   `../frontend` 的 Vite 构建产物（dist/）
 * - 输入:   webDir 指向 ../frontend/dist，`cap sync` 时复制进 android/ios 原生工程
 * - 说明:   本工程只承担原生壳职责（打包、插件、热更新），Web 源码全部在 ../frontend
 */
const config: CapacitorConfig = {
  appId: 'com.a12.teacher',
  appName: 'A12',
  webDir: '../frontend/dist',
  server: {
    // androidScheme 默认 https：HTTPS 页面请求 http://IP:8088 会被 Chromium Mixed Content 策略拦截。
    // 改为 http 后页面 origin 为 http://localhost，真机联调直连明文 API 不再构成混合内容；
    // 注意：origin 变化会使旧 localStorage 失效（未发布阶段无影响），CORS 白名单需同步含 http://localhost
    androidScheme: 'http',
    // 允许访问明文 HTTP（Android 9+ 系统层默认禁止，需配合 AndroidManifest 的 usesCleartextTraffic）
    cleartext: true,
  },
}

export default config
