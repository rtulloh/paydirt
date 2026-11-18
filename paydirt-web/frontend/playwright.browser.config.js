import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e-browser',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 600_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://127.0.0.1:18733/paydirt/',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1100 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npx vite preview --host 127.0.0.1 --port 18733 --strictPort --outDir dist-browser --base /paydirt/',
    url: 'http://127.0.0.1:18733/paydirt/',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
