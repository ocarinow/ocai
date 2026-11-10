# Identity and secrets

**Currency:** researched 2026-11-10 against cloud-provider and secret-manager
documentation as published that day. Auth schemes are stable; product
packaging (Bedrock API keys, Foundry token audiences) is not, and is cited to
the page read. Anything not confirmed from an official page is marked
*unverified*.

**Status:** planned. The kernel ships the `Credential` protocol and one
implementation, `ApiKey` (header + scheme, `from_env`, `from_file`, redacted
`repr`). No cloud credential, no secret-manager binding, and no signing code
exist in any ocai distribution.

## 1. Why this family matters to ocai

Rule 13 is the kernel's strongest security statement: *credentials are
explicit-only — no ambient discovery; applied by the driver at the leaf, per
attempt, after all hooks; redacted; never in `raw`, reports, or
`provider_options`.* Rule 12 adds the only exception to "no provider SDKs":
*a narrow signing library inside a cloud-hosting plugin.* Everything in this
family is an implementation of those two rules against real identity systems.
The design question is not "which secret manager do we support" but "how does
a `Credential` value get its secret without the kernel ever discovering one on
its own".

## 2. Landscape

### 2.1 How each provider authenticates a request

| Target | Scheme | What goes on the wire | Lifetime / rotation |
|---|---|---|---|
| OpenAI, Anthropic, Gemini (API key) | Static API key | `Authorization: Bearer <key>` (OpenAI); `x-api-key: <key>` plus `anthropic-version` (Anthropic); Gemini key as header or query (*header name not re-verified here*) | Until revoked; rotation is a manual or secret-manager concern |
| AWS Bedrock (SigV4) | AWS Signature Version 4 over the request (canonical request → string to sign → HMAC-SHA256 signing key scoped to date/region/service → `Authorization` header); temporary credentials add `X-Amz-Security-Token`; SigV4a (ECDSA) signs once for several regions | `Authorization: AWS4-HMAC-SHA256 Credential=…, SignedHeaders=…, Signature=…`, `X-Amz-Date`, and the content hash header (*exact header name not on the page read*) | Access keys long-lived; STS temporary credentials expire; a request must reach AWS within five minutes of its timestamp (replay protection) |
| AWS Bedrock (API keys) | Bearer token instead of SigV4 | `Authorization: Bearer <key>`; env var `AWS_BEARER_TOKEN_BEDROCK` is read by the AWS SDKs | Short-term keys: up to 12 h, region-bound, inherit the generating IAM principal (recommended for production; `aws-bedrock-token-generator` libraries cache and refresh). Long-term keys: IAM user service-specific credential with an expiry, "for exploration only". IAM actions `bedrock:CallWithBearerToken`, `bedrock-mantle:CallWithBearerToken`, condition key `bedrock:bearerTokenType` ∈ `SHORT_TERM`/`LONG_TERM` |
| Google Vertex AI | OAuth 2.0 access token from Application Default Credentials (local `gcloud auth application-default login`; attached service account on Google Cloud compute, "the preferred authentication method"; Workload Identity Federation off-cloud); API keys only for `generateContent`/`streamGenerateContent` (bill to a project, do not identify a caller) | `Authorization: Bearer <access-token>` | Tokens are short-lived (lifetime *not stated on the page read*; conventionally one hour, *unverified*); WIF exchanges an external IdP token through the Security Token Service (OAuth 2.0 token exchange), with direct resource access recommended over service-account impersonation (`roles/iam.workloadIdentityUser`) |
| Azure OpenAI / Microsoft Foundry | Microsoft Entra ID bearer token for audience `https://ai.azure.com/.default` (data plane; the page read uses this audience, older material uses `https://cognitiveservices.azure.com/.default` — *the relationship between the two is unverified*), control plane `https://management.azure.com/.default`; or the `api-key` header | `Authorization: Bearer <token>` via `get_bearer_token_provider(DefaultAzureCredential(), audience)`; roles `Cognitive Services OpenAI User`/`Contributor`; managed identities (system- or user-assigned, `AZURE_CLIENT_ID` selects one) | Entra tokens are short-lived and refreshed by the credential chain; managed identities have no secret to rotate; service principals carry a client secret or certificate the owner rotates |

### 2.2 Secret stores

| Store | Model | Machine access | Rotation |
|---|---|---|---|
| HashiCorp Vault | Secrets engines; KV v2 is versioned with soft delete; dynamic secrets with leases/TTL (database engine) | Auth methods mounted under `auth/<type>`: Token, AppRole, AWS, Azure, Google Cloud, Kubernetes, JWT/OIDC, TLS certificates, SPIFFE, and others; client tokens with TTLs; Vault Agent / Proxy and the Secrets Operator inject secrets | Operator-set TTLs; external-method renewals re-check the IdP |
| AWS Secrets Manager | Secret with staging labels | IAM; `GetSecretValue` (*API name not on the page read; conventional*) | Managed rotation (no Lambda) for managed secrets; managed external secrets for partner-held secrets; Lambda rotation functions for the rest |
| Google Secret Manager | Secret (global or regional) with versions; versions can be disabled/destroyed; CMEK via Cloud KMS; AES-256 at rest by default | IAM roles and conditions; version history records who changed what | Rotation supported; Pub/Sub notifications *unverified on the page read* |
| Azure Key Vault | Vaults (keys, secrets, certificates; software or HSM-backed) and Managed HSM pools | Entra ID only: managed identity (recommended), service principal + certificate, service principal + secret (discouraged); TLS with PFS | Versions per secret; the page stresses that managed identity removes the "first secret" rotation problem |
| Infisical | Open-source platform for secrets, certificates, privileged access, "AI agent access"; organizations/projects/members; machine identities with roles | Machine identities (auth methods *not named on the page read*) | Rotation and dynamic credentials listed as workflows |
| Doppler | Hosted SecretOps; projects/configs; versioning and logs | Service tokens (read-only access to one config); API; syncs to AWS/GCP/Vercel | Rotation *not described on the page read* |
| 1Password | Service accounts (up to 100 per account, vault-scoped, usage reports) for CLI/CI; Connect server recommended for production | Service account token; CLI secret references (`op://…`, *syntax not on the page read*); SDKs | Human-managed items; Connect for self-hosted access |

### 2.3 Workload identity in one line

The industry direction on every cloud is the same: *no long-lived secret on
the workload.* AWS: short-term Bedrock keys or STS credentials from an
instance/role; GCP: attached service accounts on-cloud and Workload Identity
Federation off-cloud ("service account keys are powerful credentials that are
risky if poorly managed"); Azure: managed identities ("there's no secret for
you to store or rotate"); Vault: Kubernetes/JWT/cloud auth methods that trade
a platform identity for a short-lived Vault token. A credential model that
assumes a static string is already behind the market.

## 3. What the kernel has today

```python
class Credential(Protocol):
    def apply(self, request: HttpRequest) -> None: ...
```

- `apply` is called **once per attempt, just before send**, at the driver
  leaf — "so a short-lived/rotating credential can resolve its current value
  at send time". The protocol is already shaped for rotating and
  token-exchanging credentials; it needs no change.
- `ApiKey(key, header="Authorization", scheme="Bearer")` with `from_env(var)`
  and `from_file(path)` — the *only* sanctioned reads of env/filesystem, and
  only when called. `repr` redacts; `__eq__`/`__hash__` compare values without
  exposing them.
- `CredentialError(OSError)` is deliberately outside the `OcaiError` taxonomy:
  a missing secret is an operator fault, not a call outcome.
- `Vertex(project, region)` host value documents that "authentication is a
  separate Google OAuth/ADC `Credential`, not this host's concern" — hosting
  composes with credentials, never bundles them.
- Observers receive `WireExchanged.request` **post-redaction** by
  construction: every `WirePolicy` and interceptor runs before `apply`.
  Nothing in the hook chain can see a secret; this is structural, not a
  convention.

What is missing: any `Credential` whose secret comes from a signer, a token
exchange, or a secret store.

## 4. Verdict

### 4.1 `Credential` implementations are satellites, one per source

Secret-store bindings are `ocai-vault-*` satellites (the prefix is generic:
`ocai-vault-hashicorp`, `ocai-vault-aws`, `ocai-vault-gcp`,
`ocai-vault-azure`, `ocai-vault-infisical`, …). Each exports `Credential`
values whose `apply` resolves the current secret *at send time* from the
store's client, with the store's own caching and renewal (Vault leases,
Secrets Manager client-side cache, Entra token refresh). They depend on
`ocai.core` only (the protocol is in core) plus the store's client library —
which is why they cannot live in the kernel (rule 12 keeps third-party
clients out of `ocai`).

The contract for every satellite, testable:

1. No ambient discovery: constructing the credential takes an explicit
   locator (secret path, ARN, resource URI); the satellite never walks a
   default credential chain *unless the caller constructs the chain
   explicitly* (`AzureEntraToken(DefaultAzureCredential(), audience)` is
   explicit; `AzureEntraToken()` reading the environment is not allowed).
2. Resolution happens in `apply`, never in `__init__`, so a rotated secret is
   picked up on the next attempt without rebuilding the model.
3. `repr`, logs, `CallResult.raw`, reports, and `provider_options` never
   contain the secret — inherited from the leaf-application rule, verified by
   a shared conformance test the kernel ships for satellites (the same
   pattern as plugin conformance in WU-20).
4. Failure to resolve raises `CredentialError`, never an `OcaiError`.

### 4.2 Cloud identity is a credential too, not a host concern

`Vertex` (and a future `Bedrock`/`Foundry` host) stays a pure URL and envelope
transformer. The identity side becomes:

| Credential (satellite) | Wraps | Applies |
|---|---|---|
| `GoogleAccessToken` (`ocai-gcp`) | a `google-auth` credentials object the caller built (ADC, WIF credential configuration, impersonated SA) | `Authorization: Bearer` with refresh on expiry |
| `AzureEntraToken` (`ocai-azure`) | an `azure-identity` `TokenCredential` the caller built, plus the audience string | `Authorization: Bearer` |
| `BedrockBearerToken` (`ocai-bedrock`) | the short-term key provider (`aws-bedrock-token-generator`) or a long-term key | `Authorization: Bearer` |
| `SigV4Credential` (`ocai-bedrock`) | AWS credentials (static, STS, or a provider chain the caller constructed) and a signer | SigV4 headers over the canonical request |

The first three are header writers over a token provider; they are ordinary
satellites. The fourth is the rule-12 exception.

### 4.3 SigV4 lives inside the Bedrock plugin, through a narrow signer

SigV4 needs the full request (method, URL, headers, body hash) — exactly
what `Credential.apply(request)` receives — so the protocol fits without
change. The signing library is the sanctioned "narrow signing library inside
a cloud-hosting plugin". Options, in order of preference: a small
pure-Python SigV4 implementation vendored or pinned (the algorithm is
documented and stable), `botocore.auth` (brings all of botocore — too wide),
or the AWS CRT signer (native extension). Recommendation: a dedicated
minimal SigV4/SigV4a signer dependency, pinned in `ocai-bedrock`, with the
`X-Amz-Security-Token` path tested with recorded pairs under rule 10 (the
signature over a recorded request is deterministic given a fixed
`X-Amz-Date`, which makes it fixture-testable without live keys).
`BedrockBearerToken` is the simpler default for new deployments and avoids
the signer entirely; SigV4 remains necessary for IAM-role-only environments
and for every non-runtime Bedrock operation.

### 4.4 What the gateway and agent runtime need from this family

- A **credential reference without the secret** in transcripts and
  checkpoints (the modernization plan's open decision: "credential references
  without secrets in transcript data"). Proposal: a `CredentialRef(kind,
  locator)` value in `ocai.core` — the locator a satellite can resolve, never
  the material — so a replayed run names *which* credential it used
  (`vault:kv/teams/payments/openai`) and an auditor can match it to the
  store's access log. It is pure data, zero-dependency, and belongs in core.
- Per-tenant isolation remains "several models built from different
  credentials/catalogs"; the gateway's virtual-key table maps to
  `CredentialRef`s and resolves them through satellites at composition time.

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| Satellite conformance test for `Credential` implementations (no ambient discovery, resolve-in-`apply`, redaction everywhere, `CredentialError`) — shipped by the kernel like plugin conformance | **P1** | — |
| `CredentialRef` value in `ocai.core` (pure data) | P1 (needed by audit and the agent runtime checkpoint format) | — |
| `ocai-gcp` `GoogleAccessToken` (unblocks Vertex, which already has a host value) | P1 (first real non-API-key credential; H2 Gemini-on-Vertex) | H2 |
| `ocai-bedrock` with `BedrockBearerToken` first, `SigV4Credential` second | P2 (Bedrock is not among the three providers "plenty until v1", but it is the enterprise default host) | a Bedrock interface plugin |
| `ocai-azure` `AzureEntraToken` | P2 | an Azure/Foundry host value |
| `ocai-vault-hashicorp`, `ocai-vault-aws`, `ocai-vault-gcp`, `ocai-vault-azure` | P2 (thin; each is a token provider wrapped in a header writer) | conformance test |
| Infisical / Doppler / 1Password bindings | P3 (community or on demand) | conformance test |

## 6. Open questions and unverified items

- The Azure data-plane audience: the Foundry (classic) page read uses
  `https://ai.azure.com/.default`; the older `https://cognitiveservices.azure.com/.default`
  audience's current status is *unverified*.
- Vertex access-token lifetime and the Gemini API-key header name were not on
  the pages read.
- Google Secret Manager rotation notifications via Pub/Sub, Infisical auth
  method names, Doppler rotation, and 1Password secret-reference syntax were
  not on the pages read (*unverified*).
- Whether `CredentialRef` should be a kernel type or a satellite convention:
  the recommendation above is kernel, because the audit archive (G-02) and
  the transcript fixture class (G-03) both need to serialize it.
- Whether a `Credential` may *also* set non-auth headers (for example
  `anthropic-version` rides `DialectTraits`, not the credential) — keep the
  rule strict: a credential writes authentication material only.

## Sources

- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html (read 2026-11-10)
- https://docs.cloud.google.com/vertex-ai/docs/authentication (read 2026-11-10)
- https://docs.cloud.google.com/iam/docs/workload-identity-federation (read 2026-11-10)
- https://docs.cloud.google.com/secret-manager/docs/overview (read 2026-11-10)
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/managed-identity (read 2026-11-10)
- https://learn.microsoft.com/en-us/azure/key-vault/general/basic-concepts (read 2026-11-10)
- https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2 (read 2026-11-10)
- https://developer.hashicorp.com/vault/docs/auth (read 2026-11-10)
- https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html (read 2026-11-10)
- https://infisical.com/docs/documentation/getting-started/introduction (read 2026-11-10)
- https://docs.doppler.com/docs/start (read 2026-11-10)
- https://www.1password.dev/service-accounts/ (read 2026-11-10)
