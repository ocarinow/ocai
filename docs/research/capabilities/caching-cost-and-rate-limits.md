# Caching, cost, and rate limits

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against provider documentation as published
that day. Provider caching rules change per model generation; the tables below
cite the documented value and the model families it applies to. Anything not
confirmed from an official page is marked *unverified*.

**Status:** planned. Nothing on this page is implemented. The kernel ships
`CacheHint` and `CacheConfig` as [provisional] IR types, both censused
`DROPPED` by every shipped edge; `RateLimitPolicy` and `WireTap` are [stub].

## 1. Why this family matters to ocai

Three distinct concerns hide under one heading, and the kernel treats them
differently because they live at different tiers of architecture §8:

| Concern | Where it lives | Why |
|---|---|---|
| Provider prompt caching | Wire knob inside each codec (edge) | It is a per-interface request field with provider-varying semantics: the §11 litmus test says "provider-varying wire dialect → capability concern, owned by the edge" |
| Semantic / exact response caching | Port-tier `CallInterceptor` (§5) | It operates on canonical IR calls, is meaningful for local and remote adapters alike (the admission test for that tier), and never touches the wire |
| Rate limiting and server pacing | Wire-tier `RateLimitPolicy` (§6) | It needs the raw `HttpResponse` headers and the `Retry(after)` decision vocabulary; a port-tier object cannot see headers |
| Cost | Port-tier interceptor over `Usage` + a pricing table | Usage is already dimensional (`Consumption(modality, unit, source, value)`); price is a satellite's lookup, not a kernel fact |

The honesty rule applies to all three: a cache hit, a dropped cache hint, or a
client-side throttle is reported, never silent.

## 2. Provider prompt caching — the landscape

### 2.1 Knobs per interface

| Interface | Mechanism | Request field(s) | Usage fields reporting hits / writes |
|---|---|---|---|
| OpenAI Responses (GPT-5.6 and later) | Automatic prefix caching with optional explicit breakpoints | `prompt_cache_key` (optional, per-customer accounting), `prompt_cache_options.ttl` (`"30m"` default, `"12h"` Responses-only), `prompt_cache_options.mode` (`implicit`/`explicit` — documented on Bedrock's OpenAI page, *unverified on OpenAI's own page*), `prompt_cache_breakpoint: {"mode": "explicit"}` on content blocks (Bedrock page) | `usage.input_tokens_details.cached_tokens`, `usage.input_tokens_details.cache_write_tokens`, `cache_write_tokens_details.{ttl_30m_tokens, ttl_12h_tokens}` |
| OpenAI (earlier models) | Automatic prefix caching | `prompt_cache_key` (routing hint), `prompt_cache_retention` (`in_memory` or `24h`) | `usage.input_tokens_details.cached_tokens` (Responses); Chat Completions path *unverified on the current page* |
| Anthropic Messages | Explicit breakpoints or one top-level automatic marker | Per-block `cache_control: {"type": "ephemeral", "ttl": "1h"?}` on `tools`/`system`/`messages` blocks (max 4); or a single top-level `cache_control` for automatic placement (uses one of the 4 slots) | `usage.cache_creation_input_tokens`, `usage.cache_read_input_tokens`, `usage.cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}` |
| Gemini (generateContent) | Implicit (default on 2.5+) and explicit `cachedContents` resource (Beta, `v1beta`; not on Gemini 4 or the Interactions API) | Create cache with `model`, `contents`, `systemInstruction`, `display_name`, `ttl` (e.g. `"300s"`, default 1 hour, no min/max); reference via `cachedContent` (REST) / `cached_content` (Python config) | `usage_metadata` carries the cached count; the Interactions API reports `usage.total_cached_tokens` |
| Bedrock Converse | Explicit `cachePoint` blocks; implicit on some models | `{"cachePoint": {"type": "default", "ttl": "1h"?}}` inside `system`, `messages[].content`, `toolConfig.tools`; Claude on Bedrock also accepts the top-level `cache_control` via `additionalModelRequestFields` | `usage.cacheReadInputTokens`, `usage.cacheWriteInputTokens`, `cacheDetails` |

### 2.2 Minimums, TTLs, pricing

| Provider | Minimum cacheable prefix | TTL | Write price | Read price |
|---|---|---|---|---|
| OpenAI GPT-5.6+ | 1,024 tokens (visible input only) | 30 min default (min), 12 h on Responses | 1.25× input (30 m), 2.5× (12 h) | 0.1× input (0.05× on some GPT-6.1 variants) |
| OpenAI earlier models | varies by request settings; `cached_tokens` rounded down to a multiple of 128 | `in_memory` ≈ 5–10 min inactivity, up to 1 h; `24h` ≈ 30 min, up to 24 h | none documented | model-dependent, "up to 95%" discount |
| Anthropic | 512 / 1,024 / 2,048 / 4,096 by model family (512 on the Claude 5.x line, 4,096 on Opus 4.5/4.6 and Haiku 4.5) | 5 min default, `"1h"` optional; refreshed on every read | 1.25× (5 m), 2× (1 h) | 0.1× (0.025×–0.05× on the newest families) |
| Gemini implicit | 2,048 (2.5 Flash/Pro) or 4,096 (3.x, 4) tokens; Gemini 4 caches a multi-turn request only if it adds ≥ 2,050 tokens | provider-managed | none | discounted automatically |
| Gemini explicit | not stated on the page | default 1 h; any TTL | storage billed per TTL | reduced rate (page refers to pricing page) |
| Bedrock (Claude) | 512–4,096 per model, cumulative across `tools`→`system`→`messages` | 5 min (default) or 1 h where listed; TTL resets on hit | model cache-write rate | model cache-read rate |
| Bedrock (OpenAI GPT-5.6+) | 1,024 | 30 min only | 1.25× | model cache-read rate; cached tokens do not count against TPM |
| Bedrock (Nova) | 1K (max 20K cacheable) | 5 min | — | implicit reuse is not reported or billed |

Two facts matter for the IR design: (a) the *write* side has a price on most
providers now, so a cache marker is not free and cannot be emitted on a user's
behalf silently; (b) cache reads are excluded from rate-limit accounting on
Anthropic (ITPM) and on Bedrock's OpenAI models — caching is also a throughput
lever, which is why the rate-limit policy must read usage, not just headers.

## 3. Kernel assessment at the research date

- `ChatConfig.cache: CacheConfig | None` [provisional] — `mode` (open code,
  `"auto" | "explicit" | "off"`) and `ref: ProviderRef | None` for a
  provider-side cache handle (the Gemini `cachedContent` case; crossing a
  `(provider, interface)` boundary is `UNSUPPORTED`-and-reported, §2.4).
- `CacheHint(ttl: str | None)` [provisional] on every part's `cache_hint`
  field — the Anthropic-style positional breakpoint, with `ttl` as an open
  provider-shaped token (`"5m"`, `"1h"`).
- **Both shipped edges declare `config.cache` as `DROPPED`** in their
  `EdgeContract` census (`ocai.openai.chat_completions.edges`,
  `ocai.anthropic.messages.edges`); the Anthropic edge carries a `# TODO:
  cache_hint → per-block cache_control breakpoints`. Today a caller who sets a
  cache knob gets an honest `DROPPED` entry in the `FidelityReport` and no
  caching. That is correct behavior for an unimplemented knob and the baseline
  the first caching WU must improve on.
- `Usage` already models `UsageSource.CACHED` as a disjoint bucket, so cache
  *reads* have a canonical home. Cache *writes* do not: there is no
  `UsageSource` for "written to cache", and the per-TTL write split
  (Anthropic `ephemeral_5m`/`ephemeral_1h`, OpenAI `ttl_30m`/`ttl_12h`) has no
  slot either.

## 4. Verdict

### 4.1 Prompt caching is a wire knob per codec, with first-class hints

Apply the three-lane law (§3.5):

- **First-class** — `CacheHint` on parts and `CacheConfig.mode` pass the
  checklist: ≥3 interfaces (Anthropic, Bedrock Converse, OpenAI Responses
  5.6+ breakpoints) share the *positional breakpoint* semantics; Gemini and
  older OpenAI models implement an *automatic* regime that an edge reports as
  `EMULATED` (hint accepted, placement is the provider's) or `ABSENT`. The
  `ttl` stays an open string because the admissible values differ (`5m`/`1h`
  vs `30m`/`12h` vs seconds); a codec validates against its own table and
  reports `APPROXIMATED` when it has to pick the nearest supported TTL —
  never clamps silently (rule 5).
- **Censused extension** — the provider-side cache *handle* for Gemini
  (`CacheConfig.ref`) is already a `ProviderRef`; the explicit
  `cachedContents` lifecycle (create/update/delete) is a separate operation,
  not a chat request field, and belongs to a future `cache` capability or a
  facade helper, never to the edge.
- **`provider_options`** — `prompt_cache_key` (OpenAI accounting key) and
  `prompt_cache_options.mode` are destination-scoped and ride
  `provider_options["openai.responses"]`; they have one interface and no
  congruent sibling.

Promotion trigger to record: if Gemini ships positional breakpoints, the
`EMULATED` disposition on its edge is re-censused to `EXACT`.

### 4.2 Usage needs a write-side bucket before the knob ships

Add `UsageSource.CACHE_WRITE` (open-code addition, additive, no schema break)
so that `Consumption(modality="text", unit="tokens", source="cache_write",
value=n)` can carry Anthropic `cache_creation_input_tokens`, OpenAI
`cache_write_tokens`, and Bedrock `cacheWriteInputTokens`. The per-TTL split
rides the consumption's `extensions` under a censused key (for example
`anthropic.cache_creation`), because only two providers itemize it and their
buckets differ. This is the "cache hits/misses visible in `Usage` across at
least two providers" freeze condition written on `CacheConfig`.

### 4.3 Semantic cache is a port-tier interceptor

A semantic or exact cache implements `CallInterceptor.intercept(call, next)`:
hash the canonical request (`canonjson`, the equality predicate — exact match
for free) or embed it (semantic); on a hit, return a `CallResult` whose
`route.host` is a cache label and whose `report` carries a `SemanticShift`
of a new kind (`cache_hit`), so the ledger never pretends the provider was
called. It is meaningful for local adapters too, which is the admission test
for the tier. Effectful backends (Redis, a vector store) declare
`SyncBackend`/`AsyncBackend` faces so `Binding.validate()` can reject an
impossible composition. The external products to interoperate with: LiteLLM
proxy caching (`cache_params.type` ∈ `redis`, `redis-semantic`,
`valkey-semantic`, `qdrant-semantic`, `s3`, `gcs`, `local`, `disk`; hit
signaled by an `x-litellm-cache-key` header), Portkey (`cache.mode` ∈
`simple`/`semantic`, `cache.max_age`, default TTL 7 days, force refresh via
`x-portkey-cache-force-refresh`), Redis LangCache (REST
`POST /v1/caches/{cacheId}/entries/search` then `POST
/v1/caches/{cacheId}/entries`; in preview), GPTCache (MIT; maintainers have
stopped adding new model support). The lesson from LiteLLM's own docs — that
semantic caching "can go badly wrong on agentic traffic" — is why ocai's
semantic cache must key on the whole canonical transcript, not the last
message, and must bypass requests that carry tool results.

### 4.4 Rate limiting is `RateLimitPolicy` with header parsing

The stub's two faces map exactly onto provider truth:

- `on_request` consults a token-bucket backend and returns
  `Proceed | Retry(after) | Fail` (deadline from `CallContext.deadline`).
- `on_outcome` feeds server signals into the bucket. The headers to parse:

| Provider | Headers | Value format |
|---|---|---|
| OpenAI | `x-ratelimit-limit-requests`, `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-requests`, `x-ratelimit-reset-tokens`, project-scoped `x-ratelimit-{limit,remaining,reset}-project-tokens`, `Retry-After` | counts; resets as duration strings (`1s`, `6m0s`); `Retry-After` in seconds; 429 body `type: rate_limit_error`, `code: slow_down` for ramp-rate limits |
| Anthropic | `retry-after`; `anthropic-ratelimit-{requests,tokens,input-tokens,output-tokens}-{limit,remaining,reset}`; `anthropic-priority-{input,output}-tokens-{limit,remaining,reset}` (Priority Tier); `anthropic-workspace-id` | counts (tokens rounded to the nearest thousand); resets as RFC 3339 timestamps; token bucket semantics; ITPM counts `input_tokens + cache_creation_input_tokens` only; a spend-cap 429 carries no `retry-after` and `error.details.error_code = enforced_spend_limit_reached` |
| Gemini | none documented | 429 with status `RESOURCE_EXHAUSTED`; limits are per project, dimensions RPM/TPM/RPD |
| Bedrock | none documented for Converse (*unverified*); cached reads excluded from TPM on OpenAI models | throttling surfaces as `ThrottlingException` (*unverified from the fetched pages*) |

The policy stays pure: it parses headers into a `RateState` value and the
backend holds it. The existing `RetryPolicy` already honors `retry_after`;
`RateLimitPolicy` is the proactive complement. Both are wire-tier because they
need the raw response.

### 4.5 Cost is a satellite lookup over `Usage`

`UsageUnit.CURRENCY` is reserved for *gateway-reported* cost (OpenRouter
returns `usage.cost` and `cost_details`; Vercel AI Gateway logs cost per
request). First-party cost stays an interceptor concern: a `CostInterceptor`
multiplies each `Consumption` by a price keyed on `(route.node.provider,
resource, source, unit)` and attaches a `Consumption(unit="currency")` with
the currency code in `extensions`. Pricing sources, in order of preference:
the provider's own pricing page (authoritative, no API), `models.dev`
(`https://models.dev/api.json`, MIT, TOML-per-provider, fields `cost.input`,
`cost.output`, `cost.cache_read`, `cost.cache_write`, `cost.reasoning`,
`limit.context`, `limit.output`), and OpenRouter's model list (per-provider
pricing; exact field names *unverified* here because the reference page was
not reachable on the read date). The kernel never ships a price table.

### 4.6 Token counting

Local counting exists only for OpenAI (`tiktoken`, MIT, encodings
`o200k_base`, `cl100k_base`); Anthropic exposes `POST
/v1/messages/count_tokens` (free, separate RPM limits per tier, returns
`{"input_tokens": n}`, rejects server tools and the MCP connector, estimates
only); Gemini exposes `models.countTokens` (`client.models.count_tokens`,
returns `total_tokens`). Anthropic also documents that Claude 4.7-and-later
models use a different tokenizer (~30% more tokens for the same text), so a
count is only valid for the `model` it was made against. ocai should expose
counting as a *separate operation* on the chat port (`count_tokens`) returning
`CallResult[TokenCount]` with `route`, so that an estimate is attributable to
the interface and tag that produced it; interfaces without an endpoint report
`UNSUPPORTED`. It is a §11 operation, not an interceptor, because it has
provider-varying wire dialects.

## 5. Priority and sequencing

| Item | Tier | Priority | Depends on |
|---|---|---|---|
| Anthropic edge: `CacheHint` → `cache_control`, `CacheConfig.mode="auto"` → top-level `cache_control`; census moves `config.cache` from `DROPPED` to `EXACT`/`EMULATED`; fixtures with `cache_read`/`cache_write` usage | edge | **P1** (first real cache knob; unblocks the provisional freeze) | `UsageSource.CACHE_WRITE` |
| `UsageSource.CACHE_WRITE` + censused per-TTL extension | core (additive) | **P1** | — |
| OpenAI Responses edge: `prompt_cache_options`/breakpoints via the same hints; `prompt_cache_key` via `provider_options` | edge | P1 (lands with H1 `/responses`) | H1 |
| `RateLimitPolicy` implementation with OpenAI + Anthropic header parsing, in-process bucket backend | wire | **P1** (H4 names it; needed for any fleet deployment) | — |
| `CostInterceptor` + pricing-table protocol (models.dev loader as the reference implementation) | port tier, satellite `ocai-cost` | P2 | `Usage` write bucket |
| Exact-match cache interceptor (canonical-JSON keyed) | port tier | P2 | — |
| Semantic cache interceptor with pluggable backend | port tier, satellite | P3 | exact cache |
| `count_tokens` operation on the chat port | capability op | P3 | H2 (Gemini) for a second dialect |
| Gemini explicit `cachedContents` lifecycle as a facade helper / future capability | facade | P3 | H2 |

## 6. Open questions and unverified items

- Whether OpenAI's Chat Completions endpoint exposes the GPT-5.6
  `prompt_cache_options` object is *unverified*; the fetched OpenAI page
  documents the Responses and Agents APIs only, and Bedrock's page says
  explicit breakpoints are not supported through Converse for those models.
- The exact Gemini `usageMetadata` field name for cached tokens on
  `generateContent` (`cachedContentTokenCount`) was not confirmed on the
  pages read; the Interactions API field `usage.total_cached_tokens` was.
- Bedrock throttling header behavior and the `ThrottlingException` name were
  not confirmed on the pages read.
- Whether a cache *hit served by an interceptor* should count toward the
  caller's `Usage` at all (zero consumption with a `cache_hit` shift, or the
  original call's usage replayed and flagged) is a decision for the WU; the
  recommendation is zero consumption plus the shift, with the original
  `CallResult` reachable through `raw`.

## Sources

- https://developers.openai.com/api/docs/guides/prompt-caching (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/rate-limits (read 2026-11-10)
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching (read 2026-11-10)
- https://platform.claude.com/docs/en/api/rate-limits (read 2026-11-10)
- https://platform.claude.com/docs/en/build-with-claude/token-counting (read 2026-11-10)
- https://aistudio.google.com/docs/caching (read 2026-11-10)
- https://aistudio.google.com/docs/caching?generate-content=true (read 2026-11-10)
- https://aistudio.google.com/docs/tokens (read 2026-11-10)
- https://aistudio.google.com/docs/rate-limits (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html (read 2026-11-10)
- https://docs.litellm.ai/docs/proxy/caching (read 2026-11-10)
- https://portkey.ai/docs/product/ai-gateway/cache-simple-and-semantic (read 2026-11-10)
- https://redis.io/docs/latest/develop/ai/langcache/ (read 2026-11-10)
- https://github.com/zilliztech/GPTCache (read 2026-11-10)
- https://github.com/openai/tiktoken (read 2026-11-10)
- https://github.com/sst/models.dev (read 2026-11-10)
- https://openrouter.ai/docs/api-reference/overview (read 2026-11-10)
