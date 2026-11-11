import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import layerStyles from './layer-styles'

export default defineNuxtConfig({
  modules: ['shadcn-nuxt', layerStyles],
  shadcn: {
    prefix: 'Ui',
    componentDir: fileURLToPath(new URL('./app/components/ui', import.meta.url)),
  },
  vite: { plugins: [tailwindcss()] },
  hooks: {
    'components:extend'(components) {
      // shadcn-nuxt 2.9 also registers type-only exports and injection keys.
      // Keep those available through explicit imports, never as Vue components.
      const nonComponents = new Set([
        'UiCarouselApi', 'UiHighlightedToken', 'UiFORM_ITEM_INJECTION_KEY',
        'UiMessageScrollerButtonDirection', 'UiMessageScrollerDefaultScrollPosition',
        'UiMessageScrollerProviderProps', 'UiMessageScrollerScrollable',
        'UiMessageScrollerScrollAlign', 'UiMessageScrollerScrollOptions',
        'UiMessageScrollerVisibilityState',
      ])
      for (let index = components.length - 1; index >= 0; index--) {
        if (nonComponents.has(components[index]!.pascalName)) components.splice(index, 1)
      }
    },
  },
})
