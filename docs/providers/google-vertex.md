# Google Vertex AI — Capabilities & Features (as a model host)

> Currency: researched 2026-11-10 against docs.cloud.google.com (the Vertex
> generative-AI REST reference, now titled "Gemini Enterprise Agent Platform"),
> aistudio.google.com (Gemini Developer API reference), and platform.claude.com
> (Claude on Vertex). Google moved and rebranded these docs in 2026; the service
> is still `aiplatform.googleapis.com`. Model ids, regions, and the Developer
> API's new Interactions endpoint are fast-moving. Anything not confirmed on an
> official page is marked *unverified*. See
> [google-gemini.md](./google-gemini.md) for the Gemini dialect itself.

Vertex is a host that serves **three dialects**: Google's own `generateContent`
(Gemini), partner models through `:rawPredict`/`:streamRawPredict` with the
partner's native body (Claude, Mistral), and an OpenAI-compatible
`/endpoints/openapi/chat/completions` route (Gemini, Llama MaaS, open-weight
MaaS). The `generateContent` body is *mostly* the Gemini Developer API body,
but the two are **not byte-identical** — Vertex adds `labels`,
`modelArmorConfig`, enterprise retrieval tools, and `trafficType`, and names
cached content and block reasons differently.

## 1. API surface / endpoints

| Dialect | URL | Notes |
|---|---|---|
| **Gemini generateContent** | `POST https://{region}-aiplatform.googleapis.com/v1/projects/{p}/locations/{region}/publishers/google/models/{model}:generateContent` | `:streamGenerateContent` for streaming; `v1` and `v1beta1` both live |
| Global endpoint | `https://aiplatform.googleapis.com/v1/projects/{p}/locations/global/publishers/google/models/{model}:generateContent` | no data-residency guarantee; excludes tuning, partner batch |
| Multi-region | `https://aiplatform.us.rep.googleapis.com` / `aiplatform.eu.rep.googleapis.com` with `locations/us` / `locations/eu` | jurisdictional residency |
| Tuned endpoints | `.../locations/{l}/endpoints/{endpoint}:generateContent` | path accepts `publishers/*/models/*` or `endpoints/*` |
| **Claude (Google-managed)** | `.../publishers/anthropic/models/{model}:rawPredict` / `:streamRawPredict` | Anthropic Messages body; global host recommended |
| Mistral | `.../publishers/mistralai/models/{model}:rawPredict` / `:streamRawPredict` | body *includes* `model`; OpenAI-shaped responses |
| **OpenAI-compatible** | `.../locations/{l}/endpoints/openapi/chat/completions` (Gemini: `v1`, global or regional; Llama MaaS: `v1beta1`, `us-east5`; open MaaS: `v1`, `global`) | `model` = `google/gemini-…`, `meta/llama-4-…-maas`, `openai/gpt-oss-120b-maas` |
| Claude count tokens | `.../publishers/anthropic/models/count-tokens:rawPredict` with `{model, messages}` → `{input_tokens}` | |
| Context cache | `projects/{p}/locations/{l}/cachedContents` resource | referenced by `cachedContent` |
| Batch | `.../locations/{l}/batchPredictionJobs` (BigQuery or GCS JSONL) | not the Anthropic Batches API; not on global |
| Express mode | `https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent` with an API key | consumer accounts only, pre-GA |

Gemini Developer API, for contrast: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`;
its docs now foreground a separate Interactions API (`POST /v1beta/interactions`,
header `Api-Revision: 2026-05-20`) and describe `streamGenerateContent` as the
path "for existing generateContent integrations".

A separate **Anthropic-managed** offering on Google Cloud exists at
`https://claude.googleapis.com/v1/projects/{p}/locations/global/workspaces/{ws}/invoke/v1/messages`
(first-party Messages wire: `anthropic-version` header, `model` in body,
Google OAuth bearer, IAM `roles/claude.user`).

## 2. Request & response model

Gemini body on Vertex (v1 reference): `contents[]`, `systemInstruction`,
`cachedContent` (full resource name `projects/…/cachedContents/{id}`; the
Developer API uses `cachedContents/{id}`), `tools[]`, `toolConfig`, `labels`
(map, "billing and reporting only"), `safetySettings[]`, `modelArmorConfig`
(cannot be combined with `safetySettings`), `generationConfig`;
`continuationToken` is `v1beta1`-only. Response: `candidates[]`,
`modelVersion`, `createTime` (Vertex only), `responseId`, `promptFeedback`,
`usageMetadata`. The Developer API response adds `modelStatus{modelStage,
retirementTime, message}` and candidate `tokenCount`, and lacks `createTime`.

Vertex `finishReason` enum (bare names in the REST reference; the inference
guide still prints `FINISH_REASON_*` spellings): `STOP, MAX_TOKENS, SAFETY,
RECITATION, OTHER, BLOCKLIST, PROHIBITED_CONTENT, SPII, MALFORMED_FUNCTION_CALL,
MODEL_ARMOR, IMAGE_SAFETY, IMAGE_PROHIBITED_CONTENT, IMAGE_RECITATION,
IMAGE_OTHER, UNEXPECTED_TOOL_CALL, NO_IMAGE, MALFORMED_RESPONSE, CONTINUATION,
TOO_MANY_TOOL_CALLS`. Developer API adds `LANGUAGE, MISSING_THOUGHT_SIGNATURE,
ESCALATION, PUP_LIMITED_DISABLED` and lacks `MODEL_ARMOR`.
`promptFeedback.blockReason` zero-values differ: Vertex `BLOCKED_REASON_UNSPECIFIED`
(+ `MODEL_ARMOR`, `JAILBREAK`), Developer API `BLOCK_REASON_UNSPECIFIED`.

## 3. Generation parameters

`generationConfig`: `temperature, topP, topK, candidateCount, maxOutputTokens,
presencePenalty, frequencyPenalty, stopSequences, seed, responseLogprobs,
logprobs, audioTimestamp, responseModalities, mediaResolution, speechConfig,
enableAffectiveDialog, routingConfig{autoMode|manualMode}, thinkingConfig{
includeThoughts, thinkingBudget, thinkingLevel}`, and `responseFormat`.
`responseMimeType`, `responseSchema`, `responseJsonSchema`, `imageConfig` are
now marked *deprecated, use `responseFormat`* on Vertex (the Developer API
still lists `responseMimeType`/`responseJsonSchema` alongside `responseFormat`).
Through the OpenAI-compatible route, `reasoning_effort` low/medium/high maps
to thinking budgets 1024/8192/24576 and unsupported OpenAI params are
**silently ignored**.

## 4. Structured outputs

`generationConfig.responseFormat` (new) or the deprecated
`responseMimeType: "application/json"` + `responseSchema`/`responseJsonSchema`.
Claude on Vertex supports `output_config.format{type: "json_schema", schema}`.

## 5. Tool / function calling

Vertex `Tool`: `functionDeclarations[]` (≤512), `retrieval{vertexAiSearch{
datastore} | vertexRagStore{ragResources{ragCorpus}, …}}`, `googleSearch`
(`excludeDomains`, `searchTypes`), `googleSearchRetrieval` (deprecated),
`enterpriseWebSearch`, `googleMaps`, `parallelAiSearch`, `exaAiSearch`,
`codeExecution`, `urlContext`, `computerUse`. Developer API `Tool` instead has
`fileSearch`, `mcpServers` and lacks `retrieval`/`enterpriseWebSearch`. Search
tools cannot be mixed with function declarations in one request. OpenAI-compat
route: `tool_choice` adds a Google-specific `validated` value;
`web_search_options` → `googleSearch`; `extra_body.google.{safety_settings,
cached_content, thinking_config, thought_tag_marker,
stream_function_call_arguments, tools, media_resolution}` and response
`extra_content.google.{thought, thought_signature, parts}`.

## 6. Streaming

`alt` is a Google system parameter (`json` default, `sse` "for JSON
streams"), so `?alt=sse` is the sanctioned SSE switch on `streamGenerateContent`.
The Vertex reference only says the body is "a stream of `GenerateContentResponse`
instances" — that the default framing is a JSON array is consistent with
`alt=json` but *unverified on an official page*. The OpenAI-compatible route
streams standard `data:` chunks with `object: "chat.completion.chunk"`, final
chunk carrying `finish_reason` + `usage`, terminated by `data: [DONE]`.
Claude on Vertex streams SSE from `:streamRawPredict`; event-level identity with
the first-party Messages stream is *unverified* (Anthropic's SDK consumes it
unchanged, which is strong evidence). Google's own Claude examples keep
`"stream": true` in the body alongside the `:streamRawPredict` verb.

## 7. Reasoning / thinking

Gemini: `thinkingConfig{includeThoughts, thinkingBudget, thinkingLevel}`,
`usageMetadata.thoughtsTokenCount`, thought signatures in parts (and
`extra_content.google.thought_signature` on the OpenAI route). Claude:
`thinking{type: "enabled", budget_tokens ≥ 1024}` per Google's page (the
adaptive form is the first-party default on newer models — which form Vertex
accepts per model is Anthropic's table, not re-verified here). Anthropic
beta features are requested with the `anthropic-beta` **header**; Vertex
reads only one such header (comma-join values). A body `anthropic_beta`
array is Bedrock-only.

## 8. Prompt / context caching

Vertex `cachedContents` resource (`model, systemInstruction, contents[],
tools[], toolConfig, ttl|expireTime, displayName, encryptionSpec,
usageMetadata`); default expiry 60 min; `usageMetadata.cachedContentTokenCount`
+ `cacheTokensDetails[]`. Claude on Vertex supports `cache_control` incl.
`ttl: "1h"`.

## 9. Multimodal

As Gemini (inline/file parts; Vertex `fileData` accepts `gs://` URIs — see
google-gemini.md). Claude on Vertex: no URL image/document sources, no Files
API, 30 MB payload cap.

## 10. Models

- Gemini: `publishers/google/models/{gemini-…}`; regions as listed on the
  locations page (per-model availability *unverified* from this read).
- Claude: pre-4.6 ids keep an `@` snapshot (`claude-opus-4-1@20250805`,
  `claude-sonnet-4-5@20250929`, `claude-haiku-4-5@20251001`,
  `claude-opus-4-5@20251101`); 4.6+ use plain ids (`claude-opus-4-6`,
  `claude-sonnet-4-6`, …). Regional endpoints serve Sonnet 4.6 and earlier
  only; regional/multi-region carry +10% price; PT requires regional.
- Mistral: `mistral-medium-3`, `mistral-small-2503`, `codestral-2`,
  `mistral-ocr-2505` (`us-central1`, `europe-west4`).
- MaaS via OpenAI route: `meta/llama-4-maverick-17b-128e-instruct-maas`,
  `meta/llama-4-scout-17b-16e-instruct-maas` (`us-east5`, needs EULA +
  `cloudcommerceconsumerprocurement.googleapis.com`), `openai/gpt-oss-120b-maas`,
  DeepSeek/Qwen `…-maas` ids (seen in search snippets — *unverified*).
  `meta/llama-3.3-70b-instruct-maas` is not on the current page — *unverified/retired*.

## 11. Auth, limits, errors

- **OAuth bearer**: `Authorization: Bearer <access_token>`; scope
  `https://www.googleapis.com/auth/cloud-platform`; optional
  `x-goog-user-project` (quota project, needs `serviceusage.services.use`).
  Token sources: (i) metadata server
  `GET http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token`
  with `Metadata-Flavor: Google` → `{access_token, expires_in, token_type}`;
  (ii) service-account JWT grant — RS256 JWT (`iss`, `scope`, `aud:
  https://oauth2.googleapis.com/token`, `iat`, `exp ≤ 1h`) POSTed as
  `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=…`;
  (iii) self-signed JWT as bearer with `aud: https://aiplatform.googleapis.com/`;
  (iv) pre-minted ADC/user tokens. **Express mode** API keys
  (`x-goog-api-key` or `?key=`) are consumer-account, pre-GA, global-host only.
- **Provisioned Throughput / priority**: `X-Vertex-AI-LLM-Request-Type:
  dedicated|shared`; `X-Vertex-AI-LLM-Shared-Request-Type: priority`
  (global/us/eu); outcome reported in `usageMetadata.trafficType` ∈
  `ON_DEMAND, ON_DEMAND_PRIORITY, ON_DEMAND_FLEX, PROVISIONED_THROUGHPUT`
  (Developer API uses `serviceTier` instead).
- **Quota**: Gemini on Vertex uses "Standard PayGo usage tiers" — no per-tier
  RPM, TPM threshold is prioritisation, a 429 "doesn't indicate a fixed
  quota" (the DSQ name is gone). Claude/Mistral/Llama MaaS keep fixed
  QPM/TPM per model per endpoint. `Retry-After` not documented — *unverified*.
- **Errors** (AIP-193): `{"error": {"code": <int>, "message", "status":
  "<google.rpc.Code>", "details": [{"@type": "…google.rpc.ErrorInfo",
  "reason", "domain", "metadata"}, …]}}`. 400 `INVALID_ARGUMENT` /
  `FAILED_PRECONDITION`; 401 `UNAUTHENTICATED`; 403 `PERMISSION_DENIED`; 404
  `NOT_FOUND`; 429 `RESOURCE_EXHAUSTED`; 499 `CANCELLED`; 500 `INTERNAL` /
  `UNKNOWN`; 503 `UNAVAILABLE`; 504 `DEADLINE_EXCEEDED` (10-min server
  deadline). Safety blocks are JSON-body outcomes (`promptFeedback.blockReason`,
  candidate `finishReason: SAFETY|…` with cleared content) — HTTP 200 is
  implied, *unverified*. No `anthropic-ratelimit-*` headers for Claude on
  Vertex — *unverified/absent*.
- Request-response logging: `setPublisherModelConfig` (`v1beta1`) with
  `loggingConfig{enabled, samplingRate, bigqueryDestination.outputUri,
  enableOtelLogging}` covers Gemini and Claude calls.

## 12. Distinctive to Vertex

- Three dialects under one IAM/VPC/billing umbrella; the body of a partner
  model is the partner's own, with `model` moved into the URL (Claude) or
  kept (Mistral).
- **Model Armor** (`modelArmorConfig{promptTemplateName, responseTemplateName}`)
  and enterprise grounding (`vertexAiSearch`, `vertexRagStore`,
  `enterpriseWebSearch`) as request-level tools.
- Explicit `trafficType` accounting, PT/priority steering by header, `labels`
  for billing attribution, multi-region residency hosts, request-response
  logging to BigQuery/OTel.
- Deprecation of `responseSchema`/`responseMimeType` in favour of
  `responseFormat` ahead of the Developer API.

## 13. Mapping to `ocai`

**(a) Codec vs host.** Three answers, one per dialect:

- **Claude on Vertex** is served today by the existing `anthropic/messages`
  codec + the kernel's `Vertex` host: `_RawPredictEnvelope` already drops
  `model`/`stream` and injects `cloud_body_version =
  ("anthropic_version", "vertex-2023-10-16")`. Gaps to close in the host, not
  the codec: a `global` location (`aiplatform.googleapis.com`, no region
  prefix) and the `us`/`eu` multi-region hosts (`aiplatform.{us|eu}.rep.googleapis.com`)
  — i.e. `Vertex.endpoint()` must derive the host from `location` rather than
  assume `{region}-aiplatform`; forwarding the dialect's `anthropic-beta`
  header (collapsed to one header) while still dropping `anthropic-version`
  — a trait split between *version* headers (dropped on clouds) and
  *feature* headers (forwarded); and the `count-tokens:rawPredict` path.
  Mistral via `:rawPredict` keeps `model` in the body — the envelope's
  `model`-drop must become a trait (`cloud_body_keeps_model`), not a constant.
- **Gemini on Vertex** needs the Gemini dialect first (`ocai.google.generate_content`,
  a horizon item). Once it exists, Vertex is a host for it: URL verb
  `:generateContent`/`:streamGenerateContent?alt=sse` keyed by `Operation.kind`
  (`_VERB_BY_KIND` grows a per-dialect verb table or the dialect supplies its
  verbs as a trait), `model` in URL, no version injection. The Vertex-only
  fields (`labels`, `modelArmorConfig`, `retrieval`, `enterpriseWebSearch`,
  `trafficType`, `createTime`, `MODEL_ARMOR` codes) are the difference
  between two **tags** of one interface, or a host-level census — the former
  is cleaner: `google/generate_content@vertex` vs `@developer` sibling nodes
  sharing a codec with a traits-driven field allowlist.
- **OpenAI-compatible route** (`/endpoints/openapi/chat/completions`) is the
  existing `openai/chat_completions` codec through a `Custom`-like path
  template on the Vertex host with OAuth bearer. Silent parameter dropping
  on Google's side is the honesty hazard: ocai must declare those fields
  `UNSUPPORTED` from `CapabilityProfile` facts since the wire will not tell.

**(b) Auth.** A `GoogleOAuthCredential` in an `ocai-google-cloud` plugin:
metadata-server, Workload Identity, and pre-minted tokens need **no signing
library**; the service-account-key JWT flow needs RS256, which CPython stdlib
cannot do — that is the one justified narrow signing dependency under
rule 12 (optional extra, imported lazily). Refresh is per attempt at the
driver leaf; `x-goog-user-project` is a credential-adjacent header the host
contributes.

**(c) Honesty.** `usageMetadata.trafficType`, `labels`, `createTime`,
`responseId` → `google.vertex.*` censused extensions. `modelArmorConfig`,
`X-Vertex-AI-LLM-*` headers → `provider_options["google.generate_content"]`
(or host options). `finishReason: MODEL_ARMOR|SAFETY|PROHIBITED_CONTENT|SPII|
BLOCKLIST|RECITATION` → `ContentFilterError` or the canonical finish with
`native` preserved, and an empty candidate is a `SemanticShift` ("output
withheld"). The `FINISH_REASON_*` vs bare spelling split is exactly what the
`native` lane is for. Claude-on-Vertex `anthropic_version` body injection is
a `RENAMED` disposition (header → body) on the host edge, reported, not
hidden. Gemini-vs-Vertex field census differences must be in the
`EdgeContract` of each tag so a Developer-API request carrying `fileSearch`
converts to Vertex with `UNSUPPORTED`, never silently.

**(d) Errors.** Map by `error.status`: `RESOURCE_EXHAUSTED` (429) →
`RateLimitError` (no reliable `retry_after`); `UNAUTHENTICATED` (401),
`PERMISSION_DENIED` (403) → `AuthError`; `INVALID_ARGUMENT` with a
token-limit message → `ContextLengthError` (message-matching is brittle —
prefer `ErrorInfo.reason` when present, else generic `OcaiError` with
`code=status`); `UNAVAILABLE`, `INTERNAL`, `UNKNOWN`, `DEADLINE_EXCEEDED`
(503/500/504) → `TransientError`; `NOT_FOUND` → `OcaiError(code="NOT_FOUND")`;
safety outcomes on 200 → `ContentFilterError` only when the caller opted in
to raising, else a reported finish.

**(e) Priority: P1 — third of the three clouds, but its Claude slice is
nearly free.** Rationale: the kernel already ships a `Vertex` host, so
"Anthropic on Vertex with real OAuth" is a half-WU proof worth taking early
(and it validates the `D + H` composition claim with a recorded pair). The
Gemini-on-Vertex path is gated on the Gemini dialect, which is a horizon
item; without it Vertex offers enterprises only Claude/Mistral/MaaS, which
Bedrock and Azure already cover for most of them. Effort: **1 WU** now
(`ocai-google-cloud`: `GoogleOAuthCredential`, global/multi-region host
fix, beta-header forwarding trait, `count-tokens`, recorded Claude pairs
unary + stream), **+2 WUs** when the Gemini dialect lands (Vertex
`generateContent` host verbs + the Vertex/Developer tag split with its
census and fold triples; the OpenAI-compat route as a rider).

## Sources (read 2026-11-10)

- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.publishers.models/generateContent
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.publishers.models/streamGenerateContent
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerateContentResponse
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerationConfig
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/ModelArmorConfig
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.cachedContents
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-filters
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-your-data
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-use
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/migrate/migrate-google-ai
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/use-provisioned-throughput
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/request-response-logging
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/error-code-429
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/dsq
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/llama/use-llama
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/maas/call-open-model-apis
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/mistral
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/partner-models/claude/use-claude
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/count-tokens
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/batch
- https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/google-managed
- https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/overview
- https://platform.claude.com/docs/en/api/beta-headers
- https://docs.cloud.google.com/docs/authentication/rest
- https://developers.google.com/identity/protocols/oauth2/service-account
- https://docs.cloud.google.com/compute/docs/access/authenticate-workloads
- https://docs.cloud.google.com/apis/docs/system-parameters
- https://google.aip.dev/193
- https://aistudio.google.com/api-reference/generate-content
- https://aistudio.google.com/api-reference/caching
- https://aistudio.google.com/docs/safety-settings
