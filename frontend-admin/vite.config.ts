import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    plugins: [vue(), tailwindcss()],
    server: {
      port: 8888,
      fs: {
        // 审核页复用教师端的只读社区预览组件。
        allow: [fileURLToPath(new URL('..', import.meta.url))],
      },
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET,
          changeOrigin: true
        },
        // '/content': {
        //   target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL,
        //   changeOrigin: true,
        //   rewrite: (path) => path
        // }
      }
    }
  }
})