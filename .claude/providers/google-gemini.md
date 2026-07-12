# Google Gemini API — Capabilities & Features

Base: `https://generativelanguage.googleapis.com`, version `v1beta` (primary) / `v1`.
Two deployments share one SDK (`google-genai`): **AI Studio / Gemini Developer API**
(API key) and **Vertex AI** (IAM/ADC, enterprise). Convention: **REST is camelCase**
(`maxOutputTokens`), the **Python SDK is snake_case** (`max_output_tokens`), the JS SDK
is camelCase.

## 1. API surface / endpoints

| Capability | Method |
|---|---|
| Generate | `POST /v1beta/models/{model}:generateContent` |
| Stream (SSE) | `:streamGenerateContent` (`?alt=sse`) |
| Live API (bidi) | `BidiGenerateContent` over WebSocket |
| Batch | `:batchGenerateContent` (50% discount, ~24h) |
| Embeddings | `:embedContent`, `:batchEmbedContents` |
| Count tokens | `:countTokens` |
| Files | `POST /upload/v1beta/files` (≤2GB, 48h retention, free) |
| Caching | `POST /v1beta/cachedContents` |
| Image / Video / Music | Imagen / Veo / Lyria via `:predict` / `:predictLongRunning` |
| Tuning | `tunedModels` |

## 2. Request & response model

**Request body** (to `generateContent`):
- **`contents`** (required) — array of `Content`, each with `role` (`"user"` |
  `"model"`) and **`parts[]`**.
- **`systemInstruction`** — a `Content` shaping behavior outside the turn list.
- `tools`, `toolConfig`, `safetySettings`, `generationConfig`, `cachedContent`.

**Part types** (a `Part` is exactly one of):
- `text`
- `inlineData` `{mimeType, data}` (base64, small media)
- `fileData` `{mimeType, fileUri}` (Files API reference)
- `functionCall` `{name, args, id}` (model-emitted)
- `functionResponse` `{name, response, id}` (you send back; `id` must match)
- `executableCode` / `codeExecutionResult` (code execution)
- `thought` (boolean flag marking a thought-summary part); `thoughtSignature` (opaque
  reasoning carried across turns)

Natively multimodal input: text, images, audio, **video**, PDF — via `inlineData` /
`fileData`.

**Response** (`GenerateContentResponse`): `candidates[]` each with `content` (parts),
`finishReason` (`STOP`, `MAX_TOKENS`, `SAFETY`, `RECITATION`, …), `safetyRatings`,
`groundingMetadata`; plus `promptFeedback`, `usageMetadata` (`promptTokenCount`,
`candidatesTokenCount`, `cachedContentTokenCount`, `thoughtsTokenCount`),
`modelVersion`, `responseId`.

## 3. Generation config (`generationConfig`, camelCase)

`temperature` (0–2) · `topP` · `topK` · `maxOutputTokens` · `stopSequences[]` ·
`candidateCount` · `responseMimeType` (`text/plain` | `application/json` | `text/x.enum`)
· `responseSchema` / `responseJsonSchema` · `responseModalities[]` (`TEXT`/`IMAGE`/`AUDIO`)
· `seed` · `presencePenalty` · `frequencyPenalty` · `responseLogprobs` / `logprobs` ·
`thinkingConfig` · `mediaResolution`.

## 4. Structured output

Set `responseMimeType:"application/json"` + `responseSchema` (OpenAPI-subset Schema) or
`responseJsonSchema` (standard JSON Schema). Schema supports types, `properties`,
`required`, `enum`, `format`, `anyOf`, `$ref` (recursive), `prefixItems` (tuples),
`propertyOrdering`. **Enum mode**: `responseMimeType:"text/x.enum"` with a string-enum
schema — ideal for classification. Output is constrained-decoded to valid JSON.

## 5. Function calling / tools

- **`tools[].functionDeclarations[]`**: `{name, description, parameters}` (OpenAPI-subset
  schema).
- **`toolConfig.functionCallingConfig.mode`**: `AUTO` (default) · `ANY` (force a call) ·
  `VALIDATED` · `NONE`; plus `allowedFunctionNames[]`.
- Parallel calling and compositional/sequential calling (mapped by `id`).
- **Built-in tools**: `googleSearch` (grounding; older `googleSearchRetrieval` with
  `dynamicThreshold`), `codeExecution` (sandboxed Python), `urlContext`, Google Maps
  grounding, File Search (managed RAG). Tools combine freely.

## 6. Thinking / reasoning

`generationConfig.thinkingConfig`:
- `thinkingBudget` (int) — Gemini 2.5 reasoning-token budget (2.5 Pro 128–32768, can't
  disable; 2.5 Flash 0–24576, `0` disables; `-1` = dynamic).
- `includeThoughts` (bool) — return **thought summaries** (parts flagged
  `part.thought=true`).
- `thinkingLevel` — Gemini 3 replaces numeric budget with discrete levels
  (`minimal`/`low`/`high`).
- `thoughtSignature` — encrypted reasoning carried across turns (function-calling
  continuity).
- Thinking tokens billed; reported at `usageMetadata.thoughtsTokenCount`.

## 7. Context caching

- **Explicit**: `POST /v1beta/cachedContents` (`model`, `contents`, `systemInstruction`,
  `tools`, `ttl`/`expireTime`); reference via `cachedContent:"cachedContents/{id}"`.
  Reduced billing; reported as `cachedContentTokenCount`. Minimum cacheable tokens
  ~2048–4096 (model-dependent).
- **Implicit**: automatic on Gemini 2.5+; savings passed through on hits.

## 8. Safety settings

`safetySettings[]` of `{category, threshold}`. Categories: `HARASSMENT`, `HATE_SPEECH`,
`SEXUALLY_EXPLICIT`, `DANGEROUS_CONTENT`, `CIVIC_INTEGRITY`. Thresholds: `BLOCK_NONE`,
`BLOCK_ONLY_HIGH`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_LOW_AND_ABOVE`, `OFF`. `safetyRatings`
report `category`/`probability`/`blocked`; blocks surface in `promptFeedback.blockReason`
or `finishReason:SAFETY`. **No other mainstream provider exposes per-category safety
tuning like this.**

## 9. Streaming

- **`streamGenerateContent`** — SSE of incremental `GenerateContentResponse` chunks.
- **Live API** — stateful WebSocket (`BidiGenerateContent`): `setup`, `clientContent`,
  `realtimeInput`, `serverContent`, `toolCall`. Features: input/output audio
  transcription, **Voice Activity Detection**, **barge-in/interruption**, session
  resumption, native audio out (16kHz in / 24kHz out).

## 10. Models (mid-2026)

Gemini 3 series (3.1 Pro, 3.5 Flash, 3 Flash, 3.1 Flash-Lite; `thinkingLevel`, 1M ctx) ·
Gemini 2.5 (Pro / Flash / Flash-Lite; `thinkingBudget`) · embeddings
(`gemini-embedding-001`, Matryoshka dims 128–3072) · Imagen 4 / Nano Banana (image) ·
Veo 3.1 (video) · Lyria 3 (music). SynthID watermarking on generated media.

## 11. Auth, tokens, errors

- Auth: API key via `x-goog-api-key` header or `?key=` (AI Studio); IAM/ADC on Vertex.
- `countTokens` for pre-flight; rough rates: ~4 chars/token, image 258 tokens, video
  ~263 tok/s, audio ~32 tok/s. Flagship context window **1,000,000 tokens**.
- Rate limits: per-project RPM / TPM / RPD, tiered by spend.
- Errors: Google envelope `{error:{code, message, status, details}}` (400
  INVALID_ARGUMENT, 403 PERMISSION_DENIED, 429 RESOURCE_EXHAUSTED, 500, 503).

## 12. Distinctive to Gemini

- **1M-token context** across flagship models (largest mainstream).
- **Natively multimodal incl. video and audio** with explicit token rates.
- **Live API**: real-time bidi voice/vision with VAD + barge-in + native audio out.
- **Built-in code execution** + Google Search / Maps / URL grounding with structured
  `groundingMetadata` citations.
- **Tunable thinking** (`thinkingBudget`/`thinkingLevel`) with returnable summaries.
- **Per-category safety controls**.
- First-party image/video/music in the same API family.
- Dual deploy (AI Studio key vs Vertex IAM) under one SDK.

## 13. Mapping to `ocai`

- **Role mismatch**: Gemini uses `"model"` (not `"assistant"`) and has **no system
  role** — system prompt is the separate `systemInstruction`. The adapter must translate
  `assistant ↔ model` and hoist a `system` message into `systemInstruction`. This is a
  named lossy/structural edge.
- **Parts vs flat content**: the IR's `Message.content: str | tool_calls` is flatter
  than Gemini's `parts[]`. Multimodal parts (`inlineData`/`fileData`/video) have no
  canonical home → `extensions` (or a richer future IR content model).
- `functionCall`/`functionResponse` map to `ToolCall`, but Gemini keys responses by
  matching `id`/`name` and has no separate `tool` role — the adapter reconstructs turns.
- Sampling, `thinkingConfig`, `safetySettings`, grounding tools → `provider_options` /
  `extensions`. Token accounting maps to `Usage` (note `thoughtsTokenCount` is extra).
