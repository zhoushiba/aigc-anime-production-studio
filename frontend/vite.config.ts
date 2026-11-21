import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// hash 路由不需要服务端回退配置，base 用相对路径方便静态托管与截图
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    // 与 tsconfig.json 的 paths 保持一致，否则 Rollup 无法解析 "@/..." 别名
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1600
  }
})
