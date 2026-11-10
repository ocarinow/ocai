# WU-20 — Catalog composition and external conformance

- **Status:** complete, verified locally and committed with the implementation.
- **Dependencies:** WU-17 baseline and WU-18 installed plugin example.
- **Scope:** architecture §4 catalog/graph/conformance boundaries and the chat
  front door's interface selection; no new runtime IR or provider adapter.
- **Decision:** [ADR 0004](../decisions/0004-catalog-composition-and-evidence.md).

## Done criteria

- [x] Reject contradictory node metadata and competing directed unary/stream
  edges; preserve identical-registration idempotence and builder usability after
  rejection. Enforce one graph shape.
- [x] Prove equal-grade routes are independent of registration order for unary
  and streaming graphs; reject conflicting profile declarations and stabilize ties.
- [x] Require explicit sibling-interface selection when ambiguous, while retaining
  tag pins, revision ordering within an interface, and front-door stub exclusion.
- [x] Snapshot declarations and protect catalog fingerprints from caller mutation.
  Include full contracts, traits, endpoints, and resource manifests in lock format 2;
  document code/artifact/resource-content exclusions.
- [x] Load independently packaged fixtures and extension schemas, rejecting missing
  resources, conflicting schemas, bad metadata, mismatched coordinates, uncovered
  payload edges, incorrect outputs/reports, and exceeded declarations.
- [x] Exercise real wheel installation/discovery and packaged data in the echo
  plugin; keep schema-validation dependencies in tests.
- [x] Run the full Python checks and the isolated installed-plugin suite.

The conformance helper validates only supplied evidence. It does not automatically
certify discovery, scan every possible payload, or replace stream fold tests.
Resource manifests locate data; they do not authenticate publishers.

Next: qualify the ordered-item candidate against modern provider examples, then
implement a dated canonical revision, migrations, and item streaming together with
their fidelity evidence. See [the modernization program](core-modernization.md).
