import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configured for Metal Engine (localhost:8000)
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
      }
    }
  }
})
