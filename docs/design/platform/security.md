# Platform security and enterprise trust

> **Proposed design, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Status: proposed security requirements and qualification plan. These controls
are not implemented or certified by this documentation. Detailed threat models,
owners, tests, and release gates belong to implementing WUs.

## Boundaries and verification

Threat-model browser sessions, management operations, inference, authorization,
storage, secrets, providers, telemetry, and later custom execution. Include
malicious callers, compromised credentials, accidental misconfiguration, and
dependency failures. Document customer-hosted operating responsibilities.

| Boundary | Proposed requirement | Qualification example |
|---|---|---|
| Organization and compartment | Scope access across primary data, caches, exports, jobs, and evidence | Substitute another organization's resource ID through every API surface |
| Administration and content | Infrastructure administration does not automatically grant payload access | An operator can rotate a connection without reading conversations |
| API key and principal | Effective authority is key scope intersected with current principal permissions | Revoked membership/key cannot keep using an old cached grant beyond the documented bound |
| Provider connection | Credentials stay outside caller-visible results and diagnostics | Inject secret-bearing upstream errors and verify every output channel |
| Gateway egress | Only approved destinations and network paths are eligible | Reject unauthorized URLs, redirects, and infrastructure metadata access |
| Agent execution | Authorize each tool action using trusted delegated context | Model output cannot expand authority or bypass required approval |

Use tenant-aware database access, with PostgreSQL row-level security as a proposed
additional barrier where appropriate. Test pooled connection context and database
roles. No storage control substitutes for resource authorization in the service.

## Authentication, authorization, and secrets

The [identity design](identity.md) and [ADR 0013](../../decisions/0013-platform-identity.md)
record Keycloak selection, local and federated login, Nuxt server sessions,
FastAPI enforcement, non-human identities and inter-service delegation. These
are architectural requirements; the foundation has no authentication yet.

Integrate established identity providers and federation implementations. Proposed
baseline: OIDC, privileged MFA through the identity provider, secure browser
sessions, CSRF protection where applicable, expiration, and revocation. Identify
federated users by issuer and subject rather than email alone. Define explicit
organization membership and trusted group mappings.

Use separate service identities. Platform API keys are shown once, stored as
hashes, scoped, expiring, rotatable, and revocable. Provider secrets require a
secret store or encrypted storage with separately managed keys; they cannot use
one-way hashes because the driver must apply them. Exclude secrets from ordinary
configuration exports and telemetry.

Enforce authorization in the backend for lists, direct access, exports, streaming
admission, and background work. OpenFGA is an authorization engine, not the
identity provider or enforcement middleware by itself. Define revocation bounds,
in-flight behavior, synchronization, and cache invalidation. Enabled OpenFGA
caches can return stale decisions; choose consistency deliberately using its
[consistency guidance](https://openfga.dev/docs/interacting/consistency).
If permission cannot be established, reject the protected operation.

## Data, audit, and financial controls

Default payload capture to off. An explicit capture policy defines scope, access,
redaction, retention, deletion, and export. Apply these controls to derived
evaluation datasets and artifacts as well as production requests. Encryption,
residency, backups, and recovery must cover all relevant data paths.

Keep diagnostic telemetry, security audit, and usage accounting separate as
described in [evidence](evidence.md). Proposed management-write design: commit a
durable audit event alongside the state change and export it asynchronously.
Audit sensitive reads, exports, permission changes, key lifecycle, and provider
configuration. Restrict deletion and detect missing delivery. Immutable storage
or tamper-evidence claims require independently verified deployment controls;
a hash alone is insufficient.

Bound concurrency, request size, execution time, retries, tokens, and spending.
Reservations and idempotent ledger updates must tolerate concurrent admission,
duplicate events, crashes, and later usage reconciliation. Unknown consumption
stays unknown. Separate billing administration from inference permissions; use
an established payment processor if payment collection is introduced.

## Future execution security

Treat prompts, retrieved instructions, model outputs, and tool descriptions as
untrusted inputs. Trusted platform code authorizes each proposed action. Bind
approval to the exact action, arguments, target, identity, and expiry; recheck
authorization when executing. Custom code needs isolation appropriate to its
trust level, with controlled filesystem, network, credentials, and resources.
Callbacks do not sandbox untrusted code. This addresses the permissions and
autonomy risks described by [OWASP Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).

## Delivery evidence

Proposed application verification target: applicable OWASP ASVS Level 2
requirements, with documented applicability and gaps. Use NIST SSDF as a
development-process reference. Neither target establishes certification or
conformance until assessed. References: [ASVS](https://asvs.owasp.org/) and
[SSDF](https://csrc.nist.gov/pubs/sp/800/218/final).

| Stage | Proposed evidence |
|---|---|
| Gateway MVP | Threat model; authorization/isolation abuse tests; secret, dependency, and artifact checks; bounded execution; durable audit; secure deployment defaults |
| Enterprise production | Independent penetration assessment and remediation; restore and incident exercises; measured revocation behavior; release inventory/provenance; customer security documentation |
| Platform expansion | Delegated execution tests; sandbox qualification; approval and retrieval-revocation tests; additional isolation tiers; formal assurance as justified |

Maintain a requirements matrix giving each control an owner, enforcement point,
test/evidence reference, and release milestone. Exercise dependency outages and
partial failures, including unavailable authorization and audit services. Publish
supported versions, vulnerability reporting, patch response, incident handling,
backup/recovery responsibilities, and retention/deletion behavior.

SOC 2 or ISO 27001 are possible later assurance initiatives, not current claims.
Preserve operational evidence from the beginning and describe actual product
guarantees and deployment responsibilities accurately.
