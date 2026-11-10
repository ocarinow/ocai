import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/integration',
  testMatch: 'console.spec.ts',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:3100', browserName: 'chromium' },
  webServer: [
    {
      command: 'uv run --directory services/gateway --frozen python -m app.main',
      url: 'http://127.0.0.1:8000/health/live', reuseExistingServer: false,
    },
    {
      command: 'node apps/console/.output/server/index.mjs',
      env: { PORT: '3100', HOST: '127.0.0.1', NUXT_GATEWAY_BASE_URL: 'http://127.0.0.1:8000' },
      url: 'http://127.0.0.1:3100', reuseExistingServer: false,
    },
  ],
})
