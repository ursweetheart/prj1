import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import projectImageSizes from './vite-plugins/projectImageSizes.js'

// Dev: the AI API runs on :8001 (cd backend && python -m uvicorn api:app --port 8001 --env-file .env)
const api = 'http://localhost:8001'

export default defineConfig({
  base: '/prj1/',
  plugins: [vue(), projectImageSizes()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': { target: api, rewrite: p => p.replace(/^\/api/, '') },
      '/images': api
    }
  }
})
