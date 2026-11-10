import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  css: [fileURLToPath(new URL('./app/assets/css/theme.css', import.meta.url))],
  vite: { plugins: [tailwindcss()] },
})
