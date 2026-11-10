# Gateways and routers

**Currency:** researched 2026-11-10 against vendor documentation as published
that day. Gateway feature sets move monthly; where a page did not state a
fact it is marked *unverified* rather than inferred.

**Status:** planned. The ocai gateway is the platform module "a governed
service in front of the kernel: the single entry point for AI capabilities,
exposing the canonical `ocai` interface over the wire" (platform README,
WU-21 readiness plan under review). Nothing is implemented.

## 1. Why this family matters to ocai

Every enterprise in this market already runs, or is evaluating, an LLM
gateway. The incumbents converge on one architecture: *expose the OpenAI wire
format as the universal API, translate to every provider behind it, and bolt
governance on the proxy.* ocai's gateway has to decide whether to join that
convention or to make the canonical `ocai` interface the wire API. The
decision is the single largest product choice in this family and is argued in
§4; the feature matrix in §2 is the baseline the gateway has to meet to be
credible at all.

## 2. Landscape

### 2.1 Products

| Product | Form | License / hosting | Wire API exposed |
|---|---|---|---|
| LiteLLM proxy ("AI Gateway") | Python proxy + Admin UI, Postgres-backed | MIT core; SSO/SAML, audit logs, multi-team are enterprise | OpenAI-compatible endpoint; `/chat/completions`, `/responses`, Anthropic `/v1/messages`, `/embeddings`, `/rerank`, `/audio/transcriptions` appear in its cache docs as cached endpoints; MCP tools and A2A agents through the same endpoint |
| Portkey AI Gateway | Hosted + OSS gateway | configs available on all plans; OSS license *unverified here* | OpenAI-compatible; per-request config via `x-portkey-config` header or SDK `config` |
| OpenRouter | Hosted router | proprietary | OpenAI-compatible; `provider` routing object; `usage.cost` in responses; `/api/v1/generation?id=` for post-hoc cost |
| Kong AI Gateway 2.x | Plugin set on Kong Gateway | OSS/Enterprise split *not stated on the pages read* | AI Model entity defines upstream provider, model, routing; policies as plugins |
| Cloudflare AI Gateway | Hosted edge proxy | available on all Cloudflare plans | Provider-specific paths plus model aliases, fallbacks, dynamic routes |
| Helicone AI Gateway | Rust OSS gateway | GPL-3.0 per sidebar, Apache per README (conflicting) | OpenAI-compatible `/ai` and `/router/<name>`; `provider/model` names |
| Vercel AI Gateway | Hosted | proprietary; zero markup on provider token prices incl. BYOK | `provider/model` strings; `https://ai-gateway.vercel.sh/v1` for OpenAI Chat Completions, Responses, and Anthropic Messages formats |
| TrueFoundry AI Gateway | Self-hosted (VPC, on-prem, air-gapped) + hosted | OSS status *not stated*; sub-3 ms internal latency claimed | OpenAI-compatible, 1,600+ models |
| Bifrost (Maxim) | Go OSS gateway | Apache 2.0 | OpenAI `/v1/chat/completions`; drop-in base paths `/anthropic`, `/genai` |
| Azure API Management AI gateway | Policies on APIM (all tiers) | Azure service | Imports OpenAI Chat Completions/Responses, Anthropic Messages (v2 tiers), Google Vertex AI schemas; "unified model API (preview)" exposes multiple backends through one OpenAI-compatible endpoint with format translation |
| AWS Bedrock | Cloud service | AWS | Native Converse/InvokeModel; OpenAI Responses and Chat Completions on `bedrock-runtime` (`/openai/v1`) and `bedrock-mantle` (`/v1`); inference profiles for cross-region routing and cost allocation |

### 2.2 Feature matrix

Legend: Y documented · P partial · — not found on the pages read · ? *unverified*

| Capability | LiteLLM | Portkey | OpenRouter | Kong | Cloudflare | Helicone GW | Vercel | TrueFoundry | Bifrost | Azure APIM | Bedrock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Virtual keys / auth | Y (`/key/generate`, `models`, `team_id`, `duration`, `key_alias`) | Y (virtual key `@slug`) | Y (API keys, BYOK) | Y (consumer keys) | Y (BYOK, stored keys ?) | Y | Y (API key or OIDC on Vercel) | Y | Y (virtual keys, OIDC enterprise) | Y (subscription keys, managed identity, credential manager) | Y (IAM, short/long-term API keys) |
| Budgets | Y (`max_budget`, `budget_duration`) | ? | Y (credits, `max_price`) | — | — | Y (dollar limits) | Y (team/project/key/member; HTTP 402 on exceed; BYOK metered separately) | Y | Y (hierarchical) | P (token quotas via `llm-token-limit`) | P (application inference profile tags → cost allocation) |
| Rate limits | Y (`rpm_limit`, `tpm_limit`) | ? | Y | Y (AI Rate Limiting Advanced) | Y | Y (requests/tokens/dollars) | Y (429 handling documented) | Y | Y | Y (`llm-token-limit`, `tokens-per-minute`, `estimate-prompt-tokens`) | Y (quotas per endpoint) |
| Routing / fallback | Y (`simple-shuffle`, `least-busy`, `usage-based-routing-v2`, `latency-based-routing`, `cost-based-routing`; `fallbacks`, `context_window_fallbacks`, `num_retries`, `allowed_fails`, `cooldown_time`) | Y (`strategy.mode` ∈ `fallback`, `loadbalance`; `weight`, `override_params`, `default_params`, `drop_params`) | Y (`order`, `allow_fallbacks`, `require_parameters`, `data_collection`, `only`, `ignore`, `quantizations`, `sort`, `:nitro`, `:floor`) | Y (`round-robin`, `consistent-hashing`, `least-connections`, `lowest-usage`, `lowest-latency`, `semantic`, `priority`; `retries`, `failover_criteria`, `max_fails`) | Y (aliases, fallbacks, dynamic routes) | Y (P2C + PeakEWMA, weighted, cost) | Y (provider order, model fallbacks, routing rules) | Y (latency, weighted, geo) | Y | Y (backend pools: round-robin, weighted, priority, session-aware; circuit breaker honors `Retry-After`) | Y (cross-region inference profiles, `global.`/`us.` prefixes) |
| Caching | Y (exact + semantic, many backends) | Y (`simple`/`semantic`) | — | Y (AI Semantic Cache) | Y | Y (Redis/S3) | ? ("caching" listed under models and providers) | ? | Y (semantic) | Y (`llm-semantic-cache-lookup`/`-store`) | prompt caching is the model's, not the gateway's |
| Observability | Y (Langfuse, Datadog, OTel, Prometheus callbacks) | Y (logs) | Y (generation endpoint) | P | Y (logs, analytics) | Y (Helicone + OTel) | Y (request logs: model, provider attempts, latency, tokens, cost) | Y (logs, traces) | Y (Prometheus, tracing) | Y (`llm-emit-token-metric`, prompt/completion logging to Azure Monitor) | Y (CloudWatch, invocation logging) |
| Guardrails | Y (content filters, PII masking) | Y (hooks) | — | Y (Prompt Guard, Semantic Prompt Guard, Sanitizer, Semantic Response Guard, AWS/Azure/GCP guardrail bridges) | Y | — | P (safety controls under security) | Y (PII, toxicity, injection) | Y (governance) | Y (`llm-content-safety`) | Y (Bedrock Guardrails; `X-Amzn-Bedrock-GuardrailIdentifier` headers on the OpenAI-compatible path) |
| Prompt management | — | Y (prompt library) | — | Y (AI Prompt Template, Prompt Compressor) | — | — | — | — | — | — | Y (Prompt management) |
| MCP | Y (MCP gateway; A2A agent gateway) | ? | — | ? (not on the pages read) | — | — | — | Y (MCP gateway with OAuth2/RBAC) | Y (MCP gateway, "MCP Code Mode") | Y (expose REST as MCP; govern existing MCP servers; A2A agent APIs; API Center as MCP registry) | Y (AgentCore Gateway) |
| Admin UI | Y | Y | Y (web) | Y (Konnect) | Y (dashboard) | P | Y | Y (UI + Playground + YAML/CLI) | Y | Y (portal) | Y (console) |

### 2.3 Wire-format strategy of the incumbents

Every row above except Bedrock and Azure APIM's native-import mode uses the
OpenAI request shape as the universal client API and translates behind it.
The caveats the vendors themselves document are the interesting part:

- OpenRouter: "unsupported parameters are ignored, such as `logit_bias` for
  non-OpenAI models"; `require_parameters: true` exists precisely so a caller
  can refuse routes that would drop fields.
- Portkey: `drop_params` removes fields by path; `override_params` always
  overwrites what the client sent.
- LiteLLM: `drop_params` is a well-known setting (not confirmed on the pages
  read this date — *unverified*).
- Bedrock's OpenAI-compatible Responses path: "`model` is required on every
  request, including one that supplies `previous_response_id`" (a divergence
  from OpenAI's spec), `background=true` is rejected on `bedrock-runtime`,
  server-side tools are unavailable there, and `GET /models` is not
  implemented on `bedrock-runtime`.
- Azure APIM's unified model API "handles format translation automatically"
  — with no published account of what each translation loses.

In other words: the OpenAI-format-everywhere approach is lossy by
construction, and the market's answer is a boolean (`drop_params`,
`require_parameters`) rather than a report.

## 3. What the kernel already provides a gateway

- A per-call ledger: `CallResult(value, route, report, usage, raw)` with
  `Route(capability, node, requested_interface, requested_tag, reason,
  catalog_hash, host)` and a `FidelityReport` whose `lossless` is derived.
- `Catalog.lock()` — one hash that names the exact conversion logic (down to
  plugin distribution versions) a fleet runs; `Route.catalog_hash` stamps it on
  every call.
- `CallContext(tenant, principal, classification, deadline, tags,
  extensions)` — the governance carrier a gateway populates from its own
  authentication layer.
- `CallInterceptor` for fallback, policy, cost, cache, tracing; the
  `Decision` vocabulary (`Proceed | Retry | Fail | Return`) for budget caps and
  approval gates; `RetryPolicy` (implemented), `RateLimitPolicy` and
  `WireTap` (stubs).
- Multi-tenant isolation "is several models built from different
  credentials/catalogs — plain Python, not a framework concept" (§5
  `binding.py`); a gateway is the place where that composition is driven by
  configuration instead of code.
- The canonical IR already has a dated wire identity: it *is* the interface
  named `ocai` with revisions `ocai@YYYY-MM`, with JSON Schema in `spec/`.
  Nothing extra has to be invented to put it on the wire.

## 4. Verdict

### 4.1 Baseline the ocai gateway must meet

Credibility requires parity on the governance rows of §2.2: virtual keys
bound to tenants (`CallContext.tenant`/`principal` populated by the gateway's
auth), budgets and rate limits per key/team (a `BudgetInterceptor` returning
`Fail` via the `Decision` vocabulary; `RateLimitPolicy` at the wire),
routing/fallback (a `FallbackInterceptor` that calls `next` several times
across targets — the §5 admission example), request logs (the `Observer`
events feeding the telemetry satellite), and an admin surface. Caching,
guardrails, prompt management, and MCP are satellites the gateway *mounts*,
not features it owns.

### 4.2 Differentiators — the ones no incumbent can copy cheaply

1. **A `FidelityReport` on every response.** The gateway returns, per call,
   what the conversion cost: every `FieldLoss` with its `Disposition`, every
   `SemanticShift`. The market's `drop_params` boolean becomes a census. This
   is the flagship WU (visible fidelity report) delivered over the wire.
2. **The catalog lock as fleet configuration.** A deployment pins one
   `Catalog.lock()` hash; every `Route` carries it; an auditor reproduces any
   call's conversion from the lockfile. No gateway today can say *which
   translation code* served a request six months ago.
3. **Interface migration without client change.** The `/responses` proof (H1)
   means the gateway can move a tenant from `openai/chat_completions` to
   `openai/responses` by configuration, with the migration cost reported, while
   the client keeps sending canonical `ocai` requests.
4. **Honest failover.** A cross-provider fallback is an ordinary conversion
   through certified edges; the `report` says what the second provider could
   not honor, instead of silently serving a degraded answer.

### 4.3 Canonical `ocai` wire API versus OpenAI-format-everywhere

The trade-off, argued both ways:

| | Expose canonical `ocai` interface | Expose OpenAI format |
|---|---|---|
| Client adoption | Needs an ocai client or a thin HTTP shim per language; `spec/` schemas make generated clients cheap, but it is a new thing to adopt | Every OpenAI SDK works by changing `base_url` — the reason every incumbent chose it |
| Fidelity | Canonical → provider is one certified edge; the report is exact | Client → OpenAI shape is *already* a lossy step the gateway cannot see (the client dropped Anthropic cache breakpoints before sending); the report can only cover gateway → provider |
| Version resilience | `ocai@YYYY-MM` is dated and migrates through `migrate.py`; OpenAI's shape is a sibling interface among others | The OpenAI shape itself splits (`/chat/completions` vs `/responses`), and the gateway inherits OpenAI's deprecations as its own API breaks |
| Honesty of streaming | One `ChatChunk` union, `StreamEnd(usage, finish, report)` — the report has a place in the stream | OpenAI SSE has no slot for a fidelity report; it would have to ride a custom trailing event or a header |
| Extension census | Namespaced `extensions` and `provider_options` are first-class | Provider knobs ride `extra_body` with no census |

**Recommendation: both, with a clear primary.** The canonical `ocai`
interface is the *primary* wire API — it is the only one on which the
differentiators in §4.2 are structurally expressible — and it is published
from `spec/` so clients are generated, not hand-written. An OpenAI-compatible
*compatibility listener* (`/v1/chat/completions`, `/v1/responses`) and an
Anthropic-compatible one (`/v1/messages`) are mounted as ordinary inbound
edges: the gateway decodes the OpenAI shape into `ocai@rev` through the
*existing* `openai/chat_completions → ocai` edge (the same code that decodes
provider responses today), so the fidelity report covers that leg too and the
compatibility surfaces cost no new conversion logic. The report is returned on
compatibility listeners through a response header carrying a content address
(the full report fetchable by id), and in streams as a final vendor-prefixed
SSE event — documented as a known limitation of the compatibility surface,
never of the primary one. This mirrors what Vercel and Bifrost did (several
inbound formats over one core) while keeping the one thing they lack: an
inbound leg that is itself a certified edge.

### 4.4 Things the gateway must not do

- Hold provider secrets in a place an interceptor can read: credentials stay
  `Credential` values applied at the driver leaf, per attempt (rule 13); the
  gateway's key store maps virtual keys to `Credential`s, never to strings
  handed into middleware.
- Register vector-space or "model translation" edges to emulate a provider
  (§11 recorded doctrine).
- Become the home of the fidelity logic: every conversion is a catalog edge
  with an `EdgeContract`; the gateway composes catalogs, it never converts.

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| WU-21 readiness plan: define the canonical wire API from `spec/` (request/response/chunk framing, error wire shape, `CallContext` as headers), virtual-key → `Credential` + `CallContext` binding, the catalog-lock-as-config model | **P1** (the gateway is the platform's entry point, but it is useless before telemetry can observe it) | G-02 recorded-pair spec (the gateway's audit log *is* that format), G-04 correlation id |
| `FallbackInterceptor`, `BudgetInterceptor` reference implementations in the kernel's `runtime.interceptors` or a satellite | P1 | H4 (one real cross-provider failover is a v1.0 freeze condition) |
| OpenAI-compatible inbound listener as an inbound edge over the existing decode | P2 | H1 (`/responses` decode exists) |
| Anthropic-compatible inbound listener | P2 | — |
| Admin UI / control plane | P3 | everything above |
| MCP mounting, guardrails, prompt registry | satellites, mounted later | their own pages |

## 6. Open questions and unverified items

- Portkey's `conditional` strategy mode, `retry`, `cache`, and hook keys are
  in its Config Schema reference, not on the configs page read; *unverified*.
- Kong's OSS/Enterprise split for individual AI plugins was not stated on the
  pages read; the 2.x "AI Model entity" replaces `ai-proxy`/`ai-proxy-advanced`.
- Cloudflare header names (`cf-aig-*`) and the `/compat` endpoint were not on
  the pages reachable on the read date.
- OpenRouter's `/api/v1/models` pricing field names were not confirmed; the
  overview page confirms `usage.cost`, `cost_details`, and the generation
  endpoint.
- Whether the compatibility listeners' report-by-reference header is
  acceptable to the audit satellite, or whether every compatibility response
  must inline the report, is a WU-21 decision.

## Sources

- https://docs.litellm.ai/docs/simple_proxy (read 2026-11-10)
- https://docs.litellm.ai/docs/routing (read 2026-11-10)
- https://docs.litellm.ai/docs/proxy/virtual_keys (read 2026-11-10)
- https://docs.litellm.ai/docs/proxy/caching (read 2026-11-10)
- https://portkey.ai/docs/product/ai-gateway/configs (read 2026-11-10)
- https://portkey.ai/docs/product/ai-gateway/cache-simple-and-semantic (read 2026-11-10)
- https://openrouter.ai/docs/features/provider-routing (read 2026-11-10)
- https://openrouter.ai/docs/api-reference/overview (read 2026-11-10)
- https://developer.konghq.com/ai-gateway/ (read 2026-11-10)
- https://developer.konghq.com/ai-gateway/load-balancing/ (read 2026-11-10)
- https://developers.cloudflare.com/ai-gateway/ (read 2026-11-10)
- https://github.com/Helicone/ai-gateway (read 2026-11-10)
- https://vercel.com/docs/ai-gateway (read 2026-11-10)
- https://www.truefoundry.com/ai-gateway (read 2026-11-10)
- https://github.com/maximhq/bifrost (read 2026-11-10)
- https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html (read 2026-11-10)
