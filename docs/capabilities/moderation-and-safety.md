# Moderation and safety

**Currency.** Researched 2026-11-10 against current provider documentation
(URLs in Sources). Two currency facts shape this page: Azure AI Content
Safety retires several preview features on 2027-04-30 (multimodal analyze,
custom categories (rapid), containers, embedded SDK, groundedness), and
OpenAI's legacy `text-moderation-*` models were shut down 2025-10-27 in
favour of `omni-moderation`. Category names are quoted verbatim; *unverified*
marks claims not confirmed from an official page on this pass.

**Scope.** Standalone classification endpoints that return a verdict about
content (text, image, conversation), plus the safety signals that ride inside
chat responses. Prompt-injection detectors and PII overlap with
guardrails-and-pii.md and are cross-referenced, not duplicated.

## Provider survey

### OpenAI Moderation

- `POST /v1/moderations`, model `omni-moderation-latest`; input is text or
  an array mixing text and `image_url` items (images ≤ 20 MB); no audio.
- Response per result: `flagged` (bool), `categories` (bool per key),
  `category_scores` (float per key), `category_applied_input_types` (which
  modalities contributed per key).
- 13 categories: `harassment`, `harassment/threatening`, `hate`,
  `hate/threatening`, `illicit`, `illicit/violent`, `self-harm`,
  `self-harm/intent`, `self-harm/instructions`, `sexual`, `sexual/minors`,
  `violence`, `violence/graphic`. Image-capable: `self-harm` (all three),
  `sexual`, `violence`, `violence/graphic`; the rest are text-only.
- Free; also runnable through the Batch API (`/v1/moderations` endpoint).
  Rate limits not on the page.

### Azure AI Content Safety

- `POST {endpoint}/contentsafety/text:analyze?api-version=2024-09-01`
  (a `2026-07-01-preview` version also exists): `text` ≤ 10,000 Unicode
  code points, `categories[]` ⊆ `Hate`, `SelfHarm`, `Sexual`, `Violence`,
  `blocklistNames[]`, `haltOnBlocklistHit`, `outputType` ∈
  `FourSeverityLevels` (default; values 0, 2, 4, 6) | `EightSeverityLevels`
  (0–7). Response `categoriesAnalysis[] {category, severity}`,
  `blocklistsMatch[] {blocklistName, blocklistItemId, blocklistItemText}`.
- Image analyze: same four categories, trimmed scale only (0, 2, 4, 6).
  Multimodal (image with text) supports 0–7 but retires 2027-04-30.
- Severity semantics: `0` is "safe" (annotated, never filtered); the
  guardrail blocking levels `Low`/`Medium`/`High` map onto severity bands;
  Foundry guardrails return `{detected, filtered}` annotations instead of
  severities.
- Prompt Shields: `text:shieldPrompt` with `userPrompt` and up to five
  `documents`; response `userPromptAnalysis.attackDetected` and
  `documentsAnalysis[].attackDetected` (see guardrails-and-pii.md).
- Other operations: protected material (text), groundedness (preview,
  retiring), custom categories (standard, preview), task adherence, content
  provenance detection.
- Rate limits: F0 5 RPS; S0 1000 requests per 10 s for moderation and Prompt
  Shields; 50 RPS groundedness; 10 RPS multimodal. Tiers F0/S0.
- Languages: classifiers trained on Chinese, English, French, German,
  Italian, Japanese, Portuguese, Spanish; protected material, groundedness,
  custom categories English-only.

### Google: Gemini safety settings and ratings (inside chat)

- Request `safetySettings[] {category, threshold}` with `category` ∈
  `HARM_CATEGORY_HARASSMENT`, `HARM_CATEGORY_HATE_SPEECH`,
  `HARM_CATEGORY_SEXUALLY_EXPLICIT`, `HARM_CATEGORY_DANGEROUS_CONTENT`,
  `HARM_CATEGORY_JAILBREAK` (`HARM_CATEGORY_CIVIC_INTEGRITY` is no longer on
  the current reference page) and `threshold` ∈ `BLOCK_LOW_AND_ABOVE`,
  `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, `BLOCK_NONE`, `OFF`.
- Response `safetyRatings[] {category, probability ∈ NEGLIGIBLE | LOW |
  MEDIUM | HIGH, blocked}`; `promptFeedback.blockReason` ∈ `SAFETY`,
  `OTHER`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `IMAGE_SAFETY`; candidate
  `finishReason: SAFETY`.
- The Interactions API spells the same settings in lower case
  (`safety_settings[] {type: harassment | hate_speech | sexually_explicit |
  dangerous_content | jailbreak, threshold: off | block_only_high |
  block_medium_and_above | block_low_and_above}`); unset categories default
  to `off` on Gemini 2.5+; a block is an HTTP 400 with `code` ∈ `safety`,
  `jailbreak`, `prohibited_content`, `blocklist`, and background interactions
  go to `status: failed`.
- These are **not a standalone endpoint**: they are part of the chat
  capability (H2 already maps `promptFeedback` pre-generation blocks to
  `ContentFilterError`). Scores are *probability bands*, not calibrated
  numbers.

### Google Perspective API

- `POST https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze`
  with `comment.text`, `requestedAttributes {NAME: {...}}`, `languages[]`,
  `doNotStore`, `spanAnnotations`; response `attributeScores.{NAME}
  .summaryScore.value` (0–1 probability), `spanScores[]`, `languages[]`.
- Production attributes: `TOXICITY`, `SEVERE_TOXICITY`, `IDENTITY_ATTACK`,
  `INSULT`, `PROFANITY`, `THREAT`; experimental `SEXUALLY_EXPLICIT`,
  `FLIRTATION`. The developer documentation site failed to render on this
  pass; attribute list taken from the API discovery document and secondary
  sources. A third-party listing claims a shutdown on 2026-12-31
  (*unverified*, not from Google).

### AWS Bedrock Guardrails (`ApplyGuardrail`)

- `POST /guardrail/{guardrailIdentifier}/version/{guardrailVersion}/apply`
  (runtime endpoint) with `source` ∈ `INPUT` | `OUTPUT`, `content[]`
  (text or image blocks), `outputScope` ∈ `INTERVENTIONS` | `FULL`.
- Response: `action` ∈ `NONE` | `GUARDRAIL_INTERVENED`, `actionReason`,
  `outputs[] {text}` (the masked/replacement text), `assessments[]` with:
  - `contentPolicy.filters[] {type ∈ SEXUAL | VIOLENCE | HATE | INSULTS |
    MISCONDUCT | PROMPT_ATTACK, confidence ∈ NONE | LOW | MEDIUM | HIGH,
    filterStrength, action, detected}`; modalities `TEXT`, `IMAGE`;
  - `topicPolicy.topics[] {name, type, action, detected}` (denied topics);
  - `wordPolicy.customWords[]`, `managedWordLists[]`;
  - `sensitiveInformationPolicy.piiEntities[] {type, match, action ∈
    ANONYMIZED | BLOCKED | NONE, detected}` and `regexes[]`;
  - `contextualGroundingPolicy.filters[] {type, score, threshold, action,
    detected}` (grounding and relevance);
  - `automatedReasoningPolicy.findings[]`;
  - `invocationMetrics {guardrailProcessingLatency, guardrailCoverage
    {textCharacters, images}, usage {contentPolicyUnits,
    contentPolicyImageUnits, topicPolicyUnits, wordPolicyUnits,
    sensitiveInformationPolicyUnits, sensitiveInformationPolicyFreeUnits,
    contextualGroundingPolicyUnits, automatedReasoningPolicyUnits,
    automatedReasoningPolicies}}`.
- Billing is per policy unit (the `usage` block above) — a non-token
  consumption dimension.

### Meta Llama Guard 4 (open weights)

- 12B early-fusion multimodal classifier; prompt-format model, not an API.
  Output is a first line `safe` or `unsafe`, then a comma-separated list of
  violated codes (for example `S1,S2`).
- Default hazard taxonomy: `S1` Violent Crimes, `S2` Non-Violent Crimes,
  `S3` Sex Crimes, `S4` Child Exploitation, `S5` Defamation, `S6`
  Specialized Advice, `S7` Privacy, `S8` Intellectual Property, `S9`
  Indiscriminate Weapons, `S10` Hate, `S11` Self-Harm, `S12` Sexual Content,
  `S13` Elections, `S14` Code Interpreter Abuse. The category list is
  prompt-supplied, so hosts can change it.
- Hosts: Together serves `meta-llama/Llama-Guard-4-12B` through chat
  completions; Groq has a `meta-llama/llama-guard-4-12b` model page (tested
  up to 5 images) but a third-party gateway marks the Groq route
  deactivated since 2026-03-29 (*unverified*). Also on OpenRouter, DeepInfra,
  NVIDIA. License not stated on the Meta page.

### Mistral moderation

- `POST /v1/moderations` (`input` string or array, `model`) and
  `POST /v1/chat/moderations` (`input` = messages or array of message
  arrays; roles system/user/assistant/tool). Response `{id, model,
  results[] {categories {name: bool}, category_scores {name: float}}}`.
- Current model `mistral-moderation-2603` (`mistral-moderation-2411`
  deprecated 2026-03-31). Category keys in the API examples: `sexual`,
  `hate_and_discrimination`, `violence_and_threats`,
  `dangerous_and_criminal_content`, `selfharm`, `health`, `financial`,
  `law`, `pii`. The guardrailing guide additionally lists "Jailbreaking"
  and splits "Dangerous" from "Criminal"; the guardrail response shape there
  is `categories {score, violated}` and `decisions {threshold, score,
  violated}` — a second dialect on the same provider (*unverified* whether
  `/v1/moderations` emits a `jailbreaking` key).
- Pricing not on the page; batchable through the batch API.

### Anthropic

No standalone moderation endpoint. The official content-moderation guide
prescribes Claude as a classifier through the Messages API with a prompt
that lists the categories and asks for JSON (`violation`, `categories`,
`explanation`), suggests Haiku-class models and graded 0–3 risk levels, and
notes that Claude's own safety behaviour may refuse independently of the
prompt. Third-party directories advertising an "Anthropic Moderation API"
are not backed by Anthropic documentation.

### Prompt-injection / guard products

Lakera Guard (now branded "Check Point AI Guardrails"), Azure Prompt Shields,
Bedrock `PROMPT_ATTACK`, Gemini `HARM_CATEGORY_JAILBREAK`, Mistral
jailbreaking, Llama Guard: see guardrails-and-pii.md for shapes. The only
one with a moderation-like category output is Lakera's `/v2/guard`
(`flagged`, `breakdown[] {detector_type, detected, …}`, confidence levels
`l1_confident` … `l5_unlikely`, `no_level`).

## Category taxonomies side by side

Rows are ocai's proposed canonical open codes (not a frozen taxonomy —
rule 5 says enums are open codes with the native value preserved). Cells
show the native key that *most nearly* corresponds; "≈" marks a semantic
shift, "—" means no counterpart.

| Canonical code | OpenAI | Azure CS | Gemini | Bedrock | Llama Guard 4 | Mistral | Perspective |
|---|---|---|---|---|---|---|---|
| `hate` | `hate`, `hate/threatening` | `Hate` | `HARM_CATEGORY_HATE_SPEECH` | `HATE` | `S10` | `hate_and_discrimination` | `IDENTITY_ATTACK` ≈ |
| `harassment` | `harassment`, `harassment/threatening` | ≈ inside `Hate` ("harassment and bullying") | `HARM_CATEGORY_HARASSMENT` | `INSULTS` ≈ | — | ≈ `hate_and_discrimination` | `INSULT`, `PROFANITY`, `THREAT` ≈ |
| `sexual` | `sexual` | `Sexual` | `HARM_CATEGORY_SEXUALLY_EXPLICIT` | `SEXUAL` | `S12` | `sexual` | `SEXUALLY_EXPLICIT` (exp.) |
| `sexual.minors` | `sexual/minors` | ≈ inside `Sexual` ("child exploitation") | — | — | `S4` | — | — |
| `violence` | `violence`, `violence/graphic` | `Violence` | `HARM_CATEGORY_DANGEROUS_CONTENT` ≈ | `VIOLENCE` | `S1`, `S9` ≈ | `violence_and_threats` | `THREAT` ≈ |
| `self_harm` | `self-harm`, `/intent`, `/instructions` | `SelfHarm` | ≈ `DANGEROUS_CONTENT` | — | `S11` | `selfharm` | — |
| `illicit` | `illicit`, `illicit/violent` | — | ≈ `DANGEROUS_CONTENT` | `MISCONDUCT` ≈ | `S2`, `S3` | `dangerous_and_criminal_content` | — |
| `prompt_attack` | — | Prompt Shields (separate op) | `HARM_CATEGORY_JAILBREAK` | `PROMPT_ATTACK` | — | jailbreaking (guide only) | — |
| `pii` | — | (Language service) | — | `sensitiveInformationPolicy` | `S7` ≈ | `pii` | — |
| `specialized_advice` | — | — | — | — | `S6` | `health`, `financial`, `law` | — |
| `ip` / `defamation` / `elections` | — | protected material ≈ | — | — | `S8`, `S5`, `S13` | — | — |
| `code_abuse` | — | — | — | — | `S14` | — | — |
| `grounding` | — | groundedness (retiring) | — | `contextualGroundingPolicy` | — | — | — |

The honesty problem is visible: no two taxonomies are isomorphic; several
are many-to-one in both directions (Azure folds harassment into `Hate`;
OpenAI splits self-harm into three). Mapping a native key to a canonical
code is a **declared `SemanticShift`**, and a canonical result must carry
the native keys verbatim alongside.

## Score and severity semantics

| Provider | Per-category value | Meaning | Threshold owner |
|---|---|---|---|
| OpenAI | `category_scores` 0–1 float + `categories` bool | model-calibrated flag at an OpenAI-chosen threshold | OpenAI (bool), caller (float) |
| Azure CS | `severity` 0,2,4,6 or 0–7 integer | ordinal *severity of consequences*, not probability | caller |
| Gemini | `probability` 4 bands | likelihood band; blocking by `threshold` | caller via settings |
| Bedrock | `confidence` NONE/LOW/MEDIUM/HIGH + `filterStrength` | likelihood band vs configured strength | guardrail config (server) |
| Llama Guard | none (membership only) | binary per category | model |
| Mistral | `category_scores` float + bool | probability + provider threshold | provider (bool) |
| Perspective | `summaryScore.value` 0–1 | probability that a reader perceives the attribute | caller |
| Lakera | confidence levels `l1`–`l5` | ordinal confidence | policy (server) |

A probability, an ordinal severity and a binary verdict are **three
incompatible lanes**. Converting an Azure severity 4 into a 0–1 score, or an
OpenAI 0.83 into a Gemini band, would be the kind of silent rescale rule 5
forbids. The canonical result keeps three optional lanes per category
(`flagged: bool | None`, `score: float | None`, `severity: str | None` as an
open ordinal code) and never fills one from another; a consumer that needs a
single number declares its own policy in a hook.

## Canonical proposal (per H7)

- **Identity.** `Capability("moderation")`, shapes
  `("moderation","request")`, `("moderation","response")`. No streaming shape
  (no provider streams a verdict).
- **Request IR.** `ModerationRequest(input: list[Part] | list[Message],
  policy: ProviderRef | None, categories: list[str] | None,
  provider_options, extensions)`. `input` reuses the chat `Part` union (text,
  image, document) so a chat turn can be moderated without re-encoding;
  Mistral's conversational endpoint and Bedrock `source: INPUT|OUTPUT`
  consume the message form. `policy` is a provider-scoped `ProviderRef`
  (`kind="guardrail"` for Bedrock `guardrailIdentifier`/`guardrailVersion`,
  Lakera `project_id`, Azure blocklist names) — never portable, always
  `UNSUPPORTED` on crossing. No `model` field: the moderation model name is
  the front-door resource (`openai/omni-moderation-latest`,
  `together/meta-llama/Llama-Guard-4-12B`).
- **Response IR.** `ModerationResult(flagged: bool | None, categories:
  list[CategoryVerdict], redacted: list[Part] | None, finish: FinishInfo,
  extensions)`; `CategoryVerdict(code: str, native: str, flagged: bool |
  None, score: float | None, severity: str | None, applied_to: list[str] |
  None, span: Span | None)`. `code` is an open code with the canonical
  constants above; `native` is the provider's verbatim key. Unknown native
  keys decode to `code="unknown"` with `native` preserved — total decode,
  rule 6. `redacted` carries Bedrock `outputs[].text` style transformed
  content.
- **Port.** `moderate(request, *, ctx) -> CallResult[ModerationResult]` and
  `amoderate`. `usage` reports `Consumption` in open units: tokens where
  billed as tokens (Llama Guard via chat), `policy_units` for Bedrock,
  characters for Azure, requests for OpenAI (free, zero cost).
- **Profile keys.** `moderation.input.image`, `moderation.input.conversation`,
  `moderation.score.probability`, `moderation.score.severity`,
  `moderation.redaction`, `moderation.policy_ref`, `moderation.span`.
- **Edges and census.** One edge per provider interface; each
  `EdgeContract` declares the category mapping as `SemanticShift`s and every
  provider-only category as a censused extension
  (`spec/extensions/moderation.<provider>.schema.json`). Chat-embedded
  signals (Gemini `safetyRatings`, Azure OpenAI `content_filter_results`)
  are **not** moderation edges; they stay in the chat IR as extensions and
  `FinishInfo` details, with a documented helper that lifts them into
  `CategoryVerdict`s for consumers who want one vocabulary.
- **Limits as data.** Azure 10k characters, OpenAI 20 MB images, Bedrock
  coverage counters: catalog rows (see model-catalog.md); the facade splits
  over-long text as a declared fan-out, never truncates silently.

## Priority and effort

**P2** (not P1): the scope litmus admits moderation cleanly and the
enterprise demand is real, but three things argue against doing it before
files, jobs and the catalog: (1) the chat path already carries the two most
used safety signals (Gemini ratings, Azure OpenAI filter results) as
extensions, so the urgent honesty work is in chat edges, not a new port;
(2) the taxonomy shift is the *only* conversion content, so the capability
is small once the IR exists — a good "recipe proof" after rerank, which H6
already reserves that role for; (3) the Azure surface is mid-retirement and
the Perspective status is unclear, so fixture investment there now is risky.
If a product needs a single provider first, OpenAI (free, stable, simplest
shape) and Bedrock `ApplyGuardrail` (richest shape, exercises `policy` refs
and non-token consumption) are the two edges that prove the design. Effort:
one WU for IR + schema + OpenAI + Mistral (same shape), one for Bedrock +
Azure (severity lane, policy refs, redaction), Llama Guard as a thin chat-
backed adapter in the Together plugin.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/guides/moderation
- https://developers.openai.com/api/docs/deprecations
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/harm-categories
- https://learn.microsoft.com/en-us/rest/api/contentsafety/text-operations/analyze-text
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection
- https://aistudio.google.com/docs/api/generate-content
- https://aistudio.google.com/docs/safety-settings
- https://code.googlesource.com/google-api-go-client/+/refs/tags/v0/commentanalyzer/v1alpha1/commentanalyzer-api.json
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_GuardrailContentFilter.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailPiiEntityFilter.html
- https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama-guard-4/
- https://together.ai/models/llama-guard-4-12b
- https://console.groq.com/docs/model/meta-llama/llama-guard-4-12b
- https://docs.mistral.ai/capabilities/guardrailing/
- https://docs.mistral.ai/api/endpoint/classifiers
- https://platform.claude.com/docs/en/about-claude/use-case-guides/content-moderation
- https://docs.lakera.ai/api-reference/lakera-api/guard/screen-content.md
