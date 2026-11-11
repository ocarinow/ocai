# Mistral AI API — Capabilities & Features

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Base: `https://api.mistral.ai/v1`. Auth: `Authorization: Bearer <key>` (no URL-param
keys). Platform branded **La Plateforme / Mistral Studio**. EU-hosted (France) — a
data-residency differentiator. The chat surface is broadly **OpenAI-Chat-Completions
shaped**, with several distinctive additions (FIM, OCR, prefix messages, open weights).

## 1. API surface / endpoints

| Capability | Method |
|---|---|
| Chat completions | `POST /v1/chat/completions` |
| FIM completions | `POST /v1/fim/completions` (fill-in-the-middle, Codestral) |
| Embeddings | `POST /v1/embeddings` |
| **OCR / Document AI** | `POST /v1/ocr` (distinctive) |
| Moderation / classifiers | `POST /v1/moderations` |
| Files | `/v1/files` |
| Fine-tuning | `/v1/fine_tuning/jobs` |
| Batch | `/v1/batch/jobs` (50% discount) |
| Audio | `/v1/audio/transcriptions`, `/audio/speech`, `/audio/voices` (Voxtral) |
| Agents (beta) | `/v1/agents`, `/v1/conversations` (stateful, connectors, handoffs) |
| Libraries (beta) | `/v1/libraries` (document RAG store) |

## 2. Request & response model (chat)

- **`messages`** array; roles `system` / `user` / `assistant` / `tool` (the last carries
  `tool_call_id` + optional `name`).
- **Multimodal content**: `content` is a string or array of chunks — `{type:"text"}`,
  `{type:"image_url"}` (vision), `{type:"document_url"}` (PDF in chat). Reasoning models
  also use `{type:"thinking"}` (ThinkChunk) and `{type:"text"}` (TextChunk).
- **Prefix / prefill**: set `"prefix": true` on a trailing **assistant** message — its
  content is prepended to the model's output, forcing the response to start with a given
  string (format locking, language locking). Distinctive to Mistral.
- **Response**: OpenAI-shaped — `choices[].message`, `finish_reason` (`stop`, `length`,
  `tool_calls`, `model_length`, `error`), `usage` (`prompt_tokens`,
  `completion_tokens`, `total_tokens`).

## 3. Generation parameters

`model` · `messages` · `temperature` · `top_p` · `max_tokens` · `stop` · **`random_seed`**
(Mistral's name for seed) · `frequency_penalty` · `presence_penalty` · `n` ·
**`safe_prompt`** (boolean guardrail injection) · `stream` · `prediction` (predicted
outputs / speculative edits) · `response_format` · `tools` / `tool_choice` /
`parallel_tool_calls` · `reasoning_effort`.

## 4. Structured outputs

`response_format`:
- **JSON mode** — `{type:"json_object"}` (valid JSON, no schema enforcement).
- **Custom Structured Outputs** — `{type:"json_schema", json_schema:{name, schema,
  strict:true}}`; SDKs accept a Pydantic/Zod model directly and `client.chat.parse(...)`
  returns a typed object.

## 5. Tool / function calling

- **`tools`**: `{type:"function", function:{name, description, parameters}}` (OpenAI-
  shaped).
- **`tool_choice`**: `auto` · `any`/`required` · `none` · named function.
- **`parallel_tool_calls`** (default true).
- Response tool calls: `{id, type:"function", function:{name, arguments}}` —
  `arguments` is a **JSON string**; feed results back as a `tool`-role message with
  matching `tool_call_id`.
- **Built-in connectors (Agents API only)**: `web_search` / `web_search_premium`,
  `code_interpreter`, `image_generation`, `document_library` (RAG).

## 6. Streaming

`stream:true` → SSE of `chat.completion.chunk` with `choices[].delta`, terminated by
`data: [DONE]`. For reasoning models, `delta.content` shifts shape mid-stream (chunk
array during thinking → string during the answer).

## 7. Reasoning models (Magistral)

Reasoning line is **Magistral** (`magistral-small/medium-latest`); also available on
hybrid models via **`reasoning_effort`** (`"high"` returns a ThinkChunk before the
TextChunk; `"none"` suppresses it). Reasoning is exposed **inline as content chunks**,
not a separate top-level field. Multi-turn: replay the assistant message *including the
ThinkChunk*.

## 8. OCR / Document AI (distinctive)

`POST /v1/ocr`, model `mistral-ocr-latest`. Request: `document`
(`{type:"document_url"|"image_url"}`, supports PDF/PPTX/DOCX/images), `pages`,
`include_image_base64`, `table_format` (`markdown`/`html`), `extract_header/footer`,
`confidence_scores_granularity`, schema-driven `document_annotation` / `bbox_annotation`.
Response: per-page `markdown`, `images`, `tables`, `hyperlinks`, `confidence_scores`,
`dimensions`. Layout-preserving Markdown output with bounding boxes — most LLM providers
have nothing equivalent.

## 9. Agents & Conversations API

- **`/v1/agents`** — persistent agent definitions (`model`, `instructions`, `tools`
  connector list, `completion_args`) → `agent_id`.
- **`/v1/conversations`** — **stateful** runs from an `agent_id`; server maintains
  state (no resending history). Outputs are typed entries (`message.output` with
  inline `tool_reference` citations, `tool.execution`).
- **Handoffs** — agents delegate to other agents (multi-agent orchestration). A
  **Workflows** layer adds scheduling/deployment.

## 10. Models (2026 positioning)

Generalist (mostly **open-weight Apache 2.0**, multimodal): Mistral Large 3
(`mistral-large-latest`), Medium 3.5 (`mistral-medium-3-5`), Small 4
(`mistral-small-latest`), Ministral 3 (edge). Reasoning: Magistral. Code: Codestral
(FIM), Devstral 2, Codestral Embed. Embeddings: `mistral-embed`. OCR:
`mistral-ocr-latest`. Moderation: `mistral-moderation-latest`. Audio: Voxtral
(transcription + TTS with zero-shot voice cloning). Legacy multimodal: Pixtral.

## 11. Auth, limits, errors

- Auth: `Authorization: Bearer` only.
- Errors: standard HTTP (400/401/422/429/5xx), JSON `message`/`type`/`code`; `429`
  carries `Retry-After`.
- Limits: per-tier requests/sec + tokens/minute (free ~5 RPS; paid from ~50 RPS). SDK
  `max_retries` (default 0 — set it).

## 12. Distinctive to Mistral

- **FIM / Codestral** — dedicated `/v1/fim/completions` with `prompt` + `suffix`.
- **Mistral OCR** — first-class layout-preserving document AI with annotations.
- **Prefix / prefill assistant messages** (`prefix:true`).
- **Open-weight frontier models** (Apache 2.0) across generalist/reasoning/code/audio.
- **EU sovereignty** (GDPR-aligned hosting).
- **Agents API** with built-in connectors + handoffs + Workflows.
- **`safe_prompt`** flag and **`random_seed`** naming.
- **Voxtral** open-weight transcription + TTS with voice cloning.

## 13. Mapping to `ocai`

- Closest to the IR of the four — OpenAI-Chat-Completions shape maps almost directly to
  `Message(role, content, tool_calls)`. The `system` role exists natively.
- `tool_calls.arguments` is a **JSON string** the adapter must parse into
  `ToolCall.arguments`.
- The **prefix** flag, `reasoning_effort`, `safe_prompt`, `random_seed`,
  `prediction`, connectors → `provider_options` / `extensions`.
- Reasoning ThinkChunks and multimodal content chunks (image/document) exceed the IR's
  flat `content: str` → `extensions`. OCR is a separate non-chat capability — out of
  scope for the `ChatModel` port (a candidate future port).
- Low conversion loss to/from OpenAI formats — a high-fidelity **direct edge** in the
  conversion graph is justified.
