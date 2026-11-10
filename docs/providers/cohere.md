# Cohere (Command) v2 Chat API — Capabilities & Features

> Currency: researched 2026-11-10 against docs.cohere.com (v2 API reference and
> guides). Cohere also exposes an OpenAI-compatible shim, but the native v2 surface
> is **not** OpenAI-shaped: upper-case enums, `tool_plan`, span-anchored citations,
> request-level `documents`, `k`/`p` sampling names. Anything the docs did not state
> is marked **unverified**.

Base: `https://api.cohere.com/v2`. Auth: `Authorization: Bearer <key>`; optional
`X-Client-Name`. One chat endpoint, `POST /v2/chat`, with `stream: true` for SSE.
The v1 endpoint (`preamble`, `chat_history`, `connectors`) is legacy; the v1→v2
migration guide is the cleanest statement of the current shapes.

## 1. API surface / endpoints

| Capability | Endpoint |
|---|---|
| Chat (unary + streaming) | `POST /v2/chat` |
| OpenAI-compatible shim | `https://api.cohere.ai/compatibility/v1/chat/completions` (+ `/embeddings`, `/audio/transcriptions`) — **no `documents`, `citation_options`, `connectors`**; `reasoning_effort` only `none`/`high`; unsupported: `store`, `metadata`, `logit_bias`, `top_logprobs`, `n`, `modalities`, `prediction`, `audio`, `service_tier`, `parallel_tool_calls` |
| Embed, Rerank, Classify, Tokenize, Parse, Audio transcriptions, Datasets, Fine-tuning | separate endpoints (out of chat scope) |

## 2. Request & response model

**Messages** (`messages[]`, by `role`):

| Role | Fields |
|---|---|
| `system` | `content`: string or text blocks |
| `user` | `content`: string or blocks `text`, `image_url` |
| `assistant` | `content` (string or blocks `text`, `thinking`), `tool_calls[]`, `tool_plan`, `citations[]` |
| `tool` | `tool_call_id` (required), `content`: JSON string or blocks `{"type":"document","document":{data, id?}}` |

Request-level **`documents[]`**: strings or `{id?, data: {title, snippet, ...}}`;
auto ids are `doc:<n>`.

**Response**: `id`, `finish_reason`, `message{role: assistant, content[]
({type: text, text} | {type: thinking, thinking}), tool_calls[]{id, type: function,
function{name, arguments: string}}, tool_plan, citations[]}`, `usage{billed_units{
input_tokens, output_tokens, search_units, classifications}, tokens{input_tokens,
output_tokens}, cached_tokens}`, `logprobs[]{token_ids, text, logprobs}`.
`finish_reason` ∈ `COMPLETE | STOP_SEQUENCE | MAX_TOKENS | TOOL_CALL | ERROR | TIMEOUT`.

**Citation**: `{start, end, text, sources[]{type: document|tool, id, document |
tool_output}, content_index, type: TEXT_CONTENT | THINKING_CONTENT | PLAN}`;
`start`/`end` index into the cited content block; tool-sourced ids are
`<tool_call_id>:<index>`.

## 3. Generation parameters

| Field | Type / range / default | Notes |
|---|---|---|
| `model` | string | §10 |
| `messages` | required | |
| `stream` | bool, default false | SSE |
| `max_tokens` | int | |
| `stop_sequences` | ≤ 5 strings | |
| `temperature` | double, **default 0.3** | |
| `seed` | int | |
| `frequency_penalty`, `presence_penalty` | **0.0–1.0**, default 0 | not OpenAI's -2..2 |
| `k` | 0–500, default 0 (off) | top-k |
| `p` | 0.01–0.99, default 0.75 | top-p |
| `logprobs` | bool | |
| `tools`, `tool_choice`, `strict_tools` | `REQUIRED \| NONE`; strict experimental | §5 |
| `documents`, `citation_options.mode` | `FAST \| ACCURATE \| OFF` (reference also lists `ENABLED \| DISABLED`; guides use lowercase) — inconsistency | §12 |
| `response_format` | `{type: text \| json_object, json_schema?}` | §4 |
| `safety_mode` | `CONTEXTUAL` (default) \| `STRICT` \| `OFF` | §11 |
| `thinking` | `{type: enabled \| disabled, token_budget}` | §7 |
| `priority` | int, default 0 (lower = higher priority) | queue hint |

No `n`, no `user`, no `parallel_tool_calls` knob, no `reasoning_effort` on v2.

## 4. Structured outputs

- JSON mode: `response_format: {"type":"json_object"}`; prompt must ask for JSON or
  "it may generate endlessly".
- JSON Schema mode: `response_format: {"type":"json_object","json_schema": {...}}`
  (the schema rides under the *same* type; there is no `json_schema` type). Top-level
  `type` must be `object`; every object needs ≥ 1 `required`; nesting unlimited with
  a schema, ≤ 5 levels without. Supported: basic types, arrays, nested objects,
  `enum`, `const`, `pattern`, `format` (`date-time|uuid|date|time`), `$ref`/`$def`,
  `additionalProperties`, `anyOf`. Unsupported: `allOf`, `oneOf`, `not`, numeric
  ranges, array/string length bounds, regex anchors/lookarounds, other formats.
- `strict_tools: true` enforces tool names/params/required/types; needs ≥ 1
  required parameter per tool; ≤ 200 fields across tools; v2 only.
- JSON mode is **not supported in RAG mode** (with `documents`). Schemas are cached
  after the first requests. Models: Command A+, Command A, Command R+/R (08-2024).

## 5. Tool / function calling

- Definition: `{"type":"function","function":{name, description?, parameters:
  JSON Schema}}` (same wrapper as OpenAI, same argument string).
- `tool_choice`: `"REQUIRED"` (force ≥ 1 call) or `"NONE"` (force text); omit for
  auto. **No named-tool forcing.** Forcing only on Command R7B and newer.
- The assistant turn returns **`tool_plan`** (free-text reflection on next steps)
  plus `tool_calls[]` with server-generated `id`s. Parallel calls are returned in
  one message; multi-step loops continue until a turn has no tool calls.
- Tool results: one `tool` message per call with `tool_call_id` and `content` as a
  JSON string or **document blocks** (`{"type":"document","document":{data, id?}}`)
  so the final answer can cite them (`sources[].type = "tool"`,
  `id = "<tool_call_id>:<index>"`, `tool_output`).
- Replay: append the assistant message (with `tool_plan` and `tool_calls`) then the
  tool messages; thinking blocks are allowed in assistant content but whether they
  must be echoed is **not documented**.
- Server-side tools: none in v2 (v1 `connectors` were removed; web search is "a
  user-defined tool"). `safety_mode` with `tools` or `documents` is forced to
  `CONTEXTUAL`.

## 6. Streaming

SSE with `event:` and `data:` lines (named events).

| Event | Payload |
|---|---|
| `message-start` | `id`, `delta.message.role` |
| `content-start` | `index`, `delta.message.content{type: text\|thinking, text}` |
| `content-delta` | `index`, `delta.message.content.text` or `.thinking`, optional `logprobs` |
| `content-end` | `index` |
| `tool-plan-delta` | `delta.message.tool_plan` |
| `tool-call-start` | `index`, `delta.message.tool_calls{id, type, function{name, arguments}}` |
| `tool-call-delta` | `index`, `delta.message.tool_calls.function.arguments` (fragment) |
| `tool-call-end` | `index` |
| `citation-start` | `index`, `delta.message.citations{start, end, text, sources, type}` |
| `citation-end` | `index` |
| `message-end` | `id`, `delta.finish_reason`, `delta.usage{billed_units, tokens, cached_tokens}`, `delta.error` |
| `debug` | `event_type` (`stream-start`, `search-queries-generation`, `search-results`, `text-generation`, `citation-generation`, `stream-end`, `debug`), `prompt` |

RAG order: `message-start → content-start → content-delta* → citation-start/end* →
content-end → message-end`. With `citation_options.mode = "accurate"` (default)
citations are generated **after** the full text; with `"fast"` they stream inline
with slightly lower precision. `content-start` with `type: thinking` precedes the
text block on reasoning models. Mid-stream failures surface as `message-end` with
`delta.error` / `finish_reason: ERROR|TIMEOUT`.

## 7. Reasoning / thinking

- Model: `command-a-reasoning-08-2025` (Command A+ "covers thinking budgets and
  enabling/disabling in the Reasoning guide" — support on `command-a-plus-05-2026`
  implied, **unverified**).
- Enabled by default; `thinking: {"type": "disabled"}` turns it off;
  `thinking: {"token_budget": N}` caps it ("leave at least 1K tokens for the
  response"; 31K for maximum reasoning). When the budget is exceeded "the model will
  immediately proceed with the final response".
- Output: `message.content[]` items `{type: "thinking", thinking}` before
  `{type: "text"}`; streamed via `content-delta` with `delta.message.content.thinking`.
  Citations may target thinking (`type: THINKING_CONTENT`) or the plan (`PLAN`).
- No signature, no encrypted blob, no effort enum on v2 (the compat shim maps
  `reasoning_effort: none|high`); reasoning-token usage bucket: not documented
  (**unverified**). Safety Modes are "not optimized" when reasoning is on.

## 8. Prompt / context caching

`usage.cached_tokens` exists on the response and `message-end` delta, but no caching
guide (opt-in, prefix rules, TTL, pricing) was found on docs.cohere.com —
**unverified**; treat caching as automatic and undocumented.

## 9. Multimodal

- Image input on `command-a-vision-07-2025` and `command-a-plus-05-2026`:
  `{"type":"image_url","image_url":{"url": data-URI | https, "detail": low|high|auto}}`
  in user content. ≤ 20 images or 20 MB per request; PNG/JPEG/WEBP/non-animated GIF;
  `low` = 256 tokens (fit 512×512), `high` = 256 tokens per 512×512 tile + preview
  (fit 1536×2048), `auto` picks `high` above 768 px. HTTP URLs are unavailable on
  Azure/Bedrock deployments.
- Documents are **structured data** (`documents[]`, document blocks), not files;
  no PDF part on chat (use the Parse endpoint). No audio in/out on chat
  (transcription is a separate model), no image generation.
- Whether images may appear in assistant/tool messages: not stated (**unverified**).

## 10. Models (snapshot 2026-11-10)

| Model | Context / max out | Modality | Notes |
|---|---|---|---|
| `command-a-plus-05-2026` | 128k / 64k | text + image | newest; 25B active / 218B MoE; open weights (Apache 2.0) |
| `command-a-03-2025` | 256k / 8k | text | 500 rpm production |
| `command-a-reasoning-08-2025` | 256k / 32k | text | thinking; prod keys treated as trial until sales contact |
| `command-a-vision-07-2025` | 128K / 8K | text + image | |
| `command-a-translate-08-2025` | 8K / 8K | text | translation |
| `command-r-plus-08-2024`, `command-r-08-2024`, `command-r7b-12-2024` | 128k / 4k | text | |
| `north-mini-code-1.0` (256k/64k), `north-small-translate-1.0`, `tiny-aya-*`, `c4ai-aya-expanse-32b`, `c4ai-aya-vision-32b` | various | | regional/open models |
| Deprecated 2025-09-15 | `command-r`, `command-r-plus`, `command-r-03-2024`, `command-r-plus-04-2024`, `command-light`, `command` | | |

Pricing: not captured (pricing page not fetched) — **unverified**.

## 11. Auth, limits, errors

- Rate limits: chat 20 req/min on trial keys for every model; production 500 req/min
  on Command A/R family, "contact sales" for Command A+, Reasoning, Vision,
  Translate; trial keys and prod keys on newer variants capped at 1,000 calls/month.
  Trial token limit example: 100,000 tokens/min. No rate-limit headers documented.
- Error body: `{message, id}` (status-specific pages give example messages only).

| HTTP | Meaning |
|---|---|
| 400 | invalid body / values |
| 401 | missing, invalid or expired key |
| 402 | billing limit reached |
| 403 | forbidden (not detailed) |
| 404 | model / dataset / connector not found |
| 422 | unprocessable (not detailed) |
| 429 | rate limit |
| 498 | deny-listed token |
| 499 | request cancelled by client |
| 500 / 501 / 503 / 504 | server / not implemented / unavailable / gateway timeout |

Safety modes: `CONTEXTUAL` (default; wide-ranging with core protections), `STRICT`
(avoids sensitive topics, profanity, regulated activity), `OFF` (only on models
older than Command R7B). With `tools` or `documents` the mode is **forced to
`CONTEXTUAL`** whatever was sent; core child-safety protections are unconditional.
Context-overflow and moderation codes: **not documented** as distinct statuses.

## 12. Distinctive features

- **Span-anchored citations** (`start`/`end`/`text`/`sources`) over request
  `documents` and tool outputs, with `accurate` vs `fast` generation modes, and
  citation targets that can be thinking or plan text.
- **`tool_plan`**: a natural-language plan emitted beside tool calls.
- Tool results as **document blocks** so they are citable; tool-source ids
  `<tool_call_id>:<index>`.
- Upper-case enums everywhere (`REQUIRED`, `COMPLETE`, `CONTEXTUAL`, `ACCURATE`).
- `safety_mode` as a first-class request knob with forced fallback under RAG/tools.
- `k`/`p` naming, `temperature` default 0.3, penalties on a 0–1 scale.
- `priority` queue hint; `usage.billed_units` distinct from `usage.tokens`
  (`search_units`, `classifications`).
- `debug` stream events; v1→v2 removed `connectors`, `prompt_truncation`,
  `search_queries_only`, `conversation_id`, `force_single_step`.

## 13. Mapping to `ocai`

**(a) Interface decision.** Not OpenAI-compatible: message content is a typed block
list with `thinking`, tool choice is `REQUIRED|NONE`, citations and `documents` are
first-class, usage has `billed_units`, streaming uses named events with per-index
`citation-*`. It needs its own interface subpackage, **`ocai.cohere.v2`**
(`NodeId("cohere","v2",tag,"chat.*")`), mirroring `ocai.anthropic.messages` in
layout. The compatibility shim could be a `DialectTraits` host of
`openai/chat_completions` for text-only use, but it drops exactly the features that
make Cohere worth adapting (citations, documents, safety mode), so it is a fallback
edge with a loud EdgeContract, not the plan.

**(b) Parts.** `PartText` with `annotations` populated from `citations[]`
(`start`/`end` are block-relative offsets — the one provider whose citations already
match ocai's span model; validate against decoded text, else censused extension);
`PartReasoning(text)` from `thinking` blocks; `PartToolCall` (`arguments` string);
`PartToolResult` whose nested parts carry the document blocks: Cohere documents are
structured JSON, not media, so model them as `PartDocument` with an inline `data`
object and `id` (ABSENT elsewhere) or, until `PartDocument` grows that source, as a
censused extension `cohere.document`; `PartImage` (user only).
`tool_plan` → censused extension `cohere.tool_plan` (it is neither text content nor
reasoning); request-level `documents[]` → `ChatRequest` has no such field →
`provider_options["cohere.v2"].documents` initially, with a promotion trigger once a
second interface (Gemini grounding, Anthropic `document` blocks) shows congruent
semantics; citations with `type: PLAN|THINKING_CONTENT` → extension (no part to
anchor to). `debug` events → `PartOpaque`/`raw_event` only.

**(c) Reasoning.** `ReasoningConfig.include_thoughts` → `thinking.type`
(first-class); `budget_tokens` → `thinking.token_budget` (first-class; the
"proceed immediately when exceeded" behaviour is a declared **SemanticShift** vs
Anthropic's budget semantics); `effort` → UNSUPPORTED (no enum on v2; the shim's
`none|high` is a different interface). Thinking is plain text, no signature, no
`ProviderRef`; echo requirement unverified → the codec re-emits `PartReasoning` as
`thinking` blocks and the census records it as best-effort.

**(d) Streaming.** `fold(stream) == complete` is achievable: `content-start/delta/end`
and `tool-call-start/delta/end` map directly onto PART_START/DELTA/STOP with
`index`; `tool-plan-delta` accumulates into the extension; `citation-start` arrives
after text in `accurate` mode, so `DeltaAnnotation` must attach to an already-sealed
text part (the fold law must allow post-STOP annotation deltas, or the codec holds
the text part open until `message-end`); `message-end` carries usage + finish +
`error` → `StreamEnd`. Known gap: `usage.cached_tokens` with no documented source.

**(e) Errors.** 429 → `RateLimitError`; 401, 402, 403, 498 → `AuthError`; context
overflow has no distinct code (**unverified**; message-sniff or `MAX_TOKENS`
finish) → `ContextLengthError` only when evidenced; no moderation status —
`safety_mode` refusals arrive as normal text → `ContentFilterError` is never raised
by this codec (census it); 499, 500, 501, 503, 504 and `finish_reason: ERROR|TIMEOUT`
→ `TransientError`. Finish map: `COMPLETE→complete`, `STOP_SEQUENCE→stop_sequence`,
`MAX_TOKENS→max_tokens`, `TOOL_CALL→tool_call`, `ERROR/TIMEOUT→error`, natives
preserved. `tool_choice` named-function from the IR → UNSUPPORTED-and-reported
(Cohere has only `REQUIRED`); penalties outside 0–1 and `temperature` defaults →
verbatim + APPROXIMATED.

**(f) Priority: P3 (watch).** Rationale: a full new interface for a single-vendor
family with lower demand than the OpenAI-shaped dialects, and its two interesting
features (span citations, documents) are better promoted to the IR once Gemini
grounding and Anthropic citations have both landed — Cohere then becomes the third
data point that justifies a first-class `documents`/annotation design. Effort if
pulled forward: a full WU-13 / WU-14a / WU-14b triple (≈ 3 WUs) plus ≈ 0.5 WU for
the citation→annotation validation path.

## Sources (read 2026-11-10)

- https://docs.cohere.com/reference/chat
- https://docs.cohere.com/reference/chat-stream
- https://docs.cohere.com/docs/migrating-v1-to-v2
- https://docs.cohere.com/docs/rag-citations
- https://docs.cohere.com/docs/rag-streaming
- https://docs.cohere.com/docs/tool-use-overview
- https://docs.cohere.com/docs/tool-use-usage-patterns
- https://docs.cohere.com/docs/structured-outputs
- https://docs.cohere.com/docs/reasoning
- https://docs.cohere.com/docs/safety-modes
- https://docs.cohere.com/docs/image-inputs
- https://docs.cohere.com/docs/command-a-plus
- https://docs.cohere.com/docs/models
- https://docs.cohere.com/docs/compatibility-api
- https://docs.cohere.com/docs/rate-limits
- https://docs.cohere.com/reference/errors
