# AI Gateway product design

Status: proposed first platform product. Prerequisites and support limits are
tracked in [delivery](delivery.md), not implied by this design.

## Product promise

Let enterprises change model providers and interfaces while enforcing their
application contracts and exposing conversion effects. Conversion fidelity
does not establish equivalent model quality; quality requires evaluation.

Provide familiar compatibility endpoints for adoption and a native ocai
surface for full contracts. Endpoint selection and initial coverage remain
open. Compatibility clients should receive an execution identifier that can
resolve to an authorized receipt without modifying provider response bodies
in ways that break clients.

## First-release management experience

Ship the console and management API together. Administrators manage organization
membership, teams, resource grants, service accounts, scoped API keys, provider
connections, deployments, routing policies, and quotas through the same backend
contracts. Operators inspect authorized requests, conversion receipts, usage,
and audit history. Detailed endpoint paths and UI flows remain implementation
work.

PostgreSQL is the authoritative configuration store. Executions resolve versioned
configuration snapshots so changes remain attributable. Files support deployment
bootstrap and controlled import/export, rather than being the primary product
configuration workflow. Secret values never appear in ordinary exports.

The first capability is chat generation, through native and qualified provider
interfaces sharing authentication, authorization, limits, and evidence. OpenAI
Chat Completions is the proposed first compatibility surface; other interfaces
require explicit qualification. Keep protocol adapters extensible for future
tools/MCP/agents without creating an arbitrary-destination proxy.

See [stack](stack.md) and [security](security.md) for cross-product boundaries.

## Request lifecycle

1. Authenticate the caller and resolve trusted tenant, compartment, application,
   and deployment context. Untrusted request metadata cannot grant authority.
2. Resolve a versioned policy/configuration snapshot and eligible deployments.
3. Inspect the conversion plan and enforce request-side loss restrictions
   before provider I/O. Explain excluded candidates without exposing forbidden
   deployments or sensitive policy details.
4. Admit the request under concurrency, rate, and budget controls. Record
   reservations and their provenance.
5. Execute through ocai, applying credentials at the driver leaf. Recheck
   authorization and eligibility on each fallback or materially changed route.
6. Convert the response, report actual effects, finalize usage where known,
   and produce a receipt. Retain authorized evidence if response conversion
   violates policy, with an explicit failure/partial-result contract.

Response-side violations may only become known after inference or streamed
delivery has begun. A strict pre-delivery guarantee may require buffering,
which changes latency and streaming behavior. This tradeoff must be explicit.

## Routing and streaming

Candidate eligibility includes allowed provider/deployment/region, capabilities,
reference scope, caller permissions, budget, and permitted conversion loss.
Cost and latency optimization happens among eligible candidates. Provider
continuation handles and reasoning references cannot be assumed portable.

A healthy fallback that violates the application's requirements is ineligible.
Refusal and content-policy failures must not become an automatic way to evade
the application's safety policy through another provider.

Default proposed stream behavior after partial delivery is an explicit partial
failure. Cross-provider continuation requires an opt-in contract documenting
provenance, possible duplication, and changed semantics. Do not silently stitch
answers or replay tool actions. Cancellation propagates upstream where possible;
cancellation does not establish that the provider stopped billing.

## Control and data planes

The data plane authenticates, admits, routes, executes, streams, and emits
evidence. The control plane manages principals, deployments, policy, budgets,
and configuration releases. Keep their responsibilities distinct; the MVP may
serve both in one process. Separate deployment is a later operational choice.

Proposed outage behavior permits eligible traffic under a bounded last-known-good
configuration. Snapshot expiry, revocation propagation, and unavailable budget,
credential, or audit services need explicit per-operation behavior. "Fail open"
and "fail closed" are not one global switch. No offline availability promise
may imply immediate knowledge of a remote revocation.

## Production requirements

| Area | Required qualification |
|---|---|
| Identity | Workload identity, scoped virtual keys, rotation, delegated administration |
| Isolation | Compartments enforced across credentials, quotas, caches, receipts, and payload access |
| Data boundaries | Endpoint/egress restrictions, private deployment options, retention controls |
| Reliability | Deadlines, bounded retries, circuit breakers, backpressure, stream draining, cancellation |
| Accounting | Reservations under concurrency, reconciliation, duplicate handling, pricing versions |
| Configuration | Validation, staged rollout, rollback, emergency controls, provenance |
| Operations | Health and saturation signals, dependency outage behavior, recovery procedures |
| Supply chain | Artifact provenance, signed releases, dependency inventory, plugin admission, patch policy |

Estimated reservations cannot guarantee an absolute spending ceiling where
provider charges are unbounded or unknown. Strict caps require bounded workloads
and enforceable accounting semantics; otherwise publish uncertainty and possible
overshoot. Billable failed attempts remain visible. Unknown usage is not zero.

Self-hosting places the gateway in customer infrastructure; configured external
providers still receive inference requests. Region claims must include the
inference endpoint and supporting data paths, not only the gateway location.

## Migration workflow

Use an authorized traffic sample to inspect a proposed provider/interface change:
unsupported features, scoped references, conversion differences, quality
evaluations, and cost estimates. Offline conversion replay and live model
evaluation are different activities. Shadow traffic adds disclosure and spend
and requires approved destinations and data policy.

Produce a reviewable migration report, then permit approved canary rollout and
rollback. Pin converter artifacts as well as configuration; a catalog fingerprint
alone must not be advertised as proof of executable code identity.

## First demonstration

During a provider outage, evaluate alternatives for an application requiring
approved deployments and preserved structured-output semantics. Explain why an
incompatible route is rejected; select an eligible route or return an explicit
failure. The receipt links every attempt, policy decision, and fidelity finding.
Run the equivalent scenario for unary calls and interrupted streams.
