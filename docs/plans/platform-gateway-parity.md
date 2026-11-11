# Gateway competitive feature program

Source: maintainer request on 2026-11-11 to include the gateway features identified
by the competitive review, in addition to access/ABAC. Status: proposed WUs;
none of these entries asserts implementation or feature parity.

The [gateway console program](platform-gateway.md) owns WU-82–105 and its lettered
foundations. This companion assigns WU-107–134 to remaining gateway workflows.
WU-106 is allocated to the independent CI-latency work in PR #123.
It inherits that program's scope, attribute, audit, credential, provenance,
revocation, fixture, migration and gate contracts. Each new endpoint extends the
WU-101 inventory and the WU-103 qualification profile in its own PR; the completed
baseline is not retrospectively claimed to qualify a new feature.

## Competitive feature coverage

| Capability | Owning WUs | Release evidence |
|---|---|---|
| Users, organizations, projects, teams, environments, compartments | 73–80, 82a–82i, 101 | Scoped lifecycle, RBAC/ReBAC/ABAC and revocation matrix |
| Enterprise SSO, provisioning, workload identity, custom roles | 119–121, 130–131 | Qualified protocol profiles, delegation ceilings and deprovisioning |
| Provider credentials, rotation and external vaults | 83, 122 | Sealed/versioned credentials and leaf-only application |
| Qualified model/deployment discovery | 84–85, 98–99, 128 | Supported-operation matrix and safe connect examples |
| Chat, Responses, native Messages, embeddings, multimodal chat | 87–88, 107–108, 133–134 | Recorded wire/stream contract tests per exposed operation |
| Retries, deadlines, failover, balancing and circuit recovery | 86–89, 109 | Current-policy eligibility on every attempt, bounded retry budget |
| Rate/concurrency controls and multi-scope budgets | 89–92a | Concurrent reservation/recovery tests and explicit uncertainty |
| Exact and semantic response caching | 110, 132 | Authorization partitioning, invalidation and honest reuse evidence |
| Provider prompt caching | library 66–68; gateway 90–91 | Provider-reported consumption and priced cache dimensions; not response caching |
| Guardrails, sensitive-data checks and redaction | 111–112 | Versioned adapters, fixture census and explicit streaming limits |
| Receipts, sessions, user attribution, analytics and alerts | 90–97 | Authorized aggregates, immutable attribution and safe delivery |
| Application tracing and gateway operational metrics | 113, 126 | OTLP collector tests, measured timing and bounded cardinality |
| Audit search/export and evidence lifecycle | 94, 114, 127 | Separate metadata/content permissions and retained scope on export |
| Prompt versions and governed prompt invocation | 115–116 | Pinned versions, validated inputs and ordinary invocation controls |
| Datasets and model/prompt evaluations | 117–118 | Source lineage, reproducible scores and attributable evaluation cost |
| Migration, canary, rollback and shadow traffic | 100, 104–105, 129 | Independent approval, qualified destinations and bounded experiments |
| Configuration as code and management automation | 123 | Secret-free plan/diff/apply with optimistic versions and audit |
| Replicated customer-hosted operation and disaster recovery | 124–126 | Real restart/drain/restore tests with measured limits |

## Milestones and sequencing

- **Governed gateway pilot:** WU-82–105 with their access prerequisites. This is
  the first complete customer workflow, not a claim of broad market parity.
- **Competitive gateway operations:** WU-109–114, 119–124, 126, 128, 130–131;
  add provider/front-door coverage only when the library evidence is available.
- **Development and improvement workflows:** WU-115–118 and 129, then optional
  semantic reuse WU-132. Basic quality comparison is scoped here; a complete Arize
  or Langfuse replacement is not promised.
- **Recoverable enterprise operation:** WU-125 and 127, alongside supported
  deployment qualification. Recovery/retention claims require their evidence.

These groups express product milestones, not a single serial schedule. Deps are
explicit per entry and shared files are sequenced or isolated by worktree. WU-126
uses the baseline qualification before WU-124 tests replication; WU-125 then tests
restoration. Do not introduce a cycle by making the baseline depend on these
later operational profiles.

## Scope boundaries and implementation dependencies

Library work remains owned by the independent public-library track. WU-107–108
and 133–134 may be defined before their required public artifacts are qualified;
their Open bullets explicitly gate implementation. Existing integration WUs
61–70 are consumed, not reimplemented. No private codec, SDK dependency or bare
result is an acceptable shortcut. Implementation discovery of a missing library
contract must add evidence to `gaps.md` and obtain a separately defined library WU.

MCP/agent gateways, durable agent orchestration, RAG/source permissions, audiovisual
generation, realtime sessions, batch/file APIs, a full asset catalog and hosted
billing are adjacent products/capabilities in the [delivery sequence](../design/platform/delivery.md).
They are not implied by this inference-gateway feature set; each requires its own
bounded program and qualified capability contracts before being advertised.
Nested teams, a generic policy-expression editor, every cloud vault/IdP, and a
Terraform provider are explicit extensions to the first qualified profiles,
not hidden acceptance requirements. Basic declarative management is WU-123.

The comparison is grounded in official documentation: [LiteLLM routing](https://docs.litellm.ai/docs/routing),
[caching](https://docs.litellm.ai/docs/proxy/caching),
[guardrails](https://docs.litellm.ai/docs/proxy/guardrails/quick_start),
[enterprise features](https://docs.litellm.ai/docs/enterprise),
[Portkey features/editions](https://portkey.ai/pricing),
[Langfuse gateway roadmap](https://langfuse.com/docs/gateway/overview),
[Logfire gateway](https://pydantic.dev/docs/logfire/manage/ai-gateway/),
[Vercel budgets](https://vercel.com/docs/ai-gateway/observability-and-spend/budgets),
[Arize experiments](https://arize.com/docs/ax/quickstarts/quickstart-run-first-experiment),
and [Helicone feature index](https://docs.helicone.ai/llms.txt).
A feature being enterprise-only, beta or roadmap at a competitor does not establish
its readiness here. The first external-vault profile uses the documented
[Vault KV v2 versioned API](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2).

## WU-107 — Serve the qualified Anthropic Messages compatibility endpoint

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Applications use /v1/messages with native request/error/SSE shapes through the existing governed executor and scoped credentials.
- **Scope:** Platform `compatibility/messages` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Implementing provider dialects or advertising every native beta API.
- **Acceptance:**
  - Recorded native Messages requests and streams preserve qualified tool/usage/error semantics —
    `platform/services/gateway/tests/test_compatibility_messages.py::test_recorded_messages`
  - Keys, ABAC restrictions and no-fallback-after-output match the chat endpoint —
    `platform/services/gateway/tests/test_compatibility_messages.py::test_governance_parity`
  - Connect lists native examples only after their recorded execution tests pass —
    `platform/services/gateway/tests/test_compatibility_messages.py::test_connect_qualification`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/messages.test.ts`
- **Done:** An application completes recorded native Messages requests and streams with
  correct errors, usage and authorized fallback; unsupported cross-interface behavior is
  reported.
- **Deps:** WU-87, WU-88, WU-101; qualified public inbound/outbound Anthropic Messages codecs.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/compatibility/messages/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → messages
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[messages]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  POST /v1/messages -> shared invocation and policy -> public codecs
  request version is explicit; unsupported beta fields follow the qualified contract
  ```
- **Alternatives considered:** Translate every Messages request into a generic chat
  subset (simpler endpoint, but may lose native semantics); expose only the public-
  library-qualified native surface and report conversion limits.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Native streaming can drift from compatibility behavior; reuse execution and test native frames. Rollback disables this front door.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** Implementation waits for public-library qualification of all required native front-door codecs; package presence alone is insufficient.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-108 — Serve governed embeddings with attributable usage

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A scoped embeddings endpoint enforces model access, budgets and evidence using a qualified public CallResult-based embedding capability.
- **Scope:** Platform `compatibility/embeddings` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Implementing embedding providers in platform code, vector storage, RAG or semantic caching itself.
- **Acceptance:**
  - Recorded embedding requests enforce scope, dimensions and input limits without silently changing vectors —
    `platform/services/gateway/tests/test_compatibility_embeddings.py::test_recorded_embeddings`
  - Known/unknown consumption participates in reservation, settlement and provenance —
    `platform/services/gateway/tests/test_compatibility_embeddings.py::test_usage_and_budget`
  - Response vectors never enter metadata logs or unauthorized evidence reads —
    `platform/services/gateway/tests/test_compatibility_embeddings.py::test_vector_privacy`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/embeddings.test.ts`
- **Done:** An authorized application obtains qualified embeddings, and its receipt and
  ledger reconcile usage and known or unknown cost without a chat-shaped adapter.
- **Deps:** WU-82i, WU-92a, WU-101; independently qualified public embedding execution and pricing contracts.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/compatibility/embeddings/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → embeddings
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[embeddings]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  POST /v1/embeddings -> scoped admission -> public embedding port -> CallResult
  usage/pricing dimensions remain those reported by the qualified capability
  ```
- **Alternatives considered:** Wrap embeddings as chat calls (reuses endpoint machinery,
  but falsifies capability and usage); retain a distinct qualified capability behind
  shared admission and evidence services.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Provisional library types are not execution support. Rollback removes endpoint discovery and rejects new embedding calls.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** Not implementation-ready until the library owns qualified embedding CallResult execution and recorded pairs; create a separate library gap/WU through that track before scheduling.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-109 — Route eligible traffic with measured balancing and circuit recovery

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An application policy chooses weighted, least-busy, measured-latency or evidenced-cost ordering only after scope, ABAC and fidelity eligibility; unhealthy deployments enter bounded circuit states.
- **Scope:** Platform `routing/balancing` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** LLM-based semantic routers, guaranteed latency improvement, or replacing kernel provider-rate pacing WU-70.
- **Acceptance:**
  - Every strategy chooses only eligible candidates and records its inputs/version and selection reason —
    `platform/services/gateway/tests/test_routing_balancing.py::test_eligibility_before_strategy`
  - Recorded outage/load opens and half-opens circuits without a retry storm or cross-replica limit bypass —
    `platform/services/gateway/tests/test_routing_balancing.py::test_circuit_recovery`
  - Missing/stale latency or price uses a declared safe fallback; deterministic fixtures reproduce the decision —
    `platform/services/gateway/tests/test_routing_balancing.py::test_missing_measurements`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/balancing.test.ts`
- **Done:** A recorded outage/load scenario balances only eligible destinations, bounds
  all retries, and recovers circuits across replicas with reproducible selection
  evidence.
- **Deps:** WU-86, WU-89, WU-91, WU-103.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/routing/balancing/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → balancing
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[balancing]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  strategy = weighted | least_busy | measured_latency | evidenced_cost
  circuit = closed | open(until) | half_open(probe_budget)
  global attempt/deadline budget applies to retries and fallback together
  ```
- **Alternatives considered:** Use round-robin alone (predictable but ignores
  load/health); use adaptive strategies without evidence (responsive but
  irreproducible). Select from bounded strategies with recorded measurements and
  eligibility first.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Stale measurements and nested retries can amplify failures; bound attempts/deadlines and log selection evidence. Rollback selects the existing ordered strategy.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-110 — Cache exact responses within authorized execution scopes

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Explicitly opted-in applications reuse eligible unary responses with exact request/configuration matching, current authorization and honest cache/usage receipts.
- **Scope:** Platform `cache/exact` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Stream/tool-effect caching, semantic reuse (WU-132), or treating provider prompt caching as response caching.
- **Acceptance:**
  - Cache identity includes principal/credential restrictions, scope, compartments and relevant policy/model/prompt versions —
    `platform/services/gateway/tests/test_cache_exact.py::test_cache_identity`
  - Expiry, deletion, revocation or tightened capture policy prevents cached content release —
    `platform/services/gateway/tests/test_cache_exact.py::test_cache_invalidation`
  - Hits record origin and avoided provider execution without inventing provider usage or billing savings —
    `platform/services/gateway/tests/test_cache_exact.py::test_hit_evidence`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/exact.test.ts`
- **Done:** An identical authorized request reuses an eligible cached response with zero
  provider I/O, while changed authorization, policy or scope prevents reuse and the
  receipt identifies the hit.
- **Deps:** WU-87, WU-92a, WU-94, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/cache/exact/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → exact
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[exact]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  CachePolicy(enabled=False, ttl, permitted_operations)
  key = canonical_request + effective_access_context + configuration_versions
  cache hit -> current authorize -> audited release -> receipt(cache_hit, origin)
  ```
- **Alternatives considered:** Use an organization-wide request hash (higher hit rate,
  but crosses content and authorization boundaries); partition by effective execution
  scope and versions even when this reduces reuse.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Content reuse can leak across scopes; first profile isolates by effective principal context and stores encrypted content under explicit retention. Rollback disables reads and expires entries.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-111 — Execute versioned guardrails with explicit failure semantics

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Published gateway policies run registered bounded pre-call and post-call guardrails, report allow/block/transform decisions and prevent failover from bypassing them.
- **Scope:** Platform `guardrails/pipeline` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Arbitrary uploaded code, unapproved external data disclosure or claims that classifiers prevent every prompt injection.
- **Acceptance:**
  - A deterministic recorded guardrail blocks before provider I/O and produces an attributed decision —
    `platform/services/gateway/tests/test_guardrails_pipeline.py::test_pre_call_block`
  - Mandatory guardrail timeout/unavailable fails closed; response checks document buffered versus incremental guarantees —
    `platform/services/gateway/tests/test_guardrails_pipeline.py::test_timeout_and_stream_semantics`
  - Transformations record original/transformed references and reason without pretending conversion fidelity describes the guardrail change —
    `platform/services/gateway/tests/test_guardrails_pipeline.py::test_transform_evidence`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/pipeline.test.ts`
- **Done:** A published guardrail policy blocks or transforms the recorded cases,
  reports its version and action, and follows its declared outage and buffered/streaming
  semantics.
- **Deps:** WU-82g, WU-86, WU-88, WU-103.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/guardrails/pipeline/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → pipeline
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[pipeline]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  GuardrailBinding(adapter_id, version, phase, timeout, required, approved_destination?)
  result = allow | block | transform | unavailable
  full-response guarantee requires explicit bounded buffering, never silent streaming fallback
  ```
- **Alternatives considered:** Allow arbitrary uploaded policy code (flexible but
  unbounded execution and disclosure); use versioned qualified adapters with declared
  failure and streaming contracts.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Guardrail services are additional disclosure/availability boundaries; authorize their destinations and cap execution. Rollback keeps mandatory policy blocking until a qualified replacement exists.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-112 — Apply qualified PII and secret-redaction policies

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A first deterministic detector/redactor integrates with guardrails to block or mask configured sensitive patterns in requests, captured evidence and exports.
- **Scope:** Platform `guardrails/redaction` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Universal PII detection, arbitrary semantic redaction or automatic declassification.
- **Acceptance:**
  - Recorded positive/negative fixtures establish each supported detector and its false-positive/negative limits —
    `platform/services/gateway/tests/test_guardrails_redaction.py::test_detector_census`
  - Configured transformations are explicit and secrets/PII do not leak through logs, traces or errors —
    `platform/services/gateway/tests/test_guardrails_redaction.py::test_transform_and_secondary_paths`
  - Raw content requires a separate permitted retention policy; missing detector support cannot silently pass a mandatory rule —
    `platform/services/gateway/tests/test_guardrails_redaction.py::test_policy_and_unsupported`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/redaction.test.ts`
- **Done:** The published detector census reproduces its fixture results, redacts
  approved fields before the configured disclosure boundary, and records transformations
  without storing detected secrets.
- **Deps:** WU-111, WU-94.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/guardrails/redaction/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → redaction
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[redaction]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  DetectorProfile(id, version, supported_patterns, test_census)
  action = block | replace_with_marker; evidence = safe counts + rule/version
  no reversible mapping is retained in the initial profile
  ```
- **Alternatives considered:** Claim universal PII detection from one heuristic (easy
  positioning, unverifiable coverage); publish a detector/fixture census and explicit
  unsupported classes with configurable redaction actions.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Masking changes meaning and may miss variants; publish measured fixture coverage and record transformation evidence. Rollback blocks workloads requiring the withdrawn detector.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-113 — Export correlated gateway traces through the telemetry satellite

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Gateway attempts, policy decisions, timing and usage correlate with application traces and export to a configured OTLP collector without default payload capture.
- **Scope:** Platform `observability/traces` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Implementing the public OTel library here or claiming a gateway trace observes application tool/agent steps that were never instrumented.
- **Acceptance:**
  - A real local collector receives the request/attempt tree with trace-context provenance and recorded streaming timings —
    `platform/services/gateway/tests/test_observability_traces.py::test_correlated_export`
  - Spoofed baggage cannot change authority; payload/attribute restrictions apply before export —
    `platform/services/gateway/tests/test_observability_traces.py::test_export_privacy`
  - Collector outage/backpressure is bounded and reported without changing inference success or pretending export succeeded —
    `platform/services/gateway/tests/test_observability_traces.py::test_export_failure`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/traces.test.ts`
- **Done:** A real local OTLP collector receives correlated request/attempt spans
  without default payload capture; collector outage stays bounded and leaves accurate
  local receipts.
- **Deps:** WU-87, WU-88, WU-94; library WU-61, WU-62 and WU-63.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/observability/traces/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → traces
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[traces]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  trace -> execution -> attempts; decisions reference model/policy revisions
  export allowlist includes usage provenance, TTFT, completion and partial status
  collector destination and project binding are explicitly configured
  ```
- **Alternatives considered:** Build a private telemetry schema/exporter in the gateway
  (fast local progress, duplicates the satellite contract); consume the public telemetry
  APIs and qualify one OTLP collector profile.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Export can leak sensitive context or block execution; allowlist fields, bound buffers and report dropped export counts. Rollback disables export only.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-114 — Inspect and export scoped administrative audit evidence

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Authorized auditors search mutations, access changes and sensitive reads and export safe evidence to an approved sink with resumable delivery.
- **Scope:** Platform `audit/export` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Claiming database-admin-proof immutability, legal hold or payload export.
- **Acceptance:**
  - Search/count/export respect current project/compartment grants and separate audit permission —
    `platform/services/gateway/tests/test_audit_export.py::test_scope_and_export`
  - Export resumes after failure with stable event IDs and exposes duplicates/gaps honestly —
    `platform/services/gateway/tests/test_audit_export.py::test_delivery_recovery`
  - Raw credentials, payloads, policy attributes and inaccessible resource identifiers are absent —
    `platform/services/gateway/tests/test_audit_export.py::test_audit_allowlist`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/export.test.ts`
- **Done:** An authorized auditor searches and exports only permitted administrative
  events, with stable ordering/IDs, explicit delivery semantics, and no inference
  payload access.
- **Deps:** WU-101, WU-96.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/audit/export/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → export
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[export]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  AuditCursor(scope, last_event_id); export = allowlisted event + source revision
  destination policy and exporter service identity rechecked for each batch
  ```
- **Alternatives considered:** Reuse request-history authorization for admin audit (less
  UI, but conflates payload and administrative access); give audit search/export
  distinct permissions and stable event semantics.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** An audit export is a new disclosure path; validate destination and current grants before batches. Rollback pauses delivery while retaining durable cursors/events.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-115 — Version prompt templates with scoped publication

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Project teams create immutable prompt-template versions, validate input schemas and promote explicit environment labels with audit.
- **Scope:** Platform `prompts/registry` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Full asset catalog, agent builder, executable templates or prompt execution (WU-116).
- **Acceptance:**
  - Template inputs are typed and rendering is deterministic with bounded size and no executable expressions —
    `platform/services/gateway/tests/test_prompts_registry.py::test_template_validation`
  - Draft/publication/label changes require scoped permissions and preserve earlier version references —
    `platform/services/gateway/tests/test_prompts_registry.py::test_version_and_publish`
  - Prompt content obeys compartment read restrictions independently of metadata visibility —
    `platform/services/gateway/tests/test_prompts_registry.py::test_prompt_content_access`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/registry.test.ts`
- **Done:** A prompt author publishes an immutable validated version to an authorized
  environment label; stale publication conflicts and forbidden content reads are denied.
- **Deps:** WU-82h, WU-85, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/prompts/registry/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → registry
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[registry]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  PromptVersion(id, project, compartments, version, input_schema, template, digest)
  EnvironmentLabel(name, prompt_version, version); labels are mutable audited pointers
  ```
- **Alternatives considered:** Store editable prompt strings on applications (fewer
  objects, loses reproducibility); version templates independently and move environment
  labels through audited publication.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Labels can conceal changed behavior; resolve to immutable versions before execution. Rollback moves the label with audit and preserves history.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-116 — Invoke published prompts through governed application bindings

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An application binds a published prompt version and validated inputs to the existing gateway path, with rendered prompt/version attribution and ordinary budgets/guardrails.
- **Scope:** Platform `prompts/execution` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Agent workflows, tool execution or changing caller payloads without an explicit prompt-binding contract.
- **Acceptance:**
  - An environment label resolves once to a version and rendered inputs are validated before provider I/O —
    `platform/services/gateway/tests/test_prompts_execution.py::test_version_resolution`
  - Prompt invocation applies the same scope, guardrails, budgets and receipt evidence as direct requests —
    `platform/services/gateway/tests/test_prompts_execution.py::test_governed_execution`
  - Callers cannot substitute a hidden template or widen its compartment/classification —
    `platform/services/gateway/tests/test_prompts_execution.py::test_template_scope`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/execution.test.ts`
- **Done:** An application invokes a pinned published prompt through ordinary routing,
  guardrails and admission, with exact template/input provenance and separately
  attributed usage.
- **Deps:** WU-115, WU-111, WU-92a.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/prompts/execution/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → execution
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[execution]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  ApplicationPromptBinding(application, environment, published_prompt_ref, version)
  validated inputs -> pinned rendered template -> ordinary invocation pipeline
  ```
- **Alternatives considered:** Render templates solely in the client (less gateway code,
  loses controlled provenance); resolve a published binding server-side and keep
  ordinary invocation policy/admission intact.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Template versions and cache entries can diverge; pin render/version hashes and include them in reuse policy. Rollback disables bindings without changing stored prompts.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-117 — Curate scoped datasets from authorized request evidence

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Authorized reviewers create versioned evaluation datasets from recorded fixtures or permitted captured requests, retaining source lineage and access restrictions.
- **Scope:** Platform `evaluation/datasets` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** General dataset warehouse, automatic synthetic-data generation or model fine-tuning.
- **Acceptance:**
  - Adding a captured example requires current content access and records lineage without widening scope —
    `platform/services/gateway/tests/test_evaluation_datasets.py::test_source_authority`
  - Dataset versions are immutable and deletion/revocation updates derived-example availability —
    `platform/services/gateway/tests/test_evaluation_datasets.py::test_lineage_and_revocation`
  - Import/export validates schemas, sizes and permissions and excludes secrets —
    `platform/services/gateway/tests/test_evaluation_datasets.py::test_dataset_io`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/datasets.test.ts`
- **Done:** An authorized curator creates a versioned dataset from permitted evidence;
  lineage remains traceable, and source revocation/deletion is enforced by the
  documented dataset policy.
- **Deps:** WU-94, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/evaluation/datasets/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → datasets
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[datasets]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  DatasetVersion(scope, compartments, version, example_refs, source_revision_refs)
  Example(input_ref, expected_output_ref?, source_execution?, permitted_uses)
  ```
- **Alternatives considered:** Copy payloads into untracked dataset rows (simple
  ingestion, loses source restrictions); retain explicit lineage, version snapshots and
  qualified revocation/deletion semantics.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Copying evidence can bypass deletion/access; keep tracked lineage and reauthorize downstream use. Rollback disables new versions and keeps retention enforcement.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-118 — Compare governed model and prompt changes with evaluations

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An authorized evaluator compares pinned candidates on a versioned dataset with deterministic scorers and optional bounded live model judging, linked to executions and cost.
- **Scope:** Platform `evaluation/experiments` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Rebuilding all Arize/Langfuse analytics or automatic promotion based on unqualified judges.
- **Acceptance:**
  - Recorded baseline/candidate runs reproduce scores with scorer, prompt, model and dataset versions —
    `platform/services/gateway/tests/test_evaluation_experiments.py::test_comparison_reproducibility`
  - Optional live runs require approved destinations, invocation/content grants and dedicated budgets —
    `platform/services/gateway/tests/test_evaluation_experiments.py::test_live_run_authority`
  - Missing/failed scores remain unknown, judging costs are attributed and no unsupported quality verdict is shown —
    `platform/services/gateway/tests/test_evaluation_experiments.py::test_score_provenance`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/experiments.test.ts`
- **Done:** A recorded model/prompt comparison produces reproducible metric results,
  input/version lineage, and reconciled evaluation usage; optional live judges require
  explicit approval and budgets.
- **Deps:** WU-117, WU-116, WU-104, WU-92a.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/evaluation/experiments/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → experiments
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[experiments]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  Experiment(dataset_version, candidate_versions, scorer_versions, execution_refs)
  Score(value?, outcome, evaluator_version, evidence_ref); human review is explicit
  quality evidence complements conversion reports; it does not redefine fidelity
  ```
- **Alternatives considered:** Make live LLM judging mandatory (broad qualitative
  signals, nondeterministic cost/results); qualify deterministic offline metrics first
  and make governed live judging an explicit opt-in.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Judges can leak data and produce noisy scores; use explicit destinations, bounded runs and uncertainty labels. Rollback stops queued runs and preserves completed evidence.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-119 — Provision users and teams through scoped SCIM synchronization

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** One qualified SCIM 2.0 profile provisions users/groups into organization memberships/teams with stable external bindings and tested deprovisioning.
- **Scope:** Platform `access/scim` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Every IdP dialect, nested groups or treating SCIM groups as arbitrary platform permissions.
- **Acceptance:**
  - Create/update/PATCH/deactivate replay idempotently using organization-bound external identifiers —
    `platform/services/gateway/tests/test_access_scim.py::test_scim_lifecycle`
  - Group synchronization cannot create owner/content grants or cross organization scope —
    `platform/services/gateway/tests/test_access_scim.py::test_group_mapping_limits`
  - Deactivation revokes access and relevant human credentials while preserving independent service accounts —
    `platform/services/gateway/tests/test_access_scim.py::test_deprovisioning`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/scim.test.ts`
- **Done:** The qualified SCIM profile provisions a user and group, tolerates retries,
  and deprovisions their authority without email-based identity merging or automatic
  owner grants.
- **Deps:** WU-82c, WU-82e, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/access/scim/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → scim
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[scim]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  SCIM integration(org, credential, attribute_mapping_version, allowed_team_mappings)
  externalId maps within its integration; email is not an account-linking key
  ```
- **Alternatives considered:** Merge accounts by email (convenient provisioning, unsafe
  identity collision); bind stable issuer/provider IDs and require explicit linking for
  pre-existing identities.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Provisioning retries and renamed identities can resurrect access; use tombstones/version checks and deny stale updates. Rollback disables sync without undoing revocations.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-120 — Delegate custom roles through bounded permission templates

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Authorized grant administrators define versioned custom permission sets within their delegation ceiling and assign them at existing resource scopes.
- **Scope:** Platform `access/custom_roles` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Custom executable policy expressions or removal of fixed starter templates.
- **Acceptance:**
  - Unknown permissions, privilege expansion and content-grant shortcuts are rejected —
    `platform/services/gateway/tests/test_access_custom_roles.py::test_delegation_ceiling`
  - Role edits produce versions, projection and immediate current-policy enforcement —
    `platform/services/gateway/tests/test_access_custom_roles.py::test_role_version_revocation`
  - Effective-access explanations and endpoint matrix include custom templates —
    `platform/services/gateway/tests/test_access_custom_roles.py::test_custom_role_matrix`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/custom_roles.test.ts`
- **Done:** A delegated administrator publishes a bounded custom permission template and
  binding; escalation attempts fail and template changes invalidate affected
  authorization decisions.
- **Deps:** WU-82e, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/access/custom_roles/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → custom_roles
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[custom roles]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  CustomRole(scope, version, permission_set, created_by)
  grant ceiling constrains both role definition and binding; mandatory ABAC remains
  ```
- **Alternatives considered:** Expose arbitrary authorization expressions (very
  flexible, hard to bound delegation); version named permission subsets under the
  grantor ceiling and mandatory restrictions.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Role edits have broad impact; simulate affected grants, audit versions and fail closed during projection. Rollback cannot restore removed privileges implicitly.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-121 — Authenticate one federated Kubernetes workload profile

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A qualified Kubernetes service-account OIDC token maps to an explicit platform service account and scoped invocation without a stored long-lived client secret.
- **Scope:** Platform `identity/workload_federation` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** All clouds/CI issuers or preview agent delegation.
- **Acceptance:**
  - The configured issuer, audience, namespace and service-account binding are validated against a real disposable cluster profile —
    `platform/services/gateway/tests/test_identity_workload_federation.py::test_workload_binding`
  - Foreign audience/issuer, expired tokens and spoofed claims cannot select another principal —
    `platform/services/gateway/tests/test_identity_workload_federation.py::test_token_substitution`
  - Platform suspension revokes access independently of token lifetime and JWKS outage follows the declared bound —
    `platform/services/gateway/tests/test_identity_workload_federation.py::test_revocation_and_outage`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/workload_federation.test.ts`
- **Done:** A workload in the reference Kubernetes cluster invokes with a short-lived
  federated identity only under the bound issuer, audience and subject; rotation and
  revocation tests pass.
- **Deps:** WU-79, WU-82i, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/identity/workload_federation/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → workload_federation
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[workload federation]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  FederatedBinding(issuer, audience, namespace, service_account, platform_principal)
  configured issuer only; no token-selected discovery endpoint; exact subject mapping
  ```
- **Alternatives considered:** Start with every cloud federation provider (wide
  coverage, weak qualification); prove one Kubernetes OIDC profile and extend issuer
  profiles with separate evidence.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Issuer/profile drift can widen trust; pin the qualified cluster/token profile and test rotation. Rollback removes the binding and requires an existing qualified credential.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-122 — Resolve provider credentials from a qualified external vault

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A scoped connection references a versioned HashiCorp Vault KV v2 secret; the gateway resolves it with explicit installation credentials and applies it only at the driver leaf.
- **Scope:** Platform `secrets/vault` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** All cloud vaults, ambient credential discovery, storing vault tokens in user configuration or introducing provider SDKs.
- **Acceptance:**
  - A real disposable Vault fixture supplies an explicitly authorized secret version without management/API exposure —
    `platform/services/gateway/tests/test_secrets_vault.py::test_versioned_resolution`
  - Denied path, deleted version, expired vault credential and vault outage fail closed without stale-secret fallback —
    `platform/services/gateway/tests/test_secrets_vault.py::test_vault_failure`
  - Rotation records secret-version evidence without secret values; gateway hooks and receipts never receive plaintext —
    `platform/services/gateway/tests/test_secrets_vault.py::test_rotation_isolation`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/vault.test.ts`
- **Done:** A qualified Vault KV v2 credential version is applied only at the provider
  driver leaf; rotation, vault outage and revoked access have tested behavior without
  management plaintext exposure.
- **Deps:** WU-83, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/secrets/vault/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → vault
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[vault]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  VaultSecretRef(mount, path, version); endpoint/auth configured explicitly
  resolution -> in-memory credential -> driver leaf; record only safe reference/version
  ```
- **Alternatives considered:** Copy vault secrets into gateway storage (simpler steady-
  state reads, duplicates secret lifecycle); resolve explicit version references at the
  credential leaf under a qualified failure policy.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Vault availability affects attempts and paths can leak naming; scope references and bound resolution. Rollback uses an explicitly provisioned sealed connection, never an automatic fallback.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-123 — Apply declarative gateway configuration with a reviewed diff

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Operators export secret-free configuration and plan/apply version-checked changes through the same authorized management services used by the console.
- **Scope:** Platform `configuration/declarative` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Hand-editing database state, a Terraform provider in this WU, or undocumented all-or-nothing guarantees.
- **Acceptance:**
  - Export contains resource references and versions but no secrets or inaccessible configuration —
    `platform/services/gateway/tests/test_configuration_declarative.py::test_safe_export`
  - Plan reports create/update/conflict effects without mutation; apply rejects stale versions or excessive scope —
    `platform/services/gateway/tests/test_configuration_declarative.py::test_plan_apply`
  - Interrupted apply reports completed operations and resumes idempotently without claiming cross-service atomicity —
    `platform/services/gateway/tests/test_configuration_declarative.py::test_resume`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/declarative.test.ts`
- **Done:** An operator exports a secret-free configuration, reviews a versioned diff,
  applies it with conflict checks, and resumes a partially failed application without
  claiming global atomicity.
- **Deps:** WU-101, WU-92a, WU-86.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/configuration/declarative/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → declarative
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[declarative]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  gateway config export | plan FILE | apply PLAN --expected-revision REV
  stable external names map to scoped IDs; secrets are references supplied separately
  ```
- **Alternatives considered:** Ship a Terraform provider first (familiar tooling,
  introduces provider lifecycle before API convergence); qualify neutral
  export/plan/apply first and leave adapters independent.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Automation amplifies mistakes; use explicit scopes, reviewed plans and normal audit. Rollback is a new version-checked plan, not database restoration.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-124 — Qualify a replicated customer-hosted gateway deployment

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A reference deployment runs multiple console/gateway/projector replicas with explicit database/issuer/FGA dependencies, graceful draining and scoped configuration.
- **Scope:** Platform `operations/replicated_deployment` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Managed SaaS, multi-region active-active or automatic database failover claims.
- **Acceptance:**
  - Recorded load across replicas preserves authorization, reservations and session behavior during a replica restart —
    `platform/services/gateway/tests/test_operations_replicated_deployment.py::test_replica_restart`
  - Graceful draining terminates streams with explicit outcomes and prevents duplicate admissions —
    `platform/services/gateway/tests/test_operations_replicated_deployment.py::test_drain`
  - Readiness reflects dependency failures and supports controlled recovery without insecure startup fallbacks —
    `platform/services/gateway/tests/test_operations_replicated_deployment.py::test_dependency_recovery`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/replicated_deployment.test.ts`
- **Done:** The reference replicated deployment survives the documented restart/drain
  scenario while preserving authorization, admission and receipt invariants within
  published measured limits.
- **Deps:** WU-103, WU-126.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/operations/replicated_deployment/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → replicated_deployment
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[replicated deployment]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  pinned deployment artifacts + external secret inputs + health/readiness contracts
  replicas share authoritative state; no per-process correctness assumptions
  ```
- **Alternatives considered:** Infer HA from two running replicas (quick setup, no
  crash/drain proof); qualify the reference topology with shared-state and in-flight
  fault scenarios and publish its limits.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Replication can expose hidden local state; run the real multi-replica fixture and publish measured limits. Rollback follows a tested compatible deployment version.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-125 — Restore a gateway installation with consistent authorization and evidence

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Operators restore the supported platform databases/configuration and externally managed key material into an isolated installation, then reconcile projection before accepting traffic.
- **Scope:** Platform `operations/restore` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Guaranteed zero data loss, automatic legal-hold handling or backing up secret material into ordinary artifacts.
- **Acceptance:**
  - A real backup/restore fixture recovers scoped configuration and encrypted evidence with explicit key availability —
    `platform/services/gateway/tests/test_operations_restore.py::test_restore`
  - Revocation watermark and restored grants cannot resurrect authority; expired sessions/keys remain unusable —
    `platform/services/gateway/tests/test_operations_restore.py::test_restore_revocation`
  - Measured recovery time/data-loss boundaries and operator steps are reported from evidence —
    `platform/services/gateway/tests/test_operations_restore.py::test_recovery_report`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/restore.test.ts`
- **Done:** A clean reference installation restores the tested backup set, reconciles
  authorization and key references before admission, and produces a measured recovery
  report with declared data loss.
- **Deps:** WU-124, WU-82b, WU-94.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/operations/restore/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → restore
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[restore]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  restore manifest = database snapshots + schema/model revisions + key references
  start unavailable -> reconcile authorization and retention -> qualify -> admit
  ```
- **Alternatives considered:** Restore databases independently (simple tooling,
  inconsistent authorization/evidence); qualify a coordinated restore procedure with
  reconciliation before enabling admission.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** An older backup can resurrect credentials; require a qualified revocation recovery strategy or invalidate affected credentials. Rollback keeps the restore isolated.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-126 — Measure gateway service health and operational limits

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Operators see bounded-cardinality operational metrics and measured latency/availability under declared load, separate from provider inference and export delivery.
- **Scope:** Platform `operations/metrics` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** An arbitrary performance promise or a general observability backend.
- **Acceptance:**
  - Metrics separate admission, authorization, queue, gateway overhead, TTFT and provider latency —
    `platform/services/gateway/tests/test_operations_metrics.py::test_metric_semantics`
  - Unknown usage, partial streams, dropped telemetry and projection lag are explicit signals without secret/high-cardinality labels —
    `platform/services/gateway/tests/test_operations_metrics.py::test_operational_signals`
  - A recorded load/failure campaign emits a reproducible capacity report with conditions and no invented SLO guarantee —
    `platform/services/gateway/tests/test_operations_metrics.py::test_capacity_report`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/metrics.test.ts`
- **Done:** The reference load run produces bounded-cardinality metrics and a report
  separating gateway/provider timing, errors and saturation; its operational limits are
  measured rather than inferred.
- **Deps:** WU-103, WU-113, WU-96.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/operations/metrics/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → metrics
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[metrics]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  metrics allowlist + bounded dimensions + histogram definitions
  report = workload profile + versions + measured distributions + failure behavior
  ```
- **Alternatives considered:** Use provider latency as total service health (easy
  metric, hides gateway queues); separate measured timing stages and publish bounded-
  cardinality operational metrics.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Misleading latency metrics hide bottlenecks; test timing boundaries and cardinality. Rollback removes optional dashboards/export without changing admission behavior.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-127 — Govern evidence retention and approved export destinations

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An organization configures bounded retention for metadata/audit/evaluation artifacts and approved export destinations, with per-scope restrictions and deletion evidence.
- **Scope:** Platform `governance/evidence_lifecycle` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Legal-hold workflows, regulatory certification or a claim that gateway locality proves end-to-end residency.
- **Acceptance:**
  - Retention jobs scope every record and retain lineage/deletion evidence without releasing expired content —
    `platform/services/gateway/tests/test_governance_evidence_lifecycle.py::test_retention_scope`
  - Destination policy applies to traces, audit, alerts and dataset export and rejects missing region/processing approval —
    `platform/services/gateway/tests/test_governance_evidence_lifecycle.py::test_destination_policy`
  - Backup/restore documentation states residual copies and re-applies deletion policy rather than claiming instant erasure everywhere —
    `platform/services/gateway/tests/test_governance_evidence_lifecycle.py::test_restore_retention`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/evidence_lifecycle.test.ts`
- **Done:** An operator applies qualified retention and export-destination rules to
  metadata, audit and datasets; expired records and unauthorized queued exports follow
  the tested lifecycle policy.
- **Deps:** WU-94, WU-114, WU-117.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/governance/evidence_lifecycle/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → evidence_lifecycle
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[evidence lifecycle]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  RetentionPolicy(scope, artifact_kind, duration, version)
  ExportDestination(approved_processing_attributes, allowed_scopes, version)
  deletion evidence contains IDs/codes, never deleted payload content
  ```
- **Alternatives considered:** Use one global TTL for every evidence type (simple
  config, wrong retention semantics); apply versioned type/scope policies with
  destination checks and tested deletion behavior.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Deletion and audit retention can conflict; validate supported policy combinations and reject unsupported holds. Rollback stops policy edits while existing restrictions continue.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-128 — Publish model discovery from reviewed capability evidence

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Applications and developers discover accessible model aliases and supported operations from the platform support manifest plus attributable model/pricing facts.
- **Scope:** Platform `catalog/model_discovery` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Advertising a provider/model merely because a name appears in a registry, or editing the library model-facts pipeline here.
- **Acceptance:**
  - GET /v1/models lists only the caller's authorized application routes and does not leak provider connections —
    `platform/services/gateway/tests/test_catalog_model_discovery.py::test_scoped_models`
  - Capability/cost/context facts identify source/date and distinguish declared versus qualified support —
    `platform/services/gateway/tests/test_catalog_model_discovery.py::test_fact_provenance`
  - Refreshing reviewed facts does not silently enable unqualified routes or change a pinned execution contract —
    `platform/services/gateway/tests/test_catalog_model_discovery.py::test_refresh_review`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/model_discovery.test.ts`
- **Done:** An authenticated client discovers only authorized application aliases and
  qualified capabilities through the documented model endpoint, with stale evidence
  invalidated and no hidden deployment leakage.
- **Deps:** WU-98, WU-103; library WU-64 and WU-65.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/catalog/model_discovery/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → model_discovery
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[model discovery]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  model alias -> application/environment route -> support manifest + dated facts
  management discovery can explain more only with the corresponding scoped permission
  ```
- **Alternatives considered:** Proxy the upstream model list (broad catalogue, leaks
  inaccessible/unqualified destinations); publish authorized application aliases derived
  from reviewed qualification evidence.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Discovery drift can break clients; version reviewed snapshots and retain unknowns. Rollback restores the prior manifest without broadening access.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-129 — Run approved shadow traffic for a bounded migration comparison

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An explicitly approved migration can sample eligible production requests to a qualified shadow destination with separate budgets, capture policy and evidence.
- **Scope:** Platform `migration/shadow` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Unapproved payload copying, tool side effects or automatic promotion.
- **Acceptance:**
  - Shadow requires explicit source-content use and destination approval; scope/ABAC restrictions apply independently —
    `platform/services/gateway/tests/test_migration_shadow.py::test_shadow_authority`
  - Sampling and total cost/concurrency are capped; shadow failure cannot change the primary response —
    `platform/services/gateway/tests/test_migration_shadow.py::test_shadow_bounds`
  - Receipts distinguish primary/shadow executions, disclosure and additional cost; revocation stops new shadow attempts —
    `platform/services/gateway/tests/test_migration_shadow.py::test_shadow_evidence`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/shadow.test.ts`
- **Done:** An approved sample is sent to an independently authorized candidate within a
  finite budget and expiry; the original response is unaffected and comparison receipts
  expose both disclosure and spend.
- **Deps:** WU-104, WU-105, WU-111, WU-92a.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/migration/shadow/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → shadow
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[shadow]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  ShadowPolicy(source_route, candidate_version, sample_cap, budget, expires_at, approval)
  primary execution and shadow have separate IDs; no response substitution
  ```
- **Alternatives considered:** Mirror all traffic by default (large comparison sample,
  doubles disclosure and cost); require finite sampled approval with independent
  authorization, admission and expiry.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Shadow doubles disclosure and spend; default off with finite approval/budget. Rollback disables new shadow admission and cancels queued work.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-130 — Issue personal development keys with current human authority

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Authorized members create expiring personal development keys scoped to their permitted applications/environments; departure or role changes revoke their effective access.
- **Scope:** Platform `credentials/personal` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Using human keys for shared production services, never-expiring credentials or client-side provider secrets.
- **Acceptance:**
  - Personal keys intersect current human grants and cannot inherit another team's unrelated authority —
    `platform/services/gateway/tests/test_credentials_personal.py::test_personal_scope`
  - Membership removal, suspension and approval expiry invalidate use independently of stored key expiry —
    `platform/services/gateway/tests/test_credentials_personal.py::test_owner_revocation`
  - Spend is attributed to the authenticated owner and configured team allocation, not arbitrary end-user metadata —
    `platform/services/gateway/tests/test_credentials_personal.py::test_personal_attribution`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/personal.test.ts`
- **Done:** A developer issues a scoped personal key, invokes within current human
  authority, and loses that capability after suspension or grant revocation; usage
  remains attributed to the human principal.
- **Deps:** WU-82i, WU-92a, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/credentials/personal/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → personal
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[personal]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  PersonalKey(owner_principal, scope, expires_at, hashed_secret, status)
  personal and service-account keys are distinct types with separate lifecycle displays
  ```
- **Alternatives considered:** Reuse service-account keys for humans (fewer credential
  kinds, obscures accountability); bind personal keys to current human authority with
  separate issuance and revocation rules.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Developer keys can outlive employment; recheck current owner state per invocation. Rollback revokes personal keys without altering independent service accounts.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-131 — Qualify enterprise SSO through the reference identity broker

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** A customer identity provider authenticates users through a pinned Keycloak broker profile while platform membership and ABAC mappings remain explicitly controlled.
- **Scope:** Platform `identity/enterprise_sso` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Implementing SAML in gateway code, universal IdP certification or direct customer OIDC profiles without separate qualification.
- **Acceptance:**
  - A real local broker/upstream-IdP fixture completes SAML-to-OIDC sign-in with exact issuer/audience/binding checks —
    `platform/services/gateway/tests/test_identity_enterprise_sso.py::test_brokered_sign_in`
  - Claim mapping cannot turn IdP administration or matching email into platform ownership —
    `platform/services/gateway/tests/test_identity_enterprise_sso.py::test_claim_mapping_authority`
  - Upstream removal, session expiry, signing-key rotation and outage follow documented revocation bounds —
    `platform/services/gateway/tests/test_identity_enterprise_sso.py::test_broker_lifecycle`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/enterprise_sso.test.ts`
- **Done:** The reference upstream SAML identity provider authenticates through Keycloak
  into the existing OIDC flow, with tested issuer isolation, logout/session limits and
  membership revocation.
- **Deps:** WU-76, WU-82c, WU-82f, WU-101.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/identity/enterprise_sso/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → enterprise_sso
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[enterprise sso]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  EnterpriseProfile(broker_version, upstream_metadata_ref, claim_mapping_version)
  upstream login -> broker OIDC -> existing console session -> explicit platform grants
  ```
- **Alternatives considered:** Implement SAML inside the gateway (direct integration,
  duplicates the broker security surface); qualify SAML at the reference broker and keep
  the gateway OIDC-only.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Broker metadata/claim changes can alter trust; pin and audit mappings and keep break-glass explicit. Rollback disables the profile rather than silently enabling local login.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-132 — Offer explicit semantic response reuse within isolated scopes

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** An opt-in policy may reuse a semantically similar eligible cached response with similarity/quality evidence and a visible approximation decision, never as an exact model execution.
- **Scope:** Platform `cache/semantic` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Silent approximation, cross-principal reuse, tool-effect replay or a universal answer-quality guarantee.
- **Acceptance:**
  - Candidates are filtered by authorized exact scope/configuration before similarity search and reauthorized before release —
    `platform/services/gateway/tests/test_cache_semantic.py::test_scope_before_similarity`
  - A versioned threshold and evaluation fixture establish accepted/rejected examples and expose approximation provenance —
    `platform/services/gateway/tests/test_cache_semantic.py::test_similarity_qualification`
  - Reuse bypasses neither current guardrails nor content retention and does not invent provider usage —
    `platform/services/gateway/tests/test_cache_semantic.py::test_reuse_evidence`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/semantic.test.ts`
- **Done:** An opted-in request reuses a response only within its authorized semantic-
  cache partition and qualified threshold, with explicit approximation evidence and
  measured false-match behavior.
- **Deps:** WU-108, WU-110, WU-118.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/cache/semantic/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → semantic
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[semantic]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  SemanticReusePolicy(enabled=False, embedding_version, threshold, evaluation_ref)
  exact authorized partition -> similarity -> current policy -> labelled cached result
  ```
- **Alternatives considered:** Enable approximate reuse globally (higher hit rate,
  semantic and isolation risk); make reuse opt-in with scope partitioning, measured
  thresholds and explicit approximation evidence.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** Similarity does not establish correctness or permission; require explicit opt-in and regression evidence. Rollback disables semantic reuse and retains exact-cache rules.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** none; implement only after the listed prerequisites are qualified.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 5
- **Owner:** unassigned

## WU-133 — Qualify multimodal chat inputs on supported gateway routes

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** The gateway accepts only evidenced image/document chat input forms with bounded transfer, compartment classification and explicit provider compatibility.
- **Scope:** Platform `compatibility/multimodal_chat` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Audio/video generation, realtime sessions, batch/file APIs or private platform codecs; each new capability needs its own qualified library contract and WU.
- **Acceptance:**
  - Recorded image/document requests preserve qualified fields and report unsupported conversion explicitly —
    `platform/services/gateway/tests/test_compatibility_multimodal_chat.py::test_multimodal_contract`
  - Untrusted remote URLs cannot trigger unapproved fetches; payload/size/type limits and processing restrictions apply —
    `platform/services/gateway/tests/test_compatibility_multimodal_chat.py::test_media_egress`
  - Streaming, fallback and evidence capture retain the same content/access restrictions —
    `platform/services/gateway/tests/test_compatibility_multimodal_chat.py::test_media_governance`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/multimodal_chat.test.ts`
- **Done:** The published multimodal profile completes recorded supported image/document
  requests and streams while enforcing size, egress, content-access and processing
  restrictions; unsupported forms fail explicitly.
- **Deps:** WU-87, WU-88, WU-101, WU-111; qualified public multimodal chat fixtures for each exposed form.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/compatibility/multimodal_chat/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → multimodal_chat
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[multimodal chat]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  supported input forms are enumerated in the support manifest per interface/tag
  media reference -> authorized bounded resolver or explicit rejection -> public chat port
  ```
- **Alternatives considered:** Accept arbitrary media URLs and advertise multimodal
  support (broad input surface, unbounded egress and unsupported conversion); qualify a
  bounded image/document profile with explicit rejection.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** External media and provider references create disclosure/SSRF risks; test explicit egress and reference scope. Rollback removes unsupported forms from discovery.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** Expose only input forms proven by a pinned public artifact; any missing codec/fixture is a library dependency, not permission to implement conversion in the platform.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-134 — Serve the qualified OpenAI Responses compatibility endpoint

- **Status:** ⬜ defined
- **Context:** The competitive coverage matrix above assigns this missing gateway
  workflow; the baseline WU-82–105 program does not qualify it.
- **Goal:** Applications use /v1/responses through the same scoped invocation, policy, streaming and receipt path as chat completions. Unsupported continuation/reference behavior is rejected with evidence.
- **Scope:** Platform `compatibility/responses` workflow, management/data-plane contracts where
  applicable, client/console controls, fixtures and operations documentation;
  approximately 12–24 files. Extend the access inventory and qualification profile
  for this workflow in the same PR.
- **Non-goals:** Provider conversion changes, undocumented Responses storage APIs, realtime or batch APIs; public-library work remains independent.
- **Acceptance:**
  - Unary and streaming recorded Responses traffic uses the public codecs with contract/fold evidence —
    `platform/services/gateway/tests/test_compatibility_responses.py::test_recorded_responses`
  - Scoped references cannot cross provider, application or compartment boundaries on fallback —
    `platform/services/gateway/tests/test_compatibility_responses.py::test_reference_and_scope`
  - The endpoint advertises only qualified operations; unsupported storage/continuation is explicit —
    `platform/services/gateway/tests/test_compatibility_responses.py::test_supported_surface`
  - The documented operator/client workflow runs against the real service fixture
    and its controls match backend permissions —
    `platform/tests/integration/responses.test.ts`
- **Done:** An application completes recorded unary and streamed Responses requests
  through the governed gateway; the support matrix rejects unqualified
  continuation/reference operations explicitly.
- **Deps:** WU-87, WU-88, WU-101; qualified public Responses request/response/stream codecs and execution evidence.
- **Architecture:** §12, the corresponding gateway workflow subsection allocated
  against current main; no public-library layer or freeze changes.
- **Integration:**
  - Layer: platform service/console and explicitly listed public-library APIs.
  - Modules: `platform/services/gateway/app/compatibility/responses/`, matching platform
    contracts, client/console controls and tests; deployment files for operations WUs.
  - Flow: authenticated scoped input → current authorization/policy → responses
    workflow → safe evidence and scoped result; background execution reauthorizes.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Scoped input] --> Policy[Current authorization and policy]
      Policy --> Workflow[responses]
      Workflow --> Evidence[Attributed result and evidence]
    ```
- **Design sketch:**
  ```text
  POST /v1/responses -> InvocationContext -> shared execution -> qualified Responses encoder
  contract support = interface + tag + operation + feature + streaming/replay evidence
  ```
- **Alternatives considered:** Pass provider JSON through unchanged (small adapter, but
  bypasses conversion and fidelity evidence); use the qualified public codecs and shared
  execution path so Responses has the same governed contract.
- **Freeze:** none; platform-only provisional contracts. Public-library changes
  require their own WU and release intent and cannot be hidden in this PR.
- **Decision (boundary):** Inherit the reviewed WU-82a scope/ABAC contract and the
  shared gateway contracts. The Design sketch defines this proposed delivery profile;
  experimental or unsupported features cannot become implicit dependencies.
- **Risks:** An OpenAI-compatible label can overpromise support; publish the operation matrix. Rollback disables this endpoint while retaining receipts.
- **Dependency impact:** Consumes the listed WUs; extends the endpoint/feature
  inventory and qualification profile without relabelling baseline evidence.
- **Open:** Implementation waits for a pinned public-library artifact proving the required Responses codecs and stream behavior; WU-82a records the dependency, without assigning kernel implementation here.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned
