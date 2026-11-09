import { defineConfig } from '@playwright/test'
import { backendPort, backendURL, frontendPort, frontendURL } from './e2e/ports.js'

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: frontendURL,
    browserName: 'chromium',
    viewport: { width: 1440, height: 1100 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `python3 e2e/serve_backend.py --port ${backendPort}`,
      url: `${backendURL}/api/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --host localhost --port ${frontendPort} --strictPort`,
      url: frontendURL,
      env: { VITE_API_BASE: frontendURL },
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})
