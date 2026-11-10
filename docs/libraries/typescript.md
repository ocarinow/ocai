---
icon: lucide/braces
---

# TypeScript

!!! warning "Status: deferred"

    Not implemented. `typescript/` holds a placeholder README and CI has a
    stub job that re-runs on `typescript/**` and `spec/**` changes, so the
    spec-drift alarm is already wired.

When it starts, the port begins from
[`spec/canonical-json.md`](https://github.com/ocarinow/ocai/blob/main/spec/canonical-json.md)
— implement `canonical` and `semantic_equal` first — and must pass the
identical `spec/fixtures/` suite: unknown-X vectors, edge fixtures, fold
triples. Planned packages: `@ocai/core` plus one plugin package per provider
interface. Sequencing is set by the [roadmap](../plans/README.md).
