# Evidence observability and evaluation contracts

> **Proposed design, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Status: proposed shared satellite contracts, first exercised by the gateway.
No event schema, persistence engine, or transport is frozen here.

## Scope and identity

The gateway produces evidence for model access. Agent runtimes, retrieval
services, tools, and applications instrument their own execution boundaries.
A gateway cannot independently observe whether a business action succeeded or
a retrieved document was relevant. Direct ocai consumers should be able to
emit the same contracts without using the gateway server.

Distinguish tenant, compartment, project/workspace, application definition,
deployment, session, run, step, logical call, attempt, and event identities.
Not every producer needs every identity. A call may have multiple attempts;
a durable run may span several distributed traces. Parent and causal links
must represent asynchronous work without requiring a single uninterrupted span.

Use a small versioned event envelope with typed payloads. Candidate envelope
fields include event identity/type/version, producer identity/version,
authenticated scope, subject and causal references, occurrence and ingestion
times, policy/configuration versions, and payload/artifact references. Names
and schemas remain open. Caller-supplied correlation is not authorization.

## Separate guarantees

| Evidence class | Purpose | Proposed guarantees |
|---|---|---|
| Diagnostic logs | Debug a component | Structured, redacted, searchable; configurable retention |
| Traces and metrics | Explain latency, errors, saturation, and execution | Correlation, aggregation, explicit sampling and cardinality policies |
| Audit records | Attribute actions and authorization decisions | Durable delivery, controlled access, retention and integrity controls |
| Usage ledger | Attribute consumption and charges | Deduplication, reservations, reconciliation, provenance, explicit corrections |
| Evaluation records | Assess behavior against criteria | Versioned rubrics, evaluators, datasets, targets, results, and review history |

Sampled traces cannot substitute for required audit records or accounting.
Administrative changes and execution decisions both need evidence. A successful
logging callback does not establish durable storage. Human assessment, automated
scores, end-user feedback, and release approvals are distinct record types.

## Execution receipt

A logical call receipt should reference the authenticated principal and scope,
application/deployment versions, effective policy, selected endpoint/interface,
converter artifact identity, attempts and reasons, fidelity findings, consumption,
pricing provenance, and terminal or incomplete status. Link to authorized payload
evidence where retained rather than embedding all content in every record.

Separate declared conversion properties, observed per-payload effects, and
conformance evidence. Preserve the difference between provider-reported,
locally estimated, reconciled, and unknown usage. Receipts need authorization
on lookup and export; a hard-to-guess identifier is insufficient access control.

## Delivery and integrity

Define acknowledgement and persistence points for required evidence. A practical
candidate is durable local/outbox recording plus retriable delivery and consumer
deduplication; final mechanisms depend on deployment topology. Do not promise
global event ordering or exactly-once external actions.

Record producer sequence where useful, tolerate duplicate and out-of-order
delivery, and identify missing or unfinished execution. Reconciliation handles
process crashes, expired reservations, and later-arriving provider usage.
Corrections reference prior records rather than silently changing history.

For governed operations, decide whether durable intent evidence must precede
the effect. Define behavior when evidence storage is unavailable or buffers are
full. Tamper evidence, retention locking, and verification procedures require
their own design; a content hash alone does not establish authenticity or
completeness.

## Privacy and access

Separate metadata from prompts, outputs, source excerpts, attachments, and
artifacts. Set payload capture, redaction, encryption, retention, deletion,
and export controls by compartment and data classification. Secrets never enter
telemetry. Even metadata and hashes may disclose sensitive information.

Access to an execution summary need not permit access to its payload. Access
changes must affect traces, exports, review queues, and derived datasets as well
as the primary application. Define deletion and retention-lock conflicts before
offering either guarantee; preserve only permitted non-content evidence after
payload deletion. Record who viewed or exported restricted evidence.

## Monitoring and evaluation

Monitor availability, time to first output, total latency, stream aborts,
retry amplification, saturation, cost uncertainty, evidence ingestion lag,
and policy/fidelity violations. Choose measurable service objectives per product
and deployment; no numeric SLA is assumed here.

Evaluation links a target version/run to a rubric, dataset version, evaluator
version/configuration, scores, explanations, and evidence references. Distinguish
conversion fidelity from answer quality and business success. Judge-model
results are assessments, not ground truth; calibrate against expert review and
record disagreement and uncertainty.

The [human evaluation workflow](authoring.md#human-evaluation) supplies domain
review and acceptance. Controlled experiments can test suspected causes of
regressions; a version correlation alone does not establish causality.

## Interoperability and replay

Map to [OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/) through
versioned adapters. Keep our evidence and accounting contracts independent of
a particular trace backend. Exporters should support existing customer systems;
using the gateway must not require adopting our observability product.

Recorded conversion can be replayed when inputs and exact artifacts are retained.
Live generation cannot generally be reproduced exactly, even with a recorded
model name. Provider aliases may change; record available revision evidence and
its limits. Replaying tools with effects requires explicit authorization and
separate safety controls, not a generic trace replay button.
