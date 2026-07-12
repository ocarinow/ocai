# Provider Feature Matrix

Side-by-side comparison of the four chat APIs `ocai` adapts. Use this to decide what
belongs in the canonical IR's typed core vs. its `provider_options` / `extensions`
escape hatches, and where high-fidelity direct edges in the conversion graph pay off.

Legend: ✅ native / first-class · ⚠️ partial or indirect · ❌ not available · — n/a

## Core request shape

| Aspect | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Primary endpoint | `/responses` (or `/chat/completions`) | `:generateContent` | `/v1/messages` | `/chat/completions` |
| Message container | `input` / `messages` | `contents` | `messages` | `messages` |
| Content unit | typed parts / string | `parts[]` | content blocks / string | chunks / string |
| Assistant role name | `assistant` | **`model`** | `assistant` | `assistant` |
| System prompt | `instructions` (Responses) / `system` msg | **`systemInstruction`** (no role) | **top-level `system`** (no role) | `system` **role** |
| Tool-result role | `tool` / `function_call_output` | `functionResponse` part (no role) | `tool_result` block in `user` msg | `tool` role |
| Stateful server-side | ✅ `previous_response_id` / Conversations | ⚠️ Live API / caches | ⚠️ Managed Agents | ✅ Conversations / Agents |

## Generation parameters

| Param | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| max output | `max_output_tokens` / `max_tokens` | `maxOutputTokens` | `max_tokens` (required) | `max_tokens` |
| temperature | ✅ (❌ on reasoning) | `temperature` | ⚠️ removed on Fable/4.7/4.8 | `temperature` |
| top_p / top_k | top_p ✅ / top_k ❌ | `topP` / `topK` | ⚠️ removed on Fable/4.7/4.8 | `top_p` only |
| seed | ✅ (CC only) | `seed` | ❌ | `random_seed` |
| stop sequences | `stop` (CC) | `stopSequences` | `stop_sequences` | `stop` |
| frequency/presence penalty | ✅ (CC) | ✅ | ❌ | ✅ |
| n (multiple) | ✅ (CC) | `candidateCount` | ❌ | `n` |
| safety / guardrail flag | moderation endpoint | `safetySettings` (per-category) | built-in (refusal) | `safe_prompt` |

## Structured output

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| JSON mode | ✅ `json_object` | `responseMimeType:json` | ⚠️ via schema | ✅ `json_object` |
| Strict JSON schema | ✅ `json_schema` strict | ✅ `responseSchema` / `responseJsonSchema` | ✅ `output_config.format` | ✅ `json_schema` strict |
| Enum/classification mode | via schema | ✅ `text/x.enum` | via schema/tool | via schema |
| SDK typed parse | ✅ | ✅ | ✅ `messages.parse` | ✅ `chat.parse` |

## Tool / function calling

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Custom functions | ✅ | ✅ `functionDeclarations` | ✅ | ✅ |
| Definition wrapper | flat (Resp) / nested (CC) | flat | flat (`input_schema`) | nested (`function`) |
| `arguments` type | **JSON string** | parsed object | parsed object | **JSON string** |
| tool_choice modes | auto/none/required/named/allowed | AUTO/ANY/VALIDATED/NONE | auto/any/tool/none | auto/any/none/named |
| parallel calls | ✅ | ✅ | ✅ | ✅ |
| strict schema tools | ✅ | ⚠️ | ✅ `strict` | ⚠️ |
| Built-in web search | ✅ tool | ✅ Google grounding | ✅ `web_search` (+citations) | ✅ connector (Agents) |
| Built-in code exec | ✅ code_interpreter | ✅ codeExecution | ✅ code_execution | ✅ code_interpreter (Agents) |
| Remote MCP | ✅ | ⚠️ | ✅ `mcp_servers` | ⚠️ |

## Reasoning / thinking

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Control knob | `reasoning.effort` | `thinkingBudget` / `thinkingLevel` | `thinking:adaptive` + `effort` | `reasoning_effort` |
| Budget vs effort | effort enum | token budget *or* level | effort enum (budget removed) | effort enum |
| Returns summary | ✅ `reasoning.summary` | ✅ `includeThoughts` | ✅ `display:summarized` | ✅ inline ThinkChunk |
| Raw CoT returned | ❌ (encrypted) | ❌ (signature) | ❌ | ⚠️ ThinkChunk |
| Cross-turn carry | encrypted_content | thoughtSignature | echo block unchanged | replay ThinkChunk |

## Prompt / context caching

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Automatic | ✅ (≥1024 tok, free) | ✅ implicit (2.5+) | ⚠️ top-level auto | ❌ |
| Explicit control | `prompt_cache_key` | `cachedContents` + ttl | `cache_control` breakpoints | ❌ |
| Reported as | `cached_tokens` | `cachedContentTokenCount` | `cache_read_input_tokens` | — |

## Multimodal & media

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Vision (image in) | ✅ | ✅ | ✅ (hi-res) | ✅ |
| Document/PDF in | ✅ | ✅ | ✅ (+citations) | ✅ + **OCR endpoint** |
| Audio in | ✅ | ✅ native | ❌ | ✅ Voxtral |
| Video in | ❌ | ✅ native | ❌ | ❌ |
| Image generation | ✅ | ✅ Imagen | ⚠️ via code exec | ✅ connector |
| TTS / STT | ✅ / ✅ | ✅ Live / native | ❌ | ✅ Voxtral |
| Realtime voice | ✅ Realtime API | ✅ Live API | ❌ | ⚠️ realtime transcription |

## Streaming

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| SSE | ✅ typed (Resp) / chunk (CC) | ✅ chunk | ✅ typed events | ✅ chunk + `[DONE]` |
| Bidirectional | ✅ Realtime WS | ✅ Live WS | ❌ | ⚠️ |

## Operational

| | OpenAI | Gemini | Anthropic | Mistral |
|---|---|---|---|---|
| Auth | Bearer key | API key / IAM | `x-api-key` / OAuth | Bearer key |
| Batch (50% off) | ✅ | ✅ | ✅ | ✅ |
| Context window (flagship) | 1M | 1M | 1M | up to 256K |
| Open weights | ❌ | ❌ | ❌ | ✅ (many) |
| Distinctive | Responses agentic loop, encrypted reasoning, Realtime | huge ctx, video/audio native, grounding, Live API | single endpoint, adaptive thinking, refusal stop reason, server tools | FIM, OCR, prefix, open weights, EU |

## What this implies for the canonical IR

**Safe to make first-class** (all four agree on the *idea*, differ only in naming —
low conversion loss): role-tagged messages, text content, a system instruction, tool
declarations + tool calls/results, max-output limit, temperature/top_p, stop sequences,
streaming, JSON-schema structured output, token usage.

**Keep in `provider_options`** (sampling/limit knobs with no single canonical home):
seed naming, penalties, `n`/`candidateCount`, `safe_prompt`/`safetySettings`,
`reasoning_effort`/`thinkingBudget`/`effort`.

**Keep in `extensions` + favor direct high-fidelity edges** (provider-specific, high
loss to normalize): reasoning summaries & cross-turn carry, prompt caching directives,
server-side/built-in tools, multimodal parts (image/audio/video/document blocks),
statefulness (`previous_response_id`/Conversations), Mistral prefix, Anthropic
`stop_reason:refusal`, grounding metadata.

**Out of scope for the `ChatModel` port** (separate ports): embeddings
(`EmbeddingModel`), OCR, image/audio generation, realtime bidi voice, vector/RAG
stores (`VectorStore`), tracing (`Tracer`).
