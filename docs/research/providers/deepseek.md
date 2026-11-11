# DeepSeek API — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

> Currency: researched 2026-11-10 against api-docs.deepseek.com. The catalogue is now
> the V4 generation (`deepseek-flash` = DeepSeek-V4.1-Flash-1017, `deepseek-v4-pro` =
> DeepSeek-V4-Pro-0813); the historical `deepseek-chat`/`deepseek-reasoner` ids no
> longer appear on the pricing page (their retirement date is reported by third
> parties only — **unverified**). Field names are stable.

Base: `https://api.deepseek.com` (OpenAI format; the docs show the base without
`/v1`), `https://api.deepseek.com/beta` (prefix completion, FIM, strict tools),
`https://api.deepseek.com/anthropic` (Anthropic format). Auth: `Authorization:
Bearer <key>`. The chat surface is **OpenAI-Chat-Completions-shaped** plus a
`thinking` object, `reasoning_content`, prefix completion, FIM, and automatic
disk-backed context caching with explicit hit/miss usage fields.

## 1. API surface / endpoints

| Surface | Endpoint |
|---|---|
| Chat completions | `POST /chat/completions` |
| Chat prefix completion (Beta) | same path on base `/beta`, last message `role: assistant` + `prefix: true` |
| FIM completion (Beta) | `POST /completions` on base `/beta` (`prompt`, `suffix`, `echo`; max 4K tokens; non-thinking only) |
| Strict tool schemas (Beta) | same path on base `/beta`, `function.strict: true` |
| OpenAI-Responses-compatible | `POST /responses` (stateless; §12) |
| Anthropic-Messages-compatible | `POST /anthropic/v1/messages` |
| Files | referenced via `file_id` parts (Files API; path **unverified**) |
| Models, balance | `GET /models`, `GET /user/balance` (listed in the reference sidebar; **unverified**) |

## 2. Request & response model

Messages: `system{content, name}`, `user{content: string | parts, name}`,
`assistant{content | null, name, prefix (Beta), reasoning_content (Beta, requires
prefix: true)}`, `tool{content: string | parts, tool_call_id}`. Content parts:
`text`, `image_url{url, detail}`, `file{file_id | file_data, filename}`.

Response: `chat.completion` with `id`, `created`, `model`, `system_fingerprint`,
`choices[]{index, finish_reason, logprobs, message{role, content, reasoning_content,
tool_calls[]{id, type: function, function{name, arguments}}}}` and
`usage{prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details.cached_tokens,
prompt_cache_hit_tokens, prompt_cache_miss_tokens, completion_tokens_details.reasoning_tokens}`.
`prompt_tokens == prompt_cache_hit_tokens + prompt_cache_miss_tokens`. `logprobs`
has both `content[]` and `reasoning_content[]` arrays.

## 3. Generation parameters

| Field | Type / range / default | Notes |
|---|---|---|
| `model` | `deepseek-flash`, `deepseek-v4-pro` | legacy `deepseek-v4-flash`, `deepseek-v4-flash-vision-exp` still accepted |
| `messages` | ≥ 1 | |
| `thinking` | `{type: enabled\|disabled}` or null | takes precedence over `reasoning_effort`; default follows effort |
| `reasoning_effort` | `none\|low\|high\|max`, default **`high`** | `none` disables; `minimal→low`, `medium→high`, `xhigh→high`, `ultra→max` |
| `max_tokens` | 1–393216 | default 8K non-thinking, 64K thinking, 128K at `max` effort |
| `response_format` | `{type: text\|json_object}` | no `json_schema` |
| `stop` | string or ≤ 16 strings | |
| `stream`, `stream_options.include_usage` | | `stream_options` without `stream` → 400 |
| `temperature` | 0–2, default 1 | **no effect in thinking mode** |
| `top_p` | (0, 1], default 1 | flash: effective only in thinking mode, clamped to ≥ 0.95; pro: ignored in thinking mode |
| `tools`, `tool_choice` | `none\|auto\|required\|{function}` | **`required` and named → 400 in thinking mode** |
| `logprobs`, `top_logprobs` (0–20) | | |
| `user_id` | ≤ 512 bytes ASCII | per-user rate isolation |
| `frequency_penalty`, `presence_penalty` | **deprecated, ignored** | accepted silently |
| `n`, `seed`, `parallel_tool_calls`, `max_completion_tokens` | — | not in the reference (unverified; Responses docs say `parallel_tool_calls` is silently ignored) |

## 4. Structured outputs

`response_format: {"type": "json_object"}` only; the word "json" must appear in the
system or user prompt, and an example is recommended. Failure mode: if the output is
not recognised as JSON the API **replaces it with spaces (U+0020)** and still returns
`finish_reason: "stop"` — callers must treat whitespace-only content as a retry.
Strict JSON Schema is available only on **tool** schemas (Beta `strict: true`).

## 5. Tool / function calling

- Definition: OpenAI nested; `name` ≤ 128 chars; `strict` (Beta, base `/beta`):
  every property must be in `required`, `additionalProperties: false`; supported
  types `object|string|number|integer|boolean|array|enum|anyOf` plus `$ref`/`$def`;
  no `minLength`/`maxLength`/`minItems`/`maxItems`; numbers support bounds and
  `multipleOf`; strings support `pattern` and `format` (`email|hostname|ipv4|ipv6|uuid`).
  Invalid schemas are rejected server-side. Works in thinking and non-thinking mode.
- `tool_choice: "none"` disables calls even with `tools`; `required`/named are 400 in
  thinking mode.
- Multiple `tool_calls` per message; no documented `parallel_tool_calls` knob.
- **Thinking + tools replay rule**: with `tools` present, "the `reasoning_content` of
  all previous turns should be passed back ... and must be passed back in all
  subsequent requests, including turns without tool calls. If it is not, the API
  returns a **400**." Without `tools`, `reasoning_content` in input is ignored.
- Streaming: `delta.tool_calls[]` with required `index`; `id`/`type`/`function.name`
  in the first chunk per call, argument fragments afterwards; `arguments` "may be
  invalid" JSON and must be validated.
- Server-side tools: none on chat completions. Responses API accepts `web_search`
  on `deepseek-v4-pro` only (ignored on flash); `file_search`, `code_interpreter`,
  `computer_use`, `mcp` are ignored. Anthropic mode supports `web_search_20250305`
  (`server_tool_use` + `web_search_tool_result` blocks).
- Chat completions cannot insert tool-call messages mid-conversation (Responses and
  Anthropic modes can).

## 6. Streaming

SSE `data:` chunks of `chat.completion.chunk`, terminator `data: [DONE]`.

| Chunk field | Notes |
|---|---|
| `delta.role`, `delta.content`, `delta.reasoning_content` | reasoning first, then content |
| `delta.tool_calls[]` | `index` required; identity in first chunk |
| `choices[].finish_reason` | `stop\|length\|content_filter\|tool_calls\|insufficient_system_resource\|aborted` |
| `usage` | with `include_usage`, `null` on intermediate chunks; **the final content chunk carries the full usage** (not a separate empty-`choices` chunk) |
| keep-alive | under load: SSE comments `: keep-alive` (streaming) or empty lines (unary); connection closed if inference has not started after 10 minutes |

Responses mode streams typed events (`response.created`, `.output_item.added/done`,
`.content_part.added/done`, `.output_text.delta/done`, `.reasoning_text.delta/done`,
`.function_call_arguments.delta/done`, `.custom_tool_call_input.delta/done`,
`.web_search_call.*` on pro, `.completed|.incomplete|.failed`) with
`sequence_number` and **no `data: [DONE]`**. Anthropic mode streams the Anthropic
event set plus `ping` and does not end with `[DONE]`.

## 7. Reasoning / thinking

- Enabled by default (`reasoning_effort: high`). Toggle with
  `thinking: {"type": "enabled"|"disabled"}` (`extra_body` in the OpenAI SDK) or
  `reasoning_effort: "none"`. Anthropic mode: `thinking.type` (`adaptive` treated as
  enabled, `budget_tokens` ignored), `output_config.effort: low|high|max`.
  Responses mode: `reasoning.effort: none|low|high|max`.
- Output: `message.reasoning_content` / `delta.reasoning_content` (plain text);
  Anthropic mode returns `thinking` blocks **without a documented signature**;
  `redacted_thinking` unsupported; Responses mode streams
  `response.reasoning_text.delta` and does not generate summaries or
  `encrypted_content` (both unsupported as input).
- Replay: not needed without tools (ignored if sent); **mandatory with tools (400
  otherwise)**; in Anthropic mode "pass back the complete assistant `content`
  array, including thinking and tool-use blocks".
- Sampling in thinking mode: `temperature`/penalties no effect; `top_p` model-specific.
- Reasoning tokens: `completion_tokens_details.reasoning_tokens`; reasoning counts
  against `max_tokens` (default 64K in thinking mode).
- Tool use in thinking mode exists since DeepSeek-V3.2; `tool_choice` restrictions
  above.

## 8. Prompt / context caching ("context caching on disk")

Automatic for everyone, no opt-out. Each request writes a disk cache; a later request
sharing a **prefix** hits it. Hits require a full match to a persisted "cache prefix
unit" (created at the end of user input and model output, on detected common prefixes,
and at fixed token intervals). `A+B` then `A+B+C` hits; `A+C` misses first, then `A`
is persisted. Cache build takes seconds; unused entries are cleared "within a few
hours to a few days"; best-effort, no hit guarantee. Usage:
`usage.prompt_cache_hit_tokens`, `usage.prompt_cache_miss_tokens` (and
`prompt_tokens_details.cached_tokens` = hits). Pricing (per 1M, off-peak/peak):
flash hit $0.003/$0.006 vs miss $0.15/$0.30; pro hit $0.022/$0.044 vs miss
$0.66/$1.32. Anthropic mode: `cache_control` ignored, `cache_creation_input_tokens`
always 0, `cache_read_input_tokens` reported. Minimum cacheable size: not stated
(**unverified**).

## 9. Multimodal

- Images on `deepseek-flash` only (`deepseek-v4-pro` replaces them with
  "[Unsupported Image]" in Anthropic mode; chat behaviour **unverified**).
- Parts: `image_url{url: https | data-URL, detail: low|high|original|auto}` (`low`
  → 512×512; `auto` = `original`); `file{file_id | file_data, filename}`.
  Responses: `input_image{image_url | file_id, detail}`. Anthropic: `image.source`
  `base64|url|file` (file needs `anthropic-beta: files-api-2025-04-14`).
- Limits: JPEG/PNG/GIF/WebP; URL ≤ 8192 chars, 60 s download; body ≤ 48 MiB; single
  image ≤ 32 MiB (64 MiB via `file_id`); total ≤ 64 MiB (200 MiB with `file_id`);
  ≤ 600 images; ≤ 8192 px per side (4096 when ≥ 15 images); ≤ 1024 tokens per image.
- **Images only in `user` messages** (chat); `system`/`assistant` → 400. Responses
  mode also allows them in `developer` messages and tool outputs.
- No audio, no video, no first-party document parsing beyond `file` parts (behaviour
  of non-image files **unverified**), no image generation.

## 10. Models (snapshot 2026-11-10)

| Model | Version | Context / max out | Modes | Price $/1M (off-peak / peak) |
|---|---|---|---|---|
| `deepseek-flash` | DeepSeek-V4.1-Flash-1017 | 1M / 384K | thinking (default) + non-thinking; vision; JSON; tools; Responses; Anthropic; prefix; FIM (non-thinking) | hit 0.003/0.006, miss 0.15/0.30, out 0.6/1.2 |
| `deepseek-v4-pro` | DeepSeek-V4-Pro-0813 | 1M / 384K | same minus vision | hit 0.022/0.044, miss 0.66/1.32, out 1.98/3.96 |

Peak = 01:00–04:00 and 06:00–10:00 UTC Mon–Fri (ex. Chinese holidays).
Concurrency limits: flash 2500, pro 500 per account (expandable, free). The
`reasoning_model` guide still lists DeepSeek-R1-era names only in passing; V3/R1 ids
are gone from pricing.

## 11. Auth, limits, errors

- Rate limiting is **concurrency-based**, account-level, with optional per-`user_id`
  sub-limits; 429 when exceeded. No rate-limit headers documented.
- Error body shape: not documented (OpenAI-style `error` object observed in SDK
  usage — **unverified**).

| HTTP | Name | Meaning |
|---|---|---|
| 400 | Invalid Format | malformed body |
| 401 | Authentication Fails | bad key |
| 402 | Insufficient Balance | top up |
| 422 | Invalid Parameters | bad parameter values (incl. unsupported Anthropic `type: custom`) |
| 429 | Rate Limit Reached | concurrency / QPS |
| 500 | Server Error | retry |
| 503 | Server Overloaded | retry |

Context overflow: Responses docs say requests over the window return **400**; chat
completions: not stated (**unverified** code).

## 12. Distinctive features

- **Mandatory reasoning replay when tools are present, enforced with 400** — the
  strictest replay rule among OpenAI-shaped providers.
- **Chat prefix completion** (`prefix: true`, Beta) with optional `reasoning_content`
  prefix; **FIM** with `suffix` on `/completions`.
- **Disk context cache** with explicit `prompt_cache_hit_tokens` /
  `prompt_cache_miss_tokens` and 50× cheaper hits; off-peak pricing windows.
- `reasoning_effort` remap table (`minimal/medium/xhigh/ultra` collapse).
- JSON mode failure = whitespace content with `finish_reason: stop`.
- `finish_reason` values `insufficient_system_resource` and `aborted`.
- Three protocols: OpenAI chat, stateless Responses (`store` always false, no
  `previous_response_id`), Anthropic Messages (Claude model names remapped:
  `claude-opus*` → pro, `claude-sonnet*`/`claude-haiku*` → flash).

## 13. Mapping to `ocai`

**(a) Interface decision.** `ocai.openai.chat_completions` through a
`Host`/`DialectTraits` variant (`vendor="deepseek"`, base URL + a `/beta` host for
prefix/strict/FIM). Divergences to census: `thinking{type}`, `reasoning_effort`
(`none|low|high|max`, default `high`, remap table); `reasoning_content` on message,
delta and (Beta) assistant input; `prefix` on assistant messages; `usage.prompt_cache_hit_tokens`
/ `prompt_cache_miss_tokens`; `finish_reason` extras; `tool_choice` restrictions in
thinking mode; penalties ignored; `temperature` ignored in thinking mode; usage on
the final content chunk rather than a trailing chunk; `file` content part;
`user_id`; no `json_schema`. FIM is a different shape (`completion`), not chat —
out of the chat port. The Anthropic and Responses modes ride `anthropic/messages`
and the future `openai/responses` codecs as hosts.

**(b) Parts.** `PartText`, `PartImage` (url/base64/`SourceRef(file_id)`),
`PartDocument` (`file` part; semantics unverified → census as provisional),
`PartReasoning` (text only), `PartToolCall`, `PartToolResult`. Responses-mode
`web_search_call` and Anthropic `server_tool_use`/`web_search_tool_result` →
`PartServerToolCall/Result(kind="web_search")`. Prefix-completion assistant tail →
the existing prefill convention (last `model`-role message) with `prefix: true`
emitted by the codec; a `PartOpaque` is not needed.

**(c) Reasoning.** `ReasoningConfig.include_thoughts` → `thinking.type`
(first-class); `effort` → `reasoning_effort` (first-class; the collapse of
`medium→high`, `xhigh→high`, `minimal→low` is a declared **SemanticShift**, reported
APPROXIMATED); `budget_tokens` → UNSUPPORTED (ignored in Anthropic mode too).
Replay: plain text, no signature — but because omission with tools is a hard 400,
the codec must re-emit every `PartReasoning.text` of prior `model` turns whenever
`tools` is set; a history converted *from* a provider that returned no reasoning
(or summaries only) cannot satisfy this and must surface as UNSUPPORTED/reported
rather than fail at the wire. Anthropic-mode `thinking` blocks carry no signature,
so no `ProviderRef` crossing arises.

**(d) Streaming.** `fold(stream) == complete` achievable: reasoning precedes
content; tool args by `index`. Gaps: usage rides the last *content* chunk (fold must
accept usage on a chunk that also carries `finish_reason`); keep-alive comments /
blank lines must be tolerated by the SSE parser; `insufficient_system_resource` →
`FinishInfo(reason="error")` with native preserved; `content_filter` finish is a
mid-generation refusal (response), not an exception.

**(e) Errors.** 429 → `RateLimitError`; 401, 402 → `AuthError` (402 = billing);
400/422 with context-overflow message → `ContextLengthError` (message-sniffed;
code unverified); `finish_reason: content_filter` → response-level; a pre-generation
block code is not documented (**unverified**) → `ContentFilterError` reserved;
500/503 → `TransientError`.

**(f) Priority: P0** (next after Gemini). Rationale: cheapest fixtures to record,
the dominant OpenAI-shaped reasoning dialect, and the one hard rule — reasoning
replay enforced by 400 — is exactly the honesty case `PartReasoning` replay rules
exist for; landing it first gives the other `reasoning_content` dialects (Qwen,
Kimi, GLM) a shared trait set. Effort: ≈ 1 WU for the dialect variant + census +
unary fixtures (half of WU-13), ≈ 1 WU for streaming fold triples incl. the
usage-on-final-chunk shape (WU-14b analogue), ≈ 0.5 WU for prefix/strict on the
`/beta` host.

## Sources (read 2026-11-10)

- https://api-docs.deepseek.com/api/create-chat-completion
- https://api-docs.deepseek.com/api/create-completion.md
- https://api-docs.deepseek.com/guides/thinking_mode.md
- https://api-docs.deepseek.com/guides/reasoning_model
- https://api-docs.deepseek.com/guides/tool_calls
- https://api-docs.deepseek.com/guides/json_mode.md
- https://api-docs.deepseek.com/guides/chat_prefix_completion
- https://api-docs.deepseek.com/guides/fim_completion
- https://api-docs.deepseek.com/guides/kv_cache
- https://api-docs.deepseek.com/guides/vision.md
- https://api-docs.deepseek.com/guides/responses_api.md
- https://api-docs.deepseek.com/guides/anthropic_api.md
- https://api-docs.deepseek.com/quick_start/pricing
- https://api-docs.deepseek.com/quick_start/error_codes
- https://api-docs.deepseek.com/quick_start/rate_limit.md

## 14. WU-44a descriptor verification (2026-11-11)

The [first-call guide](https://api-docs.deepseek.com/) confirms the OpenAI-format
base `https://api.deepseek.com`, bearer authorization, and the preferred model
names `deepseek-flash` and `deepseek-v4-pro`. Its legacy Flash aliases route to
the current Flash implementation; this does not establish a retirement date
for the historical `deepseek-chat` or `deepseek-reasoner` ids.
The [model table](https://api-docs.deepseek.com/quick_start/pricing/) identifies
Flash-1017 and Pro-0813 behind those names. These are model facts, not API tags.
The [API reference](https://api-docs.deepseek.com/api/create-chat-completion/)
confirms `POST /chat/completions` and text/JSON-object response formats.

The descriptor's `2026-11` tag and ordering date `2026-11-11` identify ocai's
observation snapshot, not a vendor version header or model release date.
Registration carries DeepSeek provenance and no executable edge or codec factory;
sharing OpenAI wire DTOs does not inherit OpenAI conversion qualification.
Only the documented lack of JSON-schema response output is declared in the
initial model profiles. Other coverage remains unknown until WU-44b fixtures.

## 15. WU-44b conversion verification (2026-11-11)

[Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/) confirms
that thinking defaults on, effort aliases have provider-defined effects, and
sampling controls can be ignored or bounded differently by model and mode.
Values must pass unchanged with visible findings. With tools present, prior
reasoning accompanies history; without tools the provider ignores that lane.
The [thinking tool guide](https://api-docs.deepseek.com/guides/thinking_mode/#tool-calls) requires retaining
prior reasoning across subsequent requests, including turns without tool calls.
Missing required history is unsupported, never reconstructed from final text.

[JSON output](https://api-docs.deepseek.com/guides/json_mode/) can return spaces
with a stop finish when JSON validation fails. Conversion preserves those bytes;
it never fabricates a JSON value or upgrades the finish semantics.
[Errors](https://api-docs.deepseek.com/quick_start/error_codes/) verifies HTTP
400/401/402/422/429/500/503 meanings, but does not document stable native error
code strings. Those strings are not invented for fixtures. Payment taxonomy
qualification remains WU-59.

The [reference](https://api-docs.deepseek.com/api/create-chat-completion/)
identifies hit/miss prompt buckets and reasoning as part of output tokens.
Missing or inconsistent measurements retain evidence rather than inferred zero.
Model-dependent top_p is conservatively unsupported in the model-independent
conversion edge (G-10); no request body gains routing metadata to work around it.


## 16. Streaming preflight verification (WU-46, 2026-11-11)

Rechecked the official [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
and [error-code reference](https://api-docs.deepseek.com/quick_start/error_codes/).
The streaming contract supplies `id`, `model`, `created`, reasoning/content/tool
fragments, finish state, and usage. Usage on the final content chunk must be
processed alongside its finish; that final choice carries no new content. Do not
assume a separate empty-choices usage event. The HTTP error reference still does not specify a
stable SSE error-envelope schema: unknown error payloads must remain evidence,
without asserting an undocumented provider-specific error-code mapping.

WU-46a resolves G-11 with a reusable response-info carrier under ADR 0015.
DeepSeek streaming qualification uses that carrier and must compare full
canonical responses; existing unary expectations retain their response identity.

WU-46 qualifies `system_fingerprint` as a censused response-info extension on both
unary and streaming paths; it is provider metadata, not a new first-class canonical
field. Recorded text/tools/parallel-tools and unknown-finish streams include full
identity and paired unary values. Future stream fields retain event-level evidence
and findings; G-12 tracks folding such unknown response-envelope extensions.
