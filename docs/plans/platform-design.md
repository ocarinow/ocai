# Platform design documentation

## WU-33 — Publish the platform and gateway design

Source: maintainer request, "Make the appropriate commit and PR" for the platform
documentation developed in the product discussion.

- [x] **Status:** complete.
- **Scope:** Publish one coherent documentation set under `docs/design/platform/`,
  reconcile its index with the existing platform landing page, record accepted
  product layout in ADR 0006 and architecture §12, and distinguish agreed product
  choices from proposed controls and open implementation decisions. Own those
  files, the ADR index, this entry, the roadmap status row, and the platform
  navigation entries in `zensical.toml`.
- **Done:** The linked documentation set reflects console plus management API,
  selected stack, shared frontend layers, enterprise compartments, evidence,
  human evaluation, execution profiles, and the proposed security approach;
  relative links resolve and `scripts/check.py` exits 0 without runtime changes.
- **Deps:** none; the gateway readiness program is referenced, not implemented
  or reprioritized here.
- **Architecture:** §12 added; §11 kernel/satellite boundary preserved.
- **Freeze:** none. Shapes, nodes, edges, schemas, extension census, fixtures,
  public fields, streaming contracts, and runtime dependencies: none changed.
- **Decision (layout):** ADR 0006 records deployable products under `platform/`
  and independently distributed libraries under language directories.
- **Decision (product):** Customer-hosted first; console and management API in
  the first gateway slice; Nuxt/Vue, shadcn-vue/Tailwind, FastAPI, PostgreSQL,
  and OpenFGA selected. Precise APIs and security mechanisms remain proposals.
- **Out:** Application scaffolding, kernel implementation, dependency changes,
  security certification, and implementation WUs for the wider portfolio.
- **Open:** none for publishing this design. Product questions are explicitly
  tracked in `docs/design/platform/decisions.md` and do not block documentation.
