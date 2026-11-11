# Hosting, aggregators, and local servers

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

> Currency: researched 2026-11-10 against each vendor's official docs or
> official source (vLLM/SGLang/Ollama/llama.cpp/TGI protocol files on GitHub).
> These hosts move monthly — field renames (`reasoning_content` → `reasoning`),
> removed params (vLLM `guided_*`), new routes (`/v1/responses`, `/v1/messages`)
> are the norm; unconfirmed facts are marked *unverified*. Enterprise clouds:
> [amazon-bedrock.md](../providers/amazon-bedrock.md),
> [azure-openai.md](../providers/azure-openai.md),
> [google-vertex.md](../providers/google-vertex.md).

**Thesis:** nearly every aggregator and local server speaks
`openai/chat_completions` (increasingly also `anthropic/messages`), so ocai
reaches them with the **existing codecs** through a `Host` value and
`DialectTraits` — never a plugin per host. The long tail (auth header, URL
prefix, id grammar, ignored params, usage/cost placement, reasoning field,
error envelope) is host *data*: profile facts, censused extensions, error maps.
Target: `ocai.chat.model("openai/meta-llama/Llama-3.3-70B", host=Custom("http://vllm:8000"))`.

## Comparison table

| Host | Base URL | Auth | Model id grammar | `/responses` | `/embeddings` | `/v1/messages` | Reasoning field | Stream usage | Rate-limit headers | Cost in body |
|---|---|---|---|---|---|---|---|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | Bearer | `vendor/model[:variant…]` | yes | yes | path *unverified* | `reasoning` + `reasoning_details[]` | always, final chunk | 429-only `X-RateLimit-*` | `usage.cost` |
| Together | `https://api.together.ai/v1` | Bearer | `org/Model-Name` | yes | yes | no | `reasoning` / `reasoning_content` | final usage-only chunk | none | no |
| Fireworks | `https://api.fireworks.ai/inference/v1` | Bearer | `accounts/fireworks/models/<slug>` | yes (stateful) | yes | exists, not read | `reasoning_content` | final chunk (default) | `X-Ratelimit-Limit-Tokens-*` | no |
| Groq | `https://api.groq.com/openai/v1` | Bearer | short / `org/model` | beta, stateless | no | no | `reasoning` / `<think>` | `stream_options` undocumented | full `x-ratelimit-*` + `retry-after` | no |
| DeepInfra | `https://api.deepinfra.com/v1/openai` | Bearer | `org/Model`, `:VERSION`, `deploy_id:` | *unverified* | yes | no | *unverified* | `include_usage` | none | `usage.estimated_cost` |
| HF Inference Providers | `https://router.huggingface.co/v1` | Bearer `hf_…` | `org/model[:policy\|:provider]` | beta | no (task routes) | no | provider-dependent | `include_usage` | none | no |
| Cloudflare Workers AI | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/v1` | Bearer CF token | `@cf/<author>/<model>` | gpt-oss, no stream | yes | gateway only | *unverified* | *unverified* | none | no (Neurons) |
| vLLM | `http://localhost:8000/v1` | `--api-key` Bearer (`/v1` only) | `--served-model-name` / HF id | yes | yes | yes + `count_tokens` | `reasoning` (renamed) | `include_usage`, `continuous_usage_stats` | none | no |
| Ollama | `http://localhost:11434/v1` (native `/api`) | none local; Bearer cloud | `name:tag`, `name:cloud` | yes (0.13.3+) | yes | yes | `reasoning` | `include_usage` | none | no |
| llama.cpp server | `http://127.0.0.1:9931/v1` (README default) | `--api-key` Bearer | path or `--alias` | yes | yes | yes + `count_tokens` | `reasoning_content` | SSE; `timings` | none | no |
| LM Studio | `http://localhost:1234/v1` (native `/api/v1`) | opt-in Bearer tokens | model key | yes (0.3.29) | yes | yes (0.4.1) | `reasoning` / `reasoning_content` | `include_usage` | none | no |
| SGLang | `http://127.0.0.1:30000/v1` | `--api-key` Bearer | `--served-model-name` / HF id | yes | yes | yes + `count_tokens` | `reasoning_content` | `include_usage`, `continuous_usage_stats` | none | no |
| TGI (archived) | `http://localhost:3000/v1` (Docker `8080`) | `--api-key` Bearer | `tgi` (other = LoRA `adapter_id`) | no | no | no | none | `include_usage` | none (`x-*` timings) | no |

## Hosted aggregators

### OpenRouter

- **Surface/ids**: `/chat/completions`, `/responses`, `/completions`,
  `/embeddings`, `GET /models`, `GET /generation?id=`, `GET /key`. Bearer plus
  optional `HTTP-Referer`, `X-OpenRouter-Title`, `X-OpenRouter-Metadata: enabled`.
  Ids `vendor/model` + catalog variants (`:free`, `:batch`) and stackable
  routing variants (`:nitro`, `:floor`, `:exacto`).
- **Divergences**: SSE keep-alive comments `: OPENROUTER PROCESSING`; **every
  stream ends with an extra usage chunk** whose empty delta *repeats*
  `finish_reason`; `stream_options.include_usage` is a no-op. Finish reasons
  normalized (`tool_calls|stop|length|content_filter|error`), raw value in
  `native_finish_reason`. Usage adds `cost`, `cost_details{…}`, `is_byok`,
  `prompt_tokens_details.cache_write_tokens`, `completion_tokens_details.reasoning_tokens`.
  Reasoning: request `reasoning{effort, max_tokens, enabled, exclude}`;
  response `message.reasoning` + `reasoning_details[]` (`reasoning.summary|
  encrypted|text`, `format`, `signature`), streamed as `delta.reasoning_details[]`.
- **Extensions**: `provider{order[], allow_fallbacks, require_parameters,
  data_collection, zdr, only[], ignore[], quantizations[], sort, max_price}`;
  `models[]` fallback; `route` **deprecated**; `transforms: ["middle-out"]`
  *unverified in current docs* (now the `context-compression` plugin);
  `plugins[]`; response `provider`, `openrouter_metadata{strategy, attempts[]}`.
- **Errors**: `{error: {code: <int>, message, metadata?}}`, status =
  `error.code`: 402 credits, 403 moderation (`metadata.reasons[]`), 404, 408,
  429, 502 model down, 503 no provider. **Mid-stream errors are HTTP 200**
  chunks with top-level `error` and `finish_reason: "error"`. `X-RateLimit-*`
  only on 429s, plus `Retry-After`.

### Together AI

- **Surface**: chat, completions, embeddings, images, audio, models,
  `/responses`, `/rerank`, `/tci/execute`; no OpenAI `/batches`.
  `https://us-api.together.ai/v1` at 1.25×.
- **Divergences**: streamed `delta.tool_calls[]` with `index`; final
  usage-only chunk, `stream_options` undocumented. `reasoning{enabled}`,
  `reasoning_effort` (out-of-range accepted silently); response has **both**
  `message.reasoning` and `message.reasoning_content`. `logprobs` is an
  **integer 0–20** returning `{token_ids[], tokens[], token_logprobs[]}`;
  `finish_reason` ∈ `stop|eos|length|tool_calls|function_call`; `service_tier`,
  `store`, `metadata` accepted-but-ignored; `cached_tokens` sometimes flat.
- **Extensions/errors**: `repetition_penalty`, `min_p`, `top_k`, `safety_model`,
  `echo`, `context_length_exceeded_behavior` (**default `error` → 400**).
  OpenAI envelope; 402 spend cut-off, 413, 429 (no headers), 503, 504, 524, 529.

### Fireworks AI

- **Surface**: chat, completions, embeddings, `/rerank`, `/responses`
  (stateful; `store` default true; tools `function|mcp|sse|python`). Headers
  `x-session-affinity`, `x-prompt-cache-isolation-key`; response
  `fireworks-prompt-tokens`, `fireworks-cached-prompt-tokens`.
- **Divergences**: `tool_choice` adds `any`/`{allowed_tools}`; usage in the
  final chunk **by default**; `stream_options{include_usage, buffer_tokens,
  buffer_ms, buffer_mode}`. `reasoning_effort` (level|bool|int),
  `reasoning_history`, `thinking{type, budget_tokens}`; response
  `reasoning_content` (some models leave `<think>` in `content`); `json_schema`
  disables reasoning. `response_format.type` adds `grammar` (GBNF). `max_tokens`
  auto-lowered unless `context_length_exceeded_behavior: "error"` (default
  `truncate` — opposite of Together).
- **Extensions/errors**: `top_k`, `min_p`, `typical_p`, `repetition_penalty`,
  `mirostat_*`, `prompt_truncate_len`, `raw_output`, `prompt_cache_key`,
  `perf_metrics_in_response`; `prompt_cache_max_len` *unverified*.
  `X-Ratelimit-Limit-Tokens-Prompt|Uncached-Prompt|Generated|Cache-Adjusted-Prompt`;
  `Retry-After` on 429; 402, 412, 503 load shedding, 520; 422 FastAPI
  `detail[]`; general error body *unverified*.

### Groq

- **Surface**: chat, `/responses` (beta, stateless), audio, models,
  `/batches`, `/files`; no completions/embeddings/rerank.
- **Divergences**: **400 on** `logprobs`, `top_logprobs`, `logit_bias`,
  `messages[].name`, `n != 1`; `temperature: 0` → `1e-8`; structured outputs
  incompatible with streaming and tools. `reasoning_format: parsed|raw|hidden`
  (parsed → `message.reasoning`; raw → `<think>` in content; raw + JSON/tools
  → 400), `reasoning_effort`, `include_reasoning`. Usage adds `queue_time,
  prompt_time, completion_time, total_time`; `x_groq{id}` on unary responses
  (`x_groq.usage` in streams *unverified*). `max_tokens` deprecated.
- **Extensions/errors**: `service_tier: auto|on_demand|flex|performance`;
  batch at 50%; `Groq-Beta: inference-metrics`. Every response carries
  `x-ratelimit-limit-requests` (RPD), `x-ratelimit-limit-tokens` (TPM),
  `x-ratelimit-remaining-*`, `x-ratelimit-reset-*` (durations like `2m59.56s`);
  `retry-after` on 429; 413, 422, **498** flex capacity, **499** cancelled.

### DeepInfra

- **Surface**: `/v1/openai/{chat/completions, embeddings, images}`; native
  `/v1/inference/{model}`; other sub-paths *unverified*. Bodies may be gzip.
- **Divergences**: `response_format` adds `regex`; `reasoning_effort` /
  `reasoning{effort, enabled}`; response reasoning field *unverified*; no
  `max_completion_tokens`/`logit_bias`/`top_logprobs`. Usage adds
  **`estimated_cost`** (USD).
- **Extensions/errors**: `min_p`, `top_k`, `repetition_penalty`, `cache_salt`,
  `chat_template_kwargs`, `service_tier: default|priority|flex`, `fail_fast`
  (immediate 429, unbilled), `models[]` fallback; `x-deepinfra-source`
  *unverified*. Concurrency-limited, no headers; 429 `code: "engine_overloaded"`;
  422 FastAPI; 400 context exceeded.

### Hugging Face Inference Providers

- **Surface/ids**: `/chat/completions`, `/responses` (beta), `GET /models`
  (per-provider `pricing`, `supports_tools`, `status`); non-chat tasks use
  task routes. Bearer `hf_…`; `X-HF-Bill-To: <org>`. Ids
  `org/model[:fastest|:cheapest|:preferred|:<provider>]` (`:groq`, `:together`, …).
- **Divergences/errors**: the router **proxies to the chosen provider**, so
  tool, reasoning, and usage nuances are provider-dependent; spec lists
  `logprobs` (bool), `top_logprobs` (0–5), `tool_prompt`; no `n`, `logit_bias`,
  `parallel_tool_calls`. Provider 429s passed through; 402/503 *unverified*.

### Cloudflare Workers AI (and AI Gateway)

- **Surface**: `…/accounts/{id}/ai/v1/{chat/completions, embeddings,
  responses}`; native `…/ai/run/{model}` wrapped in `{result, success,
  errors[], messages[]}`. AI Gateway `https://gateway.ai.cloudflare.com/v1/{account}/{gateway}/{provider}/…`
  with `cf-aig-authorization`, `cf-aig-gateway-id`, `cf-aig-cache-*`,
  `cf-aig-max-attempts`, `cf-aig-custom-cost`; response `cf-aig-cache-status`.
- **Divergences/errors**: native function calling returns `tool_calls[{name,
  arguments: {…}}]` — **parsed, no `id`/`function` wrapper**; OpenAI-route
  tool shape, `tool_choice`, `logprobs`, `seed`, `n`, stream usage *unverified*.
  `options.rejectIfBusy` fails fast (429/`3040`). Neurons billing is **never
  reported in the response**. Envelope codes `3036` (429 free Neurons), `3040`
  (429 capacity), `3042` (404 model), `5028` (410), `5035` (403), `3006` (413).

## Local and self-hosted servers

### vLLM

- **Surface**: `--api-key`/`VLLM_API_KEY` guards **only** `/v1`, `/v2`,
  `/inference`, `/cohere`. OpenAI chat/completions/responses/embeddings/
  audio/realtime; Anthropic `/v1/messages` + `count_tokens`; `/v1/rerank`,
  `/score`, `/classify`, `/tokenize`, `/detokenize`, `/health`, `/metrics`.
  `--served-model-name` (default the HF id).
- **Divergences**: tools need `--enable-auto-tool-choice --tool-call-parser
  <hermes|mistral|llama3_json|deepseek_v3|qwen3_xml|glm45|kimi_k2|openai|…>`
  (named/required without a parser → 400); **streamed tool calls are emitted
  whole once parsed**; unparseable calls dropped. `--reasoning-parser
  <deepseek_r1|qwen3|gemma4|…>` → field **`reasoning`** on `message`/`delta`
  ("`reasoning` used to be called `reasoning_content`"; incoming
  `reasoning_content` is renamed); `include_reasoning`, `reasoning_effort`,
  `thinking_token_budget`, `chat_template_kwargs: {"enable_thinking": false}`.
  Structured outputs apply from the first token (no reasoning). `max_tokens`
  deprecated (both accepted); `user`, `image_url.detail` ignored;
  `finish_reason` is a free string. `prompt_tokens_details{cached_tokens, …}`
  only with `--enable-prompt-tokens-details`; `X-Request-Id` only with
  `--enable-request-id-headers`; `X-Vllm-Priority` request header.
- **Extensions/errors** (`extra_body`): `top_k`, `min_p`, `repetition_penalty`,
  `length_penalty`, `use_beam_search`, `stop_token_ids`, `ignore_eos`,
  `min_tokens`, `truncate_prompt_tokens`, `prompt_logprobs`, `echo`,
  `continue_final_message`, `chat_template_kwargs`, `priority`, `cache_salt`,
  `kv_transfer_params`, `vllm_xargs`. **`guided_*` removed in v0.12.0** →
  `structured_outputs: {json|regex|choice|grammar|structural_tag}`, backend
  `auto|xgrammar|guidance`. Errors `{"error": {"message", "type", "param",
  "code": <int>}}` (flat `{"object": "error"}` is gone).

### Ollama

- **Surface**: local ignores auth; cloud `https://ollama.com/{api|v1}` with
  Bearer. Ids `name:tag`; `gemma4:cloud` via a local server (`-cloud` suffix
  *unverified*). OpenAI chat/completions/embeddings/models/responses
  (0.13.3+)/audio; Anthropic `/v1/messages`; native `/api/chat`,
  `/api/generate`, `/api/embed`, `/api/tags`, `/api/show`, `/api/ps`, `/api/pull`.
- **OpenAI-mode divergences**: **unsupported** image URLs (rejected),
  `tool_choice`, `logit_bias`, `user`, `n` (`logprobs` in source, *version
  unverified*). Reasoning field **`reasoning`**; effort `none`→off,
  `minimal`→`low`, `xhigh`→`max`. `json_object` → native `format: "json"`;
  other `response_format` types ignored. `finish_reason` `stop|tool_calls`
  (`length` *unverified*); non-string `stop` entries silently dropped.
- **Native/errors**: `/api/chat {model, messages[{role, content, thinking,
  images, tool_calls}], tools, format, options{seed, temperature, top_k, top_p,
  min_p, num_ctx, num_predict, repeat_penalty, …}, stream, keep_alive, think}`;
  **NDJSON** streaming (`done: true` last; final `{"error": …}` line on
  failure); usage `prompt_eval_count`, `eval_count`, `*_duration` (ns).
  Errors: native `{"error": "<string>"}`; OpenAI routes `{"error": {"message",
  "type": invalid_request_error|not_found_error|api_error}}`.

### llama.cpp `llama-server`

- **Surface**: `--port 9931` (README default; Docker examples 8080);
  `--api-key`/`LLAMA_API_KEY`; id = path or `--alias`. OpenAI chat/completions/
  embeddings/models/responses/audio; Anthropic `/v1/messages` + `count_tokens`;
  native `/completion`, `/infill`, `/tokenize`, `/reranking`, `/slots`, `/props`.
- **Divergences**: tools via `--jinja` (default on); `--reasoning-format
  none|deepseek|deepseek-legacy` → **`reasoning_content`**; per-request
  `reasoning_format`, `reasoning_effort: "none"`, `--reasoning-budget`;
  native `stop_type` ∈ `none|eos|limit|word` (OpenAI mapping *unverified*).
  Usage: `prompt_tokens_details.cached_tokens` + `timings{cache_n, prompt_n,
  prompt_ms, predicted_n, predicted_per_second}`.
- **Extensions/errors**: `n_predict`, `n_keep`, `dynatemp_*`, `top_k`, `min_p`,
  `dry_*`, `xtc_*`, `mirostat*`, `grammar`, `json_schema`, `n_probs`,
  `id_slot`, `cache_prompt`, `samplers`. `{"error": {"code", "message",
  "type"}}` with `authentication_error` 401, `invalid_request_error` 400,
  `not_supported_error` 501, `unavailable_error` 503 ("Loading model").

### LM Studio

- **Surface**: auth off by default; opt-in `Authorization: Bearer
  $LM_API_TOKEN` (0.4.0+; `/v1` coverage *unverified*). OpenAI models/chat/
  completions/embeddings/responses (0.3.29); Anthropic `/v1/messages` (0.4.1);
  native `/api/v1/chat`, `/api/v1/models[/load|unload]` (v0 legacy).
- **Divergences**: `tool_choice` `none|auto|required` (named *unverified*);
  unparseable tool calls fall back into `content`. Reasoning:
  `reasoning_content` (0.3.9, opt-in) **and** `message.reasoning` (0.3.23,
  gpt-oss); `reasoning_effort`/`reasoning_tokens` (0.4.8) — read both.
  `json_schema` confirmed; `json_object`, `logprobs`, `n`, `seed` *unverified*.
  `ttl` (seconds) accepted in the body. Native `stats{input_tokens,
  total_output_tokens, reasoning_output_tokens, tokens_per_second}`; native
  errors `{type, message}`; OpenAI-route error JSON *unverified*.

### SGLang

- **Surface**: `--api-key` checks `Authorization: bearer` on everything but
  `/health*`, `/ready`, `/metrics`; `401 {"error": "Unauthorized"}`. OpenAI
  chat/completions/embeddings/models/responses/score/rerank/classify/audio;
  Anthropic `/v1/messages` + `count_tokens`; native `/generate`; Ollama-compat `/api/chat`.
- **Divergences**: `--tool-call-parser`; `tool_choice` required/named via
  EBNF (xgrammar). `--reasoning-parser` → **`reasoning_content`**;
  `separate_reasoning` (default true), `stream_reasoning`. `n` 1–128;
  `response_format` + `structural_tag`; invalid sampling params → 400 before
  generation. `finish_reason` ∈ `stop|length|tool_calls|content_filter|
  function_call|abort`. Stream validation errors arrive as `data: {"error": …}`
  on HTTP 200. `prompt_tokens_details{cached_tokens, image_tokens}` (needs
  `--enable-cache-report`), `reasoning_tokens`.
- **Extensions/errors**: `regex`, `ebnf`, `min_tokens`, `stop_regex`,
  `lora_path`, `session_params`, `rid`, `priority`; errors `{object, message,
  type, param, code}` (flat, vLLM-legacy).

### Hugging Face TGI (maintenance mode)

- **Status/surface**: "maintenance mode"; repo archived 2026-03-21; maintainers
  recommend vLLM/SGLang. `--port 3000`; `--api-key`/`API_KEY`. `model` is
  documented `[UNUSED]` (`"tgi"`), **but any other value is a LoRA `adapter_id`**.
  `/generate`, `/generate_stream`, `/v1/chat/completions`, `/v1/completions`,
  `/tokenize`, `/info`, `/metrics`, `/v1/models`.
- **Divergences/errors**: `response_format` is a **grammar object** `{type:
  "json"|"regex"|"json_schema", value}`; `logit_bias`, `n` `[UNUSED]`;
  `finish_reason` `stop|length|stop_sequence` (no `tool_calls`); no reasoning.
  Timing headers `x-compute-time`, `x-total-time`, `x-queue-time`,
  `x-inference-time`, `x-time-per-token`, `x-prompt-tokens`, `x-generated-tokens`
  on `/generate*` and `/v1/completions` (chat *unverified*). Errors
  `{error, error_type: validation|generation|overloaded|incomplete_generation}`.

## Mapping to `ocai`

**(a) Codec vs host.** Every host above is served by the **existing**
`openai/chat_completions` codec (and `anthropic/messages` where `/v1/messages`
exists) through a `Host` value — no interface subpackage per host.
`Custom(base_url, paths)` already reaches most of them. What must grow:

- host `path_prefix` (Groq `/openai/v1`, DeepInfra `/v1/openai`, OpenRouter
  `/api/v1`, Fireworks `/inference/v1`, Cloudflare `/client/v4/accounts/{id}/ai/v1`)
  — explicit, so `Route` audits show the real path instead of a folded `base_url`.
- host `static_headers` (OpenRouter attribution, HF `X-HF-Bill-To`, Cloudflare
  `cf-aig-*`, Groq `Groq-Beta`) so attribution stays out of user code.
- a host `profile_key(resource)` hook: variant suffixes (`:nitro`, `:groq`,
  `:cloud`) pass verbatim, but `CapabilityProfile` lookup needs the base id.
- an explicit `NoCredential` for unconfigured local servers, and a header-name
  parameter on `ApiKey` (Cloudflare `cf-aig-authorization`; Azure `api-key`).
- Aggregator fragments (`ocai-openrouter`, …) are **data-only**: `vendor`,
  `first_party_base_url`, header defaults, profile facts — no codec, no edges.
  Ollama `/api/chat` (NDJSON) and Cloudflare `/ai/run` (parsed `tool_calls`)
  would need their own interface; both have OpenAI routes, so defer.

**(b) Auth.** All bearer `ApiKey`s; nothing needs signing or rule 12.

**(c) Honesty — `SemanticShift` or censused extension.**

- Reasoning drift: `reasoning` (vLLM, Ollama, OpenRouter, Groq parsed, LM
  Studio gpt-oss) vs `reasoning_content` (SGLang, llama.cpp, Fireworks,
  Together both) vs inline `<think>` (Groq raw). The codec decodes **both
  keys** into the canonical reasoning part with `native` recording which was
  seen; inline `<think>` stays *unparsed* text. OpenRouter `reasoning_details[]`
  → `openrouter.reasoning_details`.
- Usage extras (OpenRouter `cost`/`cost_details`, DeepInfra `estimated_cost`,
  Groq `queue_time`…, llama.cpp `timings`, Ollama `*_duration`) →
  `<host>.usage_*` extensions; cost stays out of canonical `Usage`.
- Stream shape: OpenRouter's **duplicated finish_reason** and usage-in-final-
  chunk variants are fold-law hazards — one fold-triple fixture per host.
  **Errors inside HTTP 200 streams** (OpenRouter `error` chunk, SGLang
  `data: {"error"}`, Ollama final NDJSON line) → the rule-8 mid-stream shape.
- Silent parameter dropping (Together ignores `service_tier`; Ollama drops
  `tool_choice`; Groq 400s on `logprobs`/`n`): the wire will not report it, so
  per-host `CapabilityProfile` facts are the only honest source —
  `UNSUPPORTED` declared from profile, certified by recorded pairs.
- Non-standard shapes (Together integer `logprobs`, `finish_reason: eos`, TGI
  grammar `response_format`, Cloudflare parsed `tool_calls`) → open codes with
  `native`, `APPROXIMATED` where re-shaped. Host-chosen model (OpenRouter
  `provider`/`openrouter_metadata`, HF provider selection) → censused
  `openrouter.provider_metadata` / `huggingface.provider`; `Route` gains a
  resolution `reason` saying the *host* picked.

**(d) Errors → taxonomy.** 401/403 → `AuthError`; 429 → `RateLimitError`
(parse `retry-after` on Groq/OpenRouter/Fireworks); 5xx incl. 520/524/529 →
`TransientError`; 402 (OpenRouter, Together, Fireworks, HF) →
`OcaiError(code="payment_required")` — a candidate taxonomy addition since
four hosts share it; 400 with context-length semantics (Together, DeepInfra,
vLLM) → `ContextLengthError` where a code exists; OpenRouter 403 moderation →
`ContentFilterError`; capacity signals (Groq 498, DeepInfra `engine_overloaded`,
Cloudflare `3040`, Together 529, TGI 429) → `TransientError`, not rate limit.
Envelope parsers: OpenAI nested (int `code` on OpenRouter), vLLM nested-int,
SGLang flat, Ollama string, TGI `{error, error_type}`, Cloudflare `errors[]`,
FastAPI `detail[]`.

**(e) Priority.**

| Host | Priority | Why | Effort |
|---|---|---|---|
| vLLM | **P0** | enterprise self-hosting default; `Custom` already targets it; reasoning rename + tool-parser gating are the first per-host profile facts; `/v1/messages` tests the Anthropic codec locally | 1 WU |
| OpenRouter | **P0** | de-facto aggregator and source of the `vendor/model` grammar; richest honesty surface (cost, provider metadata, duplicated finish, 200-stream errors) | 1.5 WUs |
| Groq | P1 | hard 400s make it the best negative-fixture host; full rate-limit headers exercise `RateLimitPolicy` | 0.5 WU |
| Ollama (OpenAI mode) | P1 | developer-laptop default; `reasoning` field; native NDJSON deferred | 0.5 WU |
| Together, Fireworks | P1 | large enterprise usage; mostly profile + usage census; Together `eos`/integer `logprobs` need `native` | 0.5 WU each |
| SGLang, llama.cpp, LM Studio | P2 | pattern replays of vLLM with `reasoning_content`; llama.cpp `timings` census | 0.5 WU combined |
| DeepInfra, HF router, Cloudflare (OpenAI route) | P2 | profile facts + `estimated_cost`/bill-to header; HF is provider-dependent so only the triple is certifiable | 0.5 WU combined |
| Ollama native, Cloudflare native, TGI | P3 | TGI archived; natives duplicate OpenAI routes | defer |

Hosts that **change the wire** come before hosts that only change the URL; a
host is done when recorded pairs certify every ignored param as `UNSUPPORTED`.

## Sources (read 2026-11-10)

- https://openrouter.ai/docs/api-reference/overview · /api-reference/errors · /api-reference/limits · /api-reference/streaming · /api-reference/parameters · /features/provider-routing · /features/model-routing · /guides/routing/model-variants/overview · /guides/features/plugins · /guides/routing/routers/router-metadata · /use-cases/usage-accounting · /use-cases/reasoning-tokens
- https://docs.together.ai/docs/openai-api-compatibility · /docs/rate-limits · /docs/error-codes · /docs/function-calling · /docs/gpt-oss · /reference/chat-completions-1 · /reference/rerank-1
- https://docs.fireworks.ai/api-reference/post-chatcompletions · /api-reference/post-responses · /tools-sdks/openai-compatibility · /guides/prompt-caching · /guides/function-calling · /guides/reasoning · /guides/inference-error-codes · /serverless/rate-limits · /structured-responses/structured-output-grammar-based
- https://console.groq.com/docs/openai · /docs/rate-limits · /docs/errors · /docs/reasoning · /docs/flex-processing · /docs/service-tiers · /docs/api-reference · /docs/tool-use · /docs/responses-api · /docs/batch · /docs/structured-outputs
- https://docs.deepinfra.com/chat/overview · /account/rate-limits · /api-reference/chat-completions/openai-chat-completions · /apis/deepinfra-native
- https://huggingface.co/docs/inference-providers/index · /pricing · /tasks/chat-completion · /hub-api · /guides/responses-api
- https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/ · /workers-ai/get-started/rest-api/ · /workers-ai/platform/pricing/ · /workers-ai/platform/limits/ · /workers-ai/platform/errors/ · /workers-ai/features/function-calling/ · /workers-ai/features/reject-if-busy/ · /ai-gateway/usage/providers/workersai/ · /ai-gateway/usage/rest-api/ · /ai-gateway/configuration/authentication/ · /ai-gateway/glossary/
- https://docs.vllm.ai/en/latest/serving/online_serving/ · /features/tool_calling/ · /features/reasoning_outputs/ · /features/structured_outputs/ · /cli/serve/ · https://github.com/vllm-project/vllm (`entrypoints/openai/chat_completion/protocol.py`, `serve/engine/protocol.py`, `openai/responses/protocol.py`, `anthropic/protocol.py`)
- https://docs.ollama.com/api/openai-compatibility · /api/introduction · /api/chat · /api/generate · /api/embed · /api/anthropic-compatibility · /cloud · /capabilities/thinking · https://github.com/ollama/ollama (`docs/api.md`, `openai/openai.go`, `server/routes.go`)
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://lmstudio.ai/docs/developer/openai-compat · /openai-compat/tools · /openai-compat/structured-output · /rest · /rest/endpoints · /rest/chat · /rest/streaming-events · /core/authentication · /core/ttl-and-auto-evict · /api-changelog
- https://docs.sglang.io/basic_usage/openai_api_completions.html · /basic_usage/sampling_params.html · /basic_usage/native_api.html · /advanced_features/server_arguments.html · /advanced_features/separate_reasoning.html · /advanced_features/structured_outputs.html · /advanced_features/tool_parser.html · https://github.com/sgl-project/sglang (`srt/entrypoints/openai/protocol.py`, `http_server.py`, `utils/auth.py`)
- https://github.com/huggingface/text-generation-inference · https://huggingface.co/docs/text-generation-inference/en/reference/api_reference · /reference/launcher · /basic_tutorials/using_guidance (`router/src/server.rs`, `docs/openapi.json`)
