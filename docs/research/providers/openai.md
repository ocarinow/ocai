# OpenAI API — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Base: `https://api.openai.com/v1`. Auth: `Authorization: Bearer <key>` (+ optional
`OpenAI-Organization` / `OpenAI-Project`). Two chat surfaces coexist: the newer
**Responses API** (recommended, agentic, stateful) and the classic **Chat
Completions API** (stateless, still fully supported). Where field names differ, both
are given.

## 1. API surface / endpoints

| Capability | Endpoint | Status |
|---|---|---|
| **Responses** | `POST /v1/responses` | Recommended primary API — stateful, multimodal, built-in tools |
| **Chat Completions** | `POST /v1/chat/completions` | Supported; best for lightweight stateless chat |
| Completions (legacy text) | `POST /v1/completions` | Legacy |
| Conversations | `/v1/conversations` | Persistent conversation objects (pairs with Responses; replaces Threads) |
| Assistants | `/v1/assistants`, `/threads`, `/runs` | **Deprecated** — sunset Aug 26 2026; migrate to Responses + Conversations |
| Embeddings | `POST /v1/embeddings` | `text-embedding-3-small/large`, `dimensions` param |
| Images | `/v1/images/generations`, `/edits` | GPT Image 2 |
| Audio | `/v1/audio/speech` (TTS), `/transcriptions`, `/translations` (STT) | |
| Realtime | WebSocket / WebRTC | Voice-to-voice, low latency |
| Moderation | `POST /v1/moderations` | |
| Batch | `POST /v1/batches` | Async, 50% discount, 24h window |
| Fine-tuning | `POST /v1/fine_tuning/jobs` | SFT, DPO, RFT, vision |
| Files | `POST /v1/files` | For batch, fine-tune, file_search, input |

## 2. Request & response model

- **Responses**: top-level **`input`** (string *or* array of typed "Items") + separate
  **`instructions`** field (replaces the system message). Output is a typed
  **`output`** array of Items; `response.output_text` is a convenience accessor.
- **Chat Completions**: single **`messages`** array; system guidance is a
  `role: "system"` message; output at `choices[0].message.content` with
  `choices[].finish_reason`.
- **Roles**: `user`, `assistant`, `tool`, plus `developer` (Responses; the renamed
  `system`, reflecting the instruction hierarchy `platform > developer > user`). Chat
  Completions still uses `system`.
- **Multimodal input parts (Responses)**: `input_text`, `input_image` (URL / base64 /
  `file_id`, with `detail`), `input_file` (PDF/docs), `input_audio`. (Chat Completions
  uses `text` / `image_url` / `input_audio`.)
- **Output Item types (Responses)**: `message` (with `output_text` / `refusal` parts),
  `reasoning`, `function_call`, plus built-in tool items (`web_search_call`, …).

## 3. Generation parameters

| Responses | Chat Completions equivalent | Notes |
|---|---|---|
| `model` | `model` | required |
| `max_output_tokens` | `max_tokens` / `max_completion_tokens` | Responses count **includes reasoning tokens** |
| `temperature`, `top_p` | same | |
| `instructions` | system message | resend each turn when chaining |
| `reasoning: {effort, summary}` | — | see §7 |
| `text: {format, verbosity}` | `response_format` (format) | structured output + length control |
| `tools`, `tool_choice`, `parallel_tool_calls`, `max_tool_calls` | same (minus `max_tool_calls`) | |
| `stream`, `store`, `metadata` | `stream`, (no `store`), `metadata` | |
| `previous_response_id`, `conversation` | — | statefulness |
| `background` | — | async long jobs |
| `include` | — | request extras, e.g. `reasoning.encrypted_content` |
| `prompt_cache_key`, `prompt_cache_retention` | — | cache routing/retention |
| `service_tier`, `safety_identifier`, `truncation` | partial | |
| — | `frequency_penalty`, `presence_penalty`, `logit_bias`, `stop`, `seed`, `n`, `logprobs` | **Chat-Completions-only**; Responses drops most penalty knobs and `n` |

## 4. Structured outputs

Two mechanisms:

- **Structured Outputs (strict JSON Schema)** — guarantees schema conformance.
  - Responses: `text.format = {type:"json_schema", name, schema, strict:true}`
  - Chat Completions: `response_format = {type:"json_schema", json_schema:{name, schema, strict:true}}`
  - Strict rules: every object needs `additionalProperties:false`; all properties in
    `required`; optionals modeled as `["type","null"]`. Refusals surface in a dedicated
    `refusal` field.
- **JSON Mode (legacy)** — `type:"json_object"` guarantees *valid JSON* but not schema
  conformance. Superseded.

## 5. Tool / function calling

- **Custom function (Responses, flattened)**: `{type:"function", name, description,
  parameters, strict}`. Chat Completions nests under `{type:"function", function:{…}}`.
- **`tool_choice`**: `auto` · `none` · `required` · named `{type:"function", name}` ·
  `allowed_tools` (restrict to a subset).
- **Parallel**: `parallel_tool_calls` (default true).
- **Wire format**: Responses uses `function_call` items + `function_call_output`
  results keyed by `call_id`; Chat Completions uses `message.tool_calls[].{id,
  function:{name, arguments}}` + `{role:"tool", tool_call_id, content}`. `arguments` is
  a **JSON string** — always parse.
- **Built-in (server-side) tools (Responses only)**: `web_search`, `file_search`,
  `code_interpreter`, `computer_use_preview`, `image_generation`, **`mcp`** (remote MCP
  servers, with `require_approval`).

## 6. Streaming

`stream:true`.
- **Responses**: semantic **typed SSE events** — `response.created`,
  `response.output_text.delta`, `response.function_call_arguments.delta`,
  `response.refusal.delta`, tool-specific events, `response.completed`, `error`.
- **Chat Completions**: chunk deltas at `chunk.choices[0].delta.content`.

## 7. Reasoning models

- Configured via **`reasoning: {effort, summary}`**.
- `effort`: `none` · `minimal` · `low` · `medium` (flagship default) · `high` ·
  `xhigh`.
- **Reasoning tokens** bill as output tokens, occupy context, reported at
  `usage.output_tokens_details.reasoning_tokens`. Reserve large output headroom.
- **Summaries**: `reasoning.summary:"auto"` → a `reasoning` item with a `summary` array.
- **Encrypted reasoning**: for stateless (`store:false` / ZDR), add
  `"reasoning.encrypted_content"` to `include`; replay on the next request to preserve
  chain-of-thought.
- Reasoning models: GPT-5 family + o-series (o3, o4-mini).

## 8. Prompt caching

Automatic, no code change, **no extra fee**. Activates at ≥1024 tokens, longest-common-
prefix match. Heavy discount on cached input; reported as `cached_tokens`
(`usage.input_tokens_details.cached_tokens` / `prompt_tokens_details.cached_tokens`).
`prompt_cache_key` improves routing; `prompt_cache_retention:"24h"` extends retention.

## 9. Multimodal

- **Vision**: `input_image` via URL/base64/`file_id`; `detail` = `low|high|original|auto`.
- **Documents/PDF**: `input_file`.
- **Audio in chat models**: input `input_audio`; output via `modalities:["text","audio"]`
  + `audio:{voice, format}`.
- **TTS** (`/audio/speech`): `voice`, `response_format`, `speed`.
- **Transcription** (`/audio/transcriptions`): `whisper-1`, `gpt-4o-transcribe`.
- **Image gen** (`/images/generations` or in-loop `image_generation` tool).

## 10. Models (2026 positioning)

GPT-5.5 (flagship, 1M ctx) / 5.5-pro / 5.4 / 5.4-mini / 5.4-nano; o-series (o3,
o4-mini); GPT-4.1 / 4o (prior gen, FT targets); GPT Image 2; Realtime/audio family;
embeddings (`text-embedding-3-small` 1536, `-large` 3072, `dimensions` to shorten).

## 11. Auth, rate limits, errors

- Auth: `Authorization: Bearer`. Optional org/project headers.
- Limits: per **usage tier** (Free, Tier 1–5) on RPM + TPM; live headers
  `x-ratelimit-*`.
- Errors: `{error:{message, type, code, param}}`. Codes: 400, 401, 403, 404, 422, 429
  (rate **or** quota exhausted — distinguish before retrying), 500, 503.

## 12. Distinctive to OpenAI

- **Responses API as a server-side agentic loop** (chains built-in/custom tools in one
  request).
- **Stateful conversations** via `store:true` + `previous_response_id` or the
  Conversations API.
- **Background mode** (`background:true`) for long async jobs.
- **Hosted built-in tools** (web/file search, code interpreter, computer use, image gen,
  remote MCP).
- **Encrypted reasoning** for ZDR stateless multi-turn.
- **Realtime API** voice-to-voice.
- First-class **`verbosity`** + **`reasoning.effort`** instead of penalty knobs.

## 13. Mapping to `ocai`

- The split system message: OpenAI Chat Completions models the system prompt as a
  `role:"system"` message (matches the IR's `Message` directly); Responses hoists it to
  `instructions`. The IR's `system` role + adapter can normalize both.
- `tool_calls` map cleanly to `ToolCall(id, name, arguments)` — but note OpenAI's
  `arguments` is a serialized string the adapter must `json.loads`.
- Sampling knobs (`temperature`, `top_p`, penalties, `seed`, `n`) have **no canonical
  home** yet → `provider_options`.
- Reasoning effort/summaries, structured-output placement (`text.format` vs
  `response_format`), built-in tools, statefulness (`previous_response_id`) are
  high-loss / OpenAI-specific → `extensions` + a direct OpenAI↔OpenAI edge, or a
  lossy edge to canonical.
- `ChatResponse.raw` should retain the full `response`/`choices` payload for lossless
  escape.
