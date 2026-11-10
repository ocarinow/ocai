# Z.ai / Zhipu BigModel (GLM) — Capabilities & Features

> Currency: researched 2026-11-10 against docs.z.ai (international) and
> docs.bigmodel.cn (China). The international reference OpenAPI page is the primary
> source; model IDs and pricing drift. Anything the docs did not state is marked
> **unverified**.

Z.ai (international) and Zhipu BigModel (China) run the same GLM API on two base URLs.
The chat surface is **OpenAI-Chat-Completions-shaped** with a GLM-specific long tail:
a `thinking` object, `reasoning_effort` defaulting to `max`, `do_sample`, server-side
`web_search`/`retrieval` tool types, a top-level `web_search` result array, and numeric
business error codes.

## 1. API surface / endpoints

| Surface | Endpoint |
|---|---|
| Chat completions (international) | `POST https://api.z.ai/api/paas/v4/chat/completions` |
| Chat completions (China) | `POST https://open.bigmodel.cn/api/paas/v4/chat/completions` |
| GLM Coding Plan (subscription keys) | `https://api.z.ai/api/coding/paas/v4` (OpenAI Chat) — "meant only for supported tools" |
| OpenAI-Responses-compatible | `https://api.z.ai/api/v1` (listed on the GLM-5.3 page; parameters **unverified**) |
| Anthropic-Messages-compatible | `https://api.z.ai/api/anthropic` (listed on the GLM-5.3 page; parameters **unverified**) |
| Standalone web search | `POST https://api.z.ai/api/paas/v4/web_search` (`search_engine`, `search_query`, `count`, `search_domain_filter`, `search_recency_filter`) |
| Layout parsing (GLM-OCR), file upload, agents, image/video/audio | separate APIs, out of chat scope |

Auth: `Authorization: Bearer <key>`; optional `Accept-Language: en-US,en`. Same API
key works for international; China keys are issued separately (which keys work on
which host: **unverified**).

## 2. Request & response model

Request: `model`, `messages[]` with roles `user|system|assistant|tool`. Assistant
messages carry `content` and optional `tool_calls[]` (`id`, `type:
"function"|"web_search"|"retrieval"`, `function.{name, arguments}` — arguments is a
JSON **string** on input but typed `object` in the response schema, a documented
inconsistency). Tool messages: `content` + required `tool_call_id`. Vision models take
`content` as parts: `text`, `image_url`, `video_url`, `file`.

Response: `id`, `request_id`, `created`, `model`, `choices[]{index, message{role,
content (null "when a function is hit"), tool_calls[]}, finish_reason}`,
`usage{prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details.cached_tokens}`,
and a top-level **`web_search[]`** (`title`, `content`, `link`, `media`, `icon`,
`refer`, `publish_date`) when the web-search tool fired. `message.reasoning_content`
is **not in the response schema** but is documented in the thinking guide and shown
in examples — a schema gap.

## 3. Generation parameters

| Field | Type / range / default | Notes |
|---|---|---|
| `model` | enum (§10) | default `glm-5.3` on the reference |
| `messages` | ≥ 1 | |
| `do_sample` | bool, default `true` | `false` makes `temperature`/`top_p` no-ops — non-OpenAI |
| `stream` | bool, default `false` | SSE ending with `data: [DONE]` |
| `thinking` | `{type: "enabled"\|"disabled", clear_thinking: bool}` | default `enabled`; §7 |
| `reasoning_effort` | `max\|xhigh\|high\|medium\|low\|minimal\|none`, default **`max`** | vision models: `max\|high\|low`; GLM-5.3: `low\|high\|max` |
| `temperature` | 0–1, default 1 | **not 0–2** |
| `top_p` | 0.01–1, default 0.95 | |
| `max_tokens` | 1–131072 | |
| `tool_stream` | bool, default `false` (`true` default on GLM-5.3) | streams tool-call arguments |
| `tools` | ≤ 128 | `function`, `retrieval`, `web_search` (`mcp` on China docs) |
| `tool_choice` | `"auto"` only | **`none`/`required`/named unsupported** |
| `stop` | string[] ≤ 4 | prose says only one stop word honoured |
| `response_format` | `{type: "text"\|"json_object"}` | text models only; no `json_schema` |
| `request_id` | 6–64 chars | client-supplied idempotency/trace id |
| `user_id` | 6–128 chars | |
| `stream_options`, `n`, `seed`, `logprobs`, `frequency_penalty`, `presence_penalty`, `parallel_tool_calls` | — | **not in the schema** (presumably ignored; unverified) |

## 4. Structured outputs

Only `response_format: {"type": "json_object"}`. The structured-output guide embeds the
JSON Schema in the system prompt and validates client-side with `jsonschema`. No
`json_schema` type, no strict mode, no documented tool-schema strictness. Interaction
with thinking/streaming is not documented.

## 5. Tool / function calling

- Function tools: `{"type":"function","function":{name (^[a-zA-Z0-9_-]+$, ≤64),
  description, parameters}}`; results via `role: "tool"` + `tool_call_id`.
- `tool_choice` is `"auto"` only; parallel calls are returned as multiple
  `tool_calls` (no `parallel_tool_calls` knob).
- `tool_stream: true` (with `stream: true`) streams `delta.tool_calls[]` with
  `index`, `function.name`, `function.arguments` fragments appended per index; the
  guide's example shows no `id` on deltas (**unverified** whether `id` is present).
  Without it, tool calls arrive whole.
- **Server-side `web_search` tool** declared in `tools`:
  `{"type":"web_search","web_search":{enable, search_engine (required; enum
  `search_pro_jina` on the reference, `search-prime` in the guide), search_query,
  count (1–50, default 10), search_domain_filter, search_recency_filter
  (`oneDay|oneWeek|oneMonth|oneYear|noLimit`), content_size (`medium|high`),
  result_sequence (`before|after`), search_result, require_search, search_prompt}}`.
  Results arrive in the top-level `web_search[]`; the model cites inline as
  `[Source: ref_1]` matching each result's `refer`. Billed $0.01 per use.
- **`retrieval` tool**: `{"type":"retrieval","retrieval":{knowledge_id,
  prompt_template with {{knowledge}}/{{question}}}}` — platform knowledge base RAG.
- `mcp` tool type appears only on the China reference (**unverified** shape).

## 6. Streaming

SSE `data:` lines; each chunk `{id, created, model, choices[0]{index, delta{content |
reasoning_content | tool_calls}, finish_reason}}`; `finish_reason` and `usage`
**appear only in the last chunk, with no `stream_options` opt-in**; terminator
`data: [DONE]`.

| Event / signal | Carries |
|---|---|
| chunk with `delta.reasoning_content` | thinking text (precedes content) |
| chunk with `delta.content` | answer text |
| chunk with `delta.tool_calls[]` | only with `tool_stream: true`; fragments by `index` |
| last chunk | `finish_reason` + `usage` |
| `data: [DONE]` | end |

**Mid-stream failures are not HTTP errors**: the error-code page states that for SSE
calls "these codes aren't returned; the reason appears in the response body's
`finish_reason` field" — values `sensitive`, `model_context_window_exceeded`,
`network_error` (alongside `stop`, `tool_calls`, `length`).

## 7. Reasoning / thinking

- Enable/disable: `thinking: {"type": "enabled"|"disabled"}`. **GLM-5.3 and
  GLM-5.3-Flash force thinking** ("Disabling reasoning is no longer supported";
  requests with `disabled` fail — migrate to `enabled` + `reasoning_effort: "low"`).
  GLM-5.2/5.1/5/4.7 default on and can be disabled; GLM-4.6 "default hybrid".
- Depth: `reasoning_effort`, default `max`.
- **Preserved thinking**: `thinking.clear_thinking: false` keeps prior-turn
  `reasoning_content` in context; the caller must pass it back "complete, unmodified
  and in the original order" or performance and cache hits degrade. Default: on for
  the Coding Plan endpoint, **off** for the standard endpoint.
- **Interleaved thinking** between tool calls is "supported by default"; the guide
  recommends returning `reasoning_content` with the assistant tool-call message
  (required only under preserved thinking).
- Output: `delta.reasoning_content` (stream) / `message.reasoning_content` (unary,
  not in schema). Plain text; no signature, no encrypted blob, no reasoning-token
  usage bucket documented (**unverified**).

## 8. Prompt / context caching

Automatic ("triggered based on content similarity, no manual configuration"); no
explicit markers, no TTL stated ("reasonable time limits"), no minimum stated. Hits
are reported in `usage.prompt_tokens_details.cached_tokens` and billed at the
"Cached Input" price (e.g. GLM-5.3 $0.26 vs $1.40 input). The docs never say
"prefix", so prefix semantics are **unverified**; preserved thinking is advertised as
raising hit rates.

## 9. Multimodal

Text models (`glm-5.x`, `glm-4.x`) are **text-only input**. Vision models
(`glm-5.3-flash`, `glm-5.3-flashx`, `glm-5.3-flashx-legal`; China also `glm-5v-turbo`,
`glm-4.6v*`, `glm-4.5v`) accept user-content parts:

| Part | Shape | Limits |
|---|---|---|
| `image_url` | `{"type":"image_url","image_url":{"url": URL or base64}}` | ≤ 5 MB, ≤ 6000×6000, jpg/png/jpeg; GLM-5V ≤ 150 images |
| `video_url` | `{"type":"video_url","video_url":{"url"}}` | ≤ 200 MB, mp4/mkv/mov |
| `file` | `{"type":"file","file":{file_id \| file_url \| file_data, filename?}}` | ≤ 50 MB; GLM-5.3-Flash series only for `file_id`/`file_url`; cannot mix with image/video in one request |

Vision requests have **no `response_format`, no `tool_stream`, no `tool` role** in
the schema. Output is text only; no audio in/out on chat (`glm-4-voice` is a separate
China model). No first-party image generation on this endpoint.

## 10. Models (snapshot 2026-11-10)

| Model | Context / max out | Thinking | $/1M in – cached – out |
|---|---|---|---|
| `glm-5.3` | 1M / 128K | forced; `low\|high\|max` | 1.40 – 0.26 – 4.40 |
| `glm-5.2` | 1M / 128K | toggleable | 1.40 – 0.26 – 4.40 |
| `glm-5.1`, `glm-5` | unverified | toggleable | 1.40/1.00 – 0.26/0.20 – 4.40/3.20 |
| `glm-4.7`, `glm-4.6` | unverified | toggleable / hybrid | 0.60 – 0.11 – 2.20 |
| `glm-5.3-flash` / `-flashx` | 1M / 128K; image+video+file in | forced | 0.15 – 0.03 – 0.50 / 0.37 – 0.075 – 1.25 |
| `glm-4.6v`, `glm-4.5v`, `glm-4.6v-flash(x)` | unverified | — | 0.30/0.60 – … – 0.90/1.80 (4.6v-flash free) |
| China-only ids | `glm-5-turbo`, `glm-4.7-flash(x)`, `glm-4.5-air(x)`, `glm-4.5-flash`, `glm-5v-turbo`, `glm-4.1v-thinking-*`, `glm-4-voice` | — | — |

Coding Plan models are billed in points (off-peak 50%). Lineage note: the international
docs no longer carry GLM-4.x model pages; the China reference still enumerates them.

## 11. Auth, limits, errors

- Rate limits: the docs page redirects to a console page (no public figures) —
  **unverified**; dimensions presumably concurrency/RPM/TPM.
- Error body: `{"error": {"code": "<numeric string>", "message"}}`; HTTP status is
  the outer code.

| HTTP | code | Meaning |
|---|---|---|
| 401 | 1000, 1001, 1003, 1005 | auth failed / header missing / token expired / 2FA |
| 403 | 1220 | no permission for the API |
| 400 | 1210–1215, 1221, 1222 | invalid param, unknown model, unsupported call method, missing/invalid param, conflicting params, API offline/nonexistent |
| 400 | **1261** | prompt too long (context length) |
| 400 | **1301** | input or output flagged unsafe/sensitive |
| 429 | **1302** | request rate limit |
| 429 | 1305 | service overloaded, retry |
| 429 | 1113 | insufficient balance / no package |
| 429 | 1308, 1310, 1313, 1316–1321 | time-window / weekly / fair-use / 5-hour / 7-day quotas |
| 429 | 1309, 1311, 1314, 1315 | plan expired / model not in plan / enterprise package |
| 500 | 1200, 1230, 1234 | API call / process / network error |

## 12. Distinctive features

- `reasoning_effort` **defaults to `max`** and GLM-5.3 cannot stop thinking.
- `do_sample` master switch for sampling.
- `tool_choice` is `auto`-only; server-side `web_search` and `retrieval` are
  **tool types next to `function`**, with results in a top-level `web_search[]` and
  `[Source: ref_n]` inline markers.
- `tool_stream` opt-in for streamed arguments (default off before GLM-5.3).
- Mid-stream errors are encoded in `finish_reason` (`sensitive`,
  `model_context_window_exceeded`, `network_error`).
- Numeric business error codes with quota semantics (5-hour / 7-day windows) under
  HTTP 429.
- Client-supplied `request_id` and `user_id`.

## 13. Mapping to `ocai`

**(a) Interface decision.** Serve through `ocai.openai.chat_completions` with a
`Host`/`DialectTraits` variant (`vendor="zai"`, two base URLs for international/China).
Divergences to census: `thinking{type, clear_thinking}` and `reasoning_effort`
(default `max`, enum includes `none`/`minimal`); `do_sample`; `tool_stream`;
`tool_choice` restricted to `auto`; tool types `web_search`/`retrieval` (+ `mcp`);
top-level `web_search[]` response field; `reasoning_content` on message/delta;
`temperature` 0–1 and `top_p` ≥ 0.01; `max_tokens` ≤ 131072; `stop` effectively one
item; `finish_reason` extra values; usage only in last chunk without opt-in; numeric
`error.code`; `request_id`/`user_id`; no `n`/`seed`/`logprobs`/penalties. No separate
interface subpackage is warranted.

**(b) Parts.** `PartText`, `PartImage`/`PartVideo`/`PartDocument` (vision models, via
`image_url`/`video_url`/`file` — `file_id` becomes a `SourceRef`), `PartReasoning`
(text only), `PartToolCall`, `PartToolResult`. `web_search[]` →
`PartServerToolCall/Result(kind="web_search")` with verbatim payload; the
`[Source: ref_n]` markers become `PartText.annotations` only when offsets validate.
`retrieval` results are not surfaced separately in the response (**unverified**) →
`PartOpaque` if they ever are.

**(c) Reasoning.** `ReasoningConfig.include_thoughts` → `thinking.type`
(first-class; **UNSUPPORTED-and-reported on GLM-5.3** where disabling fails);
`effort` → `reasoning_effort` (first-class; the `max` default and the extra
`minimal`/`none` levels are a declared **SemanticShift** when converting from
OpenAI's `low|medium|high`); `budget_tokens` → UNSUPPORTED (no budget knob).
`clear_thinking:false` + mandatory verbatim replay → censused extension
`zai.clear_thinking`; replayed reasoning is plain text, so no `ProviderRef` anchor.
Converting a GLM history with preserved reasoning to a provider that drops it is a
reported loss, not silent.

**(d) Streaming.** Achievable: incremental `reasoning_content` then `content`; tool
args by `index` only with `tool_stream` (the codec should set it to keep one delta
model). Gaps: `finish_reason`-encoded errors must become `ChatChunk.error` with
canonical code + native + retryable (`network_error` retryable, `sensitive` →
`content_filter`, `model_context_window_exceeded` → context length); usage only on the
last chunk; possibly no `id` on streamed tool-call deltas (fixture needed).

**(e) Errors.** 1302/1305 → `RateLimitError` (1305 retryable); 1113 and the quota
family 1308–1321 → `RateLimitError` vs `AuthError` is a judgement call — map balance /
plan codes (1113, 1309, 1311, 1314, 1315) to `AuthError`, window quotas to
`RateLimitError`; 1000–1005, 1220 → `AuthError`; **1261 → `ContextLengthError`**;
**1301 → `ContentFilterError`** (also `finish_reason: "sensitive"` mid-stream);
1200/1230/1234 and HTTP 5xx → `TransientError`.

**(f) Priority: P2.** Rationale: same `reasoning_content` dialect family as DeepSeek
(P0) and Qwen/Kimi (P1), cheap to add once that family's traits exist, but with
fewer novel semantics and an unverified rate-limit/`id`-on-delta story; the one new
mechanism (errors in `finish_reason`) is worth a fixture pair. Effort: ≈ 1 WU
(dialect variant + census + unary/stream fixtures, about half of WU-13 + WU-14b).

## Sources (read 2026-11-10)

- https://docs.z.ai/api-reference/llm/chat-completion.md
- https://docs.z.ai/api-reference/introduction.md
- https://docs.z.ai/guides/llm/glm-5.3.md
- https://docs.z.ai/guides/llm/glm-5.2.md
- https://docs.z.ai/guides/vlm/glm-5.3-flash.md
- https://docs.z.ai/guides/overview/migrate-to-glm-new.md
- https://docs.z.ai/guides/capabilities/thinking-mode.md
- https://docs.z.ai/guides/capabilities/function-calling.md
- https://docs.z.ai/guides/capabilities/stream-tool.md
- https://docs.z.ai/guides/capabilities/streaming.md
- https://docs.z.ai/guides/capabilities/cache.md
- https://docs.z.ai/guides/capabilities/struct-output.md
- https://docs.z.ai/guides/tools/web-search.md
- https://docs.z.ai/api-reference/api-code.md
- https://docs.z.ai/guides/overview/pricing.md
- https://docs.bigmodel.cn/api-reference/模型-api/对话补全.md (China chat completion reference)
- https://docs.bigmodel.cn/llms.txt
