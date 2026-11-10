# Model catalog and discovery

**Currency.** Researched 2026-11-10 against current provider documentation
and the public catalogs named below (URLs in Sources). Catalog *schemas* are
fairly stable; catalog *contents* (prices, context windows, deprecation
dates) change weekly, which is the whole point of treating them as refreshed
data rather than code. *Unverified* marks claims not confirmed from an
official page on this pass.

**Scope.** Provider `models` endpoints, what metadata each exposes, the
third-party catalogs that fill the gaps, and how `CapabilityProfile` facts
and cost metering could be sourced from them as data.

## Why this matters to ocai

Two kernel mechanisms consume model facts today without a data source:

- the **feature gate** reads `CapabilityProfile` (§2.5), keyed
  `(provider, interface, model_pattern)`, whose `Support` values are
  hand-written in plugin fragments;
- the **cost interceptor** (H4) needs per-model prices per `Consumption`
  dimension, and the batch tier (see batch-and-jobs.md) needs the discount.

Both are currently prose-maintained facts, and "rules that are prose rot".
This page argues they should be *declared data with provenance*, refreshed
from catalogs, and certified like fixtures.

## Provider endpoints

| Provider | Endpoint | Fields exposed (2026-11-10) | Context | Max output | Modalities | Pricing | Deprecation | Rate limits |
|---|---|---|---|---|---|---|---|---|
| OpenAI | `GET /models`, `GET /models/{model}`, `DELETE /models/{model}` | `id`, `object`, `created`, `owned_by`, `shutdown_date` (`YYYY-MM-DD` or `null`) | no | no | no | no | **yes** (`shutdown_date`) | no |
| Anthropic | `GET /v1/models` (`lifecycle` filter, `limit` ≤ 1000, `before_id`/`after_id`; `anthropic-workspace-id` header) | `id`, `type`, `display_name`, `created_at`, `deprecated_at`, `retires_at`, `lifecycle` ∈ `active`/`deprecated`/`retired`, `line` (`haiku`/`sonnet`/`opus`/`fable`/`mythos`), `max_input_tokens`, `max_tokens`, `capabilities` | **yes** | **yes** | partly (`image_input`, `pdf_input`) | no | **yes** (three dates + lifecycle) | no |
| Anthropic `capabilities` detail | — | `batch`, `citations`, `code_execution`, `context_management {clear_thinking_20251015, clear_tool_uses_20250919, compact_20260112}`, `effort {low, medium, high, xhigh, max}`, `image_input`, `pdf_input`, `server_tools {web_search, code_execution}`, `structured_outputs`, `thinking {types: adaptive, between_tools, disabled, enabled}` — each `{supported: bool}` | | | | | | |
| Gemini API | `GET /v1beta/models`, `GET /v1beta/models/{model}` | `name`, `baseModelId`, `version`, `displayName`, `description`, `inputTokenLimit`, `outputTokenLimit`, `supportedGenerationMethods`, `thinking`, `temperature`, `maxTemperature`, `topP`, `topK` | **yes** | **yes** | no (methods only) | no | no | no |
| Vertex Model Garden | `GET /v1beta1/publishers/{publisher}/models` (list), `GET /v1/publishers/{publisher}/models/{model}` (get) | `publisherModels[]` with `launchStage` (`GA`, `PUBLIC_PREVIEW`, …), `CallToAction` (`viewRestApi`, `deploy`, `requestAccess`, …); a developer forum thread notes model-card metadata (display name, overview, tags) is **not** in the API response | no | no | no | no | partial (`launchStage`) | no |
| Mistral | `GET /v1/models` (`provider`, `model` filters), `GET /v1/models/{model_id}`, `DELETE` (fine-tuned), `PATCH /v1/fine_tuning/models/{id}`, archive/unarchive | `id`, `created`, `owned_by`, `root`, `job`, `archived`, `max_context_length`, `aliases`, `capabilities {completion_chat, completion_fim, function_calling, fine_tuning, vision, classification}`, type base/fine-tuned | **yes** | no | partly (`vision`) | no | no (`archived` for FT) | no |
| Groq | `GET /openai/v1/models`, `GET /openai/v1/models/{model}` | `id`, `object`, `created`, `owned_by`, `active`, `context_window`, `public_apps`; retrieve adds `max_completion_tokens` | **yes** | **yes** (retrieve) | no | no | partial (`active`) | no |
| Together | `GET /v1/models` | `context_length` (integer) and a `pricing` object whose schema requires `hourly`; community sources report `input`/`output` per 1M tokens; `display_name`/`object` *unverified* | **yes** | no | no | **yes** (schema truncated) | no | no |
| OpenRouter | `GET /api/v1/models` (filters `category`, `supported_parameters`, `input_modalities`, `output_modalities`, `context`, `min_price`/`max_price`, `zdr`, `q`, `sort`, `limit` ≤ 1000, `use_rss`) | `id`, `canonical_slug`, `name`, `created`, `description`, `context_length`, `architecture {modality, input_modalities, output_modalities, tokenizer, instruct_type}`, `pricing {prompt, completion, request, image, audio, web_search, internal_reasoning, input_cache_read, input_cache_write, …}` (strings), `top_provider {context_length, max_completion_tokens, is_moderated}`, `per_request_limits {prompt_tokens, completion_tokens}`, `supported_parameters[]`, `default_parameters`, `hugging_face_id`, `expiration_date` | **yes** | **yes** | **yes** | **yes** | **yes** (`expiration_date`) | partial (`per_request_limits`) |
| Bedrock | `GET /foundation-models` (`ListFoundationModels`; filters `byProvider`, `byCustomizationType`, `byOutputModality`, `byInferenceType`) | `modelSummaries[]`: `modelArn`, `modelId`, `modelName`, `providerName`, `inputModalities`, `outputModalities`, `responseStreamingSupported`, `customizationsSupported`, `inferenceTypesSupported`, `modelLifecycle {status, startOfLifeTime, legacyTime, endOfLifeTime, publicExtendedAccessTime}` | no | no | **yes** | no | **yes** (lifecycle dates) | no |

Observations:

- Only OpenRouter and (partly) Together expose **prices** on the wire. Every
  first-party provider keeps pricing on web pages.
- Only Anthropic exposes **feature support** as structured booleans, and its
  keys map almost one-to-one onto `CapabilityProfile` feature keys
  (`thinking.types.disabled` is exactly the fact the feature gate needs for
  "newest models reject `temperature`"-class checks). Mistral's
  `capabilities` is the only other structured source.
- Deprecation is exposed by OpenAI (`shutdown_date`), Anthropic
  (`deprecated_at`, `retires_at`, `lifecycle`), Bedrock (`modelLifecycle`),
  OpenRouter (`expiration_date`); Gemini, Mistral, Groq, Together expose
  nothing or a bare `active`/`archived` flag.
- **Rate limits are nowhere** except OpenRouter's per-request token caps.
  They remain response-header territory (`RateLimitPolicy`, H4).

## Third-party catalogs

| Catalog | Access | Per-model fields (2026-11-10) | Update model | License |
|---|---|---|---|---|
| models.dev | `https://models.dev/api.json` (providers × models), `models.json` (provider-agnostic), `catalog.json` (both), `logos/{provider}.svg`; repo `providers/<provider>/models/<model>.toml`, `models/<lab>/<model>.toml`, `schema = 2` | `cost {input, output, cache_read, cache_write}` (reasoning/audio where billed), `limit {context, input, output}`, `modalities {input, output}`, `reasoning`, `tool_call`, `attachment`, `temperature`, `structured_output`, `knowledge`, `release_date`, `last_updated`, `open_weights`, optional `type`, `status` (`alpha`/`beta`/`deprecated`) | community PRs, `bun validate` | MIT |
| LiteLLM `model_prices_and_context_window.json` | raw JSON on GitHub (`BerriAI/litellm`, `main`); 3.5 MB | per key: `litellm_provider`, `mode`, `max_input_tokens`, `max_output_tokens`, `input_cost_per_token`, `output_cost_per_token`, `cache_read_input_token_cost`, `cache_creation_input_token_cost`, audio/image/video/per-second/per-character/per-page cost keys, `_above_200k_tokens`, `_priority`, `_flex`, `_batches` variants, `supported_endpoints`, `supported_modalities`, `supported_output_modalities`, `supports_function_calling`, `supports_vision`, `supports_prompt_caching`, `supports_reasoning`, `supports_tool_choice`, `deprecation_date`, `deprecation_source`, `source`, `provider_specific_entry`; a `sample_spec` entry documents the schema | repo commits; LiteLLM proxies fetch it at start | repository license (not read on this pass; *unverified*) |
| OpenRouter | live endpoint above | includes pricing and `supported_parameters` per model as served *through OpenRouter* | live | terms of service |

Caveats: models.dev and LiteLLM describe the *provider's list price*, which
is the right thing for metering but not for an enterprise's negotiated
contract; OpenRouter describes OpenRouter's price. None of the three is an
authority on *behaviour* (what a model rejects), which only the provider API
or ocai's own conformance fixtures can establish.

## Proposal: catalog facts as declared, provenance-stamped data

### Shape

A per-model descriptor file, hand-reviewable and machine-refreshable, under
`spec/interfaces/<provider>/<interface>/models/<model-pattern>.json` (name
negotiable; `spec/` is already the language-neutral truth, §10):

```
{
  "provider": "anthropic", "interface": "messages",
  "model_pattern": "claude-haiku-4-5-*",
  "revision": "2026-11-10",
  "sources": [
    {"kind": "provider_api", "url": ".../v1/models", "fetched": "2026-11-10"},
    {"kind": "catalog", "name": "models.dev", "fetched": "2026-11-10"}
  ],
  "limits": {"context_tokens": ..., "max_output_tokens": ...},
  "lifecycle": {"status": "active", "deprecated_at": null, "retires_at": null},
  "support": {"chat.thinking.disabled": "NATIVE", "chat.pdf_input": "NATIVE"},
  "pricing": {"currency": "USD", "unit": "per_1m_tokens",
              "input": ..., "output": ..., "cache_read": ...,
              "tiers": {"batch": {"multiplier": 0.5}}},
  "extensions": {"anthropic.line": "haiku"}
}
```

- `support` uses the **existing** `CapabilityProfile` feature keys and
  `Support` codes; the descriptor is simply the serialized source of a
  profile row. Plugins stop hand-writing profiles and load descriptors
  (still frozen, declarative data — no import-time mutation, rule 14).
- `pricing` is **data the cost interceptor reads**, keyed by the same
  `Consumption` dimensions `Usage` already reports (§2.8), so adding a
  modality (`seconds`, `read_units`) is a new key, not a release.
- `sources[]` is the **provenance stamp**: every fact says where it came
  from and when. A descriptor with no provider-API source for a `support`
  value is marked `"confidence": "catalog"` and the feature gate's strict
  mode may refuse to trust it.
- The catalog lock (`Catalog.lock()`, format `ocai.catalog-lock/2`) already
  hashes profiles; descriptors fall under the same hash, so a price or
  limit change shows up in `Route.catalog_lock` — every eval run becomes
  attributable to the catalog revision as well as the code (the H7
  reproducibility argument).

### Refresh cadence and verification

- A `scripts/refresh-catalog.py` (no network at test time, rule 10) pulls
  provider endpoints and third-party catalogs into a diff; a human merges.
  Weekly is enough for prices; deprecation dates need a check whenever a
  provider's list changes (OpenAI gives ≥ 6 months notice for GA models,
  ≥ 3 for specialized, ~2 weeks for previews).
- Conformance adds a **descriptor consistency** check: a `support` value
  of `NATIVE` must be backed by at least one recorded wire pair or fixture
  that exercises the feature on a model matching the pattern; `ABSENT` must
  be backed by a recorded rejection. That is the same "declaration ⊆
  evidence" rule EdgeContracts already live under.

### What is unverifiable per provider

| Provider | Verifiable from its API | Must come from catalogs or fixtures | Never verifiable without a live call |
|---|---|---|---|
| OpenAI | existence, `shutdown_date` | context, max output, modalities, prices, feature support | per-org rate limits |
| Anthropic | existence, limits, lifecycle dates, structured capabilities | prices | org-level tool restrictions ("a supported tool can still be rejected for your organization") |
| Gemini API | existence, token limits, generation methods, sampling defaults | prices, deprecation, feature support | safety defaults per model |
| Vertex | publisher list, launch stage | everything else | regional availability per project |
| Mistral | existence, context, coarse capabilities | prices, max output, deprecation | |
| Groq | existence, context, max output, `active` | prices, modalities | |
| Together | context, (partial) pricing | modalities, support | dedicated vs serverless pricing |
| Bedrock | existence, modalities, streaming flag, customization, lifecycle dates | context, prices | per-region model enablement |
| OpenRouter | nearly everything (for OpenRouter routes) | n/a | upstream provider identity per call |

## Priority: P1

- It **feeds the profile gate**, which is the first honesty mechanism a
  request meets; a wrong `Support` value produces either a false refusal or
  a silent provider 400 — both violate rule 5.
- It **feeds the cost interceptor** and the batch tier; without catalog data
  `Usage` is counted but never priced, and the enterprise "honest reporting"
  claim stops at tokens.
- It is **cheap**: pure data plus one refresh script plus one conformance
  rule; zero core changes (`CapabilityProfile` already exists, `Consumption`
  already carries open dimensions).
- It **de-risks every other family on these pages**: batch discounts,
  fine-tuned model inheritance (`ft:*` patterns), moderation model limits,
  file size caps are all catalog rows.

Effort: one WU for the descriptor schema, loader into `CapabilityProfile`,
and the OpenAI + Anthropic descriptors sourced from their `models`
endpoints; one WU for the refresh script and consistency check; catalogs
for other providers accrete with their plugins. Decide early whether
pricing lives in `spec/` (public, versioned) or in a separate data package
with its own release cadence — recommended: `spec/` for limits/support/
lifecycle, a sibling data file for prices, both under the lock hash.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/reference/resources/models
- https://developers.openai.com/api/docs/deprecations
- https://platform.claude.com/docs/en/api/models/list
- https://aistudio.google.com/api-reference/models
- https://docs.cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/publishers.models/list
- https://docs.cloud.google.com/vertex-ai/docs/reference/rest/v1/publishers.models
- https://discuss.google.dev/t/vertex-ai-publishermodel-api-does-not-expose-model-garden-model-card-metadata-display-name-overview-tags/299460
- https://docs.mistral.ai/api/endpoint/models
- https://console.groq.com/docs/api-reference
- https://docs.together.ai/reference/models.md
- https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties.md
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html
- https://models.dev/ and https://github.com/sst/models.dev
- https://docs.litellm.ai/docs/proxy/custom_pricing
- https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
