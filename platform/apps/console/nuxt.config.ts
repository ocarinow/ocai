export default defineNuxtConfig({
  extends: ['@ocarinow/nuxt-platform'],
  compatibilityDate: '2026-11-10',
  devtools: { enabled: false },
  runtimeConfig: { gatewayBaseUrl: 'http://127.0.0.1:8000' },
  app: {
    head: {
      title: 'Ocarinow · Gateway',
      htmlAttrs: { lang: 'en' },
      meta: [{ name: 'description', content: 'Ocarinow AI platform console' }],
    },
  },
  routeRules: { '/api/**': { headers: { 'cache-control': 'no-store' } } },
  typescript: { strict: true },
})
