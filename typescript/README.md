# `ocai` — TypeScript (not yet implemented)

Placeholder. The TypeScript implementation will be scaffolded to **mirror the
language-neutral `spec/`** and consume the **same golden fixtures** in
`spec/fixtures/`, so its conformance suite proves parity with Python.

Planned end-user install (layout stays invisible to users):

```bash
npm i @ocai/core
npm i @ocai/openai     # plugin, mirrors python/packages/ocai-openai
```

Planned shape:

- `@ocai/core` — canonical IR types, ports, conversion graph, middleware.
- per-provider plugin packages (`@ocai/openai`, ...).
- `conformance.test.ts` loads `spec/fixtures/*.json` and asserts codec round-trips.

CI already has a stubbed `typescript` job that re-runs on `typescript/**` and
`spec/**` changes (the spec-drift alarm).
