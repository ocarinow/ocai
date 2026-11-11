# 0013 — Platform identity and session boundaries

- **Status:** accepted direction; internal identity/authorization implemented, console/workloads pending
- **Date:** 2026-11-10
- **Deciders:** maintainer, following the platform identity design discussion

## Context

The platform needs local login without customer infrastructure, enterprise
OIDC/SAML federation, service accounts, scoped API keys, and eventual agent
delegation. The Nuxt/FastAPI foundation has none of these yet. Later products must
share stable identity and permission semantics without requiring every call to
pass through the AI Gateway. The maintainer requested preservation of the design
before further implementation.

## Decision

Use Keycloak as the reference bundled identity provider, deployed separately.
Keep direct integration with qualified customer OIDC providers possible. Broker
SAML through an established provider; local passwords, recovery and MFA belong
to the identity provider. Use OIDC Authorization Code with PKCE for browser login.

Nuxt's server layer owns the console's OIDC callback and opaque browser session;
tokens stay server-side. FastAPI validates API access tokens or platform API keys
and enforces resource authorization. Keep platform identity integration in modular
gateway application code initially. OpenFGA evaluates relationships and qualified
conditions; platform code supplies trusted context and enforces decisions.

Platform principal IDs, organization/compartment membership, resource grants,
service-account ownership and audit semantics remain independent of the provider.
OAuth clients/API keys are credentials bound to principals. Federation uses verified
issuer/subject bindings, not email-based account merging. Future services enforce
their own audience and resource permissions.

Service accounts and client credentials form the initial machine-access model.
Human-delegated agent authority is distinct from a worker's own permissions and
requires subject/actor preservation and task restrictions. Do not depend on
preview delegation for the initial production release. Exact versions, providers,
libraries, persistence, TTLs and revocation behavior require implementing WUs.

The detailed requirements, protocol references, alternatives and acceptance matrix
live in [the identity design](../design/platform/identity.md).

## Alternatives considered

- Custom password/federation service: adds protocol and credential-management
  responsibility unrelated to the platform's AI capabilities.
- Mandatory external customer identity provider: fails the standalone local-login
  requirement. Mandatory Keycloak everywhere would unnecessarily constrain customers.
- Browser-held access/refresh tokens: unnecessary for the server-rendered Nuxt
  console; a server session keeps bearer credentials out of browser application state.
- Separate custom platform auth microservice immediately: no second backend
  consumer yet; modular boundaries preserve extraction without another deployment.
- Provider-specific roles as the complete permission model: insufficient for our
  compartments, resource grants, API-key restrictions and delegated task policies.
- Authentik, ZITADEL and Ory: credible alternatives with different feature,
  licensing and integration tradeoffs, documented in the identity design.

## Consequences

We must own identity-provider packaging, upgrades, backups, recovery, and support
policy. A supported distribution may be needed for customers requiring longer
maintenance windows. Standard OIDC and narrow administrative adapters limit coupling;
they do not make provider migration or account linking automatic.

Implementation must qualify CSRF/session behavior, token validation/rotation,
cross-tenant isolation, revocation, audit durability, database/OpenFGA consistency,
and dependency outages. The existing public status proxy remains credential-free.
No kernel contract, distribution dependency, schema, or runtime behavior changes
in this decision. The platform is not authenticated or production-ready merely
because these boundaries are recorded.
