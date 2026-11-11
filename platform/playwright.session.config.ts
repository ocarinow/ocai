import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/session', testMatch: '*.spec.ts', workers: 1,
  timeout: 120000, expect: { timeout: 10000 },
  use: { browserName: 'chromium', trace: 'off', screenshot: 'off', video: 'off' },
  reporter: 'list',
})
