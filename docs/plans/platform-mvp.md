# Platform MVP implementation

Source: maintainer request to "start the implementation of the MVP" and create
reusable layers, including middleware, where necessary.

The first release remains console plus management API and governed chat, as
defined in [the product design](../platform/gateway.md). The foundation below
starts implementation; it does not itself constitute the release. No platform
API is production-qualified until identity, authorization, persistence, evidence,
and the supported inference paths have been exercised together.

## WU-34 — Define the first MVP implementation slice

- [x] **Status:** complete.
- **Scope:** This program and its roadmap rows only.
- **Done:** WU-35 has bounded ownership, explicit runtime/non-runtime claims,
  dependency decisions, and executable acceptance criteria.
- **Deps:** WU-33.
- **Architecture:** §12 unchanged; implementation updates it in WU-35.
- **Freeze:** none. No shapes, edges, fixtures, schemas, or dependencies change.
- **Decision:** Preserve ADR 0006 and the selected product stack.
- **Open:** none for defining the foundation. Future identity and resource
  contracts are deliberately outside this WU.

## WU-35 — Connect the console through reusable platform layers

- [x] **Status:** complete.
- **Scope:** One runnable foundation from Nuxt console through a typed management
  client to FastAPI. Own `platform/`, platform verification scripts and CI wiring,
  root ignore/tool-discovery adjustments, this status row, architecture §12, and
  the associated implementation ADR. Create only packages exercised by this path:
  UI layer, platform shell layer, and management client. Reusable ASGI middleware
  stays inside `services/gateway/app/middleware/`; no separate HTTP distribution.
- **Done:** A built console displays actual service availability through the
  typed client, with explicit unavailable/retry states. HTTP tests prove generated
  request identity, safe error responses, concurrent isolation, and streaming
  transparency. Contract/boundary checks, strict typing, isolated deployment-source import,
  frontend production build, browser smoke coverage, and the repository gate pass.
- **Deps:** WU-34 and accepted ADR 0006. Inference integration later consumes
  the WU-22–32 public APIs; this foundation does not modify or duplicate them.
- **Architecture:** §12, plus ADR 0009 for reusable HTTP and frontend
  boundaries and the initial public, non-sensitive system-status contract.
- **Freeze:** none. Kernel fields, shapes, nodes, edges, censuses, fixtures,
  extension keys, and stream conversion contracts remain unchanged.
- **Decision (dependencies):** An isolated gateway uv project/lock and a platform npm workspace/lock;
  FastAPI/Starlette and Uvicorn in the product workspace; Nuxt/Vue/TypeScript,
  Tailwind and owned shadcn-vue components in frontend layers. Platform packages
  are private. No new dependency in distributed ocai libraries.
- **Decision (HTTP):** Pure ASGI middleware, per-request generated identifiers,
  allowlisted completion metadata, sanitized errors, no body/stream buffering,
  and no inferred tenant identity from request headers. Startup creates explicit
  app instances; modules have no import-time registry or logging setup.
- **Decision (console):** The UI layer owns styling/components; the platform
  layer owns reusable shell composition; the app owns the status page; a plain
  TypeScript package owns the management client. Same-origin API proxying has a
  fixed configured upstream and exposes only this WU's status operation.
- **Out:** Authentication bypasses, dummy tenant data, database administration,
  authorization models, provider requests, production readiness, accounting,
  durable audit, and unimplemented product navigation. The readiness endpoint
  must not advertise a production-ready gateway at this stage.
- **Open:** none for this slice. Exact auth and resource contracts are qualified
  in subsequent WUs before any protected administration or inference is exposed.

## WU-71 — Record platform identity and access design

Source: maintainer request to "document everything you have documented on your
answers so far so we do not loose this knowledge" before further implementation.

- [x] **Status:** complete (documentation; review pending).
- **Scope:** Own the identity design, its ADR, architecture §12.2, platform
  overview/stack/security/direction cross-references, documentation navigation,
  and this WU's roadmap entry.
- **Done:** A linked design records the protocol/local-login strategy, reference
  provider rationale and alternatives, frontend/backend ownership, service
  interconnection, non-human identities, delegation limits, operations and
  qualification requirements without presenting them as implemented features;
  repository verification passes.
- **Deps:** WU-33 and WU-35.
- **Architecture:** §12.2; §12.1 implementation claims remain unchanged.
- **Freeze:** none. No shapes, nodes, edges, censuses, fixtures, fields, extension
  keys, provider options, streaming contracts, schemas or dependencies change.
- **Decision:** [ADR 0013](../decisions/0013-platform-identity.md); preserve
  ADRs 0006 and 0009 and the independent kernel boundary.
- **Out:** Runtime code, package changes, identity-provider deployment, production
  support claims, and implementation of subsequent identity workflows.
- **Open:** none for recording the design. Version/library selection, session
  persistence, realm mapping, revocation bounds and permission synchronization
  are explicitly assigned to future implementation WUs.

## Next slices to define

Define each as a separate WU before implementation, keeping one observable
workflow per PR. This ordering is a dependency guide, not completed scope:

1. PostgreSQL migrations and an OIDC-backed organization/session workflow;
   implement the selected Keycloak reference and Nuxt server session boundary
   from [the identity design](../platform/identity.md), with controlled bootstrap,
   one protected operation, logout and durable audit.
2. OpenFGA resource checks, organizations/teams/service accounts, and scoped-key
   administration with durable audit and tested revocation behavior. Include
   service-account OAuth client-credentials access. Qualify direct customer OIDC,
   brokered SAML and workload federation separately; preview agent delegation
   remains outside the initial production dependency set.
3. Provider connection/deployment administration and versioned configuration,
   with secret handling and approved egress.
4. Native and OpenAI-compatible governed chat, unary and streaming, through
   public ocai contracts, with correlated receipts and cancellation.
5. Admission limits, usage ledger/reconciliation, request inspection, exports,
   and production outage/isolation qualification.

The platform overview remains the product scope; later slices must resolve its
open decisions explicitly and must not turn these headings into implied runtime
support. Security verification accompanies each owning feature.
