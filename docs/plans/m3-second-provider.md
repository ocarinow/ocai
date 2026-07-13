# M3 — The second provider and the proofs

Goal: Anthropic end-to-end **with zero changes to `ocai/chat/facade.py`** (the
pattern-replay claim, tested), plus the cross-conversion fidelity report demo
— flagship demo #1. Architecture refs: §7 (plugin shape), §8 (lifecycle), §2.2
(SemanticShift), §2.4 (ProviderRef crossing rule).

---

## WU-13 — Anthropic messages unary certification

- **Scope:** pattern replay of WU-06. `spec/fixtures/anthropic/messages/` —
  ≥5 fixtures: system-hoist with declared `SemanticShift(relocation)`; tool
  round; required `max_tokens` injection (+ shift); out-of-range APPROXIMATED
  per the WU-06 census-upper-bound decision; extensions sweep incl. the
  `cache_creation_input_tokens` dimension decision (codec.py:232). Census
  truth-up in `edges.py`; new
  `python/packages/ocai-anthropic/tests/test_conformance.py`; anthropic
  unknown-X vectors.
- **Done:** ocai-anthropic suite collected and green; `certify_edge` returns
  `[]`; the system hoist appears in `expect_shifts` and matches runtime;
  fixtures validate against schemas; ruff clean.
- **Deps:** WU-02/03/04 (hard); WU-06 (pattern, soft). Parallel with M2.
- **Decision (census upper bound, replayed):** the WU-06 rule applied to this
  dialect's ranges — `temperature` and `top_p` are both **0..1** here (the
  temperature ceiling is 1.0, not OpenAI's 2.0), so both declare
  APPROXIMATED in the encode census and `_KNOB_RANGES` in `codec.py` emits
  the APPROXIMATED `FieldLoss` only for out-of-range values, passed verbatim,
  never clamped. Same value, different fate per interface — that asymmetry is
  the point of per-edge censuses.
- **Decision (max_tokens injection is a shift, not a loss):** the wire
  REQUIRES `max_tokens`; when the canonical config omits it (None = "provider
  default", inexpressible here) the encoder injects `DEFAULT_MAX_TOKENS` and
  records a declared `SemanticShift(emulation)` at `config.max_output_tokens`
  — no canonical field was lost, but the call runs under a ceiling the caller
  never set, which is semantic divergence, not field loss (§2.2 keeps those
  distinct). Declared on `ENCODE_REQUEST_CONTRACT.semantic_shifts`.
- **Decision (the cache dimension, codec.py:232):**
  `cache_read_input_tokens` → the canonical `cached` consumption source;
  `cache_creation_input_tokens` → an **open-source `Consumption`** under the
  plugin-namespaced code `anthropic.cache_write` — NOT an extensions-bag
  entry: cache writes are real billed tokens Anthropic itemizes disjointly
  from `input_tokens`, so they belong on the dimensional model where
  `Usage.total_tokens` stays a plain sum (§11.9: new dimensions are open-code
  data, never releases). The source code is namespaced like every
  plugin-minted open code (precedent: the `anthropic.args_serialized` shift
  kind); promotion to a core `UsageSource` constant triggers when a second
  provider itemizes cache writes. No `spec/extensions/` entry — the census
  governs extensions-bag keys, and this never enters a bag.
- **Decision (unary closures the fixtures forced):** the canonical `tool`
  role threads as a `role: user` wire message carrying the native
  `tool_result` blocks (the Messages wire has no tool role) with a declared
  `SemanticShift(relocation)` — while `is_error` crosses EXACT, the honest
  asymmetry vs chat_completions, asserted explicitly in the suite; canonical
  `ToolChoice` now maps by `mode` (`auto`→`{type: auto}`,
  `required`→`{type: any}`, `none`→`{type: none}`, `named`→`{type: tool,
  name}` — the old code matched on `isinstance(str)` and silently mis-routed
  every mode-object); response `info` decodes typed — `id` becomes an
  interface-scoped `ProviderRef(kind="response_id")`, `model` stays the echo,
  and this wire carries no creation timestamp; `output_config.format.schema`
  renders through `JsonSchema.to_dict()` (it was embedding the typed object),
  with `config.output.name`/`.strict` honestly DROPPED-censused (the wire
  format object carries only the schema itself).
- **Decision (extension census):** `anthropic.stop_sequence` and
  `anthropic.container` are census-registered in `spec/extensions/` — both
  now appear in a shipped fixture's `extensions` bag, and an unregistered key
  there is a CI failure by the census law.
- **Decision (collection & scope):** root `testpaths` gained the anthropic
  tests dir (`--import-mode=importlib` already in place from WU-06). The
  streaming transducer TODOs (`message_delta` fold, typed mid-stream error)
  stay untouched — WU-14b territory.

## WU-14a — Anthropic unary end-to-end (the pattern proof)

- **Scope:** extend `tests/http/anthropic_messages.json` with tool-call and
  error pairs; facade unary tests for anthropic mirroring
  `test_facade_unary.py`.
- **Done:** chat/achat e2e green **with zero changes to
  `ocai/chat/facade.py`** — assert the pattern holds; this is the "adding
  providers follows the same pattern" proof. pytest green.
- **Deps:** WU-07, WU-13.

## WU-14b — Anthropic streaming end-to-end — **MILESTONE M3**

- **Scope:** close anthropic streaming TODOs: fold `message_delta`
  usage/finish into the terminal STREAM_STOP (codec.py:1007); typed mid-stream
  error shape — canonical code + native + detail (codec.py:925). ≥3 anthropic
  fold triples in `spec/fixtures/anthropic/messages/streams/`; facade stream
  e2e.
- **Done:** `check_fold_triples` green; fold-equals-unary on a paired recorded
  exchange; pytest green.
- **Deps:** WU-11, WU-14a.

## WU-15 — Cross-conversion fidelity proof (flagship demo #1)

- **Scope:** pure `ocai.convert`, **no wire needed** (can land before WU-14):
  convert a recorded openai/chat_completions request → canonical →
  anthropic/messages, and a response leg in reverse, via two-hop planning
  through the canonical backbone. `spec/fixtures/cross/` pinning the
  expectation. A runnable example (docs snippet or `examples/`) that prints
  the `FidelityReport` — the system hoist shift, tool-id regeneration, the
  `is_error` drop. Test that a `ProviderRef` crossing `(provider, interface)`
  is UNSUPPORTED-and-reported (§2.4).
- **Done:** `tests/test_cross_conversion.py` asserts the planner chose the
  2-hop path, the merged per-edge report contents, and `semantic_equal`
  against the cross fixture; the example's printed report is asserted in a
  test; pytest green.
- **Deps:** WU-06 + WU-13 only.
- **Decision (wire `model` disposition):** EXTENSIONS, not dropped-to-route —
  `decode_request` banks the wire `model` as the censused
  `extensions["openai.model"]` / `extensions["anthropic.model"]`
  (`spec/extensions/`): routing data never enters the request IR (§3.4), but
  the echo stays recoverable on the canonical artifact for the audit trail.
  The cross direction then reports the foreign extension **DROPPED at the
  destination encode edge** — both encode censuses gained an `extensions[]`
  DROPPED row (the bag has no encode lane yet; TODO: re-expand own-namespace
  censused keys) so the sweep is declared, never silent. Net effect in the
  demo: the model echo is ultimately dropped-to-route, and the report shows
  exactly where.
- **Decision (where the `is_error` drop is pinned):** a recorded
  chat_completions request *cannot* carry the flag — the wire has no lane
  for it, which is precisely why the encode census drops it — so
  `spec/fixtures/cross/` pins BOTH directions:
  `request_openai_to_anthropic.json` (system hoist + tool-turn threading)
  and `request_anthropic_to_openai.json` (system un-hoist +
  `anthropic.args_serialized` + the `is_error` DROP). Two `decode_request_*`
  fixtures pin each audit edge alone so the intermediate canonical form is
  golden and schema-validated; they live in `cross/` (not the per-interface
  dirs) because the shared plugin suites dispatch decode fixtures by
  response shape via non-recursive globs and would misroute request-shaped
  decode pins — keeping WU-15's pins in `cross/` leaves those suites
  untouched for the concurrent streaming work.
- **Decision (response leg — the recorded deviation):** the REQUEST cross
  direction landed fully; the response leg runs decode-only. Both
  wire→canonical response edges exist and their reports `merge` onto the
  request leg exactly as the facade folds a call (asserted + demoed);
  canonical→wire response needs encode_response edges that do not exist
  yet — pinned by `test_encode_response_direction_does_not_exist_yet`,
  which flips the day they land.
- **Decision (§2.4 enforcement point):** the scoped ref rule runs in the
  encode edge functions — a `_foreign_ref_loss` helper per codec checks
  `part.anchor` and `SourceRef` media handles (anthropic thinking anchors
  keep their existing replay-refusal path); the encode censuses gained
  `messages[].parts[].anchor`/`.source` (and anthropic `.signature`)
  UNSUPPORTED rows. Interface-scoped refs are UNSUPPORTED crossing any
  other `(provider, interface)`; provider-scoped refs cross same-provider
  siblings unreported; model-scoped qualifier breakage stays below the
  graph at bind time (not modeled here).
- **Decision (tool-call ids cross verbatim):** no ID_REGENERATED shift is
  emitted — both destination wires accept the foreign-shaped id strings the
  fixtures pin (`call_*` on Messages, `toolu_*` on chat_completions), so
  regenerating (or fabricating a shift for) them would be dishonest; the
  kind stays reserved for a destination that rejects foreign id shapes.
- **Decision (decode-request inverse moves, declared):** the audit edges
  declare the encode moves run backwards — anthropic `system` un-hoists to
  a leading canonical system turn (RELOCATION at `system`), `role: user`
  wire messages carrying `tool_result` blocks re-thread as canonical tool
  turns (RELOCATION), openai sibling `role: tool` messages likewise, and
  `tool_use.input` reuses the plugin-minted `anthropic.args_serialized`
  kind. The runnable example is `examples/cross_conversion_demo.py` (a
  script, not a docs snippet — it imports both plugins and reads the golden
  fixtures, so demo and spec cannot drift); its printed report is asserted
  in `test_example_output_is_the_real_report`.

## WU-16 — The front doors wired end-to-end (§3.4)

Maintainer-refined design (2026-07-13): TWO equivalent doors, neither forced —
the core string door for data-driven switching, and the plugin helper as
sanctioned sugar over the same machinery. Installing a provider dist has
exactly one structural effect: graph augmentation. No framework containers.

- **Scope:** (1) NEW `ocai.chat.model(spec, *, credentials, host=None,
  catalog=None, transport=None, interceptors=())` per §3.4, where `spec` is
  the single string `"<provider>/<model>"` (maintainer decision 2026-07-13:
  LiteLLM/OpenRouter convention; split on the FIRST slash only — the model
  part may contain slashes, e.g. HF ids on vLLM; the spec never carries an
  interface — pinning stays a kwarg; one config value switches providers) —
  resolves against the discovered default catalog (or an explicit one), builds
  the codec via the fragment's component factory, composes the `Binding`
  internally (`Direct` from the fragment's first-party endpoint data), returns
  a `ChatModel` bound to the parsed model name. Lives in `ocai/chat/__init__.py` (the
  facade module is `chat/facade.py` — never shares the factory's name).
  (2) Move first-party endpoint data (base URL) into the fragment (extend
  `DialectTraits` or the `Component` descriptor — decide in-WU) so the core
  door never imports a plugin. (3) WIRE the plugin `chat_model()` helpers
  (currently NotImplementedError stubs) as thin wrappers over the exact same
  fragment + facade path — deferred imports per the documented seam.
  (4) DELETE the `Workspace` class from `ocai/runtime/binding.py` (keep
  `Binding` + `validate()`; scrub Workspace from runtime docstrings and the
  catalog.py docstring). (5) `ocai/runtime/dual.py` — `from_sync`/`from_async`.
  (6) `Catalog.discover()` integration test (entry points already declared).
- **Done:** the §3.4 five-liner works end-to-end on a recorded pair with zero
  provider imports; `ocai.openai.chat_model("gpt-5", credentials=...)` returns
  the identical composition (asserted); grep proves no `Workspace` remains;
  dual adapters pass sync↔async round-trips; the discovery test composes both
  installed fragments; pytest green.
- **Deps:** WU-07 (facade); pull EARLY — right after WU-07 — so examples and
  tests teach the real doors from the start.
- **Decision (2026-07-13, WU-16):** first-party endpoint data rides
  `DialectTraits` (new optional `first_party_base_url` field in
  `core/traits.py`), NOT the `Component` descriptor — it is hosting-relevant
  dialect data, exactly what traits carry; the module-level `*_BASE_URL`
  constants stay the source and both codecs' `dialect_traits()` forward them.
  No spec schema/census references traits, so no fixture change.
- **Decision (2026-07-13, WU-16):** plugins register their codec as a
  `Component(provider, interface, CHAT, factory=<Codec class>)` on their
  interface `FRAGMENT` (zero-arg factory — the front door calls it bare);
  added `Catalog.components_for(provider, capability)` as the public lookup.
  Unpinned front-door resolution auto-selects only among component-backed
  interfaces (then resolve's own newest-wins ordering): the nodes-only
  `openai/responses` stub is newer-released than `chat_completions` and
  would otherwise win resolution it cannot serve; it stays reachable by
  explicit `interface=` pin (which fails at the component lookup with the
  install-hint `LookupError`).
- **Decision (2026-07-13, WU-16):** door 2 is literally door 1 —
  `chat_model()` defers `from ocai.chat import model` to call time and calls
  it with `catalog=Catalog.of(FRAGMENT)`; the thinnest truthful sugar, one
  code path. Import contracts: lint-imports flagged the function-level
  seams, so the layers contract gained `ocai.chat -> {convert.catalog,
  runtime.binding, wire.hosting, wire.transport}`, the plugin contract
  gained the two door-2 edges (`ocai.openai.chat_completions -> ocai.chat`,
  `ocai.anthropic.messages -> ocai.chat`), and the httpx contract gained
  `ocai.chat -> ocai.wire.transport` — all documented in pyproject comments.
- **Decision (2026-07-13, WU-16):** `interceptors=` wraps the facade in
  `InterceptedChatModel` (lives in `chat/facade.py`, the one sanctioned
  composing module): `compose`/`acompose` folded once at construction;
  `stream`/`astream` pass through UNintercepted (documented — the
  `CallInterceptor` contract is unary `Call -> CallResult`; streaming
  interception is a later explicit seam, never a silent partial one).
- **Decision (2026-07-13, WU-16):** `dual.py` wrappers are generic
  `__getattr__` proxies over the bare-name/`a`-prefix convention (thread
  offload via `asyncio.to_thread`; `from_async` uses a lazy daemon portal
  thread with a private loop, `run_coroutine_threadsafe` per call); sync
  iterators bridge to async (and vice versa) one hop per item with
  non-iterating attributes (`.end`) passing through. Caveat recorded in the
  module docstring: `isinstance` against runtime_checkable protocols uses
  `inspect.getattr_static` (3.12+) and cannot see the synthesized faces —
  conformance is behavioral, asserted structurally in tests.
- **Decision (2026-07-13, WU-16):** the one prose mention of "no
  `Workspace`/container object" in `binding.py` stays — it mirrors
  architecture §5's deliberate negative statement; the class, its exports,
  and every load-bearing docstring reference are gone.
