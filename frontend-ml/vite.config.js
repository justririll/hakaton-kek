import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5180,
    // Бэкенд поднимается на 8010; прокси избавляет фронтенд от CORS и
    // от знания адреса API в коде компонентов.
    proxy: { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true } },
  },
})
