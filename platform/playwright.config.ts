import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/integration',
  testMatch: 'console.spec.ts',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:3100', browserName: 'chromium' },
  webServer: [
    {
      command: 'uv run --directory services/gateway --frozen uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --no-access-log --no-proxy-headers',
      url: 'http://127.0.0.1:8100/health/live', reuseExistingServer: false,
    },
    {
      command: 'node apps/console/.output/server/index.mjs',
      env: { PORT: '3100', HOST: '127.0.0.1', NUXT_GATEWAY_BASE_URL: 'http://127.0.0.1:8100' },
      url: 'http://127.0.0.1:3100', reuseExistingServer: false,
    },
  ],
})
