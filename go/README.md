# `ocai` — Go (not yet implemented)

Placeholder. ocai is a monorepo whose source of truth is the language-neutral
[`spec/`](../spec/README.md); the Python workspace in [`python/`](../python/README.md)
is the first port. The Go port will be scaffolded to **mirror `spec/`** and
consume the **same golden fixtures** in `spec/fixtures/`, so its conformance
suite proves parity with Python rather than re-deriving the contracts. Work
on it is deferred until the Python
[core modernization program](../docs/plans/core-modernization.md) lands.

Module path:

```
github.com/ocarinow/ocai/go
```

Planned end-user install (layout stays invisible to users):

```bash
go get github.com/ocarinow/ocai/go
```

Planned shape, mirroring the Python layers:

- root module: the canonical contracts (`CallResult`, `FidelityReport`,
  identity), capability ports (interfaces) and IR, the conversion catalog,
  runtime.
- per-provider subpackages (`.../go/openai`, ...) contributing a
  `CatalogFragment` each, never a provider SDK.
- a conformance suite that loads `spec/fixtures/*.json` (edge fixtures and
  fold triples) and asserts the same results Python certifies.

CI already has a stubbed `go` job that re-runs on `go/**` and `spec/**`
changes (the spec-drift alarm). Source-available under FSL-1.1-ALv2; ocai is
not open source.
