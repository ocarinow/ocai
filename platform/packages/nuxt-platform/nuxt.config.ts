import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  runtimeConfig: { session: { enabled: false, local: false, origin: '', issuer: '', clientId: '', clientSecret: '', databaseUrl: '', activeKey: '', keys: '' } },
  extends: ['@ocarinow/nuxt-ui'],
  css: [fileURLToPath(new URL('./app/assets/css/theme.css', import.meta.url))],
})
