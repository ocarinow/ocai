# Guardrails and PII

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency.** Researched 2026-11-10 against current vendor documentation
(URLs in Sources). Notable churn in this family: Microsoft Presidio now
lives under the Data Privacy Stack organization (docs at
presidio.dataprivacystack.org); Protect AI's LLM Guard and Rebuff are
archived (last LLM Guard release 2025-05; Rebuff read-only since
2025-05-16); Lakera Guard is branded "Check Point AI Guardrails"; Private AI
documentation also appears under the Limina name. *Unverified* marks claims
not confirmed from an official page on this pass.

**Scope.** PII detection and redaction, output validation frameworks,
prompt-injection and jailbreak detection, secrets detection — and the
verdict on which of these belong in ocai's kernel, which are platform policy
hooks, and which are interceptors.

## Survey

### PII detection and redaction services

| Service | Deployment | Request | Response | Redaction modes | Entity vocabulary (size, examples) | Limits |
|---|---|---|---|---|---|---|
| Microsoft Presidio | local library / container (analyzer + anonymizer) | `POST /analyze {text, language, entities?, score_threshold?}` | `[{entity_type, start, end, score}]` | anonymizer operators (replace, redact, mask, hash, encrypt — names from project docs, *unverified* this pass) | global: `CREDIT_CARD`, `CRYPTO`, `DATE_TIME`, `EMAIL_ADDRESS`, `IBAN_CODE`, `IP_ADDRESS`, `MAC_ADDRESS`, `NRP`, `LOCATION`, `PERSON`, `PHONE_NUMBER`, `MEDICAL_LICENSE`, `URL`, `UUID`; ~100 country-specific (`US_SSN`, `UK_NHS`, `ES_NIF`, `IN_AADHAAR`, `DE_TAX_ID`, …); medical NER set via transformers | none (local) |
| AWS Comprehend PII | API | `DetectPiiEntities` (sync, ≤ 100 KB UTF-8, English/Spanish); `StartPiiEntitiesDetectionJob` with `RedactionConfig` for async redaction | `Entities[] {Score, Type, BeginOffset, EndOffset}` | async only: mask characters or replace with entity type (*exact `MaskMode` names unverified*) | universal: `ADDRESS`, `AGE`, `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `CREDIT_DEBIT_CVV`, `CREDIT_DEBIT_EXPIRY`, `CREDIT_DEBIT_NUMBER`, `DATE_TIME`, `DRIVER_ID`, `EMAIL`, `INTERNATIONAL_BANK_ACCOUNT_NUMBER`, `IP_ADDRESS`, `LICENSE_PLATE`, `MAC_ADDRESS`, `NAME`, `PASSWORD`, `PHONE`, `PIN`, `SWIFT_CODE`, `URL`, `USERNAME`, `VEHICLE_IDENTIFICATION_NUMBER`; country: `SSN`, `PASSPORT_NUMBER`, `BANK_ACCOUNT_NUMBER`, `BANK_ROUTING`, `US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER`, `CA_*`, `IN_*`, `UK_*` | 100 KB |
| Azure AI Language PII | API | `POST {endpoint}/language/:analyze-text?api-version=…` with `kind: "PiiEntityRecognition"`, `parameters {modelVersion, piiCategories[], redactionPolicies[] {policyKind ∈ syntheticReplacement | characterMask (+ redactionCharacter) | noMask | entityMask, entityTypes?}, confidenceScoreThreshold {default, overrides[]}, disableEntityValidation, entitySynonyms, valueExclusionPolicy}`, `analysisInput.documents[] {id, language, text}` | `results.documents[] {id, redactedText, entities[] {text, category, offset, length, confidenceScore}, warnings}` | four policy kinds above; synthetic replacement in preview | categories like `Person`, `PhoneNumber`, `USSocialSecurityNumber` (PascalCase), `domain: phi` for health | per the data-limits page; GA `2026-05-01`, preview `2026-05-15-preview` as labelled on the how-to |
| Google Sensitive Data Protection (Cloud DLP) | API | `POST https://dlp.googleapis.com/v2/{parent}/content:inspect` with `inspectConfig {infoTypes[], minLikelihood, limits.maxFindingsPerRequest, includeQuote, customInfoTypes[], ruleSet[]}`, `item`; `content:deidentify` with `deidentifyConfig` | findings with `infoType`, `likelihood` ∈ `VERY_UNLIKELY`, `UNLIKELY`, `POSSIBLE` (default floor), `LIKELY`, `VERY_LIKELY`, location, optional quote | `replaceConfig`, `redactConfig`, `characterMaskConfig`, `cryptoHashConfig`, `dateShiftConfig` (also format-preserving encryption and bucketing per the transformation reference, *unverified* this pass) | infoType names (`EMAIL_ADDRESS`, `US_SOCIAL_SECURITY_NUMBER`, …; list not fetched) | "limits on input size" (value not on page) |
| Private AI / Limina | API or container | `process/text` (detect + redact) and `analyze/text` / `ner/text` (detect only) with `entity_detection {entity_types[] {type: ENABLE | DISABLE, value[]}, accuracy}` | entities with spans; redacted or synthetic text | redact, mask, synthetic replacement | ~50+: `NAME`, `NAME_GIVEN`, `NAME_FAMILY`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `SSN`, `CREDIT_CARD`, `CVV`, `BANK_ACCOUNT`, `LOCATION_ADDRESS`, `DOB`, `CONDITION`, `DRUG`, … each mapped to GDPR/CPRA/HIPAA/QPA/APPI columns | not fetched |
| Nightfall | API | `POST https://api.nightfall.ai/v3/scan` with `payload[]` strings and inline `detectionRules` or `policyUUIDs[]`; detectors `NIGHTFALL_DETECTOR` (for example `API_KEY`) | one findings list per payload item | n/a (DLP alerting) | PII, PHI, PCI, banking, **API keys, passwords**, network | 500 KB aggregate, 50,000 items |
| AWS Bedrock Guardrails PII | API (inside `ApplyGuardrail`) | see moderation-and-safety.md | `sensitiveInformationPolicy.piiEntities[] {type, match, action ∈ ANONYMIZED | BLOCKED | NONE, detected}`, `regexes[]`, `outputs[].text` | anonymize or block | 31 types: `ADDRESS`, `AGE`, `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `CA_HEALTH_NUMBER`, `CA_SOCIAL_INSURANCE_NUMBER`, `CREDIT_DEBIT_CARD_CVV`, `CREDIT_DEBIT_CARD_EXPIRY`, `CREDIT_DEBIT_CARD_NUMBER`, `DRIVER_ID`, `EMAIL`, `INTERNATIONAL_BANK_ACCOUNT_NUMBER`, `IP_ADDRESS`, `LICENSE_PLATE`, `MAC_ADDRESS`, `NAME`, `PASSWORD`, `PHONE`, `PIN`, `SWIFT_CODE`, `UK_NATIONAL_HEALTH_SERVICE_NUMBER`, `UK_NATIONAL_INSURANCE_NUMBER`, `UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER`, `URL`, `USERNAME`, `US_BANK_ACCOUNT_NUMBER`, `US_BANK_ROUTING_NUMBER`, `US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER`, `US_PASSPORT_NUMBER`, `US_SOCIAL_SECURITY_NUMBER`, `VEHICLE_IDENTIFICATION_NUMBER` | per-policy units |

The entity vocabularies rhyme (Comprehend and Bedrock are near-identical,
unsurprisingly) but diverge in casing (`US_SSN` / `SSN` /
`USSocialSecurityNumber` / `US_SOCIAL_SECURITY_NUMBER`), granularity
(`NAME` vs `NAME_GIVEN`/`NAME_FAMILY` vs `PERSON`), and confidence semantics
(float score, 0–1 confidence, five-band likelihood). That is the same
honesty problem as moderation categories, with the same answer: open codes
plus a verbatim native lane, span offsets preserved in the input's own
indexing (code points vs UTF-16 vs bytes — Azure documents offset encoding
choices; Comprehend uses character offsets; DLP offers byte and code-point
ranges), and no cross-lane rescaling.

### Output validation frameworks

| Framework | Model | Integration surface | Status / license |
|---|---|---|---|
| Guardrails AI | `Guard().use(validator, …)`, `guard.validate(text)`, `Guard.for_pydantic(output_class, prompt)` for structured output (function calling or prompt optimization); validators installed from Guardrails Hub (for example `RegexMatch`, `CompetitorCheck`, `ToxicLanguage`); `on_fail` actions (only `OnFailAction.EXCEPTION` shown on the README; `reask`/`fix`/`filter`/`refrain`/`noop` *unverified* this pass) | library, or `guardrails start` server exposing `http://localhost:8000/guards/<guard-name>/openai/v1/` as an OpenAI-compatible proxy | active; Apache 2.0 |
| NVIDIA NeMo Guardrails | input, dialog, retrieval, execution, output rails; Colang flows; YAML config directory; "LLM self-checking"; integrations with LlamaGuard, Presidio, ActiveFence and other moderation APIs | library, or `nemoguardrails server --config ./config --port 8000` exposing `/v1/chat/completions` with a `config_id` field | active; license not on the page (*unverified*) |
| Rebuff (Protect AI) | four layers: heuristics, LLM-based detection, vector DB of past attacks, canary tokens; `rb.detect_injection(user_input)` → `injection_detected` | library/SDK | **archived** 2025-05-16, "still a prototype"; Apache-2.0 |
| LLM Guard (Protect AI) | prompt scanners (`PromptInjection`, `Anonymize`, `Secrets`, `Toxicity`, …) and output scanners (`Sensitive`, `Relevance`, `Bias`, …) | library | **no longer maintained** (last release 2025-05); MIT |

Both live frameworks sit *in front of* an OpenAI-shaped chat endpoint and
return a chat completion; they have no wire dialect of their own beyond
`config_id` / guard name. They are consumers of ocai, not providers.

### Prompt-injection and jailbreak detection (cross-reference)

| Detector | Shape | Where it lives in ocai |
|---|---|---|
| Azure Prompt Shields | `text:shieldPrompt {userPrompt, documents[] ≤ 5}` → `userPromptAnalysis.attackDetected`, `documentsAnalysis[].attackDetected`; subtypes (rule change, conversation mockup, role-play, encoding; document attacks: manipulated content, intrusion, information gathering, availability, fraud, malware); Spotlighting (base-64 tagging of documents, Chat Completions only, preview) | moderation capability, category `prompt_attack` (see moderation-and-safety.md) |
| Bedrock `PROMPT_ATTACK` content filter | `contentPolicy.filters[] {type: PROMPT_ATTACK, confidence, action}` | same |
| Gemini `HARM_CATEGORY_JAILBREAK` | safety setting + rating inside chat | chat IR extension / `FinishInfo` |
| Mistral jailbreaking | guardrail category (guide); API key *unverified* | moderation |
| Lakera / Check Point | `POST /v2/guard {messages[], project_id, payload, breakdown, metadata {user_id, session_id, ip_address, internal_request_id}, dev_info}` → `flagged`, `payload[]`, `breakdown[] {project_id, policy_id, detector_id, detector_type (free string), detected, message_id}`; confidence `l1_confident` … `l5_unlikely`, `no_level`; categories Prompt Defense, Content Moderation, Data Leakage Prevention, Malicious links, Agent Behavior Defense (tool allow/deny), Custom (beta) | moderation (policy-ref edge) |
| Llama Guard 4 | prompt-format classifier; no injection category by default | moderation via chat-backed adapter |

### Secrets detection

Only Nightfall exposes a dedicated secrets detector family (`API_KEY` and
friends) as an API; Comprehend and Bedrock cover `AWS_ACCESS_KEY` /
`AWS_SECRET_KEY` / `PASSWORD` inside PII; Presidio has `CRYPTO`
(wallet addresses) and relies on custom regex recognizers for keys. The
widely used scanners for code (gitleaks, trufflehog) are local tools without
an inference-time API and were not surveyed. ocai already has one secrets
rule that matters more than any detector: credentials are applied at the
driver leaf after every hook and never appear in `raw`, reports or
`provider_options` (rule 13); a secrets-detection interceptor must therefore
never see them either, which the hook ordering already guarantees.

## Verdict: hooks and interceptors first, one capability maybe

The architecture gives three homes for this family, and the survey sorts
cleanly into them:

1. **Policy hooks returning `Decision`s** (`Proceed | Retry | Fail |
   Return`, §4/§5). Output validation (Guardrails AI style re-ask, refuse,
   fix), prompt-injection *blocking*, and "refuse if PII detected" are
   decisions about a request or response, taken from inspection of
   pure IR. They need no wire dialect of their own. A platform package
   implements them as hooks that *call* a moderation/PII port when they need
   a detector; the kernel contributes the hook protocol and nothing else.
   `Return` is the right decision for "reply with a canned refusal";
   `Retry` with a modified request is the re-ask pattern; `Fail` raises the
   taxonomy error (`ContentFilterError`) so callers see one vocabulary
   regardless of which detector fired.
2. **Port-tier `CallInterceptor`s** for *transformations* that apply to local
   and remote adapters alike: redact PII in the request before the codec
   sees it, re-identify in the response, attach a validation verdict to the
   `CallResult`. Interceptors compose over any port, so a PII redactor built
   once covers chat, embedding, batch items and moderation itself. Because
   interceptors run before credentials are applied (rule 13), they can never
   leak a key; because they run *inside* the port call, their changes are
   visible to the report — an interceptor that rewrites a request must add
   a `SemanticShift` to `CallResult.report` naming what it replaced, so a
   redacted call is never confused with the original (honest reporting
   extends to ocai's own edits).
3. **A capability** only where wire dialects vary — the §11 litmus. PII
   detection/redaction qualifies: six surveyed services, six request shapes,
   three confidence lanes, four redaction vocabularies. If a product needs
   provider-switchable PII redaction (local Presidio in dev, Azure or DLP in
   production, Bedrock Guardrails on AWS), it should be
   `Capability("pii")` with `("pii","detect.request/response")` and
   `("pii","redact.request/response")`, a `PiiFinding(code, native, span,
   score | None, likelihood | None)` with open entity codes, a `Redaction`
   open code (`mask`, `entity_label`, `synthetic`, `hash`, `encrypt`) and
   per-provider census for unsupported modes. It is kernel-adjacent: it
   imports core only, is consumed by the interceptor above, and is the
   natural second use of the moderation IR's `redacted` lane. Presidio as a
   local in-process adapter would be the port-plane peer proof (H3's
   pattern) for this capability.

What should **not** become a capability: output validators (no dialect; the
validator *is* the policy), NeMo/Guardrails servers (they are OpenAI-shaped
chat endpoints — ocai talks to them through the existing chat plugin with a
`provider_options` `config_id`), secrets scanning (a local interceptor
reading pure IR text; vendors differ only in regex sets).

## Priority

- **P2 — hook and interceptor substrate exercised with one real detector.**
  The protocols exist (`Decision` hooks, `CallInterceptor`); they freeze at
  v1.0 only after being exercised through a migration and a failover (ADR
  0005). A PII-redaction interceptor backed by a local Presidio adapter is a
  cheap, dependency-free (`import-linter` permitting an optional extra)
  exercise that also validates the "interceptor edits are reported" rule
  before the hook protocols freeze. One WU.
- **P3 — `pii` capability with remote edges** (Azure Language, Bedrock
  Guardrails via the moderation edge, DLP). Build after moderation lands so
  the `redacted` lane and `policy` refs are shared, and only when a product
  needs provider-switchable redaction. One WU per two providers.
- **Not planned — validation frameworks and injection detectors as kernel
  features.** Injection detection rides the moderation capability's
  `prompt_attack` code; validation is platform policy; both are documented
  as such in the platform README when it exists.

## Sources (read 2026-11-10)

- https://presidio.dataprivacystack.org/supported_entities/
- https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html
- https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview
- https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/how-to/redact-text-pii
- https://docs.cloud.google.com/sensitive-data-protection/docs/reference/rest/v2/projects.content/inspect
- https://docs.cloud.google.com/sensitive-data-protection/docs/reference/rest/v2/InspectConfig
- https://docs.cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data
- https://docs.private-ai.com/entities/supported-entity-types.md
- https://docs.private-ai.com/fundamentals/analyze-text
- https://help.nightfall.ai/developer-api/key-concepts/text_scan
- https://developer.nightfall.ai/reference
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailPiiEntityFilter.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html
- https://cdn.jsdelivr.net/gh/guardrails-ai/guardrails@main/README.md
- https://docs.nvidia.com/nemo/guardrails/latest/index.html
- https://github.com/protectai/rebuff
- https://cdn.jsdelivr.net/gh/protectai/llm-guard@main/README.md (status via search snippet)
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection
- https://docs.lakera.ai/api-reference/lakera-api/guard/screen-content.md
- https://docs.lakera.ai/docs/defenses.md
