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
    // 不使用代理，直接从前端调用后端API
    // 后端已配置CORS，可以直接跨域请求
  }
  }
})
