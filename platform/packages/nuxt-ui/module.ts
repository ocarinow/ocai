import { fileURLToPath } from 'node:url'
import { addTemplate, defineNuxtModule, getLayerDirectories } from '@nuxt/kit'

/** Integrate upstream components and styles across consuming Nuxt layers. */
export default defineNuxtModule({
  meta: { name: 'ocarinow-ui-integration' },
  setup(_options, nuxt) {
    const theme = fileURLToPath(new URL('./app/assets/css/theme.css', import.meta.url))
    const stylesheet = addTemplate({
      filename: 'ocarinow-ui.css',
      write: true,
      getContents: () => [
        `@import ${JSON.stringify(theme)};`,
        ...getLayerDirectories(nuxt).map(layer => `@source ${JSON.stringify(layer.app)};`),
      ].join('\n'),
    })
    nuxt.options.css.unshift(stylesheet.dst)

    // Register after shadcn-nuxt's hooks: 2.9 treats uppercase type exports and
    // the form injection key as components. Keep explicit imports available.
    const directory = fileURLToPath(new URL('./app/components/ui/', import.meta.url))
    const nonComponents = new Set([
      'CarouselApi', 'HighlightedToken', 'FORM_ITEM_INJECTION_KEY',
      'MessageScrollerButtonDirection', 'MessageScrollerDefaultScrollPosition',
      'MessageScrollerProviderProps', 'MessageScrollerScrollable',
      'MessageScrollerScrollAlign', 'MessageScrollerScrollOptions',
      'MessageScrollerVisibilityState',
    ])
    nuxt.hook('components:extend', (components) => {
      for (let index = components.length - 1; index >= 0; index--) {
        const component = components[index]!
        if (component.filePath.startsWith(directory) && nonComponents.has(component.export ?? '')) {
          components.splice(index, 1)
        }
      }
    })
  },
})
