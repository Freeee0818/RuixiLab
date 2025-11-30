import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  
  return {
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  define: {
    'process.env': {}
  },
  server: {
    proxy: {
      '/api': {
          target: env.VITE_API_BASE_URL_1 || 'http://localhost:8000',
        changeOrigin: true
      },
      '/data-analysis': {
          target: env.VITE_API_BASE_URL_2 || 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/data-analysis/, '/api')
        }
      }
    }
  }
})
