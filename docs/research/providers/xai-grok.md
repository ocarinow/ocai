# xAI (Grok) API — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

> Currency: researched 2026-11-10 against docs.x.ai. xAI now labels Chat Completions
> a **legacy** endpoint and ships new features on the Responses API first; model
> IDs, tiers and prices drift. Anything the docs did not state is marked
> **unverified**.

Base: `https://api.x.ai/v1`. Auth: `Authorization: Bearer <key>`. Two chat
protocols: an **OpenAI-Chat-Completions-shaped** `/v1/chat/completions` (stateless,
"legacy endpoint, limited updates") and an **OpenAI-Responses-shaped** `/v1/responses`
(stateful, server-side agentic tools, encrypted reasoning). There is no
Anthropic-compatible endpoint in the docs.

## 1. API surface / endpoints

| Surface | Endpoint |
|---|---|
| Chat completions (legacy) | `POST /v1/chat/completions` |
| Deferred chat completion | `POST /v1/chat/completions` with `deferred: true` → `GET /v1/chat/deferred-completion/{request_id}` (202 until ready; result retrievable once within 24 h) |
| Responses | `POST /v1/responses`, `GET`/`DELETE /v1/responses/{response_id}` (stored 30 days), `POST /v1/responses/compact` |
| Models | `GET /v1/models` (listed in the reference index; **unverified** body) |
| Image generation / edit | `POST /v1/images/generations`, `POST /v1/images/edits`, `GET /v1/images/{request_id}` (deferred) |
| Collections (RAG) search | collections API + `file_search` tool |
| Voice (speech-to-speech, STT, TTS), video generation, batch | separate surfaces |

## 2. Request & response model

**Chat completions**: `messages[]` (`system|user|assistant` "in any order", `tool`),
content parts "image and text" (shape not enumerated on the reference; the
image-understanding guide documents only the Responses form). Response:
`chat.completion` with `choices[]{index, message{role, content, reasoning_content,
refusal, tool_calls[]}, finish_reason, logprobs}`, top-level **`citations[]`**
(URLs), `output_files[]`, `system_fingerprint`, `service_tier`, and `usage`
(§11). `finish_reason`: `stop`, `length`, **`end_turn`** (non-OpenAI value).

**Responses**: `input` (string or typed items: messages with `input_text` /
`input_image`, `reasoning` items, `function_call` / `function_call_output`),
`instructions`, `previous_response_id`, `store` (default true), `include`
(`reasoning.encrypted_content`). Output items: `message` (`content[]` of
`output_text{text, logprobs, annotations[]}`), `reasoning{summary[]{summary_text},
encrypted_content}`, `function_call{name, arguments, call_id}`, and tool items
(`image_generation_call{result}` with ids `ig_`/`ie_`, `custom_tool_call` for
X-search sub-tools; `web_search_call`/`code_interpreter_call`/`mcp_call` item names
**unverified** on the reference page). `status`: `completed|in_progress|incomplete`.

## 3. Generation parameters

| Field | Chat completions | Responses | Notes |
|---|---|---|---|
| `model` | ✓ | ✓ | |
| `temperature` | 0–2, "sampled at most 1" | same | |
| `top_p` | ≤ model default 0.95 | same | |
| `top_k`, `min_p` | — | ✓ (disabled when unset) | |
| `seed` | best-effort | — | check `system_fingerprint` |
| `frequency_penalty`, `presence_penalty` | -2–2; **rejected on reasoning models** | **unsupported** (echoed) | |
| `stop` | ≤ 4; **rejected on reasoning models** | — | |
| `n` | ✓ | — | |
| `max_completion_tokens` / `max_tokens` (deprecated) | visible output only; default 128,000 | `max_output_tokens` (min? default 128,000) | reasoning not counted |
| `reasoning_effort` | `low\|medium\|high\|xhigh` per model | `reasoning.effort` (+ `generate_summary`, `summary`); `reasoning_effort` as fallback | §7 |
| `response_format` | `text\|json_object\|json_schema{name, schema, strict}` | `text.format` same | §4 |
| `tools`, `tool_choice`, `parallel_tool_calls` | functions only, ≤ 1000 | functions + server tools | §5 |
| `search_parameters` | `{mode: off\|on(default)\|auto, sources, from_date, to_date, max_search_results, return_citations}` | same object (still listed) | Live Search; see §12 |
| `web_search_options` | OpenAI-compat shim (`search_context_size` → max_search) | — | |
| `logprobs`, `top_logprobs` (0–8) | ignored on grok-4.20+ | same | |
| `guidelines` | per-category output instructions (400 with `stop` or multi-agent) | same | non-OpenAI |
| `prompt_cache_key` | sticky routing → header `x-grok-conv-id` | same | §8 |
| `safety_identifier`, `user` | ✓ | ✓ | |
| `service_tier` | `default\|priority\|fast` (2× billing when confirmed) | same | |
| `deferred` | ✓ | `background` **unsupported** | |
| `stream`, `stream_options.include_usage` | ✓ | `stream` | §6 |
| `logit_bias`, `metadata`, `truncation` | unsupported | unsupported | |
| `max_turns`, `context_management` | — | ✓ / parsed-not-executed | agent loop cap |

## 4. Structured outputs

`response_format: {"type":"json_schema","json_schema":{"name","schema","strict":true}}`
(Responses: `text.format`). `json_object` accepted for shapeless JSON. Rich schema
support: `string|number|integer|boolean|null|enum|const|array|object|anyOf|oneOf`,
single-subschema `allOf`, non-circular `$ref`/`$defs`; enforced formats
`date|time|date-time|email|uuid|ipv4|ipv6|uri`; `additionalProperties` defaults to
false; guaranteed `minLength`/`maxLength` ≤ 2048, `minItems`/`maxItems` ≤ 256,
`minProperties`/`maxProperties` ≤ 64; `pattern` is an ECMAScript subset (no
backreferences/lookarounds). Rejected with 400: empty `enum`/`anyOf`, boolean
property schemas, `maxContains`/`minContains`, array-form `items`. **Tool-call
arguments are always strict** ("`strict` implicitly `true`"). Combinable with
server-side tools and function calling ("supported Grok 4 family models").

## 5. Tool / function calling

- Definition (Responses, flat): `{"type":"function","name","description","parameters"}`;
  root must be `object` (or `anyOf`/`oneOf` of objects); ≤ 350 tools per request
  (reference says ≤ 1000). Chat completions use the nested OpenAI form
  (**unverified** on the current page).
- `tool_choice`: `auto` (default), `required`, `none`, `{"type":"function","function":{"name"}}`.
- Parallel by default; `parallel_tool_calls: false` → at most one.
- Responses items: `function_call{name, arguments, call_id}` → reply with
  `{"type":"function_call_output","call_id","output"}`; continue with
  `previous_response_id`.
- **Streaming: "the function call is returned in whole in a single chunk, not
  streamed across chunks."**
- **Server-side tools (Responses only)**, declared in `tools`:

| Tool type | Fields | Output / billing |
|---|---|---|
| `web_search` | `filters.allowed_domains` / `filters.excluded_domains` (≤ 5, mutually exclusive), `enable_image_understanding` (`view_image`), `enable_image_search` | `url_citation` annotations; $5 / 1k calls |
| `x_search` | `allowed_x_handles` / `excluded_x_handles` (≤ 20), `from_date`, `to_date`, `enable_image_understanding`, `enable_video_understanding` | `custom_tool_call` items named `x_keyword_search`, `x_semantic_search`, `x_thread_fetch`, `x_user_search`; $5 / 1k posts + $10 / 1k profiles (since 2026-09-21, per item) |
| `code_interpreter` (SDK: `code_execution`) | — | $5 / 1k calls |
| `file_search` (SDK: `collections_search`) | `vector_store_ids`, `max_num_results` | citations `collections://<collection_id>/files/<file_id>`; $2.50 / 1k calls |
| `image_generation` | `action: auto\|generate\|edit`; no size params | `image_generation_call.result` (base64, no data-URL prefix); Imagine per-image rates |
| `mcp` | `server_url` (HTTP/SSE), `server_label`, `server_description`, `allowed_tools`, `authorization`, `headers` | `require_approval`/`connector_id` unsupported |

Tool usage counts: `usage.server_side_tool_usage_details.{web_search_calls,
x_search_calls, x_posts_fetched, x_users_fetched, code_interpreter_calls,
file_search_calls, document_search_calls, image_generation_calls, mcp_calls}`,
`usage.num_sources_used`, `usage.num_server_side_tools_used`.

## 6. Streaming

Both endpoints stream **data-only SSE** (`data: {...}`), terminated by `data: [DONE]`
(the Responses reference says so too, unlike OpenAI's typed events — **unverified**
whether `event:` lines are present).

| Chat completions chunk | Notes |
|---|---|
| `delta.role`, `delta.reasoning_content`, `delta.content` | reasoning appears in the first chunk of the streaming example |
| `delta.tool_calls` | whole call in one chunk |
| `finish_reason` | `null` until final |
| `usage` | the streaming guide shows `usage` on **every** chunk; the reference says `null` except a final chunk with `include_usage` — inconsistent, fixture needed |

Responses events named in the docs: `response.reasoning_text.delta`,
`response.reasoning_summary_text.delta` (reasoning guide); the full OpenAI event set
(`response.created`, `response.output_item.added/done`, `response.output_text.delta`,
`response.completed`, …) is implied by SDK compatibility but **not enumerated** on
the reference page. Citations stream as annotations (`url_citation`); the xAI SDK
exposes `chunk.inline_citations` (`id`, `start_index`, `end_index`,
`web_citation{url}` | `x_citation{url}`). `include: ["verbose_streaming"]` (xAI
SDK) surfaces server-side tool calls as they happen.

## 7. Reasoning / thinking

- `reasoning_effort` / `reasoning.effort`: `low|medium|high` (default `high`) on
  grok-4.5+, `xhigh` on grok-4.6+ (treated as `high` on 4.5). **Reasoning cannot be
  disabled** on grok-4.5/4.6/4.7; grok-4.20 ships explicit `-reasoning` /
  `-non-reasoning` variants; `grok-4.20-multi-agent` reuses the enum to pick 4 or
  16 agents (a semantic overload). Some models (reported for grok-4.3) error when
  `reasoning_effort` is set — **unverified**.
- Chat completions: `message.reasoning_content` (raw trace; the deferred-completion
  guide calls it "the raw thinking trace"), but the migration page says Chat
  Completions returns "No reasoning content" — contradictory; assume model-dependent.
- Responses: `reasoning` item with `summary[]` (grok-4.7 exposes summarised
  reasoning) and **`encrypted_content`**; request with `include:
  ["reasoning.encrypted_content"]`; **grok-4.7 always returns it** regardless of
  `include`. Pass reasoning items back unchanged in `input` to preserve reasoning
  across turns (independent of `store`). Chat completions "has no field for the
  ciphertext".
- Usage: `completion_tokens_details.reasoning_tokens` (chat) /
  `output_tokens_details.reasoning_tokens` (Responses); reasoning is billed and not
  counted against `max_completion_tokens`.
- Incompatible with reasoning models: `presence_penalty`, `frequency_penalty`, `stop`.

## 8. Prompt / context caching

Automatic prefix caching over the leading `messages`; "cached tokens are billed at a
reduced rate" ($0.50 vs $2.00 on grok-4.7); eviction under memory pressure; use
`prompt_cache_key` / header `x-grok-conv-id` for sticky routing. Usage:
`prompt_tokens_details.cached_tokens` (chat) / `input_tokens_details.cached_tokens`
(Responses). Responses also "automatically caches conversation history" when using
`previous_response_id`. Minimum size, TTL: not stated (**unverified**).

## 9. Multimodal

- Image in: Responses `{"type":"input_image","image_url": https-or-data-URI,
  "detail":"high"}` (other `detail` values **unverified**); chat completions "image
  and text" parts (shape unverified). jpg/jpeg/png, ≤ 20 MiB, no count limit, any
  order with text. Vision-capable model list not published (examples use grok-4.7).
- Image out: `POST /v1/images/generations` with `model: grok-imagine-image-2.0`,
  `prompt`, `n` (1–10), `response_format: url|b64_json`, `aspect_ratio` (16 values
  + `auto`), `resolution: 1k|2k`, `quality: low|medium|auto`, `deferred`; response
  `data[]{url | b64_json}`; $0.02 (`grok-imagine-image`) / $0.04
  (`grok-imagine-image-2.0`) per image. Also the `image_generation` server tool.
- Video out (`grok-imagine-video*`), voice (`grok-voice-3.0`) — separate surfaces.
- No audio or document parts on chat; `output_files[]` exists for code-execution
  outputs.

## 10. Models (snapshot 2026-11-10; $/1M in – cached – out, <200k prompt)

| Model | Context | Price | Notes |
|---|---|---|---|
| `grok-4.7` | 500k | 2.00 – 0.50 – 6.00 (2× at ≥ 200k) | reasoning always on; `xhigh`; encrypted reasoning always returned; cutoff May 2026 |
| `grok-4.6` | 500k | same | `xhigh` |
| `grok-4.5` | 500k | 2.00 – 0.30 – 6.00 | `xhigh` → `high` |
| `grok-4.3` | 1M | 1.25 – 0.20 – 2.50 | |
| `grok-4.20-0309-reasoning` / `-non-reasoning` / `grok-4.20-multi-agent-0309` | 1M | 1.25 – 0.20 – 2.50 | no logprobs |
| `grok-build-0.1` | 256k | 1.00 – 0.20 – 2.00 | |
| `grok-imagine-image(-2.0)`, `grok-imagine-video(-1.5/-lite)`, `grok-voice-3.0` | — | per image / second / minute | media |

Aliases: `<name>` = latest stable, `<name>-latest`, `<name>-<date>`. Older
grok-3/grok-4 ids are absent from the current models page (**unverified** status).
"Grok 4.7 Fast" exists only inside Cursor/Grok Build. Priority tier = 2× tokens.

## 11. Auth, limits, errors

- Rate limits: per-model RPS (= RPM/48, min 2) and TPM (prompt + completion +
  reasoning + cached); tiers by cumulative spend since 2026-01-01 (Tier 0 $0 → Tier 4
  $5,000, Enterprise); **429** on any limit; no rate-limit headers documented.
- Usage object (chat): `prompt_tokens`, `completion_tokens`, `total_tokens`,
  `prompt_tokens_details{text_tokens, audio_tokens, image_tokens, cached_tokens}`,
  `completion_tokens_details{reasoning_tokens, audio_tokens, accepted_prediction_tokens,
  rejected_prediction_tokens}`, **`cost_in_usd_ticks`** (10^10 ticks per dollar),
  `num_sources_used`, `server_side_tool_usage_details`. Responses adds
  `cost_in_nano_usd` and `context_details`.
- Error body shape: not documented (**unverified**). Status codes documented: 400,
  401 (missing/invalid bearer), 403, 404, 405, 415, 422 (invalid field format), 429;
  5xx not enumerated. Context-length, moderation and insufficient-credit codes:
  **not documented**.

## 12. Distinctive features

- Chat Completions explicitly **legacy**; Responses is the primary surface with
  30-day server-side storage, `previous_response_id`, `/responses/compact`.
- **Encrypted reasoning** (`reasoning.encrypted_content`) as the replay token,
  always present on grok-4.7.
- Server-side **X search** with per-post / per-profile billing, surfaced as
  `custom_tool_call` sub-tools; `web_search` with image understanding/search flags.
- `cost_in_usd_ticks` / `cost_in_nano_usd` — provider-reported cost in usage.
- `guidelines` parameter; `service_tier: fast|priority` (2× billing).
- Deferred completions with single-read 24 h retention.
- `search_parameters` (Live Search) still documented on both endpoints while third
  parties report its removal — status **unverified**; new code should use the
  `web_search`/`x_search` tools.
- Function calls arrive whole in one streaming chunk.

## 13. Mapping to `ocai`

**(a) Interface decision.** Two hosts, no new interface subpackage. Chat completions
→ `ocai.openai.chat_completions` with a `DialectTraits` variant (`vendor="xai"`);
census: `reasoning_content` on message/delta, `refusal`, top-level `citations[]`,
`output_files[]`, `finish_reason: end_turn`, `search_parameters`/`web_search_options`,
`guidelines`, `deferred`, `service_tier: fast`, usage extras (`cost_in_usd_ticks`,
`num_sources_used`, `server_side_tool_usage_details`, `text_tokens`/`image_tokens`),
`stop`/penalties rejected on reasoning models, whole-chunk tool calls, usage on
every chunk. Responses → the future `ocai.openai.responses` codec as a host;
census there: `encrypted_content` always present, `x_search` as `custom_tool_call`,
`file_search` citations as `collections://` strings, `max_turns`, `top_k`/`min_p`,
`guidelines`, `cost_in_nano_usd`, `background`/`metadata`/`truncation` unsupported.

**(b) Parts.** `PartText` with `annotations` from `url_citation`
(`start_index`/`end_index` validate against `output_text`) and `PartImage` (in);
`PartReasoning(summary, opaque=ProviderRef(encrypted_content))` on Responses,
`PartReasoning(text)` on chat; `PartToolCall`/`PartToolResult`;
`PartServerToolCall/Result` for `web_search`, `x_search` (`kind="x_search"`, payload
= the `custom_tool_call` item), `code_interpreter`, `file_search`, `mcp`,
`image_generation` (result base64 → nested `PartImage`); `PartRefusal` from
`message.refusal`; top-level chat `citations[]` (bare URLs, no spans) → censused
extension `xai.citations`, never fabricated into annotations; `output_files` →
`PartOpaque`.

**(c) Reasoning.** `ReasoningConfig.effort` → `reasoning_effort`/`reasoning.effort`
(first-class; `xhigh` on 4.5 silently equals `high` → declared **SemanticShift**;
`include_thoughts=false` is UNSUPPORTED on 4.5+ and reported; the multi-agent
overload is a SemanticShift to census); `budget_tokens` → UNSUPPORTED. The
`encrypted_content` blob is a `ProviderRef` anchored to `("xai","responses")`;
replay to `("xai","chat_completions")` or any other provider is an
UNSUPPORTED-and-reported crossing (chat "has no field for the ciphertext").
`summary` is first-class summary text.

**(d) Streaming.** Chat: fold is achievable but the delta model degenerates for tools
(one chunk = whole `PartToolCall`, `DeltaToolArgs` carries the full string) and the
usage-per-chunk vs final-chunk inconsistency needs a recorded pair; `end_turn` →
`FinishInfo(reason="complete", native="end_turn")`. Responses: standard item/delta
events plus `response.reasoning_summary_text.delta` → `DeltaReasoning`; annotations
stream late (DeltaAnnotation). `[DONE]` terminator on Responses is non-standard.

**(e) Errors.** 429 → `RateLimitError`; 401/403 → `AuthError`; 400/422 → generic
invalid-request unless a context-length signal is recorded (none documented →
`ContextLengthError` mapping is **unverified**); moderation → `refusal` field is a
response-level `PartRefusal`, pre-generation filter code unknown
(`ContentFilterError` reserved); 5xx → `TransientError`.

**(f) Priority: P2.** Rationale: the valuable surface is Responses, which ocai's
`openai/responses` codec does not exist yet; adding xAI as a second host of that
codec (encrypted reasoning as the canonical opaque-replay case, X search as a
server-tool kind) is the right time — not before. The legacy chat dialect alone is
low value. Effort: ≈ 0.5 WU chat dialect variant, ≈ 1.5 WU as a Responses host
(census + fixtures + fold triples incl. annotations), after the `/responses` WU.

## Sources (read 2026-11-10)

- https://docs.x.ai/developers/rest-api-reference/inference/chat-completions
- https://docs.x.ai/docs/api-reference (Responses reference)
- https://docs.x.ai/developers/rest-api-reference/inference/responses
- https://docs.x.ai/developers/model-capabilities/text/comparison
- https://docs.x.ai/developers/model-capabilities/legacy/chat-completions
- https://docs.x.ai/docs/guides/reasoning
- https://docs.x.ai/developers/model-capabilities/text/structured-outputs
- https://docs.x.ai/developers/model-capabilities/text/streaming
- https://docs.x.ai/developers/tools/function-calling
- https://docs.x.ai/developers/tools/web-search
- https://docs.x.ai/developers/tools/x-search
- https://docs.x.ai/developers/tools/code-execution
- https://docs.x.ai/developers/tools/collections-search
- https://docs.x.ai/developers/tools/remote-mcp
- https://docs.x.ai/developers/tools/image-generation
- https://docs.x.ai/developers/tools/citations
- https://docs.x.ai/developers/model-capabilities/images/understanding
- https://docs.x.ai/developers/model-capabilities/images/generation
- https://docs.x.ai/developers/advanced-api-usage/prompt-caching/how-it-works
- https://docs.x.ai/developers/advanced-api-usage/deferred-chat-completions
- https://docs.x.ai/developers/models
- https://docs.x.ai/developers/pricing
- https://docs.x.ai/developers/rate-limits
- https://docs.x.ai/developers/debugging
- https://docs.x.ai/developers/release-notes
