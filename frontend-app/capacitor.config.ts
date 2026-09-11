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
}

export default config
