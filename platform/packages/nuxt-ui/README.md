# Shared shadcn-vue layer

Private Nuxt layer for every Ocarinow app. Extend `@ocarinow/nuxt-ui` for
neutral upstream components, or `@ocarinow/nuxt-platform` for the Ocarinow theme
and platform shell. Templates use `UiButton`, `UiDialog`, `UiTable`, and the
other upstream names prefixed with `Ui`. No wrapper component library is required.
Types, variants and composables use explicit imports, for example:

```ts
import { buttonVariants } from '@ocarinow/nuxt-ui/components/ui/button'
import type { ChartConfig } from '@ocarinow/nuxt-ui/components/ui/chart'
```

`shadcn-nuxt` registers components on demand. Unused families are not imported
into the browser's JavaScript bundle; Tailwind scans the catalogue, so its shared
CSS does include utilities for installed components. `module.ts` also scans
each consuming Nuxt layer's app directory through Nuxt Kit. A new app needs no
hardcoded source path in this package. Neutral light/dark tokens live here;
Ocarinow overrides live in `nuxt-platform/app/assets/css/theme.css`. Future brand
work changes higher-layer tokens/compositions while retaining upstream controls.

## Upstream snapshot

Imported on 2026-11-11 using `shadcn-vue@2.9.0 add --all --yes`, with the
`new-york` style and neutral CSS-variable palette. This snapshot contains
68 registry component families and 390 Vue source files. The CLI version is
pinned in the command; the remote registry is mutable. The checked-in source and
workspace lockfile, not rerunning the command, reproduce this snapshot.

Upstream component code is MIT licensed; see [LICENSE.shadcn-vue](LICENSE.shadcn-vue).
The rest of ocai remains source-available under FSL-1.1-ALv2.

`accordion`, `alert`, `alert-dialog`, `aspect-ratio`, `attachment`, `avatar`, `badge`, `breadcrumb`, `bubble`, `button`, `button-group`, `calendar`, `card`, `carousel`, `chart`, `checkbox`, `code-block`, `collapsible`, `combobox`, `command`, `context-menu`, `dialog`, `drawer`, `dropdown-menu`, `empty`, `field`, `form`, `hover-card`, `input`, `input-group`, `input-otp`, `item`, `kbd`, `label`, `marker`, `menubar`, `message`, `message-scroller`, `native-select`, `navigation-menu`, `number-field`, `pagination`, `pin-input`, `popover`, `progress`, `questionnaire`, `radio-group`, `range-calendar`, `resizable`, `scroll-area`, `select`, `separator`, `sheet`, `sidebar`, `skeleton`, `slider`, `sonner`, `spinner`, `stepper`, `switch`, `table`, `tabs`, `tags-input`, `textarea`, `toggle`, `toggle-group`, `tooltip`, `trace`.

This is the complete UI catalogue returned by `add --all`, including chart,
form, sidebar, message, and code-block families. Data Table and Date Picker are
[upstream composition guides](https://www.shadcn-vue.com/docs/components/data-table),
not additional registry primitives: Table and TanStack Table, and Calendar and
Popover, are installed. Per-product columns, queries and date behavior belong
in their consuming app. Toast is superseded upstream by Sonner. Example apps,
marketing blocks and the separately published AI Elements recipes are not
additional base UI components.

## Updating

From the repository root, with the supported Node version:

```bash
npx --yes shadcn-vue@2.9.0 add --all --yes --overwrite --cwd platform/packages/nuxt-ui
npm run --prefix platform typecheck
uv run python scripts/check.py
```

Run updates on a branch and review the generated diff and dependency advisories.
Do not overwrite local files blindly when upgrading. Commit the source and lock
changes together, update this snapshot note, and preserve the upstream license.
The registry handles cross-component imports through `components.json` aliases
and package subpath exports, including Vue file imports used by Sidebar.

Integration adjustments outside upstream component source:

- Install `@unovis/vue`, `@unovis/ts`, and `@internationalized/date` explicitly;
  the registry's chart dependency metadata does not install Unovis itself.
- TanStack Table is available for the documented Data Table compositions.
- Omit unused `@vee-validate/zod` and Zod 3. Registry form components use
  `vee-validate` directly; the optional Zod 3 adapter adds a known high-severity
  dependency advisory and is not required to use those components.
- `shadcn-nuxt@2.9.0` mistakes capitalized type-only exports and the form
  injection key for Vue components. A narrow registration filter excludes those
  ten symbols. Their explicit imports remain available; remove the workaround
  when the upstream module correctly distinguishes runtime component exports.

Full Nuxt type checking covers the installed layer source. The built-console
browser test exercises real upstream controls, higher-layer styling and mobile
layout, alongside the management connection/retry workflow.
