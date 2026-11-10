# Core modernization

The next program makes Python ocai a foundation for an enterprise agent
platform while retaining independently usable libraries. Provider conversion,
canonical contracts, and fidelity reporting remain the first product. Telemetry,
auditing, evaluation, asset registries, and agent hosting build on those contracts.
TypeScript and Go implementation are deferred; the specification remains neutral.

This plan supersedes the execution order in [horizon.md](horizon.md). M1–M3
remain completed history. Each work unit should be reviewed separately; later
milestones are split into small work units when reached.

## Starting work units

| Work unit | Deliverable | Status |
|---|---|---|
| WU-17 | Refresh status, record platform boundaries and revised freeze gates, publish the feature matrix | ✅ Complete |
| WU-18 | Repair the independent conversion plugin; test wheel installation, discovery, every edge, and unknown content in CI | ✅ Complete |
| WU-19 | Draft item schemas and provenance-labelled design fixtures, schema-tested without changing runtime revision | ✅ Complete |
| WU-20 | Harden catalog composition and external plugin conformance integration | Next |

WU-19 is a design checkpoint, not an adapter or canonical migration release.
Acceptance requires schema validity, preservation requirements, negative
examples, and explicit unresolved decisions. It must not register a new canonical
node, rewrite existing fixtures, or claim conversions/streaming are implemented.

Completed work units are committed locally; no PRs have been merged. WU-17 follows M1–M3;
WU-18 and WU-19 depend on that baseline and are otherwise independent. Their
scope and acceptance are the deliverables above. WU-19 records the candidate under `spec/proposals/ordered-items/` and its
rationale in [proposed ADR 0003](../decisions/0003-ordered-item-modernization.md).
The item shape remains open to change before runtime implementation.

## Implementation sequence and gates

1. **Catalog and plugin boundaries (WU-20).** Specify duplicate node/edge
   conflicts, deterministic equal-cost paths, and interface selection.
   Support independently packaged extension schemas and conformance fixtures.
   Test explicit catalogs and installed discovery. Endpoint ownership is
   self-declared and entry-point loading executes Python; admission is not
   publisher authentication. Define what catalog fingerprints include before
   advertising reproducibility of converter code.
2. **Next canonical revision.** Implement the ordered item contract after
   the WU-19 proposal is exercised
   against provider examples. Preserve message boundaries, phase, identity,
   replay references, tool correlation, and source grouping. Design history
   inputs alongside outputs. Keep text views derived. Introduce a dated
   revision with forward/reverse migration edges and explicit reports for lossy
   downgrade to `2026-07`; do not rewrite old recordings.
3. **Content, evidence, and artifacts.** Preserve verbatim text; native JSON
   differs from parsed generated text. Separate answer attribution from source
   locations. Add reusable evidence/search results and file metadata over the
   source union. Provider handles remain scoped. Resource transfer belongs to
   an effectful service, never a graph edge. Gate: fixtures for JSON null/scalars,
   citations, locations, files, unknown data, and invalid provider references.
4. **Item streaming and middleware parity.** Add item-addressed events and
   content deltas with ordering, finalization, and abort behavior. Complete
   citation and binary accumulation, distinguishing independently encoded
   chunks from fragments of one base64 stream. Fold paired recordings into
   the unary result. Apply governance/observation to streams as well as unary
   calls. No new production part ships without tested fold/partial behavior.
5. **Fidelity as a user contract.** Separate declarations, per-payload reports,
   and conformance evidence. Add inspectable plans and caller loss policies;
   reject forbidden request changes before sending, retain results/evidence
   when response conversion violates policy. Preserve or version `lossless`;
   severity is not a percentage. Document static planning and require evidence
   before adding payload-aware planning. Gate: independent expected outputs,
   faulty-converter negative tests, replay checks, and explained conversions.
6. **Provider vertical slices.** Adapt current Chat Completions and Messages;
   implement Responses; implement Gemini Interactions to challenge the design.
   Land schemas, edges, profiles, runtime behavior, and HTTP/SSE fixtures per
   feature. Exercise continuation, reasoning replay, hosted tools/MCP approval,
   citations, and caching. Keep continuation, storage, caching, and background
   execution distinct. Add submit/retrieve/cancel and file operations as
   separate capabilities/runtime services when needed. Optional live smoke
   tests supplement secret-free CI.
7. **Decision capability.** Add shapes for evidence, typed questions, predicates,
   choices, scores, refusals, and distributions. Reuse shared result/context/usage
   and graph machinery; no decision-specific engine branch. Chat emulation must
   report semantic differences. This is unrelated to `runtime.decisions`.
8. **Core release qualification.** Demonstrate configuration-only interface
   switching, cross-provider conversion with explicit losses, old-revision
   migration, and an independently packaged plugin. Publish representation,
   conversion, and execution support separately. Freeze only exercised contracts.

Implementation units run targeted behavioral tests, the full Python suite,
Ruff, and import contracts. Schema changes require positive and negative cases.
Packaging changes require the isolated wheel job. Fixtures must distinguish live
recordings, documentation examples, and synthetic cases. Schema-valid output
does not establish a working adapter or fidelity guarantee.

## Enterprise platform after core qualification

Build one workflow: version an agent and its assets, execute it, capture linked
telemetry and durable audit records, evaluate the result, and trace it to exact
definitions/configuration. Start with run/parent/asset identity and event emission;
add independent telemetry and audit libraries, typed asset registries, and
evaluation. Agent execution adds tools, state, approvals, cancellation, and
recovery. Management adds deployments, workers, scheduling, authorization,
budgets, and administration.

The kernel remains independent of storage engines, telemetry vendors, agent
frameworks, and HTTP. Agent definition, deployment, and run have distinct
identities. Sampled traces are not durable audit evidence. Registry infrastructure
may be shared while agent, skill, tool, and MCP asset contracts remain distinct.

## Decisions still to settle

- Item naming, reasoning placement, source grouping, and a compatible convenience
  API for single-message applications.
- Provider approval exchange versus application authorization; credential
  references without secrets in transcript data.
- Evidence identity, page/time/region locations, artifact ownership/digests,
  JSON streaming, and exact versus normalized text for citation spans.
- Loss-policy defaults, report versioning, and artifact/conformance fingerprints.
- Job cancellation/resume semantics; async Python is not durable provider work.

These are implementation inputs, not reasons to suspend independent work.
