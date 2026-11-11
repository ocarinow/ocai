# 0011 — First authenticated console implementation contract

- **Status:** proposed; accepted when the WU-72 plan is merged or approved in place
- **Date:** 2026-11-10
- **Deciders:** maintainer through plan review

## Context

[ADR 0013](0013-platform-identity.md) establishes the identity boundaries but
leaves persistence, session policy, bootstrap and permission synchronization to
implementation qualification. The first workflow needs concrete defaults before
it can expose protected organization administration. The detailed WUs and their
acceptance evidence are in [the identity program](../plans/platform-identity.md).

## Decision

Use PostgreSQL with typed SQLAlchemy 2.x, psycopg 3 and Alembic for platform state.
Principal IDs are stable UUIDs; external identities bind verified issuer/subject
pairs uniquely. Organization-owned repositories require explicit scope. Database
roles separate migrations, gateway operations, Nuxt sessions, Keycloak and OpenFGA.
Do not claim database row-level security until independently implemented/tested.

Use `joserfc` for backend JWT verification and `openid-client` for Nuxt's
server-side OIDC flow. The first reference profile is one configured Keycloak
realm per installation, a confidential console client, RS256 access tokens and
a dedicated API audience. Production requires HTTPS, exact callback URLs and
explicit secrets. Local loopback-only development exceptions must be isolated
from production validation. No untrusted token value selects a network endpoint.

Store opaque console sessions in a separate PostgreSQL schema through Node `pg`.
Hash random session IDs; encrypt server-held tokens and login verifiers with
fixed AES-256-GCM using the runtime's cryptographic implementation, record-bound
additional data, fresh nonces and an externally supplied versioned key. No
application-written cryptographic primitives. Require session-bound CSRF and
origin checks for mutations/logout. Host-only Secure HttpOnly SameSite=Lax
cookies carry no tokens. Sessions expire after 30 minutes idle or 8 hours absolute;
login transactions are one-use and expire after 5 minutes. Reference access
tokens expire after 5 minutes, with at most 30 seconds clock tolerance.

Refresh leases and compare-and-set version checks prevent concurrent replicas
from reusing rotated credentials or reviving a logged-out session. Local logout
invalidates server session state regardless of provider availability; it is not
a claim of globally revoking all already-issued access tokens.

Bootstrap is an explicit operator command consuming installation bootstrap state
transactionally. It binds an operator-verified issuer/subject to the first
organization owner. No first-login-wins, public owner-claim endpoint or email-only
account linking. Organization owner can read/update, viewer can read. Platform
permissions do not derive from identity-provider administrative roles.

PostgreSQL owns grants and writes desired authorization revision, outbox and
audit in the same transaction. A serialized per-organization projector updates
OpenFGA idempotently against a pinned model and records applied revision after
confirmation. Protected actions require matching desired/applied revisions,
current active principal/membership and a fresh OpenFGA decision. Pending or
unavailable authorization produces a sanitized 503, never an implicit allow.
Mutations serialize/recheck relevant membership and revision before commit so
permission revocation races have a defined order. No positive authorization cache
is introduced in the initial workflow.

The first management operation reads/updates an organization's display name with
optimistic resource versioning. Mutation and durable allowlisted audit commit
together. Runtime audit privileges do not allow modification/deletion, without
claiming protection from database administrators or immutable-storage certification.
Missing and inaccessible resource identifiers share outward behavior.

Machine access follows through owned platform service accounts, explicit OAuth
bindings and scoped API keys. Initial service-account grants permit organization
read only. API keys require explicit expiry (30-day default, 90-day maximum in
this profile), show-once secrets and hashed storage; rotation overlaps are explicit
and bounded to 24 hours. Platform suspension/revocation is checked independently
of an OAuth token's remaining lifetime. No preview delegation dependency.

## Alternatives considered

- In-memory sessions: cannot support replica failover or coherent logout. JWT
  browser cookies containing refresh tokens undermine the chosen token boundary.
- Another session database immediately: PostgreSQL already provides the required
  durable store and transactional concurrency; Redis is not needed by this workflow.
- Dual synchronous PostgreSQL/OpenFGA writes without recovery: partial failures
  leave ambiguous authority. An outbox and revision gate make pending access
  explicit, at the cost of temporary unavailability during synchronization.
- Token roles or long-lived cached grants as the only check: cannot enforce our
  current memberships, suspension and resource-specific permissions.
- Unbounded login/key lifetime or silent development fallbacks: make configuration
  mistakes persistent authority. Explicit finite bounds are testable defaults.
- Immediate full enterprise federation, arbitrary ABAC and agent delegation:
  exceed the first workflow and need their own protocol/resource qualification.

## Consequences

The first workflow spans WU-73–77; machine access spans WU-78–80. Each WU has
real-service integration acceptance and ships through its own PR. State, audit and
authorization are available before protected UI mutations; a login screen alone
does not establish the workflow's completion.

Operational configuration includes database roles, encryption keys, pinned issuer
and model identity, service versions and upgrade/recovery procedures. The outbox
requires bounded retries, monitoring and an operator recovery path. Key rotation,
refresh/logout races, permission projection crashes and dependency outages are
required tests, not deferred hardening. The main gate must run those integrations
without real customer credentials, and must fail rather than silently skip them.

Versions are locked in implementing WUs; changing the above security defaults or
ownership boundaries needs a successor decision with evidence. No implementation,
new dependency, runtime schema or production support claim is delivered by this ADR.
