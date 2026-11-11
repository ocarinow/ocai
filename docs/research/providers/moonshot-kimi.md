# Moonshot AI (Kimi) — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

> Currency: researched 2026-11-10 against platform.kimi.ai (the international
> Moonshot developer platform; `platform.kimi.com` and `platform.moonshot.ai` serve
> the same pages). The K2 generation is being retired in favour of K3/K3.1; model IDs
> and prices drift. Anything the docs did not state is marked **unverified**.

Base: `https://api.moonshot.ai/v1` (China: `https://api.moonshot.cn/v1`, mentioned
but not re-verified). Auth: `Authorization: Bearer <key>`. The chat surface is
**OpenAI-Chat-Completions-shaped**, with Kimi-specific additions: `partial` prefill,
`reasoning_content` with *preserved thinking*, implicit prompt caching with TTL
options, dynamic tool loading through `system` messages, and fixed (non-settable)
sampling parameters on K3.1.

## 1. API surface / endpoints

| Surface | Endpoint |
|---|---|
| Chat completions | `POST /v1/chat/completions` |
| OpenAI-Responses-compatible | `POST /v1/responses` (stateless; §12) |
| Anthropic-Messages-compatible | `POST https://api.moonshot.ai/anthropic/v1/messages` (K3 models only) |
| Files | `POST /v1/files` (`purpose`: `image`, `video`, file QA) + list/retrieve/delete/content |
| Web search (standalone) | `POST /v1/tools/search`, `POST /v1/tools/search_pro` |
| Official tools ("Formula") | `GET /formulas/{uri}/tools`, `POST /formulas/{uri}/fibers` (e.g. `moonshot/web-search:latest`) |
| Models | `GET /v1/models` (listed under models-overview; **unverified** path) |
| Batch | separate pricing page (60% of standard) |

Optional header `X-Msh-Request-Nonce` (UUID v4) makes the response carry
`Msh-Request-Timestamp` and `Msh-Request-Signature` (`reqsigv1_...`) for
non-repudiation.

## 2. Request & response model

`messages[]` with `role: system|user|assistant|tool`, `content` string or parts
(`text`, `image_url`, `video_url`), optional `name`, optional **`partial`** on the last
assistant message. Tool messages carry `tool_call_id` (and the guide also sets
`name`), though the OpenAPI `Message` schema omits `tool_call_id` — a schema gap.
A **dynamic tool message** `{"role":"system","tools":[...]}` with no `content`
declares tools mid-history on K3 models.

Response: standard `chat.completion` with `choices[].message.{role, content,
reasoning_content, tool_calls[]}`, `finish_reason: stop|length|tool_calls`,
`usage.{prompt_tokens, completion_tokens, total_tokens, cached_tokens,
prompt_tokens_details.{cached_tokens, cache_write_tokens}}` (the schema lists
`cached_tokens` top-level *and* under details — inconsistency). `prompt_tokens`
= cached + cache-written + uncached.

## 3. Generation parameters

| Field | Notes (exact names) |
|---|---|
| `model` | `kimi-k3.1-pro` (default), `kimi-k3.1-pro-highspeed`, `kimi-k3`, `kimi-k2.7-code(-highspeed)`, `kimi-k2.6` |
| `messages` | required |
| `max_completion_tokens` | K3: default **131072**, max **1048576**; `max_tokens` deprecated |
| `reasoning_effort` | K3 only: `low\|high\|max`, default **`max`** |
| `thinking` | K2.6: `{type: enabled\|disabled, keep: null\|"all"}`; K2.7-code: `type` must be `enabled`, `keep` `"all"`/omitted; **absent on K3** |
| `response_format` | `text` (default), `json_object`, `json_schema{name, schema, strict (default true)}` |
| `stop` | string or ≤ 5 strings, each ≤ 32 bytes |
| `stream`, `stream_options.include_usage` | final chunk `choices: []` + `usage` |
| `tools` | `{type: function, function{name ^[a-zA-Z_][a-zA-Z0-9-_]{0,127}$, description, parameters (MFJS), strict default true}}` |
| `tool_choice` | `auto\|none\|required\|{type: function, function{name}}` |
| `logprobs`, `top_logprobs` (0–20) | |
| `prediction` | `{type: "content", content}` (predicted outputs) |
| `prompt_cache_key` | string; sticky routing hint (**unverified** semantics beyond the schema) |
| `prompt_cache_options` | `{mode: "implicit", ttl: "5m"\|"1h"}` |
| `safety_identifier` | stable hashed end-user id |
| `temperature`, `top_p`, `n`, `presence_penalty`, `frequency_penalty` | **not in the schema**; K3.1 Pro quickstart: "`temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0`, `frequency_penalty=0` are fixed; omit them" |

## 4. Structured outputs

- `{"type":"json_object"}` — valid JSON, unconstrained.
- `{"type":"json_schema","json_schema":{"name","strict":true,"schema"}}` — the schema
  must satisfy "MFJS" (Moonshot's JSON-Schema subset; nullable type arrays,
  `additionalProperties: false`, `anyOf`/`oneOf`/`$ref` on K2.7-code). A non-object
  `schema` → 400 `invalid_request_error`; invalid-but-accepted schemas often return
  200 with no warning.
- Thinking models still emit `reasoning_content`; parse only `message.content`.
- Do not mix `json_object` with `partial`; `json_schema` + `partial` works on simple
  schemas only.
- Tool schemas: `function.strict` defaults to **true**.

## 5. Tool / function calling

- Standard OpenAI nested definition; parallel calls in one turn; every `tool_calls[i]`
  needs exactly one `role: "tool"` reply (mismatch → error).
- `tool_choice`: `auto` (default), `none`, `required`, named function. **Named
  function + thinking → 400** `tool_choice 'specified' is incompatible with thinking
  enabled`.
- Streaming: first chunk per `index` carries `id` and `function.name`; later chunks
  carry `arguments` fragments; `delta.tool_calls` may follow `delta.content`.
- **Preserved thinking in tool loops**: on K3/K3.1 and K2.7-code, append the
  *complete* assistant message (`reasoning_content` + `content` + `tool_calls`)
  unchanged, then the tool messages; "keeping `reasoning_content` is required in
  multi-turn conversations and tool-call loops". What happens if omitted: not stated
  (**unverified**: no 400 documented, unlike DeepSeek).
- Dynamic tool loading: full tool definitions inside a `system` message's `tools`
  field, effective from that position; the server does not retain them.
- **Official tools** are ordinary `function` tools fetched from
  `/formulas/{uri}/tools`; the model returns e.g. `id: "web_search:0"`,
  `name: "web_search"`; the client executes it via `POST /formulas/{uri}/fibers` and
  returns `context.encrypted_output` or `context.output` in the tool message. Web
  search is billed per call and "not recommended for production near-term".
- Responses API: `tools` also accepts `web_search` (server-side, one per request),
  `custom` (only `apply_patch` with a Lark grammar) and `namespace`.

## 6. Streaming

`text/event-stream`, `data: <json>` chunks, `data: [DONE]` terminator.

| Chunk field | Notes |
|---|---|
| `delta.role` | first chunk |
| `delta.reasoning_content` | **always before** any `content`; first `content` chunk marks end of thinking |
| `delta.content` | answer |
| `delta.tool_calls[]` | `index`, `id`+`name` first, then `arguments` |
| `finish_reason` | `stop\|length\|tool_calls` on the last content chunk |
| `usage` | `null` except on the final `choices: []` chunk with `include_usage`; "may not arrive if the stream is interrupted" |

Anthropic-compatible stream: `message_start`, `content_block_start/delta/stop`
(`text_delta`, `thinking_delta`, `signature_delta`, `input_json_delta`),
`message_delta`, `message_stop`. Responses stream: `response.created`, `.in_progress`,
`.output_item.added/done`, `.content_part.added/done`, `.output_text.delta/done`,
`.reasoning_summary_part.added/done`, `.reasoning_summary_text.delta/done`,
`.function_call_arguments.delta/done`, `.custom_tool_call_input.delta/done`,
`.web_search_call.in_progress/searching/completed`, `.completed`, `.incomplete`,
`.failed`, `error`.

## 7. Reasoning / thinking

| Model | Thinking | Control |
|---|---|---|
| `kimi-k3.1-pro(-highspeed)`, `kimi-k3` | always on; preserved thinking always on | `reasoning_effort: low\|high\|max` (default `max`); no `thinking` param |
| `kimi-k2.7-code` | always on; preserved always on | `thinking.type` must be `enabled` |
| `kimi-k2.6` | on by default, can disable | `thinking: {type, keep: null\|"all"}` |

- `reasoning_content` sits beside `content`; billed as output;
  `reasoning_content + content ≤ max_tokens` (recommend ≥ 16000 with tools).
- Chat completions expose **plain text** reasoning, no signature. The
  **Anthropic-compatible endpoint returns `thinking` blocks with a `signature`** that
  must be passed back unchanged; the Responses endpoint returns `reasoning` items with
  `summary[]` and `encrypted_content: null`.
- Changing `reasoning_effort`/`output_config.effort` breaks prefix-cache hits.
- Reasoning token breakdown: Anthropic mode `output_tokens_details.thinking_tokens`;
  chat completions: no `reasoning_tokens` bucket documented (**unverified**).

## 8. Prompt / context caching

Implicit prefix caching only (`prompt_cache_options.mode` "currently supports only
`implicit`"); block-granular ("a portion smaller than one full block is not cached
and is billed at the cache-miss rate"); per-organization; cannot be cleared.
`ttl`: `5m` (default) or `1h`, locked at first write, reset on each hit.
Pricing (kimi-k3, per 1M): miss $3.00, write-5m $3.00, write-1h $6.00, hit $0.30.
Cache **writes are billed** on K3/K3.1 (not on K2.x). `prompt_cache_breakpoint`
inside content → **HTTP 400**. Usage: `prompt_tokens_details.cached_tokens` /
`cache_write_tokens`; headers `Msh-Usage-Cache-Write-Tokens-5m` / `-1h`. Anthropic
mode: top-level `cache_control` only (markers inside `messages` are ignored); usage
`cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_creation.ephemeral_5m/1h_input_tokens`
— and there `input_tokens` **excludes** cache reads/writes, unlike chat completions.

## 9. Multimodal

- Images: `{"type":"image_url","image_url":{"url":"data:image/...;base64,..."}}` or
  `ms://<file-id>` after `files.create(purpose="image")`. **Public image URLs are not
  supported.** MIME: jpeg/png/gif/webp/bmp/heic/heif (animated gif/webp may be billed
  as video); SVG rejected (send as text). Request body ≤ 100 MB; recommended ≤ 4K.
- Video: `{"type":"video_url","video_url":{"url":"ms://<file-id>"}}` after
  `purpose="video"`; mp4/mpeg/mov/avi/x-flv/mpg/webm/wmv/3gpp; recommended ≤ FHD.
- Models: K3.1 Pro, K3, K2.6, K2.7-code all "native visual understanding" + video.
- No audio in/out, no document part on chat (file QA goes through the Files API and
  system-message injection), no image generation.

## 10. Models (snapshot 2026-11-10)

| Model | Context | Notes |
|---|---|---|
| `kimi-k3.1-pro` | 1,048,576 | flagship; thinking always on; sampling fixed; vision + video |
| `kimi-k3.1-pro-highspeed` | 1M (unverified) | 2–3× faster variant |
| `kimi-k3` | 1,048,576 | previous flagship, 2.8T params; cache write supported |
| `kimi-k2.7-code(-highspeed)`, `kimi-k2.6` | unverified | not for new registrations; deprecation expected late Dec 2026 |
| Deprecated | `kimi-k2.5`, `kimi-k2-0711-preview`, `kimi-k2-0905-preview`, `kimi-k2-turbo-preview`, `kimi-k2-thinking(-turbo)`, `kimi-latest`, `kimi-thinking-preview`, `moonshot-v1-*` | |

Output price for K3: **unverified** (pricing tables rendered empty); input prices in §8.
Batch: 60% of standard.

## 11. Auth, limits, errors

- Rate-limit dimensions: concurrency, RPM, TPM, TPD (+ independent web-search QPS);
  tiers by cumulative recharge (values **unverified**). `X-RateLimit-Limit/-Remaining/-Reset`
  documented only for the search endpoints.
- Error body: `{"error": {"type", "message"}}` (schema also allows `code`; none listed).

| HTTP | `error.type` | Meaning |
|---|---|---|
| 400 | `content_filter` | input/output "considered high risk" |
| 400 | `invalid_request_error` | malformed; **"Input token length too long"** (context) |
| 401 | `invalid_authentication_error`, `incorrect_api_key_error` | auth |
| 403 | `permission_denied_error` | account/IP allowlist |
| 404 | `resource_not_found_error` | model |
| 429 | `rate_limit_reached_error` | concurrency / RPM / TPM / TPD |
| 429 | `exceeded_current_quota_error` | balance / token quota |
| 429 | `engine_overloaded_error` | capacity; honour `Retry-After` |
| 499 | `client_closed_request` | client disconnected |
| 500 | `server_error`, `unexpected_output` | retry |
| 503 | `server_unavailable` | retry |
| 504 | HTML gateway timeout (not JSON) | after 900 s without response; use streaming |

## 12. Distinctive features

- **Partial mode**: last `{"role":"assistant","content":"<prefix>","partial":true}`;
  the `name` field counts as part of the prefix (role-play); prefix **not echoed**.
- **Preserved thinking** as the default contract on K3: replay the whole assistant
  message, model "chooses which parts are necessary".
- **Dynamic tool loading** via `system` messages carrying `tools`.
- **Fixed sampling** on K3.1 (`temperature`/`top_p` not settable).
- Signed responses (`X-Msh-Request-Nonce`).
- **Paid cache writes** with 5m/1h TTL and header-level cache accounting.
- Three protocols (chat, Responses, Anthropic) on K3; the Anthropic one is the only
  place thinking carries a `signature` and `stop_reason: refusal`.
- Responses API is stateless (`previous_response_id` always `null`, `store` false).

## 13. Mapping to `ocai`

**(a) Interface decision.** `ocai.openai.chat_completions` through a
`Host`/`DialectTraits` variant (`vendor="moonshot"`). Divergences to census:
`partial` on assistant messages; `reasoning_content` on message/delta (and required
replay); `reasoning_effort` enum `low|high|max` with default `max`; `thinking{type,
keep}` on K2.x; `max_completion_tokens` huge default; `prompt_cache_options`,
`prompt_cache_key`, `safety_identifier`, `prediction`; `usage.cache_write_tokens`;
`system` messages carrying `tools`; `tool_choice` named + thinking → 400; sampling
params fixed (a request setting `temperature` is **APPROXIMATED-reported**, value
passed verbatim, provider ignores or rejects — fixture needed); `stop` byte limits;
image URLs rejected (only data URIs / `ms://` refs); `error.type` vocabulary. The
Anthropic-compatible surface can ride `ocai.anthropic.messages` as a host
(`cache_control` top-level only, `thinking` + `signature`). No new interface
subpackage needed.

**(b) Parts.** `PartText`, `PartImage` (base64 or `SourceRef("ms://...")`),
`PartVideo` (`SourceRef`), `PartReasoning` (text; `signature` only on the Anthropic
host), `PartToolCall`, `PartToolResult`. Responses-mode `web_search_call` →
`PartServerToolCall(kind="web_search")`; Formula tools are client-executed `function`
calls (no server-tool part). `prediction` → `provider_options`. Dynamic-tool system
messages → censused extension `moonshot.dynamic_tools` (they are not conversation
content).

**(c) Reasoning.** `ReasoningConfig.effort` → `reasoning_effort` (first-class;
`medium`→? **unverified**, declare `low|high|max` and report `medium` as
APPROXIMATED); `include_thoughts` → `thinking.type` on K2.6 only (UNSUPPORTED-reported
on K3/K2.7-code where thinking cannot be disabled); `budget_tokens` → UNSUPPORTED.
Replay: chat completions reasoning is plain text (no anchor), but the contract
"return the complete message" means a converted history that strips reasoning is a
reported loss. On the Anthropic host the `signature` is a `ProviderRef` anchored to
`("moonshot","messages")`; crossing to `("moonshot","chat_completions")` is
UNSUPPORTED-and-reported, not silently dropped.

**(d) Streaming.** Achievable; `reasoning_content` strictly precedes `content`;
tool args by `index`. Gaps: usage only in the terminal empty-`choices` chunk and may
be missing on interruption (seal `incomplete`); no `reasoning_tokens` bucket on chat
completions; 504 arrives as HTML (transport must map to `TransientError`).

**(e) Errors.** `rate_limit_reached_error`, `engine_overloaded_error` →
`RateLimitError` (overloaded retryable); `exceeded_current_quota_error`,
`invalid_authentication_error`, `incorrect_api_key_error`, `permission_denied_error`
→ `AuthError`; `invalid_request_error` + "Input token length too long" →
`ContextLengthError` (message-sniffed); `content_filter` → `ContentFilterError`;
`server_error`, `unexpected_output`, `server_unavailable`, 504, 499 →
`TransientError`.

**(f) Priority: P1.** Rationale: same dialect family as DeepSeek (P0) with two
semantics ocai must prove anyway — mandatory reasoning replay without an anchor, and
a provider that *rejects* standard sampling knobs — plus a second Anthropic-shaped
host to exercise `DialectTraits` on `anthropic/messages`. Effort: ≈ 1 WU for the
chat dialect (half of WU-13 + fixtures), ≈ 1 WU for streaming fold triples (WU-14b
analogue), ≈ 0.5 WU for the Anthropic host variant.

## Sources (read 2026-11-10)

- https://platform.kimi.ai/docs/api/chat.md
- https://platform.kimi.ai/docs/api/partial.md
- https://platform.kimi.ai/docs/api/responses.md
- https://platform.kimi.ai/docs/api/messages.md
- https://platform.kimi.ai/docs/api/errors.md
- https://platform.kimi.ai/docs/api/tools-search.md
- https://platform.kimi.ai/docs/guide/context-caching.md
- https://platform.kimi.ai/docs/guide/use-thinking-models.md
- https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls.md
- https://platform.kimi.ai/docs/guide/use-tool-choice.md
- https://platform.kimi.ai/docs/guide/use-official-tools.md
- https://platform.kimi.ai/docs/guide/response_format.md
- https://platform.kimi.ai/docs/guide/use-kimi-vision-model.md
- https://platform.kimi.ai/docs/guide/kimi-k3-1-pro-quickstart.md
- https://platform.kimi.ai/docs/models.md
- https://platform.kimi.ai/docs/pricing/chat.md
- https://platform.kimi.ai/docs/pricing/limits.md
- https://platform.kimi.ai/docs/llms.txt
