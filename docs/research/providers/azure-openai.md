# Azure OpenAI (Microsoft Foundry) — Capabilities & Features (as a model host)

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

> Currency: researched 2026-11-10 against learn.microsoft.com (the v1 API
> lifecycle page, the v1 REST reference, content-filter and quota pages). Azure
> is mid-migration from dated `api-version` deployment URLs to the unified
> `/openai/v1` surface; the dated-version retirement table could not be found —
> treat dated versions as legacy, not retired. Anything not confirmed on an
> official page is marked *unverified*.

Azure OpenAI is the clearest "same dialect, different host" case: the wire body
**is** OpenAI `chat/completions` / `responses` / `embeddings`, with three host
deltas — the URL (resource subdomain, `/openai/v1` or deployment-scoped path,
optional `api-version` query), the auth header (`api-key` or Entra bearer), and
**content-filter annotations** grafted onto responses and stream chunks. Models
from other vendors (DeepSeek, Grok, MAI, Llama) are served through the same v1
chat-completions syntax, so one codec plus one host covers the catalog.

## 1. API surface / endpoints

| Surface | URL | Notes |
|---|---|---|
| **v1 chat** | `POST https://{resource}.openai.azure.com/openai/v1/chat/completions` | `model` = deployment name in body; `api-version` optional (`v1` default, `preview`) |
| **v1 responses** | `POST …/openai/v1/responses` (+ `GET/DELETE /{id}`, `/{id}/cancel`, `/{id}/input_items`, `/compact`) | recommended for OpenAI models; 30-day retention; background mode |
| v1 embeddings | `POST …/openai/v1/embeddings` | `input`, `model`, `encoding_format`, `dimensions`; ≤300K tokens/request |
| v1 images | `POST …/openai/v1/images/generations?api-version=preview` | edits still shown on the legacy path |
| Audio | legacy `…/openai/deployments/{deployment}/audio/transcriptions|translations|speech?api-version=2024-10-21|2025-04-01-preview` | v1 audio paths *unverified* (reference page 404) |
| Legacy deployment-scoped | `POST https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=YYYY-MM-DD` | `api-version` required; GA `2024-10-21`, preview `2025-04-01-preview` |
| Azure AI Model Inference (retired SDK) | `https://{resource}.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview` | migration guide says use `/openai/v1/` instead |

`base_url` accepts both `https://{resource}.openai.azure.com/openai/v1/` and
`https://{resource}.services.ai.azure.com/openai/v1/`. A
`*.cognitiveservices.azure.com` host for v1 was not seen — *unverified*.
Preview features on v1 are selected by **feature headers** (e.g. the former
`aoai-evals: preview`) or an `alpha` path segment, not by `api-version`.

## 2. Request & response model

Identical to OpenAI direct for the body: `messages[]` with `system|developer|
user|assistant|tool`, `choices[].message`, `finish_reason`, `usage`. The
Foundry example for non-OpenAI models uses `role: "developer"` as the system
role. Azure adds:

- `prompt_filter_results[]` at the top level of a chat response — each
  `{prompt_index, content_filter_results{…}}` — and `choices[].content_filter_results`.
- Responses API: top-level `content_filters[{source_type: "prompt"|…, blocked,
  content_filter_results, content_filter_offsets, tool_call_id?}]` (a Foundry
  extension the SDKs do not type).
- `user_security_context{application_name, end_user_id, end_user_tenant_id,
  source_ip}` — Azure-only request field for Defender for Cloud.
- Response header `apim-request-id` (request id) on success and error.

## 3. Generation parameters

The v1 chat spec lists the OpenAI set: `logprobs`, `top_logprobs`, `n` (≤128),
`store`, `metadata`, `prediction`, `modalities`, `audio`, `parallel_tool_calls`,
`seed` (deprecated), `stream_options{include_usage, include_obfuscation}`,
`reasoning_effort` (`none|minimal|low|medium|high|xhigh`), `verbosity`,
`response_format`, `tools`, `functions` (deprecated), `user` (deprecated).
`service_tier`, `prompt_cache_key`, `safety_identifier`, `web_search_options`
on Azure chat — *unverified*. Reasoning models reject `max_tokens` (use
`max_completion_tokens`; Responses: `max_output_tokens`), `temperature`,
`top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `logit_bias`.

## 4. Structured outputs

`response_format` with `json_schema` (`OpenAI.ResponseFormatJsonSchema`) as on
OpenAI direct; added in `2024-08-01-preview`. No Azure-specific delta found.

## 5. Tool / function calling

OpenAI wire (`tools[].function`, `tool_calls[]` with string `arguments`,
`tool_choice`, `parallel_tool_calls`). Azure-specific constraints: on some
reasoning models function tools are accepted only with `reasoning_effort:
"none"` on `/v1/chat/completions` (documented error text names the model);
parallel tool calls are unsupported with `minimal`. Responses API supports
remote MCP (`type: "mcp"` with `mcp_approval_request`/`mcp_approval_response`),
image generation, code interpreter, computer use.

The retired **On Your Data** extension (`data_sources[{type: "azure_search",
parameters}]`, response `message.context{citations[], intent,
all_retrieved_documents[]}`) lived on the legacy path and was retired
2026-10-14; it is not in the v1 spec.

## 6. Streaming

SSE `data: {...}` chunks ending `data: [DONE]`, same `chat.completion.chunk`
shape as OpenAI. Azure deltas:

- A **leading annotation chunk** with `choices: []`, `id: ""`, `object: ""`,
  `created: 0`, `model: ""`, and `prompt_filter_results[]` (older samples:
  `prompt_annotations`) precedes the first token.
- Default (synchronous) filter mode buffers output and evaluates it in chunks
  before release; `finish_reason: "content_filter"` on the last chunk of a
  filtered generation.
- **Asynchronous Filter** (opt-in per filter config, `2024-02-01+`): tokens
  stream unbuffered; separate annotation chunks with empty `delta` carry
  `choices[].content_filter_results`, `content_filter_raw`, and
  `content_filter_offsets{check_offset, start_offset, end_offset}` (character
  offsets from prompt start; `check_offset` never decreases); block signal
  guaranteed within a ~1,000-character window. The last streamed segment may
  escape output filtering (documented caveat).
- `stream_options.include_usage` supported: a final chunk with `usage` and
  empty `choices` before `[DONE]`.
- Responses streams on HTTP 200 deliver errors as an `error` event with codes
  `server_error`(500), `too_many_requests`(429), `forbidden`(403),
  `user_error`(400).

## 7. Reasoning / thinking

Same wire as OpenAI: `reasoning_effort` (`none|minimal|low|medium|high|xhigh|
max`, model-dependent — `max` only on the newest models via Responses),
`completion_tokens_details.reasoning_tokens` (chat) /
`output_tokens_details.reasoning_tokens` (responses), Responses
`reasoning.summary` (`auto|concise|detailed`), `reasoning.context`,
`reasoning.mode` (`standard|pro`), `text.verbosity`,
`include: ["reasoning.encrypted_content"]` with `store: false` for stateless
reasoning. Truncation → `status: "incomplete"`,
`incomplete_details.reason: "max_output_tokens"`. Known issue: Foundry
(non-OpenAI) reasoning models report `reasoning_tokens: 0`. Some models are
Responses-only.

## 8. Prompt caching

Implicit, as on OpenAI direct (`usage.prompt_tokens_details.cached_tokens`);
PTU request cost is estimated from prompt tokens *minus cached* plus
`max_tokens`. No Azure-specific caching control was found on the pages read.

## 9. Multimodal

Vision/audio/file input parts as OpenAI; `gpt-image` models always return
`b64_json`; image responses carry `data[].prompt_filter_results` /
`content_filter_results`; image filter errors use `error.code: "contentFilter"`
with `inner_error.code: "ResponsibleAIPolicyViolation"` and
`inner_error.revised_prompt`. Content filters do not apply to embeddings or
audio models. `dall-e-3` retired 2026-03-04.

## 10. Models

The identifier is the **deployment name**, not the model name. Deployment SKUs
(ARM `sku.name`): `GlobalStandard`, `GlobalProvisionedManaged`, `GlobalBatch`,
`DataZoneStandard`, `DataZoneProvisionedManaged`, `DataZoneBatch`, `Standard`,
`ProvisionedManaged`, `DeveloperTier`. Instant access (preview) calls models
by name with no deployment. Non-OpenAI Foundry models (DeepSeek, Grok,
`MAI-DS-R1`, Llama) are called through the same v1 chat/responses routes;
an unsupported deployment on Responses → `400 Model not supported`. A retired
model returns `410 Gone`.

## 11. Auth, limits, errors

- **Key**: `api-key: <key>` (the v1 spec also lists an `authorization`-header
  key scheme; Foundry pages show `Authorization: Bearer <key>`). Env
  conventions `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, or the plain
  `OPENAI_BASE_URL`/`OPENAI_API_KEY` for the v1 client.
- **Entra ID**: `Authorization: Bearer <token>`. Current how-to pages use scope
  `https://ai.azure.com/.default`; the v1 REST spec declares
  `https://cognitiveservices.azure.com/.default` — both are official, which a
  given resource accepts is *unverified* (ocai should let the scope be data).
  Entra requires the custom subdomain (`{resource}.openai.azure.com`), else
  401. Roles: `Cognitive Services OpenAI User` (data plane); propagation up to
  five minutes. Keys can be disabled (`disableLocalAuth: true`); expect
  `401 Access denied due to invalid subscription key or wrong API endpoint`.
- **Rate-limit headers** (documented): `x-ratelimit-limit-requests`,
  `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-requests`,
  `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-requests`,
  `x-ratelimit-reset-tokens`, `retry-after-ms` (429); PTU also sends
  `retry-after`. `x-ms-region`, `azureml-model-session`, `x-ms-deployment-name`
  — *unverified* (Q&A only). Up to 10 custom request headers are echoed back
  (431 beyond; pass-through may end in future versions).
- **Quota**: TPM per deployment with derived RPM; 1 s / 10 s enforcement
  windows; billed on actual tokens, limited on estimated; from 2026-05-07
  quota is pooled at subscription level per model/version (Global) or per
  zone (Data Zone). PTU: leaky-bucket utilization, 429 at 100%.
- **Error body** (v1 spec): `{"error": {"code", "message", "param"?, "type"?,
  "inner_error"?}}` — note `inner_error` (v1) vs `innererror` (classic
  content-filter example). Prompt blocked → 400 `error.code: "content_filter"`,
  `param: "prompt"`, with `innererror.content_filter_result` /
  `inner_error.content_filter_results`. Invalid `x-policy-id` →
  `error.code: "InvalidContentFilterPolicy"`. Wrong deployment → 404.
  `DeploymentNotFound`, `PermissionDenied`, `NoCapacity`,
  `context_length_exceeded` as literal codes — *unverified*.

## 12. Distinctive to Azure OpenAI

- **Deployment indirection**: the caller names a deployment, which pins a
  model+version+SKU+region; the same code switches models by redeploying.
- **Content-filter annotations** on every response and in-stream, with
  per-category `severity` (`safe|low|medium|high`) and detection flags
  (`jailbreak`, `indirect_attack`, `profanity`, `protected_material_text`,
  `protected_material_code{citation{URL, license}}`, `custom_blocklists`,
  `custom_topics`, `personally_identifiable_information{redacted_text,
  sub_categories[]}`, `ungrounded_material{details[{completion_start_offset,
  completion_end_offset}]}`, `task_adherence` on Responses), per-request
  override `x-policy-id`, and a filter-failure marker
  `content_filter_results.error`.
- **Two version axes on the host itself**: the dated `api-version` (legacy)
  and the feature-header preview opt-in (v1) — exactly the thing ocai's
  "interface tag" axis is for, but living on the host rather than the dialect.
- Data-zone / global / provisioned SKUs, subscription-pooled quota,
  `retry-after-ms`, `apim-request-id`, `user_security_context`.
- Responses: 30-day server retention, `background: true`, `/compact`,
  `context_management` compaction with `store: false`.

## 13. Mapping to `ocai`

**(a) Codec vs host.** Azure needs **no new interface subpackage**: the
existing `openai/chat_completions` (and later `openai/responses`) codecs serve
it through an `AzureOpenAI` `Host` value. Traits/host fields needed:

- host `resource` (subdomain) and `domain` (`openai.azure.com` |
  `services.ai.azure.com`), `surface` ∈ `v1|deployment`, optional
  `deployment` (legacy path interpolation), optional `api_version` query
  (`v1|preview|YYYY-MM-DD`), optional `preview_headers` map, optional
  `policy_id` → `x-policy-id`.
- The host's `endpoint()` maps the dialect `native_path`
  (`/v1/chat/completions`) to `/openai/v1/chat/completions` — a **path-prefix
  rewrite** rather than `Custom`'s per-kind template; an `EnvelopeTransform`
  that strips `model` on the deployment surface (the deployment is in the
  URL) and leaves it on v1 (where `model` = deployment name — the facade's
  bound resource is the deployment).
- `DialectTraits` needs nothing new for Azure; the growth is on the host:
  a generic `path_prefix` and `query` map would let `Custom` cover Azure v1
  without a dedicated class, but the content-filter decode (below) argues for
  a named host so the codec can be told "expect Azure annotations".

**(b) Auth.** `api-key` is a header-named `ApiKey` (the credential must be
able to choose its header name — `ApiKey(header="api-key")`). Entra bearer
tokens: the client-credentials / managed-identity flows are plain HTTPS
POSTs to `login.microsoftonline.com` and IMDS; a refreshing
`BearerTokenCredential` in an `ocai-azure` plugin needs **no signing
library** (JWT client assertions, if used, are RS256 over stdlib-unfriendly
RSA — that one case would justify a narrow signing dependency under rule 12).
Scope is data on the credential, defaulting to `https://ai.azure.com/.default`.

**(c) Honesty.** `prompt_filter_results` and `choices[].content_filter_results`
→ censused extension `azure.content_filter_results` (schema with the category
map above; `content_filter_offsets` and `content_filter_raw` included for
async mode). `finish_reason: "content_filter"` already maps to the canonical
finish with `native` preserved; a filtered completion on HTTP 200 with empty
content is a `SemanticShift` ("output withheld by host policy"), not a drop.
The leading empty-`choices` annotation chunk must fold to nothing but attach
its annotations to `StreamEnd.report`/extensions — a fold-triple fixture for
the Azure stream edge is mandatory (rule 7). `user_security_context` and
`x-policy-id` → `provider_options["azure.openai"]`. `apim-request-id`,
`x-ms-region` → `raw`/trace, never IR. Model-name ≠ deployment-name is a
`Route` concern: the `Route` records the deployment, `CapabilityProfile`
facts are keyed by the underlying model, so the host must carry a
`deployment → model` hint or profile gating degrades to annotate-only.

**(d) Errors.** `error.code: "content_filter"` (400) → `ContentFilterError`
with `raw` holding the filter result; 429 → `RateLimitError` honoring
`retry-after-ms` (milliseconds — the transport must divide by 1000 before
filling `retry_after`); 401/403 (`PermissionDenied`, key disabled) →
`AuthError`; 404 wrong deployment → `OcaiError(code="DeploymentNotFound")`
(code literal *unverified*); 410 retired model → `UnsupportedFeatureError`-adjacent
`OcaiError`; `context_length_exceeded` → `ContextLengthError` if the code
appears (it does on OpenAI direct; Azure parity *unverified*); 500/503 and
Responses stream `server_error` → `TransientError`.

**(e) Priority: P0 — second cloud after Bedrock, ahead of Vertex.** Rationale:
near-zero codec work (the `openai/chat_completions` codec is already
certified), so Azure is the cheapest proof that `Host` + `Credential`
composition reaches a real enterprise cloud; the content-filter annotations
are the first host-level censused extension and exercise the "annotation
chunk with empty choices" fold path. Effort: **2 WUs** — (1) `ocai-azure`:
`AzureOpenAI` host (v1 + deployment surfaces), `ApiKey` header-name support,
Entra `BearerTokenCredential`, recorded unary pairs incl. a 400
`content_filter`; (2) streaming: annotation-chunk fold triples, async-filter
offsets census, `retry-after-ms`, and the `/openai/v1/responses` route riding
the `openai/responses` codec once that lands.

## Sources (read 2026-11-10)

- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview
- https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/chat?view=rest-microsoft-foundry-v1
- https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/responses?view=rest-microsoft-foundry-v1
- https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/embeddings?view=rest-microsoft-foundry-v1
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/managed-identity
- https://learn.microsoft.com/en-us/azure/ai-services/disable-local-auth
- https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/how-to/configure-entra-id
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/content-filter-annotations
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/content-streaming
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/content-filter
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/content-filters
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/quotas-limits
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/quota
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/deployment-types
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/provisioned-get-started
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/dall-e
- https://learn.microsoft.com/en-us/azure/foundry-classic/openai/references/on-your-data
- https://learn.microsoft.com/en-us/azure/foundry/how-to/model-inference-to-openai-migration
- https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/endpoints
