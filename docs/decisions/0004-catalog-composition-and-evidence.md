# 0004 — Explicit composition conflicts and packaged conformance evidence

- **Status:** accepted for the provisional implementation
- **Date:** 2026-11-10
- **Deciders:** WU-20 implementation workstream; subject to maintainer review

## Context

Two converters could claim one directed pair and tie on grade, making behavior
depend on registration order. Node identity includes metadata, so contradictory
release/status declarations could coexist under the same four public coordinates.
Sibling interface dates were compared as if they ranked interchangeable revisions.
Independent plugins lacked a shared way to locate their own conformance resources.

## Decision

Reject competing directed-edge declarations, contradictory node metadata,
same-pattern profile conflicts, and conflicting component factories. Identical
registrations remain idempotent. Enforce one shape per graph and snapshot
declaration mappings. Break equal-cost path ties by structural destination
coordinates; rank equally specific profile patterns lexically.

Require an interface pin when multiple sibling interfaces remain eligible.
Revision dates rank revisions within one interface. The chat front door considers
only component-backed interfaces, preserving the ability to publish stubs.

Add an optional package-relative conformance manifest to fragments. The explicit
test harness loads local JSON resources, checks extension metadata/conflicts,
matches fixture coordinates, checks every payload edge's expected output and
records, and certifies those emitted records against the declaration. Test suites
provide schema validators; no third-party validation import enters runtime code.
Streaming certification still requires the existing fold-triple harness.

Lock format `ocai.catalog-lock/2` includes full contracts, structured endpoint
metadata, traits, and resource locations. Equivalent orderings hash equally.
It deliberately does not fingerprint callable code or packaged resource contents.

## Alternatives considered

- Pick a competing converter by insertion order or declared grade: silently
  changes behavior when packages are composed and lets declarations act as priority.
- Prefer whichever sibling API has a later release date: dates say nothing about
  compatibility, capabilities, or application preference.
- Require external authors to register schemas in this repository: couples
  independent release cycles to core.
- Run validators on catalog discovery: adds dependencies and work to runtime
  initialization without proving correctness for untested payloads.

## Consequences

Ambiguous compositions that previously chose a route now fail with an actionable
error. Lock hashes change with the new format; persisted old locks remain historical
records, not an input silently reinterpreted by this implementation. Plugin ABI
remains provisional. Resource manifests are declarations, not signed certificates;
loading a Python package still executes its code. Artifact verification and broader
fidelity evidence remain later work.

See [WU-20](../plans/wu-20-catalog-conformance.md).
