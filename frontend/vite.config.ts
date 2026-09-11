import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5180,
    // Бэкенд слушает 8010; прокси снимает CORS и избавляет код от знания адреса API.
    proxy: { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true } },
  },
  build: { chunkSizeWarningLimit: 900 },
})
