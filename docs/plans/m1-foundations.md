# M1 — Foundations: one provider end-to-end (unary)

Historical completed milestone. The scope and original acceptance below are
retained; current behavior is documented in [the user guides](../user/index.md).

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
  `ocai.chat.facade`; `.github/workflows/ci.yml` — add `uv run lint-imports`;
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
  coupling). Besides the sanctioned `ocai.chat.facade` exception, the layered
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

## WU-05a — API shape correction: `model` off `ChatRequest`; two front doors

Maintainer course-correction (2026-07-13, architecture §3.4): pydantic-ai-shaped
UX. The model name is routing data bound to the model object, never carried in
the request; provider helpers are sanctioned sugar alongside the core string
door.

- **Scope:** (1) `ocai/chat/types/request.py` — drop the `model` field;
  `ChatRequest(messages, tools, tool_choice, config)` is pure conversation.
  (2) `spec/schema/chat_request.schema.json` + canonical fixtures — drop
  `model`; rule-11 test stays green. (3) Both plugin codecs — `encode_request`
  no longer reads `request.model`; the wire `model` field is injected from the
  bound resource (thread it through the edge/codec signature the way
  `EndpointSpec.resource` already flows; decide the exact seam in-WU and
  record it). Censuses updated (no `model` row). (4) `ocai/chat/facade.py` —
  `WireChatModel` gains the bound `model_name`; document that the §3.4 front
  doors pass it at construction. (5) Reinstate the plugin helper stubs
  (`ocai.openai.chat_model`, `ocai.anthropic.chat_model`) as thin sanctioned
  sugar (may stay NotImplementedError until WU-16 wires the doors; the
  DOCSTRING must define them as wrappers over the same fragment+facade path).
- **Done:** grep shows no `request.model` anywhere; schemas/fixtures/tests
  updated; full suite + lint-imports green; censuses re-certified.
- **Deps:** WU-02/03 (schemas exist). MUST precede WU-06.
- **Decision:** the injection seam. `ConversionGraph.convert` has no
  call-time context parameter and fragment edges are frozen before any model
  name exists, so the bound resource cannot ride the edge/codec signature
  through the graph. Instead, `encode_request` emits the wire body with **no
  `model` member** and each codec exposes a pure
  `bind_resource(payload, resource)`; the facade (`WireChatModel`) injects
  its bound `model_name` post-conversion, before the driver send — the same
  value that becomes `EndpointSpec.resource`. Edges stay pure functions of
  their payload, fragments stay model-agnostic, and the dialect knowledge of
  *where* the wire carries the name stays in the codec (hosting envelopes
  may still relocate/strip it — Vertex lifts it into the URL).
- **Decision:** the model-less edge output carries no `FieldLoss`: the
  canonical request has no model field, so emitting no `model` member drops
  nothing — rule-5 reporting covers canonical material only. The `model`
  rows were removed from both encode censuses; the response-side `model`
  echo rows stay (wire material, decoded to `info.model`).
- **Decision:** the additive-only property snapshot in
  `test_schema_conformance.py` was amended (`model` removed from the
  `chat_request.schema.json` entry) — sanctioned because WU-05a is a
  pre-freeze maintainer course-correction (stability domains freeze at v0.2,
  rule 2); the additive-only regime governs from the corrected shape onward.
- **Decision:** the sugar doors are exported at distribution level
  (`ocai.openai.chat_model`, `ocai.anthropic.chat_model`, per the §3.4
  example) as re-exports of the interface helpers; they stay
  `NotImplementedError` stubs with **no module-level wire/runtime imports**
  (plugin import contract stays green) — WU-16 wires them through the same
  fragment + facade machinery via documented deferred imports.

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
- **Decision (census upper bound):** range-limited knobs (`temperature`
  0..2, `top_p` 0..1, both penalties -2..2) declare **APPROXIMATED** in the
  encode census. The runtime emits APPROXIMATED only for an out-of-range
  value (passed verbatim, never clamped) and stays silent (EXACT) in range —
  certification accepts that because EXACT sits in a strictly lower severity
  band — but a census entry bounds *every* payload the edge may see, so the
  edge's `LossGrade` honestly pays four approximated slots rather than
  advertising an exactness it cannot promise. Recorded as a comment above
  `ENCODE_REQUEST_CONTRACT` in `edges.py`.
- **Decision (the implicit harness dependency):** the edge-fixture runner did
  not exist; implemented `check_edge` in `ocai/convert/conformance.py` (the
  name `docs/user/writing-a-plugin.md` already advertised). It asserts output
  equality under `semantic_equal` plus **exact** loss/shift match — records
  compare on `(path, disposition)` / `(kind, path)` as multisets; notes and
  severities are prose/diagnostics and are never compared, mirroring
  `EdgeContract.certify`. Two seams keep it capability-neutral:
  `decode_input` lifts a canonical-source fixture's `input` into the IR
  object, and `bind` is the below-the-graph facade seam where the fixtures'
  wire `model` member is injected via `bind_resource` (WU-05a: the edge
  output carries no `model`; the wire bodies do).
- **Decision (no graph round trip yet):** `assert_graph_roundtrip` needs both
  directions registered and only `encode_request` / `decode_response` exist
  (the `decode_request` audit edge is still a TODO; an encode-response edge
  does not exist). The suite instead converts every fixture through
  `Catalog.of(ocai.openai.FRAGMENT)` in its edge's registered direction and
  asserts value **and** report records — proving the planner routes through
  the certified edges. The true round trip lands with the reverse edges.
- **Decision (unary closures the fixtures forced):** canonical `ToolChoice`
  now maps by `mode` (`auto`/`none`/`required` pass as wire strings, `named`
  becomes the named-tool object, anything else is DROPPED-reported — the old
  code silently mis-handled `auto`); a turn whose parts were all tool results
  no longer emits an empty `{role, content:""}` husk (wire-invalid beside the
  relocated `role: tool` siblings); `OutputFormat.schema` renders through
  `to_dict()` at encode (it was embedding the `JsonSchema` object into the
  payload); response `info` decodes typed — `id` becomes an interface-scoped
  `ProviderRef(kind="response_id")`, `created` (Unix seconds) becomes the UTC
  `info.created` timestamp (census row `created`: EXTENSIONS → RENAMED); and
  decode-side loss paths were normalized to the wire-true census grammar
  (`choices[0].message.…`).
- **Decision (extension census):** `openai.service_tier` and
  `openai.system_fingerprint` are census-registered in `spec/extensions/` —
  they now appear in a shipped fixture's `extensions` bag, and an
  unregistered key there is a CI failure by the census law.
- **Decision (collection):** root `testpaths` gained the plugin tests dir and
  `addopts` gained `--import-mode=importlib` so sibling distributions can
  ship same-named test modules (core and openai both carry a
  `test_conformance.py`).

## WU-07 — Facade unary lifecycle: `WireChatModel.chat/achat` — **MILESTONE M1**

- **Scope:** `ocai/chat/facade.py` — the §8 assembly:
  `catalog.resolve(CHAT, provider, pins)` → `Route`;
  `catalog.convert(request, canonical → route node)`; build `EndpointSpec`
  (Operation from the codec's `native_path`, `DialectTraits` from the
  fragment); `SyncDriver.execute(refine_error=codec.map_error)`;
  `catalog.convert(raw → canonical)`; merge request-leg + response-leg
  reports; extract usage; assemble `CallResult` (raw verbatim, never
  credentials). `achat` over `AsyncDriver` with shared pure helpers. Replace
  `codec: Any` with a small typed codec Protocol (home: `ocai.chat.facade`).
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
- **Decision (interface pin defaults to the codec):** `interface=None` now
  pins the composed codec's own interface instead of letting resolution
  roam — the facade is composed *of* a dialect, and an unpinned resolve
  over `ocai.openai.FRAGMENT` would pick `openai/responses` (newer
  `released`) and mismatch the `ChatCompletionsCodec`. Free catalog choice
  is the §3.4 front doors' job (they resolve first, then build the matching
  codec from the fragment's component factory). An *explicit* pin that
  resolves off the codec's interface raises `CompositionError` at the seam.
- **Decision (`ChatCodec` protocol):** typed home `ocai.chat.facade`, as
  planned; members are what both plugin codecs actually share — `provider`/
  `interface`, the three shape nodes, `native_path`, `bind_resource`,
  `encode_request`/`decode_response`/`decode_event`, `map_error` — plus
  `dialect_traits()`, which existed only as a module function in both
  plugins and was added as a codec method (additive) because the catalog
  carries traits opaquely with no `(provider, interface)` key to look them
  up by. The facade builds `EndpointSpec` from it and closes `map_error`
  over `(err.status, err.raw)` as the drivers' `ErrorRefiner`.
- **Decision (policies enter at the facade):** `WireChatModel` gained
  `policies: Sequence[WirePolicy] = ()` — the drivers take their hook chain
  at construction and the WU's 429-then-200 test composes `RetryPolicy`
  through the facade; both drivers are built once in `__init__`. `ctx` is
  accepted per the port contract but not yet threaded into the wire hooks
  (no driver seam exists; a later WU's job).
- **Decision (decode-leg node + host stamp):** resolution is request-shape,
  so the decode leg finds the published response-shape sibling (same
  provider/interface/tag) in `catalog.nodes` — `ResolutionError` names the
  fragment if it failed to publish one. `Route.host` is stamped with
  `Host.endpoint(spec)` (the physical URL) after the spec exists — hosting
  stays below the graph, resolution never knows clouds exist.
- **Decision (tests + fixtures):** `tests/test_facade_unary.py` (13 tests)
  replays synthetic wire-accurate pairs through the real `HttpxTransport`
  via respx; new recordings `openai_chat_completion_{tool_call,retry,
  auth_error,context_length}.json`. The extra 400-overflow pair exists
  because `context_length_exceeded` is a 400 only `map_error` can classify —
  the positive proof the layer-2 refiner is wired (a 401 alone cannot
  distinguish coarse from refined).
- **Decision (lint-imports verified):** the three package-level ignore
  entries (`facade -> ocai.convert/runtime/wire` bare) could never match —
  the facade imports specific value modules (`catalog`, `drivers`,
  `binding`, `hosting`); a bare `ocai.wire` import would chain to httpx
  through its `__init__` and break the quarantine contract. Trimmed them to
  the matched `.**` entries and restored default unmatched-ignore erroring,
  so a stale ignore is itself a build failure. 3 contracts kept, zero
  warnings.
