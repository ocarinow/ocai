# `ocai` — Go (not yet implemented)

Placeholder. The Go implementation will be scaffolded to **mirror the
language-neutral `spec/`** and consume the **same golden fixtures** in
`spec/fixtures/`, so its conformance suite proves parity with Python.

Module path:

```
github.com/walid/ocai/go
```

Planned end-user install (layout stays invisible to users):

```bash
go get github.com/walid/ocai/go
```

Planned shape:

- root module: canonical IR types, ports (interfaces), conversion graph, middleware.
- per-provider subpackages / modules (`.../go/openai`, ...).
- `conformance_test.go` loads `spec/fixtures/*.json` and asserts codec round-trips.

CI already has a stubbed `go` job that re-runs on `go/**` and `spec/**` changes
(the spec-drift alarm).
