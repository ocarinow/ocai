import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  extends: ['@ocarinow/nuxt-ui'],
  css: [fileURLToPath(new URL('./app/assets/css/theme.css', import.meta.url))],
})
