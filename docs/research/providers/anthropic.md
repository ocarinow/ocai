# Anthropic (Claude) API — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Base: `https://api.anthropic.com/v1`. Auth: `x-api-key: <key>` + `anthropic-version:
2023-06-01` (OAuth uses `Authorization: Bearer` + `anthropic-beta: oauth-2025-04-20`).
Everything chat goes through **one endpoint**: `POST /v1/messages`. Tools, structured
outputs, caching, and thinking are all features of that single endpoint, not separate
APIs.

## 1. API surface / endpoints

| Capability | Endpoint |
|---|---|
| **Messages** | `POST /v1/messages` (the core endpoint) |
| Token counting | `POST /v1/messages/count_tokens` |
| Batches | `POST /v1/messages/batches` (50% discount, ≤100k req / 256MB) |
| Files | `POST /v1/files` (beta `files-api-2025-04-14`, ≤500MB) |
| Models | `GET /v1/models`, `/v1/models/{id}` (live capability lookup) |
| Managed Agents | `/v1/agents`, `/v1/sessions`, `/v1/environments` (beta) — server-run agent loop + hosted container |

No separate embeddings endpoint (Anthropic recommends third-party embeddings).

## 2. Request & response model

- Top-level **`messages`** (alternating `user`/`assistant`; first must be `user`),
  separate top-level **`system`** (string or array of text blocks — *not* a message
  role), `model`, `max_tokens` (required).
- **Content blocks**: a message's `content` is a string or an array of typed blocks —
  `text`, `image` (`source`: base64 / url / `file_id`), `document` (PDF/text, with
  optional `citations`), `tool_use`, `tool_result`, `thinking`, `redacted_thinking`.
- **Response**: `content` is a list of blocks (`TextBlock`, `ThinkingBlock`,
  `ToolUseBlock`, …) — **check `block.type` before reading**. Plus `stop_reason`,
  `stop_details`, `usage`, `model`, `id`.
- **Mid-conversation system messages** (beta `mid-conversation-system-2026-04-07`):
  append `{role:"system", …}` into `messages[]` (must follow a user turn) for operator
  instructions without invalidating the cached prefix.

## 3. Generation parameters

`model` · `max_tokens` (required; ≤128K on Opus/Fable with streaming, ≤64K Sonnet/Haiku)
· `system` · `messages` · `stop_sequences` · `stream` · `tools` / `tool_choice` ·
`thinking` (see §7) · `output_config` (effort, structured-output format, task_budget) ·
`metadata` · `cache_control`.

> **Removed on Fable 5 / Opus 4.8 / 4.7**: `temperature`, `top_p`, `top_k`, and
> `thinking:{type:"enabled", budget_tokens:N}` all return **400**. Steer via prompting +
> `effort` instead. (Older models still accept them; `temperature` and `top_p` are
> mutually exclusive on all Claude 4+.)

## 4. Structured outputs

- **JSON output**: `output_config: {format: {type:"json_schema", schema:{…}}}` on
  `messages.create()` (the old top-level `output_format` is deprecated). SDKs offer
  `messages.parse(..., output_format=PydanticModel)` returning a validated object.
- **Strict tool use**: add `strict: true` to a tool definition to guarantee valid
  parameter schemas.
- JSON-schema support is a subset (no recursion, no numeric/length constraints — SDKs
  validate those client-side). Incompatible with citations and prefilling.

## 5. Tool / function calling

- **Definition**: `{name, description, input_schema, strict?}` (input_schema is JSON
  Schema). No `function` wrapper — flat.
- **`tool_choice`**: `{type:"auto"}` · `{type:"any"}` · `{type:"tool", name}` ·
  `{type:"none"}`; any value accepts `disable_parallel_tool_use:true`. Parallel tool
  use is on by default.
- **Wire format**: assistant emits `tool_use` blocks `{id, name, input}` (input is a
  **parsed object**, but escaping varies — never raw-string-match it); you return a
  `user` message with `tool_result` blocks `{tool_use_id, content, is_error?}`.
- **Server-side tools** (run on Anthropic infra, declared in `tools`): `code_execution`
  (sandboxed container), `web_search` / `web_fetch` (with citations + dynamic
  filtering), `computer_use`, `bash`, `text_editor`, `memory`, plus remote MCP via
  `mcp_servers`. Server-tool loops can return `stop_reason:"pause_turn"` — re-send to
  resume.
- **Tool runner** (SDK beta): handles the agentic loop automatically; manual loop
  available for human-in-the-loop gating.

## 6. Streaming

`stream:true` or `messages.stream()` helper. Event types: `message_start`,
`content_block_start`, `content_block_delta` (`text_delta` / `thinking_delta` /
`input_json_delta`), `content_block_stop`, `message_delta` (carries `stop_reason`,
usage), `message_stop`. The SDK helper exposes `text_stream` and `.get_final_message()`.
Streaming is required above ~16K `max_tokens` (SDK guards against HTTP timeouts).

## 7. Reasoning — adaptive thinking + effort

- **Adaptive thinking** (Fable 5, Opus 4.6/4.7/4.8, Sonnet 4.6): `thinking:
  {type:"adaptive"}` — Claude decides when/how much to think; auto-enables interleaved
  thinking between tool calls. **`budget_tokens` is deprecated/removed** — the
  fixed-budget model is gone.
- **Effort**: `output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}` — controls
  thinking depth *and* overall token spend. Default `high`. `xhigh` is the sweet spot
  for coding/agentic.
- **Display**: `thinking.display` = `"omitted"` (default on Fable 5 / Opus 4.7/4.8 —
  empty thinking text) or `"summarized"`. The raw chain of thought is never returned;
  Fable 5 returns regular (summarizable) `thinking` blocks. Echo thinking blocks back
  unchanged on the same model.
- **Task Budgets** (beta `task-budgets-2026-03-13`): `output_config.task_budget` tells
  the model its token budget for a whole agentic loop (it self-moderates) — distinct
  from the enforced `max_tokens`.

## 8. Prompt caching

`cache_control: {type:"ephemeral", ttl?:"1h"}` on any content block, or top-level
`cache_control` to auto-cache the last block. **Prefix match** — render order is `tools
→ system → messages`; any byte change in the prefix invalidates everything after. Max 4
breakpoints. Minimum cacheable prefix is model-dependent (~1024–4096 tokens). Reads
~0.1× input price; writes 1.25× (5-min) / 2× (1h). Verify via
`usage.cache_read_input_tokens`. **Compaction** (beta) auto-summarizes history near the
context limit (append `response.content` back, including compaction blocks).

## 9. Multimodal

- **Vision**: `image` blocks (base64 / url / `file_id`). High-res support (up to 2576px
  long edge on Opus 4.7+, pixel-accurate coordinates for computer use).
- **Documents/PDF**: `document` blocks with optional citation support.
- No first-party audio in/out or image generation (image generation only via the
  server-side code-execution tool).

## 10. Models (cached 2026-06-04)

| Model | ID | Context | $/1M in–out |
|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | 1M | $10 / $50 |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | $5 / $25 |
| Claude Opus 4.7 / 4.6 | `claude-opus-4-7` / `-4-6` | 1M | $5 / $25 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | $3 / $15 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | $1 / $5 |

Use exact ID strings (no date suffix on aliases). Default to `claude-opus-4-8` unless a
model is named. Fable 5: thinking always on (omit the param), no ZDR, `refusal` stop
reason, no prefill.

## 11. Auth, limits, errors

- Auth: `x-api-key` + `anthropic-version`.
- Limits: per-tier RPM / ITPM / OTPM; headers `x-ratelimit-*`, `retry-after`; SDK
  auto-retries 408/409/429/5xx.
- Errors: `{type:"error", error:{type, message}, request_id}`. Codes: 400
  `invalid_request_error`, 401, 403, 404, 413 `request_too_large`, 429
  `rate_limit_error`, 500 `api_error`, 529 `overloaded_error`. Use typed SDK exceptions.

## 12. Distinctive to Anthropic

- **Single `/v1/messages` endpoint** — tools, structured output, caching, thinking are
  all features of it.
- **System prompt is a top-level field**, not a message role.
- **Adaptive thinking + `effort`** instead of fixed budgets or sampling temperature.
- **`stop_reason:"refusal"`** as a first-class safety outcome (HTTP 200) with
  `stop_details.category`; server-side `fallbacks` / client middleware to retry on
  another model.
- **Server-side tools** (code execution, web search/fetch with citations, computer use,
  memory) declared inline.
- **Explicit, breakpoint-based prompt caching** with a strict prefix-match model.
- **Managed Agents**: Anthropic runs the agent loop + hosts a per-session container.
- **Citations** as a first-class document feature.

## 13. Mapping to `ocai`

- The IR's separate `system` role must become Anthropic's **top-level `system`** field
  (not a message) — adapter responsibility.
- `tool_use`/`tool_result` map to `ToolCall` and a `tool`-role `Message`, but Anthropic
  threads `tool_result` as `user`-role content blocks — the adapter reconstructs.
- Content blocks (images, documents, thinking) are richer than the IR's `content: str` —
  multimodal + thinking blocks live in `extensions` (or a future richer IR content
  model); `ChatResponse.raw` keeps the full block list.
- `effort` / adaptive thinking / `cache_control` / server tools / `output_config` →
  `provider_options` / `extensions`. `stop_reason` (esp. `refusal`) has no canonical
  home yet → a candidate first-class IR field.
- `usage` maps to `Usage`, but Anthropic adds `cache_creation_input_tokens` /
  `cache_read_input_tokens` — extra fields the IR's `Usage` should grow or stash in
  `extensions`.

## WU-37 host declaration verification (2026-11-10)

The [Bedrock request reference](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-request-response.html)
specifies body `anthropic_version=bedrock-2023-05-31` and optional
`anthropic_beta` as an array. The [Google Cloud Claude REST examples](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/use-claude)
specify `anthropic_version=vertex-2023-10-16`. These confirm separate host
versions, not interchangeable values in one cloud tuple. Beta feature availability
is model/host-specific; declaring the Bedrock mapping enables no feature.

The synthetic `anthropic_vertex_version.json` HTTP recording qualifies the existing
Vertex unary envelope in both drivers. Bedrock transport, signing and streaming
remain later WUs. No Vertex beta body mapping is inferred from the Bedrock example;
explicit unmapped feature headers remain headers. Binding-level overrides are
not relocated by the trait-only resolver in WU-37.

## 16. WU-43 search qualification (verified 2026-11-11)

The initial surface is `web_search_20250305`, basic direct search. Later dynamic
filtering versions are excluded. Domain allow/block lists are alternatives;
location uses `type: approximate`. Native `max_uses` stays a provider control.
Results retain `encrypted_content`, citations retain `encrypted_index`, and both
must survive replay. Search failures appear inside a successful HTTP response;
an empty result list is a successful search with no matches. Billing uses the
reported `usage.server_tool_use.web_search_requests`, not result or part counts.
Source: [Web search tool: definition, response, streaming and usage](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool).

Direct server calls stream their input as JSON fragments; result blocks arrive
complete. Call/result identity is `id`/`tool_use_id`, independent of position.
Source: [Server tools: block identity and streaming events](https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools).

Implementation boundary: buffer one server-call input until its block closes,
then emit a complete canonical part; do not add a kernel delta type. A result's
required `anchor` scopes its complete native payload, identified by `tool_use_id`;
multiple encrypted result strings remain verbatim inside that payload. Citation
`opaque` stores its native encrypted index. Missing replay evidence is unsupported.

WU-43 implementation qualification pins the basic version explicitly on each
`ServerTool` through `provider_options["anthropic.messages"]["type"]`.
Unpinned intent remains unsupported. `max_uses` uses the registered
`anthropic.web_search` extension; absent usage remains unknown. Recordings are
synthetic examples of the documented wire, not live-provider certification.
Search input timing is reported as a semantic shift; incomplete input retains
fragments without successful termination or replay authority.
