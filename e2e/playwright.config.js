import { defineConfig, devices } from '@playwright/test'

const frontendUrl = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5173'
const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8000'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: frontendUrl,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm --prefix ../frontend run dev -- --host 127.0.0.1 --port 5173',
    url: frontendUrl,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_API_BASE_URL: backendUrl,
      VITE_WS_URL: backendUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
