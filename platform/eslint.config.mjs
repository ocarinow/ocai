// ESLint for the platform workspace (console, nuxt-platform, management-client,
// tests). The vendored shadcn-vue catalogue in packages/nuxt-ui is upstream code
// and is not linted; generated and build output are ignored.
import { createConfigForNuxt } from '@nuxt/eslint-config/flat'

export default createConfigForNuxt({
  features: {
    tooling: true,
    stylistic: false,
  },
}).append({
  // Nuxt names pages and layouts by file path (index.vue, default.vue); the
  // multi-word rule is for registered components, not routed files.
  files: ['**/pages/**/*.vue', '**/layouts/**/*.vue'],
  rules: { 'vue/multi-word-component-names': 'off' },
}, {
  ignores: [
    '**/node_modules/**',
    '**/.nuxt/**',
    '**/.output/**',
    'packages/nuxt-ui/**',
    'packages/management-client/schema.d.ts',
    'test-results/**',
    'playwright-report/**',
  ],
})
