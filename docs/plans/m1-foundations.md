# M1 — Foundations: one provider end-to-end (unary)

Goal: `WireChatModel.chat/achat` returns a `CallResult` with a real two-leg
`FidelityReport` on a recorded OpenAI wire pair. Architecture refs: §2 (core
contracts), §3.2–3.4 (port, facade, three-lane law), §4 (convert), §8
(lifecycle).

State going in (verified inventory): the drivers' unary pipeline, Dijkstra
planner, catalog compose/resolve/lock, IR envelope (omit-absent + tolerant +
TagRegistry), canonjson, RetryPolicy, and both provider codecs'
encode/decode are implemented. The gaps this milestone closes: schemas,
certification, and the facade assembly.

---

## WU-00 — Baseline commit + roadmap replacement ✅

Initial commit of the settled skeleton; archive the pre-rearchitecture
milestone files to `archive/`; this roadmap replaces them.
**Done:** `git log` shows baseline + roadmap commits; suite stays green.

## WU-01 — Enforcement becomes executable

- **Scope:** `pyproject.toml` — `[tool.importlinter]` contracts encoding §1:
  layered contract (`ocai.core` ← capabilities ← `ocai.convert` ←
  `ocai.runtime` ← `ocai.wire`); forbidden contracts (plugins must not import
  `ocai.wire`/`ocai.runtime`/httpx) with the single sanctioned exception
  `ocai.chat.model`; `.github/workflows/ci.yml` — add `uv run lint-imports`;
  `ocai/convert/catalog.py` — finish the canonical-backbone admission check in
  `_admit` (every edge endpoint canonical or fragment-owned).
- **Done:** `lint-imports` passes locally and in CI; a violation smoke test
  proves it bites; ≥3 new admission tests in `tests/test_conformance.py`;
  pytest green.
- **Deps:** WU-00. Parallel-safe with everything.
- **Decision:** canonical-backbone admission is the pragmatic
  per-interface-overall rule: for each non-canonical `(provider, interface)` a
  fragment publishes nodes for, if the fragment registers ≥1 edge/transducer
  touching that interface then ≥1 of them must have its other endpoint on the
  canonical interface; interfaces published with zero touching edges admit as
  declared conversionless stubs (the `openai/responses` shape today). The
  connectivity check runs under every trust policy — `ALLOW_LISTED` exempts
  only the endpoint-ownership check. The per-shape refinement is deferred
  until a real fragment needs it.
- **Decision:** import-linter runs with `exclude_type_checking_imports = true`
  (annotation-only imports are erased at runtime and carry no layer
  coupling). Besides the sanctioned `ocai.chat.model` exception, the layered
  contract `ignore_imports` the runtime drivers'/binding's documented
  *deferred* function-level imports of `ocai.wire` value modules
  (http/sse/transport) — the package arrow stays wire → runtime. A third
  forbidden contract quarantines direct httpx imports to `ocai.wire`, with
  the same two deferred seams ignored.

## WU-02 — spec/schema regeneration I: message, parts, chat.request

- **Scope:** `spec/schema/` — new `message.schema.json` (parts-only Message),
  `parts.schema.json` (full taxonomy incl. `PartUnknown`/`PartOpaque`,
  `id`/`anchor` lanes, open `type` codes), `chat_request.schema.json` (tools,
  tool_choice, three-lane config). Delete the three stale schemas (their
  "kept until regeneration" condition expires). Replace the stale
  `spec/fixtures/openai_v1_chat_request.json`. Add the validator harness:
  `tests/test_spec_schemas.py` validating every `spec/fixtures/**/*.json`
  against its declared schema — `jsonschema` as a **dev-only** dependency
  (never a runtime dep of `ocai.core`; rule 11 safe).
- **Done:** stale schemas gone, new ones land, `spec/schema/README.md` banner
  removed; validation test collects every fixture; pytest green.
- **Deps:** WU-00. (WU-02/03 are one logical unit, deliberately pre-split.)
- **Decision:** fixture→schema mapping is structural (documented in
  `spec/README.md` "How fixtures map to schemas"): shape token `x.y` →
  `schema/x_y.schema.json`; canonical-document fixtures (`shape`+`document`),
  edge fixtures (only `provider == "ocai"` sides validate), fold triples
  (`chunks`/`response`). Shared `$defs` (envelope, providerRef, source, span,
  annotation, cacheHint) live in `parts.schema.json`; the replacement fixture
  is `spec/fixtures/canonical/chat_request.json` (wire-accurate `to_dict()`
  output, synthetic hand-authored).

## WU-03 — spec/schema regeneration II: response, finish, usage + rule-11 test

- **Scope:** `spec/schema/` — `chat_response.schema.json`,
  `finish.schema.json` (open codes + `native` lane + detail union),
  `usage.schema.json` (Consumption dimensions, cached/reasoning sources).
  New `tests/test_schema_conformance.py`: the rule-11 test — dataclass fields
  ↔ schema properties for Message/parts/ChatRequest/ChatResponse/FinishInfo/
  Usage, omit-absent compliance, additive-only guard (exhaustive field/property
  set comparison so an unschema'd field fails).
- **Done:** pytest green; demonstrably fails when a dataclass field lacks a
  schema property.
- **Deps:** WU-02 (shares the validator harness).
- **Decision:** the rule-11 comparison is a strict field-set == property-set
  equality extended to *every* schema'd IR dataclass (incl. the WU-02
  building blocks: Tool/ToolChoice/ChatConfig family, ProviderRef,
  Annotation/Span/CacheHint, Source variants); the verbatim fallbacks
  (`PartUnknown`/`SourceUnknown`/`DetailOpaque`) are exempt and instead
  asserted byte-faithful (their `data`/`type` are internal carriers, never
  wire members). `chat_response.schema.json` documents `raw` as a
  deliberately unconstrained verbatim provider lane (excluded from semantic
  equality per `canonical-json.md` §8); `FinishDetail` branches live in
  `finish.schema.json#/$defs/finishDetail` mirroring the parts if/then
  pattern, with `Consumption`/`SafetyRating` as plain value objects (no IR
  envelope, like `span`). The canonical fixture
  (`spec/fixtures/canonical/chat_response.json`, synthetic) is an
  OpenAI-/responses-flavored truncation — reason `max_tokens`, native
  `length`, incomplete detail — covering all four disjoint usage buckets,
  and its wire accuracy is pinned by a byte-identical
  `from_dict → to_dict` round-trip test. The additive-only snapshot stores
  each node's full conditional property union; its file-coverage check is
  scoped to the six chat-unary schemas so schema files newer WUs add (e.g.
  streaming deltas) join the snapshot in the WU that authors them.

## WU-04 — `EdgeContract.certify`: the certification gate

- **Scope:** `ocai/convert/contract.py` — severity partial order over
  `Disposition` (EXACT < RENAMED/EXTENSIONS < APPROXIMATED/EMULATED <
  DROPPED/UNSUPPORTED); census path matching (`[]` wildcard vs concrete
  indices, exact-path precedence); declared-but-unexercised entries produce no
  violation; certify runtime `SemanticShift`s against `semantic_shifts`.
  (`conformance.certify_edge` is already hooked.)
- **Done:** no `NotImplementedError` left in `contract.py`; new
  `tests/test_contract_certify.py` with ≥8 cases (undeclared path → violation;
  DROPPED-where-APPROXIMATED-declared → violation; milder-than-declared →
  clean; wildcards; unexercised entry → clean; undeclared shift → violation);
  `certify_edge` over the echo example fixtures returns `[]`; pytest green.
- **Deps:** WU-00. Parallel with WU-02/03.

## WU-05 — Unknown-X fixture vocabulary + `check_unknown_inputs`

- **Scope:** `spec/README.md` — document the fixture `expect` vocabulary
  (which paths must decode to Unknown types vs sweep to `extensions` vs
  preserve `native`). `spec/fixtures/unknown/` — ≥5 normative vectors
  (unknown part tag → `PartUnknown`; unknown delta → `DeltaUnknown`; unknown
  envelope key → `extensions`; unknown finish reason → `"unknown"` + native;
  unknown role verbatim). Implement `conformance.check_unknown_inputs`
  (never-raise, fallback typing, verbatim re-encode under `semantic_equal`).
- **Done:** implemented + `tests/test_unknown_inputs.py` runs it against the
  chat IR decoders; fixtures validate against WU-02/03 schemas; pytest green.
- **Deps:** WU-02 (soft — parallel development fine, lands after the harness).
- **Decision:** unknown vectors are canonical document fixtures (`shape` +
  `document`) extended with a required `expect` block — three optional lists
  (`fallbacks` / `extensions` / `preserved`) plus the sweep-adjusted
  round-trip law, documented normatively in `spec/README.md`. They validate
  through the existing WU-02 mapping unchanged (the `expect` key is additive).
- **Decision:** `expect.fallbacks` names canonical fallback *type names*
  (`PartUnknown`, `DeltaUnknown`, `DetailOpaque`, `SourceUnknown`); the
  harness compares by type name so `ocai.convert.conformance` stays
  capability-neutral and the vocabulary language-neutral.
- **Decision:** the mandated unknown-delta vector needs a schema'd home and
  no WU owns one (WU-08's `chat_chunk.schema.json` is M2), so a minimal open
  `spec/schema/deltas.schema.json` (the `Delta` union, shape token `deltas`,
  mirroring `parts.schema.json`) was added; the M2 chunk schema can `$ref`
  it. The finish vectors validate against WU-03's `finish.schema.json`.

## WU-06 — OpenAI chat_completions unary certification

- **Scope:** `spec/fixtures/openai/chat_completions/` — ≥5 edge fixtures with
  `expect_losses`/`expect_shifts`: plain text; multi-turn + system; tool call
  + tool result round (incl. the `is_error` DROPPED loss); config knobs incl.
  out-of-range `temperature`; extensions sweep (`service_tier`,
  `system_fingerprint`). `ocai/openai/chat_completions/codec.py` — emit
  APPROXIMATED `FieldLoss` for out-of-range knobs (codec.py:448) and record
  the census-upper-bound decision in `edges.py` (range-limited knobs declare
  APPROXIMATED and grade honestly worse). Census truth-up until certification
  is empty. New `python/packages/ocai-openai/tests/test_conformance.py`
  wiring `check_codec` + `assert_graph_roundtrip` + `certify_edge` +
  `check_unknown_inputs`; extend root `testpaths` to collect plugin tests.
- **Done:** ocai-openai suite collected and green; `certify_edge` returns `[]`
  over all fixtures; each fixture's `expect_losses` matches the runtime report
  exactly; fixtures validate against schemas; ruff clean.
- **Deps:** WU-02, WU-03, WU-04 (hard); WU-05 (soft).
- **Scope guard:** media Source-union encode stays OUT (census honestly
  declares DROPPED — that is certifiable); citations stay EXTENSIONS. If
  still heavy, split request-side vs response-side fixtures.

## WU-07 — Facade unary lifecycle: `WireChatModel.chat/achat` — **MILESTONE M1**

- **Scope:** `ocai/chat/model.py` — the §8 assembly:
  `catalog.resolve(CHAT, provider, pins)` → `Route`;
  `catalog.convert(request, canonical → route node)`; build `EndpointSpec`
  (Operation from the codec's `native_path`, `DialectTraits` from the
  fragment); `SyncDriver.execute(refine_error=codec.map_error)`;
  `catalog.convert(raw → canonical)`; merge request-leg + response-leg
  reports; extract usage; assemble `CallResult` (raw verbatim, never
  credentials). `achat` over `AsyncDriver` with shared pure helpers. Replace
  `codec: Any` with a small typed codec Protocol (home: `ocai.chat.model`).
- **Tests:** `tests/test_facade_unary.py` on recorded pairs replayed through
  the real `HttpxTransport` via respx: the existing
  `tests/http/openai_chat_completion.json`, plus new tool-call, 429-then-200
  (RetryPolicy end-to-end), and 401 (→ `AuthError` via `map_error`) pairs.
- **Done:** `WireChatModel(codec, binding, catalog).chat(req)` returns a
  `CallResult` where `value` is `semantic_equal` to the fixture canonical,
  `route.catalog_hash == catalog.lock().hash`, `report` spans both legs with
  the expected losses, `usage.input_tokens` matches the recording, `raw` is
  untouched; `achat` twin passes; pytest green.
- **Deps:** WU-06 (hard), WU-01 (soft).
