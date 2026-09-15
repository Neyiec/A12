import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const defaultApiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8088'
  const javaApiProxyTarget = env.VITE_JAVA_API_PROXY_TARGET || defaultApiProxyTarget

  return {
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    plugins: [vue(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        // 开发与生产均使用正式接口；开发时这里只负责转发，不再承载模型调用。
        '/api': {
          target: javaApiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
