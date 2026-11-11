# 0012 — Full upstream shadcn-vue component layer

- **Status:** accepted
- **Date:** 2026-11-11
- **Deciders:** maintainer's explicit component-library and full-catalogue requests

## Context

The initial foundation provided a handwritten button following shadcn composition
patterns. This did not satisfy the chosen component-library requirement. The
maintainer requires actual shadcn-vue source and all UI components installed
up front, with a reusable boundary for future Ocarinow branding.

## Decision

`platform/packages/nuxt-ui` vendors the complete upstream UI registry snapshot
using the pinned shadcn-vue CLI, with its MIT attribution and workspace lockfile.
`shadcn-nuxt` registers `Ui*` components for direct consumption. Do not create a
parallel set of wrapper primitives. Keep neutral light/dark semantic tokens in
this layer and Ocarinow overrides in the higher `nuxt-platform` layer. Nuxt Kit
supplies consuming layer directories to Tailwind so shared shell classes are
included without making the UI layer depend on a named app.

Install the dependencies needed by the catalogue, including charts, date controls
and forms. Include TanStack Table for upstream Data Table compositions. Optional
schema adapters unused by component code are not mandatory dependencies. Example
applications, domain-specific table columns, and separate AI Elements recipes are
outside the base component catalogue. Record upstream integration workarounds in
the layer README and keep component source recognizable for future upgrades.

## Consequences

Each app inherits the same controls and can evolve its higher-level presentation.
Unused component JavaScript is excluded from the app bundle, but the installation,
type-checking workload and shared utility CSS grow with the full catalogue.
Pinned CLI versions do not pin the live registry; committed sources and the npm
lockfile are the reproducibility boundary. Updates require reviewing source,
licenses, advisories, Nuxt typing and browser behavior together.
