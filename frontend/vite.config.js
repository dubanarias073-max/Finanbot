import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true, // o ['.trycloudflare.com'] para limitarlo al túnel
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/legacy': 'http://127.0.0.1:8000',
      '/images': 'http://127.0.0.1:8000',
    },
  },
})