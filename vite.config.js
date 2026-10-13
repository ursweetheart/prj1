import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Dev: the AI API runs on :8000 (uvicorn api:app, started from backend/: cd backend && uvicorn api:app)
const api = 'http://localhost:8000'

export default defineConfig({
  base: '/prj1/',
  plugins: [vue()],
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
