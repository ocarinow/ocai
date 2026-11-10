---
icon: lucide/box
---

# Go

!!! warning "Status: deferred"

    Not implemented. `go/` holds a placeholder README and CI has a stub job
    that re-runs on `go/**` and `spec/**` changes.

Planned module path `github.com/ocarinow/ocai/go`, with the canonical IR
types, ports as interfaces, and the conversion catalog in the root module and
one subpackage per provider interface. Same rule as every port: the
conformance suite over `spec/fixtures/` must pass unchanged. Sequencing is
set by the [roadmap](../plans/README.md).
