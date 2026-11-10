# 0009 — Platform application and reusable layers

- **Status:** accepted for the first implementation slice
- **Date:** 2026-11-10
- **Deciders:** maintainer layout clarification; WU-35 implementation

## Context

ADR 0006 separates products from public libraries. The maintainer clarified that
the gateway should use `services/gateway/app/` and that shared HTTP middleware
does not yet justify a separate package or Python distribution. The console
still needs reusable UI and application-shell layers from its first workflow.

## Decision

Use an isolated, non-package uv project and lockfile in `services/gateway/`.
`app/main.py` composes FastAPI; `app/middleware/` contains pure ASGI request
infrastructure and safe error handlers. No extra Python namespace or wheel is
introduced. Future extraction requires a real second consumer.

Keep one npm workspace/lockfile under `platform/`. The console extends
`nuxt-platform`, which extends `nuxt-ui`. The UI layer owns tokens and generic
components; the platform layer owns a shell with navigation/content slots; the
console owns pages and product navigation. The plain TypeScript management client
uses types generated from the committed OpenAPI document and validates the
initial status response at runtime. These packages are private.

Initial endpoints expose only public health and non-sensitive system status.
Readiness stays unsuccessful until inference is qualified; no authentication
bypass, example organizations, or fake operational statistics are introduced.
The console server proxies only the fixed status operation to an operator-chosen
upstream, without forwarding user credentials/headers or following redirects.
It does not yet provide an authenticated session boundary.

Each HTTP request receives a server-generated ID, independent of incoming headers.
Request state is local to the ASGI scope. Middleware never reads or buffers bodies,
so chunks and cancellation pass through. Pre-header errors become a sanitized
envelope; errors after headers interrupt delivery without a replacement body.
Diagnostic events allowlist metadata and never serialize arbitrary exceptions,
request paths/queries, headers, or payloads. Passive observer failures cannot alter
authorization or substitute for durable audit. Authentication, authorization,
OpenTelemetry export, and durable evidence remain separate future work.

## Alternatives and consequences

A new `platform-http` package and `src/ocarinow_gateway` distribution were
rejected as premature packaging. Putting product middleware in public `ocai`
libraries would violate the kernel boundary. Using one oversized Nuxt layer would
couple visual components to platform state and product navigation.

Independent Python/JavaScript environments add setup steps. The repository gate
and CI exercise both, including API/type drift, library/platform boundaries,
concurrent request isolation, sanitized failures, stream transparency, source
deployment isolation, and the built console's connection/retry experience.
This foundation is not the complete Gateway MVP or a production security claim.
