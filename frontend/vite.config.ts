import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const defaultApiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8088'
  const javaApiProxyTarget = env.VITE_JAVA_API_PROXY_TARGET || defaultApiProxyTarget
  const pythonApiProxyTarget = env.VITE_PYTHON_API_PROXY_TARGET || 'http://127.0.0.1:8001'

  return {
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    plugins: [vue(), tailwindcss()],
    optimizeDeps: {
      // Lazy workspace imports must be discovered before the first navigation.
      include: ['katex', 'mathlive'],
      force: mode === 'development',
    },
    server: {
      port: 5173,
      proxy: {
        '/api/v1/python': {
          target: pythonApiProxyTarget,
          changeOrigin: true,
        },
        // Java 继续提供登录、会话、项目和资源业务接口。
        '/api': {
          target: javaApiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
