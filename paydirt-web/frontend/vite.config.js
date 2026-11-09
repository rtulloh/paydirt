import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { backendPort, frontendPort } from './e2e/ports.js'

export default defineConfig({
  plugins: [react()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        // Match Uvicorn's default IPv4 listener even when localhost resolves to ::1.
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://localhost:${backendPort}`,
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.{test,spec}.{js,jsx,mjs}'],
    testTimeout: 30000,
  },
})
