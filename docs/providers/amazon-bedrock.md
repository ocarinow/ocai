# Amazon Bedrock — Capabilities & Features (as a model host)

> Currency: researched 2026-11-10 against the Bedrock Runtime API reference and
> user guide. Model ids, geographic prefixes, and the `bedrock-mantle` route are
> fast-moving; re-verify against `ListFoundationModels` / `ListInferenceProfiles`
> before pinning a string. Field names on `Converse` are stable. Anything not
> confirmed on an official page is marked *unverified*.

Bedrock is a **host**, not a dialect: it serves Anthropic, Amazon Nova, Meta,
Mistral, DeepSeek, OpenAI open-weight and other models behind one AWS endpoint.
It exposes **four sibling interfaces** on that endpoint: `Converse` (AWS's own
provider-neutral chat body), `InvokeModel` (the model's *native* body, passed
through), an OpenAI-compatible `/openai/v1/chat/completions`, and an
Anthropic-compatible `/anthropic/v1/messages`. Only the first is Bedrock's own
dialect; the other three are either per-model pass-through or compatibility
shims. Streaming on the native operations is **binary AWS event-stream**, not SSE.

## 1. API surface / endpoints

Host: `https://bedrock-runtime.{region}.amazonaws.com` (FIPS:
`bedrock-runtime-fips.{region}.amazonaws.com`; control plane
`bedrock.{region}.amazonaws.com`). All operations are `POST` with
`Content-Type: application/json`; `{modelId}` is a URL path segment.

| Interface | Endpoint | Body dialect |
|---|---|---|
| **Converse** | `POST /model/{modelId}/converse` | Bedrock-neutral (`messages[]`/`system[]`/`inferenceConfig`/`toolConfig`) |
| **ConverseStream** | `POST /model/{modelId}/converse-stream` | same; response is event-stream |
| InvokeModel | `POST /model/{modelId}/invoke` | model-native (Anthropic Messages body, Nova body, …) |
| InvokeModelWithResponseStream | `POST /model/{modelId}/invoke-with-response-stream` | model-native chunks inside event-stream `chunk.bytes` |
| OpenAI-compatible chat | `POST /openai/v1/chat/completions` | OpenAI `chat/completions` (`model` in body) |
| OpenAI-compatible responses | `/openai/v1` Responses API — documented as available for models whose card lists it; exact path *unverified* |
| Anthropic-compatible | `POST /anthropic/v1/messages` | Anthropic Messages (`model` in body, `anthropic-version` header) |

A second compatibility host, `https://bedrock-mantle.{region}.api.aws`, serves
only the OpenAI-compatible (`/v1/chat/completions`, some models under
`/openai/v1`) and Anthropic-compatible (`/anthropic/v1/messages`) routes, plus
`GET /v1/models`. `bedrock-runtime` does **not** implement `GET /openai/v1/models`
(returns `404 UnknownOperationException`); it has no Guardrails or
cross-region profiles on mantle. AWS recommends `bedrock-runtime` for new work.

Model identifier forms accepted in `{modelId}` (max 2048 chars): foundation
model id (`anthropic.claude-sonnet-4-6`, `amazon.nova-2-lite-v1:0`) or ARN;
inference-profile id (`us.anthropic.…`, `eu.…`, `jp.…`, `au.…`, `global.…`;
`apac.` is referenced by geography name but was not seen as a literal prefix —
*unverified*) or ARN; application inference profile ARN; provisioned-model ARN;
custom-model-deployment / imported-model ARN; prompt-router ARN; SageMaker
endpoint ARN.

## 2. Request & response model (Converse)

- `messages[]` with `role` ∈ `user|assistant`; first message must be `user`.
  Each message's `content[]` is a list of typed blocks: `text`, `image`
  (`format: png|jpeg|gif|webp`, `source{bytes|s3Location}`), `document`
  (`name`, `format: pdf|csv|doc|docx|xls|xlsx|html|txt|md`, `source`,
  `citations`), `video`, `audio`, `toolUse{toolUseId,name,input}`,
  `toolResult{toolUseId, content[], status: success|error}`,
  `reasoningContent`, `cachePoint`, `guardContent`, `citationsContent`,
  `searchResult`.
- `system[]` is a top-level list of `text` | `guardContent` | `cachePoint`
  blocks — not a message role (same shape as Anthropic).
- Response: `output.message{role, content[]}`, `stopReason`, `usage`,
  `metrics{latencyMs}`, `additionalModelResponseFields`, `performanceConfig`,
  `serviceTier`, `trace{guardrail, promptRouter{invokedModelId}}`.
- `stopReason` ∈ `end_turn | tool_use | max_tokens | stop_sequence |
  guardrail_intervened | content_filtered | malformed_model_output |
  malformed_tool_use | model_context_window_exceeded`. Nova's native body adds
  `service_unavailable`, `invalid_query`, `max_tool_invocations`.
- Tool results are `toolResult` blocks inside a `user` message (Anthropic-style
  threading); Mistral/Meta models get a prompt template applied server-side.

## 3. Generation parameters

- `inferenceConfig{maxTokens (≥1), temperature (0..1), topP (0..1),
  stopSequences[] (≤2500)}` — note Bedrock clamps the documented
  `temperature` range to `0..1` regardless of model.
- `additionalModelRequestFields` — free JSON passed to the model for anything
  Converse does not model: Anthropic `top_k`, `thinking`, `output_config`,
  `anthropic_beta`, `cache_control`, `context_management`; Nova
  `{"inferenceConfig": {"topK": N}}` and `{"reasoningConfig": {...}}`.
- `additionalModelResponseFieldPaths[]` — ≤10 JSON Pointers (e.g.
  `"/stop_sequence"`) surfaced back under `additionalModelResponseFields`.
- `performanceConfig{latency: standard|optimized}`, `serviceTier{type:
  priority|default|flex|reserved}`, `requestMetadata{str:str}` (≤16 entries,
  constrained charset), `promptVariables` (prompt-management only; mutually
  exclusive with `inferenceConfig`/`system`/`toolConfig`/`additionalModelRequestFields`).
- InvokeModel carries the same knobs as headers: `X-Amzn-Bedrock-Service-Tier`,
  `X-Amzn-Bedrock-PerformanceConfig-Latency`, `X-Amzn-Bedrock-Request-Metadata`.

## 4. Structured outputs

`outputConfig{textFormat{type: "json_schema", structure{…}}}` exists on
Converse (the `OutputFormatStructure` members were not read — *unverified*).
Per-model native JSON modes pass through `additionalModelRequestFields` /
InvokeModel. Tool definitions accept `strict: bool`.

## 5. Tool / function calling

- `toolConfig{tools[], toolChoice}`. `Tool` is a union: `toolSpec{name
  (1–64, [a-zA-Z0-9_-]+), description, inputSchema{json}, strict}` |
  `cachePoint` | `systemTool`.
- `toolChoice` ∈ `auto{}` | `any{}` | `tool{name}`; `tool` is documented as
  supported only by Anthropic Claude and Amazon Nova models.
- Assistant emits `toolUse{toolUseId, name, input}` (parsed JSON object; ids
  like `toolu_bdrk_…`); caller replies with a `user` message holding
  `toolResult{toolUseId, content[…], status}`. Streamed tool input arrives as
  partial-JSON strings in `contentBlockDelta.delta.toolUse.input`.

## 6. Streaming

- Framing: `application/vnd.amazon.eventstream` — binary messages (prelude
  with total/headers length + CRC32, typed headers, payload, trailing CRC32).
  Headers `:message-type` (`event|exception`), `:event-type`, `:content-type`
  (`application/json`), `:exception-type`. The HTTP `Content-Type` is
  `application/vnd.amazon.eventstream` with `x-amzn-bedrock-content-type:
  application/json` on InvokeModelWithResponseStream.
- `ConverseStreamOutput` events (verbatim): `messageStart{role}`,
  `contentBlockStart{contentBlockIndex, start{toolUse|toolResult|image}}`
  (emitted for tool use, not plain text), `contentBlockDelta{contentBlockIndex,
  delta{text | toolUse{input} | reasoningContent{text|signature|redactedContent}
  | citation | image | toolResult}}`, `contentBlockStop{contentBlockIndex}`,
  `messageStop{stopReason, additionalModelResponseFields}`, then
  `metadata{usage, metrics{latencyMs}, trace, performanceConfig, serviceTier}`
  **after** `messageStop`.
- Mid-stream exceptions are typed events: `internalServerException` (500),
  `modelStreamErrorException` (424; `originalMessage`, `originalStatusCode`),
  `validationException` (400), `throttlingException` (429),
  `serviceUnavailableException` (503); InvokeModelWithResponseStream adds
  `modelTimeoutException` (408).
- InvokeModelWithResponseStream wraps the model's native chunk JSON (Anthropic
  `message_start` … `message_stop` events) in `chunk.bytes`. Whether the
  OpenAI/Anthropic compatibility routes stream as SSE is not stated on the
  pages read — *unverified* (the SDK examples imply SSE).

## 7. Reasoning / thinking

- Converse block (verbatim): `{"reasoningContent": {"reasoningText": {"text",
  "signature"}}}` or `{"reasoningContent": {"redactedContent": "<base64>"}}`
  (a union, one or the other). Signatures must be echoed back unmodified with
  all prior messages or the request errors.
- Anthropic: `additionalModelRequestFields: {"thinking": {"type": "adaptive",
  "display": "summarized"|"omitted"}, "output_config": {"effort": "low|medium|
  high|xhigh|max"}}` on Converse; the legacy `{"type":"enabled",
  "budget_tokens":N}` form is confirmed for InvokeModel (its Converse use is
  the documented mechanism but no Converse-specific example was read —
  *unverified by example*). Thinking tokens are broken out only in the
  Anthropic-native body (`usage.output_tokens_details.thinking_tokens`);
  Converse `usage` has no thinking breakdown.
- Nova 2: `additionalModelRequestFields: {"reasoningConfig": {"type":
  "enabled", "maxReasoningEffort": "low|medium|high"}}`; reasoning text is
  returned as `"[REDACTED]"`; `high` forbids `temperature`/`topP`/`topK`.

## 8. Prompt caching

- Converse: `{"cachePoint": {"type": "default", "ttl": "5m"|"1h"}}` block in
  `messages[].content`, `system[]`, or `toolConfig.tools[]`. Prefix order is
  `tools → system → messages`; sending `ttl: "1h"` to a 5-minute-only model
  can raise `ValidationException`.
- Usage: `cacheReadInputTokens`, `cacheWriteInputTokens`,
  `cacheDetails[{inputTokens, ttl}]`; `inputTokens` counts **non-cached tokens
  only** (total = `inputTokens + cacheRead + cacheWrite`) — a different
  convention from OpenAI's `cached_tokens` sub-bucket.
- Anthropic via InvokeModel uses native `cache_control`; Nova adds implicit
  (unreported) caching. Cross-region routing can increase cache writes
  (entries are server-local).

## 9. Multimodal

`image` (bytes or `s3Location`), `document` (with optional `citations`),
`video`, `audio` blocks on Converse; support varies by model card. Nova 2 Lite
is multimodal in; Nova Sonic (`global.amazon.nova-2-sonic-v1:0`) is
speech-to-speech; `amazon.nova-2-multimodal-embeddings-v1:0` embeds media.

## 10. Models

| Family | Example ids (as read) | Notes |
|---|---|---|
| Amazon Nova 2 | `amazon.nova-2-lite-v1:0`, `global.amazon.nova-2-lite-v1:0` | 1M ctx, 64K out; not on chat-completions/mantle |
| Amazon Nova 1 | `amazon.nova-premier-v1:0`, `nova-pro`, `nova-lite`, `nova-micro` | profile ids `us.amazon.nova-*` |
| Anthropic | `anthropic.claude-sonnet-4-6`, `anthropic.claude-opus-4-5-20251101-v1:0` | prefer `us.`/`global.` profiles |
| OpenAI open-weight | `openai.gpt-oss-120b-1:0`, `openai.gpt-oss-20b-1:0` | the chat-completions route's example models |
| Meta / Mistral / DeepSeek / others | per model card | InvokeModel bodies are model-native |

Cross-region inference: geographic profiles (`us.`, `eu.`, `jp.`, `au.`, …)
route to a fixed destination set; `global.` routes to all commercial Regions
(≈10% cheaper, list may grow). Price is the calling Region's; the SCP must
allow every destination Region (`"aws:RequestedRegion": "unspecified"` for
global); CloudTrail `additionalEventData.inferenceRegion` reveals where it ran.
Inference profiles do not support Provisioned Throughput.

## 11. Auth, limits, errors

- **SigV4** (service `bedrock`): `Authorization: AWS4-HMAC-SHA256 Credential=
  <AKID>/<YYYYMMDD>/<region>/bedrock/aws4_request, SignedHeaders=host;x-amz-date
  [;x-amz-security-token], Signature=<hex>`, `X-Amz-Date` (ISO8601 basic),
  `X-Amz-Security-Token` for STS credentials. The signing chain is four HMACs
  over `"AWS4"+secret → date → region → service → "aws4_request"` plus a
  SHA-256 of the canonical request; whether Bedrock requires an explicit
  `X-Amz-Content-Sha256` header is *unverified* (it is documented as required
  for S3 only).
- **Bedrock API keys** (bearer): `Authorization: Bearer <key>`; env
  `AWS_BEARER_TOKEN_BEDROCK`. Short-term keys (≤12h, region-bound, generated
  from IAM creds) and long-term IAM service-specific credentials ("exploration
  only"); IAM gate `bedrock:CallWithBearerToken` with condition
  `bedrock:bearerTokenType ∈ SHORT_TERM|LONG_TERM`.
- No `x-ratelimit-*` headers are documented — *unverified/absent*. Quotas are
  per-model TPM/RPM per endpoint; `Retry-After` may appear on 529.
- Error wire shape (AWS-general REST-JSON): status + `x-amzn-RequestId` +
  `x-amzn-ErrorType: <ExceptionName>` + body `{"message": "…"}`.
- Operation errors: `ValidationException` 400, `AccessDeniedException` 403,
  `ResourceNotFoundException` 404, `ModelTimeoutException` 408,
  `ModelErrorException` 424 (`originalStatusCode`, `resourceName`),
  `ModelStreamErrorException` 424, `ThrottlingException` 429,
  `ModelNotReadyException` 429, `ServiceQuotaExceededException` 400,
  `InternalServerException` 500, `ServiceUnavailableException` 503,
  `overloaded_error` 529 (troubleshooting page). Common: `ExpiredTokenException`
  403, `IncompleteSignature` 403, `NotAuthorized` 401, `UnrecognizedClientException`
  403, `RequestEntityTooLargeException` 413, `UnknownOperationException` 404.
  The common-errors table lists `ThrottlingException` as 400 while operation
  pages say 429 — map by exception name, not status.

## 12. Distinctive to Bedrock

- **Four interfaces on one host**; Converse is the only one with a
  host-owned neutral body; InvokeModel is per-model dialect pass-through.
- **Binary event-stream** framing with typed exception events mid-stream.
- **Guardrails** as a first-class request field (`guardrailConfig{
  guardrailIdentifier, guardrailVersion, trace: enabled|disabled|enabled_full}`,
  `streamProcessingMode: sync|async` on the stream), `guardContent` blocks
  (once present, *only* those blocks are assessed), `stopReason:
  guardrail_intervened` with masked text (`{NAME}`/`{EMAIL}` placeholders)
  and a large `trace.guardrail{inputAssessment, outputAssessments,
  invocationMetrics, appliedGuardrailDetails}` that rides the `metadata` event
  when streaming. On the OpenAI-compatible route the same controls are headers
  (`X-Amzn-Bedrock-GuardrailIdentifier/Version/Trace`) plus body
  `amazon-bedrock-guardrailConfig.tagSuffix`; InvokeModel responses gain
  `amazon-bedrock-guardrailAction: INTERVENED|NONE` and `amazon-bedrock-trace`.
- **Cross-region / global inference profiles** as model-id prefixes.
- `serviceTier`, `performanceConfig.latency`, `requestMetadata`, prompt
  routers (`trace.promptRouter.invokedModelId`), `metrics.latencyMs`.
- Cache accounting excludes cached tokens from `inputTokens`.

## 13. Mapping to `ocai`

**(a) Codec vs host.** Three answers for three routes:

- `/openai/v1/chat/completions` and `/anthropic/v1/messages` are served by the
  **existing** `openai/chat_completions` and `anthropic/messages` codecs through
  a `Bedrock` `Host` value plus a bearer `Credential`. Traits needed: a
  `Custom`-style URL template with the dialect path remapped
  (`/openai/v1/chat/completions`, `/anthropic/v1/messages`), the dialect's
  `first_party_headers` kept (`anthropic-version`), and a region in the origin.
  `DialectTraits` as it stands (`vendor`, `first_party_headers`,
  `cloud_body_version`, `first_party_base_url`) suffices; the host needs a
  `region` and a `route` (`runtime|mantle`) field. Model-card gating (which
  models accept which route) is `CapabilityProfile` data.
- **Converse needs its own interface subpackage, `ocai.bedrock.converse`**, with
  a `bedrock` vendor, its own `wire.py`/`codec.py`, and an event-stream
  decoder (`ocai.wire` gains an `EventStreamParser` sibling to `SSEParser`,
  sans-io, CRC-checked). The body is close to Anthropic's (top-level `system`,
  typed blocks, `toolResult` in `user` turns) so the codec is a pattern replay
  of `anthropic/messages`, but `inferenceConfig` nesting, camelCase, the
  `stopReason` enum, and the `metadata`-after-`messageStop` ordering are their
  own edges. Converse is the route that gives **one codec for every Bedrock
  model**, which is the reason to build it.
- `InvokeModel` is pass-through: the Anthropic codec encodes a Messages body,
  and an `InvokeModel` envelope (an `EnvelopeTransform`) drops `model`,
  injects `anthropic_version: "bedrock-2023-05-31"` via the dialect's
  `cloud_body_version` (today it carries the Vertex value — this becomes a
  **per-host map**, not a single tuple), moves `anthropic_beta` from header to
  body array, and unwraps `chunk.bytes`. That is the `_RawPredictEnvelope`
  pattern with one more field.

**(b) Auth.** Bearer API keys are a plain `ApiKey` applied at the driver leaf.
SigV4 is HMAC-SHA256 + SHA-256 over a canonical request — stdlib `hmac`/
`hashlib` suffice, so a `SigV4Credential` can live in a cloud-hosting plugin
(`ocai-aws`) with **no third-party signing library**; rule 12 would permit a
narrow one but it is not needed. Credential refresh (STS session tokens, IMDS)
is the credential's concern, applied per attempt after hooks.

**(c) Honesty.** `trace.guardrail` → censused extension `bedrock.guardrail_trace`;
`stopReason: guardrail_intervened` and `content_filtered` → `ContentFilterError`
*or* a canonical finish with `native` preserved (the response is HTTP 200 with
masked text — a `SemanticShift` "masked output" record, never a silent pass).
`malformed_model_output`/`malformed_tool_use`/`model_context_window_exceeded`
→ open finish codes with `native`. `metrics.latencyMs`, `serviceTier`,
`performanceConfig`, `trace.promptRouter` → `bedrock.*` extensions.
`inferenceConfig.temperature` is `0..1`: out-of-range IR values pass verbatim
with `APPROXIMATED`. Usage: `cacheRead/WriteInputTokens` map to the existing
cache buckets, but `inputTokens` excluding cached tokens is a `SemanticShift`
on the usage edge (the disjoint-bucket rule must be applied in the other
direction from OpenAI). `reasoningContent.signature` round-trips like
Anthropic's `signature` (the `ocai.signature_buffer` mechanism already
exists); `redactedContent` → `PartUnknown`-safe redacted-thinking part.
`requestMetadata` → `provider_options["bedrock.converse"]`.

**(d) Errors.** Map by `x-amzn-ErrorType` / stream `:exception-type`, never by
status alone: `ThrottlingException`, `ModelNotReadyException`, `overloaded_error`
→ `RateLimitError`; `ServiceUnavailableException`, `InternalServerException`,
`ModelTimeoutException`, `ModelStreamErrorException`, `ModelErrorException` →
`TransientError`; `AccessDeniedException`, `ExpiredTokenException`,
`UnrecognizedClientException`, `NotAuthorized`, `IncompleteSignature` →
`AuthError`; `ValidationException` whose stream/finish reports
`model_context_window_exceeded` → `ContextLengthError` (otherwise generic
`OcaiError` with `code`); `guardrail_intervened` → `ContentFilterError` when
the output is blocked. Mid-stream exception events must surface as the
canonical mid-stream error shape (code + native + retryable), per rule 8.

**(e) Priority: P0 — Bedrock is first among the three clouds.** Rationale: it
is the host most enterprises already have IAM, VPC endpoints, and spend
commitments on; it hosts Anthropic (ocai's second certified dialect) so the
InvokeModel envelope is a near-free proof of "hosting composes"; and Converse
is the one place a single codec covers Nova, Meta, Mistral, and DeepSeek
without a dialect each. Effort: **3 WUs** — (1) `ocai-aws` plugin with
`SigV4Credential` + `Bedrock` host + InvokeModel envelope for Anthropic,
recorded pairs; (2) `EventStreamParser` + the Anthropic streaming fold through
`chunk.bytes`; (3) `ocai.bedrock.converse` unary + streaming codec with
`EdgeContract`, guardrail/usage census, fold triples. The OpenAI/Anthropic
compatibility routes are a half-WU rider on (1).

## Sources (read 2026-11-10)

- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStream.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStreamOutput.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModelWithResponseStream.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlock.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ReasoningContentBlock.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_TokenUsage.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/CommonErrors.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference-chat-completions.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-streaming.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-adaptive-thinking.html
- https://docs.aws.amazon.com/nova/latest/nova2-userguide/request-response-schema.html
- https://docs.aws.amazon.com/nova/latest/nova2-userguide/extended-thinking.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv-create-signed-request.html
- https://docs.aws.amazon.com/transcribe/latest/dg/streaming-setting-up.html (event-stream framing)
