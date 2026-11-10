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

## Next slices to define

Define each as a separate WU before implementation, keeping one observable
workflow per PR. This ordering is a dependency guide, not completed scope:

1. PostgreSQL migrations and an OIDC-backed organization/session workflow;
   qualify the identity-provider reference and browser session boundary.
2. OpenFGA resource checks, organizations/teams/service accounts, and scoped-key
   administration with durable audit and tested revocation behavior.
3. Provider connection/deployment administration and versioned configuration,
   with secret handling and approved egress.
4. Native and OpenAI-compatible governed chat, unary and streaming, through
   public ocai contracts, with correlated receipts and cancellation.
5. Admission limits, usage ledger/reconciliation, request inspection, exports,
   and production outage/isolation qualification.

The platform overview remains the product scope; later slices must resolve its
open decisions explicitly and must not turn these headings into implied runtime
support. Security verification accompanies each owning feature.
