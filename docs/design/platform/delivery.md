# Platform delivery and qualification

> **Proposed design, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Status: proposed product sequence, not an implementation schedule. The active
work queue remains [docs/plans](../../plans/README.md). No existing WU is completed
or reprioritized by this document.

## Sequence

| Stage | Outcome | Prerequisites and exit evidence |
|---|---|---|
| Foundation | Qualified kernel paths and minimal shared platform contracts | Conversion/streaming evidence, identity model, scope propagation, version references |
| Gateway | One governed model-access workflow | Auth, compartment isolation, eligible routing, receipts, budgets, outage and stream tests |
| Observability and Evaluation | Investigate runs and judge outcomes | Instrumentation beyond the gateway, evidence lifecycle, experiments, human review |
| Full Catalog | Discover and govern reusable assets | Typed versions, ownership, dependencies, approvals, lifecycle |
| Agent Runtime | Operate tools and durable workflows | Profiles, environments, action authorization, recovery, approval tests |
| Builder and Studios | Configure and publish usable agents | Shared authoring contracts, tested profiles, evaluations, deployment lifecycle |
| Application Experiences | Deliver capabilities to end users | Authenticated interfaces, artifacts, long-running interactions, feedback |
| Model Operations | Govern private serving infrastructure | Customer demand, serving adapters, operational/capacity evidence |

Minimal registry and policy capabilities start with the gateway. Early prompt
authoring and evaluation prototypes can precede the full catalog UI. The runtime
must support a profile before the builder promises it. Model operations or
knowledge services may move earlier when required by the first customer;
the sequence expresses dependencies, not a rigid serial project plan.

## Kernel prerequisites

The [modernization program](../../plans/core-modernization.md) and
[governed gateway program](../../plans/gateway-readiness.md) cover:

- Catalog composition, deterministic planning, independently packaged plugins,
  artifact identity, and external conformance.
- Ordered interactions, replay/reference preservation, and the next canonical
  revision with explicit migration loss.
- Streaming finalization/abort behavior and governance parity.
- Inspectable conversion plans, caller loss policies, and response violation
  handling.
- Qualified provider vertical slices and release evidence.

Scope the gateway's supported surface to exercised capabilities. Consult the [integration guide](../../user/gateway-integration.md),
[feature matrix](../../user/provider-feature-matrix.md), and merged release evidence rather
than infer execution support from schemas, package names, or this vision.

Existing [gap records](../../plans/gaps.md) cover continuation anchors (G-01),
recorded-pair formats (G-02), transcript fixtures (G-03), correlation identity
(G-04), and MCP ownership (G-05). Validate their current status when scheduling
work. New gaps discovered by implementation should be recorded there with
evidence, not solved by expanding core silently.

## First gateway slice

The agreed launch direction is customer-hosted first, with managed hosting
later. Keep the architecture suitable for a managed service without requiring
both operating models for the first release. Customer-hosted topology,
infrastructure support, and operating responsibilities remain to be specified.

Target a platform team standardizing model access, governance, and costs. Pair
the gateway pilot with one concrete application so it exercises compartments,
observability, and human evaluation together. A domain knowledge assistant is
the proposed example; the named partner and exact application remain open.

Choose that partner's application contract. A candidate gateway slice uses
OpenAI and Anthropic, unary and streaming execution, scoped credentials,
compartment propagation, versioned policy, reservations, and a receipt view.
The console and management API ship in this first slice; configuration lives in
PostgreSQL and changes produce versioned execution snapshots.
Compatibility endpoints and detailed deployment topology remain open decisions.

Qualification should establish:

1. The application succeeds on its supported path with expected conversion
   evidence and attributable consumption.
2. Forbidden request transformations are rejected before provider I/O, and
   late response violations have a documented result contract.
3. Failover respects the same scope, reference, residency, and capability
   constraints as the primary path.
4. Partial streams, disconnects, cancellation, process crashes, and dependency
   outages produce explicit outcomes and reconcilable evidence.
5. Concurrent admissions and duplicate delivery cannot silently corrupt the
   ledger; uncertainty and possible overshoot are visible.
6. Unauthorized cross-compartment access fails across payloads, caches,
   receipts, administration, and exports.
7. Support is documented by interface, revision, feature, operation, and
   stream/replay behavior.

Measure gateway overhead separately from inference latency, under stated load
and payload conditions. Set numeric objectives only after measuring the intended
deployment. Fault injection and recorded-provider tests should supplement normal
success cases; ordinary CI remains secret-free.

## Integrated platform demonstration

A procurement owner authors a rubric and reviews a grounded assistant. Its
domain package references approved tools and restricted knowledge. A designer
binds those assets to an approval profile and environment. A published deployment
answers with authorized evidence, prepares a purchasing action, pauses for
approval, and executes only the approved action.

The owner can inspect the relevant run, reviewer assessments, policy decisions,
source versions, usage, and action outcome. A proposed prompt/provider change
runs against a regression dataset before promotion. An unauthorized Finance user
can invoke a specifically shared supplier-status capability but cannot read
Procurement's contract collection or private evaluation evidence.

This scenario connects products without requiring all of them for the first
gateway release. It is a design target, not a shipped demo.

## Turn proposals into work

Before implementation, select unresolved decisions from [the register](decisions.md),
record settled architectural choices as ADRs, and create small WUs with scope,
dependencies, done criteria, and executable qualification. Update architecture
sections in the same implementation change. Keep one WU per PR.

Do not invent detailed distant WUs or dates before customer evidence and
interfaces justify them. A future feature's qualification scenario becomes a
test with that feature; this documentation does not introduce runtime invariants
without implementation.
