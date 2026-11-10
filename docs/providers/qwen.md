# Alibaba Cloud Model Studio / DashScope (Qwen) — Capabilities & Features

> Currency: researched 2026-11-10 against Alibaba Cloud Model Studio's live English
> docs (alibabacloud.com and help.aliyun.com mirrors). Model IDs, regional feature
> matrices and prices drift monthly; field names are stable. Anything the docs did not
> state is marked **unverified**.

Model Studio (the international name; "Bailian" in China) exposes Qwen **and hosted
third-party models** (DeepSeek, GLM, Kimi, MiniMax) through **four protocols on one
platform**: an OpenAI-compatible Chat Completions mode, an OpenAI-compatible Responses
mode, an Anthropic-compatible Messages mode, and the native **DashScope** protocol.
Hosts are workspace- and region-scoped: `https://{WorkspaceId}.{region}.maas.aliyuncs.com`
(regions `cn-beijing`, `ap-southeast-1`, `us-east-1`, `eu-central-1`, `cn-hongkong`,
`ap-northeast-1`); the legacy hosts `dashscope.aliyuncs.com` (Beijing),
`dashscope-intl.aliyuncs.com` (Singapore) and `dashscope-us.aliyuncs.com` still work.
Auth: `Authorization: Bearer <key>`; **keys are region-bound** (a Beijing key on the
Singapore host returns 401 `invalid_api_key`).

## 1. API surface / endpoints

| Protocol | Endpoint (relative to the regional host) |
|---|---|
| OpenAI-compatible Chat Completions | `POST /compatible-mode/v1/chat/completions` |
| OpenAI-compatible Responses | `POST /compatible-mode/v1/responses` (the older `/api/v2/apps/protocols/compatible-mode/v1/responses` is "no longer maintained") |
| Anthropic-compatible Messages | `POST /apps/anthropic/v1/messages` (no `/v1/models`; clients doing model discovery get 404) |
| DashScope native, text | `POST /api/v1/services/aigc/text-generation/generation` |
| DashScope native, multimodal (VL, Omni, Audio) | `POST /api/v1/services/aigc/multimodal-generation/generation` |
| Streaming over DashScope HTTP | header `X-DashScope-SSE: enable` (the `stream` body field is SDK-only) |
| Standalone web search, OCR, embeddings, rerank, TTS/ASR, image/video generation | separate services (out of chat scope) |

Protocol support is **model-specific**: Qwen3.5+ open-source models "use the DashScope
multimodal interface" (`url error` on the text endpoint); multimodal models with web
search must use the multimodal endpoint with streaming or return 400.

## 2. Request & response model

**OpenAI-compatible mode** is byte-shaped like OpenAI Chat Completions: `messages[]`
with `system|user|assistant|tool` roles, string or content-part `content`, assistant
`tool_calls[]` (`id`, `type:"function"`, `function.{name,arguments}` with JSON-string
arguments), tool messages with `tool_call_id`. Two additions ride on the assistant
message: `partial: true` (prefix continuation, §12) and `reasoning_content` (echoed
thinking, §7). The response adds `choices[].message.reasoning_content` and
`system_fingerprint` is **always `""`**.

**DashScope native** wraps the same ideas in a different envelope:

```
{ "model": "...",
  "input":      { "messages": [ {role, content} ] },
  "parameters": { "result_format": "message", "incremental_output": true, ... } }
→
{ "request_id": "...", "code"?: "...", "message"?: "...",
  "output": { "text"?: "...", "finish_reason": "stop|length|tool_calls|null",
              "choices": [ { "finish_reason", "message": {role, content, reasoning_content, tool_calls[], image_hw?} } ] },
  "usage":  { "input_tokens", "output_tokens", "total_tokens", "image_tokens"?, "video_tokens"?, "audio_tokens"?,
              "input_tokens_details": {text_tokens, image_tokens, video_tokens},
              "output_tokens_details": {text_tokens, reasoning_tokens, audio_tokens},
              "prompt_tokens_details": {cached_tokens, cache_type, cache_creation: {ephemeral_5m_input_tokens, cache_creation_input_tokens}} } }
```

`result_format: "text"` returns `output.text` (legacy); `"message"` returns
`output.choices[]`. Multimodal content on DashScope is a list of bare-key objects —
`{"text": ...}`, `{"image": ...}`, `{"video": [...frames...], "fps": 2}` — not
OpenAI's `{"type": ..., "...": {...}}` parts. Errors come back as top-level
`code`/`message`/`request_id`, not an `error` object.

## 3. Generation parameters (OpenAI-compatible mode)

| Field | Notes (exact names) |
|---|---|
| `model` | required; region-specific catalogue |
| `messages` | required; compat reference says `system` only at `messages[0]` |
| `stream`, `stream_options.include_usage` | final chunk has empty `choices` + `usage`; `stream_options` rejected when `stream=false` |
| `temperature` | `[0, 2)`; `0` "not recommended" |
| `top_p` | `(0, 1.0)` |
| `presence_penalty` | `[-2.0, 2.0]`; commercial Qwen + open-source qwen1.5+ only |
| `n` | 1–4; "qwen-plus only"; forced to 1 when `tools` is set |
| `max_tokens` | per-model cap; DashScope marks it "to be deprecated" for `max_completion_tokens` |
| `seed` | unsigned 64-bit |
| `stop` | string, string[], or token-id arrays (not mixed) |
| `tools`, `tool_choice`, `parallel_tool_calls` | §5 |
| `response_format` | `{"type":"json_object"}` or `{"type":"json_schema", ...}` (§4) |
| `logprobs`, `top_logprobs` | listed on DashScope; present in compat on supported models (unverified per model) |
| `enable_thinking`, `thinking_budget`, `preserve_thinking`, `reasoning_effort` | §7 — **non-OpenAI**; Python SDK users pass them in `extra_body` |
| `enable_search`, `search_options` | §5 (web search) — non-OpenAI |
| `modalities`, `audio` | Omni only (§9) |
| `vl_high_resolution_images`, `vl_enable_image_hw_output` | VL only (§9) — non-OpenAI |
| `frequency_penalty`, `max_completion_tokens`, `user` | not documented on the compat reference page — **unverified** |

The compat reference page still says `tools` "cannot be used with `stream=True`";
the function-calling guide documents streamed `tool_calls` deltas on current models.
Treat the reference statement as stale.

DashScope-only sampling knobs: `top_k`, `repetition_penalty`.

## 4. Structured outputs

- `response_format: {"type": "json_object"}` — valid JSON, no shape guarantee; the
  prompt **must contain the word "JSON"** (case-insensitive) or the API errors.
- `response_format: {"type": "json_schema", "json_schema": {"schema": ..., "strict": true}}`
  — Qwen3.7-Plus/Flash/Max and Qwen3.8-Max/Flash series only; **not yet available in
  the Singapore region**; unsupported keywords (`multipleOf`, `uniqueItems`,
  `patternProperties`) return 400.
- **Silent fallback**: with image/video/audio input, `json_schema` "falls back to
  `json_object` and the schema is ignored" — no error.
- Responses mode: `text.format` with `text|json_schema|json_object`.
- Models marked "non-thinking mode" support structured output only with thinking off.

## 5. Tool / function calling

- Definition: OpenAI nested `{"type":"function","function":{name,description,parameters}}`;
  Responses mode uses the flat form. Name ≤ 64 chars.
- `tool_choice`: `"auto"` (default), `"none"`, `{"type":"function","function":{"name"}}`.
  **`"required"` is not supported by Qwen models** and is not supported in thinking mode.
- `parallel_tool_calls` defaults to **`true`** (several calls per response); `false`
  limits to one — except hosted `kimi-k3`, which "may still return multiple".
- Streaming: `delta.tool_calls[]` items carry `index`, `id`, `type`, `function`; the
  first chunk per index has the non-empty `id` and `name`, later chunks have empty
  `id`, `name: null` and `arguments` fragments to concatenate by `index`.
- Thinking + tools: keep the assistant message with `reasoning_content`, `content`
  and `tool_calls` in history before the tool results; `preserve_thinking` governs
  whether the model re-reads it (§7).
- **Web search** (server-side, non-OpenAI): `enable_search: true` plus
  `search_options: {forced_search, search_strategy: "turbo"|"max"|"agent"|"agent_max",
  enable_source, enable_citation, citation_format: "[<number>]"|"[ref_<number>]",
  enable_search_extension}`. Results come back in `search_info.search_results[]`
  (`index`, `title`, `url`, `site_name`, `icon`) — **DashScope protocol only**; the
  compat protocol runs the search but does not return sources. In Responses mode web
  search is a tool: `{"type":"web_search"}` alongside `web_extractor`,
  `code_interpreter`, `web_search_image`, `image_search`, `file_search`
  (one `vector_store_ids` entry) and `mcp` (`server_protocol`, `server_label`,
  `server_url`, `headers`).
- Strict tool schemas: not documented — **unverified**.

## 6. Streaming

OpenAI-compatible mode: SSE `data:` lines of `chat.completion.chunk`, `delta.content`,
`delta.reasoning_content`, `delta.tool_calls`, `delta.audio` (Omni); terminal
`data: [DONE]`; `usage` only on the last chunk when `include_usage` is set.

DashScope native: `X-DashScope-SSE: enable`; chunks are full response envelopes.
`incremental_output` **defaults to false** (every chunk repeats the whole text so far);
with `enable_thinking: true` on DashScope, `incremental_output: true` is mandatory or
the API errors.

Responses mode event names (documented): `response.created`, `response.in_progress`,
`response.completed`, `response.incomplete`, `response.output_item.added/done`,
`response.content_part.added/done`, `response.output_text.delta/done`,
`response.reasoning_text.delta/done`, `response.web_search_call.in_progress/searching/completed`,
`response.code_interpreter_call.in_progress/interpreting/completed`,
`response.file_search_call.*`, `response.mcp_call_arguments.delta/done`,
`response.mcp_call.in_progress/completed`, `response.custom_tool_call_input.delta/done`.
`web_search_image` and `image_search` emit no intermediate events.

Streaming-only models: Qwen3.5+ open-source (`parameter.enable_thinking only support
stream call`), QwQ/QVQ, all Omni models.

## 7. Reasoning / thinking

| Knob | Shape |
|---|---|
| `enable_thinking` | boolean; toggles **hybrid** models; ignored by thinking-only models. Non-standard: `extra_body` in the OpenAI Python SDK, `parameters` on DashScope HTTP. Responses mode: "will be deprecated; `reasoning.effort` takes precedence" |
| `thinking_budget` | integer cap on reasoning tokens (not on hosted Kimi K3) |
| `reasoning_effort` | Qwen3.8 series: `xhigh` (default), `medium`, `low`; Responses `reasoning.effort` accepts `none|minimal|low|medium|high|xhigh|max` with per-model remapping (`minimal`→`low`) |
| `preserve_thinking` | boolean; when true, historical assistant `reasoning_content` is re-read. Default **off** for most Qwen, **on** for hosted `kimi-k3.1-pro`/`kimi-k3`; enabling it without history "does not cause an error" |
| Prompt switches | `/think`, `/no_think` on Qwen3 open-source hybrids |

Output: `message.reasoning_content` next to `content` (compat), `delta.reasoning_content`
first then `delta.content` (stream), `output.choices[0].message.reasoning_content`
(DashScope); Responses mode returns an output item `{"type":"reasoning","summary":[{"type":"summary_text", ...}]}`.
No signature or opaque blob exists; replay is plain text and billed as input.
Reasoning tokens: `completion_tokens_details.reasoning_tokens` (compat) /
`output_tokens_details.reasoning_tokens` (DashScope). For Qwen3.8, `max_tokens`
covers answer **plus** chain of thought; for other models answer only.

Hybrid (toggleable) families: Qwen3.8/3.7/3.6/3.5 commercial, `qwen-plus`/`qwen-flash`
(off by default), `qwen3-vl-plus` (off by default). Thinking-only: `qwen3.8-2.4t-a95b`,
`qwen3.7-max-preview`, QwQ/QVQ, R1 distills, hosted `glm-5.3`, `kimi-k2.7-code`.

## 8. Prompt / context caching

- **Implicit** cache: automatic on supported models, cannot be disabled, no hit
  guarantee; hit tokens typically 20% of input price; TTL "indeterminate".
- **Explicit** cache: Anthropic-style `cache_control: {"type":"ephemeral"}` on a
  `content` block of a system/user/assistant/tool message (tool *definitions* cannot be
  cached); ≤ 4 markers (extra markers: only the last four count); backward search over
  ≤ 20 preceding blocks; creation ≈ 125% input price, hit ≈ 10%; **5-minute TTL reset
  on each hit**; min 1,024 tokens (both modes). Explicit and implicit are mutually
  exclusive per request. The cache is created *after* the response returns.
- Usage: `usage.prompt_tokens_details.cached_tokens` and
  `usage.prompt_tokens_details.cache_creation_input_tokens` (compat and DashScope);
  Singapore implicit cache currently reports `usage.cached_tokens` (slated to move).
  Anthropic mode: `cache_read_input_tokens` / `cache_creation_input_tokens`.
- Responses mode has a separate "session cache" (`x-dashscope-session-cache: enable`
  header); when off, implicit cache applies.
- ~10 tokens may be appended after a marker and billed at standard rate.

## 9. Multimodal

| Modality | Compat shape | DashScope shape |
|---|---|---|
| Image in | `{"type":"image_url","image_url":{"url": https-or-data-URI}}` | `{"image": url\|data-URI\|file://}` |
| Video file | `{"type":"video_url","video_url":{"url"}}` | `{"video": url, "fps"}` |
| Video as frames | `{"type":"video","video":[img, img, ...]}` | `{"video":[...], "fps"}` (fps `[0.1, 10]`, default 2.0; `max_frames` SDK-only) |
| Audio in (Omni) | `{"type":"input_audio","input_audio":{"data": url\|data-URI, "format":"wav"\|"mp3"}}` | — (unverified) |
| Audio out (Omni) | `modalities:["text","audio"]`, `audio:{"voice":"Tina","format":"wav"}`; chunks carry `delta.audio.data` (base64 PCM 24 kHz) and `delta.audio.transcript` | — |
| Resolution knobs | `vl_high_resolution_images` (fixed-resolution strategy, ignores `max_pixels`), `max_pixels`, `min_pixels`, `total_pixels`; `vl_enable_image_hw_output` returns `message.image_hw` | same names |

Omni specifics: `qwen3.8-omni-flash` accepts text/image/audio/video, **text output
only**, 1M context, tools + web search, JSON mode but not JSON Schema;
`qwen3.5-omni-plus/-flash` and `qwen3-omni-flash` produce audio (non-thinking mode
only; `modalities` must be `["text"]` in thinking mode). All Omni models are
streaming-only. Function calling on Omni requires streaming.
Responses mode: `input_text`, `input_image`, `input_file` (only `qwen3.8-flash`,
`qwen3.8-max`, `qwen3.5-ocr`), `input_audio`/`input_video` (`qwen3.8-omni-flash` only).
Document parts: no first-party PDF part on chat; use `qwen3.5-ocr` / `input_file`.

## 10. Models (catalogue snapshot 2026-11-10; verify in the console)

| Family | IDs (examples) | Facts verified |
|---|---|---|
| Qwen3.8 commercial | `qwen3.8-max`, `qwen3.8-max-0902`, `qwen3.8-flash` | `qwen3.8-flash`: 1,000,000 context, 991,808 max input (983,616 thinking), 131,072 max output, 262,144 max CoT; CNY 0.8 / 2.7 per 1M in/out (Beijing). `qwen3.8-max` specs: **unverified** (third-party sites say 1M / 131K) |
| Qwen3.8 open-weight | `qwen3.8-27b`, `qwen3.8-2.4t-a95b` (thinking-only) | `qwen3.8-27b`: same limits; USD 0.5 / 3.0 (Singapore), 0.424 / 1.696 (Beijing) |
| Qwen3.7 / 3.6 / 3.5 | `qwen3.7-max`, `qwen3.7-plus`, `qwen3.7-flash`, `qwen3.6-plus`, `qwen3.6-35b-a3b`, `qwen3.5-plus`, `qwen3.5-397b-a17b`, `qwen3.5-122b-a10b`, `qwen3.5-27b` (+ dated snapshots) | hybrid thinking; open-weight ones streaming-only with thinking |
| Qwen3 generation | `qwen-plus`, `qwen-flash`, `qwen-max`, `qwen-turbo`, `qwen3-coder-flash`, `qwen3-vl-plus` | thinking off by default on `qwen-plus`/`qwen-flash` |
| Omni | `qwen3.8-omni-flash`, `qwen3.8-omni-flash-realtime`, `qwen3.5-omni-plus/-flash`, `qwen3-omni-flash` | §9 |
| Hosted third-party | `deepseek-v4-pro`, `deepseek-v4.1-flash(-1017)`, `glm-5.3`, `glm-5.2`, `glm-5.1`, `glm-5`, `kimi-k3.1-pro`, `kimi-k3`, `kimi-k2.7-code`, `kimi-k2.6`, `MiniMax-M2.5` | same four protocols; knobs partially differ (e.g. Kimi default `preserve_thinking`) |

Feature availability (function calling, structured output, web search, prefix,
caching, batch) is a **per-region matrix** on every model page.

## 11. Auth, limits, errors

- Auth: Bearer key, region-bound; sub-workspace model authorization required.
- Rate limits: per account+model RPM and TPM (also enforced per second as RPM/60);
  tiering by monthly spend; **no rate-limit headers documented**.
- Error envelopes: DashScope `{code, message, request_id}`; compat
  `{"error": {"code", "message", "type", "param"}}` with paired codes
  (`InvalidApiKey`/`invalid_api_key`, `DataInspectionFailed`/`data_inspection_failed`).

| HTTP | Code(s) | Meaning |
|---|---|---|
| 400 | `InvalidParameter` (incl. `InternalError.Algo.InvalidParameter`) | bad params; **input exceeds model limit** (context length); thinking/streaming-only model called non-streaming; repetitive tool-call loop; "No backend server available" |
| 400 | `DataInspectionFailed` / `data_inspection_failed`, `IPInfringementSuspect`, `CustomRoleBlocked` | input **or output** content moderation |
| 400 | `invalid_request_error` / `invalid_value` | compat-style validation (bad `seed`, missing `model`) |
| 401 | `InvalidApiKey` / `invalid_api_key` | wrong key or wrong region |
| 403 | `AccessDenied`, `Arrearage`, `AllocationQuota.FreeTierOnly`, `Model.AccessDenied`, `AccessDenied.Unpurchased` | permissions / billing |
| 404 | `ModelNotFound` / `model_not_found` | id, region or activation |
| 429 | `Throttling.RateQuota`, `Throttling.AllocationQuota`, `Throttling.ResourceExhausted`, `Throttling.ServiceOverloaded` | RPM / TPM / burst |
| 500 / 503 | `InternalError`, `ServiceUnavailable` | retry |

Finish reasons (compat): `stop`, `length`, `tool_calls`, `null`; DashScope the same.

## 12. Distinctive features

- **One platform, four wire protocols** (compat chat, compat Responses, Anthropic
  Messages, DashScope) over the same models — the clearest real-world instance of
  "interface ≠ provider".
- **Hosted competitors** (DeepSeek, GLM, Kimi, MiniMax) behind the same knobs, with
  per-model knob remapping (effort levels, `preserve_thinking` defaults).
- **Partial mode**: `{"role":"assistant","content":"<prefix>","partial":true}` as the
  last message; the prefix is **not echoed**, the caller concatenates.
- **Explicit Anthropic-style cache markers on an OpenAI-shaped request.**
- Responses mode **silently truncates input to ~80% of the context window** and
  **ignores any parameter it does not list**; `logprobs` always `null`.
- Web search as a request flag with `search_strategy` tiers and optional inline
  citations whose markers are configurable (`[1]` vs `[ref_1]`).
- Qwen-Omni audio-in/audio-out on the chat endpoint; region-gated feature matrix.

## 13. Mapping to `ocai`

**(a) Interface decision.** The compat Chat Completions mode is close enough for
`ocai.openai.chat_completions` served through a `Host`/`DialectTraits` variant
(`vendor="alibaba"`, base URL per region + workspace). Exact divergences to census:
`enable_thinking`/`thinking_budget`/`preserve_thinking`/`reasoning_effort` (extra
request fields); `reasoning_content` on assistant messages and in `delta`; `partial`
on assistant messages; `enable_search`/`search_options` + `search_info` on the
response; `vl_high_resolution_images`, `video` (frame-list part type), `input_audio`,
`modalities`/`audio` + `delta.audio`; `cache_control` on content blocks +
`prompt_tokens_details.cache_creation_input_tokens`; `tool_choice:"required"`
rejected; `n` forced to 1 with tools; `system_fingerprint` always `""`; error codes
paired DashScope/OpenAI. The **DashScope native protocol is a different interface**
(`input`/`parameters`/`output` envelope, bare-key multimodal parts, non-incremental
streaming default, `code`/`message` errors) and would be `ocai.qwen.dashscope`
(`NodeId("alibaba", "dashscope", tag, shape)`) — defer it; the Responses and
Anthropic modes should ride the future `openai/responses` and the existing
`anthropic/messages` codecs as hosts (`signature` always `""` there).

**(b) Parts.** Emits/accepts: `PartText`, `PartImage` (url/base64), `PartVideo`
(url, plus the frame-list form → per-part optional `frames`, ABSENT elsewhere),
`PartAudio` (in and out, Omni), `PartReasoning` (`text` only), `PartToolCall`,
`PartToolResult`. `search_info.search_results` → `PartServerToolCall/Result(kind="web_search")`
with verbatim payload; inline `[ref_n]` markers → `PartText.annotations` only when the
marker offsets validate, otherwise censused extension. `input_file`/OCR → `PartDocument`
on Responses mode only. `image_hw` → censused extension.

**(c) Reasoning.** Requested via `ReasoningConfig`: `include_thoughts`→`enable_thinking`
(first-class), `budget_tokens`→`thinking_budget` (first-class),
`effort`→`reasoning_effort` (first-class; Qwen's `xhigh` default and `max/high→xhigh`
remap on the Anthropic mode is a **SemanticShift**). Returned as plain text; **no
signature/opaque blob**, so no `ProviderRef` anchor is required for replay —
`preserve_thinking` decides whether replayed text is read and is a **censused
extension** (`alibaba.preserve_thinking`). Prompt switches `/think` are
`provider_options` only.

**(d) Streaming.** `fold(stream) == complete` is achievable on compat mode: deltas are
incremental, `reasoning_content` precedes `content`, tool args stream by `index`.
Gaps: usage only on the last chunk and only with `include_usage` (StreamEnd must
tolerate absent usage); Omni `delta.audio` needs `DeltaBlob`; DashScope
non-incremental default must be normalized by the codec (`incremental_output: true`
forced). Streaming-only models make the unary edge UNSUPPORTED-and-reported for them.

**(e) Errors.** 429 `Throttling.*` → `RateLimitError`; 401 `InvalidApiKey` and 403
`AccessDenied*`/`Arrearage` → `AuthError`; 400 `InvalidParameter` with the
"input length exceeds" message → `ContextLengthError` (message-sniffed, census it);
400 `DataInspectionFailed`/`IPInfringementSuspect`/`CustomRoleBlocked` →
`ContentFilterError` (note it fires on **output** too — a mid-stream wire error
shape, not only pre-generation); 500/503 `InternalError`/`ServiceUnavailable` →
`TransientError`.

**(f) Priority: P1.** Rationale: the largest model catalogue behind one
OpenAI-shaped dialect, and it is the natural host for the `reasoning_content` dialect
family (shared with DeepSeek, GLM, Kimi) — but the first dialect of that family should
be DeepSeek (P0) because its replay rule is the strictest. Effort by analogy: 1 WU for
the `Host`/`DialectTraits` variant + census + unary fixtures (≈ half of WU-13), 1 WU for
streaming fold triples incl. `reasoning_content` and `search_info` (≈ WU-14b),
+1 WU later for Omni audio deltas; `ocai.qwen.dashscope` would be a full
WU-13/14a/14b triple and is P3.

## Sources (read 2026-11-10)

- https://www.alibabacloud.com/help/en/model-studio/deep-thinking
- https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-responses
- https://help.aliyun.com/en/model-studio/compatibility-of-openai-with-dashscope
- https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-dashscope
- https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference
- https://www.alibabacloud.com/help/en/model-studio/anthropic-api-messages
- https://www.alibabacloud.com/help/en/model-studio/partial-mode
- https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output
- https://www.alibabacloud.com/help/en/model-studio/qwen-function-calling
- https://help.aliyun.com/en/model-studio/web-search
- https://www.alibabacloud.com/help/en/model-studio/context-cache
- https://www.alibabacloud.com/help/en/model-studio/qwen-omni
- https://www.alibabacloud.com/help/en/model-studio/vision
- https://help.aliyun.com/en/model-studio/qwen-vl-compatible-with-openai
- https://www.alibabacloud.com/help/en/model-studio/models
- https://help.aliyun.com/en/model-studio/qwen3-8-flash
- https://www.alibabacloud.com/help/en/model-studio/qwen3-8-27b
- https://help.aliyun.com/en/model-studio/error-code
- https://help.aliyun.com/en/model-studio/rate-limit
