# 0007 — Governed execution through public package contracts

- **Status:** accepted (implementation staged by WU-21–32)
- **Date:** 2026-11-10
- **Deciders:** maintainer requirements; package implementation design

## Context
A gateway must govern local and remote, unary and streaming execution without
private facade calls or copied provider mapping. WU-17–20 supplies the catalog
baseline; it does not supply secure execution or complete client output edges.

## Decision
Authenticate a detached transport-only request on each physical attempt. Never
mutate the hook-visible request. Propagate explicit per-call context snapshots;
trusted identities are platform assertions, not kernel authentication. Context is
not wire payload. Whole-call deadlines use a monotonic budget derived once from
an aware UTC deadline, including admission and retries. Transports must respect
remaining timeout; sync arbitrary user transport code cannot be forcibly preempted
and late results are rejected. Async operations additionally use cancellation.

Streams have explicit ownership (close/aclose and context managers), one terminal
execution outcome, and separate aborted evidence from successful StreamEnd.
A non-consumed stream is pending until explicitly closed; garbage collection is
not an audit guarantee. Streaming middleware has its own continuation contract;
unary-only governance must fail closed for streaming. No generation replay after
output, no transparent cross-provider continuation. Wrappers close upstream.

Lifecycle observers are passive, isolated, metadata-first and per invocation.
Admission retries do not count as provider attempts. Caller parent/correlation
facts are explicit. No automatic request/response/error-body export; authorized
payload capture is separately opted in by the application with redaction. Durable
required audit belongs in enforceable middleware, not passive callbacks.

Public prepared handles bind detached request data and configuration to the model
that prepared them. Inspection returns copies of route, paths, declarations,
coverage and request findings; declarations never imply certification. Unknown
profile coverage stays unknown. Execution consumes the approved snapshot, rejects
foreign/stale configuration, and rechecks fidelity policy before I/O. Both losses
and shifts are independently enforceable. Response rejection retains accounting;
streaming enforcement cannot retract delivered content or promise whole-response
approval before the first chunk. Partial execution is explicit.

Provider plugins own request/response/chunk mappings. Gateway code owns serving
metadata and HTTP/SSE framing. Every conversion leg keeps its own report identity;
aggregation merges each leg exactly once. Qualify only the supported matrix in
the program; new edges require contracts, golden fixtures and fold triples.

## Alternatives considered
Shallow request copying leaves shared headers exposed. Reusing unary continuation
for streams breaks usage and lifetime semantics. A hidden context variable makes
concurrency/correlation implicit. Exposing `_prepare` exposes mutable internals.
A `lossless` boolean hides semantic shifts and uncertainty. Gateway field mapping
would duplicate plugin logic and evade conformance.

## Consequences
No gateway service, database, auth scheme, budget engine or platform registry
enters core. No canonical revision promotion. Tests must distinguish declared
capability from demonstrated coverage, partial evidence from successful completion,
and logical calls from actual transport attempts. Each implementation lands in its
own PR with the current strict gate.
