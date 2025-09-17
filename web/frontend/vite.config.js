import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Load environment variables from root directory
  // envDir: path.resolve(__dirname, '../..'),
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000/',
        changeOrigin: true,
      },
    },
  },
})