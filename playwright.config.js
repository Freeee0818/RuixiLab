import { defineConfig } from '@playwright/test'

const port = process.env.PLAYWRIGHT_PORT || '5173'
const useDevServer = process.env.PLAYWRIGHT_USE_DEV === 'true'
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  fullyParallel: false,
  reporter: 'line',
  use: {
    baseURL,
    channel: 'msedge',
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `node node_modules/vite/bin/vite.js ${useDevServer ? '' : 'preview'} --host 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: !process.env.PLAYWRIGHT_PORT,
    timeout: 120_000,
  },
})
