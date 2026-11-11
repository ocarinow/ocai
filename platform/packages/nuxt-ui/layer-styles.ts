import { fileURLToPath } from 'node:url'
import { addTemplate, defineNuxtModule, getLayerDirectories } from '@nuxt/kit'

/** Include Tailwind classes from every consuming layer without naming an app. */
export default defineNuxtModule({
  meta: { name: 'ocarinow-ui-layer-styles' },
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
  },
})
