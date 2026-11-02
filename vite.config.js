import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import projectImageSizes from './vite-plugins/projectImageSizes.js'

// Dev: the AI API runs on :8001 (cd backend && python -m uvicorn api:app --port 8001 --env-file .env)
const api = 'http://localhost:8001'

// GitHub Pages không biết các đường dẫn của Vue Router (/du-an/<slug>…): mở thẳng hay F5
// sẽ ra 404. Chép index.html thành 404.html để Pages trả về app, router lo phần còn lại.
const spaFallback = () => {
  let outDir = 'dist'
  return {
    name: 'spa-404-fallback',
    apply: 'build',
    configResolved(c) { outDir = path.resolve(c.root, c.build.outDir) },
    closeBundle() { fs.copyFileSync(path.join(outDir, 'index.html'), path.join(outDir, '404.html')) }
  }
}

export default defineConfig({
  base: '/prj1/',
  plugins: [vue(), projectImageSizes(), spaFallback()],
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
