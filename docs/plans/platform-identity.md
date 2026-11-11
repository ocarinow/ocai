# Authenticated console and machine access

Source: the maintainer approved proceeding with publication of the identity
design, definition of the implementation work units, the first authenticated
console workflow, and then machine access ("Do it").

This is the implementation sequence for [ADR 0013](../decisions/0013-platform-identity.md).
It consumes the existing Nuxt/FastAPI foundation. Each WU has one observable
workflow, one branch and one PR. This plan does not mark identity features as
implemented. WU-72 records the plan; WU-73–80 implement it in order. Implementation
may proceed on stacked PRs: the maintainer approved proceeding in place on
2026-11-11. Each implementation remains separately reviewable; plan merge is not
a prerequisite for starting these approved entries.

## Acceptance workflow

An operator provisions local identity infrastructure and bootstraps an explicit
user as the first organization owner. That user signs into the console, views
their organization, changes its display name, observes confirmation, and signs
out. PostgreSQL holds the state change and durable audit evidence atomically.
An unauthenticated user, a member without the action permission, and a user from
another organization cannot perform the same operation. Subsequent WUs let an
owned service account read its authorized organization through OAuth or a scoped
API key and demonstrate that suspension/revocation removes that access.

This workflow establishes identity and management, not a production inference
gateway. Inference readiness remains false. Teams, nested compartments, enterprise
SSO administration, SCIM, agent delegation and provider connections follow in
separate plans; there is no implicit grant to those future resources.

## Implementation decisions

[ADR 0011](../decisions/0011-authenticated-console-contract.md) records the proposed
implementation contract. It becomes accepted with this plan's merge or explicit
approval in place. Routine implementation choices are fixed here to avoid another
design pause before each WU:

| Concern | Contract |
|---|---|
| Persistence | PostgreSQL; SQLAlchemy 2.x typed async unit of work, psycopg 3 driver, Alembic migrations |
| Python token verification | `joserfc` for JOSE with explicit algorithms and claim validation; `httpx` for bounded metadata/key retrieval |
| Nuxt OIDC client | `openid-client` server-side; no custom OAuth or signature implementation |
| Console session storage | PostgreSQL separate schema/runtime role; Node `pg`; encrypted token material with key supplied outside the database |
| First issuer profile | One configured Keycloak realm per installation; confidential console client; dedicated API audience; RS256 access tokens |
| Bootstrap | Explicit operator CLI binds a verified issuer/subject pair to the first owner; no public registration/bootstrap HTTP endpoint |
| First permissions | Organization `can_read` and `can_update`; owner and viewer relationships; no realm-admin or email-derived platform authority |
| Synchronization | PostgreSQL authoritative grants + transactional outbox; per-organization desired/applied authorization revisions and pinned OpenFGA model |
| Evidence | State change and allowlisted audit event in one database transaction; no external exporter dependency for commit |
| Initial session policy | 30-minute idle and 8-hour absolute limit; 5-minute one-use login transaction; 5-minute access tokens; at most 30-second clock tolerance |
| Authorization freshness | No positive decision cache in this workflow; check current principal status, membership and authorization revision on protected requests |
| Deployment | Version-pinned disposable development/CI services; production configuration rejects missing secrets, unsafe issuer URLs and insecure cookie settings |

Exact package patch versions and container digests are locked in the WU introducing
them, after registry/security checks and compatibility verification. No floating
`latest` images, no provider SDKs, no new public library distributions. Do not
select experimental or preview features to satisfy an acceptance criterion.

Use separate database roles for migrations, gateway runtime, console sessions,
identity provider and OpenFGA. Never use the migration/admin role for requests.
The deployment can share a PostgreSQL server without sharing table privileges.
The initial application repositories require organization scope explicitly; SQL
row-level security is a later defense and is not claimed by this workflow.

## Shared ownership and verification

All WUs own their listed product files and the necessary portion of platform
verification, CI, documentation and architecture §12. Kernel source, root `spec/`,
conversion fixtures and the parallel integration program are out of scope.
Backend modules remain inside `platform/services/gateway/app/`; frontend reuse
stays in the established Nuxt layers and typed management client. Add only modules
consumed by the WU. No empty future package scaffolds.

Implementation tests use real disposable PostgreSQL/OpenFGA/Keycloak services for
the behavior they claim. Recorded or locally generated adversarial protocol inputs
supplement those integrations; mocks alone do not qualify authentication. No real
user/provider secrets or cloud accounts are needed. Service provisioning belongs to
an explicit test runner/fixture with teardown, bounded waits and isolated ports;
missing dependencies fail the required integration job rather than silently skip it.

Each WU wires its checks into `scripts/check.py` through the platform gate and CI,
and reports the literal summary. Use the same service versions locally and in CI.
Keep unit-only iterations available, but do not label them the full gate. Do not
change public liveness or foundation status to expose deployment secrets.

## WU-72 — Define the authenticated console program

- [x] **Status:** complete (plan; review pending).
- **Goal:** Make the authenticated-console and machine-access program executable as one bounded, reviewable PR per workflow.
- **Scope:** This plan, ADR 0011, architecture §12.2 cross-reference, roadmap,
  MVP/identity design links and site navigation.
- **Done:** WU-73–80 have bounded ownership, explicit acceptance tests, ordered
  dependencies, protocol/security decisions and scope exclusions; documentation
  and full repository checks pass.
- **Deps:** WU-71 (publication may be stacked for review).
- **Architecture:** §12.2; no implemented behavior changes.
- **Integration:** Platform planning only: ADR 0011 and the identity program connect architecture section 12.2 to WU-73–80; runtime dependency arrows stay unchanged.
- **Freeze:** none; no kernel shapes/nodes/edges/fields/extensions/options,
  streaming, fixtures, dependencies or schemas change in this planning WU.
- **Decision:** Preserve ADRs 0006, 0009 and 0010; propose ADR 0011.
- **Out:** All runtime implementation, deployment and production support claims.
- **Open:** none for the bounded plan. Advanced federation and resource models
  remain outside this program, not blockers on its first workflow.
- **Area:** platform
- **Priority:** P1
- **Tier:** program
- **Owner:** Codex

## WU-73 — Persist organization identity and transactional audit

- [x] **Status:** complete (implementation; review pending).
- **Evidence:** Real PostgreSQL 16.15 tests cover migration/restart persistence,
  audit and outbox rollback, identity uniqueness, scoped reads/composite foreign
  keys, concurrent grant revision ordering, cancellation, stale writes and runtime
  privilege/schema rejection. The full gate includes these tests and requires
  Docker. See [operations](../../platform/README.md).
- **Goal:** Provide durable organization identity state and atomic audit evidence so later authenticated operations cannot succeed without their recorded state transition.
- **Scope:** Gateway `app/storage/`, initial `migrations/`, project/lock,
  PostgreSQL development/test provisioning, storage integration tests, platform
  gate/CI wiring and operating instructions.
- **Done:** Against a real fresh PostgreSQL database, an explicit migration and
  unit of work persist principal, issuer/subject binding, organization, membership,
  authorization revision/outbox and audit records; successful commit survives a
  restart, injected audit failure rolls back the whole mutation, duplicate identity
  bindings are rejected, and organization-scoped reads cannot cross boundaries.
- **Deps:** WU-72.
- **Architecture:** §12.2 plus implemented persistence subsection in §12.
- **Integration:** Platform service: app.storage settings → Database transaction → scoped Repository → SQLAlchemy/psycopg → PostgreSQL; operator Alembic migrations establish schema and grants. No dependency flows into public ocai packages.
- **Freeze:** none; platform-only database schema. No kernel or streaming changes.
- **Decision:** SQLAlchemy/psycopg/Alembic; explicit database settings and pool
  lifecycle; parameterized queries; stable UUID principal/resource IDs; unique
  issuer/subject bindings. Tenant-owned records use scoped constraints/foreign keys.
  Audit records contain action, actor, target, organization, request ID and safe
  outcome metadata; no tokens or raw request bodies. Runtime audit role cannot
  update/delete audit rows; this is not an immutable-storage certification.
- **Decision (migration):** Run migrations as an operator command, never on each
  worker's startup. Verify role privileges and schema version, bound pool/query
  waits, sanitize connection failures. Downgrade/reset commands are test-only or
  explicitly destructive operator actions, not automatic startup recovery.
- **Out:** HTTP tenant endpoints, bootstrap, identity provider, OpenFGA calls,
  console sessions, APIs for future grants/resources, production RLS claims.
- **Open:** none. Dependencies and image versions lock during implementation.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex

## WU-74 — Authenticate API callers through the reference issuer

- [x] **Status:** complete (implementation; review pending).
- **Evidence:** Real Keycloak Authorization Code + S256 PKCE login, access-token
  acceptance and ID-token rejection; adversarial claims, headers, rotation/outage
  tests; full repository gate passed. Local PostgreSQL-backed Keycloak and
  gateway/console startup verified through `serve:*` tasks.
- **Goal:** Verify reference-provider access tokens into a trusted external identity context before any protected API can resolve a platform principal.
- **Scope:** Gateway `app/identity/` verifier/context, configured app lifecycle,
  Keycloak development/CI provisioning, token-validation tests, explicit runtime
  dependencies and safe error handling. Include `tasks/serve.Taskfile.yml`, the
  root include, local Compose/helper configuration and generated task catalogue
  for service startup with infrastructure/package dependencies (maintainer request).
- **Done:** A real Keycloak Authorization Code login yields an access token which
  the gateway authentication dependency validates; tests reject ID tokens, wrong
  issuer/audience/algorithm, expired or malformed tokens and forged headers, and
  verify bounded signing-key refresh/rotation without fetching caller-chosen URLs.
- **Deps:** WU-73.
- **Architecture:** §12.2 plus implemented authentication subsection in §12.
- **Integration:** Platform service: explicit issuer configuration → bounded HTTP discovery/JWKS cache → joserfc verification → trusted identity dependency; storage resolves bindings. Keycloak supplies credentials; middleware never infers identity from caller headers.
- **Freeze:** none; platform identity context only, no kernel changes/streaming.
- **Decision:** Use `joserfc`, explicit issuer/API audience and RS256 allowlist.
  Verify the reference access-token profile (including token type); distinguish
  authenticated external identity from a bound, active platform principal. Never
  create an organization/membership just because login succeeds. No untrusted
  `iss`, `jku`, `x5u` or `kid` selects a network destination or filesystem path.
- **Decision (outage):** Fixed, bounded HTTP requests; a signing-key cache with
  maximum 5-minute freshness, single-flight refresh and unknown-key rate limiting.
  Valid tokens may use fresh cached keys during issuer outage; unknown/stale keys
  fail closed. Authentication infrastructure failure is sanitized 503, invalid
  credentials 401; neither falls back to unauthenticated access.
- **Decision (deployment):** Generate disposable credentials explicitly, bind
  local-only services to loopback, never check in usable default admin passwords.
  Production uses HTTPS and exact redirect URIs. A separately selected local
  profile may use loopback HTTP; it must not disable verification in production.
- **Out:** User-facing login/session UI, account self-registration, public tenant
  administration endpoints, introspection/opaque-token support, direct customer
  OIDC certification, SAML, delegated agent tokens and machine authentication.
- **Open:** none; key rotation and ID-token rejection are acceptance conditions.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex

## WU-75 — Bootstrap an organization with synchronized access

- [x] **Status:** complete (implementation; review pending).
- **Evidence:** Fourteen authorization tests cover real PostgreSQL/OpenFGA
  bootstrap races, permission isolation, crash recovery, revocation serialization,
  suspension, model rejection and bounded reconciliation. Full repository and
  strict documentation checks pass. The local PostgreSQL-backed deployment was
  verified from Keycloak login through operator bootstrap and worker projection.
- **Goal:** Create the first organization owner safely and project explicit organization permissions into OpenFGA without treating partial synchronization as authorization.
- **Scope:** Operator bootstrap command, initial OpenFGA model/adapter and
  outbox reconciler, principal/membership repository integration, bootstrap and
  authorization integration tests, deploy/test service configuration.
- **Done:** An operator explicitly provisions the first owner and organization
  once; concurrent/replayed bootstrap cannot claim a second owner. Real OpenFGA
  grants owner read/update and viewer read only, denies another organization,
  and interrupted grant projection never permits use of stale authority.
- **Deps:** WU-74.
- **Architecture:** §12.2 plus implemented bootstrap/authorization subsection.
- **Integration:** Platform service: operator bootstrap → storage transaction with memberships/audit/outbox → serialized projector → OpenFGA → applied revision. Request authorization checks platform state plus pinned-model decisions.
- **Freeze:** none; internal platform authorization model/version only.
- **Decision:** Bootstrap takes the configured issuer and exact subject inspected
  by the operator in the trusted provider. Require an explicit installation
  bootstrap state and serialize consumption transactionally; no first-login-wins,
  email-based owner assignment or permanently enabled bootstrap endpoint.
- **Decision (projection):** PostgreSQL owns relationships; changes write audit,
  outbox and desired authorization revision atomically. One serialized reconciler
  per organization writes idempotent tuple changes against a pinned model and
  marks applied revision only after confirmation. Reject protected operations
  with 503 while revisions differ or synchronization cannot be established.
  Check current principal/membership status and use OpenFGA higher consistency;
  never treat the consistency option alone as a cross-database transaction.
- **Decision (races):** A management mutation rechecks/locks the relevant revision
  and membership before commit; a concurrent revocation either precedes and denies
  the action or follows its committed audit event. Outbox retries cannot reorder
  old grants after new revocations. Test crashes before/after tuple writes.
- **Out:** Arbitrary role editor, team/compartment inheritance, delegated grants,
  production multi-region synchronization, public registration and browser login.
- **Decision (implementation):** Seed a singleton installation identity during migration;
  operator bootstrap consumes it and pins the OpenFGA store/model atomically.
  Check the exact reviewed model at adapter startup. Use OpenFGA 1.22.1 with
  authenticated HTTP and bounded requests; tuple retries use duplicate/missing
  ignore semantics. Real tests exercise crashes around acknowledgement and
  serialization between permission revocation and an audited mutation.
- **Open:** none for the owner/viewer organization model.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex

## WU-76 — Establish durable OIDC console sessions

- [x] **Status:** complete (PR #115).
- **Evidence:** `platform/tests/session/session.spec.ts` qualifies real Keycloak
  login/refresh across two console processes, replay/browser binding, CSRF,
  nonce rejection, expiry, ciphertext tampering/key rotation, production cookie
  flags, invalid startup, concurrent refresh/logout and provider outage.
  The full repository gate and strict documentation build pass; the exact gate
  summary and tested commit are recorded in PR #115.
- **Goal:** Let users sign in and out through durable console sessions while keeping access and refresh tokens out of browser application state.
- **Scope:** Reusable Nuxt server identity/session modules in `nuxt-platform`,
  console route wiring and sign-in/out UI, console-session schema migration,
  server-only dependencies/configuration, real-provider browser/session tests.
- **Done:** Browser login through real Keycloak establishes an opaque session
  that works across two console instances and renewal; logout, idle/absolute
  expiry and a concurrent refresh cannot revive the session, and tokens never
  appear in browser storage, hydrated state, URLs after callback, or diagnostics.
- **Deps:** WU-75 and WU-81 (maintainer-directed shared component foundation).
- **Architecture:** §12.2 plus implemented browser-session subsection.
- **Integration:** Nuxt server modules in nuxt-platform use openid-client → Keycloak and pg → separate session schema. The console consumes shared session presentation; server credentials never enter nuxt-ui or client bundles.
- **Freeze:** none; platform routes and console-only persistence are provisional.
- **Decision:** `openid-client` server-only Authorization Code + S256 PKCE,
  state/nonce and issuer checks; one-use login transaction bound to the initiating
  browser; registered callback and allowlisted relative return destinations.
  Nuxt owns session state. FastAPI remains the API credential validator.
- **Decision (storage):** PostgreSQL session schema with a dedicated Nuxt role;
  migration owner manages schema, gateway request role has no token-table access.
  Random 256-bit session identifiers stored as hashes; tokens/login verifiers
  encrypted with fixed AES-256-GCM through Node's crypto implementation, fresh
  nonce, record-bound additional data and key ID. Keys are supplied explicitly
  outside the DB; missing/invalid keys fail startup. Test key rotation and reject
  tampered ciphertext without leaking it. Do not implement cryptographic primitives.
- **Decision (lifecycle):** Host-only HttpOnly Secure SameSite=Lax session cookie
  in production; 30-minute idle/8-hour absolute limits. No offline tokens.
  Refresh uses a bounded database lease/version check; logout invalidates the
  row/version so a late refresh cannot recreate it. Use bounded refresh requests
  and fail closed after ambiguity rather than reuse an uncertain rotated token.
- **Decision (CSRF):** Mutation/logout require same-origin validation and a
  session-bound CSRF token; reject cross-origin requests. Route guards are only
  presentation. Session responses are no-store and are never shared-cached.
  Local logout is guaranteed; provider logout is explicit best effort and cannot
  be presented as global token revocation. Cleanup expires sessions and login
  transactions without logging their secrets.
- **Out:** Persistent login across the absolute bound, cross-app cookies,
  back-channel logout certification, public registration and enterprise SSO UI.
- **Open:** none; password recovery/MFA remain provider responsibilities.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex

### Design sketch

The shared Nuxt layer owns fixed login, callback, session and logout routes.
A dedicated PostgreSQL role accesses only the console session schema. Login
transactions are browser-bound and consumed before token exchange; encrypted
records bind their ciphertext to the hashed record identifier. Refresh acquires
a 15-second lease and increments a version, then writes rotated tokens only
if that version still exists and is unexpired. Logout deletes the record before
any optional provider sign-out. An expired lease is terminal, never reclaimable.
Production enables the module explicitly and fails startup on invalid settings;
the public foundation can run with the module disabled.

## WU-77 — Update an organization through the authenticated console

- [ ] **Status:** in progress; protected management workflow and qualification.
- **Goal:** Deliver the first complete authenticated product workflow: an organization owner can change a display name with resource authorization and durable audit.
- **Scope:** Organization read/update API, request/response contracts and typed
  client, console organization settings, fixed Nuxt authenticated forwarding,
  application authorization/audit composition and end-to-end tests.
- **Done:** The acceptance workflow at the top of this plan runs against real
  services: owner signs in, reads and renames their organization, observes the
  persisted change and audit event, and signs out; viewer, foreign-organization
  and unauthenticated attempts leave both organization state and success audit
  unchanged, and unavailable required dependencies cannot produce success.
- **Deps:** WU-76.
- **Architecture:** §12.2 plus the implemented management workflow in §12.
- **Integration:** Console feature → fixed Nuxt authenticated route → typed management client → FastAPI identity/resource checks → OpenFGA plus scoped storage transaction → audit and versioned response.
- **Freeze:** none; platform OpenAPI/client changes only; no streaming/inference.
- **Decision (API):** `GET /management/v1/me` returns the current bound principal
  and authorized organization summaries; `GET` and `PATCH
  /management/v1/organizations/{id}` read/update a display name. Resource responses
  include a version; update requires that version and returns conflict on stale
  writes. Trim/validate a nonempty bounded display name; no arbitrary field patch.
  Missing and inaccessible resource IDs have the same outward 404 response.
- **Decision (composition):** Authenticate, resolve scoped resource, authorize,
  recheck current membership/revision under transaction, mutate and write audit
  in one commit. Restrict product errors to safe envelopes; request IDs link to
  durable evidence. Audit failed access with bounded metadata through the security
  evidence path; no raw token/body or sensitive display-name content in diagnostics.
- **Decision (frontend):** Reuse platform session/context/permission helpers;
  keep the organization page in the console. Backend-derived capabilities only
  guide UI. Proxy fixed routes/methods, validate parameters and payloads, attach
  the server-held access token, reject redirects, clear scoped state on organization
  switch and handle 401/403/404/409/503 without leaking other tenants' data.
- **Out:** Generic user/role management, arbitrary resources, audit-search UI,
  provider connections, inference and production-ready status.
- **Open:** none. This is the first complete authenticated product slice.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex

## WU-78 — Administer owned service-account principals

- [ ] **Status:** defined.
- **Goal:** Make non-human actors accountable platform principals with explicit ownership and narrowly delegated organization access.
- **Scope:** Service-account persistence/lifecycle, organization-scoped API and
  console administration, OpenFGA resource model extension, audit and integration
  tests. Credential issuance belongs to the following WUs.
- **Done:** An authorized organization owner creates, inspects and suspends an
  owned service account with explicit read access to that organization; another
  organization's owner cannot discover or modify it, and its grants cannot exceed
  the creator's delegable authority.
- **Deps:** WU-77.
- **Architecture:** §12 identity and management subsections updated in the WU.
- **Integration:** Console administration → management API → scoped service-account storage and audit → authorization outbox/OpenFGA resource relationships; credential bindings remain separate.
- **Freeze:** none; platform-only service-account resource and model migration.
- **Decision:** Require purpose and accountable owner; one organization per
  service account in this slice. Default to no grants; initial supported grant
  is organization read only. Suspension removes access independently of issued
  token expiry. Audit creation/grants/suspension; expose no credential material.
- **Out:** Service-account administration of other principals, agents, wildcard
  grants, team/compartment grants, keys or OAuth client provisioning.
- **Open:** none; broader grant types require owning resource WUs.
- **Area:** platform
- **Priority:** P1
- **Tier:** 2
- **Owner:** Codex

## WU-79 — Bind OAuth workloads to service accounts

- [ ] **Status:** defined.
- **Goal:** Allow a provisioned workload to use OAuth client credentials while preserving current platform suspension and resource restrictions.
- **Scope:** Narrow Keycloak administrative adapter/operator provisioning,
  verified external credential bindings, service-principal authentication and
  real client-credentials integration tests. Reuse existing resource authorization.
- **Done:** A separately provisioned Keycloak client obtains a short-lived access
  token and reads only its service account's authorized organization; wrong audience,
  conflicting binding, human-token substitution and suspension deny access even
  when an old token remains cryptographically valid.
- **Deps:** WU-78.
- **Architecture:** §12 identity/credential subsections updated in the WU.
- **Integration:** Operator provider adapter → Keycloak confidential client → access token → FastAPI verifier → service-principal binding → existing organization authorization and audit.
- **Freeze:** none; platform credential binding only.
- **Decision:** Bind issuer, subject and expected client identity to an active
  service principal. Separate bindings from roles/grants. Provision credentials
  explicitly to a restricted operator destination; never print them in CI/logs
  or return client secrets through ordinary management reads. Use least-privilege
  IdP administration outside gateway request handling. Check active platform
  status on each admitted request; disabling the IdP client is not sufficient.
- **Out:** Kubernetes/SPIFFE federation, external token exchange, preview client
  delegation, automatic trust of arbitrary issuer/client combinations.
- **Open:** none; confidential-client secret authentication is the initial
  qualified profile, with asymmetric/federated profiles added separately.
- **Area:** platform
- **Priority:** P1
- **Tier:** 2
- **Owner:** Codex

## WU-80 — Issue and revoke scoped platform API keys

- [ ] **Status:** defined.
- **Goal:** Provide show-once, expiring API credentials for service accounts with explicit scope and tested rotation/revocation.
- **Scope:** Service-account key lifecycle, hashed storage, API authentication,
  console show-once issuance/revocation, audit and integration tests.
- **Done:** An owner issues an expiring key for their service account's explicit
  organization-read grant, sees it only once, uses it successfully, rotates it
  with bounded overlap, and revokes it; expired/revoked keys or suspended principals
  cannot use previously valid access, and cross-organization attempts fail.
- **Deps:** WU-79.
- **Architecture:** §12 identity/credential subsections updated in the WU.
- **Integration:** Console issuance → protected management operation → hashed key storage/audit; incoming key → credential resolver → active principal and scope intersection → existing resource authorization.
- **Freeze:** none; provisional platform credential/API schema only.
- **Decision:** Generate a 256-bit random secret with a distinct opaque public
  key identifier; store a one-way digest, compare safely, never expose digest or
  secret in listings/logs. Require explicit expiry (default 30 days, maximum
  90 days for this initial profile) and scopes; no wildcard or never-expire mode.
  Effective access intersects current grants, key scope and organization policy.
  No positive key-auth cache. Rotation creates a new key and explicit expiry of
  the old one (default immediate; bounded overlap at most 24 hours); audit both.
- **Decision (HTTP):** Distinguish platform-key format from JWT access tokens;
  reject ambiguous/multiple credentials instead of trying fallback authenticators.
  Issuance is POST with CSRF protection and no-store; transport failure after
  commit cannot reveal the secret later, so revoke/reissue rather than retrieve.
- **Out:** Provider secrets, human-bound personal keys, inference scopes before
  inference is implemented, arbitrary downstream token minting or delegation.
- **Open:** none. Enterprise key-policy customization is a later explicit WU.

- **Area:** platform
- **Priority:** P1
- **Tier:** 2
- **Owner:** Codex

## References and follow-on scope

Primary references supporting these integration choices:
[openid-client](https://github.com/panva/openid-client),
[joserfc claims and signatures](https://jose.authlib.org/en/guide/jwt/),
[SQLAlchemy async session ownership](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html),
[psycopg concurrency](https://www.psycopg.org/psycopg3/docs/advanced/async.html),
[OpenFGA consistency](https://openfga.dev/docs/interacting/consistency).
Security claims are established by the WUs' tests and deployment evidence, not
by these dependencies alone.

After WU-80, define provider-connection management and governed inference from
the [MVP sequence](platform-mvp.md). Enterprise SAML/direct-OIDC onboarding,
SCIM, workload federation, resource-specific teams/compartments, human delegation,
audit search/export and deployment SLO qualification retain separate ownership.


## WU-81 — Integrate the full shadcn-vue component layer

Maintainer request: "Integrate in the layer all the shadcn-vue components so we do not have to do this after."

- [x] **Status:** complete — 68 upstream UI families, shared registration and
  neutral theme, higher-layer Ocarinow overrides, full typing and browser checks.
- **Goal:** Make the complete upstream shadcn-vue component catalogue available to
  every platform app through one reusable Nuxt layer, with Ocarinow presentation
  supplied above that layer instead of rebuilding primitive components.
- **Scope:** `platform/packages/nuxt-ui`, brand theme overrides in `nuxt-platform`,
  console component consumption, frontend manifests/lock, component catalogue
  provenance, documentation and layer/browser validation. Registry component files
  are a mechanical upstream import; no bespoke replacements or wrapper catalogue.
- **Done:** All components from the committed upstream UI registry snapshot are installed and
  type-check through the consuming console; shadcn module exports resolve from the
  shared layer; the console renders actual registry components with higher-layer
  Ocarinow theme tokens, and unused component families do not add JavaScript to its client bundle.
- **Deps:** WU-75 as the current platform stack; this foundation precedes WU-76.
- **Architecture:** §12.1 and the UI layer implementation notes in §12.
- **Integration:** Console extends nuxt-platform (product shell/theme overrides),
  which extends nuxt-ui (upstream shadcn-vue components and neutral theme).
  Components are registered with shadcn-nuxt and consumed directly; no public
  language package imports platform code. No authentication behavior changes.
- **Freeze:** none; private platform components and build configuration only.
- **Decision:** Use shadcn-vue 2.9.0 CLI and committed registry snapshot with shadcn-nuxt
  ([ADR 0012](../decisions/0012-shadcn-component-layer.md));
  import the full UI catalogue as explicitly requested. Preserve upstream source
  and license attribution. Keep brand decisions in higher-layer CSS overrides.
- **Out:** Custom primitive design, authentication/session implementation,
  copying example applications or marketing blocks, a new public UI distribution.
- **Open:** none.
- **Area:** platform
- **Priority:** P1
- **Tier:** 1
- **Owner:** Codex
