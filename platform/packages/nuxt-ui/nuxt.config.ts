import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import uiIntegration from './module'

export default defineNuxtConfig({
  modules: ['shadcn-nuxt', uiIntegration],
  shadcn: {
    prefix: 'Ui',
    componentDir: fileURLToPath(new URL('./app/components/ui', import.meta.url)),
  },
  vite: { plugins: [tailwindcss()] },
})
