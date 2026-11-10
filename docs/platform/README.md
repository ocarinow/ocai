---
icon: lucide/layers
---

# Platform

ocai is the kernel of an enterprise AI platform. The kernel is one call →
one `CallResult`; everything a platform adds — governance, observability,
evaluation, registries, agent execution, a gateway — is built **on** the
kernel's contracts as a satellite library or a separate service, never
inside `ocai.core` (architecture [§11](../architecture.md#11-adding-a-capability-normative-recipe),
the scope litmus test). This section documents those modules as they are
defined and built.

!!! warning "Status: planned"

    No platform module is implemented today. The pages in this section are
    definitions, decisions, and readiness plans. Each module page carries
    its own status badge; read it before assuming any behavior exists.

| Module | What it is | Status |
|---|---|---|
| Gateway | A governed service in front of the kernel: the single entry point for AI capabilities, exposing the canonical `ocai` interface over the wire | Readiness plan under review (WU-21) |
| Telemetry | Observer-driven export of `Route`, `FidelityReport`, and `Usage` to tracing and metrics backends | Planned |
| Audit | Content-addressed archive of post-redaction wire exchanges, fed by `WireTap` | Planned |
| Eval | Reproducible evaluation runs keyed by `Route` + catalog lock hash + `FidelityReport` | Planned |
| Registries | Typed, versioned registries of tools, skills, and MCP servers | Planned |
| Agent runtime | Durable tool-calling loops with checkpoints, approvals, and honest mid-run provider failover | Planned |

What the kernel already provides for them: pure, serializable transcripts
(a checkpoint format for free); `ProviderRef` anchors that make provider-side
state portable or honestly `UNSUPPORTED`; the `Decision` vocabulary
(`Proceed | Retry | Fail | Return`) that an approval gate or budget cap can
reuse; `CallContext(tenant, principal, classification, deadline, tags)` as the
governance carrier; and `Catalog.lock()` so a fleet can run one signed
conversion catalog. The gaps found while designing on top of it are tracked
in [kernel gaps](../plans/gaps.md).

Conventions for this section: one directory per module as it gets defined,
each with a `README.md` index page; a status badge at the top of every page
(planned, provisional, implemented); decisions in
[Decisions](../decisions/README.md), not here.
